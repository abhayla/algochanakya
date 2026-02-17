"""
Kite Connect (Zerodha) Ticker Adapter

WebSocket implementation using KiteTicker from kiteconnect library.

Key characteristics:
- Threading model: KiteTicker manages its own thread (connect(threaded=True))
- Callbacks execute on KiteTicker's thread → bridge to asyncio via _dispatch_from_thread
- Token format: Integer — identical to canonical Kite tokens (no mapping needed)
- Price normalization: None — kiteconnect library returns prices in rupees
- on_ticks receives a LIST of tick dicts (batched delivery)
- Subscribe + set_mode are separate calls
"""

import asyncio
import logging
import threading
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..adapter_base import TickerAdapter
from ..models import NormalizedTick

logger = logging.getLogger(__name__)


class KiteTickerAdapter(TickerAdapter):
    """
    Kite Connect WebSocket ticker adapter.

    Threading pattern (CRITICAL — do not modify):
    - KiteTicker runs on its own internal thread (connect(threaded=True))
    - Callbacks (_on_ticks, _on_connect, _on_close, _on_error) execute on that thread
    - Use _dispatch_from_thread() to bridge ticks to the asyncio event loop

    Token identity:
    - Kite instrument_token (int) IS the canonical token format
    - No token translation needed — _translate_to_broker_tokens is identity
    - No token map pre-loading required
    """

    # KiteTicker subscription modes (mapped from our standard mode names)
    MODES = {
        "ltp": "ltp",
        "quote": "quote",
        "full": "full",
    }

    def __init__(self, broker_type: str = "kite"):
        super().__init__(broker_type)
        self.kws = None  # KiteTicker instance
        self._ws_connected_event = threading.Event()

    # ═══════════════════════════════════════════════════════════════════════
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════════════════

    async def _connect_ws(self, credentials: dict) -> None:
        """
        Connect to Kite WebSocket.

        Args:
            credentials: {
                "api_key": str,
                "access_token": str,
            }
        """
        from kiteconnect import KiteTicker

        api_key = credentials["api_key"]
        access_token = credentials["access_token"]

        logger.info("[Kite] Connecting WebSocket...")

        # Reset connection event
        self._ws_connected_event.clear()

        # Create KiteTicker instance
        self.kws = KiteTicker(
            api_key=api_key,
            access_token=access_token,
        )

        # Set callbacks (execute on KiteTicker's internal thread)
        self.kws.on_ticks = self._on_ticks
        self.kws.on_connect = self._on_connect
        self.kws.on_close = self._on_close
        self.kws.on_error = self._on_error
        self.kws.on_reconnect = self._on_reconnect

        # Start WS in threaded mode (KiteTicker manages its own thread)
        self.kws.connect(threaded=True)

        # Wait for WS connection with timeout
        connected = await asyncio.get_event_loop().run_in_executor(
            None, self._ws_connected_event.wait, 10.0  # 10s timeout
        )
        if not connected:
            raise ConnectionError("[Kite] WebSocket connection timed out after 10s")

        logger.info("[Kite] WebSocket connected")

    async def _disconnect_ws(self) -> None:
        """Disconnect from Kite WebSocket."""
        if self.kws:
            try:
                self.kws.close()
            except Exception as e:
                logger.warning("[Kite] Disconnect error: %s", e)
            self.kws = None
        self._ws_connected_event.clear()
        logger.info("[Kite] WebSocket disconnected")

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        """
        Subscribe to Kite tokens and set mode.

        Args:
            broker_tokens: List of integer instrument tokens (e.g., [256265, 260105])
            mode: 'ltp', 'quote', or 'full'
        """
        if not self.kws:
            raise ConnectionError("[Kite] WebSocket not connected")

        logger.debug("[Kite] Subscribing: %s (mode=%s)", broker_tokens, mode)

        # Subscribe to tokens
        self.kws.subscribe(broker_tokens)

        # Set subscription mode
        kite_mode = self._get_kite_mode(mode)
        self.kws.set_mode(kite_mode, broker_tokens)

        logger.info("[Kite] Subscribed to %d tokens (mode=%s)", len(broker_tokens), mode)

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        """
        Unsubscribe from Kite tokens.

        Args:
            broker_tokens: List of integer instrument tokens
        """
        if not self.kws:
            return

        self.kws.unsubscribe(broker_tokens)
        logger.info("[Kite] Unsubscribed from %d tokens", len(broker_tokens))

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Convert canonical tokens to Kite tokens — identity operation.

        Kite instrument_token IS the canonical format, so no translation needed.

        Args:
            canonical_tokens: [256265, 260105, ...]

        Returns:
            Same list of integers (identity)
        """
        return list(canonical_tokens)

    def _get_canonical_token(self, broker_token: Any) -> int:
        """
        Convert Kite token to canonical — identity operation.

        Args:
            broker_token: Kite instrument_token (int)

        Returns:
            Same integer (identity)
        """
        try:
            return int(broker_token)
        except (ValueError, TypeError):
            logger.warning("[Kite] Invalid broker token: %s", broker_token)
            return 0

    def _parse_tick(self, raw_data: Any) -> List[NormalizedTick]:
        """
        Parse a single Kite tick dict into NormalizedTick.

        KiteTicker returns prices in RUPEES (no paise conversion needed).

        Tick structure:
            {
                "instrument_token": 256265,
                "last_price": 24500.50,
                "ohlc": {"open": 24400.0, "high": 24550.25, "low": 24380.0, "close": 24450.75},
                "change": 49.75,
                "volume": 1234567,
                "oi": 5678900,
                "exchange_timestamp": datetime(...),
            }

        Returns:
            List with a single NormalizedTick, or empty list on error
        """
        try:
            instrument_token = raw_data.get("instrument_token")
            if not instrument_token:
                return []

            canonical_token = self._get_canonical_token(instrument_token)
            if canonical_token == 0:
                return []

            # Prices already in rupees — convert to Decimal for precision
            ltp = Decimal(str(raw_data.get("last_price", 0)))

            # OHLC comes as a nested dict
            ohlc = raw_data.get("ohlc") or {}
            open_price = Decimal(str(ohlc.get("open", 0)))
            high = Decimal(str(ohlc.get("high", 0)))
            low = Decimal(str(ohlc.get("low", 0)))
            close = Decimal(str(ohlc.get("close", 0)))

            # Change metrics
            change = ltp - close
            change_percent = (change / close * 100) if close != 0 else Decimal("0")

            volume = raw_data.get("volume", 0) or 0
            oi = raw_data.get("oi", 0) or 0

            # Use exchange timestamp if available, else now
            timestamp = raw_data.get("exchange_timestamp")
            if not isinstance(timestamp, datetime):
                timestamp = datetime.now()

            tick = NormalizedTick(
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
            )

            return [tick]

        except Exception as e:
            logger.error("[Kite] Tick parsing error: %s", e, exc_info=True)
            return []

    # ═══════════════════════════════════════════════════════════════════════
    # KiteTicker CALLBACKS (run on KiteTicker's internal thread)
    # ═══════════════════════════════════════════════════════════════════════

    def _on_connect(self, ws, response) -> None:
        """Callback when WebSocket connection opens (KiteTicker thread)."""
        logger.info("[Kite] WebSocket connected: %s", response)
        self._ws_connected_event.set()

    def _on_ticks(self, ws, ticks) -> None:
        """
        Callback when tick data arrives (KiteTicker thread).

        KiteTicker delivers ticks as a list of dicts (batched).
        Parse each tick and dispatch all at once.

        CRITICAL: bridges to asyncio via _dispatch_from_thread.
        """
        try:
            normalized: List[NormalizedTick] = []
            for raw_tick in ticks:
                parsed = self._parse_tick(raw_tick)
                normalized.extend(parsed)

            if normalized:
                self._dispatch_from_thread(normalized)
        except Exception as e:
            logger.error("[Kite] on_ticks error: %s", e, exc_info=True)

    def _on_error(self, ws, code, reason) -> None:
        """Callback on WebSocket error (KiteTicker thread)."""
        logger.error("[Kite] WebSocket error: code=%s reason=%s", code, reason)

    def _on_close(self, ws, code, reason) -> None:
        """Callback when WebSocket closes (KiteTicker thread)."""
        logger.warning("[Kite] WebSocket closed: code=%s reason=%s", code, reason)
        self._ws_connected_event.clear()
        self._connected = False

    def _on_reconnect(self, ws, attempts_count) -> None:
        """Callback on KiteTicker's built-in reconnect attempt."""
        logger.info("[Kite] WebSocket reconnecting... attempt %d", attempts_count)

    # ═══════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    def _get_kite_mode(self, mode: str):
        """
        Get KiteTicker mode constant from our standard mode name.

        Maps: ltp → MODE_LTP, quote → MODE_QUOTE, full → MODE_FULL
        """
        if not self.kws:
            return mode

        mode_map = {
            "ltp": self.kws.MODE_LTP,
            "quote": self.kws.MODE_QUOTE,
            "full": self.kws.MODE_FULL,
        }
        return mode_map.get(mode, self.kws.MODE_QUOTE)
