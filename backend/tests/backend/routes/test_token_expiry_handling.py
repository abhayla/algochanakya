"""
Token Expiry Handling Tests (Gaps D & E)

Tests that _ensure_broker_credentials() checks token_expiry on user credentials,
marks expired credentials as inactive, and includes token_expiry in pool cache.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, BigInteger, select
from sqlalchemy.ext.compiler import compiles

from app.database import Base
from app.models.broker_api_credentials import BrokerAPICredentials


# SQLite adapters
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


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def test_user_id():
    return uuid4()

@pytest.fixture
def mock_user(test_user_id):
    user = MagicMock()
    user.id = test_user_id
    return user

@pytest.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DB_URL, poolclass=StaticPool,
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
def mock_pool():
    pool = MagicMock()
    pool._credentials = {}
    pool.set_credentials = MagicMock()
    pool.credentials_valid = MagicMock(return_value=False)
    pool.clear_expired_credentials = MagicMock(return_value=[])
    return pool


class TestExpiredUserCredentialsSkipped:
    """User creds with expired token_expiry should be skipped (fall through to .env)."""

    @pytest.mark.asyncio
    async def test_dhan_skips_expired_user_creds(
        self, db_session, mock_user, mock_pool, test_user_id
    ):
        """Dhan should skip user creds when token_expiry is in the past."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        cred = BrokerAPICredentials(
            user_id=test_user_id, broker="dhan",
            client_id="EXPIRED_DHAN", access_token="expired_token",
            token_expiry=past, is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            mock_settings.DHAN_CLIENT_ID = "ENV_DHAN"
            mock_settings.DHAN_ACCESS_TOKEN = "env_token"
            result = await _ensure_broker_credentials("dhan", mock_user, db_session)

        assert result is True
        call_args = mock_pool.set_credentials.call_args[0][1]
        # Should use .env creds, not the expired user creds
        assert call_args["client_id"] == "ENV_DHAN"

    @pytest.mark.asyncio
    async def test_fyers_skips_expired_user_creds(
        self, db_session, mock_user, mock_pool, test_user_id
    ):
        """Fyers should skip user creds when token_expiry is in the past."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        cred = BrokerAPICredentials(
            user_id=test_user_id, broker="fyers",
            client_id="EXPIRED_FYERS", access_token="expired_token",
            token_expiry=past, is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            mock_settings.FYERS_APP_ID = "env_fyers"
            mock_settings.FYERS_ACCESS_TOKEN = "env_fyers_token"
            result = await _ensure_broker_credentials("fyers", mock_user, db_session)

        assert result is True
        call_args = mock_pool.set_credentials.call_args[0][1]
        assert call_args["access_token"] == "env_fyers_token"

    @pytest.mark.asyncio
    async def test_kite_skips_expired_user_creds(
        self, db_session, mock_user, mock_pool, test_user_id
    ):
        """Kite should skip user creds when token_expiry is in the past."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        cred = BrokerAPICredentials(
            user_id=test_user_id, broker="zerodha",
            api_key="expired_kite_key", access_token="expired_token",
            token_expiry=past, is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            mock_settings.KITE_API_KEY = "env_kite_key"
            mock_settings.KITE_ACCESS_TOKEN = "env_kite_token"
            result = await _ensure_broker_credentials("kite", mock_user, db_session)

        assert result is True
        call_args = mock_pool.set_credentials.call_args[0][1]
        assert call_args["api_key"] == "env_kite_key"


class TestTokenExpiryIncludedInPoolCache:
    """set_credentials should include token_expiry for TickerPool cache validation."""

    @pytest.mark.asyncio
    async def test_dhan_user_creds_include_token_expiry(
        self, db_session, mock_user, mock_pool, test_user_id
    ):
        """Dhan set_credentials should include token_expiry from user creds."""
        future = datetime.now(timezone.utc) + timedelta(hours=12)
        cred = BrokerAPICredentials(
            user_id=test_user_id, broker="dhan",
            client_id="DHAN_VALID", access_token="valid_token",
            token_expiry=future, is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            mock_settings.DHAN_CLIENT_ID = "env"
            mock_settings.DHAN_ACCESS_TOKEN = "env"
            await _ensure_broker_credentials("dhan", mock_user, db_session)

        call_args = mock_pool.set_credentials.call_args[0][1]
        assert "token_expiry" in call_args
        assert call_args["token_expiry"] == future
