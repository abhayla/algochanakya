"""Tests for TickerPool — ref-counted subscriptions, adapter lifecycle."""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime
from decimal import Decimal
from typing import List, Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.brokers.market_data.ticker.models import NormalizedTick
from app.services.brokers.market_data.ticker.adapter_base import TickerAdapter
from app.services.brokers.market_data.ticker.pool import TickerPool


# ─── Mock Adapter ──────────────────────────────────────────────────────────────

class MockTickerAdapter(TickerAdapter):
    """Concrete TickerAdapter for testing."""

    def __init__(self, broker_type: str = "mock"):
        super().__init__(broker_type)
        self.connect_calls: list = []
        self.disconnect_calls: int = 0
        self.subscribe_calls: list = []
        self.unsubscribe_calls: list = []

    async def _connect_ws(self, credentials: dict) -> None:
        self.connect_calls.append(credentials)

    async def _disconnect_ws(self) -> None:
        self.disconnect_calls += 1

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        self.subscribe_calls.append((broker_tokens, mode))

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        self.unsubscribe_calls.append(broker_tokens)

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        return canonical_tokens  # Identity mapping for tests

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
async def pool():
    """Create an initialized TickerPool."""
    p = TickerPool.get_instance()
    on_tick = AsyncMock()
    await p.initialize(on_tick_callback=on_tick)
    p.register_adapter("mock", MockTickerAdapter)
    p.set_credentials("mock", {"key": "test"})
    yield p
    await p.shutdown()


# ─── Tests ─────────────────────────────────────────────────────────────────────

class TestTickerPoolSingleton:
    def test_singleton_returns_same_instance(self):
        a = TickerPool.get_instance()
        b = TickerPool.get_instance()
        assert a is b

    def test_reset_creates_new_instance(self):
        a = TickerPool.get_instance()
        TickerPool.reset_instance()
        b = TickerPool.get_instance()
        assert a is not b


class TestAdapterRegistry:
    @pytest.mark.asyncio
    async def test_register_and_create_adapter(self, pool: TickerPool):
        adapter = await pool.get_or_create_adapter("mock")
        assert adapter.is_connected
        assert isinstance(adapter, MockTickerAdapter)
        assert pool.adapter_count == 1

    @pytest.mark.asyncio
    async def test_unregistered_broker_raises(self, pool: TickerPool):
        with pytest.raises(ValueError, match="No adapter registered"):
            await pool.get_or_create_adapter("unknown")

    @pytest.mark.asyncio
    async def test_no_credentials_raises(self, pool: TickerPool):
        pool.register_adapter("nocreds", MockTickerAdapter)
        with pytest.raises(ValueError, match="No credentials set"):
            await pool.get_or_create_adapter("nocreds")

    @pytest.mark.asyncio
    async def test_get_existing_adapter(self, pool: TickerPool):
        adapter1 = await pool.get_or_create_adapter("mock")
        adapter2 = await pool.get_or_create_adapter("mock")
        assert adapter1 is adapter2  # Same instance

    @pytest.mark.asyncio
    async def test_remove_adapter(self, pool: TickerPool):
        await pool.get_or_create_adapter("mock")
        assert pool.adapter_count == 1
        await pool.remove_adapter("mock")
        assert pool.adapter_count == 0


class TestRefCountedSubscriptions:
    @pytest.mark.asyncio
    async def test_first_subscribe_calls_adapter(self, pool: TickerPool):
        await pool.subscribe("mock", [256265])
        adapter: MockTickerAdapter = pool.get_adapter("mock")
        assert len(adapter.subscribe_calls) == 1
        assert adapter.subscribe_calls[0] == ([256265], "quote")
        assert pool.get_ref_count("mock", 256265) == 1

    @pytest.mark.asyncio
    async def test_second_subscribe_increments_ref_no_adapter_call(self, pool: TickerPool):
        await pool.subscribe("mock", [256265])
        await pool.subscribe("mock", [256265])
        adapter: MockTickerAdapter = pool.get_adapter("mock")
        # Only one adapter.subscribe call — second was ref-count only
        assert len(adapter.subscribe_calls) == 1
        assert pool.get_ref_count("mock", 256265) == 2

    @pytest.mark.asyncio
    async def test_partial_unsubscribe_no_adapter_call(self, pool: TickerPool):
        await pool.subscribe("mock", [256265])
        await pool.subscribe("mock", [256265])
        await pool.unsubscribe("mock", [256265])
        adapter: MockTickerAdapter = pool.get_adapter("mock")
        # No unsubscribe call — ref count went 2→1, not to 0
        assert len(adapter.unsubscribe_calls) == 0
        assert pool.get_ref_count("mock", 256265) == 1

    @pytest.mark.asyncio
    async def test_full_unsubscribe_calls_adapter(self, pool: TickerPool):
        await pool.subscribe("mock", [256265])
        await pool.unsubscribe("mock", [256265])
        adapter: MockTickerAdapter = pool.get_adapter("mock")
        assert len(adapter.unsubscribe_calls) == 1
        assert 256265 in adapter.unsubscribe_calls[0]
        assert pool.get_ref_count("mock", 256265) == 0

    @pytest.mark.asyncio
    async def test_multi_token_subscribe(self, pool: TickerPool):
        await pool.subscribe("mock", [256265, 260105, 257801])
        adapter: MockTickerAdapter = pool.get_adapter("mock")
        assert len(adapter.subscribe_calls) == 1
        tokens_sent = adapter.subscribe_calls[0][0]
        assert set(tokens_sent) == {256265, 260105, 257801}

    @pytest.mark.asyncio
    async def test_mixed_new_and_existing_tokens(self, pool: TickerPool):
        await pool.subscribe("mock", [256265])
        await pool.subscribe("mock", [256265, 260105])
        adapter: MockTickerAdapter = pool.get_adapter("mock")
        # Second call should only contain the NEW token 260105
        assert len(adapter.subscribe_calls) == 2
        assert adapter.subscribe_calls[1][0] == [260105]

    @pytest.mark.asyncio
    async def test_get_subscribed_tokens(self, pool: TickerPool):
        await pool.subscribe("mock", [256265, 260105])
        tokens = pool.get_subscribed_tokens("mock")
        assert tokens == {256265, 260105}


class TestTickDispatch:
    @pytest.mark.asyncio
    async def test_adapter_tick_forwarded_to_callback(self, pool: TickerPool):
        tick = NormalizedTick(token=256265, ltp=Decimal("24500"), broker_type="mock")
        await pool._on_adapter_tick([tick])
        pool._on_tick.assert_awaited_once_with([tick])

    @pytest.mark.asyncio
    async def test_no_callback_no_error(self):
        p = TickerPool.get_instance()
        await p.initialize(on_tick_callback=None)
        # Should not raise
        tick = NormalizedTick(token=1, ltp=Decimal("100"), broker_type="mock")
        await p._on_adapter_tick([tick])
        await p.shutdown()


class TestFailoverMigration:
    @pytest.mark.asyncio
    async def test_migrate_subscriptions(self, pool: TickerPool):
        pool.register_adapter("backup", MockTickerAdapter)
        pool.set_credentials("backup", {"key": "backup"})

        # Subscribe on primary
        await pool.subscribe("mock", [256265, 260105])
        assert pool.get_ref_count("mock", 256265) == 1

        # Migrate
        await pool.migrate_subscriptions("mock", "backup")

        # Backup should have the tokens
        assert pool.get_ref_count("backup", 256265) == 1
        assert pool.get_ref_count("backup", 260105) == 1
        # Source should be cleared
        assert pool.get_ref_count("mock", 256265) == 0


class TestDiagnostics:
    @pytest.mark.asyncio
    async def test_stats_output(self, pool: TickerPool):
        await pool.subscribe("mock", [256265])
        s = pool.stats()
        assert "adapters" in s
        assert "mock" in s["adapters"]
        assert s["adapters"]["mock"]["connected"] is True
        assert s["adapters"]["mock"]["subscribed_tokens"] == 1
        assert "ref_counts" in s
        assert s["ref_counts"]["mock"][256265] == 1

    @pytest.mark.asyncio
    async def test_active_adapters(self, pool: TickerPool):
        await pool.get_or_create_adapter("mock")
        assert "mock" in pool.active_adapters
