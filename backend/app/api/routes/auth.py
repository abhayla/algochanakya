from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from kiteconnect import KiteConnect
from datetime import datetime
import hashlib
import logging

from app.database import get_db, get_redis
from app.config import settings
from app.models import User, BrokerConnection
from app.models.smartapi_credentials import SmartAPICredentials
from app.schemas import UserResponse, BrokerConnectionResponse
from app.utils.jwt import create_access_token
from app.utils.dependencies import get_current_user
from app.utils.encryption import decrypt
from app.services.legacy.smartapi_auth import get_smartapi_auth, SmartAPIAuthError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/zerodha/login")
async def zerodha_login():
    """
    Generate Zerodha Kite Connect login URL.

    Returns:
        JSON with login URL for redirect
    """
    try:
        # Initialize Kite Connect
        kite = KiteConnect(api_key=settings.KITE_API_KEY)

        # Generate login URL
        login_url = kite.login_url()

        return {
            "login_url": login_url,
            "message": "Redirect user to this URL for Zerodha login"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate login URL: {str(e)}"
        )


@router.get("/zerodha/callback")
async def zerodha_callback(
    request_token: str,
    status: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Zerodha OAuth callback.

    Args:
        request_token: Request token from Zerodha
        status: Status from Zerodha callback
        db: Database session

    Returns:
        Redirect to frontend with JWT token
    """
    if status != "success":
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=auth_failed",
            status_code=302
        )

    try:
        # Initialize Kite Connect
        kite = KiteConnect(api_key=settings.KITE_API_KEY)

        # Generate session/access token
        data = kite.generate_session(
            request_token=request_token,
            api_secret=settings.KITE_API_SECRET
        )

        access_token = data["access_token"]

        # Set access token to get user profile
        kite.set_access_token(access_token)

        # Get user profile from Kite
        profile = kite.profile()
        broker_user_id = profile["user_id"]  # e.g., "AB1234"
        email = profile.get("email")  # May be None
        user_name = profile.get("user_name", "")

        # Check if user exists
        result = await db.execute(
            select(User).join(BrokerConnection).where(
                BrokerConnection.broker == "zerodha",
                BrokerConnection.broker_user_id == broker_user_id
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            user = User(email=email)
            db.add(user)
            await db.flush()  # Get user.id

        # Update last login
        user.last_login = datetime.utcnow()

        # Check if broker connection exists
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == "zerodha",
                BrokerConnection.broker_user_id == broker_user_id
            )
        )
        broker_connection = result.scalar_one_or_none()

        if broker_connection:
            # Update existing connection
            broker_connection.access_token = access_token
            broker_connection.is_active = True
            broker_connection.updated_at = datetime.utcnow()
        else:
            # Create new broker connection
            broker_connection = BrokerConnection(
                user_id=user.id,
                broker="zerodha",
                broker_user_id=broker_user_id,
                access_token=access_token,
                is_active=True
            )
            db.add(broker_connection)

        await db.commit()
        await db.refresh(user)
        await db.refresh(broker_connection)

        # Generate JWT token
        jwt_token = create_access_token(
            user_id=user.id,
            broker_connection_id=broker_connection.id
        )

        # Store session in Redis
        redis = await get_redis()
        session_key = f"session:{user.id}"
        await redis.setex(
            session_key,
            settings.JWT_EXPIRY_HOURS * 3600,  # Convert hours to seconds
            jwt_token
        )

        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}",
            status_code=302
        )

    except Exception as e:
        print(f"[ERROR] Zerodha callback failed: {str(e)}")
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message={str(e)}",
            status_code=302
        )


@router.get("/me")
async def get_current_user_info(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user information.

    Requires: Bearer token in Authorization header

    Returns:
        User info with active broker connections
    """
    # Get active broker connections
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id,
            BrokerConnection.is_active == True
        )
    )
    broker_connections = result.scalars().all()

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None
        },
        "broker_connections": [
            {
                "id": str(bc.id),
                "broker": bc.broker,
                "broker_user_id": bc.broker_user_id,
                "is_active": bc.is_active,
                "created_at": bc.created_at.isoformat()
            }
            for bc in broker_connections
        ]
    }


@router.get("/broker/validate")
async def validate_broker_token(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate if the Kite broker access token is still valid.

    Kite tokens expire daily around 6 AM IST. This endpoint checks
    if the stored access token can still make API calls to Zerodha.

    Requires: Bearer token in Authorization header

    Returns:
        is_valid: True if broker token is valid, False otherwise
        message: Description of validation result
    """
    try:
        # Get active broker connection
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == "zerodha",
                BrokerConnection.is_active == True
            )
        )
        broker_connection = result.scalar_one_or_none()

        if not broker_connection:
            return {
                "is_valid": False,
                "message": "No active broker connection found"
            }

        if not broker_connection.access_token:
            return {
                "is_valid": False,
                "message": "No access token stored"
            }

        # Try to make a simple API call to Kite to validate the token
        kite = KiteConnect(api_key=settings.KITE_API_KEY)
        kite.set_access_token(broker_connection.access_token)

        try:
            # profile() is a lightweight API call to validate token
            profile = kite.profile()
            return {
                "is_valid": True,
                "message": "Broker token is valid",
                "broker_user_id": profile.get("user_id")
            }
        except Exception as kite_error:
            error_msg = str(kite_error)
            # Token expired or invalid
            if "TokenException" in error_msg or "403" in error_msg or "Invalid" in error_msg.lower():
                return {
                    "is_valid": False,
                    "message": f"Broker token expired or invalid: {error_msg}"
                }
            # Other Kite API error
            return {
                "is_valid": False,
                "message": f"Kite API error: {error_msg}"
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate broker token: {str(e)}"
        )


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout current user.

    Removes session from Redis and optionally deactivates broker connections.

    Requires: Bearer token in Authorization header
    """
    try:
        # Remove session from Redis
        redis = await get_redis()
        session_key = f"session:{user.id}"
        await redis.delete(session_key)

        return {
            "message": "Logged out successfully",
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.post("/angelone/login")
async def angelone_login(
    db: AsyncSession = Depends(get_db)
):
    """
    Login with AngelOne/SmartAPI using stored credentials.

    Uses stored SmartAPI credentials with auto-TOTP generation.
    No manual TOTP entry required - TOTP is generated automatically
    from the stored TOTP secret.

    This endpoint:
    1. Fetches stored SmartAPI credentials from database
    2. Decrypts PIN and TOTP secret
    3. Authenticates with SmartAPI (auto-generates TOTP)
    4. Creates/updates user and broker connection
    5. Returns JWT token for app authentication

    Returns:
        JSON with JWT token and redirect URL
    """
    try:
        # Get stored SmartAPI credentials (any user for now - single user system)
        result = await db.execute(select(SmartAPICredentials))
        credentials = result.scalar_one_or_none()

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No SmartAPI credentials configured. Please add credentials in Settings first."
            )

        # Decrypt credentials
        try:
            pin = decrypt(credentials.encrypted_pin)
            totp_secret = decrypt(credentials.encrypted_totp_secret)
        except Exception as e:
            logger.error(f"[AngelOne] Failed to decrypt credentials: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to decrypt stored credentials"
            )

        # Authenticate with SmartAPI (auto-TOTP)
        auth = get_smartapi_auth()
        try:
            auth_result = auth.authenticate(
                client_id=credentials.client_id,
                pin=pin,
                totp_secret=totp_secret
            )
        except SmartAPIAuthError as e:
            logger.error(f"[AngelOne] Authentication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"SmartAPI authentication failed: {str(e)}"
            )

        # Get profile from SmartAPI - use the auth service's API instance
        # which already has the correct token set
        from SmartApi import SmartConnect
        api = SmartConnect(api_key=getattr(settings, 'ANGEL_API_KEY', ''))
        api.setAccessToken(auth_result['jwt_token'])

        # Use client_id as the user identifier since getProfile may fail
        # Profile call is optional - we have the client_id from credentials
        broker_user_id = credentials.client_id
        client_name = broker_user_id  # Default to client_id
        email = None

        try:
            profile = api.getProfile(auth_result['jwt_token'])
            if profile and profile.get('data'):
                profile_data = profile['data']
                client_name = profile_data.get('name', broker_user_id)
                email = profile_data.get('email')
        except Exception as profile_error:
            # Profile call failed - continue with basic info
            logger.warning(f"[AngelOne] Profile fetch failed (continuing): {profile_error}")

        logger.info(f"[AngelOne] Authenticated user: {broker_user_id} ({client_name})")

        # Check if user exists with this AngelOne account
        result = await db.execute(
            select(User).join(BrokerConnection).where(
                BrokerConnection.broker == "angelone",
                BrokerConnection.broker_user_id == broker_user_id
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            user = User(email=email)
            db.add(user)
            await db.flush()
            logger.info(f"[AngelOne] Created new user for {broker_user_id}")

        # Update last login
        user.last_login = datetime.utcnow()

        # Check if broker connection exists
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == "angelone",
                BrokerConnection.broker_user_id == broker_user_id
            )
        )
        broker_connection = result.scalar_one_or_none()

        if broker_connection:
            # Update existing connection
            broker_connection.access_token = auth_result['jwt_token']
            broker_connection.is_active = True
            broker_connection.updated_at = datetime.utcnow()
        else:
            # Create new broker connection
            broker_connection = BrokerConnection(
                user_id=user.id,
                broker="angelone",
                broker_user_id=broker_user_id,
                access_token=auth_result['jwt_token'],
                is_active=True
            )
            db.add(broker_connection)

        # Update SmartAPI credentials with new tokens
        credentials.jwt_token = auth_result['jwt_token']
        credentials.refresh_token = auth_result.get('refresh_token')
        credentials.feed_token = auth_result['feed_token']
        credentials.token_expiry = auth_result['token_expiry']
        credentials.last_auth_at = datetime.utcnow()
        credentials.last_error = None
        credentials.is_active = True
        credentials.user_id = user.id  # Link to user

        await db.commit()
        await db.refresh(user)
        await db.refresh(broker_connection)

        # Generate JWT token for app
        jwt_token = create_access_token(
            user_id=user.id,
            broker_connection_id=broker_connection.id
        )

        # Store session in Redis (optional - login still works without Redis)
        try:
            redis = await get_redis()
            session_key = f"session:{user.id}"
            await redis.setex(
                session_key,
                settings.JWT_EXPIRY_HOURS * 3600,
                jwt_token
            )
        except Exception as redis_error:
            # Redis is optional for login - warn but continue
            logger.warning(f"[AngelOne] Redis session storage failed (continuing): {redis_error}")

        logger.info(f"[AngelOne] Login successful for {broker_user_id}")

        return {
            "success": True,
            "token": jwt_token,
            "redirect_url": f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}",
            "user": {
                "id": str(user.id),
                "broker_user_id": broker_user_id,
                "name": client_name,
                "email": email
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AngelOne] Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )
