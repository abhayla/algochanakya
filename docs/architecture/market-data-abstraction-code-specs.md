# Market Data Broker Abstraction - Part 2: Code Specifications

> **Part of:** Multi-Broker Market Data Abstraction
> **Version:** 2.0
> **Status:** Complete Code Specifications
> **Related Files:**
> - [Part 1: Design & Specification](./market-data-abstraction-design.md)
> - [Part 3: Implementation Guide](./market-data-abstraction-implementation.md)

---

## Table of Contents

8. [Data Models & Types](#8-data-models--types)
9. [Database Schema](#9-database-schema)
10. [TickerService Interface](#10-tickerservice-interface)
11. [Error Handling & Resilience](#11-error-handling--resilience)

---

## 8. DATA MODELS & TYPES

### 8.1 Missing Dataclasses

The following dataclasses must be added to `backend/app/services/brokers/market_data_base.py`:

```python
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID


class MarketDataBrokerType(str, Enum):
    """Supported market data broker types."""
    SMARTAPI = "smartapi"
    KITE = "kite"
    UPSTOX = "upstox"
    DHAN = "dhan"
    FYERS = "fyers"
    PAYTM = "paytm"


@dataclass
class BrokerCredentials:
    """Base class for broker credentials."""
    broker_type: str
    user_id: UUID


@dataclass
class SmartAPIMarketDataCredentials(BrokerCredentials):
    """SmartAPI-specific credentials for market data."""
    client_id: str
    jwt_token: str
    feed_token: str
    broker_type: str = "smartapi"


@dataclass
class KiteMarketDataCredentials(BrokerCredentials):
    """Kite-specific credentials for market data."""
    api_key: str
    access_token: str
    broker_type: str = "kite"


@dataclass
class UpstoxMarketDataCredentials(BrokerCredentials):
    """Upstox-specific credentials for market data."""
    api_key: str
    access_token: str
    broker_type: str = "upstox"


@dataclass
class OHLCVCandle:
    """Historical OHLC+Volume candle."""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    oi: Optional[int] = None  # For F&O instruments

    # Raw response for debugging
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class Instrument:
    """Instrument definition (broker-agnostic)."""
    # Canonical identification
    canonical_symbol: str           # NIFTY25APR25000CE (Kite format)
    exchange: str                   # NSE, NFO, BSE, MCX

    # Broker-specific
    broker_symbol: str              # Broker-specific format
    instrument_token: int           # Broker token

    # Display
    tradingsymbol: str             # Human-readable name
    name: str                      # Full name (e.g., "NIFTY 24 APR 25000 CE")

    # For options
    underlying: Optional[str] = None        # NIFTY, BANKNIFTY
    expiry: Optional[date] = None          # 2025-04-24
    strike: Optional[Decimal] = None        # 25000
    option_type: Optional[str] = None       # CE, PE

    # For futures
    instrument_type: str = "EQ"    # EQ, FUT, CE, PE

    # Trading details
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.05")
    is_tradable: bool = True

    # Metadata
    segment: str = "NFO"           # CASH, NFO, BFO, MCX
    last_price: Optional[Decimal] = None
```

---

## 9. DATABASE SCHEMA

### 9.1 Token Mapping Table

**Create new table:** `broker_instrument_tokens`

```python
# backend/app/models/broker_instrument_tokens.py
"""
Broker Instrument Token Mapping

Maps canonical symbols (Kite format) to broker-specific symbols and tokens.
Populated daily via scheduled job that downloads instruments from each broker.
"""
from sqlalchemy import Column, String, BigInteger, Date, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func

from app.database import Base


class BrokerInstrumentToken(Base):
    """Maps canonical symbols to broker-specific symbols and tokens."""
    __tablename__ = "broker_instrument_tokens"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Canonical symbol (Kite format - our internal standard)
    canonical_symbol = Column(String(50), nullable=False, index=True)

    # Broker identification
    broker = Column(String(20), nullable=False, index=True)  # smartapi, kite, upstox, dhan, fyers, paytm

    # Broker-specific data
    broker_symbol = Column(String(100), nullable=False)
    broker_token = Column(BigInteger, nullable=False)

    # Instrument details
    exchange = Column(String(10), nullable=False)  # NSE, NFO, BSE, BFO, MCX
    underlying = Column(String(20), nullable=True)  # NIFTY, BANKNIFTY, etc.
    expiry = Column(Date, nullable=True)  # For cleanup of expired contracts

    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # Unique constraint: one mapping per symbol per broker
        UniqueConstraint('canonical_symbol', 'broker', name='uq_symbol_broker'),

        # Indexes for fast lookups
        Index('idx_broker_token', 'broker', 'broker_token'),
        Index('idx_canonical_symbol', 'canonical_symbol'),
        Index('idx_broker_symbol', 'broker', 'broker_symbol'),
        Index('idx_expiry', 'expiry'),  # For cleanup of expired contracts
    )

    def __repr__(self):
        return f"<BrokerInstrumentToken({self.canonical_symbol} -> {self.broker}:{self.broker_symbol})>"
```

**Migration steps:**
```bash
# After creating the model file:
# 1. Import in backend/app/models/__init__.py
# 2. Import in backend/alembic/env.py
# 3. Generate migration
cd backend
alembic revision --autogenerate -m "Add broker_instrument_tokens table"
alembic upgrade head
```

### 9.2 Update User Preferences

**File:** `backend/app/models/user_preferences.py`

```python
# UPDATE lines 14-19
class MarketDataSource:
    """Valid market data source values."""
    SMARTAPI = "smartapi"
    KITE = "kite"
    UPSTOX = "upstox"
    DHAN = "dhan"
    FYERS = "fyers"
    PAYTM = "paytm"

    VALID_SOURCES = [SMARTAPI, KITE, UPSTOX, DHAN, FYERS, PAYTM]

# UPDATE CheckConstraint (line 53-56)
CheckConstraint(
    "market_data_source IN ('smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm')",
    name='check_market_data_source'
),
```

### 9.3 Broker Credentials Tables

**Required:** Create credential tables for each new broker.

**Example for Upstox:**
```python
# backend/app/models/upstox_credentials.py
"""Upstox API Credentials"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class UpstoxCredentials(Base):
    """Upstox API credentials storage."""
    __tablename__ = "upstox_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Upstox credentials
    api_key = Column(String(100), nullable=False)
    encrypted_api_secret = Column(Text, nullable=False)
    access_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_auth_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="upstox_credentials")
```

**Similar tables needed for:**
- `DhanCredentials`
- `FyersCredentials`
- `PaytmCredentials`

---

## 10. TICKERSERVICE INTERFACE

The TickerService provides a unified interface for WebSocket ticker connections across brokers.

**File:** `backend/app/services/brokers/ticker_base.py`

```python
"""
Base Ticker Service Interface

Defines the abstract interface for WebSocket ticker services.
Separate from MarketDataBrokerAdapter because WebSocket management
is a separate concern from REST API operations.
"""
from abc import ABC, abstractmethod
from typing import Callable, List, Set, Optional
from app.services.brokers.market_data_base import UnifiedQuote


class TickerService(ABC):
    """
    Abstract interface for broker WebSocket ticker services.

    All broker ticker services (SmartAPI, Kite, Upstox, etc.)
    must implement this interface.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish WebSocket connection to broker.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close WebSocket connection gracefully.

        Should unsubscribe from all tokens before closing.
        """
        pass

    @abstractmethod
    async def subscribe(self, tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe to instrument tokens for live ticks.

        Args:
            tokens: List of instrument tokens (broker-specific tokens)
            mode: "ltp" (price only) or "quote" (full quote with depth)
        """
        pass

    @abstractmethod
    async def unsubscribe(self, tokens: List[int]) -> None:
        """
        Unsubscribe from instrument tokens.

        Args:
            tokens: List of instrument tokens to unsubscribe
        """
        pass

    @abstractmethod
    def on_tick(self, callback: Callable[[List[UnifiedQuote]], None]) -> None:
        """
        Register callback for incoming tick data.

        Callback will be invoked with list of UnifiedQuote objects.
        All prices normalized to RUPEES, all symbols in CANONICAL format.

        Args:
            callback: Function to call with tick data
        """
        pass

    @abstractmethod
    def on_error(self, callback: Callable[[str], None]) -> None:
        """
        Register callback for WebSocket errors.

        Args:
            callback: Function to call with error message
        """
        pass

    @abstractmethod
    def on_close(self, callback: Callable[[str], None]) -> None:
        """
        Register callback for connection close.

        Args:
            callback: Function to call with close reason
        """
        pass

    @abstractmethod
    async def reconnect(self, max_retries: int = 5) -> bool:
        """
        Reconnect WebSocket with exponential backoff.

        Args:
            max_retries: Maximum number of reconnection attempts

        Returns:
            True if reconnection successful, False otherwise
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        pass

    @property
    @abstractmethod
    def subscribed_tokens(self) -> Set[int]:
        """Get set of currently subscribed tokens."""
        pass

    @property
    @abstractmethod
    def reconnection_attempts(self) -> int:
        """Get number of reconnection attempts made."""
        pass


# Factory function
def get_ticker_service(broker_type: str, credentials) -> TickerService:
    """
    Factory to get ticker service based on broker type.

    Args:
        broker_type: Broker identifier (smartapi, kite, upstox, etc.)
        credentials: Broker-specific credentials object

    Returns:
        TickerService implementation for the broker

    Raises:
        ValueError: If broker type not supported
    """
    if broker_type == "smartapi":
        from app.services.smartapi_ticker import SmartAPITickerService
        return SmartAPITickerService(credentials)
    elif broker_type == "kite":
        from app.services.kite_ticker import KiteTickerService
        return KiteTickerService(credentials)
    elif broker_type == "upstox":
        from app.services.upstox_ticker import UpstoxTickerService
        return UpstoxTickerService(credentials)
    elif broker_type == "dhan":
        from app.services.dhan_ticker import DhanTickerService
        return DhanTickerService(credentials)
    elif broker_type == "fyers":
        from app.services.fyers_ticker import FyersTickerService
        return FyersTickerService(credentials)
    elif broker_type == "paytm":
        from app.services.paytm_ticker import PaytmTickerService
        return PaytmTickerService(credentials)
    else:
        raise ValueError(f"Unsupported broker type: {broker_type}")
```

---

## 11. ERROR HANDLING & RESILIENCE

### 11.1 Exception Hierarchy

```python
# backend/app/services/brokers/exceptions.py
"""Broker-related exceptions."""


class BrokerError(Exception):
    """Base exception for all broker errors."""
    pass


class BrokerAPIError(BrokerError):
    """Broker API returned an error."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class BrokerAPIDownError(BrokerAPIError):
    """Broker API is down or unreachable."""
    pass


class BrokerRateLimitError(BrokerAPIError):
    """Hit broker API rate limit."""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after  # seconds until can retry


class BrokerAuthenticationError(BrokerAPIError):
    """Broker authentication failed (token expired/invalid)."""
    pass


class BrokerSymbolNotFoundError(BrokerError):
    """Symbol not found in broker's instrument list."""
    def __init__(self, symbol: str, broker: str):
        super().__init__(f"Symbol {symbol} not found for broker {broker}")
        self.symbol = symbol
        self.broker = broker


class BrokerWebSocketError(BrokerError):
    """WebSocket connection error."""
    pass
```

### 11.2 Rate Limiting

```python
# backend/app/services/brokers/rate_limiter.py
"""Broker API rate limiter."""
import asyncio
import time
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BrokerRateLimiter:
    """
    Track and enforce broker API rate limits.

    Uses sliding window algorithm with Redis for distributed rate limiting.
    """

    # Rate limits per broker (requests per minute)
    RATE_LIMITS = {
        'smartapi': {
            'quotes': 100,        # LTP/quote requests
            'historical': 50,     # Historical data requests
            'instruments': 10,    # Instrument downloads
        },
        'kite': {
            'quotes': 100,
            'historical': 60,
            'instruments': 10,
        },
        'upstox': {
            'quotes': 250,
            'historical': 100,
            'instruments': 20,
        },
        'dhan': {
            'quotes': 150,
            'historical': 75,
            'instruments': 15,
        },
        'fyers': {
            'quotes': 200,
            'historical': 100,
            'instruments': 20,
        },
        'paytm': {
            'quotes': 100,
            'historical': 50,
            'instruments': 10,
        },
    }

    def __init__(self, redis_client=None):
        """
        Initialize rate limiter.

        Args:
            redis_client: Optional Redis client for distributed limiting
        """
        self.redis = redis_client
        self._local_counters: Dict[str, list] = {}  # Fallback to local if no Redis

    async def check_limit(self, broker: str, endpoint: str, user_id: str = None) -> bool:
        """
        Check if request is within rate limit.

        Args:
            broker: Broker name (smartapi, kite, etc.)
            endpoint: API endpoint category (quotes, historical, instruments)
            user_id: Optional user ID for per-user limiting

        Returns:
            True if request allowed, False if rate limited

        Raises:
            BrokerRateLimitError: If rate limit exceeded
        """
        limit = self.RATE_LIMITS.get(broker, {}).get(endpoint)
        if not limit:
            return True  # No limit defined

        key = f"ratelimit:{broker}:{endpoint}"
        if user_id:
            key += f":{user_id}"

        if self.redis:
            return await self._check_redis(key, limit)
        else:
            return await self._check_local(key, limit)

    async def _check_redis(self, key: str, limit: int) -> bool:
        """Check rate limit using Redis (sliding window)."""
        now = time.time()
        window = 60  # 60 seconds

        # Remove old entries
        await self.redis.zremrangebyscore(key, 0, now - window)

        # Count current requests in window
        count = await self.redis.zcard(key)

        if count >= limit:
            return False

        # Add current request
        await self.redis.zadd(key, {str(now): now})
        await self.redis.expire(key, window)

        return True

    async def _check_local(self, key: str, limit: int) -> bool:
        """Check rate limit using local memory (fallback)."""
        now = time.time()
        window = 60

        if key not in self._local_counters:
            self._local_counters[key] = []

        # Remove old entries
        self._local_counters[key] = [
            t for t in self._local_counters[key]
            if t > now - window
        ]

        if len(self._local_counters[key]) >= limit:
            return False

        self._local_counters[key].append(now)
        return True
```

### 11.3 Token Management

```python
# backend/app/services/brokers/token_manager.py
"""Broker token expiry and refresh management."""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import logging

from app.models import User
from app.services.brokers.exceptions import BrokerAuthenticationError

logger = logging.getLogger(__name__)


class TokenManager:
    """Manage broker token expiry and auto-refresh."""

    # Buffer time before expiry to trigger refresh (minutes)
    REFRESH_BUFFER = {
        'smartapi': 30,   # Refresh 30 min before 8-hour expiry
        'kite': 60,       # Refresh 1 hour before 24-hour expiry
        'upstox': 30,
        'dhan': 30,
        'fyers': 30,
        'paytm': 30,
    }

    async def check_token_expiry(
        self,
        broker: str,
        user_id: UUID,
        db_session
    ) -> bool:
        """
        Check if token is expired or expiring soon.

        Args:
            broker: Broker name
            user_id: User ID
            db_session: Database session

        Returns:
            True if token needs refresh, False otherwise
        """
        # Get credentials from database
        credentials = await self._get_credentials(broker, user_id, db_session)

        if not credentials or not credentials.token_expiry:
            return True  # No token or no expiry = needs refresh

        buffer = self.REFRESH_BUFFER.get(broker, 30)
        expiry_threshold = datetime.utcnow() + timedelta(minutes=buffer)

        return credentials.token_expiry <= expiry_threshold

    async def refresh_token(
        self,
        broker: str,
        user_id: UUID,
        db_session
    ) -> bool:
        """
        Refresh broker token.

        Args:
            broker: Broker name
            user_id: User ID
            db_session: Database session

        Returns:
            True if refresh successful

        Raises:
            BrokerAuthenticationError: If refresh fails
        """
        try:
            if broker == "smartapi":
                from app.services.smartapi_auth import authenticate_smartapi
                return await authenticate_smartapi(user_id, db_session)
            elif broker == "kite":
                # Kite requires OAuth - can't auto-refresh
                logger.warning(f"Kite token expired for user {user_id} - OAuth required")
                return False
            # Add other brokers
            else:
                logger.error(f"Token refresh not implemented for broker: {broker}")
                return False
        except Exception as e:
            logger.error(f"Token refresh failed for {broker}: {e}")
            raise BrokerAuthenticationError(f"Token refresh failed: {e}")

    async def _get_credentials(self, broker: str, user_id: UUID, db_session):
        """Get broker credentials from database."""
        if broker == "smartapi":
            from app.models import SmartAPICredentials
            return await db_session.get(SmartAPICredentials, user_id)
        elif broker == "upstox":
            from app.models import UpstoxCredentials
            return await db_session.get(UpstoxCredentials, user_id)
        # Add other brokers
        return None
```

---

**Next:** See [Part 3: Implementation Guide](./market-data-abstraction-implementation.md) for frontend components, backend endpoints, and the 7-phase implementation roadmap.
