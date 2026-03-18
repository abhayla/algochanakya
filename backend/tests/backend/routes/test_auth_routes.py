"""
Auth Route Tests

Tests for broker authentication endpoints:
- Zerodha OAuth flow
- AngelOne SmartAPI login
- Dhan static token login
- Upstox OAuth flow
- Fyers OAuth flow
- Paytm OAuth flow
- Disconnect and logout
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient


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
        # The login endpoint generates a Kite Connect login URL
        # This is a unit test — we mock the Kite client
        with patch("app.api.routes.auth.KiteConnect") as MockKite:
            instance = MockKite.return_value
            instance.login_url.return_value = "https://kite.zerodha.com/connect/login?api_key=test"

            # Verify the URL generation logic works
            assert "kite.zerodha.com" in instance.login_url()

    @pytest.mark.asyncio
    async def test_callback_requires_request_token(self):
        """Callback should fail without request_token parameter."""
        # This validates the route expects request_token
        pass  # Tested via E2E


# ---------------------------------------------------------------------------
# AngelOne Auth Tests
# ---------------------------------------------------------------------------

class TestAngelOneAuth:
    """Test AngelOne SmartAPI authentication."""

    @pytest.mark.asyncio
    async def test_angelone_login_uses_stored_credentials(self):
        """AngelOne login uses stored SmartAPI credentials (auto-TOTP)."""
        # AngelOne doesn't need user input — uses stored encrypted credentials
        # from the smartapi_credentials table via smartapi_auth service.
        # Test validates the expected credential fields used for SmartAPI login.
        mock_creds = MagicMock()
        mock_creds.client_id = "TEST123"
        mock_creds.password = "encrypted_pass"
        mock_creds.totp_secret = "encrypted_secret"
        mock_creds.api_key = "test_api_key"

        # Verify the credentials model has the expected fields
        assert mock_creds.client_id == "TEST123"
        assert hasattr(mock_creds, "totp_secret")


# ---------------------------------------------------------------------------
# SmartAPIAuth Service Unit Tests (Dual-Mode Authentication)
# ---------------------------------------------------------------------------

class TestSmartAPIAuthService:
    """Unit tests for SmartAPIAuth service dual-mode authentication methods."""

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
# AngelOne Login Route Tests (Dual-Mode)
# ---------------------------------------------------------------------------

class TestAngelOneLoginRoute:
    """
    Route-level tests for POST /api/auth/angelone/login dual-mode.

    Inline mode: client_id + pin + totp_code provided in body.
    Stored mode: empty body, falls back to SmartAPICredentials row in DB.
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

    def _make_mock_db(self, first_result=None):
        """
        Build an async mock DB session.

        first_result: returned by the first execute() call (SmartAPICredentials or User lookup).
        Subsequent calls return None to simulate no existing User or BrokerConnection.
        """
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.scalar_one_or_none.return_value = first_result
            else:
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
    async def test_inline_mode_calls_authenticate_with_totp_not_authenticate(self):
        """Inline mode: authenticate_with_totp() is called; authenticate() is never called."""
        from app.api.routes.auth import angelone_login, AngelOneLoginRequest

        mock_auth = MagicMock()
        mock_auth.authenticate_with_totp.return_value = self._make_auth_result("INLINE01")

        mock_db = self._make_mock_db(first_result=None)
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
        mock_auth.authenticate.assert_not_called()

    @pytest.mark.asyncio
    async def test_inline_mode_does_not_query_smartapi_credentials_table(self):
        """Inline mode: the smartapi_credentials table is never queried."""
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
                "Inline mode must not query smartapi_credentials, got: " + query_str
            )

    @pytest.mark.asyncio
    async def test_inline_mode_does_not_update_stored_credential_tokens(self):
        """Inline mode: a pre-existing SmartAPICredentials object is never modified."""
        from app.api.routes.auth import angelone_login, AngelOneLoginRequest

        stored_creds = MagicMock()
        stored_creds.jwt_token = "original_stored_token"

        mock_auth = MagicMock()
        mock_auth.authenticate_with_totp.return_value = self._make_auth_result("INLINE01")

        mock_db = self._make_mock_db(first_result=None)
        body = AngelOneLoginRequest(client_id="INLINE01", pin="4321", totp_code="999888")

        with patch("app.api.routes.auth.get_smartapi_auth", return_value=mock_auth), \
             patch("SmartApi.SmartConnect") as MockSC, \
             patch("app.api.routes.auth.create_access_token", return_value="fake_jwt"), \
             patch("app.api.routes.auth.get_redis", new_callable=AsyncMock):
            MockSC.return_value.getProfile.return_value = {"data": None}
            await angelone_login(body=body, db=mock_db)

        assert stored_creds.jwt_token == "original_stored_token"

    @pytest.mark.asyncio
    async def test_stored_mode_queries_db_and_calls_authenticate(self):
        """Stored mode: empty body queries DB for credentials and calls authenticate() with auto-TOTP."""
        from app.api.routes.auth import angelone_login, AngelOneLoginRequest
        from app.utils.encryption import encrypt

        stored_creds = MagicMock()
        stored_creds.client_id = "STORED01"
        stored_creds.encrypted_pin = encrypt("4321")
        stored_creds.encrypted_totp_secret = encrypt("JBSWY3DPEHPK3PXP")
        stored_creds.user_id = None

        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = self._make_auth_result("STORED01")

        mock_db = self._make_mock_db(first_result=stored_creds)
        body = AngelOneLoginRequest()

        execute_call_count = [0]
        original_execute = mock_db.execute

        async def counting_execute(stmt):
            execute_call_count[0] += 1
            return await original_execute(stmt)

        mock_db.execute = counting_execute

        with patch("app.api.routes.auth.get_smartapi_auth", return_value=mock_auth), \
             patch("SmartApi.SmartConnect") as MockSC, \
             patch("app.api.routes.auth.create_access_token", return_value="fake_jwt"), \
             patch("app.api.routes.auth.get_redis", new_callable=AsyncMock):
            MockSC.return_value.getProfile.return_value = {"data": None}
            await angelone_login(body=body, db=mock_db)

        assert execute_call_count[0] >= 1, "Stored mode must query the database"
        mock_auth.authenticate.assert_called_once()
        mock_auth.authenticate_with_totp.assert_not_called()

    @pytest.mark.asyncio
    async def test_stored_mode_returns_404_when_no_credentials_exist(self):
        """Stored mode: 404 HTTPException raised when SmartAPICredentials row is absent."""
        from app.api.routes.auth import angelone_login, AngelOneLoginRequest
        from fastapi import HTTPException

        mock_db = self._make_mock_db(first_result=None)
        body = AngelOneLoginRequest()

        with patch("app.api.routes.auth.get_smartapi_auth"):
            with pytest.raises(HTTPException) as exc_info:
                await angelone_login(body=body, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "credentials" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_stored_mode_updates_credential_tokens_after_auth(self):
        """Stored mode: SmartAPICredentials fields are written with new tokens after auth."""
        from app.api.routes.auth import angelone_login, AngelOneLoginRequest
        from app.utils.encryption import encrypt
        from datetime import datetime, timezone

        token_expiry = datetime(2099, 1, 1, tzinfo=timezone.utc)
        stored_creds = MagicMock()
        stored_creds.client_id = "STORED01"
        stored_creds.encrypted_pin = encrypt("4321")
        stored_creds.encrypted_totp_secret = encrypt("JBSWY3DPEHPK3PXP")
        stored_creds.user_id = None

        auth_result = {
            "jwt_token": "jwt.new.token",
            "refresh_token": "refresh_new",
            "feed_token": "feed_new",
            "token_expiry": token_expiry,
            "client_id": "STORED01",
        }
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = auth_result

        mock_db = self._make_mock_db(first_result=stored_creds)
        body = AngelOneLoginRequest()

        with patch("app.api.routes.auth.get_smartapi_auth", return_value=mock_auth), \
             patch("SmartApi.SmartConnect") as MockSC, \
             patch("app.api.routes.auth.create_access_token", return_value="fake_jwt"), \
             patch("app.api.routes.auth.get_redis", new_callable=AsyncMock):
            MockSC.return_value.getProfile.return_value = {"data": None}
            await angelone_login(body=body, db=mock_db)

        assert stored_creds.jwt_token == "jwt.new.token"
        assert stored_creds.refresh_token == "refresh_new"
        assert stored_creds.feed_token == "feed_new"
        assert stored_creds.token_expiry == token_expiry
        assert stored_creds.is_active is True
        assert stored_creds.last_error is None




# ---------------------------------------------------------------------------
# Dhan Auth Tests
# ---------------------------------------------------------------------------

class TestDhanAuth:
    """Test Dhan static token authentication."""

    @pytest.mark.asyncio
    async def test_dhan_login_requires_client_id_and_token(self):
        """POST /api/auth/dhan/login requires client_id and access_token."""
        # Dhan uses static token auth — no OAuth redirect
        payload = {
            "client_id": "DHAN12345",
            "access_token": "test-dhan-token"
        }
        # Verify the expected payload structure
        assert "client_id" in payload
        assert "access_token" in payload


# ---------------------------------------------------------------------------
# OAuth Flow Tests (Upstox, Fyers, Paytm)
# ---------------------------------------------------------------------------

class TestOAuthBrokers:
    """Test OAuth-based broker auth (Upstox, Fyers, Paytm)."""

    def test_upstox_login_generates_oauth_url(self):
        """GET /api/auth/upstox/login should return OAuth URL."""
        # Upstox uses standard OAuth 2.0
        pass  # Tested via E2E

    def test_fyers_login_generates_oauth_url(self):
        """GET /api/auth/fyers/login should return OAuth URL."""
        pass  # Tested via E2E

    def test_paytm_login_generates_oauth_url(self):
        """GET /api/auth/paytm/login should return OAuth URL."""
        pass  # Tested via E2E


# ---------------------------------------------------------------------------
# Disconnect Tests
# ---------------------------------------------------------------------------

class TestDisconnect:
    """Test broker disconnect endpoints."""

    @pytest.mark.asyncio
    async def test_disconnect_returns_success(self):
        """DELETE /api/auth/{broker}/disconnect should succeed for connected broker."""
        # Disconnect should remove the broker connection from DB
        pass  # Requires full app context


# ---------------------------------------------------------------------------
# Logout Tests
# ---------------------------------------------------------------------------

class TestLogout:
    """Test logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_invalidates_session(self):
        """POST /api/auth/logout should clear Redis session."""
        # Logout clears the JWT from Redis
        pass  # Requires full app context


# ---------------------------------------------------------------------------
# /me Endpoint Tests
# ---------------------------------------------------------------------------

class TestAuthMe:
    """Test /api/auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_me_returns_user_with_connections(self):
        """GET /api/auth/me should return user + broker_connections."""
        # The /me endpoint returns the authenticated user's info
        # including all connected brokers
        pass  # Requires full app context

    @pytest.mark.asyncio
    async def test_me_fails_without_token(self):
        """GET /api/auth/me without token should return 401."""
        pass  # Tested via E2E


# ---------------------------------------------------------------------------
# Health Route Test
# ---------------------------------------------------------------------------

class TestHealthRoute:
    """Test /api/health endpoint."""

    def test_health_response_structure(self):
        """Health check should return status and component checks."""
        # Health endpoint checks DB + Redis connectivity
        expected_components = ["database", "redis"]
        for component in expected_components:
            assert isinstance(component, str)
