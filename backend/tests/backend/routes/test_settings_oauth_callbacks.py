"""
Settings OAuth Callback Tests (Gap N)

Tests for /api/settings/{broker}/connect-callback endpoints.
These callbacks store tokens in broker_api_credentials (for market data),
NOT in broker_connections (for order execution).
They must NOT create JWT sessions or overwrite login state.

Covers: Zerodha, Upstox, Fyers, Paytm (OAuth brokers).
AngelOne uses direct auth (no OAuth callback needed).
Dhan uses static token (no OAuth yet — Gap K).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, BigInteger, select
from sqlalchemy.ext.compiler import compiles

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
    """Create app with auth + DB overrides."""
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
# Core Requirements: Settings callbacks must NOT create sessions
# ---------------------------------------------------------------------------

class TestSettingsCallbacksDoNotCreateSessions:
    """Settings callbacks must store tokens in broker_api_credentials only.
    They must NOT touch broker_connections, create JWTs, or write to Redis."""

    @pytest.mark.asyncio
    async def test_upstox_settings_callback_stores_in_broker_api_credentials(
        self, app_with_overrides, db_session, test_user_id
    ):
        """Upstox Settings callback stores access_token in broker_api_credentials."""
        from httpx import AsyncClient, ASGITransport

        # Mock the Upstox token exchange and profile fetch
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "upstox_market_token"}

        mock_profile_response = MagicMock()
        mock_profile_response.status_code = 200
        mock_profile_response.json.return_value = {"data": {"user_id": "UP123", "email": "test@test.com"}}

        with patch("app.api.routes.settings_credentials.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_profile_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/settings/upstox/connect-callback?code=test_auth_code",
                    follow_redirects=False,
                )

        # Should redirect to settings page (not login)
        assert resp.status_code == 302
        assert "/settings" in resp.headers["location"]
        assert "token=" not in resp.headers["location"]  # No JWT in URL

        # Check broker_api_credentials was created
        result = await db_session.execute(
            select(BrokerAPICredentials).where(
                BrokerAPICredentials.user_id == test_user_id,
                BrokerAPICredentials.broker == "upstox",
            )
        )
        cred = result.scalar_one_or_none()
        assert cred is not None
        assert cred.access_token == "upstox_market_token"
        assert cred.is_active is True

    @pytest.mark.asyncio
    async def test_zerodha_settings_callback_stores_in_broker_api_credentials(
        self, app_with_overrides, db_session, test_user_id
    ):
        """Zerodha Settings callback stores access_token in broker_api_credentials."""
        from httpx import AsyncClient, ASGITransport

        with patch("app.api.routes.settings_credentials.KiteConnect") as MockKite:
            instance = MockKite.return_value
            instance.generate_session.return_value = {
                "access_token": "kite_market_data_token",
                "user_id": "ZR123",
            }
            instance.profile.return_value = {
                "user_id": "ZR123",
                "email": "test@test.com",
                "user_name": "Test",
            }

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/settings/zerodha/connect-callback?request_token=test_req_token",
                    follow_redirects=False,
                )

        assert resp.status_code == 302
        assert "/settings" in resp.headers["location"]

        result = await db_session.execute(
            select(BrokerAPICredentials).where(
                BrokerAPICredentials.user_id == test_user_id,
                BrokerAPICredentials.broker == "zerodha",
            )
        )
        cred = result.scalar_one_or_none()
        assert cred is not None
        assert cred.access_token == "kite_market_data_token"
        assert cred.is_active is True

    @pytest.mark.asyncio
    async def test_settings_callback_does_not_import_jwt_or_redis(self):
        """Settings credentials module must NOT import create_access_token or get_redis."""
        import app.api.routes.settings_credentials as mod
        import inspect

        source = inspect.getsource(mod)
        assert "create_access_token" not in source, \
            "Settings credentials must not import create_access_token"
        assert "get_redis" not in source, \
            "Settings credentials must not import get_redis"

    @pytest.mark.asyncio
    async def test_settings_callback_updates_existing_credentials(
        self, app_with_overrides, db_session, test_user_id
    ):
        """Settings callback updates existing credentials instead of creating duplicates."""
        # Pre-create credential row
        existing = BrokerAPICredentials(
            user_id=test_user_id,
            broker="upstox",
            api_key="old_key",
            access_token="old_token",
            is_active=False,
            last_error="Previous error",
        )
        db_session.add(existing)
        await db_session.commit()

        from httpx import AsyncClient, ASGITransport

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "new_upstox_token"}

        mock_profile_response = MagicMock()
        mock_profile_response.status_code = 200
        mock_profile_response.json.return_value = {"data": {"user_id": "UP123"}}

        with patch("app.api.routes.settings_credentials.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_profile_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/settings/upstox/connect-callback?code=new_code",
                    follow_redirects=False,
                )

        # Should have updated existing row, not created new
        result = await db_session.execute(
            select(BrokerAPICredentials).where(
                BrokerAPICredentials.user_id == test_user_id,
                BrokerAPICredentials.broker == "upstox",
            )
        )
        creds = result.scalars().all()
        assert len(creds) == 1
        assert creds[0].access_token == "new_upstox_token"
        assert creds[0].is_active is True
        assert creds[0].last_error is None


# ---------------------------------------------------------------------------
# Settings Connect Initiation (OAuth URL generation)
# ---------------------------------------------------------------------------

class TestSettingsConnectInitiation:
    """Tests for GET /api/settings/{broker}/connect — returns OAuth URL."""

    @pytest.mark.asyncio
    async def test_upstox_connect_returns_oauth_url(self, app_with_overrides):
        """GET /api/settings/upstox/connect returns Upstox OAuth URL."""
        from httpx import AsyncClient, ASGITransport

        async with AsyncClient(
            transport=ASGITransport(app=app_with_overrides), base_url="http://test"
        ) as client:
            resp = await client.get("/api/settings/upstox/connect")

        assert resp.status_code == 200
        data = resp.json()
        assert "login_url" in data
        assert "upstox.com" in data["login_url"]
        # Must use settings redirect URL, NOT login redirect
        assert "settings" in data["login_url"]

    @pytest.mark.asyncio
    async def test_zerodha_connect_returns_oauth_url(self, app_with_overrides):
        """GET /api/settings/zerodha/connect returns Kite OAuth URL."""
        from httpx import AsyncClient, ASGITransport

        with patch("app.api.routes.settings_credentials.KiteConnect") as MockKite:
            instance = MockKite.return_value
            instance.login_url.return_value = "https://kite.zerodha.com/connect/login?api_key=test"

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides), base_url="http://test"
            ) as client:
                resp = await client.get("/api/settings/zerodha/connect")

        assert resp.status_code == 200
        data = resp.json()
        assert "login_url" in data


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------

class TestSettingsCallbackErrors:
    """Settings callbacks should redirect to settings with error params on failure."""

    @pytest.mark.asyncio
    async def test_callback_redirects_to_settings_on_token_exchange_failure(
        self, app_with_overrides
    ):
        """Failed token exchange redirects to /settings?error=..."""
        from httpx import AsyncClient, ASGITransport

        mock_token_response = MagicMock()
        mock_token_response.status_code = 401
        mock_token_response.text = "Invalid code"

        with patch("app.api.routes.settings_credentials.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            async with AsyncClient(
                transport=ASGITransport(app=app_with_overrides), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/settings/upstox/connect-callback?code=bad_code",
                    follow_redirects=False,
                )

        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "/settings" in location
        assert "error=" in location
