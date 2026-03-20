"""
WebSocket Credential Loading Tests (Gap P)

Tests that _ensure_broker_credentials() loads from broker_api_credentials
first (user's Settings credentials), then falls back to platform .env.

Priority: user broker_api_credentials → platform .env → fallback
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
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
    user = MagicMock()
    user.id = test_user_id
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
def mock_pool():
    """Mock TickerPool that tracks set_credentials calls."""
    pool = MagicMock()
    pool._credentials = {}
    pool.set_credentials = MagicMock()
    return pool


# ---------------------------------------------------------------------------
# Kite: should check broker_api_credentials first, then .env
# ---------------------------------------------------------------------------

class TestKiteCredentialLoading:

    @pytest.mark.asyncio
    async def test_kite_uses_user_api_credentials_when_available(
        self, db_session, mock_user, mock_pool, test_user_id
    ):
        """Kite should load from broker_api_credentials (user's Settings creds) first."""
        # User has saved Kite API credentials via Settings
        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="zerodha",
            api_key="user_kite_key",
            access_token="user_kite_token",
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool:
            MockPool.get_instance.return_value = mock_pool
            result = await _ensure_broker_credentials("kite", mock_user, db_session)

        assert result is True
        mock_pool.set_credentials.assert_called_once()
        call_args = mock_pool.set_credentials.call_args
        creds_dict = call_args[0][1]
        assert creds_dict["access_token"] == "user_kite_token"

    @pytest.mark.asyncio
    async def test_kite_falls_back_to_env_when_no_user_creds(
        self, db_session, mock_user, mock_pool
    ):
        """Kite falls back to platform .env when no user credentials exist."""
        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            mock_settings.KITE_API_KEY = "platform_kite_key"
            mock_settings.KITE_ACCESS_TOKEN = "platform_kite_token"
            result = await _ensure_broker_credentials("kite", mock_user, db_session)

        # Should use platform .env credentials as fallback
        if result:
            call_args = mock_pool.set_credentials.call_args
            creds_dict = call_args[0][1]
            assert creds_dict["api_key"] == "platform_kite_key"


# ---------------------------------------------------------------------------
# Dhan: should check broker_api_credentials first, then .env
# ---------------------------------------------------------------------------

class TestDhanCredentialLoading:

    @pytest.mark.asyncio
    async def test_dhan_uses_user_api_credentials_when_available(
        self, db_session, mock_user, mock_pool, test_user_id
    ):
        """Dhan should load from broker_api_credentials first."""
        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="dhan",
            client_id="USER_DHAN_123",
            access_token="user_dhan_token",
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            # Platform also has creds, but user creds should take priority
            mock_settings.DHAN_CLIENT_ID = "PLATFORM_DHAN"
            mock_settings.DHAN_ACCESS_TOKEN = "platform_dhan_token"
            result = await _ensure_broker_credentials("dhan", mock_user, db_session)

        assert result is True
        call_args = mock_pool.set_credentials.call_args
        creds_dict = call_args[0][1]
        assert creds_dict["client_id"] == "USER_DHAN_123"
        assert creds_dict["access_token"] == "user_dhan_token"

    @pytest.mark.asyncio
    async def test_dhan_falls_back_to_env(
        self, db_session, mock_user, mock_pool
    ):
        """Dhan falls back to .env when no user credentials."""
        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            mock_settings.DHAN_CLIENT_ID = "ENV_DHAN"
            mock_settings.DHAN_ACCESS_TOKEN = "env_dhan_token"
            result = await _ensure_broker_credentials("dhan", mock_user, db_session)

        assert result is True
        call_args = mock_pool.set_credentials.call_args
        creds_dict = call_args[0][1]
        assert creds_dict["client_id"] == "ENV_DHAN"


# ---------------------------------------------------------------------------
# Upstox: should check broker_api_credentials first, then .env
# ---------------------------------------------------------------------------

class TestUpstoxCredentialLoading:

    @staticmethod
    def _make_future_jwt():
        """Create a fake JWT with exp far in the future."""
        import base64, json, time
        header = base64.b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
        payload = base64.b64encode(json.dumps({"exp": int(time.time()) + 86400}).encode()).decode().rstrip("=")
        return f"{header}.{payload}.fakesig"

    @pytest.mark.asyncio
    async def test_upstox_uses_user_api_credentials_when_available(
        self, db_session, mock_user, mock_pool, test_user_id
    ):
        """Upstox should load from broker_api_credentials first."""
        future_jwt = self._make_future_jwt()
        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="upstox",
            api_key="user_upstox_key",
            access_token=future_jwt,
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            mock_settings.UPSTOX_API_KEY = "platform_key"
            mock_settings.UPSTOX_ACCESS_TOKEN = ""
            result = await _ensure_broker_credentials("upstox", mock_user, db_session)

        assert result is True
        call_args = mock_pool.set_credentials.call_args
        creds_dict = call_args[0][1]
        assert creds_dict["access_token"] == future_jwt


# ---------------------------------------------------------------------------
# Fyers: should check broker_api_credentials first, then .env
# ---------------------------------------------------------------------------

class TestFyersCredentialLoading:

    @pytest.mark.asyncio
    async def test_fyers_uses_user_api_credentials_when_available(
        self, db_session, mock_user, mock_pool, test_user_id
    ):
        """Fyers should load from broker_api_credentials first."""
        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="fyers",
            client_id="FYERS_APP_ID",
            access_token="user_fyers_token",
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            mock_settings.FYERS_APP_ID = "platform_fyers"
            mock_settings.FYERS_ACCESS_TOKEN = "platform_fyers_token"
            result = await _ensure_broker_credentials("fyers", mock_user, db_session)

        assert result is True
        call_args = mock_pool.set_credentials.call_args
        creds_dict = call_args[0][1]
        assert creds_dict["access_token"] == "user_fyers_token"

    @pytest.mark.asyncio
    async def test_fyers_falls_back_to_env(
        self, db_session, mock_user, mock_pool
    ):
        """Fyers falls back to .env when no user credentials."""
        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            mock_settings.FYERS_APP_ID = "env_fyers_app"
            mock_settings.FYERS_ACCESS_TOKEN = "env_fyers_token"
            result = await _ensure_broker_credentials("fyers", mock_user, db_session)

        assert result is True
        call_args = mock_pool.set_credentials.call_args
        creds_dict = call_args[0][1]
        assert creds_dict["access_token"] == "env_fyers_token"


# ---------------------------------------------------------------------------
# Paytm: should check broker_api_credentials first, then .env
# ---------------------------------------------------------------------------

class TestPaytmCredentialLoading:

    @pytest.mark.asyncio
    async def test_paytm_uses_user_api_credentials_when_available(
        self, db_session, mock_user, mock_pool, test_user_id
    ):
        """Paytm should load from broker_api_credentials first."""
        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="paytm",
            access_token="user_paytm_token",
            feed_token="user_public_access_token",
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        from app.api.routes.websocket import _ensure_broker_credentials

        with patch("app.api.routes.websocket.TickerPool") as MockPool, \
             patch("app.api.routes.websocket.settings") as mock_settings:
            MockPool.get_instance.return_value = mock_pool
            mock_settings.PAYTM_API_KEY = "platform_paytm"
            mock_settings.PAYTM_PUBLIC_ACCESS_TOKEN = "platform_public"
            result = await _ensure_broker_credentials("paytm", mock_user, db_session)

        assert result is True
        call_args = mock_pool.set_credentials.call_args
        creds_dict = call_args[0][1]
        # Paytm WebSocket uses public_access_token (stored as feed_token)
        assert creds_dict["public_access_token"] == "user_public_access_token"
