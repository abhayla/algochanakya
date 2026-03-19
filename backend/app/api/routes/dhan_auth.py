"""Dhan authentication endpoints.

Dhan uses static token auth — user provides client_id + access_token
from the Dhan developer console. No OAuth redirect needed.
"""
from fastapi import APIRouter, Depends, HTTPException, status
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


class DhanLoginRequest(BaseModel):
    client_id: str
    access_token: str


@router.post("/dhan/login")
async def dhan_login(
    body: DhanLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with Dhan using client_id + access_token.

    Validates credentials by calling Dhan orders API,
    creates/updates user and broker connection, returns JWT.
    """
    try:
        # Validate credentials by calling Dhan API
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
                detail="Invalid Dhan credentials. Check your client_id and access_token.",
            )
        if resp.status_code not in (200, 201):
            logger.warning(f"[Dhan] Validation returned status {resp.status_code}: {resp.text[:200]}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Dhan API returned unexpected status {resp.status_code}",
            )

        broker_user_id = body.client_id

        # Resolve or create user (prevents duplicates across brokers)
        user = await resolve_or_create_user(
            db=db, broker="dhan", broker_user_id=broker_user_id
        )

        user.last_login = datetime.utcnow()

        # Find or create broker connection
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
            broker_connection.updated_at = datetime.utcnow()
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
            logger.warning(f"[Dhan] Redis session storage failed (continuing): {e}")

        logger.info(f"[Dhan] Login successful for {broker_user_id}")

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
        logger.error(f"[Dhan] Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dhan login failed: {str(e)}",
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
    conn.updated_at = datetime.utcnow()
    await db.commit()
    logger.info(f"[Dhan] Disconnected user {user.id}")
    return {"success": True, "message": "Dhan disconnected"}
