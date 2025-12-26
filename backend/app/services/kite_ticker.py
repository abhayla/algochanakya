"""
Kite Ticker WebSocket Service

Manages WebSocket connection to Kite Connect for live market data.
Integrates with WebSocket Health Monitor for circuit breaker protection.
"""
import asyncio
import logging
import time
from typing import Set, Dict, Optional
from fastapi import WebSocket
from kiteconnect import KiteTicker, KiteConnect

from app.config import settings

logger = logging.getLogger(__name__)

# Health monitor integration (lazy import to avoid circular imports)
_health_monitor = None


def _get_health_monitor():
    """Get health monitor instance (lazy initialization)."""
    global _health_monitor
    if _health_monitor is None:
        try:
            from app.services.ai.websocket_health_monitor import get_health_monitor
            _health_monitor = get_health_monitor()
        except ImportError:
            logger.warning("WebSocket health monitor not available")
    return _health_monitor


class KiteTickerService:
    """
    Service for managing Kite WebSocket connection and broadcasting ticks.
    """

    def __init__(self):
        self.kite_ws: Optional[KiteTicker] = None
        self.is_connected = False
        self.access_token: Optional[str] = None
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._latest_ticks: Dict[int, dict] = {}  # token -> tick data
        self._connected_clients: Dict[str, WebSocket] = {}  # user_id -> websocket
        self._user_subscriptions: Dict[str, Set[int]] = {}  # user_id -> set of tokens
        self._subscribed_tokens: Set[int] = set()  # All tokens subscribed on Kite

    async def connect(self, access_token: str):
        """
        Connect to Kite WebSocket.

        Args:
            access_token: Kite access token from OAuth
        """
        if self.is_connected:
            logger.info("Already connected to Kite WebSocket")
            return

        try:
            self.access_token = access_token
            self._main_loop = asyncio.get_running_loop()

            # Validate access token with a test API call before WebSocket connection
            print(f"[KITE] Validating Kite access token...", flush=True)
            logger.info("Validating Kite access token...")
            kite = KiteConnect(api_key=settings.KITE_API_KEY)
            kite.set_access_token(access_token)
            try:
                profile = kite.profile()
                print(f"[KITE] API validated for user: {profile.get('user_name', 'Unknown')}", flush=True)
                logger.info(f"Kite API validated for user: {profile.get('user_name', 'Unknown')}")
            except Exception as e:
                print(f"[KITE] API validation failed: {e}", flush=True)
                logger.error(f"Kite API validation failed: {e}")
                raise Exception(f"Invalid Kite access token: {e}")

            # Initialize Kite Ticker
            self.kite_ws = KiteTicker(
                api_key=settings.KITE_API_KEY,
                access_token=access_token
            )

            # Set callbacks
            self.kite_ws.on_ticks = self._on_ticks
            self.kite_ws.on_connect = self._on_connect
            self.kite_ws.on_close = self._on_close
            self.kite_ws.on_error = self._on_error
            self.kite_ws.on_reconnect = self._on_reconnect

            # Connect in threaded mode
            self.kite_ws.connect(threaded=True)

            logger.info("Kite WebSocket connection initiated")

        except Exception as e:
            logger.error(f"Failed to connect to Kite WebSocket: {e}")
            raise

    def _on_connect(self, ws, response):
        """Callback when WebSocket connects."""
        logger.info(f"Kite WebSocket connected: {response}")
        self.is_connected = True

        # Record connection status in health monitor
        monitor = _get_health_monitor()
        if monitor:
            monitor.record_connection_status(True)

        # Re-subscribe to existing tokens if any
        if self._subscribed_tokens:
            logger.info(f"Resubscribing to {len(self._subscribed_tokens)} tokens")
            ws.subscribe(list(self._subscribed_tokens))
            ws.set_mode(ws.MODE_LTP, list(self._subscribed_tokens))

    def _on_close(self, ws, code, reason):
        """Callback when WebSocket closes."""
        logger.warning(f"Kite WebSocket closed: {code} - {reason}")
        self.is_connected = False

        # Record connection status in health monitor
        monitor = _get_health_monitor()
        if monitor:
            monitor.record_connection_status(False)
            monitor.record_error("connection_closed", f"Code: {code}, Reason: {reason}")

        # Schedule reconnection using thread-safe method
        if self._main_loop and self.access_token:
            asyncio.run_coroutine_threadsafe(
                self._reconnect(),
                self._main_loop
            )

    def _on_error(self, ws, code, reason):
        """Callback on WebSocket error."""
        logger.error(f"Kite WebSocket error: code={code}, reason={reason}")

        # Record error in health monitor
        monitor = _get_health_monitor()
        if monitor:
            monitor.record_error("websocket_error", f"Code: {code}, Reason: {reason}")

        # Log additional debug info
        if self.access_token:
            logger.error(f"Access token (last 10 chars): ...{self.access_token[-10:]}")
        else:
            logger.error("Access token: None")

    def _on_reconnect(self, ws, attempts_count):
        """Callback on reconnection attempt."""
        logger.info(f"Kite WebSocket reconnecting... attempt {attempts_count}")

    def _on_ticks(self, ws, ticks):
        """
        Handle incoming ticks from Kite.
        Runs in Kite's thread - must use thread-safe async execution.
        """
        try:
            # Record tick in health monitor
            monitor = _get_health_monitor()
            if monitor:
                # Calculate approximate latency based on tick exchange timestamp if available
                latency_ms = 0
                for tick in ticks:
                    if tick.get("exchange_timestamp"):
                        try:
                            tick_time = tick["exchange_timestamp"]
                            if hasattr(tick_time, 'timestamp'):
                                latency_ms = (time.time() - tick_time.timestamp()) * 1000
                                break
                        except Exception:
                            pass
                monitor.record_tick_received(latency_ms=latency_ms)

            # Store latest ticks in memory
            for tick in ticks:
                token = tick.get("instrument_token")
                if token:
                    self._latest_ticks[token] = tick

            # Broadcast to connected clients (thread-safe)
            if self._main_loop and self._connected_clients:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_ticks(ticks),
                    self._main_loop
                )

        except Exception as e:
            logger.error(f"Error processing ticks: {e}")
            # Record error in health monitor
            monitor = _get_health_monitor()
            if monitor:
                monitor.record_error("tick_processing_error", str(e))

    async def _broadcast_ticks(self, ticks: list):
        """Broadcast ticks to all connected WebSocket clients."""
        if not ticks:
            return

        for user_id, websocket in list(self._connected_clients.items()):
            try:
                # Filter ticks for this user's subscriptions
                user_tokens = self._user_subscriptions.get(user_id, set())
                user_ticks = []

                for t in ticks:
                    token = t.get("instrument_token")
                    if token in user_tokens:
                        ltp = t.get("last_price", 0)
                        change = t.get("change", 0)
                        close = t.get("ohlc", {}).get("close") if t.get("ohlc") else None
                        # Calculate percentage using previous close, not LTP
                        change_percent = ((ltp - close) / close * 100) if close else 0
                        user_ticks.append({
                            "token": token,
                            "ltp": ltp,
                            "change": change,
                            "change_percent": change_percent,
                            "volume": t.get("volume"),
                            "oi": t.get("oi"),
                            "high": t.get("ohlc", {}).get("high") if t.get("ohlc") else None,
                            "low": t.get("ohlc", {}).get("low") if t.get("ohlc") else None,
                            "open": t.get("ohlc", {}).get("open") if t.get("ohlc") else None,
                            "close": close,
                        })

                if user_ticks:
                    await websocket.send_json({"type": "ticks", "data": user_ticks})

            except Exception as e:
                logger.warning(f"Error broadcasting to user {user_id}: {e}")
                # Remove disconnected client
                await self.unregister_client(user_id)

    async def register_client(self, user_id: str, websocket: WebSocket):
        """Register a WebSocket client."""
        user_id = str(user_id)
        self._connected_clients[user_id] = websocket
        self._user_subscriptions[user_id] = set()
        logger.info(f"Client registered: {user_id}. Total clients: {len(self._connected_clients)}")

    async def unregister_client(self, user_id: str):
        """Unregister a WebSocket client."""
        user_id = str(user_id)

        # Get user's tokens before removing
        user_tokens = self._user_subscriptions.get(user_id, set())

        # Remove user
        if user_id in self._connected_clients:
            del self._connected_clients[user_id]
        if user_id in self._user_subscriptions:
            del self._user_subscriptions[user_id]

        # Cleanup tokens no one is subscribed to
        self._cleanup_subscriptions(user_tokens)

        logger.info(f"Client unregistered: {user_id}. Total clients: {len(self._connected_clients)}")

    async def subscribe(self, tokens: list, user_id: str, mode: str = "ltp"):
        """
        Subscribe to instrument tokens for a user.

        Args:
            tokens: List of instrument tokens
            user_id: User identifier
            mode: Subscription mode - 'ltp', 'quote', or 'full'
        """
        user_id = str(user_id)
        tokens_set = set(tokens)

        # Add to user's subscriptions
        if user_id not in self._user_subscriptions:
            self._user_subscriptions[user_id] = set()
        self._user_subscriptions[user_id].update(tokens_set)

        # Find new tokens to subscribe on Kite
        new_tokens = tokens_set - self._subscribed_tokens

        if new_tokens and self.is_connected and self.kite_ws:
            logger.info(f"Subscribing to {len(new_tokens)} new tokens on Kite")
            self._subscribed_tokens.update(new_tokens)
            self.kite_ws.subscribe(list(new_tokens))

            # Set mode
            if mode == "ltp":
                self.kite_ws.set_mode(self.kite_ws.MODE_LTP, list(new_tokens))
            elif mode == "quote":
                self.kite_ws.set_mode(self.kite_ws.MODE_QUOTE, list(new_tokens))
            elif mode == "full":
                self.kite_ws.set_mode(self.kite_ws.MODE_FULL, list(new_tokens))

        # Send cached ticks immediately
        await self._send_cached_ticks(user_id, tokens)

        logger.info(f"User {user_id} subscribed to {len(tokens)} tokens")

    async def _send_cached_ticks(self, user_id: str, tokens: list):
        """Send cached tick data immediately to user."""
        websocket = self._connected_clients.get(str(user_id))
        if not websocket:
            return

        cached_ticks = []
        for token in tokens:
            if token in self._latest_ticks:
                t = self._latest_ticks[token]
                ltp = t.get("last_price", 0)
                change = t.get("change", 0)
                close = t.get("ohlc", {}).get("close") if t.get("ohlc") else None
                # Calculate percentage using previous close, not LTP
                change_percent = ((ltp - close) / close * 100) if close else 0
                cached_ticks.append({
                    "token": t.get("instrument_token"),
                    "ltp": ltp,
                    "change": change,
                    "change_percent": change_percent,
                    "close": close,
                })

        if cached_ticks:
            try:
                await websocket.send_json({"type": "ticks", "data": cached_ticks})
            except Exception as e:
                logger.warning(f"Failed to send cached ticks to {user_id}: {e}")

    async def unsubscribe(self, tokens: list, user_id: str):
        """
        Unsubscribe from instrument tokens for a user.

        Args:
            tokens: List of instrument tokens
            user_id: User identifier
        """
        user_id = str(user_id)
        tokens_set = set(tokens)

        # Remove from user's subscriptions
        if user_id in self._user_subscriptions:
            self._user_subscriptions[user_id] -= tokens_set

        # Cleanup tokens no one is subscribed to
        self._cleanup_subscriptions(tokens_set)

        logger.info(f"User {user_id} unsubscribed from {len(tokens)} tokens")

    def _cleanup_subscriptions(self, tokens: Set[int]):
        """Unsubscribe from Kite for tokens no user needs."""
        # Find which tokens are still needed by any user
        all_user_tokens = set()
        for user_tokens in self._user_subscriptions.values():
            all_user_tokens.update(user_tokens)

        # Tokens to unsubscribe from Kite
        tokens_to_remove = tokens - all_user_tokens

        if tokens_to_remove and self.is_connected and self.kite_ws:
            logger.info(f"Unsubscribing from {len(tokens_to_remove)} unused tokens on Kite")
            self._subscribed_tokens -= tokens_to_remove
            self.kite_ws.unsubscribe(list(tokens_to_remove))

    def get_latest_tick(self, token: int) -> Optional[dict]:
        """Get the latest tick data for an instrument."""
        return self._latest_ticks.get(token)

    async def _reconnect(self):
        """Attempt to reconnect after delay."""
        await asyncio.sleep(5)  # Wait 5 seconds before reconnecting

        if not self.is_connected and self.access_token:
            logger.info("Attempting to reconnect to Kite WebSocket...")
            try:
                await self.connect(self.access_token)
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")

    def disconnect(self):
        """Disconnect from Kite WebSocket."""
        try:
            if self.kite_ws:
                self.kite_ws.close()
                self.is_connected = False
                logger.info("Kite WebSocket disconnected")

        except Exception as e:
            logger.error(f"Error disconnecting: {e}")


# Global singleton instance
kite_ticker_service = KiteTickerService()
