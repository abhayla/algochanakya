"""
Platform Token Auto-Refresh Service

Refreshes platform-level broker tokens (stored in .env) on startup.
Covers AngelOne (SmartAPI direct auth) and Upstox (HTTP-based TOTP login).

Called from main.py lifespan on startup. Non-blocking — failures are logged
but don't prevent the backend from starting.
"""
import base64
import json
import logging
import time
from pathlib import Path
from typing import Optional


import asyncio as _asyncio

from app.config import settings
from app.services.brokers.market_data.ticker.token_policy import can_auto_refresh

logger = logging.getLogger(__name__)

# Per-broker locks to prevent concurrent refresh attempts
_refresh_locks: dict[str, _asyncio.Lock] = {}


# ============================================================================
# Upstox HTTP-Based Auto-Login (no browser required)
# ============================================================================

class UpstoxHttpAuth:
    """
    Authenticates with Upstox using pure HTTP requests (no Playwright/Selenium).

    6-step flow:
    1. GET authorization dialog → extract user_id
    2. POST generate OTP → get validateOTPToken
    3. POST verify TOTP → validate 1FA
    4. POST 2FA PIN → authenticate
    5. POST OAuth authorize → get authorization code
    6. POST token exchange → get access_token
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        redirect_uri: str,
        login_phone: str,
        login_pin: str,
        totp_secret: str,
    ):
        missing = []
        for name, val in [
            ("api_key", api_key), ("api_secret", api_secret),
            ("redirect_uri", redirect_uri), ("login_phone", login_phone),
            ("login_pin", login_pin), ("totp_secret", totp_secret),
        ]:
            if not val:
                missing.append(name)
        if missing:
            raise ValueError(f"Missing Upstox credentials: {', '.join(missing)}")

        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.login_phone = login_phone
        self.login_pin = login_pin
        self.totp_secret = totp_secret

    async def authenticate(self) -> str:
        """Execute the 6-step HTTP login flow. Returns access_token.

        Uses the upstox-totp library which handles Cloudflare bot detection
        via curl_cffi with Chrome impersonation. The library manages the
        complete TOTP-based login flow internally.
        """
        import asyncio
        return await asyncio.to_thread(self._sync_authenticate)

    def _sync_authenticate(self) -> str:
        """Synchronous auth via upstox-totp library (runs in thread)."""
        try:
            from upstox_totp import UpstoxTOTP
        except ImportError:
            raise RuntimeError(
                "upstox-totp is required for Upstox auto-login. "
                "Install with: pip install upstox-totp"
            )

        logger.info("[Upstox Refresh] Starting upstox-totp authentication")
        client = UpstoxTOTP(
            username=self.login_phone,
            password=self.login_pin,
            pin_code=self.login_pin,
            totp_secret=self.totp_secret,
            client_id=self.api_key,
            client_secret=self.api_secret,
            redirect_uri=self.redirect_uri,
        )

        result = client.app_token.get_access_token()
        if not result.success or not result.data:
            raise RuntimeError(f"Upstox auth failed: {result.error}")

        access_token = result.data.access_token
        if not access_token:
            raise RuntimeError("No access_token in upstox-totp response")

        logger.info("[Upstox Refresh] Token obtained successfully")
        return access_token


# ============================================================================
# Token Expiry Helpers
# ============================================================================

def _is_upstox_token_expired(token: str) -> bool:
    """Check if an Upstox JWT token is expired."""
    if not token:
        return True
    try:
        payload = json.loads(base64.b64decode(token.split(".")[1] + "=="))
        return int(time.time()) >= payload.get("exp", 0)
    except Exception:
        return True


def _is_smartapi_token_expired() -> bool:
    """Check if SmartAPI platform token needs refresh (5 AM IST flush)."""
    # SmartAPI tokens are refreshed per-user via get_valid_smartapi_credentials()
    # Platform-level .env doesn't have a token — it uses api_key + auto-TOTP
    # So this always returns False (platform SmartAPI doesn't expire the same way)
    return False


# ============================================================================
# Token Persistence
# ============================================================================

def _save_token_to_env(key: str, value: str) -> None:
    """Update a token value in backend/.env file."""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if not env_path.exists():
        logger.warning(f"[TokenRefresh] .env not found at {env_path}")
        return

    lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    env_path.write_text("".join(new_lines), encoding="utf-8")
    logger.info(f"[TokenRefresh] {key} saved to .env")


# ============================================================================
# Main Refresh Orchestrator
# ============================================================================

async def _refresh_upstox_token() -> str:
    """Refresh Upstox platform token using HTTP-based TOTP login."""
    auth = UpstoxHttpAuth(
        api_key=settings.UPSTOX_API_KEY,
        api_secret=settings.UPSTOX_API_SECRET,
        redirect_uri=settings.UPSTOX_REDIRECT_URL,
        login_phone=settings.UPSTOX_LOGIN_PHONE,
        login_pin=settings.UPSTOX_LOGIN_PIN,
        totp_secret=settings.UPSTOX_TOTP_SECRET,
    )
    token = await auth.authenticate()
    _save_token_to_env("UPSTOX_ACCESS_TOKEN", token)
    # Update in-memory settings
    settings.UPSTOX_ACCESS_TOKEN = token
    return token


async def _refresh_smartapi_token() -> str:
    """Refresh SmartAPI platform token using auto-TOTP.

    SmartAPI uses api_key + client_id + TOTP for auth. The platform
    credentials are in .env. Returns the new JWT token.
    """
    from app.services.legacy.smartapi_auth import SmartAPIAuthService

    auth_service = SmartAPIAuthService()
    result = await auth_service.authenticate_platform()
    token = result.get("jwtToken") or result.get("data", {}).get("jwtToken", "")
    if not token:
        raise RuntimeError("SmartAPI auth returned no jwtToken")
    logger.info("[SmartAPI Refresh] Platform token refreshed")
    return token


async def refresh_broker_token(broker: str) -> bool:
    """Refresh credentials for a broker. Returns True on success, False otherwise.

    Only auto-refreshable brokers (smartapi, upstox) are supported.
    Non-refreshable brokers (kite, dhan, fyers, paytm) return False immediately.
    Uses per-broker locks to prevent concurrent refresh attempts.
    """
    if not can_auto_refresh(broker):
        return False

    # Get or create per-broker lock
    if broker not in _refresh_locks:
        _refresh_locks[broker] = _asyncio.Lock()

    async with _refresh_locks[broker]:
        try:
            if broker == "upstox":
                await _refresh_upstox_token()
            elif broker == "smartapi":
                await _refresh_smartapi_token()
            else:
                return False
            return True
        except Exception as e:
            logger.error("[TokenRefresh] %s refresh failed: %s", broker, e)
            return False


async def refresh_platform_tokens() -> dict:
    """
    Refresh all expired platform-level broker tokens.

    Called on startup from main.py lifespan. Non-blocking — failures
    are logged but don't prevent the backend from starting.

    Returns dict with status per broker: 'skipped', 'refreshed', or 'failed'.
    """
    results = {}

    # AngelOne: platform uses .env api_key + auto-TOTP per request (no token to refresh)
    if _is_smartapi_token_expired():
        results["angelone"] = "needs_refresh"
    else:
        results["angelone"] = "skipped"

    # Upstox: check JWT expiry, refresh if expired
    upstox_token = getattr(settings, "UPSTOX_ACCESS_TOKEN", "")
    if not upstox_token or _is_upstox_token_expired(upstox_token):
        # Check if we have auto-login credentials
        has_creds = all([
            getattr(settings, "UPSTOX_API_KEY", ""),
            getattr(settings, "UPSTOX_API_SECRET", ""),
            getattr(settings, "UPSTOX_REDIRECT_URL", ""),
            getattr(settings, "UPSTOX_LOGIN_PHONE", ""),
            getattr(settings, "UPSTOX_LOGIN_PIN", ""),
            getattr(settings, "UPSTOX_TOTP_SECRET", ""),
        ])
        if has_creds:
            try:
                await _refresh_upstox_token()
                results["upstox"] = "refreshed"
                logger.info("[TokenRefresh] Upstox platform token refreshed")
            except Exception as e:
                results["upstox"] = "failed"
                logger.error(f"[TokenRefresh] Upstox refresh failed: {e}")
        else:
            results["upstox"] = "no_credentials"
            logger.info("[TokenRefresh] Upstox auto-login credentials not configured")
    else:
        results["upstox"] = "skipped"

    return results
