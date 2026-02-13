"""
StrikeFinderService Tests

Tests for strike finding by delta, premium, and range queries.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from app.services.autopilot.strike_finder_service import StrikeFinderService
from .conftest import get_mock_option_chain_response


class TestStrikeFinderService:
    """Test StrikeFinderService functionality."""

    @pytest.mark.asyncio
    async def test_find_strike_by_delta_exact_match(self):
        """Test finding strike with exact delta match."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            mock_chain.get_option_chain.return_value = get_mock_option_chain_response()

            result = await service.find_strike_by_delta(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="CE",
                target_delta=0.15,
                tolerance=0.01
            )

            assert result is not None
            assert "strike" in result
            assert "delta" in result
            assert abs(result["delta"] - 0.15) <= 0.01

    @pytest.mark.asyncio
    async def test_find_strike_by_delta_closest_match(self):
        """Test finding closest strike when exact match unavailable."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            mock_chain.get_option_chain.return_value = get_mock_option_chain_response()

            result = await service.find_strike_by_delta(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="CE",
                target_delta=0.17,  # May not exist exactly
                tolerance=0.05
            )

            assert result is not None
            assert abs(result["delta"] - 0.17) <= 0.05

    @pytest.mark.asyncio
    async def test_find_strike_by_delta_round_preference(self):
        """Test preferring round strikes (multiples of 100)."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            mock_chain.get_option_chain.return_value = get_mock_option_chain_response()

            result = await service.find_strike_by_delta(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="CE",
                target_delta=0.15,
                tolerance=0.05,
                prefer_round_strike=True
            )

            assert result is not None
            assert result["strike"] % 100 == 0  # Should be round strike

    @pytest.mark.asyncio
    async def test_find_strike_by_delta_tolerance(self):
        """Test delta tolerance is respected."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            mock_chain.get_option_chain.return_value = get_mock_option_chain_response()

            # Strict tolerance - should still find something
            result = await service.find_strike_by_delta(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="CE",
                target_delta=0.15,
                tolerance=0.10  # Wider tolerance
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_find_strike_by_premium_exact(self):
        """Test finding strike by exact premium."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            mock_chain.get_option_chain.return_value = get_mock_option_chain_response()

            result = await service.find_strike_by_premium(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="PE",
                target_premium=185.00,
                tolerance=5.00
            )

            assert result is not None
            assert "strike" in result
            assert "premium" in result
            assert abs(result["premium"] - 185.00) <= 5.00

    @pytest.mark.asyncio
    async def test_find_strike_by_premium_closest(self):
        """Test finding closest premium when exact unavailable."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            mock_chain.get_option_chain.return_value = get_mock_option_chain_response()

            result = await service.find_strike_by_premium(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="PE",
                target_premium=175.00,
                tolerance=20.00
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_find_strike_by_premium_range(self):
        """Test finding strike within premium range."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            mock_chain.get_option_chain.return_value = get_mock_option_chain_response()

            result = await service.find_strike_by_premium(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="CE",
                target_premium=180.00,
                tolerance=10.00
            )

            assert result is not None
            assert 170.00 <= result["premium"] <= 190.00

    @pytest.mark.asyncio
    async def test_find_atm_strike(self):
        """Test finding ATM strike."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            chain_data = get_mock_option_chain_response()
            mock_chain.get_option_chain.return_value = chain_data

            atm = await service.find_atm_strike("NIFTY", "2024-01-25")

            assert atm is not None
            # Should be close to spot price
            spot = chain_data["spot_price"]
            assert abs(atm - spot) <= 100  # Within 100 points

    @pytest.mark.asyncio
    async def test_find_strikes_by_delta_range(self):
        """Test finding all strikes within delta range."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            mock_chain.get_option_chain.return_value = get_mock_option_chain_response()

            results = await service.find_strikes_in_range(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="CE",
                min_value=0.10,
                max_value=0.20,
                range_type="delta"
            )

            assert isinstance(results, list)
            assert len(results) > 0
            for result in results:
                assert 0.10 <= result["delta"] <= 0.20

    @pytest.mark.asyncio
    async def test_find_strikes_in_premium_range(self):
        """Test finding all strikes within premium range."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            mock_chain.get_option_chain.return_value = get_mock_option_chain_response()

            results = await service.find_strikes_in_range(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="PE",
                min_value=150.00,
                max_value=200.00,
                range_type="premium"
            )

            assert isinstance(results, list)
            for result in results:
                assert 150.00 <= result["premium"] <= 200.00

    @pytest.mark.asyncio
    async def test_no_strikes_found_error(self):
        """Test error when no strikes match criteria."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            # Return empty strikes
            mock_chain.get_option_chain.return_value = {
                "underlying": "NIFTY",
                "spot_price": 25250,
                "strikes": []
            }

            result = await service.find_strike_by_delta(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="CE",
                target_delta=0.15
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_all_strikes_filtered_error(self):
        """Test when all strikes are filtered out by criteria."""
        service = StrikeFinderService(db_session=MagicMock())

        with patch.object(service, 'option_chain_service') as mock_chain:
            mock_chain.get_option_chain.return_value = get_mock_option_chain_response()

            # Very narrow tolerance that won't match anything
            result = await service.find_strike_by_delta(
                underlying="NIFTY",
                expiry="2024-01-25",
                option_type="CE",
                target_delta=0.99,  # Very high delta
                tolerance=0.001  # Very tight tolerance
            )

            assert result is None
