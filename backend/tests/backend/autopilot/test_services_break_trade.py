"""
BreakTradeService Tests

Tests for break/split trade algorithm and execution.
"""

import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from app.services.break_trade_service import BreakTradeService
from app.models.autopilot import PositionLegStatus


class TestBreakTradeService:
    """Test BreakTradeService functionality."""

    @pytest.mark.asyncio
    async def test_calculate_exit_cost(self, db_session, test_break_trade_scenario):
        """Test exit cost calculation."""
        service = BreakTradeService(db_session)
        strategy, losing_leg = test_break_trade_scenario

        cost = service.calculate_exit_cost(losing_leg.entry_price, Decimal("320.00"), losing_leg.quantity)

        # SELL PE: exit at higher price = loss = (320 - 180) * 25 = 3500
        assert cost == Decimal("3500.00")

    @pytest.mark.asyncio
    async def test_calculate_recovery_premiums_equal_split(self, db_session):
        """Test equal split recovery premium calculation."""
        service = BreakTradeService(db_session)

        premiums = service.calculate_recovery_premiums(Decimal("140.00"), split_mode="equal")

        assert premiums["put_premium"] == Decimal("70.00")
        assert premiums["call_premium"] == Decimal("70.00")

    @pytest.mark.asyncio
    async def test_calculate_recovery_premiums_weighted(self, db_session):
        """Test weighted split recovery premium."""
        service = BreakTradeService(db_session)

        premiums = service.calculate_recovery_premiums(Decimal("140.00"), split_mode="weighted", weights={"put": 0.6, "call": 0.4})

        assert premiums["put_premium"] == Decimal("84.00")
        assert premiums["call_premium"] == Decimal("56.00")

    @pytest.mark.asyncio
    async def test_find_new_strikes_by_premium(self, db_session):
        """Test finding new strikes by target premium."""
        service = BreakTradeService(db_session)

        with patch.object(service, 'strike_finder') as mock_finder:
            mock_finder.find_strike_by_premium.side_effect = [
                {"strike": 24800, "premium": 70.00},
                {"strike": 25700, "premium": 70.00}
            ]

            strikes = await service.find_new_strikes(
                underlying="NIFTY",
                expiry="2024-01-25",
                put_premium=Decimal("70.00"),
                call_premium=Decimal("70.00")
            )

            assert strikes["put_strike"] == 24800
            assert strikes["call_strike"] == 25700

    @pytest.mark.asyncio
    async def test_find_new_strikes_round_preference(self, db_session):
        """Test round strike preference."""
        service = BreakTradeService(db_session)

        with patch.object(service, 'strike_finder') as mock_finder:
            mock_finder.find_strike_by_premium.side_effect = [
                {"strike": 24800, "premium": 70.00},
                {"strike": 25700, "premium": 70.00}
            ]

            strikes = await service.find_new_strikes(
                underlying="NIFTY",
                expiry="2024-01-25",
                put_premium=Decimal("70.00"),
                call_premium=Decimal("70.00"),
                prefer_round_strikes=True
            )

            assert strikes["put_strike"] % 100 == 0
            assert strikes["call_strike"] % 100 == 0

    @pytest.mark.asyncio
    async def test_execute_break_trade_full_flow(self, db_session, test_break_trade_scenario):
        """Test full break trade execution flow."""
        service = BreakTradeService(db_session)
        strategy, losing_leg = test_break_trade_scenario

        with patch.object(service, 'order_executor') as mock_executor:
            mock_executor.execute_orders.return_value = {"status": "success"}

            result = await service.execute_break_trade(
                strategy_id=strategy.id,
                leg_id=losing_leg.id,
                execution_mode="market"
            )

            assert result["status"] == "success"
            assert "new_legs" in result
            assert len(result["new_legs"]) == 2

    @pytest.mark.asyncio
    async def test_execute_break_trade_partial_failure_rollback(self, db_session, test_break_trade_scenario):
        """Test rollback on partial failure."""
        service = BreakTradeService(db_session)
        strategy, losing_leg = test_break_trade_scenario

        with patch.object(service, 'order_executor') as mock_executor:
            mock_executor.execute_orders.side_effect = Exception("Second leg failed")

            with pytest.raises(Exception):
                await service.execute_break_trade(strategy.id, losing_leg.id)

            # Verify rollback - original leg still open
            await db_session.refresh(losing_leg)
            assert losing_leg.status == PositionLegStatus.OPEN

    @pytest.mark.asyncio
    async def test_execute_break_trade_dry_run(self, db_session, test_break_trade_scenario):
        """Test dry run mode."""
        service = BreakTradeService(db_session)
        strategy, losing_leg = test_break_trade_scenario

        result = await service.execute_break_trade(
            strategy_id=strategy.id,
            leg_id=losing_leg.id,
            execution_mode="dry_run"
        )

        assert "preview" in result or "exit_cost" in result
        # No actual changes
        await db_session.refresh(losing_leg)
        assert losing_leg.status == PositionLegStatus.OPEN

    @pytest.mark.asyncio
    async def test_validate_invalid_leg_rejected(self, db_session, test_strategy_active):
        """Test validation rejects invalid leg."""
        service = BreakTradeService(db_session)

        with pytest.raises(Exception):
            await service.execute_break_trade(test_strategy_active.id, 99999)

    @pytest.mark.asyncio
    async def test_validate_closed_leg_rejected(self, db_session, test_position_leg):
        """Test validation rejects closed leg."""
        service = BreakTradeService(db_session)

        test_position_leg.status = PositionLegStatus.CLOSED
        await db_session.commit()

        with pytest.raises(Exception):
            await service.execute_break_trade(test_position_leg.strategy_id, test_position_leg.id)
