"""
Upstox Order Execution Adapter

Implements BrokerAdapter interface for Upstox v2 API using httpx.
Auth: OAuth 2.0 access token (~1 year validity).

Key Upstox API characteristics:
- Base URL: https://api.upstox.com/v2
- Auth header: Authorization: Bearer <access_token>
- Instrument key format: NSE_FO|<instrument_token>  (for F&O)
- Order types: MARKET, LIMIT, SL, SL-M
- Products: D (Delivery/NRML), I (Intraday/MIS)
- Status: open, complete, cancelled, rejected, trigger pending, after market order req received
- Cancel order: DELETE /order (with order_id as query param)
- Positions: GET /portfolio/short-term-positions
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

UPSTOX_API_BASE = "https://api.upstox.com/v2"

_ORDER_TYPE_MAP = {
    OrderType.MARKET: "MARKET",
    OrderType.LIMIT: "LIMIT",
    OrderType.STOP_LOSS: "SL",
    OrderType.STOP_LOSS_MARKET: "SL-M",
}

_PRODUCT_MAP = {
    ProductType.NRML: "D",   # Delivery (carry forward) for F&O
    ProductType.MIS: "I",    # Intraday
}

_SIDE_MAP = {
    OrderSide.BUY: "BUY",
    OrderSide.SELL: "SELL",
}

# Reverse
_ORDER_TYPE_FROM_UPSTOX = {v: k for k, v in _ORDER_TYPE_MAP.items()}
_PRODUCT_FROM_UPSTOX = {v: k for k, v in _PRODUCT_MAP.items()}
_SIDE_FROM_UPSTOX = {v: k for k, v in _SIDE_MAP.items()}

_STATUS_FROM_UPSTOX = {
    "open": OrderStatus.OPEN,
    "complete": OrderStatus.COMPLETE,
    "cancelled": OrderStatus.CANCELLED,
    "rejected": OrderStatus.REJECTED,
    "trigger pending": OrderStatus.TRIGGER_PENDING,
    "after market order req received": OrderStatus.PENDING,
    "modified": OrderStatus.OPEN,
    "open pending": OrderStatus.PENDING,
    "not modified": OrderStatus.OPEN,
    "not cancelled": OrderStatus.OPEN,
    "validation pending": OrderStatus.PENDING,
    "put order req received": OrderStatus.PENDING,
}


class UpstoxOrderAdapter(BrokerAdapter):
    """
    Broker adapter for Upstox v2 order execution.

    Uses httpx for async REST calls. No separate SDK required.
    OAuth token has ~1 year validity; no refresh needed in normal operation.
    """

    def __init__(self, access_token: str):
        super().__init__(access_token)
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @property
    def broker_type(self) -> BrokerType:
        return BrokerType.UPSTOX

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_basket_orders=False,
            supports_amo=True,
            supports_gtt=True,
            supports_trailing_sl=False,
            max_orders_per_second=10,
            max_instruments_per_quote=500,
            supports_websocket=True,
            supports_historical_data=True,
        )

    async def initialize(self) -> bool:
        """No SDK initialization needed for Upstox (pure REST)."""
        self._initialized = True
        self._log_info("initialize", "Upstox order adapter ready")
        return True

    async def validate_session(self) -> bool:
        """Validate token by fetching user profile."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{UPSTOX_API_BASE}/user/profile",
                    headers=self._headers,
                )
            data = resp.json()
            return resp.status_code == 200 and data.get("status") == "success"
        except Exception as e:
            self._log_error("validate_session", e)
            return False

    # =========================================================================
    # Order Management
    # =========================================================================

    async def place_order(self, order: UnifiedOrder) -> UnifiedOrder:
        """Place order via Upstox v2 API."""
        try:
            # Build instrument key from exchange + tradingsymbol
            # Upstox format: NSE_FO|<instrument_token> or NSE_EQ|<symbol>
            instrument_key = self._build_instrument_key(order)

            payload = {
                "quantity": order.quantity,
                "product": _PRODUCT_MAP[order.product],
                "validity": order.validity or "DAY",
                "price": float(order.price) if order.price else 0,
                "tag": (order.tag or "")[:20],
                "instrument_token": instrument_key,
                "order_type": _ORDER_TYPE_MAP[order.order_type],
                "transaction_type": _SIDE_MAP[order.side],
                "disclosed_quantity": order.disclosed_quantity,
                "trigger_price": float(order.trigger_price) if order.trigger_price else 0,
                "is_amo": False,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{UPSTOX_API_BASE}/order/place",
                    headers=self._headers,
                    json=payload,
                )

            data = resp.json()

            if resp.status_code == 200 and data.get("status") == "success":
                order.order_id = str(data.get("data", {}).get("order_id", ""))
                order.status = OrderStatus.PENDING
                order.placed_at = datetime.utcnow()
                self._log_info("place_order", f"Order placed: {order.order_id}")
            else:
                errors = data.get("errors") or [{"message": data.get("message", "Unknown error")}]
                order.status = OrderStatus.REJECTED
                order.rejection_reason = "; ".join(e.get("message", "") for e in errors)
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
        """Modify existing order."""
        try:
            payload = {"order_id": order_id}
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
                    f"{UPSTOX_API_BASE}/order/modify",
                    headers=self._headers,
                    json=payload,
                )

            return await self.get_order(order_id) or UnifiedOrder(order_id=order_id)

        except Exception as e:
            self._log_error("modify_order", e)
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order via Upstox DELETE /order."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.delete(
                    f"{UPSTOX_API_BASE}/order",
                    headers=self._headers,
                    params={"order_id": order_id},
                )
            data = resp.json()
            return resp.status_code == 200 and data.get("status") == "success"
        except Exception as e:
            self._log_error("cancel_order", e)
            return False

    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """Get specific order details."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{UPSTOX_API_BASE}/order/details",
                    headers=self._headers,
                    params={"order_id": order_id},
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("status") == "success":
                return self._convert_order(data.get("data", {}))
            return None
        except Exception as e:
            self._log_error("get_order", e)
            return None

    async def get_orders(self) -> List[UnifiedOrder]:
        """Get all orders for today."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{UPSTOX_API_BASE}/order/retrieve-all",
                    headers=self._headers,
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("status") == "success":
                return [self._convert_order(o) for o in (data.get("data") or [])]
            return []
        except Exception as e:
            self._log_error("get_orders", e)
            return []

    def _convert_order(self, raw: Dict) -> UnifiedOrder:
        """Convert Upstox order response to UnifiedOrder."""
        status_str = (raw.get("status") or "").lower()
        status = _STATUS_FROM_UPSTOX.get(status_str, OrderStatus.PENDING)

        price = raw.get("price") or 0
        trig = raw.get("trigger_price") or 0
        avg = raw.get("average_price") or 0

        return UnifiedOrder(
            order_id=str(raw.get("order_id", "")),
            exchange=raw.get("exchange", ""),
            tradingsymbol=raw.get("tradingsymbol", ""),
            side=_SIDE_FROM_UPSTOX.get(raw.get("transaction_type", "BUY"), OrderSide.BUY),
            order_type=_ORDER_TYPE_FROM_UPSTOX.get(raw.get("order_type", "MARKET"), OrderType.MARKET),
            product=_PRODUCT_FROM_UPSTOX.get(raw.get("product", "D"), ProductType.NRML),
            quantity=raw.get("quantity", 0),
            price=Decimal(str(price)) if price else None,
            trigger_price=Decimal(str(trig)) if trig else None,
            status=status,
            filled_quantity=raw.get("filled_quantity", 0),
            average_price=Decimal(str(avg)) if avg else None,
            pending_quantity=raw.get("pending_quantity", 0),
            tag=raw.get("tag", ""),
            validity=raw.get("validity", "DAY"),
            status_message=raw.get("status_message", ""),
            rejection_reason=raw.get("status_message", "") if status == OrderStatus.REJECTED else "",
            raw_response=raw,
        )

    # =========================================================================
    # Position Management
    # =========================================================================

    async def get_positions(self) -> List[UnifiedPosition]:
        """Get positions from Upstox short-term positions endpoint."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{UPSTOX_API_BASE}/portfolio/short-term-positions",
                    headers=self._headers,
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("status") == "success":
                return [self._convert_position(p) for p in (data.get("data") or [])]
            return []
        except Exception as e:
            self._log_error("get_positions", e)
            return []

    def _convert_position(self, raw: Dict) -> UnifiedPosition:
        """Convert Upstox position to UnifiedPosition."""
        tradingsymbol = raw.get("tradingsymbol", "")
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

        pnl = Decimal(str(raw.get("pnl") or "0"))

        return UnifiedPosition(
            exchange=raw.get("exchange", "NFO"),
            tradingsymbol=tradingsymbol,
            underlying=underlying,
            option_type=option_type,
            quantity=raw.get("quantity", 0),
            buy_quantity=raw.get("buy_quantity", 0),
            sell_quantity=raw.get("sell_quantity", 0),
            average_price=Decimal(str(raw.get("average_price") or "0")),
            buy_average=Decimal(str(raw.get("buy_price") or "0")),
            sell_average=Decimal(str(raw.get("sell_price") or "0")),
            last_price=Decimal(str(raw.get("last_price") or "0")),
            pnl=pnl,
            unrealised_pnl=pnl,
            product=_PRODUCT_FROM_UPSTOX.get(raw.get("product", "D"), ProductType.NRML),
            overnight_quantity=raw.get("overnight_quantity", 0),
            raw_response=raw,
        )

    # =========================================================================
    # Market Data
    # =========================================================================

    async def get_ltp(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Get LTP via Upstox market quote endpoint."""
        try:
            # Upstox uses instrument_key format NSE_FO|<token>
            # For simplicity we pass through the instrument strings as provided
            instrument_keys = ",".join(instruments)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{UPSTOX_API_BASE}/market-quote/ltp",
                    headers=self._headers,
                    params={"instrument_key": instrument_keys},
                )
            data = resp.json()
            result = {}
            if resp.status_code == 200 and data.get("status") == "success":
                for key, quote_data in (data.get("data") or {}).items():
                    result[key] = UnifiedQuote(
                        tradingsymbol=key,
                        last_price=Decimal(str(quote_data.get("last_price") or "0")),
                        raw_response=quote_data,
                    )
            return result
        except Exception as e:
            self._log_error("get_ltp", e)
            return {}

    async def get_quote(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """Get full quote via Upstox market-quote endpoint."""
        try:
            instrument_keys = ",".join(instruments)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{UPSTOX_API_BASE}/market-quote/quotes",
                    headers=self._headers,
                    params={"instrument_key": instrument_keys},
                )
            data = resp.json()
            result = {}
            if resp.status_code == 200 and data.get("status") == "success":
                for key, q in (data.get("data") or {}).items():
                    ohlc = q.get("ohlc") or {}
                    depth = q.get("depth") or {}
                    bids = depth.get("buy") or [{}]
                    asks = depth.get("sell") or [{}]
                    result[key] = UnifiedQuote(
                        tradingsymbol=key,
                        last_price=Decimal(str(q.get("last_price") or "0")),
                        open=Decimal(str(ohlc.get("open") or "0")),
                        high=Decimal(str(ohlc.get("high") or "0")),
                        low=Decimal(str(ohlc.get("low") or "0")),
                        close=Decimal(str(ohlc.get("close") or "0")),
                        volume=q.get("volume", 0),
                        oi=q.get("oi", 0),
                        bid_price=Decimal(str(bids[0].get("price") or "0")),
                        bid_quantity=bids[0].get("quantity", 0),
                        ask_price=Decimal(str(asks[0].get("price") or "0")),
                        ask_quantity=asks[0].get("quantity", 0),
                        raw_response=q,
                    )
            return result
        except Exception as e:
            self._log_error("get_quote", e)
            return {}

    # =========================================================================
    # Account Information
    # =========================================================================

    async def get_margins(self) -> Dict[str, Any]:
        """Get fund and margin summary."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{UPSTOX_API_BASE}/user/get-funds-and-margin",
                    headers=self._headers,
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("status") == "success":
                return data.get("data", {})
            return {}
        except Exception as e:
            self._log_error("get_margins", e)
            return {}

    async def get_profile(self) -> Dict[str, Any]:
        """Get user profile."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{UPSTOX_API_BASE}/user/profile",
                    headers=self._headers,
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("status") == "success":
                return data.get("data", {})
            return {}
        except Exception as e:
            self._log_error("get_profile", e)
            return {}

    # =========================================================================
    # Instruments
    # =========================================================================

    async def get_instruments(self, exchange: str = "NFO") -> List[Dict[str, Any]]:
        """Get instruments — Upstox provides instrument master as compressed JSON."""
        try:
            # Upstox instrument master is a large JSON file downloaded separately
            # Full sync handled by instrument master job
            return []
        except Exception as e:
            self._log_error("get_instruments", e)
            return []

    # =========================================================================
    # Helpers
    # =========================================================================

    def _build_instrument_key(self, order: UnifiedOrder) -> str:
        """
        Build Upstox instrument key from order.

        Upstox uses format: NSE_FO|<instrument_token> for F&O
        Falls back to tradingsymbol if no token available.
        """
        if order.instrument_token:
            exchange_map = {
                "NFO": "NSE_FO",
                "NSE": "NSE_EQ",
                "BSE": "BSE_EQ",
                "BFO": "BSE_FO",
                "MCX": "MCX_FO",
            }
            upstox_exchange = exchange_map.get(order.exchange, "NSE_FO")
            return f"{upstox_exchange}|{order.instrument_token}"
        # Fall back to tradingsymbol (may work for some endpoints)
        return order.tradingsymbol
