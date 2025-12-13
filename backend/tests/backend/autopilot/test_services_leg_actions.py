"""
LegActionsService Tests

Tests for exit, shift, and roll leg operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import date, timedelta

from app.services.leg_actions_service import LegActionsService
from app.models.autopilot import PositionLegStatus


class TestLegActionsService:
    """Test LegActionsService functionality."""

    @pytest.mark.asyncio
    async def test_exit_leg_market(self, db_session, test_position_leg):
        """Test exiting leg with market order."""
        service = LegActionsService(db_session)

        with patch.object(service, 'order_executor') as mock_executor:
            mock_executor.execute_exit.return_value = {"status": "success", "price": Decimal("120.00")}

            result = await service.exit_leg(test_position_leg.id, execution_mode="market")

            assert result["status"] == "closed"
            assert result["exit_price"] is not None

    @pytest.mark.asyncio
    async def test_exit_leg_limit(self, db_session, test_position_leg):
        """Test exiting leg with limit order."""
        service = LegActionsService(db_session)

        with patch.object(service, 'order_executor') as mock_executor:
            mock_executor.execute_exit.return_value = {"status": "success", "price": Decimal("125.00")}

            result = await service.exit_leg(test_position_leg.id, execution_mode="limit", limit_price=Decimal("125.00"))

            assert result["exit_price"] == Decimal("125.00")

    @pytest.mark.asyncio
    async def test_shift_leg_by_strike(self, db_session, test_position_leg):
        """Test shifting leg to specific strike."""
        service = LegActionsService(db_session)

        with patch.object(service, 'order_executor') as mock_executor:
            mock_executor.execute_orders.return_value = {"status": "success"}

            result = await service.shift_leg(test_position_leg.id, target_strike=24900)

            assert result["new_strike"] == 24900

    @pytest.mark.asyncio
    async def test_shift_leg_by_delta(self, db_session, test_position_leg):
        """Test shifting leg by target delta."""
        service = LegActionsService(db_session)

        with patch.object(service, 'strike_finder') as mock_finder:
            mock_finder.find_strike_by_delta.return_value = {"strike": 24900, "delta": 0.18}

            result = await service.shift_leg(test_position_leg.id, target_delta=Decimal("0.18"))

            assert "new_strike" in result

    @pytest.mark.asyncio
    async def test_shift_leg_by_direction(self, db_session, test_position_leg):
        """Test shifting by direction (closer/further)."""
        service = LegActionsService(db_session)

        result = await service.shift_leg(test_position_leg.id, shift_direction="closer", shift_amount=100)

        assert "new_strike" in result

    @pytest.mark.asyncio
    async def test_roll_leg_to_expiry(self, db_session, test_position_leg):
        """Test rolling leg to new expiry."""
        service = LegActionsService(db_session)
        new_expiry = date.today() + timedelta(days=14)

        with patch.object(service, 'order_executor') as mock_executor:
            mock_executor.execute_orders.return_value = {"status": "success"}

            result = await service.roll_leg(test_position_leg.id, target_expiry=new_expiry)

            assert result["new_expiry"] == new_expiry
            assert result["old_leg_status"] == PositionLegStatus.ROLLED

    @pytest.mark.asyncio
    async def test_roll_leg_with_strike_change(self, db_session, test_position_leg):
        """Test rolling with strike change."""
        service = LegActionsService(db_session)
        new_expiry = date.today() + timedelta(days=14)

        result = await service.roll_leg(test_position_leg.id, target_expiry=new_expiry, target_strike=25100)

        assert result["new_strike"] == 25100

    @pytest.mark.asyncio
    async def test_shift_failure_rollback(self, db_session, test_position_leg):
        """Test rollback on shift failure."""
        service = LegActionsService(db_session)

        with patch.object(service, 'order_executor') as mock_executor:
            mock_executor.execute_orders.side_effect = Exception("Order failed")

            with pytest.raises(Exception):
                await service.shift_leg(test_position_leg.id, target_strike=24900)

            # Verify original leg still open
            await db_session.refresh(test_position_leg)
            assert test_position_leg.status == PositionLegStatus.OPEN

    @pytest.mark.asyncio
    async def test_roll_failure_rollback(self, db_session, test_position_leg):
        """Test rollback on roll failure."""
        service = LegActionsService(db_session)
        new_expiry = date.today() + timedelta(days=14)

        with patch.object(service, 'order_executor') as mock_executor:
            mock_executor.execute_orders.side_effect = Exception("Order failed")

            with pytest.raises(Exception):
                await service.roll_leg(test_position_leg.id, target_expiry=new_expiry)

            # Verify no changes
            await db_session.refresh(test_position_leg)
            assert test_position_leg.status == PositionLegStatus.OPEN

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, db_session, test_position_leg):
        """Test dry run mode returns preview without executing."""
        service = LegActionsService(db_session)

        result = await service.shift_leg(test_position_leg.id, target_strike=24900, execution_mode="dry_run")

        assert "preview" in result or "cost" in result
        # Verify no actual changes
        await db_session.refresh(test_position_leg)
        assert test_position_leg.status == PositionLegStatus.OPEN
