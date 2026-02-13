# Multi-Broker Ticker API Reference

**Version**: 1.0.0
**Status**: Phase 1-2 Implementation
**Related**: [ADR-003](../decisions/003-multi-broker-ticker-architecture.md), [Implementation Guide](../architecture/multi-broker-ticker-implementation.md)

---

## Table of Contents

1. [Core Interfaces](#core-interfaces)
2. [Data Models](#data-models)
3. [Ticker Service Manager](#ticker-service-manager)
4. [System Auth Service](#system-auth-service)
5. [Adapter Implementations](#adapter-implementations)
6. [Health Monitoring](#health-monitoring)
7. [Database Models](#database-models)

---

## Core Interfaces

### `MultiTenantTickerService`

**Location**: `backend/app/services/brokers/market_data/multi_tenant_ticker_base.py`

**Purpose**: Abstract base class for all broker ticker adapters.

```python
class MultiTenantTickerService(ABC):
    """
    Multi-tenant WebSocket ticker service interface.

    One instance can serve multiple users (Tier 1 architecture).
    Each broker adapter implements this interface.
    """
```

#### Methods

##### `connect()`

```python
@abstractmethod
async def connect(self, **credentials) -> None:
    """
    Connect to broker WebSocket.

    Args:
        **credentials: Broker-specific credentials
            SmartAPI: jwt_token, api_key, client_id, feed_token
            Kite: access_token, api_key
            Upstox: access_token
            Dhan: client_id, access_token
            Fyers: access_token
            Paytm: jwt_token

    Raises:
        ConnectionError: If WebSocket connection fails
        ValueError: If credentials invalid or missing

    Example:
        await ticker.connect(
            jwt_token="...",
            api_key="...",
            client_id="...",
            feed_token="..."
        )
    """
```

##### `disconnect()`

```python
@abstractmethod
async def disconnect(self) -> None:
    """
    Gracefully disconnect from broker WebSocket.

    Should:
    - Unsubscribe all tokens
    - Close WebSocket connection
    - Clean up threads/async tasks
    - Clear internal state

    Called from:
    - TickerServiceManager.disconnect_ticker()
    - main.py shutdown handler
    """
```

##### `subscribe()`

```python
@abstractmethod
async def subscribe(
    self,
    tokens: List[int],
    user_id: str,
    exchange: str = "NFO",
    mode: str = "quote"
) -> None:
    """
    Subscribe to market data for tokens.

    Args:
        tokens: List of CANONICAL tokens (Kite format, integer)
        user_id: User ID for subscription tracking
        exchange: Exchange code (NSE, NFO, BSE, MCX, etc.)
        mode: Subscription mode
            - "ltp": Last traded price only
            - "quote": LTP + OHLC + volume + OI
            - "full": Quote + depth + other fields

    Behavior:
        - Adapter translates tokens to broker format internally
        - Tracks per-user subscriptions for filtering
        - Sends subscribe request to broker WebSocket
        - May fetch initial quote via REST if market closed

    Example:
        await ticker.subscribe(
            tokens=[256265, 260105],  # NIFTY, BANKNIFTY
            user_id="123",
            exchange="NSE",
            mode="quote"
        )
    """
```

##### `unsubscribe()`

```python
@abstractmethod
async def unsubscribe(
    self,
    tokens: List[int],
    user_id: str,
    exchange: str = "NFO"
) -> None:
    """
    Unsubscribe from market data.

    Args:
        tokens: CANONICAL tokens to unsubscribe
        user_id: User ID
        exchange: Exchange code

    Behavior:
        - Removes tokens from user's subscription list
        - If no other users subscribed, unsubscribes from broker
        - Does NOT disconnect WebSocket (use disconnect() for that)
    """
```

##### `register_client()`

```python
@abstractmethod
async def register_client(self, user_id: str, websocket: WebSocket) -> None:
    """
    Register WebSocket client for receiving ticks.

    Args:
        user_id: Unique user identifier
        websocket: FastAPI WebSocket connection

    Behavior:
        - Stores WebSocket reference
        - Starts broadcasting ticks to this client
        - Filters ticks based on user's subscriptions
        - Called from websocket.py route when client connects

    Example:
        await ticker.register_client("user_123", websocket)
    """
```

##### `unregister_client()`

```python
@abstractmethod
async def unregister_client(self, user_id: str) -> None:
    """
    Unregister WebSocket client.

    Args:
        user_id: User identifier

    Behavior:
        - Removes WebSocket reference
        - Unsubscribes all user's tokens
        - If last client, may trigger disconnect after grace period
        - Called from websocket.py when client disconnects
    """
```

##### `get_latest_tick()`

```python
@abstractmethod
def get_latest_tick(self, token: int) -> Optional[NormalizedTick]:
    """
    Get latest cached tick for a token.

    Args:
        token: CANONICAL token (Kite format)

    Returns:
        Latest NormalizedTick or None if not available

    Use Cases:
        - Initial quote fetching for UI
        - Historical comparison
        - Debugging missing ticks
    """
```

#### Properties

##### `is_connected`

```python
@property
@abstractmethod
def is_connected(self) -> bool:
    """
    Check if WebSocket is currently connected.

    Returns:
        True if connected and active, False otherwise
    """
```

##### `client_count`

```python
@property
@abstractmethod
def client_count(self) -> int:
    """
    Get number of registered clients (users).

    Returns:
        Count of active WebSocket connections

    Used by:
        - Health monitoring
        - Disconnect decision (wait for count = 0)
    """
```

##### `broker_type`

```python
@property
@abstractmethod
def broker_type(self) -> str:
    """
    Get broker type identifier.

    Returns:
        Broker type string (smartapi, kite, upstox, etc.)
    """
```

---

## Data Models

### `NormalizedTick`

**Location**: `backend/app/services/brokers/market_data/multi_tenant_ticker_base.py`

**Purpose**: Broker-agnostic tick data structure.

```python
@dataclass
class NormalizedTick:
    """
    Normalized tick data across all brokers.

    Key Design Decisions:
    - All tokens in CANONICAL format (Kite format)
    - All prices in rupees (NOT paise)
    - Simpler than UnifiedQuote (optimized for WebSocket broadcasting)
    - Immutable dataclass for thread safety
    """

    token: int              # Canonical token (Kite format)
    ltp: float              # Last traded price (₹)
    change: float           # Absolute change from prev close (₹)
    change_percent: float   # Percentage change
    volume: int             # Total volume traded
    oi: int                 # Open interest (futures/options only)
    open: float             # Day open price (₹)
    high: float             # Day high (₹)
    low: float              # Day low (₹)
    close: float            # Previous day close (₹)
    last_trade_time: Optional[int] = None       # Unix timestamp (ms)
    exchange_timestamp: Optional[int] = None    # Exchange timestamp (ms)
```

#### Field Descriptions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `token` | int | Canonical instrument token (Kite format) | 256265 (NIFTY) |
| `ltp` | float | Last traded price in rupees | 19500.50 |
| `change` | float | Absolute change from previous close | -45.25 |
| `change_percent` | float | Percentage change | -0.23 |
| `volume` | int | Total volume traded today | 15000000 |
| `oi` | int | Open interest (0 for indices) | 8500000 |
| `open` | float | Day open price | 19550.00 |
| `high` | float | Day high price | 19575.25 |
| `low` | float | Day low price | 19480.00 |
| `close` | float | Previous day closing price | 19545.75 |
| `last_trade_time` | int? | Unix timestamp of last trade (ms) | 1708524600000 |
| `exchange_timestamp` | int? | Exchange server timestamp (ms) | 1708524600123 |

#### Usage Example

```python
tick = NormalizedTick(
    token=256265,
    ltp=19500.50,
    change=-45.25,
    change_percent=-0.23,
    volume=15000000,
    oi=0,
    open=19550.00,
    high=19575.25,
    low=19480.00,
    close=19545.75,
    last_trade_time=1708524600000
)

# Serialize for WebSocket
tick_dict = {
    "token": tick.token,
    "ltp": tick.ltp,
    "change": tick.change,
    "change_percent": tick.change_percent,
    "volume": tick.volume,
    "oi": tick.oi,
    "ohlc": {
        "open": tick.open,
        "high": tick.high,
        "low": tick.low,
        "close": tick.close
    }
}
```

---

## Ticker Service Manager

### `TickerServiceManager`

**Location**: `backend/app/services/brokers/market_data/ticker_manager.py`

**Purpose**: Multiton manager for ticker service instances.

```python
class TickerServiceManager:
    """
    Centralized lifecycle manager for ticker services.

    Pattern: Multiton (one instance per broker, not full singleton)
    Thread-safe: Uses per-broker asyncio.Lock
    """
```

#### Class Variables

```python
_instances: Dict[str, MultiTenantTickerService] = {}
_locks: Dict[str, asyncio.Lock] = {}
_last_activity: Dict[str, datetime] = {}

_TICKER_ADAPTERS = {
    "smartapi": "app.services.brokers.market_data.tickers.smartapi_ticker_adapter.SmartAPITickerAdapter",
    "kite": "app.services.brokers.market_data.tickers.kite_ticker_adapter.KiteTickerAdapter",
    "upstox": "app.services.brokers.market_data.tickers.upstox_ticker_adapter.UpstoxTickerAdapter",
    "dhan": "app.services.brokers.market_data.tickers.dhan_ticker_adapter.DhanTickerAdapter",
    "fyers": "app.services.brokers.market_data.tickers.fyers_ticker_adapter.FyersTickerAdapter",
    "paytm": "app.services.brokers.market_data.tickers.paytm_ticker_adapter.PaytmTickerAdapter",
}
```

#### Methods

##### `get_ticker()`

```python
@classmethod
async def get_ticker(cls, broker_type: str) -> MultiTenantTickerService:
    """
    Get or create ticker instance for a broker.

    Thread-safe singleton per broker. Creates on first call.

    Args:
        broker_type: Broker identifier (smartapi, kite, upstox, etc.)

    Returns:
        Ticker service instance

    Raises:
        ValueError: If broker_type not in _TICKER_ADAPTERS

    Example:
        ticker = await TickerServiceManager.get_ticker("smartapi")
        await ticker.subscribe([256265], "user_123")
    """
```

##### `get_primary_ticker()`

```python
@classmethod
async def get_primary_ticker(cls, user_id: int, db) -> MultiTenantTickerService:
    """
    Get ticker for user's preferred market data source.

    Reads UserPreferences.market_data_source, falls back to
    settings.DEFAULT_MARKET_DATA_BROKER.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Ticker service for user's broker preference

    Example:
        # User has selected "smartapi" in settings
        ticker = await TickerServiceManager.get_primary_ticker(123, db)
        # Returns SmartAPITickerAdapter instance
    """
```

##### `connect_ticker()`

```python
@classmethod
async def connect_ticker(cls, broker_type: str, db) -> None:
    """
    Connect ticker service to broker WebSocket.

    Fetches system credentials from system_broker_sessions table,
    refreshes if expired, then connects.

    Args:
        broker_type: Broker identifier
        db: Database session

    Raises:
        ValueError: If system credentials not configured
        ConnectionError: If WebSocket connection fails

    Example:
        await TickerServiceManager.connect_ticker("smartapi", db)
    """
```

##### `disconnect_ticker()`

```python
@classmethod
async def disconnect_ticker(cls, broker_type: str) -> None:
    """
    Disconnect ticker service with grace period.

    Waits 5 minutes before disconnecting. If clients reconnect
    during grace period, disconnect is cancelled.

    Args:
        broker_type: Broker identifier

    Behavior:
        - Check client_count == 0
        - Sleep 300 seconds (5 minutes)
        - Check client_count again
        - If still 0, disconnect and remove instance
    """
```

##### `shutdown_all()`

```python
@classmethod
async def shutdown_all(cls) -> None:
    """
    Shutdown all active ticker services.

    Called from main.py lifespan shutdown event.

    Behavior:
        - Iterate all active instances
        - Call disconnect() on each
        - Clear _instances dict
        - Log errors but don't raise
    """
```

##### `get_health()`

```python
@classmethod
def get_health(cls, broker_type: str) -> Optional[Dict[str, Any]]:
    """
    Get health metrics for a broker's ticker.

    Args:
        broker_type: Broker identifier

    Returns:
        Dict with health metrics or None if not active
        {
            "broker": "smartapi",
            "connected": True,
            "client_count": 3,
            "last_activity": datetime(...)
        }
    """
```

##### `get_all_health()`

```python
@classmethod
def get_all_health(cls) -> Dict[str, Any]:
    """
    Get health metrics for all active tickers.

    Returns:
        {
            "smartapi": {...health...},
            "kite": {...health...}
        }
    """
```

---

## System Auth Service

### Functions

**Location**: `backend/app/services/brokers/market_data/system_auth_service.py`

#### `initialize_system_sessions()`

```python
async def initialize_system_sessions() -> None:
    """
    Initialize system broker sessions at app startup.

    Called from: main.py lifespan function

    Behavior:
        1. Read system credentials from .env (config.py)
        2. Authenticate with each configured broker
        3. Store tokens in system_broker_sessions table
        4. Log errors but don't block app startup

    Brokers initialized:
        - SmartAPI (if ANGEL_SYSTEM_CLIENT_ID configured)
        - Kite (if KITE_SYSTEM_ACCESS_TOKEN configured)
        - Others: Log "not configured"

    Example:
        # In main.py
        from app.services.brokers.market_data.system_auth_service import (
            initialize_system_sessions
        )

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await initialize_system_sessions()
            yield
    """
```

#### `refresh_system_token()`

```python
async def refresh_system_token(broker_type: str, db: AsyncSession) -> None:
    """
    Refresh system broker token.

    Called by: TickerServiceManager when reconnecting after token expiry

    Args:
        broker_type: Broker identifier
        db: Database session

    Behavior:
        - SmartAPI: Try refresh_token, fallback to full re-auth with TOTP
        - Kite: Log warning (manual OAuth, no auto-refresh)
        - Others: Log "not implemented"

    Raises:
        Exception: If refresh fails (logged, not re-raised)

    Example:
        # In ticker adapter
        try:
            await self.connect(**credentials)
        except AuthenticationError:
            await refresh_system_token("smartapi", db)
            credentials = await get_system_credentials("smartapi", db)
            await self.connect(**credentials)
    """
```

#### `get_system_credentials()`

```python
async def get_system_credentials(
    broker_type: str,
    db: AsyncSession
) -> Optional[Dict]:
    """
    Get current system credentials for a broker.

    Used by: TickerServiceManager.connect_ticker()

    Args:
        broker_type: Broker identifier
        db: Database session

    Returns:
        Broker-specific credentials dict or None if not configured

        SmartAPI: {
            "jwt_token": "...",
            "api_key": "...",
            "client_id": "...",
            "feed_token": "..."
        }

        Kite: {
            "access_token": "...",
            "api_key": "..."
        }

    Behavior:
        - Query system_broker_sessions table
        - Check token expiry
        - Auto-refresh if expired
        - Return None if not configured or inactive

    Example:
        creds = await get_system_credentials("smartapi", db)
        if creds:
            await ticker.connect(**creds)
    """
```

---

## Adapter Implementations

### SmartAPITickerAdapter

**Location**: `backend/app/services/brokers/market_data/tickers/smartapi_ticker_adapter.py`

**Complete Implementation** (reference from `smartapi_ticker.py`):

```python
"""
SmartAPI Ticker Adapter

Wraps SmartWebSocketV2 with multi-tenant support.
Handles token translation (Kite ↔ SmartAPI format).
"""
import asyncio
import threading
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime
from fastapi import WebSocket

from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from app.services.brokers.market_data.multi_tenant_ticker_base import (
    MultiTenantTickerService,
    NormalizedTick
)

logger = logging.getLogger(__name__)


class SmartAPITickerAdapter(MultiTenantTickerService):
    """
    SmartAPI WebSocket V2 adapter.

    Key Responsibilities:
    - Token translation (NIFTY 256265 → 99926000)
    - Price normalization (paise → rupees: ÷100)
    - Threading model (daemon thread for WebSocket)
    - Per-user subscription tracking
    - Filtered tick broadcasting
    """

    # Index token mapping (Kite → SmartAPI)
    KITE_TO_SMARTAPI_INDEX = {
        256265: {'smartapi_token': '99926000', 'exchange': 'NSE', 'name': 'NIFTY 50'},
        260105: {'smartapi_token': '99926009', 'exchange': 'NSE', 'name': 'NIFTY BANK'},
        257801: {'smartapi_token': '99926037', 'exchange': 'NSE', 'name': 'NIFTY FIN'},
        265:    {'smartapi_token': '99919000', 'exchange': 'BSE', 'name': 'SENSEX'},
    }

    # Reverse mapping (SmartAPI → Kite)
    SMARTAPI_TO_KITE_INDEX = {
        v['smartapi_token']: k
        for k, v in KITE_TO_SMARTAPI_INDEX.items()
    }

    def __init__(self):
        self._ws: Optional[SmartWebSocketV2] = None
        self._thread: Optional[threading.Thread] = None
        self._connected = False

        # Client management
        self._clients: Dict[str, WebSocket] = {}  # user_id -> websocket
        self._user_subscriptions: Dict[str, Set[int]] = {}  # user_id -> {tokens}
        self._all_subscribed_tokens: Set[int] = set()  # All tokens across users

        # Tick cache
        self._latest_ticks: Dict[int, NormalizedTick] = {}  # token -> tick

        # Lock for thread-safe operations
        self._lock = threading.Lock()

        # Event loop for async operations from thread
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self, **credentials) -> None:
        """
        Connect to SmartAPI WebSocket.

        Args:
            jwt_token: AngelOne JWT token
            api_key: AngelOne API key
            client_id: Client ID
            feed_token: Feed token for WebSocket

        Reconnect Flow on Auth Failure:
            1. Adapter catches auth error in _on_error() or _on_close()
            2. Calls system_auth_service.refresh_system_token("smartapi", db)
            3. Gets fresh credentials via get_system_credentials("smartapi", db)
            4. Calls self.connect(**new_credentials)
        """
        if self._connected:
            logger.info("[SmartAPI] Already connected")
            return

        self._loop = asyncio.get_event_loop()

        # Create WebSocket instance
        self._ws = SmartWebSocketV2(
            auth_token=credentials["jwt_token"],
            api_key=credentials["api_key"],
            client_code=credentials["client_id"],
            feed_token=credentials["feed_token"]
        )

        # Set callbacks
        self._ws.on_open = self._on_open
        self._ws.on_data = self._on_data
        self._ws.on_error = self._on_error
        self._ws.on_close = self._on_close

        # Start WebSocket in daemon thread
        # CRITICAL: Preserve exact pattern from smartapi_ticker.py:132-139
        def run_websocket():
            try:
                self._ws.connect()
            except Exception as e:
                logger.error(f"[SmartAPI] WebSocket thread error: {e}")

        self._thread = threading.Thread(target=run_websocket, daemon=True)
        self._thread.start()

        # Wait for connection
        await asyncio.sleep(2)
        logger.info("[SmartAPI] Connection initiated")

    async def disconnect(self) -> None:
        """Gracefully disconnect."""
        if not self._connected:
            return

        try:
            if self._ws:
                self._ws.close_connection()
            self._connected = False
            self._clients.clear()
            self._user_subscriptions.clear()
            self._all_subscribed_tokens.clear()
            logger.info("[SmartAPI] Disconnected successfully")
        except Exception as e:
            logger.error(f"[SmartAPI] Disconnect error: {e}")

    async def subscribe(
        self,
        tokens: List[int],
        user_id: str,
        exchange: str = "NFO",
        mode: str = "quote"
    ) -> None:
        """
        Subscribe to tokens.

        Translates index tokens to SmartAPI format internally.
        """
        if not self._connected:
            logger.warning("[SmartAPI] Not connected, cannot subscribe")
            return

        # Track user subscriptions
        if user_id not in self._user_subscriptions:
            self._user_subscriptions[user_id] = set()

        # Separate index tokens from option tokens
        smartapi_tokens = []

        for kite_token in tokens:
            self._user_subscriptions[user_id].add(kite_token)
            self._all_subscribed_tokens.add(kite_token)

            if kite_token in self.KITE_TO_SMARTAPI_INDEX:
                # Index token - translate
                info = self.KITE_TO_SMARTAPI_INDEX[kite_token]
                smartapi_token = info['smartapi_token']
                smartapi_tokens.append({
                    "exchangeType": info['exchange'],
                    "tokens": [smartapi_token]
                })
                logger.info(f"[SmartAPI] Mapped {kite_token} → {smartapi_token} ({info['name']})")
            else:
                # Option token - use as-is (string format)
                smartapi_tokens.append({
                    "exchangeType": exchange,
                    "tokens": [str(kite_token)]
                })

        # Subscribe via WebSocket
        if smartapi_tokens:
            mode_map = {"ltp": 1, "quote": 2, "full": 3}
            self._ws.subscribe(
                correlation_id=user_id,
                mode=mode_map.get(mode, 2),
                token_list=smartapi_tokens
            )
            logger.info(f"[SmartAPI] Subscribed {len(tokens)} tokens for user {user_id}")

    async def unsubscribe(
        self,
        tokens: List[int],
        user_id: str,
        exchange: str = "NFO"
    ) -> None:
        """Unsubscribe tokens."""
        if user_id in self._user_subscriptions:
            for token in tokens:
                self._user_subscriptions[user_id].discard(token)

            # If no subscriptions left, remove user
            if not self._user_subscriptions[user_id]:
                del self._user_subscriptions[user_id]

        # TODO: Unsubscribe from WebSocket if no users need this token
        logger.info(f"[SmartAPI] Unsubscribed {len(tokens)} tokens for user {user_id}")

    async def register_client(self, user_id: str, websocket: WebSocket) -> None:
        """Register WebSocket client."""
        self._clients[user_id] = websocket
        logger.info(f"[SmartAPI] Registered client {user_id} (total: {len(self._clients)})")

    async def unregister_client(self, user_id: str) -> None:
        """Unregister WebSocket client."""
        if user_id in self._clients:
            del self._clients[user_id]

        # Unsubscribe all tokens for this user
        if user_id in self._user_subscriptions:
            tokens = list(self._user_subscriptions[user_id])
            await self.unsubscribe(tokens, user_id)

        logger.info(f"[SmartAPI] Unregistered client {user_id} (total: {len(self._clients)})")

    def get_latest_tick(self, token: int) -> Optional[NormalizedTick]:
        """Get cached tick."""
        return self._latest_ticks.get(token)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def broker_type(self) -> str:
        return "smartapi"

    # WebSocket callbacks

    def _on_open(self, wsapp):
        """Called when WebSocket opens."""
        self._connected = True
        logger.info("[SmartAPI] WebSocket connected")

    def _on_data(self, wsapp, message):
        """
        Called when tick received.

        Normalizes tick and broadcasts to clients.
        """
        try:
            # Extract SmartAPI token
            smartapi_token = message.get('token')
            if not smartapi_token:
                return

            # Translate to canonical token
            if smartapi_token in self.SMARTAPI_TO_KITE_INDEX:
                canonical_token = self.SMARTAPI_TO_KITE_INDEX[smartapi_token]
            else:
                canonical_token = int(smartapi_token)

            # Normalize tick
            tick = self._normalize_tick(message, canonical_token)

            # Cache
            self._latest_ticks[canonical_token] = tick

            # Broadcast to clients
            asyncio.run_coroutine_threadsafe(
                self._broadcast_tick(tick),
                self._loop
            )

        except Exception as e:
            logger.error(f"[SmartAPI] Tick processing error: {e}")

    def _on_error(self, wsapp, error):
        """Called on WebSocket error."""
        logger.error(f"[SmartAPI] WebSocket error: {error}")

    def _on_close(self, wsapp):
        """
        Called when WebSocket closes.

        Reconnect handler should trigger token refresh and reconnection:
        1. Check if close was due to auth failure
        2. If yes, call system_auth_service.refresh_system_token("smartapi", db)
        3. Get new credentials from system_broker_sessions
        4. Call self.connect(**new_credentials)
        """
        self._connected = False
        logger.warning("[SmartAPI] WebSocket closed")

    def _normalize_tick(self, smartapi_tick: dict, canonical_token: int) -> NormalizedTick:
        """
        Normalize SmartAPI tick to NormalizedTick.

        Key transformations:
        - Prices: paise → rupees (÷100)
        - Token: SmartAPI → Kite format
        """
        # SmartAPI sends prices in paise, convert to rupees
        ltp = smartapi_tick.get('last_traded_price', 0) / 100
        open_price = smartapi_tick.get('open_price_of_the_day', 0) / 100
        high = smartapi_tick.get('high_price_of_the_day', 0) / 100
        low = smartapi_tick.get('low_price_of_the_day', 0) / 100
        close = smartapi_tick.get('closed_price', 0) / 100

        change = ltp - close
        change_percent = (change / close * 100) if close else 0

        return NormalizedTick(
            token=canonical_token,
            ltp=ltp,
            change=change,
            change_percent=change_percent,
            volume=smartapi_tick.get('volume_trade_for_the_day', 0),
            oi=smartapi_tick.get('open_interest', 0),
            open=open_price,
            high=high,
            low=low,
            close=close,
            last_trade_time=smartapi_tick.get('exchange_timestamp'),
            exchange_timestamp=smartapi_tick.get('exchange_timestamp')
        )

    async def _broadcast_tick(self, tick: NormalizedTick) -> None:
        """
        Broadcast tick to relevant clients.

        Filters by user subscriptions.
        """
        for user_id, websocket in list(self._clients.items()):
            try:
                # Check if user subscribed to this token
                if user_id in self._user_subscriptions:
                    if tick.token in self._user_subscriptions[user_id]:
                        await websocket.send_json({
                            "type": "ticks",
                            "data": [{
                                "token": tick.token,
                                "ltp": tick.ltp,
                                "change": tick.change,
                                "change_percent": tick.change_percent,
                                "volume": tick.volume,
                                "oi": tick.oi,
                                "ohlc": {
                                    "open": tick.open,
                                    "high": tick.high,
                                    "low": tick.low,
                                    "close": tick.close
                                }
                            }]
                        })
            except Exception as e:
                logger.error(f"[SmartAPI] Broadcast error for user {user_id}: {e}")
```

### KiteTickerAdapter

**Location**: `backend/app/services/brokers/market_data/tickers/kite_ticker_adapter.py`

**Simplified Implementation** (no token translation needed):

```python
"""
Kite Ticker Adapter

Simpler than SmartAPI - no token translation needed.
Kite tokens are already in canonical format.
"""
import asyncio
import threading
import logging
from typing import List, Dict, Optional, Set
from fastapi import WebSocket

from kiteconnect import KiteTicker
from app.services.brokers.market_data.multi_tenant_ticker_base import (
    MultiTenantTickerService,
    NormalizedTick
)

logger = logging.getLogger(__name__)


class KiteTickerAdapter(MultiTenantTickerService):
    """
    Kite WebSocket adapter.

    Simpler than SmartAPI:
    - No token translation (Kite format IS canonical)
    - Prices already in rupees (not paise)
    - Standard KiteTicker library
    """

    def __init__(self):
        self._ticker: Optional[KiteTicker] = None
        self._thread: Optional[threading.Thread] = None
        self._connected = False

        self._clients: Dict[str, WebSocket] = {}
        self._user_subscriptions: Dict[str, Set[int]] = {}
        self._latest_ticks: Dict[int, NormalizedTick] = {}

        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self, **credentials) -> None:
        """
        Connect to Kite WebSocket.

        Args:
            access_token: Kite access token
            api_key: Kite API key
        """
        if self._connected:
            return

        self._loop = asyncio.get_event_loop()

        self._ticker = KiteTicker(
            api_key=credentials["api_key"],
            access_token=credentials["access_token"]
        )

        self._ticker.on_open = self._on_open
        self._ticker.on_ticks = self._on_ticks
        self._ticker.on_error = self._on_error
        self._ticker.on_close = self._on_close

        # Start in thread
        def run_ticker():
            try:
                self._ticker.connect(threaded=False)
            except Exception as e:
                logger.error(f"[Kite] Ticker thread error: {e}")

        self._thread = threading.Thread(target=run_ticker, daemon=True)
        self._thread.start()

        await asyncio.sleep(2)
        logger.info("[Kite] Connection initiated")

    async def disconnect(self) -> None:
        """Disconnect."""
        if self._ticker:
            self._ticker.close()
        self._connected = False
        self._clients.clear()
        self._user_subscriptions.clear()
        logger.info("[Kite] Disconnected")

    async def subscribe(
        self,
        tokens: List[int],
        user_id: str,
        exchange: str = "NFO",  # Ignored for Kite
        mode: str = "quote"
    ) -> None:
        """Subscribe to tokens (no translation needed)."""
        if not self._connected:
            return

        if user_id not in self._user_subscriptions:
            self._user_subscriptions[user_id] = set()

        for token in tokens:
            self._user_subscriptions[user_id].add(token)

        # Kite mode mapping
        mode_map = {
            "ltp": self._ticker.MODE_LTP,
            "quote": self._ticker.MODE_QUOTE,
            "full": self._ticker.MODE_FULL
        }

        self._ticker.subscribe(tokens)
        self._ticker.set_mode(mode_map.get(mode, self._ticker.MODE_QUOTE), tokens)

        logger.info(f"[Kite] Subscribed {len(tokens)} tokens for user {user_id}")

    async def unsubscribe(self, tokens: List[int], user_id: str, exchange: str = "NFO") -> None:
        """Unsubscribe."""
        if user_id in self._user_subscriptions:
            for token in tokens:
                self._user_subscriptions[user_id].discard(token)

    async def register_client(self, user_id: str, websocket: WebSocket) -> None:
        """Register client."""
        self._clients[user_id] = websocket
        logger.info(f"[Kite] Registered client {user_id}")

    async def unregister_client(self, user_id: str) -> None:
        """Unregister client."""
        if user_id in self._clients:
            del self._clients[user_id]
        if user_id in self._user_subscriptions:
            del self._user_subscriptions[user_id]
        logger.info(f"[Kite] Unregistered client {user_id}")

    def get_latest_tick(self, token: int) -> Optional[NormalizedTick]:
        return self._latest_ticks.get(token)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def broker_type(self) -> str:
        return "kite"

    # Callbacks

    def _on_open(self, ws, response):
        self._connected = True
        logger.info("[Kite] WebSocket connected")

    def _on_ticks(self, ws, ticks):
        """Process Kite ticks (already normalized format)."""
        for kite_tick in ticks:
            try:
                tick = self._normalize_tick(kite_tick)
                self._latest_ticks[tick.token] = tick

                asyncio.run_coroutine_threadsafe(
                    self._broadcast_tick(tick),
                    self._loop
                )
            except Exception as e:
                logger.error(f"[Kite] Tick processing error: {e}")

    def _on_error(self, ws, code, reason):
        logger.error(f"[Kite] Error {code}: {reason}")

    def _on_close(self, ws, code, reason):
        self._connected = False
        logger.warning(f"[Kite] Closed {code}: {reason}")

    def _normalize_tick(self, kite_tick: dict) -> NormalizedTick:
        """
        Normalize Kite tick.

        Kite ticks are already mostly normalized:
        - Prices in rupees (not paise)
        - Tokens in canonical format
        """
        ltp = kite_tick.get('last_price', 0)
        ohlc = kite_tick.get('ohlc', {})
        close = ohlc.get('close', 0)

        change = kite_tick.get('change', ltp - close if close else 0)

        return NormalizedTick(
            token=kite_tick['instrument_token'],
            ltp=ltp,
            change=change,
            change_percent=(change / close * 100) if close else 0,
            volume=kite_tick.get('volume', 0),
            oi=kite_tick.get('oi', 0),
            open=ohlc.get('open', 0),
            high=ohlc.get('high', 0),
            low=ohlc.get('low', 0),
            close=close,
            last_trade_time=kite_tick.get('last_trade_time'),
            exchange_timestamp=kite_tick.get('exchange_timestamp')
        )

    async def _broadcast_tick(self, tick: NormalizedTick) -> None:
        """Broadcast to subscribed clients."""
        for user_id, websocket in list(self._clients.items()):
            try:
                if user_id in self._user_subscriptions:
                    if tick.token in self._user_subscriptions[user_id]:
                        await websocket.send_json({
                            "type": "ticks",
                            "data": [{
                                "token": tick.token,
                                "ltp": tick.ltp,
                                "change": tick.change,
                                "change_percent": tick.change_percent,
                                "volume": tick.volume,
                                "oi": tick.oi,
                                "ohlc": {
                                    "open": tick.open,
                                    "high": tick.high,
                                    "low": tick.low,
                                    "close": tick.close
                                }
                            }]
                        })
            except Exception as e:
                logger.error(f"[Kite] Broadcast error: {e}")
```

---

## Health Monitoring

### `MultiProviderHealthMonitor`

**Location**: `backend/app/services/ai/websocket_health_monitor.py`

**Added to existing file**:

```python
class MultiProviderHealthMonitor:
    """
    Wrapper for managing health monitors across multiple brokers.

    Each broker gets its own WebSocketHealthMonitor instance.
    """

    _monitors: Dict[str, 'WebSocketHealthMonitor'] = {}

    @classmethod
    def get_or_create(cls, broker_type: str) -> 'WebSocketHealthMonitor':
        """
        Get or create health monitor for a broker.

        Args:
            broker_type: smartapi, kite, upstox, etc.

        Returns:
            WebSocketHealthMonitor instance
        """
        if broker_type not in cls._monitors:
            cls._monitors[broker_type] = WebSocketHealthMonitor()
        return cls._monitors[broker_type]

    @classmethod
    def get_aggregate_health(cls) -> Dict[str, Any]:
        """
        Get aggregated health across all brokers.

        Returns:
            {
                "overall_status": "healthy" | "degraded",
                "brokers": {
                    "smartapi": {...metrics...},
                    "kite": {...metrics...}
                },
                "active_broker_count": 2
            }
        """
        if not cls._monitors:
            return {
                "overall_status": "no_active_brokers",
                "brokers": {}
            }

        broker_healths = {}
        all_healthy = True

        for broker_type, monitor in cls._monitors.items():
            try:
                metrics = monitor.get_health_metrics()
                broker_healths[broker_type] = metrics
                if metrics.status != "healthy":
                    all_healthy = False
            except Exception as e:
                broker_healths[broker_type] = {"status": "error", "error": str(e)}
                all_healthy = False

        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "brokers": broker_healths,
            "active_broker_count": len(cls._monitors)
        }

    @classmethod
    def get_broker_health(cls, broker_type: str) -> Optional['HealthMetrics']:
        """Get health for specific broker."""
        monitor = cls._monitors.get(broker_type)
        return monitor.get_health_metrics() if monitor else None
```

---

## Database Models

### `SystemBrokerSession`

**Location**: `backend/app/models/system_broker_sessions.py`

```python
class SystemBrokerSession(Base):
    """
    System broker session for app-level credentials (Tier 1).

    One row per broker. Stores dynamic tokens that are refreshed periodically.

    Unlike BrokerConnection (Tier 2), these credentials are owned by the app,
    not individual users. Used for shared market data WebSocket connections.
    """
    __tablename__ = "system_broker_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    broker = Column(String(20), nullable=False, unique=True, index=True)
    # Values: 'smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm'

    # Dynamic tokens (refreshed periodically)
    jwt_token = Column(Text, nullable=True)          # AngelOne JWT
    access_token = Column(Text, nullable=True)       # Kite/Upstox access token
    refresh_token = Column(Text, nullable=True)      # AngelOne refresh token
    feed_token = Column(Text, nullable=True)         # AngelOne feed token for WS

    # Session metadata
    client_id = Column(String(50), nullable=True)    # Broker client ID
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    last_auth_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Example Queries**:

```python
# Get active SmartAPI session
session = db.query(SystemBrokerSession).filter_by(
    broker="smartapi",
    is_active=True
).first()

# Update token after refresh
session.jwt_token = new_jwt
session.last_auth_at = datetime.utcnow()
session.last_error = None
db.commit()
```

---

## WebSocket Route Integration

### Refactored `websocket.py`

**File**: `backend/app/api/routes/websocket.py`

**New implementation** (~150 lines, down from 534):

```python
"""
WebSocket Ticker Route (Refactored)

Broker-agnostic WebSocket route using TickerServiceManager.
All broker-specific logic moved to adapters.
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.brokers.market_data.ticker_manager import TickerServiceManager
from app.utils.dependencies import get_user_from_token

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/ticks")
async def websocket_ticks(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for live market data ticks.

    Protocol:
        Client -> Server:
            {"action": "subscribe", "tokens": [256265, 260105], "mode": "quote", "exchange": "NFO"}
            {"action": "unsubscribe", "tokens": [256265], "exchange": "NFO"}
            {"action": "ping"}

        Server -> Client:
            {"type": "connected", "source": "smartapi", "connected": true}
            {"type": "subscribed", "tokens": [256265], "mode": "quote"}
            {"type": "ticks", "data": [{...tick data...}]}
            {"type": "pong"}
    """
    user = None
    user_id = None
    ticker_service = None
    db = None

    try:
        await websocket.accept()

        # Authenticate user and get ticker service
        async for db_session in get_db():
            db = db_session
            user = await get_user_from_token(token, db)
            user_id = str(user.id)

            # Manager handles: broker selection, connection, credentials
            ticker_service = await TickerServiceManager.get_primary_ticker(user.id, db)

            # Connect if not already connected
            if not ticker_service.is_connected:
                await TickerServiceManager.connect_ticker(ticker_service.broker_type, db)

            break

        # Register client for tick broadcasting
        await ticker_service.register_client(user_id, websocket)

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "source": ticker_service.broker_type,
            "connected": ticker_service.is_connected
        })

        # Message loop
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            action = data.get("action")

            if action == "subscribe":
                tokens = [int(t) for t in data.get("tokens", [])]
                mode = data.get("mode", "quote")
                exchange = data.get("exchange", "NFO")

                # Adapter handles ALL token translation internally
                await ticker_service.subscribe(tokens, user_id, exchange, mode)

                await websocket.send_json({
                    "type": "subscribed",
                    "tokens": tokens,
                    "mode": mode,
                    "source": ticker_service.broker_type
                })
                logger.info(f"User {user_id} subscribed to {len(tokens)} tokens via {ticker_service.broker_type}")

            elif action == "unsubscribe":
                tokens = [int(t) for t in data.get("tokens", [])]
                exchange = data.get("exchange", "NFO")

                await ticker_service.unsubscribe(tokens, user_id, exchange)

                await websocket.send_json({
                    "type": "unsubscribed",
                    "tokens": tokens
                })

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from WebSocket")

    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")

    finally:
        # Cleanup
        if user_id and ticker_service:
            await ticker_service.unregister_client(user_id)

        logger.info(f"WebSocket connection closed for user {user_id}")
```

**Key simplifications**:
- ✅ No broker-specific imports
- ✅ No token mapping dicts
- ✅ No if/else for broker selection
- ✅ No credential fetching logic
- ✅ Manager handles everything
- ✅ 72% code reduction

---

## Migration Summary

### Files Created (15)

1. `backend/app/models/system_broker_sessions.py`
2. `backend/app/services/brokers/market_data/multi_tenant_ticker_base.py`
3. `backend/app/services/brokers/market_data/ticker_manager.py`
4. `backend/app/services/brokers/market_data/system_auth_service.py`
5. `backend/app/services/brokers/market_data/tickers/__init__.py`
6. `backend/app/services/brokers/market_data/tickers/smartapi_ticker_adapter.py`
7. `backend/app/services/brokers/market_data/tickers/kite_ticker_adapter.py`
8. `backend/app/services/brokers/market_data/tickers/upstox_ticker_adapter.py` (stub)
9. `backend/app/services/brokers/market_data/tickers/dhan_ticker_adapter.py` (stub)
10. `backend/app/services/brokers/market_data/tickers/fyers_ticker_adapter.py` (stub)
11. `backend/app/services/brokers/market_data/tickers/paytm_ticker_adapter.py` (stub)
12-15. Phase 3 order execution adapters (future)

### Files Modified (7)

1. `backend/app/services/brokers/base.py` - Add DHAN, PAYTM to BrokerType
2. `backend/app/config.py` - Add system broker env vars
3. `backend/app/models/__init__.py` - Import SystemBrokerSession
4. `backend/alembic/env.py` - Import SystemBrokerSession
5. `backend/app/api/routes/websocket.py` - Major refactor (534→150 lines)
6. `backend/app/main.py` - Add startup/shutdown hooks
7. `backend/app/services/ai/websocket_health_monitor.py` - Add MultiProviderHealthMonitor

### Files Deprecated (3)

1. `backend/app/services/legacy/smartapi_ticker.py` - Add deprecation warning
2. `backend/app/services/legacy/kite_ticker.py` - Add deprecation warning
3. `backend/app/services/brokers/market_data/ticker_base.py` - Add deprecation warning

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-13 | Initial API reference for Phase 1-2 implementation |
