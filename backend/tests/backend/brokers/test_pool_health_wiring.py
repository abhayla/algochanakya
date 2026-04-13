"""Tests for TickerPool → HealthMonitor wiring — Layer 1.3.

Tests that TickerPool correctly forwards events to HealthMonitor:
- Tick arrivals → record_ticks()
- Adapter creation → record_connect()
- Adapter removal → record_disconnect()
- Adapter errors → record_error()
- Backward compat: pool works without health_monitor
"""

import asyncio
import pytest
import pytest_asyncio
from decimal import Decimal
from typing import List, Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.brokers.market_data.ticker.models import NormalizedTick
from app.services.brokers.market_data.ticker.adapter_base import TickerAdapter
from app.services.brokers.market_data.ticker.pool import TickerPool
from app.services.brokers.market_data.ticker.health import HealthMonitor


# ─── Mock Adapter ──────────────────────────────────────────────────────────────

class MockTickerAdapter(TickerAdapter):
    """Concrete TickerAdapter for testing."""

    def __init__(self, broker_type: str = "mock"):
        super().__init__(broker_type)

    async def _connect_ws(self, credentials: dict) -> None:
        pass

    async def _disconnect_ws(self) -> None:
        pass

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        pass

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        pass

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        return canonical_tokens

    def _get_canonical_token(self, broker_token: Any) -> int:
        return broker_token

    def _parse_tick(self, raw_data: Any) -> List[NormalizedTick]:
        return []


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_pool():
    """Reset TickerPool singleton before each test."""
    TickerPool.reset_instance()
    yield
    TickerPool.reset_instance()


@pytest_asyncio.fixture
async def health_monitor():
    """Create a HealthMonitor with mock broker registered."""
    m = HealthMonitor()
    m.register_adapter("mock")
    return m


@pytest_asyncio.fixture
async def pool_with_health(health_monitor):
    """TickerPool initialized with a HealthMonitor."""
    p = TickerPool.get_instance()
    on_tick = AsyncMock()
    await p.initialize(on_tick_callback=on_tick, health_monitor=health_monitor)
    p.register_adapter("mock", MockTickerAdapter)
    p.set_credentials("mock", {"key": "test"})
    yield p
    await p.shutdown()


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestPoolForwardsTicksToHealthMonitor:
    @pytest.mark.asyncio
    async def test_ticks_recorded_in_health_monitor(self, pool_with_health, health_monitor):
        """When adapter dispatches ticks, pool records them in health monitor."""
        tick = NormalizedTick(token=256265, ltp=Decimal("24500"), broker_type="mock")
        await pool_with_health._on_adapter_tick([tick])

        health = health_monitor.get_health("mock")
        assert health.tick_count_1min == 1


class TestPoolRecordsConnectOnAdapterCreation:
    @pytest.mark.asyncio
    async def test_connect_recorded(self, pool_with_health, health_monitor):
        """When adapter is created, pool records connect in health monitor."""
        await pool_with_health.get_or_create_adapter("mock")

        health = health_monitor.get_health("mock")
        assert health.is_connected is True


class TestPoolRecordsDisconnectOnAdapterRemoval:
    @pytest.mark.asyncio
    async def test_disconnect_recorded(self, pool_with_health, health_monitor):
        """When adapter is removed, pool records disconnect in health monitor."""
        await pool_with_health.get_or_create_adapter("mock")
        await pool_with_health.remove_adapter("mock")

        health = health_monitor.get_health("mock")
        assert health.is_connected is False


class TestPoolForwardsErrorsToHealthMonitor:
    @pytest.mark.asyncio
    async def test_adapter_error_recorded(self, pool_with_health, health_monitor):
        """When adapter reports error, pool forwards to health monitor."""
        adapter = await pool_with_health.get_or_create_adapter("mock")
        # Simulate adapter error via the error callback
        adapter._report_error("websocket_error", "Connection timeout")

        health = health_monitor.get_health("mock")
        assert health.error_count_5min >= 1


class TestPoolWorksWithoutHealthMonitor:
    @pytest.mark.asyncio
    async def test_no_health_monitor_no_crash(self):
        """Pool still works when initialized without health_monitor."""
        p = TickerPool.get_instance()
        on_tick = AsyncMock()
        await p.initialize(on_tick_callback=on_tick)
        p.register_adapter("mock", MockTickerAdapter)
        p.set_credentials("mock", {"key": "test"})

        # All operations should work without health_monitor
        adapter = await p.get_or_create_adapter("mock")
        assert adapter.is_connected

        tick = NormalizedTick(token=256265, ltp=Decimal("24500"), broker_type="mock")
        await p._on_adapter_tick([tick])  # Should not raise

        await p.remove_adapter("mock")
        await p.shutdown()
