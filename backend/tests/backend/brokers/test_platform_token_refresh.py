"""
Platform Token Auto-Refresh Tests

Tests for automatic refresh of platform-level broker tokens on startup.
Covers AngelOne (SmartAPI) and Upstox (HTTP-based TOTP login).
Also tests refresh_broker_token() dispatcher (Layer 3.1).
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


class TestUpstoxHttpLogin:
    """Tests for Upstox HTTP-based auto-login (no browser)."""

    @pytest.mark.asyncio
    async def test_authenticate_returns_access_token(self):
        """upstox-totp based login should return an access_token."""
        from app.services.brokers.platform_token_refresh import UpstoxHttpAuth

        auth = UpstoxHttpAuth(
            api_key="test_key",
            api_secret="test_secret",
            redirect_uri="http://localhost:8001/api/auth/upstox/callback",
            login_phone="9999999999",
            login_pin="123456",
            totp_secret="JBSWY3DPEHPK3PXP",
        )

        with patch.object(auth, "_sync_authenticate", return_value="fresh_upstox_token"):
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


# ─── refresh_broker_token() dispatcher (Layer 3.1) ──────────────────────────

class TestRefreshBrokerTokenDispatch:
    @pytest.mark.asyncio
    async def test_upstox_calls_refresh_upstox(self):
        """refresh_broker_token('upstox') should call _refresh_upstox_token."""
        from app.services.brokers.platform_token_refresh import refresh_broker_token

        with patch(
            "app.services.brokers.platform_token_refresh._refresh_upstox_token",
            new_callable=AsyncMock,
            return_value="new_token",
        ) as mock_refresh:
            result = await refresh_broker_token("upstox")
            assert result is True
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_smartapi_calls_refresh_smartapi(self):
        """refresh_broker_token('smartapi') should call _refresh_smartapi_token."""
        from app.services.brokers.platform_token_refresh import refresh_broker_token

        with patch(
            "app.services.brokers.platform_token_refresh._refresh_smartapi_token",
            new_callable=AsyncMock,
            return_value="new_token",
        ) as mock_refresh:
            result = await refresh_broker_token("smartapi")
            assert result is True
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_kite_returns_false(self):
        from app.services.brokers.platform_token_refresh import refresh_broker_token
        result = await refresh_broker_token("kite")
        assert result is False

    @pytest.mark.asyncio
    async def test_dhan_returns_false(self):
        from app.services.brokers.platform_token_refresh import refresh_broker_token
        result = await refresh_broker_token("dhan")
        assert result is False

    @pytest.mark.asyncio
    async def test_fyers_returns_false(self):
        from app.services.brokers.platform_token_refresh import refresh_broker_token
        result = await refresh_broker_token("fyers")
        assert result is False

    @pytest.mark.asyncio
    async def test_paytm_returns_false(self):
        from app.services.brokers.platform_token_refresh import refresh_broker_token
        result = await refresh_broker_token("paytm")
        assert result is False

    @pytest.mark.asyncio
    async def test_unknown_broker_returns_false(self):
        from app.services.brokers.platform_token_refresh import refresh_broker_token
        result = await refresh_broker_token("unknown_broker")
        assert result is False


class TestRefreshBrokerTokenFailure:
    @pytest.mark.asyncio
    async def test_upstox_refresh_failure_returns_false(self):
        """If the underlying refresh raises, refresh_broker_token returns False."""
        from app.services.brokers.platform_token_refresh import refresh_broker_token

        with patch(
            "app.services.brokers.platform_token_refresh._refresh_upstox_token",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Auth failed"),
        ):
            result = await refresh_broker_token("upstox")
            assert result is False


class TestRefreshBrokerTokenConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_refresh_serialized_by_lock(self):
        """Two concurrent calls for the same broker are serialized by lock."""
        from app.services.brokers.platform_token_refresh import refresh_broker_token

        call_count = 0

        async def slow_refresh():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return "token"

        with patch(
            "app.services.brokers.platform_token_refresh._refresh_upstox_token",
            new_callable=AsyncMock,
            side_effect=slow_refresh,
        ):
            results = await asyncio.gather(
                refresh_broker_token("upstox"),
                refresh_broker_token("upstox"),
            )
            assert all(results)
            # Both calls go through (serialized), so count should be 2
            assert call_count == 2
