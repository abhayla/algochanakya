# ADR-003: Multi-Broker Ticker Architecture

**Status:** Proposed

**Date:** 2026-02-13

**Decision Makers:** Development Team

**Supersedes:** Legacy singleton ticker services (smartapi_ticker.py, kite_ticker.py)

## Context

AlgoChanakya currently uses WebSocket connections for real-time market data (live prices, ticks) with two hardcoded global singletons:
- `smartapi_ticker_service` (SmartAPI WebSocket V2)
- `kite_ticker_service` (Kite Ticker WebSocket)

### Current Architecture Problems

1. **Hardcoded Broker Logic**: `websocket.py` has 534 lines with hardcoded if/else branches for SmartAPI vs Kite
2. **Token Mapping Scattered**: `KITE_TO_SMARTAPI_INDEX` mapping hardcoded in route (lines 32-43)
3. **No Lifecycle Management**: Singletons always alive, consuming resources even when unused
4. **Dead Interface**: `TickerService` base class exists but is never inherited; method signatures don't match reality
5. **No Multi-Tenancy**: Cannot serve multiple users with different broker preferences efficiently
6. **System Credentials Missing**: No concept of app-level broker credentials (uses per-user workaround)
7. **Blocks Platform Goal**: Adding a new broker requires extensive route modifications

### Current Two-Tier Architecture Goal

The platform has a two-tier architecture for broker access:

#### Tier 1: Market Data (Shared App-Level)
- **Goal**: App owner's broker APIs serve ALL users
- **Implementation**: One shared WebSocket per broker (e.g., one SmartAPI connection for all users)
- **User Requirement**: Users don't need their own broker credentials for market data
- **Why**: Cost optimization - one ₹500/month Kite subscription OR free SmartAPI can serve unlimited users

#### Tier 2: Order Execution (Per-User)
- **Goal**: Each user logs in with THEIR OWN broker credentials
- **Implementation**: Per-user broker connections for order placement
- **User Requirement**: Users must authenticate with their broker (OAuth/TOTP)
- **Why**: Legal/compliance - orders must be placed from user's own account

### Why This Blocks Multi-Broker Support

The current hardcoded singletons make it impossible to:
- Add new market data brokers (Upstox, Dhan, Fyers) without route changes
- Switch market data sources dynamically per user preference
- Implement Tier 1 properly (app-level shared credentials)
- Reuse the same pattern for order execution brokers (Tier 2)

## Decision

We will implement a **Ticker Service Manager (Multiton)** pattern with broker adapter wrappers to enable true multi-broker support for both Tier 1 (market data) and Tier 2 (order execution).

### Core Components

#### 1. New Interface: `MultiTenantTickerService`

Replaces the dead `TickerService` interface with a multi-tenant-aware contract:

```python
class MultiTenantTickerService(ABC):
    async def connect(self, **credentials) -> None
    async def disconnect(self) -> None
    async def subscribe(tokens: List[int], user_id: str, exchange: str, mode: str)
    async def unsubscribe(tokens: List[int], user_id: str, exchange: str)
    async def register_client(user_id: str, websocket: WebSocket)
    async def unregister_client(user_id: str)
    def get_latest_tick(token: int) -> Optional[NormalizedTick]

    @property
    def is_connected(self) -> bool
    @property
    def client_count(self) -> int
    @property
    def broker_type(self) -> str
```

**Key Differences from Dead `TickerService`**:
- Adds `user_id` parameter to all subscription methods
- Adds `exchange` parameter for broker-specific requirements
- Adds client management (`register_client`, `unregister_client`, `client_count`)
- Uses direct WebSocket broadcasting instead of callback pattern
- Returns `NormalizedTick` dataclass instead of `UnifiedQuote`

#### 2. Normalized Tick Model

```python
@dataclass
class NormalizedTick:
    token: int              # CANONICAL (Kite format)
    ltp: float
    change: float
    change_percent: float
    volume: int
    oi: int
    open: float
    high: float
    low: float
    close: float
    last_trade_time: Optional[int] = None
    exchange_timestamp: Optional[int] = None
```

**Design Choice**: Use dataclass instead of `UnifiedQuote` because:
- Simpler model focused only on tick data (no complex order/position fields)
- Faster serialization for high-frequency tick broadcasting
- Clearer separation between market data (ticks) and execution data (quotes)

#### 3. Ticker Service Manager (Multiton)

```python
class TickerServiceManager:
    _instances: Dict[str, MultiTenantTickerService] = {}
    _locks: Dict[str, asyncio.Lock] = {}

    _TICKER_ADAPTERS = {
        "smartapi": "...SmartAPITickerAdapter",
        "kite": "...KiteTickerAdapter",
        "upstox": "...UpstoxTickerAdapter",
        "dhan": "...DhanTickerAdapter",
        "fyers": "...FyersTickerAdapter",
        "paytm": "...PaytmTickerAdapter",
    }

    @staticmethod
    async def get_ticker(broker_type: str) -> MultiTenantTickerService
    @staticmethod
    async def get_primary_ticker(user_id: int, db) -> MultiTenantTickerService
    @staticmethod
    async def connect_ticker(broker_type: str, db)
    @staticmethod
    async def disconnect_ticker(broker_type: str)
    @staticmethod
    async def shutdown_all()
```

**Pattern Choice**: Multiton (one instance per broker) instead of:
- **Factory per request**: Would create duplicate WebSocket connections
- **Full singleton**: Locks us to one broker
- **Multiton**: One shared WebSocket per broker, efficient resource use

#### 4. System Broker Sessions

**New Database Table**: `system_broker_sessions`

```python
class SystemBrokerSession(Base):
    __tablename__ = "system_broker_sessions"

    id = Column(BigInteger, primary_key=True)
    broker = Column(String(20), unique=True)  # smartapi, kite, etc.

    # Dynamic tokens (refreshed periodically)
    jwt_token = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    feed_token = Column(Text, nullable=True)

    # Session metadata
    client_id = Column(String(50), nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    last_auth_at = Column(DateTime(timezone=True))
    last_error = Column(Text, nullable=True)
```

**Why Needed**:
- Stores app-level broker credentials (Tier 1)
- Enables automatic token refresh without manual intervention
- Separates system credentials from user credentials
- Supports the "one shared WebSocket for all users" model

#### 5. System Auth Service

**New Service**: `system_auth_service.py`

```python
async def initialize_system_sessions() -> None
    """Called at app startup from main.py lifespan"""

async def refresh_system_token(broker_type: str, db) -> None
    """Refresh expired system tokens"""

async def get_system_credentials(broker_type: str, db) -> Dict
    """Get current valid tokens for a broker"""
```

**Responsibilities**:
- Authenticate app owner's broker accounts at startup
- Store tokens in `system_broker_sessions` table
- Auto-refresh tokens before expiry
- Called by adapter on WebSocket reconnect/auth failure to refresh tokens
- For SmartAPI: Reuse auto-TOTP logic from `smartapi_auth.py`
- For Kite: Manual OAuth token from .env (no auto-refresh)

#### 6. Ticker Adapter Wrappers

**New Directory**: `backend/app/services/brokers/market_data/tickers/`

Each broker gets an adapter implementing `MultiTenantTickerService`:
- `smartapi_ticker_adapter.py` - Wraps `SmartWebSocketV2`, handles token translation
- `kite_ticker_adapter.py` - Wraps `KiteTicker`, no translation needed
- `upstox_ticker_adapter.py` - Stub (raises NotImplementedError)
- `dhan_ticker_adapter.py` - Stub
- `fyers_ticker_adapter.py` - Stub
- `paytm_ticker_adapter.py` - Stub

**Token Mapping Self-Contained**:
```python
class SmartAPITickerAdapter(MultiTenantTickerService):
    KITE_TO_SMARTAPI_INDEX = {
        256265: {'smartapi_token': '99926000', 'exchange': 'NSE'},  # NIFTY
        260105: {'smartapi_token': '99926009', 'exchange': 'NSE'},  # BANKNIFTY
        257801: {'smartapi_token': '99926037', 'exchange': 'NSE'},  # FINNIFTY
        265:    {'smartapi_token': '99919000', 'exchange': 'BSE'},  # SENSEX
    }
```

**Design Choice**: Token mapping inside adapter instead of route because:
- Each broker has unique token format quirks
- Keeps route broker-agnostic
- Easier to test and maintain
- Follows single responsibility principle

### Route Simplification

**Before** (534 lines):
- Lines 26-27: Direct singleton imports
- Lines 32-43: Token mapping dicts
- Lines 84-110: `get_user_broker_connection()`
- Lines 135-163: `get_smartapi_credentials()`
- Lines 166-244: `fetch_initial_index_quotes()`
- Lines 288-384: Broker selection if/else
- Lines 413-468: Token translation in subscribe

**After** (~150 lines):
```python
@router.websocket("/ws/ticks")
async def websocket_ticks(websocket: WebSocket, token: str):
    async for db in get_db():
        user = await get_user_from_token(token, db)
        ticker_service = await TickerServiceManager.get_primary_ticker(user.id, db)
        break

    await ticker_service.register_client(str(user.id), websocket)

    while True:
        message = await websocket.receive_text()
        data = json.loads(message)

        if data["action"] == "subscribe":
            # Adapter handles ALL translation internally
            await ticker_service.subscribe(
                tokens=data["tokens"],
                user_id=str(user.id),
                exchange=data.get("exchange", "NFO"),
                mode=data.get("mode", "quote")
            )
```

**Result**: 72% reduction in route code, zero broker-specific logic

### Health Monitoring

Extend existing `WebSocketHealthMonitor` with per-broker tracking:

```python
class MultiProviderHealthMonitor:
    _monitors: Dict[str, WebSocketHealthMonitor] = {}

    def get_or_create(self, broker_type: str) -> WebSocketHealthMonitor
    def get_aggregate_health(self) -> Dict[str, Any]
    def get_broker_health(self, broker_type: str) -> Optional[HealthMetrics]
```

Each ticker adapter gets its own health monitor instance.

## Implementation Phases

### Phase 1: Core Infrastructure (~3-4 days)
- Add missing `DHAN`, `PAYTM` to `BrokerType` enum
- Add system broker env vars to `config.py`
- Create `system_broker_sessions` table + migration
- Create `MultiTenantTickerService` interface
- Remove dead WebSocket stubs from `MarketDataBrokerAdapter` in `market_data_base.py` (subscribe, unsubscribe, on_tick, connect, disconnect, is_connected)
- Create `TickerServiceManager` multiton
- Create `SystemAuthService`
- Add broker name mapping utility (`"zerodha"→"kite"`, `"angelone"→"angel"`) + Alembic migration to normalize `broker_connections.broker` column values
- Extend `WebSocketHealthMonitor`

**Milestone**: App boots with new tables, interfaces defined, old tickers still work

### Phase 2: Market Data Adapters (~4-5 days)
- Create `tickers/` subdirectory
- Implement `SmartAPITickerAdapter` (move logic from legacy service)
- Implement `KiteTickerAdapter` (move logic from legacy service)
- Create 4 stub adapters (Upstox, Dhan, Fyers, Paytm)
- Update frontend WebSocket subscribe messages to include `exchange` field (~8 files)
- Refactor `websocket.py` to use manager (534→150 lines)
- Integrate system auth in `main.py` startup
- Deprecate legacy singletons (don't delete yet)

**Milestone**: WebSocket route uses manager, token mapping self-contained

### Phase 3: Order Execution (~1-2 weeks)
- Add `order_execution_broker` column to `UserPreferences`
- Remove `get_kite_client()` from `BrokerAdapter` abstract base class (`base.py:490`)
- Migrate ~40 `get_kite_client()` usages across AutoPilot/AI routes to use `get_broker_adapter()`
- Refactor `BrokerAdapter.__init__` to accept generic credentials dict (currently only `access_token`)
- Add broker name mapping utility: display names ↔ BrokerType values
- Implement `AngelAdapter` (full order execution)
- Create 4 stub order adapters (Upstox, Dhan, Fyers, Paytm)
- Register all in order factory (`backend/app/services/brokers/factory.py`)
- Update `get_broker_adapter_dep()` to read user preference (currently hardcodes `BrokerType.KITE`)
- Add broker name migration: Alembic migration to update `broker_connections.broker` values (`"zerodha"` → `"kite"`, `"angelone"` → `"angel"`)
- Add OAuth flows for new brokers
- Frontend settings UI for broker selection

**Milestone**: Users can select broker for orders (6 options)

## Consequences

### Positive

1. **True Multi-Broker Support**: Add new broker = implement adapter + register in factory (zero route changes)
2. **Resource Efficiency**: WebSockets created on-demand, cleaned up when unused
3. **Tier 1 Properly Implemented**: System credentials separate from user credentials
4. **Maintainability**: Route code reduced 72%, broker logic isolated
5. **Testability**: Each adapter can be unit tested independently
6. **Extensibility**: Same pattern works for Tier 2 (order execution)
7. **Performance**: Token mapping cached inside adapters, faster lookups

### Negative

1. **Migration Complexity**: Need to carefully port threading logic from legacy services
2. **Testing Burden**: 6 broker adapters to test (2 full + 4 stubs initially)
3. **Credential Management**: Need .env variables for 6 brokers
4. **Backward Compatibility**: Keep legacy singletons temporarily during migration period. Grep for imports before final removal.

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SmartAPI threading breaks | HIGH | Port exact `threading.Thread + asyncio.run_coroutine_threadsafe` pattern from `smartapi_ticker.py:132-139` |
| Token refresh race condition | MEDIUM | Per-broker `asyncio.Lock` in manager |
| Token mapping incomplete | MEDIUM | Use `broker_instrument_tokens` table via `TokenManager` as fallback |
| Legacy singleton still imported | LOW | Grep codebase before Phase 2 deployment |
| WebSocket disconnect cascade | MEDIUM | Send "reconnecting" message to clients, auto-resubscribe after reconnect |
| Broker name mismatch in DB | MEDIUM | Add mapping function + data migration. BrokerConnection stores "zerodha"/"angelone" but BrokerType uses "kite"/"angel" |

## Alternatives Considered

### Alternative 1: Keep Singletons, Add Router

**Approach**: Keep `smartapi_ticker_service` and `kite_ticker_service` but add a router function

**Rejected Because**:
- Doesn't solve lifecycle management (singletons always alive)
- Doesn't solve system credentials problem
- Doesn't reduce route complexity significantly
- Can't scale to 6 brokers efficiently

### Alternative 2: Full Factory Pattern (No Manager)

**Approach**: Create new ticker instance per WebSocket connection

**Rejected Because**:
- Creates duplicate WebSocket connections to broker
- Wastes resources (each connection has overhead)
- Violates Tier 1 goal (one shared connection for all users)

### Alternative 3: Hybrid - Singleton Manager + Adapters

**Approach**: Manager itself is singleton, but manages multiple broker instances

**Rejected Because**:
- Adds unnecessary layer of indirection
- Multiton pattern simpler - static methods sufficient
- No state needed in manager itself

### Alternative 4: Keep Token Mapping in Route

**Approach**: Keep `KITE_TO_SMARTAPI_INDEX` in `websocket.py`

**Rejected Because**:
- Route becomes broker-aware (violates abstraction)
- Can't add new brokers without route changes
- Token mapping belongs to broker-specific logic

## References

- [ADR-002: Multi-Broker Abstraction](./002-broker-abstraction.md) - Parent architecture
- [Broker Abstraction Architecture](../architecture/broker-abstraction.md) - Complete technical design
- [Multi-Broker Ticker Implementation Guide](../architecture/multi-broker-ticker-implementation.md) - Step-by-step guide
- [Legacy SmartAPI Ticker](../../backend/app/services/legacy/smartapi_ticker.py) - Reference implementation
- [Legacy Kite Ticker](../../backend/app/services/legacy/kite_ticker.py) - Reference implementation
- [Current WebSocket Route](../../backend/app/api/routes/websocket.py) - To be refactored

## Approval

- [ ] Development Team Review
- [ ] Architecture Review
- [ ] Security Review (system credentials in .env)
- [ ] Testing Strategy Approved
- [ ] Migration Plan Approved
- [ ] Rollback Plan Defined

## Rollback Plan

If implementation fails:

1. **Phase 1 Rollback**: Drop `system_broker_sessions` table, remove new files, no route changes yet
2. **Phase 2 Rollback**: Revert `websocket.py`, reconnect to legacy singletons
3. **Phase 3 Rollback**: Revert `UserPreferences` migration, keep `KiteAdapter` only

**Git Tags**: Tag before each phase deployment for easy rollback

## Notes

- `example_ticker_manager.py` is a reference implementation - delete after Phase 2 complete
- Legacy singletons deprecated but not deleted during migration period. Run grep to confirm zero imports before deletion.
- Old `TickerService` interface at `ticker_base.py` marked deprecated
- SmartAPI auto-TOTP logic reused from `smartapi_auth.py` (no changes needed)
