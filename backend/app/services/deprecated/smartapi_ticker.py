"""
DEPRECATED — SmartAPI Ticker WebSocket Service

Replaced by: app.services.brokers.market_data.ticker.adapters.smartapi.SmartAPITickerAdapter
See: docs/guides/TICKER-MIGRATION.md

This file is kept for reference only. DO NOT import in new code.

Original: Manages WebSocket V2 connection to AngelOne SmartAPI for live market data.
"""
import asyncio
import logging
import time
from typing import Set, Dict, Optional, List, Any

from fastapi import WebSocket

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


class SmartAPITickerService:
    """
    Service for managing SmartAPI WebSocket V2 connection and broadcasting ticks.

    Mirrors KiteTickerService interface for seamless switching between providers.
    """

    # SmartAPI WebSocket modes
    MODES = {
        'ltp': 1,       # Last Traded Price only
        'quote': 2,     # OHLC + Volume + OI
        'snap': 3,      # Snapshot quote
        'depth': 4      # Best 20 Buy/Sell
    }

    # Exchange type mapping
    EXCHANGE_TYPES = {
        'NSE': 1,   # NSE Cash
        'NFO': 2,   # NSE F&O
        'BSE': 3,   # BSE Cash
        'BFO': 4,   # BSE F&O
        'MCX': 5,   # MCX
    }

    def __init__(self):
        self.sws = None  # SmartWebSocketV2 instance
        self.is_connected = False
        self.jwt_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.api_key: Optional[str] = None
        self.client_id: Optional[str] = None
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._latest_ticks: Dict[str, dict] = {}  # token -> tick data
        self._connected_clients: Dict[str, WebSocket] = {}  # user_id -> websocket
        self._user_subscriptions: Dict[str, Set[str]] = {}  # user_id -> set of tokens
        self._subscribed_tokens: Dict[str, Set[str]] = {}  # exchange -> set of tokens

    async def connect(
        self,
        jwt_token: str,
        api_key: str,
        client_id: str,
        feed_token: str
    ):
        """
        Connect to SmartAPI WebSocket V2.

        Args:
            jwt_token: JWT token from authentication
            api_key: AngelOne API key
            client_id: Client ID
            feed_token: Feed token for WebSocket
        """
        if self.is_connected:
            logger.info("[SmartAPI] Already connected to WebSocket")
            return

        try:
            from SmartApi.smartWebSocketV2 import SmartWebSocketV2
            import threading

            self.jwt_token = jwt_token
            self.api_key = api_key
            self.client_id = client_id
            self.feed_token = feed_token
            self._main_loop = asyncio.get_running_loop()

            print(f"[SmartAPI] Connecting to WebSocket for client: {client_id}", flush=True)
            logger.info(f"[SmartAPI] Connecting to WebSocket for client: {client_id}")

            # Initialize SmartWebSocketV2
            self.sws = SmartWebSocketV2(
                auth_token=jwt_token,
                api_key=api_key,
                client_code=client_id,
                feed_token=feed_token
            )

            # Set callbacks
            self.sws.on_data = self._on_ticks
            self.sws.on_open = self._on_connect
            self.sws.on_close = self._on_close
            self.sws.on_error = self._on_error

            # Run connect in a separate thread (it blocks with run_forever)
            def run_websocket():
                try:
                    self.sws.connect()
                except Exception as e:
                    logger.error(f"[SmartAPI] WebSocket thread error: {e}")

            ws_thread = threading.Thread(target=run_websocket, daemon=True)
            ws_thread.start()

            logger.info("[SmartAPI] WebSocket connection initiated in background thread")

        except Exception as e:
            logger.error(f"[SmartAPI] Failed to connect to WebSocket: {e}")
            raise

    def _on_connect(self, wsapp):
        """Callback when WebSocket connects."""
        logger.info("[SmartAPI] WebSocket connected")
        print("[SmartAPI] WebSocket connected", flush=True)
        self.is_connected = True

        # Record connection status in health monitor
        monitor = _get_health_monitor()
        if monitor:
            monitor.record_connection_status(True)

        # Re-subscribe to existing tokens if any
        if self._subscribed_tokens:
            total_tokens = sum(len(tokens) for tokens in self._subscribed_tokens.values())
            logger.info(f"[SmartAPI] Resubscribing to {total_tokens} tokens")
            self._resubscribe_all()

    def _on_close(self, wsapp, code, reason):
        """Callback when WebSocket closes."""
        logger.warning(f"[SmartAPI] WebSocket closed: {code} - {reason}")
        print(f"[SmartAPI] WebSocket closed: {code} - {reason}", flush=True)
        self.is_connected = False

        # Record connection status in health monitor
        monitor = _get_health_monitor()
        if monitor:
            monitor.record_connection_status(False)
            monitor.record_error("smartapi_connection_closed", f"Code: {code}, Reason: {reason}")

        # Schedule reconnection
        if self._main_loop and self.jwt_token:
            asyncio.run_coroutine_threadsafe(
                self._reconnect(),
                self._main_loop
            )

    def _on_error(self, wsapp, error):
        """Callback on WebSocket error."""
        logger.error(f"[SmartAPI] WebSocket error: {error}")
        print(f"[SmartAPI] WebSocket error: {error}", flush=True)

        # Record error in health monitor
        monitor = _get_health_monitor()
        if monitor:
            monitor.record_error("smartapi_websocket_error", str(error))

    def _on_ticks(self, wsapp, message):
        """
        Handle incoming ticks from SmartAPI.
        Runs in SmartAPI's thread - must use thread-safe async execution.

        SmartAPI prices are in PAISE - we convert to rupees here.
        """
        try:
            # Record tick in health monitor
            monitor = _get_health_monitor()
            if monitor:
                latency_ms = 0
                if message.get('exchange_timestamp'):
                    try:
                        tick_time = message['exchange_timestamp'] / 1000  # ms to seconds
                        latency_ms = (time.time() - tick_time) * 1000
                    except Exception:
                        pass
                monitor.record_tick_received(latency_ms=latency_ms)

            # Normalize tick data (convert paise to rupees)
            normalized = self._normalize_tick(message)

            # Store latest tick
            token = normalized.get('token')
            if token:
                self._latest_ticks[token] = normalized

            # Broadcast to connected clients (thread-safe)
            if self._main_loop and self._connected_clients:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_ticks([normalized]),
                    self._main_loop
                )

        except Exception as e:
            logger.error(f"[SmartAPI] Error processing tick: {e}")
            monitor = _get_health_monitor()
            if monitor:
                monitor.record_error("smartapi_tick_processing_error", str(e))

    def _normalize_tick(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize SmartAPI tick to match Kite format.

        SmartAPI prices are in PAISE (divide by 100 for rupees).
        """
        # Convert paise to rupees for all price fields
        def to_rupees(paise):
            if paise is None:
                return None
            return paise / 100 if isinstance(paise, (int, float)) else paise

        ltp = to_rupees(message.get('last_traded_price', 0))
        open_price = to_rupees(message.get('open_price_of_the_day', 0))
        high_price = to_rupees(message.get('high_price_of_the_day', 0))
        low_price = to_rupees(message.get('low_price_of_the_day', 0))
        close_price = to_rupees(message.get('closed_price', 0))  # Previous close

        # Calculate change
        change = ltp - close_price if ltp and close_price else 0
        change_percent = (change / close_price * 100) if close_price else 0

        return {
            'token': message.get('token'),
            'ltp': ltp,
            'change': change,
            'change_percent': change_percent,
            'volume': message.get('volume_trade_for_the_day', 0),
            'oi': message.get('open_interest', 0),
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'last_trade_time': message.get('last_traded_timestamp'),
            'exchange_timestamp': message.get('exchange_timestamp'),
        }

    async def _broadcast_ticks(self, ticks: list):
        """Broadcast ticks to all connected WebSocket clients."""
        if not ticks:
            return

        for user_id, websocket in list(self._connected_clients.items()):
            try:
                # Filter ticks for this user's subscriptions
                user_tokens = self._user_subscriptions.get(user_id, set())
                user_ticks = [t for t in ticks if t.get('token') in user_tokens]

                if user_ticks:
                    await websocket.send_json({"type": "ticks", "data": user_ticks})

            except Exception as e:
                logger.warning(f"[SmartAPI] Error broadcasting to user {user_id}: {e}")
                await self.unregister_client(user_id)

    async def register_client(self, user_id: str, websocket: WebSocket):
        """Register a WebSocket client."""
        user_id = str(user_id)
        self._connected_clients[user_id] = websocket
        self._user_subscriptions[user_id] = set()
        logger.info(f"[SmartAPI] Client registered: {user_id}. Total clients: {len(self._connected_clients)}")

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

        logger.info(f"[SmartAPI] Client unregistered: {user_id}. Total clients: {len(self._connected_clients)}")

    async def subscribe(
        self,
        tokens: List[str],
        user_id: str,
        exchange: str = "NFO",
        mode: str = "quote"
    ):
        """
        Subscribe to instrument tokens for a user.

        Args:
            tokens: List of SmartAPI instrument tokens
            user_id: User identifier
            exchange: Exchange (NFO, NSE, etc.)
            mode: Subscription mode - 'ltp', 'quote', 'snap', or 'depth'
        """
        user_id = str(user_id)
        tokens_set = set(tokens)

        # Add to user's subscriptions
        if user_id not in self._user_subscriptions:
            self._user_subscriptions[user_id] = set()
        self._user_subscriptions[user_id].update(tokens_set)

        # Initialize exchange set if needed
        if exchange not in self._subscribed_tokens:
            self._subscribed_tokens[exchange] = set()

        # Find new tokens to subscribe
        new_tokens = tokens_set - self._subscribed_tokens[exchange]

        if new_tokens and self.is_connected and self.sws:
            logger.info(f"[SmartAPI] Subscribing to {len(new_tokens)} new tokens on {exchange}")
            self._subscribed_tokens[exchange].update(new_tokens)

            # Build subscription request
            token_list = [{
                "exchangeType": self.EXCHANGE_TYPES.get(exchange, 2),
                "tokens": list(new_tokens)
            }]

            try:
                self.sws.subscribe(
                    "algochanakya",
                    self.MODES.get(mode, 2),
                    token_list
                )
            except Exception as e:
                logger.error(f"[SmartAPI] Subscription error: {e}")

        # Send cached ticks immediately
        await self._send_cached_ticks(user_id, tokens)

        logger.info(f"[SmartAPI] User {user_id} subscribed to {len(tokens)} tokens")

    async def _send_cached_ticks(self, user_id: str, tokens: List[str]):
        """Send cached tick data immediately to user."""
        websocket = self._connected_clients.get(str(user_id))
        if not websocket:
            return

        cached_ticks = []
        for token in tokens:
            if token in self._latest_ticks:
                cached_ticks.append(self._latest_ticks[token])

        if cached_ticks:
            try:
                await websocket.send_json({"type": "ticks", "data": cached_ticks})
            except Exception as e:
                logger.warning(f"[SmartAPI] Failed to send cached ticks to {user_id}: {e}")

    async def unsubscribe(self, tokens: List[str], user_id: str, exchange: str = "NFO"):
        """
        Unsubscribe from instrument tokens for a user.

        Args:
            tokens: List of instrument tokens
            user_id: User identifier
            exchange: Exchange
        """
        user_id = str(user_id)
        tokens_set = set(tokens)

        # Remove from user's subscriptions
        if user_id in self._user_subscriptions:
            self._user_subscriptions[user_id] -= tokens_set

        # Cleanup tokens no one is subscribed to
        self._cleanup_subscriptions(tokens_set, exchange)

        logger.info(f"[SmartAPI] User {user_id} unsubscribed from {len(tokens)} tokens")

    def _cleanup_subscriptions(self, tokens: Set[str], exchange: str = "NFO"):
        """Unsubscribe from SmartAPI for tokens no user needs."""
        # Find which tokens are still needed by any user
        all_user_tokens = set()
        for user_tokens in self._user_subscriptions.values():
            all_user_tokens.update(user_tokens)

        # Tokens to unsubscribe
        tokens_to_remove = tokens - all_user_tokens

        if tokens_to_remove and self.is_connected and self.sws:
            if exchange in self._subscribed_tokens:
                self._subscribed_tokens[exchange] -= tokens_to_remove

            logger.info(f"[SmartAPI] Unsubscribing from {len(tokens_to_remove)} unused tokens")

            token_list = [{
                "exchangeType": self.EXCHANGE_TYPES.get(exchange, 2),
                "tokens": list(tokens_to_remove)
            }]

            try:
                self.sws.unsubscribe("algochanakya", 2, token_list)
            except Exception as e:
                logger.warning(f"[SmartAPI] Unsubscription error: {e}")

    def _resubscribe_all(self):
        """Resubscribe to all tokens after reconnection."""
        for exchange, tokens in self._subscribed_tokens.items():
            if tokens:
                token_list = [{
                    "exchangeType": self.EXCHANGE_TYPES.get(exchange, 2),
                    "tokens": list(tokens)
                }]
                try:
                    self.sws.subscribe("algochanakya", 2, token_list)
                except Exception as e:
                    logger.error(f"[SmartAPI] Resubscription error for {exchange}: {e}")

    def get_latest_tick(self, token: str) -> Optional[dict]:
        """Get the latest tick data for an instrument."""
        return self._latest_ticks.get(token)

    async def _reconnect(self):
        """Attempt to reconnect after delay."""
        await asyncio.sleep(5)

        if not self.is_connected and self.jwt_token:
            logger.info("[SmartAPI] Attempting to reconnect...")
            try:
                await self.connect(
                    self.jwt_token,
                    self.api_key,
                    self.client_id,
                    self.feed_token
                )
            except Exception as e:
                logger.error(f"[SmartAPI] Reconnection failed: {e}")

    def disconnect(self):
        """Disconnect from SmartAPI WebSocket."""
        try:
            if self.sws:
                self.sws.close_connection()
                self.is_connected = False
                logger.info("[SmartAPI] WebSocket disconnected")
        except Exception as e:
            logger.error(f"[SmartAPI] Error disconnecting: {e}")


# Global singleton instance
smartapi_ticker_service = SmartAPITickerService()
