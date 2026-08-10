"""
LegActionsService Tests

Tests for exit, shift, and roll leg operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import date, timedelta

from app.services.autopilot.leg_actions_service import LegActionsService
from app.models.autopilot import PositionLegStatus


class TestLegActionsService:
    """Test LegActionsService functionality."""

    @pytest.mark.asyncio
    async def test_exit_leg_market(self, db_session, test_position_leg, test_strategy_active):
        """Test exiting leg with market order."""
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()
        service = LegActionsService(MagicMock(), db_session, str(test_strategy_active.user_id))

        result = await service.exit_leg(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            execution_mode="market"
        )

        assert result["status"] == "success"
        assert result["exit_price"] is not None

        await db_session.refresh(test_position_leg)
        assert test_position_leg.status == PositionLegStatus.CLOSED.value

    @pytest.mark.asyncio
    async def test_exit_leg_limit(self, db_session, test_position_leg, test_strategy_active):
        """Test exiting leg with limit order."""
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()
        service = LegActionsService(MagicMock(), db_session, str(test_strategy_active.user_id))

        result = await service.exit_leg(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            execution_mode="limit",
            limit_price=Decimal("125.00")
        )

        assert result["status"] == "success"
        assert result["exit_price"] is not None

    @pytest.mark.asyncio
    async def test_shift_leg_by_strike(self, db_session, test_position_leg, test_strategy_active):
        """Test shifting leg to specific strike."""
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()
        service = LegActionsService(MagicMock(), db_session, str(test_strategy_active.user_id))

        result = await service.shift_leg(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            target_strike=Decimal("24900")
        )

        assert result["status"] == "executed"
        assert result["new_leg"]["strike"] == Decimal("24900")

    @pytest.mark.asyncio
    async def test_shift_leg_by_delta(self, db_session, test_position_leg, test_strategy_active):
        """Test shifting leg by target delta."""
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()
        service = LegActionsService(MagicMock(), db_session, str(test_strategy_active.user_id))

        with patch.object(
            service.strike_finder, 'find_strike_by_delta',
            AsyncMock(return_value={"strike": Decimal("24900"), "delta": 0.18})
        ):
            result = await service.shift_leg(
                strategy_id=test_strategy_active.id,
                leg_id=test_position_leg.leg_id,
                target_delta=Decimal("0.18")
            )

        assert result["new_leg"]["strike"] == Decimal("24900")

    @pytest.mark.asyncio
    async def test_shift_leg_by_direction(self, db_session, test_position_leg, test_strategy_active):
        """Test shifting by direction (closer/further)."""
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()
        service = LegActionsService(MagicMock(), db_session, str(test_strategy_active.user_id))

        result = await service.shift_leg(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            shift_direction="closer",
            shift_amount=100
        )

        assert "new_leg" in result
        assert result["new_leg"]["strike"] is not None

    @pytest.mark.asyncio
    async def test_roll_leg_to_expiry(self, db_session, test_position_leg, test_strategy_active):
        """Test rolling leg to new expiry."""
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()
        service = LegActionsService(MagicMock(), db_session, str(test_strategy_active.user_id))
        new_expiry = date.today() + timedelta(days=14)

        result = await service.roll_leg(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            target_expiry=new_expiry
        )

        assert result["status"] == "executed"
        assert result["new_leg"]["expiry"] == new_expiry

        await db_session.refresh(test_position_leg)
        assert test_position_leg.status == PositionLegStatus.ROLLED.value

    @pytest.mark.asyncio
    async def test_roll_leg_with_strike_change(self, db_session, test_position_leg, test_strategy_active):
        """Test rolling with strike change."""
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()
        service = LegActionsService(MagicMock(), db_session, str(test_strategy_active.user_id))
        new_expiry = date.today() + timedelta(days=14)

        result = await service.roll_leg(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            target_expiry=new_expiry,
            target_strike=Decimal("25100")
        )

        assert result["new_leg"]["strike"] == Decimal("25100")

    @pytest.mark.asyncio
    async def test_shift_failure_rollback(self, db_session, test_position_leg, test_strategy_active):
        """Test the original leg is untouched when strike resolution fails before any exit/entry order is placed."""
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()
        service = LegActionsService(MagicMock(), db_session, str(test_strategy_active.user_id))

        with pytest.raises(ValueError):
            # No target_strike/target_delta/shift_direction+shift_amount provided
            await service.shift_leg(
                strategy_id=test_strategy_active.id,
                leg_id=test_position_leg.leg_id
            )

        # Verify original leg still open
        await db_session.refresh(test_position_leg)
        assert test_position_leg.status == PositionLegStatus.OPEN.value

    @pytest.mark.asyncio
    async def test_roll_failure_rollback(self, db_session, test_strategy_active):
        """Test roll on a non-existent leg raises and touches nothing."""
        service = LegActionsService(MagicMock(), db_session, str(test_strategy_active.user_id))
        new_expiry = date.today() + timedelta(days=14)

        with pytest.raises(ValueError):
            await service.roll_leg(
                strategy_id=test_strategy_active.id,
                leg_id="nonexistent_leg",
                target_expiry=new_expiry
            )

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, db_session, test_position_leg, test_strategy_active):
        """Test shift still executes under execution_mode='limit' (no separate dry-run path in current service)."""
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()
        service = LegActionsService(MagicMock(), db_session, str(test_strategy_active.user_id))

        result = await service.shift_leg(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            target_strike=Decimal("24900"),
            execution_mode="limit"
        )

        assert result["status"] == "executed"
