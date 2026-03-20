"""Tests for the refactored websocket.py route (Phase 4 ticker architecture)."""

import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

from app.api.routes.websocket import (
    _authenticate_user,
    _get_market_data_source,
    _ensure_broker_credentials,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_mock_user(user_id=None):
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id or uuid4()
    return user


def make_mock_db():
    """Create a mock AsyncSession."""
    db = AsyncMock()
    return db


def make_mock_prefs(source="smartapi"):
    """Create a mock UserPreferences."""
    prefs = MagicMock()
    prefs.market_data_source = source
    return prefs


def make_mock_smartapi_credentials(
    access_token="test-jwt", feed_token="test-feed", client_id="TEST001",
    token_expiry=None,
):
    """Create a mock BrokerAPICredentials for SmartAPI."""
    creds = MagicMock()
    creds.access_token = access_token
    creds.feed_token = feed_token
    creds.client_id = client_id
    creds.token_expiry = token_expiry
    return creds


def make_mock_broker_connection(access_token="test-access-token"):
    """Create a mock BrokerConnection."""
    conn = MagicMock()
    conn.access_token = access_token
    return conn


# ─── _authenticate_user ──────────────────────────────────────────────────────


class TestAuthenticateUser:
    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.verify_access_token")
    async def test_authenticate_success(self, mock_verify):
        user_id = uuid4()
        mock_verify.return_value = {"user_id": str(user_id)}

        mock_user = make_mock_user(user_id)
        db = make_mock_db()

        # Mock the DB query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = mock_result

        user = await _authenticate_user("valid-jwt", db)
        assert user.id == user_id
        mock_verify.assert_called_once_with("valid-jwt")

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.verify_access_token")
    async def test_authenticate_invalid_token(self, mock_verify):
        mock_verify.side_effect = Exception("Token expired")
        db = make_mock_db()

        with pytest.raises(Exception, match="Token expired"):
            await _authenticate_user("bad-jwt", db)

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.verify_access_token")
    async def test_authenticate_missing_user_id(self, mock_verify):
        mock_verify.return_value = {}  # No user_id
        db = make_mock_db()

        with pytest.raises(Exception, match="missing user_id"):
            await _authenticate_user("jwt-no-uid", db)

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.verify_access_token")
    async def test_authenticate_user_not_found(self, mock_verify):
        mock_verify.return_value = {"user_id": str(uuid4())}
        db = make_mock_db()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(Exception, match="User not found"):
            await _authenticate_user("jwt-unknown-user", db)


# ─── _get_market_data_source ─────────────────────────────────────────────────


class TestGetMarketDataSource:
    @pytest.mark.asyncio
    async def test_returns_user_preference(self):
        db = make_mock_db()
        prefs = make_mock_prefs("kite")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = prefs
        db.execute.return_value = mock_result

        source = await _get_market_data_source(uuid4(), db)
        assert source == "kite"

    @pytest.mark.asyncio
    async def test_defaults_to_smartapi(self):
        db = make_mock_db()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        source = await _get_market_data_source(uuid4(), db)
        assert source == "smartapi"

    @pytest.mark.asyncio
    async def test_defaults_when_source_is_none(self):
        db = make_mock_db()
        prefs = make_mock_prefs(None)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = prefs
        db.execute.return_value = mock_result

        source = await _get_market_data_source(uuid4(), db)
        assert source == "smartapi"


# ─── _ensure_broker_credentials ──────────────────────────────────────────────


class TestEnsureBrokerCredentials:
    @pytest.fixture(autouse=True)
    def reset_pool(self):
        """Reset TickerPool singleton before each test."""
        from app.services.brokers.market_data.ticker import TickerPool
        TickerPool.reset_instance()
        yield
        TickerPool.reset_instance()

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.get_valid_smartapi_credentials")
    async def test_smartapi_credentials_loaded(self, mock_get_creds):
        from app.services.brokers.market_data.ticker import TickerPool

        creds = make_mock_smartapi_credentials()
        mock_get_creds.return_value = creds

        pool = TickerPool.get_instance()
        user = make_mock_user()
        db = make_mock_db()

        # Mock DB to return empty results for both kite and smartapi token queries
        # (triggers hardcoded index fallback)
        mock_empty_result = MagicMock()
        mock_empty_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_empty_result

        result = await _ensure_broker_credentials("smartapi", user, db)
        assert result is True
        assert "smartapi" in pool._credentials
        assert pool._credentials["smartapi"]["jwt_token"] == "test-jwt"
        assert pool._credentials["smartapi"]["feed_token"] == "test-feed"
        # token_map must be present (either from DB or hardcoded fallback)
        assert "token_map" in pool._credentials["smartapi"]

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.get_valid_smartapi_credentials")
    async def test_smartapi_empty_db_uses_fallback_token_map(self, mock_get_creds):
        """When DB returns no rows, hardcoded index token fallback is used."""
        from app.services.brokers.market_data.ticker import TickerPool

        creds = make_mock_smartapi_credentials()
        mock_get_creds.return_value = creds

        pool = TickerPool.get_instance()
        user = make_mock_user()
        db = make_mock_db()

        mock_empty_result = MagicMock()
        mock_empty_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_empty_result

        result = await _ensure_broker_credentials("smartapi", user, db)
        assert result is True
        token_map = pool._credentials["smartapi"]["token_map"]
        # Fallback must include NIFTY index token
        assert 256265 in token_map, "NIFTY token 256265 missing from fallback token_map"
        assert 260105 in token_map, "BANKNIFTY token 260105 missing from fallback token_map"
        assert 257801 in token_map, "FINNIFTY token 257801 missing from fallback token_map"
        assert 265 in token_map, "SENSEX token 265 missing from fallback token_map"

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.get_valid_smartapi_credentials")
    async def test_smartapi_no_credentials(self, mock_get_creds):
        mock_get_creds.return_value = None

        user = make_mock_user()
        db = make_mock_db()

        result = await _ensure_broker_credentials("smartapi", user, db)
        assert result is False

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket._get_user_broker_creds")
    async def test_kite_credentials_loaded_from_user_creds(self, mock_get_creds):
        """User-level BrokerAPICredentials are used for kite when available."""
        from app.services.brokers.market_data.ticker import TickerPool

        pool = TickerPool.get_instance()
        user = make_mock_user()
        db = make_mock_db()

        user_creds = MagicMock()
        user_creds.access_token = "user-kite-token"
        user_creds.api_key = "user-kite-api-key"
        user_creds.token_expiry = None  # No expiry = valid
        mock_get_creds.return_value = user_creds

        result = await _ensure_broker_credentials("kite", user, db)
        assert result is True
        assert "kite" in pool._credentials
        assert pool._credentials["kite"]["access_token"] == "user-kite-token"

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.settings")
    @patch("app.api.routes.websocket._get_user_broker_creds")
    async def test_kite_no_user_creds_falls_back_to_env(self, mock_get_creds, mock_settings):
        """When no user credentials, falls back to platform .env credentials."""
        from app.services.brokers.market_data.ticker import TickerPool

        pool = TickerPool.get_instance()
        user = make_mock_user()
        db = make_mock_db()

        mock_get_creds.return_value = None
        mock_settings.KITE_API_KEY = "env-api-key"
        mock_settings.KITE_ACCESS_TOKEN = "env-access-token"

        result = await _ensure_broker_credentials("kite", user, db)
        assert result is True
        assert pool._credentials["kite"]["access_token"] == "env-access-token"

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.settings")
    @patch("app.api.routes.websocket._get_user_broker_creds")
    async def test_kite_no_credentials_at_all(self, mock_get_creds, mock_settings):
        """Returns False when neither user nor .env credentials are available."""
        user = make_mock_user()
        db = make_mock_db()

        mock_get_creds.return_value = None
        mock_settings.KITE_API_KEY = ""
        mock_settings.KITE_ACCESS_TOKEN = ""

        result = await _ensure_broker_credentials("kite", user, db)
        assert result is False

    @pytest.mark.asyncio
    async def test_already_has_credentials_skips_load(self):
        from app.services.brokers.market_data.ticker import TickerPool

        pool = TickerPool.get_instance()
        pool.set_credentials("smartapi", {"jwt_token": "existing"})

        user = make_mock_user()
        db = make_mock_db()

        result = await _ensure_broker_credentials("smartapi", user, db)
        assert result is True
        # Should not have called DB — credentials already present
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_broker_returns_false(self):
        user = make_mock_user()
        db = make_mock_db()

        result = await _ensure_broker_credentials("nonexistent_broker", user, db)
        assert result is False


# ─── WebSocket Route Integration ─────────────────────────────────────────────


class TestWebSocketRouteNoLegacyImports:
    """Verify the refactored route no longer imports legacy services."""

    def test_no_legacy_smartapi_ticker_import(self):
        """Ensure legacy smartapi_ticker_service is not imported."""
        import app.api.routes.websocket as ws_module
        source = open(ws_module.__file__).read()
        assert "smartapi_ticker_service" not in source
        assert "from app.services.legacy.smartapi_ticker" not in source

    def test_no_legacy_kite_ticker_import(self):
        """Ensure legacy kite_ticker_service is not imported."""
        import app.api.routes.websocket as ws_module
        source = open(ws_module.__file__).read()
        assert "kite_ticker_service" not in source
        assert "from app.services.legacy.kite_ticker" not in source

    def test_imports_new_ticker_components(self):
        """Ensure new ticker architecture components are imported."""
        import app.api.routes.websocket as ws_module
        source = open(ws_module.__file__).read()
        assert "TickerPool" in source
        assert "TickerRouter" in source

    def test_no_smartapi_market_data_import(self):
        """Ensure legacy SmartAPIMarketData is not imported."""
        import app.api.routes.websocket as ws_module
        source = open(ws_module.__file__).read()
        assert "SmartAPIMarketData" not in source
        assert "from app.services.legacy.smartapi_market_data" not in source

    def test_line_count_reduced(self):
        """Route should be smaller than the original legacy 494 lines.
        Now supports all 6 brokers with user-creds → .env → fallback credential chain,
        so ~475 lines is expected (still broker-agnostic in the message loop).
        """
        import app.api.routes.websocket as ws_module
        with open(ws_module.__file__) as f:
            line_count = sum(1 for _ in f)
        assert line_count < 500, f"websocket.py is {line_count} lines (expected < 500)"
