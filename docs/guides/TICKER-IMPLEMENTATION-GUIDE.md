# Multi-Broker Ticker System - Step-by-Step Implementation Guide

**Status:** Ready for Implementation
**Date:** February 16, 2026
**Design Reference:** [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md)
**Estimated Time:** ~28 hours (across 5 phases)

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Implementation Phases Overview](#implementation-phases-overview)
3. [Phase T1: Core Infrastructure](#phase-t1-core-infrastructure-6-hours)
4. [Phase T2: SmartAPI + Kite Adapters](#phase-t2-smartapi--kite-adapters-8-hours)
5. [Phase T3: Health + Failover](#phase-t3-health--failover-6-hours)
6. [Phase T4: System Credentials + Remaining Adapters](#phase-t4-system-credentials--remaining-adapters-6-hours)
7. [Phase T5: Frontend + Cleanup](#phase-t5-frontend--cleanup-2-hours)
8. [Testing Strategy](#testing-strategy)
9. [Migration from Legacy](#migration-from-legacy)
10. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Before Starting

1. ✅ **Read Design Documents:**
   - [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md) - Current 5-component design
   - [ADR-002: Broker Abstraction](../decisions/002-broker-abstraction.md) - Multi-broker architecture
   - [ADR-003 v2](../decisions/003-multi-broker-ticker-architecture.md) - Original proposal (reference only)

2. ✅ **Understand Current Code:**
   - `backend/app/services/legacy/smartapi_ticker.py` (463 lines) - Current SmartAPI WebSocket
   - `backend/app/services/legacy/kite_ticker.py` (390 lines) - Current Kite WebSocket
   - `backend/app/api/routes/websocket.py` (494 lines) - Current route (to be refactored)

3. ✅ **Environment Setup:**
   - Python 3.11+
   - PostgreSQL database (for `system_broker_credentials` table)
   - Redis (already in use for sessions)
   - Dev backend running on port 8001

4. ✅ **Create Git Branch:**
   ```bash
   git checkout -b feat/ticker-architecture-v2
   git tag pre-ticker-refactor  # Rollback point
   ```

### Key Design Decisions to Remember

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **5 components, not 6** | SystemCredentialManager merged into TickerPool | Simpler wiring, fewer dependencies |
| **Decimal for prices** | Eliminates floating-point precision errors | All adapters must normalize to Decimal |
| **Canonical token format** | Kite instrument_token = internal standard | Token translation needed for all non-Kite brokers |
| **Lazy adapter creation** | Adapters created only when first user subscribes | No idle resource consumption |
| **Ref-counted subscriptions** | 100 users on NIFTY = 1 broker subscription | Efficient broker API usage |

---

## Implementation Phases Overview

| Phase | Components | Files | Time | Deliverable |
|-------|-----------|-------|------|-------------|
| **T1** | Core Infrastructure | models.py, adapter_base.py, pool.py, router.py | 6h | Abstract interfaces, singletons, wiring |
| **T2** | SmartAPI + Kite | adapters/smartapi.py, adapters/kite.py, websocket.py | 8h | 2 working adapters, refactored route |
| **T3** | Health + Failover | health.py, failover.py | 6h | Monitoring + automatic failover |
| **T4** | System Credentials + Stubs | system_broker_credentials.py, upstox/dhan/fyers/paytm adapters | 6h | Database model, credential loading, adapter stubs |
| **T5** | Frontend + Cleanup | Frontend WebSocket handling, legacy service removal | 2h | Production-ready |

**Total:** ~28 hours

---

## Phase T1: Core Infrastructure (6 hours)

### Goal
Create the foundational architecture: NormalizedTick data model, TickerAdapter abstract base, TickerPool singleton, TickerRouter singleton. No broker-specific code yet.

### Step 1.1: Create Directory Structure (15 min)

```bash
cd backend/app/services/brokers/market_data
mkdir -p ticker/adapters
touch ticker/__init__.py
touch ticker/models.py
touch ticker/adapter_base.py
touch ticker/pool.py
touch ticker/router.py
touch ticker/adapters/__init__.py
```

**Verification:**
```bash
tree backend/app/services/brokers/market_data/ticker
# Should show:
# ticker/
# ├── __init__.py
# ├── models.py
# ├── adapter_base.py
# ├── pool.py
# ├── router.py
# └── adapters/
#     └── __init__.py
```

---

### Step 1.2: Implement NormalizedTick Data Model (30 min)

**File:** `backend/app/services/brokers/market_data/ticker/models.py`

```python
"""
Universal tick data model for multi-broker ticker system.

All broker adapters convert their specific tick formats to this normalized structure.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class NormalizedTick:
    """
    Universal tick format. All adapters convert to this structure.

    Design Decisions:
    - Uses Decimal for prices (not float) to eliminate floating-point precision errors
    - All prices in RUPEES (paise conversion done by adapters)
    - Canonical Kite instrument_token as the primary identifier
    - IST timezone for timestamp
    """
    token: int                      # Canonical Kite instrument token (e.g., 256265 for NIFTY)
    ltp: Decimal                    # Last traded price in RUPEES
    open: Decimal                   # Open price in RUPEES
    high: Decimal                   # High price in RUPEES
    low: Decimal                    # Low price in RUPEES
    close: Decimal                  # Previous close in RUPEES
    change: Decimal                 # Absolute change: ltp - close
    change_percent: Decimal         # Percentage change: ((ltp - close) / close) * 100
    volume: int                     # Total volume traded
    oi: int                         # Open interest (0 for non-F&O instruments)
    timestamp: datetime             # Tick timestamp in IST
    broker_type: str                # Source broker: "smartapi", "kite", "upstox", etc.

    # Optional fields (may not be available from all brokers)
    bid: Optional[Decimal] = None   # Best bid price
    ask: Optional[Decimal] = None   # Best ask price
    bid_qty: Optional[int] = None   # Best bid quantity
    ask_qty: Optional[int] = None   # Best ask quantity

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for WebSocket transmission."""
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

**Testing:**
```python
# Quick sanity test in Python REPL
from backend.app.services.brokers.market_data.ticker.models import NormalizedTick
from datetime import datetime
from decimal import Decimal
import pytz

tick = NormalizedTick(
    token=256265,
    ltp=Decimal("24500.50"),
    open=Decimal("24400.00"),
    high=Decimal("24550.25"),
    low=Decimal("24380.00"),
    close=Decimal("24450.75"),
    change=Decimal("49.75"),
    change_percent=Decimal("0.20"),
    volume=1234567,
    oi=5678900,
    timestamp=datetime.now(pytz.timezone('Asia/Kolkata')),
    broker_type="smartapi"
)

print(tick.to_dict())
# Should output valid JSON-serializable dict
```

---

### Step 1.3: Implement TickerAdapter Abstract Base (90 min)

**File:** `backend/app/services/brokers/market_data/ticker/adapter_base.py`

```python
"""
Abstract base class for broker-specific ticker adapters.

Each broker (SmartAPI, Kite, Upstox, etc.) implements this interface
to provide a uniform WebSocket tick streaming API.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, List, Optional, Set, Any
from decimal import Decimal

from .models import NormalizedTick


logger = logging.getLogger(__name__)


class TickerAdapter(ABC):
    """
    Abstract base for broker-specific WebSocket ticker adapters.

    Each broker's adapter handles:
    1. WebSocket connection lifecycle
    2. Binary/JSON/Protobuf tick parsing
    3. Token translation (broker format ↔ canonical Kite format)
    4. Price normalization (paise→rupees where needed)
    5. Tick conversion to NormalizedTick
    6. Thread→asyncio bridge (for blocking WS libraries)

    Concrete implementations:
    - SmartAPITickerAdapter (binary, threading)
    - KiteTickerAdapter (binary, threading)
    - UpstoxTickerAdapter (protobuf, asyncio-native)
    - DhanTickerAdapter (little-endian binary, threading)
    - FyersTickerAdapter (JSON, asyncio-native)
    - PaytmTickerAdapter (JSON, asyncio-native)
    """

    def __init__(self, broker_type: str):
        self.broker_type = broker_type
        self._is_connected = False
        self._subscribed_tokens: Set[int] = set()  # Canonical tokens
        self._last_tick_time: Optional[datetime] = None
        self._on_tick_callback: Optional[Callable[[List[NormalizedTick]], None]] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        logger.info(f"[{self.broker_type}] TickerAdapter initialized")

    # ========== Public API (called by TickerPool) ==========

    async def connect(self, credentials: dict) -> None:
        """
        Connect to broker WebSocket with provided credentials.

        Args:
            credentials: Broker-specific credentials dict. Format varies per broker:
                SmartAPI: {jwt_token, api_key, client_id, feed_token}
                Kite: {api_key, access_token}
                Upstox: {access_token}
                Dhan: {access_token}
                Fyers: {app_id, access_token}
                Paytm: {public_access_token}

        Raises:
            ConnectionError: If connection fails after retries
        """
        if self._is_connected:
            logger.warning(f"[{self.broker_type}] Already connected, skipping")
            return

        try:
            logger.info(f"[{self.broker_type}] Connecting to WebSocket...")
            await self._connect_ws(credentials)
            self._is_connected = True
            logger.info(f"[{self.broker_type}] Connected successfully")
        except Exception as e:
            logger.error(f"[{self.broker_type}] Connection failed: {e}")
            raise ConnectionError(f"Failed to connect {self.broker_type}: {e}")

    async def disconnect(self) -> None:
        """Disconnect from broker WebSocket and cleanup resources."""
        if not self._is_connected:
            logger.warning(f"[{self.broker_type}] Not connected, skipping disconnect")
            return

        try:
            logger.info(f"[{self.broker_type}] Disconnecting...")
            await self._disconnect_ws()
            self._is_connected = False
            self._subscribed_tokens.clear()
            logger.info(f"[{self.broker_type}] Disconnected successfully")
        except Exception as e:
            logger.error(f"[{self.broker_type}] Disconnect error: {e}")

    async def reconnect(self, credentials: dict, max_retries: int = 5) -> bool:
        """
        Reconnect to broker WebSocket with exponential backoff.

        Args:
            credentials: Broker credentials (same format as connect())
            max_retries: Maximum reconnection attempts

        Returns:
            True if reconnect successful, False otherwise
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[{self.broker_type}] Reconnect attempt {attempt}/{max_retries}")
                await self.disconnect()
                await asyncio.sleep(2 ** attempt)  # Exponential backoff: 2, 4, 8, 16, 32 seconds
                await self.connect(credentials)

                # Re-subscribe to previously subscribed tokens
                if self._subscribed_tokens:
                    logger.info(f"[{self.broker_type}] Re-subscribing to {len(self._subscribed_tokens)} tokens")
                    await self.subscribe(list(self._subscribed_tokens))

                return True
            except Exception as e:
                logger.error(f"[{self.broker_type}] Reconnect attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    return False

        return False

    async def subscribe(self, canonical_tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe to live ticks for given canonical tokens.

        Args:
            canonical_tokens: List of Kite instrument tokens (e.g., [256265, 260105])
            mode: Tick mode ("ltp", "quote", "full"). Default: "quote"

        Raises:
            ValueError: If mode invalid or tokens empty
        """
        if not canonical_tokens:
            logger.warning(f"[{self.broker_type}] Empty token list, skipping subscribe")
            return

        if not self._is_connected:
            raise ConnectionError(f"[{self.broker_type}] Cannot subscribe: not connected")

        # Translate canonical tokens → broker-specific format
        broker_tokens = self._translate_to_broker_tokens(canonical_tokens)

        try:
            logger.info(f"[{self.broker_type}] Subscribing to {len(canonical_tokens)} tokens (mode={mode})")
            await self._subscribe_ws(broker_tokens, mode)
            self._subscribed_tokens.update(canonical_tokens)
            logger.info(f"[{self.broker_type}] Subscribed successfully. Total: {len(self._subscribed_tokens)}")
        except Exception as e:
            logger.error(f"[{self.broker_type}] Subscribe error: {e}")
            raise

    async def unsubscribe(self, canonical_tokens: List[int]) -> None:
        """
        Unsubscribe from live ticks for given canonical tokens.

        Args:
            canonical_tokens: List of Kite instrument tokens to unsubscribe
        """
        if not canonical_tokens:
            return

        if not self._is_connected:
            logger.warning(f"[{self.broker_type}] Cannot unsubscribe: not connected")
            return

        broker_tokens = self._translate_to_broker_tokens(canonical_tokens)

        try:
            logger.info(f"[{self.broker_type}] Unsubscribing from {len(canonical_tokens)} tokens")
            await self._unsubscribe_ws(broker_tokens)
            self._subscribed_tokens.difference_update(canonical_tokens)
            logger.info(f"[{self.broker_type}] Unsubscribed. Remaining: {len(self._subscribed_tokens)}")
        except Exception as e:
            logger.error(f"[{self.broker_type}] Unsubscribe error: {e}")

    def set_on_tick_callback(self, callback: Callable[[List[NormalizedTick]], None]) -> None:
        """
        Set callback function to receive normalized ticks.

        Args:
            callback: Async function that receives List[NormalizedTick]
        """
        self._on_tick_callback = callback
        logger.debug(f"[{self.broker_type}] Tick callback set")

    async def update_credentials(self, credentials: dict) -> None:
        """
        Update credentials (e.g., after token refresh).

        Default implementation: disconnect + reconnect.
        Subclasses can override for hot credential updates if broker supports it.

        Args:
            credentials: New broker credentials
        """
        logger.info(f"[{self.broker_type}] Updating credentials (will reconnect)")
        await self.reconnect(credentials)

    # ========== Properties ==========

    @property
    def is_connected(self) -> bool:
        """Whether WebSocket is currently connected."""
        return self._is_connected

    @property
    def subscribed_tokens(self) -> Set[int]:
        """Set of canonical tokens currently subscribed."""
        return self._subscribed_tokens.copy()

    @property
    def last_tick_time(self) -> Optional[datetime]:
        """Timestamp of last received tick (for health monitoring)."""
        return self._last_tick_time

    # ========== Abstract Methods (broker-specific implementation) ==========

    @abstractmethod
    async def _connect_ws(self, credentials: dict) -> None:
        """
        Broker-specific WebSocket connection logic.

        Implementation notes:
        - SmartAPI: threading.Thread + SmartWebSocketV2
        - Kite: threading + KiteTicker
        - Upstox/Fyers/Paytm: asyncio-native websockets
        - Dhan: threading + custom binary protocol
        """
        pass

    @abstractmethod
    async def _disconnect_ws(self) -> None:
        """Broker-specific WebSocket disconnection logic."""
        pass

    @abstractmethod
    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        """
        Broker-specific subscription logic.

        Args:
            broker_tokens: Tokens in broker-specific format (already translated)
            mode: Subscription mode ("ltp", "quote", "full")
        """
        pass

    @abstractmethod
    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        """Broker-specific unsubscription logic."""
        pass

    @abstractmethod
    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Translate canonical Kite tokens to broker-specific format.

        Examples:
        - SmartAPI: 256265 → "99926000" (string, via TokenManager lookup)
        - Kite: 256265 → 256265 (identity, Kite IS canonical)
        - Upstox: 256265 → "NSE_FO|256265" (string with prefix)
        - Dhan: 256265 → {security_id} (via CSV instrument master)
        - Fyers: 256265 → "NSE:NIFTY50-INDEX" (symbol string)
        - Paytm: 256265 → "4.1!{security_id}" (RIC format)

        Returns:
            List of broker-specific tokens (type varies: str, int, dict)
        """
        pass

    @abstractmethod
    def _parse_tick(self, raw_data: Any) -> List[NormalizedTick]:
        """
        Parse broker-specific tick data to NormalizedTick.

        Args:
            raw_data: Raw tick data from broker WS (format varies per broker)

        Returns:
            List of NormalizedTick objects

        Implementation notes:
        - Extract broker-specific token → translate to canonical
        - Normalize prices (paise→rupees if needed)
        - Convert to Decimal
        - Calculate change and change_percent
        - Set broker_type field
        """
        pass

    @abstractmethod
    def _get_canonical_token(self, broker_token: Any) -> int:
        """
        Extract canonical Kite token from broker-specific token.

        Inverse of _translate_to_broker_tokens.

        Args:
            broker_token: Token in broker-specific format

        Returns:
            Canonical Kite instrument token (int)
        """
        pass

    # ========== Helper Methods for Tick Dispatching ==========

    def _dispatch_from_thread(self, ticks: List[NormalizedTick]) -> None:
        """
        Dispatch ticks from background thread to asyncio event loop.

        Use this for blocking WebSocket libraries (SmartAPI, Kite, Dhan)
        that run on separate threads.

        Args:
            ticks: List of normalized ticks to dispatch
        """
        if not self._on_tick_callback:
            logger.warning(f"[{self.broker_type}] No tick callback set, dropping {len(ticks)} ticks")
            return

        if not self._event_loop:
            logger.error(f"[{self.broker_type}] Event loop not set, cannot dispatch from thread")
            return

        # Schedule callback on the asyncio event loop
        asyncio.run_coroutine_threadsafe(
            self._dispatch_async(ticks),
            self._event_loop
        )

    async def _dispatch_async(self, ticks: List[NormalizedTick]) -> None:
        """
        Dispatch ticks to callback (async context).

        Use this for asyncio-native WebSocket libraries (Upstox, Fyers, Paytm).

        Args:
            ticks: List of normalized ticks to dispatch
        """
        if not self._on_tick_callback:
            return

        if ticks:
            self._last_tick_time = datetime.now()
            await self._on_tick_callback(ticks)

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Set the asyncio event loop for thread→asyncio bridge.

        Required for adapters using threading (SmartAPI, Kite, Dhan).

        Args:
            loop: The asyncio event loop to dispatch ticks to
        """
        self._event_loop = loop
        logger.debug(f"[{self.broker_type}] Event loop set")
```

**Verification:**
```bash
# Check if file parses without errors
python -m py_compile backend/app/services/brokers/market_data/ticker/adapter_base.py
```

---

### Step 1.4: Implement TickerPool Singleton (120 min)

**File:** `backend/app/services/brokers/market_data/ticker/pool.py`

```python
"""
TickerPool: Singleton that manages adapter lifecycle, credentials, and subscriptions.

Responsibilities:
- Lazy adapter creation (create only when needed)
- Ref-counted subscription aggregation (100 users on NIFTY = 1 broker subscription)
- System credentials loading and refresh
- Adapter→Router tick dispatching
- Failover subscription migration
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict

from app.database import get_db
from app.models.system_broker_credentials import SystemBrokerCredential
from app.utils.encryption import decrypt_field
from app.services.legacy.smartapi_auth import SmartAPIAuth

from .adapter_base import TickerAdapter
from .models import NormalizedTick


logger = logging.getLogger(__name__)


class TickerPool:
    """
    Singleton that manages all ticker adapters.

    Design pattern:
    - Lazy creation: Adapters created only when first subscription arrives
    - Ref-counting: Tracks how many users subscribed to each token per broker
    - Idle cleanup: Disconnects adapters with zero subscriptions after 5 minutes
    - Credential management: Loads system credentials + manages refresh loops
    """

    _instance: Optional["TickerPool"] = None

    def __init__(self):
        if TickerPool._instance is not None:
            raise RuntimeError("TickerPool is a singleton. Use get_instance()")

        self._adapters: Dict[str, TickerAdapter] = {}  # broker_type → adapter
        self._adapter_registry: Dict[str, type] = {}  # broker_type → adapter class

        # Ref-counted subscriptions: broker_type → {canonical_token → ref_count}
        self._subscriptions: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

        # System credentials: broker_type → credentials dict
        self._credentials: Dict[str, dict] = {}

        # Per-broker credential refresh tasks
        self._refresh_tasks: Dict[str, asyncio.Task] = {}

        # Dependencies (injected during initialization)
        self._router: Optional["TickerRouter"] = None  # type: ignore
        self._health_monitor: Optional["HealthMonitor"] = None  # type: ignore

        # Idle cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._idle_threshold = timedelta(minutes=5)

        TickerPool._instance = self
        logger.info("TickerPool singleton created")

    @classmethod
    def get_instance(cls) -> "TickerPool":
        """Get or create the TickerPool singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ========== Initialization ==========

    async def initialize(
        self,
        router: "TickerRouter",  # type: ignore
        health_monitor: Optional["HealthMonitor"] = None  # type: ignore
    ) -> None:
        """
        Initialize TickerPool with dependencies.

        Args:
            router: TickerRouter instance (for tick dispatching)
            health_monitor: HealthMonitor instance (optional, for health tracking)
        """
        self._router = router
        self._health_monitor = health_monitor

        # Load system credentials from database
        await self.load_system_credentials()

        # Start idle cleanup loop
        self._cleanup_task = asyncio.create_task(self._idle_cleanup_loop())

        logger.info("TickerPool initialized with router and health monitor")

    async def shutdown(self) -> None:
        """Shutdown all adapters and cleanup resources."""
        logger.info("Shutting down TickerPool...")

        # Cancel credential refresh tasks
        for task in self._refresh_tasks.values():
            task.cancel()
        self._refresh_tasks.clear()

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Disconnect all adapters
        for broker_type, adapter in self._adapters.items():
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting {broker_type}: {e}")

        self._adapters.clear()
        self._subscriptions.clear()

        logger.info("TickerPool shutdown complete")

    # ========== Adapter Registry ==========

    def register_adapter(self, broker_type: str, adapter_class: type) -> None:
        """
        Register a broker adapter class.

        Args:
            broker_type: Broker identifier ("smartapi", "kite", "upstox", etc.)
            adapter_class: TickerAdapter subclass
        """
        self._adapter_registry[broker_type] = adapter_class
        logger.info(f"Registered adapter: {broker_type} → {adapter_class.__name__}")

    # ========== Subscription Management ==========

    async def subscribe(self, broker_type: str, tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe to tokens on specified broker (with ref-counting).

        Args:
            broker_type: Broker to subscribe on ("smartapi", "kite", etc.)
            tokens: List of canonical Kite instrument tokens
            mode: Subscription mode ("ltp", "quote", "full")
        """
        if not tokens:
            return

        # Get or create adapter
        adapter = await self.get_or_create_adapter(broker_type)

        # Determine which tokens need actual broker subscription (ref_count 0 → 1)
        new_tokens = []
        for token in tokens:
            self._subscriptions[broker_type][token] += 1
            if self._subscriptions[broker_type][token] == 1:
                new_tokens.append(token)

        if new_tokens:
            logger.info(
                f"[{broker_type}] Subscribing to {len(new_tokens)} new tokens "
                f"(total subscriptions: {len(self._subscriptions[broker_type])})"
            )
            await adapter.subscribe(new_tokens, mode)
        else:
            logger.debug(f"[{broker_type}] All {len(tokens)} tokens already subscribed (ref-counted)")

    async def unsubscribe(self, broker_type: str, tokens: List[int]) -> None:
        """
        Unsubscribe from tokens on specified broker (with ref-counting).

        Args:
            broker_type: Broker to unsubscribe from
            tokens: List of canonical Kite instrument tokens
        """
        if not tokens or broker_type not in self._adapters:
            return

        adapter = self._adapters[broker_type]

        # Determine which tokens need actual broker unsubscription (ref_count 1 → 0)
        to_unsubscribe = []
        for token in tokens:
            if token in self._subscriptions[broker_type]:
                self._subscriptions[broker_type][token] -= 1
                if self._subscriptions[broker_type][token] <= 0:
                    del self._subscriptions[broker_type][token]
                    to_unsubscribe.append(token)

        if to_unsubscribe:
            logger.info(
                f"[{broker_type}] Unsubscribing from {len(to_unsubscribe)} tokens "
                f"(remaining subscriptions: {len(self._subscriptions[broker_type])})"
            )
            await adapter.unsubscribe(to_unsubscribe)

    # ========== Adapter Lifecycle ==========

    async def get_or_create_adapter(self, broker_type: str) -> TickerAdapter:
        """
        Get existing adapter or create new one (lazy creation).

        Args:
            broker_type: Broker identifier

        Returns:
            TickerAdapter instance

        Raises:
            ValueError: If broker_type not registered or no credentials available
        """
        # Return existing adapter if already created
        if broker_type in self._adapters:
            return self._adapters[broker_type]

        # Validate broker is registered
        if broker_type not in self._adapter_registry:
            raise ValueError(
                f"Broker '{broker_type}' not registered. "
                f"Available: {list(self._adapter_registry.keys())}"
            )

        # Validate credentials exist
        if broker_type not in self._credentials:
            raise ValueError(
                f"No system credentials for '{broker_type}'. "
                "Ensure system_broker_credentials table has entry."
            )

        # Create adapter
        adapter_class = self._adapter_registry[broker_type]
        adapter = adapter_class(broker_type)

        # Set event loop for thread→asyncio bridge (needed for SmartAPI/Kite/Dhan)
        adapter.set_event_loop(asyncio.get_event_loop())

        # Set tick callback to dispatch to router
        adapter.set_on_tick_callback(self._on_adapter_tick)

        # Connect with credentials
        logger.info(f"[{broker_type}] Creating new adapter...")
        await adapter.connect(self._credentials[broker_type])

        # Register with health monitor
        if self._health_monitor:
            self._health_monitor.register_adapter(broker_type)

        # Store adapter
        self._adapters[broker_type] = adapter
        logger.info(f"[{broker_type}] Adapter created and connected")

        return adapter

    async def remove_adapter(self, broker_type: str) -> None:
        """
        Remove adapter (disconnect and cleanup).

        Args:
            broker_type: Broker identifier
        """
        if broker_type not in self._adapters:
            return

        adapter = self._adapters[broker_type]

        try:
            await adapter.disconnect()
        except Exception as e:
            logger.error(f"[{broker_type}] Error disconnecting adapter: {e}")

        # Unregister from health monitor
        if self._health_monitor:
            self._health_monitor.unregister_adapter(broker_type)

        del self._adapters[broker_type]
        logger.info(f"[{broker_type}] Adapter removed")

    # ========== System Credentials Management ==========

    async def load_system_credentials(self) -> None:
        """
        Load system broker credentials from database.

        For each active broker:
        1. Decrypt credentials
        2. Authenticate (SmartAPI: auto-TOTP, others: validate token)
        3. Store in self._credentials
        4. Schedule refresh loop if needed
        """
        logger.info("Loading system broker credentials from database...")

        async for db in get_db():
            # Query active system credentials
            result = await db.execute(
                "SELECT * FROM system_broker_credentials WHERE is_active = TRUE"
            )
            credentials_list = result.fetchall()

            for cred_row in credentials_list:
                broker_type = cred_row.broker

                try:
                    # Decrypt sensitive fields
                    credentials = {
                        "broker": broker_type,
                        "api_key": decrypt_field(cred_row.api_key) if cred_row.api_key else None,
                        "api_secret": decrypt_field(cred_row.api_secret) if cred_row.api_secret else None,
                        "access_token": decrypt_field(cred_row.access_token) if cred_row.access_token else None,
                        "refresh_token": decrypt_field(cred_row.refresh_token) if cred_row.refresh_token else None,
                        "jwt_token": decrypt_field(cred_row.jwt_token) if cred_row.jwt_token else None,
                        "feed_token": decrypt_field(cred_row.feed_token) if cred_row.feed_token else None,
                        "client_id": cred_row.client_id,
                    }

                    # Broker-specific authentication
                    if broker_type == "smartapi":
                        credentials = await self._authenticate_smartapi(credentials)
                    elif broker_type == "kite":
                        logger.warning(
                            "[kite] System credentials not supported (OAuth only). "
                            "Will use first connected user's token as fallback."
                        )
                        continue  # Skip Kite for system credentials
                    # Add other brokers (upstox, dhan, fyers, paytm) authentication here

                    # Store credentials
                    self._credentials[broker_type] = credentials
                    logger.info(f"[{broker_type}] System credentials loaded")

                    # Schedule refresh loop if token expires
                    if broker_type == "smartapi":
                        self._refresh_tasks[broker_type] = asyncio.create_task(
                            self._smartapi_refresh_loop(broker_type)
                        )

                except Exception as e:
                    logger.error(f"[{broker_type}] Failed to load credentials: {e}")

        logger.info(f"System credentials loaded for: {list(self._credentials.keys())}")

    async def _authenticate_smartapi(self, credentials: dict) -> dict:
        """
        Authenticate with SmartAPI using auto-TOTP.

        Args:
            credentials: Encrypted credentials from database

        Returns:
            Credentials dict with jwt_token and feed_token
        """
        logger.info("[smartapi] Authenticating with auto-TOTP...")

        smartapi_auth = SmartAPIAuth(
            api_key=credentials["api_key"],
            client_id=credentials["client_id"],
            totp_secret=credentials.get("totp_secret"),  # May be in api_secret field
        )

        # Auto-TOTP login
        auth_result = await smartapi_auth.login()

        credentials.update({
            "jwt_token": auth_result["jwt_token"],
            "feed_token": auth_result["feed_token"],
            "refresh_token": auth_result.get("refresh_token"),
        })

        logger.info("[smartapi] Authenticated successfully")
        return credentials

    async def refresh_credentials(self, broker_type: str) -> None:
        """
        Refresh credentials for specified broker.

        Args:
            broker_type: Broker to refresh credentials for
        """
        if broker_type not in self._credentials:
            logger.warning(f"[{broker_type}] No credentials to refresh")
            return

        logger.info(f"[{broker_type}] Refreshing credentials...")

        # Broker-specific refresh logic
        if broker_type == "smartapi":
            self._credentials[broker_type] = await self._authenticate_smartapi(
                self._credentials[broker_type]
            )
        # Add other brokers refresh logic here

        # Update adapter if already connected
        if broker_type in self._adapters:
            await self._adapters[broker_type].update_credentials(self._credentials[broker_type])

        logger.info(f"[{broker_type}] Credentials refreshed")

    async def _smartapi_refresh_loop(self, broker_type: str) -> None:
        """
        Auto-refresh SmartAPI credentials 30 minutes before 5 AM IST expiry.

        Args:
            broker_type: Should be "smartapi"
        """
        import pytz

        while True:
            try:
                # Calculate time until next refresh (30 min before 5 AM IST)
                ist = pytz.timezone('Asia/Kolkata')
                now = datetime.now(ist)
                next_expiry = now.replace(hour=5, minute=0, second=0, microsecond=0)
                if now.hour >= 5:
                    next_expiry += timedelta(days=1)  # Tomorrow's 5 AM

                refresh_time = next_expiry - timedelta(minutes=30)  # Refresh at 4:30 AM
                sleep_duration = (refresh_time - now).total_seconds()

                if sleep_duration > 0:
                    logger.info(
                        f"[smartapi] Next credential refresh at {refresh_time.strftime('%Y-%m-%d %H:%M:%S IST')} "
                        f"(in {sleep_duration / 3600:.1f} hours)"
                    )
                    await asyncio.sleep(sleep_duration)

                # Refresh credentials
                await self.refresh_credentials(broker_type)

            except asyncio.CancelledError:
                logger.info(f"[{broker_type}] Refresh loop cancelled")
                break
            except Exception as e:
                logger.error(f"[{broker_type}] Refresh loop error: {e}")
                await asyncio.sleep(300)  # Retry after 5 minutes on error

    # ========== Tick Dispatching ==========

    async def _on_adapter_tick(self, ticks: List[NormalizedTick]) -> None:
        """
        Callback when adapter receives ticks. Dispatches to router.

        Args:
            ticks: List of normalized ticks from adapter
        """
        if not self._router:
            logger.warning("Router not set, dropping ticks")
            return

        # Update health monitor
        if self._health_monitor and ticks:
            broker_type = ticks[0].broker_type
            self._health_monitor.record_ticks(broker_type, len(ticks))

        # Dispatch to router for fan-out to users
        await self._router.dispatch(ticks)

    # ========== Failover Support ==========

    async def migrate_subscriptions(self, from_broker: str, to_broker: str) -> None:
        """
        Migrate subscriptions from one broker to another (for failover).

        Make-before-break pattern:
        1. Subscribe on to_broker (secondary now receiving ticks)
        2. Wait 2s overlap
        3. Router switches user routing
        4. Unsubscribe from from_broker (cleanup)

        Args:
            from_broker: Primary broker (failing)
            to_broker: Secondary broker (taking over)
        """
        if from_broker not in self._adapters:
            logger.error(f"Cannot migrate from '{from_broker}': adapter not found")
            return

        # Get tokens to migrate
        tokens_to_migrate = list(self._subscriptions[from_broker].keys())

        if not tokens_to_migrate:
            logger.warning(f"No tokens to migrate from '{from_broker}'")
            return

        logger.info(
            f"Migrating {len(tokens_to_migrate)} tokens: {from_broker} → {to_broker}"
        )

        try:
            # Step 1: Subscribe on secondary (make)
            await self.subscribe(to_broker, tokens_to_migrate)

            # Step 2: Wait for overlap (both brokers sending ticks)
            await asyncio.sleep(2)

            # Step 3: Router switches (handled by FailoverController)
            # This method only handles adapter subscriptions

            # Step 4: Cleanup primary (break)
            await self.unsubscribe(from_broker, tokens_to_migrate)

            logger.info(f"Migration complete: {from_broker} → {to_broker}")

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

    # ========== Idle Cleanup ==========

    async def _idle_cleanup_loop(self) -> None:
        """
        Periodically check for idle adapters and disconnect them.

        An adapter is idle if it has zero subscriptions for > 5 minutes.
        """
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                for broker_type in list(self._adapters.keys()):
                    # Check if adapter has zero subscriptions
                    if not self._subscriptions[broker_type]:
                        # Check if adapter has been idle for > threshold
                        adapter = self._adapters[broker_type]
                        if adapter.last_tick_time:
                            idle_duration = datetime.now() - adapter.last_tick_time
                            if idle_duration > self._idle_threshold:
                                logger.info(
                                    f"[{broker_type}] Idle for {idle_duration.total_seconds() / 60:.1f} min, "
                                    "disconnecting..."
                                )
                                await self.remove_adapter(broker_type)

            except asyncio.CancelledError:
                logger.info("Idle cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Idle cleanup error: {e}")
```

**Verification:**
```bash
# Check if file parses without errors
python -m py_compile backend/app/services/brokers/market_data/ticker/pool.py
```

---

### Step 1.5: Implement TickerRouter Singleton (90 min)

**File:** `backend/app/services/brokers/market_data/ticker/router.py`

```python
"""
TickerRouter: Singleton that manages user WebSocket connections and tick fan-out.

Responsibilities:
- User WebSocket connection registration
- Token→User subscription mapping
- Hot-path tick dispatching (broadcast to all subscribed users)
- Cached tick delivery (send last tick immediately on subscribe)
- Failover user routing changes
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from collections import defaultdict
from fastapi import WebSocket

from .models import NormalizedTick


logger = logging.getLogger(__name__)


class TickerRouter:
    """
    Singleton that routes ticks from adapters to user WebSockets.

    Design pattern:
    - 1:N fan-out: One tick from adapter → N user WebSockets
    - Subscription mapping: token → {user_id1, user_id2, ...}
    - Cached ticks: Store last tick per token for instant delivery on subscribe
    - Hot path optimization: No locks on dispatch (GIL makes dict reads thread-safe)
    """

    _instance: Optional["TickerRouter"] = None

    def __init__(self):
        if TickerRouter._instance is not None:
            raise RuntimeError("TickerRouter is a singleton. Use get_instance()")

        # User management: user_id → {websocket, broker_type, subscribed_tokens}
        self._users: Dict[str, dict] = {}

        # Token subscriptions: canonical_token → Set[user_id]
        self._token_subscriptions: Dict[int, Set[str]] = defaultdict(set)

        # Cached ticks: canonical_token → NormalizedTick (last tick)
        self._cached_ticks: Dict[int, NormalizedTick] = {}

        # Dependencies
        self._pool: Optional["TickerPool"] = None  # type: ignore

        TickerRouter._instance = self
        logger.info("TickerRouter singleton created")

    @classmethod
    def get_instance(cls) -> "TickerRouter":
        """Get or create the TickerRouter singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ========== Initialization ==========

    def set_pool(self, pool: "TickerPool") -> None:  # type: ignore
        """
        Set TickerPool dependency (for subscribe/unsubscribe forwarding).

        Args:
            pool: TickerPool instance
        """
        self._pool = pool
        logger.info("TickerRouter: TickerPool dependency set")

    # ========== User Management ==========

    async def register_user(
        self,
        user_id: str,
        websocket: WebSocket,
        broker_type: str
    ) -> None:
        """
        Register user WebSocket connection.

        Args:
            user_id: Unique user identifier
            websocket: FastAPI WebSocket connection
            broker_type: User's preferred broker for market data
        """
        if user_id in self._users:
            logger.warning(f"User {user_id} already registered, updating connection")

        self._users[user_id] = {
            "websocket": websocket,
            "broker_type": broker_type,
            "subscribed_tokens": set(),
        }

        logger.info(f"User {user_id} registered (broker={broker_type})")

    async def unregister_user(self, user_id: str) -> None:
        """
        Unregister user and cleanup all subscriptions.

        Args:
            user_id: User identifier to unregister
        """
        if user_id not in self._users:
            logger.warning(f"User {user_id} not found, skipping unregister")
            return

        # Get user's subscriptions
        subscribed_tokens = self._users[user_id]["subscribed_tokens"]
        broker_type = self._users[user_id]["broker_type"]

        # Unsubscribe from all tokens
        if subscribed_tokens:
            await self.unsubscribe(user_id, list(subscribed_tokens))

        # Remove user
        del self._users[user_id]

        logger.info(f"User {user_id} unregistered (cleaned up {len(subscribed_tokens)} subscriptions)")

    # ========== Subscription Management ==========

    async def subscribe(self, user_id: str, tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe user to tokens.

        Args:
            user_id: User identifier
            tokens: List of canonical Kite instrument tokens
            mode: Subscription mode ("ltp", "quote", "full")
        """
        if user_id not in self._users:
            logger.error(f"User {user_id} not registered, cannot subscribe")
            return

        if not tokens:
            return

        user = self._users[user_id]
        broker_type = user["broker_type"]

        # Update token→user mapping
        for token in tokens:
            self._token_subscriptions[token].add(user_id)
            user["subscribed_tokens"].add(token)

        # Forward to pool for broker subscription
        if self._pool:
            await self._pool.subscribe(broker_type, tokens, mode)

        logger.info(
            f"User {user_id} subscribed to {len(tokens)} tokens on {broker_type} "
            f"(total: {len(user['subscribed_tokens'])})"
        )

        # Send cached ticks immediately (instant UI update)
        await self._send_cached_ticks(user_id, tokens)

    async def unsubscribe(self, user_id: str, tokens: List[int]) -> None:
        """
        Unsubscribe user from tokens.

        Args:
            user_id: User identifier
            tokens: List of canonical Kite instrument tokens
        """
        if user_id not in self._users:
            return

        if not tokens:
            return

        user = self._users[user_id]
        broker_type = user["broker_type"]

        # Update token→user mapping
        for token in tokens:
            if token in self._token_subscriptions:
                self._token_subscriptions[token].discard(user_id)
                if not self._token_subscriptions[token]:
                    del self._token_subscriptions[token]

            user["subscribed_tokens"].discard(token)

        # Forward to pool for broker unsubscription (ref-counted)
        if self._pool:
            await self._pool.unsubscribe(broker_type, tokens)

        logger.info(
            f"User {user_id} unsubscribed from {len(tokens)} tokens "
            f"(remaining: {len(user['subscribed_tokens'])})"
        )

    # ========== Tick Dispatching (HOT PATH) ==========

    async def dispatch(self, ticks: List[NormalizedTick]) -> None:
        """
        Dispatch ticks to all subscribed users (HOT PATH - optimize for speed).

        Args:
            ticks: List of normalized ticks from adapter
        """
        if not ticks:
            return

        # Group ticks by token for efficient caching
        for tick in ticks:
            self._cached_ticks[tick.token] = tick

        # Build token→tick dict for fast lookup
        tick_dict = {tick.token: tick for tick in ticks}

        # Dispatch to users (fan-out)
        dispatch_tasks = []
        for token, tick in tick_dict.items():
            if token in self._token_subscriptions:
                for user_id in self._token_subscriptions[token]:
                    if user_id in self._users:
                        dispatch_tasks.append(
                            self._send_tick_to_user(user_id, tick)
                        )

        # Send all ticks concurrently
        if dispatch_tasks:
            await asyncio.gather(*dispatch_tasks, return_exceptions=True)

    async def _send_tick_to_user(self, user_id: str, tick: NormalizedTick) -> None:
        """
        Send single tick to single user WebSocket.

        Args:
            user_id: User identifier
            tick: Normalized tick to send
        """
        if user_id not in self._users:
            return

        user = self._users[user_id]
        websocket = user["websocket"]

        try:
            await websocket.send_json({
                "type": "tick",
                "data": tick.to_dict()
            })
        except Exception as e:
            logger.error(f"Error sending tick to user {user_id}: {e}")
            # Connection broken, unregister user
            await self.unregister_user(user_id)

    async def _send_cached_ticks(self, user_id: str, tokens: List[int]) -> None:
        """
        Send cached ticks for subscribed tokens (instant UI update).

        Args:
            user_id: User identifier
            tokens: List of tokens just subscribed to
        """
        cached_ticks = []
        for token in tokens:
            if token in self._cached_ticks:
                cached_ticks.append(self._cached_ticks[token])

        if cached_ticks:
            logger.debug(f"Sending {len(cached_ticks)} cached ticks to user {user_id}")
            for tick in cached_ticks:
                await self._send_tick_to_user(user_id, tick)

    # ========== Failover Support ==========

    async def switch_users_broker(self, from_broker: str, to_broker: str) -> None:
        """
        Switch all users from one broker to another (for failover).

        Updates user routing without reconnecting WebSockets.

        Args:
            from_broker: Primary broker (failing)
            to_broker: Secondary broker (taking over)
        """
        switched_count = 0

        for user_id, user in self._users.items():
            if user["broker_type"] == from_broker:
                user["broker_type"] = to_broker
                switched_count += 1

        logger.info(f"Switched {switched_count} users: {from_broker} → {to_broker}")

        # Send failover notification to all users
        await self._broadcast_failover_notification(from_broker, to_broker)

    async def _broadcast_failover_notification(self, from_broker: str, to_broker: str) -> None:
        """
        Broadcast failover notification to all connected users.

        Args:
            from_broker: Primary broker
            to_broker: Secondary broker
        """
        notification = {
            "type": "failover",
            "from": from_broker,
            "to": to_broker,
            "message": f"Switched to {to_broker} ({from_broker} recovering)"
        }

        for user in self._users.values():
            try:
                await user["websocket"].send_json(notification)
            except Exception as e:
                logger.error(f"Error sending failover notification: {e}")

    def get_subscribed_tokens(self, broker_type: str) -> Set[int]:
        """
        Get all tokens subscribed on a specific broker.

        Args:
            broker_type: Broker identifier

        Returns:
            Set of canonical tokens
        """
        tokens = set()
        for user in self._users.values():
            if user["broker_type"] == broker_type:
                tokens.update(user["subscribed_tokens"])
        return tokens

    # ========== Stats/Properties ==========

    @property
    def connected_users(self) -> int:
        """Number of connected users."""
        return len(self._users)

    @property
    def total_token_subscriptions(self) -> int:
        """Total unique token subscriptions across all users."""
        return len(self._token_subscriptions)
```

**Verification:**
```bash
# Check if file parses without errors
python -m py_compile backend/app/services/brokers/market_data/ticker/router.py
```

---

### Step 1.6: Create Package __init__.py (15 min)

**File:** `backend/app/services/brokers/market_data/ticker/__init__.py`

```python
"""
Multi-broker ticker system.

5-component architecture:
1. TickerAdapter - Per-broker WebSocket connection + tick normalization
2. TickerPool - Adapter lifecycle + credentials + ref-counted subscriptions
3. TickerRouter - User fan-out + cached tick delivery
4. HealthMonitor - Active health monitoring + failover triggers
5. FailoverController - Make-before-break failover execution

Usage:
    from app.services.brokers.market_data.ticker import (
        TickerPool,
        TickerRouter,
        NormalizedTick,
    )

    # In main.py lifespan:
    pool = TickerPool.get_instance()
    router = TickerRouter.get_instance()
    await pool.initialize(router)

    # In websocket.py:
    await router.register_user(user_id, websocket, broker_type="smartapi")
    await router.subscribe(user_id, tokens=[256265, 260105])
"""

from .models import NormalizedTick
from .adapter_base import TickerAdapter
from .pool import TickerPool
from .router import TickerRouter

__all__ = [
    "NormalizedTick",
    "TickerAdapter",
    "TickerPool",
    "TickerRouter",
]
```

---

### Step 1.7: Verification & Testing (30 min)

**Create test file:** `tests/backend/ticker/test_phase_t1.py`

```python
"""
Phase T1 verification tests.

Tests core infrastructure without broker-specific implementations.
"""

import pytest
from decimal import Decimal
from datetime import datetime
import pytz

from app.services.brokers.market_data.ticker.models import NormalizedTick
from app.services.brokers.market_data.ticker.pool import TickerPool
from app.services.brokers.market_data.ticker.router import TickerRouter


def test_normalized_tick_creation():
    """Test NormalizedTick dataclass creation and to_dict()."""
    tick = NormalizedTick(
        token=256265,
        ltp=Decimal("24500.50"),
        open=Decimal("24400.00"),
        high=Decimal("24550.25"),
        low=Decimal("24380.00"),
        close=Decimal("24450.75"),
        change=Decimal("49.75"),
        change_percent=Decimal("0.20"),
        volume=1234567,
        oi=5678900,
        timestamp=datetime.now(pytz.timezone('Asia/Kolkata')),
        broker_type="smartapi"
    )

    # Test to_dict conversion
    tick_dict = tick.to_dict()
    assert tick_dict["token"] == 256265
    assert tick_dict["ltp"] == 24500.50  # Decimal→float conversion
    assert tick_dict["broker_type"] == "smartapi"


def test_ticker_pool_singleton():
    """Test TickerPool singleton pattern."""
    pool1 = TickerPool.get_instance()
    pool2 = TickerPool.get_instance()
    assert pool1 is pool2  # Same instance


def test_ticker_router_singleton():
    """Test TickerRouter singleton pattern."""
    router1 = TickerRouter.get_instance()
    router2 = TickerRouter.get_instance()
    assert router1 is router2  # Same instance


@pytest.mark.asyncio
async def test_pool_router_wiring():
    """Test TickerPool and TickerRouter dependency injection."""
    pool = TickerPool.get_instance()
    router = TickerRouter.get_instance()

    # Wire dependencies
    router.set_pool(pool)
    await pool.initialize(router)

    # Verify wiring
    assert router._pool is pool
    assert pool._router is router


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Run tests:**
```bash
cd backend
pytest tests/backend/ticker/test_phase_t1.py -v
```

**Expected output:**
```
tests/backend/ticker/test_phase_t1.py::test_normalized_tick_creation PASSED
tests/backend/ticker/test_phase_t1.py::test_ticker_pool_singleton PASSED
tests/backend/ticker/test_phase_t1.py::test_ticker_router_singleton PASSED
tests/backend/ticker/test_phase_t1.py::test_pool_router_wiring PASSED

==================== 4 passed in 0.15s ====================
```

---

### Phase T1 Deliverables Checklist

- [x] Directory structure created (`ticker/`, `ticker/adapters/`)
- [x] `models.py` - NormalizedTick dataclass with Decimal prices
- [x] `adapter_base.py` - TickerAdapter abstract base class
- [x] `pool.py` - TickerPool singleton with credential management
- [x] `router.py` - TickerRouter singleton
- [x] `__init__.py` - Package exports
- [x] Unit tests pass
- [x] No syntax errors (all files compile)

**Git commit:**
```bash
git add backend/app/services/brokers/market_data/ticker/
git add tests/backend/ticker/
git commit -m "feat(ticker): Phase T1 - Core infrastructure (models, pool, router, adapter base)"
git tag post-phase-t1
```

---

## Phase T2: SmartAPI + Kite Adapters (8 hours)

### Goal
Implement SmartAPI and Kite ticker adapters by porting logic from legacy singletons, refactor websocket.py route to use new architecture.

### Prerequisites for Phase T2

✅ **Phase T1 complete** (all tests passing)
✅ **Legacy code references:**
- `backend/app/services/legacy/smartapi_ticker.py` (463 lines) - Current SmartAPI implementation
- `backend/app/services/legacy/kite_ticker.py` (390 lines) - Current Kite implementation
- `backend/app/api/routes/websocket.py` (494 lines) - Current route

✅ **External dependencies:**
- SmartAPI: `SmartApi` package (`SmartWebSocketV2`)
- Kite: `kiteconnect` package (`KiteTicker`)
- TokenManager: Already exists at `app/services/brokers/market_data/token_manager.py`

---

### Step 2.1: Implement SmartAPI Ticker Adapter (180 min)

**File:** `backend/app/services/brokers/market_data/ticker/adapters/smartapi.py`

**Critical Pattern to Preserve:**
SmartAPI's `SmartWebSocketV2` library uses **blocking threading**. Must preserve exact thread→asyncio bridge pattern from legacy `smartapi_ticker.py:117-124` and `208-211`.

```python
"""
SmartAPI (Angel One) Ticker Adapter

WebSocket V2 implementation using SmartWebSocketV2 library.

Key characteristics:
- Binary tick parsing (big-endian)
- Threading model (blocking WS library)
- Token format: String (e.g., "99926000" for NIFTY)
- Price normalization: Paise ÷ 100 → Rupees
- Exchange type codes required for subscriptions
"""

import asyncio
import logging
import threading
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
import pytz

from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from ..adapter_base import TickerAdapter
from ..models import NormalizedTick
from app.services.brokers.market_data.token_manager import token_manager


logger = logging.getLogger(__name__)


class SmartAPITickerAdapter(TickerAdapter):
    """
    SmartAPI WebSocket V2 ticker adapter.

    Threading pattern (CRITICAL - do not modify):
    - SmartWebSocketV2 runs on separate daemon thread
    - Callbacks execute on that thread
    - Use asyncio.run_coroutine_threadsafe to bridge to main event loop
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

    def __init__(self, broker_type: str = "smartapi"):
        super().__init__(broker_type)
        self.sws: Optional[SmartWebSocketV2] = None
        self.jwt_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.api_key: Optional[str] = None
        self.client_id: Optional[str] = None

        # Token grouping: exchange_type → set of broker tokens
        self._token_groups: Dict[int, set] = {}

    # ========== Abstract Method Implementations ==========

    async def _connect_ws(self, credentials: dict) -> None:
        """
        Connect to SmartAPI WebSocket V2.

        Args:
            credentials: {jwt_token, api_key, client_id, feed_token}
        """
        self.jwt_token = credentials["jwt_token"]
        self.api_key = credentials["api_key"]
        self.client_id = credentials["client_id"]
        self.feed_token = credentials["feed_token"]

        logger.info(f"[SmartAPI] Connecting to WebSocket for client: {self.client_id}")

        # Correlation ID for this connection
        correlation_id = "ticker_pool"

        # Create SmartWebSocketV2 instance
        self.sws = SmartWebSocketV2(
            auth_token=self.jwt_token,
            api_key=self.api_key,
            client_code=self.client_id,
            feed_token=self.feed_token
        )

        # Set callbacks
        self.sws.on_open = self._on_open
        self.sws.on_data = self._on_data
        self.sws.on_error = self._on_error
        self.sws.on_close = self._on_close

        # Connect in separate thread (CRITICAL PATTERN)
        ws_thread = threading.Thread(
            target=self.sws.connect,
            daemon=True,
            name="SmartAPI-WS-Thread"
        )
        ws_thread.start()

        logger.info("[SmartAPI] WebSocket thread started")

        # Wait for connection (with timeout)
        await asyncio.sleep(3)  # Give thread time to connect

        if not self._is_connected:
            raise ConnectionError("[SmartAPI] Failed to connect within timeout")

    async def _disconnect_ws(self) -> None:
        """Disconnect from SmartAPI WebSocket."""
        if self.sws:
            try:
                self.sws.close_connection()
                logger.info("[SmartAPI] WebSocket disconnected")
            except Exception as e:
                logger.error(f"[SmartAPI] Disconnect error: {e}")

        self.sws = None

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        """
        Subscribe to SmartAPI tokens.

        Args:
            broker_tokens: List of dicts with 'exchangeType' and 'tokens' keys
            mode: 'ltp', 'quote', 'snap', or 'depth'
        """
        if not self.sws:
            raise ConnectionError("[SmartAPI] WebSocket not connected")

        mode_value = self.MODES.get(mode, 2)  # Default to 'quote'

        # SmartAPI expects: [{"exchangeType": 2, "tokens": ["99926000", "99926009"]}]
        # broker_tokens is already in this format from _translate_to_broker_tokens

        correlation_id = "ticker_pool"

        logger.debug(f"[SmartAPI] Subscribing: {broker_tokens}, mode={mode_value}")

        # CRITICAL: Must run on the WS thread's context
        # SmartWebSocketV2.subscribe() is thread-safe
        self.sws.subscribe(correlation_id, mode_value, broker_tokens)

        logger.info(f"[SmartAPI] Subscribed to {len(broker_tokens)} token groups")

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        """
        Unsubscribe from SmartAPI tokens.

        Args:
            broker_tokens: List of dicts with 'exchangeType' and 'tokens' keys
        """
        if not self.sws:
            logger.warning("[SmartAPI] WebSocket not connected, skipping unsubscribe")
            return

        mode_value = self.MODES['quote']  # Mode doesn't matter for unsubscribe
        correlation_id = "ticker_pool"

        self.sws.unsubscribe(correlation_id, mode_value, broker_tokens)

        logger.info(f"[SmartAPI] Unsubscribed from {len(broker_tokens)} token groups")

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Translate canonical Kite tokens to SmartAPI format.

        Args:
            canonical_tokens: [256265, 260105, ...]

        Returns:
            [{"exchangeType": 2, "tokens": ["99926000", "99926009"]}, ...]

        Groups tokens by exchange type for efficient subscription.
        """
        # Group tokens by exchange type
        exchange_groups: Dict[int, List[str]] = {}

        for canonical_token in canonical_tokens:
            # Lookup SmartAPI token via TokenManager
            try:
                smartapi_token = token_manager.get_broker_token_sync(
                    canonical_token,
                    "smartapi"
                )

                # Determine exchange type (NFO for F&O, NSE for indices/cash)
                # For now, assume NFO for all (most common for options trading)
                # TODO: Improve exchange detection based on instrument type
                exchange_type = self.EXCHANGE_TYPES['NFO']

                if exchange_type not in exchange_groups:
                    exchange_groups[exchange_type] = []

                exchange_groups[exchange_type].append(str(smartapi_token))

            except Exception as e:
                logger.error(f"[SmartAPI] Token translation failed for {canonical_token}: {e}")

        # Convert to SmartAPI subscription format
        broker_tokens = [
            {"exchangeType": ex_type, "tokens": tokens}
            for ex_type, tokens in exchange_groups.items()
        ]

        return broker_tokens

    def _get_canonical_token(self, broker_token: str) -> int:
        """
        Extract canonical token from SmartAPI token.

        Args:
            broker_token: SmartAPI token string (e.g., "99926000")

        Returns:
            Canonical Kite instrument token (e.g., 256265)
        """
        try:
            canonical_token = token_manager.get_canonical_token_sync(
                broker_token,
                "smartapi"
            )
            return canonical_token
        except Exception as e:
            logger.error(f"[SmartAPI] Reverse token lookup failed for {broker_token}: {e}")
            return 0  # Invalid token

    def _parse_tick(self, raw_data: dict) -> List[NormalizedTick]:
        """
        Parse SmartAPI binary tick to NormalizedTick.

        Args:
            raw_data: Parsed tick dict from SmartWebSocketV2

        Returns:
            List containing single NormalizedTick
        """
        try:
            # Extract SmartAPI token
            broker_token = raw_data.get("token")
            if not broker_token:
                return []

            # Translate to canonical token
            canonical_token = self._get_canonical_token(str(broker_token))
            if canonical_token == 0:
                return []

            # Extract prices (in paise) and normalize to rupees
            ltp_paise = raw_data.get("last_traded_price", 0)
            open_paise = raw_data.get("open_price_of_the_day", 0)
            high_paise = raw_data.get("high_price_of_the_day", 0)
            low_paise = raw_data.get("low_price_of_the_day", 0)
            close_paise = raw_data.get("closed_price", 0)

            # Convert paise → rupees (÷ 100)
            ltp = Decimal(str(ltp_paise / 100))
            open_price = Decimal(str(open_paise / 100))
            high = Decimal(str(high_paise / 100))
            low = Decimal(str(low_paise / 100))
            close = Decimal(str(close_paise / 100))

            # Calculate change
            change = ltp - close
            change_percent = (change / close * 100) if close != 0 else Decimal("0")

            # Extract volume and OI
            volume = raw_data.get("volume_trade_for_the_day", 0)
            oi = raw_data.get("open_interest", 0)

            # Create NormalizedTick
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
                timestamp=datetime.now(pytz.timezone('Asia/Kolkata')),
                broker_type=self.broker_type
            )

            return [tick]

        except Exception as e:
            logger.error(f"[SmartAPI] Tick parsing error: {e}")
            return []

    # ========== SmartWebSocketV2 Callbacks (run on WS thread) ==========

    def _on_open(self, ws):
        """Callback when WebSocket connection opens."""
        logger.info("[SmartAPI] WebSocket connected")
        self._is_connected = True

    def _on_data(self, ws, message):
        """
        Callback when tick data arrives (runs on WS thread).

        CRITICAL: Must bridge to asyncio event loop using run_coroutine_threadsafe.
        """
        try:
            # Parse tick (SmartWebSocketV2 delivers pre-parsed dict)
            ticks = self._parse_tick(message)

            if ticks:
                # Bridge to asyncio event loop (CRITICAL PATTERN)
                self._dispatch_from_thread(ticks)

        except Exception as e:
            logger.error(f"[SmartAPI] On-data error: {e}")

    def _on_error(self, ws, error):
        """Callback when WebSocket error occurs."""
        logger.error(f"[SmartAPI] WebSocket error: {error}")
        self._is_connected = False

    def _on_close(self, ws, code, reason):
        """Callback when WebSocket closes."""
        logger.warning(f"[SmartAPI] WebSocket closed: {code} - {reason}")
        self._is_connected = False
```

**Testing SmartAPI Adapter:**
```python
# tests/backend/ticker/test_smartapi_adapter.py
import pytest
from decimal import Decimal
from datetime import datetime

from app.services.brokers.market_data.ticker.adapters.smartapi import SmartAPITickerAdapter
from app.services.brokers.market_data.ticker.models import NormalizedTick


def test_smartapi_adapter_creation():
    """Test SmartAPI adapter instantiation."""
    adapter = SmartAPITickerAdapter()
    assert adapter.broker_type == "smartapi"
    assert not adapter.is_connected


def test_smartapi_tick_parsing():
    """Test SmartAPI tick parsing."""
    adapter = SmartAPITickerAdapter()

    # Sample SmartAPI tick data (in paise)
    raw_tick = {
        "token": "99926000",  # SmartAPI token for NIFTY
        "last_traded_price": 2450050,  # 24500.50 rupees in paise
        "open_price_of_the_day": 2440000,
        "high_price_of_the_day": 2455025,
        "low_price_of_the_day": 2438000,
        "closed_price": 2445075,
        "volume_trade_for_the_day": 1234567,
        "open_interest": 5678900,
    }

    # Mock token manager lookup (would need actual mock in real test)
    # For now, just test parsing logic structure
    # ticks = adapter._parse_tick(raw_tick)
    # assert len(ticks) == 1
    # assert ticks[0].ltp == Decimal("24500.50")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Step 2.2: Implement Kite Ticker Adapter (120 min)

**File:** `backend/app/services/brokers/market_data/ticker/adapters/kite.py`

```python
"""
Kite (Zerodha) Ticker Adapter

WebSocket implementation using KiteTicker library.

Key characteristics:
- Binary tick parsing (big-endian, handled by KiteTicker library)
- Threading model (blocking WS library)
- Token format: Integer (same as canonical)
- Price normalization: WS ticks in paise ÷ 100 → Rupees
- No exchange type grouping needed
"""

import asyncio
import logging
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import pytz

from kiteconnect import KiteTicker

from ..adapter_base import TickerAdapter
from ..models import NormalizedTick


logger = logging.getLogger(__name__)


class KiteTickerAdapter(TickerAdapter):
    """
    Kite WebSocket ticker adapter.

    Threading pattern (CRITICAL - do not modify):
    - KiteTicker runs on separate thread (threaded=True)
    - Callbacks execute on that thread
    - Use asyncio.run_coroutine_threadsafe to bridge to main event loop
    """

    # Kite tick modes
    MODE_LTP = "ltp"
    MODE_QUOTE = "quote"
    MODE_FULL = "full"

    def __init__(self, broker_type: str = "kite"):
        super().__init__(broker_type)
        self.kite_ws: Optional[KiteTicker] = None
        self.api_key: Optional[str] = None
        self.access_token: Optional[str] = None

    # ========== Abstract Method Implementations ==========

    async def _connect_ws(self, credentials: dict) -> None:
        """
        Connect to Kite WebSocket.

        Args:
            credentials: {api_key, access_token}
        """
        self.api_key = credentials["api_key"]
        self.access_token = credentials["access_token"]

        logger.info("[Kite] Connecting to WebSocket...")

        # Create KiteTicker instance
        self.kite_ws = KiteTicker(
            api_key=self.api_key,
            access_token=self.access_token
        )

        # Set callbacks
        self.kite_ws.on_ticks = self._on_ticks
        self.kite_ws.on_connect = self._on_connect
        self.kite_ws.on_close = self._on_close
        self.kite_ws.on_error = self._on_error
        self.kite_ws.on_reconnect = self._on_reconnect

        # Connect in threaded mode (CRITICAL PATTERN)
        self.kite_ws.connect(threaded=True)

        logger.info("[Kite] WebSocket connection initiated (threaded)")

        # Wait for connection
        await asyncio.sleep(3)

        if not self._is_connected:
            raise ConnectionError("[Kite] Failed to connect within timeout")

    async def _disconnect_ws(self) -> None:
        """Disconnect from Kite WebSocket."""
        if self.kite_ws:
            try:
                self.kite_ws.close()
                logger.info("[Kite] WebSocket disconnected")
            except Exception as e:
                logger.error(f"[Kite] Disconnect error: {e}")

        self.kite_ws = None

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        """
        Subscribe to Kite tokens.

        Args:
            broker_tokens: List of instrument tokens (integers)
            mode: 'ltp', 'quote', or 'full'
        """
        if not self.kite_ws:
            raise ConnectionError("[Kite] WebSocket not connected")

        # Subscribe to tokens
        self.kite_ws.subscribe(broker_tokens)

        # Set mode
        if mode == "ltp":
            self.kite_ws.set_mode(self.kite_ws.MODE_LTP, broker_tokens)
        elif mode == "quote":
            self.kite_ws.set_mode(self.kite_ws.MODE_QUOTE, broker_tokens)
        elif mode == "full":
            self.kite_ws.set_mode(self.kite_ws.MODE_FULL, broker_tokens)

        logger.info(f"[Kite] Subscribed to {len(broker_tokens)} tokens (mode={mode})")

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        """
        Unsubscribe from Kite tokens.

        Args:
            broker_tokens: List of instrument tokens (integers)
        """
        if not self.kite_ws:
            logger.warning("[Kite] WebSocket not connected, skipping unsubscribe")
            return

        self.kite_ws.unsubscribe(broker_tokens)
        logger.info(f"[Kite] Unsubscribed from {len(broker_tokens)} tokens")

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        """
        Translate canonical tokens to Kite format.

        Kite format IS canonical format (identity mapping).

        Args:
            canonical_tokens: [256265, 260105, ...]

        Returns:
            Same list (Kite tokens are canonical)
        """
        return canonical_tokens  # Identity mapping

    def _get_canonical_token(self, broker_token: int) -> int:
        """
        Extract canonical token from Kite token.

        Kite token IS canonical token (identity mapping).

        Args:
            broker_token: Kite instrument token

        Returns:
            Same token (Kite tokens are canonical)
        """
        return broker_token  # Identity mapping

    def _parse_tick(self, raw_data: dict) -> List[NormalizedTick]:
        """
        Parse Kite tick to NormalizedTick.

        Args:
            raw_data: Tick dict from KiteTicker (pre-parsed by library)

        Returns:
            List containing single NormalizedTick
        """
        try:
            # Extract token (already canonical)
            canonical_token = raw_data.get("instrument_token")
            if not canonical_token:
                return []

            # Extract prices (in paise for WebSocket, rupees for some fields)
            # KiteTicker normalizes some fields, check library behavior
            ltp = Decimal(str(raw_data.get("last_price", 0)))
            open_price = Decimal(str(raw_data.get("ohlc", {}).get("open", 0)))
            high = Decimal(str(raw_data.get("ohlc", {}).get("high", 0)))
            low = Decimal(str(raw_data.get("ohlc", {}).get("low", 0)))
            close = Decimal(str(raw_data.get("ohlc", {}).get("close", 0)))

            # Calculate change
            change = ltp - close
            change_percent = (change / close * 100) if close != 0 else Decimal("0")

            # Extract volume and OI
            volume = raw_data.get("volume", 0)
            oi = raw_data.get("oi", 0)

            # Create NormalizedTick
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
                timestamp=datetime.now(pytz.timezone('Asia/Kolkata')),
                broker_type=self.broker_type
            )

            return [tick]

        except Exception as e:
            logger.error(f"[Kite] Tick parsing error: {e}")
            return []

    # ========== KiteTicker Callbacks (run on WS thread) ==========

    def _on_connect(self, ws, response):
        """Callback when WebSocket connection opens."""
        logger.info(f"[Kite] WebSocket connected: {response}")
        self._is_connected = True

    def _on_ticks(self, ws, ticks):
        """
        Callback when tick data arrives (runs on WS thread).

        CRITICAL: Must bridge to asyncio event loop.

        Args:
            ticks: List of tick dicts from KiteTicker
        """
        try:
            normalized_ticks = []
            for raw_tick in ticks:
                parsed = self._parse_tick(raw_tick)
                normalized_ticks.extend(parsed)

            if normalized_ticks:
                # Bridge to asyncio event loop (CRITICAL PATTERN)
                self._dispatch_from_thread(normalized_ticks)

        except Exception as e:
            logger.error(f"[Kite] On-ticks error: {e}")

    def _on_close(self, ws, code, reason):
        """Callback when WebSocket closes."""
        logger.warning(f"[Kite] WebSocket closed: {code} - {reason}")
        self._is_connected = False

    def _on_error(self, ws, error):
        """Callback when WebSocket error occurs."""
        logger.error(f"[Kite] WebSocket error: {error}")
        self._is_connected = False

    def _on_reconnect(self, ws, attempts_count):
        """Callback during reconnection attempts."""
        logger.info(f"[Kite] Reconnecting... (attempt {attempts_count})")
```

---

### Step 2.3: Register Adapters in TickerPool (15 min)

**File:** `backend/app/main.py` (add to lifespan startup)

```python
# In lifespan startup function
from app.services.brokers.market_data.ticker import TickerPool, TickerRouter
from app.services.brokers.market_data.ticker.adapters.smartapi import SmartAPITickerAdapter
from app.services.brokers.market_data.ticker.adapters.kite import KiteTickerAdapter

# ... existing startup code ...

# Initialize ticker system
pool = TickerPool.get_instance()
router = TickerRouter.get_instance()

# Register adapters
pool.register_adapter("smartapi", SmartAPITickerAdapter)
pool.register_adapter("kite", KiteTickerAdapter)

# Wire dependencies
router.set_pool(pool)
await pool.initialize(router)

logger.info("Ticker system initialized (SmartAPI, Kite adapters registered)")
```

---

### Step 2.4: Refactor websocket.py Route (120 min)

**File:** `backend/app/api/routes/websocket.py`

**Goal:** Reduce from 494 lines → ~90 lines by delegating to TickerRouter.

```python
"""
WebSocket route for live market data ticks.

Refactored to use new 5-component ticker architecture.

Before: 494 lines with broker-specific logic
After: ~90 lines (broker-agnostic)
"""

import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional

from app.utils.dependencies import get_current_user_ws
from app.services.brokers.market_data.ticker import TickerRouter
from app.models.user import User


logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/ticks")
async def websocket_ticks(
    websocket: WebSocket,
    token: str = Query(...),  # JWT token
):
    """
    WebSocket endpoint for live market data ticks.

    Query params:
        token: JWT token for authentication

    Client messages:
        {"action": "subscribe", "tokens": [256265, 260105], "mode": "quote"}
        {"action": "unsubscribe", "tokens": [256265]}

    Server messages:
        {"type": "tick", "data": {...}}  # NormalizedTick
        {"type": "subscribed", "tokens": [...], "broker": "smartapi"}
        {"type": "unsubscribed", "tokens": [...]}
        {"type": "error", "message": "..."}
        {"type": "failover", "from": "smartapi", "to": "kite"}
    """
    await websocket.accept()
    user: Optional[User] = None
    ticker_router = TickerRouter.get_instance()

    try:
        # Authenticate user via JWT token
        user = await get_current_user_ws(token)

        if not user:
            await websocket.send_json({
                "type": "error",
                "message": "Authentication failed"
            })
            await websocket.close()
            return

        # Get user's preferred market data broker
        broker_type = user.preferences.market_data_source if user.preferences else "smartapi"

        # Register user with ticker router
        await ticker_router.register_user(
            user_id=str(user.id),
            websocket=websocket,
            broker_type=broker_type
        )

        logger.info(f"User {user.id} connected to WebSocket (broker={broker_type})")

        # Send connection success message
        await websocket.send_json({
            "type": "connected",
            "user_id": user.id,
            "broker": broker_type
        })

        # Message loop
        while True:
            # Receive message from client
            message = await websocket.receive_json()

            action = message.get("action")

            if action == "subscribe":
                tokens = message.get("tokens", [])
                mode = message.get("mode", "quote")

                if not tokens:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No tokens provided"
                    })
                    continue

                # Subscribe via router
                await ticker_router.subscribe(
                    user_id=str(user.id),
                    tokens=tokens,
                    mode=mode
                )

                # Confirm subscription
                await websocket.send_json({
                    "type": "subscribed",
                    "tokens": tokens,
                    "mode": mode,
                    "broker": broker_type
                })

                logger.info(f"User {user.id} subscribed to {len(tokens)} tokens")

            elif action == "unsubscribe":
                tokens = message.get("tokens", [])

                if not tokens:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No tokens provided"
                    })
                    continue

                # Unsubscribe via router
                await ticker_router.unsubscribe(
                    user_id=str(user.id),
                    tokens=tokens
                )

                # Confirm unsubscription
                await websocket.send_json({
                    "type": "unsubscribed",
                    "tokens": tokens
                })

                logger.info(f"User {user.id} unsubscribed from {len(tokens)} tokens")

            elif action == "ping":
                # Heartbeat
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown action: {action}"
                })

    except WebSocketDisconnect:
        logger.info(f"User {user.id if user else 'unknown'} disconnected")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass

    finally:
        # Cleanup: Unregister user from ticker router
        if user:
            await ticker_router.unregister_user(str(user.id))
            logger.info(f"User {user.id} cleanup complete")
```

**Line count:** ~90 lines (82% reduction from 494 lines) ✅

---

### Step 2.5: Update Frontend WebSocket Client (30 min)

**File:** `frontend/src/stores/marketData.js` (or wherever WS client lives)

**Changes needed:**
1. Message format now uses `NormalizedTick` structure
2. Prices are already in RUPEES (no need for ÷100 conversion)
3. Handle new message types: `connected`, `failover`

```javascript
// Example changes in frontend WebSocket handler
function handleTickMessage(message) {
  if (message.type === 'tick') {
    const tick = message.data
    // tick.ltp is already in RUPEES (no paise conversion needed)
    // tick.token is canonical Kite format
    updateTickData(tick.token, {
      ltp: tick.ltp,
      change: tick.change,
      changePercent: tick.change_percent,
      volume: tick.volume,
      // ... other fields
    })
  } else if (message.type === 'failover') {
    console.warn(`[Ticker] Failover: ${message.from} → ${message.to}`)
    showNotification(`Market data switched to ${message.to}`, 'warning')
  } else if (message.type === 'connected') {
    console.log(`[Ticker] Connected using ${message.broker}`)
  }
}
```

---

### Step 2.6: Create System Broker Credentials Model (45 min)

**File:** `backend/app/models/system_broker_credentials.py`

```python
"""
System broker credentials for ticker adapters.

These are app-level credentials (not per-user) for market data streaming.
"""

from sqlalchemy import Column, BigInteger, String, Boolean, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base


class SystemBrokerCredential(Base):
    """
    System-level broker credentials for market data adapters.

    Stores encrypted credentials for each broker's market data access.
    """

    __tablename__ = "system_broker_credentials"

    id = Column(BigInteger, primary_key=True, index=True)
    broker = Column(String(20), unique=True, nullable=False, index=True)
    # Broker: 'smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm'

    # Encrypted credential storage (use app/utils/encryption.py)
    jwt_token = Column(Text, nullable=True)        # SmartAPI JWT
    access_token = Column(Text, nullable=True)     # Kite/Upstox/Fyers/Paytm
    refresh_token = Column(Text, nullable=True)    # SmartAPI/Upstox/Fyers refresh
    feed_token = Column(Text, nullable=True)       # SmartAPI feed token for WS
    api_key = Column(Text, nullable=True)          # Broker API key (encrypted)
    api_secret = Column(Text, nullable=True)       # Broker API secret (encrypted)

    # Session metadata
    client_id = Column(String(50), nullable=True)  # Broker client/user ID
    token_expiry = Column(TIMESTAMP(timezone=True), nullable=True)  # Token expiry time

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    last_auth_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
```

**Create migration:**
```bash
cd backend
alembic revision --autogenerate -m "Add system_broker_credentials table"
alembic upgrade head
```

**Populate initial data (SmartAPI):**
```sql
-- Insert SmartAPI system credentials (replace with actual encrypted values)
INSERT INTO system_broker_credentials (
    broker,
    api_key,
    api_secret,  -- Should store encrypted TOTP secret here
    client_id,
    is_active
) VALUES (
    'smartapi',
    'encrypted_api_key_here',
    'encrypted_totp_secret_here',
    'your_client_id',
    TRUE
);
```

---

### Step 2.7: Verification & Testing (60 min)

**Test Plan:**

1. **Unit tests for adapters:**
```bash
pytest tests/backend/ticker/test_smartapi_adapter.py -v
pytest tests/backend/ticker/test_kite_adapter.py -v
```

2. **Integration test for websocket.py:**
```bash
pytest tests/backend/api/test_websocket_refactored.py -v
```

3. **Manual WebSocket test:**
```bash
# Start backend
cd backend
python run.py

# In browser console (http://localhost:5173)
const ws = new WebSocket('ws://localhost:8001/ws/ticks?token=YOUR_JWT')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
ws.send(JSON.stringify({
  action: 'subscribe',
  tokens: [256265, 260105],  // NIFTY, BANKNIFTY
  mode: 'quote'
}))
```

**Expected output:**
```json
{"type": "connected", "user_id": 1, "broker": "smartapi"}
{"type": "subscribed", "tokens": [256265, 260105], "mode": "quote", "broker": "smartapi"}
{"type": "tick", "data": {"token": 256265, "ltp": 24500.50, "change": 49.75, ...}}
{"type": "tick", "data": {"token": 260105, "ltp": 48200.25, "change": -120.50, ...}}
```

---

### Phase T2 Deliverables Checklist

- [x] SmartAPI adapter implemented (`adapters/smartapi.py`)
- [x] Kite adapter implemented (`adapters/kite.py`)
- [x] Adapters registered in TickerPool
- [x] websocket.py refactored (494 → ~90 lines)
- [x] Frontend WebSocket client updated
- [x] SystemBrokerCredential model created
- [x] Migration run successfully
- [x] Manual WebSocket test successful
- [x] Unit tests pass

**Git commit:**
```bash
git add backend/app/services/brokers/market_data/ticker/adapters/
git add backend/app/api/routes/websocket.py
git add backend/app/models/system_broker_credentials.py
git add backend/alembic/versions/
git add frontend/src/stores/marketData.js
git commit -m "feat(ticker): Phase T2 - SmartAPI/Kite adapters + websocket refactor"
git tag post-phase-t2
```

---

## Phase T3: Health + Failover (6 hours)

### Goal
Implement HealthMonitor for active health tracking and FailoverController for automatic broker failover with make-before-break pattern.

### Step 3.1: Implement HealthMonitor (150 min)

**File:** `backend/app/services/brokers/market_data/ticker/health.py`

```python
"""
HealthMonitor: Active health monitoring for ticker adapters.

Runs a 5-second heartbeat loop to track:
- Tick latency
- Tick rate (ticks per minute)
- Error rate
- Connection staleness

Triggers failover when health degrades below threshold.
"""

import asyncio
import logging
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class AdapterHealth:
    """Health metrics for a single adapter."""
    broker_type: str
    is_connected: bool = False
    health_score: float = 100.0  # 0-100

    # Metrics
    tick_count_1min: int = 0
    error_count_5min: int = 0
    avg_latency_ms: float = 0.0
    last_tick_time: Optional[datetime] = None

    # Consecutive low scores (for failover trigger)
    consecutive_low_count: int = 0

    # Historical tracking
    tick_timestamps: list = field(default_factory=list)
    error_timestamps: list = field(default_factory=list)
    latency_samples: list = field(default_factory=list)


class HealthMonitor:
    """
    Active health monitoring for all ticker adapters.

    Runs a 5-second heartbeat loop to calculate health scores and
    trigger failover when degradation detected.
    """

    # Health thresholds
    FAILOVER_THRESHOLD = 30  # Trigger failover if health < 30
    FAILBACK_THRESHOLD = 70  # Trigger failback if primary > 70
    CONSECUTIVE_LOW_COUNT = 3  # Require 3 consecutive low scores (15s total)

    def __init__(self):
        self._adapter_health: Dict[str, AdapterHealth] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._on_health_change_callback: Optional[Callable] = None
        self._is_running = False

    # ========== Registration ==========

    def register_adapter(self, broker_type: str) -> None:
        """
        Register adapter for health monitoring.

        Args:
            broker_type: Broker identifier
        """
        if broker_type not in self._adapter_health:
            self._adapter_health[broker_type] = AdapterHealth(broker_type=broker_type)
            logger.info(f"[HealthMonitor] Registered adapter: {broker_type}")

    def unregister_adapter(self, broker_type: str) -> None:
        """
        Unregister adapter from health monitoring.

        Args:
            broker_type: Broker identifier
        """
        if broker_type in self._adapter_health:
            del self._adapter_health[broker_type]
            logger.info(f"[HealthMonitor] Unregistered adapter: {broker_type}")

    # ========== Recording (called by pool/adapters) ==========

    def record_ticks(self, broker_type: str, count: int) -> None:
        """
        Record tick arrival.

        Args:
            broker_type: Broker identifier
            count: Number of ticks received
        """
        if broker_type not in self._adapter_health:
            return

        health = self._adapter_health[broker_type]
        now = datetime.now()

        # Update last tick time
        health.last_tick_time = now

        # Record timestamp for each tick
        health.tick_timestamps.extend([now] * count)

        # Cleanup old timestamps (keep only last 1 minute)
        cutoff = now - timedelta(minutes=1)
        health.tick_timestamps = [
            ts for ts in health.tick_timestamps if ts > cutoff
        ]

        # Update tick count
        health.tick_count_1min = len(health.tick_timestamps)

    def record_error(self, broker_type: str, error: str) -> None:
        """
        Record error occurrence.

        Args:
            broker_type: Broker identifier
            error: Error message
        """
        if broker_type not in self._adapter_health:
            return

        health = self._adapter_health[broker_type]
        now = datetime.now()

        # Record error timestamp
        health.error_timestamps.append(now)

        # Cleanup old timestamps (keep only last 5 minutes)
        cutoff = now - timedelta(minutes=5)
        health.error_timestamps = [
            ts for ts in health.error_timestamps if ts > cutoff
        ]

        # Update error count
        health.error_count_5min = len(health.error_timestamps)

        logger.warning(f"[HealthMonitor] {broker_type} error: {error}")

    def record_disconnect(self, broker_type: str) -> None:
        """
        Record adapter disconnection.

        Args:
            broker_type: Broker identifier
        """
        if broker_type not in self._adapter_health:
            return

        health = self._adapter_health[broker_type]
        health.is_connected = False
        logger.warning(f"[HealthMonitor] {broker_type} disconnected")

    def record_connect(self, broker_type: str) -> None:
        """
        Record adapter connection.

        Args:
            broker_type: Broker identifier
        """
        if broker_type not in self._adapter_health:
            return

        health = self._adapter_health[broker_type]
        health.is_connected = True
        logger.info(f"[HealthMonitor] {broker_type} connected")

    def record_latency(self, broker_type: str, latency_ms: float) -> None:
        """
        Record tick latency sample.

        Args:
            broker_type: Broker identifier
            latency_ms: Latency in milliseconds
        """
        if broker_type not in self._adapter_health:
            return

        health = self._adapter_health[broker_type]
        health.latency_samples.append(latency_ms)

        # Keep only last 20 samples
        if len(health.latency_samples) > 20:
            health.latency_samples.pop(0)

        # Calculate moving average
        health.avg_latency_ms = sum(health.latency_samples) / len(health.latency_samples)

    # ========== Health Queries ==========

    def get_health(self, broker_type: str) -> Optional[AdapterHealth]:
        """
        Get health metrics for specific broker.

        Args:
            broker_type: Broker identifier

        Returns:
            AdapterHealth or None if not registered
        """
        return self._adapter_health.get(broker_type)

    def get_all_health(self) -> Dict[str, AdapterHealth]:
        """
        Get health metrics for all brokers.

        Returns:
            Dict mapping broker_type → AdapterHealth
        """
        return self._adapter_health.copy()

    # ========== Lifecycle ==========

    async def start(self) -> None:
        """Start health monitoring heartbeat loop."""
        if self._is_running:
            logger.warning("[HealthMonitor] Already running")
            return

        self._is_running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("[HealthMonitor] Started (5s heartbeat)")

    async def stop(self) -> None:
        """Stop health monitoring."""
        self._is_running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        logger.info("[HealthMonitor] Stopped")

    # ========== Callback ==========

    def set_on_health_change(self, callback: Callable) -> None:
        """
        Set callback for health change events.

        Callback signature: async def callback(broker_type: str, health_score: float)

        Args:
            callback: Async function to call when health changes significantly
        """
        self._on_health_change_callback = callback
        logger.debug("[HealthMonitor] Health change callback set")

    # ========== Private: Heartbeat Loop ==========

    async def _heartbeat_loop(self) -> None:
        """
        5-second heartbeat loop to calculate health scores.

        Triggers failover callback when health degrades.
        """
        while self._is_running:
            try:
                await asyncio.sleep(5)

                # Calculate health scores for all adapters
                for broker_type, health in self._adapter_health.items():
                    old_score = health.health_score
                    new_score = self._calculate_health_score(health)
                    health.health_score = new_score

                    # Check for significant change
                    if abs(new_score - old_score) > 10:
                        logger.info(
                            f"[HealthMonitor] {broker_type} health: "
                            f"{old_score:.1f} → {new_score:.1f}"
                        )

                    # Check for failover trigger
                    if new_score < self.FAILOVER_THRESHOLD:
                        health.consecutive_low_count += 1

                        if health.consecutive_low_count >= self.CONSECUTIVE_LOW_COUNT:
                            logger.warning(
                                f"[HealthMonitor] {broker_type} health degraded: {new_score:.1f} "
                                f"({health.consecutive_low_count} consecutive low)"
                            )

                            # Trigger failover callback
                            if self._on_health_change_callback:
                                await self._on_health_change_callback(broker_type, new_score)

                    else:
                        # Reset consecutive low count
                        health.consecutive_low_count = 0

            except asyncio.CancelledError:
                logger.info("[HealthMonitor] Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"[HealthMonitor] Heartbeat loop error: {e}")

    def _calculate_health_score(self, health: AdapterHealth) -> float:
        """
        Calculate health score (0-100) for adapter.

        Formula (from TICKER-DESIGN-SPEC):
        health_score = (
            latency_score      * 0.30 +    # 30%: Average tick latency
            tick_rate_score    * 0.30 +    # 30%: Ticks per minute
            error_score        * 0.20 +    # 20%: Error rate in last 5 min
            staleness_score    * 0.20      # 20%: Time since last tick
        )

        Args:
            health: AdapterHealth instance

        Returns:
            Health score (0-100)
        """
        # Component 1: Latency score (30%)
        latency_score = self._score_latency(health.avg_latency_ms)

        # Component 2: Tick rate score (30%)
        tick_rate_score = self._score_tick_rate(health.tick_count_1min)

        # Component 3: Error score (20%)
        error_score = self._score_errors(health.error_count_5min)

        # Component 4: Staleness score (20%)
        staleness_score = self._score_staleness(health.last_tick_time)

        # Weighted sum
        health_score = (
            latency_score * 0.30 +
            tick_rate_score * 0.30 +
            error_score * 0.20 +
            staleness_score * 0.20
        )

        return round(health_score, 1)

    def _score_latency(self, avg_latency_ms: float) -> float:
        """Score latency: 100 if <100ms, 50 if 100-500ms, 0 if >1000ms."""
        if avg_latency_ms < 100:
            return 100.0
        elif avg_latency_ms < 500:
            # Linear interpolation: 100 at 100ms, 50 at 500ms
            return 100 - ((avg_latency_ms - 100) / 400) * 50
        elif avg_latency_ms < 1000:
            # Linear interpolation: 50 at 500ms, 0 at 1000ms
            return 50 - ((avg_latency_ms - 500) / 500) * 50
        else:
            return 0.0

    def _score_tick_rate(self, tick_count_1min: int) -> float:
        """Score tick rate: min(100, tick_count * 2). Expected ~50 ticks/min."""
        return min(100.0, tick_count_1min * 2)

    def _score_errors(self, error_count_5min: int) -> float:
        """Score errors: max(0, 100 - error_count * 20)."""
        return max(0.0, 100 - error_count_5min * 20)

    def _score_staleness(self, last_tick_time: Optional[datetime]) -> float:
        """Score staleness: 100 if <10s, decay after."""
        if last_tick_time is None:
            return 0.0

        seconds_since_last_tick = (datetime.now() - last_tick_time).total_seconds()

        if seconds_since_last_tick < 10:
            return 100.0
        else:
            # Decay: 100 at 10s, 0 at 60s
            return max(0.0, 100 - (seconds_since_last_tick - 10) * 2)
```

---

### Step 3.2: Implement FailoverController (150 min)

**File:** `backend/app/services/brokers/market_data/ticker/failover.py`

```python
"""
FailoverController: Automatic broker failover with make-before-break pattern.

Responsibilities:
- Listen to HealthMonitor for degraded health
- Execute failover (primary → secondary) with make-before-break
- Execute failback (secondary → primary) when primary recovers
- Flap prevention (120s cooldown between events)
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class FailoverController:
    """
    Automatic broker failover controller.

    Pattern: Make-before-break
    1. Connect + subscribe on secondary
    2. Wait 2s overlap (both adapters active)
    3. Switch user routing
    4. Unsubscribe + cleanup primary
    """

    # Configuration
    FAILOVER_THRESHOLD = 30  # Trigger failover if health < 30
    FAILBACK_THRESHOLD = 70  # Trigger failback if primary > 70
    FAILBACK_SUSTAINED_SECONDS = 60  # Primary must be healthy for 60s before failback
    FLAP_PREVENTION_SECONDS = 120  # Min 120s between failover events

    def __init__(
        self,
        primary_broker: str = "smartapi",
        secondary_broker: str = "kite"
    ):
        self.primary_broker = primary_broker
        self.secondary_broker = secondary_broker
        self.active_broker = primary_broker
        self.is_failed_over = False

        # Dependencies (injected)
        self._pool: Optional["TickerPool"] = None  # type: ignore
        self._router: Optional["TickerRouter"] = None  # type: ignore
        self._health_monitor: Optional["HealthMonitor"] = None  # type: ignore

        # Failover tracking
        self._last_failover_time: Optional[datetime] = None
        self._primary_healthy_since: Optional[datetime] = None

    # ========== Dependency Injection ==========

    def set_dependencies(
        self,
        pool: "TickerPool",  # type: ignore
        router: "TickerRouter",  # type: ignore
        health_monitor: "HealthMonitor"  # type: ignore
    ) -> None:
        """
        Set dependencies.

        Args:
            pool: TickerPool instance
            router: TickerRouter instance
            health_monitor: HealthMonitor instance
        """
        self._pool = pool
        self._router = router
        self._health_monitor = health_monitor

        # Register health change callback
        health_monitor.set_on_health_change(self._on_health_degraded)

        logger.info(
            f"[FailoverController] Initialized: primary={self.primary_broker}, "
            f"secondary={self.secondary_broker}"
        )

    # ========== Health Callback ==========

    async def _on_health_degraded(self, broker_type: str, health_score: float) -> None:
        """
        Callback when adapter health degrades.

        Args:
            broker_type: Broker with degraded health
            health_score: Current health score
        """
        # Check if this is the active broker
        if broker_type != self.active_broker:
            logger.debug(
                f"[FailoverController] Health degraded for {broker_type}, "
                f"but not active broker (active={self.active_broker})"
            )
            return

        # Check flap prevention
        if self._last_failover_time:
            seconds_since_last = (datetime.now() - self._last_failover_time).total_seconds()
            if seconds_since_last < self.FLAP_PREVENTION_SECONDS:
                logger.warning(
                    f"[FailoverController] Flap prevention: Only {seconds_since_last:.0f}s "
                    f"since last failover (need {self.FLAP_PREVENTION_SECONDS}s)"
                )
                return

        # Execute failover
        if broker_type == self.primary_broker:
            await self._execute_failover(self.primary_broker, self.secondary_broker)
        elif broker_type == self.secondary_broker and self.is_failed_over:
            logger.error(
                f"[FailoverController] Secondary {self.secondary_broker} also degraded! "
                f"No more failover options."
            )

    # ========== Failover Execution ==========

    async def _execute_failover(self, from_broker: str, to_broker: str) -> None:
        """
        Execute failover with make-before-break pattern.

        Args:
            from_broker: Primary broker (failing)
            to_broker: Secondary broker (taking over)
        """
        logger.warning(
            f"[FailoverController] Executing failover: {from_broker} → {to_broker}"
        )

        try:
            # Step 1: Migrate subscriptions (make-before-break)
            await self._pool.migrate_subscriptions(from_broker, to_broker)

            # Step 2: Switch user routing
            await self._router.switch_users_broker(from_broker, to_broker)

            # Step 3: Update state
            self.active_broker = to_broker
            self.is_failed_over = True
            self._last_failover_time = datetime.now()

            logger.warning(
                f"[FailoverController] Failover complete: {from_broker} → {to_broker}"
            )

            # Start monitoring for failback
            if from_broker == self.primary_broker:
                asyncio.create_task(self._monitor_failback())

        except Exception as e:
            logger.error(f"[FailoverController] Failover failed: {e}")

    async def _monitor_failback(self) -> None:
        """
        Monitor primary broker health for failback opportunity.

        Failback when:
        - Primary health > 70 sustained for 60s
        - Currently failed over to secondary
        """
        logger.info("[FailoverController] Monitoring for failback opportunity...")

        while self.is_failed_over:
            await asyncio.sleep(10)  # Check every 10s

            # Get primary health
            primary_health = self._health_monitor.get_health(self.primary_broker)
            if not primary_health:
                continue

            # Check if healthy
            if primary_health.health_score >= self.FAILBACK_THRESHOLD:
                # Track sustained healthy period
                if self._primary_healthy_since is None:
                    self._primary_healthy_since = datetime.now()
                    logger.info(
                        f"[FailoverController] Primary {self.primary_broker} recovering "
                        f"(health={primary_health.health_score:.1f})"
                    )

                # Check if sustained for required duration
                healthy_duration = (datetime.now() - self._primary_healthy_since).total_seconds()
                if healthy_duration >= self.FAILBACK_SUSTAINED_SECONDS:
                    logger.info(
                        f"[FailoverController] Primary healthy for {healthy_duration:.0f}s, "
                        "executing failback"
                    )
                    await self._execute_failback()
                    break

            else:
                # Reset sustained healthy tracking
                self._primary_healthy_since = None

    async def _execute_failback(self) -> None:
        """Execute failback (secondary → primary)."""
        logger.warning(
            f"[FailoverController] Executing failback: {self.secondary_broker} → {self.primary_broker}"
        )

        try:
            # Same make-before-break pattern
            await self._pool.migrate_subscriptions(self.secondary_broker, self.primary_broker)
            await self._router.switch_users_broker(self.secondary_broker, self.primary_broker)

            # Update state
            self.active_broker = self.primary_broker
            self.is_failed_over = False
            self._last_failover_time = datetime.now()
            self._primary_healthy_since = None

            logger.warning(
                f"[FailoverController] Failback complete: {self.secondary_broker} → {self.primary_broker}"
            )

        except Exception as e:
            logger.error(f"[FailoverController] Failback failed: {e}")
```

---

### Step 3.3: Wire Health + Failover into main.py (30 min)

**File:** `backend/app/main.py` (update lifespan startup)

```python
# Add to imports
from app.services.brokers.market_data.ticker.health import HealthMonitor
from app.services.brokers.market_data.ticker.failover import FailoverController

# In lifespan startup (after pool/router initialization)
# Create health monitor
health_monitor = HealthMonitor()

# Create failover controller
failover_controller = FailoverController(
    primary_broker="smartapi",
    secondary_broker="kite"
)

# Wire dependencies
failover_controller.set_dependencies(pool, router, health_monitor)

# Update pool initialization to include health monitor
await pool.initialize(router, health_monitor)

# Start health monitoring
await health_monitor.start()

logger.info("Ticker system initialized with health monitoring + failover")
```

---

### Step 3.4: Add Health API Endpoint (30 min)

**File:** `backend/app/api/routes/ticker.py` (new file)

```python
"""
Ticker system API endpoints.

Provides health status, failover control, and diagnostics.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.utils.dependencies import get_current_user
from app.services.brokers.market_data.ticker.health import HealthMonitor
from app.services.brokers.market_data.ticker.failover import FailoverController


router = APIRouter(prefix="/ticker", tags=["Ticker"])


@router.get("/health")
async def get_ticker_health(current_user = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get health status of all ticker adapters.

    Returns:
        {
            "smartapi": {"broker_type": "smartapi", "health_score": 95.0, ...},
            "kite": {"broker_type": "kite", "health_score": 82.0, ...}
        }
    """
    health_monitor = HealthMonitor()  # Get singleton
    all_health = health_monitor.get_all_health()

    return {
        broker: {
            "broker_type": health.broker_type,
            "health_score": health.health_score,
            "is_connected": health.is_connected,
            "tick_count_1min": health.tick_count_1min,
            "error_count_5min": health.error_count_5min,
            "avg_latency_ms": health.avg_latency_ms,
            "last_tick_time": health.last_tick_time.isoformat() if health.last_tick_time else None,
        }
        for broker, health in all_health.items()
    }


@router.get("/failover/status")
async def get_failover_status(current_user = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get failover controller status.

    Returns:
        {
            "active_broker": "smartapi",
            "is_failed_over": False,
            "primary_broker": "smartapi",
            "secondary_broker": "kite"
        }
    """
    # Access failover controller singleton (TODO: proper singleton access)
    return {
        "active_broker": "smartapi",  # Placeholder
        "is_failed_over": False,
        "primary_broker": "smartapi",
        "secondary_broker": "kite",
    }
```

**Register in main.py:**
```python
from app.api.routes import ticker

app.include_router(ticker.router, prefix="/api")
```

---

### Phase T3 Deliverables Checklist

- [x] HealthMonitor implemented (`health.py`)
- [x] FailoverController implemented (`failover.py`)
- [x] Health + Failover wired in main.py
- [x] Health API endpoint (`/api/ticker/health`)
- [x] Failover status endpoint
- [x] Health monitoring started on app startup

**Git commit:**
```bash
git add backend/app/services/brokers/market_data/ticker/health.py
git add backend/app/services/brokers/market_data/ticker/failover.py
git add backend/app/api/routes/ticker.py
git add backend/app/main.py
git commit -m "feat(ticker): Phase T3 - Health monitoring + failover controller"
git tag post-phase-t3
```

### Token Policy Integration

When implementing or modifying a ticker adapter, integrate with `token_policy.py`:

1. **Classify error codes**: Add broker-specific error codes to `_BROKER_ERRORS` in `token_policy.py`
2. **Report auth errors**: Call `self._report_auth_error(error_code, error_msg)` in adapter error handlers
3. **Report general errors**: Call `self._report_error(error_type, error_msg)` for non-auth failures
4. **Health pipeline flow**:
   ```
   Adapter._report_auth_error() → Pool._on_adapter_error() → HealthMonitor.record_auth_failure()
   → classify_auth_error() → instant failover (NOT_RETRYABLE) or gradual decay (RETRYABLE)
   ```
5. **Auto-refresh**: If broker supports credential refresh, add to `_AUTO_REFRESHABLE_BROKERS` and implement refresh in `platform_token_refresh.py`

---

## Phase T4: System Credentials + Remaining Adapters (6 hours)

### Goal
Complete system credentials integration, create stub adapters for Upstox/Dhan/Fyers/Paytm.

### Step 4.1: System Credentials Integration (Already done in Phase T1/T2)

✅ **Completed:**
- SystemBrokerCredential model created (Phase T2)
- TickerPool.load_system_credentials() implemented (Phase T1)
- SmartAPI auto-TOTP authentication working (Phase T2)

**Verify:**
```bash
# Check system credentials table exists
psql -d algochanakya -c "\d system_broker_credentials"

# Check SmartAPI credentials loaded
# (Check backend logs on startup for "[smartapi] Authenticated successfully")
```

---

### Step 4.2: Create Adapter Stubs (120 min)

Create stub adapters for remaining brokers (Upstox, Dhan, Fyers, Paytm) to enable future development.

**File:** `backend/app/services/brokers/market_data/ticker/adapters/upstox.py`

```python
"""
Upstox Ticker Adapter (STUB)

TODO: Implement full Upstox WebSocket V2 protocol.
- Protobuf deserialization
- Async-native WebSocket (no threading)
- Instrument master CSV lookup
"""

from ..adapter_base import TickerAdapter


class UpstoxTickerAdapter(TickerAdapter):
    """Upstox adapter stub."""

    def __init__(self, broker_type: str = "upstox"):
        super().__init__(broker_type)
        raise NotImplementedError("Upstox adapter not yet implemented (Phase 5)")
```

**Repeat for:** `dhan.py`, `fyers.py`, `paytm.py` with similar stub structure.

**Register stubs in main.py:**
```python
from app.services.brokers.market_data.ticker.adapters.upstox import UpstoxTickerAdapter
from app.services.brokers.market_data.ticker.adapters.dhan import DhanTickerAdapter
from app.services.brokers.market_data.ticker.adapters.fyers import FyersTickerAdapter
from app.services.brokers.market_data.ticker.adapters.paytm import PaytmTickerAdapter

# Register stubs (will raise NotImplementedError if used)
pool.register_adapter("upstox", UpstoxTickerAdapter)
pool.register_adapter("dhan", DhanTickerAdapter)
pool.register_adapter("fyers", FyersTickerAdapter)
pool.register_adapter("paytm", PaytmTickerAdapter)
```

---

### Phase T4 Deliverables Checklist

- [x] System credentials fully integrated
- [x] Adapter stubs created (Upstox, Dhan, Fyers, Paytm)
- [x] Stubs registered in TickerPool
- [x] Documentation updated for stub status

**Git commit:**
```bash
git add backend/app/services/brokers/market_data/ticker/adapters/{upstox,dhan,fyers,paytm}.py
git commit -m "feat(ticker): Phase T4 - Adapter stubs for future brokers"
git tag post-phase-t4
```

---

## Phase T5: Frontend + Cleanup (2 hours)

### Goal
Finalize frontend integration, remove legacy services, update documentation.

### Step 5.1: Frontend WebSocket Updates (Already done in Phase T2)

✅ **Completed:**
- WebSocket message format updated to use NormalizedTick
- Failover notifications handled
- Connection status messages handled

---

### Step 5.2: Remove Legacy Services (45 min)

**Deprecate (but keep for reference):**
```bash
# Move legacy services to deprecated folder
mkdir -p backend/app/services/deprecated
git mv backend/app/services/legacy/smartapi_ticker.py backend/app/services/deprecated/
git mv backend/app/services/legacy/kite_ticker.py backend/app/services/deprecated/

# Update imports (if any remain)
# Find and replace: from app.services.legacy.smartapi_ticker → (removed)
```

---

### Step 5.3: Update Documentation (45 min)

**Create migration guide:** `docs/guides/TICKER-MIGRATION.md`

```markdown
# Migrating from Legacy Tickers to New Architecture

## What Changed

**Before (Legacy):**
- 2 hardcoded singletons (smartapi_ticker_service, kite_ticker_service)
- 494-line websocket.py with broker-specific logic
- No failover, no health monitoring

**After (New):**
- 5-component architecture (TickerAdapter, Pool, Router, Health, Failover)
- 90-line websocket.py (broker-agnostic)
- Automatic failover with make-before-break
- Active health monitoring

## Migration Checklist

1. ✅ Database: Add system_broker_credentials table
2. ✅ Backend: New ticker system in main.py startup
3. ✅ Frontend: Update WebSocket message handlers
4. ✅ Remove: Legacy service imports

## Testing

- Manual WebSocket test: `ws://localhost:8001/ws/ticks?token=JWT`
- Health endpoint: `GET /api/ticker/health`
- Failover status: `GET /api/ticker/failover/status`
```

---

### Phase T5 Deliverables Checklist

- [x] Legacy services moved to deprecated/
- [x] All imports updated
- [x] Migration guide created
- [x] Documentation index updated
- [x] TICKER-IMPLEMENTATION-GUIDE.md complete

**Final Git commit:**
```bash
git add backend/app/services/deprecated/
git add docs/guides/TICKER-MIGRATION.md
git commit -m "feat(ticker): Phase T5 - Cleanup legacy services + documentation"
git tag phase-t5-complete
```

---

## Testing Strategy

### Unit Tests

**Core components:**
```bash
pytest tests/backend/ticker/test_models.py -v
pytest tests/backend/ticker/test_pool.py -v
pytest tests/backend/ticker/test_router.py -v
pytest tests/backend/ticker/test_health.py -v
pytest tests/backend/ticker/test_failover.py -v
```

**Adapters:**
```bash
pytest tests/backend/ticker/test_smartapi_adapter.py -v
pytest tests/backend/ticker/test_kite_adapter.py -v
```

### Integration Tests

**WebSocket flow:**
```bash
pytest tests/backend/api/test_websocket_e2e.py -v
```

### Manual Testing

**1. Basic tick streaming:**
```javascript
// Browser console
const ws = new WebSocket('ws://localhost:8001/ws/ticks?token=YOUR_JWT')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
ws.send(JSON.stringify({action: 'subscribe', tokens: [256265], mode: 'quote'}))
// Expect: {"type": "tick", "data": {...}} messages
```

**2. Failover simulation:**
```bash
# Kill SmartAPI connection (simulate failure)
# Watch logs for automatic failover to Kite
# Check /api/ticker/health endpoint
```

**3. Health monitoring:**
```bash
curl http://localhost:8001/api/ticker/health
# Expect: JSON with health scores for all adapters
```

---

## Migration from Legacy

### Rollback Plan

If issues arise, rollback to legacy system:

```bash
# Revert to pre-ticker-refactor tag
git checkout pre-ticker-refactor

# Or revert specific phases
git checkout post-phase-t2  # Keep Phase T1-T2, revert T3-T5
```

### Gradual Migration

**Option: Run both systems in parallel (NOT recommended for production):**

1. Keep legacy services active
2. Add new ticker system alongside
3. Use feature flag to route users to new/old system
4. Monitor for 1 week
5. Fully cut over to new system

---

## Troubleshooting

### Issue: SmartAPI WebSocket won't connect

**Symptoms:** `[SmartAPI] Failed to connect within timeout`

**Solutions:**
1. Check system_broker_credentials table has valid encrypted credentials
2. Verify auto-TOTP authentication succeeds (check logs for "Authenticated successfully")
3. Check jwt_token and feed_token not expired
4. Verify SmartWebSocketV2 library installed

### Issue: Kite adapter fails with "Invalid access token"

**Symptoms:** `[Kite] API validation failed`

**Solutions:**
1. Kite requires user OAuth (no system credentials)
2. Ensure at least one user has connected with valid Kite access_token
3. Check access_token hasn't expired (24 hours)

### Issue: No ticks received

**Symptoms:** WebSocket connected but no tick messages

**Solutions:**
1. Check subscriptions: `await router.subscribe(user_id, tokens, mode)`
2. Verify tokens are valid canonical Kite instrument tokens
3. Check TickerPool ref-counting: `pool._subscriptions`
4. Check adapter is actually connected: `adapter.is_connected`
5. Look for errors in adapter callback logs

### Issue: Failover not triggering

**Symptoms:** SmartAPI health degraded but no automatic failover

**Solutions:**
1. Check health score: `GET /api/ticker/health`
2. Verify health < 30 for 3 consecutive checks (15s)
3. Check flap prevention (120s cooldown)
4. Verify FailoverController callback registered

---

## Performance Optimization

### Hot Path (Tick Dispatching)

**Critical:** The `TickerRouter.dispatch()` method is the hot path. Optimize:

1. ✅ No locks on dispatch (GIL makes dict reads thread-safe)
2. ✅ Pre-build tick dict for fast lookup
3. ✅ Concurrent dispatch with `asyncio.gather()`
4. ⚠️ Monitor: If >1000 concurrent users, consider batching

### Memory Management

**Cleanup strategies:**
1. ✅ Idle adapter cleanup (5 min threshold)
2. ✅ Cached tick limit (last tick only per token)
3. ✅ Health timestamp cleanup (1 min for ticks, 5 min for errors)
4. ✅ Latency samples limit (20 samples)

---

## Success Criteria

### Phase T1-T5 Complete When:

- [x] All 5 components implemented and tested
- [x] SmartAPI + Kite adapters working
- [x] websocket.py reduced to ~90 lines
- [x] Health monitoring active (5s heartbeat)
- [x] Automatic failover functional
- [x] Manual WebSocket test successful
- [x] Unit tests passing (>90% coverage)
- [x] Integration tests passing
- [x] Documentation complete
- [x] Legacy services deprecated

---

## Next Steps After Phase T5

### Phase 6: Implement Remaining Broker Adapters

**Priority order:**
1. **Upstox** - Protobuf, asyncio-native (Q2 2026)
2. **Fyers** - JSON, asyncio-native (Q2 2026)
3. **Dhan** - Little-endian binary, threading (Q3 2026)
4. **Paytm** - JSON, 3-token auth (Q3 2026)

**Per-broker checklist:**
- [ ] Implement TickerAdapter subclass
- [ ] Add system credentials to database
- [ ] Implement token translation logic
- [ ] Add unit tests
- [ ] Update documentation

---

## Conclusion

This implementation guide provides step-by-step instructions for implementing the 5-component multi-broker ticker architecture across 5 phases (T1-T5).

**Total estimated time:** ~28 hours

**Key design principles:**
- Broker abstraction via adapter pattern
- Ref-counted subscriptions for efficiency
- Make-before-break failover for reliability
- Active health monitoring for proactive failover
- Decimal prices for precision
- Canonical token format for consistency

**Result:** A production-ready, broker-agnostic ticker system that enables easy addition of new brokers without core code changes.

---

**Questions or Issues?**

Refer to:
- Design spec: [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md)
- Architecture: [ADR-003 v2](../decisions/003-multi-broker-ticker-architecture.md) (reference only)
- Migration guide: [TICKER-MIGRATION.md](TICKER-MIGRATION.md)
- API reference: [Multi-Broker Ticker API](../api/multi-broker-ticker-api.md)

**Ready to implement? Start with Phase T1!**
