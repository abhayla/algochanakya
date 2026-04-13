"""
Tests for EODOptionSnapshot model.

TDD: Written FIRST, before the model implementation.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.market_hours import IST

# Import will fail until model is created — that's the RED phase
from app.models.eod_option_snapshot import EODOptionSnapshot


def _captured_at():
    """Helper: recent IST timestamp."""
    return datetime(2026, 4, 10, 15, 36, tzinfo=IST)


@pytest.mark.asyncio
class TestEODOptionSnapshotModel:

    async def test_create_row_persists_all_fields(self, db_session: AsyncSession):
        """Insert a row, query back, verify all fields including Decimal precision."""
        row = EODOptionSnapshot(
            id=uuid.uuid4(),
            underlying="NIFTY",
            expiry_date=date(2026, 4, 16),
            strike=Decimal("24000.00"),
            ce_ltp=Decimal("550.25"),
            ce_oi=1234567,
            ce_volume=45000,
            ce_iv=Decimal("18.50"),
            pe_ltp=Decimal("120.75"),
            pe_oi=987654,
            pe_volume=38000,
            pe_iv=Decimal("19.20"),
            spot_price=Decimal("24050.50"),
            captured_at=_captured_at(),
        )
        db_session.add(row)
        await db_session.commit()

        result = await db_session.execute(
            select(EODOptionSnapshot).where(
                EODOptionSnapshot.underlying == "NIFTY",
                EODOptionSnapshot.strike == Decimal("24000.00"),
            )
        )
        fetched = result.scalar_one()

        assert fetched.underlying == "NIFTY"
        assert fetched.expiry_date == date(2026, 4, 16)
        assert fetched.strike == Decimal("24000.00")
        assert fetched.ce_ltp == Decimal("550.25")
        assert fetched.ce_oi == 1234567
        assert fetched.ce_volume == 45000
        assert fetched.pe_ltp == Decimal("120.75")
        assert fetched.pe_oi == 987654
        assert fetched.spot_price == Decimal("24050.50")
        assert fetched.captured_at is not None

    async def test_unique_constraint_prevents_duplicate_strike(self, db_session: AsyncSession):
        """Same (underlying, expiry_date, strike) should raise IntegrityError."""
        common = dict(
            underlying="NIFTY",
            expiry_date=date(2026, 4, 16),
            strike=Decimal("24000.00"),
            ce_ltp=Decimal("100"),
            ce_oi=100,
            ce_volume=10,
            ce_iv=Decimal("15"),
            pe_ltp=Decimal("50"),
            pe_oi=50,
            pe_volume=5,
            pe_iv=Decimal("16"),
            spot_price=Decimal("24000"),
            captured_at=_captured_at(),
        )
        row1 = EODOptionSnapshot(id=uuid.uuid4(), **common)
        row2 = EODOptionSnapshot(id=uuid.uuid4(), **common)

        db_session.add(row1)
        await db_session.commit()

        db_session.add(row2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    async def test_different_strikes_same_underlying_allowed(self, db_session: AsyncSession):
        """Two different strikes for same underlying+expiry should both persist."""
        common = dict(
            underlying="BANKNIFTY",
            expiry_date=date(2026, 4, 16),
            ce_ltp=Decimal("100"),
            ce_oi=100,
            ce_volume=10,
            ce_iv=Decimal("15"),
            pe_ltp=Decimal("50"),
            pe_oi=50,
            pe_volume=5,
            pe_iv=Decimal("16"),
            spot_price=Decimal("51000"),
            captured_at=_captured_at(),
        )
        row1 = EODOptionSnapshot(id=uuid.uuid4(), strike=Decimal("51000.00"), **common)
        row2 = EODOptionSnapshot(id=uuid.uuid4(), strike=Decimal("51100.00"), **common)

        db_session.add_all([row1, row2])
        await db_session.commit()

        result = await db_session.execute(
            select(EODOptionSnapshot).where(
                EODOptionSnapshot.underlying == "BANKNIFTY"
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 2

    async def test_different_expiry_same_strike_allowed(self, db_session: AsyncSession):
        """Same underlying+strike but different expiry should both persist."""
        common = dict(
            underlying="NIFTY",
            strike=Decimal("24000.00"),
            ce_ltp=Decimal("100"),
            ce_oi=100,
            ce_volume=10,
            ce_iv=Decimal("15"),
            pe_ltp=Decimal("50"),
            pe_oi=50,
            pe_volume=5,
            pe_iv=Decimal("16"),
            spot_price=Decimal("24000"),
            captured_at=_captured_at(),
        )
        row1 = EODOptionSnapshot(id=uuid.uuid4(), expiry_date=date(2026, 4, 16), **common)
        row2 = EODOptionSnapshot(id=uuid.uuid4(), expiry_date=date(2026, 4, 23), **common)

        db_session.add_all([row1, row2])
        await db_session.commit()

        result = await db_session.execute(
            select(EODOptionSnapshot).where(
                EODOptionSnapshot.underlying == "NIFTY"
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 2
