"""
Kite Connect Adapter - Priority 4.2

Implements BrokerAdapter interface for Zerodha Kite Connect.
Converts between Kite-specific formats and unified schemas.
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Optional, Any

from kiteconnect import KiteConnect
from kiteconnect.exceptions import (
    TokenException,
    NetworkException,
    GeneralException,
    InputException
)

from app.config import settings
from app.services.brokers.base import (
    BrokerAdapter,
    BrokerType,
    BrokerCapabilities,
    UnifiedOrder,
    UnifiedPosition,
    UnifiedQuote,
    OrderType,
    OrderSide,
    ProductType,
    OrderStatus
)

logger = logging.getLogger(__name__)


class KiteAdapter(BrokerAdapter):
    """
    Broker adapter for Zerodha Kite Connect.

    Handles all communication with Kite Connect API and converts
    data to/from unified formats.
    """

    # Kite-specific mappings
    KITE_ORDER_TYPE_MAP = {
        OrderType.MARKET: "MARKET",
        OrderType.LIMIT: "LIMIT",
        OrderType.STOP_LOSS: "SL",
        OrderType.STOP_LOSS_MARKET: "SL-M"
    }

    KITE_PRODUCT_MAP = {
        ProductType.NRML: "NRML",
        ProductType.MIS: "MIS"
    }

    KITE_SIDE_MAP = {
        OrderSide.BUY: "BUY",
        OrderSide.SELL: "SELL"
    }

    # Reverse mappings
    ORDER_TYPE_FROM_KITE = {v: k for k, v in KITE_ORDER_TYPE_MAP.items()}
    PRODUCT_FROM_KITE = {v: k for k, v in KITE_PRODUCT_MAP.items()}
    SIDE_FROM_KITE = {v: k for k, v in KITE_SIDE_MAP.items()}

    # Order status mapping from Kite
    STATUS_FROM_KITE = {
        "PENDING": OrderStatus.PENDING,
        "OPEN": OrderStatus.OPEN,
        "COMPLETE": OrderStatus.COMPLETE,
        "CANCELLED": OrderStatus.CANCELLED,
        "REJECTED": OrderStatus.REJECTED,
        "TRIGGER PENDING": OrderStatus.TRIGGER_PENDING,
        "PUT ORDER REQ RECEIVED": OrderStatus.PENDING,
        "VALIDATION PENDING": OrderStatus.PENDING,
        "OPEN PENDING": OrderStatus.PENDING,
        "MODIFY PENDING": OrderStatus.OPEN,
        "MODIFY VALIDATION PENDING": OrderStatus.OPEN,
        "CANCEL PENDING": OrderStatus.OPEN,
    }

    def __init__(self, access_token: str, api_key: str = None):
        """
        Initialize Kite adapter.

        Args:
            access_token: Kite access token
            api_key: Kite API key (optional, uses settings if not provided)
        """
        super().__init__(access_token)
        self.api_key = api_key or settings.KITE_API_KEY
        self.kite: Optional[KiteConnect] = None

    @property
    def broker_type(self) -> BrokerType:
        return BrokerType.KITE

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_basket_orders=True,
            supports_amo=True,
            supports_gtt=True,
            supports_trailing_sl=False,
            max_orders_per_second=10,
            max_instruments_per_quote=500,
            supports_websocket=True,
            supports_historical_data=True
        )

    async def initialize(self) -> bool:
        """Initialize Kite Connect client."""
        try:
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            self._initialized = True
            self._log_info("initialize", "Kite Connect client initialized")
            return True
        except Exception as e:
            self._log_error("initialize", e)
            return False

    async def validate_session(self) -> bool:
        """Validate Kite session by fetching profile."""
        try:
            if not self.kite:
                return False
            profile = self.kite.profile()
            return profile is not None
        except TokenException:
            self._log_info("validate_session", "Token expired or invalid")
            return False
        except Exception as e:
            self._log_error("validate_session", e)
            return False

    # =========================================================================
    # Order Management
    # =========================================================================

    async def place_order(self, order: UnifiedOrder) -> UnifiedOrder:
        """Place order via Kite Connect."""
        try:
            if not self.kite:
                raise Exception("Kite client not initialized")

            # Build Kite order params
            params = {
                "exchange": order.exchange,
                "tradingsymbol": order.tradingsymbol,
                "transaction_type": self.KITE_SIDE_MAP[order.side],
                "quantity": order.quantity,
                "order_type": self.KITE_ORDER_TYPE_MAP[order.order_type],
                "product": self.KITE_PRODUCT_MAP[order.product],
                "validity": order.validity or "DAY"
            }

            # Add price for limit orders
            if order.order_type == OrderType.LIMIT and order.price:
                params["price"] = float(order.price)

            # Add trigger price for SL orders
            if order.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LOSS_MARKET]:
                if order.trigger_price:
                    params["trigger_price"] = float(order.trigger_price)

            # Add tag if present
            if order.tag:
                params["tag"] = order.tag[:20]  # Kite limits to 20 chars

            # Add disclosed quantity
            if order.disclosed_quantity > 0:
                params["disclosed_quantity"] = order.disclosed_quantity

            # Place order
            order_id = self.kite.place_order(variety="regular", **params)

            # Update order with result
            order.order_id = str(order_id)
            order.status = OrderStatus.PENDING
            order.placed_at = datetime.utcnow()

            self._log_info("place_order", f"Order placed: {order_id}")

            return order

        except InputException as e:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = str(e)
            self._log_error("place_order", e)
            return order
        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = str(e)
            self._log_error("place_order", e)
            raise

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
        trigger_price: Optional[Decimal] = None,
        order_type: Optional[OrderType] = None
    ) -> UnifiedOrder:
        """Modify existing order."""
        try:
            if not self.kite:
                raise Exception("Kite client not initialized")

            params = {}
            if quantity is not None:
                params["quantity"] = quantity
            if price is not None:
                params["price"] = float(price)
            if trigger_price is not None:
                params["trigger_price"] = float(trigger_price)
            if order_type is not None:
                params["order_type"] = self.KITE_ORDER_TYPE_MAP[order_type]

            self.kite.modify_order(variety="regular", order_id=order_id, **params)

            # Fetch updated order
            return await self.get_order(order_id)

        except Exception as e:
            self._log_error("modify_order", e)
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            if not self.kite:
                raise Exception("Kite client not initialized")

            self.kite.cancel_order(variety="regular", order_id=order_id)
            self._log_info("cancel_order", f"Order cancelled: {order_id}")
            return True

        except Exception as e:
            self._log_error("cancel_order", e)
            return False

    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """Get order details by ID."""
        try:
            if not self.kite:
                return None

            orders = self.kite.orders()
            for order in orders:
                if str(order.get("order_id")) == order_id:
                    return self._convert_kite_order(order)
            return None

        except Exception as e:
            self._log_error("get_order", e)
            return None

    async def get_orders(self) -> List[UnifiedOrder]:
        """Get all orders for today."""
        try:
            if not self.kite:
                return []

            orders = self.kite.orders()
            return [self._convert_kite_order(o) for o in orders]

        except Exception as e:
            self._log_error("get_orders", e)
            return []

    async def place_basket_order(self, legs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Place multiple orders as a basket (legacy format).

        This method accepts a list of dictionaries (similar to KiteOrderService)
        for backward compatibility with existing code.

        Args:
            legs: List of leg dictionaries with:
                - tradingsymbol: Trading symbol
                - exchange: Exchange (default: NFO)
                - transaction_type: BUY or SELL
                - quantity: Order quantity
                - price: Limit price (optional for market orders)
                - order_type: LIMIT or MARKET

        Returns:
            List of order results with success status and order_id or error
        """
        results = []

        for leg in legs:
            try:
                if not self.kite:
                    raise Exception("Kite client not initialized")

                # Determine order type
                order_type_str = leg.get("order_type", "LIMIT").upper()
                if order_type_str == "LIMIT":
                    kite_order_type = self.kite.ORDER_TYPE_LIMIT
                else:
                    kite_order_type = self.kite.ORDER_TYPE_MARKET

                # Build order params
                order_params = {
                    "variety": self.kite.VARIETY_REGULAR,
                    "exchange": leg.get("exchange", self.kite.EXCHANGE_NFO),
                    "tradingsymbol": leg["tradingsymbol"],
                    "transaction_type": (
                        self.kite.TRANSACTION_TYPE_BUY
                        if leg["transaction_type"].upper() == "BUY"
                        else self.kite.TRANSACTION_TYPE_SELL
                    ),
                    "quantity": int(leg["quantity"]),
                    "product": self.kite.PRODUCT_NRML,  # Normal for F&O
                    "order_type": kite_order_type,
                }

                # Add price for limit orders
                if order_type_str == "LIMIT" and leg.get("price"):
                    order_params["price"] = float(leg["price"])

                # Place order
                order_id = self.kite.place_order(**order_params)

                results.append({
                    "tradingsymbol": leg["tradingsymbol"],
                    "success": True,
                    "order_id": order_id,
                    "error": None
                })

                self._log_info("place_basket_order", f"Order placed: {order_id} for {leg['tradingsymbol']}")

            except Exception as e:
                self._log_error("place_basket_order", e)
                results.append({
                    "tradingsymbol": leg.get("tradingsymbol"),
                    "success": False,
                    "order_id": None,
                    "error": str(e)
                })

        return results

    def _convert_kite_order(self, kite_order: Dict) -> UnifiedOrder:
        """Convert Kite order format to unified format."""
        status_str = kite_order.get("status", "PENDING")
        status = self.STATUS_FROM_KITE.get(status_str, OrderStatus.PENDING)

        return UnifiedOrder(
            order_id=str(kite_order.get("order_id", "")),
            exchange=kite_order.get("exchange", ""),
            tradingsymbol=kite_order.get("tradingsymbol", ""),
            instrument_token=kite_order.get("instrument_token"),
            side=self.SIDE_FROM_KITE.get(kite_order.get("transaction_type", "BUY"), OrderSide.BUY),
            order_type=self.ORDER_TYPE_FROM_KITE.get(kite_order.get("order_type", "MARKET"), OrderType.MARKET),
            product=self.PRODUCT_FROM_KITE.get(kite_order.get("product", "NRML"), ProductType.NRML),
            quantity=kite_order.get("quantity", 0),
            price=Decimal(str(kite_order.get("price", 0))) if kite_order.get("price") else None,
            trigger_price=Decimal(str(kite_order.get("trigger_price", 0))) if kite_order.get("trigger_price") else None,
            status=status,
            filled_quantity=kite_order.get("filled_quantity", 0),
            average_price=Decimal(str(kite_order.get("average_price", 0))) if kite_order.get("average_price") else None,
            pending_quantity=kite_order.get("pending_quantity", 0),
            tag=kite_order.get("tag", ""),
            validity=kite_order.get("validity", "DAY"),
            exchange_timestamp=kite_order.get("exchange_timestamp"),
            status_message=kite_order.get("status_message", ""),
            rejection_reason=kite_order.get("status_message", "") if status == OrderStatus.REJECTED else "",
            raw_response=kite_order
        )

    # =========================================================================
    # Position Management
    # =========================================================================

    async def get_positions(self) -> List[UnifiedPosition]:
        """Get all positions."""
        try:
            if not self.kite:
                return []

            positions = self.kite.positions()
            result = []

            # Process net positions
            for pos in positions.get("net", []):
                result.append(self._convert_kite_position(pos, is_day=False))

            return result

        except Exception as e:
            self._log_error("get_positions", e)
            return []

    def _convert_kite_position(self, kite_pos: Dict, is_day: bool = False) -> UnifiedPosition:
        """Convert Kite position to unified format."""
        tradingsymbol = kite_pos.get("tradingsymbol", "")

        # Parse option details from tradingsymbol
        underlying = ""
        expiry = None
        strike = None
        option_type = ""

        # Try to extract from tradingsymbol (e.g., "NIFTY24DEC26000CE")
        # This is a simplified parser - production code should be more robust
        if tradingsymbol:
            for idx in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
                if tradingsymbol.startswith(idx):
                    underlying = idx
                    break

            if tradingsymbol.endswith("CE"):
                option_type = "CE"
            elif tradingsymbol.endswith("PE"):
                option_type = "PE"

        return UnifiedPosition(
            exchange=kite_pos.get("exchange", "NFO"),
            tradingsymbol=tradingsymbol,
            instrument_token=kite_pos.get("instrument_token"),
            underlying=underlying,
            expiry=expiry,
            strike=strike,
            option_type=option_type,
            quantity=kite_pos.get("quantity", 0),
            buy_quantity=kite_pos.get("buy_quantity", 0),
            sell_quantity=kite_pos.get("sell_quantity", 0),
            average_price=Decimal(str(kite_pos.get("average_price", 0))),
            buy_average=Decimal(str(kite_pos.get("buy_price", 0))),
            sell_average=Decimal(str(kite_pos.get("sell_price", 0))),
            last_price=Decimal(str(kite_pos.get("last_price", 0))),
            pnl=Decimal(str(kite_pos.get("pnl", 0))),
            realised_pnl=Decimal(str(kite_pos.get("realised", 0))),
            unrealised_pnl=Decimal(str(kite_pos.get("unrealised", 0))),
            value=Decimal(str(kite_pos.get("value", 0))),
            buy_value=Decimal(str(kite_pos.get("buy_value", 0))),
            sell_value=Decimal(str(kite_pos.get("sell_value", 0))),
            product=self.PRODUCT_FROM_KITE.get(kite_pos.get("product", "NRML"), ProductType.NRML),
            overnight_quantity=kite_pos.get("overnight_quantity", 0),
            day_buy_quantity=kite_pos.get("day_buy_quantity", 0),
            day_sell_quantity=kite_pos.get("day_sell_quantity", 0),
            multiplier=kite_pos.get("multiplier", 1),
            raw_response=kite_pos
        )

    # =========================================================================
    # Market Data
    # =========================================================================

    async def get_ltp(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Get LTP for instruments."""
        try:
            if not self.kite:
                return {}

            ltp_data = self.kite.ltp(instruments)
            result = {}

            for key, data in ltp_data.items():
                result[key] = UnifiedQuote(
                    tradingsymbol=key.split(":")[-1] if ":" in key else key,
                    exchange=key.split(":")[0] if ":" in key else "",
                    instrument_token=data.get("instrument_token"),
                    last_price=Decimal(str(data.get("last_price", 0))),
                    raw_response=data
                )

            return result

        except Exception as e:
            self._log_error("get_ltp", e)
            return {}

    async def get_quote(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Get full quote for instruments."""
        try:
            if not self.kite:
                return {}

            quote_data = self.kite.quote(instruments)
            result = {}

            for key, data in quote_data.items():
                ohlc = data.get("ohlc", {})
                depth = data.get("depth", {})

                # Get best bid/ask
                bid_price = Decimal("0")
                bid_qty = 0
                ask_price = Decimal("0")
                ask_qty = 0

                if depth.get("buy"):
                    bid_price = Decimal(str(depth["buy"][0].get("price", 0)))
                    bid_qty = depth["buy"][0].get("quantity", 0)
                if depth.get("sell"):
                    ask_price = Decimal(str(depth["sell"][0].get("price", 0)))
                    ask_qty = depth["sell"][0].get("quantity", 0)

                result[key] = UnifiedQuote(
                    tradingsymbol=key.split(":")[-1] if ":" in key else key,
                    exchange=key.split(":")[0] if ":" in key else "",
                    instrument_token=data.get("instrument_token"),
                    last_price=Decimal(str(data.get("last_price", 0))),
                    open=Decimal(str(ohlc.get("open", 0))),
                    high=Decimal(str(ohlc.get("high", 0))),
                    low=Decimal(str(ohlc.get("low", 0))),
                    close=Decimal(str(ohlc.get("close", 0))),
                    change=Decimal(str(data.get("net_change", 0))),
                    volume=data.get("volume", 0),
                    oi=data.get("oi", 0),
                    oi_change=data.get("oi_day_change", 0),
                    bid_price=bid_price,
                    bid_quantity=bid_qty,
                    ask_price=ask_price,
                    ask_quantity=ask_qty,
                    last_trade_time=data.get("last_trade_time"),
                    exchange_timestamp=data.get("exchange_timestamp"),
                    raw_response=data
                )

            return result

        except Exception as e:
            self._log_error("get_quote", e)
            return {}

    # =========================================================================
    # Account Information
    # =========================================================================

    async def get_margins(self) -> Dict[str, Any]:
        """Get account margins."""
        try:
            if not self.kite:
                return {}
            return self.kite.margins()
        except Exception as e:
            self._log_error("get_margins", e)
            return {}

    async def get_profile(self) -> Dict[str, Any]:
        """Get user profile."""
        try:
            if not self.kite:
                return {}
            return self.kite.profile()
        except Exception as e:
            self._log_error("get_profile", e)
            return {}

    # =========================================================================
    # Instruments
    # =========================================================================

    async def get_instruments(self, exchange: str = "NFO") -> List[Dict[str, Any]]:
        """Get available instruments."""
        try:
            if not self.kite:
                return []
            return self.kite.instruments(exchange)
        except Exception as e:
            self._log_error("get_instruments", e)
            return []

    # =========================================================================
    # Direct Access (for features not abstracted)
    # =========================================================================

    def get_kite_client(self) -> Optional[KiteConnect]:
        """
        Get direct access to Kite Connect client.

        Use for features not yet abstracted in the unified interface.
        """
        return self.kite
