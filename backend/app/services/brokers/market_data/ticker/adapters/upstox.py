"""
Upstox Ticker Adapter

Upstox MarketDataFeedV3 — Protobuf WebSocket protocol.

Key characteristics:
- Asyncio model: native `websockets` library (NOT thread-based)
  Protobuf frames arrive in the async receive loop, no thread bridging needed.
  Use _dispatch_async() directly (not _dispatch_from_thread).
- Auth: OAuth 2.0 — call REST /v2/feed/market-data-feed/authorize to get
  an authorized WebSocket URL, then connect. access_token valid ~24h;
  extended_token valid ~1 year (read-only, ideal for platform market data).
- Token format: "{EXCHANGE_SEGMENT}|{instrument_key}" string
  e.g. "NSE_FO|12345", "NSE_INDEX|Nifty 50", "NSE_EQ|2885"
- Price normalization: RUPEES (no paise conversion needed)
- Connection limits: 1 connection/access_token
- Capacity: ~1,500 tokens (basic plan) or ~5,000 tokens (pro plan)
- Unique feature: option_greeks mode delivers delta/gamma/theta/vega via WebSocket
- Protocol: Protobuf binary frames (parsed at runtime — no compiled _pb2 required)
- Rate limits: 25 req/sec

Credentials dict expected:
    {
        "api_key": str,        # Upstox API key
        "access_token": str,   # OAuth access_token or extended_token
    }

Subscription modes (passed to subscribe()):
    "ltp"    → Upstox "ltpc" mode (LTP + close + change)
    "quote"  → Upstox "full" mode (OHLC + volume + OI + 5-level depth)
    "full"   → Upstox "full" mode
    "greeks" → Upstox "option_greeks" mode (full + delta/gamma/theta/vega)

Protobuf schema (FeedResponse):
    message FeedResponse {
        string type = 1;               // "live_feed"
        map<string, Feed> feeds = 2;   // keyed by instrument_key
    }
    message Feed {
        LTPC ltpc = 1;
        FullFeed ff = 2;
        OptionGreeks og = 3;
    }
    message LTPC { double ltp=1; double close=2; double change=3; double change_percent=4; }
    message FullFeed { OHLC ohlc=1; MarketDepth depth=2; int64 volume=3; int64 oi=4;
                       double avg_price=5; int64 total_buy_qty=6; int64 total_sell_qty=7; }
    message OHLC { double open=1; double high=2; double low=3; double close=4; }
    message MarketDepth { repeated Level bid=1; repeated Level ask=2; }
    message Level { double price=1; int64 quantity=2; int64 orders=3; }
    message OptionGreeks { double delta=1; double gamma=2; double theta=3;
                           double vega=4; double iv=5; }
"""

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..adapter_base import TickerAdapter
from ..models import NormalizedTick

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# CONSTANTS
# ───────────────────────────────────────────────────────────────────────

_REST_AUTHORIZE_URL = "https://api.upstox.com/v3/feed/market-data-feed/authorize"

# Mode mapping: our internal mode → Upstox subscription mode string
_MODE_TO_UPSTOX: Dict[str, str] = {
    "ltp": "ltpc",
    "quote": "full",
    "snap": "full",
    "full": "full",
    "greeks": "option_greeks",
    "option_greeks": "option_greeks",
}

# Capacity warning threshold (instruments per connection)
_MAX_INSTRUMENTS_BASIC = 1500
_MAX_INSTRUMENTS_PRO = 5000

# ───────────────────────────────────────────────────────────────────────
# PROTOBUF SCHEMA — inline descriptor, no compiled _pb2 required
# ───────────────────────────────────────────────────────────────────────
# We use google.protobuf's runtime descriptor API to parse the schema at
# module import time. This avoids the need for a compiled _pb2.py file.

_PROTO_SCHEMA = """
syntax = "proto3";
package com.upstox.marketdatafeeder.rpc.proto;

message FeedResponse {
  string type = 1;
  map<string, Feed> feeds = 2;
}

message Feed {
  LTPC ltpc = 1;
  FullFeed ff = 2;
  OptionGreeks og = 3;
}

message LTPC {
  double ltp = 1;
  double close = 2;
  double change = 3;
  double change_percent = 4;
}

message FullFeed {
  OHLC ohlc = 1;
  MarketDepth depth = 2;
  int64 volume = 3;
  int64 oi = 4;
  double avg_price = 5;
  int64 total_buy_qty = 6;
  int64 total_sell_qty = 7;
}

message OHLC {
  double open = 1;
  double high = 2;
  double low = 3;
  double close = 4;
}

message MarketDepth {
  repeated Level bid = 1;
  repeated Level ask = 2;
}

message Level {
  double price = 1;
  int64 quantity = 2;
  int64 orders = 3;
}

message OptionGreeks {
  double delta = 1;
  double gamma = 2;
  double theta = 3;
  double vega = 4;
  double iv = 5;
}
"""


def _build_proto_classes():
    """
    Build protobuf message classes from inline schema at runtime.

    Returns the FeedResponse class, or None if protobuf is unavailable.
    This avoids the need for a compiled _pb2.py — the descriptor is built
    from the embedded string schema using google.protobuf's descriptor_pool.
    """
    try:
        from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
        from google.protobuf.descriptor_pool import DescriptorPool

        # Parse the .proto text into a FileDescriptorProto
        file_proto = descriptor_pb2.FileDescriptorProto()
        from google.protobuf import text_format as _tf
        # Use descriptor_pool to add the file
        pool = DescriptorPool()

        # Parse the schema string into a FileDescriptorProto using descriptor_pb2
        # We use protoc-style parsing via google.protobuf.descriptor_pb2
        from google.protobuf.descriptor import FieldDescriptor  # noqa — validate import

        # Manually parse the proto schema without protoc
        # Use google.protobuf.descriptor_pb2 + message factory (runtime approach)
        _parse_proto_schema(file_proto)
        pool.Add(file_proto)

        factory = message_factory.MessageFactory(pool=pool)
        desc = pool.FindMessageTypeByName(
            "com.upstox.marketdatafeeder.rpc.proto.FeedResponse"
        )
        FeedResponse = factory.GetPrototype(desc)
        logger.info("[Upstox] Protobuf FeedResponse class built successfully")
        return FeedResponse
    except Exception as e:
        logger.warning(
            "[Upstox] Could not build protobuf classes: %s — will use fallback", e
        )
        return None


def _parse_proto_schema(file_proto):
    """
    Populate a FileDescriptorProto from the inline _PROTO_SCHEMA string.

    Rather than using protoc or text_format (which requires descriptor.proto),
    we build the FileDescriptorProto programmatically. This is the most portable
    approach for runtime-only protobuf usage.
    """
    from google.protobuf import descriptor_pb2

    pkg = "com.upstox.marketdatafeeder.rpc.proto"
    file_proto.name = "upstox_market_data_feed.proto"
    file_proto.package = pkg
    file_proto.syntax = "proto3"

    # Helper to add a message descriptor with named fields
    def add_msg(name, fields):
        """fields: list of (field_name, field_number, field_type, label, type_name=None)"""
        from google.protobuf.descriptor_pb2 import FieldDescriptorProto as FDP
        msg = file_proto.message_type.add()
        msg.name = name
        for fname, fnum, ftype, flabel, *rest in fields:
            f = msg.field.add()
            f.name = fname
            f.number = fnum
            f.type = ftype
            f.label = flabel
            if rest and rest[0]:
                f.type_name = f".{pkg}.{rest[0]}"
            if len(rest) > 1 and rest[1]:
                f.json_name = rest[1]
        return msg

    FDP = descriptor_pb2.FieldDescriptorProto
    TYPE_DOUBLE = FDP.TYPE_DOUBLE
    TYPE_INT64 = FDP.TYPE_INT64
    TYPE_STRING = FDP.TYPE_STRING
    TYPE_MESSAGE = FDP.TYPE_MESSAGE
    LABEL_OPTIONAL = FDP.LABEL_OPTIONAL
    LABEL_REPEATED = FDP.LABEL_REPEATED

    # ── Level ──
    add_msg("Level", [
        ("price", 1, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("quantity", 2, TYPE_INT64, LABEL_OPTIONAL),
        ("orders", 3, TYPE_INT64, LABEL_OPTIONAL),
    ])

    # ── OHLC ──
    add_msg("OHLC", [
        ("open", 1, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("high", 2, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("low", 3, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("close", 4, TYPE_DOUBLE, LABEL_OPTIONAL),
    ])

    # ── LTPC ──
    add_msg("LTPC", [
        ("ltp", 1, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("close", 2, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("change", 3, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("change_percent", 4, TYPE_DOUBLE, LABEL_OPTIONAL),
    ])

    # ── MarketDepth ──
    add_msg("MarketDepth", [
        ("bid", 1, TYPE_MESSAGE, LABEL_REPEATED, "Level"),
        ("ask", 2, TYPE_MESSAGE, LABEL_REPEATED, "Level"),
    ])

    # ── OptionGreeks ──
    add_msg("OptionGreeks", [
        ("delta", 1, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("gamma", 2, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("theta", 3, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("vega", 4, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("iv", 5, TYPE_DOUBLE, LABEL_OPTIONAL),
    ])

    # ── FullFeed ──
    add_msg("FullFeed", [
        ("ohlc", 1, TYPE_MESSAGE, LABEL_OPTIONAL, "OHLC"),
        ("depth", 2, TYPE_MESSAGE, LABEL_OPTIONAL, "MarketDepth"),
        ("volume", 3, TYPE_INT64, LABEL_OPTIONAL),
        ("oi", 4, TYPE_INT64, LABEL_OPTIONAL),
        ("avg_price", 5, TYPE_DOUBLE, LABEL_OPTIONAL),
        ("total_buy_qty", 6, TYPE_INT64, LABEL_OPTIONAL),
        ("total_sell_qty", 7, TYPE_INT64, LABEL_OPTIONAL),
    ])

    # ── Feed ──
    add_msg("Feed", [
        ("ltpc", 1, TYPE_MESSAGE, LABEL_OPTIONAL, "LTPC"),
        ("ff", 2, TYPE_MESSAGE, LABEL_OPTIONAL, "FullFeed"),
        ("og", 3, TYPE_MESSAGE, LABEL_OPTIONAL, "OptionGreeks"),
    ])

    # ── FeedResponse ── (has a map field — needs special handling)
    # Protobuf maps are represented as repeated message with key/value fields
    # We use descriptor_pb2 map_entry pattern
    resp_msg = file_proto.message_type.add()
    resp_msg.name = "FeedResponse"

    # type field
    type_f = resp_msg.field.add()
    type_f.name = "type"
    type_f.number = 1
    type_f.type = TYPE_STRING
    type_f.label = LABEL_OPTIONAL

    # feeds map<string, Feed> — represented as a nested MapEntry message
    map_entry = resp_msg.nested_type.add()
    map_entry.name = "FeedsEntry"
    map_entry.options.CopyFrom(descriptor_pb2.MessageOptions())
    map_entry.options.map_entry = True

    key_f = map_entry.field.add()
    key_f.name = "key"
    key_f.number = 1
    key_f.type = TYPE_STRING
    key_f.label = LABEL_OPTIONAL

    val_f = map_entry.field.add()
    val_f.name = "value"
    val_f.number = 2
    val_f.type = TYPE_MESSAGE
    val_f.label = LABEL_OPTIONAL
    val_f.type_name = f".{pkg}.Feed"

    feeds_f = resp_msg.field.add()
    feeds_f.name = "feeds"
    feeds_f.number = 2
    feeds_f.type = TYPE_MESSAGE
    feeds_f.label = LABEL_REPEATED
    feeds_f.type_name = f".{pkg}.FeedResponse.FeedsEntry"


# Build the FeedResponse class at import time (None if protobuf unavailable)
_FeedResponse = _build_proto_classes()


class UpstoxTickerAdapter(TickerAdapter):
    """
    Upstox WebSocket ticker adapter (Protobuf, asyncio-native).

    Platform failover rank: #5
    Cost: ₹499/month
    Capacity: ~1,500 tokens (basic plan)

    Protocol model (asyncio-native — same as Dhan):
    - Calls REST to get an authorized WebSocket URL
    - Connects via `websockets` library in an async receive loop
    - No daemon thread needed — _ws_receive_loop() is a long-running coroutine
    - Protobuf frames → _parse_protobuf() → _dispatch_async()

    Token mapping:
    - canonical Kite token (int) → Upstox instrument_key string
      e.g. 256265 → "NSE_INDEX|Nifty 50"
    - Upstox instrument_key string → canonical Kite token (int)
    - Must be pre-loaded via load_token_map() before subscribing
    """

    def __init__(self, broker_type: str = "upstox"):
        super().__init__(broker_type)
        self._ws = None                            # websockets.WebSocketClientProtocol
        self._receive_task: Optional[asyncio.Task] = None

        # Token mapping caches (loaded before first subscribe)
        # canonical Kite token (int) → Upstox instrument_key string
        self._canonical_to_instrument_key: Dict[int, str] = {}
        # Upstox instrument_key string → canonical Kite token (int)
        self._instrument_key_to_canonical: Dict[str, int] = {}

        # Credentials stored for reconnect
        self._access_token: str = ""
        self._api_key: str = ""

        # Current authorized WebSocket URL (fetched via REST before each connect)
        self._authorized_ws_url: Optional[str] = None

        # Current subscription mode (Upstox mode string)
        self._current_upstox_mode: str = "full"

    # ═══════════════════════════════════════════════════════════════════════
    # TOKEN MAP MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def load_token_map(self, mapping: Dict[int, str]) -> None:
        """
        Pre-load canonical ↔ Upstox instrument_key mappings.

        Called before subscribing. The TickerPool or startup code loads this
        from the broker_instrument_tokens DB table (async) and passes it here.

        Args:
            mapping: {canonical_token: instrument_key_str}
                     e.g. {256265: "NSE_INDEX|Nifty 50",
                            260105: "NSE_INDEX|Nifty Bank",
                            12345678: "NSE_FO|43854"}
        """
        for canonical, instrument_key in mapping.items():
            self._canonical_to_instrument_key[canonical] = instrument_key
            self._instrument_key_to_canonical[instrument_key] = canonical
        logger.info("[Upstox] Loaded %d token mappings", len(mapping))

    # ═══════════════════════════════════════════════════════════════════════
    # REST — AUTHORIZED WebSocket URL
    # ═══════════════════════════════════════════════════════════════════════

    async def _fetch_authorized_ws_url(self) -> str:
        """
        Call Upstox REST to get an authorized WebSocket URL.

        GET /v2/feed/market-data-feed/authorize
        Authorization: Bearer {access_token}

        Returns:
            Authorized WebSocket URL string (wss://ws.upstox.com/...)

        Raises:
            ConnectionError: if REST call fails or returns unexpected response
        """
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(_REST_AUTHORIZE_URL, headers=headers)
            if resp.status_code != 200:
                error_msg = (
                    f"[Upstox] Failed to get authorized WS URL "
                    f"(HTTP {resp.status_code}): {resp.text}"
                )
                if resp.status_code == 401:
                    self._report_auth_error("UDAPI100050", error_msg)
                else:
                    self._report_error("http_error", error_msg)
                raise ConnectionError(error_msg)
            data = resp.json()

        try:
            authorized_url = data["data"]["authorized_redirect_uri"]
        except (KeyError, TypeError) as e:
            raise ConnectionError(
                f"[Upstox] Unexpected authorize response structure: {data} — {e}"
            )

        logger.info("[Upstox] Got authorized WebSocket URL")
        return authorized_url

    # ═══════════════════════════════════════════════════════════════════════
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════════════════

    async def _connect_ws(self, credentials: dict) -> None:
        """
        Connect to Upstox MarketDataFeedV3 WebSocket.

        Steps:
        1. Extract credentials
        2. Optionally pre-load token mappings
        3. Call REST to get authorized WS URL
        4. Connect to authorized WS URL
        5. Start background receive loop

        Args:
            credentials: {
                "api_key": str,         # Upstox API key
                "access_token": str,    # OAuth access_token or extended_token
                "token_map": optional dict for load_token_map (canonical → instrument_key)
            }
        """
        import websockets

        self._api_key = credentials.get("api_key", "")
        self._access_token = credentials["access_token"]

        # Optional: pre-load token mappings from credentials
        token_map = credentials.get("token_map")
        if token_map:
            self.load_token_map(token_map)

        logger.info("[Upstox] Fetching authorized WebSocket URL...")
        self._authorized_ws_url = await self._fetch_authorized_ws_url()

        logger.info("[Upstox] Connecting WebSocket...")

        # Connect — Upstox auth is embedded in the authorized URL (no extra headers)
        self._ws = await websockets.connect(
            self._authorized_ws_url,
            ping_interval=30,    # Keep-alive pings every 30s
            ping_timeout=10,
        )

        # Start background receive loop
        self._receive_task = asyncio.create_task(
            self._ws_receive_loop(),
            name="Upstox-WS-Receive",
        )

        logger.info("[Upstox] WebSocket connected")

    async def _disconnect_ws(self) -> None:
        """Disconnect from Upstox WebSocket."""
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
                logger.warning("[Upstox] Disconnect error: %s", e)
            self._ws = None

        self._authorized_ws_url = None
        logger.info("[Upstox] WebSocket disconnected")

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        """
        Subscribe to Upstox instruments via JSON subscription message.

        Upstox subscription message format (JSON, sent as text):
            {
                "guid": "<unique_id>",
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": ["NSE_FO|12345", "NSE_INDEX|Nifty 50"]
                }
            }

        Args:
            broker_tokens: List of Upstox instrument_key strings
                           e.g. ["NSE_FO|12345", "NSE_INDEX|Nifty 50"]
            mode: internal mode string — mapped to Upstox mode via _MODE_TO_UPSTOX
        """
        if not self._ws:
            raise ConnectionError("[Upstox] WebSocket not connected")

        if not broker_tokens:
            return

        upstox_mode = _MODE_TO_UPSTOX.get(mode, "full")
        self._current_upstox_mode = upstox_mode

        if len(broker_tokens) > _MAX_INSTRUMENTS_BASIC:
            logger.warning(
                "[Upstox] %d tokens requested — basic plan supports ~%d/connection",
                len(broker_tokens), _MAX_INSTRUMENTS_BASIC,
            )

        msg = {
            "guid": f"upstox-sub-{id(broker_tokens)}",
            "method": "sub",
            "data": {
                "mode": upstox_mode,
                "instrumentKeys": list(broker_tokens),
            },
        }

        await self._ws.send(json.dumps(msg))
        logger.info(
            "[Upstox] Subscribed to %d instruments (mode=%s)",
            len(broker_tokens), upstox_mode,
        )

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        """
        Unsubscribe from Upstox instruments.

        Args:
            broker_tokens: List of Upstox instrument_key strings
        """
        if not self._ws:
            return

        if not broker_tokens:
            return

        msg = {
            "guid": f"upstox-unsub-{id(broker_tokens)}",
            "method": "unsub",
            "data": {
                "mode": self._current_upstox_mode,
                "instrumentKeys": list(broker_tokens),
            },
        }

        await self._ws.send(json.dumps(msg))
        logger.info("[Upstox] Unsubscribed from %d instruments", len(broker_tokens))

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Convert canonical Kite tokens to Upstox instrument_key strings.

        Args:
            canonical_tokens: [256265, 260105, ...]

        Returns:
            ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank", ...]
        """
        result = []
        for canonical_token in canonical_tokens:
            instrument_key = self._canonical_to_instrument_key.get(canonical_token)
            if instrument_key is None:
                logger.warning(
                    "[Upstox] No instrument_key for canonical token %d — skipping",
                    canonical_token,
                )
                continue
            result.append(instrument_key)
        return result

    def _get_canonical_token(self, broker_token: Any) -> int:
        """
        Convert Upstox instrument_key string to canonical Kite token.

        Args:
            broker_token: Upstox instrument_key string (e.g. "NSE_FO|12345")

        Returns:
            Canonical Kite instrument token (e.g. 256265), or 0 if unknown
        """
        if not isinstance(broker_token, str):
            logger.warning("[Upstox] Expected string instrument_key, got: %r", broker_token)
            return 0

        canonical = self._instrument_key_to_canonical.get(broker_token)
        if canonical is None:
            logger.warning("[Upstox] Unknown instrument_key: %s", broker_token)
            return 0
        return canonical

    def _parse_tick(self, raw_data: Any) -> List[NormalizedTick]:
        """
        Parse Upstox Protobuf binary frame into NormalizedTick list.

        raw_data is a bytes object containing a serialized FeedResponse.
        Falls back to JSON parsing if Protobuf is unavailable and the
        message is text (edge case for error/control messages).
        """
        if isinstance(raw_data, (bytes, bytearray)):
            return self._parse_protobuf(bytes(raw_data))
        # Text frames are control messages (not tick data)
        return []

    # ═══════════════════════════════════════════════════════════════════════
    # PROTOBUF PARSER
    # ═══════════════════════════════════════════════════════════════════════

    def _parse_protobuf(self, data: bytes) -> List[NormalizedTick]:
        """
        Deserialize a Protobuf FeedResponse binary frame into NormalizedTick list.

        Each key in FeedResponse.feeds is an instrument_key string; each value
        is a Feed message containing ltpc, ff (FullFeed), and/or og (OptionGreeks).
        """
        if not data:
            return []

        if _FeedResponse is None:
            logger.warning(
                "[Upstox] protobuf library not available — cannot parse binary frame"
            )
            return []

        try:
            feed_response = _FeedResponse()
            feed_response.ParseFromString(data)
        except Exception as e:
            logger.error("[Upstox] Protobuf parse error (len=%d): %s", len(data), e)
            return []

        # type field: "live_feed" for live data, "disconnected" etc. for control
        msg_type = feed_response.type
        if msg_type and msg_type != "live_feed":
            logger.debug("[Upstox] Non-tick message type: %s", msg_type)
            return []

        ticks: List[NormalizedTick] = []
        now = datetime.now()

        for instrument_key, feed in feed_response.feeds.items():
            tick = self._feed_to_tick(instrument_key, feed, now)
            if tick is not None:
                ticks.append(tick)

        return ticks

    def _feed_to_tick(
        self,
        instrument_key: str,
        feed: Any,
        fallback_ts: datetime,
    ) -> Optional[NormalizedTick]:
        """
        Convert a single Upstox Feed protobuf message to NormalizedTick.

        Args:
            instrument_key: e.g. "NSE_FO|12345"
            feed: protobuf Feed message (has ltpc, ff, og fields)
            fallback_ts: datetime to use if no server timestamp available

        Returns:
            NormalizedTick, or None if instrument_key is unknown or ltpc missing
        """
        canonical_token = self._get_canonical_token(instrument_key)
        if canonical_token == 0:
            return None

        # ── LTPC (always present) ──
        if not feed.HasField("ltpc"):
            logger.debug("[Upstox] No ltpc for %s — skipping", instrument_key)
            return None

        ltpc = feed.ltpc
        ltp = Decimal(str(round(ltpc.ltp, 2)))
        close = Decimal(str(round(ltpc.close, 2)))
        change = Decimal(str(round(ltpc.change, 2)))
        change_percent = Decimal(str(round(ltpc.change_percent, 4)))

        # ── FullFeed (present in full / option_greeks mode) ──
        open_price = Decimal("0")
        high = Decimal("0")
        low = Decimal("0")
        volume = 0
        oi = 0
        bid: Optional[Decimal] = None
        ask: Optional[Decimal] = None
        bid_qty: Optional[int] = None
        ask_qty: Optional[int] = None

        if feed.HasField("ff"):
            ff = feed.ff
            volume = int(ff.volume)
            oi = int(ff.oi)

            if ff.HasField("ohlc"):
                ohlc = ff.ohlc
                open_price = Decimal(str(round(ohlc.open, 2)))
                high = Decimal(str(round(ohlc.high, 2)))
                low = Decimal(str(round(ohlc.low, 2)))
                # OHLC.close and LTPC.close should match; prefer OHLC.close
                if ohlc.close:
                    close = Decimal(str(round(ohlc.close, 2)))

            if ff.HasField("depth"):
                depth = ff.depth
                if depth.bid:
                    best_bid = depth.bid[0]
                    if best_bid.price > 0:
                        bid = Decimal(str(round(best_bid.price, 2)))
                        bid_qty = int(best_bid.quantity)
                if depth.ask:
                    best_ask = depth.ask[0]
                    if best_ask.price > 0:
                        ask = Decimal(str(round(best_ask.price, 2)))
                        ask_qty = int(best_ask.quantity)

        # Recalculate change from Decimal to avoid float precision drift
        if close != 0:
            change = ltp - close
            change_percent = (change / close * 100).quantize(Decimal("0.0001"))

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
            timestamp=fallback_ts,
            broker_type=self.broker_type,
            bid=bid,
            ask=ask,
            bid_qty=bid_qty,
            ask_qty=ask_qty,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # ASYNCIO RECEIVE LOOP
    # ═══════════════════════════════════════════════════════════════════════

    async def _ws_receive_loop(self) -> None:
        """
        Main asyncio receive loop for Upstox WebSocket Protobuf frames.

        Runs as an asyncio.Task until disconnect. Dispatches parsed ticks
        directly via _dispatch_async (no thread bridging needed).
        """
        import websockets.exceptions

        logger.info("[Upstox] Receive loop started")
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    ticks = self._parse_protobuf(message)
                    if ticks:
                        await self._dispatch_async(ticks)
                else:
                    # Text control frames (e.g. connection acknowledgment, errors)
                    try:
                        payload = json.loads(message)
                        logger.debug("[Upstox] Text control message: %s", payload)
                    except json.JSONDecodeError:
                        logger.debug(
                            "[Upstox] Non-JSON text message: %s", message[:100]
                        )

        except asyncio.CancelledError:
            logger.info("[Upstox] Receive loop cancelled (graceful disconnect)")
            raise  # Re-raise so the task completes cleanly

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning("[Upstox] WebSocket connection closed: %s", e)
            self._report_error("connection_closed", str(e))
            self._connected = False

        except Exception as e:
            logger.error("[Upstox] Receive loop error: %s", e, exc_info=True)
            self._report_error("receive_loop_error", str(e))
            self._connected = False

        logger.info("[Upstox] Receive loop ended")
