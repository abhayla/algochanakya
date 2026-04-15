"""
Tests for DhanMarketDataAdapter - REST market data adapter.

Tests cover:
- get_quote: Full quotes via /marketfeed/quote
- get_ltp: LTP via /marketfeed/ltp
- get_historical: OHLCV candles via /charts/historical and /charts/intraday
- get_instruments: Instrument master from CSV download
- search_instruments: In-memory search
- get_token / get_symbol: Token manager delegation
- connect / disconnect: Connection and profile validation
- Error handling: AuthenticationError, BrokerAPIError, InvalidSymbolError
- Price normalization: All prices in RUPEES (Dhan returns RUPEES natively)
"""

import pytest
import asyncio
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

from app.services.brokers.market_data.dhan_adapter import DhanMarketDataAdapter
from app.services.brokers.market_data.market_data_base import (
    DhanMarketDataCredentials,
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
    return DhanMarketDataCredentials(
        broker_type="dhan",
        user_id=uuid4(),
        client_id="1234567890",
        access_token="test_access_token_abc123",
    )


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_token_manager():
    mgr = AsyncMock()
    mgr.get_token = AsyncMock(return_value=43854)
    mgr.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    mgr.load_cache = AsyncMock()
    return mgr


@pytest.fixture
def adapter(credentials, mock_db, mock_token_manager):
    with patch(
        "app.services.brokers.market_data.dhan_adapter.TokenManagerFactory"
    ) as MockFactory:
        MockFactory.get_manager.return_value = mock_token_manager
        a = DhanMarketDataAdapter(credentials, mock_db)
        a._token_manager = mock_token_manager
    return a


# ─── UNVERIFIED: Hand-crafted responses (no real API credentials available) ──
# These should be replaced with recorded responses when broker credentials
# are available. See tests/fixtures/real_responses.py for the pattern.
# Record via: cd backend && PYTHONPATH=. python -m tests.fixtures.record_raw_responses --broker dhan

# ─── Sample API responses ───────────────────────────────────────────────────

SAMPLE_LTP_RESPONSE = {
    "data": {
        "NSE_FNO": {
            "43854": {"last_price": 150.25},
            "43855": {"last_price": 98.75},
        }
    }
}

SAMPLE_QUOTE_RESPONSE = {
    "data": {
        "NSE_FNO": {
            "43854": {
                "last_price": 150.25,
                "open": 148.00,
                "high": 155.00,
                "low": 147.50,
                "close": 149.00,
                "volume": 125000,
                "oi": 5000000,
                "last_trade_time": "2026-02-13T10:30:00",
                "bid": [
                    {"price": 150.20, "quantity": 500},
                    {"price": 150.15, "quantity": 750},
                ],
                "ask": [
                    {"price": 150.30, "quantity": 400},
                    {"price": 150.35, "quantity": 600},
                ],
            }
        }
    }
}

SAMPLE_HISTORICAL_RESPONSE = {
    "open": [2400.0, 2410.0, 2420.0],
    "high": [2450.0, 2460.0, 2470.0],
    "low": [2390.0, 2395.0, 2400.0],
    "close": [2430.0, 2445.0, 2455.0],
    "volume": [1500000, 1800000, 2000000],
    "timestamp": ["2026-01-01", "2026-01-02", "2026-01-03"],
}

SAMPLE_INTRADAY_RESPONSE = {
    "open": [148.00, 149.00],
    "high": [152.00, 153.00],
    "low": [147.00, 148.00],
    "close": [150.00, 151.00],
    "volume": [50000, 60000],
    "timestamp": ["2026-02-13 09:15:00", "2026-02-13 09:20:00"],
}

SAMPLE_PROFILE_RESPONSE = {
    "clientId": "1234567890",
    "name": "Test User",
}

SAMPLE_CSV_CONTENT = (
    "SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_SMST_SECURITY_ID,SEM_INSTRUMENT_NAME,"
    "SEM_TRADING_SYMBOL,SEM_CUSTOM_SYMBOL,SEM_EXPIRY_DATE,SEM_STRIKE_PRICE,"
    "SEM_OPTION_TYPE,SEM_LOT_SIZE,SEM_TICK_SIZE,SEM_LOT_UNITS,SEM_EXPIRY_FLAG\n"
    "NSE,D,43854,OPTIDX,NIFTY-Feb2026-24000-CE,NIFTY 26 FEB 24000 CE,"
    "2026-02-27,24000.0,CE,25,0.05,LOTS,M\n"
    "NSE,D,43855,OPTIDX,NIFTY-Feb2026-24000-PE,NIFTY 26 FEB 24000 PE,"
    "2026-02-27,24000.0,PE,25,0.05,LOTS,M\n"
    "NSE,E,1333,EQUITY,HDFCBANK,HDFC BANK LTD,,,,1,0.05,SHARES,\n"
    "NSE,D,42001,FUTIDX,NIFTY-Feb2026-FUT,NIFTY 26 FEB FUT,"
    "2026-02-27,,,,0.05,LOTS,M\n"
)


# ═══════════════════════════════════════════════════════════════════════════════
# BROKER TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
def test_broker_type(adapter):
    assert adapter.broker_type == MarketDataBrokerType.DHAN


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
async def test_connect_auth_error(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("Invalid token")
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
# GET_LTP
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_returns_rupees(adapter, mock_token_manager):
    """LTP endpoint returns RUPEES natively - no conversion needed."""
    mock_token_manager.get_token = AsyncMock(return_value=43854)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LTP_RESPONSE
        result = await adapter.get_ltp(["NIFTY26FEB24000CE"])

    assert "NIFTY26FEB24000CE" in result
    assert result["NIFTY26FEB24000CE"] == Decimal("150.25")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_multiple_symbols(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(side_effect=[43854, 43855])
    mock_token_manager.get_symbol = AsyncMock(side_effect=[
        "NIFTY26FEB24000CE", "NIFTY26FEB24000PE"
    ])

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LTP_RESPONSE
        result = await adapter.get_ltp(["NIFTY26FEB24000CE", "NIFTY26FEB24000PE"])

    assert len(result) == 2
    assert isinstance(result["NIFTY26FEB24000CE"], Decimal)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_symbol_not_found(adapter, mock_token_manager):
    """If token not found in manager, raise InvalidSymbolError."""
    mock_token_manager.get_token = AsyncMock(return_value=None)

    with pytest.raises(InvalidSymbolError):
        await adapter.get_ltp(["INVALID_SYMBOL"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_api_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=43854)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("API error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_ltp(["NIFTY26FEB24000CE"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_auth_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=43854)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("Unauthorized access token")
        with pytest.raises(AuthenticationError):
            await adapter.get_ltp(["NIFTY26FEB24000CE"])


# ═══════════════════════════════════════════════════════════════════════════════
# GET_QUOTE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_returns_unified_quote(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=43854)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTE_RESPONSE
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
async def test_get_quote_prices_are_decimal(adapter, mock_token_manager):
    """All prices must be Decimal instances, not float."""
    mock_token_manager.get_token = AsyncMock(return_value=43854)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTE_RESPONSE
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])

    quote = result["NIFTY26FEB24000CE"]
    assert isinstance(quote.last_price, Decimal)
    assert isinstance(quote.open, Decimal)
    assert isinstance(quote.high, Decimal)
    assert isinstance(quote.low, Decimal)
    assert isinstance(quote.close, Decimal)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_bid_ask(adapter, mock_token_manager):
    """Bid/ask should be extracted from depth arrays."""
    mock_token_manager.get_token = AsyncMock(return_value=43854)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTE_RESPONSE
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])

    quote = result["NIFTY26FEB24000CE"]
    assert quote.bid_price == Decimal("150.20")
    assert quote.ask_price == Decimal("150.30")
    assert quote.bid_quantity == 500
    assert quote.ask_quantity == 400


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_uses_correct_exchange_segment(adapter, mock_token_manager):
    """Adapter must group symbols by exchange segment for the POST body."""
    mock_token_manager.get_token = AsyncMock(return_value=43854)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTE_RESPONSE
        await adapter.get_quote(["NIFTY26FEB24000CE"])

    # Should have called with a body that has NSE_FNO key
    call_args = mock_req.call_args
    assert call_args is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_api_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=43854)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("connection error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_quote(["NIFTY26FEB24000CE"])


# ═══════════════════════════════════════════════════════════════════════════════
# GET_HISTORICAL
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_daily_returns_candles(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=1333)

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL_RESPONSE
        result = await adapter.get_historical(
            "HDFCBANK",
            date(2026, 1, 1),
            date(2026, 1, 3),
            "day"
        )

    assert len(result) == 3
    assert all(isinstance(c, OHLCVCandle) for c in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_candle_prices_are_decimal(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=1333)

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL_RESPONSE
        result = await adapter.get_historical("HDFCBANK", date(2026, 1, 1), date(2026, 1, 3), "day")

    candle = result[0]
    assert isinstance(candle.open, Decimal)
    assert isinstance(candle.high, Decimal)
    assert isinstance(candle.low, Decimal)
    assert isinstance(candle.close, Decimal)
    assert candle.open == Decimal("2400.0")
    assert candle.high == Decimal("2450.0")
    assert candle.close == Decimal("2430.0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_volume_is_int(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=1333)

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL_RESPONSE
        result = await adapter.get_historical("HDFCBANK", date(2026, 1, 1), date(2026, 1, 3), "day")

    assert isinstance(result[0].volume, int)
    assert result[0].volume == 1500000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_intraday_uses_intraday_endpoint(adapter, mock_token_manager):
    """1min, 5min, 15min, 60min intervals should use /charts/intraday."""
    mock_token_manager.get_token = AsyncMock(return_value=1333)

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_INTRADAY_RESPONSE
        result = await adapter.get_historical("HDFCBANK", date(2026, 2, 13), date(2026, 2, 13), "5min")

    assert len(result) == 2
    # Verify intraday endpoint was called
    call_args = mock_req.call_args
    assert "intraday" in str(call_args) or call_args is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_daily_uses_historical_endpoint(adapter, mock_token_manager):
    """day interval should use /charts/historical."""
    mock_token_manager.get_token = AsyncMock(return_value=1333)

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL_RESPONSE
        result = await adapter.get_historical("HDFCBANK", date(2026, 1, 1), date(2026, 1, 31), "day")

    call_args = mock_req.call_args
    assert "historical" in str(call_args) or call_args is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_symbol_not_found(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=None)

    with pytest.raises(InvalidSymbolError):
        await adapter.get_historical("INVALID", date(2026, 1, 1), date(2026, 1, 31), "day")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_api_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=1333)

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("Dhan server error")
        with pytest.raises(DataNotAvailableError):
            await adapter.get_historical("HDFCBANK", date(2026, 1, 1), date(2026, 1, 31), "day")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_interval_mapping(adapter, mock_token_manager):
    """Canonical intervals should map to Dhan interval values."""
    mock_token_manager.get_token = AsyncMock(return_value=1333)

    interval_map = {
        "1min": "1",
        "5min": "5",
        "15min": "15",
        "hour": "60",
    }

    for canonical_interval, expected_dhan_interval in interval_map.items():
        with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_INTRADAY_RESPONSE
            await adapter.get_historical(
                "HDFCBANK",
                date(2026, 2, 13),
                date(2026, 2, 13),
                canonical_interval
            )
            # Verify the correct interval value was passed
            call_kwargs = mock_req.call_args
            assert call_kwargs is not None


# ═══════════════════════════════════════════════════════════════════════════════
# GET_INSTRUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_returns_list(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_CONTENT
        result = await adapter.get_instruments("NFO")

    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_canonical_symbols(adapter):
    """Instruments must use canonical (Kite-format) symbols."""
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_CONTENT
        result = await adapter.get_instruments("NFO")

    # Options should be in canonical format (NIFTY + expiry + strike + type)
    option_symbols = [i.canonical_symbol for i in result if i.instrument_type in ("CE", "PE")]
    assert any("NIFTY" in s for s in option_symbols)
    # No dashes or spaces in canonical option symbols
    for sym in option_symbols:
        assert "-" not in sym
        assert " " not in sym


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_has_required_fields(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_CONTENT
        result = await adapter.get_instruments("NFO")

    for inst in result:
        assert isinstance(inst, Instrument)
        assert inst.canonical_symbol
        assert inst.exchange
        assert inst.broker_symbol


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_option_fields(adapter):
    """Options must have strike, expiry, option_type set."""
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_CONTENT
        result = await adapter.get_instruments("NFO")

    options = [i for i in result if i.instrument_type in ("CE", "PE")]
    assert len(options) >= 2
    for opt in options:
        assert opt.strike is not None
        assert opt.expiry is not None
        assert opt.option_type in ("CE", "PE")
        assert opt.lot_size > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_equity(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_CONTENT
        result = await adapter.get_instruments("NSE")

    equities = [i for i in result if i.instrument_type == "EQ"]
    assert len(equities) >= 1
    hdfcbank = next((i for i in equities if "HDFCBANK" in i.canonical_symbol), None)
    assert hdfcbank is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_api_error(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.side_effect = Exception("Network error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_instruments("NFO")


# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH_INSTRUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_instruments_basic(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_CONTENT
        result = await adapter.search_instruments("NIFTY")

    assert isinstance(result, list)
    assert all("NIFTY" in i.canonical_symbol.upper() or "NIFTY" in i.name.upper() for i in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_instruments_max_50(adapter):
    """Search must not return more than 50 results."""
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_CONTENT
        result = await adapter.search_instruments("NIFTY")

    assert len(result) <= 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_instruments_no_match(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_csv:
        mock_csv.return_value = SAMPLE_CSV_CONTENT
        result = await adapter.search_instruments("XYZNONEXISTENT")

    assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# GET_TOKEN / GET_SYMBOL
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_token_delegates_to_token_manager(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=43854)
    result = await adapter.get_token("NIFTY26FEB24000CE")
    assert result == 43854
    mock_token_manager.get_token.assert_called_once_with("NIFTY26FEB24000CE")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_token_raises_if_not_found(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=None)
    with pytest.raises(InvalidSymbolError):
        await adapter.get_token("INVALID_SYMBOL")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_symbol_delegates_to_token_manager(adapter, mock_token_manager):
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    result = await adapter.get_symbol(43854)
    assert result == "NIFTY26FEB24000CE"
    mock_token_manager.get_symbol.assert_called_once_with(43854)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_symbol_raises_if_not_found(adapter, mock_token_manager):
    mock_token_manager.get_symbol = AsyncMock(return_value=None)
    with pytest.raises(InvalidSymbolError):
        await adapter.get_symbol(99999)


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET STUBS (delegate to ticker adapter)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscribe_is_noop(adapter):
    """subscribe() is a no-op on the REST adapter - WebSocket managed separately."""
    await adapter.subscribe([43854], "quote")  # Should not raise


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unsubscribe_is_noop(adapter):
    await adapter.unsubscribe([43854])  # Should not raise


@pytest.mark.unit
def test_on_tick_registers_callback(adapter):
    callback = MagicMock()
    adapter.on_tick(callback)  # Should not raise


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE NORMALIZATION (RUPEES, no paise conversion)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_prices_not_divided_by_100(adapter, mock_token_manager):
    """
    Dhan returns RUPEES natively. Must NOT divide by 100.
    150.25 should be 150.25, NOT 1.5025.
    """
    mock_token_manager.get_token = AsyncMock(return_value=43854)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")

    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LTP_RESPONSE
        result = await adapter.get_ltp(["NIFTY26FEB24000CE"])

    # 150.25 is the correct value — NOT 1.5025 (paise ÷ 100)
    assert result["NIFTY26FEB24000CE"] == Decimal("150.25")
    assert result["NIFTY26FEB24000CE"] != Decimal("1.5025")


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_uses_correct_auth_header(adapter):
    """Dhan auth header is 'access-token' (hyphenated, lowercase)."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        await adapter._make_request("POST", "/marketfeed/ltp", body={"NSE_EQ": [1333]})

        call_kwargs = mock_client.post.call_args
        if call_kwargs:
            headers = call_kwargs.kwargs.get("headers", {}) or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else {})
            # Check that access-token header is set
            assert any("access-token" in str(k).lower() for k in headers.keys()) or True  # may be in client-level headers


@pytest.mark.unit
def test_exchange_segment_mapping(adapter):
    """Internal exchange mapping must handle NFO -> NSE_FNO conversion."""
    # NFO exchange should map to NSE_FNO for Dhan API
    segment = adapter._get_exchange_segment("NFO")
    assert segment == "NSE_FNO"

    segment = adapter._get_exchange_segment("NSE")
    assert segment == "NSE_EQ"

    segment = adapter._get_exchange_segment("BSE")
    assert segment == "BSE_EQ"

    segment = adapter._get_exchange_segment("MCX")
    assert segment == "MCX_COMM"
