"""
TickerAdapter — Abstract base class for broker WebSocket ticker adapters.

Each broker implements this ABC to provide live tick data. The adapter handles:
- Broker-specific WebSocket connection lifecycle
- Token translation (canonical ↔ broker-specific)
- Raw tick parsing into NormalizedTick
- Thread → asyncio bridging for callback-based WS libraries

Concrete implementations: ticker/adapters/{smartapi,kite,upstox,dhan,fyers,paytm}.py
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set, Any

from app.services.brokers.market_data.ticker.models import NormalizedTick

logger = logging.getLogger(__name__)


class TickerAdapter(ABC):
    """
    Abstract base for all broker WebSocket ticker adapters.

    Subclasses implement the _* abstract methods for broker-specific behavior.
    The public API (connect, subscribe, etc.) handles common logic and delegates.
    """

    def __init__(self, broker_type: str):
        self.broker_type = broker_type
        self._connected = False
        self._subscribed_tokens: Set[int] = set()  # canonical tokens
        self._on_tick_callback: Optional[Callable[[List[NormalizedTick]], Any]] = None
        self._on_error_callback: Optional[Callable[[str, str, str], Any]] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._last_tick_time: Optional[datetime] = None
        self._last_error: Optional[Dict[str, str]] = None
        self._reconnect_count: int = 0

    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════

    async def connect(self, credentials: dict) -> None:
        """Connect to broker WebSocket with given credentials."""
        logger.info("[%s] Connecting ticker adapter...", self.broker_type)
        await self._connect_ws(credentials)
        self._connected = True
        self._reconnect_count = 0
        logger.info("[%s] Ticker adapter connected", self.broker_type)

    async def disconnect(self) -> None:
        """Disconnect from broker WebSocket gracefully."""
        logger.info("[%s] Disconnecting ticker adapter...", self.broker_type)
        self._connected = False
        try:
            await self._disconnect_ws()
        except Exception as e:
            logger.warning("[%s] Error during disconnect: %s", self.broker_type, e)
        self._subscribed_tokens.clear()
        logger.info("[%s] Ticker adapter disconnected", self.broker_type)

    async def reconnect(self, credentials: dict, max_retries: int = 5) -> bool:
        """Reconnect with exponential backoff. Returns True on success."""
        for attempt in range(1, max_retries + 1):
            self._reconnect_count += 1
            wait = min(2 ** attempt, 30)
            logger.info(
                "[%s] Reconnect attempt %d/%d (wait %ds)...",
                self.broker_type, attempt, max_retries, wait,
            )
            await asyncio.sleep(wait)
            try:
                await self.connect(credentials)
                # Re-subscribe to previously active tokens
                if self._subscribed_tokens:
                    await self.subscribe(list(self._subscribed_tokens))
                logger.info("[%s] Reconnected successfully", self.broker_type)
                return True
            except Exception as e:
                logger.warning("[%s] Reconnect attempt %d failed: %s", self.broker_type, attempt, e)
        logger.error("[%s] All %d reconnect attempts failed", self.broker_type, max_retries)
        return False

    async def update_credentials(self, credentials: dict) -> None:
        """Hot-swap credentials without dropping the connection if possible."""
        logger.info("[%s] Updating credentials...", self.broker_type)
        saved_tokens = set(self._subscribed_tokens)
        await self.disconnect()
        await self.connect(credentials)
        if saved_tokens:
            await self.subscribe(list(saved_tokens))
        logger.info("[%s] Credentials updated, %d tokens re-subscribed", self.broker_type, len(saved_tokens))

    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC SUBSCRIPTIONS (canonical tokens)
    # ═══════════════════════════════════════════════════════════════════════

    async def subscribe(self, canonical_tokens: List[int], mode: str = "quote") -> None:
        """Subscribe to canonical tokens. Translates to broker tokens internally."""
        if not self._connected:
            raise ConnectionError(f"[{self.broker_type}] Not connected — cannot subscribe")
        new_tokens = [t for t in canonical_tokens if t not in self._subscribed_tokens]
        if not new_tokens:
            return
        broker_tokens = self._translate_to_broker_tokens(new_tokens)
        await self._subscribe_ws(broker_tokens, mode)
        self._subscribed_tokens.update(new_tokens)
        logger.debug("[%s] Subscribed to %d tokens (total: %d)", self.broker_type, len(new_tokens), len(self._subscribed_tokens))

    async def unsubscribe(self, canonical_tokens: List[int]) -> None:
        """Unsubscribe from canonical tokens."""
        if not self._connected:
            return
        active = [t for t in canonical_tokens if t in self._subscribed_tokens]
        if not active:
            return
        broker_tokens = self._translate_to_broker_tokens(active)
        await self._unsubscribe_ws(broker_tokens)
        self._subscribed_tokens.difference_update(active)
        logger.debug("[%s] Unsubscribed from %d tokens (total: %d)", self.broker_type, len(active), len(self._subscribed_tokens))

    # ═══════════════════════════════════════════════════════════════════════
    # CALLBACKS
    # ═══════════════════════════════════════════════════════════════════════

    def set_on_tick_callback(self, callback: Callable[[List[NormalizedTick]], Any]) -> None:
        """Register the callback invoked when normalized ticks arrive."""
        self._on_tick_callback = callback

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the asyncio event loop for thread → async bridging."""
        self._event_loop = loop

    def set_on_error_callback(self, callback: Callable[[str, str, str], Any]) -> None:
        """Register callback invoked on errors. Signature: (broker_type, error_type, error_msg)."""
        self._on_error_callback = callback

    # ═══════════════════════════════════════════════════════════════════════
    # ERROR REPORTING (used by subclasses)
    # ═══════════════════════════════════════════════════════════════════════

    def _report_error(self, error_type: str, error_msg: str) -> None:
        """Report a general error. Stores in last_error and notifies callback."""
        self._last_error = {"error_type": error_type, "error_msg": error_msg}
        if self._on_error_callback:
            self._on_error_callback(self.broker_type, error_type, error_msg)

    def _report_auth_error(self, error_code: str, error_msg: str) -> None:
        """Report an authentication error. Stores error_code in last_error."""
        combined_msg = f"{error_code}: {error_msg}"
        self._last_error = {
            "error_type": "auth",
            "error_code": error_code,
            "error_msg": combined_msg,
        }
        if self._on_error_callback:
            self._on_error_callback(self.broker_type, "auth", combined_msg)

    # ═══════════════════════════════════════════════════════════════════════
    # PROPERTIES
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscribed_tokens(self) -> Set[int]:
        return set(self._subscribed_tokens)

    @property
    def last_tick_time(self) -> Optional[datetime]:
        return self._last_tick_time

    @property
    def last_error(self) -> Optional[Dict[str, str]]:
        return self._last_error

    @property
    def reconnect_count(self) -> int:
        return self._reconnect_count

    # ═══════════════════════════════════════════════════════════════════════
    # DISPATCH HELPERS (used by subclasses)
    # ═══════════════════════════════════════════════════════════════════════

    def _dispatch_from_thread(self, ticks: List[NormalizedTick]) -> None:
        """
        Bridge for thread-based WS libraries (SmartAPI, Kite, Dhan).

        Call this from a callback running on the WS library's thread.
        It schedules the async dispatch on the event loop.
        """
        if not ticks or not self._on_tick_callback:
            return
        self._last_tick_time = datetime.now()
        loop = self._event_loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self._dispatch_async(ticks), loop)
        else:
            logger.warning("[%s] Event loop not available for thread dispatch", self.broker_type)

    async def _dispatch_async(self, ticks: List[NormalizedTick]) -> None:
        """
        Dispatch ticks to the registered callback (asyncio-native path).

        For asyncio-native WS libraries (Fyers, Paytm, Upstox), call this directly.
        """
        if not ticks or not self._on_tick_callback:
            return
        self._last_tick_time = datetime.now()
        try:
            result = self._on_tick_callback(ticks)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error("[%s] Error in tick callback: %s", self.broker_type, e, exc_info=True)

    # ═══════════════════════════════════════════════════════════════════════
    # ABSTRACT METHODS — implement per broker
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def _connect_ws(self, credentials: dict) -> None:
        """Establish the broker-specific WebSocket connection."""
        ...

    @abstractmethod
    async def _disconnect_ws(self) -> None:
        """Close the broker-specific WebSocket connection."""
        ...

    @abstractmethod
    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        """Send subscription message for broker-specific tokens."""
        ...

    @abstractmethod
    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        """Send unsubscription message for broker-specific tokens."""
        ...

    @abstractmethod
    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """Convert canonical Kite tokens to broker-specific token format."""
        ...

    @abstractmethod
    def _get_canonical_token(self, broker_token: Any) -> int:
        """Convert a single broker-specific token back to canonical Kite token."""
        ...

    @abstractmethod
    def _parse_tick(self, raw_data: Any) -> List[NormalizedTick]:
        """
        Parse broker-specific raw tick data into NormalizedTick list.

        Must:
        - Convert paise → rupees if needed (SmartAPI, Kite)
        - Map broker tokens → canonical tokens via _get_canonical_token()
        - Set broker_type on each tick
        """
        ...
