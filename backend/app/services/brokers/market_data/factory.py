"""
Market Data Broker Factory

Factory function to instantiate market data adapters based on broker type.
Retrieves credentials from database and creates appropriate adapter instance.

Usage:
    adapter = await get_market_data_adapter("smartapi", user_id, db)
    quote = await adapter.get_quote(["NIFTY25APR25000CE"])
"""

import logging
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.brokers.market_data.market_data_base import (
    MarketDataBrokerAdapter,
    MarketDataBrokerType,
    SmartAPIMarketDataCredentials,
    KiteMarketDataCredentials,
)
from app.services.brokers.market_data.exceptions import AuthenticationError
from app.models.smartapi_credentials import SmartAPICredentials
from app.models.broker_connections import BrokerConnection

logger = logging.getLogger(__name__)


async def get_market_data_adapter(
    broker_type: str,
    user_id: UUID,
    db: AsyncSession
) -> MarketDataBrokerAdapter:
    """
    Factory to create market data adapter based on broker type.

    Args:
        broker_type: Broker identifier (smartapi, kite, upstox, etc.)
        user_id: User UUID
        db: Database session

    Returns:
        MarketDataBrokerAdapter instance for the broker

    Raises:
        ValueError: If broker type not supported
        AuthenticationError: If credentials not found or invalid

    Example:
        >>> adapter = await get_market_data_adapter("smartapi", user.id, db)
        >>> quotes = await adapter.get_quote(["NIFTY25APR25000CE"])
    """
    broker_type = broker_type.lower()

    if broker_type == MarketDataBrokerType.SMARTAPI:
        return await _create_smartapi_adapter(user_id, db)
    elif broker_type == MarketDataBrokerType.KITE:
        return await _create_kite_adapter(user_id, db)
    elif broker_type == MarketDataBrokerType.UPSTOX:
        raise NotImplementedError("Upstox market data adapter not yet implemented (Phase 3)")
    elif broker_type == MarketDataBrokerType.DHAN:
        raise NotImplementedError("Dhan market data adapter not yet implemented (Phase 4)")
    elif broker_type == MarketDataBrokerType.FYERS:
        raise NotImplementedError("Fyers market data adapter not yet implemented (Phase 5)")
    elif broker_type == MarketDataBrokerType.PAYTM:
        raise NotImplementedError("Paytm market data adapter not yet implemented (Phase 6)")
    else:
        raise ValueError(f"Unsupported broker type: {broker_type}")


async def _create_smartapi_adapter(user_id: UUID, db: AsyncSession) -> MarketDataBrokerAdapter:
    """
    Create SmartAPI adapter with credentials from database.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        SmartAPIMarketDataAdapter instance

    Raises:
        AuthenticationError: If credentials not found
    """
    try:
        # Get SmartAPI credentials
        result = await db.execute(
            select(SmartAPICredentials).where(SmartAPICredentials.user_id == user_id)
        )
        creds = result.scalar_one_or_none()

        if not creds:
            raise AuthenticationError(
                "smartapi",
                "SmartAPI credentials not found. Please configure in Settings."
            )

        if not creds.is_active:
            raise AuthenticationError(
                "smartapi",
                "SmartAPI credentials are inactive. Please re-authenticate."
            )

        # Create credentials object
        credentials = SmartAPIMarketDataCredentials(
            broker_type="smartapi",
            user_id=user_id,
            client_id=creds.client_id,
            jwt_token=creds.jwt_token,
            feed_token=creds.feed_token
        )

        # Create and initialize adapter
        from app.services.brokers.market_data.smartapi_adapter import SmartAPIMarketDataAdapter
        adapter = SmartAPIMarketDataAdapter(credentials, db)
        await adapter.connect()

        logger.info(f"[Factory] Created SmartAPI adapter for user {user_id}")
        return adapter

    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"[Factory] Failed to create SmartAPI adapter: {e}")
        raise AuthenticationError("smartapi", f"Failed to initialize: {str(e)}")


async def _create_kite_adapter(user_id: UUID, db: AsyncSession) -> MarketDataBrokerAdapter:
    """
    Create Kite adapter with credentials from database.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        KiteMarketDataAdapter instance (Phase 3)

    Raises:
        AuthenticationError: If credentials not found
    """
    try:
        # Get Kite credentials (BrokerConnection)
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user_id,
                BrokerConnection.broker == "zerodha"
            )
        )
        conn = result.scalar_one_or_none()

        if not conn:
            raise AuthenticationError(
                "kite",
                "Kite credentials not found. Please login via Zerodha OAuth."
            )

        if not conn.access_token:
            raise AuthenticationError(
                "kite",
                "Kite access token expired. Please re-login."
            )

        # Create credentials object
        credentials = KiteMarketDataCredentials(
            broker_type="kite",
            user_id=user_id,
            api_key=conn.api_key,
            access_token=conn.access_token
        )

        # Create and initialize adapter (Phase 3 - not implemented yet)
        raise NotImplementedError("Kite market data adapter not yet implemented (Phase 3)")

        # Future implementation:
        # from app.services.brokers.market_data.kite_adapter import KiteMarketDataAdapter
        # adapter = KiteMarketDataAdapter(credentials, db)
        # await adapter.connect()
        # return adapter

    except AuthenticationError:
        raise
    except NotImplementedError:
        raise
    except Exception as e:
        logger.error(f"[Factory] Failed to create Kite adapter: {e}")
        raise AuthenticationError("kite", f"Failed to initialize: {str(e)}")


# Convenience function to get adapter from user preferences
async def get_user_market_data_adapter(user_id: UUID, db: AsyncSession) -> MarketDataBrokerAdapter:
    """
    Get market data adapter based on user's preference.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        MarketDataBrokerAdapter for user's preferred broker

    Raises:
        ValueError: If user preferences not found
        AuthenticationError: If credentials not found
    """
    from app.models.user_preferences import UserPreferences

    # Get user preferences
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Default to SmartAPI if no preferences
        logger.info(f"[Factory] No preferences found for user {user_id}, using SmartAPI")
        broker_type = "smartapi"
    else:
        broker_type = prefs.market_data_source

    return await get_market_data_adapter(broker_type, user_id, db)
