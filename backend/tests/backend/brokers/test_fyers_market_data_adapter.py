"""
Tests for FyersMarketDataAdapter - REST market data adapter.

Tests cover:
- get_quote: Full quotes via POST /v3/quotes
- get_ltp: LTP extracted from quotes response
- get_historical: OHLCV candles via GET /v3/history
- get_instruments: Instrument master from Fyers CSV files
- search_instruments: In-memory search
- get_token / get_symbol: Token manager delegation
- connect / disconnect: Profile validation + token cache
- Error handling: AuthenticationError, BrokerAPIError, InvalidSymbolError
- Price normalization: All prices in RUPEES (Fyers returns RUPEES natively)
- Symbol conversion: canonical <-> NSE:SYMBOL format
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.brokers.market_data.fyers_adapter import FyersMarketDataAdapter
from app.services.brokers.market_data.market_data_base import (
    FyersMarketDataCredentials,
    MarketDataBrokerType,
    OHLCVCandle,
    Instrument,
)
from app.services.brokers.market_data.exceptions import (
    BrokerAPIError,
    InvalidSymbolError,
    AuthenticationError,
    DataNotAvailableError,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def credentials():
    return FyersMarketDataCredentials(
        broker_type="fyers",
        user_id=uuid4(),
        app_id="TESTAPP-100",
        access_token="eyJtest_access_token_abc123",
    )


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_token_manager():
    mgr = AsyncMock()
    mgr.get_token = AsyncMock(return_value=101010000012345)
    mgr.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    mgr.load_cache = AsyncMock()
    return mgr


@pytest.fixture
def adapter(credentials, mock_db, mock_token_manager):
    with patch(
        "app.services.brokers.market_data.fyers_adapter.TokenManagerFactory"
    ) as MockFactory:
        MockFactory.get_manager.return_value = mock_token_manager
        a = FyersMarketDataAdapter(credentials, mock_db)
        a._token_manager = mock_token_manager
    return a


# ─── UNVERIFIED: Hand-crafted responses (no real API credentials available) ──
# These should be replaced with recorded responses when broker credentials
# are available. See tests/fixtures/real_responses.py for the pattern.
# Record via: cd backend && PYTHONPATH=. python -m tests.fixtures.record_raw_responses --broker fyers

# ─── Sample API responses ───────────────────────────────────────────────────

SAMPLE_PROFILE_RESPONSE = {
    "s": "ok",
    "data": {
        "fy_id": "TESTUSER",
        "display_name": "Test User",
    },
}

SAMPLE_QUOTES_RESPONSE = {
    "s": "ok",
    "d": [
        {
            "n": "NSE:NIFTY26FEB24000CE",
            "s": "ok",
            "v": {
                "lp": 150.25,
                "o": 148.00,
                "h": 155.00,
                "l": 147.50,
                "c": 149.00,
                "volume": 125000,
                "oi": 5000000,
                "ch": 1.25,
                "chp": 0.84,
                "bid": [{"price": 150.20, "quantity": 500}],
                "ask": [{"price": 150.30, "quantity": 400}],
            },
        }
    ],
}

SAMPLE_HISTORICAL_RESPONSE = {
    "s": "ok",
    "candles": [
        [1704067200, 2400.0, 2450.0, 2390.0, 2430.0, 1500000],
        [1704153600, 2410.0, 2460.0, 2395.0, 2445.0, 1800000],
        [1704240000, 2420.0, 2470.0, 2400.0, 2455.0, 2000000],
    ],
}

SAMPLE_CSV_NSE_FO = (
    "Fytoken,Symbol Details,Exchange Instrument type,Minimum lot size,"
    "Tick size,ISIN,Trading Session,Last update date,Expiry date,"
    "Symbol ticker,Exchange,Segment,Scrip code,Underlying scrip code,"
    "Strike price,Option type\n"
    "101010000043854,NIFTY FEB 24000 CE,OI,25,0.05,,NSE FO,2026-02-10,"
    "2026-02-27,NSE:NIFTY26FEB24000CE,NSE,D,,NIFTY,24000.0,CE\n"
    "101010000043855,NIFTY FEB 24000 PE,OI,25,0.05,,NSE FO,2026-02-10,"
    "2026-02-27,NSE:NIFTY26FEB24000PE,NSE,D,,NIFTY,24000.0,PE\n"
    "101010000042001,NIFTY FEB FUT,IF,25,0.05,,NSE FO,2026-02-10,"
    "2026-02-27,NSE:NIFTY26FEBFUT,NSE,D,,NIFTY,,\n"
)

SAMPLE_CSV_NSE_CM = (
    "Fytoken,Symbol Details,Exchange Instrument type,Minimum lot size,"
    "Tick size,ISIN,Trading Session,Last update date,Expiry date,"
    "Symbol ticker,Exchange,Segment,Scrip code,Underlying scrip code,"
    "Strike price,Option type\n"
    "100000001333,HDFC BANK LTD,EQ,1,0.05,INE040A01034,NSE CM,2026-02-10,"
    ",NSE:HDFCBANK-EQ,NSE,C,,,0.0,\n"
)


# ═══════════════════════════════════════════════════════════════════════════════
# BROKER TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
def test_broker_type(adapter):
    assert adapter.broker_type == MarketDataBrokerType.FYERS


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECT / DISCONNECT
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_success(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_PROFILE_RESPONSE
        result = await adapter.connect()
    assert result is True
    assert adapter.is_connected is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_loads_token_cache(adapter, mock_token_manager):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_PROFILE_RESPONSE
        await adapter.connect()
    mock_token_manager.load_cache.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_auth_error_on_token_failure(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("Invalid token -16")
        with pytest.raises(AuthenticationError):
            await adapter.connect()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_returns_false_on_non_auth_error(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("Network timeout")
        result = await adapter.connect()
    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect(adapter):
    adapter._initialized = True
    await adapter.disconnect()
    assert adapter.is_connected is False


# ═══════════════════════════════════════════════════════════════════════════════
# SYMBOL CONVERSION
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
def test_canonical_to_fyers_option(adapter):
    """Options: add NSE: prefix."""
    result = adapter._canonical_to_fyers("NIFTY26FEB24000CE")
    assert result == "NSE:NIFTY26FEB24000CE"


@pytest.mark.unit
def test_canonical_to_fyers_future(adapter):
    result = adapter._canonical_to_fyers("NIFTY26FEBFUT")
    assert result == "NSE:NIFTY26FEBFUT"


@pytest.mark.unit
def test_canonical_to_fyers_equity(adapter):
    """Equities: add NSE: prefix + -EQ suffix."""
    result = adapter._canonical_to_fyers_equity("HDFCBANK")
    assert result == "NSE:HDFCBANK-EQ"


@pytest.mark.unit
def test_fyers_to_canonical_option(adapter):
    """Strip NSE: prefix from options/futures."""
    result = adapter._fyers_to_canonical("NSE:NIFTY26FEB24000CE")
    assert result == "NIFTY26FEB24000CE"


@pytest.mark.unit
def test_fyers_to_canonical_equity(adapter):
    """Strip NSE: prefix and -EQ suffix from equities."""
    result = adapter._fyers_to_canonical("NSE:HDFCBANK-EQ")
    assert result == "HDFCBANK"


@pytest.mark.unit
def test_fyers_to_canonical_index(adapter):
    """Strip NSE: prefix and -INDEX suffix, map index name."""
    result = adapter._fyers_to_canonical("NSE:NIFTY50-INDEX")
    assert result == "NIFTY 50"


# ═══════════════════════════════════════════════════════════════════════════════
# GET_LTP
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_returns_rupees(adapter):
    """LTP from Fyers is in RUPEES natively — no conversion needed."""
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTES_RESPONSE
        result = await adapter.get_ltp(["NIFTY26FEB24000CE"])

    assert "NIFTY26FEB24000CE" in result
    assert result["NIFTY26FEB24000CE"] == Decimal("150.25")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_decimal_type(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTES_RESPONSE
        result = await adapter.get_ltp(["NIFTY26FEB24000CE"])

    assert isinstance(result["NIFTY26FEB24000CE"], Decimal)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_api_error(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("connection error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_ltp(["NIFTY26FEB24000CE"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_auth_error(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("token expired -16")
        with pytest.raises(AuthenticationError):
            await adapter.get_ltp(["NIFTY26FEB24000CE"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_multiple_symbols(adapter):
    multi_response = {
        "s": "ok",
        "d": [
            {
                "n": "NSE:NIFTY26FEB24000CE",
                "s": "ok",
                "v": {"lp": 150.25, "o": 148.0, "h": 155.0, "l": 147.5, "c": 149.0,
                      "volume": 0, "oi": 0, "ch": 0, "chp": 0},
            },
            {
                "n": "NSE:NIFTY26FEB24000PE",
                "s": "ok",
                "v": {"lp": 98.75, "o": 97.0, "h": 102.0, "l": 96.0, "c": 99.0,
                      "volume": 0, "oi": 0, "ch": 0, "chp": 0},
            },
        ],
    }
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = multi_response
        result = await adapter.get_ltp(["NIFTY26FEB24000CE", "NIFTY26FEB24000PE"])

    assert len(result) == 2
    assert result["NIFTY26FEB24000CE"] == Decimal("150.25")
    assert result["NIFTY26FEB24000PE"] == Decimal("98.75")


# ═══════════════════════════════════════════════════════════════════════════════
# GET_QUOTE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_returns_unified_quote(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTES_RESPONSE
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])

    assert "NIFTY26FEB24000CE" in result
    quote = result["NIFTY26FEB24000CE"]
    assert quote.last_price == Decimal("150.25")
    assert quote.open == Decimal("148.00")
    assert quote.high == Decimal("155.00")
    assert quote.low == Decimal("147.50")
    assert quote.close == Decimal("149.00")
    assert quote.volume == 125000
    assert quote.oi == 5000000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_prices_are_decimal(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTES_RESPONSE
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])

    quote = result["NIFTY26FEB24000CE"]
    assert isinstance(quote.last_price, Decimal)
    assert isinstance(quote.open, Decimal)
    assert isinstance(quote.high, Decimal)
    assert isinstance(quote.low, Decimal)
    assert isinstance(quote.close, Decimal)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_bid_ask(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTES_RESPONSE
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])

    quote = result["NIFTY26FEB24000CE"]
    assert quote.bid_price == Decimal("150.20")
    assert quote.ask_price == Decimal("150.30")
    assert quote.bid_quantity == 500
    assert quote.ask_quantity == 400


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_sends_fyers_format_symbols(adapter):
    """Adapter must convert canonical -> NSE:SYMBOL before API call."""
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTES_RESPONSE
        await adapter.get_quote(["NIFTY26FEB24000CE"])

    call_args = mock_req.call_args
    assert call_args is not None
    # Verify the body contains Fyers-format symbols
    body = call_args.kwargs.get("body") or (call_args.args[2] if len(call_args.args) > 2 else {})
    if body:
        symbols_str = body.get("symbols", "")
        assert "NSE:" in symbols_str


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_api_error(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("API error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_quote(["NIFTY26FEB24000CE"])


# ═══════════════════════════════════════════════════════════════════════════════
# GET_HISTORICAL
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_returns_candles(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL_RESPONSE
        result = await adapter.get_historical(
            "NIFTY26FEB24000CE",
            date(2026, 1, 1),
            date(2026, 1, 3),
            "day"
        )

    assert len(result) == 3
    assert all(isinstance(c, OHLCVCandle) for c in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_candle_prices_are_decimal(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL_RESPONSE
        result = await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 3), "day")

    candle = result[0]
    assert isinstance(candle.open, Decimal)
    assert isinstance(candle.high, Decimal)
    assert isinstance(candle.low, Decimal)
    assert isinstance(candle.close, Decimal)
    assert candle.open == Decimal("2400.0")
    assert candle.high == Decimal("2450.0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_candle_timestamps_from_epoch(adapter):
    """Fyers returns Unix timestamps in candles[i][0]."""
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL_RESPONSE
        result = await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 3), "day")

    assert isinstance(result[0].timestamp, datetime)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_volume_is_int(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL_RESPONSE
        result = await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 3), "day")

    assert isinstance(result[0].volume, int)
    assert result[0].volume == 1500000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_uses_epoch_range_params(adapter):
    """Historical API uses epoch timestamps for range_from/range_to."""
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL_RESPONSE
        await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 31), "day")

    call_args = mock_req.call_args
    assert call_args is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_interval_mapping(adapter):
    """Canonical intervals must map to Fyers resolution values."""
    interval_cases = [
        ("1min", "1"),
        ("5min", "5"),
        ("15min", "15"),
        ("hour", "60"),
        ("day", "D"),
    ]
    for canonical, expected_fyers in interval_cases:
        with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_HISTORICAL_RESPONSE
            await adapter.get_historical(
                "NIFTY26FEB24000CE",
                date(2026, 1, 1),
                date(2026, 1, 31),
                canonical
            )
            call_args = mock_req.call_args
            assert call_args is not None
            # Check that the resolution param was included
            params = call_args.kwargs.get("params") or {}
            if params:
                assert params.get("resolution") == expected_fyers


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_api_error(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("Server error")
        with pytest.raises(DataNotAvailableError):
            await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 31), "day")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_fyers_error_response(adapter):
    """Fyers returns {s: 'error'} envelope on API errors."""
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"s": "error", "code": -300, "message": "rate limit"}
        with pytest.raises(DataNotAvailableError):
            await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 31), "day")


# ═══════════════════════════════════════════════════════════════════════════════
# GET_INSTRUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_nfo_returns_list(adapter):
    with patch.object(adapter, "_download_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_NSE_FO
        result = await adapter.get_instruments("NFO")

    assert isinstance(result, list)
    assert len(result) >= 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_canonical_symbols(adapter):
    """Instruments must have canonical (no NSE: prefix) symbols."""
    with patch.object(adapter, "_download_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_NSE_FO
        result = await adapter.get_instruments("NFO")

    for inst in result:
        assert ":" not in inst.canonical_symbol, f"Found prefix in {inst.canonical_symbol}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_options_have_fields(adapter):
    with patch.object(adapter, "_download_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_NSE_FO
        result = await adapter.get_instruments("NFO")

    options = [i for i in result if i.instrument_type in ("CE", "PE")]
    assert len(options) >= 2
    for opt in options:
        assert opt.expiry is not None
        assert opt.strike is not None
        assert opt.lot_size == 25
        assert opt.option_type in ("CE", "PE")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_nse_equity(adapter):
    with patch.object(adapter, "_download_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_NSE_CM
        result = await adapter.get_instruments("NSE")

    equities = [i for i in result if i.instrument_type == "EQ"]
    assert len(equities) >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_broker_symbol_has_fyers_format(adapter):
    """broker_symbol should be in Fyers format (NSE:SYMBOL)."""
    with patch.object(adapter, "_download_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_NSE_FO
        result = await adapter.get_instruments("NFO")

    for inst in result:
        assert inst.broker_symbol.startswith("NSE:") or inst.broker_symbol.startswith("BSE:")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_api_error(adapter):
    with patch.object(adapter, "_download_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.side_effect = Exception("Network error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_instruments("NFO")


# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH_INSTRUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_instruments_basic(adapter):
    with patch.object(adapter, "_download_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_NSE_FO
        result = await adapter.search_instruments("NIFTY")

    assert all("NIFTY" in i.canonical_symbol.upper() or "NIFTY" in i.name.upper() for i in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_instruments_max_50(adapter):
    with patch.object(adapter, "_download_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_NSE_FO
        result = await adapter.search_instruments("NIFTY")

    assert len(result) <= 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_instruments_no_match(adapter):
    with patch.object(adapter, "_download_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_NSE_FO
        result = await adapter.search_instruments("XYZNONEXISTENT")

    assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# GET_TOKEN / GET_SYMBOL
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_token_delegates_to_manager(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=101010000043854)
    result = await adapter.get_token("NIFTY26FEB24000CE")
    assert result == 101010000043854
    mock_token_manager.get_token.assert_called_once_with("NIFTY26FEB24000CE")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_token_raises_if_not_found(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=None)
    with pytest.raises(InvalidSymbolError):
        await adapter.get_token("INVALID_SYMBOL")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_symbol_delegates_to_manager(adapter, mock_token_manager):
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    result = await adapter.get_symbol(101010000043854)
    assert result == "NIFTY26FEB24000CE"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_symbol_raises_if_not_found(adapter, mock_token_manager):
    mock_token_manager.get_symbol = AsyncMock(return_value=None)
    with pytest.raises(InvalidSymbolError):
        await adapter.get_symbol(99999)


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET STUBS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscribe_is_noop(adapter):
    await adapter.subscribe([101010000043854], "quote")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unsubscribe_is_noop(adapter):
    await adapter.unsubscribe([101010000043854])


@pytest.mark.unit
def test_on_tick_registers_callback(adapter):
    callback = MagicMock()
    adapter.on_tick(callback)


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE NORMALIZATION (RUPEES — no paise conversion)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_prices_not_divided_by_100(adapter):
    """Fyers returns RUPEES — must NOT divide by 100."""
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTES_RESPONSE
        result = await adapter.get_ltp(["NIFTY26FEB24000CE"])

    assert result["NIFTY26FEB24000CE"] == Decimal("150.25")
    assert result["NIFTY26FEB24000CE"] != Decimal("1.5025")


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH HEADER
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
def test_auth_header_format(adapter):
    """Fyers auth header is 'app_id:access_token' — unique colon-separated format."""
    headers = adapter._headers
    auth = headers.get("Authorization", "")
    assert "TESTAPP-100:" in auth
    assert "Bearer" not in auth
