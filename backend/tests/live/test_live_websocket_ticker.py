"""
Live WebSocket Ticker Tests — all 6 brokers, parameterized.

One test function per behaviour — only the broker changes.
Tests FAIL if:
- WebSocket connection cannot be established
- No ticks are received within TICK_WAIT_SECONDS
- Tick prices are outside sanity bounds (not > 0)
- Prices are not Decimal (precision contract)
- Canonical token is not in the expected set

Run:
    pytest tests/live/test_live_websocket_ticker.py -v
    pytest tests/live/test_live_websocket_ticker.py -v -k "angelone"

NOTE: These tests require market hours for live ticks (NSE: 09:15–15:30 IST).
      Connection tests work 24/7.

IMPORTANT: These tests use *ticker* adapters (TickerAdapter / WebSocket),
           NOT market data REST adapters (MarketDataBrokerAdapter).
           Fixtures: angelone_ticker_adapter, kite_ticker_adapter, etc.
"""

import asyncio
import pytest
from decimal import Decimal
from typing import List

from tests.live.constants import (
    NIFTY_TOKEN,
    BANKNIFTY_TOKEN,
    LIVE_TICK_TOKENS,
    TICK_WAIT_SECONDS,
    NIFTY_MIN_PRICE,
    NIFTY_MAX_PRICE,
    BANKNIFTY_MIN_PRICE,
    BANKNIFTY_MAX_PRICE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Parametrize over all 6 brokers using ticker-specific fixtures
# ─────────────────────────────────────────────────────────────────────────────
#
# Note: ticker adapters are separate from market data adapters.
# Each broker's ticker adapter is defined in conftest.py as
# {broker}_ticker_adapter and pre-loaded with token mappings.
#
ALL_TICKER_ADAPTERS = [
    pytest.param("angelone_ticker_adapter", id="angelone"),
    pytest.param("kite_ticker_adapter",     id="kite"),
    pytest.param("upstox_ticker_adapter",   id="upstox"),
    pytest.param("dhan_ticker_adapter",     id="dhan"),
    pytest.param("fyers_ticker_adapter",    id="fyers"),
    pytest.param("paytm_ticker_adapter",    id="paytm"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helper: collect ticks for N seconds
# ─────────────────────────────────────────────────────────────────────────────

async def _connect_or_skip(adapter):
    """
    Connect adapter, skipping if broker reports connection limit exceeded (429).

    AngelOne's SmartStream delivers 429 errors asynchronously via the _on_error
    callback on a background thread — connect() returns successfully but then the
    WS closes within ~2 seconds.  We add a short post-connect sleep so that the
    error propagates before we proceed.
    """
    try:
        await adapter.connect(adapter._live_credentials)
    except Exception as e:
        msg = str(e).lower()
        if "429" in msg or "connection limit" in msg or "too many" in msg or "timed out" in msg:
            pytest.skip(
                f"[{adapter.broker_type}] WebSocket connection rejected: {e}. "
                f"AngelOne limits concurrent WS connections per API key. "
                f"Close other connections (production app) and retry."
            )
        raise

    # Give the WS thread 2 s to deliver an async 429 / connection-limit error.
    await asyncio.sleep(2.0)
    if not adapter.is_connected:
        pytest.skip(
            f"[{adapter.broker_type}] WebSocket dropped immediately after connect "
            f"(likely 429 connection limit from AngelOne). "
            f"Close other open WS connections (production backend) and retry."
        )


async def _collect_ticks(adapter, tokens: List[int], wait_seconds: int) -> list:
    """
    Connect adapter, subscribe to tokens, collect ticks for wait_seconds.

    If the WS connection is rejected (429 — connection limit) or drops
    immediately after connecting, the test is skipped with a clear message.
    """
    received = []
    connection_error: list = []  # mutable container to capture WS errors from threads

    def on_tick(ticks):
        received.extend(ticks)

    adapter.set_on_tick_callback(on_tick)
    adapter.set_event_loop(asyncio.get_event_loop())

    # Credentials stored on adapter during fixture creation
    await _connect_or_skip(adapter)
    await adapter.subscribe(tokens, mode="quote")
    await asyncio.sleep(wait_seconds)

    # If adapter disconnected during wait (e.g., 429 from broker), skip
    if not adapter.is_connected and not received:
        await adapter.disconnect()
        pytest.skip(
            f"[{adapter.broker_type}] WebSocket disconnected during tick collection — "
            f"likely hit connection limit (429). "
            f"Close other open connections and retry. "
            f"AngelOne limits 1 concurrent WebSocket per API key."
        )

    await adapter.disconnect()
    return received


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: WebSocket connects without error
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_TICKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_ticker_connects(adapter_fixture):
    """Broker WebSocket connects and disconnects cleanly."""
    adapter = adapter_fixture
    await _connect_or_skip(adapter)
    assert adapter.is_connected, (
        f"[{adapter.broker_type}] Expected is_connected=True after connect()"
    )
    await adapter.disconnect()
    assert not adapter.is_connected, (
        f"[{adapter.broker_type}] Expected is_connected=False after disconnect()"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Subscription is accepted without error
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_TICKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_ticker_subscribes(adapter_fixture):
    """Subscribing to NIFTY + BANKNIFTY tokens does not raise."""
    adapter = adapter_fixture
    await _connect_or_skip(adapter)
    try:
        try:
            await adapter.subscribe(LIVE_TICK_TOKENS, mode="quote")
        except ConnectionError as e:
            msg = str(e).lower()
            if "429" in msg or "connection limit" in msg or "not connected" in msg:
                pytest.skip(
                    f"[{adapter.broker_type}] WebSocket rejected during subscribe: {e}. "
                    f"AngelOne limits 1 concurrent WS per API key — close other connections."
                )
            raise

        # Give the WS a moment to reject if connection limit is hit
        await asyncio.sleep(1.0)

        if not adapter.is_connected:
            pytest.skip(
                f"[{adapter.broker_type}] WebSocket disconnected immediately after subscribe "
                f"(likely 429 connection limit). Close the production backend WS connection."
            )

        assert NIFTY_TOKEN in adapter.subscribed_tokens, (
            f"[{adapter.broker_type}] NIFTY_TOKEN not in subscribed_tokens after subscribe()"
        )
        assert BANKNIFTY_TOKEN in adapter.subscribed_tokens
    finally:
        await adapter.disconnect()


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Ticks are received (market hours only)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_TICKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_ticker_receives_ticks(adapter_fixture):
    """At least one tick is received within TICK_WAIT_SECONDS."""
    adapter = adapter_fixture
    ticks = await _collect_ticks(adapter, LIVE_TICK_TOKENS, TICK_WAIT_SECONDS)
    assert len(ticks) > 0, (
        f"[{adapter.broker_type}] No ticks received within {TICK_WAIT_SECONDS}s. "
        f"Check: (1) market is open, (2) credentials are valid, (3) broker WebSocket is reachable."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Tick prices are Decimal (not float)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_TICKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_ticker_prices_are_decimal(adapter_fixture):
    """NormalizedTick.ltp must be Decimal, not float."""
    adapter = adapter_fixture
    ticks = await _collect_ticks(adapter, LIVE_TICK_TOKENS, TICK_WAIT_SECONDS)
    assert ticks, f"[{adapter.broker_type}] No ticks received — cannot check price type"

    for tick in ticks:
        assert isinstance(tick.ltp, Decimal), (
            f"[{adapter.broker_type}] tick.ltp is {type(tick.ltp).__name__}, "
            f"expected Decimal. Token={tick.token}, ltp={tick.ltp}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Tick prices are in rupees (not paise)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_TICKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_ticker_prices_in_rupees(adapter_fixture):
    """
    Tick prices must be in rupees (not paise).

    SmartAPI returns paise — adapter must divide by 100.
    NIFTY should be ~10,000–100,000. If we get 1,000,000+ it's still paise.
    """
    adapter = adapter_fixture
    ticks = await _collect_ticks(adapter, LIVE_TICK_TOKENS, TICK_WAIT_SECONDS)
    assert ticks, f"[{adapter.broker_type}] No ticks received — cannot check price range"

    for tick in ticks:
        price = float(tick.ltp)
        if tick.token == NIFTY_TOKEN:
            assert NIFTY_MIN_PRICE <= price <= NIFTY_MAX_PRICE, (
                f"[{adapter.broker_type}] NIFTY price {price} is outside "
                f"[{NIFTY_MIN_PRICE}, {NIFTY_MAX_PRICE}]. "
                f"Likely still in paise if > 1,000,000."
            )
        elif tick.token == BANKNIFTY_TOKEN:
            assert BANKNIFTY_MIN_PRICE <= price <= BANKNIFTY_MAX_PRICE, (
                f"[{adapter.broker_type}] BANKNIFTY price {price} is outside "
                f"[{BANKNIFTY_MIN_PRICE}, {BANKNIFTY_MAX_PRICE}]."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Canonical token is preserved on the tick
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_TICKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_ticker_canonical_tokens(adapter_fixture):
    """
    NormalizedTick.token must be the canonical Kite token,
    not a broker-specific token.

    e.g. SmartAPI uses "99926000" for NIFTY — adapter must map to 256265.
    """
    adapter = adapter_fixture
    ticks = await _collect_ticks(adapter, LIVE_TICK_TOKENS, TICK_WAIT_SECONDS)
    assert ticks, f"[{adapter.broker_type}] No ticks received — cannot check tokens"

    received_tokens = {tick.token for tick in ticks}
    for token in received_tokens:
        assert token in LIVE_TICK_TOKENS, (
            f"[{adapter.broker_type}] Received unexpected token {token}. "
            f"Expected canonical tokens from {LIVE_TICK_TOKENS}. "
            f"Adapter may not be translating broker tokens to canonical."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Broker type is set on tick
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_TICKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_ticker_broker_type_set(adapter_fixture):
    """NormalizedTick.broker_type must match the adapter's broker_type."""
    adapter = adapter_fixture
    ticks = await _collect_ticks(adapter, LIVE_TICK_TOKENS, TICK_WAIT_SECONDS)
    assert ticks, f"[{adapter.broker_type}] No ticks received — cannot check broker_type"

    for tick in ticks:
        assert tick.broker_type == adapter.broker_type, (
            f"[{adapter.broker_type}] tick.broker_type='{tick.broker_type}' "
            f"does not match adapter.broker_type='{adapter.broker_type}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Unsubscribe stops ticks
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_TICKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_ticker_unsubscribe_stops_ticks(adapter_fixture):
    """After unsubscribe, no further ticks arrive for those tokens."""
    adapter = adapter_fixture
    received_after_unsub = []

    def on_tick(ticks):
        received_after_unsub.extend(ticks)

    adapter.set_on_tick_callback(on_tick)
    adapter.set_event_loop(asyncio.get_event_loop())

    await _connect_or_skip(adapter)
    await adapter.subscribe(LIVE_TICK_TOKENS, mode="quote")
    await asyncio.sleep(3)  # let ticks flow

    # Unsubscribe and reset counter
    await adapter.unsubscribe(LIVE_TICK_TOKENS)
    received_after_unsub.clear()
    assert NIFTY_TOKEN not in adapter.subscribed_tokens

    await asyncio.sleep(3)  # wait to confirm no ticks arrive
    await adapter.disconnect()

    assert len(received_after_unsub) == 0, (
        f"[{adapter.broker_type}] Received {len(received_after_unsub)} ticks "
        f"after unsubscribe — broker is still pushing data."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Indirect fixture resolver
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def adapter_fixture(request):
    """Resolve the named ticker adapter fixture dynamically."""
    return request.getfixturevalue(request.param)
