"""
Multi-Broker Abstraction Layer - Priority 4.2

Provides a unified interface for interacting with different brokers.
Currently supports Zerodha Kite Connect, with architecture ready for:
- Upstox
- Angel One (Angel Broking)
- Fyers

Usage:
    from app.services.brokers import get_broker_adapter, BrokerType

    # Get adapter for user's broker
    adapter = await get_broker_adapter(broker_type=BrokerType.KITE, access_token=token)

    # Use unified methods
    positions = await adapter.get_positions()
    order_id = await adapter.place_order(order_request)
    quote = await adapter.get_ltp(["NSE:NIFTY BANK"])
"""

from app.services.brokers.base import (
    BrokerAdapter,
    BrokerType,
    UnifiedOrder,
    UnifiedPosition,
    UnifiedQuote,
    OrderType,
    OrderSide,
    ProductType,
    OrderStatus
)
from app.services.brokers.kite_adapter import KiteAdapter
from app.services.brokers.factory import get_broker_adapter

__all__ = [
    "BrokerAdapter",
    "BrokerType",
    "UnifiedOrder",
    "UnifiedPosition",
    "UnifiedQuote",
    "OrderType",
    "OrderSide",
    "ProductType",
    "OrderStatus",
    "KiteAdapter",
    "get_broker_adapter"
]
