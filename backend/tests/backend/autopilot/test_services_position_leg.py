"""
PositionLegService Tests

Tests for position leg CRUD, Greeks updates, and P&L calculations.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.services.autopilot.position_leg_service import PositionLegService
from app.models.autopilot import PositionLegStatus


class TestPositionLegService:
    """Test PositionLegService functionality."""

    @pytest.mark.asyncio
    async def test_create_leg_with_all_fields(self, db_session, test_strategy_active):
        """Test creating position leg with all fields."""
        service = PositionLegService(MagicMock(), db_session)

        leg = await service.create_position_leg(
            strategy_id=test_strategy_active.id,
            leg_id="leg_new",
            contract_type="CE",
            action="BUY",
            strike=Decimal("25100"),
            expiry=date.today() + timedelta(days=7),
            lots=1,
            entry_price=Decimal("200.00")
        )

        assert leg.id is not None
        assert leg.strike == Decimal("25100")
        assert leg.status == PositionLegStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_update_leg_greeks(self, db_session, test_position_leg, test_strategy_active):
        """Test updating leg Greeks."""
        service = PositionLegService(MagicMock(), db_session)
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()

        with patch.object(
            service, '_calculate_leg_greeks',
            AsyncMock(return_value={
                "delta": Decimal("-0.20"),
                "gamma": Decimal("0.0025"),
                "theta": Decimal("-13.00"),
                "vega": Decimal("9.00"),
                "iv": Decimal("19.00"),
            })
        ):
            updated = await service.update_leg_greeks(
                strategy_id=test_strategy_active.id,
                leg_id=test_position_leg.leg_id,
                spot_price=Decimal("25000"),
                current_price=Decimal("150.00")
            )

        assert updated.delta == Decimal("-0.20")
        assert updated.gamma == Decimal("0.0025")

    @pytest.mark.asyncio
    async def test_update_leg_pnl_via_exit(self, db_session, test_position_leg, test_strategy_active):
        """Test P&L is calculated on exit (update_leg_exit)."""
        service = PositionLegService(MagicMock(), db_session)
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()

        exit_price = Decimal("150.00")
        # SELL PE: entry 185.50, exit 150.00 = profit 35.50 * lots * lot_size
        updated = await service.update_leg_exit(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            exit_price=exit_price,
            exit_order_ids=["order_1"],
            exit_reason="manual"
        )

        assert updated.realized_pnl is not None
        assert updated.unrealized_pnl == Decimal('0')

    @pytest.mark.asyncio
    async def test_close_leg_sets_status_and_exit(self, db_session, test_position_leg, test_strategy_active):
        """Test closing leg sets status and exit fields."""
        service = PositionLegService(MagicMock(), db_session)
        test_position_leg.status = PositionLegStatus.OPEN.value
        await db_session.commit()

        exit_price = Decimal("120.00")
        closed = await service.update_leg_exit(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            exit_price=exit_price,
            exit_order_ids=["order_1"],
            exit_reason="target_hit"
        )

        assert closed.status == PositionLegStatus.CLOSED.value
        assert closed.exit_price == exit_price
        assert closed.exit_time is not None
        assert closed.realized_pnl is not None

    @pytest.mark.asyncio
    async def test_get_legs_by_strategy(self, db_session, test_strategy_active, test_position_legs_multiple):
        """Test getting all legs for a strategy."""
        service = PositionLegService(MagicMock(), db_session)

        legs = await service.get_all_strategy_legs(test_strategy_active.id)

        assert len(legs) >= 2
        assert all(leg.strategy_id == test_strategy_active.id for leg in legs)

    @pytest.mark.asyncio
    async def test_get_open_legs_only(self, db_session, test_strategy_active, test_position_legs_multiple):
        """Test filtering for open legs only."""
        service = PositionLegService(MagicMock(), db_session)

        # Close one leg
        test_position_legs_multiple[0].status = PositionLegStatus.CLOSED.value
        await db_session.commit()

        open_legs = await service.get_all_strategy_legs(
            test_strategy_active.id, status_filter=PositionLegStatus.OPEN.value
        )

        assert all(leg.status == PositionLegStatus.OPEN.value for leg in open_legs)
        assert len(open_legs) < len(test_position_legs_multiple)

    @pytest.mark.asyncio
    async def test_calculate_unrealized_pnl(self, db_session, test_position_leg, test_strategy_active):
        """Test unrealized P&L calculation formula (via _calculate_unrealized_pnl)."""
        service = PositionLegService(MagicMock(), db_session)

        current_price = Decimal("160.00")
        pnl = await service._calculate_unrealized_pnl(test_position_leg, current_price)

        # SELL: (entry - current) * lots * lot_size
        from app.constants import get_lot_size
        lot_size = get_lot_size(test_strategy_active.underlying)
        expected = (test_position_leg.entry_price - current_price) * test_position_leg.lots * lot_size
        assert pnl == expected

    @pytest.mark.asyncio
    async def test_calculate_realized_pnl(self, db_session, test_position_leg, test_strategy_active):
        """Test realized P&L after exit (via _calculate_realized_pnl)."""
        service = PositionLegService(MagicMock(), db_session)

        exit_price = Decimal("130.00")
        pnl = await service._calculate_realized_pnl(test_position_leg, exit_price)

        # SELL: (entry - exit) * lots * lot_size
        from app.constants import get_lot_size
        lot_size = get_lot_size(test_strategy_active.underlying)
        expected = (test_position_leg.entry_price - exit_price) * test_position_leg.lots * lot_size
        assert pnl == expected

    @pytest.mark.asyncio
    async def test_link_rolled_legs(self, db_session, test_strategy_active):
        """Test linking rolled legs correctly."""
        service = PositionLegService(MagicMock(), db_session)

        # Create original leg
        original = await service.create_position_leg(
            strategy_id=test_strategy_active.id,
            leg_id="leg_original",
            contract_type="PE",
            action="SELL",
            strike=Decimal("25000"),
            expiry=date.today() + timedelta(days=7),
            lots=1,
            entry_price=Decimal("180.00")
        )

        # Create rolled leg
        rolled = await service.create_position_leg(
            strategy_id=test_strategy_active.id,
            leg_id="leg_rolled",
            contract_type="PE",
            action="SELL",
            strike=Decimal("25000"),
            expiry=date.today() + timedelta(days=14),
            lots=1,
            entry_price=Decimal("190.00")
        )

        # Mark original as rolled, linked to the new leg
        updated_original = await service.mark_leg_as_rolled(
            strategy_id=test_strategy_active.id,
            old_leg_id=original.leg_id,
            new_leg_id=rolled.id
        )

        assert updated_original.status == PositionLegStatus.ROLLED.value
        assert updated_original.rolled_to_leg_id == rolled.id

    @pytest.mark.asyncio
    async def test_get_leg_not_found(self, db_session, test_strategy_active):
        """Test getting non-existent leg returns None."""
        service = PositionLegService(MagicMock(), db_session)

        leg = await service.get_position_leg(test_strategy_active.id, "nonexistent_leg")

        assert leg is None
