"""
Tests for UpstoxMarketDataAdapter - REST market data adapter.

Covers: get_quote, get_ltp, get_historical, get_instruments,
search_instruments, get_token, get_symbol, connect, disconnect,
error handling, price normalization (RUPEES), auth header (Bearer).
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.brokers.market_data.upstox_adapter import UpstoxMarketDataAdapter
from app.services.brokers.market_data.market_data_base import (
    UpstoxMarketDataCredentials,
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
    return UpstoxMarketDataCredentials(
        broker_type="upstox",
        user_id=uuid4(),
        api_key="TEST_API_KEY",
        access_token="eyJ_upstox_access_token",
    )


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_token_manager():
    mgr = AsyncMock()
    mgr.get_token = AsyncMock(return_value="NSE_FO|12345")
    mgr.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    mgr.load_cache = AsyncMock()
    return mgr


@pytest.fixture
def adapter(credentials, mock_db, mock_token_manager):
    with patch("app.services.brokers.market_data.upstox_adapter.TokenManagerFactory") as MockFactory:
        MockFactory.get_manager.return_value = mock_token_manager
        a = UpstoxMarketDataAdapter(credentials, mock_db)
        a._token_manager = mock_token_manager
    return a


# ─── Sample responses ────────────────────────────────────────────────────────

SAMPLE_PROFILE = {"data": {"user_id": "TEST123", "name": "Test User"}, "status": "success"}

SAMPLE_LTP_RESPONSE = {
    "status": "success",
    "data": {
        "NSE_FO|12345": {
            "last_price": 150.25,
        }
    }
}

SAMPLE_QUOTE_RESPONSE = {
    "status": "success",
    "data": {
        "NSE_FO|12345": {
            "last_price": 150.25,
            "ohlc": {
                "open": 148.00,
                "high": 155.00,
                "low": 147.50,
                "close": 149.00,
            },
            "volume": 125000,
            "oi": 5000000,
            "depth": {
                "buy": [{"price": 150.20, "quantity": 500, "orders": 5}],
                "sell": [{"price": 150.30, "quantity": 400, "orders": 4}],
            },
        }
    }
}

# Historical candles: descending order (newest first), format: [epoch, O, H, L, C, V]
SAMPLE_HISTORICAL = {
    "status": "success",
    "data": {
        "candles": [
            [1704153600, 2410.0, 2460.0, 2395.0, 2445.0, 1800000],
            [1704067200, 2400.0, 2450.0, 2390.0, 2430.0, 1500000],
        ]
    }
}

SAMPLE_CSV = (
    "instrument_key,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,"
    "instrument_type,option_type,exchange\n"
    "NSE_FO|12345,12345,NIFTY26FEB24000CE,NIFTY,150.25,2026-02-27,24000.0,0.05,25,OPTIDX,CE,NSE_FO\n"
    "NSE_FO|12346,12346,NIFTY26FEB24000PE,NIFTY,145.50,2026-02-27,24000.0,0.05,25,OPTIDX,PE,NSE_FO\n"
    "NSE_EQ|2885,2885,RELIANCE,Reliance Industries,2500.00,,,,1,EQ,,NSE_EQ\n"
    "NSE_INDEX|13,13,NIFTY 50,Nifty 50,22500.00,,,,1,INDEX,,NSE_INDEX\n"
    "NSE_FO|67890,67890,NIFTY26FEBFUT,NIFTY,22450.0,2026-02-27,,0.05,25,FUTIDX,,NSE_FO\n"
)


# ═══════════════════════════════════════════════════════════════════════════════
# BROKER TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
def test_broker_type(adapter):
    assert adapter.broker_type == MarketDataBrokerType.UPSTOX


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
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LTP_RESPONSE
        result = await adapter.get_ltp(["NIFTY26FEB24000CE"])
    assert "NIFTY26FEB24000CE" in result
    assert result["NIFTY26FEB24000CE"] == Decimal("150.25")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_decimal_type(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LTP_RESPONSE
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
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("connection error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_ltp(["NIFTY26FEB24000CE"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ltp_auth_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
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
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTE_RESPONSE
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])
    assert "NIFTY26FEB24000CE" in result
    q = result["NIFTY26FEB24000CE"]
    assert q.last_price == Decimal("150.25")
    assert q.open == Decimal("148.0")
    assert q.high == Decimal("155.0")
    assert q.low == Decimal("147.5")
    assert q.close == Decimal("149.0")
    assert q.volume == 125000
    assert q.oi == 5000000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_prices_decimal(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTE_RESPONSE
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])
    q = result["NIFTY26FEB24000CE"]
    assert isinstance(q.last_price, Decimal)
    assert isinstance(q.open, Decimal)
    assert isinstance(q.close, Decimal)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_bid_ask(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_QUOTE_RESPONSE
        result = await adapter.get_quote(["NIFTY26FEB24000CE"])
    q = result["NIFTY26FEB24000CE"]
    assert q.bid_price == Decimal("150.20")
    assert q.ask_price == Decimal("150.30")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_api_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
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
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL
        result = await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), "day")
    assert len(result) == 2
    assert all(isinstance(c, OHLCVCandle) for c in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_prices_decimal(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL
        result = await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), "day")
    candle = result[0]
    assert isinstance(candle.open, Decimal)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_volume_int(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL
        result = await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), "day")
    assert isinstance(result[0].volume, int)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_candles_ascending(adapter, mock_token_manager):
    """Upstox returns descending; adapter should return ascending (oldest first)."""
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_HISTORICAL
        result = await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), "day")
    # Oldest candle should come first
    assert result[0].timestamp <= result[1].timestamp


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_symbol_not_found(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value=None)
    with pytest.raises(InvalidSymbolError):
        await adapter.get_historical("INVALID", date(2026, 1, 1), date(2026, 1, 2), "day")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_api_error(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("Server error")
        with pytest.raises(DataNotAvailableError):
            await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), "day")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_interval_mapping(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    for canonical in ["1min", "5min", "15min", "30min", "hour", "day", "week", "month"]:
        with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_HISTORICAL
            await adapter.get_historical("NIFTY26FEB24000CE", date(2026, 1, 1), date(2026, 1, 2), canonical)
            assert mock_req.called


# ═══════════════════════════════════════════════════════════════════════════════
# GET_INSTRUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_returns_list(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.get_instruments("NFO")
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_canonical_symbols(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.get_instruments("NFO")
    for inst in result:
        assert inst.canonical_symbol


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_instruments_options_have_fields(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_dl:
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
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_dl:
        mock_dl.side_effect = Exception("Network error")
        with pytest.raises(BrokerAPIError):
            await adapter.get_instruments("NFO")


# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH_INSTRUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_instruments_basic(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.search_instruments("NIFTY")
    assert all("NIFTY" in i.canonical_symbol.upper() or "NIFTY" in i.name.upper() for i in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_instruments_max_50(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.search_instruments("NIFTY")
    assert len(result) <= 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_no_match(adapter):
    with patch.object(adapter, "_download_instrument_csv", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = SAMPLE_CSV
        result = await adapter.search_instruments("XYZNONEXISTENT")
    assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# TOKEN / SYMBOL
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_token_delegates(adapter, mock_token_manager):
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    result = await adapter.get_token("NIFTY26FEB24000CE")
    assert result == "NSE_FO|12345"


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
    result = await adapter.get_symbol("NSE_FO|12345")
    assert result == "NIFTY26FEB24000CE"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_symbol_not_found(adapter, mock_token_manager):
    mock_token_manager.get_symbol = AsyncMock(return_value=None)
    with pytest.raises(InvalidSymbolError):
        await adapter.get_symbol("NSE_FO|99999")


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET STUBS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscribe_noop(adapter):
    await adapter.subscribe(["NSE_FO|12345"], "quote")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unsubscribe_noop(adapter):
    await adapter.unsubscribe(["NSE_FO|12345"])


@pytest.mark.unit
def test_on_tick_registers(adapter):
    adapter.on_tick(MagicMock())


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.asyncio
async def test_prices_not_divided_by_100(adapter, mock_token_manager):
    """Upstox returns RUPEES — must NOT divide by 100."""
    mock_token_manager.get_token = AsyncMock(return_value="NSE_FO|12345")
    mock_token_manager.get_symbol = AsyncMock(return_value="NIFTY26FEB24000CE")
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_LTP_RESPONSE
        result = await adapter.get_ltp(["NIFTY26FEB24000CE"])
    assert result["NIFTY26FEB24000CE"] == Decimal("150.25")
    assert result["NIFTY26FEB24000CE"] != Decimal("1.5025")


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH HEADER
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
def test_auth_header_uses_bearer(adapter):
    """Upstox auth header is 'Authorization: Bearer {token}'."""
    headers = adapter._headers
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")
    assert "x-jwt-token" not in headers


@pytest.mark.unit
def test_auth_header_contains_token(adapter, credentials):
    """Authorization header must include the actual access token."""
    assert credentials.access_token in adapter._headers["Authorization"]


# ═══════════════════════════════════════════════════════════════════════════════
# GET_OPTION_CHAIN_QUOTES
# ═══════════════════════════════════════════════════════════════════════════════

# Sample Upstox /v2/option/chain response — matches real API structure.
# NOTE: Upstox does NOT return a "trading_symbol" field; only "instrument_key".
SAMPLE_OPTION_CHAIN_RESPONSE = {
    "status": "success",
    "data": [
        {
            "expiry": "2026-04-13",
            "strike_price": 24000.0,
            "underlying_key": "NSE_INDEX|Nifty 50",
            "underlying_spot_price": 24050.6,
            "call_options": {
                "instrument_key": "NSE_FO|54771",
                "market_data": {
                    "ltp": 150.25,
                    "volume": 125000,
                    "oi": 5000000,
                    "close_price": 145.50,
                    "bid_price": 150.0,
                    "bid_qty": 500,
                    "ask_price": 150.50,
                    "ask_qty": 400,
                    "prev_oi": 4800000,
                    "open_price": 148.0,
                    "high_price": 155.0,
                    "low_price": 147.5,
                },
                "option_greeks": {
                    "vega": 8.25,
                    "theta": -12.50,
                    "gamma": 0.0003,
                    "delta": 0.55,
                    "iv": 18.50,
                    "pop": 52.3,
                },
            },
            "put_options": {
                "instrument_key": "NSE_FO|54772",
                "market_data": {
                    "ltp": 45.75,
                    "volume": 80000,
                    "oi": 3000000,
                    "close_price": 50.25,
                    "bid_price": 45.50,
                    "bid_qty": 300,
                    "ask_price": 46.00,
                    "ask_qty": 250,
                    "prev_oi": 2900000,
                    "open_price": 50.0,
                    "high_price": 52.0,
                    "low_price": 44.0,
                },
                "option_greeks": {
                    "vega": 8.25,
                    "theta": -10.30,
                    "gamma": 0.0003,
                    "delta": -0.45,
                    "iv": 19.20,
                    "pop": 47.7,
                },
            },
        },
    ],
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_option_chain_quotes_with_token_mapping(adapter):
    """Quotes must be keyed by canonical symbol via token_to_symbol mapping."""
    token_to_symbol = {"54771": "NIFTY26041324000CE", "54772": "NIFTY26041324000PE"}
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_OPTION_CHAIN_RESPONSE
        result = await adapter.get_option_chain_quotes("NIFTY", "2026-04-13", token_to_symbol=token_to_symbol)
    assert "NFO:NIFTY26041324000CE" in result
    assert "NFO:NIFTY26041324000PE" in result
    assert result["NFO:NIFTY26041324000CE"]["last_price"] == 150.25
    assert result["NFO:NIFTY26041324000CE"]["oi"] == 5000000
    # The broken key "NFO:" must NOT exist
    assert "NFO:" not in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_option_chain_quotes_no_token_mapping(adapter):
    """Without token_to_symbol, should return empty dict (graceful degradation)."""
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_OPTION_CHAIN_RESPONSE
        result = await adapter.get_option_chain_quotes("NIFTY", "2026-04-13")
    assert result == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_option_chain_quotes_market_closed(adapter):
    """When ltp=0 (market closed), should fall back to close_price."""
    closed_response = {
        "status": "success",
        "data": [{
            "strike_price": 24000.0,
            "call_options": {
                "instrument_key": "NSE_FO|54771",
                "market_data": {"ltp": 0, "close_price": 145.50, "oi": 5000000, "volume": 0},
                "option_greeks": {"iv": 18.5, "delta": 0.55, "gamma": 0.0003, "theta": -12.5, "vega": 8.25},
            },
            "put_options": None,
        }],
    }
    token_to_symbol = {"54771": "NIFTY26041324000CE"}
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = closed_response
        result = await adapter.get_option_chain_quotes("NIFTY", "2026-04-13", token_to_symbol=token_to_symbol)
    assert result["NFO:NIFTY26041324000CE"]["last_price"] == 145.50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_option_chain_quotes_includes_greeks(adapter):
    """Upstox pre-calculated Greeks must be included in the quote."""
    token_to_symbol = {"54771": "NIFTY26041324000CE"}
    with patch.object(adapter, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = SAMPLE_OPTION_CHAIN_RESPONSE
        result = await adapter.get_option_chain_quotes("NIFTY", "2026-04-13", token_to_symbol=token_to_symbol)
    quote = result["NFO:NIFTY26041324000CE"]
    assert "greeks" in quote
    assert quote["greeks"]["iv"] == 18.50
    assert quote["greeks"]["delta"] == 0.55
    assert quote["greeks"]["gamma"] == 0.0003
    assert quote["greeks"]["theta"] == -12.50
    assert quote["greeks"]["vega"] == 8.25
