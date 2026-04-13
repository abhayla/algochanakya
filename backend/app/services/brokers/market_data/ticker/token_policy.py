"""
Token policy — auth error classification per broker.

Classifies broker auth errors into retry categories so the system knows
whether to retry, refresh credentials, or failover immediately.

Auto-refreshable: AngelOne (pyotp TOTP), Upstox (upstox-totp)
Not refreshable:  Kite (OAuth), Dhan (static), Fyers (OAuth), Paytm (broken)
"""

from enum import Enum
from typing import Optional


class RetryCategory(str, Enum):
    RETRYABLE = "retryable"                # 3x exponential backoff
    RETRYABLE_ONCE = "retryable_once"      # 30s TOTP wait, then 1 retry
    NOT_RETRYABLE = "not_retryable"        # Config error, failover immediately
    NOT_REFRESHABLE = "not_refreshable"    # Can't auto-refresh, failover + notify frontend


# ─── Error Classification Tables ─────────────────────────────────────────────

_SMARTAPI_ERRORS: dict[str, RetryCategory] = {
    "AB1010": RetryCategory.RETRYABLE,       # Invalid Token — refreshable via TOTP
    "AB1004": RetryCategory.NOT_RETRYABLE,   # Invalid API Key — config error
    "AB2000": RetryCategory.RETRYABLE,       # Rate limited
}

_UPSTOX_ERRORS: dict[str, RetryCategory] = {
    "UDAPI100050": RetryCategory.RETRYABLE,  # Invalid token — refreshable via upstox-totp
    "UDAPI100010": RetryCategory.RETRYABLE,  # Rate limited
    "403": RetryCategory.NOT_RETRYABLE,      # Forbidden — config/permission error
}

_KITE_ERRORS: dict[str, RetryCategory] = {
    "TokenException": RetryCategory.NOT_REFRESHABLE,   # OAuth only — can't auto-refresh
    "NetworkException": RetryCategory.RETRYABLE,       # Transient network issue
    "GeneralException": RetryCategory.RETRYABLE,       # Transient
}

_DHAN_ERRORS: dict[str, RetryCategory] = {
    "401": RetryCategory.NOT_REFRESHABLE,    # Static token — portal refresh only
    "DH-901": RetryCategory.NOT_REFRESHABLE, # Invalid token
}

_FYERS_ERRORS: dict[str, RetryCategory] = {
    "invalid_token": RetryCategory.NOT_REFRESHABLE,  # OAuth only
    "-16": RetryCategory.NOT_REFRESHABLE,            # Invalid token
    "-300": RetryCategory.RETRYABLE,                 # Rate limit
}

_PAYTM_ERRORS: dict[str, RetryCategory] = {
    "ACCESS_TOKEN_EXPIRED": RetryCategory.NOT_REFRESHABLE,  # Portal broken
    "SESSION_EXPIRED": RetryCategory.NOT_REFRESHABLE,
}

_BROKER_ERROR_TABLES: dict[str, dict[str, RetryCategory]] = {
    "smartapi": _SMARTAPI_ERRORS,
    "upstox": _UPSTOX_ERRORS,
    "kite": _KITE_ERRORS,
    "dhan": _DHAN_ERRORS,
    "fyers": _FYERS_ERRORS,
    "paytm": _PAYTM_ERRORS,
}

# Generic patterns that match across all brokers
_GENERIC_RETRYABLE_PATTERNS = [
    "ConnectionTimeout",
    "connection timed out",
    "timeout",
]

# Brokers that support automatic token refresh
_AUTO_REFRESHABLE_BROKERS = {"smartapi", "upstox"}


# ─── Public API ───────────────────────────────────────────────────────────────

def classify_auth_error(broker: str, error_code: str, error_msg: str) -> RetryCategory:
    """Classify a broker auth error into a retry category.

    Checks broker-specific error tables first, then generic patterns.
    Defaults to RETRYABLE for unknown errors (safe default — will retry
    before giving up).
    """
    table = _BROKER_ERROR_TABLES.get(broker, {})
    if error_code in table:
        return table[error_code]

    # Check generic retryable patterns
    for pattern in _GENERIC_RETRYABLE_PATTERNS:
        if pattern.lower() in error_code.lower() or pattern.lower() in error_msg.lower():
            return RetryCategory.RETRYABLE

    # Unknown error — safe default
    return RetryCategory.RETRYABLE


def can_auto_refresh(broker: str) -> bool:
    """Check if a broker supports automatic token refresh."""
    return broker in _AUTO_REFRESHABLE_BROKERS


def get_retry_params(category: RetryCategory) -> dict:
    """Get retry parameters for a given category."""
    if category == RetryCategory.RETRYABLE:
        return {
            "max_retries": 3,
            "base_delay_s": 5,
            "backoff_factor": 2,
        }
    elif category == RetryCategory.RETRYABLE_ONCE:
        return {
            "max_retries": 1,
            "base_delay_s": 30,
            "backoff_factor": 1,
        }
    else:
        # NOT_RETRYABLE and NOT_REFRESHABLE — no retries
        return {
            "max_retries": 0,
            "base_delay_s": 0,
            "backoff_factor": 1,
        }


def get_frontend_notification(broker: str) -> Optional[dict]:
    """Get frontend notification for brokers that can't auto-refresh.

    Returns None for auto-refreshable brokers (no notification needed).
    Returns a dict with broker name and message for non-refreshable brokers.
    """
    if can_auto_refresh(broker):
        return None

    messages = {
        "kite": "Zerodha session expired. Please re-login via the Kite OAuth flow.",
        "dhan": "Dhan token expired. Please regenerate your access token from the Dhan portal.",
        "fyers": "Fyers session expired. Please re-login via the Fyers OAuth flow.",
        "paytm": "Paytm Money session expired. Please re-login from the Paytm Money portal.",
    }

    msg = messages.get(broker, f"{broker} session expired. Please re-authenticate.")
    return {
        "broker": broker,
        "message": msg,
        "action": "re_authenticate",
    }
