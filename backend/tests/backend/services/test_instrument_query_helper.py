"""
Tests for the centralized NFO instrument query helper.

Validates:
- source_broker filtering prevents duplicate rows
- Fallback chain when preferred source is missing
- Underlying/expiry/type filtering
- Single instrument lookup (no scalar_one_or_none crash)
- Broker-to-source mapping correctness
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

# SQLite dialect adapters (same pattern as root conftest.py)
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


# ── Fixtures ────────────────────────────────────────────────────────────────

FUTURE_EXPIRY = date.today() + timedelta(days=7)
PAST_EXPIRY = date.today() - timedelta(days=7)


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
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # Clean instruments table
        await session.execute(Instrument.__table__.delete())
        await session.commit()
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_db(db):
    """Seed DB with dual-source instruments for NIFTY + edge cases."""
    instruments = [
        # Kite-sourced NIFTY CE options (Kite-internal instrument_token)
        Instrument(instrument_token=14032898, tradingsymbol="NIFTY26APR24000CE",
                   name="NIFTY", exchange="NFO", instrument_type="CE",
                   option_type="CE", strike=Decimal("24000"), expiry=FUTURE_EXPIRY,
                   lot_size=75, source_broker="kite"),
        Instrument(instrument_token=14032900, tradingsymbol="NIFTY26APR24100CE",
                   name="NIFTY", exchange="NFO", instrument_type="CE",
                   option_type="CE", strike=Decimal("24100"), expiry=FUTURE_EXPIRY,
                   lot_size=75, source_broker="kite"),
        Instrument(instrument_token=14032902, tradingsymbol="NIFTY26APR24200CE",
                   name="NIFTY", exchange="NFO", instrument_type="CE",
                   option_type="CE", strike=Decimal("24200"), expiry=FUTURE_EXPIRY,
                   lot_size=75, source_broker="kite"),
        # SmartAPI-sourced NIFTY CE options (NSE exchange tokens — different numbers)
        Instrument(instrument_token=54816, tradingsymbol="NIFTY26APR24000CE",
                   name="NIFTY", exchange="NFO", instrument_type="CE",
                   option_type="CE", strike=Decimal("24000"), expiry=FUTURE_EXPIRY,
                   lot_size=75, source_broker="smartapi"),
        Instrument(instrument_token=54817, tradingsymbol="NIFTY26APR24100CE",
                   name="NIFTY", exchange="NFO", instrument_type="CE",
                   option_type="CE", strike=Decimal("24100"), expiry=FUTURE_EXPIRY,
                   lot_size=75, source_broker="smartapi"),
        Instrument(instrument_token=54818, tradingsymbol="NIFTY26APR24200CE",
                   name="NIFTY", exchange="NFO", instrument_type="CE",
                   option_type="CE", strike=Decimal("24200"), expiry=FUTURE_EXPIRY,
                   lot_size=75, source_broker="smartapi"),
        # Expired instrument (should be excluded by date filter)
        Instrument(instrument_token=99999, tradingsymbol="NIFTY26MAR24000CE",
                   name="NIFTY", exchange="NFO", instrument_type="CE",
                   option_type="CE", strike=Decimal("24000"), expiry=PAST_EXPIRY,
                   lot_size=75, source_broker="kite"),
        # FUT instrument (should be excluded by type filter)
        Instrument(instrument_token=88888, tradingsymbol="NIFTY26APRFUT",
                   name="NIFTY", exchange="NFO", instrument_type="FUT",
                   option_type=None, strike=None, expiry=FUTURE_EXPIRY,
                   lot_size=75, source_broker="kite"),
        # BANKNIFTY — different underlying
        Instrument(instrument_token=77777, tradingsymbol="BANKNIFTY26APR50000CE",
                   name="BANKNIFTY", exchange="NFO", instrument_type="CE",
                   option_type="CE", strike=Decimal("50000"), expiry=FUTURE_EXPIRY,
                   lot_size=35, source_broker="kite"),
    ]
    db.add_all(instruments)
    await db.commit()
    yield db


# ── Tests: Broker-to-source mapping ────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
class TestBrokerSourceMapping:
    async def test_broker_source_mapping_smartapi(self):
        """SmartAPI prefers smartapi source, falls back to kite."""
        from app.services.brokers.market_data.instrument_query import preferred_source_brokers
        assert preferred_source_brokers("smartapi") == ["smartapi", "kite"]

    async def test_broker_source_mapping_upstox(self):
        """Upstox uses SmartAPI tokens (same NSE exchange tokens)."""
        from app.services.brokers.market_data.instrument_query import preferred_source_brokers
        assert preferred_source_brokers("upstox") == ["smartapi", "kite"]

    async def test_broker_source_mapping_kite(self):
        """Kite prefers kite source (different instrument_token numbering)."""
        from app.services.brokers.market_data.instrument_query import preferred_source_brokers
        assert preferred_source_brokers("kite") == ["kite", "smartapi"]


# ── Tests: get_nfo_instruments ──────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetNfoInstruments:
    async def test_filters_by_source_broker(self, seeded_db):
        """When querying for smartapi broker, returns only smartapi rows."""
        from app.services.brokers.market_data.instrument_query import get_nfo_instruments
        instruments = await get_nfo_instruments(
            seeded_db, "NIFTY", FUTURE_EXPIRY, broker_type="smartapi"
        )
        assert len(instruments) == 3
        assert all(i.source_broker == "smartapi" for i in instruments)
        # Verify correct token numbers (SmartAPI = NSE exchange tokens)
        tokens = {i.instrument_token for i in instruments}
        assert tokens == {54816, 54817, 54818}

    async def test_fallback_when_preferred_missing(self, seeded_db):
        """Upstox prefers smartapi; if smartapi exists, uses it."""
        from app.services.brokers.market_data.instrument_query import get_nfo_instruments
        instruments = await get_nfo_instruments(
            seeded_db, "NIFTY", FUTURE_EXPIRY, broker_type="upstox"
        )
        assert len(instruments) == 3
        # Should use smartapi rows (same NSE tokens as Upstox)
        assert all(i.source_broker == "smartapi" for i in instruments)

    async def test_fallback_to_kite_when_smartapi_missing(self, db):
        """When only kite instruments exist, upstox query falls back to kite."""
        from app.services.brokers.market_data.instrument_query import get_nfo_instruments
        # Seed only kite instruments
        db.add(Instrument(
            instrument_token=14032898, tradingsymbol="NIFTY26APR24000CE",
            name="NIFTY", exchange="NFO", instrument_type="CE",
            option_type="CE", strike=Decimal("24000"), expiry=FUTURE_EXPIRY,
            lot_size=75, source_broker="kite",
        ))
        await db.commit()

        instruments = await get_nfo_instruments(
            db, "NIFTY", FUTURE_EXPIRY, broker_type="upstox"
        )
        assert len(instruments) == 1
        assert instruments[0].source_broker == "kite"

    async def test_filters_by_underlying_and_expiry(self, seeded_db):
        """Only returns instruments matching the requested underlying."""
        from app.services.brokers.market_data.instrument_query import get_nfo_instruments
        instruments = await get_nfo_instruments(
            seeded_db, "BANKNIFTY", FUTURE_EXPIRY, broker_type="kite"
        )
        assert len(instruments) == 1
        assert instruments[0].name == "BANKNIFTY"

    async def test_returns_only_ce_pe(self, seeded_db):
        """FUT instruments are excluded from NFO option queries."""
        from app.services.brokers.market_data.instrument_query import get_nfo_instruments
        instruments = await get_nfo_instruments(
            seeded_db, "NIFTY", FUTURE_EXPIRY, broker_type="kite"
        )
        types = {i.instrument_type for i in instruments}
        assert types.issubset({"CE", "PE"})
        assert "FUT" not in types

    async def test_empty_for_nonexistent_underlying(self, seeded_db):
        """Returns empty list for an underlying with no instruments."""
        from app.services.brokers.market_data.instrument_query import get_nfo_instruments
        instruments = await get_nfo_instruments(
            seeded_db, "FINNIFTY", FUTURE_EXPIRY, broker_type="kite"
        )
        assert instruments == []


# ── Tests: get_single_instrument ────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetSingleInstrument:
    async def test_no_crash_with_duplicates(self, seeded_db):
        """Single lookup with duplicate rows (kite + smartapi) must not crash."""
        from app.services.brokers.market_data.instrument_query import get_single_instrument
        inst = await get_single_instrument(
            seeded_db, "NIFTY", FUTURE_EXPIRY,
            strike=Decimal("24000"), contract_type="CE", broker_type="smartapi"
        )
        assert inst is not None
        assert inst.source_broker == "smartapi"
        assert inst.instrument_token == 54816

    async def test_returns_none_for_missing(self, seeded_db):
        """Returns None for a non-existent strike."""
        from app.services.brokers.market_data.instrument_query import get_single_instrument
        inst = await get_single_instrument(
            seeded_db, "NIFTY", FUTURE_EXPIRY,
            strike=Decimal("99999"), contract_type="CE", broker_type="smartapi"
        )
        assert inst is None
