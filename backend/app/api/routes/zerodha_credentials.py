"""
Zerodha Credentials API Routes

Endpoints for Zerodha Kite Connect app credential management (Tier 3).
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.models.zerodha_credentials import ZerodhaCredentials
from app.schemas.zerodha_credentials import (
    ZerodhaCredentialsCreate,
    ZerodhaCredentialsResponse,
)
from app.utils.dependencies import get_current_user
from app.utils.encryption import encrypt

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/credentials", response_model=ZerodhaCredentialsResponse)
async def get_zerodha_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if Zerodha API credentials are configured for the user."""
    result = await db.execute(
        select(ZerodhaCredentials).where(ZerodhaCredentials.user_id == user.id)
    )
    credentials = result.scalar_one_or_none()

    if not credentials:
        return ZerodhaCredentialsResponse(has_credentials=False, is_active=False)

    return ZerodhaCredentialsResponse(
        has_credentials=True,
        api_key=credentials.api_key,
        is_active=credentials.is_active,
        last_error=credentials.last_error,
    )


@router.post("/credentials", response_model=ZerodhaCredentialsResponse)
async def store_zerodha_credentials(
    request: ZerodhaCredentialsCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Store Zerodha Kite Connect app credentials (encrypted)."""
    try:
        encrypted_api_secret = encrypt(request.api_secret)

        result = await db.execute(
            select(ZerodhaCredentials).where(ZerodhaCredentials.user_id == user.id)
        )
        credentials = result.scalar_one_or_none()

        if credentials:
            credentials.api_key = request.api_key
            credentials.encrypted_api_secret = encrypted_api_secret
            credentials.is_active = True
            credentials.last_error = None
            credentials.updated_at = datetime.now(timezone.utc)
        else:
            credentials = ZerodhaCredentials(
                user_id=user.id,
                api_key=request.api_key,
                encrypted_api_secret=encrypted_api_secret,
                is_active=True,
            )
            db.add(credentials)

        await db.commit()
        await db.refresh(credentials)

        logger.info(f"[ZerodhaCredentials] Stored for user {user.id}")

        return ZerodhaCredentialsResponse(
            has_credentials=True,
            api_key=credentials.api_key,
            is_active=credentials.is_active,
            last_error=credentials.last_error,
        )

    except Exception as e:
        logger.error(f"[ZerodhaCredentials] Failed to store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store credentials"
        )


@router.delete("/credentials")
async def delete_zerodha_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete Zerodha credentials for the user."""
    result = await db.execute(
        select(ZerodhaCredentials).where(ZerodhaCredentials.user_id == user.id)
    )
    credentials = result.scalar_one_or_none()

    if not credentials:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No credentials found")

    await db.delete(credentials)
    await db.commit()

    logger.info(f"[ZerodhaCredentials] Deleted for user {user.id}")
    return {"message": "Credentials deleted successfully"}
