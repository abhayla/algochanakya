"""Tests for FailoverController credential check before failback — Layer 3.3.

Tests:
- Failback skipped when primary credentials are invalid and non-refreshable
- Failback attempts refresh before switching back
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime

from app.services.brokers.market_data.ticker.failover import FailoverController


@pytest.fixture
def controller():
    fc = FailoverController(primary_broker="smartapi", secondary_broker="kite")
    return fc


@pytest.fixture
def mock_deps(controller):
    """Set up mock dependencies for failover controller."""
    pool = MagicMock()
    pool.migrate_subscriptions = AsyncMock()
    pool.credentials_valid = MagicMock(return_value=False)

    router = MagicMock()
    router.switch_users_broker = AsyncMock()

    health = MagicMock()
    health.set_on_health_change = MagicMock()
    primary_health = MagicMock()
    primary_health.health_score = 80.0  # Healthy enough for failback
    health.get_health = MagicMock(return_value=primary_health)

    controller.set_dependencies(pool, router, health)
    return pool, router, health


class TestFailbackSkippedWhenCredentialsInvalid:
    @pytest.mark.asyncio
    async def test_failback_skipped_for_non_refreshable(self, controller, mock_deps):
        """If primary credentials are invalid and broker can't auto-refresh,
        failback should NOT execute."""
        pool, router, health = mock_deps

        # Simulate failed-over state
        controller.is_failed_over = True
        controller.active_broker = "kite"

        pool.credentials_valid.return_value = False

        with patch(
            "app.services.brokers.market_data.ticker.failover.can_auto_refresh",
            return_value=False,
        ):
            # Call _execute_failback directly — should skip
            await controller._execute_failback()

            # Should NOT have migrated subscriptions
            pool.migrate_subscriptions.assert_not_called()


class TestFailbackAttemptsRefresh:
    @pytest.mark.asyncio
    async def test_failback_refreshes_before_switching(self, controller, mock_deps):
        """If primary credentials are invalid but broker can auto-refresh,
        failback should attempt refresh first."""
        pool, router, health = mock_deps

        controller.is_failed_over = True
        controller.active_broker = "kite"

        # First call: invalid, second call (after refresh): valid
        pool.credentials_valid.side_effect = [False, True]

        with patch(
            "app.services.brokers.market_data.ticker.failover.can_auto_refresh",
            return_value=True,
        ), patch(
            "app.services.brokers.market_data.ticker.failover.refresh_broker_token",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_refresh:
            await controller._execute_failback()

            mock_refresh.assert_called_once_with("smartapi")
            pool.migrate_subscriptions.assert_called_once()

    @pytest.mark.asyncio
    async def test_failback_skipped_when_refresh_fails(self, controller, mock_deps):
        """If refresh attempt fails, failback should be skipped."""
        pool, router, health = mock_deps

        controller.is_failed_over = True
        controller.active_broker = "kite"

        pool.credentials_valid.return_value = False

        with patch(
            "app.services.brokers.market_data.ticker.failover.can_auto_refresh",
            return_value=True,
        ), patch(
            "app.services.brokers.market_data.ticker.failover.refresh_broker_token",
            new_callable=AsyncMock,
            return_value=False,
        ):
            await controller._execute_failback()

            pool.migrate_subscriptions.assert_not_called()
