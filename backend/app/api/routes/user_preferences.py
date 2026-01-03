"""
User Preferences API Routes

Endpoints for managing user preferences and settings.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, UserPreferences
from app.schemas.user_preferences import (
    UserPreferencesResponse,
    UserPreferencesUpdateRequest
)
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=UserPreferencesResponse)
async def get_user_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's preferences.

    Returns:
        User preferences with default values if not set
    """
    result = await db.execute(
        select(UserPreferences).where(
            UserPreferences.user_id == user.id
        )
    )
    preferences = result.scalar_one_or_none()

    if not preferences:
        # Create default preferences
        from app.models.user_preferences import MarketDataSource
        preferences = UserPreferences(
            user_id=user.id,
            pnl_grid_interval=100,
            market_data_source=MarketDataSource.SMARTAPI
        )
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)

    return UserPreferencesResponse.model_validate(preferences)


@router.put("/", response_model=UserPreferencesResponse)
async def update_user_preferences(
    request: UserPreferencesUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user's preferences.

    Args:
        request: Preferences update request

    Returns:
        Updated user preferences
    """
    result = await db.execute(
        select(UserPreferences).where(
            UserPreferences.user_id == user.id
        )
    )
    preferences = result.scalar_one_or_none()

    if not preferences:
        # Create if doesn't exist
        preferences = UserPreferences(user_id=user.id)
        db.add(preferences)

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)

    # Validate interval value
    if 'pnl_grid_interval' in update_data:
        interval = update_data['pnl_grid_interval']
        if interval not in [50, 100]:
            raise HTTPException(
                status_code=400,
                detail="pnl_grid_interval must be either 50 or 100"
            )

    # Validate market_data_source
    if 'market_data_source' in update_data:
        from app.models.user_preferences import MarketDataSource
        source = update_data['market_data_source']
        if source not in MarketDataSource.VALID_SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"market_data_source must be one of: {MarketDataSource.VALID_SOURCES}"
            )

    for key, value in update_data.items():
        setattr(preferences, key, value)

    await db.commit()
    await db.refresh(preferences)

    return UserPreferencesResponse.model_validate(preferences)
