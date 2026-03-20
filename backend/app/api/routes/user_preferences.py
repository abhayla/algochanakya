"""
User Preferences API Routes

Endpoints for managing user preferences and settings.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, UserPreferences
from app.models.user_preferences import MarketDataSource, OrderBroker
from app.schemas.user_preferences import (
    UserPreferencesResponse,
    UserPreferencesUpdateRequest,
    BrokerCredentialStatusResponse
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
        preferences = UserPreferences(
            user_id=user.id,
            pnl_grid_interval=100,
            market_data_source=MarketDataSource.PLATFORM
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
        source = update_data['market_data_source']
        if source not in MarketDataSource.VALID_SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"market_data_source must be one of: {MarketDataSource.VALID_SOURCES}"
            )

    # Validate order_broker
    if 'order_broker' in update_data and update_data['order_broker'] is not None:
        broker = update_data['order_broker']
        if broker not in OrderBroker.VALID_BROKERS:
            raise HTTPException(
                status_code=400,
                detail=f"order_broker must be one of: {OrderBroker.VALID_BROKERS}"
            )

    old_source = preferences.market_data_source if hasattr(preferences, 'market_data_source') else None

    for key, value in update_data.items():
        setattr(preferences, key, value)

    await db.commit()
    await db.refresh(preferences)

    # Trigger live WebSocket switch if market_data_source changed
    if 'market_data_source' in update_data:
        try:
            from app.services.brokers.market_data.ticker import TickerRouter
            ticker_router = TickerRouter.get_instance()
            await ticker_router.switch_user_broker(str(user.id), update_data['market_data_source'])
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "Live broker switch failed for user %s: %s", user.id, e
            )

    return UserPreferencesResponse.model_validate(preferences)


BROKER_NAME_TO_KEY = {
    "zerodha": "kite",
    "upstox": "upstox",
    "dhan": "dhan",
    "fyers": "fyers",
    "paytm": "paytm",
}


@router.get("/broker-status", response_model=BrokerCredentialStatusResponse)
async def get_broker_credential_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get credential configuration status for all supported brokers.

    Returns a boolean for each broker indicating whether valid credentials exist.
    Checks the unified broker_api_credentials table for all brokers.
    """
    from app.models.broker_api_credentials import BrokerAPICredentials

    creds_result = await db.execute(
        select(BrokerAPICredentials).where(
            BrokerAPICredentials.user_id == user.id,
            BrokerAPICredentials.is_active == True,
        )
    )
    creds = creds_result.scalars().all()

    # Map broker names to response keys
    broker_to_key = {
        "angelone": "smartapi",
        "zerodha": "kite",
        "upstox": "upstox",
        "dhan": "dhan",
        "fyers": "fyers",
        "paytm": "paytm",
    }

    status = {}
    for cred in creds:
        key = broker_to_key.get(cred.broker)
        if key:
            status[key] = True

    return BrokerCredentialStatusResponse(**status)
