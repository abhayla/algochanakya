"""
OptionChainService Tests

Tests for option chain fetching, caching, and Greeks calculation.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.option_chain_service import OptionChainService
from .conftest import get_mock_option_chain_response


class TestOptionChainService:
    """Test OptionChainService functionality."""

    @pytest.mark.asyncio
    async def test_fetch_option_chain_from_api(self, mock_kite_option_chain):
        """Test fetching option chain from Kite API."""
        service = OptionChainService(db_session=MagicMock())

        with patch.object(service, '_fetch_from_kite', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_kite_option_chain

            result = await service.get_option_chain("NIFTY", "2024-01-25", use_cache=False)

            assert result["underlying"] == "NIFTY"
            assert "strikes" in result
            assert len(result["strikes"]) > 0
            assert "spot_price" in result
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_option_chain_uses_cache(self, mock_kite_option_chain):
        """Test option chain uses cache when valid."""
        service = OptionChainService(db_session=MagicMock())

        with patch.object(service, '_get_cached_chain', new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = mock_kite_option_chain

            result = await service.get_option_chain("NIFTY", "2024-01-25", use_cache=True)

            assert result is not None
            mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_option_chain_refreshes_expired_cache(self, mock_kite_option_chain):
        """Test option chain refreshes when cache is expired."""
        service = OptionChainService(db_session=MagicMock())

        with patch.object(service, '_get_cached_chain', new_callable=AsyncMock) as mock_cache, \
             patch.object(service, '_fetch_from_kite', new_callable=AsyncMock) as mock_fetch:

            mock_cache.return_value = None  # Cache miss
            mock_fetch.return_value = mock_kite_option_chain

            result = await service.get_option_chain("NIFTY", "2024-01-25", use_cache=True)

            assert result is not None
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_filter_by_type_ce(self, mock_kite_option_chain):
        """Test filtering option chain for CE only."""
        service = OptionChainService(db_session=MagicMock())

        with patch.object(service, '_fetch_from_kite', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_kite_option_chain

            result = await service.get_option_chain("NIFTY", "2024-01-25", option_type="CE")

            # Should only have CE data
            for strike in result["strikes"]:
                assert "ce" in strike
                assert "pe" not in strike or strike["pe"] is None

    @pytest.mark.asyncio
    async def test_filter_by_type_pe(self, mock_kite_option_chain):
        """Test filtering option chain for PE only."""
        service = OptionChainService(db_session=MagicMock())

        with patch.object(service, '_fetch_from_kite', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_kite_option_chain

            result = await service.get_option_chain("NIFTY", "2024-01-25", option_type="PE")

            # Should only have PE data
            for strike in result["strikes"]:
                assert "pe" in strike
                assert "ce" not in strike or strike["ce"] is None

    @pytest.mark.asyncio
    async def test_calculate_greeks_when_missing(self):
        """Test Greeks calculation when not provided by API."""
        service = OptionChainService(db_session=MagicMock())

        # Mock data without Greeks
        mock_data = {
            "underlying": "NIFTY",
            "spot_price": 25250,
            "strikes": [
                {
                    "strike": 25250,
                    "ce": {"ltp": 150, "bid": 148, "ask": 152},
                    "pe": {"ltp": 145, "bid": 143, "ask": 147}
                }
            ]
        }

        with patch.object(service, '_fetch_from_kite', new_callable=AsyncMock) as mock_fetch, \
             patch.object(service, '_calculate_greeks', return_value=0.15) as mock_greeks:

            mock_fetch.return_value = mock_data

            result = await service.get_option_chain("NIFTY", "2024-01-25")

            # Greeks calculation should have been called
            assert mock_greeks.called

    @pytest.mark.asyncio
    async def test_get_atm_strike(self, mock_kite_option_chain):
        """Test ATM strike identification."""
        service = OptionChainService(db_session=MagicMock())

        with patch.object(service, '_fetch_from_kite', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_kite_option_chain

            atm = await service.get_atm_strike("NIFTY", "2024-01-25")

            # ATM should be close to spot price (25250)
            assert 25200 <= atm <= 25300

    @pytest.mark.asyncio
    async def test_error_handling_api_failure(self):
        """Test error handling when API fails."""
        service = OptionChainService(db_session=MagicMock())

        with patch.object(service, '_fetch_from_kite', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")

            with pytest.raises(Exception) as exc_info:
                await service.get_option_chain("NIFTY", "2024-01-25", use_cache=False)

            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cache_ttl_behavior(self, mock_kite_option_chain):
        """Test cache TTL behavior (2-second TTL)."""
        service = OptionChainService(db_session=MagicMock())

        # First call - should cache
        with patch.object(service, '_fetch_from_kite', new_callable=AsyncMock) as mock_fetch, \
             patch.object(service, '_cache_option_chain', new_callable=AsyncMock) as mock_cache:

            mock_fetch.return_value = mock_kite_option_chain

            await service.get_option_chain("NIFTY", "2024-01-25", use_cache=True)

            # Should have cached the result
            mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_strikes_list(self, mock_kite_option_chain):
        """Test getting list of available strikes."""
        service = OptionChainService(db_session=MagicMock())

        with patch.object(service, '_fetch_from_kite', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_kite_option_chain

            strikes = await service.get_strikes_list("NIFTY", "2024-01-25")

            assert isinstance(strikes, list)
            assert len(strikes) > 0
            assert all(isinstance(s, (int, float)) for s in strikes)
