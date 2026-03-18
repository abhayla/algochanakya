"""Upstox OAuth 2.0 authentication endpoints.

Standard OAuth 2.0 code flow. Token validity ~1 year.
Uses httpx (no SDK needed).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import httpx
import logging

from app.database import get_db, get_redis
from app.config import settings
from app.models import User, BrokerConnection
from app.utils.jwt import create_access_token
from app.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/upstox/login")
async def upstox_login():
    """Return Upstox OAuth authorization URL."""
    if not settings.UPSTOX_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upstox API key not configured",
        )

    login_url = (
        "https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code"
        f"&client_id={settings.UPSTOX_API_KEY}"
        f"&redirect_uri={settings.UPSTOX_REDIRECT_URL}"
    )
    return {"login_url": login_url}


@router.get("/upstox/callback")
async def upstox_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Upstox OAuth callback — exchange code for access token."""
    try:
        # Exchange code for token
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(
                "https://api.upstox.com/v2/login/authorization/token",
                data={
                    "code": code,
                    "client_id": settings.UPSTOX_API_KEY,
                    "client_secret": settings.UPSTOX_API_SECRET,
                    "redirect_uri": settings.UPSTOX_REDIRECT_URL,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if token_resp.status_code != 200:
            logger.error(f"[Upstox] Token exchange failed: {token_resp.text[:300]}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message=Token exchange failed",
                status_code=302,
            )

        token_data = token_resp.json()
        access_token = token_data["access_token"]

        # Get user profile
        async with httpx.AsyncClient(timeout=15) as client:
            profile_resp = await client.get(
                "https://api.upstox.com/v2/user/profile",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if profile_resp.status_code != 200:
            logger.error(f"[Upstox] Profile fetch failed: {profile_resp.text[:300]}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message=Profile fetch failed",
                status_code=302,
            )

        profile = profile_resp.json().get("data", {})
        broker_user_id = profile.get("user_id", "unknown")
        email = profile.get("email")

        # Find or create user — first by existing Upstox connection, then by email
        result = await db.execute(
            select(User).join(BrokerConnection).where(
                BrokerConnection.broker == "upstox",
                BrokerConnection.broker_user_id == broker_user_id,
            )
        )
        user = result.scalar_one_or_none()

        if not user and email:
            # Check if user already exists with this email (from another broker)
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

        if not user:
            user = User(email=email)
            db.add(user)
            await db.flush()

        # Update first_name from Upstox profile
        user_name = profile.get("user_name", "")
        if user_name and not user.first_name:
            user.first_name = user_name.split()[0].capitalize() if user_name else None

        user.last_login = datetime.utcnow()

        # Find or create broker connection
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == "upstox",
                BrokerConnection.broker_user_id == broker_user_id,
            )
        )
        broker_connection = result.scalar_one_or_none()

        if broker_connection:
            broker_connection.access_token = access_token
            broker_connection.is_active = True
            broker_connection.updated_at = datetime.utcnow()
        else:
            broker_connection = BrokerConnection(
                user_id=user.id,
                broker="upstox",
                broker_user_id=broker_user_id,
                access_token=access_token,
                is_active=True,
            )
            db.add(broker_connection)

        await db.commit()
        await db.refresh(user)
        await db.refresh(broker_connection)

        # Generate JWT
        jwt_token = create_access_token(
            user_id=user.id,
            broker_connection_id=broker_connection.id,
        )

        # Store session in Redis
        try:
            redis = await get_redis()
            await redis.setex(
                f"session:{user.id}",
                settings.JWT_EXPIRY_HOURS * 3600,
                jwt_token,
            )
        except Exception as e:
            logger.warning(f"[Upstox] Redis session storage failed: {e}")

        logger.info(f"[Upstox] Login successful for {broker_user_id}")

        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}",
            status_code=302,
        )

    except Exception as e:
        logger.error(f"[Upstox] Callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message={str(e)}",
            status_code=302,
        )


@router.delete("/upstox/disconnect")
async def upstox_disconnect(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect active Upstox broker connection."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id,
            BrokerConnection.broker == "upstox",
            BrokerConnection.is_active == True,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No active Upstox connection found")
    conn.is_active = False
    conn.access_token = None
    conn.updated_at = datetime.utcnow()
    await db.commit()
    logger.info(f"[Upstox] Disconnected user {user.id}")
    return {"success": True, "message": "Upstox disconnected"}
