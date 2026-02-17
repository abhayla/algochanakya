"""
Paytm Money Ticker Adapter

Paytm WebSocket: JSON-based, asyncio-native (same pattern as Dhan).

Key characteristics:
- Threading model: asyncio-native — `websockets` library in async receive loop.
  Use _dispatch_async() directly (no thread bridge needed).
- Token format: Paytm security_id (string) + exchange + scrip_type stored in
  _canonical_to_broker as (security_id_str, exchange_str, scrip_type_str).
- Price normalization: RUPEES (no paise conversion needed).
- Connection limits: 200 instruments/connection, 1 connection per API key.
- Auth: OAuth 2.0 with 3 JWTs:
    - access_token (REST full)
    - read_access_token (REST read-only)
    - public_access_token (WebSocket) — CRITICAL: this one for WS, NOT access_token
  All tokens expire at midnight IST (daily re-auth required).
- Auth URL: wss://...?x_jwt_token={public_access_token} (query param, NOT header).
- Subscription: per-instrument JSON ADD/REMOVE messages (or batched list).
- Modes: LTP (price only) or FULL (OHLC + volume + OI + bid/ask).
- Ping: client sends websocket ping every 30s to keep connection alive.
- Maturity warning: Paytm WS may disconnect without close frame. Implement
  reconnect logic; connection drops during high-volatility periods have been observed.

Credentials dict expected:
    {
        "api_key": str,                 # Paytm API key
        "public_access_token": str,     # WebSocket token (NOT access_token!)
    }

Token mapping dict expected via load_token_map():
    {
        canonical_kite_token (int): (security_id_str, exchange_str, scrip_type_str)
        # e.g. {256265: ("999920000", "NSE", "INDEX")}
    }
"""

import asyncio
import json
import logging
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..adapter_base import TickerAdapter
from ..models import NormalizedTick

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# CONSTANTS
# ───────────────────────────────────────────────────────────────────────

_WS_BASE_URL = "wss://developer-ws.paytmmoney.com/broadcast/user/v1/data"

# Maximum instruments per connection (Paytm limit)
_MAX_INSTRUMENTS = 200

# Ping interval in seconds (keep-alive per Paytm recommendation)
_PING_INTERVAL = 30

# Mode → Paytm modeType string
_MODE_TO_PAYTM: Dict[str, str] = {
    "ltp": "LTP",
    "quote": "FULL",
    "snap": "FULL",
    "full": "FULL",
    "depth": "FULL",
}

# scrip_type values (stored in token map; used in subscription messages)
# Callers should pre-populate scrip_type from the Paytm script master.
# Defaults: EQUITY for stocks, INDEX for indices, DERIVATIVE for F&O.
_VALID_SCRIP_TYPES = {"EQUITY", "INDEX", "DERIVATIVE"}

# Message type field in received JSON
_MSG_TICK = "tick"
_MSG_CONNECTED = "connected"
_MSG_SUBSCRIBED = "subscribed"
_MSG_ERROR = "error"
_MSG_CLOSE = "close"


class PaytmTickerAdapter(TickerAdapter):
    """
    Paytm Money WebSocket ticker adapter (JSON, asyncio-native).

    Platform failover rank: #4
    Cost: FREE
    Capacity: 200 instruments/connection (lowest among all brokers)

    Protocol model (same as Dhan — asyncio-native):
    - Uses `websockets` library in an async receive loop.
    - No daemon thread needed — _ws_receive_loop() is a long-running coroutine.
    - JSON frames → _parse_json_tick() → _dispatch_async().

    Token mapping:
    - canonical Kite token (int) → (security_id_str, exchange_str, scrip_type_str)
    - Paytm security_id_str → canonical Kite token (int)
    - Must be pre-loaded via load_token_map() before subscribing.

    Auth note:
    - WebSocket URL includes public_access_token as query parameter.
    - Tokens expire at midnight IST — reconnect required after each trading day.
    """

    def __init__(self, broker_type: str = "paytm"):
        super().__init__(broker_type)
        self._ws = None                             # websockets.WebSocketClientProtocol
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None

        # Token mapping caches
        # canonical Kite token (int) → (security_id_str, exchange_str, scrip_type_str)
        self._canonical_to_broker: Dict[int, Tuple[str, str, str]] = {}
        # Paytm security_id_str → canonical Kite token (int)
        self._security_id_to_canonical: Dict[str, int] = {}

        # Credentials stored for reconnect
        self._public_access_token: str = ""
        self._api_key: str = ""

    # ═══════════════════════════════════════════════════════════════════════
    # TOKEN MAP MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def load_token_map(
        self, mapping: Dict[int, Tuple[str, str, str]]
    ) -> None:
        """
        Pre-load canonical ↔ Paytm token mappings.

        Called before subscribing. The TickerPool or startup code loads this
        from the broker_instrument_tokens DB table and passes it here.

        Args:
            mapping: {canonical_token: (security_id_str, exchange_str, scrip_type_str)}
                     e.g. {256265: ("999920000", "NSE", "INDEX"),
                           260105: ("999920005", "NSE", "INDEX"),
                           12345678: ("46512", "NSE", "DERIVATIVE")}
        """
        for canonical, (sec_id_str, exchange, scrip_type) in mapping.items():
            self._canonical_to_broker[canonical] = (sec_id_str, exchange, scrip_type)
            self._security_id_to_canonical[sec_id_str] = canonical

        logger.info("[Paytm] Loaded %d token mappings", len(mapping))

    # ═══════════════════════════════════════════════════════════════════════
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════════════════

    async def _connect_ws(self, credentials: dict) -> None:
        """
        Connect to Paytm WebSocket using public_access_token.

        Args:
            credentials: {
                "api_key": str,
                "public_access_token": str,     # WebSocket auth token
                "token_map": optional dict for load_token_map
            }
        """
        import websockets

        self._api_key = credentials.get("api_key", "")
        self._public_access_token = credentials["public_access_token"]

        # Optional: pre-load token mappings from credentials
        token_map = credentials.get("token_map")
        if token_map:
            self.load_token_map(token_map)

        # Build WebSocket URL — public_access_token as query param (not header)
        ws_url = f"{_WS_BASE_URL}?x_jwt_token={self._public_access_token}"

        logger.info("[Paytm] Connecting WebSocket (api_key: %s...)", self._api_key[:8] if self._api_key else "N/A")

        self._ws = await websockets.connect(ws_url)

        # Start background receive loop
        self._receive_task = asyncio.create_task(
            self._ws_receive_loop(),
            name="Paytm-WS-Receive",
        )

        # Start background ping loop (keep-alive)
        self._ping_task = asyncio.create_task(
            self._ws_ping_loop(),
            name="Paytm-WS-Ping",
        )

        logger.info("[Paytm] WebSocket connected")

    async def _disconnect_ws(self) -> None:
        """Disconnect from Paytm WebSocket and cancel background tasks."""
        # Cancel ping loop
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None

        # Cancel receive loop
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # Close WebSocket
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.warning("[Paytm] Disconnect error: %s", e)
            self._ws = None

        logger.info("[Paytm] WebSocket disconnected")

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        """
        Subscribe to Paytm instruments via JSON ADD messages.

        Args:
            broker_tokens: List of (security_id_str, exchange_str, scrip_type_str) tuples
                           e.g. [("999920000", "NSE", "INDEX"), ("46512", "NSE", "DERIVATIVE")]
            mode: 'ltp', 'quote', 'snap', 'full', or 'depth'
        """
        if not self._ws:
            raise ConnectionError("[Paytm] WebSocket not connected")

        if not broker_tokens:
            return

        paytm_mode = _MODE_TO_PAYTM.get(mode, "FULL")

        if len(broker_tokens) > _MAX_INSTRUMENTS:
            logger.warning(
                "[Paytm] %d tokens requested but max is %d/connection",
                len(broker_tokens), _MAX_INSTRUMENTS,
            )

        # Build batch subscription list
        messages = [
            {
                "actionType": "ADD",
                "modeType": paytm_mode,
                "scripType": scrip_type,
                "exchangeType": exchange,
                "scripId": sec_id,
            }
            for sec_id, exchange, scrip_type in broker_tokens
        ]

        # Send as batch (list) for efficiency
        await self._ws.send(json.dumps(messages))
        logger.info(
            "[Paytm] Subscribed to %d instruments (mode=%s)",
            len(messages), paytm_mode,
        )

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        """
        Unsubscribe from Paytm instruments via JSON REMOVE messages.

        Args:
            broker_tokens: List of (security_id_str, exchange_str, scrip_type_str) tuples
        """
        if not self._ws:
            return

        if not broker_tokens:
            return

        messages = [
            {
                "actionType": "REMOVE",
                "modeType": "LTP",  # mode doesn't matter for REMOVE
                "scripType": scrip_type,
                "exchangeType": exchange,
                "scripId": sec_id,
            }
            for sec_id, exchange, scrip_type in broker_tokens
        ]

        await self._ws.send(json.dumps(messages))
        logger.info("[Paytm] Unsubscribed from %d instruments", len(messages))

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Convert canonical Kite tokens to Paytm (security_id_str, exchange_str, scrip_type_str) tuples.

        Args:
            canonical_tokens: [256265, 260105, ...]

        Returns:
            [("999920000", "NSE", "INDEX"), ("999920005", "NSE", "INDEX"), ...]
        """
        result = []
        for canonical_token in canonical_tokens:
            broker_triple = self._canonical_to_broker.get(canonical_token)
            if broker_triple is None:
                logger.warning(
                    "[Paytm] No broker token for canonical %d — skipping",
                    canonical_token,
                )
                continue
            result.append(broker_triple)
        return result

    def _get_canonical_token(self, broker_token: Any) -> int:
        """
        Convert Paytm security_id (str or int) to canonical Kite token.

        Args:
            broker_token: Paytm security_id as str or int (e.g., "999920000" or 999920000)

        Returns:
            Canonical Kite instrument token (e.g., 256265), or 0 if unknown.
        """
        sec_id_str = str(broker_token)
        canonical = self._security_id_to_canonical.get(sec_id_str)
        if canonical is None:
            logger.warning("[Paytm] Unknown security_id: %s", sec_id_str)
            return 0
        return canonical

    def _parse_tick(self, raw_data: Any) -> List[NormalizedTick]:
        """
        Parse a Paytm JSON tick message into NormalizedTick list.

        Paytm sends JSON text frames — raw_data should be a str or dict.
        Non-tick messages (connected, subscribed, error, close) are handled
        as control messages and return [].
        """
        if isinstance(raw_data, (bytes, bytearray)):
            try:
                raw_data = raw_data.decode("utf-8")
            except UnicodeDecodeError:
                logger.warning("[Paytm] Failed to decode bytes tick")
                return []

        if isinstance(raw_data, str):
            try:
                payload = json.loads(raw_data)
            except json.JSONDecodeError as e:
                logger.warning("[Paytm] JSON decode error: %s — data: %.100s", e, raw_data)
                return []
        elif isinstance(raw_data, dict):
            payload = raw_data
        else:
            return []

        return self._parse_json_tick(payload)

    # ═══════════════════════════════════════════════════════════════════════
    # JSON TICK PARSER
    # ═══════════════════════════════════════════════════════════════════════

    def _parse_json_tick(self, payload: Any) -> List[NormalizedTick]:
        """
        Parse a Paytm JSON payload into NormalizedTick(s).

        Handles:
        - Single tick dict: {"type": "tick", "data": {...}}
        - Batch tick list: [{"type": "tick", ...}, ...]
        - Control messages: connected, subscribed, error, close (logged, return [])
        """
        if isinstance(payload, list):
            ticks = []
            for item in payload:
                ticks.extend(self._parse_json_tick(item))
            return ticks

        if not isinstance(payload, dict):
            return []

        msg_type = payload.get("type", "")

        if msg_type == _MSG_TICK:
            data = payload.get("data", {})
            if not data:
                return []
            tick = self._build_normalized_tick(data)
            return [tick] if tick else []

        elif msg_type == _MSG_CONNECTED:
            logger.info("[Paytm] Connection confirmed: %s", payload.get("message", ""))
            return []

        elif msg_type == _MSG_SUBSCRIBED:
            logger.debug("[Paytm] Subscribed: security_id=%s", payload.get("security_id"))
            return []

        elif msg_type == _MSG_ERROR:
            logger.warning(
                "[Paytm] Server error: %s (code=%s)",
                payload.get("message"), payload.get("code"),
            )
            return []

        elif msg_type == _MSG_CLOSE:
            logger.warning(
                "[Paytm] Server close: code=%s reason=%s",
                payload.get("code"), payload.get("reason"),
            )
            return []

        else:
            logger.debug("[Paytm] Unknown message type: %s", msg_type)
            return []

    def _build_normalized_tick(self, data: dict) -> Optional[NormalizedTick]:
        """
        Convert a Paytm tick data dict to NormalizedTick.

        Paytm tick data dict (FULL mode):
        {
            "security_id": "500325",        # str
            "exchange": "NSE",
            "last_price": 1825.50,          # RUPEES (no conversion needed)
            "open": 1820.00,
            "high": 1830.00,
            "low": 1815.00,
            "close": 1818.25,
            "change": 7.25,
            "change_pct": 0.40,
            "volume": 1234567,
            "oi": 0,
            "bid_price": 1825.45,
            "bid_qty": 100,
            "ask_price": 1825.55,
            "ask_qty": 150,
            "last_trade_time": "2024-01-15T10:30:15",
            "exchange_timestamp": "2024-01-15T10:30:15",
        }

        LTP mode only has: security_id, exchange, last_price, change, change_pct.
        """
        try:
            sec_id = data.get("security_id")
            if sec_id is None:
                logger.warning("[Paytm] Tick missing security_id: %s", data)
                return None

            canonical_token = self._get_canonical_token(sec_id)
            if canonical_token == 0:
                return None

            # last_price → ltp (Paytm sends RUPEES — no paise conversion)
            ltp_raw = data.get("last_price", 0)
            ltp = Decimal(str(round(float(ltp_raw), 2)))

            # OHLC (FULL mode only; zero for LTP mode)
            open_price = Decimal(str(round(float(data.get("open", 0)), 2)))
            high = Decimal(str(round(float(data.get("high", 0)), 2)))
            low = Decimal(str(round(float(data.get("low", 0)), 2)))
            close = Decimal(str(round(float(data.get("close", 0)), 2)))

            # Change metrics
            change_raw = data.get("change", 0)
            change = Decimal(str(round(float(change_raw), 2)))

            # Recalculate change_percent from Decimal for precision
            # Prefer: (ltp - close) / close * 100 if close available
            if close != 0:
                change = ltp - close
                change_percent = (change / close * 100).quantize(Decimal("0.01"))
            else:
                # LTP mode — use server-provided change_pct
                change_pct_raw = data.get("change_pct", 0)
                change_percent = Decimal(str(round(float(change_pct_raw), 2)))

            # Volume & OI
            volume = int(data.get("volume", 0))
            oi = int(data.get("oi", 0))

            # Timestamp from exchange_timestamp or last_trade_time
            timestamp = self._parse_paytm_timestamp(
                data.get("exchange_timestamp") or data.get("last_trade_time")
            )

            # Bid/Ask (FULL mode only)
            bid: Optional[Decimal] = None
            ask: Optional[Decimal] = None
            bid_qty: Optional[int] = None
            ask_qty: Optional[int] = None

            bid_price_raw = data.get("bid_price")
            ask_price_raw = data.get("ask_price")

            if bid_price_raw is not None and float(bid_price_raw) > 0:
                bid = Decimal(str(round(float(bid_price_raw), 2)))
                bid_qty = int(data.get("bid_qty", 0))

            if ask_price_raw is not None and float(ask_price_raw) > 0:
                ask = Decimal(str(round(float(ask_price_raw), 2)))
                ask_qty = int(data.get("ask_qty", 0))

            return NormalizedTick(
                token=canonical_token,
                ltp=ltp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                change=change,
                change_percent=change_percent,
                volume=volume,
                oi=oi,
                timestamp=timestamp,
                broker_type=self.broker_type,
                bid=bid,
                ask=ask,
                bid_qty=bid_qty,
                ask_qty=ask_qty,
            )

        except (TypeError, ValueError, ArithmeticError) as e:
            logger.error("[Paytm] Tick build error: %s — data: %s", e, data)
            return None

    @staticmethod
    def _parse_paytm_timestamp(ts_str: Optional[str]) -> datetime:
        """
        Parse Paytm ISO timestamp string to datetime.

        Formats observed:
        - "2024-01-15T10:30:15"
        - "2024-01-15T10:30:15.000Z"

        Falls back to datetime.now() on parse failure.
        """
        if not ts_str:
            return datetime.now()
        try:
            # Strip trailing Z and microseconds for simplicity
            clean = ts_str.replace("Z", "").split(".")[0]
            return datetime.fromisoformat(clean)
        except (ValueError, AttributeError):
            return datetime.now()

    # ═══════════════════════════════════════════════════════════════════════
    # ASYNCIO LOOPS
    # ═══════════════════════════════════════════════════════════════════════

    async def _ws_receive_loop(self) -> None:
        """
        Main asyncio receive loop for Paytm WebSocket JSON frames.

        Runs as an asyncio.Task until disconnect. Dispatches parsed ticks
        directly via _dispatch_async (no thread bridging needed).

        Paytm may drop connection without close frame during high-volatility
        periods. Sets _connected=False on unexpected disconnects so the
        FailoverController can detect and trigger failover.
        """
        import websockets.exceptions

        logger.info("[Paytm] Receive loop started")
        try:
            async for message in self._ws:
                if isinstance(message, str):
                    ticks = self._parse_tick(message)
                    if ticks:
                        await self._dispatch_async(ticks)
                elif isinstance(message, (bytes, bytearray)):
                    # Paytm is JSON-only, but handle bytes defensively
                    ticks = self._parse_tick(message)
                    if ticks:
                        await self._dispatch_async(ticks)
                else:
                    logger.debug("[Paytm] Unknown message type: %s", type(message))

        except asyncio.CancelledError:
            logger.info("[Paytm] Receive loop cancelled (graceful disconnect)")
            raise  # Re-raise so the task completes cleanly

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning("[Paytm] WebSocket connection closed: %s", e)
            self._connected = False

        except Exception as e:
            logger.error("[Paytm] Receive loop error: %s", e, exc_info=True)
            self._connected = False

        logger.info("[Paytm] Receive loop ended")

    async def _ws_ping_loop(self) -> None:
        """
        Background ping loop to keep Paytm WebSocket alive.

        Paytm recommends pinging every 30 seconds. Uses websockets native
        ping() which sends a WebSocket PING frame (not application-level JSON).
        """
        try:
            while self._ws and self._connected:
                await asyncio.sleep(_PING_INTERVAL)
                if self._ws:
                    try:
                        await self._ws.ping()
                        logger.debug("[Paytm] Ping sent")
                    except Exception as e:
                        logger.warning("[Paytm] Ping failed: %s", e)
                        break

        except asyncio.CancelledError:
            logger.debug("[Paytm] Ping loop cancelled")
            raise

        except Exception as e:
            logger.error("[Paytm] Ping loop error: %s", e)

        logger.debug("[Paytm] Ping loop ended")
