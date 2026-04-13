"""
Dhan Ticker Adapter

DhanHQ WebSocket v2 — binary little-endian protocol.

Key characteristics:
- Asyncio model: native `websockets` library (NOT thread-based)
  Binary frames arrive in the async receive loop, no thread bridging needed.
  Use _dispatch_async() directly (not _dispatch_from_thread).
- Token format: Numeric security_id (uint32) — stored as str in InstrumentList JSON
- Price normalization: RUPEES (no paise conversion needed)
- Connection limits: 100 tokens/connection (Ticker), 50 (Quote/Full), 1 (200-Depth)
- Max connections: 5 concurrent
- Auth: Static access token in subscription JSON body (never expires)
- Unique: Little-endian binary frames (`struct.unpack('<...')`), 200-level depth
- Response codes: 2=Ticker, 3=Quote, 4=Full, 5=200-Depth, 50=Disconnect, 100=Heartbeat

Credentials dict expected:
    {
        "client_id": str,       # Dhan client ID
        "access_token": str,    # Static API access token (never expires unless revoked)
    }

Binary packet structures (little-endian throughout):

Ticker packet (32 bytes):
  [0:2]   response_code   uint16  (=2)
  [2:3]   exchange_seg    uint8
  [3:7]   security_id     uint32
  [7:11]  ltp             float32
  [11:13] ltq             uint16
  [13:17] ltt             uint32  (epoch seconds)
  [17:21] volume          uint32
  [21:25] oi              uint32
  [25:29] change          float32
  [29:33] change_pct      float32

Quote packet (33 + 16 OHLC + 20×12 bid + 20×12 ask = 529 bytes):
  [0:33]  ticker header (same as above)
  [33:37] open            float32
  [37:41] high            float32
  [41:45] low             float32
  [45:49] close           float32
  [49+]   20 bid levels × 12 bytes, then 20 ask levels × 12 bytes
          per level: price(float32) + qty(uint32) + orders(uint16) + pad(2)
"""

import asyncio
import json
import logging
import struct
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..adapter_base import TickerAdapter
from ..models import NormalizedTick

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# CONSTANTS
# ───────────────────────────────────────────────────────────────────────

_WS_URL = "wss://api-feed.dhan.co"

# Response codes (first uint16 of each binary frame)
_RC_TICKER = 2
_RC_QUOTE = 3
_RC_FULL = 4
_RC_DEPTH_200 = 5
_RC_DISCONNECT = 50
_RC_HEARTBEAT = 100

# Exchange segment byte → string (used only for logging/debug)
_EXCHANGE_MAP: Dict[int, str] = {
    0: "NSE_EQ",
    1: "NSE_FNO",
    2: "NSE_CURRENCY",
    3: "BSE_EQ",
    4: "BSE_FNO",
    5: "BSE_CURRENCY",
    6: "MCX_COMM",
    7: "IDX_I",
}

# Exchange segment string → string (subscription JSON format)
# Reverse of _EXCHANGE_MAP but some segments have IDX_I as exception
_SEG_TO_DHAN: Dict[str, str] = {v: v for v in _EXCHANGE_MAP.values()}

# Mode → Dhan subscription mode string
# Used as a hint for capacity warnings; actual data format determined by server
_MODE_TO_DHAN: Dict[str, str] = {
    "ltp": "Ticker",
    "quote": "Quote",
    "snap": "Quote",
    "full": "Full",
    "depth": "Quote",
}

# Max instruments per connection per mode (for capacity warnings)
_MODE_CAPACITY: Dict[str, int] = {
    "Ticker": 100,
    "Quote": 50,
    "Full": 50,
    "200-Depth": 1,
}

# Minimum viable ticker packet size (bytes)
_TICKER_MIN_SIZE = 29


class DhanTickerAdapter(TickerAdapter):
    """
    Dhan WebSocket ticker adapter (binary little-endian, asyncio-native).

    Platform failover rank: #2
    Cost: FREE (with 25+ F&O trades/month)
    Capacity: 100 tokens/connection × 5 connections = 500 tokens (Ticker mode)

    Protocol model (DIFFERENT from SmartAPI/Kite/Fyers — asyncio-native):
    - Uses `websockets` library in an async receive loop
    - No daemon thread needed — _ws_receive_loop() is a long-running coroutine
    - Binary frames → _parse_binary() → _dispatch_async() (not _dispatch_from_thread)

    Token mapping:
    - canonical Kite token (int) → Dhan (security_id_str, exchange_segment_str)
    - Dhan security_id (uint32) → canonical Kite token (int)
    - Must be pre-loaded via load_token_map() before subscribing
    """

    def __init__(self, broker_type: str = "dhan"):
        super().__init__(broker_type)
        self._ws = None                          # websockets.WebSocketClientProtocol
        self._receive_task: Optional[asyncio.Task] = None

        # Token mapping caches (loaded before first subscribe)
        # canonical Kite token (int) → (security_id_str, exchange_segment_str)
        self._canonical_to_broker: Dict[int, Tuple[str, str]] = {}
        # Dhan security_id (int) → canonical Kite token (int)
        self._security_id_to_canonical: Dict[int, int] = {}

        # Current mode (set at first subscribe — Dhan doesn't change modes mid-session)
        self._current_mode: str = "Ticker"

        # Credentials stored for reconnect and subscription messages
        self._access_token: str = ""
        self._client_id: str = ""

    # ═══════════════════════════════════════════════════════════════════════
    # TOKEN MAP MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def load_token_map(self, mapping: Dict[int, Tuple[str, str]]) -> None:
        """
        Pre-load canonical ↔ Dhan token mappings.

        Called before subscribing. The TickerPool or startup code loads this
        from the broker_instrument_tokens DB table (async) and passes it here.

        Args:
            mapping: {canonical_token: (security_id_str, exchange_segment_str)}
                     e.g. {256265: ("13", "IDX_I"), 260105: ("25", "IDX_I"),
                           12345678: ("43854", "NSE_FNO")}
        """
        for canonical, (sec_id_str, exchange_seg) in mapping.items():
            self._canonical_to_broker[canonical] = (sec_id_str, exchange_seg)
            # security_id as int for binary frame lookup
            try:
                self._security_id_to_canonical[int(sec_id_str)] = canonical
            except ValueError:
                logger.warning(
                    "[Dhan] Invalid security_id '%s' for canonical %d — skipping",
                    sec_id_str, canonical,
                )
        logger.info("[Dhan] Loaded %d token mappings", len(mapping))

    # ═══════════════════════════════════════════════════════════════════════
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════════════════

    async def _connect_ws(self, credentials: dict) -> None:
        """
        Connect to Dhan Feed WebSocket.

        Args:
            credentials: {
                "client_id": str,       # Dhan client ID
                "access_token": str,    # Static API access token
                "token_map": optional dict for load_token_map
            }
        """
        import websockets

        self._client_id = credentials["client_id"]
        self._access_token = credentials["access_token"]

        # Optional: pre-load token mappings from credentials
        token_map = credentials.get("token_map")
        if token_map:
            self.load_token_map(token_map)

        logger.info("[Dhan] Connecting WebSocket for client_id: %s", self._client_id)

        # Connect — Dhan auth is sent via subscription JSON, NOT the HTTP headers
        self._ws = await websockets.connect(_WS_URL)

        # Start background receive loop
        self._receive_task = asyncio.create_task(
            self._ws_receive_loop(),
            name="Dhan-WS-Receive",
        )

        logger.info("[Dhan] WebSocket connected for client_id: %s", self._client_id)

    async def _disconnect_ws(self) -> None:
        """Disconnect from Dhan WebSocket."""
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.warning("[Dhan] Disconnect error: %s", e)
            self._ws = None

        logger.info("[Dhan] WebSocket disconnected")

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        """
        Subscribe to Dhan instruments via JSON subscription frame.

        Args:
            broker_tokens: List of (security_id_str, exchange_segment_str) tuples
                           e.g. [("13", "IDX_I"), ("25", "IDX_I"), ("43854", "NSE_FNO")]
            mode: 'ltp', 'quote', 'snap', 'full', or 'depth'
        """
        if not self._ws:
            raise ConnectionError("[Dhan] WebSocket not connected")

        if not broker_tokens:
            return

        dhan_mode = _MODE_TO_DHAN.get(mode, "Ticker")
        self._current_mode = dhan_mode

        capacity = _MODE_CAPACITY.get(dhan_mode, 100)
        if len(broker_tokens) > capacity:
            logger.warning(
                "[Dhan] %d tokens requested but mode '%s' supports max %d/connection",
                len(broker_tokens), dhan_mode, capacity,
            )

        instrument_list = [
            {"ExchangeSegment": seg, "SecurityId": sec_id}
            for sec_id, seg in broker_tokens
        ]

        msg = {
            "RequestCode": 21,  # Subscribe
            "InstrumentCount": len(instrument_list),
            "InstrumentList": instrument_list,
        }

        await self._ws.send(json.dumps(msg))
        logger.info(
            "[Dhan] Subscribed to %d instruments (mode=%s)",
            len(instrument_list), dhan_mode,
        )

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        """
        Unsubscribe from Dhan instruments.

        Args:
            broker_tokens: List of (security_id_str, exchange_segment_str) tuples
        """
        if not self._ws:
            return

        if not broker_tokens:
            return

        instrument_list = [
            {"ExchangeSegment": seg, "SecurityId": sec_id}
            for sec_id, seg in broker_tokens
        ]

        msg = {
            "RequestCode": 22,  # Unsubscribe
            "InstrumentCount": len(instrument_list),
            "InstrumentList": instrument_list,
        }

        await self._ws.send(json.dumps(msg))
        logger.info("[Dhan] Unsubscribed from %d instruments", len(instrument_list))

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Convert canonical Kite tokens to Dhan (security_id_str, exchange_segment_str) tuples.

        Args:
            canonical_tokens: [256265, 260105, ...]

        Returns:
            [("13", "IDX_I"), ("25", "IDX_I"), ...]
        """
        result = []
        for canonical_token in canonical_tokens:
            broker_pair = self._canonical_to_broker.get(canonical_token)
            if broker_pair is None:
                logger.warning(
                    "[Dhan] No broker token for canonical %d — skipping",
                    canonical_token,
                )
                continue
            result.append(broker_pair)
        return result

    def _get_canonical_token(self, broker_token: Any) -> int:
        """
        Convert Dhan security_id (int or str) to canonical Kite token.

        Args:
            broker_token: Dhan security_id as int or str (e.g., 13 or "13")

        Returns:
            Canonical Kite instrument token (e.g., 256265), or 0 if unknown
        """
        try:
            sec_id = int(broker_token)
        except (TypeError, ValueError):
            logger.warning("[Dhan] Invalid security_id: %s", broker_token)
            return 0

        canonical = self._security_id_to_canonical.get(sec_id)
        if canonical is None:
            logger.warning("[Dhan] Unknown security_id: %d", sec_id)
            return 0
        return canonical

    def _parse_tick(self, raw_data: Any) -> List[NormalizedTick]:
        """
        Parse Dhan binary frame into NormalizedTick.

        Dhan always sends binary bytes — raw_data is a bytes object.
        Dispatched internally by _ws_receive_loop → _parse_binary.
        External callers should pass bytes; non-bytes input is ignored.
        """
        if not isinstance(raw_data, (bytes, bytearray)):
            return []

        return self._parse_binary(raw_data)

    # ═══════════════════════════════════════════════════════════════════════
    # BINARY PARSER — little-endian
    # ═══════════════════════════════════════════════════════════════════════

    def _parse_binary(self, data: bytes) -> List[NormalizedTick]:
        """
        Parse a Dhan binary frame (little-endian).

        Dispatches to the appropriate parser based on the first 2-byte
        response_code (uint16 little-endian).
        """
        if len(data) < 2:
            return []

        response_code = struct.unpack_from("<H", data, 0)[0]

        if response_code == _RC_HEARTBEAT:
            logger.debug("[Dhan] Heartbeat received")
            return []

        if response_code == _RC_DISCONNECT:
            logger.warning("[Dhan] Disconnect message received from server")
            return []

        if response_code in (_RC_TICKER, _RC_QUOTE, _RC_FULL, _RC_DEPTH_200):
            return self._parse_tick_packet(data, response_code)

        logger.debug("[Dhan] Unknown response_code=%d (len=%d)", response_code, len(data))
        return []

    def _parse_tick_packet(self, data: bytes, response_code: int) -> List[NormalizedTick]:
        """
        Parse a Ticker/Quote/Full binary packet into NormalizedTick.

        Ticker packet layout (32+ bytes, little-endian):
          [0:2]   response_code  uint16
          [2:3]   exchange_seg   uint8
          [3:7]   security_id    uint32
          [7:11]  ltp            float32
          [11:13] ltq            uint16
          [13:17] ltt            uint32  (epoch seconds)
          [17:21] volume         uint32
          [21:25] oi             uint32
          [25:29] change         float32
          [29:33] change_pct     float32

        Quote/Full adds OHLC at [33:49]:
          [33:37] open           float32
          [37:41] high           float32
          [41:45] low            float32
          [45:49] close          float32

        Then 20×12-byte bid levels + 20×12-byte ask levels for Quote/Full.
        """
        if len(data) < _TICKER_MIN_SIZE:
            logger.debug(
                "[Dhan] Packet too small: %d bytes (response_code=%d)",
                len(data), response_code,
            )
            return []

        try:
            # ── Header (common to all modes) ──
            # [0:2] already consumed as response_code
            exchange_seg_byte = struct.unpack_from("<B", data, 2)[0]
            security_id = struct.unpack_from("<I", data, 3)[0]
            ltp_raw = struct.unpack_from("<f", data, 7)[0]
            # ltq at [11:13] — not used in NormalizedTick
            ltt = struct.unpack_from("<I", data, 13)[0]
            volume = struct.unpack_from("<I", data, 17)[0]
            oi = struct.unpack_from("<I", data, 21)[0]
            change_raw = struct.unpack_from("<f", data, 25)[0]
            # change_pct at [29:33] — Dhan provides it, but we recalculate from Decimal

            # Look up canonical token
            canonical_token = self._get_canonical_token(security_id)
            if canonical_token == 0:
                return []

            # Convert prices to Decimal (Dhan sends RUPEES — no paise conversion)
            ltp = Decimal(str(round(ltp_raw, 2)))
            change = Decimal(str(round(change_raw, 2)))

            # Timestamp from ltt (epoch seconds)
            try:
                timestamp = datetime.fromtimestamp(ltt) if ltt else datetime.now()
            except (ValueError, OSError, OverflowError):
                timestamp = datetime.now()

            # ── OHLC (Quote/Full mode only — starts at offset 33) ──
            open_price = Decimal("0")
            high = Decimal("0")
            low = Decimal("0")
            close = Decimal("0")

            if response_code in (_RC_QUOTE, _RC_FULL, _RC_DEPTH_200) and len(data) >= 49:
                open_raw = struct.unpack_from("<f", data, 33)[0]
                high_raw = struct.unpack_from("<f", data, 37)[0]
                low_raw = struct.unpack_from("<f", data, 41)[0]
                close_raw = struct.unpack_from("<f", data, 45)[0]

                open_price = Decimal(str(round(open_raw, 2)))
                high = Decimal(str(round(high_raw, 2)))
                low = Decimal(str(round(low_raw, 2)))
                close = Decimal(str(round(close_raw, 2)))

            # Recalculate change from Decimal to avoid float precision drift
            # (use close/prev_close if available, else fall back to raw change)
            if close != 0:
                change = ltp - close
                change_percent = (change / close * 100)
            else:
                # Close not available (Ticker mode) — use raw change from packet
                change_percent = Decimal("0")

            # ── Bid/Ask (Quote/Full mode — depth level 0 = best bid/ask) ──
            bid: Optional[Decimal] = None
            ask: Optional[Decimal] = None
            bid_qty: Optional[int] = None
            ask_qty: Optional[int] = None

            # Depth starts at offset 49 for Quote/Full; each level = 12 bytes
            # (4 price + 4 qty + 2 orders + 2 pad)
            _DEPTH_OFFSET = 49
            _LEVEL_SIZE = 12
            _BID_BLOCK_SIZE = 20 * _LEVEL_SIZE   # 240 bytes for 20 bid levels

            if response_code in (_RC_QUOTE, _RC_FULL) and len(data) >= _DEPTH_OFFSET + _LEVEL_SIZE:
                bid_price_raw = struct.unpack_from("<f", data, _DEPTH_OFFSET)[0]
                bid_qty_raw = struct.unpack_from("<I", data, _DEPTH_OFFSET + 4)[0]
                if bid_price_raw > 0:
                    bid = Decimal(str(round(bid_price_raw, 2)))
                    bid_qty = int(bid_qty_raw)

                # First ask level starts after all 20 bid levels
                ask_offset = _DEPTH_OFFSET + _BID_BLOCK_SIZE
                if len(data) >= ask_offset + _LEVEL_SIZE:
                    ask_price_raw = struct.unpack_from("<f", data, ask_offset)[0]
                    ask_qty_raw = struct.unpack_from("<I", data, ask_offset + 4)[0]
                    if ask_price_raw > 0:
                        ask = Decimal(str(round(ask_price_raw, 2)))
                        ask_qty = int(ask_qty_raw)

            tick = NormalizedTick(
                token=canonical_token,
                ltp=ltp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                change=change,
                change_percent=change_percent,
                volume=int(volume),
                oi=int(oi),
                timestamp=timestamp,
                broker_type=self.broker_type,
                bid=bid,
                ask=ask,
                bid_qty=bid_qty,
                ask_qty=ask_qty,
            )

            return [tick]

        except struct.error as e:
            logger.error(
                "[Dhan] Binary parse error (response_code=%d, len=%d): %s",
                response_code, len(data), e,
            )
            return []
        except Exception as e:
            logger.error("[Dhan] Tick parsing error: %s", e, exc_info=True)
            return []

    # ═══════════════════════════════════════════════════════════════════════
    # ASYNCIO RECEIVE LOOP
    # ═══════════════════════════════════════════════════════════════════════

    async def _ws_receive_loop(self) -> None:
        """
        Main asyncio receive loop for Dhan WebSocket binary frames.

        Runs as an asyncio.Task until disconnect. Dispatches parsed ticks
        directly via _dispatch_async (no thread bridging needed).
        """
        import websockets.exceptions

        logger.info("[Dhan] Receive loop started")
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    ticks = self._parse_binary(message)
                    if ticks:
                        await self._dispatch_async(ticks)
                else:
                    # JSON control message (rare — Dhan mostly uses binary)
                    try:
                        payload = json.loads(message)
                        logger.debug("[Dhan] JSON control message: %s", payload)
                    except json.JSONDecodeError:
                        logger.debug("[Dhan] Non-JSON text message: %s", message[:100])

        except asyncio.CancelledError:
            logger.info("[Dhan] Receive loop cancelled (graceful disconnect)")
            raise  # Re-raise so the task completes cleanly

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning("[Dhan] WebSocket connection closed: %s", e)
            self._report_error("connection_closed", str(e))
            self._connected = False

        except Exception as e:
            logger.error("[Dhan] Receive loop error: %s", e, exc_info=True)
            self._report_error("receive_loop_error", str(e))
            self._connected = False

        logger.info("[Dhan] Receive loop ended")
