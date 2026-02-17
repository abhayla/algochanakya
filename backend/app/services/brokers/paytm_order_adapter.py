"""
Paytm Money Order Execution Adapter

Implements BrokerAdapter interface for Paytm Money API using httpx.
Auth: Paytm Money uses a unique 3-token system:
  - access_token: Primary auth token (Authorization header)
  - read_token:   Read-only operations token (x-read-token header)
  - edge_token:   Edge/trading operations token (x-edge-token header)

Key Paytm Money API characteristics:
- Base URL: https://developer.paytmmoney.com
- Order endpoints: /orders/v1/place, /orders/v1/modify, /orders/v1/cancel
- Auth: Authorization: Bearer <access_token>
- Order types: RL=LIMIT, MKT=MARKET, SL=STOP_LOSS, SLM=STOP_LOSS_MARKET
- Sides: B=BUY, S=SELL
- Products: D=NRML (delivery/carry-forward for F&O), I=INTRADAY
- Order status: open, complete, cancelled, rejected, trigger pending
- Cancel order: POST /orders/v1/cancel (not DELETE)

Reference: https://developer.paytmmoney.com/docs/api/
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

PAYTM_API_BASE = "https://developer.paytmmoney.com"

_ORDER_TYPE_MAP = {
    OrderType.LIMIT: "RL",
    OrderType.MARKET: "MKT",
    OrderType.STOP_LOSS: "SL",
    OrderType.STOP_LOSS_MARKET: "SLM",
}

_SIDE_MAP = {
    OrderSide.BUY: "B",
    OrderSide.SELL: "S",
}

_PRODUCT_MAP = {
    ProductType.NRML: "D",   # Delivery / carry-forward for F&O
    ProductType.MIS: "I",    # Intraday
}

# Reverse
_ORDER_TYPE_FROM_PAYTM = {
    "RL": OrderType.LIMIT,
    "MKT": OrderType.MARKET,
    "SL": OrderType.STOP_LOSS,
    "SLM": OrderType.STOP_LOSS_MARKET,
    "L": OrderType.LIMIT,    # alternate form
    "M": OrderType.MARKET,
}
_SIDE_FROM_PAYTM = {"B": OrderSide.BUY, "S": OrderSide.SELL}
_PRODUCT_FROM_PAYTM = {"D": ProductType.NRML, "I": ProductType.MIS, "CNC": ProductType.NRML}

_STATUS_FROM_PAYTM = {
    "open": OrderStatus.OPEN,
    "complete": OrderStatus.COMPLETE,
    "cancelled": OrderStatus.CANCELLED,
    "rejected": OrderStatus.REJECTED,
    "trigger pending": OrderStatus.TRIGGER_PENDING,
    "pending": OrderStatus.PENDING,
    "amo pending": OrderStatus.PENDING,
    "open pending": OrderStatus.PENDING,
    "validation pending": OrderStatus.PENDING,
}


class PaytmOrderAdapter(BrokerAdapter):
    """
    Broker adapter for Paytm Money order execution.

    Uses the unique 3-token auth system required by Paytm Money API.
    """

    def __init__(
        self,
        access_token: str,
        read_token: str = None,
        edge_token: str = None,
    ):
        """
        Initialize Paytm Money order adapter.

        Args:
            access_token: Primary Paytm Money access token (Bearer)
            read_token: Read-only operations token (x-read-token header)
            edge_token: Edge/trading token (x-edge-token header)
        """
        super().__init__(access_token)
        self.read_token = read_token or ""
        self.edge_token = edge_token or ""
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "x-read-token": self.read_token,
            "x-edge-token": self.edge_token,
            "Content-Type": "application/json",
        }

    @property
    def broker_type(self) -> BrokerType:
        return BrokerType.PAYTM

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_basket_orders=False,
            supports_amo=True,
            supports_gtt=False,
            supports_trailing_sl=False,
            max_orders_per_second=5,
            max_instruments_per_quote=50,
            supports_websocket=True,
            supports_historical_data=True,
        )

    async def initialize(self) -> bool:
        """No SDK initialization needed for Paytm Money (pure REST)."""
        self._initialized = True
        self._log_info("initialize", "Paytm Money order adapter ready")
        return True

    async def validate_session(self) -> bool:
        """Validate session by fetching user profile."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{PAYTM_API_BASE}/accounts/v1/user/details",
                    headers=self._headers,
                )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("status") == 200 or "data" in data
            return False
        except Exception as e:
            self._log_error("validate_session", e)
            return False

    # =========================================================================
    # Order Management
    # =========================================================================

    async def place_order(self, order: UnifiedOrder) -> UnifiedOrder:
        """Place order via Paytm Money API."""
        try:
            payload = {
                "txn_type": _SIDE_MAP[order.side],
                "exchange": order.exchange,
                "segment": "D",  # Derivatives segment for F&O
                "product": _PRODUCT_MAP[order.product],
                "security_id": str(order.instrument_token or ""),
                "quantity": order.quantity,
                "validity": order.validity or "DAY",
                "order_type": _ORDER_TYPE_MAP[order.order_type],
                "price": float(order.price) if order.price else 0,
                "trigger_price": float(order.trigger_price) if order.trigger_price else 0,
                "off_mkt_flag": False,
            }

            if order.tag:
                payload["user_order_id"] = order.tag[:20]

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{PAYTM_API_BASE}/orders/v1/place",
                    headers=self._headers,
                    json=payload,
                )

            data = resp.json()

            if resp.status_code == 200 and data.get("status") == 200:
                order_data = data.get("data", {})
                order.order_id = str(order_data.get("orderId") or order_data.get("order_id", ""))
                order.status = OrderStatus.PENDING
                order.placed_at = datetime.utcnow()
                self._log_info("place_order", f"Order placed: {order.order_id}")
            else:
                msg = data.get("message") or data.get("errorMessage", "Unknown error")
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
        """Modify existing order via Paytm Money PUT /orders/v1/modify."""
        try:
            payload: Dict[str, Any] = {"order_id": order_id}
            if quantity is not None:
                payload["quantity"] = quantity
            if price is not None:
                payload["price"] = float(price)
            if trigger_price is not None:
                payload["trigger_price"] = float(trigger_price)
            if order_type is not None:
                payload["order_type"] = _ORDER_TYPE_MAP[order_type]

            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.put(
                    f"{PAYTM_API_BASE}/orders/v1/modify",
                    headers=self._headers,
                    json=payload,
                )

            return await self.get_order(order_id) or UnifiedOrder(order_id=order_id)

        except Exception as e:
            self._log_error("modify_order", e)
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order via Paytm Money PUT /orders/v1/cancel."""
        try:
            payload = {"order_id": order_id}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.put(
                    f"{PAYTM_API_BASE}/orders/v1/cancel",
                    headers=self._headers,
                    json=payload,
                )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("status") == 200
            return False
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
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{PAYTM_API_BASE}/orders/v1/details",
                    headers=self._headers,
                )
            if resp.status_code == 200:
                data = resp.json()
                order_list = (
                    data.get("data", {}).get("orders")
                    if isinstance(data.get("data"), dict)
                    else data.get("data", [])
                )
                return [self._convert_order(o) for o in (order_list or [])]
            return []
        except Exception as e:
            self._log_error("get_orders", e)
            return []

    def _convert_order(self, raw: Dict) -> UnifiedOrder:
        """Convert Paytm Money order dict to UnifiedOrder."""
        status_str = (raw.get("order_status") or "pending").lower()
        status = _STATUS_FROM_PAYTM.get(status_str, OrderStatus.PENDING)

        qty_str = raw.get("quantity") or "0"
        filled_str = raw.get("traded_quantity") or "0"
        avg_str = raw.get("traded_price") or "0"
        price_str = raw.get("price") or "0"
        trig_str = raw.get("trigger_price") or "0"
        pending_str = raw.get("pending_quantity") or "0"

        qty = int(qty_str) if str(qty_str).isdigit() else 0
        filled = int(filled_str) if str(filled_str).isdigit() else 0
        pending = int(pending_str) if str(pending_str).isdigit() else qty - filled

        return UnifiedOrder(
            order_id=str(raw.get("order_id") or raw.get("orderId", "")),
            exchange=raw.get("exchange", ""),
            tradingsymbol=raw.get("scrip_code") or raw.get("security_id", ""),
            side=_SIDE_FROM_PAYTM.get(raw.get("order_side") or raw.get("txn_type", "B"), OrderSide.BUY),
            order_type=_ORDER_TYPE_FROM_PAYTM.get(
                raw.get("order_type", "RL"), OrderType.LIMIT
            ),
            product=_PRODUCT_FROM_PAYTM.get(raw.get("product_type") or raw.get("product", "D"), ProductType.NRML),
            quantity=qty,
            price=Decimal(str(price_str)) if float(price_str) else None,
            trigger_price=Decimal(str(trig_str)) if float(trig_str) else None,
            status=status,
            filled_quantity=filled,
            average_price=Decimal(str(avg_str)) if float(avg_str) else None,
            pending_quantity=pending,
            validity=raw.get("validity", "DAY"),
            rejection_reason=raw.get("rejection_reason", "") if status == OrderStatus.REJECTED else "",
            raw_response=raw,
        )

    # =========================================================================
    # Position Management
    # =========================================================================

    async def get_positions(self) -> List[UnifiedPosition]:
        """Get positions from Paytm Money /orders/v1/positions."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{PAYTM_API_BASE}/orders/v1/position",
                    headers=self._headers,
                )
            if resp.status_code == 200:
                data = resp.json()
                positions = (
                    data.get("data", {}).get("positions")
                    if isinstance(data.get("data"), dict)
                    else data.get("data", [])
                )
                return [self._convert_position(p) for p in (positions or [])]
            return []
        except Exception as e:
            self._log_error("get_positions", e)
            return []

    def _convert_position(self, raw: Dict) -> UnifiedPosition:
        """Convert Paytm Money position dict to UnifiedPosition."""
        tradingsymbol = raw.get("scrip_code") or raw.get("security_id", "")

        qty_str = raw.get("quantity") or "0"
        qty = int(qty_str) if str(qty_str).lstrip("-").isdigit() else 0

        ltp = Decimal(str(raw.get("last_traded_price") or raw.get("ltp") or "0"))
        avg = Decimal(str(raw.get("average_price") or raw.get("avg_price") or "0"))
        unrealised = Decimal(str(raw.get("unrealized_pnl") or raw.get("m2m_pnl") or "0"))
        realised = Decimal(str(raw.get("realized_pnl") or raw.get("booked_pnl") or "0"))

        return UnifiedPosition(
            exchange=raw.get("exchange", ""),
            tradingsymbol=tradingsymbol,
            quantity=qty,
            average_price=avg,
            last_price=ltp,
            pnl=unrealised + realised,
            realised_pnl=realised,
            unrealised_pnl=unrealised,
            product=_PRODUCT_FROM_PAYTM.get(
                raw.get("product_type") or raw.get("product", "D"),
                ProductType.NRML,
            ),
            raw_response=raw,
        )

    # =========================================================================
    # Market Data
    # =========================================================================

    async def get_ltp(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Basic LTP — Paytm Money market data handled by dedicated market data adapter."""
        return {}

    async def get_quote(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Full quote — Paytm Money market data handled by dedicated market data adapter."""
        return {}

    # =========================================================================
    # Account Information
    # =========================================================================

    async def get_margins(self) -> Dict[str, Any]:
        """Get fund limits from Paytm Money."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{PAYTM_API_BASE}/accounts/v1/funds/summary",
                    headers=self._headers,
                )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {})
            return {}
        except Exception as e:
            self._log_error("get_margins", e)
            return {}

    async def get_profile(self) -> Dict[str, Any]:
        """Get user profile from Paytm Money."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{PAYTM_API_BASE}/accounts/v1/user/details",
                    headers=self._headers,
                )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {})
            return {}
        except Exception as e:
            self._log_error("get_profile", e)
            return {}

    # =========================================================================
    # Instruments
    # =========================================================================

    async def get_instruments(self, exchange: str = "NFO") -> List[Dict[str, Any]]:
        """Instrument master handled by Paytm Money market data adapter."""
        return []
