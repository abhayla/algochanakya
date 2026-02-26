"""
Live Market Data Tests (REST API) — all 6 brokers, parameterized.

Covers:
- get_quote()      — full quote with OHLC, volume, bid/ask
- get_ltp()        — lightweight last-traded price
- get_historical() — OHLCV candles over 5 trading days

Tests FAIL if:
- API returns an error / raises an exception
- Response prices are <= 0 or outside sanity bounds
- Prices are not Decimal
- OHLCV candles are empty or have zero close price

Run:
    pytest tests/live/test_live_market_data.py -v
    pytest tests/live/test_live_market_data.py -v -k "dhan"
"""

import pytest
from decimal import Decimal

from tests.live.constants import (
    NIFTY_SYMBOL,
    BANKNIFTY_SYMBOL,
    NIFTY_TOKEN,
    BANKNIFTY_TOKEN,
    HIST_FROM_DATE,
    HIST_TO_DATE,
    HIST_INTERVAL,
    NIFTY_MIN_PRICE,
    NIFTY_MAX_PRICE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: fetch historical candles with skip on known access errors
# ─────────────────────────────────────────────────────────────────────────────

async def _get_historical_or_skip(adapter, symbol, from_date, to_date, interval):
    """
    Fetch historical candles, skipping on access/permission errors.

    AngelOne historical API (getCandleData) requires:
    - A valid JWT token (8h expiry)
    - The API key must have historical data access enabled
    - A separate ANGEL_API_KEY_HISTORICAL may be required

    Skips with a clear message instead of failing on AG8001 (Invalid Token)
    or other access-denied errors, since these are config issues not test bugs.
    """
    from app.services.brokers.market_data.exceptions import DataNotAvailableError
    try:
        return await adapter.get_historical(symbol, from_date=from_date, to_date=to_date, interval=interval)
    except DataNotAvailableError as e:
        msg = str(e).lower()
        if "invalid token" in msg or "ag8001" in msg or "unauthorized" in msg or "access" in msg:
            pytest.skip(
                f"[{adapter.broker_type}] Historical API returned access error: {e}. "
                f"Check: (1) JWT token is fresh (8h expiry), "
                f"(2) ANGEL_HIST_API_KEY is set in backend/.env (separate key for historical data), "
                f"(3) The key has historical data access enabled in AngelOne developer console."
            )
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Parametrize over all 6 brokers
# ─────────────────────────────────────────────────────────────────────────────

ALL_BROKER_ADAPTERS = [
    pytest.param("angelone_adapter", id="angelone"),
    pytest.param("kite_adapter",     id="kite"),
    pytest.param("upstox_adapter",   id="upstox"),
    pytest.param("dhan_adapter",     id="dhan"),
    pytest.param("fyers_adapter",    id="fyers"),
    pytest.param("paytm_adapter",    id="paytm"),
]

TEST_SYMBOLS = [NIFTY_SYMBOL, BANKNIFTY_SYMBOL]


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: get_quote() returns valid quotes for NIFTY + BANKNIFTY
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_quote_returns_data(adapter_fixture):
    """get_quote() returns non-empty result for NIFTY and BANKNIFTY."""
    adapter = adapter_fixture
    result = await adapter.get_quote(TEST_SYMBOLS)

    assert result, (
        f"[{adapter.broker_type}] get_quote() returned empty dict. "
        f"Check if broker API is reachable and credentials are valid."
    )
    assert len(result) > 0, f"[{adapter.broker_type}] get_quote() returned 0 symbols"


@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_quote_prices_are_positive(adapter_fixture):
    """All returned quote last_prices must be > 0."""
    adapter = adapter_fixture
    result = await adapter.get_quote(TEST_SYMBOLS)
    assert result, f"[{adapter.broker_type}] get_quote() returned empty"

    for symbol, quote in result.items():
        assert quote.last_price > 0, (
            f"[{adapter.broker_type}] {symbol} last_price={quote.last_price} is not > 0"
        )


@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_quote_prices_are_decimal(adapter_fixture):
    """Quote last_price must be Decimal, not float."""
    adapter = adapter_fixture
    result = await adapter.get_quote(TEST_SYMBOLS)
    assert result, f"[{adapter.broker_type}] get_quote() returned empty"

    for symbol, quote in result.items():
        assert isinstance(quote.last_price, Decimal), (
            f"[{adapter.broker_type}] {symbol} last_price is {type(quote.last_price).__name__}, "
            f"expected Decimal"
        )


@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_quote_nifty_price_in_range(adapter_fixture):
    """NIFTY quote price must be within realistic bounds (not paise)."""
    adapter = adapter_fixture
    result = await adapter.get_quote([NIFTY_SYMBOL])
    assert result, f"[{adapter.broker_type}] get_quote() returned empty for NIFTY"

    quote = next(iter(result.values()))
    price = float(quote.last_price)
    assert NIFTY_MIN_PRICE <= price <= NIFTY_MAX_PRICE, (
        f"[{adapter.broker_type}] NIFTY price={price} outside expected range "
        f"[{NIFTY_MIN_PRICE}, {NIFTY_MAX_PRICE}]. May still be in paise."
    )


@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_quote_ohlc_present(adapter_fixture):
    """Quote must include open, high, low, close fields (not all zero)."""
    adapter = adapter_fixture
    result = await adapter.get_quote([NIFTY_SYMBOL])
    assert result, f"[{adapter.broker_type}] get_quote() returned empty"

    quote = next(iter(result.values()))
    ohlc_sum = quote.open + quote.high + quote.low + quote.close
    assert ohlc_sum > 0, (
        f"[{adapter.broker_type}] NIFTY OHLC is all zeros: "
        f"open={quote.open} high={quote.high} low={quote.low} close={quote.close}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: get_ltp() — lightweight last-traded price
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_ltp_returns_data(adapter_fixture):
    """get_ltp() returns a non-empty dict."""
    adapter = adapter_fixture
    result = await adapter.get_ltp(TEST_SYMBOLS)

    assert result, (
        f"[{adapter.broker_type}] get_ltp() returned empty. "
        f"Check broker API connectivity."
    )


@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_ltp_prices_are_positive_decimal(adapter_fixture):
    """LTP values must be Decimal > 0."""
    adapter = adapter_fixture
    result = await adapter.get_ltp(TEST_SYMBOLS)
    assert result, f"[{adapter.broker_type}] get_ltp() returned empty"

    for symbol, ltp in result.items():
        assert isinstance(ltp, Decimal), (
            f"[{adapter.broker_type}] {symbol} LTP is {type(ltp).__name__}, expected Decimal"
        )
        assert ltp > 0, (
            f"[{adapter.broker_type}] {symbol} LTP={ltp} is not > 0"
        )


@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_ltp_consistent_with_quote(adapter_fixture):
    """LTP from get_ltp() must be within 5% of last_price from get_quote()."""
    adapter = adapter_fixture
    ltp_result = await adapter.get_ltp([NIFTY_SYMBOL])
    quote_result = await adapter.get_quote([NIFTY_SYMBOL])

    assert ltp_result and quote_result, (
        f"[{adapter.broker_type}] get_ltp or get_quote returned empty"
    )

    ltp = float(next(iter(ltp_result.values())))
    quote_price = float(next(iter(quote_result.values())).last_price)

    diff_pct = abs(ltp - quote_price) / quote_price * 100
    assert diff_pct < 5, (
        f"[{adapter.broker_type}] LTP={ltp} and quote.last_price={quote_price} "
        f"differ by {diff_pct:.1f}% — they should be within 5% of each other"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: get_historical() — OHLCV candles
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_historical_returns_candles(adapter_fixture):
    """get_historical() returns at least 1 candle for NIFTY over 5 days."""
    adapter = adapter_fixture
    candles = await _get_historical_or_skip(
        adapter, NIFTY_SYMBOL,
        from_date=HIST_FROM_DATE, to_date=HIST_TO_DATE, interval=HIST_INTERVAL,
    )
    assert candles, (
        f"[{adapter.broker_type}] get_historical() returned 0 candles for NIFTY "
        f"({HIST_FROM_DATE} → {HIST_TO_DATE}, interval={HIST_INTERVAL}). "
        f"Check broker API and symbol format."
    )


@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_historical_candle_prices_positive(adapter_fixture):
    """All candle OHLC values must be > 0."""
    adapter = adapter_fixture
    candles = await _get_historical_or_skip(
        adapter, NIFTY_SYMBOL,
        from_date=HIST_FROM_DATE, to_date=HIST_TO_DATE, interval=HIST_INTERVAL,
    )
    assert candles, f"[{adapter.broker_type}] No historical candles returned"

    for candle in candles:
        assert candle.open > 0,  f"[{adapter.broker_type}] Candle open={candle.open} not > 0"
        assert candle.high > 0,  f"[{adapter.broker_type}] Candle high={candle.high} not > 0"
        assert candle.low > 0,   f"[{adapter.broker_type}] Candle low={candle.low} not > 0"
        assert candle.close > 0, f"[{adapter.broker_type}] Candle close={candle.close} not > 0"


@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_historical_candle_ohlc_logical(adapter_fixture):
    """high >= open, close, low. low <= open, close, high."""
    adapter = adapter_fixture
    candles = await _get_historical_or_skip(
        adapter, NIFTY_SYMBOL,
        from_date=HIST_FROM_DATE, to_date=HIST_TO_DATE, interval=HIST_INTERVAL,
    )
    assert candles, f"[{adapter.broker_type}] No historical candles returned"

    for candle in candles:
        assert candle.high >= candle.open, (
            f"[{adapter.broker_type}] high={candle.high} < open={candle.open}"
        )
        assert candle.high >= candle.close, (
            f"[{adapter.broker_type}] high={candle.high} < close={candle.close}"
        )
        assert candle.low <= candle.open, (
            f"[{adapter.broker_type}] low={candle.low} > open={candle.open}"
        )
        assert candle.low <= candle.close, (
            f"[{adapter.broker_type}] low={candle.low} > close={candle.close}"
        )


@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_historical_candle_prices_are_decimal(adapter_fixture):
    """Candle OHLC prices must be Decimal."""
    adapter = adapter_fixture
    candles = await _get_historical_or_skip(
        adapter, NIFTY_SYMBOL,
        from_date=HIST_FROM_DATE, to_date=HIST_TO_DATE, interval=HIST_INTERVAL,
    )
    assert candles, f"[{adapter.broker_type}] No historical candles returned"

    candle = candles[0]
    for field_name, value in [("open", candle.open), ("high", candle.high),
                               ("low", candle.low), ("close", candle.close)]:
        assert isinstance(value, Decimal), (
            f"[{adapter.broker_type}] candle.{field_name} is {type(value).__name__}, "
            f"expected Decimal"
        )


@pytest.mark.parametrize("adapter_fixture", ALL_BROKER_ADAPTERS, indirect=True)
@pytest.mark.live
async def test_get_historical_candle_timestamps_ordered(adapter_fixture):
    """Candles must be returned in ascending timestamp order."""
    adapter = adapter_fixture
    candles = await _get_historical_or_skip(
        adapter, NIFTY_SYMBOL,
        from_date=HIST_FROM_DATE, to_date=HIST_TO_DATE, interval=HIST_INTERVAL,
    )
    if len(candles) < 2:
        pytest.skip("Only 1 candle returned — cannot check ordering")

    for i in range(1, len(candles)):
        assert candles[i].timestamp >= candles[i - 1].timestamp, (
            f"[{adapter.broker_type}] Candles not in ascending order at index {i}: "
            f"{candles[i - 1].timestamp} > {candles[i].timestamp}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Indirect fixture resolver
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def adapter_fixture(request):
    """Resolve the named adapter fixture dynamically."""
    return request.getfixturevalue(request.param)
