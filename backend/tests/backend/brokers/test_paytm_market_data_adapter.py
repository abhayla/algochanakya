"""
Tests for PaytmMarketDataAdapter - REST market data adapter.

Covers: get_quote, get_ltp, get_historical, get_instruments,
search_instruments, get_token, get_symbol, connect, disconnect,
error handling, price normalization (RUPEES), auth header (x-jwt-token).
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.brokers.market_data.paytm_adapter import PaytmMarketDataAdapter
from app.services.brokers.market_data.market_data_base import (
    PaytmMarketDataCredentials,
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


@pytest.fixture
def credentials():
    return PaytmMarketDataCredentials(
        broker_type="paytm",
        user_id=uuid4(),
        api_key="TEST_API_KEY",
        access_token="eyJ_access_token",
    )


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_token_manager():
    mgr = AsyncMock()
    mgr.get_token = AsyncMock(return_value=46512)
    mgr.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    mgr.load_cache = AsyncMock()
    return mgr


@pytest.fixture
def adapter(credentials, mock_db, mock_token_manager):
    with patch("app.services.brokers.market_data.paytm_adapter.TokenManagerFactory") as MockFactory:
        MockFactory.get_manager.return_value = mock_token_manager
        a = PaytmMarketDataAdapter(credentials, mock_db)
        a._token_manager = mock_token_manager
    return a


# ─── Sample responses ────────────────────────────────────────────────────────

SAMPLE_PROFILE = {"data": {"client_id": "TEST123", "name": "Test User"}}

SAMPLE_LIVE_LTP = {
    "data": [{"security_id": "46512", "last_price": 150.25}]
}

SAMPLE_LIVE_FULL = {
    "data": [
        {
            "security_id": "46512",
            "last_price": 150.25,
            "open": 148.00,
            "high": 155.00,
            "low": 147.50,
            "close": 149.00,
            "volume": 125000,
            "oi": 5000000,
            "bid_price": 150.20,
            "ask_price": 150.30,
            "bid_qty": 500,
            "ask_qty": 400,
        }
    ]
}

SAMPLE_OHLC = {
    "candles": [
        [1704067200, 2400.0, 2450.0, 2390.0, 2430.0, 1500000],
        [1704153600, 2410.0, 2460.0, 2395.0, 2445.0, 1800000],
    ]
}

SAMPLE_CSV = (
    "security_id,exchange,segment,symbol,series,expiry,strike_price,option_type,lot_size,tick_size\n"
    "46512,NSE,D,NIFTY,OPT,2026-02-27,24000.00,CE,25,0.05\n"
    "46513,NSE,D,NIFTY,OPT,2026-02-27,24000.00,PE,25,0.05\n"
    "500325,NSE,E,RELIANCE,EQ,,,,1,0.05\n"
    "999920000,NSE,E,NIFTY 50,INDEX,,,,1,0.05\n"
    "46514,NSE,D,NIFTY,FUT,2026-02-27,,,25,0.05\n"
)


# ═══════════════════════════════════════════════════════════════════════════════
# BROKER TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
def test_broker_type(adapter):
    assert adapter.broker_type == MarketDataBrokerType.PAYTM


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECT / DISCONNECT
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_success(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_PROFILE
        result = await adapter.connect()
    assert result is True
    assert adapter.is_connected is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_loads_token_cache(adapter, mock_token_manager):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_PROFILE
        await adapter.connect()
    mock_token_manager.load_cache.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_auth_error(adapter):
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("Invalid token 401")
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
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LIVE_LTP
        result = await adapter.get_ltp(["NIFTY26FEB24000CE"])
    assert "NIFTY26FEB24000CE" in result
    assert result["NIFTY26FEB24000CE"] == Decimal("150.25")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_decimal_type(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LIVE_LTP
        result = await adapter.get_ltp(["NIFTY26FEB24000CE"])
    assert isinstance(result["NIFTY26FEB24000CE"], Decimal)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_symbol_not_found(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=None)
    with pytest.raises(InvalidSymbolError):
        await adapter.get_ltp(["INVALID"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_api_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("connection error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_ltp(["NIFTY26FEB24000CE"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_auth_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("Unauthorized token 401")
        with pytest.raises(AuthenticationError):
            await adapter.get_ltp(["NIFTY26FEB24000CE"])


# ═══════════════════════════════════════════════════════════════════════════════
# GET_QUOTE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_returns_unified_quote(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LIVE_FULL
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])
    assert "NIFTY26FEB24000CE" in result
    q = result["NIFTY26FEB24000CE"]
    assert q.last_price == Decimal("150.25")
    assert q.open == Decimal("148.00")
    assert q.high == Decimal("155.00")
    assert q.low == Decimal("147.50")
    assert q.close == Decimal("149.00")
    assert q.volume == 125000
    assert q.oi == 5000000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_prices_decimal(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LIVE_FULL
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])
    q = result["NIFTY26FEB24000CE"]
    assert isinstance(q.last_price, Decimal)
    assert isinstance(q.open, Decimal)
    assert isinstance(q.close, Decimal)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_bid_ask(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LIVE_FULL
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])
    q = result["NIFTY26FEB24000CE"]
    assert q.bid_price == Decimal("150.20")
    assert q.ask_price == Decimal("150.30")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_api_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("API error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_quote(["NIFTY26FEB24000CE"])


# ═══════════════════════════════════════════════════════════════════════════════
# GET_HISTORICAL
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_returns_candles(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_OHLC
        result = await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), "day")
    assert len(result) == 2
    assert all(isinstance(c, OHLCVCandle) for c in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_prices_decimal(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_OHLC
        result = await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), "day")
    candle = result[0]
    assert isinstance(candle.open, Decimal)
    assert candle.open == Decimal("2400.0")
    assert candle.high == Decimal("2450.0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_volume_int(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_OHLC
        result = await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), "day")
    assert isinstance(result[0].volume, int)
    assert result[0].volume == 1500000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_symbol_not_found(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=None)
    with pytest.raises(InvalidSymbolError):
        await adapter.get_historical("INVALID", date(2026, 1, 1), date(2026, 1, 2), "day")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_api_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("Server error")
        with pytest.raises(DataNotAvailableError):
            await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), "day")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_interval_mapping(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    for canonical, expected in [("1min", "1"), ("5min", "5"), ("15min", "15"), ("hour", "60"), ("day", "1D")]:
        with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_OHLC
            await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), canonical)
            assert mock_req.called


# ═══════════════════════════════════════════════════════════════════════════════
# GET_INSTRUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_returns_list(adapter):
    with patch.object(adapter, "_download_script_master", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.get_instruments("NFO")
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_canonical_symbols(adapter):
    with patch.object(adapter, "_download_script_master", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.get_instruments("NFO")
    for inst in result:
        assert inst.canonical_symbol


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_options_have_fields(adapter):
    with patch.object(adapter, "_download_script_master", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.get_instruments("NFO")
    options = [i for i in result if i.instrument_type in ("CE", "PE")]
    assert len(options) >= 2
    for opt in options:
        assert opt.strike is not None
        assert opt.expiry is not None
        assert opt.lot_size == 25


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_api_error(adapter):
    with patch.object(adapter, "_download_script_master", new_callable=AsyncMock) as mock_dl:
        mock_dl.side_effect = Exception("Network error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_instruments("NFO")


# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH_INSTRUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_instruments_basic(adapter):
    with patch.object(adapter, "_download_script_master", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.search_instruments("NIFTY")
    assert all("NIFTY" in i.canonical_symbol.upper() or "NIFTY" in i.name.upper() for i in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_instruments_max_50(adapter):
    with patch.object(adapter, "_download_script_master", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.search_instruments("NIFTY")
    assert len(result) <= 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_no_match(adapter):
    with patch.object(adapter, "_download_script_master", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.search_instruments("XYZNONEXISTENT")
    assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# TOKEN / SYMBOL
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_token_delegates(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    result = await adapter.get_token("NIFTY26FEB24000CE")
    assert result == 46512


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_token_not_found(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=None)
    with pytest.raises(InvalidSymbolError):
        await adapter.get_token("INVALID")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_symbol_delegates(adapter, mock_token_manager):
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    result = await adapter.get_symbol(46512)
    assert result == "NIFTY26FEB24000CE"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_symbol_not_found(adapter, mock_token_manager):
    mock_token_manager.get_symbol = AsyncMock(return_value=None)
    with pytest.raises(InvalidSymbolError):
        await adapter.get_symbol(99999)


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET STUBS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscribe_noop(adapter):
    await adapter.subscribe([46512], "quote")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unsubscribe_noop(adapter):
    await adapter.unsubscribe([46512])


@pytest.mark.unit
def test_on_tick_registers(adapter):
    adapter.on_tick(MagicMock())


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_prices_not_divided_by_100(adapter, mock_token_manager):
    """Paytm returns RUPEES — must NOT divide by 100."""
    mock_token_manager.get_token = AsyncMock(return_value=46512)
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LIVE_LTP
        result = await adapter.get_ltp(["NIFTY26FEB24000CE"])
    assert result["NIFTY26FEB24000CE"] == Decimal("150.25")
    assert result["NIFTY26FEB24000CE"] != Decimal("1.5025")


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH HEADER
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
def test_auth_header_uses_x_jwt_token(adapter):
    """Paytm auth header is 'x-jwt-token' (not Authorization: Bearer)."""
    headers = adapter._headers
    assert "x-jwt-token" in headers
    assert "Authorization" not in headers
