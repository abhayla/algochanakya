"""Fyers OAuth 2.0 authentication endpoints.

OAuth 2.0 with SHA256 appIdHash for token exchange.
Token expires midnight IST daily.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import hashlib
import httpx
import logging

from app.database import get_db, get_redis
from app.config import settings
from app.models import User, BrokerConnection
from app.utils.jwt import create_access_token
from app.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/fyers/login")
async def fyers_login():
    """Return Fyers OAuth authorization URL."""
    if not settings.FYERS_APP_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fyers App ID not configured",
        )

    login_url = (
        "https://api-t1.fyers.in/api/v3/generate-authcode"
        f"?client_id={settings.FYERS_APP_ID}"
        f"&redirect_uri={settings.FYERS_REDIRECT_URL}"
        f"&response_type=code"
        f"&state=algochanakya"
    )
    return {"login_url": login_url}


@router.get("/fyers/callback")
async def fyers_callback(
    auth_code: str,
    s: str = "ok",
    state: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Handle Fyers OAuth callback.

    Note: Fyers uses `auth_code` (not `code`) and `s` (not `status`).
    """
    if s != "ok":
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message=Fyers auth denied",
            status_code=302,
        )

    try:
        # Build appIdHash = SHA256(app_id:secret_key)
        app_id_hash = hashlib.sha256(
            f"{settings.FYERS_APP_ID}:{settings.FYERS_SECRET_KEY}".encode()
        ).hexdigest()

        # Exchange auth_code for access_token
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(
                "https://api-t1.fyers.in/api/v3/validate-authcode",
                json={
                    "grant_type": "authorization_code",
                    "appIdHash": app_id_hash,
                    "code": auth_code,
                },
            )

        token_data = token_resp.json()
        if token_data.get("s") != "ok" or not token_data.get("access_token"):
            msg = token_data.get("message", "Token exchange failed")
            logger.error(f"[Fyers] Token exchange failed: {msg}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message={msg}",
                status_code=302,
            )

        access_token = token_data["access_token"]

        # Get profile — Fyers uses {client_id}:{access_token} as auth header
        async with httpx.AsyncClient(timeout=15) as client:
            profile_resp = await client.get(
                "https://api-t1.fyers.in/api/v3/profile",
                headers={"Authorization": f"{settings.FYERS_APP_ID}:{access_token}"},
            )

        profile_data = profile_resp.json()
        profile = profile_data.get("data", {})
        broker_user_id = profile.get("fy_id", "unknown")
        email = profile.get("email_id")

        # Find or create user
        result = await db.execute(
            select(User).join(BrokerConnection).where(
                BrokerConnection.broker == "fyers",
                BrokerConnection.broker_user_id == broker_user_id,
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(email=email)
            db.add(user)
            await db.flush()

        user.last_login = datetime.utcnow()

        # Find or create broker connection
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == "fyers",
                BrokerConnection.broker_user_id == broker_user_id,
            )
        )
        broker_connection = result.scalar_one_or_none()

        if broker_connection:
            broker_connection.access_token = access_token
            broker_connection.is_active = True
            broker_connection.updated_at = datetime.utcnow()
            broker_connection.broker_metadata = {"client_id": settings.FYERS_APP_ID}
        else:
            broker_connection = BrokerConnection(
                user_id=user.id,
                broker="fyers",
                broker_user_id=broker_user_id,
                access_token=access_token,
                is_active=True,
                broker_metadata={"client_id": settings.FYERS_APP_ID},
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
            logger.warning(f"[Fyers] Redis session storage failed: {e}")

        logger.info(f"[Fyers] Login successful for {broker_user_id}")

        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}",
            status_code=302,
        )

    except Exception as e:
        logger.error(f"[Fyers] Callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message={str(e)}",
            status_code=302,
        )


@router.delete("/fyers/disconnect")
async def fyers_disconnect(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect active Fyers broker connection."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id,
            BrokerConnection.broker == "fyers",
            BrokerConnection.is_active == True,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No active Fyers connection found")
    conn.is_active = False
    conn.access_token = None
    conn.updated_at = datetime.utcnow()
    await db.commit()
    logger.info(f"[Fyers] Disconnected user {user.id}")
    return {"success": True, "message": "Fyers disconnected"}
