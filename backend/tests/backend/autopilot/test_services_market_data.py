"""
Market Data Service Tests

Tests for app/services/market_data.py:
- get_ltp() - Last Traded Price
- get_quote() - Full market quotes
- get_spot_price() - Index spot prices
- get_vix() - India VIX value
- get_option_chain_ltp() - Option chain LTP
- Caching behavior
- Error handling
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock
import time

from app.services.market_data import (
    MarketDataService, MarketQuote, SpotData,
    get_market_data_service, clear_market_data_services
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_kite():
    """Create mock KiteConnect client."""
    kite = MagicMock()
    kite.access_token = "test_access_token"

    # Mock LTP response
    kite.ltp.return_value = {
        "NFO:NIFTY24DEC24500CE": {"last_price": 150.50},
        "NFO:NIFTY24DEC24500PE": {"last_price": 120.25},
        "NFO:NIFTY24DEC25000CE": {"last_price": 85.75},
        "NFO:NIFTY24DEC25000PE": {"last_price": 200.00},
    }

    # Mock quote response
    kite.quote.return_value = {
        "NSE:NIFTY 50": {
            "instrument_token": 256265,
            "tradingsymbol": "NIFTY 50",
            "last_price": 25000.0,
            "ohlc": {"open": 24900, "high": 25100, "low": 24850, "close": 24950},
            "volume": 0,
            "oi": 0
        },
        "NSE:NIFTY BANK": {
            "instrument_token": 260105,
            "tradingsymbol": "NIFTY BANK",
            "last_price": 52000.0,
            "ohlc": {"open": 51800, "high": 52200, "low": 51700, "close": 51900},
            "volume": 0,
            "oi": 0
        },
        "NSE:INDIA VIX": {
            "instrument_token": 264969,
            "tradingsymbol": "INDIA VIX",
            "last_price": 15.50,
            "ohlc": {"open": 14.80, "high": 16.00, "low": 14.50, "close": 15.20},
            "volume": 0,
            "oi": 0
        },
        "NFO:NIFTY24DEC24500CE": {
            "instrument_token": 12345,
            "tradingsymbol": "NIFTY24DEC24500CE",
            "last_price": 150.50,
            "ohlc": {"open": 145.0, "high": 155.0, "low": 140.0, "close": 148.0},
            "volume": 100000,
            "oi": 5000000
        }
    }

    return kite


@pytest.fixture
def market_data_service(mock_kite):
    """Create MarketDataService with mock Kite client."""
    # Clear any cached services
    clear_market_data_services()
    return MarketDataService(mock_kite)


# =============================================================================
# GET_LTP TESTS
# =============================================================================

class TestGetLTP:
    """Tests for get_ltp method."""

    @pytest.mark.asyncio
    async def test_get_ltp_single_instrument(self, market_data_service, mock_kite):
        """Test getting LTP for single instrument."""
        instruments = ["NFO:NIFTY24DEC24500CE"]

        result = await market_data_service.get_ltp(instruments)

        assert len(result) == 1
        assert "NFO:NIFTY24DEC24500CE" in result
        assert isinstance(result["NFO:NIFTY24DEC24500CE"], Decimal)
        assert result["NFO:NIFTY24DEC24500CE"] == Decimal("150.50")

        mock_kite.ltp.assert_called_once_with(instruments)

    @pytest.mark.asyncio
    async def test_get_ltp_multiple_instruments(self, market_data_service, mock_kite):
        """Test getting LTP for multiple instruments."""
        instruments = [
            "NFO:NIFTY24DEC24500CE",
            "NFO:NIFTY24DEC24500PE",
            "NFO:NIFTY24DEC25000CE"
        ]

        result = await market_data_service.get_ltp(instruments)

        assert len(result) == 3
        assert result["NFO:NIFTY24DEC24500CE"] == Decimal("150.50")
        assert result["NFO:NIFTY24DEC24500PE"] == Decimal("120.25")
        assert result["NFO:NIFTY24DEC25000CE"] == Decimal("85.75")

    @pytest.mark.asyncio
    async def test_get_ltp_empty_list(self, market_data_service, mock_kite):
        """Test getting LTP with empty instrument list."""
        mock_kite.ltp.return_value = {}

        result = await market_data_service.get_ltp([])

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_ltp_api_error(self, market_data_service, mock_kite):
        """Test error handling when Kite API fails."""
        mock_kite.ltp.side_effect = Exception("API connection failed")

        with pytest.raises(Exception) as exc_info:
            await market_data_service.get_ltp(["NFO:NIFTY24DEC24500CE"])

        assert "API connection failed" in str(exc_info.value)


# =============================================================================
# GET_QUOTE TESTS
# =============================================================================

class TestGetQuote:
    """Tests for get_quote method."""

    @pytest.mark.asyncio
    async def test_get_quote_returns_market_quote(self, market_data_service, mock_kite):
        """Test get_quote returns MarketQuote objects."""
        instruments = ["NFO:NIFTY24DEC24500CE"]

        result = await market_data_service.get_quote(instruments)

        assert len(result) == 1
        assert "NFO:NIFTY24DEC24500CE" in result

        quote = result["NFO:NIFTY24DEC24500CE"]
        assert isinstance(quote, MarketQuote)
        assert quote.instrument_token == 12345
        assert quote.ltp == Decimal("150.50")
        assert quote.open == Decimal("145.0")
        assert quote.high == Decimal("155.0")
        assert quote.low == Decimal("140.0")
        assert quote.close == Decimal("148.0")
        assert quote.volume == 100000
        assert quote.oi == 5000000

    @pytest.mark.asyncio
    async def test_get_quote_handles_missing_ohlc(self, market_data_service, mock_kite):
        """Test get_quote handles missing OHLC data gracefully."""
        mock_kite.quote.return_value = {
            "NFO:TEST": {
                "instrument_token": 99999,
                "last_price": 100.0,
                # No OHLC data
                "volume": 1000,
                "oi": 5000
            }
        }

        result = await market_data_service.get_quote(["NFO:TEST"])

        quote = result["NFO:TEST"]
        assert quote.ltp == Decimal("100.0")
        assert quote.open == Decimal("0")
        assert quote.high == Decimal("0")
        assert quote.low == Decimal("0")
        assert quote.close == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_quote_api_error(self, market_data_service, mock_kite):
        """Test error handling when quote API fails."""
        mock_kite.quote.side_effect = Exception("Quote API failed")

        with pytest.raises(Exception) as exc_info:
            await market_data_service.get_quote(["NFO:NIFTY24DEC24500CE"])

        assert "Quote API failed" in str(exc_info.value)


# =============================================================================
# GET_SPOT_PRICE TESTS
# =============================================================================

class TestGetSpotPrice:
    """Tests for get_spot_price method."""

    @pytest.mark.asyncio
    async def test_get_spot_price_nifty(self, market_data_service, mock_kite):
        """Test getting NIFTY spot price."""
        result = await market_data_service.get_spot_price("NIFTY")

        assert isinstance(result, SpotData)
        assert result.symbol == "NIFTY"
        assert result.ltp == Decimal("25000.0")
        # Change = 25000 - 24950 = 50
        assert result.change == Decimal("50.0")
        # Change % = 50 / 24950 * 100 ≈ 0.2004%
        assert 0.20 <= result.change_pct <= 0.21

        mock_kite.quote.assert_called_with(["NSE:NIFTY 50"])

    @pytest.mark.asyncio
    async def test_get_spot_price_banknifty(self, market_data_service, mock_kite):
        """Test getting BANKNIFTY spot price."""
        result = await market_data_service.get_spot_price("BANKNIFTY")

        assert result.symbol == "BANKNIFTY"
        assert result.ltp == Decimal("52000.0")

        mock_kite.quote.assert_called_with(["NSE:NIFTY BANK"])

    @pytest.mark.asyncio
    async def test_get_spot_price_case_insensitive(self, market_data_service, mock_kite):
        """Test spot price lookup is case insensitive."""
        result = await market_data_service.get_spot_price("nifty")

        assert result.symbol == "NIFTY"
        assert result.ltp == Decimal("25000.0")

    @pytest.mark.asyncio
    async def test_get_spot_price_unknown_underlying(self, market_data_service):
        """Test error for unknown underlying."""
        with pytest.raises(ValueError) as exc_info:
            await market_data_service.get_spot_price("UNKNOWN")

        assert "Unknown underlying" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_spot_price_uses_cache(self, market_data_service, mock_kite):
        """Test spot price is cached."""
        # First call
        result1 = await market_data_service.get_spot_price("NIFTY")

        # Second call (should use cache)
        result2 = await market_data_service.get_spot_price("NIFTY")

        # Should only call API once
        assert mock_kite.quote.call_count == 1
        assert result1.ltp == result2.ltp

    @pytest.mark.asyncio
    async def test_get_spot_price_cache_expiry(self, market_data_service, mock_kite):
        """Test spot price cache expires."""
        # Set short TTL
        market_data_service._cache_ttl = 0.1  # 100ms

        # First call
        await market_data_service.get_spot_price("NIFTY")
        assert mock_kite.quote.call_count == 1

        # Wait for cache to expire
        await asyncio.sleep(0.15)

        # Second call (should call API again)
        await market_data_service.get_spot_price("NIFTY")
        assert mock_kite.quote.call_count == 2


# =============================================================================
# GET_VIX TESTS
# =============================================================================

class TestGetVix:
    """Tests for get_vix method."""

    @pytest.mark.asyncio
    async def test_get_vix_returns_decimal(self, market_data_service, mock_kite):
        """Test get_vix returns Decimal value."""
        result = await market_data_service.get_vix()

        assert isinstance(result, Decimal)
        assert result == Decimal("15.50")

        mock_kite.quote.assert_called_with(["NSE:INDIA VIX"])

    @pytest.mark.asyncio
    async def test_get_vix_uses_cache(self, market_data_service, mock_kite):
        """Test VIX value is cached."""
        # First call
        result1 = await market_data_service.get_vix()

        # Second call (should use cache)
        result2 = await market_data_service.get_vix()

        # Should only call API once
        assert mock_kite.quote.call_count == 1
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_get_vix_api_error(self, market_data_service, mock_kite):
        """Test error handling when VIX API fails."""
        mock_kite.quote.side_effect = Exception("VIX not available")

        with pytest.raises(Exception) as exc_info:
            await market_data_service.get_vix()

        assert "VIX not available" in str(exc_info.value)


# =============================================================================
# GET_OPTION_CHAIN_LTP TESTS
# =============================================================================

class TestGetOptionChainLTP:
    """Tests for get_option_chain_ltp method."""

    @pytest.mark.asyncio
    async def test_get_option_chain_ltp_single_strike(self, market_data_service, mock_kite):
        """Test getting LTP for single strike."""
        expiry = date(2024, 12, 26)
        strikes = [Decimal("24500")]

        await market_data_service.get_option_chain_ltp("NIFTY", expiry, strikes)

        # Should request both CE and PE for the strike
        called_instruments = mock_kite.ltp.call_args[0][0]
        assert "NFO:NIFTY24DEC2624500CE" in called_instruments
        assert "NFO:NIFTY24DEC2624500PE" in called_instruments

    @pytest.mark.asyncio
    async def test_get_option_chain_ltp_multiple_strikes(self, market_data_service, mock_kite):
        """Test getting LTP for multiple strikes."""
        expiry = date(2024, 12, 26)
        strikes = [Decimal("24500"), Decimal("25000"), Decimal("25500")]

        await market_data_service.get_option_chain_ltp("NIFTY", expiry, strikes)

        called_instruments = mock_kite.ltp.call_args[0][0]

        # Should have 6 instruments (3 strikes x 2 types)
        assert len(called_instruments) == 6

        # Verify all CE and PE are included
        for strike in [24500, 25000, 25500]:
            assert f"NFO:NIFTY24DEC26{strike}CE" in called_instruments
            assert f"NFO:NIFTY24DEC26{strike}PE" in called_instruments

    @pytest.mark.asyncio
    async def test_get_option_chain_ltp_expiry_format(self, market_data_service, mock_kite):
        """Test expiry date is formatted correctly."""
        # Test with different expiry dates
        expiry = date(2025, 1, 9)
        strikes = [Decimal("25000")]

        await market_data_service.get_option_chain_ltp("NIFTY", expiry, strikes)

        called_instruments = mock_kite.ltp.call_args[0][0]

        # Format should be 25JAN09
        assert "NFO:NIFTY25JAN0925000CE" in called_instruments
        assert "NFO:NIFTY25JAN0925000PE" in called_instruments


# =============================================================================
# CACHING TESTS
# =============================================================================

class TestCaching:
    """Tests for caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_is_initially_empty(self, market_data_service):
        """Test cache starts empty."""
        assert len(market_data_service._cache) == 0
        assert len(market_data_service._cache_expiry) == 0

    @pytest.mark.asyncio
    async def test_clear_cache(self, market_data_service, mock_kite):
        """Test clear_cache removes all cached data."""
        # Populate cache
        await market_data_service.get_spot_price("NIFTY")
        await market_data_service.get_vix()

        assert len(market_data_service._cache) > 0

        # Clear cache
        market_data_service.clear_cache()

        assert len(market_data_service._cache) == 0
        assert len(market_data_service._cache_expiry) == 0

    @pytest.mark.asyncio
    async def test_is_cache_valid(self, market_data_service, mock_kite):
        """Test _is_cache_valid method."""
        # Initially not valid (doesn't exist)
        assert not market_data_service._is_cache_valid("test_key")

        # Add to cache
        market_data_service._cache["test_key"] = "test_value"
        market_data_service._cache_expiry["test_key"] = datetime.now()

        # Should be valid
        assert market_data_service._is_cache_valid("test_key")

    @pytest.mark.asyncio
    async def test_cache_ttl_respected(self, market_data_service, mock_kite):
        """Test cache TTL is respected."""
        # Set very short TTL
        market_data_service._cache_ttl = 0.05  # 50ms

        # Add to cache
        market_data_service._cache["test_key"] = "test_value"
        market_data_service._cache_expiry["test_key"] = datetime.now()

        # Should be valid immediately
        assert market_data_service._is_cache_valid("test_key")

        # Wait for expiry
        await asyncio.sleep(0.1)

        # Should be invalid now
        assert not market_data_service._is_cache_valid("test_key")


# =============================================================================
# SERVICE FACTORY TESTS
# =============================================================================

class TestServiceFactory:
    """Tests for service factory functions."""

    def test_get_market_data_service_creates_new(self, mock_kite):
        """Test get_market_data_service creates new instance."""
        clear_market_data_services()

        service = get_market_data_service(mock_kite)

        assert isinstance(service, MarketDataService)
        assert service.kite == mock_kite

    def test_get_market_data_service_returns_cached(self, mock_kite):
        """Test get_market_data_service returns cached instance."""
        clear_market_data_services()

        service1 = get_market_data_service(mock_kite)
        service2 = get_market_data_service(mock_kite)

        # Should be same instance
        assert service1 is service2

    def test_get_market_data_service_different_tokens(self):
        """Test different access tokens get different services."""
        clear_market_data_services()

        kite1 = MagicMock()
        kite1.access_token = "token_1"

        kite2 = MagicMock()
        kite2.access_token = "token_2"

        service1 = get_market_data_service(kite1)
        service2 = get_market_data_service(kite2)

        # Should be different instances
        assert service1 is not service2

    def test_clear_market_data_services(self, mock_kite):
        """Test clear_market_data_services clears all instances."""
        # Create some services
        get_market_data_service(mock_kite)

        # Clear all
        clear_market_data_services()

        # Creating should give new instance
        service = get_market_data_service(mock_kite)
        assert isinstance(service, MarketDataService)


# =============================================================================
# INDEX TOKEN TESTS
# =============================================================================

class TestIndexTokens:
    """Tests for index token mappings."""

    def test_nifty_token(self, market_data_service):
        """Test NIFTY token is correct."""
        assert MarketDataService.INDEX_TOKENS["NIFTY"] == 256265

    def test_banknifty_token(self, market_data_service):
        """Test BANKNIFTY token is correct."""
        assert MarketDataService.INDEX_TOKENS["BANKNIFTY"] == 260105

    def test_finnifty_token(self, market_data_service):
        """Test FINNIFTY token is correct."""
        assert MarketDataService.INDEX_TOKENS["FINNIFTY"] == 257801

    def test_vix_token(self, market_data_service):
        """Test INDIA VIX token is correct."""
        assert MarketDataService.INDEX_TOKENS["INDIAVIX"] == 264969


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestDataClasses:
    """Tests for data classes."""

    def test_market_quote_creation(self):
        """Test MarketQuote dataclass."""
        quote = MarketQuote(
            instrument_token=12345,
            tradingsymbol="NIFTY24DEC24500CE",
            ltp=Decimal("150.50"),
            open=Decimal("145.0"),
            high=Decimal("155.0"),
            low=Decimal("140.0"),
            close=Decimal("148.0"),
            volume=100000,
            oi=5000000,
            timestamp=datetime.now()
        )

        assert quote.instrument_token == 12345
        assert quote.tradingsymbol == "NIFTY24DEC24500CE"
        assert quote.ltp == Decimal("150.50")
        assert quote.volume == 100000
        assert quote.oi == 5000000

    def test_spot_data_creation(self):
        """Test SpotData dataclass."""
        spot = SpotData(
            symbol="NIFTY",
            ltp=Decimal("25000.0"),
            change=Decimal("50.0"),
            change_pct=0.2,
            timestamp=datetime.now()
        )

        assert spot.symbol == "NIFTY"
        assert spot.ltp == Decimal("25000.0")
        assert spot.change == Decimal("50.0")
        assert spot.change_pct == 0.2


# =============================================================================
# CONCURRENT REQUEST TESTS
# =============================================================================

class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_ltp_requests(self, market_data_service, mock_kite):
        """Test concurrent LTP requests."""
        # Make concurrent requests
        tasks = [
            market_data_service.get_ltp(["NFO:NIFTY24DEC24500CE"]),
            market_data_service.get_ltp(["NFO:NIFTY24DEC24500PE"]),
            market_data_service.get_ltp(["NFO:NIFTY24DEC25000CE"]),
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 3
        for result in results:
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_concurrent_spot_and_vix(self, market_data_service, mock_kite):
        """Test concurrent spot price and VIX requests."""
        tasks = [
            market_data_service.get_spot_price("NIFTY"),
            market_data_service.get_vix(),
        ]

        results = await asyncio.gather(*tasks)

        assert isinstance(results[0], SpotData)
        assert isinstance(results[1], Decimal)
