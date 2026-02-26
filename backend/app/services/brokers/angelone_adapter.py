"""
Angel One (SmartAPI) Order Execution Adapter

Implements BrokerAdapter interface for Angel One using the smartapi-python SDK.
Handles order placement, modification, cancellation, positions, and quotes.

Auth: JWT access_token obtained after PIN+TOTP login.
SDK: smartapi-python (SmartConnect)

Key mappings:
- producttype: CARRYFORWARD (NRML), INTRADAY (MIS)
- ordertype: LIMIT, MARKET, STOPLOSS_LIMIT, STOPLOSS_MARKET
- status: complete, open, rejected, cancelled, pending, trigger pending
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Any

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
    OrderStatus,
)

logger = logging.getLogger(__name__)


# SmartAPI order type strings
_ORDER_TYPE_MAP = {
    OrderType.MARKET: "MARKET",
    OrderType.LIMIT: "LIMIT",
    OrderType.STOP_LOSS: "STOPLOSS_LIMIT",
    OrderType.STOP_LOSS_MARKET: "STOPLOSS_MARKET",
}

_PRODUCT_MAP = {
    ProductType.NRML: "CARRYFORWARD",
    ProductType.MIS: "INTRADAY",
}

_SIDE_MAP = {
    OrderSide.BUY: "BUY",
    OrderSide.SELL: "SELL",
}

# Reverse mappings
_ORDER_TYPE_FROM_ANGEL = {v: k for k, v in _ORDER_TYPE_MAP.items()}
_PRODUCT_FROM_ANGEL = {v: k for k, v in _PRODUCT_MAP.items()}
_SIDE_FROM_ANGEL = {v: k for k, v in _SIDE_MAP.items()}

_STATUS_FROM_ANGEL = {
    "complete": OrderStatus.COMPLETE,
    "open": OrderStatus.OPEN,
    "rejected": OrderStatus.REJECTED,
    "cancelled": OrderStatus.CANCELLED,
    "pending": OrderStatus.PENDING,
    "trigger pending": OrderStatus.TRIGGER_PENDING,
    "open pending": OrderStatus.PENDING,
    "validation pending": OrderStatus.PENDING,
    "put order req received": OrderStatus.PENDING,
    "modify validation pending": OrderStatus.OPEN,
    "cancel pending": OrderStatus.OPEN,
}


class AngelOneAdapter(BrokerAdapter):
    """
    Broker adapter for Angel One (SmartAPI).

    Uses the smartapi-python SDK. Authentication is via JWT access_token
    obtained after PIN+TOTP-based login flow.
    """

    def __init__(self, access_token: str, api_key: str = None, client_id: str = None):
        """
        Initialize Angel One adapter.

        Args:
            access_token: SmartAPI JWT access token
            api_key: SmartAPI API key (optional, uses settings if not provided)
            client_id: Angel One client ID / login ID
        """
        super().__init__(access_token)
        self.api_key = api_key
        self.client_id = client_id
        self.client = None  # SmartConnect instance

    @property
    def broker_type(self) -> BrokerType:
        return BrokerType.ANGEL

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_basket_orders=True,
            supports_amo=True,
            supports_gtt=True,
            supports_trailing_sl=False,
            max_orders_per_second=10,
            max_instruments_per_quote=50,
            supports_websocket=True,
            supports_historical_data=True,
        )

    async def initialize(self) -> bool:
        """
        Initialize SmartConnect client.

        JWT binding rule: a JWT returned by loginByPassword with X-PrivateKey=KEY_A
        is bound to KEY_A.  Using it with a different key returns AG8001.

        Strategy:
        - If access_token is provided, assume the caller has already ensured the JWT
          matches this api_key (e.g. the test fixture pre-authenticates with trade key
          and passes both together).  Reuse without re-login.
        - If access_token is absent, perform a fresh login with this api_key so the
          resulting JWT is correctly bound to it.

        This avoids a second consecutive login when the fixture already provides the
        trade-key JWT, preventing AngelOne's per-minute login rate limit errors.
        """
        try:
            from SmartApi import SmartConnect  # type: ignore
            from app.config import settings

            api_key = self.api_key or (
                getattr(settings, "ANGEL_TRADE_API_KEY", "")
                or getattr(settings, "ANGEL_API_KEY", "")
            )

            self.client = SmartConnect(api_key=api_key)

            if self.access_token:
                # Caller provided a JWT — trust that it matches this api_key and reuse.
                self.client.access_token = self.access_token
                self.client.feed_token = None
                self._log_info("initialize", "Reusing provided access_token")
            else:
                # No JWT — perform a fresh login so the JWT is bound to this api_key.
                import pyotp
                totp = pyotp.TOTP(settings.ANGEL_TOTP_SECRET).now()
                session = self.client.generateSession(
                    settings.ANGEL_CLIENT_ID,
                    settings.ANGEL_PIN,
                    totp,
                )
                if not session or not session.get('status'):
                    self._log_error(
                        "initialize",
                        Exception(f"Fresh login failed: "
                                  f"{session.get('message') if session else 'No response'}")
                    )
                    return False
                self.access_token = session['data']['jwtToken']
                self.client.feed_token = None
                self._log_info("initialize", f"Fresh login successful with api_key={api_key[:4]}...")

            self._initialized = True
            self._log_info("initialize", "SmartConnect client initialized")
            return True
        except Exception as e:
            self._log_error("initialize", e)
            return False

    async def validate_session(self) -> bool:
        """Validate session by fetching profile."""
        try:
            if not self.client:
                return False
            resp = self.client.getProfile(refreshToken="")
            return bool(resp and resp.get("status") is True)
        except Exception as e:
            self._log_error("validate_session", e)
            return False

    # =========================================================================
    # Order Management
    # =========================================================================

    async def place_order(self, order: UnifiedOrder) -> UnifiedOrder:
        """Place order via SmartAPI."""
        try:
            if not self.client:
                raise RuntimeError("SmartConnect client not initialized")

            params = {
                "variety": "NORMAL",
                "tradingsymbol": order.tradingsymbol,
                "symboltoken": str(order.instrument_token or ""),
                "transactiontype": _SIDE_MAP[order.side],
                "exchange": order.exchange,
                "ordertype": _ORDER_TYPE_MAP[order.order_type],
                "producttype": _PRODUCT_MAP[order.product],
                "duration": order.validity or "DAY",
                "price": str(float(order.price)) if order.price else "0",
                "triggerprice": str(float(order.trigger_price)) if order.trigger_price else "0",
                "quantity": str(order.quantity),
            }

            if order.tag:
                params["ordertag"] = order.tag[:20]

            resp = self.client.placeOrder(params)

            if resp and resp.get("status") is True:
                order.order_id = str(resp.get("data", {}).get("orderid", ""))
                order.status = OrderStatus.PENDING
                order.placed_at = datetime.utcnow()
                self._log_info("place_order", f"Order placed: {order.order_id}")
            else:
                msg = resp.get("message", "Unknown error") if resp else "No response"
                order.status = OrderStatus.REJECTED
                order.rejection_reason = msg
                self._log_info("place_order", f"Order rejected: {msg}")

            order.raw_response = resp
            return order

        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = str(e)
            self._log_error("place_order", e)
            return order

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
        trigger_price: Optional[Decimal] = None,
        order_type: Optional[OrderType] = None,
    ) -> UnifiedOrder:
        """Modify existing order via SmartAPI."""
        try:
            if not self.client:
                raise RuntimeError("SmartConnect client not initialized")

            params = {"variety": "NORMAL", "orderid": order_id}
            if quantity is not None:
                params["quantity"] = str(quantity)
            if price is not None:
                params["price"] = str(float(price))
            if trigger_price is not None:
                params["triggerprice"] = str(float(trigger_price))
            if order_type is not None:
                params["ordertype"] = _ORDER_TYPE_MAP[order_type]

            self.client.modifyOrder(params)
            return await self.get_order(order_id) or UnifiedOrder(order_id=order_id)

        except Exception as e:
            self._log_error("modify_order", e)
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order via SmartAPI."""
        try:
            if not self.client:
                return False
            resp = self.client.cancelOrder(order_id, "NORMAL")
            return bool(resp and resp.get("status") is True)
        except Exception as e:
            self._log_error("cancel_order", e)
            return False

    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """Get specific order by ID from order book."""
        orders = await self.get_orders()
        for order in orders:
            if order.order_id == order_id:
                return order
        return None

    async def get_orders(self) -> List[UnifiedOrder]:
        """Get all orders for today."""
        try:
            if not self.client:
                return []
            resp = self.client.orderBook()
            if not resp or resp.get("status") is not True:
                return []
            raw_orders = resp.get("data") or []
            return [self._convert_order(o) for o in raw_orders]
        except Exception as e:
            self._log_error("get_orders", e)
            return []

    def _convert_order(self, raw: Dict) -> UnifiedOrder:
        """Convert SmartAPI order dict to UnifiedOrder."""
        status_str = (raw.get("status") or "pending").lower()
        status = _STATUS_FROM_ANGEL.get(status_str, OrderStatus.PENDING)

        qty_str = raw.get("quantity") or "0"
        filled_str = raw.get("filledshares") or "0"
        avg_str = raw.get("averageprice") or "0"
        price_str = raw.get("price") or "0"
        trig_str = raw.get("triggerprice") or "0"

        return UnifiedOrder(
            order_id=str(raw.get("orderid", "")),
            exchange=raw.get("exchange", ""),
            tradingsymbol=raw.get("tradingsymbol", ""),
            side=_SIDE_FROM_ANGEL.get(raw.get("transactiontype", "BUY"), OrderSide.BUY),
            order_type=_ORDER_TYPE_FROM_ANGEL.get(raw.get("ordertype", "MARKET"), OrderType.MARKET),
            product=_PRODUCT_FROM_ANGEL.get(raw.get("producttype", "CARRYFORWARD"), ProductType.NRML),
            quantity=int(qty_str),
            price=Decimal(price_str) if float(price_str) else None,
            trigger_price=Decimal(trig_str) if float(trig_str) else None,
            status=status,
            filled_quantity=int(filled_str),
            average_price=Decimal(avg_str) if float(avg_str) else None,
            pending_quantity=int(qty_str) - int(filled_str),
            tag=raw.get("ordertag", ""),
            validity=raw.get("duration", "DAY"),
            status_message=raw.get("text", ""),
            rejection_reason=raw.get("text", "") if status == OrderStatus.REJECTED else "",
            raw_response=raw,
        )

    # =========================================================================
    # Position Management
    # =========================================================================

    async def get_positions(self) -> List[UnifiedPosition]:
        """Get all positions."""
        try:
            if not self.client:
                return []
            resp = self.client.position()
            if not resp or resp.get("status") is not True:
                return []
            raw_positions = resp.get("data") or []
            return [self._convert_position(p) for p in raw_positions]
        except Exception as e:
            self._log_error("get_positions", e)
            return []

    def _convert_position(self, raw: Dict) -> UnifiedPosition:
        """Convert SmartAPI position dict to UnifiedPosition."""
        qty = int(raw.get("netqty") or "0")
        buy_qty = int(raw.get("buyqty") or "0")
        sell_qty = int(raw.get("sellqty") or "0")
        avg = Decimal(str(raw.get("netprice") or "0"))
        ltp = Decimal(str(raw.get("ltp") or "0"))
        pnl = Decimal(str(raw.get("pnl") or "0"))
        product_str = raw.get("producttype") or "CARRYFORWARD"

        tradingsymbol = raw.get("tradingsymbol", "")
        underlying = ""
        for idx in ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"):
            if tradingsymbol.startswith(idx):
                underlying = idx
                break
        option_type = ""
        if tradingsymbol.endswith("CE"):
            option_type = "CE"
        elif tradingsymbol.endswith("PE"):
            option_type = "PE"

        return UnifiedPosition(
            exchange=raw.get("exchange", "NFO"),
            tradingsymbol=tradingsymbol,
            underlying=underlying,
            option_type=option_type,
            quantity=qty,
            buy_quantity=buy_qty,
            sell_quantity=sell_qty,
            average_price=avg,
            buy_average=Decimal(str(raw.get("buyprice") or "0")),
            sell_average=Decimal(str(raw.get("sellprice") or "0")),
            last_price=ltp,
            pnl=pnl,
            realised_pnl=Decimal(str(raw.get("realisedpnl") or "0")),
            unrealised_pnl=Decimal(str(raw.get("unrealisedpnl") or pnl)),
            product=_PRODUCT_FROM_ANGEL.get(product_str, ProductType.NRML),
            raw_response=raw,
        )

    # =========================================================================
    # Market Data (light — for LTP/quote alongside order flow)
    # =========================================================================

    async def get_ltp(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Get LTP for instruments via SmartAPI."""
        try:
            if not self.client:
                return {}
            result = {}
            for instrument in instruments:
                parts = instrument.split(":")
                exchange = parts[0] if len(parts) == 2 else "NFO"
                symbol = parts[1] if len(parts) == 2 else parts[0]
                try:
                    resp = self.client.ltpData(exchange, symbol, "")
                    if resp and resp.get("status") is True:
                        data = resp.get("data", {})
                        result[instrument] = UnifiedQuote(
                            tradingsymbol=symbol,
                            exchange=exchange,
                            last_price=Decimal(str(data.get("ltp") or "0")),
                            raw_response=data,
                        )
                except Exception:
                    pass
            return result
        except Exception as e:
            self._log_error("get_ltp", e)
            return {}

    async def get_quote(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Get full quote — SmartAPI LTP data only for order adapters."""
        return await self.get_ltp(instruments)

    # =========================================================================
    # Account Information
    # =========================================================================

    async def get_margins(self) -> Dict[str, Any]:
        """Get account margins (RMS limits)."""
        try:
            if not self.client:
                return {}
            resp = self.client.rmsLimit()
            if resp and resp.get("status") is True:
                return resp.get("data", {})
            return {}
        except Exception as e:
            self._log_error("get_margins", e)
            return {}

    async def get_profile(self) -> Dict[str, Any]:
        """Get user profile."""
        try:
            if not self.client:
                return {}
            resp = self.client.getProfile(refreshToken="")
            if resp and resp.get("status") is True:
                return resp.get("data", {})
            return {}
        except Exception as e:
            self._log_error("get_profile", e)
            return {}

    # =========================================================================
    # Instruments
    # =========================================================================

    async def get_instruments(self, exchange: str = "NFO") -> List[Dict[str, Any]]:
        """Get instruments — SmartAPI provides instrument master via separate download."""
        try:
            if not self.client:
                return []
            # SmartAPI instrument master is a CSV download; return empty for now
            # Full instrument sync handled by TokenManager / instrument master job
            return []
        except Exception as e:
            self._log_error("get_instruments", e)
            return []
