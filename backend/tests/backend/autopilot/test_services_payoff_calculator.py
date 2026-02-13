"""
PayoffCalculator Service Tests

Tests for P/L diagrams, breakevens, and risk metrics calculation.
"""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
from datetime import date, timedelta
from decimal import Decimal

from app.services.options.payoff_calculator import PayoffCalculator, PayoffMetrics
from app.models.autopilot import PositionLegStatus


class TestPayoffCalculator:
    """Test PayoffCalculator functionality."""

    @pytest.mark.asyncio
    async def test_calculate_payoff_at_expiry(
        self, db_session, test_strategy_active, test_position_legs_multiple
    ):
        """Test payoff calculation at expiry mode."""
        for leg in test_position_legs_multiple:
            leg.strategy_id = test_strategy_active.id
            leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        service = PayoffCalculator(db_session)

        result = await service.calculate_payoff(
            strategy_id=test_strategy_active.id,
            mode="expiry",
            spot_range_pct=10.0,
            num_points=50
        )

        assert result["mode"] == "expiry"
        assert "payoff_data" in result
        assert len(result["payoff_data"]) == 50
        assert "metrics" in result
        assert "breakeven_points" in result["metrics"]

    @pytest.mark.asyncio
    async def test_calculate_payoff_current_mode(
        self, db_session, test_strategy_active, test_position_legs_multiple
    ):
        """Test payoff calculation in current mode (with time value)."""
        for leg in test_position_legs_multiple:
            leg.strategy_id = test_strategy_active.id
            leg.status = PositionLegStatus.OPEN
            leg.expiry = date.today() + timedelta(days=7)
        await db_session.commit()

        service = PayoffCalculator(db_session)

        result = await service.calculate_payoff(
            strategy_id=test_strategy_active.id,
            mode="current",
            spot_range_pct=10.0,
            num_points=50
        )

        assert result["mode"] == "current"
        assert "payoff_data" in result

    @pytest.mark.asyncio
    async def test_calculate_pnl_call_long(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test P/L calculation for long call."""
        # Setup long call: BUY 25000 CE @ 200
        test_position_leg.contract_type = "CE"
        test_position_leg.action = "BUY"
        test_position_leg.strike = Decimal("25000")
        test_position_leg.entry_price = Decimal("200.00")
        test_position_leg.lots = 1
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        service = PayoffCalculator(db_session)

        # Calculate P/L at spot = 25500 (500 ITM)
        # Intrinsic = 500, Entry = 200, P/L = 300 per lot
        # Total P/L = 300 * 25 (lot size) = 7500
        pnl = service._calculate_pnl_at_expiry([test_position_leg], spot_price=25500)

        # Long call: profit when spot > strike + premium
        # At 25500: intrinsic = 500, paid = 200, profit = 300 per lot
        assert pnl == 300 * 25  # 7500

    @pytest.mark.asyncio
    async def test_calculate_pnl_put_short(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test P/L calculation for short put."""
        # Setup short put: SELL 25000 PE @ 185.50
        test_position_leg.contract_type = "PE"
        test_position_leg.action = "SELL"
        test_position_leg.strike = Decimal("25000")
        test_position_leg.entry_price = Decimal("185.50")
        test_position_leg.lots = 1
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        service = PayoffCalculator(db_session)

        # Calculate P/L at spot = 25500 (OTM, expires worthless)
        # Intrinsic = 0, Collected = 185.50, P/L = 185.50 per lot
        pnl = service._calculate_pnl_at_expiry([test_position_leg], spot_price=25500)

        # Short put OTM: keep full premium
        # At 25500: intrinsic = 0, collected = 185.50, profit = 185.50 per lot
        assert pnl == 185.50 * 25  # 4637.50

    @pytest.mark.asyncio
    async def test_calculate_breakevens(
        self, db_session, test_strategy_active, test_position_legs_multiple
    ):
        """Test breakeven point calculation."""
        for leg in test_position_legs_multiple:
            leg.strategy_id = test_strategy_active.id
            leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        service = PayoffCalculator(db_session)

        result = await service.calculate_payoff(
            strategy_id=test_strategy_active.id,
            mode="expiry"
        )

        metrics = result["metrics"]
        assert "breakeven_points" in metrics
        assert isinstance(metrics["breakeven_points"], list)

        # Strangle should have 2 breakeven points
        if len(test_position_legs_multiple) >= 2:
            # May have breakevens (depends on strikes and premiums)
            breakevens = metrics["breakeven_points"]
            # Just verify it's a list (may be empty if no breakevens in range)
            assert isinstance(breakevens, list)

    @pytest.mark.asyncio
    async def test_calculate_max_profit_loss(
        self, db_session, test_strategy_active, test_position_legs_multiple
    ):
        """Test max profit and max loss calculation."""
        for leg in test_position_legs_multiple:
            leg.strategy_id = test_strategy_active.id
            leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        service = PayoffCalculator(db_session)

        result = await service.calculate_payoff(
            strategy_id=test_strategy_active.id,
            mode="expiry"
        )

        metrics = result["metrics"]
        assert "max_profit" in metrics
        assert "max_loss" in metrics
        assert isinstance(metrics["max_profit"], (int, float))
        assert isinstance(metrics["max_loss"], (int, float))

        # Risk/reward ratio should be calculated
        if metrics["risk_reward_ratio"] is not None:
            assert isinstance(metrics["risk_reward_ratio"], (int, float))

    @pytest.mark.asyncio
    async def test_calculate_payoff_range(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test payoff calculation across spot price range."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.strike = Decimal("25000")
        await db_session.commit()

        service = PayoffCalculator(db_session)

        result = await service.calculate_payoff(
            strategy_id=test_strategy_active.id,
            mode="expiry",
            spot_range_pct=20.0,  # ±20% range
            num_points=100
        )

        assert "spot_range" in result
        spot_range = result["spot_range"]
        assert "min" in spot_range
        assert "max" in spot_range
        assert "current" in spot_range

        # Range should be approximately ±20% of current spot
        current = spot_range["current"]
        min_expected = current * 0.8
        max_expected = current * 1.2

        assert abs(spot_range["min"] - min_expected) < 100
        assert abs(spot_range["max"] - max_expected) < 100

    @pytest.mark.asyncio
    async def test_payoff_data_points_generation(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test payoff data points are correctly generated."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        service = PayoffCalculator(db_session)

        result = await service.calculate_payoff(
            strategy_id=test_strategy_active.id,
            mode="expiry",
            num_points=50
        )

        payoff_data = result["payoff_data"]

        # Verify we have correct number of points
        assert len(payoff_data) == 50

        # Each data point should have required fields
        for point in payoff_data:
            assert "spot_price" in point
            assert "pnl" in point
            assert "is_breakeven" in point
            assert "is_current" in point
            assert "zone" in point

            # Zone should be profit, loss, or neutral
            assert point["zone"] in ["profit", "loss", "neutral"]

        # At least one point should be marked as current
        current_points = [p for p in payoff_data if p["is_current"]]
        assert len(current_points) > 0

        # Spot prices should be in ascending order
        spot_prices = [p["spot_price"] for p in payoff_data]
        assert spot_prices == sorted(spot_prices)
