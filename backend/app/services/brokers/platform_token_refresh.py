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
from urllib.parse import urlparse, parse_qs

import httpx
import pyotp

from app.config import settings

logger = logging.getLogger(__name__)


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

    API_BASE = "https://api.upstox.com"
    SERVICE_BASE = "https://service.upstox.com"

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

    def _generate_totp(self) -> str:
        return pyotp.TOTP(self.totp_secret).now()

    async def authenticate(self) -> str:
        """Execute the 6-step HTTP login flow. Returns access_token."""
        return await self._execute_login_flow()

    async def _execute_login_flow(self) -> str:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=False,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            },
        ) as client:
            # Step 1: Authorization dialog → get user_id from redirect
            logger.info("[Upstox Refresh] Step 1: Authorization dialog")
            resp = await client.get(
                f"{self.API_BASE}/v2/login/authorization/dialog",
                params={
                    "response_type": "code",
                    "client_id": self.api_key,
                    "redirect_uri": self.redirect_uri,
                },
            )
            # Follow redirect to get user_id from URL
            redirect_url = resp.headers.get("location", str(resp.url))
            parsed = urlparse(redirect_url)
            qs = parse_qs(parsed.query)
            user_id = qs.get("user_id", [None])[0]

            if not user_id:
                # Try following the redirect chain
                resp2 = await client.get(redirect_url, follow_redirects=True)
                parsed2 = urlparse(str(resp2.url))
                qs2 = parse_qs(parsed2.query)
                user_id = qs2.get("user_id", [None])[0]

            if not user_id:
                raise RuntimeError(f"Could not extract user_id from redirect: {redirect_url}")

            # Step 2: Generate OTP
            logger.info("[Upstox Refresh] Step 2: Generate OTP")
            resp = await client.post(
                f"{self.SERVICE_BASE}/login/open/v6/auth/1fa/otp/generate",
                json={"data": {"mobileNumber": self.login_phone, "userId": user_id}},
            )
            otp_data = resp.json()
            validate_token = otp_data.get("data", {}).get("validateOTPToken")
            if not validate_token:
                raise RuntimeError(f"OTP generation failed: {otp_data}")

            # Step 3: Verify TOTP
            logger.info("[Upstox Refresh] Step 3: Verify TOTP")
            totp_code = self._generate_totp()
            resp = await client.post(
                f"{self.SERVICE_BASE}/login/open/v4/auth/1fa/otp-totp/verify",
                json={"data": {"otp": totp_code, "validateOtpToken": validate_token}},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"TOTP verification failed: {resp.text[:200]}")

            # Step 4: 2FA PIN
            logger.info("[Upstox Refresh] Step 4: Submit PIN")
            encoded_pin = base64.b64encode(self.login_pin.encode()).decode()
            resp = await client.post(
                f"{self.SERVICE_BASE}/login/open/v3/auth/2fa",
                params={"client_id": self.api_key, "redirect_uri": self.redirect_uri},
                json={"data": {"twoFAMethod": "SECRET_PIN", "inputText": encoded_pin}},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"2FA PIN failed: {resp.text[:200]}")

            # Step 5: OAuth authorize → get code
            logger.info("[Upstox Refresh] Step 5: OAuth authorize")
            resp = await client.post(
                f"{self.SERVICE_BASE}/login/v2/oauth/authorize",
                params={
                    "client_id": self.api_key,
                    "redirect_uri": self.redirect_uri,
                    "response_type": "code",
                },
                json={"data": {"userOAuthApproval": True}},
            )
            # Extract code from redirect URL
            auth_redirect = resp.headers.get("location", str(resp.url))
            parsed_auth = urlparse(auth_redirect)
            qs_auth = parse_qs(parsed_auth.query)
            auth_code = qs_auth.get("code", [None])[0]
            if not auth_code:
                raise RuntimeError(f"Could not extract auth code from: {auth_redirect}")

            # Step 6: Exchange code for token
            logger.info("[Upstox Refresh] Step 6: Token exchange")
            resp = await client.post(
                f"{self.API_BASE}/v2/login/authorization/token",
                data={
                    "code": auth_code,
                    "client_id": self.api_key,
                    "client_secret": self.api_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Token exchange failed: {resp.text[:300]}")

            token_data = resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise RuntimeError(f"No access_token in response: {token_data}")

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
    env_path = Path(__file__).parent.parent.parent / ".env"
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
