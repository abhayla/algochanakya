"""
PositionLegService Tests

Tests for position leg CRUD, Greeks updates, and P&L calculations.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.services.position_leg_service import PositionLegService
from app.models.autopilot import PositionLegStatus


class TestPositionLegService:
    """Test PositionLegService functionality."""

    @pytest.mark.asyncio
    async def test_create_leg_with_all_fields(self, db_session, test_strategy_active):
        """Test creating position leg with all fields."""
        service = PositionLegService(db_session)

        leg_data = {
            "leg_id": "leg_new",
            "underlying": "NIFTY",
            "expiry": date.today() + timedelta(days=7),
            "strike": 25100,
            "option_type": "CE",
            "transaction_type": "BUY",
            "quantity": 25,
            "entry_price": Decimal("200.00"),
            "delta": Decimal("0.25"),
            "gamma": Decimal("0.003"),
            "theta": Decimal("-15.00"),
            "vega": Decimal("9.50"),
            "iv": Decimal("0.19")
        }

        leg = await service.create_leg(test_strategy_active.id, leg_data)

        assert leg.id is not None
        assert leg.strike == 25100
        assert leg.delta == Decimal("0.25")

    @pytest.mark.asyncio
    async def test_update_leg_greeks(self, db_session, test_position_leg):
        """Test updating leg Greeks."""
        service = PositionLegService(db_session)

        new_greeks = {
            "delta": Decimal("-0.20"),
            "gamma": Decimal("0.0025"),
            "theta": Decimal("-13.00"),
            "vega": Decimal("9.00"),
            "iv": Decimal("0.19")
        }

        updated = await service.update_leg_greeks(test_position_leg.id, new_greeks)

        assert updated.delta == Decimal("-0.20")
        assert updated.gamma == Decimal("0.0025")

    @pytest.mark.asyncio
    async def test_update_leg_pnl(self, db_session, test_position_leg):
        """Test updating leg P&L."""
        service = PositionLegService(db_session)

        current_price = Decimal("150.00")
        # SELL PE: entry 185.50, current 150.00 = profit 35.50 * 25
        expected_pnl = (test_position_leg.entry_price - current_price) * test_position_leg.quantity

        updated = await service.update_leg_pnl(test_position_leg.id, current_price)

        assert updated.unrealized_pnl == expected_pnl

    @pytest.mark.asyncio
    async def test_close_leg_sets_status_and_exit(self, db_session, test_position_leg):
        """Test closing leg sets status and exit fields."""
        service = PositionLegService(db_session)

        exit_price = Decimal("120.00")
        closed = await service.close_leg(test_position_leg.id, exit_price)

        assert closed.status == PositionLegStatus.CLOSED
        assert closed.exit_price == exit_price
        assert closed.exit_time is not None
        assert closed.realized_pnl is not None

    @pytest.mark.asyncio
    async def test_get_legs_by_strategy(self, db_session, test_strategy_active, test_position_legs_multiple):
        """Test getting all legs for a strategy."""
        service = PositionLegService(db_session)

        legs = await service.get_all_strategy_legs(test_strategy_active.id)

        assert len(legs) >= 2
        assert all(leg.strategy_id == test_strategy_active.id for leg in legs)

    @pytest.mark.asyncio
    async def test_get_open_legs_only(self, db_session, test_strategy_active, test_position_legs_multiple):
        """Test filtering for open legs only."""
        service = PositionLegService(db_session)

        # Close one leg
        test_position_legs_multiple[0].status = PositionLegStatus.CLOSED
        await db_session.commit()

        open_legs = await service.get_open_legs(test_strategy_active.id)

        assert all(leg.status == PositionLegStatus.OPEN for leg in open_legs)
        assert len(open_legs) < len(test_position_legs_multiple)

    @pytest.mark.asyncio
    async def test_calculate_unrealized_pnl(self, db_session, test_position_leg):
        """Test unrealized P&L calculation formula."""
        service = PositionLegService(db_session)

        current_price = Decimal("160.00")
        pnl = service.calculate_unrealized_pnl(
            test_position_leg.entry_price,
            current_price,
            test_position_leg.quantity,
            test_position_leg.transaction_type
        )

        # SELL: (entry - current) * qty = (185.50 - 160.00) * 25 = 637.50
        expected = (test_position_leg.entry_price - current_price) * test_position_leg.quantity
        assert pnl == expected

    @pytest.mark.asyncio
    async def test_calculate_realized_pnl(self, db_session, test_position_leg):
        """Test realized P&L after exit."""
        service = PositionLegService(db_session)

        exit_price = Decimal("130.00")
        pnl = service.calculate_realized_pnl(
            test_position_leg.entry_price,
            exit_price,
            test_position_leg.quantity,
            test_position_leg.transaction_type
        )

        # SELL: (entry - exit) * qty = (185.50 - 130.00) * 25 = 1387.50
        expected = (test_position_leg.entry_price - exit_price) * test_position_leg.quantity
        assert pnl == expected

    @pytest.mark.asyncio
    async def test_link_rolled_legs(self, db_session, test_strategy_active):
        """Test linking rolled legs correctly."""
        service = PositionLegService(db_session)

        # Create original leg
        original_data = {
            "leg_id": "leg_original",
            "underlying": "NIFTY",
            "expiry": date.today() + timedelta(days=7),
            "strike": 25000,
            "option_type": "PE",
            "transaction_type": "SELL",
            "quantity": 25,
            "entry_price": Decimal("180.00")
        }
        original = await service.create_leg(test_strategy_active.id, original_data)

        # Mark as rolled
        original.status = PositionLegStatus.ROLLED
        await db_session.commit()

        # Create rolled leg
        rolled_data = {
            "leg_id": "leg_rolled",
            "underlying": "NIFTY",
            "expiry": date.today() + timedelta(days=14),
            "strike": 25000,
            "option_type": "PE",
            "transaction_type": "SELL",
            "quantity": 25,
            "entry_price": Decimal("190.00"),
            "rolled_from_leg_id": original.id
        }
        rolled = await service.create_leg(test_strategy_active.id, rolled_data)

        assert rolled.rolled_from_leg_id == original.id

    @pytest.mark.asyncio
    async def test_get_leg_not_found(self, db_session):
        """Test getting non-existent leg returns None."""
        service = PositionLegService(db_session)

        leg = await service.get_leg(99999)

        assert leg is None
