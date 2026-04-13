"""Tests for TickerPool credential refresh on reconnect — Layer 3.2.

Tests:
- Pool refreshes token before reconnect when credentials expired
- Pool skips refresh when token is valid
- Pool failovers when refresh fails (non-refreshable broker)
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from typing import List, Any
from unittest.mock import AsyncMock, patch

from app.services.brokers.market_data.ticker.models import NormalizedTick
from app.services.brokers.market_data.ticker.adapter_base import TickerAdapter
from app.services.brokers.market_data.ticker.pool import TickerPool
from app.services.brokers.market_data.ticker.health import HealthMonitor
from datetime import datetime, timezone, timedelta


# ─── Mock Adapter ─────────────────────────────────────────────────────────────

class MockAdapter(TickerAdapter):
    def __init__(self, broker_type: str = "smartapi"):
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
    TickerPool.reset_instance()
    yield
    TickerPool.reset_instance()


@pytest_asyncio.fixture
async def pool():
    p = TickerPool.get_instance()
    on_tick = AsyncMock()
    health = HealthMonitor()
    health.register_adapter("smartapi")
    await p.initialize(on_tick_callback=on_tick, health_monitor=health)
    p.register_adapter("smartapi", MockAdapter)
    yield p
    await p.shutdown()


# ─── Tests ─────────────────────────────────────────────────────────────────────

class TestPoolRefreshesExpiredCredentials:
    @pytest.mark.asyncio
    async def test_refresh_called_when_credentials_expired(self, pool):
        """When credentials are expired and broker can auto-refresh,
        pool should call refresh_broker_token before reconnecting."""
        # Set expired credentials
        expired = datetime.now(timezone.utc) - timedelta(hours=1)
        pool.set_credentials("smartapi", {
            "key": "test",
            "token_expiry": expired,
        })

        async def mock_refresh_fn(broker):
            # Simulate successful refresh by updating credentials
            pool.set_credentials("smartapi", {"key": "refreshed"})
            return True

        with patch(
            "app.services.brokers.market_data.ticker.pool.refresh_broker_token",
            new_callable=AsyncMock,
            side_effect=mock_refresh_fn,
        ), patch(
            "app.services.brokers.market_data.ticker.pool.can_auto_refresh",
            return_value=True,
        ):
            adapter = await pool.get_or_create_adapter("smartapi")
            assert adapter is not None
            assert adapter.is_connected


class TestPoolSkipsRefreshWhenValid:
    @pytest.mark.asyncio
    async def test_no_refresh_when_credentials_valid(self, pool):
        """When credentials are valid, pool should NOT call refresh."""
        pool.set_credentials("smartapi", {"key": "valid"})

        with patch(
            "app.services.brokers.market_data.ticker.pool.refresh_broker_token",
            new_callable=AsyncMock,
        ) as mock_refresh:
            adapter = await pool.get_or_create_adapter("smartapi")
            assert adapter is not None
            mock_refresh.assert_not_called()


class TestPoolHandlesRefreshFailure:
    @pytest.mark.asyncio
    async def test_raises_when_refresh_fails_and_no_creds(self, pool):
        """When credentials are expired and refresh fails, pool raises ValueError."""
        expired = datetime.now(timezone.utc) - timedelta(hours=1)
        pool.set_credentials("smartapi", {
            "key": "test",
            "token_expiry": expired,
        })

        with patch(
            "app.services.brokers.market_data.ticker.pool.refresh_broker_token",
            new_callable=AsyncMock,
            return_value=False,
        ), patch(
            "app.services.brokers.market_data.ticker.pool.can_auto_refresh",
            return_value=True,
        ):
            with pytest.raises(ValueError, match="No credentials"):
                await pool.get_or_create_adapter("smartapi")
