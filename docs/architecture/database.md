# Database Architecture

AlgoChanakya uses PostgreSQL for persistent storage with SQLAlchemy async ORM, and Redis for session caching.

## Database Schema

```
┌──────────────────┐     ┌────────────────────────┐
│      users       │     │   broker_connections   │
├──────────────────┤     ├────────────────────────┤
│ id (PK)          │◄────│ user_id (FK)           │
│ email            │     │ id (PK)                │
│ name             │     │ broker_type            │
│ created_at       │     │ broker_user_id         │
│ updated_at       │     │ access_token           │
└──────────────────┘     │ is_active              │
         │               │ created_at             │
         │               └────────────────────────┘
         │
         ▼
┌──────────────────┐     ┌────────────────────────┐
│    watchlists    │     │ watchlist_instruments  │
├──────────────────┤     ├────────────────────────┤
│ id (PK)          │◄────│ watchlist_id (FK)      │
│ user_id (FK)     │     │ instrument_token (FK)  │
│ name             │     │ position               │
│ created_at       │     └────────────────────────┘
└──────────────────┘              │
                                  │
                                  ▼
                        ┌────────────────────────┐
                        │     instruments        │
                        ├────────────────────────┤
                        │ instrument_token (PK)  │
                        │ exchange_token         │
                        │ tradingsymbol          │
                        │ name                   │
                        │ exchange               │
                        │ instrument_type        │
                        │ segment                │
                        │ lot_size               │
                        │ tick_size              │
                        │ expiry                 │
                        │ strike                 │
                        └────────────────────────┘

┌──────────────────┐     ┌────────────────────────┐
│    strategies    │     │    strategy_legs       │
├──────────────────┤     ├────────────────────────┤
│ id (PK)          │◄────│ strategy_id (FK)       │
│ user_id (FK)     │     │ id (PK)                │
│ name             │     │ instrument_token       │
│ underlying       │     │ tradingsymbol          │
│ share_code       │     │ strike                 │
│ status           │     │ expiry                 │
│ created_at       │     │ contract_type (CE/PE)  │
│ updated_at       │     │ transaction_type       │
└──────────────────┘     │ lots                   │
                         │ entry_price            │
                         │ exit_price             │
                         │ order_id               │
                         │ position_status        │
                         └────────────────────────┘
```

## Models

### User

```python
# app/models/users.py

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=True)  # Optional
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    broker_connections = relationship("BrokerConnection", back_populates="user")
    watchlists = relationship("Watchlist", back_populates="user")
    strategies = relationship("Strategy", back_populates="user")
```

**Notes:**
- Email is optional (supports broker-only users)
- Can have multiple broker connections
- Owns watchlists and strategies

### BrokerConnection

```python
# app/models/broker_connections.py

class BrokerConnection(Base):
    __tablename__ = "broker_connections"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    broker_type = Column(String)  # "zerodha", "upstox", etc.
    broker_user_id = Column(String)  # Kite user ID
    access_token = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="broker_connections")
```

**Notes:**
- Stores broker access tokens
- `is_active` indicates current connection status
- Multiple connections per user supported

### Watchlist

```python
# app/models/watchlists.py

class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="watchlists")
    instruments = relationship("WatchlistInstrument", back_populates="watchlist")
```

### Instrument

```python
# app/models/instruments.py

class Instrument(Base):
    __tablename__ = "instruments"

    instrument_token = Column(Integer, primary_key=True)
    exchange_token = Column(Integer)
    tradingsymbol = Column(String)
    name = Column(String)
    exchange = Column(String)  # NSE, NFO, BFO
    instrument_type = Column(String)  # EQ, FUT, CE, PE
    segment = Column(String)
    lot_size = Column(Integer)
    tick_size = Column(Float)
    expiry = Column(Date, nullable=True)
    strike = Column(Float, nullable=True)
```

**Notes:**
- Populated from Kite instruments dump
- Used for search and watchlist functionality

### Strategy

```python
# app/models/strategies.py

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    underlying = Column(String)  # NIFTY, BANKNIFTY, FINNIFTY
    share_code = Column(String, unique=True, nullable=True)
    status = Column(String, default="open")  # open, closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="strategies")
    legs = relationship("StrategyLeg", back_populates="strategy")
```

### StrategyLeg

```python
# app/models/strategies.py

class StrategyLeg(Base):
    __tablename__ = "strategy_legs"

    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    instrument_token = Column(Integer)
    tradingsymbol = Column(String)
    strike = Column(Float)
    expiry = Column(Date)
    contract_type = Column(String)  # CE, PE
    transaction_type = Column(String)  # BUY, SELL
    lots = Column(Integer)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    order_id = Column(String, nullable=True)
    position_status = Column(String, default="pending")

    strategy = relationship("Strategy", back_populates="legs")
```

## Database Connection

### Async PostgreSQL

```python
# app/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Connection string must use asyncpg driver
DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/db"

engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession)
```

### Alembic Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "add strategy legs"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

**Note:** Alembic uses `psycopg2` driver (sync). The `alembic/env.py` converts the URL automatically.

## Redis Session Storage

```python
# app/database.py

import redis.asyncio as redis

redis_pool = redis.ConnectionPool.from_url(REDIS_URL)

async def get_redis():
    return redis.Redis(connection_pool=redis_pool)
```

### Session Keys

```
session:<jwt_token> → {"user_id": 123, "broker_connection_id": 456}
```

Sessions expire based on `JWT_EXPIRY_HOURS` setting.

## Adding New Models

1. Create model in `backend/app/models/<name>.py`
2. Import in `backend/app/models/__init__.py`
3. Import in `backend/alembic/env.py`
4. Generate migration:
   ```bash
   alembic revision --autogenerate -m "add <name> model"
   ```
5. Review migration file
6. Apply: `alembic upgrade head`

## Production Database

| Service | Host | Port |
|---------|------|------|
| PostgreSQL | 103.118.16.189 | 5432 |
| Redis | 103.118.16.189 | 6379 |

## Related Documentation

- [Overview](overview.md) - System architecture
- [Database Setup](../guides/database-setup.md) - Configuration guide
