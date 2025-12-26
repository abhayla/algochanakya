"""
Broker Factory - Priority 4.2

Factory for creating broker adapters based on broker type.
Provides a unified way to get the appropriate adapter for a user's broker.
"""

import logging
from typing import Optional

from app.services.brokers.base import BrokerAdapter, BrokerType
from app.services.brokers.kite_adapter import KiteAdapter

logger = logging.getLogger(__name__)

# Registry of available broker adapters
_BROKER_ADAPTERS = {
    BrokerType.KITE: KiteAdapter,
    # Future brokers:
    # BrokerType.UPSTOX: UpstoxAdapter,
    # BrokerType.ANGEL: AngelAdapter,
    # BrokerType.FYERS: FyersAdapter,
}


async def get_broker_adapter(
    broker_type: BrokerType,
    access_token: str,
    api_key: Optional[str] = None,
    initialize: bool = True
) -> BrokerAdapter:
    """
    Factory method to get the appropriate broker adapter.

    Args:
        broker_type: Type of broker (KITE, UPSTOX, etc.)
        access_token: OAuth access token from broker
        api_key: API key (optional, uses settings if not provided)
        initialize: Whether to initialize the adapter after creation

    Returns:
        Initialized broker adapter

    Raises:
        ValueError: If broker type is not supported
        Exception: If initialization fails
    """
    if broker_type not in _BROKER_ADAPTERS:
        supported = [b.value for b in _BROKER_ADAPTERS.keys()]
        raise ValueError(
            f"Unsupported broker type: {broker_type}. "
            f"Supported brokers: {supported}"
        )

    adapter_class = _BROKER_ADAPTERS[broker_type]

    # Create adapter with appropriate args
    if broker_type == BrokerType.KITE:
        adapter = adapter_class(access_token=access_token, api_key=api_key)
    else:
        adapter = adapter_class(access_token=access_token)

    # Initialize if requested
    if initialize:
        success = await adapter.initialize()
        if not success:
            raise Exception(f"Failed to initialize {broker_type.value} adapter")

    logger.info(f"Created {broker_type.value} adapter (initialized={initialize})")
    return adapter


def get_supported_brokers() -> list:
    """
    Get list of supported broker types.

    Returns:
        List of BrokerType values that are currently supported
    """
    return list(_BROKER_ADAPTERS.keys())


def is_broker_supported(broker_type: BrokerType) -> bool:
    """
    Check if a broker type is supported.

    Args:
        broker_type: Broker type to check

    Returns:
        True if broker is supported
    """
    return broker_type in _BROKER_ADAPTERS


# Convenience function for Kite (most common case)
async def get_kite_adapter(access_token: str, api_key: str = None) -> KiteAdapter:
    """
    Get a Kite adapter (convenience function).

    Args:
        access_token: Kite access token
        api_key: Kite API key (optional)

    Returns:
        Initialized KiteAdapter
    """
    adapter = await get_broker_adapter(
        broker_type=BrokerType.KITE,
        access_token=access_token,
        api_key=api_key
    )
    return adapter  # type: ignore
