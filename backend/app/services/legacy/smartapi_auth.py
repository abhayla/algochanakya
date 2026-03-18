"""
SmartAPI Authentication Service

Handles authentication with AngelOne SmartAPI including:
- Session generation with auto-TOTP
- Token refresh
- Session validation
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import pyotp
from SmartApi import SmartConnect

from app.config import settings

logger = logging.getLogger(__name__)


class SmartAPIAuthError(Exception):
    """Exception raised for SmartAPI authentication errors."""
    pass


class SmartAPIAuth:
    """
    Authentication service for AngelOne SmartAPI.

    Handles session management with auto-TOTP generation.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SmartAPI auth service.

        Args:
            api_key: AngelOne API key (defaults to ANGEL_API_KEY from settings)
        """
        self.api_key = api_key or getattr(settings, 'ANGEL_API_KEY', None)
        if not self.api_key:
            logger.warning("ANGEL_API_KEY not configured in settings")
        self._api: Optional[SmartConnect] = None

    def _get_api(self) -> SmartConnect:
        """Get or create SmartConnect instance."""
        if self._api is None:
            if not self.api_key:
                raise SmartAPIAuthError("ANGEL_API_KEY not configured")
            self._api = SmartConnect(api_key=self.api_key)
        return self._api

    def generate_totp(self, totp_secret: str) -> str:
        """
        Generate current TOTP code from secret.

        Args:
            totp_secret: Base32-encoded TOTP secret

        Returns:
            6-digit TOTP code
        """
        try:
            totp = pyotp.TOTP(totp_secret)
            return totp.now()
        except Exception as e:
            logger.error(f"Failed to generate TOTP: {e}")
            raise SmartAPIAuthError(f"Invalid TOTP secret: {e}")

    def authenticate_with_totp(
        self,
        client_id: str,
        pin: str,
        totp_code: str
    ) -> Dict[str, Any]:
        """
        Authenticate with SmartAPI using a user-provided TOTP code.

        Used for inline login where the user enters their 6-digit TOTP
        from an authenticator app. Credentials are NOT stored.

        Args:
            client_id: AngelOne trading account ID
            pin: Trading PIN
            totp_code: 6-digit TOTP code from authenticator app

        Returns:
            Dict with jwt_token, refresh_token, feed_token, and token_expiry
        """
        return self._do_authenticate(client_id, pin, totp_code)

    def authenticate(
        self,
        client_id: str,
        pin: str,
        totp_secret: str
    ) -> Dict[str, Any]:
        """
        Authenticate with SmartAPI using stored TOTP secret (auto-generates code).

        Args:
            client_id: AngelOne trading account ID
            pin: Trading PIN
            totp_secret: TOTP secret for auto-generation
        """
        totp_code = self.generate_totp(totp_secret)
        return self._do_authenticate(client_id, pin, totp_code)

    def _do_authenticate(
        self,
        client_id: str,
        pin: str,
        totp_code: str
    ) -> Dict[str, Any]:
        """
        Core authentication logic shared by both authenticate() and authenticate_with_totp().
        """
        try:
            api = self._get_api()
            logger.info(f"[SmartAPI] Authenticating client: {client_id}")

            data = api.generateSession(client_id, pin, totp_code)

            if not data or not data.get('data'):
                error_msg = data.get('message', 'Unknown error') if data else 'No response'
                logger.error(f"[SmartAPI] Authentication failed: {error_msg}")
                raise SmartAPIAuthError(f"Authentication failed: {error_msg}")

            session_data = data['data']
            feed_token = api.getfeedToken()

            from zoneinfo import ZoneInfo
            ist = ZoneInfo('Asia/Kolkata')
            now_ist = datetime.now(ist)

            if now_ist.hour < 5:
                expiry_ist = now_ist.replace(hour=5, minute=0, second=0, microsecond=0)
            else:
                expiry_ist = (now_ist + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)

            token_expiry = expiry_ist.astimezone(timezone.utc)

            result = {
                'jwt_token': session_data.get('jwtToken'),
                'refresh_token': session_data.get('refreshToken'),
                'feed_token': feed_token,
                'token_expiry': token_expiry,
                'client_id': client_id
            }

            logger.info(f"[SmartAPI] Authentication successful for {client_id}")
            return result

        except SmartAPIAuthError:
            raise
        except Exception as e:
            logger.error(f"[SmartAPI] Authentication error: {e}")
            raise SmartAPIAuthError(f"Authentication failed: {e}")

    def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired session.

        Args:
            refresh_token: Refresh token from previous session

        Returns:
            Dict with new jwt_token and feed_token

        Raises:
            SmartAPIAuthError: If refresh fails
        """
        try:
            api = self._get_api()

            data = api.generateToken(refresh_token)

            if not data or not data.get('data'):
                error_msg = data.get('message', 'Unknown error') if data else 'No response'
                logger.error(f"[SmartAPI] Token refresh failed: {error_msg}")
                raise SmartAPIAuthError(f"Token refresh failed: {error_msg}")

            session_data = data['data']
            feed_token = api.getfeedToken()

            # SmartAPI tokens are flushed at 5 AM IST daily
            from zoneinfo import ZoneInfo
            ist = ZoneInfo('Asia/Kolkata')
            now_ist = datetime.now(ist)

            if now_ist.hour < 5:
                expiry_ist = now_ist.replace(hour=5, minute=0, second=0, microsecond=0)
            else:
                expiry_ist = (now_ist + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)

            token_expiry = expiry_ist.astimezone(timezone.utc)

            return {
                'jwt_token': session_data.get('jwtToken'),
                'feed_token': feed_token,
                'token_expiry': token_expiry
            }

        except SmartAPIAuthError:
            raise
        except Exception as e:
            logger.error(f"[SmartAPI] Token refresh error: {e}")
            raise SmartAPIAuthError(f"Token refresh failed: {e}")

    def validate_session(self, jwt_token: str) -> bool:
        """
        Validate if a session token is still valid.

        Args:
            jwt_token: JWT token to validate

        Returns:
            True if session is valid, False otherwise
        """
        try:
            api = self._get_api()
            api.setSessionExpiryHook(lambda: None)  # Disable auto-logout

            # Set the token and try to fetch profile
            api.setAccessToken(jwt_token)
            profile = api.getProfile(jwt_token)

            if profile and profile.get('data'):
                return True
            return False

        except Exception as e:
            logger.warning(f"[SmartAPI] Session validation failed: {e}")
            return False

    def logout(self, client_id: str) -> bool:
        """
        Logout and invalidate session.

        Args:
            client_id: Client ID to logout

        Returns:
            True if logout successful
        """
        try:
            api = self._get_api()
            api.terminateSession(client_id)
            logger.info(f"[SmartAPI] Session terminated for {client_id}")
            return True
        except Exception as e:
            logger.warning(f"[SmartAPI] Logout error: {e}")
            return False


# Global singleton instance
_smartapi_auth: Optional[SmartAPIAuth] = None


def get_smartapi_auth() -> SmartAPIAuth:
    """Get the global SmartAPI auth service instance."""
    global _smartapi_auth
    if _smartapi_auth is None:
        _smartapi_auth = SmartAPIAuth()
    return _smartapi_auth
