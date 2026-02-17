"""
Tests for broker preferences API endpoints.

Tests GET/PUT /api/user/preferences/ for broker-related fields:
- market_data_source (7 values: platform + 6 brokers)
- order_broker (6 brokers)
"""
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.compiler import compiles


# SQLite JSONB compatibility
@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(element, compiler, **kw):
    return compiler.visit_JSON(JSON(), **kw)


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

from app.database import Base, get_db
from app.main import app
from app.models import User


@pytest.fixture(scope="module")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="module")
async def test_user(test_session_factory):
    async with test_session_factory() as session:
        user = User(id=uuid4(), email="broker_pref_test@example.com")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture(scope="module")
async def client(test_session_factory, test_user):
    """HTTP client with overridden DB and auth."""
    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    async def override_get_current_user():
        return test_user

    from app.utils.dependencies import get_current_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# GET /api/user/preferences/ — broker fields returned
# =============================================================================

@pytest.mark.asyncio
async def test_get_preferences_returns_market_data_source(client):
    """GET preferences includes market_data_source field."""
    response = await client.get("/api/user/preferences/")
    assert response.status_code == 200
    data = response.json()
    assert "market_data_source" in data


@pytest.mark.asyncio
async def test_get_preferences_returns_order_broker(client):
    """GET preferences includes order_broker field."""
    response = await client.get("/api/user/preferences/")
    assert response.status_code == 200
    data = response.json()
    assert "order_broker" in data


@pytest.mark.asyncio
async def test_get_preferences_default_market_data_source(client):
    """Default market_data_source should be a valid value."""
    response = await client.get("/api/user/preferences/")
    assert response.status_code == 200
    data = response.json()
    valid = ("platform", "smartapi", "kite", "upstox", "dhan", "fyers", "paytm")
    assert data["market_data_source"] in valid


# =============================================================================
# PUT /api/user/preferences/ — update market_data_source
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["platform", "smartapi", "kite", "upstox", "dhan", "fyers", "paytm"])
async def test_update_market_data_source_valid(client, source):
    """All 7 valid market_data_source values should be accepted."""
    response = await client.put("/api/user/preferences/", json={"market_data_source": source})
    assert response.status_code == 200, (
        f"Expected 200 for source={source}, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert data["market_data_source"] == source


@pytest.mark.asyncio
async def test_update_market_data_source_invalid(client):
    """Invalid market_data_source should return 400 or 422."""
    response = await client.put("/api/user/preferences/", json={"market_data_source": "invalid_broker"})
    assert response.status_code in (400, 422)


# =============================================================================
# PUT /api/user/preferences/ — update order_broker
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("broker", ["kite", "angel", "upstox", "dhan", "fyers", "paytm"])
async def test_update_order_broker_valid(client, broker):
    """All 6 valid order_broker values should be accepted."""
    response = await client.put("/api/user/preferences/", json={"order_broker": broker})
    assert response.status_code == 200, (
        f"Expected 200 for broker={broker}, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert data["order_broker"] == broker


@pytest.mark.asyncio
async def test_update_order_broker_invalid(client):
    """Invalid order_broker should return 400 or 422."""
    response = await client.put("/api/user/preferences/", json={"order_broker": "not_a_broker"})
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_update_both_broker_fields(client):
    """Can update both market_data_source and order_broker together."""
    response = await client.put("/api/user/preferences/", json={
        "market_data_source": "dhan",
        "order_broker": "upstox"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["market_data_source"] == "dhan"
    assert data["order_broker"] == "upstox"


@pytest.mark.asyncio
async def test_update_preserves_pnl_grid_interval(client):
    """Updating broker fields does not overwrite pnl_grid_interval."""
    # Set pnl_grid_interval to 50
    await client.put("/api/user/preferences/", json={"pnl_grid_interval": 50})
    # Update broker field only
    response = await client.put("/api/user/preferences/", json={"market_data_source": "fyers"})
    assert response.status_code == 200
    data = response.json()
    assert data["pnl_grid_interval"] == 50
    assert data["market_data_source"] == "fyers"
