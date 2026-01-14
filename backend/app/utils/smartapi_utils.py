"""
SmartAPI Utility Functions

Provides token validation and auto-refresh functionality for SmartAPI.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.smartapi_credentials import SmartAPICredentials
from app.utils.encryption import decrypt
from app.services.smartapi_auth import get_smartapi_auth, SmartAPIAuthError

logger = logging.getLogger(__name__)

# Refresh token 30 minutes before expiry to avoid edge cases
TOKEN_REFRESH_BUFFER_MINUTES = 30


async def get_valid_smartapi_credentials(
    user_id,
    db: AsyncSession,
    auto_refresh: bool = True
) -> Optional[SmartAPICredentials]:
    """
    Get SmartAPI credentials with automatic token refresh if expired.

    This function:
    1. Fetches the user's SmartAPI credentials
    2. Checks if the JWT token is expired or about to expire
    3. If expired, automatically re-authenticates using stored credentials
    4. Returns the credentials with a valid token

    Args:
        user_id: User's UUID
        db: Database session
        auto_refresh: Whether to auto-refresh expired tokens (default True)

    Returns:
        SmartAPICredentials with valid token, or None if not configured/refresh failed
    """
    # Fetch credentials
    result = await db.execute(
        select(SmartAPICredentials).where(
            SmartAPICredentials.user_id == user_id,
            SmartAPICredentials.is_active == True
        )
    )
    credentials = result.scalar_one_or_none()

    if not credentials:
        logger.debug(f"[SmartAPI] No active credentials for user {user_id}")
        return None

    # Check if token is valid
    if credentials.jwt_token and credentials.token_expiry:
        # Add buffer to avoid edge cases
        expiry_with_buffer = credentials.token_expiry - timedelta(minutes=TOKEN_REFRESH_BUFFER_MINUTES)
        now = datetime.now(timezone.utc)

        if now < expiry_with_buffer:
            # Token is still valid
            logger.debug(f"[SmartAPI] Token valid until {credentials.token_expiry}")
            return credentials
        else:
            logger.info(f"[SmartAPI] Token expired or expiring soon for user {user_id}")
    else:
        logger.info(f"[SmartAPI] No JWT token for user {user_id}")

    # Token is expired or missing - attempt refresh if allowed
    if not auto_refresh:
        logger.warning(f"[SmartAPI] Token expired but auto_refresh disabled")
        return None

    # Try to refresh the token
    refreshed = await refresh_smartapi_token(credentials, db)

    if refreshed:
        return credentials
    else:
        return None


async def refresh_smartapi_token(
    credentials: SmartAPICredentials,
    db: AsyncSession
) -> bool:
    """
    Refresh SmartAPI token using stored credentials.

    First tries to use the refresh_token if available.
    Falls back to full re-authentication with PIN + TOTP.

    Args:
        credentials: SmartAPI credentials object
        db: Database session

    Returns:
        True if refresh succeeded, False otherwise
    """
    auth = get_smartapi_auth()

    # Method 1: Try refresh token first (faster, doesn't need TOTP)
    if credentials.refresh_token:
        try:
            logger.info(f"[SmartAPI] Attempting token refresh via refresh_token")
            result = auth.refresh_session(credentials.refresh_token)

            credentials.jwt_token = result['jwt_token']
            credentials.feed_token = result['feed_token']
            credentials.token_expiry = result['token_expiry']
            credentials.last_auth_at = datetime.now(timezone.utc)
            credentials.last_error = None

            await db.commit()
            logger.info(f"[SmartAPI] Token refreshed successfully via refresh_token")
            return True

        except SmartAPIAuthError as e:
            logger.warning(f"[SmartAPI] Refresh token failed: {e}, falling back to full auth")
        except Exception as e:
            logger.error(f"[SmartAPI] Refresh token error: {e}")

    # Method 2: Full re-authentication with PIN + TOTP
    if credentials.encrypted_pin and credentials.encrypted_totp_secret:
        try:
            logger.info(f"[SmartAPI] Attempting full re-authentication for {credentials.client_id}")

            pin = decrypt(credentials.encrypted_pin)
            totp_secret = decrypt(credentials.encrypted_totp_secret)

            result = auth.authenticate(
                client_id=credentials.client_id,
                pin=pin,
                totp_secret=totp_secret
            )

            credentials.jwt_token = result['jwt_token']
            credentials.refresh_token = result.get('refresh_token')
            credentials.feed_token = result['feed_token']
            credentials.token_expiry = result['token_expiry']
            credentials.last_auth_at = datetime.now(timezone.utc)
            credentials.last_error = None
            credentials.is_active = True

            await db.commit()
            logger.info(f"[SmartAPI] Full re-authentication successful for {credentials.client_id}")
            return True

        except SmartAPIAuthError as e:
            credentials.last_error = str(e)
            credentials.is_active = False
            await db.commit()
            logger.error(f"[SmartAPI] Re-authentication failed: {e}")
            return False
        except Exception as e:
            logger.error(f"[SmartAPI] Re-authentication error: {e}")
            return False

    logger.error(f"[SmartAPI] Cannot refresh token - no credentials stored")
    return False


def is_token_expired(credentials: SmartAPICredentials) -> bool:
    """
    Check if SmartAPI token is expired or about to expire.

    Args:
        credentials: SmartAPI credentials object

    Returns:
        True if token is expired or expiring within buffer period
    """
    if not credentials or not credentials.jwt_token or not credentials.token_expiry:
        return True

    expiry_with_buffer = credentials.token_expiry - timedelta(minutes=TOKEN_REFRESH_BUFFER_MINUTES)
    return datetime.now(timezone.utc) >= expiry_with_buffer
