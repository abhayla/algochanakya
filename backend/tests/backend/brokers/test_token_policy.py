"""Tests for token_policy — auth error classification per broker.

Tests cover:
- classify_auth_error() for all broker error codes
- can_auto_refresh() for all 6 brokers
- get_retry_params() for all 4 categories
- get_frontend_notification() for refreshable vs non-refreshable
"""

import pytest

from app.services.brokers.market_data.ticker.token_policy import (
    RetryCategory,
    classify_auth_error,
    can_auto_refresh,
    get_retry_params,
    get_frontend_notification,
)


# ─── classify_auth_error: AngelOne ────────────────────────────────────────────

class TestClassifyAngelOne:
    def test_AB1010_invalid_token_retryable(self):
        result = classify_auth_error("smartapi", "AB1010", "Invalid Token")
        assert result == RetryCategory.RETRYABLE

    def test_AB1004_invalid_api_key_not_retryable(self):
        result = classify_auth_error("smartapi", "AB1004", "Invalid API Key")
        assert result == RetryCategory.NOT_RETRYABLE

    def test_AB2000_rate_limited_retryable(self):
        result = classify_auth_error("smartapi", "AB2000", "Rate limit exceeded")
        assert result == RetryCategory.RETRYABLE


# ─── classify_auth_error: Upstox ──────────────────────────────────────────────

class TestClassifyUpstox:
    def test_UDAPI100050_invalid_token_retryable(self):
        result = classify_auth_error("upstox", "UDAPI100050", "Invalid token used to access API")
        assert result == RetryCategory.RETRYABLE

    def test_UDAPI100010_rate_limited_retryable(self):
        result = classify_auth_error("upstox", "UDAPI100010", "Rate limit exceeded")
        assert result == RetryCategory.RETRYABLE

    def test_http_403_not_retryable(self):
        result = classify_auth_error("upstox", "403", "Forbidden")
        assert result == RetryCategory.NOT_RETRYABLE


# ─── classify_auth_error: Kite ────────────────────────────────────────────────

class TestClassifyKite:
    def test_token_exception_not_refreshable(self):
        result = classify_auth_error("kite", "TokenException", "Token is invalid or has expired")
        assert result == RetryCategory.NOT_REFRESHABLE

    def test_network_exception_retryable(self):
        result = classify_auth_error("kite", "NetworkException", "Connection timed out")
        assert result == RetryCategory.RETRYABLE

    def test_general_exception_retryable(self):
        result = classify_auth_error("kite", "GeneralException", "Something went wrong")
        assert result == RetryCategory.RETRYABLE


# ─── classify_auth_error: Dhan ────────────────────────────────────────────────

class TestClassifyDhan:
    def test_401_not_refreshable(self):
        result = classify_auth_error("dhan", "401", "Unauthorized")
        assert result == RetryCategory.NOT_REFRESHABLE

    def test_DH901_not_refreshable(self):
        result = classify_auth_error("dhan", "DH-901", "Invalid token")
        assert result == RetryCategory.NOT_REFRESHABLE


# ─── classify_auth_error: Fyers ───────────────────────────────────────────────

class TestClassifyFyers:
    def test_invalid_token_not_refreshable(self):
        result = classify_auth_error("fyers", "invalid_token", "Token expired")
        assert result == RetryCategory.NOT_REFRESHABLE

    def test_minus_16_not_refreshable(self):
        result = classify_auth_error("fyers", "-16", "Invalid token")
        assert result == RetryCategory.NOT_REFRESHABLE

    def test_minus_300_rate_limit_retryable(self):
        result = classify_auth_error("fyers", "-300", "Rate limit")
        assert result == RetryCategory.RETRYABLE


# ─── classify_auth_error: Paytm ───────────────────────────────────────────────

class TestClassifyPaytm:
    def test_access_token_expired_not_refreshable(self):
        result = classify_auth_error("paytm", "ACCESS_TOKEN_EXPIRED", "Token expired")
        assert result == RetryCategory.NOT_REFRESHABLE

    def test_session_expired_not_refreshable(self):
        result = classify_auth_error("paytm", "SESSION_EXPIRED", "Session expired")
        assert result == RetryCategory.NOT_REFRESHABLE


# ─── classify_auth_error: Defaults ────────────────────────────────────────────

class TestClassifyDefaults:
    def test_unknown_error_defaults_retryable(self):
        result = classify_auth_error("smartapi", "UNKNOWN_CODE", "Something unexpected")
        assert result == RetryCategory.RETRYABLE

    def test_unknown_broker_defaults_retryable(self):
        result = classify_auth_error("unknown_broker", "SOME_ERROR", "Error")
        assert result == RetryCategory.RETRYABLE

    def test_connection_timeout_retryable(self):
        result = classify_auth_error("smartapi", "ConnectionTimeout", "Connection timed out")
        assert result == RetryCategory.RETRYABLE


# ─── can_auto_refresh ─────────────────────────────────────────────────────────

class TestCanAutoRefresh:
    def test_angelone_true(self):
        assert can_auto_refresh("smartapi") is True

    def test_upstox_true(self):
        assert can_auto_refresh("upstox") is True

    def test_kite_false(self):
        assert can_auto_refresh("kite") is False

    def test_dhan_false(self):
        assert can_auto_refresh("dhan") is False

    def test_fyers_false(self):
        assert can_auto_refresh("fyers") is False

    def test_paytm_false(self):
        assert can_auto_refresh("paytm") is False

    def test_unknown_broker_false(self):
        assert can_auto_refresh("unknown") is False


# ─── get_retry_params ─────────────────────────────────────────────────────────

class TestRetryParams:
    def test_retryable_3_retries(self):
        params = get_retry_params(RetryCategory.RETRYABLE)
        assert params["max_retries"] == 3
        assert params["base_delay_s"] > 0

    def test_retryable_once_1_retry(self):
        params = get_retry_params(RetryCategory.RETRYABLE_ONCE)
        assert params["max_retries"] == 1
        assert params["base_delay_s"] == 30

    def test_not_retryable_zero_retries(self):
        params = get_retry_params(RetryCategory.NOT_RETRYABLE)
        assert params["max_retries"] == 0

    def test_not_refreshable_zero_retries(self):
        params = get_retry_params(RetryCategory.NOT_REFRESHABLE)
        assert params["max_retries"] == 0


# ─── get_frontend_notification ────────────────────────────────────────────────

class TestFrontendNotification:
    def test_kite_includes_message(self):
        notif = get_frontend_notification("kite")
        assert notif is not None
        assert "broker" in notif
        assert notif["broker"] == "kite"

    def test_dhan_includes_message(self):
        notif = get_frontend_notification("dhan")
        assert notif is not None
        assert notif["broker"] == "dhan"

    def test_fyers_includes_message(self):
        notif = get_frontend_notification("fyers")
        assert notif is not None

    def test_paytm_includes_message(self):
        notif = get_frontend_notification("paytm")
        assert notif is not None

    def test_angelone_returns_none(self):
        """Auto-refreshable brokers don't need frontend notification."""
        assert get_frontend_notification("smartapi") is None

    def test_upstox_returns_none(self):
        assert get_frontend_notification("upstox") is None
