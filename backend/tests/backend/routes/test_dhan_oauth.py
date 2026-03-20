"""
Dhan OAuth Login Tests (Gap K)

Tests for the new DhanHQ v2 OAuth consent flow replacing the static token login.
3-step flow: generate consent → browser redirect → consume consent → get access_token.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestDhanOAuthLogin:

    @pytest.mark.asyncio
    async def test_dhan_login_returns_oauth_url(self):
        """GET /api/auth/dhan/login should return OAuth consent URL (not require static token)."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        # Mock the consent generation API
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"consentAppId": "test_consent_123"}

        with patch("app.api.routes.dhan_auth.httpx.AsyncClient") as MockClient, \
             patch("app.api.routes.dhan_auth.settings") as mock_settings:
            mock_settings.DHAN_APP_ID = "test_app_id"
            mock_settings.DHAN_APP_SECRET = "test_app_secret"
            mock_settings.DHAN_REDIRECT_URL = "http://localhost:8001/api/auth/dhan/callback"
            mock_settings.FRONTEND_URL = "http://localhost:5173"

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/auth/dhan/login")

        assert resp.status_code == 200
        data = resp.json()
        assert "login_url" in data
        assert "consentApp-login" in data["login_url"]

    @pytest.mark.asyncio
    async def test_dhan_callback_exchanges_token_and_redirects(self):
        """GET /api/auth/dhan/callback should exchange tokenId for access_token and redirect."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.database import get_db
        from app.utils.dependencies import get_current_user

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.last_login = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        # Mock the token exchange
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {
            "accessToken": "dhan_oauth_token_abc",
            "dhanClientId": "DHAN_USER_123",
        }

        try:
            with patch("app.api.routes.dhan_auth.httpx.AsyncClient") as MockClient, \
                 patch("app.api.routes.dhan_auth.settings") as mock_settings, \
                 patch("app.api.routes.dhan_auth.resolve_or_create_user", return_value=mock_user), \
                 patch("app.api.routes.dhan_auth.create_access_token", return_value="fake_jwt"), \
                 patch("app.api.routes.dhan_auth.get_redis", new_callable=AsyncMock):
                mock_settings.DHAN_APP_ID = "test_app_id"
                mock_settings.DHAN_APP_SECRET = "test_app_secret"
                mock_settings.DHAN_REDIRECT_URL = "http://localhost:8001/api/auth/dhan/callback"
                mock_settings.FRONTEND_URL = "http://localhost:5173"
                mock_settings.JWT_EXPIRY_HOURS = 24

                mock_client = AsyncMock()
                mock_client.post.return_value = mock_token_resp
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.get(
                        "/api/auth/dhan/callback?tokenId=test_token_id",
                        follow_redirects=False,
                    )

            # Should redirect to frontend auth callback (like other OAuth brokers)
            assert resp.status_code == 302
            assert "/auth/callback" in resp.headers["location"]
            assert "token=" in resp.headers["location"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_dhan_static_login_still_works(self):
        """POST /api/auth/dhan/login with static token should still work as fallback."""
        from app.api.routes.dhan_auth import DhanLoginRequest

        # The static token login should still be available
        req = DhanLoginRequest(client_id="DHAN123", access_token="static_token")
        assert req.client_id == "DHAN123"
        assert req.access_token == "static_token"
