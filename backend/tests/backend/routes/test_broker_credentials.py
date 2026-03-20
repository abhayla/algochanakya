"""
Broker Tier 3 Credentials Route Tests

Tests for GET/POST/DELETE credential endpoints for Zerodha, Upstox, and Dhan.
Uses FastAPI TestClient with mocked auth dependency and in-memory SQLite DB.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, BigInteger
from sqlalchemy.ext.compiler import compiles

from app.database import Base, get_db
from app.models import User
from app.models.broker_api_credentials import BrokerAPICredentials  # noqa: F401 - needed for table creation
from app.utils.dependencies import get_current_user


# ---------------------------------------------------------------------------
# SQLite Dialect Adapters (required for in-memory test DB)
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
# Zerodha Credentials Tests
# ---------------------------------------------------------------------------

class TestZerodhaCredentials:

    @pytest.mark.asyncio
    async def test_get_credentials_empty(self, app_with_overrides):
        """GET returns has_credentials=False when nothing saved."""
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            resp = await client.get("/api/zerodha-credentials/credentials")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_credentials"] is False
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_store_credentials(self, app_with_overrides):
        """POST stores credentials and returns status."""
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            resp = await client.post(
                "/api/zerodha-credentials/credentials",
                json={"api_key": "test_api_key_123", "api_secret": "test_secret_abc"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_credentials"] is True
        assert data["api_key"] == "test_api_key_123"
        assert data["is_active"] is True
        assert data["last_error"] is None

    @pytest.mark.asyncio
    async def test_store_then_get_credentials(self, app_with_overrides):
        """POST then GET returns the stored key."""
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            await client.post(
                "/api/zerodha-credentials/credentials",
                json={"api_key": "kite_key_xyz", "api_secret": "kite_secret_xyz"},
            )
            resp = await client.get("/api/zerodha-credentials/credentials")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_credentials"] is True
        assert data["api_key"] == "kite_key_xyz"

    @pytest.mark.asyncio
    async def test_update_credentials(self, app_with_overrides):
        """Second POST updates existing credentials."""
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            await client.post(
                "/api/zerodha-credentials/credentials",
                json={"api_key": "old_key", "api_secret": "old_secret"},
            )
            resp = await client.post(
                "/api/zerodha-credentials/credentials",
                json={"api_key": "new_key", "api_secret": "new_secret"},
            )
        assert resp.status_code == 200
        assert resp.json()["api_key"] == "new_key"

    @pytest.mark.asyncio
    async def test_delete_credentials(self, app_with_overrides):
        """DELETE removes credentials; subsequent GET returns empty."""
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            await client.post(
                "/api/zerodha-credentials/credentials",
                json={"api_key": "del_key", "api_secret": "del_secret"},
            )
            del_resp = await client.delete("/api/zerodha-credentials/credentials")
            get_resp = await client.get("/api/zerodha-credentials/credentials")

        assert del_resp.status_code == 200
        assert get_resp.json()["has_credentials"] is False

    @pytest.mark.asyncio
    async def test_delete_not_found(self, app_with_overrides):
        """DELETE with no credentials returns 404."""
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            resp = await client.delete("/api/zerodha-credentials/credentials")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_store_validates_required_fields(self, app_with_overrides):
        """POST without api_secret should return 422."""
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            resp = await client.post(
                "/api/zerodha-credentials/credentials",
                json={"api_key": "only_key"},
            )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Upstox Credentials Tests
# ---------------------------------------------------------------------------

class TestUpstoxCredentials:

    @pytest.mark.asyncio
    async def test_get_credentials_empty(self, app_with_overrides):
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            resp = await client.get("/api/upstox-credentials/credentials")
        assert resp.status_code == 200
        assert resp.json()["has_credentials"] is False

    @pytest.mark.asyncio
    async def test_store_credentials(self, app_with_overrides):
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            resp = await client.post(
                "/api/upstox-credentials/credentials",
                json={"api_key": "upstox_key", "api_secret": "upstox_secret"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_credentials"] is True
        assert data["api_key"] == "upstox_key"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_delete_credentials(self, app_with_overrides):
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            await client.post(
                "/api/upstox-credentials/credentials",
                json={"api_key": "up_key", "api_secret": "up_secret"},
            )
            del_resp = await client.delete("/api/upstox-credentials/credentials")
            get_resp = await client.get("/api/upstox-credentials/credentials")

        assert del_resp.status_code == 200
        assert get_resp.json()["has_credentials"] is False


# ---------------------------------------------------------------------------
# Dhan Credentials Tests
# ---------------------------------------------------------------------------

class TestDhanCredentials:

    @pytest.mark.asyncio
    async def test_get_credentials_empty(self, app_with_overrides):
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            resp = await client.get("/api/dhan-credentials/credentials")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_credentials"] is False
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_store_credentials(self, app_with_overrides):
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            resp = await client.post(
                "/api/dhan-credentials/credentials",
                json={"client_id": "DHAN123", "access_token": "dhan_token_abc"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_credentials"] is True
        assert data["client_id"] == "DHAN123"
        assert data["is_active"] is True
        assert data["last_auth_at"] is not None

    @pytest.mark.asyncio
    async def test_update_credentials(self, app_with_overrides):
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            await client.post(
                "/api/dhan-credentials/credentials",
                json={"client_id": "OLD123", "access_token": "old_token"},
            )
            resp = await client.post(
                "/api/dhan-credentials/credentials",
                json={"client_id": "NEW456", "access_token": "new_token"},
            )
        assert resp.status_code == 200
        assert resp.json()["client_id"] == "NEW456"

    @pytest.mark.asyncio
    async def test_delete_credentials(self, app_with_overrides):
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            await client.post(
                "/api/dhan-credentials/credentials",
                json={"client_id": "D123", "access_token": "tok"},
            )
            del_resp = await client.delete("/api/dhan-credentials/credentials")
            get_resp = await client.get("/api/dhan-credentials/credentials")

        assert del_resp.status_code == 200
        assert get_resp.json()["has_credentials"] is False

    @pytest.mark.asyncio
    async def test_store_validates_required_fields(self, app_with_overrides):
        """POST without access_token should return 422."""
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            resp = await client.post(
                "/api/dhan-credentials/credentials",
                json={"client_id": "only_id"},
            )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Secret encryption test (api_secret never returned in response)
# ---------------------------------------------------------------------------

class TestSecretNotExposed:

    @pytest.mark.asyncio
    async def test_zerodha_secret_not_in_response(self, app_with_overrides):
        """api_secret must never appear in any response body."""
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            post_resp = await client.post(
                "/api/zerodha-credentials/credentials",
                json={"api_key": "check_key", "api_secret": "super_secret_value"},
            )
            get_resp = await client.get("/api/zerodha-credentials/credentials")

        assert "super_secret_value" not in post_resp.text
        assert "super_secret_value" not in get_resp.text

    @pytest.mark.asyncio
    async def test_dhan_token_not_in_response(self, app_with_overrides):
        """Dhan access_token must never appear in any response body."""
        async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as client:
            post_resp = await client.post(
                "/api/dhan-credentials/credentials",
                json={"client_id": "D1", "access_token": "very_secret_dhan_token"},
            )
            get_resp = await client.get("/api/dhan-credentials/credentials")

        assert "very_secret_dhan_token" not in post_resp.text
        assert "very_secret_dhan_token" not in get_resp.text
