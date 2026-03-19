"""Paytm Money OAuth authentication endpoints.

Custom OAuth returning 3 tokens:
- access_token (main API)
- public_access_token (WebSocket/public APIs)
- read_access_token (read-only APIs)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
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


@router.get("/paytm/login")
async def paytm_login():
    """Return Paytm Money login URL."""
    if not settings.PAYTM_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Paytm Money API key not configured",
        )

    login_url = (
        "https://login.paytmmoney.com/merchant-login"
        f"?apiKey={settings.PAYTM_API_KEY}"
        f"&state=algochanakya"
    )
    return {"login_url": login_url}


@router.get("/paytm/callback")
async def paytm_callback(
    requestToken: str,
    state: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Handle Paytm Money OAuth callback.

    Note: Paytm uses `requestToken` (camelCase), not `code`.
    Returns 3 tokens: access_token, public_access_token, read_access_token.
    """
    try:
        # Exchange requestToken for 3 tokens
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(
                "https://developer.paytmmoney.com/accounts/v2/gettoken",
                json={
                    "api_key": settings.PAYTM_API_KEY,
                    "api_secret_key": settings.PAYTM_API_SECRET,
                    "request_token": requestToken,
                },
            )

        if token_resp.status_code != 200:
            logger.error(f"[Paytm] Token exchange failed: {token_resp.text[:300]}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message=Token exchange failed",
                status_code=302,
            )

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        public_access_token = token_data.get("public_access_token", "")
        read_access_token = token_data.get("read_access_token", "")

        if not access_token:
            msg = token_data.get("message", "No access token returned")
            logger.error(f"[Paytm] No access token: {msg}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message={msg}",
                status_code=302,
            )

        # Get user profile
        async with httpx.AsyncClient(timeout=15) as client:
            profile_resp = await client.get(
                "https://developer.paytmmoney.com/accounts/v1/user/details",
                headers={
                    "x-jwt-token": access_token,
                    "Content-Type": "application/json",
                },
            )

        broker_user_id = "unknown"
        email = None
        if profile_resp.status_code == 200:
            profile = profile_resp.json()
            broker_user_id = profile.get("client_id") or profile.get("user_id") or "unknown"
            email = profile.get("email")

        # Resolve or create user (prevents duplicates across brokers)
        user = await resolve_or_create_user(
            db=db, broker="paytm", broker_user_id=broker_user_id,
            email=email
        )

        user.last_login = datetime.utcnow()

        # Find or create broker connection
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == "paytm",
                BrokerConnection.broker_user_id == broker_user_id,
            )
        )
        broker_connection = result.scalar_one_or_none()

        metadata = {
            "read_token": public_access_token,
            "edge_token": read_access_token,
        }

        if broker_connection:
            broker_connection.access_token = access_token
            broker_connection.is_active = True
            broker_connection.updated_at = datetime.utcnow()
            broker_connection.broker_metadata = metadata
        else:
            broker_connection = BrokerConnection(
                user_id=user.id,
                broker="paytm",
                broker_user_id=broker_user_id,
                access_token=access_token,
                is_active=True,
                broker_metadata=metadata,
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
            logger.warning(f"[Paytm] Redis session storage failed: {e}")

        logger.info(f"[Paytm] Login successful for {broker_user_id}")

        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}",
            status_code=302,
        )

    except Exception as e:
        logger.error(f"[Paytm] Callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=auth_failed&message={str(e)}",
            status_code=302,
        )


class PaytmPublicTokenRequest(BaseModel):
    public_access_token: str


@router.post("/paytm/public-token")
async def paytm_save_public_token(
    body: PaytmPublicTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save the Paytm public_access_token (WebSocket token) to the broker connection metadata.

    This token is separate from the OAuth access_token and is required for
    live market data via Paytm WebSocket. It must be manually obtained from
    the Paytm developer console.
    """
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id,
            BrokerConnection.broker == "paytm",
            BrokerConnection.is_active == True,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No active Paytm connection found. Connect via OAuth first.")

    metadata = conn.broker_metadata or {}
    metadata["public_access_token"] = body.public_access_token
    conn.broker_metadata = metadata
    conn.updated_at = datetime.utcnow()
    await db.commit()
    logger.info(f"[Paytm] Saved public_access_token for user {user.id}")
    return {"success": True, "message": "Public access token saved"}


@router.delete("/paytm/disconnect")
async def paytm_disconnect(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect active Paytm Money broker connection."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id,
            BrokerConnection.broker == "paytm",
            BrokerConnection.is_active == True,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No active Paytm connection found")
    conn.is_active = False
    conn.access_token = None
    conn.broker_metadata = None
    conn.updated_at = datetime.utcnow()
    await db.commit()
    logger.info(f"[Paytm] Disconnected user {user.id}")
    return {"success": True, "message": "Paytm Money disconnected"}
