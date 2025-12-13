"""
Option Chain API Tests

Tests for /api/v1/autopilot/option-chain endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.models.users import User
from .conftest import get_mock_option_chain_response, assert_option_chain_response


# =============================================================================
# GET OPTION CHAIN TESTS
# =============================================================================

class TestGetOptionChain:
    """Tests for GET /api/v1/autopilot/option-chain/{underlying}/{expiry}."""

    @pytest.mark.asyncio
    async def test_get_option_chain_full(self, client: AsyncClient, test_user: User):
        """Test getting full option chain."""
        with patch('app.services.option_chain_service.OptionChainService.get_option_chain', new_callable=AsyncMock) as mock:
            mock.return_value = get_mock_option_chain_response()

            response = await client.get("/api/v1/autopilot/option-chain/NIFTY/2024-01-25")

            assert response.status_code == 200
            data = response.json()
            assert_option_chain_response(data)

    @pytest.mark.asyncio
    async def test_get_option_chain_filter_ce_only(self, client: AsyncClient, test_user: User):
        """Test filtering option chain for CE only."""
        with patch('app.services.option_chain_service.OptionChainService.get_option_chain', new_callable=AsyncMock) as mock:
            mock_data = get_mock_option_chain_response()
            # Filter to CE only
            for strike in mock_data["strikes"]:
                strike.pop("pe", None)
            mock.return_value = mock_data

            response = await client.get("/api/v1/autopilot/option-chain/NIFTY/2024-01-25?option_type=CE")

            assert response.status_code == 200
            data = response.json()
            for strike in data["strikes"]:
                assert "ce" in strike

    @pytest.mark.asyncio
    async def test_get_option_chain_filter_pe_only(self, client: AsyncClient, test_user: User):
        """Test filtering option chain for PE only."""
        with patch('app.services.option_chain_service.OptionChainService.get_option_chain', new_callable=AsyncMock) as mock:
            mock_data = get_mock_option_chain_response()
            # Filter to PE only
            for strike in mock_data["strikes"]:
                strike.pop("ce", None)
            mock.return_value = mock_data

            response = await client.get("/api/v1/autopilot/option-chain/NIFTY/2024-01-25?option_type=PE")

            assert response.status_code == 200
            data = response.json()
            for strike in data["strikes"]:
                assert "pe" in strike

    @pytest.mark.asyncio
    async def test_get_option_chain_cache_hit(self, client: AsyncClient, test_user: User):
        """Test option chain returns cached data."""
        with patch('app.services.option_chain_service.OptionChainService.get_option_chain', new_callable=AsyncMock) as mock:
            mock.return_value = get_mock_option_chain_response()

            response = await client.get("/api/v1/autopilot/option-chain/NIFTY/2024-01-25?use_cache=true")

            assert response.status_code == 200
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_option_chain_cache_miss_refresh(self, client: AsyncClient, test_user: User):
        """Test option chain refreshes when cache disabled."""
        with patch('app.services.option_chain_service.OptionChainService.get_option_chain', new_callable=AsyncMock) as mock:
            mock.return_value = get_mock_option_chain_response()

            response = await client.get("/api/v1/autopilot/option-chain/NIFTY/2024-01-25?use_cache=false")

            assert response.status_code == 200
            mock.assert_called_with("NIFTY", "2024-01-25", use_cache=False, option_type=None)

    @pytest.mark.asyncio
    async def test_get_option_chain_invalid_underlying(self, client: AsyncClient, test_user: User):
        """Test invalid underlying is rejected."""
        response = await client.get("/api/v1/autopilot/option-chain/INVALID/2024-01-25")

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_get_option_chain_invalid_expiry_format(self, client: AsyncClient, test_user: User):
        """Test invalid expiry format is rejected."""
        response = await client.get("/api/v1/autopilot/option-chain/NIFTY/invalid-date")

        assert response.status_code in [400, 422]


# =============================================================================
# GET STRIKES LIST TESTS
# =============================================================================

class TestGetStrikes:
    """Tests for GET /api/v1/autopilot/option-chain/{underlying}/{expiry}/strikes."""

    @pytest.mark.asyncio
    async def test_get_strikes_list(self, client: AsyncClient, test_user: User):
        """Test getting list of strikes."""
        with patch('app.services.option_chain_service.OptionChainService.get_strikes_list', new_callable=AsyncMock) as mock:
            mock.return_value = [25000, 25050, 25100, 25150, 25200, 25250]

            response = await client.get("/api/v1/autopilot/option-chain/NIFTY/2024-01-25/strikes")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

    @pytest.mark.asyncio
    async def test_get_strikes_empty_for_invalid_expiry(self, client: AsyncClient, test_user: User):
        """Test empty strikes list for invalid expiry."""
        with patch('app.services.option_chain_service.OptionChainService.get_strikes_list', new_callable=AsyncMock) as mock:
            mock.return_value = []

            response = await client.get("/api/v1/autopilot/option-chain/NIFTY/2024-12-31/strikes")

            assert response.status_code == 200
            data = response.json()
            assert data == []


# =============================================================================
# FIND BY DELTA TESTS
# =============================================================================

class TestFindByDelta:
    """Tests for POST /api/v1/autopilot/option-chain/find-by-delta."""

    @pytest.mark.asyncio
    async def test_find_strike_by_delta_exact(self, client: AsyncClient, test_user: User):
        """Test finding strike by exact delta."""
        with patch('app.services.strike_finder_service.StrikeFinderService.find_strike_by_delta', new_callable=AsyncMock) as mock:
            mock.return_value = {"strike": 25000, "delta": 0.15, "premium": 185.00}

            payload = {
                "underlying": "NIFTY",
                "expiry": "2024-01-25",
                "option_type": "CE",
                "target_delta": 0.15
            }

            response = await client.post("/api/v1/autopilot/option-chain/find-by-delta", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["strike"] == 25000
            assert "delta" in data

    @pytest.mark.asyncio
    async def test_find_strike_by_delta_closest(self, client: AsyncClient, test_user: User):
        """Test finding closest strike when exact match not found."""
        with patch('app.services.strike_finder_service.StrikeFinderService.find_strike_by_delta', new_callable=AsyncMock) as mock:
            mock.return_value = {"strike": 25050, "delta": 0.16, "premium": 175.00}

            payload = {
                "underlying": "NIFTY",
                "expiry": "2024-01-25",
                "option_type": "CE",
                "target_delta": 0.15,
                "tolerance": 0.05
            }

            response = await client.post("/api/v1/autopilot/option-chain/find-by-delta", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert "strike" in data

    @pytest.mark.asyncio
    async def test_find_strike_by_delta_prefer_round(self, client: AsyncClient, test_user: User):
        """Test preferring round strikes."""
        with patch('app.services.strike_finder_service.StrikeFinderService.find_strike_by_delta', new_callable=AsyncMock) as mock:
            mock.return_value = {"strike": 25000, "delta": 0.15, "premium": 185.00}  # Round strike

            payload = {
                "underlying": "NIFTY",
                "expiry": "2024-01-25",
                "option_type": "CE",
                "target_delta": 0.15,
                "prefer_round_strike": True
            }

            response = await client.post("/api/v1/autopilot/option-chain/find-by-delta", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["strike"] % 100 == 0  # Should be round strike

    @pytest.mark.asyncio
    async def test_find_strike_by_delta_invalid_delta_rejected(self, client: AsyncClient, test_user: User):
        """Test invalid delta value is rejected."""
        payload = {
            "underlying": "NIFTY",
            "expiry": "2024-01-25",
            "option_type": "CE",
            "target_delta": 1.5  # Invalid: > 1.0
        }

        response = await client.post("/api/v1/autopilot/option-chain/find-by-delta", json=payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_find_strike_by_delta_no_match(self, client: AsyncClient, test_user: User):
        """Test no match found within tolerance."""
        with patch('app.services.strike_finder_service.StrikeFinderService.find_strike_by_delta', new_callable=AsyncMock) as mock:
            mock.return_value = None

            payload = {
                "underlying": "NIFTY",
                "expiry": "2024-01-25",
                "option_type": "CE",
                "target_delta": 0.15,
                "tolerance": 0.01
            }

            response = await client.post("/api/v1/autopilot/option-chain/find-by-delta", json=payload)

            assert response.status_code == 404


# =============================================================================
# FIND BY PREMIUM TESTS
# =============================================================================

class TestFindByPremium:
    """Tests for POST /api/v1/autopilot/option-chain/find-by-premium."""

    @pytest.mark.asyncio
    async def test_find_strike_by_premium_exact(self, client: AsyncClient, test_user: User):
        """Test finding strike by exact premium."""
        with patch('app.services.strike_finder_service.StrikeFinderService.find_strike_by_premium', new_callable=AsyncMock) as mock:
            mock.return_value = {"strike": 25000, "premium": 185.00, "delta": 0.15}

            payload = {
                "underlying": "NIFTY",
                "expiry": "2024-01-25",
                "option_type": "PE",
                "target_premium": 185.00
            }

            response = await client.post("/api/v1/autopilot/option-chain/find-by-premium", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["strike"] == 25000

    @pytest.mark.asyncio
    async def test_find_strike_by_premium_range(self, client: AsyncClient, test_user: User):
        """Test finding strike within premium range."""
        with patch('app.services.strike_finder_service.StrikeFinderService.find_strike_by_premium', new_callable=AsyncMock) as mock:
            mock.return_value = {"strike": 25050, "premium": 182.00, "delta": 0.16}

            payload = {
                "underlying": "NIFTY",
                "expiry": "2024-01-25",
                "option_type": "PE",
                "target_premium": 185.00,
                "tolerance": 10.00
            }

            response = await client.post("/api/v1/autopilot/option-chain/find-by-premium", json=payload)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_find_strike_by_premium_prefer_round(self, client: AsyncClient, test_user: User):
        """Test preferring round strikes when finding by premium."""
        with patch('app.services.strike_finder_service.StrikeFinderService.find_strike_by_premium', new_callable=AsyncMock) as mock:
            mock.return_value = {"strike": 25100, "premium": 185.00, "delta": 0.15}

            payload = {
                "underlying": "NIFTY",
                "expiry": "2024-01-25",
                "option_type": "PE",
                "target_premium": 185.00,
                "prefer_round_strike": True
            }

            response = await client.post("/api/v1/autopilot/option-chain/find-by-premium", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["strike"] % 100 == 0


# =============================================================================
# FIND ATM TESTS
# =============================================================================

class TestFindATM:
    """Tests for GET /api/v1/autopilot/option-chain/find-atm/{underlying}/{expiry}."""

    @pytest.mark.asyncio
    async def test_find_atm_strike(self, client: AsyncClient, test_user: User):
        """Test finding ATM strike."""
        with patch('app.services.option_chain_service.OptionChainService.get_atm_strike', new_callable=AsyncMock) as mock:
            mock.return_value = 25250

            response = await client.get("/api/v1/autopilot/option-chain/find-atm/NIFTY/2024-01-25")

            assert response.status_code == 200
            data = response.json()
            assert data["atm_strike"] == 25250


# =============================================================================
# FIND IN RANGE TESTS
# =============================================================================

class TestFindInRange:
    """Tests for GET /api/v1/autopilot/option-chain/strikes-in-range/{underlying}/{expiry}."""

    @pytest.mark.asyncio
    async def test_find_strikes_in_delta_range(self, client: AsyncClient, test_user: User):
        """Test finding strikes in delta range."""
        with patch('app.services.strike_finder_service.StrikeFinderService.find_strikes_in_range', new_callable=AsyncMock) as mock:
            mock.return_value = [
                {"strike": 25000, "delta": 0.15},
                {"strike": 25050, "delta": 0.18},
                {"strike": 25100, "delta": 0.20}
            ]

            response = await client.get(
                "/api/v1/autopilot/option-chain/strikes-in-range/NIFTY/2024-01-25"
                "?option_type=CE&range_type=delta&min_value=0.15&max_value=0.20"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3

    @pytest.mark.asyncio
    async def test_find_strikes_in_premium_range(self, client: AsyncClient, test_user: User):
        """Test finding strikes in premium range."""
        with patch('app.services.strike_finder_service.StrikeFinderService.find_strikes_in_range', new_callable=AsyncMock) as mock:
            mock.return_value = [
                {"strike": 25000, "premium": 180.00},
                {"strike": 25050, "premium": 185.00},
                {"strike": 25100, "premium": 190.00}
            ]

            response = await client.get(
                "/api/v1/autopilot/option-chain/strikes-in-range/NIFTY/2024-01-25"
                "?option_type=PE&range_type=premium&min_value=180&max_value=190"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3


# =============================================================================
# GET EXPIRIES TESTS
# =============================================================================

class TestGetExpiries:
    """Tests for GET /api/v1/autopilot/option-chain/expiries/{underlying}."""

    @pytest.mark.asyncio
    async def test_get_expiries_list(self, client: AsyncClient, test_user: User):
        """Test getting list of available expiries."""
        with patch('app.services.option_chain_service.OptionChainService.get_expiries', new_callable=AsyncMock) as mock:
            mock.return_value = ["2024-01-18", "2024-01-25", "2024-02-01", "2024-02-29"]

            response = await client.get("/api/v1/autopilot/option-chain/expiries/NIFTY")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 4
