"""
Integration tests verifying source_broker deduplication across query sites.

Tests that instrument queries return single-source results when
both kite and smartapi instruments exist in the DB.
"""

import pytest
import pytest_asyncio
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, BigInteger
from sqlalchemy.ext.compiler import compiles

from app.database import Base
from app.models.instruments import Instrument

# SQLite dialect adapters
@compiles(JSONB, "sqlite")
def _jsonb(element, compiler, **kw):
    return compiler.visit_JSON(JSON(), **kw)

@compiles(ARRAY, "sqlite")
def _array(element, compiler, **kw):
    return "JSON"

@compiles(BigInteger, "sqlite")
def _bigint(element, compiler, **kw):
    return "INTEGER"

@compiles(PgUUID, "sqlite")
def _uuid(element, compiler, **kw):
    return "TEXT"

@compiles(PgEnum, "sqlite")
def _enum(element, compiler, **kw):
    return "VARCHAR(50)"


FUTURE_EXPIRY = date.today() + timedelta(days=7)


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(Instrument.__table__.delete())
        await session.commit()
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def dual_source_db(db):
    """DB with same strikes from both kite and smartapi (the duplicate scenario)."""
    strikes = [24000, 24100, 24200]
    for strike in strikes:
        for opt_type in ["CE", "PE"]:
            # Kite row (Kite-internal token)
            db.add(Instrument(
                instrument_token=14000000 + strike + (1 if opt_type == "PE" else 0),
                tradingsymbol=f"NIFTY26APR{strike}{opt_type}",
                name="NIFTY", exchange="NFO", instrument_type=opt_type,
                option_type=opt_type, strike=Decimal(str(strike)),
                expiry=FUTURE_EXPIRY, lot_size=75, source_broker="kite",
            ))
            # SmartAPI row (NSE exchange token — different number)
            db.add(Instrument(
                instrument_token=50000 + strike + (1 if opt_type == "PE" else 0),
                tradingsymbol=f"NIFTY26APR{strike}{opt_type}",
                name="NIFTY", exchange="NFO", instrument_type=opt_type,
                option_type=opt_type, strike=Decimal(str(strike)),
                expiry=FUTURE_EXPIRY, lot_size=75, source_broker="smartapi",
            ))
    await db.commit()
    yield db


@pytest.mark.unit
@pytest.mark.asyncio
class TestInstrumentDeduplication:
    async def test_optionchain_uses_correct_source_for_smartapi(self, dual_source_db):
        """Option chain helper returns only smartapi tokens for smartapi broker."""
        from app.services.brokers.market_data.instrument_query import get_nfo_instruments
        instruments = await get_nfo_instruments(
            dual_source_db, "NIFTY", FUTURE_EXPIRY, broker_type="smartapi"
        )
        # Should get 6 instruments (3 strikes × 2 types) from smartapi only
        assert len(instruments) == 6
        assert all(i.source_broker == "smartapi" for i in instruments)
        # All tokens should be in the SmartAPI range (50000+), not Kite (14M+)
        for i in instruments:
            assert i.instrument_token < 100000, f"Got Kite token {i.instrument_token} instead of SmartAPI"

    async def test_optionchain_uses_correct_source_for_kite(self, dual_source_db):
        """Option chain helper returns only kite tokens for kite broker."""
        from app.services.brokers.market_data.instrument_query import get_nfo_instruments
        instruments = await get_nfo_instruments(
            dual_source_db, "NIFTY", FUTURE_EXPIRY, broker_type="kite"
        )
        assert len(instruments) == 6
        assert all(i.source_broker == "kite" for i in instruments)
        for i in instruments:
            assert i.instrument_token > 1000000, f"Got SmartAPI token {i.instrument_token} instead of Kite"

    async def test_single_instrument_no_crash_with_duplicates(self, dual_source_db):
        """get_single_instrument returns exactly one result, not MultipleResultsFound."""
        from app.services.brokers.market_data.instrument_query import get_single_instrument
        inst = await get_single_instrument(
            dual_source_db, "NIFTY", FUTURE_EXPIRY,
            strike=Decimal("24000"), contract_type="CE", broker_type="smartapi"
        )
        assert inst is not None
        assert inst.source_broker == "smartapi"
        assert inst.instrument_token == 74000  # 50000 + 24000 + 0 (CE)
