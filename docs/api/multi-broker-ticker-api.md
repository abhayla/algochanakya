# Multi-Broker Ticker API Reference

**Version**: 2.1.0 (Updated for 5-Component Design)
**Status**: ✅ **CURRENT** - Reflects TICKER-DESIGN-SPEC.md (Feb 14, 2026)
**Last Updated**: February 16, 2026
**Related**: [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md) | [Implementation Guide](../guides/TICKER-IMPLEMENTATION-GUIDE.md) | [ADR-003 v2 (Original)](../decisions/003-multi-broker-ticker-architecture.md)

**Key Updates from Original ADR-003 v2:**
- ✅ `NormalizedTick` uses `Decimal` for prices (not `float`) - **eliminates precision errors**
- ✅ Credentials managed in `TickerPool` (no separate `SystemCredentialManager`) - **5 components, not 6**
- ✅ Updated health score formula (latency 30%, tick_rate 30%, errors 20%, staleness 20%)
- ✅ Complete implementation guide available

---

## Table of Contents

1. [NormalizedTick](#1-normalizedtick) - **Updated: Decimal prices**
2. [TickerAdapter (Abstract Base)](#2-tickeradapter-abstract-base)
3. [SmartAPITickerAdapter](#3-smartapiticker-adapter)
4. [KiteTickerAdapter](#4-kiteticker-adapter)
5. [Stub Adapter Templates](#5-stub-adapter-templates)
6. [TickerPool](#6-tickerpool) - **Updated: Integrated credentials**
7. [TickerRouter](#7-tickerrouter)
8. [HealthMonitor](#8-healthmonitor) - **Updated: New formula**
9. [FailoverController](#9-failovercontroller)
10. [~~SystemCredentialManager~~](#10-systemcredentialmanager-removed) - **REMOVED: Merged into TickerPool**
11. [Refactored websocket.py](#11-refactored-websocketpy)
12. [WebSocket Message Protocol](#12-websocket-message-protocol)
13. [Configuration Reference](#13-configuration-reference)
14. [Health API Endpoint](#14-health-api-endpoint)

---

## 1. NormalizedTick

**Location**: `backend/app/services/brokers/market_data/ticker/models.py`

**Updated**: Now uses `Decimal` for all price fields (changed from `float` in original ADR-003 v2)

Broker-agnostic tick data structure used throughout the ticker pipeline. All adapters normalize their broker-specific tick format into this common model.

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

@dataclass
class NormalizedTick:
    """
    Normalized tick data across all brokers.

    Design decisions (v2.1):
    - Decimal (not float): Eliminates floating-point precision errors for financial data
    - All tokens in CANONICAL format (Kite integer tokens)
    - All prices in RUPEES (NOT paise). Adapters handle ÷100 conversion
    - IST timezone for timestamp
    - broker_type field for tracing tick source
    """
    token: int                      # Canonical instrument token (Kite format). E.g., 256265 = NIFTY
    ltp: Decimal                    # Last traded price in RUPEES (not paise)
    open: Decimal                   # Day open price in RUPEES
    high: Decimal                   # Day high in RUPEES
    low: Decimal                    # Day low in RUPEES
    close: Decimal                  # Previous close in RUPEES
    change: Decimal                 # Absolute change: ltp - close
    change_percent: Decimal         # Percentage change: ((ltp - close) / close) * 100
    volume: int                     # Total volume traded
    oi: int                         # Open interest (0 for non-F&O instruments)
    timestamp: datetime             # Tick timestamp in IST timezone
    broker_type: str                # Source broker: "smartapi", "kite", "upstox", etc.

    # Optional fields (may not be available from all brokers)
    bid: Optional[Decimal] = None   # Best bid price
    ask: Optional[Decimal] = None   # Best ask price
    bid_qty: Optional[int] = None   # Best bid quantity
    ask_qty: Optional[int] = None   # Best ask quantity

    def to_dict(self) -> dict:
        """
        Convert to JSON-serializable dict for WebSocket transmission.

        Note: Decimal → float conversion for JSON compatibility.
        """
        return {
            "token": self.token,
            "ltp": float(self.ltp),  # Convert Decimal to float for JSON
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "change": float(self.change),
            "change_percent": float(self.change_percent),
            "volume": self.volume,
            "oi": self.oi,
            "timestamp": self.timestamp.isoformat(),
            "broker_type": self.broker_type,
            "bid": float(self.bid) if self.bid is not None else None,
            "ask": float(self.ask) if self.ask is not None else None,
            "bid_qty": self.bid_qty,
            "ask_qty": self.ask_qty,
        }
```

### Field Reference

| Field | Type | Source (SmartAPI) | Source (Kite) | Source (Upstox) |
|-------|------|-------------------|---------------|-----------------|
| `token` | int | Reverse-map from SmartAPI token via TokenManager | `instrument_token` (identity) | Parse from `instrument_key` |
| `ltp` | **Decimal** | `Decimal(str(last_traded_price / 100))` | `Decimal(str(last_price / 100))` | `Decimal(str(ltp))` |
| `change` | **Decimal** | Computed: `ltp - close` | `change` or computed | Computed |
| `change_percent` | **Decimal** | Computed: `((ltp - close) / close) * 100` | Computed | Computed |
| `volume` | int | `volume_trade_for_the_day` | `volume_traded` | `vol` |
| `oi` | int | `open_interest` | `oi` | `oi` |
| `open` | **Decimal** | `Decimal(str(open_price_of_the_day / 100))` | `Decimal(str(ohlc.open / 100))` | `Decimal(str(ohlc.open))` |
| `close` | **Decimal** | `Decimal(str(closed_price / 100))` | `Decimal(str(ohlc.close / 100))` | `Decimal(str(ohlc.close))` |
| `timestamp` | datetime | `datetime.now(pytz.timezone('Asia/Kolkata'))` | Same | Same |
| `broker_type` | str | `"smartapi"` | `"kite"` | `"upstox"` |

**Why Decimal?** Trading applications require exact decimal precision. Using `float` can introduce errors like `24500.50` becoming `24500.499999999996`. `Decimal` eliminates these issues.

---

## 2. TickerAdapter (Abstract Base)

**Location**: `backend/app/services/brokers/market_data/ticker/adapter_base.py`

Abstract base class for all broker ticker adapters. Handles common lifecycle, dispatch helpers, and defines the abstract methods each broker must implement.

```python
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .models import NormalizedTick

logger = logging.getLogger(__name__)


class TickerAdapter(ABC):
    """
    Abstract base for broker WebSocket ticker adapters.

    Lifecycle: connect() → subscribe() → [ticks flow] → unsubscribe() → disconnect()

    Subclasses implement _connect_impl, _disconnect_impl, _subscribe_impl,
    _unsubscribe_impl, _translate_to_broker_tokens, _normalize_tick, _get_canonical_token.

    Thread safety:
    - _dispatch_from_thread() safely bridges broker WS thread → asyncio event loop
    - subscribed_tokens uses set operations (Python GIL protects reads)
    - No locks on hot path (dispatch) for performance
    """

    def __init__(self, broker_type: str):
        self._broker_type = broker_type
        self._connected = False
        self._subscribed_tokens: Set[int] = set()  # Canonical tokens
        self._last_tick_time: Optional[datetime] = None
        self._tick_cache: Dict[int, NormalizedTick] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._on_tick_callback: Optional[Callable] = None  # Set by TickerPool

    # ── Properties ──────────────────────────────────────────

    @property
    def broker_type(self) -> str:
        return self._broker_type

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscribed_tokens(self) -> Set[int]:
        return self._subscribed_tokens.copy()

    @property
    def last_tick_time(self) -> Optional[datetime]:
        return self._last_tick_time

    def set_on_tick(self, callback: Callable[[str, List[NormalizedTick]], Any]) -> None:
        """Set callback: callback(broker_type, ticks). Called by TickerPool."""
        self._on_tick_callback = callback

    def get_cached_tick(self, token: int) -> Optional[NormalizedTick]:
        """Get latest cached tick for immediate delivery on subscribe."""
        return self._tick_cache.get(token)

    # ── Lifecycle ───────────────────────────────────────────

    async def connect(self, credentials: dict) -> None:
        """
        Connect to broker WebSocket.

        Args:
            credentials: Broker-specific credentials dict.
                SmartAPI: {jwt_token, api_key, client_id, feed_token}
                Kite:     {access_token, api_key}
                Upstox:   {access_token}
                Dhan:     {client_id, access_token}
                Fyers:    {access_token, app_id}
                Paytm:    {public_access_token}

        Raises:
            ConnectionError: If WebSocket connection fails.
            ValueError: If required credentials missing.
        """
        if self._connected:
            logger.info(f"[{self._broker_type}] Already connected")
            return

        self._loop = asyncio.get_event_loop()
        await self._connect_impl(credentials)
        self._connected = True
        logger.info(f"[{self._broker_type}] Connected")

    async def disconnect(self) -> None:
        """Gracefully disconnect. Unsubscribes all tokens first."""
        if not self._connected:
            return

        try:
            if self._subscribed_tokens:
                await self.unsubscribe(list(self._subscribed_tokens))
            await self._disconnect_impl()
        except Exception as e:
            logger.error(f"[{self._broker_type}] Disconnect error: {e}")
        finally:
            self._connected = False
            self._subscribed_tokens.clear()
            logger.info(f"[{self._broker_type}] Disconnected")

    async def reconnect(self, credentials: dict) -> None:
        """Disconnect then reconnect with fresh credentials. Preserves subscriptions."""
        # Save tokens BEFORE disconnect (which clears them in finally block)
        saved_tokens = list(self._subscribed_tokens)
        await self.disconnect()
        await self.connect(credentials)
        # Re-subscribe to previously subscribed tokens
        if saved_tokens:
            await self.subscribe(saved_tokens)

    async def update_credentials(self, credentials: dict) -> None:
        """
        Hot-swap credentials without losing subscriptions.

        Default implementation: reconnect (preserves subscriptions via saved tokens).
        Subclasses may override for true hot-swap without reconnection if broker supports it.
        """
        await self.reconnect(credentials)

    # ── Subscriptions ───────────────────────────────────────

    async def subscribe(self, canonical_tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe to canonical tokens on broker WebSocket.

        Args:
            canonical_tokens: List of Kite-format instrument tokens.
            mode: "ltp", "quote", or "full"/"snap"/"depth" (broker-dependent).
        """
        if not self._connected:
            logger.warning(f"[{self._broker_type}] Not connected, cannot subscribe")
            return

        new_tokens = [t for t in canonical_tokens if t not in self._subscribed_tokens]
        if not new_tokens:
            return

        broker_tokens = self._translate_to_broker_tokens(new_tokens)
        await self._subscribe_impl(broker_tokens, mode)
        self._subscribed_tokens.update(new_tokens)
        logger.info(f"[{self._broker_type}] Subscribed to {len(new_tokens)} tokens (total: {len(self._subscribed_tokens)})")

    async def unsubscribe(self, canonical_tokens: List[int]) -> None:
        """Unsubscribe canonical tokens from broker WebSocket."""
        if not self._connected:
            return

        active_tokens = [t for t in canonical_tokens if t in self._subscribed_tokens]
        if not active_tokens:
            return

        broker_tokens = self._translate_to_broker_tokens(active_tokens)
        await self._unsubscribe_impl(broker_tokens)
        self._subscribed_tokens -= set(active_tokens)
        logger.info(f"[{self._broker_type}] Unsubscribed {len(active_tokens)} tokens (remaining: {len(self._subscribed_tokens)})")

    # ── Dispatch Helpers ────────────────────────────────────

    def _dispatch_from_thread(self, ticks: List[NormalizedTick]) -> None:
        """
        Bridge from broker WS thread to asyncio event loop.

        CRITICAL: Used by SmartAPI and Kite adapters which run WS in daemon threads.
        Uses asyncio.run_coroutine_threadsafe to safely cross the thread boundary.
        """
        if self._loop and self._on_tick_callback:
            self._last_tick_time = datetime.utcnow()
            for tick in ticks:
                self._tick_cache[tick.token] = tick
            asyncio.run_coroutine_threadsafe(
                self._dispatch_async(ticks),
                self._loop
            )

    async def _dispatch_async(self, ticks: List[NormalizedTick]) -> None:
        """Dispatch ticks to the registered callback (TickerPool)."""
        if self._on_tick_callback:
            self._last_tick_time = datetime.utcnow()
            for tick in ticks:
                self._tick_cache[tick.token] = tick
            await self._on_tick_callback(self._broker_type, ticks)

    # ── Abstract Methods (broker-specific) ──────────────────

    @abstractmethod
    async def _connect_impl(self, credentials: dict) -> None:
        """Broker-specific connection logic."""

    @abstractmethod
    async def _disconnect_impl(self) -> None:
        """Broker-specific disconnection logic."""

    @abstractmethod
    async def _subscribe_impl(self, broker_tokens: list, mode: str) -> None:
        """Send subscribe request to broker WS using broker-format tokens."""

    @abstractmethod
    async def _unsubscribe_impl(self, broker_tokens: list) -> None:
        """Send unsubscribe request to broker WS using broker-format tokens."""

    @abstractmethod
    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Translate canonical (Kite) tokens to broker-specific format.

        Returns broker-specific token representations. Format varies:
        - SmartAPI: [{"exchangeType": 2, "tokens": ["99926000"]}]
        - Kite: [256265, 260105] (identity — no translation)
        - Upstox: ["NSE_FO|12345"]
        - Dhan: [12345] (security_id)
        - Fyers: ["NSE:NIFTY50-INDEX"]
        - Paytm: ["4.1!12345"]
        """

    @abstractmethod
    def _normalize_tick(self, raw_tick: Any) -> NormalizedTick:
        """Convert broker-specific tick to NormalizedTick."""

    @abstractmethod
    def _get_canonical_token(self, broker_token: Any) -> int:
        """Get canonical (Kite) token from broker-specific token."""
```

---

## 3. SmartAPITickerAdapter

**Location**: `backend/app/services/brokers/market_data/ticker/adapters/smartapi.py`

```python
"""
SmartAPI Ticker Adapter

Wraps SmartWebSocketV2 with the TickerAdapter interface.
Handles: token translation, paise→rupees normalization, daemon thread.

CRITICAL: Preserves exact threading pattern from legacy/smartapi_ticker.py:117-124.
"""
import asyncio
import threading
import logging
from typing import Any, Dict, List, Optional

from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from ..adapter_base import TickerAdapter
from ..models import NormalizedTick

logger = logging.getLogger(__name__)

# SmartAPI exchange type codes
EXCHANGE_NSE = 1
EXCHANGE_NFO = 2
EXCHANGE_BSE = 3
EXCHANGE_BFO = 4
EXCHANGE_MCX = 5

# SmartAPI subscription modes
MODE_LTP = 1
MODE_QUOTE = 2
MODE_SNAP_QUOTE = 3


class SmartAPITickerAdapter(TickerAdapter):
    """
    SmartAPI WebSocket V2 adapter.

    Key behaviors:
    - Token translation: canonical (Kite) → SmartAPI format via TokenManager
    - Price normalization: paise ÷ 100 → rupees
    - Threading: SmartWebSocketV2 runs in daemon thread, dispatches via
      asyncio.run_coroutine_threadsafe
    - Exchange type codes required per subscription group
    """

    # Hardcoded index token mapping (fallback when TokenManager unavailable)
    _INDEX_MAP = {
        256265: {"smartapi_token": "99926000", "exchange": EXCHANGE_NSE, "name": "NIFTY 50"},
        260105: {"smartapi_token": "99926009", "exchange": EXCHANGE_NSE, "name": "NIFTY BANK"},
        257801: {"smartapi_token": "99926037", "exchange": EXCHANGE_NSE, "name": "NIFTY FIN"},
        265:    {"smartapi_token": "99919000", "exchange": EXCHANGE_BSE, "name": "SENSEX"},
    }
    _REVERSE_INDEX_MAP = {v["smartapi_token"]: k for k, v in _INDEX_MAP.items()}

    def __init__(self):
        super().__init__("smartapi")
        self._ws: Optional[SmartWebSocketV2] = None
        self._thread: Optional[threading.Thread] = None
        self._token_map: Dict[int, str] = {}          # canonical → smartapi token
        self._reverse_token_map: Dict[str, int] = {}   # smartapi token → canonical

    async def _connect_impl(self, credentials: dict) -> None:
        """
        Connect to SmartAPI WebSocket.

        credentials: {jwt_token, api_key, client_id, feed_token}
        """
        self._ws = SmartWebSocketV2(
            auth_token=credentials["jwt_token"],
            api_key=credentials["api_key"],
            client_code=credentials["client_id"],
            feed_token=credentials["feed_token"],
        )

        self._ws.on_open = self._on_open
        self._ws.on_data = self._on_data
        self._ws.on_error = self._on_error
        self._ws.on_close = self._on_close

        # CRITICAL: Preserve exact threading pattern from smartapi_ticker.py:117-124
        def run_websocket():
            try:
                self._ws.connect()
            except Exception as e:
                logger.error(f"[SmartAPI] WebSocket thread error: {e}")

        self._thread = threading.Thread(target=run_websocket, daemon=True)
        self._thread.start()

        # Wait for connection establishment
        await asyncio.sleep(2)

    async def _disconnect_impl(self) -> None:
        if self._ws:
            try:
                self._ws.close_connection()
            except Exception as e:
                logger.error(f"[SmartAPI] Close error: {e}")
        self._token_map.clear()
        self._reverse_token_map.clear()

    async def _subscribe_impl(self, broker_tokens: list, mode: str) -> None:
        """
        broker_tokens: list of {"exchangeType": int, "tokens": [str]}
        """
        mode_map = {"ltp": MODE_LTP, "quote": MODE_QUOTE, "full": MODE_SNAP_QUOTE, "snap": MODE_SNAP_QUOTE}
        smartapi_mode = mode_map.get(mode, MODE_QUOTE)

        self._ws.subscribe(
            correlation_id="ticker_pool",
            mode=smartapi_mode,
            token_list=broker_tokens,
        )

    async def _unsubscribe_impl(self, broker_tokens: list) -> None:
        self._ws.unsubscribe(
            correlation_id="ticker_pool",
            mode=MODE_QUOTE,
            token_list=broker_tokens,
        )

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Translate canonical tokens to SmartAPI subscription format.

        Returns: [{"exchangeType": 1, "tokens": ["99926000"]}, ...]
        Groups tokens by exchange type for SmartAPI's API format.
        """
        # Group by exchange type
        groups: Dict[int, List[str]] = {}

        for canonical in canonical_tokens:
            if canonical in self._INDEX_MAP:
                info = self._INDEX_MAP[canonical]
                smartapi_token = info["smartapi_token"]
                exchange = info["exchange"]
            else:
                # Use TokenManager for non-index tokens
                smartapi_token = str(canonical)  # Fallback; TokenManager provides real mapping
                exchange = EXCHANGE_NFO

            groups.setdefault(exchange, []).append(smartapi_token)
            self._token_map[canonical] = smartapi_token
            self._reverse_token_map[smartapi_token] = canonical

        return [{"exchangeType": ex, "tokens": tokens} for ex, tokens in groups.items()]

    def _normalize_tick(self, raw_tick: Any) -> NormalizedTick:
        """
        Normalize SmartAPI tick → NormalizedTick.

        Key transformations:
        - Prices: paise ÷ 100 → rupees
        - Token: SmartAPI string → canonical int
        """
        smartapi_token = str(raw_tick.get("token", ""))
        canonical_token = self._get_canonical_token(smartapi_token)

        ltp = raw_tick.get("last_traded_price", 0) / 100
        open_price = raw_tick.get("open_price_of_the_day", 0) / 100
        high = raw_tick.get("high_price_of_the_day", 0) / 100
        low = raw_tick.get("low_price_of_the_day", 0) / 100
        close = raw_tick.get("closed_price", 0) / 100

        change = ltp - close
        change_percent = (change / close * 100) if close else 0.0

        return NormalizedTick(
            token=canonical_token,
            ltp=ltp,
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            volume=raw_tick.get("volume_trade_for_the_day", 0),
            oi=raw_tick.get("open_interest", 0),
            open=open_price,
            high=high,
            low=low,
            close=close,
            last_trade_time=raw_tick.get("exchange_timestamp"),
            exchange_timestamp=raw_tick.get("exchange_timestamp"),
        )

    def _get_canonical_token(self, broker_token: Any) -> int:
        token_str = str(broker_token)
        if token_str in self._REVERSE_INDEX_MAP:
            return self._REVERSE_INDEX_MAP[token_str]
        if token_str in self._reverse_token_map:
            return self._reverse_token_map[token_str]
        return int(token_str)

    # ── SmartWebSocketV2 Callbacks ──────────────────────────

    def _on_open(self, wsapp):
        self._connected = True
        logger.info("[SmartAPI] WebSocket connected")

    def _on_data(self, wsapp, message):
        try:
            tick = self._normalize_tick(message)
            self._dispatch_from_thread([tick])
        except Exception as e:
            logger.error(f"[SmartAPI] Tick processing error: {e}")

    def _on_error(self, wsapp, error):
        logger.error(f"[SmartAPI] WebSocket error: {error}")

    def _on_close(self, wsapp):
        self._connected = False
        logger.warning("[SmartAPI] WebSocket closed")
```

---

## 4. KiteTickerAdapter

**Location**: `backend/app/services/brokers/market_data/ticker/adapters/kite.py`

```python
"""
Kite Ticker Adapter

Simpler than SmartAPI:
- No token translation (Kite format IS canonical)
- KiteTicker library manages its own threading
- Prices in paise for WS data (÷100 to get rupees)
"""
import asyncio
import logging
from typing import Any, List, Optional

from kiteconnect import KiteTicker

from ..adapter_base import TickerAdapter
from ..models import NormalizedTick

logger = logging.getLogger(__name__)


class KiteTickerAdapter(TickerAdapter):
    """
    Kite WebSocket adapter.

    Kite tokens are already in canonical format — no translation needed.
    KiteTicker library handles binary parsing and threading internally.
    """

    def __init__(self):
        super().__init__("kite")
        self._ticker: Optional[KiteTicker] = None

    async def _connect_impl(self, credentials: dict) -> None:
        """
        credentials: {access_token, api_key}
        """
        self._ticker = KiteTicker(
            api_key=credentials["api_key"],
            access_token=credentials["access_token"],
        )

        self._ticker.on_connect = self._on_connect
        self._ticker.on_ticks = self._on_ticks
        self._ticker.on_error = self._on_error
        self._ticker.on_close = self._on_close
        self._ticker.on_reconnect = self._on_reconnect

        # KiteTicker manages its own thread with threaded=True
        self._ticker.connect(threaded=True)
        await asyncio.sleep(2)

    async def _disconnect_impl(self) -> None:
        if self._ticker:
            self._ticker.close()

    async def _subscribe_impl(self, broker_tokens: list, mode: str) -> None:
        """broker_tokens: list of ints (canonical = Kite format)."""
        mode_map = {
            "ltp": self._ticker.MODE_LTP,
            "quote": self._ticker.MODE_QUOTE,
            "full": self._ticker.MODE_FULL,
        }
        self._ticker.subscribe(broker_tokens)
        self._ticker.set_mode(mode_map.get(mode, self._ticker.MODE_QUOTE), broker_tokens)

    async def _unsubscribe_impl(self, broker_tokens: list) -> None:
        self._ticker.unsubscribe(broker_tokens)

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """Identity mapping — Kite format IS canonical format."""
        return canonical_tokens

    def _normalize_tick(self, raw_tick: Any) -> NormalizedTick:
        """
        Normalize Kite tick.

        Kite WS sends prices in paise — divide by 100 for rupees.
        REST API sends prices in rupees (no conversion).
        """
        ohlc = raw_tick.get("ohlc", {})
        ltp = raw_tick.get("last_price", 0) / 100
        close = ohlc.get("close", 0) / 100
        change = ltp - close
        change_percent = (change / close * 100) if close else 0.0

        return NormalizedTick(
            token=raw_tick["instrument_token"],
            ltp=ltp,
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            volume=raw_tick.get("volume_traded", 0),
            oi=raw_tick.get("oi", 0),
            open=ohlc.get("open", 0) / 100,
            high=ohlc.get("high", 0) / 100,
            low=ohlc.get("low", 0) / 100,
            close=close,
            last_trade_time=raw_tick.get("last_trade_time"),
            exchange_timestamp=raw_tick.get("exchange_timestamp"),
        )

    def _get_canonical_token(self, broker_token: Any) -> int:
        """Identity — Kite token IS canonical."""
        return int(broker_token)

    # ── KiteTicker Callbacks ────────────────────────────────

    def _on_connect(self, ws, response):
        self._connected = True
        logger.info("[Kite] WebSocket connected")

    def _on_ticks(self, ws, ticks):
        try:
            normalized = [self._normalize_tick(t) for t in ticks]
            self._dispatch_from_thread(normalized)
        except Exception as e:
            logger.error(f"[Kite] Tick processing error: {e}")

    def _on_error(self, ws, code, reason):
        logger.error(f"[Kite] Error {code}: {reason}")

    def _on_close(self, ws, code, reason):
        self._connected = False
        logger.warning(f"[Kite] Closed {code}: {reason}")

    def _on_reconnect(self, ws, attempts_count):
        logger.info(f"[Kite] Reconnecting (attempt {attempts_count})")
```

---

## 5. Stub Adapter Templates

**Location**: `backend/app/services/brokers/market_data/ticker/adapters/{broker}.py`

Each stub provides broker-specific implementation notes in docstrings. Replace `NotImplementedError` with real implementation when adding the broker.

### Upstox Stub (Protobuf)

```python
"""
Upstox Ticker Adapter (Stub)

Implementation notes:
- WS URL: Obtained via GET /v2/feed/market-data-feed/authorize
- Auth: OAuth 2.0 extended token (~1 year validity)
- Parsing: Protobuf (MarketDataFeed proto) — requires protobuf dependency
- Tokens: "NSE_FO|{instrument_token}" format
- Prices: Already in rupees (no conversion)
- Threading: asyncio-native (websockets library)
- Limits: 1 connection per access token
"""

class UpstoxTickerAdapter(TickerAdapter):
    def __init__(self):
        super().__init__("upstox")
    # All abstract methods raise NotImplementedError
```

### Dhan Stub (Little-Endian Binary)

```python
"""
Dhan Ticker Adapter (Stub)

Implementation notes:
- WS URL: wss://api-feed.dhan.co
- Auth: Static API token (never expires)
- Parsing: Little-endian binary — struct.unpack('<...'). NOTE: opposite endianness from SmartAPI/Kite!
- Tokens: Numeric security_id — requires full CSV instrument master mapping
- Prices: Already in rupees
- Threading: threading.Thread (synchronous WS client)
- Limits: 5 connections max, 100 instruments per connection
- Special: 200-level market depth available
"""

class DhanTickerAdapter(TickerAdapter):
    def __init__(self):
        super().__init__("dhan")
    # All abstract methods raise NotImplementedError
```

### Fyers Stub (JSON)

```python
"""
Fyers Ticker Adapter (Stub)

Implementation notes:
- WS URL: wss://socket.fyers.in/hsm/v3/
- Auth: OAuth 2.0. WS auth: "{app_id}:{access_token}"
- Parsing: JSON (simplest of all brokers)
- Tokens: "NSE:{symbol}" prefix. Strip "NSE:" for canonical.
- Prices: Already in rupees
- Threading: asyncio-native
- Limits: 200 symbols per connection
- Special: Dual WS system (data + orders) — only data WS needed here
"""

class FyersTickerAdapter(TickerAdapter):
    def __init__(self):
        super().__init__("fyers")
    # All abstract methods raise NotImplementedError
```

### Paytm Stub (JSON)

```python
"""
Paytm Money Ticker Adapter (Stub)

Implementation notes:
- WS URL: wss://developer-ws.paytmmoney.com/broadcast/user/v1/data
- Auth: OAuth 2.0 with 3 JWTs. WS uses public_access_token.
- Parsing: JSON
- Tokens: "{exchange_segment}.{exchange_type}!{security_id}" (RIC format)
- Prices: Already in rupees
- Threading: asyncio-native
- Limits: 200 instruments per connection
"""

class PaytmTickerAdapter(TickerAdapter):
    def __init__(self):
        super().__init__("paytm")
    # All abstract methods raise NotImplementedError
```

---

## 6. TickerPool

**Location**: `backend/app/services/brokers/market_data/ticker/pool.py`

**Updated**: Now includes integrated credential management (no separate SystemCredentialManager component)

Manages adapter lifecycle, ref-counted subscription aggregation, and system credentials. Singleton.

```python
class TickerPool:
    """
    Adapter lifecycle manager with ref-counted subscriptions + credential management.

    Key behaviors:
    - Lazy adapter creation: Adapters created on first subscription
    - Ref-counted subscriptions: Multiple users subscribing to same token
      = 1 broker subscription. Unsubscribe only when ref_count hits 0.
    - Idle cleanup: If adapter has 0 subscriptions for 5 minutes, disconnect and remove it.
    - Wires adapter._on_tick → self._on_adapter_tick → router.dispatch
    - **NEW (v2.1): Integrated credential management** - loads and refreshes system credentials

    Credential management (replaces SystemCredentialManager):
    - load_system_credentials(): Load from database on startup
    - refresh_credentials(broker): Per-broker credential refresh
    - Auto-refresh loops (SmartAPI: 30 min before 5AM IST)
    """

    _instance: Optional["TickerPool"] = None

    @classmethod
    def get_instance(cls) -> "TickerPool":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._adapters: Dict[str, TickerAdapter] = {}  # broker_type → adapter
        self._adapter_registry: Dict[str, type] = {}   # broker_type → adapter class

        # Ref-counted subscriptions: broker_type → {canonical_token → ref_count}
        self._subscriptions: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

        # NEW: System credentials management (integrated)
        self._credentials: Dict[str, dict] = {}  # broker_type → credentials
        self._refresh_tasks: Dict[str, asyncio.Task] = {}  # Per-broker refresh loops

        # Dependencies (injected)
        self._router: Optional["TickerRouter"] = None
        self._health_monitor: Optional["HealthMonitor"] = None

        # Idle cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._idle_threshold = timedelta(minutes=5)

    async def initialize(
        self,
        router: "TickerRouter",
        health_monitor: Optional["HealthMonitor"] = None
    ) -> None:
        """
        Initialize TickerPool with dependencies.

        Args:
            router: TickerRouter instance (for tick dispatching)
            health_monitor: HealthMonitor instance (optional)
        """
        self._router = router
        self._health_monitor = health_monitor

        # Load system credentials from database
        await self.load_system_credentials()

        # Start idle cleanup loop
        self._cleanup_task = asyncio.create_task(self._idle_cleanup_loop())

    def register_adapter(self, broker_type: str, adapter_class: type) -> None:
        """
        Register a broker adapter class.

        Args:
            broker_type: Broker identifier ("smartapi", "kite", etc.)
            adapter_class: TickerAdapter subclass
        """
        self._adapter_registry[broker_type] = adapter_class

    # NEW: System Credentials Management (integrated from SystemCredentialManager)

    async def load_system_credentials(self) -> None:
        """
        Load system broker credentials from database.

        For each active broker in system_broker_credentials table:
        1. Decrypt credentials (using app/utils/encryption.py)
        2. Authenticate (SmartAPI: auto-TOTP, others: validate token)
        3. Store in self._credentials
        4. Schedule refresh loop if token expires
        """
        # Implementation in TICKER-IMPLEMENTATION-GUIDE.md Phase T1 Step 1.4
        pass

    async def refresh_credentials(self, broker_type: str) -> None:
        """
        Refresh credentials for specified broker.

        Broker-specific logic:
        - SmartAPI: Re-authenticate with auto-TOTP
        - Upstox/Fyers/Paytm: Standard OAuth refresh
        - Dhan: No refresh (static token)
        - Kite: Log limitation (user OAuth only)

        Args:
            broker_type: Broker to refresh
        """
        pass

    async def _smartapi_refresh_loop(self, broker_type: str) -> None:
        """
        Auto-refresh SmartAPI credentials 30 minutes before 5 AM IST expiry.

        Runs continuously in background task.
        """
        pass

    async def get_adapter(self, broker_type: str) -> TickerAdapter:
        """
        Get or create adapter for broker. Connects with system credentials.

        Returns existing connected adapter or creates new one.
        Registers adapter with HealthMonitor.
        """
        if broker_type in self._adapters:
            return self._adapters[broker_type]

        # Create adapter (lazy import to avoid circular deps)
        adapter = self._create_adapter(broker_type)
        adapter.set_on_tick(self._on_adapter_tick)

        # Get system credentials and connect
        credentials = await self._credential_manager.get_credentials(broker_type)
        await adapter.connect(credentials)

        self._adapters[broker_type] = adapter
        self._ref_counts[broker_type] = {}
        self._health_monitor.register_adapter(broker_type)
        self._health_monitor.record_connect(broker_type)

        return adapter

    def _create_adapter(self, broker_type: str) -> TickerAdapter:
        """
        Lazy-import and instantiate a broker-specific TickerAdapter.

        Uses dynamic import to avoid circular dependencies and load adapters on-demand.
        """
        if broker_type not in self.ADAPTER_MAP:
            raise ValueError(f"Unknown broker type: {broker_type}")

        module_path = self.ADAPTER_MAP[broker_type]
        module_name, class_name = module_path.rsplit(".", 1)

        # Lazy import to avoid loading all adapters at startup
        import importlib
        module = importlib.import_module(module_name)
        adapter_class = getattr(module, class_name)

        # Instantiate and wire callback
        adapter = adapter_class()
        adapter.set_on_tick(
            lambda broker, ticks: asyncio.ensure_future(
                self._on_adapter_tick(broker, ticks)
            )
        )

        return adapter

    async def add_subscriptions(self, broker_type: str, canonical_tokens: List[int], mode: str = "quote") -> None:
        """
        Add subscriptions with ref-counting.

        If token ref_count goes from 0→1, actually subscribe on broker WS.
        If token already subscribed (ref_count > 0), just increment count.
        """
        adapter = await self.get_adapter(broker_type)
        new_tokens = []

        for token in canonical_tokens:
            ref = self._ref_counts[broker_type]
            ref[token] = ref.get(token, 0) + 1
            if ref[token] == 1:  # New subscription
                new_tokens.append(token)

        if new_tokens:
            await adapter.subscribe(new_tokens, mode)

        # Cancel idle timer if exists
        self._cancel_idle_timer(broker_type)

    async def remove_subscriptions(self, broker_type: str, canonical_tokens: List[int]) -> None:
        """
        Remove subscriptions with ref-counting.

        Only unsubscribe from broker WS when ref_count hits 0.
        Start idle timer if adapter has 0 total subscriptions.
        """
        if broker_type not in self._adapters:
            return

        adapter = self._adapters[broker_type]
        tokens_to_unsub = []

        for token in canonical_tokens:
            ref = self._ref_counts.get(broker_type, {})
            if token in ref:
                ref[token] -= 1
                if ref[token] <= 0:
                    del ref[token]
                    tokens_to_unsub.append(token)

        if tokens_to_unsub:
            await adapter.unsubscribe(tokens_to_unsub)

        # Start idle timer if no subscriptions remain
        total_refs = sum(self._ref_counts.get(broker_type, {}).values())
        if total_refs == 0:
            self._start_idle_timer(broker_type)

    def _cancel_idle_timer(self, broker_type: str) -> None:
        """Cancel pending idle disconnect timer for a broker."""
        timer = self._idle_timers.pop(broker_type, None)
        if timer and not timer.done():
            timer.cancel()

    def _start_idle_timer(self, broker_type: str) -> None:
        """
        Start idle timer — disconnects adapter after TICKER_IDLE_TIMEOUT_S if no subscriptions.

        Prevents thrashing by allowing brief periods of zero subscriptions before disconnecting.
        """
        self._cancel_idle_timer(broker_type)

        async def _idle_cleanup():
            await asyncio.sleep(settings.TICKER_IDLE_TIMEOUT_S)
            if broker_type in self._adapters:
                logger.info(f"[TickerPool] Disconnecting idle adapter: {broker_type}")
                adapter = self._adapters.pop(broker_type)
                await adapter.disconnect()
                if self._health_monitor:
                    self._health_monitor.unregister_adapter(broker_type)
                self._ref_counts.pop(broker_type, None)

        self._idle_timers[broker_type] = asyncio.create_task(_idle_cleanup())

    async def _on_adapter_tick(self, broker_type: str, ticks: List[NormalizedTick]) -> None:
        """
        Called by adapter when ticks arrive. Forwards to router + health monitor.

        Also computes latency from exchange_timestamp (if available) and records to HealthMonitor.
        """
        self._health_monitor.record_ticks(broker_type, len(ticks))

        # Record latency for health scoring
        for tick in ticks:
            if tick.exchange_timestamp:
                latency_ms = (datetime.utcnow().timestamp() - tick.exchange_timestamp) * 1000
                self._health_monitor.record_latency(broker_type, latency_ms)
                break  # Only need one sample per batch

        await self._ticker_router.dispatch(ticks)

    async def shutdown(self) -> None:
        """Disconnect all adapters. Called from main.py shutdown."""
        for broker_type, adapter in list(self._adapters.items()):
            try:
                await adapter.disconnect()
                self._health_monitor.unregister_adapter(broker_type)
            except Exception as e:
                logger.error(f"[TickerPool] Error disconnecting {broker_type}: {e}")
        self._adapters.clear()
        self._ref_counts.clear()
```

---

## 7. TickerRouter

**Location**: `backend/app/services/brokers/market_data/ticker/router.py`

Maps users to WebSocket connections. Handles tick fan-out and subscription routing.

```python
class TickerRouter:
    """
    User subscription management and tick fan-out.

    Decoupled from brokers — only knows about canonical tokens and user WebSockets.
    On dispatch: looks up token → Set[user_id] → send to each user's WS.

    Performance: No locks on dispatch hot path. Python GIL protects dict reads.
    Worst case: tick sent to just-unsubscribed user (harmless, will be ignored by frontend).
    """

    _instance: Optional["TickerRouter"] = None

    @classmethod
    def get_instance(cls) -> "TickerRouter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._pool: Optional["TickerPool"] = None
        self._user_websockets: Dict[str, WebSocket] = {}       # user_id → WS
        self._user_broker: Dict[str, str] = {}                  # user_id → broker_type
        self._user_tokens: Dict[str, Set[int]] = {}             # user_id → {canonical_tokens}
        self._token_users: Dict[int, Set[str]] = {}             # token → {user_ids}

    def set_pool(self, pool: "TickerPool") -> None:
        self._pool = pool

    @property
    def connected_users(self) -> int:
        return len(self._user_websockets)

    @property
    def total_token_subscriptions(self) -> int:
        return len(self._token_users)

    # ── User Management ─────────────────────────────────────

    async def register_user(self, user_id: str, websocket: WebSocket, broker_type: str) -> None:
        """
        Register a user's WebSocket connection.

        Args:
            user_id: Unique user identifier (str)
            websocket: FastAPI WebSocket connection
            broker_type: User's preferred market data broker (from UserPreferences)
        """
        self._user_websockets[user_id] = websocket
        self._user_broker[user_id] = broker_type
        self._user_tokens[user_id] = set()
        logger.info(f"[TickerRouter] Registered user {user_id} (broker: {broker_type}, total: {self.connected_users})")

    async def unregister_user(self, user_id: str) -> None:
        """
        Unregister user. Cleans up all their subscriptions.

        Decrements ref counts in TickerPool for each token the user had subscribed.
        """
        tokens = self._user_tokens.pop(user_id, set())
        broker_type = self._user_broker.pop(user_id, None)
        self._user_websockets.pop(user_id, None)

        # Remove user from token→user mappings
        for token in tokens:
            if token in self._token_users:
                self._token_users[token].discard(user_id)
                if not self._token_users[token]:
                    del self._token_users[token]

        # Decrement ref counts in pool
        if broker_type and tokens and self._pool:
            await self._pool.remove_subscriptions(broker_type, list(tokens))

        logger.info(f"[TickerRouter] Unregistered user {user_id} (removed {len(tokens)} subscriptions, total: {self.connected_users})")

    # ── Subscriptions ───────────────────────────────────────

    async def subscribe(self, user_id: str, canonical_tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe user to tokens. Routes to TickerPool for broker subscription.

        Also delivers cached ticks immediately so user sees data before next tick.
        """
        broker_type = self._user_broker.get(user_id)
        if not broker_type:
            logger.warning(f"[TickerRouter] User {user_id} not registered")
            return

        # Track user's subscriptions
        self._user_tokens.setdefault(user_id, set()).update(canonical_tokens)

        # Track token → user mapping for fan-out
        for token in canonical_tokens:
            self._token_users.setdefault(token, set()).add(user_id)

        # Route to pool (ref-counted)
        await self._pool.add_subscriptions(broker_type, canonical_tokens, mode)

        # Deliver cached ticks immediately (so UI shows data before next real tick)
        adapter = self._pool._adapters.get(broker_type)
        if adapter:
            cached_ticks = [adapter.get_cached_tick(t) for t in canonical_tokens]
            cached_ticks = [t for t in cached_ticks if t is not None]
            if cached_ticks:
                ws = self._user_websockets.get(user_id)
                if ws:
                    await ws.send_json({"type": "ticks", "data": [t.to_dict() for t in cached_ticks]})

    async def unsubscribe(self, user_id: str, canonical_tokens: List[int]) -> None:
        """Unsubscribe user from tokens. Decrements ref counts in pool."""
        broker_type = self._user_broker.get(user_id)
        if not broker_type:
            return

        # Remove from user tracking
        user_tokens = self._user_tokens.get(user_id, set())
        user_tokens -= set(canonical_tokens)

        # Remove from token→user mapping
        for token in canonical_tokens:
            if token in self._token_users:
                self._token_users[token].discard(user_id)
                if not self._token_users[token]:
                    del self._token_users[token]

        await self._pool.remove_subscriptions(broker_type, canonical_tokens)

    # ── Tick Dispatch (HOT PATH) ────────────────────────────

    async def dispatch(self, ticks: List[NormalizedTick]) -> None:
        """
        Fan out ticks to subscribed users.

        HOT PATH — called for every tick from every broker.
        No locks. Python GIL makes dict reads thread-safe.
        """
        for tick in ticks:
            user_ids = self._token_users.get(tick.token)
            if not user_ids:
                continue

            tick_data = {"type": "ticks", "data": [tick.to_dict()]}

            for user_id in user_ids:
                ws = self._user_websockets.get(user_id)
                if ws:
                    try:
                        await ws.send_json(tick_data)
                    except Exception:
                        # User disconnected — will be cleaned up by unregister_user
                        pass

    # ── Failover Support ────────────────────────────────────

    async def switch_users_broker(self, from_broker: str, to_broker: str) -> None:
        """
        Switch all users from one broker to another (for failover).

        Updates user→broker mappings. TickerPool handles the actual
        subscription migration on broker WebSockets.
        """
        for user_id, broker in list(self._user_broker.items()):
            if broker == from_broker:
                self._user_broker[user_id] = to_broker
        logger.info(f"[TickerRouter] Switched users from {from_broker} to {to_broker}")

    def get_tokens_for_broker(self, broker_type: str) -> Set[int]:
        """Get all tokens currently subscribed on a broker (for failover migration)."""
        all_tokens: Set[int] = set()
        for user_id, broker in self._user_broker.items():
            if broker == broker_type:
                all_tokens.update(self._user_tokens.get(user_id, set()))
        return all_tokens
```

---

## 8. HealthMonitor

**Location**: `backend/app/services/brokers/market_data/ticker/health.py`

**Updated**: New health score formula (changed from original ADR-003 v2)

```python
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class AdapterHealth:
    """Health state for one broker adapter."""
    broker_type: str
    is_connected: bool = False
    health_score: float = 0.0           # 0-100
    tick_count_60s: int = 0             # Ticks received in last 60s
    error_count_60s: int = 0            # Errors in last 60s
    last_tick_time: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    avg_latency_ms: float = 0.0
    consecutive_low_count: int = 0      # Consecutive checks below threshold


class HealthMonitor:
    """
    Active health monitoring for all ticker adapters.

    Runs a 5-second heartbeat loop that:
    1. Computes health score for each adapter
    2. Tracks consecutive low scores
    3. Calls FailoverController callback when threshold breached

    Health score formula:
      connection_score * 0.30 + latency_score * 0.20 +
      error_score * 0.20 + freshness_score * 0.30
    """

    _instance: Optional["HealthMonitor"] = None

    @classmethod
    def get_instance(cls) -> "HealthMonitor":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._adapters: Dict[str, AdapterHealth] = {}
        self._on_health_change: Optional[Callable] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ── Registration ────────────────────────────────────────

    def register_adapter(self, broker_type: str) -> None:
        self._adapters[broker_type] = AdapterHealth(broker_type=broker_type)

    def unregister_adapter(self, broker_type: str) -> None:
        self._adapters.pop(broker_type, None)

    # ── Recording (called by pool/adapters) ─────────────────

    def record_ticks(self, broker_type: str, count: int) -> None:
        health = self._adapters.get(broker_type)
        if health:
            health.tick_count_60s += count
            health.last_tick_time = datetime.utcnow()

    def record_error(self, broker_type: str, error: str) -> None:
        health = self._adapters.get(broker_type)
        if health:
            health.error_count_60s += 1
            health.last_error = error
            health.last_error_time = datetime.utcnow()

    def record_disconnect(self, broker_type: str) -> None:
        health = self._adapters.get(broker_type)
        if health:
            health.is_connected = False

    def record_connect(self, broker_type: str) -> None:
        health = self._adapters.get(broker_type)
        if health:
            health.is_connected = True
            health.consecutive_low_count = 0

    def record_latency(self, broker_type: str, latency_ms: float) -> None:
        """
        Record tick delivery latency (exponential moving average).

        Called by TickerPool in _on_adapter_tick() with latency computed
        from exchange_timestamp to arrival time.
        """
        health = self._adapters.get(broker_type)
        if health:
            alpha = 0.3  # EMA smoothing factor
            health.avg_latency_ms = alpha * latency_ms + (1 - alpha) * health.avg_latency_ms

    # ── Health Queries ──────────────────────────────────────

    def get_health(self, broker_type: str) -> Optional[AdapterHealth]:
        return self._adapters.get(broker_type)

    def get_all_health(self) -> Dict[str, AdapterHealth]:
        return dict(self._adapters)

    # ── Lifecycle ───────────────────────────────────────────

    def set_on_health_change(self, callback: Callable) -> None:
        """callback(broker_type: str, health_score: float)"""
        self._on_health_change = callback

    async def start(self) -> None:
        """Start 5-second heartbeat loop."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

    async def _heartbeat_loop(self) -> None:
        """Every 5 seconds: compute scores, check thresholds, reset counters."""
        while True:
            await asyncio.sleep(5)
            for broker_type, health in self._adapters.items():
                score = self._compute_health_score(health)
                health.health_score = score

                if score < 30:
                    health.consecutive_low_count += 1
                else:
                    health.consecutive_low_count = 0

                if self._on_health_change:
                    await self._on_health_change(broker_type, score)

                # Reset 60s counters (sliding window approximation)
                health.tick_count_60s = max(0, health.tick_count_60s - health.tick_count_60s // 12)
                health.error_count_60s = max(0, health.error_count_60s - health.error_count_60s // 12)

    def _compute_health_score(self, health: AdapterHealth) -> float:
        """
        Weighted health score (0-100).

        **NEW FORMULA (v2.1):**
        health_score = (
            latency_score      * 0.30 +    # 30%: Average tick latency
            tick_rate_score    * 0.30 +    # 30%: Ticks per minute
            error_score        * 0.20 +    # 20%: Error rate in last 5 min
            staleness_score    * 0.20      # 20%: Time since last tick
        )

        **Component scoring:**
        - latency_score: 100 if <100ms, 50 if 100-500ms, 0 if >1000ms
        - tick_rate_score: min(100, tick_count_1min * 2) // Expected ~50 ticks/min
        - error_score: max(0, 100 - error_count_5min * 20)
        - staleness_score: 100 if last_tick <10s ago, else max(0, 100 - seconds*2)
        """
        # Connection (30%)
        connection = 100.0 if health.is_connected else 0.0

        # Latency (20%)
        if health.avg_latency_ms < 100:
            latency = 100.0
        elif health.avg_latency_ms < 500:
            latency = 50.0
        else:
            latency = 0.0

        # Errors (20%)
        if health.error_count_60s == 0:
            errors = 100.0
        elif health.error_count_60s <= 3:
            errors = 50.0
        else:
            errors = 0.0

        # Freshness (30%)
        if health.last_tick_time:
            seconds_since = (datetime.utcnow() - health.last_tick_time).total_seconds()
            if seconds_since < 5:
                freshness = 100.0
            elif seconds_since < 30:
                freshness = 50.0
            else:
                freshness = 0.0
        else:
            freshness = 0.0

        return connection * 0.30 + latency * 0.20 + errors * 0.20 + freshness * 0.30
```

---

## 9. FailoverController

**Location**: `backend/app/services/brokers/market_data/ticker/failover.py`

```python
from dataclasses import dataclass


@dataclass
class FailoverConfig:
    """Configurable failover thresholds."""
    primary_broker: str = "smartapi"
    secondary_broker: str = "kite"
    health_threshold: float = 30.0          # Trigger failover below this score
    consecutive_checks: int = 3             # Must be below threshold for N checks
    failback_threshold: float = 70.0        # Trigger failback above this score
    failback_sustained_seconds: float = 60  # Primary must be healthy for this long
    flap_prevention_seconds: float = 120    # Minimum seconds between failover events
    overlap_seconds: float = 2.0            # Both adapters active during switchover


class FailoverController:
    """
    Automatic failover between primary and secondary ticker adapters.

    Uses make-before-break pattern:
    1. Connect and subscribe on secondary
    2. Wait overlap_seconds (both adapters active)
    3. Switch user routing to secondary
    4. Unsubscribe from primary

    Flap prevention: Won't failover again within flap_prevention_seconds.
    Failback: Switches back when primary recovers (health > failback_threshold
    sustained for failback_sustained_seconds).
    """

    _instance: Optional["FailoverController"] = None

    @classmethod
    def get_instance(cls, config: Optional[FailoverConfig] = None) -> "FailoverController":
        """
        Get singleton instance.

        Args:
            config: Required on first instantiation, ignored on subsequent calls.

        Raises:
            ValueError: If config not provided on first instantiation.
        """
        if cls._instance is None:
            if config is None:
                raise ValueError("FailoverConfig required for first instantiation")
            cls._instance = cls(config)
        return cls._instance

    def __init__(self, config: Optional[FailoverConfig] = None):
        self._config = config or FailoverConfig()
        self._pool = None
        self._router = None
        self._health_monitor = None
        self._active_broker: str = self._config.primary_broker
        self._is_failed_over: bool = False
        self._last_failover_time: Optional[datetime] = None
        self._primary_recovery_start: Optional[datetime] = None

    def set_dependencies(self, pool, router, health_monitor) -> None:
        self._pool = pool
        self._router = router
        self._health_monitor = health_monitor

    @property
    def active_broker(self) -> str:
        return self._active_broker

    @property
    def is_failed_over(self) -> bool:
        return self._is_failed_over

    async def on_health_change(self, broker_type: str, score: float) -> None:
        """Called by HealthMonitor. Evaluates failover/failback conditions."""
        health = self._health_monitor.get_health(broker_type)
        if not health:
            return

        # Check failover condition (primary degraded)
        if (broker_type == self._config.primary_broker
                and not self._is_failed_over
                and health.consecutive_low_count >= self._config.consecutive_checks):
            await self._maybe_failover()

        # Check failback condition (primary recovered)
        if self._is_failed_over and broker_type == self._config.primary_broker:
            if score >= self._config.failback_threshold:
                await self._maybe_failback(score)
            else:
                # Reset recovery timer if score drops during recovery period
                self._primary_recovery_start = None

    async def _maybe_failover(self) -> None:
        """Execute failover if flap prevention allows."""
        if self._last_failover_time:
            elapsed = (datetime.utcnow() - self._last_failover_time).total_seconds()
            if elapsed < self._config.flap_prevention_seconds:
                logger.info(f"[Failover] Skipping — too recent ({elapsed:.0f}s < {self._config.flap_prevention_seconds}s)")
                return

        await self._execute_failover(self._config.primary_broker, self._config.secondary_broker)

    async def _execute_failover(self, from_broker: str, to_broker: str) -> None:
        """
        Make-before-break failover sequence.

        Step 1: Create secondary adapter (if not exists) with system credentials
        Step 2: Subscribe all current tokens on secondary
        Step 3: Wait overlap period (both adapters active)
        Step 4: Switch user routing to secondary
        Step 5: Unsubscribe from primary
        """
        logger.warning(f"[Failover] Executing: {from_broker} → {to_broker}")

        # Step 1-2: Ensure secondary is connected and subscribed
        tokens = self._router.get_tokens_for_broker(from_broker)
        secondary = await self._pool.get_adapter(to_broker)
        if tokens:
            await secondary.subscribe(list(tokens))

        # Step 3: Overlap period
        await asyncio.sleep(self._config.overlap_seconds)

        # Step 4: Switch routing
        await self._router.switch_users_broker(from_broker, to_broker)

        # Step 5: Clean up primary subscriptions
        primary = self._pool._adapters.get(from_broker)
        if primary and tokens:
            await primary.unsubscribe(list(tokens))

        self._active_broker = to_broker
        self._is_failed_over = True
        self._last_failover_time = datetime.utcnow()
        self._primary_recovery_start = None

        logger.warning(f"[Failover] Complete: now using {to_broker}")

    async def _maybe_failback(self, score: float) -> None:
        """Failback to primary if health sustained above threshold."""
        if self._primary_recovery_start is None:
            self._primary_recovery_start = datetime.utcnow()

        elapsed = (datetime.utcnow() - self._primary_recovery_start).total_seconds()
        if elapsed >= self._config.failback_sustained_seconds:
            await self._execute_failback()

    async def _execute_failback(self) -> None:
        """Reverse failover: switch back to primary broker."""
        logger.info(f"[Failover] Failback: {self._active_broker} → {self._config.primary_broker}")

        tokens = self._router.get_tokens_for_broker(self._active_broker)
        primary = await self._pool.get_adapter(self._config.primary_broker)
        if tokens:
            await primary.subscribe(list(tokens))

        await asyncio.sleep(self._config.overlap_seconds)
        await self._router.switch_users_broker(self._active_broker, self._config.primary_broker)

        secondary = self._pool._adapters.get(self._active_broker)
        if secondary and tokens:
            await secondary.unsubscribe(list(tokens))

        self._active_broker = self._config.primary_broker
        self._is_failed_over = False
        self._last_failover_time = datetime.utcnow()
        self._primary_recovery_start = None

        logger.info(f"[Failover] Failback complete: now using {self._config.primary_broker}")
```

---

## 10. SystemCredentialManager (REMOVED)

**Status**: ⚠️ **REMOVED IN v2.1** - Functionality merged into TickerPool

**Original ADR-003 v2**: Separate component for managing system credentials
**Current Design (v2.1)**: Credentials managed directly in TickerPool (5 components instead of 6)

**Migration**: All SystemCredentialManager functionality now available via TickerPool methods:
- `TickerPool.load_system_credentials()` - Replaces `SystemCredentialManager.initialize()`
- `TickerPool.refresh_credentials(broker)` - Replaces `SystemCredentialManager.refresh_credentials(broker)`
- `TickerPool._smartapi_refresh_loop()` - Replaces `SystemCredentialManager._smartapi_refresh_loop()`

**Why removed?**
- Simpler architecture (5 components vs 6)
- Reduced wiring complexity (one less dependency to inject)
- Credentials naturally belong with adapter lifecycle management

**See**: [TickerPool section](#6-tickerpool) for integrated credential management API

---

## ~~10. SystemCredentialManager (Original - Deprecated)~~

**Location**: `backend/app/services/brokers/market_data/ticker/credential_manager.py`

```python
class SystemCredentialManager:
    """
    Manages app-level broker credentials for Tier 1 (market data).

    Responsibilities:
    - Load credentials from system_broker_credentials table on startup
    - Authenticate with each configured broker
    - Auto-refresh tokens before expiry (per-broker schedules)
    - Serve credentials to TickerPool when adapters are created

    DB Model: SystemBrokerCredential (see backend/app/models/system_broker_credentials.py)
    """

    _instance: Optional["SystemCredentialManager"] = None

    @classmethod
    def get_instance(cls) -> "SystemCredentialManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._credentials: Dict[str, dict] = {}    # broker → credentials dict
        self._refresh_tasks: Dict[str, asyncio.Task] = {}

    async def initialize(self) -> None:
        """
        Called during main.py startup.

        1. Load system_broker_credentials from DB
        2. Authenticate each configured broker
        3. Start per-broker refresh loops
        """
        # SmartAPI: auto-TOTP authentication
        # Dhan: validate static token
        # Upstox: validate extended token
        # Fyers/Paytm: OAuth refresh
        # Kite: log limitation (requires user OAuth)
        pass  # Full implementation in implementation guide

    async def get_credentials(self, broker_type: str) -> dict:
        """
        Get current valid credentials for a broker.

        Returns:
            SmartAPI: {jwt_token, api_key, client_id, feed_token}
            Kite:     {access_token, api_key}
            Upstox:   {access_token}
            Dhan:     {client_id, access_token}
            Fyers:    {access_token, app_id}
            Paytm:    {public_access_token}

        Raises:
            ValueError: If broker not configured or credentials unavailable.
        """
        if broker_type not in self._credentials:
            raise ValueError(f"No system credentials configured for {broker_type}")
        return self._credentials[broker_type]

    async def shutdown(self) -> None:
        """Cancel all refresh tasks. Called from main.py shutdown."""
        for task in self._refresh_tasks.values():
            task.cancel()
        self._refresh_tasks.clear()
```

**DB Model: `SystemBrokerCredential`**

**Location**: `backend/app/models/system_broker_credentials.py`

```python
from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class SystemBrokerCredential(Base):
    """System-level broker credentials for Tier 1 (market data)."""
    __tablename__ = "system_broker_credentials"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    broker = Column(String(20), nullable=False, unique=True, index=True)

    # Encrypted credential storage
    jwt_token = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    feed_token = Column(Text, nullable=True)
    api_key = Column(Text, nullable=True)
    api_secret = Column(Text, nullable=True)

    # Session metadata
    client_id = Column(String(50), nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_auth_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

---

## 11. Refactored websocket.py

**Location**: `backend/app/api/routes/websocket.py`

Complete replacement (~90 lines, down from 495):

```python
"""
WebSocket Ticker Route (Refactored)

Broker-agnostic. All broker-specific logic lives in TickerAdapter implementations.
This route only handles: JWT auth, user registration, message relay, cleanup.
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.brokers.market_data.ticker.router import TickerRouter
from app.models import UserPreferences, User
from app.config import settings
from app.utils.jwt import verify_jwt_token

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_user_from_token(token: str, db: AsyncSession) -> User:
    """
    Authenticate WebSocket connection via JWT token.

    This is a local helper (not from app.utils.dependencies) because WebSocket auth
    takes (token, db) directly, unlike FastAPI dependencies which use Depends(security).
    """
    payload = verify_jwt_token(token)
    if not payload:
        raise ValueError("Invalid or expired token")

    user_id = payload.get("user_id")
    user = await db.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    return user


@router.websocket("/ws/ticks")
async def websocket_ticks(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for live market data ticks.

    Protocol: See docs/api/multi-broker-ticker-api.md Section 12.
    """
    user = None
    user_id = None
    ticker_router = TickerRouter.get_instance()

    try:
        await websocket.accept()

        # Authenticate user
        async for db in get_db():
            user = await get_user_from_token(token, db)
            user_id = str(user.id)

            # Get user's preferred market data broker
            prefs = await db.get(UserPreferences, {"user_id": user.id})
            broker_type = (
                prefs.market_data_source if prefs and prefs.market_data_source
                else settings.DEFAULT_MARKET_DATA_BROKER
            )
            break

        # Register user with router
        await ticker_router.register_user(user_id, websocket, broker_type)

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "source": broker_type,
        })

        # Message loop
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            action = data.get("action")

            if action == "subscribe":
                tokens = [int(t) for t in data.get("tokens", [])]
                mode = data.get("mode", "quote")
                await ticker_router.subscribe(user_id, tokens, mode)
                await websocket.send_json({
                    "type": "subscribed",
                    "tokens": tokens,
                    "mode": mode,
                    "source": broker_type,
                })

            elif action == "unsubscribe":
                tokens = [int(t) for t in data.get("tokens", [])]
                await ticker_router.unsubscribe(user_id, tokens)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "tokens": tokens,
                })

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected")

    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")

    finally:
        if user_id:
            await ticker_router.unregister_user(user_id)
```

---

## 12. WebSocket Message Protocol

### Client → Server

| Message | Format | Description |
|---------|--------|-------------|
| **Subscribe** | `{"action": "subscribe", "tokens": [256265, 260105], "mode": "quote"}` | Subscribe to canonical tokens. Modes: `ltp`, `quote`, `full`. |
| **Unsubscribe** | `{"action": "unsubscribe", "tokens": [256265]}` | Unsubscribe from tokens. |
| **Ping** | `{"action": "ping"}` | Keepalive ping. |

### Server → Client

| Message | Format | Description |
|---------|--------|-------------|
| **Connected** | `{"type": "connected", "source": "smartapi"}` | Connection confirmed. `source` = active data broker. |
| **Subscribed** | `{"type": "subscribed", "tokens": [256265], "mode": "quote", "source": "smartapi"}` | Subscription confirmed. |
| **Unsubscribed** | `{"type": "unsubscribed", "tokens": [256265]}` | Unsubscription confirmed. |
| **Ticks** | `{"type": "ticks", "data": [{"token": 256265, "ltp": 24500.50, "change": -45.25, "change_percent": -0.18, "volume": 15000000, "oi": 0, "ohlc": {"open": 24550.0, "high": 24575.25, "low": 24480.0, "close": 24545.75}}]}` | Live tick data. Prices in rupees. |
| **Failover** | `{"type": "failover", "from": "smartapi", "to": "kite", "message": "Switched to Kite (SmartAPI recovering)"}` | Data source changed due to failover. Connection stays open. |
| **Pong** | `{"type": "pong"}` | Response to ping. |
| **Error** | `{"type": "error", "message": "Invalid token format"}` | Error response. |

---

## 13. Configuration Reference

**Location**: `backend/app/config.py` — Add to `Settings` class:

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `DEFAULT_MARKET_DATA_BROKER` | str | `"smartapi"` | Default broker for market data when user has no preference |
| `TICKER_PRIMARY_BROKER` | str | `"smartapi"` | Primary broker for failover controller |
| `TICKER_SECONDARY_BROKER` | str | `"kite"` | Secondary broker for failover |
| `TICKER_IDLE_TIMEOUT_S` | int | `300` | Seconds before disconnecting idle adapter (0 subscriptions) |
| `TICKER_HEALTH_INTERVAL_S` | int | `5` | Health check interval in seconds |
| `TICKER_FAILOVER_THRESHOLD` | float | `30.0` | Health score below which failover triggers |
| `TICKER_FAILOVER_CHECKS` | int | `3` | Consecutive low-health checks before failover |
| `TICKER_FAILBACK_THRESHOLD` | float | `70.0` | Health score above which failback triggers |
| `TICKER_FAILBACK_SUSTAINED_S` | int | `60` | Seconds primary must stay healthy for failback |
| `TICKER_FLAP_PREVENTION_S` | int | `120` | Minimum seconds between failover events |
| `SYSTEM_SMARTAPI_CLIENT_ID` | str | `""` | SmartAPI system client ID |
| `SYSTEM_SMARTAPI_PIN` | str | `""` | SmartAPI system PIN |
| `SYSTEM_SMARTAPI_TOTP_SECRET` | str | `""` | SmartAPI system TOTP secret (base32) |
| `SYSTEM_DHAN_ACCESS_TOKEN` | str | `""` | Dhan static API token |
| `SYSTEM_DHAN_CLIENT_ID` | str | `""` | Dhan client ID |
| `SYSTEM_UPSTOX_ACCESS_TOKEN` | str | `""` | Upstox extended token |
| `SYSTEM_FYERS_ACCESS_TOKEN` | str | `""` | Fyers OAuth access token |
| `SYSTEM_FYERS_APP_ID` | str | `""` | Fyers app ID |
| `SYSTEM_PAYTM_PUBLIC_TOKEN` | str | `""` | Paytm public access token for WS |

---

## 14. Health API Endpoint

### `GET /api/ticker/health`

**Location**: Add to `backend/app/api/routes/health.py` or new `ticker_health.py`

**Response:**

```json
{
    "active_broker": "smartapi",
    "is_failed_over": false,
    "connected_users": 5,
    "total_subscriptions": 12,
    "adapters": {
        "smartapi": {
            "broker_type": "smartapi",
            "is_connected": true,
            "health_score": 95.0,
            "tick_count_60s": 342,
            "error_count_60s": 0,
            "last_tick_time": "2026-02-13T10:30:05.123Z",
            "last_error": null,
            "avg_latency_ms": 45.2,
            "consecutive_low_count": 0
        },
        "kite": {
            "broker_type": "kite",
            "is_connected": false,
            "health_score": 0.0,
            "tick_count_60s": 0,
            "error_count_60s": 0,
            "last_tick_time": null,
            "last_error": null,
            "avg_latency_ms": 0.0,
            "consecutive_low_count": 0
        }
    },
    "failover": {
        "primary": "smartapi",
        "secondary": "kite",
        "is_failed_over": false,
        "last_failover_time": null
    }
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-02-13 | Complete rewrite for ADR-003 v2 (5-component architecture) |
| 1.0.0 | 2026-02-13 | Initial API reference for Multiton pattern (superseded) |
