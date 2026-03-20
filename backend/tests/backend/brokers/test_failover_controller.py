"""Tests for FailoverController — failover, failback, flap prevention."""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.constants.brokers import ORG_ACTIVE_BROKERS
from app.services.brokers.market_data.ticker.failover import FailoverController
from app.services.brokers.market_data.ticker.health import (
    HealthMonitor,
    AdapterHealth,
)


# ─── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    pool.migrate_subscriptions = AsyncMock()
    return pool


@pytest.fixture
def mock_router():
    router = MagicMock()
    router.switch_users_broker = AsyncMock()
    return router


@pytest.fixture
def health_monitor():
    m = HealthMonitor()
    m.register_adapter("smartapi")
    m.register_adapter("kite")
    return m


@pytest.fixture
def controller(mock_pool, mock_router, health_monitor):
    fc = FailoverController(primary_broker="smartapi", secondary_broker="kite")
    fc.set_dependencies(mock_pool, mock_router, health_monitor)
    return fc


# ─── Initialization Tests ─────────────────────────────────────────────────────


class TestInitialization:
    def test_defaults(self):
        fc = FailoverController()
        assert fc.primary_broker == ORG_ACTIVE_BROKERS[0]
        assert fc.secondary_broker == (
            ORG_ACTIVE_BROKERS[1] if len(ORG_ACTIVE_BROKERS) > 1 else ORG_ACTIVE_BROKERS[0]
        )
        assert fc.active_broker == ORG_ACTIVE_BROKERS[0]
        assert not fc.is_failed_over

    def test_custom_brokers(self):
        fc = FailoverController(primary_broker="dhan", secondary_broker="fyers")
        assert fc.primary_broker == "dhan"
        assert fc.secondary_broker == "fyers"

    def test_set_dependencies(self, controller, mock_pool, mock_router, health_monitor):
        assert controller._pool is mock_pool
        assert controller._router is mock_router
        assert controller._health_monitor is health_monitor
        assert health_monitor._on_health_change_callback is not None


# ─── Failover Tests ───────────────────────────────────────────────────────────


class TestFailover:
    @pytest.mark.asyncio
    async def test_failover_executes_on_primary_degradation(
        self, controller, mock_pool, mock_router
    ):
        """Failover should migrate subscriptions and switch routing."""
        await controller._on_health_degraded("smartapi", 20.0)

        mock_pool.migrate_subscriptions.assert_called_once_with(
            "smartapi", "kite"
        )
        mock_router.switch_users_broker.assert_called_once_with(
            "smartapi", "kite"
        )
        assert controller.active_broker == "kite"
        assert controller.is_failed_over
        assert controller._last_failover_time is not None

    @pytest.mark.asyncio
    async def test_failover_ignores_non_active_broker(
        self, controller, mock_pool
    ):
        """Degradation on non-active broker should be ignored."""
        await controller._on_health_degraded("kite", 20.0)
        mock_pool.migrate_subscriptions.assert_not_called()
        assert controller.active_broker == "smartapi"

    @pytest.mark.asyncio
    async def test_flap_prevention(self, controller, mock_pool):
        """Failover should be blocked within FLAP_PREVENTION_SECONDS."""
        controller._last_failover_time = datetime.now()

        await controller._on_health_degraded("smartapi", 20.0)
        mock_pool.migrate_subscriptions.assert_not_called()

    @pytest.mark.asyncio
    async def test_flap_prevention_allows_after_cooldown(
        self, controller, mock_pool, mock_router
    ):
        """Failover should proceed after cooldown period."""
        controller._last_failover_time = datetime.now() - timedelta(
            seconds=FailoverController.FLAP_PREVENTION_SECONDS + 1
        )

        await controller._on_health_degraded("smartapi", 20.0)
        mock_pool.migrate_subscriptions.assert_called_once()

    @pytest.mark.asyncio
    async def test_secondary_degradation_logs_error(
        self, controller, mock_pool
    ):
        """If secondary also degrades during failover, no further action."""
        controller.active_broker = "kite"
        controller.is_failed_over = True

        await controller._on_health_degraded("kite", 20.0)
        mock_pool.migrate_subscriptions.assert_not_called()

    @pytest.mark.asyncio
    async def test_failover_handles_pool_error(
        self, controller, mock_pool
    ):
        """Failover should handle pool.migrate_subscriptions failure."""
        mock_pool.migrate_subscriptions.side_effect = Exception("Connection failed")

        await controller._on_health_degraded("smartapi", 20.0)
        # Should not crash, state should remain unchanged
        assert controller.active_broker == "smartapi"
        assert not controller.is_failed_over


# ─── Failback Tests ───────────────────────────────────────────────────────────


class TestFailback:
    @pytest.mark.asyncio
    async def test_failback_executes(
        self, controller, mock_pool, mock_router, health_monitor
    ):
        """Failback should migrate back to primary."""
        # First, simulate a failover
        controller.active_broker = "kite"
        controller.is_failed_over = True

        # Set primary as healthy
        primary_health = health_monitor.get_health("smartapi")
        primary_health.health_score = 80.0

        await controller._execute_failback()

        mock_pool.migrate_subscriptions.assert_called_once_with(
            "kite", "smartapi"
        )
        mock_router.switch_users_broker.assert_called_once_with(
            "kite", "smartapi"
        )
        assert controller.active_broker == "smartapi"
        assert not controller.is_failed_over

    @pytest.mark.asyncio
    async def test_failback_handles_error(
        self, controller, mock_pool
    ):
        """Failback should handle errors gracefully."""
        controller.active_broker = "kite"
        controller.is_failed_over = True
        mock_pool.migrate_subscriptions.side_effect = Exception("Error")

        await controller._execute_failback()
        # State should remain failed over
        assert controller.is_failed_over


# ─── Status Tests ──────────────────────────────────────────────────────────────


class TestStatus:
    def test_status_default(self, controller):
        status = controller.status()
        assert status["active_broker"] == "smartapi"
        assert status["is_failed_over"] is False
        assert status["primary_broker"] == "smartapi"
        assert status["secondary_broker"] == "kite"
        assert status["last_failover_time"] is None

    @pytest.mark.asyncio
    async def test_status_after_failover(
        self, controller, mock_pool, mock_router
    ):
        await controller._on_health_degraded("smartapi", 20.0)
        status = controller.status()
        assert status["active_broker"] == "kite"
        assert status["is_failed_over"] is True
        assert status["last_failover_time"] is not None


# ─── Lifecycle Tests ───────────────────────────────────────────────────────────


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_stop_cancels_failback_task(self, controller):
        """Stop should cancel any running failback monitoring task."""
        controller._failback_task = asyncio.create_task(asyncio.sleep(100))
        await controller.stop()
        assert controller._failback_task.cancelled() or controller._failback_task.done()

    @pytest.mark.asyncio
    async def test_stop_without_failback_task(self, controller):
        """Stop should not raise if no failback task."""
        await controller.stop()
