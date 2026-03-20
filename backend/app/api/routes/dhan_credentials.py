"""
Dhan Credentials API Routes

Endpoints for Dhan credential management (Tier 3).
Uses the unified broker_api_credentials table with broker='dhan'.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.models.broker_api_credentials import BrokerAPICredentials
from app.schemas.dhan_credentials import (
    DhanCredentialsCreate,
    DhanCredentialsResponse,
)
from app.utils.dependencies import get_current_user
from app.utils.encryption import encrypt

logger = logging.getLogger(__name__)

router = APIRouter()

BROKER = "dhan"


def _query(user_id):
    return select(BrokerAPICredentials).where(
        BrokerAPICredentials.user_id == user_id,
        BrokerAPICredentials.broker == BROKER
    )


@router.get("/credentials", response_model=DhanCredentialsResponse)
async def get_dhan_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if Dhan credentials are configured for the user."""
    result = await db.execute(_query(user.id))
    credentials = result.scalar_one_or_none()

    if not credentials:
        return DhanCredentialsResponse(has_credentials=False, is_active=False)

    return DhanCredentialsResponse(
        has_credentials=True,
        client_id=credentials.client_id,
        is_active=credentials.is_active,
        last_auth_at=credentials.last_auth_at,
        last_error=credentials.last_error,
    )


@router.post("/credentials", response_model=DhanCredentialsResponse)
async def store_dhan_credentials(
    request: DhanCredentialsCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Store Dhan credentials (access_token encrypted)."""
    try:
        encrypted_access_token = encrypt(request.access_token)
        now = datetime.now(timezone.utc)

        result = await db.execute(_query(user.id))
        credentials = result.scalar_one_or_none()

        if credentials:
            credentials.client_id = request.client_id
            credentials.access_token = encrypted_access_token
            credentials.is_active = True
            credentials.last_auth_at = now
            credentials.last_error = None
            credentials.updated_at = now
        else:
            credentials = BrokerAPICredentials(
                user_id=user.id,
                broker=BROKER,
                client_id=request.client_id,
                access_token=encrypted_access_token,
                is_active=True,
                last_auth_at=now,
            )
            db.add(credentials)

        await db.commit()
        await db.refresh(credentials)

        logger.info(f"[DhanCredentials] Stored for user {user.id}")

        return DhanCredentialsResponse(
            has_credentials=True,
            client_id=credentials.client_id,
            is_active=credentials.is_active,
            last_auth_at=credentials.last_auth_at,
            last_error=credentials.last_error,
        )

    except Exception as e:
        logger.error(f"[DhanCredentials] Failed to store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store credentials"
        )


@router.delete("/credentials")
async def delete_dhan_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete Dhan credentials for the user."""
    result = await db.execute(_query(user.id))
    credentials = result.scalar_one_or_none()

    if not credentials:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No credentials found")

    await db.delete(credentials)
    await db.commit()

    logger.info(f"[DhanCredentials] Deleted for user {user.id}")
    return {"message": "Credentials deleted successfully"}
