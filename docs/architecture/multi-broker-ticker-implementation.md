# Multi-Broker Ticker Implementation Guide

**Status**: Ready for Implementation

**Related**: [ADR-003: Multi-Broker Ticker Architecture](../decisions/003-multi-broker-ticker-architecture.md)

**Goal**: Replace hardcoded ticker singletons with a broker-agnostic multiton manager pattern

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Core Infrastructure](#phase-1-core-infrastructure)
4. [Phase 2: Market Data Adapters](#phase-2-market-data-adapters)
5. [Phase 3: Order Execution](#phase-3-order-execution)
6. [Verification Steps](#verification-steps)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)

---

## Overview

### Current State

- **Files**: 2 singleton services (`smartapi_ticker.py`, `kite_ticker.py`)
- **Route**: 534-line `websocket.py` with hardcoded broker logic
- **Problem**: Can't add new brokers without route modifications

### Target State

- **Files**: 6 adapter wrappers + 1 manager + 1 interface
- **Route**: ~150-line `websocket.py` with zero broker-specific code
- **Result**: Add new broker = implement adapter + register in factory

### Architecture Change

```
BEFORE:
┌─────────────────────────────────────┐
│      websocket.py (534 lines)       │
│  ┌───────────┐    ┌──────────────┐ │
│  │ if/else   │ -> │ SmartAPI WS  │ │
│  │ if/else   │ -> │ Kite WS      │ │
│  │ Token Map │    │              │ │
│  └───────────┘    └──────────────┘ │
└─────────────────────────────────────┘

AFTER:
┌────────────────────────────────────────────────┐
│         websocket.py (~150 lines)              │
│              ┌──────────────┐                  │
│              │   Manager    │                  │
│              └──────┬───────┘                  │
│                     │                          │
│        ┌────────────┼────────────┐             │
│        │            │            │             │
│   ┌────▼─────┐ ┌───▼──────┐ ┌──▼────────┐    │
│   │SmartAPI  │ │  Kite    │ │  Upstox   │    │
│   │Adapter   │ │ Adapter  │ │  Adapter  │ ...│
│   └──────────┘ └──────────┘ └───────────┘    │
└────────────────────────────────────────────────┘
```

---

## Prerequisites

### Before Starting

1. **Backup Current State**:
   ```bash
   git stash push -m "WIP before multi-broker ticker refactor" \
     backend/app/api/routes/websocket.py \
     backend/app/services/legacy/smartapi_ticker.py
   git tag pre-ticker-refactor
   ```

2. **Verify Clean State**:
   ```bash
   git status  # Should be clean
   pytest tests/ -v  # All tests passing
   npm test  # All E2E tests passing
   ```

3. **Review Reference Files**:
   - `backend/app/services/legacy/smartapi_ticker.py` - Threading model
   - `backend/app/services/legacy/kite_ticker.py` - Connection patterns
   - `backend/app/api/routes/websocket.py` - Current route logic
   - `example_ticker_manager.py` - Reference multiton pattern

4. **Read Documentation**:
   - [ADR-003](../decisions/003-multi-broker-ticker-architecture.md)
   - [Broker Abstraction](./broker-abstraction.md)
   - [WebSocket Architecture](./websocket.md)

---

## Phase 1: Core Infrastructure

**Timeline**: 3-4 days

**Milestone**: App boots with new DB tables, interfaces defined, old tickers still work. Zero user-facing changes.

### Step 1.1: Add Missing BrokerType Enum Values

**File**: `backend/app/services/brokers/base.py`

**Current state** (lines 25-30):
```python
class BrokerType(str, Enum):
    """Supported broker types."""
    KITE = "kite"
    UPSTOX = "upstox"
    ANGEL = "angel"
    FYERS = "fyers"
```

**Add**:
```python
class BrokerType(str, Enum):
    """Supported broker types."""
    KITE = "kite"           # Zerodha Kite Connect
    ANGEL = "angel"         # Angel One SmartAPI
    UPSTOX = "upstox"       # Upstox
    DHAN = "dhan"           # Dhan
    FYERS = "fyers"         # Fyers
    PAYTM = "paytm"         # Paytm Money
```

**Verification**:
```bash
python -c "from app.services.brokers.base import BrokerType; print(BrokerType.DHAN.value)"
# Output: dhan
```

---

### Step 1.2: Add System Broker Credentials to Config

**File**: `backend/app/config.py`

**Add after existing broker configs**:
```python
class Settings(BaseSettings):
    # ... existing fields ...

    # System Broker Credentials (Tier 1 - Market Data)
    # AngelOne SmartAPI (default market data provider)
    ANGEL_SYSTEM_CLIENT_ID: str = ""
    ANGEL_SYSTEM_PIN: str = ""
    ANGEL_SYSTEM_TOTP_SECRET: str = ""

    # Zerodha Kite (optional market data)
    KITE_SYSTEM_ACCESS_TOKEN: str = ""

    # Upstox
    UPSTOX_API_KEY: str = ""
    UPSTOX_API_SECRET: str = ""
    UPSTOX_REDIRECT_URL: str = "http://localhost:8001/api/auth/upstox/callback"

    # Dhan
    DHAN_API_KEY: str = ""
    DHAN_CLIENT_ID: str = ""

    # Fyers
    FYERS_APP_ID: str = ""
    FYERS_SECRET_ID: str = ""
    FYERS_REDIRECT_URL: str = "http://localhost:8001/api/auth/fyers/callback"

    # Paytm Money
    PAYTM_API_KEY: str = ""
    PAYTM_API_SECRET: str = ""

    # App-level default broker for market data
    DEFAULT_MARKET_DATA_BROKER: str = "smartapi"

    class Config:
        env_file = ".env"
```

**Update `.env` file**:
```bash
# System Broker Credentials (shared across all users)
ANGEL_SYSTEM_CLIENT_ID=your_client_id
ANGEL_SYSTEM_PIN=your_pin
ANGEL_SYSTEM_TOTP_SECRET=your_totp_secret_base32

DEFAULT_MARKET_DATA_BROKER=smartapi
```

**Verification**:
```bash
python -c "from app.config import settings; print(settings.DEFAULT_MARKET_DATA_BROKER)"
# Output: smartapi
```

---

### Step 1.3: Create `system_broker_sessions` Table

**New file**: `backend/app/models/system_broker_sessions.py`

```python
"""
System Broker Sessions Model

Stores app-level broker credentials and session tokens for Tier 1 (market data).
Each row represents one broker's system-level session.
"""
from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class SystemBrokerSession(Base):
    """
    System broker session for app-level market data access.

    Unlike user broker connections (Tier 2), these are shared credentials
    used by the app owner to serve market data to all users.
    """
    __tablename__ = "system_broker_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    broker = Column(String(20), nullable=False, unique=True, index=True)
    # Values: 'smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm'

    # Dynamic tokens (refreshed periodically)
    jwt_token = Column(Text, nullable=True)          # AngelOne JWT
    access_token = Column(Text, nullable=True)       # Kite/Upstox access token
    refresh_token = Column(Text, nullable=True)      # AngelOne refresh token
    feed_token = Column(Text, nullable=True)         # AngelOne feed token

    # Session metadata
    client_id = Column(String(50), nullable=True)    # Broker client ID
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    last_auth_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)         # Last auth error

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    def __repr__(self):
        return f"<SystemBrokerSession(broker='{self.broker}', active={self.is_active})>"
```

**Update `backend/app/models/__init__.py`**:
```python
from app.models.system_broker_sessions import SystemBrokerSession

__all__ = [
    # ... existing models ...
    "SystemBrokerSession",
]
```

**Update `backend/alembic/env.py`** (CRITICAL - required for autogenerate):
```python
# Import all models here for Alembic autogenerate
from app.models.system_broker_sessions import SystemBrokerSession
```

**Create migration**:
```bash
cd backend
alembic revision --autogenerate -m "add system_broker_sessions table"
# Review the generated migration file
alembic upgrade head
```

**Verification**:
```bash
# Check table exists
python -c "
from app.database import SessionLocal
from app.models import SystemBrokerSession
db = SessionLocal()
count = db.query(SystemBrokerSession).count()
print(f'Table exists, rows: {count}')
"
```

---

### Step 1.4: Create `MultiTenantTickerService` ABC

**New file**: `backend/app/services/brokers/market_data/multi_tenant_ticker_base.py`

```python
"""
Multi-Tenant Ticker Service Base Interface

Replaces the dead TickerService interface (ticker_base.py) with a multi-tenant-aware
contract suitable for both Tier 1 (app-level shared) and Tier 2 (per-user) brokers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from fastapi import WebSocket


@dataclass
class NormalizedTick:
    """
    Broker-agnostic tick data structure.

    All tokens are in CANONICAL format (Kite format).
    All prices are in rupees (NOT paise).

    This is simpler than UnifiedQuote because it's optimized for
    high-frequency WebSocket broadcasting, not REST API responses.
    """
    token: int              # Canonical token (Kite format)
    ltp: float              # Last traded price (₹)
    change: float           # Absolute change from previous close (₹)
    change_percent: float   # Percentage change
    volume: int             # Total volume traded
    oi: int                 # Open interest
    open: float             # Day open price (₹)
    high: float             # Day high (₹)
    low: float              # Day low (₹)
    close: float            # Previous day close (₹)
    last_trade_time: Optional[int] = None       # Unix timestamp
    exchange_timestamp: Optional[int] = None    # Exchange timestamp


class MultiTenantTickerService(ABC):
    """
    Abstract base class for multi-tenant ticker services.

    Implementations:
    - SmartAPITickerAdapter (wraps SmartWebSocketV2)
    - KiteTickerAdapter (wraps KiteTicker)
    - UpstoxTickerAdapter, DhanTickerAdapter, etc. (future)

    Key Design Decisions:
    1. Multi-tenant: One WebSocket serves multiple users (Tier 1)
    2. User-aware: subscribe() takes user_id to filter broadcasts
    3. Exchange-aware: subscribe() takes exchange for broker-specific needs
    4. Self-contained: Token mapping happens inside adapter, not in route
    5. Direct broadcast: No callback pattern, uses registered WebSockets
    """

    @abstractmethod
    async def connect(self, **credentials) -> None:
        """
        Connect to broker WebSocket.

        Args:
            **credentials: Broker-specific credentials
                SmartAPI: jwt_token, api_key, client_id, feed_token
                Kite: access_token, api_key
                Upstox: access_token
                etc.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Gracefully disconnect from broker WebSocket.

        Should:
        - Unsubscribe all tokens
        - Close WebSocket connection
        - Clean up threads/tasks
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        tokens: List[int],
        user_id: str,
        exchange: str = "NFO",
        mode: str = "quote"
    ) -> None:
        """
        Subscribe to market data for given tokens.

        Args:
            tokens: List of CANONICAL tokens (Kite format)
            user_id: User ID for filtering broadcasts
            exchange: Exchange code (NSE, NFO, BSE, etc.)
            mode: Subscription mode (ltp, quote, full)

        Note:
            - Adapter handles token translation internally
            - User subscriptions tracked separately for filtering
        """
        pass

    @abstractmethod
    async def unsubscribe(
        self,
        tokens: List[int],
        user_id: str,
        exchange: str = "NFO"
    ) -> None:
        """
        Unsubscribe from market data for given tokens.

        Args:
            tokens: List of CANONICAL tokens
            user_id: User ID
            exchange: Exchange code
        """
        pass

    @abstractmethod
    async def register_client(self, user_id: str, websocket: WebSocket) -> None:
        """
        Register a WebSocket client for receiving ticks.

        Args:
            user_id: Unique user identifier
            websocket: FastAPI WebSocket connection

        Note:
            - Multiple users can share one broker WebSocket (Tier 1)
            - Each user gets filtered ticks based on their subscriptions
        """
        pass

    @abstractmethod
    async def unregister_client(self, user_id: str) -> None:
        """
        Unregister a WebSocket client.

        Args:
            user_id: User identifier

        Note:
            - Auto-unsubscribes all tokens for this user
            - If last client, may trigger graceful disconnect after timeout
        """
        pass

    @abstractmethod
    def get_latest_tick(self, token: int) -> Optional[NormalizedTick]:
        """
        Get latest cached tick for a token.

        Args:
            token: CANONICAL token (Kite format)

        Returns:
            Latest NormalizedTick or None if not available
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        pass

    @property
    @abstractmethod
    def client_count(self) -> int:
        """Get number of registered clients (users)."""
        pass

    @property
    @abstractmethod
    def broker_type(self) -> str:
        """Get broker type (smartapi, kite, upstox, etc.)."""
        pass
```

**Key Differences from Dead `TickerService`**:

| Old `TickerService` (dead) | New `MultiTenantTickerService` |
|---|---|
| `subscribe(tokens, mode)` | `subscribe(tokens, user_id, exchange, mode)` |
| `connect()` - no args | `connect(**credentials)` - broker-specific |
| `on_tick(callback)` - callback pattern | Direct broadcasting via `register_client()` |
| Returns `UnifiedQuote` | Returns `NormalizedTick` (simpler) |
| No client management | `register_client()`, `unregister_client()`, `client_count` |
| No user awareness | Per-user subscriptions + filtering |

**Verification**:
```bash
python -c "
from app.services.brokers.market_data.multi_tenant_ticker_base import MultiTenantTickerService, NormalizedTick
print('Interface defined successfully')
print(f'NormalizedTick fields: {NormalizedTick.__dataclass_fields__.keys()}')
"
```

---

### Step 1.5: Create `TickerServiceManager`

**New file**: `backend/app/services/brokers/market_data/ticker_manager.py`

```python
"""
Ticker Service Manager (Multiton Pattern)

Manages lifecycle of ticker services across multiple brokers.
One ticker instance per broker, shared across all users (Tier 1 model).
"""
import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from app.services.brokers.market_data.multi_tenant_ticker_base import MultiTenantTickerService
from app.services.brokers.base import BrokerType
from app.database import SessionLocal
from app.models import UserPreferences

logger = logging.getLogger(__name__)


class TickerServiceManager:
    """
    Centralized manager for multi-broker ticker services.

    Features:
    - Multiton pattern: One instance per broker
    - On-demand connection creation
    - Thread-safe operations
    - Graceful cleanup after 5-minute idle period
    - System credential management
    """

    # Class-level state (multiton)
    _instances: Dict[str, MultiTenantTickerService] = {}
    _locks: Dict[str, asyncio.Lock] = {}
    _last_activity: Dict[str, datetime] = {}

    # Adapter registry (broker_type -> class path)
    # Pattern: Lazy import to avoid circular dependencies
    _TICKER_ADAPTERS = {
        "smartapi": "app.services.brokers.market_data.tickers.smartapi_ticker_adapter.SmartAPITickerAdapter",
        "kite": "app.services.brokers.market_data.tickers.kite_ticker_adapter.KiteTickerAdapter",
        "upstox": "app.services.brokers.market_data.tickers.upstox_ticker_adapter.UpstoxTickerAdapter",
        "dhan": "app.services.brokers.market_data.tickers.dhan_ticker_adapter.DhanTickerAdapter",
        "fyers": "app.services.brokers.market_data.tickers.fyers_ticker_adapter.FyersTickerAdapter",
        "paytm": "app.services.brokers.market_data.tickers.paytm_ticker_adapter.PaytmTickerAdapter",
    }

    @classmethod
    def _get_lock(cls, broker_type: str) -> asyncio.Lock:
        """Get or create per-broker lock for thread-safe initialization."""
        if broker_type not in cls._locks:
            cls._locks[broker_type] = asyncio.Lock()
        return cls._locks[broker_type]

    @classmethod
    def _lazy_import_adapter(cls, broker_type: str) -> type:
        """
        Lazily import adapter class.

        Avoids circular imports and speeds up app startup.
        """
        if broker_type not in cls._TICKER_ADAPTERS:
            raise ValueError(f"Unsupported broker type: {broker_type}")

        module_path, class_name = cls._TICKER_ADAPTERS[broker_type].rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)

    @classmethod
    async def get_ticker(cls, broker_type: str) -> MultiTenantTickerService:
        """
        Get or create ticker instance for a broker.

        Thread-safe singleton per broker. Creates instance if not exists.

        Args:
            broker_type: Broker identifier (smartapi, kite, etc.)

        Returns:
            Ticker service instance

        Raises:
            ValueError: If broker type not supported
        """
        if broker_type not in cls._instances:
            lock = cls._get_lock(broker_type)
            async with lock:
                if broker_type not in cls._instances:
                    logger.info(f"[TickerManager] Creating new ticker for {broker_type}")
                    adapter_class = cls._lazy_import_adapter(broker_type)
                    cls._instances[broker_type] = adapter_class()

        cls._last_activity[broker_type] = datetime.utcnow()
        return cls._instances[broker_type]

    @classmethod
    async def get_primary_ticker(cls, user_id: int, db) -> MultiTenantTickerService:
        """
        Get ticker for user's preferred market data source.

        Reads from UserPreferences.market_data_source, falls back to app default.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Ticker service for user's broker preference
        """
        from app.config import settings

        # Get user preference
        prefs = db.query(UserPreferences).filter_by(user_id=user_id).first()
        broker_type = (
            prefs.market_data_source if prefs and prefs.market_data_source
            else settings.DEFAULT_MARKET_DATA_BROKER
        )

        logger.info(f"[TickerManager] User {user_id} using {broker_type} for market data")
        return await cls.get_ticker(broker_type)

    @classmethod
    async def connect_ticker(cls, broker_type: str, db) -> None:
        """
        Connect ticker service to broker WebSocket.

        Fetches system credentials from database, authenticates if needed.

        Args:
            broker_type: Broker identifier
            db: Database session
        """
        from app.services.brokers.market_data.system_auth_service import get_system_credentials

        ticker = await cls.get_ticker(broker_type)

        if ticker.is_connected:
            logger.info(f"[TickerManager] {broker_type} already connected")
            return

        # Get system credentials
        credentials = await get_system_credentials(broker_type, db)
        if not credentials:
            logger.error(f"[TickerManager] No system credentials for {broker_type}")
            raise ValueError(f"System credentials not configured for {broker_type}")

        # Connect
        await ticker.connect(**credentials)
        logger.info(f"[TickerManager] {broker_type} connected successfully")

    @classmethod
    async def disconnect_ticker(cls, broker_type: str) -> None:
        """
        Disconnect ticker service.

        Graceful disconnect with 5-minute grace period.
        If no clients reconnect within 5 minutes, connection is closed.

        Args:
            broker_type: Broker identifier
        """
        if broker_type not in cls._instances:
            return

        ticker = cls._instances[broker_type]

        # Check if there are still active clients
        if ticker.client_count > 0:
            logger.warning(
                f"[TickerManager] Cannot disconnect {broker_type}: "
                f"{ticker.client_count} active clients"
            )
            return

        # Grace period: Wait 5 minutes before disconnecting
        # (in case user refreshes page)
        await asyncio.sleep(300)

        # Check again after grace period
        if ticker.client_count > 0:
            logger.info(
                f"[TickerManager] {broker_type} not disconnected: "
                f"clients reconnected during grace period"
            )
            return

        # Disconnect
        await ticker.disconnect()
        del cls._instances[broker_type]
        logger.info(f"[TickerManager] {broker_type} disconnected and removed")

    @classmethod
    async def shutdown_all(cls) -> None:
        """
        Shutdown all active ticker services.

        Called from main.py lifespan shutdown.
        """
        logger.info(f"[TickerManager] Shutting down {len(cls._instances)} tickers")

        for broker_type, ticker in list(cls._instances.items()):
            try:
                await ticker.disconnect()
                logger.info(f"[TickerManager] {broker_type} disconnected")
            except Exception as e:
                logger.error(f"[TickerManager] Error disconnecting {broker_type}: {e}")

        cls._instances.clear()
        logger.info("[TickerManager] All tickers shutdown complete")

    @classmethod
    def get_health(cls, broker_type: str) -> Optional[Dict[str, Any]]:
        """
        Get health metrics for a broker's ticker.

        Args:
            broker_type: Broker identifier

        Returns:
            Health metrics dict or None if not active
        """
        if broker_type not in cls._instances:
            return None

        ticker = cls._instances[broker_type]
        return {
            "broker": broker_type,
            "connected": ticker.is_connected,
            "client_count": ticker.client_count,
            "last_activity": cls._last_activity.get(broker_type),
        }

    @classmethod
    def get_all_health(cls) -> Dict[str, Any]:
        """
        Get health metrics for all active tickers.

        Returns:
            Dict with broker_type -> health metrics
        """
        return {
            broker_type: cls.get_health(broker_type)
            for broker_type in cls._instances.keys()
        }
```

**Design Decisions**:
- **Multiton, not Factory**: One instance per broker, reused across users
- **Lazy import**: Avoid circular dependencies, faster startup
- **Per-broker locks**: Thread-safe initialization
- **Grace period**: 5-minute delay before disconnect (user might refresh)
- **System credentials**: Fetched from `system_broker_sessions` table

**Verification**:
```bash
python -c "
from app.services.brokers.market_data.ticker_manager import TickerServiceManager
print('Manager defined successfully')
print(f'Supported brokers: {list(TickerServiceManager._TICKER_ADAPTERS.keys())}')
"
```

---

### Step 1.6: Create System Auth Service

**New file**: `backend/app/services/brokers/market_data/system_auth_service.py`

```python
"""
System Broker Authentication Service

Handles authentication and token refresh for app-level broker credentials (Tier 1).
Stores tokens in system_broker_sessions table.

Unlike user authentication (Tier 2), these are app owner's credentials
used to serve market data to all users via shared WebSocket connections.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.system_broker_sessions import SystemBrokerSession

logger = logging.getLogger(__name__)


async def initialize_system_sessions() -> None:
    """
    Initialize system broker sessions at app startup.

    Called from main.py lifespan function.
    Authenticates configured brokers and stores tokens in DB.
    """
    from app.database import SessionLocal

    async for db in SessionLocal():
        try:
            logger.info("[SystemAuth] Initializing system broker sessions...")

            # SmartAPI (default market data)
            if settings.ANGEL_SYSTEM_CLIENT_ID and settings.ANGEL_SYSTEM_PIN:
                await _init_smartapi_session(db)
            else:
                logger.warning("[SystemAuth] SmartAPI system credentials not configured")

            # Kite (optional)
            if settings.KITE_SYSTEM_ACCESS_TOKEN:
                await _init_kite_session(db)
            else:
                logger.info("[SystemAuth] Kite system credentials not configured")

            # Other brokers (stubs for now)
            logger.info("[SystemAuth] Upstox/Dhan/Fyers/Paytm not configured (future)")

            await db.commit()
            logger.info("[SystemAuth] System broker sessions initialized successfully")

        except Exception as e:
            logger.error(f"[SystemAuth] Failed to initialize sessions: {e}")
            await db.rollback()
            raise
        finally:
            break


async def _init_smartapi_session(db: AsyncSession) -> None:
    """
    Initialize SmartAPI system session.

    Reuses auto-TOTP authentication from smartapi_auth.py.
    """
    from app.services.legacy.smartapi_auth import SmartAPIAuth

    try:
        logger.info("[SystemAuth] Authenticating SmartAPI...")

        # Authenticate using auto-TOTP
        auth_result = await SmartAPIAuth.authenticate(
            client_id=settings.ANGEL_SYSTEM_CLIENT_ID,
            pin=settings.ANGEL_SYSTEM_PIN,
            totp_secret=settings.ANGEL_SYSTEM_TOTP_SECRET,
        )

        # Store or update session
        stmt = select(SystemBrokerSession).where(SystemBrokerSession.broker == "smartapi")
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            session.jwt_token = auth_result["jwtToken"]
            session.refresh_token = auth_result["refreshToken"]
            session.feed_token = auth_result["feedToken"]
            session.client_id = settings.ANGEL_SYSTEM_CLIENT_ID
            session.last_auth_at = datetime.utcnow()
            session.is_active = True
            session.last_error = None
            logger.info("[SystemAuth] SmartAPI session updated")
        else:
            session = SystemBrokerSession(
                broker="smartapi",
                jwt_token=auth_result["jwtToken"],
                refresh_token=auth_result["refreshToken"],
                feed_token=auth_result["feedToken"],
                client_id=settings.ANGEL_SYSTEM_CLIENT_ID,
                last_auth_at=datetime.utcnow(),
                is_active=True,
            )
            db.add(session)
            logger.info("[SystemAuth] SmartAPI session created")

    except Exception as e:
        logger.error(f"[SystemAuth] SmartAPI auth failed: {e}")
        # Store error in DB
        stmt = select(SystemBrokerSession).where(SystemBrokerSession.broker == "smartapi")
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session:
            session.is_active = False
            session.last_error = str(e)
        raise


async def _init_kite_session(db: AsyncSession) -> None:
    """
    Initialize Kite system session.

    Uses manually obtained access token from .env (Kite OAuth is manual).
    """
    try:
        logger.info("[SystemAuth] Initializing Kite session...")

        stmt = select(SystemBrokerSession).where(SystemBrokerSession.broker == "kite")
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            session.access_token = settings.KITE_SYSTEM_ACCESS_TOKEN
            session.last_auth_at = datetime.utcnow()
            session.is_active = True
            session.last_error = None
            logger.info("[SystemAuth] Kite session updated")
        else:
            session = SystemBrokerSession(
                broker="kite",
                access_token=settings.KITE_SYSTEM_ACCESS_TOKEN,
                last_auth_at=datetime.utcnow(),
                is_active=True,
            )
            db.add(session)
            logger.info("[SystemAuth] Kite session created")

    except Exception as e:
        logger.error(f"[SystemAuth] Kite session init failed: {e}")
        raise


async def refresh_system_token(broker_type: str, db: AsyncSession) -> None:
    """
    Refresh system broker token.

    Called by TickerServiceManager when reconnecting after token expiry.

    Args:
        broker_type: Broker identifier
        db: Database session
    """
    if broker_type == "smartapi":
        await _refresh_smartapi_token(db)
    elif broker_type == "kite":
        logger.warning("[SystemAuth] Kite tokens don't auto-refresh (manual OAuth)")
    else:
        logger.warning(f"[SystemAuth] Token refresh not implemented for {broker_type}")


async def _refresh_smartapi_token(db: AsyncSession) -> None:
    """
    Refresh SmartAPI token using refresh_token.

    Falls back to full re-auth with TOTP if refresh fails.
    """
    from app.services.legacy.smartapi_auth import SmartAPIAuth

    try:
        logger.info("[SystemAuth] Refreshing SmartAPI token...")

        # Get current session
        stmt = select(SystemBrokerSession).where(SystemBrokerSession.broker == "smartapi")
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session or not session.refresh_token:
            logger.warning("[SystemAuth] No refresh token, doing full auth")
            await _init_smartapi_session(db)
            return

        # Try refresh
        try:
            auth_result = await SmartAPIAuth.refresh_session(session.refresh_token)
            session.jwt_token = auth_result["jwtToken"]
            session.feed_token = auth_result["feedToken"]
            session.last_auth_at = datetime.utcnow()
            session.is_active = True
            session.last_error = None
            await db.commit()
            logger.info("[SystemAuth] SmartAPI token refreshed")

        except Exception as refresh_error:
            logger.warning(f"[SystemAuth] Refresh failed: {refresh_error}, doing full re-auth")
            await _init_smartapi_session(db)

    except Exception as e:
        logger.error(f"[SystemAuth] Token refresh failed: {e}")
        raise


async def get_system_credentials(broker_type: str, db: AsyncSession) -> Optional[Dict]:
    """
    Get current system credentials for a broker.

    Used by TickerServiceManager to connect ticker services.

    Args:
        broker_type: Broker identifier
        db: Database session

    Returns:
        Dict with broker-specific credentials or None if not configured

    Example returns:
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
    """
    stmt = select(SystemBrokerSession).where(
        SystemBrokerSession.broker == broker_type,
        SystemBrokerSession.is_active == True
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        logger.warning(f"[SystemAuth] No active session for {broker_type}")
        return None

    # Check if token is expired (if token_expiry is set)
    if session.token_expiry and session.token_expiry < datetime.utcnow():
        logger.info(f"[SystemAuth] {broker_type} token expired, refreshing...")
        await refresh_system_token(broker_type, db)
        # Re-fetch after refresh
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

    # Build credentials dict
    if broker_type == "smartapi":
        return {
            "jwt_token": session.jwt_token,
            "api_key": settings.ANGEL_API_KEY,  # From .env
            "client_id": session.client_id,
            "feed_token": session.feed_token,
        }
    elif broker_type == "kite":
        return {
            "access_token": session.access_token,
            "api_key": settings.KITE_API_KEY,
        }
    else:
        logger.warning(f"[SystemAuth] Credentials not implemented for {broker_type}")
        return None
```

**Key Patterns Reused**:
- `SmartAPIAuth.authenticate()` from `smartapi_auth.py` (lines 117-195)
- `SmartAPIAuth.refresh_session()` from `smartapi_utils.py`
- Auto-TOTP pattern from `smartapi_auth.py`

**Verification**:
```bash
# Test import
python -c "
from app.services.brokers.market_data.system_auth_service import initialize_system_sessions
print('System auth service defined')
"

# Test in backend shell (requires .env configured)
cd backend
python
>>> from app.database import SessionLocal
>>> from app.services.brokers.market_data.system_auth_service import initialize_system_sessions
>>> import asyncio
>>> asyncio.run(initialize_system_sessions())
# Should see: "[SystemAuth] System broker sessions initialized successfully"
```

---

### Step 1.7: Extend Health Monitor

**File**: `backend/app/services/ai/websocket_health_monitor.py`

**Add to end of file**:
```python
class MultiProviderHealthMonitor:
    """
    Wrapper for managing health monitors across multiple broker providers.

    Each broker gets its own WebSocketHealthMonitor instance.
    Provides aggregate health view for monitoring dashboard.
    """

    _monitors: Dict[str, 'WebSocketHealthMonitor'] = {}

    @classmethod
    def get_or_create(cls, broker_type: str) -> 'WebSocketHealthMonitor':
        """
        Get or create health monitor for a broker.

        Args:
            broker_type: Broker identifier (smartapi, kite, etc.)

        Returns:
            WebSocketHealthMonitor instance
        """
        if broker_type not in cls._monitors:
            cls._monitors[broker_type] = WebSocketHealthMonitor()
            logger.info(f"[HealthMonitor] Created monitor for {broker_type}")

        return cls._monitors[broker_type]

    @classmethod
    def get_aggregate_health(cls) -> Dict[str, Any]:
        """
        Get aggregated health metrics across all brokers.

        Returns:
            Dict with overall status and per-broker metrics
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
                broker_healths[broker_type] = {
                    "status": "error",
                    "error": str(e)
                }
                all_healthy = False

        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "brokers": broker_healths,
            "active_broker_count": len(cls._monitors)
        }

    @classmethod
    def get_broker_health(cls, broker_type: str) -> Optional['HealthMetrics']:
        """
        Get health metrics for specific broker.

        Args:
            broker_type: Broker identifier

        Returns:
            HealthMetrics or None if broker not active
        """
        monitor = cls._monitors.get(broker_type)
        return monitor.get_health_metrics() if monitor else None
```

**Verification**:
```bash
python -c "
from app.services.ai.websocket_health_monitor import MultiProviderHealthMonitor
print('MultiProviderHealthMonitor added successfully')
"
```

---

### Step 1.8: Update Package Exports

**File**: `backend/app/services/brokers/market_data/__init__.py`

**Add exports**:
```python
from app.services.brokers.market_data.multi_tenant_ticker_base import (
    MultiTenantTickerService,
    NormalizedTick
)
from app.services.brokers.market_data.ticker_manager import TickerServiceManager

__all__ = [
    # ... existing exports ...
    "MultiTenantTickerService",
    "NormalizedTick",
    "TickerServiceManager",
]
```

**Verification**:
```bash
python -c "
from app.services.brokers.market_data import MultiTenantTickerService, NormalizedTick, TickerServiceManager
print('All Phase 1 exports available')
"
```

---

### Step 1.9: Remove Dead WebSocket Stubs from MarketDataBrokerAdapter

**File**: `backend/app/services/brokers/market_data/market_data_base.py`

**Action**: Remove dead WebSocket abstract methods from `MarketDataBrokerAdapter`

**Methods to remove**:
- `subscribe()`
- `unsubscribe()`
- `on_tick()`
- `connect()`
- `disconnect()`
- `is_connected()`

**Rationale**: WebSocket ticker functionality belongs exclusively in `MultiTenantTickerService`, not in the REST market data adapter. These methods were never implemented and create confusion about the separation of concerns.

**Verification**:
```bash
# Search for removed methods
grep -n "def subscribe\|def unsubscribe\|def on_tick\|def connect\|def disconnect\|is_connected" backend/app/services/brokers/market_data/market_data_base.py
# Should return nothing
```

---

### Step 1.10: Broker Name Mapping Utility

**New file**: `backend/app/services/brokers/broker_name_mapper.py`

```python
"""
Broker Name Mapping Utility

Maps between display names (stored in DB) and BrokerType enum values.
"""
from typing import Optional
from app.services.brokers.base import BrokerType


# Display name → BrokerType mapping
DISPLAY_NAME_TO_BROKER_TYPE = {
    "zerodha": BrokerType.KITE,
    "angelone": BrokerType.ANGEL,
    "upstox": BrokerType.UPSTOX,
    "dhan": BrokerType.DHAN,
    "fyers": BrokerType.FYERS,
    "paytm": BrokerType.PAYTM,
}

# BrokerType → Display name mapping (reverse)
BROKER_TYPE_TO_DISPLAY_NAME = {v: k for k, v in DISPLAY_NAME_TO_BROKER_TYPE.items()}


def get_broker_type(display_name: str) -> Optional[BrokerType]:
    """
    Convert display name to BrokerType enum.

    Args:
        display_name: Display name from DB ("zerodha", "angelone", etc.)

    Returns:
        BrokerType enum or None if not found
    """
    return DISPLAY_NAME_TO_BROKER_TYPE.get(display_name.lower())


def get_display_name(broker_type: BrokerType) -> str:
    """
    Convert BrokerType enum to display name.

    Args:
        broker_type: BrokerType enum

    Returns:
        Display name for DB storage
    """
    return BROKER_TYPE_TO_DISPLAY_NAME.get(broker_type, broker_type.value)
```

**Create Alembic migration** to normalize existing DB values:

```bash
cd backend
alembic revision -m "normalize broker names in broker_connections"
```

Edit the generated migration file:

```python
def upgrade():
    # Update display names to BrokerType values
    op.execute("UPDATE broker_connections SET broker = 'kite' WHERE broker = 'zerodha'")
    op.execute("UPDATE broker_connections SET broker = 'angel' WHERE broker = 'angelone'")

def downgrade():
    # Restore display names
    op.execute("UPDATE broker_connections SET broker = 'zerodha' WHERE broker = 'kite'")
    op.execute("UPDATE broker_connections SET broker = 'angelone' WHERE broker = 'angel'")
```

**Apply migration**:
```bash
alembic upgrade head
```

**Add mapping for MarketDataSource**:

MarketDataSource in `user_preferences.py` is a plain class (not Enum). Add mapping in the same file:

```python
# In broker_name_mapper.py
from app.models.user_preferences import MarketDataSource

MARKET_DATA_SOURCE_TO_BROKER_TYPE = {
    "smartapi": BrokerType.ANGEL,
    "kite": BrokerType.KITE,
    "upstox": BrokerType.UPSTOX,
    "dhan": BrokerType.DHAN,
    "fyers": BrokerType.FYERS,
    "paytm": BrokerType.PAYTM,
}
```

**Verification**:
```bash
python -c "
from app.services.brokers.broker_name_mapper import get_broker_type, get_display_name
from app.services.brokers.base import BrokerType
print(get_broker_type('zerodha'))  # Should print BrokerType.KITE
print(get_display_name(BrokerType.ANGEL))  # Should print 'angelone'
"
```

---

### Phase 1 Verification Checklist

Run all verifications before proceeding to Phase 2:

```bash
# 1. Database migration applied
alembic current
# Should show: add_system_broker_sessions_table

# 2. All imports work
python -c "
from app.models import SystemBrokerSession
from app.services.brokers.market_data import MultiTenantTickerService, NormalizedTick, TickerServiceManager
from app.services.brokers.market_data.system_auth_service import initialize_system_sessions
from app.services.ai.websocket_health_monitor import MultiProviderHealthMonitor
from app.services.brokers.base import BrokerType
print('BrokerType values:', [e.value for e in BrokerType])
print('All Phase 1 imports successful')
"

# 3. Backend starts without errors
python run.py
# Check logs for: "[SystemAuth] System broker sessions initialized successfully"

# 4. Existing tests still pass
pytest tests/ -v -m "not slow"

# 5. E2E tests still pass (critical routes)
npm run test:specs:dashboard
npm run test:specs:watchlist

# 6. Health endpoint works
curl http://localhost:8001/api/health
```

**Success Criteria**:
- ✅ App boots normally
- ✅ New database table exists
- ✅ All imports successful
- ✅ System auth initializes (if .env configured)
- ✅ Existing functionality unchanged
- ✅ No errors in startup logs

---

## Phase 2: Market Data Adapters

**Timeline**: 4-5 days

**Milestone**: WebSocket route uses `TickerServiceManager`. Token mapping self-contained in adapters. Route shrinks from 534→150 lines.

### Step 2.1: Create `tickers/` Subdirectory

```bash
mkdir -p backend/app/services/brokers/market_data/tickers
touch backend/app/services/brokers/market_data/tickers/__init__.py
```

**File**: `backend/app/services/brokers/market_data/tickers/__init__.py`

```python
"""
Ticker Service Adapters

Implements MultiTenantTickerService for each broker.

Available adapters:
- SmartAPITickerAdapter (full implementation)
- KiteTickerAdapter (full implementation)
- UpstoxTickerAdapter (stub)
- DhanTickerAdapter (stub)
- FyersTickerAdapter (stub)
- PaytmTickerAdapter (stub)
"""

__all__ = [
    "SmartAPITickerAdapter",
    "KiteTickerAdapter",
    "UpstoxTickerAdapter",
    "DhanTickerAdapter",
    "FyersTickerAdapter",
    "PaytmTickerAdapter",
]
```

---

### Step 2.2: SmartAPI Ticker Adapter

**New file**: `backend/app/services/brokers/market_data/tickers/smartapi_ticker_adapter.py`

This is the largest file in Phase 2. It wraps the existing SmartAPI ticker logic.

**⚠️ CRITICAL**: Preserve the exact threading model from `smartapi_ticker.py` lines 132-139!

**Key responsibilities**:
- Wrap `SmartWebSocketV2` in threaded model
- Translate index tokens (KITE → SmartAPI format)
- Normalize ticks (paise → rupees, SmartAPI token → Kite token)
- Manage per-user subscriptions
- Broadcast filtered ticks
- Token refresh on reconnect — when WebSocket disconnects due to auth failure, adapter calls `system_auth_service.refresh_system_token()` to get fresh credentials before reconnecting

**Reference from**: `backend/app/services/legacy/smartapi_ticker.py`

See the full implementation in [docs/api/multi-broker-ticker-api.md](./multi-broker-ticker-api.md) (API Reference section).

---

### Step 2.3: Kite Ticker Adapter

**New file**: `backend/app/services/brokers/market_data/tickers/kite_ticker_adapter.py`

Simpler than SmartAPI - no token translation needed.

**Reference from**: `backend/app/services/legacy/kite_ticker.py`

See implementation in API Reference.

---

### Step 2.4: Stub Adapters (4 files)

Create 4 stub files (implementation details below).

---

### Step 2.5a: Frontend Exchange Parameter

**Files to update**: ~8 frontend WebSocket stores

**Changes**: Update all WebSocket subscribe messages to include `exchange` field.

**Files**:
1. `frontend/src/stores/watchlist.js` - Watchlist subscriptions
2. `frontend/src/stores/optionchain.js` - Option chain subscriptions
3. `frontend/src/stores/dashboard.js` - Dashboard index subscriptions
4. `frontend/src/stores/positions.js` - Position monitoring
5. `frontend/src/stores/strategy.js` - Strategy builder subscriptions
6. `frontend/src/stores/autopilot.js` - AutoPilot monitoring (if applicable)
7. Other stores with WebSocket subscriptions

**Before**:
```javascript
ws.send(JSON.stringify({
  action: 'subscribe',
  tokens: [256265, 260105],
  mode: 'quote'
}))
```

**After**:
```javascript
ws.send(JSON.stringify({
  action: 'subscribe',
  tokens: [256265, 260105],
  mode: 'quote',
  exchange: 'NSE'  // or 'NFO' for options
}))
```

**Exchange determination**:
- Indices (NIFTY, BANKNIFTY, SENSEX, FINNIFTY): `exchange: 'NSE'`
- Options (CE, PE strikes): `exchange: 'NFO'`
- Equities: `exchange: 'NSE'`
- Futures: `exchange: 'NFO'`

**Verification**:
```bash
# Search for subscribe messages missing exchange
grep -rn "action.*subscribe" frontend/src/stores/ | grep -v "exchange"
# Should return only non-WebSocket subscribe patterns
```

---

### Step 2.5: Refactor websocket.py (was Step 2.4)

Create 4 stub files:
- `upstox_ticker_adapter.py`
- `dhan_ticker_adapter.py`
- `fyers_ticker_adapter.py`
- `paytm_ticker_adapter.py`

**Template**:
```python
"""
{BROKER_NAME} Ticker Adapter (Stub)

To be implemented when {BROKER_NAME} support is added.
"""
from typing import List, Optional
from fastapi import WebSocket
from app.services.brokers.market_data.multi_tenant_ticker_base import (
    MultiTenantTickerService,
    NormalizedTick
)


class {BROKER_NAME_CAPS}TickerAdapter(MultiTenantTickerService):
    """Stub implementation for {BROKER_NAME} ticker service."""

    async def connect(self, **credentials) -> None:
        raise NotImplementedError("{BROKER_NAME} ticker not yet implemented")

    async def disconnect(self) -> None:
        raise NotImplementedError("{BROKER_NAME} ticker not yet implemented")

    async def subscribe(self, tokens: List[int], user_id: str, exchange: str = "NFO", mode: str = "quote") -> None:
        raise NotImplementedError("{BROKER_NAME} ticker not yet implemented")

    async def unsubscribe(self, tokens: List[int], user_id: str, exchange: str = "NFO") -> None:
        raise NotImplementedError("{BROKER_NAME} ticker not yet implemented")

    async def register_client(self, user_id: str, websocket: WebSocket) -> None:
        raise NotImplementedError("{BROKER_NAME} ticker not yet implemented")

    async def unregister_client(self, user_id: str) -> None:
        raise NotImplementedError("{BROKER_NAME} ticker not yet implemented")

    def get_latest_tick(self, token: int) -> Optional[NormalizedTick]:
        raise NotImplementedError("{BROKER_NAME} ticker not yet implemented")

    @property
    def is_connected(self) -> bool:
        return False

    @property
    def client_count(self) -> int:
        return 0

    @property
    def broker_type(self) -> str:
        return "{broker_name}"  # lowercase
```

---

### Step 2.5: Refactor `websocket.py`

**File**: `backend/app/api/routes/websocket.py`

This is the **largest change** in Phase 2.

**Remove** (~380 lines):
- Lines 26-27: `from app.services.legacy import smartapi_ticker_service, kite_ticker_service`
- Lines 32-43: `KITE_TO_SMARTAPI_INDEX`, `SMARTAPI_TO_KITE_INDEX`
- Lines 84-110: `get_user_broker_connection()`
- Lines 135-163: `get_smartapi_credentials()`
- Lines 166-244: `fetch_initial_index_quotes()`
- Lines 288-384: Broker selection if/else
- Lines 413-468: Token translation in subscribe

**New implementation** (~150 lines):

See complete refactored route in [docs/api/multi-broker-ticker-api.md](./multi-broker-ticker-api.md).

**Key changes**:
- Import `TickerServiceManager` instead of singletons
- Remove all token mapping dicts
- Remove broker-specific helper functions
- Simplify subscribe/unsubscribe handlers
- Let adapter handle ALL translation

---

### Step 2.6: App Startup Integration

**File**: `backend/app/main.py`

**Find the lifespan function** (around line 50-100):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")

    # ... existing startup code ...

    # ADD THIS: Initialize system broker sessions
    from app.services.brokers.market_data.system_auth_service import initialize_system_sessions
    try:
        await initialize_system_sessions()
    except Exception as e:
        logger.error(f"Failed to initialize system sessions: {e}")
        # Don't block app startup if system sessions fail

    yield

    # Shutdown
    logger.info("Application shutting down...")

    # ADD THIS: Shutdown all tickers
    from app.services.brokers.market_data.ticker_manager import TickerServiceManager
    try:
        await TickerServiceManager.shutdown_all()
    except Exception as e:
        logger.error(f"Error during ticker shutdown: {e}")
```

**Verification**:
```bash
python run.py
# Check logs for:
# "[SystemAuth] System broker sessions initialized successfully"
# On shutdown: "[TickerManager] All tickers shutdown complete"
```

---

### Step 2.7: Deprecate Legacy Singletons

**File**: `backend/app/services/legacy/smartapi_ticker.py`

**Add at top of file**:
```python
"""
SmartAPI Ticker Service (DEPRECATED)

⚠️ DEPRECATED: This file is deprecated and will be removed in a future release.
Use SmartAPITickerAdapter from app.services.brokers.market_data.tickers instead.

Reason: Replaced by MultiTenantTickerService architecture for multi-broker support.
See: docs/decisions/003-multi-broker-ticker-architecture.md

This file is kept temporarily for backward compatibility with services that
may still reference smartapi_ticker_service directly (e.g., AutoPilot).
"""
import warnings

warnings.warn(
    "smartapi_ticker_service is deprecated. "
    "Use TickerServiceManager.get_ticker('smartapi') instead.",
    DeprecationWarning,
    stacklevel=2
)
```

**File**: `backend/app/services/legacy/kite_ticker.py`

**Add same deprecation warning** (replace "smartapi" with "kite").

**Verification**:
```bash
# Should show deprecation warning
python -c "
from app.services.legacy.smartapi_ticker import smartapi_ticker_service
print('Import works but shows warning')
"
```

---

### Step 2.8: Deprecate Old `TickerService` ABC

**File**: `backend/app/services/brokers/market_data/ticker_base.py`

**Add to docstring**:
```python
"""
Ticker Service Base (DEPRECATED)

⚠️ DEPRECATED: This interface is deprecated and not used.
Use MultiTenantTickerService from multi_tenant_ticker_base.py instead.

Reason:
- Method signatures don't match real implementations
- No multi-tenancy support (no user_id parameter)
- Uses callback pattern instead of direct WebSocket broadcasting
- No client management

See: docs/decisions/003-multi-broker-ticker-architecture.md
"""
import warnings

warnings.warn(
    "TickerService is deprecated. Use MultiTenantTickerService instead.",
    DeprecationWarning,
    stacklevel=2
)
```

---

### Phase 2 Verification Checklist

```bash
# 1. Verify all adapter files exist
ls backend/app/services/brokers/market_data/tickers/
# Should show: __init__.py, smartapi_ticker_adapter.py, kite_ticker_adapter.py, 4 stub files

# 2. Verify imports work
python -c "
from app.services.brokers.market_data.tickers.smartapi_ticker_adapter import SmartAPITickerAdapter
from app.services.brokers.market_data.tickers.kite_ticker_adapter import KiteTickerAdapter
print('Adapters import successfully')
"

# 3. Start backend
python run.py
# Check logs for: "[SystemAuth] SmartAPI session created"
# No errors during startup

# 4. Test WebSocket connection manually
# Open browser console:
const ws = new WebSocket('ws://localhost:8001/ws/ticks?token=YOUR_JWT')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
ws.send(JSON.stringify({action: 'subscribe', tokens: [256265], mode: 'quote'}))
# Verify: {"type": "connected", "source": "smartapi", "connected": true}
# Verify: {"type": "subscribed", "tokens": [256265], ...}
# Verify: {"type": "ticks", "data": [...]} with normalized prices

# 5. Run E2E tests for WebSocket-dependent screens
npm run test:specs:optionchain
npm run test:specs:watchlist
npm run test:specs:dashboard

# 6. Verify health endpoint
curl http://localhost:8001/api/health
# Should include ticker/WebSocket status

# 7. Check websocket.py line count
wc -l backend/app/api/routes/websocket.py
# Should be ~150-200 lines (down from 534)

# 8. Grep for removed code (should return nothing)
grep -n "KITE_TO_SMARTAPI_INDEX" backend/app/api/routes/websocket.py
grep -n "get_smartapi_credentials" backend/app/api/routes/websocket.py
grep -n "fetch_initial_index_quotes" backend/app/api/routes/websocket.py
```

**Success Criteria**:
- ✅ WebSocket route reduced to ~150 lines
- ✅ No token mapping dicts in route
- ✅ All adapters registered and importable
- ✅ Manual WebSocket connection works
- ✅ E2E tests pass
- ✅ No broker-specific logic in route
- ✅ Health monitor shows ticker status

---

## Phase 3: Order Execution

**Timeline**: 1-2 weeks

**Milestone**: Users can select broker for order execution (6 brokers supported).

### Step 3.1: Add `order_execution_broker` Column to UserPreferences

**File**: `backend/app/models/user_preferences.py`

**Add column**:
```python
order_execution_broker = Column(String(20), default="kite", nullable=False)
# Check constraint for 6 values
CheckConstraint(
    "order_execution_broker IN ('kite', 'angel', 'upstox', 'dhan', 'fyers', 'paytm')",
    name="valid_order_execution_broker"
)
```

**Create migration**:
```bash
alembic revision --autogenerate -m "add order_execution_broker to user_preferences"
alembic upgrade head
```

---

### Step 3.2: Refactor BrokerAdapter Base Class

**File**: `backend/app/services/brokers/base.py`

**Remove Kite-specific method** (line ~490):
```python
# REMOVE THIS METHOD from abstract base class:
def get_kite_client(self) -> KiteConnect:
    """Returns KiteConnect instance."""
    pass
```

**Move to KiteAdapter only**:
```python
# In backend/app/services/brokers/kite_adapter.py
class KiteAdapter(BrokerAdapter):
    def get_kite_client(self) -> KiteConnect:
        """Returns KiteConnect instance. Kite-specific method."""
        return self.kite
```

**Refactor `__init__`** to accept generic credentials dict:

**Before**:
```python
def __init__(self, access_token: str):
    self.access_token = access_token
```

**After**:
```python
def __init__(self, credentials: Dict[str, Any]):
    self.credentials = credentials
    # Subclasses extract what they need
```

---

### Step 3.3: Add Broker Name Mapping Utility

Already completed in Step 1.10. Use `get_broker_type()` and `get_display_name()` helpers.

---

### Step 3.4: Implement AngelAdapter (Full Order Execution)

**New file**: `backend/app/services/brokers/angel_adapter.py`

**Implementation**:
```python
"""
Angel One Order Execution Adapter

Implements BrokerAdapter for Angel One SmartAPI order execution.
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from smartapi import SmartConnect

from app.services.brokers.base import (
    BrokerAdapter, UnifiedOrder, UnifiedPosition, UnifiedQuote,
    OrderSide, OrderType, ProductType, OrderStatus
)


class AngelAdapter(BrokerAdapter):
    """Angel One SmartAPI adapter for order execution."""

    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials)
        self.client = SmartConnect(api_key=credentials["api_key"])
        # Authenticate using credentials
        self.client.generateSession(
            clientCode=credentials["client_id"],
            password=credentials["pin"],
            totp=credentials["totp"]  # Or use auto-TOTP
        )

    async def place_order(
        self,
        tradingsymbol: str,
        exchange: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType,
        product: ProductType,
        price: Optional[Decimal] = None,
        trigger_price: Optional[Decimal] = None,
        disclosed_quantity: Optional[int] = None,
        validity: str = "DAY",
        tag: Optional[str] = None
    ) -> UnifiedOrder:
        """Place order via Angel One API."""
        # Map to Angel format
        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": tradingsymbol,
            "symboltoken": self._get_token(tradingsymbol, exchange),
            "transactiontype": "BUY" if side == OrderSide.BUY else "SELL",
            "exchange": exchange,
            "ordertype": self._map_order_type(order_type),
            "producttype": self._map_product_type(product),
            "duration": validity,
            "quantity": quantity,
        }

        if price:
            order_params["price"] = float(price)
        if trigger_price:
            order_params["triggerprice"] = float(trigger_price)

        # Place order
        response = self.client.placeOrder(order_params)

        # Convert to UnifiedOrder
        return self._normalize_order(response)

    # Implement other abstract methods...
    # (Similar to KiteAdapter but using SmartConnect API)
```

---

### Step 3.5: Create 4 Stub Order Adapters

Create stub files:
- `backend/app/services/brokers/upstox_adapter.py`
- `backend/app/services/brokers/dhan_adapter.py`
- `backend/app/services/brokers/fyers_adapter.py`
- `backend/app/services/brokers/paytm_adapter.py`

**Template** (same as market data stubs, but for BrokerAdapter):
```python
"""
{BROKER} Order Execution Adapter (Stub)
"""
from app.services.brokers.base import BrokerAdapter

class {BROKER}Adapter(BrokerAdapter):
    async def place_order(self, ...):
        raise NotImplementedError("{BROKER} order execution not yet implemented")

    # Other methods raise NotImplementedError
```

---

### Step 3.6: Register All in Order Factory

**File**: `backend/app/services/brokers/factory.py`

**Update `_BROKER_ADAPTERS`**:
```python
_BROKER_ADAPTERS = {
    BrokerType.KITE: KiteAdapter,
    BrokerType.ANGEL: AngelAdapter,
    BrokerType.UPSTOX: UpstoxAdapter,
    BrokerType.DHAN: DhanAdapter,
    BrokerType.FYERS: FyersAdapter,
    BrokerType.PAYTM: PaytmAdapter,
}
```

---

### Step 3.7: Update `get_broker_adapter_dep()` Dependency

**File**: `backend/app/utils/dependencies.py` (line ~167)

**Before** (hardcoded):
```python
async def get_broker_adapter_dep(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> BrokerAdapter:
    # Hardcoded to Kite
    adapter = get_broker_adapter(BrokerType.KITE, {"access_token": current_user.access_token})
    return adapter
```

**After** (read from user preference):
```python
async def get_broker_adapter_dep(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> BrokerAdapter:
    from app.models import UserPreferences
    from app.services.brokers.broker_name_mapper import get_broker_type

    # Get user preference
    prefs = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    prefs = prefs.scalar_one_or_none()

    broker_type = get_broker_type(prefs.order_execution_broker) if prefs else BrokerType.KITE

    # Get broker connection for credentials
    conn = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == broker_type.value
        )
    )
    conn = conn.scalar_one_or_none()

    if not conn:
        raise ValueError(f"No {broker_type.value} connection found for user")

    # Build credentials dict
    credentials = {"access_token": conn.access_token}

    adapter = get_broker_adapter(broker_type, credentials)
    return adapter
```

---

### Step 3.8: Migrate `get_kite_client()` Usages (~40 locations)

**Search for usages**:
```bash
grep -rn "get_kite_client()" backend/app/
```

**Files to update**:
- AutoPilot services: `condition_engine.py`, `order_executor.py`, `strategy_monitor.py`, etc.
- AI routes: `backend/app/api/routes/ai.py`
- Order routes: `backend/app/api/routes/orders.py`

**Pattern**:

**Before**:
```python
kite = adapter.get_kite_client()
ltp = kite.ltp([token])
```

**After**:
```python
# Use adapter methods directly
quote = await adapter.get_quote(tradingsymbol, exchange)
ltp = quote.last_price
```

**Note**: This is the most labor-intensive step. Each usage must be reviewed individually.

---

### Step 3.9: Add Broker Name Migration

Already completed in Step 1.10.

---

### Step 3.10: Add OAuth/Auth Flows for New Brokers

**File**: `backend/app/api/routes/auth.py`

**Add routes for each broker**:
- `/api/auth/upstox/login`
- `/api/auth/upstox/callback`
- `/api/auth/dhan/login`
- `/api/auth/dhan/callback`
- (etc. for Fyers, Paytm)

**Pattern**: Follow existing Zerodha OAuth flow (lines ~50-150)

**Angel One**: Refine existing flow (lines 318-499) for per-user order credentials (currently system-level only)

---

### Step 3.11: Frontend Settings UI for Broker Selection

**File**: `frontend/src/components/settings/MarketDataSourceToggle.vue`

**Remove hardcoded text** (line ~170):
```vue
<!-- REMOVE THIS: -->
<p class="text-sm text-gray-500">Orders always via Zerodha Kite</p>
```

**Add order execution broker selector**:
```vue
<div class="mt-4">
  <label class="block text-sm font-medium text-gray-700">Order Execution Broker</label>
  <select v-model="orderExecutionBroker" class="mt-1 block w-full">
    <option value="kite">Zerodha (Kite)</option>
    <option value="angel">Angel One (SmartAPI)</option>
    <option value="upstox">Upstox</option>
    <option value="dhan">Dhan</option>
    <option value="fyers">Fyers</option>
    <option value="paytm">Paytm Money</option>
  </select>
</div>
```

**Add credential management** for selected broker (API key inputs, OAuth buttons, etc.)

---

### Phase 3 Verification Checklist

```bash
# 1. Verify all adapters registered
python -c "
from app.services.brokers.factory import _BROKER_ADAPTERS
print(list(_BROKER_ADAPTERS.keys()))
# Should show: [BrokerType.KITE, BrokerType.ANGEL, ...]
"

# 2. Verify UserPreferences column exists
python -c "
from app.models import UserPreferences
print(hasattr(UserPreferences, 'order_execution_broker'))
# Should print: True
"

# 3. Test adapter dependency
# Start backend, make authenticated request to /api/positions
# Should use user's selected broker

# 4. Verify no more get_kite_client() usages in business logic
grep -rn "get_kite_client()" backend/app/services/
# Should only return KiteAdapter implementation

# 5. Frontend settings UI shows broker selector
# Navigate to /settings, verify dropdown exists
```

**Success Criteria**:
- ✅ 6 brokers registered in factory
- ✅ AngelAdapter fully implemented
- ✅ `get_broker_adapter_dep()` reads user preference
- ✅ All `get_kite_client()` usages migrated
- ✅ Frontend UI allows broker selection
- ✅ OAuth flows added for new brokers

---

## Verification Steps

### Comprehensive Testing

```bash
# Backend unit tests
cd backend
pytest tests/ -v --cov=app

# E2E tests
cd ..
npm test  # Full suite

# Specific WebSocket tests
npm run test:specs:optionchain
npm run test:specs:watchlist
npm run test:specs:positions

# AutoPilot tests (ticker-dependent)
npm run test:autopilot:fast

# Accessibility audits
npm run test:audit
```

### Manual Verification

1. **WebSocket Connection**:
   - Open browser console at `http://localhost:5173/dashboard`
   - Check network tab for `ws://localhost:8001/ws/ticks` connection
   - Verify ticks received in console

2. **Token Mapping**:
   - Subscribe to index token: `256265` (NIFTY)
   - Verify SmartAPI receives translated token: `99926000`
   - Verify ticks come back with original token: `256265`

3. **Multi-User**:
   - Open 2 browser tabs with different users
   - Both should share same WebSocket connection
   - Each should only receive ticks for their subscribed tokens

4. **Health Monitor**:
   - Visit `/api/health` endpoint
   - Verify ticker status shows "connected"
   - Check client count matches active users

---

## Troubleshooting

### Common Issues

#### 1. SmartAPI Threading Error

**Symptom**: `RuntimeError: There is no current event loop in thread`

**Cause**: Incorrect threading model when wrapping `SmartWebSocketV2`

**Fix**: Ensure using `asyncio.run_coroutine_threadsafe` pattern from `smartapi_ticker.py:139`

#### 2. Token Mapping Not Working

**Symptom**: Ticks show SmartAPI tokens instead of Kite tokens

**Fix**:
- Check `SmartAPITickerAdapter.KITE_TO_SMARTAPI_INDEX` is populated
- Verify `_normalize_tick()` translates tokens back
- Verify `SMARTAPI_TO_KITE_INDEX` reverse mapping exists

#### 3. System Credentials Not Found

**Symptom**: `ValueError: System credentials not configured for smartapi`

**Fix**:
```bash
# Verify .env has credentials
cat backend/.env | grep ANGEL_SYSTEM

# Re-run initialization
python -c "
from app.services.brokers.market_data.system_auth_service import initialize_system_sessions
import asyncio
asyncio.run(initialize_system_sessions())
"
```

#### 4. WebSocket Won't Connect

**Symptom**: `{"type": "connected", "connected": false}`

**Fix**:
- Check `system_broker_sessions` table has active session
- Verify feed_token is not expired
- Check logs for connection errors
- Try manual re-auth:
  ```bash
  python -c "
  from app.services.legacy.smartapi_auth import SmartAPIAuth
  import asyncio
  result = asyncio.run(SmartAPIAuth.authenticate(
      client_id='...', pin='...', totp_secret='...'
  ))
  print(result)
  "
  ```

#### 5. Circular Import

**Symptom**: `ImportError: cannot import name 'TickerServiceManager'`

**Cause**: Adapter trying to import manager (circular dependency)

**Fix**: Use lazy import in manager, not in adapters

---

## Rollback Procedures

### Phase 1 Rollback

```bash
# Drop migration
alembic downgrade -1

# Remove new files
rm backend/app/models/system_broker_sessions.py
rm backend/app/services/brokers/market_data/multi_tenant_ticker_base.py
rm backend/app/services/brokers/market_data/ticker_manager.py
rm backend/app/services/brokers/market_data/system_auth_service.py

# Restore original files
git checkout backend/app/services/brokers/base.py
git checkout backend/app/config.py
git checkout backend/app/models/__init__.py
git checkout backend/app/services/ai/websocket_health_monitor.py
```

### Phase 2 Rollback

```bash
# Restore original websocket.py
git checkout backend/app/api/routes/websocket.py

# Remove adapters
rm -rf backend/app/services/brokers/market_data/tickers/

# Restore main.py
git checkout backend/app/main.py

# Remove deprecation warnings
git checkout backend/app/services/legacy/smartapi_ticker.py
git checkout backend/app/services/legacy/kite_ticker.py
git checkout backend/app/services/brokers/market_data/ticker_base.py
```

### Phase 3 Rollback

```bash
# Revert migration
alembic downgrade -1

# Restore files
git checkout backend/app/models/user_preferences.py
git checkout backend/app/services/brokers/factory.py
git checkout backend/app/utils/dependencies.py

# Remove new adapters
rm backend/app/services/brokers/angel_adapter.py
rm backend/app/services/brokers/upstox_adapter.py
rm backend/app/services/brokers/dhan_adapter.py
rm backend/app/services/brokers/fyers_adapter.py
rm backend/app/services/brokers/paytm_adapter.py
```

---

## Success Metrics

### Phase 1 Success

- ✅ App boots without errors
- ✅ Database table created
- ✅ System sessions initialized
- ✅ All imports successful
- ✅ No regressions in existing tests

### Phase 2 Success

- ✅ Route reduced from 534 to ~150 lines
- ✅ Zero broker-specific logic in route
- ✅ Token mapping self-contained in adapters
- ✅ WebSocket connections work
- ✅ All E2E tests pass
- ✅ Health monitor shows per-broker status
- ✅ Multi-user subscriptions work correctly

### Phase 3 Success

- ✅ Users can select order execution broker
- ✅ AngelOne orders work via adapter
- ✅ Factory supports 6 brokers
- ✅ Settings UI complete
- ✅ OAuth flows implemented
- ✅ All order tests pass

---

## References

- [ADR-003: Multi-Broker Ticker Architecture](../decisions/003-multi-broker-ticker-architecture.md)
- [Multi-Broker Ticker API Reference](./multi-broker-ticker-api.md)
- [Broker Abstraction Architecture](./broker-abstraction.md)
- [CLAUDE.md](../../CLAUDE.md) - Project conventions
