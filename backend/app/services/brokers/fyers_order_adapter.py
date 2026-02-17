"""
Fyers Order Execution Adapter

Implements BrokerAdapter interface for Fyers API v3 using httpx.
Auth: OAuth access token; format: "client_id:access_token" in Authorization header.

Key Fyers API characteristics:
- Base URL: https://api-t1.fyers.in/api/v3
- Auth header: Authorization: <client_id>:<access_token>
- Symbol format: NSE:NIFTY24DEC26000CE (EXCHANGE:TRADINGSYMBOL)
- Response status: "ok" (success) or "error"
- Response code: 200 (success) or negative (error)
- Order types: 1=Limit, 2=Market, 3=StopOrder(SL-M), 4=StopLimit(SL)
- Sides: 1=BUY, -1=SELL
- Products: MARGIN (NRML for F&O), INTRADAY (MIS), CNC
- Order status codes: 1=cancelled, 2=traded(complete), 3=for_future_use, 4=transit,
                      5=rejected, 6=pending, 20=after_market_pending
- Cancel: DELETE /orders (sends JSON body with id and type)

Reference: https://myapi.fyers.in/docs/
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Any

import httpx

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

FYERS_API_BASE = "https://api-t1.fyers.in/api/v3"

# Fyers uses integer codes for order type and side
_ORDER_TYPE_MAP = {
    OrderType.LIMIT: 1,
    OrderType.MARKET: 2,
    OrderType.STOP_LOSS_MARKET: 3,
    OrderType.STOP_LOSS: 4,
}

_SIDE_MAP = {
    OrderSide.BUY: 1,
    OrderSide.SELL: -1,
}

_PRODUCT_MAP = {
    ProductType.NRML: "MARGIN",
    ProductType.MIS: "INTRADAY",
}

# Reverse mappings
_ORDER_TYPE_FROM_FYERS = {v: k for k, v in _ORDER_TYPE_MAP.items()}
_SIDE_FROM_FYERS = {1: OrderSide.BUY, -1: OrderSide.SELL}
_PRODUCT_FROM_FYERS = {v: k for k, v in _PRODUCT_MAP.items()}
_PRODUCT_FROM_FYERS["CNC"] = ProductType.NRML

# Status code to OrderStatus
_STATUS_FROM_FYERS = {
    1: OrderStatus.CANCELLED,
    2: OrderStatus.COMPLETE,
    4: OrderStatus.PENDING,    # transit
    5: OrderStatus.REJECTED,
    6: OrderStatus.PENDING,
    20: OrderStatus.PENDING,   # after_market_pending
}


class FyersOrderAdapter(BrokerAdapter):
    """
    Broker adapter for Fyers API v3 order execution.

    Auth header format: "{client_id}:{access_token}"
    Symbol format: "EXCHANGE:TRADINGSYMBOL" (e.g. "NSE:NIFTY24DEC26000CE")
    """

    def __init__(self, access_token: str, client_id: str = None):
        """
        Initialize Fyers order adapter.

        Args:
            access_token: Fyers OAuth access token
            client_id: Fyers client ID (app ID prefix, e.g. "XYZ12345-100")
        """
        super().__init__(access_token)
        self.client_id = client_id or ""
        # Fyers auth: "client_id:access_token"
        auth_value = f"{self.client_id}:{access_token}" if self.client_id else access_token
        self._headers = {
            "Authorization": auth_value,
            "Content-Type": "application/json",
        }

    @property
    def broker_type(self) -> BrokerType:
        return BrokerType.FYERS

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
        """No SDK initialization needed for Fyers (pure REST)."""
        self._initialized = True
        self._log_info("initialize", "Fyers order adapter ready")
        return True

    async def validate_session(self) -> bool:
        """Validate token by fetching user profile."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{FYERS_API_BASE}/profile",
                    headers=self._headers,
                )
            data = resp.json()
            return resp.status_code == 200 and data.get("s") == "ok"
        except Exception as e:
            self._log_error("validate_session", e)
            return False

    # =========================================================================
    # Order Management
    # =========================================================================

    async def place_order(self, order: UnifiedOrder) -> UnifiedOrder:
        """Place order via Fyers v3 API."""
        try:
            # Fyers symbol format: "EXCHANGE:TRADINGSYMBOL"
            exchange_map = {"NFO": "NSE", "NSE": "NSE", "BSE": "BSE", "BFO": "BSE"}
            fyers_exchange = exchange_map.get(order.exchange, order.exchange)
            fyers_symbol = f"{fyers_exchange}:{order.tradingsymbol}"

            payload = {
                "symbol": fyers_symbol,
                "qty": order.quantity,
                "type": _ORDER_TYPE_MAP[order.order_type],
                "side": _SIDE_MAP[order.side],
                "productType": _PRODUCT_MAP[order.product],
                "limitPrice": float(order.price) if order.price else 0,
                "stopPrice": float(order.trigger_price) if order.trigger_price else 0,
                "validity": order.validity or "DAY",
                "disclosedQty": order.disclosed_quantity,
                "offlineOrder": False,
                "takeProfit": 0,
                "stopLoss": 0,
            }

            if order.tag:
                payload["orderTag"] = order.tag[:20]

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{FYERS_API_BASE}/orders/sync",
                    headers=self._headers,
                    json=payload,
                )

            data = resp.json()

            if resp.status_code == 200 and data.get("s") == "ok":
                order.order_id = str(data.get("id", ""))
                order.status = OrderStatus.PENDING
                order.placed_at = datetime.utcnow()
                self._log_info("place_order", f"Order placed: {order.order_id}")
            else:
                msg = data.get("message") or data.get("errmsg") or "Unknown error"
                order.status = OrderStatus.REJECTED
                order.rejection_reason = msg
                self._log_info("place_order", f"Order rejected: {msg}")

            order.raw_response = data
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
        """Modify existing order via Fyers PATCH /orders."""
        try:
            payload: Dict[str, Any] = {"id": order_id}
            if quantity is not None:
                payload["qty"] = quantity
            if price is not None:
                payload["limitPrice"] = float(price)
            if trigger_price is not None:
                payload["stopPrice"] = float(trigger_price)
            if order_type is not None:
                payload["type"] = _ORDER_TYPE_MAP[order_type]

            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.patch(
                    f"{FYERS_API_BASE}/orders/sync",
                    headers=self._headers,
                    json=payload,
                )

            return await self.get_order(order_id) or UnifiedOrder(order_id=order_id)

        except Exception as e:
            self._log_error("modify_order", e)
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order via Fyers DELETE /orders."""
        try:
            payload = {"id": order_id, "type": 1}  # type=1 is regular order cancel
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.delete(
                    f"{FYERS_API_BASE}/orders/sync",
                    headers=self._headers,
                    json=payload,
                )
            data = resp.json()
            return resp.status_code == 200 and data.get("s") == "ok"
        except Exception as e:
            self._log_error("cancel_order", e)
            return False

    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """Get specific order by ID."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{FYERS_API_BASE}/orders",
                    headers=self._headers,
                    params={"id": order_id},
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("s") == "ok":
                orders = data.get("orderBook") or []
                if orders:
                    return self._convert_order(orders[0])
            return None
        except Exception as e:
            self._log_error("get_order", e)
            return None

    async def get_orders(self) -> List[UnifiedOrder]:
        """Get all orders for today."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{FYERS_API_BASE}/orders",
                    headers=self._headers,
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("s") == "ok":
                return [self._convert_order(o) for o in (data.get("orderBook") or [])]
            return []
        except Exception as e:
            self._log_error("get_orders", e)
            return []

    def _convert_order(self, raw: Dict) -> UnifiedOrder:
        """Convert Fyers order dict to UnifiedOrder."""
        status_code = raw.get("status", 6)
        status = _STATUS_FROM_FYERS.get(status_code, OrderStatus.PENDING)

        # Fyers symbol: "NSE:NIFTY24DEC26000CE" -> extract tradingsymbol
        fyers_symbol = raw.get("symbol", "")
        tradingsymbol = fyers_symbol.split(":")[-1] if ":" in fyers_symbol else fyers_symbol
        exchange_prefix = fyers_symbol.split(":")[0] if ":" in fyers_symbol else "NSE"
        exchange = "NFO" if exchange_prefix == "NSE" and (
            tradingsymbol.endswith("CE") or tradingsymbol.endswith("PE")
        ) else exchange_prefix

        price = raw.get("limitPrice") or 0
        trig = raw.get("stopPrice") or 0
        avg = raw.get("tradedPrice") or 0
        qty = raw.get("qty") or 0
        filled = raw.get("filledQty") or 0

        return UnifiedOrder(
            order_id=str(raw.get("id", "")),
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            side=_SIDE_FROM_FYERS.get(raw.get("side", 1), OrderSide.BUY),
            order_type=_ORDER_TYPE_FROM_FYERS.get(raw.get("type", 2), OrderType.MARKET),
            product=_PRODUCT_FROM_FYERS.get(raw.get("productType", "MARGIN"), ProductType.NRML),
            quantity=qty,
            price=Decimal(str(price)) if price else None,
            trigger_price=Decimal(str(trig)) if trig else None,
            status=status,
            filled_quantity=filled,
            average_price=Decimal(str(avg)) if avg else None,
            pending_quantity=qty - filled,
            validity=raw.get("validity", "DAY"),
            status_message=raw.get("message", ""),
            rejection_reason=raw.get("message", "") if status == OrderStatus.REJECTED else "",
            raw_response=raw,
        )

    # =========================================================================
    # Position Management
    # =========================================================================

    async def get_positions(self) -> List[UnifiedPosition]:
        """Get positions from Fyers /positions endpoint."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{FYERS_API_BASE}/positions",
                    headers=self._headers,
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("s") == "ok":
                return [self._convert_position(p) for p in (data.get("netPositions") or [])]
            return []
        except Exception as e:
            self._log_error("get_positions", e)
            return []

    def _convert_position(self, raw: Dict) -> UnifiedPosition:
        """Convert Fyers net position dict to UnifiedPosition."""
        # Symbol format: "NSE:NIFTY24DEC26000CE"
        fyers_symbol = raw.get("symbol", "")
        tradingsymbol = fyers_symbol.split(":")[-1] if ":" in fyers_symbol else fyers_symbol
        exchange_prefix = fyers_symbol.split(":")[0] if ":" in fyers_symbol else "NSE"
        exchange = "NFO" if exchange_prefix == "NSE" and (
            tradingsymbol.endswith("CE") or tradingsymbol.endswith("PE")
        ) else exchange_prefix

        underlying = ""
        for idx in ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"):
            if tradingsymbol.upper().startswith(idx):
                underlying = idx
                break
        option_type = ""
        if tradingsymbol.upper().endswith("CE"):
            option_type = "CE"
        elif tradingsymbol.upper().endswith("PE"):
            option_type = "PE"

        qty = raw.get("netQty", 0)
        buy_qty = raw.get("buyQty", 0)
        sell_qty = raw.get("sellQty", 0)
        pnl = Decimal(str(raw.get("pl") or "0"))

        return UnifiedPosition(
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            underlying=underlying,
            option_type=option_type,
            quantity=qty,
            buy_quantity=buy_qty,
            sell_quantity=sell_qty,
            average_price=Decimal(str(raw.get("netAvg") or "0")),
            buy_average=Decimal(str(raw.get("buyAvg") or "0")),
            sell_average=Decimal(str(raw.get("sellAvg") or "0")),
            last_price=Decimal(str(raw.get("ltp") or "0")),
            pnl=pnl,
            product=_PRODUCT_FROM_FYERS.get(raw.get("productType", "MARGIN"), ProductType.NRML),
            raw_response=raw,
        )

    # =========================================================================
    # Market Data
    # =========================================================================

    async def get_ltp(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Get LTP via Fyers /data/quotes."""
        try:
            # Fyers symbol format: "NSE:NIFTY24DEC26000CE"
            symbols = ",".join(instruments)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{FYERS_API_BASE}/data/quotes",
                    headers=self._headers,
                    params={"symbols": symbols},
                )
            data = resp.json()
            result = {}
            if resp.status_code == 200 and data.get("s") == "ok":
                for q in data.get("d") or []:
                    v = q.get("v") or {}
                    symbol = q.get("n", "")
                    result[symbol] = UnifiedQuote(
                        tradingsymbol=symbol.split(":")[-1] if ":" in symbol else symbol,
                        exchange=symbol.split(":")[0] if ":" in symbol else "",
                        last_price=Decimal(str(v.get("lp") or "0")),
                        raw_response=v,
                    )
            return result
        except Exception as e:
            self._log_error("get_ltp", e)
            return {}

    async def get_quote(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Delegate to get_ltp for Fyers order adapter."""
        return await self.get_ltp(instruments)

    # =========================================================================
    # Account Information
    # =========================================================================

    async def get_margins(self) -> Dict[str, Any]:
        """Get funds from Fyers /funds endpoint."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{FYERS_API_BASE}/funds",
                    headers=self._headers,
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("s") == "ok":
                return {"fund_limit": data.get("fund_limit", [])}
            return {}
        except Exception as e:
            self._log_error("get_margins", e)
            return {}

    async def get_profile(self) -> Dict[str, Any]:
        """Get user profile from Fyers /profile."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{FYERS_API_BASE}/profile",
                    headers=self._headers,
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("s") == "ok":
                return data.get("data", {})
            return {}
        except Exception as e:
            self._log_error("get_profile", e)
            return {}

    # =========================================================================
    # Instruments
    # =========================================================================

    async def get_instruments(self, exchange: str = "NFO") -> List[Dict[str, Any]]:
        """Instrument master handled by Fyers market data adapter."""
        return []
