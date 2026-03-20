"""
Unified BrokerAPICredentials Model Tests

Tests for:
1. Model creation and unique constraint (user_id, broker)
2. smartapi_utils.py querying BrokerAPICredentials (field rename jwt_token → access_token)
3. Integration with credential route endpoints via the unified table
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, BigInteger
from sqlalchemy.ext.compiler import compiles

from app.database import Base


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


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class TestBrokerAPICredentialsModel:

    @pytest.mark.asyncio
    async def test_create_angelone_credentials(self, db_session, test_user_id):
        """Can create AngelOne credentials in unified table."""
        from app.models.broker_api_credentials import BrokerAPICredentials

        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="angelone",
            client_id="A123",
            encrypted_pin="enc_pin",
            encrypted_totp_secret="enc_totp",
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()
        await db_session.refresh(cred)

        assert cred.id is not None
        assert cred.broker == "angelone"
        assert cred.client_id == "A123"

    @pytest.mark.asyncio
    async def test_create_zerodha_credentials(self, db_session, test_user_id):
        """Can create Zerodha credentials in unified table."""
        from app.models.broker_api_credentials import BrokerAPICredentials

        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="zerodha",
            api_key="kite_key_123",
            api_secret="enc_secret",
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()
        await db_session.refresh(cred)

        assert cred.broker == "zerodha"
        assert cred.api_key == "kite_key_123"

    @pytest.mark.asyncio
    async def test_multiple_brokers_per_user(self, db_session, test_user_id):
        """A user can have credentials for multiple brokers."""
        from app.models.broker_api_credentials import BrokerAPICredentials
        from sqlalchemy import select

        for broker in ["angelone", "zerodha", "upstox", "dhan"]:
            cred = BrokerAPICredentials(
                user_id=test_user_id,
                broker=broker,
                api_key=f"key_{broker}",
                is_active=True,
            )
            db_session.add(cred)

        await db_session.commit()

        result = await db_session.execute(
            select(BrokerAPICredentials).where(
                BrokerAPICredentials.user_id == test_user_id
            )
        )
        creds = result.scalars().all()
        assert len(creds) == 4
        brokers = {c.broker for c in creds}
        assert brokers == {"angelone", "zerodha", "upstox", "dhan"}

    @pytest.mark.asyncio
    async def test_unique_constraint_user_broker(self, db_session, test_user_id):
        """Cannot have two rows for same user + broker."""
        from app.models.broker_api_credentials import BrokerAPICredentials
        from sqlalchemy.exc import IntegrityError

        cred1 = BrokerAPICredentials(
            user_id=test_user_id,
            broker="angelone",
            api_key="key1",
            is_active=True,
        )
        db_session.add(cred1)
        await db_session.commit()

        cred2 = BrokerAPICredentials(
            user_id=test_user_id,
            broker="angelone",
            api_key="key2",
            is_active=True,
        )
        db_session.add(cred2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_access_token_field_exists(self, db_session, test_user_id):
        """The unified table uses 'access_token' (not 'jwt_token')."""
        from app.models.broker_api_credentials import BrokerAPICredentials

        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="angelone",
            access_token="jwt.test.token",
            feed_token="feed_test",
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()
        await db_session.refresh(cred)

        assert cred.access_token == "jwt.test.token"
        assert cred.feed_token == "feed_test"
        assert not hasattr(cred, "jwt_token")


# ---------------------------------------------------------------------------
# smartapi_utils Tests (queries BrokerAPICredentials)
# ---------------------------------------------------------------------------

class TestSmartAPIUtils:

    @pytest.mark.asyncio
    async def test_get_valid_credentials_returns_none_when_empty(self, db_session, test_user_id):
        """Returns None when no credentials exist for the user."""
        from app.utils.smartapi_utils import get_valid_smartapi_credentials

        result = await get_valid_smartapi_credentials(test_user_id, db_session, auto_refresh=False)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_valid_credentials_returns_active_angelone(self, db_session, test_user_id):
        """Returns credentials for active AngelOne row with valid token."""
        from app.models.broker_api_credentials import BrokerAPICredentials
        from app.utils.smartapi_utils import get_valid_smartapi_credentials

        future_expiry = datetime.now(timezone.utc) + timedelta(hours=12)
        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="angelone",
            client_id="TEST01",
            access_token="jwt.valid.token",
            feed_token="feed_valid",
            token_expiry=future_expiry,
            last_auth_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        result = await get_valid_smartapi_credentials(test_user_id, db_session, auto_refresh=False)
        assert result is not None
        assert result.access_token == "jwt.valid.token"
        assert result.broker == "angelone"

    @pytest.mark.asyncio
    async def test_get_valid_credentials_ignores_other_brokers(self, db_session, test_user_id):
        """Only returns 'angelone' credentials, not other brokers."""
        from app.models.broker_api_credentials import BrokerAPICredentials
        from app.utils.smartapi_utils import get_valid_smartapi_credentials

        # Add zerodha credentials (should be ignored)
        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="zerodha",
            api_key="kite_key",
            access_token="kite_token",
            is_active=True,
        )
        db_session.add(cred)
        await db_session.commit()

        result = await get_valid_smartapi_credentials(test_user_id, db_session, auto_refresh=False)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_valid_credentials_ignores_inactive(self, db_session, test_user_id):
        """Returns None when credentials exist but are inactive."""
        from app.models.broker_api_credentials import BrokerAPICredentials
        from app.utils.smartapi_utils import get_valid_smartapi_credentials

        cred = BrokerAPICredentials(
            user_id=test_user_id,
            broker="angelone",
            client_id="TEST01",
            access_token="jwt.valid.token",
            is_active=False,
        )
        db_session.add(cred)
        await db_session.commit()

        result = await get_valid_smartapi_credentials(test_user_id, db_session, auto_refresh=False)
        assert result is None

    @pytest.mark.asyncio
    async def test_is_token_expired_with_valid_token(self):
        """is_token_expired returns False for future expiry."""
        from app.utils.smartapi_utils import is_token_expired

        cred = MagicMock()
        cred.access_token = "valid"
        cred.token_expiry = datetime.now(timezone.utc) + timedelta(hours=12)

        assert is_token_expired(cred) is False

    @pytest.mark.asyncio
    async def test_is_token_expired_with_expired_token(self):
        """is_token_expired returns True for past expiry."""
        from app.utils.smartapi_utils import is_token_expired

        cred = MagicMock()
        cred.access_token = "expired"
        cred.token_expiry = datetime.now(timezone.utc) - timedelta(hours=1)

        assert is_token_expired(cred) is True

    @pytest.mark.asyncio
    async def test_is_token_expired_with_no_token(self):
        """is_token_expired returns True when no access_token."""
        from app.utils.smartapi_utils import is_token_expired

        assert is_token_expired(None) is True

        cred = MagicMock()
        cred.access_token = None
        cred.token_expiry = None
        assert is_token_expired(cred) is True
