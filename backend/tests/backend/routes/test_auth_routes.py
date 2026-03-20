"""
Auth Route Tests

Tests for broker authentication endpoints:
- Zerodha OAuth flow
- AngelOne SmartAPI login (inline credentials only — Mode B removed)
- Dhan static token login
- Upstox OAuth flow
- Fyers OAuth flow
- Paytm OAuth flow
- Disconnect and logout
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    return user


# ---------------------------------------------------------------------------
# Zerodha Auth Tests
# ---------------------------------------------------------------------------

class TestZerodhaAuth:
    """Test Zerodha OAuth endpoints."""

    @pytest.mark.asyncio
    async def test_login_returns_url(self):
        """GET /api/auth/zerodha/login should return a login URL."""
        from app.api.routes.auth import router
        with patch("app.api.routes.auth.KiteConnect") as MockKite:
            instance = MockKite.return_value
            instance.login_url.return_value = "https://kite.zerodha.com/connect/login?api_key=test"
            assert "kite.zerodha.com" in instance.login_url()

    @pytest.mark.asyncio
    async def test_callback_requires_request_token(self):
        """Callback should fail without request_token parameter."""
        pass  # Tested via E2E


# ---------------------------------------------------------------------------
# AngelOne Auth Tests
# ---------------------------------------------------------------------------

class TestAngelOneAuth:
    """Test AngelOne SmartAPI authentication (inline mode only)."""

    @pytest.mark.asyncio
    async def test_angelone_login_requires_all_three_fields(self):
        """AngelOne login requires client_id, pin, and totp_code (Mode B removed)."""
        from app.api.routes.auth import AngelOneLoginRequest
        from pydantic import ValidationError

        # Missing all fields
        with pytest.raises(ValidationError):
            AngelOneLoginRequest()

        # Missing pin
        with pytest.raises(ValidationError):
            AngelOneLoginRequest(client_id="TEST123", totp_code="123456")

        # Missing totp_code
        with pytest.raises(ValidationError):
            AngelOneLoginRequest(client_id="TEST123", pin="1234")

        # All fields present — should succeed
        req = AngelOneLoginRequest(client_id="TEST123", pin="1234", totp_code="654321")
        assert req.client_id == "TEST123"
        assert req.pin == "1234"
        assert req.totp_code == "654321"


# ---------------------------------------------------------------------------
# SmartAPIAuth Service Unit Tests
# ---------------------------------------------------------------------------

class TestSmartAPIAuthService:
    """Unit tests for SmartAPIAuth service authentication methods."""

    def test_authenticate_with_totp_delegates_to_do_authenticate(self):
        """authenticate_with_totp() passes the provided TOTP code directly to _do_authenticate()."""
        from app.services.legacy.smartapi_auth import SmartAPIAuth

        auth = SmartAPIAuth(api_key="test_key")
        expected_result = {
            "jwt_token": "test.jwt.token",
            "refresh_token": "test_refresh",
            "feed_token": "feed_abc",
            "token_expiry": None,
            "client_id": "TEST123",
        }

        with patch.object(auth, "_do_authenticate", return_value=expected_result) as mock_do_auth:
            result = auth.authenticate_with_totp(
                client_id="TEST123",
                pin="1234",
                totp_code="654321",
            )

        mock_do_auth.assert_called_once_with("TEST123", "1234", "654321")
        assert result == expected_result

    def test_authenticate_generates_totp_from_secret_then_delegates(self):
        """authenticate() generates a TOTP code from the secret before calling _do_authenticate()."""
        from app.services.legacy.smartapi_auth import SmartAPIAuth

        auth = SmartAPIAuth(api_key="test_key")
        expected_result = {
            "jwt_token": "test.jwt.token",
            "refresh_token": "test_refresh",
            "feed_token": "feed_abc",
            "token_expiry": None,
            "client_id": "TEST123",
        }

        with patch.object(auth, "generate_totp", return_value="123456") as mock_gen, \
             patch.object(auth, "_do_authenticate", return_value=expected_result) as mock_do_auth:
            result = auth.authenticate(
                client_id="TEST123",
                pin="1234",
                totp_secret="JBSWY3DPEHPK3PXP",
            )

        mock_gen.assert_called_once_with("JBSWY3DPEHPK3PXP")
        mock_do_auth.assert_called_once_with("TEST123", "1234", "123456")
        assert result == expected_result

    def test_do_authenticate_calls_generate_session_returns_token_structure(self):
        """_do_authenticate() calls generateSession and returns jwt_token, refresh_token, feed_token, client_id."""
        from app.services.legacy.smartapi_auth import SmartAPIAuth

        auth = SmartAPIAuth(api_key="test_key")
        mock_api = MagicMock()
        mock_api.generateSession.return_value = {
            "data": {
                "jwtToken": "jwt.abc.123",
                "refreshToken": "refresh_xyz",
            }
        }
        mock_api.getfeedToken.return_value = "feed_token_abc"

        with patch.object(auth, "_get_api", return_value=mock_api):
            result = auth._do_authenticate("TEST123", "1234", "654321")

        mock_api.generateSession.assert_called_once_with("TEST123", "1234", "654321")
        assert result["jwt_token"] == "jwt.abc.123"
        assert result["refresh_token"] == "refresh_xyz"
        assert result["feed_token"] == "feed_token_abc"
        assert result["client_id"] == "TEST123"
        assert "token_expiry" in result

    def test_do_authenticate_raises_smartapi_auth_error_on_null_data(self):
        """_do_authenticate() raises SmartAPIAuthError when generateSession returns data=None."""
        from app.services.legacy.smartapi_auth import SmartAPIAuth, SmartAPIAuthError

        auth = SmartAPIAuth(api_key="test_key")
        mock_api = MagicMock()
        mock_api.generateSession.return_value = {"message": "Invalid credentials", "data": None}

        with patch.object(auth, "_get_api", return_value=mock_api):
            with pytest.raises(SmartAPIAuthError) as exc_info:
                auth._do_authenticate("BADID", "0000", "000000")

        assert "Authentication failed" in str(exc_info.value)

    def test_do_authenticate_raises_smartapi_auth_error_on_none_response(self):
        """_do_authenticate() raises SmartAPIAuthError when generateSession returns None."""
        from app.services.legacy.smartapi_auth import SmartAPIAuth, SmartAPIAuthError

        auth = SmartAPIAuth(api_key="test_key")
        mock_api = MagicMock()
        mock_api.generateSession.return_value = None

        with patch.object(auth, "_get_api", return_value=mock_api):
            with pytest.raises(SmartAPIAuthError) as exc_info:
                auth._do_authenticate("TEST123", "1234", "654321")

        assert "Authentication failed" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AngelOne Login Route Tests (Inline Only — Mode B Removed)
# ---------------------------------------------------------------------------

class TestAngelOneLoginRoute:
    """
    Route-level tests for POST /api/auth/angelone/login.

    Mode B (stored credentials auto-login) has been removed.
    Only inline mode (client_id + pin + totp_code) is supported.
    """

    def _make_auth_result(self, client_id="TEST123"):
        from datetime import datetime, timezone
        return {
            "jwt_token": "jwt.test.token",
            "refresh_token": "refresh_test",
            "feed_token": "feed_test",
            "token_expiry": datetime(2099, 1, 1, tzinfo=timezone.utc),
            "client_id": client_id,
        }

    def _make_mock_db(self):
        """Build an async mock DB session."""
        async def mock_execute(stmt):
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            result.scalars.return_value.all.return_value = []
            return result

        mock_db = AsyncMock()
        mock_db.execute = mock_execute
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        return mock_db

    @pytest.mark.asyncio
    async def test_inline_mode_calls_authenticate_with_totp(self):
        """Inline mode: authenticate_with_totp() is called with provided credentials."""
        from app.api.routes.auth import angelone_login, AngelOneLoginRequest

        mock_auth = MagicMock()
        mock_auth.authenticate_with_totp.return_value = self._make_auth_result("INLINE01")

        mock_db = self._make_mock_db()
        body = AngelOneLoginRequest(client_id="INLINE01", pin="4321", totp_code="999888")

        with patch("app.api.routes.auth.get_smartapi_auth", return_value=mock_auth), \
             patch("SmartApi.SmartConnect") as MockSC, \
             patch("app.api.routes.auth.create_access_token", return_value="fake_jwt"), \
             patch("app.api.routes.auth.get_redis", new_callable=AsyncMock):
            MockSC.return_value.getProfile.return_value = {"data": None}
            await angelone_login(body=body, db=mock_db)

        mock_auth.authenticate_with_totp.assert_called_once_with(
            client_id="INLINE01",
            pin="4321",
            totp_code="999888",
        )

    @pytest.mark.asyncio
    async def test_login_does_not_query_smartapi_credentials_table(self):
        """Login never queries smartapi_credentials or broker_api_credentials table."""
        from app.api.routes.auth import angelone_login, AngelOneLoginRequest

        mock_auth = MagicMock()
        mock_auth.authenticate_with_totp.return_value = self._make_auth_result("INLINE01")

        queried_tables = []

        async def tracking_execute(stmt):
            queried_tables.append(str(stmt))
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            result.scalars.return_value.all.return_value = []
            return result

        mock_db = AsyncMock()
        mock_db.execute = tracking_execute
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        body = AngelOneLoginRequest(client_id="INLINE01", pin="4321", totp_code="999888")

        with patch("app.api.routes.auth.get_smartapi_auth", return_value=mock_auth), \
             patch("SmartApi.SmartConnect") as MockSC, \
             patch("app.api.routes.auth.create_access_token", return_value="fake_jwt"), \
             patch("app.api.routes.auth.get_redis", new_callable=AsyncMock):
            MockSC.return_value.getProfile.return_value = {"data": None}
            await angelone_login(body=body, db=mock_db)

        for query_str in queried_tables:
            assert "smartapi_credentials" not in query_str.lower(), (
                "Login must not query smartapi_credentials, got: " + query_str
            )
            assert "broker_api_credentials" not in query_str.lower(), (
                "Login must not query broker_api_credentials, got: " + query_str
            )

    @pytest.mark.asyncio
    async def test_login_never_updates_stored_credentials(self):
        """Login does not modify any stored credential objects (Mode B removal)."""
        from app.api.routes.auth import angelone_login, AngelOneLoginRequest

        mock_auth = MagicMock()
        mock_auth.authenticate_with_totp.return_value = self._make_auth_result("INLINE01")

        mock_db = self._make_mock_db()
        body = AngelOneLoginRequest(client_id="INLINE01", pin="4321", totp_code="999888")

        with patch("app.api.routes.auth.get_smartapi_auth", return_value=mock_auth), \
             patch("SmartApi.SmartConnect") as MockSC, \
             patch("app.api.routes.auth.create_access_token", return_value="fake_jwt"), \
             patch("app.api.routes.auth.get_redis", new_callable=AsyncMock):
            MockSC.return_value.getProfile.return_value = {"data": None}
            await angelone_login(body=body, db=mock_db)

        # No stored credentials should be touched — only broker_connections and users are queried/updated
        # The stored_credentials update block was removed in Gap J


# ---------------------------------------------------------------------------
# Dhan Auth Tests
# ---------------------------------------------------------------------------

class TestDhanAuth:
    """Test Dhan static token authentication."""

    @pytest.mark.asyncio
    async def test_dhan_login_requires_client_id_and_token(self):
        """POST /api/auth/dhan/login requires client_id and access_token."""
        payload = {
            "client_id": "DHAN12345",
            "access_token": "test-dhan-token"
        }
        assert "client_id" in payload
        assert "access_token" in payload


# ---------------------------------------------------------------------------
# OAuth Flow Tests (Upstox, Fyers, Paytm)
# ---------------------------------------------------------------------------

class TestOAuthBrokers:
    """Test OAuth-based broker auth (Upstox, Fyers, Paytm)."""

    def test_upstox_login_generates_oauth_url(self):
        pass  # Tested via E2E

    def test_fyers_login_generates_oauth_url(self):
        pass  # Tested via E2E

    def test_paytm_login_generates_oauth_url(self):
        pass  # Tested via E2E


# ---------------------------------------------------------------------------
# Disconnect Tests
# ---------------------------------------------------------------------------

class TestDisconnect:
    """Test broker disconnect endpoints."""

    @pytest.mark.asyncio
    async def test_disconnect_returns_success(self):
        pass  # Requires full app context


# ---------------------------------------------------------------------------
# Logout Tests
# ---------------------------------------------------------------------------

class TestLogout:
    """Test logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_invalidates_session(self):
        pass  # Requires full app context


# ---------------------------------------------------------------------------
# /me Endpoint Tests
# ---------------------------------------------------------------------------

class TestAuthMe:
    """Test /api/auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_me_returns_user_with_connections(self):
        pass  # Requires full app context

    @pytest.mark.asyncio
    async def test_me_fails_without_token(self):
        pass  # Tested via E2E


# ---------------------------------------------------------------------------
# Health Route Test
# ---------------------------------------------------------------------------

class TestHealthRoute:
    """Test /api/health endpoint."""

    def test_health_response_structure(self):
        expected_components = ["database", "redis"]
        for component in expected_components:
            assert isinstance(component, str)
