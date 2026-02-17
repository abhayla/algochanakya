"""
Dhan Order Execution Adapter

Implements BrokerAdapter interface for Dhan Trading API using httpx.
Auth: Static access token (no expiry; re-generated manually from Dhan console).

Key Dhan API characteristics:
- Base URL: https://api.dhan.co/v2
- Auth headers: access-token (hyphenated lowercase), client-id
- Order types: LIMIT, MARKET, STOP_LOSS, STOP_LOSS_MARKET
- Products: CNC, INTRADAY, MARGIN, MTF, CO, BO
- Exchanges: NSE_EQ, NSE_FNO, BSE_EQ, BSE_FNO, MCX_COMM, IDX_I
- Status: PENDING, OPEN, TRADED, TRANSIT, REJECTED, CANCELLED, PART_TRADED, EXPIRED
- security_id is numeric string (not tradingsymbol)
- Cancel: DELETE /v2/orders/{order_id}

Reference: https://dhanhq.co/docs/latest/
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

DHAN_API_BASE = "https://api.dhan.co/v2"

_ORDER_TYPE_MAP = {
    OrderType.MARKET: "MARKET",
    OrderType.LIMIT: "LIMIT",
    OrderType.STOP_LOSS: "STOP_LOSS",
    OrderType.STOP_LOSS_MARKET: "STOP_LOSS_MARKET",
}

# Dhan product types: CNC/MARGIN for carry-forward, INTRADAY for MIS
_PRODUCT_MAP = {
    ProductType.NRML: "MARGIN",    # MARGIN for F&O NRML
    ProductType.MIS: "INTRADAY",
}

_SIDE_MAP = {
    OrderSide.BUY: "BUY",
    OrderSide.SELL: "SELL",
}

# Exchange to Dhan segment
_EXCHANGE_MAP = {
    "NFO": "NSE_FNO",
    "NSE": "NSE_EQ",
    "BSE": "BSE_EQ",
    "BFO": "BSE_FNO",
    "MCX": "MCX_COMM",
    "IDX": "IDX_I",
}

_EXCHANGE_FROM_DHAN = {v: k for k, v in _EXCHANGE_MAP.items()}

_ORDER_TYPE_FROM_DHAN = {v: k for k, v in _ORDER_TYPE_MAP.items()}
_PRODUCT_FROM_DHAN = {
    "CNC": ProductType.NRML,
    "MARGIN": ProductType.NRML,
    "INTRADAY": ProductType.MIS,
    "MTF": ProductType.NRML,
    "CO": ProductType.MIS,
    "BO": ProductType.MIS,
}
_SIDE_FROM_DHAN = {v: k for k, v in _SIDE_MAP.items()}

_STATUS_FROM_DHAN = {
    "PENDING": OrderStatus.PENDING,
    "OPEN": OrderStatus.OPEN,
    "TRADED": OrderStatus.COMPLETE,
    "PART_TRADED": OrderStatus.OPEN,
    "TRANSIT": OrderStatus.PENDING,
    "REJECTED": OrderStatus.REJECTED,
    "CANCELLED": OrderStatus.CANCELLED,
    "EXPIRED": OrderStatus.CANCELLED,
}


class DhanOrderAdapter(BrokerAdapter):
    """
    Broker adapter for Dhan Trading API order execution.

    Uses static access token (no OAuth refresh flow).
    All prices in rupees (Dhan does not use paise).
    """

    def __init__(self, access_token: str, client_id: str = None):
        """
        Initialize Dhan order adapter.

        Args:
            access_token: Dhan API access token (static, from Dhan console)
            client_id: Dhan client ID (required for most API calls)
        """
        super().__init__(access_token)
        self.client_id = client_id or ""
        self._headers = {
            "access-token": access_token,
            "client-id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @property
    def broker_type(self) -> BrokerType:
        return BrokerType.DHAN

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_basket_orders=False,
            supports_amo=True,
            supports_gtt=False,
            supports_trailing_sl=False,
            max_orders_per_second=10,
            max_instruments_per_quote=100,
            supports_websocket=True,
            supports_historical_data=True,
        )

    async def initialize(self) -> bool:
        """No SDK initialization needed for Dhan (pure REST with static token)."""
        self._initialized = True
        self._log_info("initialize", "Dhan order adapter ready")
        return True

    async def validate_session(self) -> bool:
        """Validate token by fetching order list (lightweight check)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{DHAN_API_BASE}/orders",
                    headers=self._headers,
                )
            # Dhan returns 200 with list on success, 401 on invalid token
            return resp.status_code == 200
        except Exception as e:
            self._log_error("validate_session", e)
            return False

    # =========================================================================
    # Order Management
    # =========================================================================

    async def place_order(self, order: UnifiedOrder) -> UnifiedOrder:
        """Place order via Dhan v2 API."""
        try:
            dhan_exchange = _EXCHANGE_MAP.get(order.exchange, "NSE_FNO")

            payload = {
                "dhanClientId": self.client_id,
                "transactionType": _SIDE_MAP[order.side],
                "exchangeSegment": dhan_exchange,
                "productType": _PRODUCT_MAP[order.product],
                "orderType": _ORDER_TYPE_MAP[order.order_type],
                "validity": order.validity or "DAY",
                "tradingSymbol": order.tradingsymbol,
                "securityId": str(order.instrument_token or ""),
                "quantity": order.quantity,
                "disclosedQuantity": order.disclosed_quantity,
                "price": float(order.price) if order.price else 0,
                "triggerPrice": float(order.trigger_price) if order.trigger_price else 0,
                "afterMarketOrder": False,
                "boProfitValue": 0,
                "boStopLossValue": 0,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{DHAN_API_BASE}/orders",
                    headers=self._headers,
                    json=payload,
                )

            data = resp.json()

            if resp.status_code == 200:
                order.order_id = str(data.get("orderId", ""))
                order.status = _STATUS_FROM_DHAN.get(
                    str(data.get("orderStatus", "PENDING")).upper(),
                    OrderStatus.PENDING,
                )
                order.placed_at = datetime.utcnow()
                self._log_info("place_order", f"Order placed: {order.order_id}")
            else:
                error_msg = data.get("errorMessage") or data.get("message", "Unknown error")
                order.status = OrderStatus.REJECTED
                order.rejection_reason = f"[{data.get('errorCode', '')}] {error_msg}"
                self._log_info("place_order", f"Order rejected: {order.rejection_reason}")

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
        """Modify existing order via Dhan PUT /orders/{order_id}."""
        try:
            payload: Dict[str, Any] = {"dhanClientId": self.client_id}
            if quantity is not None:
                payload["quantity"] = quantity
            if price is not None:
                payload["price"] = float(price)
            if trigger_price is not None:
                payload["triggerPrice"] = float(trigger_price)
            if order_type is not None:
                payload["orderType"] = _ORDER_TYPE_MAP[order_type]

            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.put(
                    f"{DHAN_API_BASE}/orders/{order_id}",
                    headers=self._headers,
                    json=payload,
                )

            return await self.get_order(order_id) or UnifiedOrder(order_id=order_id)

        except Exception as e:
            self._log_error("modify_order", e)
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order via Dhan DELETE /orders/{order_id}."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.delete(
                    f"{DHAN_API_BASE}/orders/{order_id}",
                    headers=self._headers,
                )
            if resp.status_code == 200:
                data = resp.json()
                status = str(data.get("orderStatus", "")).upper()
                return status in ("CANCELLED", "PENDING_CANCEL")
            return False
        except Exception as e:
            self._log_error("cancel_order", e)
            return False

    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """Get specific order by ID."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{DHAN_API_BASE}/orders/{order_id}",
                    headers=self._headers,
                )
            if resp.status_code == 200:
                return self._convert_order(resp.json())
            return None
        except Exception as e:
            self._log_error("get_order", e)
            return None

    async def get_orders(self) -> List[UnifiedOrder]:
        """Get all orders for today."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{DHAN_API_BASE}/orders",
                    headers=self._headers,
                )
            if resp.status_code == 200:
                raw_orders = resp.json()
                if isinstance(raw_orders, list):
                    return [self._convert_order(o) for o in raw_orders]
            return []
        except Exception as e:
            self._log_error("get_orders", e)
            return []

    def _convert_order(self, raw: Dict) -> UnifiedOrder:
        """Convert Dhan order dict to UnifiedOrder."""
        status_str = str(raw.get("orderStatus") or "PENDING").upper()
        status = _STATUS_FROM_DHAN.get(status_str, OrderStatus.PENDING)

        price = raw.get("price") or 0
        trig = raw.get("triggerPrice") or 0
        avg = raw.get("tradedPrice") or 0
        qty = raw.get("quantity") or 0
        filled = raw.get("filledQty") or 0

        return UnifiedOrder(
            order_id=str(raw.get("orderId", "")),
            exchange=_EXCHANGE_FROM_DHAN.get(raw.get("exchangeSegment", ""), raw.get("exchangeSegment", "")),
            tradingsymbol=raw.get("tradingSymbol", ""),
            side=_SIDE_FROM_DHAN.get(raw.get("transactionType", "BUY"), OrderSide.BUY),
            order_type=_ORDER_TYPE_FROM_DHAN.get(raw.get("orderType", "MARKET"), OrderType.MARKET),
            product=_PRODUCT_FROM_DHAN.get(raw.get("productType", "MARGIN"), ProductType.NRML),
            quantity=qty,
            price=Decimal(str(price)) if price else None,
            trigger_price=Decimal(str(trig)) if trig else None,
            status=status,
            filled_quantity=filled,
            average_price=Decimal(str(avg)) if avg else None,
            pending_quantity=qty - filled,
            validity=raw.get("validity", "DAY"),
            status_message=raw.get("omsErrorDescription") or raw.get("errorMessage", ""),
            rejection_reason=(
                raw.get("omsErrorDescription") or raw.get("errorMessage", "")
                if status == OrderStatus.REJECTED else ""
            ),
            raw_response=raw,
        )

    # =========================================================================
    # Position Management
    # =========================================================================

    async def get_positions(self) -> List[UnifiedPosition]:
        """Get positions from Dhan /positions endpoint."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{DHAN_API_BASE}/positions",
                    headers=self._headers,
                )
            if resp.status_code == 200:
                raw = resp.json()
                positions = raw if isinstance(raw, list) else []
                return [self._convert_position(p) for p in positions]
            return []
        except Exception as e:
            self._log_error("get_positions", e)
            return []

    def _convert_position(self, raw: Dict) -> UnifiedPosition:
        """Convert Dhan position dict to UnifiedPosition."""
        tradingsymbol = raw.get("tradingSymbol", "")
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

        qty = raw.get("netQty") or 0
        buy_qty = raw.get("buyQty") or 0
        sell_qty = raw.get("sellQty") or 0
        ltp = Decimal(str(raw.get("lastTradedPrice") or "0"))
        unrealised = Decimal(str(raw.get("unrealizedProfit") or "0"))
        realised = Decimal(str(raw.get("realizedProfit") or "0"))

        return UnifiedPosition(
            exchange=_EXCHANGE_FROM_DHAN.get(raw.get("exchangeSegment", ""), raw.get("exchangeSegment", "NFO")),
            tradingsymbol=tradingsymbol,
            underlying=underlying,
            option_type=option_type,
            quantity=qty,
            buy_quantity=buy_qty,
            sell_quantity=sell_qty,
            average_price=Decimal(str(raw.get("costPrice") or "0")),
            buy_average=Decimal(str(raw.get("buyAvg") or "0")),
            sell_average=Decimal(str(raw.get("sellAvg") or "0")),
            last_price=ltp,
            pnl=unrealised + realised,
            realised_pnl=realised,
            unrealised_pnl=unrealised,
            product=_PRODUCT_FROM_DHAN.get(raw.get("productType", "MARGIN"), ProductType.NRML),
            raw_response=raw,
        )

    # =========================================================================
    # Market Data
    # =========================================================================

    async def get_ltp(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Get LTP via Dhan /marketfeed/ltp (POST)."""
        try:
            # Dhan LTP requires security_id, not tradingsymbol
            # For order adapters, provide a basic implementation
            return {}
        except Exception as e:
            self._log_error("get_ltp", e)
            return {}

    async def get_quote(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Get full quote — delegate to LTP for Dhan order adapter."""
        return await self.get_ltp(instruments)

    # =========================================================================
    # Account Information
    # =========================================================================

    async def get_margins(self) -> Dict[str, Any]:
        """Get fund limits from Dhan."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{DHAN_API_BASE}/fundlimit",
                    headers=self._headers,
                )
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception as e:
            self._log_error("get_margins", e)
            return {}

    async def get_profile(self) -> Dict[str, Any]:
        """Get user profile — Dhan returns it from orders endpoint."""
        try:
            return {"client_id": self.client_id}
        except Exception as e:
            self._log_error("get_profile", e)
            return {}

    # =========================================================================
    # Instruments
    # =========================================================================

    async def get_instruments(self, exchange: str = "NFO") -> List[Dict[str, Any]]:
        """Instrument master handled by Dhan market data adapter CSV download."""
        return []
