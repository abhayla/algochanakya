"""
Fyers Ticker Adapter

FyersDataSocket v3 implementation using fyers-apiv3 SDK.

Key characteristics:
- Threading model: keep_running() blocks — run on daemon thread (same as SmartAPI/Kite)
  Callbacks (on_message, on_error, on_close, on_open) execute on that thread.
  Bridge to asyncio via _dispatch_from_thread.
- Token format: NSE:{SYMBOL} string — canonical Kite token (int) mapped via _canonical_to_broker
- Price normalization: RUPEES (no paise conversion needed)
- Connection limits: 5,000 symbols/connection (v3.0.0, Feb 2026 upgrade)
- Auth: OAuth 2.0, token expires at MIDNIGHT IST daily
- Auth format: {app_id}:{access_token} (colon-separated, NOT standard Bearer)
- Data types: "SymbolUpdate" (default) or "DepthUpdate" (5-level depth)
- Tick message type field: "sf" (SymbolUpdate) or "dp" (DepthUpdate)

Credentials dict expected:
    {
        "app_id": str,          # Fyers app ID (e.g., "ABC123-100")
        "access_token": str,    # OAuth access token (expires midnight IST)
    }
"""

import asyncio
import logging
import threading
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..adapter_base import TickerAdapter
from ..models import NormalizedTick

logger = logging.getLogger(__name__)

# Mode → Fyers data_type string
_MODE_TO_DATA_TYPE = {
    "ltp": "SymbolUpdate",    # litemode=True would give LTP only, but we use full mode
    "quote": "SymbolUpdate",  # SymbolUpdate includes OHLCV + OI
    "snap": "SymbolUpdate",
    "depth": "DepthUpdate",   # Adds 5-level bid/ask depth
    "full": "DepthUpdate",
}

# Index symbol mapping: canonical symbol → Fyers NSE: format
# These don't follow the simple NSE:{canonical} pattern
_INDEX_MAP: Dict[str, str] = {
    "NIFTY 50": "NSE:NIFTY50-INDEX",
    "NIFTY50": "NSE:NIFTY50-INDEX",
    "NIFTY BANK": "NSE:NIFTYBANK-INDEX",
    "BANKNIFTY": "NSE:NIFTYBANK-INDEX",
    "NIFTY FIN SERVICE": "NSE:NIFTYFINSERVICE-INDEX",
    "FINNIFTY": "NSE:NIFTYFINSERVICE-INDEX",
    "SENSEX": "BSE:SENSEX-INDEX",
}


class FyersTickerAdapter(TickerAdapter):
    """
    Fyers WebSocket ticker adapter (FyersDataSocket v3).

    Platform failover rank: #3
    Cost: FREE
    Capacity: 5,000 symbols/connection (v3.0.0, Feb 2026)

    Threading pattern (same as SmartAPI/Kite — do not modify):
    - FyersDataSocket.keep_running() blocks on a daemon thread
    - Callbacks (on_message, on_error, on_close, on_open) execute on that thread
    - Use _dispatch_from_thread() to bridge ticks to the asyncio event loop

    Token mapping:
    - canonical Kite token (int) → Fyers symbol string (e.g., "NSE:NIFTY2522725000CE")
    - Fyers symbol string → canonical Kite token (int)
    - Must be pre-loaded via load_token_map() before subscribing
    """

    def __init__(self, broker_type: str = "fyers"):
        super().__init__(broker_type)
        self._data_socket = None  # FyersDataSocket instance
        self._ws_thread: Optional[threading.Thread] = None

        # Connection event — signalled by on_open on the WS thread
        self._ws_connected_event = threading.Event()

        # Token mapping caches (loaded before first subscribe)
        # canonical Kite token (int) → Fyers symbol string (e.g., "NSE:NIFTY2522725000CE")
        self._canonical_to_broker: Dict[int, str] = {}
        # Fyers symbol string → canonical Kite token (int)
        self._broker_to_canonical: Dict[str, int] = {}

        # Current data_type for this connection (set at connect time)
        self._data_type: str = "SymbolUpdate"

    # ═══════════════════════════════════════════════════════════════════════
    # TOKEN MAP MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def load_token_map(self, mapping: Dict[int, str]) -> None:
        """
        Pre-load canonical ↔ broker token mappings.

        Called before subscribing. The TickerPool or startup code loads this
        from the broker_instrument_tokens DB table (async) and passes it here.

        Args:
            mapping: {canonical_token: fyers_symbol}
                     e.g. {256265: "NSE:NIFTY50-INDEX", 260105: "NSE:NIFTYBANK-INDEX",
                           12345678: "NSE:NIFTY2522725000CE"}
        """
        for canonical, fyers_symbol in mapping.items():
            self._canonical_to_broker[canonical] = fyers_symbol
            self._broker_to_canonical[fyers_symbol] = canonical
        logger.info("[Fyers] Loaded %d token mappings", len(mapping))

    # ═══════════════════════════════════════════════════════════════════════
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════════════════

    async def _connect_ws(self, credentials: dict) -> None:
        """
        Connect to Fyers DataSocket v3.

        Args:
            credentials: {
                "app_id": str,        # Fyers app ID (e.g., "ABC123-100")
                "access_token": str,  # OAuth access token (expires midnight IST)
                "token_map": optional dict for load_token_map
            }
        """
        from fyers_apiv3.FyersWebsocket import data_ws

        app_id = credentials["app_id"]
        access_token = credentials["access_token"]

        # Fyers auth format: "{app_id}:{access_token}" (NOT Bearer)
        fyers_access_token = f"{app_id}:{access_token}"

        # Optional: pre-load token mappings from credentials
        token_map = credentials.get("token_map")
        if token_map:
            self.load_token_map(token_map)

        logger.info("[Fyers] Connecting WebSocket for app_id: %s", app_id)

        # Reset connection event
        self._ws_connected_event.clear()

        # Create FyersDataSocket instance
        # litemode=False → full SymbolUpdate data (OHLCV + OI + bid/ask)
        # reconnect=True → auto-reconnect on disconnect (handled by SDK)
        self._data_socket = data_ws.FyersDataSocket(
            access_token=fyers_access_token,
            log_path="",
            litemode=False,
            write_to_file=False,
            reconnect=True,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )

        # Start keep_running() in daemon thread (CRITICAL: blocks indefinitely)
        self._ws_thread = threading.Thread(
            target=self._run_ws,
            daemon=True,
            name="Fyers-WS-Thread",
        )
        self._ws_thread.start()

        # Wait for WS connection with timeout
        connected = await asyncio.get_event_loop().run_in_executor(
            None, self._ws_connected_event.wait, 15.0  # 15s timeout (Fyers can be slow)
        )
        if not connected:
            raise ConnectionError("[Fyers] WebSocket connection timed out after 15s")

        logger.info("[Fyers] WebSocket connected for app_id: %s", app_id)

    def _run_ws(self) -> None:
        """Run FyersDataSocket.keep_running() on the daemon thread."""
        try:
            self._data_socket.keep_running()
        except Exception as e:
            logger.error("[Fyers] WebSocket thread error: %s", e)

    async def _disconnect_ws(self) -> None:
        """Disconnect from Fyers WebSocket."""
        if self._data_socket:
            try:
                self._data_socket.close_connection()
            except Exception as e:
                logger.warning("[Fyers] Disconnect error: %s", e)
            self._data_socket = None
        self._ws_connected_event.clear()
        logger.info("[Fyers] WebSocket disconnected")

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        """
        Subscribe to Fyers symbols.

        Args:
            broker_tokens: List of Fyers symbol strings
                           e.g. ["NSE:NIFTY2522725000CE", "NSE:NIFTY50-INDEX"]
            mode: 'ltp', 'quote', 'snap', 'depth', or 'full'
        """
        if not self._data_socket:
            raise ConnectionError("[Fyers] WebSocket not connected")

        if not broker_tokens:
            return

        data_type = _MODE_TO_DATA_TYPE.get(mode, "SymbolUpdate")
        self._data_type = data_type

        logger.debug("[Fyers] Subscribing: %d symbols (data_type=%s)", len(broker_tokens), data_type)
        self._data_socket.subscribe(symbols=broker_tokens, data_type=data_type)
        logger.info("[Fyers] Subscribed to %d symbols (data_type=%s)", len(broker_tokens), data_type)

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        """
        Unsubscribe from Fyers symbols.

        Args:
            broker_tokens: List of Fyers symbol strings
        """
        if not self._data_socket:
            return

        if not broker_tokens:
            return

        # Unsubscribe from the current data_type
        self._data_socket.unsubscribe(symbols=broker_tokens, data_type=self._data_type)
        logger.info("[Fyers] Unsubscribed from %d symbols", len(broker_tokens))

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Convert canonical Kite tokens to Fyers symbol strings.

        Args:
            canonical_tokens: [256265, 260105, ...]

        Returns:
            ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", ...]
        """
        result = []
        for canonical_token in canonical_tokens:
            fyers_symbol = self._canonical_to_broker.get(canonical_token)
            if fyers_symbol is None:
                logger.warning(
                    "[Fyers] No broker token for canonical %d — skipping",
                    canonical_token,
                )
                continue
            result.append(fyers_symbol)
        return result

    def _get_canonical_token(self, broker_token: Any) -> int:
        """
        Convert Fyers symbol string to canonical Kite token.

        Args:
            broker_token: Fyers symbol string (e.g., "NSE:NIFTY2522725000CE")

        Returns:
            Canonical Kite instrument token (e.g., 256265), or 0 if unknown
        """
        canonical = self._broker_to_canonical.get(str(broker_token))
        if canonical is None:
            logger.warning("[Fyers] Unknown broker symbol: %s", broker_token)
            return 0
        return canonical

    def _parse_tick(self, raw_data: Any) -> List[NormalizedTick]:
        """
        Parse Fyers JSON tick dict into NormalizedTick.

        Fyers SymbolUpdate message structure:
        {
            "symbol": "NSE:NIFTY2522725000CE",
            "fyToken": "101010000012345",
            "timestamp": 1709119800,         # Unix epoch seconds
            "ltp": 150.25,                   # Already RUPEES (no paise conversion)
            "open_price": 145.00,
            "high_price": 155.50,
            "low_price": 142.00,
            "prev_close_price": 148.75,      # Previous close
            "ch": 1.50,                      # Change (rupees)
            "chp": 1.01,                     # Change percent
            "vol_traded_today": 1250000,
            "bid_price": 150.20,
            "bid_size": 500,
            "ask_price": 150.30,
            "ask_size": 400,
            "oi": 500000,
            "type": "sf"                     # "sf"=SymbolUpdate, "dp"=DepthUpdate
        }

        Returns:
            List with a single NormalizedTick, or empty list on error
        """
        try:
            fyers_symbol = raw_data.get("symbol")
            if not fyers_symbol:
                return []

            canonical_token = self._get_canonical_token(fyers_symbol)
            if canonical_token == 0:
                return []

            # All prices are already in RUPEES — convert to Decimal for precision
            ltp = Decimal(str(raw_data.get("ltp", 0)))
            open_price = Decimal(str(raw_data.get("open_price", 0)))
            high = Decimal(str(raw_data.get("high_price", 0)))
            low = Decimal(str(raw_data.get("low_price", 0)))
            close = Decimal(str(raw_data.get("prev_close_price", 0)))

            # Fyers provides pre-calculated change fields — use them
            # but recalculate from Decimal to avoid float precision issues
            change = ltp - close
            change_percent = (change / close * 100) if close != 0 else Decimal("0")

            volume = raw_data.get("vol_traded_today", 0) or 0
            oi = raw_data.get("oi", 0) or 0

            # Convert unix timestamp to datetime (Fyers sends epoch seconds)
            ts = raw_data.get("timestamp") or raw_data.get("last_traded_time")
            if ts:
                try:
                    timestamp = datetime.fromtimestamp(int(ts))
                except (ValueError, OSError, OverflowError):
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()

            # Bid/ask (present in SymbolUpdate)
            bid_price_raw = raw_data.get("bid_price")
            ask_price_raw = raw_data.get("ask_price")
            bid = Decimal(str(bid_price_raw)) if bid_price_raw is not None else None
            ask = Decimal(str(ask_price_raw)) if ask_price_raw is not None else None
            bid_qty = raw_data.get("bid_size")
            ask_qty = raw_data.get("ask_size")

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
                bid_qty=int(bid_qty) if bid_qty is not None else None,
                ask_qty=int(ask_qty) if ask_qty is not None else None,
            )

            return [tick]

        except Exception as e:
            logger.error("[Fyers] Tick parsing error: %s", e, exc_info=True)
            return []

    # ═══════════════════════════════════════════════════════════════════════
    # FyersDataSocket CALLBACKS (run on WS daemon thread)
    # ═══════════════════════════════════════════════════════════════════════

    def _on_open(self) -> None:
        """Callback when WebSocket connection opens (WS thread)."""
        logger.info("[Fyers] WebSocket connected")
        self._ws_connected_event.set()

    def _on_message(self, message: Any) -> None:
        """
        Callback when tick data arrives (WS thread).

        Fyers SDK pre-parses JSON → delivers message as a dict.
        CRITICAL: bridges to asyncio via _dispatch_from_thread.
        """
        try:
            # SDK may deliver list of dicts or a single dict
            if isinstance(message, list):
                normalized: List[NormalizedTick] = []
                for item in message:
                    normalized.extend(self._parse_tick(item))
                if normalized:
                    self._dispatch_from_thread(normalized)
            elif isinstance(message, dict):
                ticks = self._parse_tick(message)
                if ticks:
                    self._dispatch_from_thread(ticks)
        except Exception as e:
            logger.error("[Fyers] on_message error: %s", e, exc_info=True)

    def _on_error(self, message: Any) -> None:
        """Callback on WebSocket error (WS thread)."""
        logger.error("[Fyers] WebSocket error: %s", message)
        msg_str = str(message) if message else ""
        if "invalid_token" in msg_str.lower() or "-16" in msg_str:
            self._report_auth_error("invalid_token", msg_str)
        else:
            self._report_error("websocket_error", msg_str)

    def _on_close(self, message: Any) -> None:
        """Callback when WebSocket closes (WS thread)."""
        logger.warning("[Fyers] WebSocket closed: %s", message)
        self._report_error("connection_closed", str(message) if message else "")
        self._ws_connected_event.clear()
        self._connected = False
