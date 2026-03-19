"""
Market Data Broker Factory

Factory function to instantiate market data adapters based on broker type.
Retrieves credentials from database and creates appropriate adapter instance.

Usage:
    adapter = await get_market_data_adapter("smartapi", user_id, db)
    quote = await adapter.get_quote(["NIFTY25APR25000CE"])
"""

import logging
import os
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.brokers.market_data.market_data_base import (
    MarketDataBrokerAdapter,
    MarketDataBrokerType,
    SmartAPIMarketDataCredentials,
    KiteMarketDataCredentials,
    DhanMarketDataCredentials,
    FyersMarketDataCredentials,
    PaytmMarketDataCredentials,
    UpstoxMarketDataCredentials,
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
        return await _create_upstox_adapter(user_id, db)
    elif broker_type == MarketDataBrokerType.DHAN:
        return await _create_dhan_adapter(user_id, db)
    elif broker_type == MarketDataBrokerType.FYERS:
        return await _create_fyers_adapter(user_id, db)
    elif broker_type == MarketDataBrokerType.PAYTM:
        return await _create_paytm_adapter(user_id, db)
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
    from app.utils.smartapi_utils import get_valid_smartapi_credentials

    try:
        # Get SmartAPI credentials with automatic token refresh if expired
        creds = await get_valid_smartapi_credentials(user_id, db, auto_refresh=True)

        if not creds:
            raise AuthenticationError(
                "smartapi",
                "SmartAPI credentials not found or token refresh failed. Please check Settings."
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
        # Skip instrument download - it's lazy-loaded only when needed for option symbols
        # This makes index quote requests fast
        from app.services.brokers.market_data.smartapi_adapter import SmartAPIMarketDataAdapter
        adapter = SmartAPIMarketDataAdapter(credentials, db)
        await adapter.connect(skip_instrument_download=True)

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
            api_key=os.getenv("KITE_API_KEY", ""),
            access_token=conn.access_token
        )

        # Create and initialize adapter
        from app.services.brokers.market_data.kite_adapter import KiteMarketDataAdapter
        adapter = KiteMarketDataAdapter(credentials, db)
        await adapter.connect()

        logger.info(f"[Factory] Created Kite adapter for user {user_id}")
        return adapter

    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"[Factory] Failed to create Kite adapter: {e}")
        raise AuthenticationError("kite", f"Failed to initialize: {str(e)}")


async def _create_fyers_adapter(user_id: UUID, db: AsyncSession) -> MarketDataBrokerAdapter:
    """
    Create Fyers adapter with credentials from database.

    Fyers uses OAuth access_token stored in BrokerConnection (broker="fyers").
    Auth header format: {app_id}:{access_token} (colon-separated).

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        FyersMarketDataAdapter instance

    Raises:
        AuthenticationError: If credentials not found or token expired
    """
    try:
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user_id,
                BrokerConnection.broker == "fyers"
            )
        )
        conn = result.scalar_one_or_none()

        if not conn:
            raise AuthenticationError(
                "fyers",
                "Fyers credentials not found. Please login via Fyers OAuth in Settings."
            )

        if not conn.access_token:
            raise AuthenticationError(
                "fyers",
                "Fyers access token missing or expired. Please re-login via OAuth."
            )

        credentials = FyersMarketDataCredentials(
            broker_type="fyers",
            user_id=user_id,
            app_id=os.getenv("FYERS_APP_ID", ""),
            access_token=conn.access_token,
        )

        from app.services.brokers.market_data.fyers_adapter import FyersMarketDataAdapter
        adapter = FyersMarketDataAdapter(credentials, db)
        await adapter.connect()

        logger.info(f"[Factory] Created Fyers adapter for user {user_id}")
        return adapter

    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"[Factory] Failed to create Fyers adapter: {e}")
        raise AuthenticationError("fyers", f"Failed to initialize: {str(e)}")


async def _create_dhan_adapter(user_id: UUID, db: AsyncSession) -> MarketDataBrokerAdapter:
    """
    Create Dhan adapter with credentials from database.

    Dhan uses a static access token stored in BrokerConnection (broker="dhan").

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        DhanMarketDataAdapter instance

    Raises:
        AuthenticationError: If credentials not found
    """
    try:
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user_id,
                BrokerConnection.broker == "dhan"
            )
        )
        conn = result.scalar_one_or_none()

        if not conn:
            raise AuthenticationError(
                "dhan",
                "Dhan credentials not found. Please add your Dhan API token in Settings."
            )

        if not conn.access_token:
            raise AuthenticationError(
                "dhan",
                "Dhan access token missing. Please re-enter your credentials in Settings."
            )

        credentials = DhanMarketDataCredentials(
            broker_type="dhan",
            user_id=user_id,
            client_id=conn.client_id or "",
            access_token=conn.access_token,
        )

        from app.services.brokers.market_data.dhan_adapter import DhanMarketDataAdapter
        adapter = DhanMarketDataAdapter(credentials, db)
        await adapter.connect()

        logger.info(f"[Factory] Created Dhan adapter for user {user_id}")
        return adapter

    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"[Factory] Failed to create Dhan adapter: {e}")
        raise AuthenticationError("dhan", f"Failed to initialize: {str(e)}")


async def _create_upstox_adapter(user_id: UUID, db: AsyncSession) -> MarketDataBrokerAdapter:
    """
    Create Upstox adapter with credentials from database.

    Upstox uses OAuth access_token or long-lived extended_token stored in
    BrokerConnection (broker="upstox").

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        UpstoxMarketDataAdapter instance

    Raises:
        AuthenticationError: If credentials not found or token expired
    """
    try:
        # Try user-specific connection first
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user_id,
                BrokerConnection.broker == "upstox"
            )
        )
        conn = result.scalar_one_or_none()
        access_token = conn.access_token if conn else None

        # Fall back to platform .env token (used when Upstox is platform market data source)
        if not access_token:
            access_token = os.getenv("UPSTOX_ACCESS_TOKEN", "")

        if not access_token:
            raise AuthenticationError(
                "upstox",
                "Upstox credentials not found. Please login via Upstox OAuth in Settings."
            )

        credentials = UpstoxMarketDataCredentials(
            broker_type="upstox",
            user_id=user_id,
            api_key=os.getenv("UPSTOX_API_KEY", ""),
            access_token=access_token,
        )

        from app.services.brokers.market_data.upstox_adapter import UpstoxMarketDataAdapter
        adapter = UpstoxMarketDataAdapter(credentials, db)
        await adapter.connect()

        logger.info(f"[Factory] Created Upstox adapter for user {user_id} (platform token: {not conn})")
        return adapter

    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"[Factory] Failed to create Upstox adapter: {e}")
        raise AuthenticationError("upstox", f"Failed to initialize: {str(e)}")


async def _create_paytm_adapter(user_id: UUID, db: AsyncSession) -> MarketDataBrokerAdapter:
    """
    Create Paytm Money adapter with credentials from database.

    Paytm uses OAuth 3-token system; the access_token stored in BrokerConnection
    is used as the read token for REST market data calls.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        PaytmMarketDataAdapter instance

    Raises:
        AuthenticationError: If credentials not found or token expired
    """
    try:
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user_id,
                BrokerConnection.broker == "paytm"
            )
        )
        conn = result.scalar_one_or_none()

        if not conn:
            raise AuthenticationError(
                "paytm",
                "Paytm credentials not found. Please login via Paytm Money OAuth in Settings."
            )

        if not conn.access_token:
            raise AuthenticationError(
                "paytm",
                "Paytm access token missing or expired. Please re-login via OAuth."
            )

        credentials = PaytmMarketDataCredentials(
            broker_type="paytm",
            user_id=user_id,
            api_key=os.getenv("PAYTM_API_KEY", ""),
            access_token=conn.access_token,
        )

        from app.services.brokers.market_data.paytm_adapter import PaytmMarketDataAdapter
        adapter = PaytmMarketDataAdapter(credentials, db)
        await adapter.connect()

        logger.info(f"[Factory] Created Paytm adapter for user {user_id}")
        return adapter

    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"[Factory] Failed to create Paytm adapter: {e}")
        raise AuthenticationError("paytm", f"Failed to initialize: {str(e)}")


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


async def get_platform_market_data_adapter(db: AsyncSession) -> MarketDataBrokerAdapter:
    """Create a market data adapter using platform credentials (no user context).

    Tries brokers in the platform fallback chain. Many brokers download
    public instrument CSVs that don't need auth, so credential-free brokers
    are attempted first.

    Returns:
        MarketDataBrokerAdapter instance

    Raises:
        RuntimeError: If no platform adapter could be created
    """
    import os

    errors: list[str] = []

    # 1. SmartAPI — try any user's credentials
    try:
        from app.utils.smartapi_utils import get_valid_smartapi_credentials
        from app.models.smartapi_credentials import SmartAPICredentials as SmartAPICreds

        # Find any active SmartAPI credential
        result = await db.execute(
            select(SmartAPICreds).where(SmartAPICreds.jwt_token.isnot(None)).limit(1)
        )
        cred = result.scalar_one_or_none()

        if cred:
            creds = await get_valid_smartapi_credentials(cred.user_id, db, auto_refresh=True)
            if creds:
                credentials = SmartAPIMarketDataCredentials(
                    broker_type="smartapi",
                    user_id=cred.user_id,
                    client_id=creds.client_id,
                    jwt_token=creds.jwt_token,
                    feed_token=creds.feed_token,
                )
                from app.services.brokers.market_data.smartapi_adapter import SmartAPIMarketDataAdapter
                adapter = SmartAPIMarketDataAdapter(credentials, db)
                await adapter.connect(skip_instrument_download=True)
                logger.info("[Factory] Platform adapter: SmartAPI")
                return adapter
    except Exception as e:
        errors.append(f"SmartAPI: {e}")

    # 2-5. Brokers with env-based credentials (instrument CSVs are public)
    env_brokers = [
        ("dhan", "DHAN_CLIENT_ID", "DHAN_ACCESS_TOKEN", DhanMarketDataCredentials,
         "app.services.brokers.market_data.dhan_adapter", "DhanMarketDataAdapter"),
        ("fyers", "FYERS_APP_ID", "FYERS_ACCESS_TOKEN", FyersMarketDataCredentials,
         "app.services.brokers.market_data.fyers_adapter", "FyersMarketDataAdapter"),
        ("paytm", "PAYTM_API_KEY", "PAYTM_PUBLIC_ACCESS_TOKEN", PaytmMarketDataCredentials,
         "app.services.brokers.market_data.paytm_adapter", "PaytmMarketDataAdapter"),
        ("upstox", "UPSTOX_API_KEY", "UPSTOX_ACCESS_TOKEN", UpstoxMarketDataCredentials,
         "app.services.brokers.market_data.upstox_adapter", "UpstoxMarketDataAdapter"),
    ]

    for broker_name, key1_env, key2_env, cred_cls, module_path, cls_name in env_brokers:
        key1 = os.environ.get(key1_env, "")
        key2 = os.environ.get(key2_env, "")

        if not key1 and not key2:
            continue

        try:
            import importlib
            mod = importlib.import_module(module_path)
            adapter_cls = getattr(mod, cls_name)

            # Build credentials — field names vary per broker
            if broker_name == "dhan":
                creds = cred_cls(broker_type=broker_name, user_id=UUID(int=0),
                                 client_id=key1, access_token=key2)
            elif broker_name == "fyers":
                creds = cred_cls(broker_type=broker_name, user_id=UUID(int=0),
                                 app_id=key1, access_token=key2)
            else:
                creds = cred_cls(broker_type=broker_name, user_id=UUID(int=0),
                                 api_key=key1, access_token=key2)

            adapter = adapter_cls(creds, db)
            await adapter.connect()
            logger.info(f"[Factory] Platform adapter: {broker_name}")
            return adapter
        except Exception as e:
            errors.append(f"{broker_name}: {e}")

    # 6. Kite — requires active BrokerConnection (last resort)
    try:
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.broker == "zerodha",
                BrokerConnection.access_token.isnot(None),
            ).limit(1)
        )
        conn = result.scalar_one_or_none()

        if conn:
            credentials = KiteMarketDataCredentials(
                broker_type="kite",
                user_id=conn.user_id,
                api_key=os.getenv("KITE_API_KEY", ""),
                access_token=conn.access_token,
            )
            from app.services.brokers.market_data.kite_adapter import KiteMarketDataAdapter
            adapter = KiteMarketDataAdapter(credentials, db)
            await adapter.connect()
            logger.info("[Factory] Platform adapter: Kite (last resort)")
            return adapter
    except Exception as e:
        errors.append(f"Kite: {e}")

    raise RuntimeError(
        f"[Factory] No platform market data adapter available. Errors: {'; '.join(errors)}"
    )
