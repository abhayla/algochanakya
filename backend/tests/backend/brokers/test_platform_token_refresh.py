"""
Platform Token Auto-Refresh Tests

Tests for automatic refresh of platform-level broker tokens on startup.
Covers AngelOne (SmartAPI) and Upstox (HTTP-based TOTP login).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


class TestUpstoxHttpLogin:
    """Tests for Upstox HTTP-based auto-login (no browser)."""

    @pytest.mark.asyncio
    async def test_authenticate_returns_access_token(self):
        """Full HTTP login flow should return an access_token."""
        from app.services.brokers.platform_token_refresh import UpstoxHttpAuth

        auth = UpstoxHttpAuth(
            api_key="test_key",
            api_secret="test_secret",
            redirect_uri="http://localhost:8001/api/auth/upstox/callback",
            login_phone="9999999999",
            login_pin="123456",
            totp_secret="JBSWY3DPEHPK3PXP",
        )

        # Mock the 6-step HTTP flow
        mock_responses = {
            "dialog": MagicMock(status_code=200, url="https://service.upstox.com/login?user_id=UP123&client_id=test"),
            "otp": MagicMock(status_code=200, json=lambda: {"data": {"validateOTPToken": "otp_token_123"}}),
            "verify": MagicMock(status_code=200, json=lambda: {"status": "success"}),
            "2fa": MagicMock(status_code=200, json=lambda: {"status": "success"}),
            "authorize": MagicMock(status_code=200, url="http://localhost:8001/api/auth/upstox/callback?code=auth_code_xyz"),
            "token": MagicMock(status_code=200, json=lambda: {"access_token": "fresh_upstox_token"}),
        }

        with patch.object(auth, "_execute_login_flow", return_value="fresh_upstox_token"):
            token = await auth.authenticate()

        assert token == "fresh_upstox_token"

    def test_requires_all_credentials(self):
        """Should raise if any credential is missing."""
        from app.services.brokers.platform_token_refresh import UpstoxHttpAuth

        with pytest.raises(ValueError, match="Missing"):
            UpstoxHttpAuth(
                api_key="test_key",
                api_secret="",  # missing
                redirect_uri="http://localhost:8001/callback",
                login_phone="9999999999",
                login_pin="123456",
                totp_secret="SECRET",
            )


class TestPlatformTokenRefreshService:
    """Tests for the orchestrator that refreshes all platform tokens."""

    @pytest.mark.asyncio
    async def test_refresh_skips_valid_tokens(self):
        """Should not refresh tokens that are still valid."""
        from app.services.brokers.platform_token_refresh import refresh_platform_tokens

        with patch("app.services.brokers.platform_token_refresh.settings") as mock_settings, \
             patch("app.services.brokers.platform_token_refresh._is_upstox_token_expired", return_value=False), \
             patch("app.services.brokers.platform_token_refresh._is_smartapi_token_expired", return_value=False):
            mock_settings.UPSTOX_ACCESS_TOKEN = "valid_token"
            mock_settings.ANGEL_API_KEY = "key"

            results = await refresh_platform_tokens()

        assert results["upstox"] == "skipped"
        assert results["angelone"] == "skipped"

    @pytest.mark.asyncio
    async def test_refresh_refreshes_expired_upstox(self):
        """Should refresh Upstox token when expired."""
        from app.services.brokers.platform_token_refresh import refresh_platform_tokens

        with patch("app.services.brokers.platform_token_refresh.settings") as mock_settings, \
             patch("app.services.brokers.platform_token_refresh._is_upstox_token_expired", return_value=True), \
             patch("app.services.brokers.platform_token_refresh._is_smartapi_token_expired", return_value=False), \
             patch("app.services.brokers.platform_token_refresh._refresh_upstox_token", return_value="new_token") as mock_refresh:
            mock_settings.UPSTOX_ACCESS_TOKEN = "expired"
            mock_settings.UPSTOX_API_KEY = "key"
            mock_settings.UPSTOX_API_SECRET = "secret"
            mock_settings.UPSTOX_REDIRECT_URL = "http://localhost/callback"
            mock_settings.UPSTOX_LOGIN_PHONE = "9999999999"
            mock_settings.UPSTOX_LOGIN_PIN = "123456"
            mock_settings.UPSTOX_TOTP_SECRET = "SECRET"
            mock_settings.ANGEL_API_KEY = "key"

            results = await refresh_platform_tokens()

        assert results["upstox"] == "refreshed"
        mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_handles_failure_gracefully(self):
        """Should not crash if refresh fails — just log and continue."""
        from app.services.brokers.platform_token_refresh import refresh_platform_tokens

        with patch("app.services.brokers.platform_token_refresh.settings") as mock_settings, \
             patch("app.services.brokers.platform_token_refresh._is_upstox_token_expired", return_value=True), \
             patch("app.services.brokers.platform_token_refresh._is_smartapi_token_expired", return_value=False), \
             patch("app.services.brokers.platform_token_refresh._refresh_upstox_token", side_effect=Exception("Network error")):
            mock_settings.UPSTOX_ACCESS_TOKEN = "expired"
            mock_settings.UPSTOX_API_KEY = "key"
            mock_settings.UPSTOX_API_SECRET = "secret"
            mock_settings.UPSTOX_REDIRECT_URL = "http://localhost/callback"
            mock_settings.UPSTOX_LOGIN_PHONE = "9999999999"
            mock_settings.UPSTOX_LOGIN_PIN = "123456"
            mock_settings.UPSTOX_TOTP_SECRET = "SECRET"
            mock_settings.ANGEL_API_KEY = "key"

            results = await refresh_platform_tokens()

        assert results["upstox"] == "failed"
        assert results["angelone"] == "skipped"
