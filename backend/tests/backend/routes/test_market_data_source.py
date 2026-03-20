"""
Market Data Source Tests (Gap O)

Tests that:
1. PUT /api/user/preferences/ triggers live WebSocket switch when market_data_source changes
2. broker-status checks broker_api_credentials (not just broker_connections)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, BigInteger
from sqlalchemy.ext.compiler import compiles
from httpx import AsyncClient, ASGITransport

from app.database import Base, get_db
from app.models import User
from app.models.broker_api_credentials import BrokerAPICredentials
from app.utils.dependencies import get_current_user


# ---------------------------------------------------------------------------
# SQLite Dialect Adapters
# ---------------------------------------------------------------------------

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return compiler.visit_JSON(JSON(), **kw)

@compiles(ARRAY, "sqlite")
def compile_array_sqlite(element, compiler, **kw):
    return "JSON"

@compiles(BigInteger, "sqlite")
def compile_biginteger_sqlite(element, compiler, **kw):
    return "INTEGER"

@compiles(PgUUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "TEXT"

@compiles(PgEnum, "sqlite")
def compile_pgenum_sqlite(element, compiler, **kw):
    return "VARCHAR(50)"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def test_user_id():
    return uuid4()


@pytest.fixture
def mock_user(test_user_id):
    user = MagicMock(spec=User)
    user.id = test_user_id
    user.email = "test@example.com"
    user.first_name = "Test"
    return user


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DB_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def app_with_overrides(mock_user, db_session):
    from app.main import app

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    yield app

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Gap O: PUT /api/user/preferences/ should trigger live WebSocket switch
# ---------------------------------------------------------------------------

class TestPreferencesLiveSwitch:

    @pytest.mark.asyncio
    async def test_preferences_update_triggers_live_switch(self, app_with_overrides):
        """PUT /api/user/preferences/ with market_data_source must trigger ticker_router.switch_user_broker()."""
        with patch("app.services.brokers.market_data.ticker.TickerRouter") as MockRouter:
            mock_router = MagicMock()
            mock_router.switch_user_broker = AsyncMock()
            MockRouter.get_instance.return_value = mock_router

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides), base_url="http://test"
            ) as client:
                resp = await client.put(
                    "/api/user/preferences/",
                    json={"market_data_source": "smartapi"},
                )

            assert resp.status_code == 200
            mock_router.switch_user_broker.assert_called_once()

    @pytest.mark.asyncio
    async def test_preferences_update_without_source_does_not_switch(self, app_with_overrides):
        """PUT /api/user/preferences/ without market_data_source should NOT trigger switch."""
        with patch("app.services.brokers.market_data.ticker.TickerRouter") as MockRouter:
            mock_router = MagicMock()
            mock_router.switch_user_broker = AsyncMock()
            MockRouter.get_instance.return_value = mock_router

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides), base_url="http://test"
            ) as client:
                resp = await client.put(
                    "/api/user/preferences/",
                    json={"pnl_grid_interval": 50},
                )

            assert resp.status_code == 200
            mock_router.switch_user_broker.assert_not_called()


# ---------------------------------------------------------------------------
# broker-status should check broker_api_credentials for ALL brokers
# ---------------------------------------------------------------------------

class TestBrokerStatusChecksUnifiedTable:

    @pytest.mark.asyncio
    async def test_broker_status_detects_dhan_in_unified_table(
        self, app_with_overrides, db_session, test_user_id
    ):
        """broker-status should detect Dhan credentials in broker_api_credentials."""
        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="dhan",
            client_id="DHAN123",
            access_token="dhan_token",
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app_with_overrides), base_url="http://test"
        ) as client:
            resp = await client.get("/api/user/preferences/broker-status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["dhan"] is True

    @pytest.mark.asyncio
    async def test_broker_status_detects_upstox_in_unified_table(
        self, app_with_overrides, db_session, test_user_id
    ):
        """broker-status should detect Upstox credentials in broker_api_credentials."""
        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="upstox",
            api_key="upstox_key",
            access_token="upstox_token",
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app_with_overrides), base_url="http://test"
        ) as client:
            resp = await client.get("/api/user/preferences/broker-status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["upstox"] is True
