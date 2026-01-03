"""
SmartAPI API Routes

Endpoints for SmartAPI credential management and configuration.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, UserPreferences
from app.models.smartapi_credentials import SmartAPICredentials
from app.models.user_preferences import MarketDataSource
from app.schemas.smartapi import (
    SmartAPICredentialsCreate,
    SmartAPICredentialsResponse,
    SmartAPITestConnectionRequest,
    SmartAPITestConnectionResponse,
    MarketDataSourceRequest,
    MarketDataSourceResponse,
)
from app.utils.dependencies import get_current_user
from app.utils.encryption import encrypt, decrypt
from app.services.smartapi_auth import get_smartapi_auth, SmartAPIAuthError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/credentials", response_model=SmartAPICredentialsResponse)
async def get_smartapi_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if SmartAPI credentials are configured for the user.

    Returns:
        Credential status (does not return actual credentials)
    """
    result = await db.execute(
        select(SmartAPICredentials).where(
            SmartAPICredentials.user_id == user.id
        )
    )
    credentials = result.scalar_one_or_none()

    if not credentials:
        return SmartAPICredentialsResponse(
            has_credentials=False,
            is_active=False
        )

    return SmartAPICredentialsResponse(
        has_credentials=True,
        client_id=credentials.client_id,
        is_active=credentials.is_active,
        last_auth_at=credentials.last_auth_at,
        last_error=credentials.last_error,
        token_expiry=credentials.token_expiry
    )


@router.post("/credentials", response_model=SmartAPICredentialsResponse)
async def store_smartapi_credentials(
    request: SmartAPICredentialsCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Store SmartAPI credentials for the user.

    Credentials are encrypted before storage.
    """
    try:
        # Encrypt sensitive fields
        encrypted_pin = encrypt(request.pin)
        encrypted_totp_secret = encrypt(request.totp_secret)

        # Check if credentials already exist
        result = await db.execute(
            select(SmartAPICredentials).where(
                SmartAPICredentials.user_id == user.id
            )
        )
        credentials = result.scalar_one_or_none()

        if credentials:
            # Update existing
            credentials.client_id = request.client_id
            credentials.encrypted_pin = encrypted_pin
            credentials.encrypted_totp_secret = encrypted_totp_secret
            credentials.is_active = True
            credentials.last_error = None
            credentials.updated_at = datetime.now(timezone.utc)
        else:
            # Create new
            credentials = SmartAPICredentials(
                user_id=user.id,
                client_id=request.client_id,
                encrypted_pin=encrypted_pin,
                encrypted_totp_secret=encrypted_totp_secret,
                is_active=True
            )
            db.add(credentials)

        await db.commit()
        await db.refresh(credentials)

        logger.info(f"[SmartAPI] Credentials stored for user {user.id}")

        return SmartAPICredentialsResponse(
            has_credentials=True,
            client_id=credentials.client_id,
            is_active=credentials.is_active,
            last_auth_at=credentials.last_auth_at,
            last_error=credentials.last_error,
            token_expiry=credentials.token_expiry
        )

    except Exception as e:
        logger.error(f"[SmartAPI] Failed to store credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store credentials"
        )


@router.delete("/credentials")
async def delete_smartapi_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete SmartAPI credentials for the user.
    """
    result = await db.execute(
        select(SmartAPICredentials).where(
            SmartAPICredentials.user_id == user.id
        )
    )
    credentials = result.scalar_one_or_none()

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No credentials found"
        )

    await db.delete(credentials)
    await db.commit()

    logger.info(f"[SmartAPI] Credentials deleted for user {user.id}")

    return {"message": "Credentials deleted successfully"}


@router.post("/test-connection", response_model=SmartAPITestConnectionResponse)
async def test_smartapi_connection(
    request: SmartAPITestConnectionRequest,
    user: User = Depends(get_current_user)
):
    """
    Test SmartAPI connection with provided credentials.

    Does NOT store credentials - use POST /credentials to store.
    """
    try:
        auth = get_smartapi_auth()

        # Attempt authentication
        result = auth.authenticate(
            client_id=request.client_id,
            pin=request.pin,
            totp_secret=request.totp_secret
        )

        # Get profile to verify
        from SmartApi import SmartConnect
        from app.config import settings

        api = SmartConnect(api_key=getattr(settings, 'ANGEL_API_KEY', ''))
        api.setAccessToken(result['jwt_token'])
        profile = api.getProfile(result['jwt_token'])

        client_name = None
        if profile and profile.get('data'):
            client_name = profile['data'].get('name')

        logger.info(f"[SmartAPI] Connection test successful for {request.client_id}")

        return SmartAPITestConnectionResponse(
            success=True,
            message="Connection successful",
            client_name=client_name
        )

    except SmartAPIAuthError as e:
        logger.warning(f"[SmartAPI] Connection test failed: {e}")
        return SmartAPITestConnectionResponse(
            success=False,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"[SmartAPI] Connection test error: {e}")
        return SmartAPITestConnectionResponse(
            success=False,
            message=f"Connection failed: {e}"
        )


@router.post("/authenticate")
async def authenticate_smartapi(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate with SmartAPI using stored credentials.

    Returns session tokens for WebSocket and REST API usage.
    """
    # Get stored credentials
    result = await db.execute(
        select(SmartAPICredentials).where(
            SmartAPICredentials.user_id == user.id
        )
    )
    credentials = result.scalar_one_or_none()

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SmartAPI credentials configured"
        )

    try:
        # Decrypt credentials
        pin = decrypt(credentials.encrypted_pin)
        totp_secret = decrypt(credentials.encrypted_totp_secret)

        # Authenticate
        auth = get_smartapi_auth()
        result = auth.authenticate(
            client_id=credentials.client_id,
            pin=pin,
            totp_secret=totp_secret
        )

        # Update stored tokens
        credentials.jwt_token = result['jwt_token']
        credentials.refresh_token = result.get('refresh_token')
        credentials.feed_token = result['feed_token']
        credentials.token_expiry = result['token_expiry']
        credentials.last_auth_at = datetime.now(timezone.utc)
        credentials.last_error = None
        credentials.is_active = True

        await db.commit()

        logger.info(f"[SmartAPI] Authentication successful for user {user.id}")

        return {
            "success": True,
            "message": "Authentication successful",
            "token_expiry": result['token_expiry'].isoformat()
        }

    except SmartAPIAuthError as e:
        # Update error status
        credentials.last_error = str(e)
        credentials.is_active = False
        await db.commit()

        logger.warning(f"[SmartAPI] Authentication failed for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"[SmartAPI] Authentication error for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.get("/market-data-source", response_model=MarketDataSourceResponse)
async def get_market_data_source(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current market data source preference.
    """
    # Get user preferences
    prefs_result = await db.execute(
        select(UserPreferences).where(
            UserPreferences.user_id == user.id
        )
    )
    preferences = prefs_result.scalar_one_or_none()

    # Get SmartAPI credentials status
    creds_result = await db.execute(
        select(SmartAPICredentials).where(
            SmartAPICredentials.user_id == user.id
        )
    )
    smartapi_creds = creds_result.scalar_one_or_none()

    # Check if Kite is configured (user has broker connection)
    from app.models.broker_connections import BrokerConnection
    kite_result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id
        )
    )
    kite_connection = kite_result.scalar_one_or_none()

    source = MarketDataSource.SMARTAPI
    if preferences:
        source = preferences.market_data_source

    return MarketDataSourceResponse(
        source=source,
        smartapi_configured=bool(smartapi_creds and smartapi_creds.is_active),
        kite_configured=bool(kite_connection and kite_connection.access_token)
    )


@router.put("/market-data-source", response_model=MarketDataSourceResponse)
async def update_market_data_source(
    request: MarketDataSourceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update market data source preference.

    Validates that the selected source is configured.
    """
    # Validate source
    if request.source not in MarketDataSource.VALID_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source. Must be one of: {MarketDataSource.VALID_SOURCES}"
        )

    # Get SmartAPI credentials status
    creds_result = await db.execute(
        select(SmartAPICredentials).where(
            SmartAPICredentials.user_id == user.id
        )
    )
    smartapi_creds = creds_result.scalar_one_or_none()

    # Check if Kite is configured
    from app.models.broker_connections import BrokerConnection
    kite_result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id
        )
    )
    kite_connection = kite_result.scalar_one_or_none()

    # Validate selected source is configured
    if request.source == MarketDataSource.SMARTAPI:
        if not smartapi_creds or not smartapi_creds.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SmartAPI credentials not configured. Please add credentials first."
            )

    if request.source == MarketDataSource.KITE:
        if not kite_connection or not kite_connection.access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kite not configured. Please login with Zerodha first."
            )

    # Update preferences
    prefs_result = await db.execute(
        select(UserPreferences).where(
            UserPreferences.user_id == user.id
        )
    )
    preferences = prefs_result.scalar_one_or_none()

    if not preferences:
        preferences = UserPreferences(
            user_id=user.id,
            market_data_source=request.source
        )
        db.add(preferences)
    else:
        preferences.market_data_source = request.source

    await db.commit()

    logger.info(f"[SmartAPI] Market data source updated to {request.source} for user {user.id}")

    return MarketDataSourceResponse(
        source=request.source,
        smartapi_configured=bool(smartapi_creds and smartapi_creds.is_active),
        kite_configured=bool(kite_connection and kite_connection.access_token)
    )
