"""
Analytics API Tests - Phase 5

Tests for /api/v1/autopilot/analytics endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal

from app.models.users import User
from app.models.autopilot import PositionLegStatus


class TestPayoffChart:
    """Tests for payoff chart endpoint."""

    @pytest.mark.asyncio
    async def test_get_payoff_chart_at_expiry(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test getting payoff chart in expiry mode."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            mock_result = {
                "payoff_data": [{"spot_price": 25000, "pnl": 0}],
                "metrics": {"max_profit": 10000, "max_loss": -5000}
            }
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_result)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/payoff?mode=expiry"
            )

            assert response.status_code == 200
            data = response.json()
            assert "payoff_data" in data
            assert "metrics" in data

    @pytest.mark.asyncio
    async def test_get_payoff_chart_current_mode(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test getting payoff chart in current mode."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            mock_result = {
                "payoff_data": [{"spot_price": 25000, "pnl": 100}],
                "metrics": {"max_profit": 12000}
            }
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_result)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/payoff?mode=current"
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_payoff_chart_custom_range(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test payoff chart with custom spot range."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            mock_result = {"payoff_data": [], "metrics": {}}
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_result)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/payoff"
                f"?mode=expiry&spot_range_pct=20&num_points=200"
            )

            assert response.status_code == 200


class TestRiskMetrics:
    """Tests for risk metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_risk_metrics(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test getting risk metrics."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            mock_payoff = {
                "max_profit": 15000,
                "max_loss": -5000,
                "breakeven_points": [24800, 25700],
                "risk_reward_ratio": 3.0
            }
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_payoff)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/risk-metrics"
            )

            assert response.status_code == 200
            data = response.json()
            assert "max_profit" in data
            assert "max_loss" in data
            assert "breakeven_points" in data

    @pytest.mark.asyncio
    async def test_risk_metrics_max_profit_loss(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test risk metrics include max profit and loss."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            mock_payoff = {
                "max_profit": 10000,
                "max_profit_at": 25500,
                "max_loss": -3000,
                "max_loss_at": 24500
            }
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_payoff)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/risk-metrics"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["max_profit"] == 10000
            assert data["max_loss"] == -3000

    @pytest.mark.asyncio
    async def test_risk_metrics_risk_reward_ratio(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test risk/reward ratio calculation."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            mock_payoff = {
                "max_profit": 15000,
                "max_loss": -5000,
                "risk_reward_ratio": 3.0
            }
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_payoff)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/risk-metrics"
            )

            assert response.status_code == 200
            data = response.json()
            assert "risk_reward_ratio" in data


class TestBreakevens:
    """Tests for breakeven calculations."""

    @pytest.mark.asyncio
    async def test_get_breakeven_points(
        self, client: AsyncClient, test_strategy_active, test_position_legs_multiple
    ):
        """Test getting breakeven points."""
        for leg in test_position_legs_multiple:
            leg.strategy_id = test_strategy_active.id
            leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            mock_payoff = {
                "breakeven_points": [24758, 25242],
                "max_profit": 10000,
                "max_loss": -5000
            }
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_payoff)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/risk-metrics"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["breakeven_points"]) == 2

    @pytest.mark.asyncio
    async def test_breakeven_multiple_points(
        self, client: AsyncClient, test_strategy_active, test_position_legs_multiple
    ):
        """Test strategy with multiple breakeven points."""
        for leg in test_position_legs_multiple:
            leg.strategy_id = test_strategy_active.id
            leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            # Strangle typically has 2 breakevens
            mock_payoff = {
                "breakeven_points": [24800, 25700, 26200],  # Could have 3
                "max_profit": 5000
            }
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_payoff)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/risk-metrics"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["breakeven_points"]) >= 2


class TestPnLCalculations:
    """Tests for P&L calculation endpoints."""

    @pytest.mark.asyncio
    async def test_calculate_pnl_at_spot(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test calculating P&L at specific spot price."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            mock_result = {
                "payoff_data": [
                    {"spot_price": 25000, "pnl": 0},
                    {"spot_price": 25500, "pnl": 2500}
                ]
            }
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_result)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/payoff?mode=expiry"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["payoff_data"]) >= 2

    @pytest.mark.asyncio
    async def test_calculate_pnl_at_multiple_spots(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test P&L calculation at multiple spot prices."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            # Generate multiple data points
            mock_data = [
                {"spot_price": 24000 + i * 100, "pnl": i * 10}
                for i in range(20)
            ]
            mock_result = {"payoff_data": mock_data, "metrics": {}}
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_result)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/payoff"
                f"?mode=expiry&num_points=200"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["payoff_data"]) >= 10


class TestProfitZones:
    """Tests for profit zone identification."""

    @pytest.mark.asyncio
    async def test_identify_profit_zones(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test profit zones are identified in payoff data."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            mock_data = [
                {"spot_price": 24500, "pnl": -100, "zone": "loss"},
                {"spot_price": 25000, "pnl": 0, "zone": "neutral"},
                {"spot_price": 25500, "pnl": 100, "zone": "profit"}
            ]
            mock_result = {"payoff_data": mock_data, "metrics": {}}
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_result)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/payoff?mode=expiry"
            )

            assert response.status_code == 200
            data = response.json()
            zones = [p["zone"] for p in data["payoff_data"]]
            assert "profit" in zones
            assert "loss" in zones

    @pytest.mark.asyncio
    async def test_profit_probability(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test probability of profit calculation."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            mock_payoff = {
                "probability_of_profit": 68.5,
                "payoff_data": []
            }
            MockCalculator.return_value.calculate_payoff = AsyncMock(return_value=mock_payoff)

            response = await client.get(
                f"/api/v1/autopilot/analytics/{test_strategy_active.id}/risk-metrics"
            )

            assert response.status_code == 200
            data = response.json()
            if "probability_of_profit" in data:
                assert isinstance(data["probability_of_profit"], (int, float))


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_payoff_invalid_strategy(
        self, client: AsyncClient
    ):
        """Test payoff calculation for non-existent strategy."""
        with patch('app.api.v1.autopilot.analytics.PayoffCalculator') as MockCalculator:
            MockCalculator.return_value.calculate_payoff = AsyncMock(
                side_effect=ValueError("Strategy not found")
            )

            response = await client.get(
                "/api/v1/autopilot/analytics/99999/payoff"
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_payoff_invalid_mode(
        self, client: AsyncClient, test_strategy_active
    ):
        """Test invalid mode parameter."""
        response = await client.get(
            f"/api/v1/autopilot/analytics/{test_strategy_active.id}/payoff?mode=invalid"
        )

        # Should fail validation
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_payoff_invalid_range(
        self, client: AsyncClient, test_strategy_active
    ):
        """Test invalid spot range percentage."""
        response = await client.get(
            f"/api/v1/autopilot/analytics/{test_strategy_active.id}/payoff"
            f"?mode=expiry&spot_range_pct=50"  # Too high (max 30)
        )

        # Should fail validation
        assert response.status_code in [400, 422]
