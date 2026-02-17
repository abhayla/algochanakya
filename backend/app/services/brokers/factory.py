"""
Broker Factory - Priority 4.2

Factory for creating broker adapters based on broker type.
Provides a unified way to get the appropriate adapter for a user's broker.

IMPORTANT: Before modifying this file, review:
- docs/architecture/broker-abstraction.md - Multi-broker architecture
- docs/DEVELOPER-QUICK-REFERENCE.md - Development patterns
- docs/IMPLEMENTATION-CHECKLIST.md - Current implementation tasks
"""

import logging
from typing import Optional

from app.services.brokers.base import BrokerAdapter, BrokerType
from app.services.brokers.kite_adapter import KiteAdapter
from app.services.brokers.angelone_adapter import AngelOneAdapter
from app.services.brokers.upstox_order_adapter import UpstoxOrderAdapter
from app.services.brokers.dhan_order_adapter import DhanOrderAdapter
from app.services.brokers.fyers_order_adapter import FyersOrderAdapter
from app.services.brokers.paytm_order_adapter import PaytmOrderAdapter

logger = logging.getLogger(__name__)

# Registry of available broker adapters
_BROKER_ADAPTERS = {
    BrokerType.KITE: KiteAdapter,
    BrokerType.ANGEL: AngelOneAdapter,
    BrokerType.UPSTOX: UpstoxOrderAdapter,
    BrokerType.DHAN: DhanOrderAdapter,
    BrokerType.FYERS: FyersOrderAdapter,
    BrokerType.PAYTM: PaytmOrderAdapter,
}


async def get_broker_adapter(
    broker_type: BrokerType,
    access_token: str,
    api_key: Optional[str] = None,
    initialize: bool = True,
    **kwargs,
) -> BrokerAdapter:
    """
    Factory method to get the appropriate broker adapter.

    Args:
        broker_type: Type of broker (KITE, ANGEL, UPSTOX, DHAN, FYERS, PAYTM)
        access_token: OAuth/access token from broker
        api_key: API key (Kite and AngelOne; optional if set in config)
        initialize: Whether to initialize the adapter after creation
        **kwargs: Broker-specific extra args:
            - ANGEL:  client_id (str)
            - DHAN:   client_id (str)
            - FYERS:  client_id (str)
            - PAYTM:  read_token (str), edge_token (str)

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

    # Create adapter with broker-specific constructor args
    if broker_type == BrokerType.KITE:
        adapter = adapter_class(access_token=access_token, api_key=api_key)
    elif broker_type == BrokerType.ANGEL:
        adapter = adapter_class(
            access_token=access_token,
            api_key=api_key,
            client_id=kwargs.get("client_id"),
        )
    elif broker_type == BrokerType.DHAN:
        adapter = adapter_class(
            access_token=access_token,
            client_id=kwargs.get("client_id"),
        )
    elif broker_type == BrokerType.FYERS:
        adapter = adapter_class(
            access_token=access_token,
            client_id=kwargs.get("client_id") or api_key,
        )
    elif broker_type == BrokerType.PAYTM:
        adapter = adapter_class(
            access_token=access_token,
            read_token=kwargs.get("read_token"),
            edge_token=kwargs.get("edge_token"),
        )
    else:
        # UPSTOX and future brokers: access_token only
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


# =========================================================================
# Legacy Format Conversion Helpers
# =========================================================================

def positions_to_legacy_format(positions: list) -> dict:
    """
    Convert List[UnifiedPosition] to legacy {"net": [...], "day": []} format.

    This helper maintains backward compatibility with code that expects
    the old Kite positions format.

    Args:
        positions: List of UnifiedPosition objects

    Returns:
        Dict with "net" and "day" keys containing raw position data
    """
    from app.services.brokers.base import UnifiedPosition

    net_positions = []
    for pos in positions:
        if isinstance(pos, UnifiedPosition):
            # Use raw_response if available, otherwise build dict from UnifiedPosition
            if pos.raw_response:
                net_positions.append(pos.raw_response)
            else:
                net_positions.append({
                    "tradingsymbol": pos.tradingsymbol,
                    "exchange": pos.exchange,
                    "instrument_token": pos.instrument_token,
                    "quantity": pos.quantity,
                    "average_price": float(pos.average_price),
                    "last_price": float(pos.last_price),
                    "pnl": float(pos.pnl),
                    "realised": float(pos.realised_pnl),
                    "unrealised": float(pos.unrealised_pnl),
                    "buy_quantity": pos.buy_quantity,
                    "sell_quantity": pos.sell_quantity,
                    "buy_price": float(pos.buy_average),
                    "sell_price": float(pos.sell_average),
                    "buy_value": float(pos.buy_value),
                    "sell_value": float(pos.sell_value),
                    "value": float(pos.value),
                    "product": pos.product.value if hasattr(pos.product, 'value') else pos.product,
                    "overnight_quantity": pos.overnight_quantity,
                    "day_buy_quantity": pos.day_buy_quantity,
                    "day_sell_quantity": pos.day_sell_quantity,
                    "multiplier": pos.multiplier,
                })
        else:
            # Already a dict
            net_positions.append(pos)

    return {"net": net_positions, "day": []}


def orders_to_legacy_format(orders: list) -> list:
    """
    Convert List[UnifiedOrder] to legacy Kite orders format.

    Args:
        orders: List of UnifiedOrder objects

    Returns:
        List of raw order dictionaries
    """
    from app.services.brokers.base import UnifiedOrder

    result = []
    for order in orders:
        if isinstance(order, UnifiedOrder):
            if order.raw_response:
                result.append(order.raw_response)
            else:
                result.append({
                    "order_id": order.order_id,
                    "exchange": order.exchange,
                    "tradingsymbol": order.tradingsymbol,
                    "instrument_token": order.instrument_token,
                    "transaction_type": order.side.value if hasattr(order.side, 'value') else order.side,
                    "order_type": order.order_type.value if hasattr(order.order_type, 'value') else order.order_type,
                    "product": order.product.value if hasattr(order.product, 'value') else order.product,
                    "quantity": order.quantity,
                    "price": float(order.price) if order.price else 0,
                    "trigger_price": float(order.trigger_price) if order.trigger_price else 0,
                    "status": order.status.value if hasattr(order.status, 'value') else order.status,
                    "filled_quantity": order.filled_quantity,
                    "average_price": float(order.average_price) if order.average_price else 0,
                    "pending_quantity": order.pending_quantity,
                    "tag": order.tag,
                    "validity": order.validity,
                    "status_message": order.status_message,
                })
        else:
            result.append(order)

    return result


def quote_to_legacy_format(quotes: dict) -> dict:
    """
    Convert Dict[str, UnifiedQuote] to legacy Kite quote format.

    Args:
        quotes: Dict mapping instrument to UnifiedQuote

    Returns:
        Dict with legacy quote format
    """
    from app.services.brokers.base import UnifiedQuote

    result = {}
    for key, quote in quotes.items():
        if isinstance(quote, UnifiedQuote):
            if quote.raw_response:
                result[key] = quote.raw_response
            else:
                result[key] = {
                    "instrument_token": quote.instrument_token,
                    "last_price": float(quote.last_price),
                    "ohlc": {
                        "open": float(quote.open),
                        "high": float(quote.high),
                        "low": float(quote.low),
                        "close": float(quote.close),
                    },
                    "volume": quote.volume,
                    "oi": quote.oi,
                    "oi_day_change": quote.oi_change,
                    "net_change": float(quote.change),
                    "depth": {
                        "buy": [{"price": float(quote.bid_price), "quantity": quote.bid_quantity}],
                        "sell": [{"price": float(quote.ask_price), "quantity": quote.ask_quantity}],
                    },
                }
        else:
            result[key] = quote

    return result
