"""
OptionChainService Tests

Tests for option chain fetching, caching, and Greeks calculation.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.services.option_chain_service import OptionChainService
from .conftest import get_mock_option_chain_response


class TestOptionChainService:
    """Test OptionChainService functionality."""

    @pytest.mark.asyncio
    async def test_fetch_option_chain_from_api(self):
        """Test fetching option chain from API (no cache)."""
        service = OptionChainService(kite=MagicMock(), db=MagicMock())
        expiry = date.today() + timedelta(days=7)

        mock_instruments = [
            {'instrument_token': 12345, 'tradingsymbol': 'NIFTY24D2625000CE',
             'strike': 25000, 'instrument_type': 'CE'},
            {'instrument_token': 12346, 'tradingsymbol': 'NIFTY24D2625000PE',
             'strike': 25000, 'instrument_type': 'PE'},
        ]

        with patch.object(service, '_fetch_instruments', new_callable=AsyncMock) as mock_fetch, \
             patch.object(service, '_get_spot_price', new_callable=AsyncMock) as mock_spot, \
             patch.object(service.market_data, 'get_ltp', new_callable=AsyncMock) as mock_ltp, \
             patch.object(service, '_get_quotes', new_callable=AsyncMock) as mock_quotes, \
             patch.object(service, '_save_to_cache', new_callable=AsyncMock):

            mock_fetch.return_value = mock_instruments
            mock_spot.return_value = Decimal('25250')
            mock_ltp.return_value = {
                'NFO:NIFTY24D2625000CE': Decimal('150'),
                'NFO:NIFTY24D2625000PE': Decimal('145'),
            }
            mock_quotes.return_value = {}

            result = await service.get_option_chain("NIFTY", expiry, use_cache=False)

            assert result["underlying"] == "NIFTY"
            assert "options" in result
            assert result["spot_price"] == Decimal('25250')
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_option_chain_uses_cache(self):
        """Test option chain uses cache when valid."""
        service = OptionChainService(kite=MagicMock(), db=MagicMock())
        expiry = date.today() + timedelta(days=7)

        cached_result = {
            "underlying": "NIFTY",
            "expiry": expiry,
            "spot_price": Decimal('25250'),
            "options": [],
            "cached": True,
        }

        with patch.object(service, '_get_from_cache', new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = cached_result

            result = await service.get_option_chain("NIFTY", expiry, use_cache=True)

            assert result is not None
            assert result["cached"] is True
            mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_option_chain_refreshes_expired_cache(self):
        """Test option chain fetches fresh data when cache miss."""
        service = OptionChainService(kite=MagicMock(), db=MagicMock())
        expiry = date.today() + timedelta(days=7)

        with patch.object(service, '_get_from_cache', new_callable=AsyncMock) as mock_cache, \
             patch.object(service, '_fetch_instruments', new_callable=AsyncMock) as mock_fetch, \
             patch.object(service, '_get_spot_price', new_callable=AsyncMock) as mock_spot, \
             patch.object(service.market_data, 'get_ltp', new_callable=AsyncMock) as mock_ltp, \
             patch.object(service, '_get_quotes', new_callable=AsyncMock) as mock_quotes, \
             patch.object(service, '_save_to_cache', new_callable=AsyncMock):

            mock_cache.return_value = None  # Cache miss
            mock_fetch.return_value = []
            mock_spot.return_value = Decimal('25250')
            mock_ltp.return_value = {}
            mock_quotes.return_value = {}

            result = await service.get_option_chain("NIFTY", expiry, use_cache=True)

            assert result is not None
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_option_chain_returns_options_key(self):
        """Test option chain result contains 'options' key."""
        service = OptionChainService(kite=MagicMock(), db=MagicMock())
        expiry = date.today() + timedelta(days=7)

        with patch.object(service, '_fetch_instruments', new_callable=AsyncMock) as mock_fetch, \
             patch.object(service, '_get_spot_price', new_callable=AsyncMock) as mock_spot, \
             patch.object(service.market_data, 'get_ltp', new_callable=AsyncMock) as mock_ltp, \
             patch.object(service, '_get_quotes', new_callable=AsyncMock) as mock_quotes, \
             patch.object(service, '_save_to_cache', new_callable=AsyncMock):

            mock_fetch.return_value = []
            mock_spot.return_value = Decimal('25250')
            mock_ltp.return_value = {}
            mock_quotes.return_value = {}

            result = await service.get_option_chain("NIFTY", expiry, use_cache=False)

            assert "options" in result
            assert isinstance(result["options"], list)

    @pytest.mark.asyncio
    async def test_fetch_option_chain_no_instruments(self):
        """Test option chain returns empty when no instruments found."""
        service = OptionChainService(kite=MagicMock(), db=MagicMock())
        expiry = date.today() + timedelta(days=7)

        with patch.object(service, '_get_from_cache', new_callable=AsyncMock) as mock_cache, \
             patch.object(service, '_fetch_instruments', new_callable=AsyncMock) as mock_fetch:

            mock_cache.return_value = None
            mock_fetch.return_value = []  # No instruments

            result = await service.get_option_chain("NIFTY", expiry, use_cache=True)

            assert result["underlying"] == "NIFTY"
            assert result["options"] == []
            assert result["spot_price"] is None

    @pytest.mark.asyncio
    async def test_calculate_greeks_called_when_ltp_available(self):
        """Test Greeks calculation is invoked when LTP is available."""
        service = OptionChainService(kite=MagicMock(), db=MagicMock())
        expiry = date.today() + timedelta(days=7)

        mock_instruments = [
            {'instrument_token': 12345, 'tradingsymbol': 'NIFTY24D2625000CE',
             'strike': 25000, 'instrument_type': 'CE'},
        ]

        with patch.object(service, '_fetch_instruments', new_callable=AsyncMock) as mock_fetch, \
             patch.object(service, '_get_spot_price', new_callable=AsyncMock) as mock_spot, \
             patch.object(service.market_data, 'get_ltp', new_callable=AsyncMock) as mock_ltp, \
             patch.object(service, '_get_quotes', new_callable=AsyncMock) as mock_quotes, \
             patch.object(service, '_calculate_greeks', new_callable=AsyncMock) as mock_greeks, \
             patch.object(service, '_save_to_cache', new_callable=AsyncMock):

            mock_fetch.return_value = mock_instruments
            mock_spot.return_value = Decimal('25250')
            mock_ltp.return_value = {'NFO:NIFTY24D2625000CE': Decimal('150')}
            mock_quotes.return_value = {}
            mock_greeks.return_value = {'delta': Decimal('0.15'), 'iv': Decimal('0.17')}

            await service.get_option_chain("NIFTY", expiry, use_cache=False)

            assert mock_greeks.called

    @pytest.mark.asyncio
    async def test_get_strikes_list(self):
        """Test getting list of available strikes."""
        service = OptionChainService(kite=MagicMock(), db=MagicMock())
        expiry = date.today() + timedelta(days=7)

        mock_instruments = [
            {'instrument_token': 1, 'tradingsymbol': 'NIFTY24D2625000CE', 'strike': 25000, 'instrument_type': 'CE'},
            {'instrument_token': 2, 'tradingsymbol': 'NIFTY24D2625000PE', 'strike': 25000, 'instrument_type': 'PE'},
            {'instrument_token': 3, 'tradingsymbol': 'NIFTY24D2625100CE', 'strike': 25100, 'instrument_type': 'CE'},
        ]

        with patch.object(service, '_fetch_instruments', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_instruments

            strikes = await service.get_strikes_list("NIFTY", expiry)

            assert isinstance(strikes, list)
            assert len(strikes) > 0
            assert Decimal('25000') in strikes
            assert Decimal('25100') in strikes

    @pytest.mark.asyncio
    async def test_error_handling_api_failure(self):
        """Test error handling when API fails."""
        service = OptionChainService(kite=MagicMock(), db=MagicMock())
        expiry = date.today() + timedelta(days=7)

        with patch.object(service, '_get_from_cache', new_callable=AsyncMock) as mock_cache, \
             patch.object(service, '_fetch_instruments', new_callable=AsyncMock) as mock_fetch:

            mock_cache.return_value = None
            mock_fetch.side_effect = Exception("API Error")

            with pytest.raises(Exception) as exc_info:
                await service.get_option_chain("NIFTY", expiry, use_cache=True)

            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cache_save_called_after_fetch(self):
        """Test cache is saved after fresh fetch when instruments exist."""
        service = OptionChainService(kite=MagicMock(), db=MagicMock())
        expiry = date.today() + timedelta(days=7)

        mock_instruments = [
            {'instrument_token': 1, 'tradingsymbol': 'NIFTY24D2625000CE',
             'strike': 25000, 'instrument_type': 'CE'},
        ]

        with patch.object(service, '_get_from_cache', new_callable=AsyncMock) as mock_get, \
             patch.object(service, '_fetch_instruments', new_callable=AsyncMock) as mock_fetch, \
             patch.object(service, '_get_spot_price', new_callable=AsyncMock) as mock_spot, \
             patch.object(service.market_data, 'get_ltp', new_callable=AsyncMock) as mock_ltp, \
             patch.object(service, '_get_quotes', new_callable=AsyncMock) as mock_quotes, \
             patch.object(service, '_save_to_cache', new_callable=AsyncMock) as mock_save:

            mock_get.return_value = None
            mock_fetch.return_value = mock_instruments
            mock_spot.return_value = Decimal('25250')
            mock_ltp.return_value = {'NFO:NIFTY24D2625000CE': Decimal('150')}
            mock_quotes.return_value = {}

            await service.get_option_chain("NIFTY", expiry, use_cache=True)

            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_option_chain_returns_correct_structure(self):
        """Test option chain response has required keys."""
        service = OptionChainService(kite=MagicMock(), db=MagicMock())
        expiry = date.today() + timedelta(days=7)

        with patch.object(service, '_get_from_cache', new_callable=AsyncMock) as mock_cache, \
             patch.object(service, '_fetch_instruments', new_callable=AsyncMock) as mock_fetch, \
             patch.object(service, '_get_spot_price', new_callable=AsyncMock) as mock_spot, \
             patch.object(service.market_data, 'get_ltp', new_callable=AsyncMock) as mock_ltp, \
             patch.object(service, '_get_quotes', new_callable=AsyncMock) as mock_quotes, \
             patch.object(service, '_save_to_cache', new_callable=AsyncMock):

            mock_cache.return_value = None
            mock_fetch.return_value = []
            mock_spot.return_value = Decimal('25250')
            mock_ltp.return_value = {}
            mock_quotes.return_value = {}

            result = await service.get_option_chain("NIFTY", expiry, use_cache=True)

            assert "underlying" in result
            assert "expiry" in result
            assert "spot_price" in result
            assert "options" in result
            assert "cached" in result
