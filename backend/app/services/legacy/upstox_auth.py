"""
Upstox Auto-Login Service

Automates Upstox OAuth 2.0 login using Playwright headless browser.
Mirrors the AngelOne SmartAPIAuth pattern — credentials live in .env,
token is obtained once and stored as UPSTOX_ACCESS_TOKEN in .env.

Token validity: ~1 year. Run this:
  - Once on first setup
  - When UPSTOX_ACCESS_TOKEN expires (~annually)

Flow:
  1. Open Upstox authorization dialog (headless Chrome)
  2. Enter mobile number → "Get OTP"
  3. Enter TOTP (auto-generated from UPSTOX_TOTP_SECRET) → Continue
  4. Enter PIN → Continue
  5. Backend callback endpoint handles code exchange and stores token in DB
  6. Read access_token from broker_connections table → save to .env

Prerequisites:
  - Backend server must be running (handles OAuth callback)
  - .env must have: UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_REDIRECT_URL,
    UPSTOX_LOGIN_PHONE, UPSTOX_LOGIN_PIN, UPSTOX_TOTP_SECRET
"""
import asyncio
import logging
from pathlib import Path

import pyotp

from app.config import settings

logger = logging.getLogger(__name__)


class UpstoxAuthError(Exception):
    pass


class UpstoxAuth:
    """
    Automates Upstox OAuth login using Playwright headless browser.

    After successful login the token is stored by the backend in broker_connections.
    Call save_token_to_env() to persist it to .env as UPSTOX_ACCESS_TOKEN.
    """

    AUTH_DIALOG_URL = "https://api.upstox.com/v2/login/authorization/dialog"

    def _build_auth_url(self) -> str:
        return (
            f"{self.AUTH_DIALOG_URL}"
            f"?response_type=code"
            f"&client_id={settings.UPSTOX_API_KEY}"
            f"&redirect_uri={settings.UPSTOX_REDIRECT_URL}"
        )

    def generate_totp(self) -> str:
        return pyotp.TOTP(settings.UPSTOX_TOTP_SECRET).now()

    def _validate_config(self):
        missing = []
        for key in ["UPSTOX_API_KEY", "UPSTOX_API_SECRET", "UPSTOX_REDIRECT_URL",
                    "UPSTOX_LOGIN_PHONE", "UPSTOX_LOGIN_PIN", "UPSTOX_TOTP_SECRET"]:
            if not getattr(settings, key, ""):
                missing.append(key)
        if missing:
            raise UpstoxAuthError(f"Missing .env keys: {', '.join(missing)}")

    def authenticate(self) -> str:
        """
        Run headless browser login flow.

        The backend OAuth callback endpoint handles the code→token exchange
        and stores the token in broker_connections. After this returns,
        call get_token_from_db() to retrieve it.

        Returns:
            str: The access_token retrieved from DB after login.

        Raises:
            UpstoxAuthError on any failure.
        """
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        self._validate_config()
        logger.info("[Upstox] Starting auto-login via Playwright headless browser")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )
            page = context.new_page()

            try:
                # Step 1: Open authorization dialog → redirects to login.upstox.com
                logger.info("[Upstox] Opening authorization dialog")
                page.goto(self._build_auth_url(), wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)

                # Step 2: Enter mobile number
                logger.info(f"[Upstox] Entering mobile: {settings.UPSTOX_LOGIN_PHONE}")
                page.wait_for_selector("#mobileNum", timeout=10000)
                page.fill("#mobileNum", settings.UPSTOX_LOGIN_PHONE)
                page.click("button:has-text('Get OTP')")
                page.wait_for_timeout(3000)

                # Step 3: Enter TOTP (auto-generated — no human needed)
                totp_code = self.generate_totp()
                logger.info(f"[Upstox] Entering TOTP: {totp_code}")
                page.wait_for_selector("#otpNum", timeout=10000)
                page.fill("#otpNum", totp_code)
                page.click("button:has-text('Continue')")
                page.wait_for_timeout(3000)

                # Step 4: Enter PIN
                logger.info("[Upstox] Entering PIN")
                page.wait_for_selector("#pinCode", timeout=10000)
                page.fill("#pinCode", settings.UPSTOX_LOGIN_PIN)
                page.click("button:has-text('Continue')")

                # Wait for backend callback to process and redirect to frontend
                logger.info("[Upstox] Waiting for OAuth callback to complete...")
                page.wait_for_url("**/dashboard**", timeout=20000)
                logger.info(f"[Upstox] Login complete, redirected to: {page.url}")

            except PWTimeout as e:
                raise UpstoxAuthError(
                    f"Timeout during Upstox login: {e}\n"
                    f"Current URL: {page.url}\n"
                    "Ensure backend is running on port 8001 to handle the OAuth callback."
                )
            except Exception as e:
                raise UpstoxAuthError(f"Browser login failed at {page.url}: {e}")
            finally:
                browser.close()

        # Step 5: Read token from DB (backend stored it during callback)
        return asyncio.run(self._get_token_from_db())

    async def _get_token_from_db(self) -> str:
        """Read the most recent Upstox access_token from broker_connections."""
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models import BrokerConnection

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BrokerConnection)
                .where(
                    BrokerConnection.broker == "upstox",
                    BrokerConnection.is_active == True,
                )
                .order_by(BrokerConnection.updated_at.desc())
            )
            conn = result.scalar_one_or_none()

        if not conn or not conn.access_token:
            raise UpstoxAuthError(
                "Login appeared to succeed but no active Upstox token found in DB. "
                "Check backend logs for OAuth callback errors."
            )

        logger.info(f"[Upstox] Token retrieved from DB for user {conn.user_id}")
        return conn.access_token


def save_token_to_env(access_token: str) -> None:
    """
    Write UPSTOX_ACCESS_TOKEN to backend/.env in-place.
    Creates the key if missing, replaces value if already present.
    """
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if not env_path.exists():
        raise UpstoxAuthError(f".env not found at {env_path}")

    lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
    found = False
    new_lines = []
    for line in lines:
        if line.startswith("UPSTOX_ACCESS_TOKEN="):
            new_lines.append(f"UPSTOX_ACCESS_TOKEN={access_token}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"UPSTOX_ACCESS_TOKEN={access_token}\n")

    env_path.write_text("".join(new_lines), encoding="utf-8")
    logger.info(f"[Upstox] UPSTOX_ACCESS_TOKEN saved to {env_path}")


# Global singleton
_upstox_auth: UpstoxAuth | None = None


def get_upstox_auth() -> UpstoxAuth:
    global _upstox_auth
    if _upstox_auth is None:
        _upstox_auth = UpstoxAuth()
    return _upstox_auth
