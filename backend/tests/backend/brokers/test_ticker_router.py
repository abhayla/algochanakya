"""Tests for TickerRouter — user fan-out, cached ticks, dispatch."""

import asyncio
import json
import pytest
import pytest_asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from starlette.websockets import WebSocketState

from app.services.brokers.market_data.ticker.models import NormalizedTick
from app.services.brokers.market_data.ticker.router import TickerRouter


# ─── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_ws(connected: bool = True) -> MagicMock:
    """Create a mock WebSocket."""
    ws = MagicMock()
    ws.client_state = WebSocketState.CONNECTED if connected else WebSocketState.DISCONNECTED
    ws.send_text = AsyncMock()
    return ws


def make_tick(token: int = 256265, ltp: float = 24500.0, broker: str = "smartapi") -> NormalizedTick:
    return NormalizedTick(
        token=token,
        ltp=Decimal(str(ltp)),
        broker_type=broker,
        timestamp=datetime(2026, 2, 16, 10, 30, 0),
    )


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_router():
    """Reset TickerRouter singleton before each test."""
    TickerRouter.reset_instance()
    yield
    TickerRouter.reset_instance()


@pytest_asyncio.fixture
async def router():
    """Create a TickerRouter with a mock pool."""
    r = TickerRouter.get_instance()
    mock_pool = AsyncMock()
    r.set_pool(mock_pool)
    return r


# ─── Tests ─────────────────────────────────────────────────────────────────────

class TestUserManagement:
    @pytest.mark.asyncio
    async def test_register_user(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        assert router.connected_users == 1

    @pytest.mark.asyncio
    async def test_unregister_user(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.unregister_user("user-1")
        assert router.connected_users == 0

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_user(self, router: TickerRouter):
        # Should not raise
        await router.unregister_user("nonexistent")

    @pytest.mark.asyncio
    async def test_get_user_broker(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "kite")
        assert router.get_user_broker("user-1") == "kite"
        assert router.get_user_broker("nonexistent") is None


class TestSubscriptions:
    @pytest.mark.asyncio
    async def test_subscribe_forwards_to_pool(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.subscribe("user-1", [256265])

        router._pool.subscribe.assert_awaited_once_with("smartapi", [256265], "quote")
        assert router.total_token_subscriptions == 1

    @pytest.mark.asyncio
    async def test_subscribe_unregistered_user_noop(self, router: TickerRouter):
        await router.subscribe("nonexistent", [256265])
        router._pool.subscribe.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_duplicate_subscribe_noop(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.subscribe("user-1", [256265])
        await router.subscribe("user-1", [256265])  # duplicate
        # Pool should only be called once
        assert router._pool.subscribe.await_count == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.subscribe("user-1", [256265])
        await router.unsubscribe("user-1", [256265])

        router._pool.unsubscribe.assert_awaited_once_with("smartapi", [256265])
        assert router.total_token_subscriptions == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_token_noop(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.unsubscribe("user-1", [999999])
        router._pool.unsubscribe.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unregister_cleans_up_subscriptions(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.subscribe("user-1", [256265, 260105])

        await router.unregister_user("user-1")
        assert router.total_token_subscriptions == 0
        router._pool.unsubscribe.assert_awaited()


class TestCachedTicks:
    @pytest.mark.asyncio
    async def test_subscribe_sends_cached_tick(self, router: TickerRouter):
        # Pre-populate cache via dispatch
        tick = make_tick()
        ws1 = make_mock_ws()
        await router.register_user("user-1", ws1, "smartapi")
        await router.subscribe("user-1", [256265])
        await router.dispatch([tick])

        # New user subscribes — should get cached tick immediately
        ws2 = make_mock_ws()
        await router.register_user("user-2", ws2, "smartapi")
        await router.subscribe("user-2", [256265])

        # ws2 should have received the cached tick
        assert ws2.send_text.await_count == 1
        sent = json.loads(ws2.send_text.call_args[0][0])
        assert sent["type"] == "ticks"
        assert sent["data"][0]["token"] == 256265

    @pytest.mark.asyncio
    async def test_get_cached_tick(self, router: TickerRouter):
        tick = make_tick()
        await router.dispatch([tick])
        cached = router.get_cached_tick(256265)
        assert cached is not None
        assert cached.ltp == Decimal("24500.0")

    @pytest.mark.asyncio
    async def test_no_cached_tick(self, router: TickerRouter):
        assert router.get_cached_tick(999999) is None


class TestDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_to_single_user(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.subscribe("user-1", [256265])

        tick = make_tick()
        await router.dispatch([tick])

        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["type"] == "ticks"
        assert sent["data"][0]["token"] == 256265
        assert sent["data"][0]["ltp"] == 24500.0

    @pytest.mark.asyncio
    async def test_dispatch_to_multiple_users(self, router: TickerRouter):
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        await router.register_user("user-1", ws1, "smartapi")
        await router.register_user("user-2", ws2, "smartapi")
        await router.subscribe("user-1", [256265])
        await router.subscribe("user-2", [256265])

        tick = make_tick()
        await router.dispatch([tick])

        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_only_to_subscribed_users(self, router: TickerRouter):
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        await router.register_user("user-1", ws1, "smartapi")
        await router.register_user("user-2", ws2, "smartapi")
        await router.subscribe("user-1", [256265])
        # user-2 subscribes to different token
        await router.subscribe("user-2", [260105])

        tick = make_tick(token=256265)
        await router.dispatch([tick])

        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dispatch_multi_token(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.subscribe("user-1", [256265, 260105])

        t1 = make_tick(token=256265, ltp=24500.0)
        t2 = make_tick(token=260105, ltp=52000.0)
        await router.dispatch([t1, t2])

        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert len(sent["data"]) == 2

    @pytest.mark.asyncio
    async def test_dispatch_empty_ticks(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.subscribe("user-1", [256265])

        await router.dispatch([])  # should not raise or send
        ws.send_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dispatch_no_subscribers(self, router: TickerRouter):
        tick = make_tick(token=999999)
        # Should not raise even with no subscribers
        await router.dispatch([tick])

    @pytest.mark.asyncio
    async def test_broken_websocket_unregisters_user(self, router: TickerRouter):
        ws = make_mock_ws()
        ws.send_text.side_effect = Exception("connection closed")
        await router.register_user("user-1", ws, "smartapi")
        await router.subscribe("user-1", [256265])

        tick = make_tick()
        await router.dispatch([tick])

        # User should be auto-unregistered
        assert router.connected_users == 0


class TestFailover:
    @pytest.mark.asyncio
    async def test_switch_users_broker(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")

        await router.switch_users_broker("smartapi", "fyers")
        assert router.get_user_broker("user-1") == "fyers"

    @pytest.mark.asyncio
    async def test_failover_notification_sent(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")

        await router.switch_users_broker("smartapi", "fyers")

        # Should receive failover notification
        assert ws.send_text.await_count >= 1
        last_call = ws.send_text.call_args[0][0]
        msg = json.loads(last_call)
        assert msg["type"] == "failover"
        assert msg["data"]["from_broker"] == "smartapi"
        assert msg["data"]["to_broker"] == "fyers"

    @pytest.mark.asyncio
    async def test_switch_only_affects_matching_broker(self, router: TickerRouter):
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        await router.register_user("user-1", ws1, "smartapi")
        await router.register_user("user-2", ws2, "kite")

        await router.switch_users_broker("smartapi", "fyers")
        assert router.get_user_broker("user-1") == "fyers"
        assert router.get_user_broker("user-2") == "kite"  # unchanged


class TestDiagnostics:
    @pytest.mark.asyncio
    async def test_stats(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.subscribe("user-1", [256265])

        s = router.stats()
        assert s["connected_users"] == 1
        assert s["total_token_subscriptions"] == 1
        assert s["users_by_broker"]["smartapi"] == 1

    @pytest.mark.asyncio
    async def test_get_subscribed_tokens_for_broker(self, router: TickerRouter):
        ws = make_mock_ws()
        await router.register_user("user-1", ws, "smartapi")
        await router.subscribe("user-1", [256265, 260105])

        tokens = router.get_subscribed_tokens_for_broker("smartapi")
        assert tokens == {256265, 260105}

        empty = router.get_subscribed_tokens_for_broker("nonexistent")
        assert empty == set()
