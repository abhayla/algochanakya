"""
SmartAPI (Angel One) Ticker Adapter

WebSocket V2 implementation using SmartWebSocketV2 library.

Key characteristics:
- Threading model: SmartWebSocketV2 blocks with run_forever on daemon thread
- Callbacks execute on WS thread → bridge to asyncio via _dispatch_from_thread
- Token format: String (e.g., "99926000" for NIFTY)
- Price normalization: Paise ÷ 100 → Rupees (Decimal)
- Exchange type codes required for subscriptions (NSE=1, NFO=2, BSE=3, BFO=4, MCX=5)
"""

import asyncio
import logging
import threading
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from ..adapter_base import TickerAdapter
from ..models import NormalizedTick

logger = logging.getLogger(__name__)

# Paise → Rupees divisor (use Decimal to avoid float intermediaries)
_PAISE_DIVISOR = Decimal("100")


class SmartAPITickerAdapter(TickerAdapter):
    """
    SmartAPI WebSocket V2 ticker adapter.

    Threading pattern (CRITICAL — do not modify):
    - SmartWebSocketV2 runs on a separate daemon thread (blocking run_forever)
    - Callbacks (_on_open, _on_data, _on_error, _on_close) execute on that thread
    - Use _dispatch_from_thread() to bridge ticks to the asyncio event loop
    """

    # SmartAPI WebSocket modes
    MODES = {
        "ltp": 1,
        "quote": 2,
        "snap": 3,
        "depth": 4,
    }

    # Exchange type codes
    EXCHANGE_NSE = 1
    EXCHANGE_NFO = 2
    EXCHANGE_BSE = 3
    EXCHANGE_BFO = 4
    EXCHANGE_MCX = 5

    def __init__(self, broker_type: str = "smartapi"):
        super().__init__(broker_type)
        self.sws = None  # SmartWebSocketV2 instance
        self._ws_thread: Optional[threading.Thread] = None

        # Connection event — signalled by _on_open on the WS thread
        self._ws_connected_event = threading.Event()

        # Token mapping caches (loaded before first subscribe)
        # canonical Kite token (int) → SmartAPI token (str)
        self._canonical_to_broker: Dict[int, str] = {}
        # SmartAPI token (str) → canonical Kite token (int)
        self._broker_to_canonical: Dict[str, int] = {}
        # canonical Kite token (int) → exchange type code (int)
        self._token_exchange_type: Dict[int, int] = {}

    # ═══════════════════════════════════════════════════════════════════════
    # TOKEN MAP MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def load_token_map(self, mapping: Dict[int, Tuple[str, int]]) -> None:
        """
        Pre-load canonical ↔ broker token mappings.

        Called before subscribing. The TickerPool or startup code loads this
        from the broker_instrument_tokens DB table (async) and passes it here.

        Args:
            mapping: {canonical_token: (smartapi_token, exchange_type)}
                     e.g. {256265: ("99926000", 1), 260105: ("99926009", 1)}
        """
        for canonical, (broker_token, exchange_type) in mapping.items():
            self._canonical_to_broker[canonical] = broker_token
            self._broker_to_canonical[broker_token] = canonical
            self._token_exchange_type[canonical] = exchange_type
        logger.info(
            "[SmartAPI] Loaded %d token mappings", len(mapping)
        )

    # ═══════════════════════════════════════════════════════════════════════
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════════════════

    async def _connect_ws(self, credentials: dict) -> None:
        """
        Connect to SmartAPI WebSocket V2.

        Args:
            credentials: {
                "jwt_token": str,
                "api_key": str,
                "client_id": str,
                "feed_token": str,
                "token_map": optional dict for load_token_map
            }
        """
        from SmartApi.smartWebSocketV2 import SmartWebSocketV2

        jwt_token = credentials["jwt_token"]
        api_key = credentials["api_key"]
        client_id = credentials["client_id"]
        feed_token = credentials["feed_token"]

        # Optional: pre-load token mappings from credentials
        token_map = credentials.get("token_map")
        if token_map:
            self.load_token_map(token_map)

        logger.info("[SmartAPI] Connecting WebSocket for client: %s", client_id)

        # Reset connection event
        self._ws_connected_event.clear()

        # Create SmartWebSocketV2 instance
        self.sws = SmartWebSocketV2(
            auth_token=jwt_token,
            api_key=api_key,
            client_code=client_id,
            feed_token=feed_token,
        )

        # Set callbacks (execute on WS thread)
        self.sws.on_open = self._on_open
        self.sws.on_data = self._on_data
        self.sws.on_error = self._on_error
        self.sws.on_close = self._on_close

        # Start WS in daemon thread (CRITICAL: sws.connect() blocks with run_forever)
        self._ws_thread = threading.Thread(
            target=self._run_ws,
            daemon=True,
            name="SmartAPI-WS-Thread",
        )
        self._ws_thread.start()

        # Wait for WS connection with timeout
        connected = await asyncio.get_event_loop().run_in_executor(
            None, self._ws_connected_event.wait, 10.0  # 10s timeout
        )
        if not connected:
            raise ConnectionError("[SmartAPI] WebSocket connection timed out after 10s")

        logger.info("[SmartAPI] WebSocket connected for client: %s", client_id)

    def _run_ws(self) -> None:
        """Run SmartWebSocketV2.connect() on the daemon thread."""
        try:
            self.sws.connect()
        except Exception as e:
            logger.error("[SmartAPI] WebSocket thread error: %s", e)

    async def _disconnect_ws(self) -> None:
        """Disconnect from SmartAPI WebSocket."""
        if self.sws:
            try:
                self.sws.close_connection()
            except Exception as e:
                logger.warning("[SmartAPI] Disconnect error: %s", e)
            self.sws = None
        self._ws_connected_event.clear()
        logger.info("[SmartAPI] WebSocket disconnected")

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        """
        Subscribe to SmartAPI tokens.

        Args:
            broker_tokens: [{"exchangeType": 2, "tokens": ["99926000", ...]}, ...]
            mode: 'ltp', 'quote', 'snap', or 'depth'
        """
        if not self.sws:
            raise ConnectionError("[SmartAPI] WebSocket not connected")

        mode_value = self.MODES.get(mode, self.MODES["quote"])
        correlation_id = "ticker_pool"

        logger.debug("[SmartAPI] Subscribing: %s (mode=%d)", broker_tokens, mode_value)
        self.sws.subscribe(correlation_id, mode_value, broker_tokens)
        logger.info(
            "[SmartAPI] Subscribed to %d token groups",
            len(broker_tokens),
        )

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        """
        Unsubscribe from SmartAPI tokens.

        Args:
            broker_tokens: [{"exchangeType": 2, "tokens": ["99926000", ...]}, ...]
        """
        if not self.sws:
            return

        mode_value = self.MODES["quote"]  # Mode irrelevant for unsubscribe
        correlation_id = "ticker_pool"

        self.sws.unsubscribe(correlation_id, mode_value, broker_tokens)
        logger.info(
            "[SmartAPI] Unsubscribed from %d token groups",
            len(broker_tokens),
        )

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Convert canonical Kite tokens to SmartAPI subscription format.

        Groups tokens by exchange type for efficient SmartAPI subscription.

        Args:
            canonical_tokens: [256265, 260105, ...]

        Returns:
            [{"exchangeType": 2, "tokens": ["99926000", "99926009"]}, ...]
        """
        exchange_groups: Dict[int, List[str]] = {}

        for canonical_token in canonical_tokens:
            broker_token = self._canonical_to_broker.get(canonical_token)
            if broker_token is None:
                logger.warning(
                    "[SmartAPI] No broker token for canonical %d — skipping",
                    canonical_token,
                )
                continue

            exchange_type = self._token_exchange_type.get(
                canonical_token, self.EXCHANGE_NFO
            )

            if exchange_type not in exchange_groups:
                exchange_groups[exchange_type] = []
            exchange_groups[exchange_type].append(broker_token)

        return [
            {"exchangeType": ex_type, "tokens": tokens}
            for ex_type, tokens in exchange_groups.items()
        ]

    def _get_canonical_token(self, broker_token: Any) -> int:
        """
        Convert SmartAPI token string to canonical Kite token.

        Args:
            broker_token: SmartAPI token string (e.g., "99926000")

        Returns:
            Canonical Kite instrument token (e.g., 256265), or 0 if unknown
        """
        canonical = self._broker_to_canonical.get(str(broker_token))
        if canonical is None:
            logger.warning("[SmartAPI] Unknown broker token: %s", broker_token)
            return 0
        return canonical

    def _parse_tick(self, raw_data: Any) -> List[NormalizedTick]:
        """
        Parse SmartAPI tick dict into NormalizedTick.

        SmartWebSocketV2 pre-parses binary frames into a dict with keys like
        'token', 'last_traded_price' (paise), 'open_price_of_the_day', etc.

        Returns:
            List with a single NormalizedTick, or empty list on error
        """
        try:
            broker_token = raw_data.get("token")
            if not broker_token:
                return []

            canonical_token = self._get_canonical_token(broker_token)
            if canonical_token == 0:
                return []

            # Extract prices in paise and convert to Decimal rupees
            ltp = Decimal(raw_data.get("last_traded_price", 0)) / _PAISE_DIVISOR
            open_price = Decimal(raw_data.get("open_price_of_the_day", 0)) / _PAISE_DIVISOR
            high = Decimal(raw_data.get("high_price_of_the_day", 0)) / _PAISE_DIVISOR
            low = Decimal(raw_data.get("low_price_of_the_day", 0)) / _PAISE_DIVISOR
            close = Decimal(raw_data.get("closed_price", 0)) / _PAISE_DIVISOR

            # Change metrics
            change = ltp - close
            change_percent = (change / close * 100) if close != 0 else Decimal("0")

            volume = raw_data.get("volume_trade_for_the_day", 0) or 0
            oi = raw_data.get("open_interest", 0) or 0

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
                timestamp=datetime.now(),
                broker_type=self.broker_type,
            )

            return [tick]

        except Exception as e:
            logger.error("[SmartAPI] Tick parsing error: %s", e, exc_info=True)
            return []

    # ═══════════════════════════════════════════════════════════════════════
    # SmartWebSocketV2 CALLBACKS (run on WS thread)
    # ═══════════════════════════════════════════════════════════════════════

    def _on_open(self, ws) -> None:
        """Callback when WebSocket connection opens (WS thread)."""
        logger.info("[SmartAPI] WebSocket connected")
        self._ws_connected_event.set()

    def _on_data(self, ws, message) -> None:
        """
        Callback when tick data arrives (WS thread).

        CRITICAL: bridges to asyncio via _dispatch_from_thread.
        """
        try:
            ticks = self._parse_tick(message)
            if ticks:
                self._dispatch_from_thread(ticks)
        except Exception as e:
            logger.error("[SmartAPI] on_data error: %s", e, exc_info=True)

    def _on_error(self, ws, error) -> None:
        """Callback on WebSocket error (WS thread)."""
        logger.error("[SmartAPI] WebSocket error: %s", error)

    def _on_close(self, ws, code, reason) -> None:
        """Callback when WebSocket closes (WS thread)."""
        logger.warning("[SmartAPI] WebSocket closed: code=%s reason=%s", code, reason)
        self._ws_connected_event.clear()
        self._connected = False
