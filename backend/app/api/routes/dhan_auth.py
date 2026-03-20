"""Dhan authentication endpoints.

Supports two login methods:
1. OAuth consent flow (DhanHQ v2) — preferred, 24h token with auto-renewal
2. Static token fallback — user pastes client_id + access_token manually
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import httpx
import logging

from app.database import get_db, get_redis
from app.config import settings
from app.models import User, BrokerConnection
from app.utils.jwt import create_access_token
from app.utils.dependencies import get_current_user
from app.utils.user_resolver import resolve_or_create_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# OAuth Consent Flow (DhanHQ v2)
# ============================================================================

@router.get("/dhan/login")
async def dhan_login():
    """
    Initiate Dhan OAuth login.

    Step 1: Generate consent app ID, return URL for browser redirect.
    """
    if not settings.DHAN_APP_ID or not settings.DHAN_APP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dhan OAuth not configured (DHAN_APP_ID / DHAN_APP_SECRET missing)",
        )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://auth.dhan.co/app/generate-consent?client_id={settings.DHAN_CLIENT_ID or settings.DHAN_APP_ID}",
                headers={
                    "app_id": settings.DHAN_APP_ID,
                    "app_secret": settings.DHAN_APP_SECRET,
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            logger.error(f"[Dhan] Consent generation failed: {resp.text[:300]}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to generate Dhan consent",
            )

        consent_app_id = resp.json().get("consentAppId")
        if not consent_app_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Dhan API did not return consentAppId",
            )

        login_url = f"https://auth.dhan.co/login/consentApp-login?consentAppId={consent_app_id}"
        return {"login_url": login_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Dhan] OAuth login initiation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dhan login failed: {e}",
        )


@router.get("/dhan/callback")
async def dhan_callback(
    tokenId: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Dhan OAuth callback.

    Step 3: Exchange tokenId for accessToken, create session, redirect to frontend.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://auth.dhan.co/app/consumeApp-consent?tokenId={tokenId}",
                headers={
                    "app_id": settings.DHAN_APP_ID,
                    "app_secret": settings.DHAN_APP_SECRET,
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            logger.error(f"[Dhan] Token exchange failed: {resp.text[:300]}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message=Dhan token exchange failed",
                status_code=302,
            )

        token_data = resp.json()
        access_token = token_data.get("accessToken", "")
        dhan_client_id = token_data.get("dhanClientId", "")

        if not access_token:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message=No access token returned",
                status_code=302,
            )

        broker_user_id = dhan_client_id

        user = await resolve_or_create_user(
            db=db, broker="dhan", broker_user_id=broker_user_id
        )
        user.last_login = datetime.now(timezone.utc)

        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == "dhan",
                BrokerConnection.broker_user_id == broker_user_id,
            )
        )
        broker_connection = result.scalar_one_or_none()

        if broker_connection:
            broker_connection.access_token = access_token
            broker_connection.is_active = True
            broker_connection.updated_at = datetime.now(timezone.utc)
            broker_connection.token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
            broker_connection.broker_metadata = {"client_id": dhan_client_id}
        else:
            broker_connection = BrokerConnection(
                user_id=user.id,
                broker="dhan",
                broker_user_id=broker_user_id,
                access_token=access_token,
                is_active=True,
                token_expiry=datetime.now(timezone.utc) + timedelta(hours=24),
                broker_metadata={"client_id": dhan_client_id},
            )
            db.add(broker_connection)

        await db.commit()
        await db.refresh(user)
        await db.refresh(broker_connection)

        jwt_token = create_access_token(
            user_id=user.id,
            broker_connection_id=broker_connection.id,
        )

        try:
            redis = await get_redis()
            await redis.setex(
                f"session:{user.id}",
                settings.JWT_EXPIRY_HOURS * 3600,
                jwt_token,
            )
        except Exception as e:
            logger.warning(f"[Dhan] Redis session storage failed: {e}")

        logger.info(f"[Dhan] OAuth login successful for {broker_user_id}")

        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}",
            status_code=302,
        )

    except Exception as e:
        logger.error(f"[Dhan] Callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message={e}",
            status_code=302,
        )


# ============================================================================
# Static Token Login (Fallback)
# ============================================================================

class DhanLoginRequest(BaseModel):
    client_id: str
    access_token: str


@router.post("/dhan/login")
async def dhan_static_login(
    body: DhanLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with Dhan using static client_id + access_token (fallback method).

    Use GET /api/auth/dhan/login for the OAuth flow instead.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.dhan.co/v2/orders",
                headers={
                    "access-token": body.access_token,
                    "client-id": body.client_id,
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Dhan credentials.",
            )
        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Dhan API returned status {resp.status_code}",
            )

        broker_user_id = body.client_id

        user = await resolve_or_create_user(
            db=db, broker="dhan", broker_user_id=broker_user_id
        )
        user.last_login = datetime.now(timezone.utc)

        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == "dhan",
                BrokerConnection.broker_user_id == broker_user_id,
            )
        )
        broker_connection = result.scalar_one_or_none()

        if broker_connection:
            broker_connection.access_token = body.access_token
            broker_connection.is_active = True
            broker_connection.updated_at = datetime.now(timezone.utc)
            broker_connection.broker_metadata = {"client_id": body.client_id}
        else:
            broker_connection = BrokerConnection(
                user_id=user.id,
                broker="dhan",
                broker_user_id=broker_user_id,
                access_token=body.access_token,
                is_active=True,
                broker_metadata={"client_id": body.client_id},
            )
            db.add(broker_connection)

        await db.commit()
        await db.refresh(user)
        await db.refresh(broker_connection)

        jwt_token = create_access_token(
            user_id=user.id,
            broker_connection_id=broker_connection.id,
        )

        try:
            redis = await get_redis()
            await redis.setex(
                f"session:{user.id}",
                settings.JWT_EXPIRY_HOURS * 3600,
                jwt_token,
            )
        except Exception as e:
            logger.warning(f"[Dhan] Redis session storage failed: {e}")

        logger.info(f"[Dhan] Static login successful for {broker_user_id}")

        return {
            "success": True,
            "token": jwt_token,
            "redirect_url": f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}",
            "user": {
                "id": str(user.id),
                "broker_user_id": broker_user_id,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Dhan] Static login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dhan login failed: {e}",
        )


@router.delete("/dhan/disconnect")
async def dhan_disconnect(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect active Dhan broker connection."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id,
            BrokerConnection.broker == "dhan",
            BrokerConnection.is_active == True,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No active Dhan connection found")
    conn.is_active = False
    conn.access_token = None
    conn.updated_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info(f"[Dhan] Disconnected user {user.id}")
    return {"success": True, "message": "Dhan disconnected"}
