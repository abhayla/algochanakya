# ADR-002: Multi-Broker Abstraction Architecture

**Status:** Accepted

**Date:** 2026-01-14

**Decision Makers:** Development Team

## Context

AlgoChanakya needs to support multiple Indian stock brokers to provide users with flexibility and cost optimization. The platform requires:

1. **Market Data Access** - Live prices, historical OHLC, WebSocket ticks for watchlist, option chain, strategy builder
2. **Order Execution** - Placing orders, managing positions, tracking P&L
3. **Broker Diversity** - Support 10+ Indian brokers with varying APIs (Angel One, Zerodha, Upstox, Fyers, etc.)
4. **Cost Optimization** - Many brokers offer free market data but charge for trading APIs
5. **Easy Extensibility** - Adding a new broker should not require changes to existing business logic

### Current Limitations

- Initially built for Zerodha Kite Connect only
- Broker-specific code scattered across routes and services
- Adding a new broker requires code changes throughout the application
- Cannot mix brokers (e.g., use Angel One for free data + Zerodha for order execution)

### Why Multiple Brokers?

Indian broker APIs vary significantly in:
- **Pricing**: Zerodha charges ₹500/month for market data API (₹2K before 2025); many others offer free APIs
- **Data Quality**: Different latency, reliability, and coverage
- **Features**: Not all brokers support all order types or exchanges
- **Account Funding**: Users may have accounts with different brokers

## Decision

We will implement a **dual broker abstraction architecture** with two independent systems:

### 1. Market Data Broker System
**Purpose:** Live prices, historical OHLC, WebSocket ticks, instrument data

**Interface:** `MarketDataBrokerAdapter` (to be created)

**Factory:** `get_market_data_adapter(broker_type, credentials)`

**User Configuration:** Users select their preferred market data provider in settings

### 2. Order Execution Broker System
**Purpose:** Placing orders, managing positions, account margins

**Interface:** `BrokerAdapter` (already exists in `backend/app/services/brokers/base.py`)

**Factory:** `get_broker_adapter(broker_type, credentials)` (already exists)

**User Configuration:** Users select their funded broker account for order execution

### Design Patterns

| Pattern | Usage |
|---------|-------|
| **Abstract Factory** | Broker adapter instantiation based on broker type |
| **Adapter** | Wrap broker-specific APIs behind unified interfaces |
| **Strategy** | Runtime selection of broker implementation |
| **Singleton** | Shared WebSocket ticker services per broker |

### Unified Data Models

All broker adapters convert to/from these broker-agnostic models:

```python
@dataclass
class UnifiedOrder:
    order_id: str
    tradingsymbol: str
    side: OrderSide  # BUY/SELL
    order_type: OrderType  # MARKET/LIMIT/SL/SL-M
    status: OrderStatus  # PENDING/OPEN/COMPLETE/CANCELLED/REJECTED
    # ... other fields

@dataclass
class UnifiedPosition:
    tradingsymbol: str
    quantity: int
    average_price: Decimal
    pnl: Decimal
    # ... other fields

@dataclass
class UnifiedQuote:
    tradingsymbol: str
    last_price: Decimal
    ohlc: Dict[str, Decimal]
    # ... other fields

@dataclass
class NormalizedTick:
    """WebSocket tick data — uses float (not Decimal) for hot-path performance."""
    token: int            # Canonical Kite instrument token
    ltp: float            # Last traded price (rupees, always)
    change: float         # Absolute change from previous close
    change_percent: float # Percentage change
    volume: int
    oi: int               # Open interest (0 for indices)
    ohlc: dict            # {open, high, low, close} — all floats in rupees
    timestamp: float      # time.time()
    broker_type: str      # Source broker ("smartapi", "kite", etc.)
```

> **Note:** The NormalizedTick definition above was the initial design from Phase 1-2.
> The **authoritative definition** is in [ADR-003 v2](003-multi-broker-ticker-architecture.md)
> and [API Reference](../api/multi-broker-ticker-api.md) Section 1, which uses:
> - **Flat OHLC fields** (`open`, `high`, `low`, `close`) instead of nested `ohlc` dict
> - **`Optional[int]` timestamps** (`last_trade_time`, `exchange_timestamp`) instead of single `float timestamp`
> - **No `broker_type` field** (broker source tracked at router level, not in tick data)
> - `to_dict()` method nests OHLC into `{"ohlc": {...}}` for wire format, but the dataclass itself is flat

### Supported Brokers

| Broker | Market Data | Order Execution | Status |
|--------|-------------|----------------|--------|
| **Angel One** (SmartAPI) | ✅ FREE | Planned (Phase 6) | Default for market data |
| **Zerodha** (Kite Connect) | Available (₹500/mo) | ✅ Implemented | Default for orders |
| **Upstox** | FREE | Planned | Phase 5 |
| **Dhan** | FREE (25 trades/mo) | Planned | Phase 5 |
| **Fyers** | FREE | Planned | Phase 5 |
| **Paytm Money** | FREE | Planned | Phase 5 |

**Future Candidates:** Kotak NEO, Samco, Shoonya/Finvasia, Alice Blue, Pocketful, TradeSmart, ICICI Direct Breeze

## Consequences

### Positive

1. **Zero Code Changes for New Brokers**
   - Add new broker by creating adapter class and registering in factory
   - No changes to routes, services, or business logic
   - Faster onboarding of new brokers

2. **Cost Optimization**
   - Users can use free market data providers (Angel One, Upstox, Fyers)
   - Execute orders through their funded broker account
   - Mix-and-match for best pricing (e.g., Angel data + Zerodha orders)

3. **Flexibility**
   - Switch brokers via settings without reinstallation
   - Test different brokers for reliability/latency
   - Fallback to alternative broker if primary fails

4. **Clean Architecture**
   - Business logic completely decoupled from broker APIs
   - Easier to test (mock adapters)
   - Better maintainability

5. **Competitive Advantage**
   - Multi-broker support rare in Indian trading platforms
   - Attracts users locked into specific brokers
   - Future-proof as broker landscape evolves

### Negative

1. **Initial Development Complexity**
   - Requires designing abstract interfaces
   - Need to refactor existing Kite-specific code
   - More files and boilerplate (adapters, factories, mappings)

2. **Symbol/Token Mapping Overhead**
   - Different brokers use different symbol formats (e.g., "NIFTY2540125000CE" vs "NIFTY 25 APR 25000 CE")
   - Different instrument tokens (Kite: 12345678, Angel: 87654321)
   - Need to maintain mapping tables in database

3. **Testing Complexity**
   - Must test against multiple broker sandbox APIs
   - Mock different broker responses in unit tests
   - E2E tests need credentials for multiple brokers

4. **WebSocket Connection Management**
   - Each broker has connection limits
   - Need singleton services to share connections
   - Complex subscription/unsubscription logic

5. **Error Handling Complexity**
   - Broker-specific error codes must be normalized
   - Rate limiting varies by broker
   - Network failures need broker-aware retry logic

### Neutral

1. **Learning Curve**
   - New developers need to understand adapter pattern
   - More files to navigate (base, adapters, factories)
   - Mitigated by clear documentation and examples

2. **Credential Storage**
   - Each broker requires separate credentials table
   - Encryption required for sensitive tokens
   - Already needed for Kite OAuth; not a new problem

## Alternatives Considered

### Alternative 1: Single Unified Broker Interface

**Description:** One `BrokerAdapter` interface handling both market data and order execution.

**Pros:**
- Simpler conceptually (one adapter per broker)
- Less code duplication
- Single credential management

**Cons:**
- Forces users to have same broker for both data and orders
- Cannot optimize costs (use free data + paid orders)
- Broker with good data but poor execution (or vice versa) limits flexibility

**Why rejected:** Cost optimization is a key user need. Most users want free market data provider while keeping their existing funded broker for orders.

### Alternative 2: Hardcoded Broker Support

**Description:** Separate implementation for each broker without abstraction.

**Pros:**
- Fastest initial development
- No abstraction overhead
- Broker-specific optimizations easier

**Cons:**
- Adding a broker requires changes throughout codebase
- Cannot switch brokers without code changes
- Unmaintainable as broker count grows
- Violates Open/Closed Principle

**Why rejected:** Not scalable. With 10+ brokers planned, maintaining separate implementations would be a nightmare.

### Alternative 3: Plugin Architecture

**Description:** Brokers as dynamically loaded plugins (e.g., Python packages).

**Pros:**
- True zero-code-change extensibility
- Community can contribute broker plugins
- Brokers isolated in separate packages

**Cons:**
- Significantly more complex (plugin discovery, loading, sandboxing)
- Security concerns (untrusted plugins)
- Harder to debug
- Overkill for controlled broker list

**Why rejected:** Over-engineered for our use case. We control which brokers are supported; don't need dynamic plugin loading.

### Alternative 4: Third-Party Data Aggregator

**Description:** Use a service like Global Datafeeds or TrueData that aggregates multiple brokers.

**Pros:**
- Single API for all brokers
- No need to maintain multiple adapters
- Professional support and SLA

**Cons:**
- Monthly fees (defeats free API goal)
- Vendor lock-in
- Additional latency (data proxied through aggregator)
- Still need broker-specific order execution

**Why rejected:** Negates the goal of using free broker APIs. Users would still need broker accounts for order execution.

## Implementation Status

### Phase 1: SmartAPI Integration — COMPLETE ✅
- SmartAPI authentication with auto-TOTP
- SmartAPI WebSocket ticker (legacy singleton)
- Historical data fetching via SmartAPI
- Instrument lookup and `TokenManager`

### Phase 2: Market Data Abstraction — COMPLETE ✅
- `MarketDataBrokerAdapter` interface created (`backend/app/services/brokers/market_data/base.py`)
- SmartAPI wrapped in `SmartAPIMarketDataAdapter`
- `KiteMarketDataAdapter` created
- Routes updated to use `get_market_data_adapter()` factory
- `SymbolConverter` for canonical ↔ broker-specific symbols

### Phase 3: Order Execution + Route Refactoring — COMPLETE ✅
- `BrokerAdapter` interface at `backend/app/services/brokers/base.py`
- `KiteAdapter` fully implemented for order execution
- Routes refactored to use `get_broker_adapter()` factory
- Legacy direct `KiteConnect` usage removed from routes

### Phase 4: Ticker/WebSocket Refactoring — PLANNED (ADR-003 v2)
- New 5-component architecture: TickerAdapter + TickerPool + TickerRouter + HealthMonitor + FailoverController
- Replaces legacy singletons (`SmartAPITickerService`, `KiteTickerService`)
- See [ADR-003 v2: Multi-Broker Ticker Architecture](003-multi-broker-ticker-architecture.md)
- [Implementation Guide](../architecture/multi-broker-ticker-implementation.md) | [API Reference](../api/multi-broker-ticker-api.md)

### Phase 5: Additional Broker Adapters — PLANNED
- Upstox, Dhan, Fyers, Paytm Money (market data + ticker adapters)
- ~2 days per broker once Phase 4 infrastructure is in place
- Prioritize by user demand and API quality

### Phase 6: Order Execution Expansion — PLANNED
- `AngelAdapter` for Angel One order execution
- Order adapter stubs for Upstox, Dhan, Fyers, Paytm
- Migrate remaining `get_kite_client()` usages (~40 locations)
- Frontend broker selection UI for order execution

---

## Broker API Comparison Matrix

| Broker | Auth Method | WS Protocol | Price Unit | Symbol Format | Rate Limit | Pricing |
|--------|------------|-------------|------------|---------------|------------|---------|
| **SmartAPI** (Angel One) | Auto-TOTP (3 tokens: jwt, refresh, feed) | Custom binary (big-endian) | Paise (÷100) | `NIFTY27FEB2525000CE` | 1 req/sec | FREE |
| **Kite Connect** (Zerodha) | OAuth 2.0 (access_token) | Custom binary (big-endian) | Paise WS (÷100), Rupees REST | `NIFTY25FEB25000CE` (canonical) | 3 req/sec | FREE personal |
| **Upstox** | OAuth 2.0 (+1yr extended token) | Protobuf over WebSocket | Rupees | `NSE_FO\|12345` (instrument_key) | 25 req/sec | FREE |
| **Dhan** | Static access token (no expiry) | Binary (little-endian) | Rupees | Numeric security_id only | 10 req/sec | FREE (25 trades/mo) |
| **Fyers** | OAuth 2.0 (access_token) | JSON (dual WS: data + orders) | Rupees | `NSE:NIFTY25FEB25000CE` | 10 req/sec | FREE |
| **Paytm Money** | OAuth 2.0 (3 JWTs: access, read, public) | JSON | Rupees | Numeric security_id + exchange | 10 req/sec | FREE |

---

## Symbol Format Conversion Complexity

Ranked from simplest to most complex (all conversions use canonical Kite format as the internal standard):

| Rank | Broker | Conversion | Example | Method |
|------|--------|-----------|---------|--------|
| 1 | **Kite** | Identity (canonical = Kite) | `256265` → `256265` | No conversion needed |
| 2 | **Fyers** | Prefix strip/add | `256265` → `NSE:NIFTY25FEB25000CE` | Prepend `NSE:` + tradingsymbol |
| 3 | **SmartAPI** | Date format rewrite | `256265` → `NIFTY27FEB2525000CE` | Reformat date portion (`DDMONYY` → `YYMON`) |
| 4 | **Upstox** | Instrument key lookup | `256265` → `NSE_FO\|12345` | Lookup in `broker_instrument_tokens` table |
| 5 | **Dhan** | Full CSV mapping | `256265` → `45678` (numeric security_id) | Full instrument master CSV required |
| 6 | **Paytm** | Full CSV mapping | `256265` → `12345` (numeric) + exchange | Full instrument master CSV required |

**Implementation:** `SymbolConverter` handles all conversions. The `broker_instrument_tokens` database table stores pre-computed mappings populated by `TokenManager` from each broker's instrument master file.

---

## Authentication Flow Comparison

| Capability | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|-----------|---------|------|--------|------|-------|-------|
| **Auto-login (no user action)** | ✅ Auto-TOTP | ❌ Requires OAuth | ✅ Extended token (1yr) | ✅ Static token | ✅ Token refresh | ✅ Token refresh |
| **System credentials supported** | ✅ | ❌ (user OAuth only) | ✅ | ✅ | ✅ | ✅ |
| **Token lifetime** | ~24h (jwt), 15d (refresh) | ~6h (access_token) | 1 year (extended) | No expiry | ~24h | ~24h |
| **Auto-refresh possible** | ✅ (via refresh token) | ❌ (manual re-auth) | ✅ (1yr token) | N/A (no expiry) | ✅ | ✅ |
| **Credentials needed** | API key, client ID, MPIN/TOTP secret | API key, API secret, request_token | API key, API secret, redirect_uri | Client ID, access token | App ID, secret, redirect_uri | API key, secret, request_token |
| **WS auth method** | jwt + feed_token | access_token | Bearer token in URL | access_token + client_id | `app_id:access_token` | public_access_token |

**System Credential Strategy:** SmartAPI (auto-TOTP, refresh loop) and Dhan (static token, never expires) are the easiest for system-level credentials. Kite is the notable exception — requires per-user OAuth, so the system falls back to using the first connected user's token for shared ticker data.

---

## WebSocket Protocol Details

| Feature | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|---------|---------|------|--------|------|-------|-------|
| **Protocol** | Custom binary | Custom binary | Protobuf | Custom binary | JSON | JSON |
| **Byte order** | Big-endian | Big-endian | N/A (protobuf) | Little-endian | N/A (JSON) | N/A (JSON) |
| **Parser needed** | `struct.unpack('>...')` | KiteTicker library | `protobuf` library | `struct.unpack('<...')` | `json.loads()` | `json.loads()` |
| **Max tokens/conn** | 3000 | 3000 | Unlimited (1 conn) | 100 | 200 | 200 |
| **Max connections** | 3 | 3 | 1 per access_token | 5 | 1 | 1 |
| **Threading model** | Daemon thread + asyncio bridge | KiteTicker thread + asyncio bridge | asyncio-native | Daemon thread | asyncio-native | asyncio-native |
| **Subscription modes** | LTP, Quote, Snap Quote | LTP, Quote, Full | Full only | Ticker (15), Quote (17), Full (21) | LiteMode, FullMode | LTP, OHLCV, Full, Depth |
| **Heartbeat** | Server-sent (5s) | Client ping (5s) | Server-sent (30s) | Server-sent (30s) | Client ping (30s) | Server-sent |
| **Reconnect support** | Manual | Auto (built-in) | Manual | Manual | Auto (built-in) | Manual |

**Adapter Threading Pattern:** SmartAPI and Kite use daemon threads with `asyncio.run_coroutine_threadsafe()` to bridge tick callbacks back to the async event loop. Upstox, Fyers, and Paytm are asyncio-native (connect via `websockets` or `aiohttp`). Dhan uses a daemon thread similar to SmartAPI. See [ADR-003 v2 Section 6](003-multi-broker-ticker-architecture.md#6-per-broker-adapter-specifications) for full adapter specs.

---

## Related Decisions

- [ADR-001: Tech Stack Selection](001-tech-stack.md) — FastAPI + Python chosen for async and scipy (relevant for broker API integration)
- [ADR-003 v2: Multi-Broker Ticker Architecture](003-multi-broker-ticker-architecture.md) — New 5-component ticker/WebSocket architecture (Phase 4)

## References

### Broker API Documentation
- [Angel One SmartAPI](https://smartapi.angelbroking.com/docs/)
- [Zerodha Kite Connect](https://kite.trade/docs/connect/v3/)
- [Upstox API](https://upstox.com/developer/api-documentation/)
- [Fyers API](https://myapi.fyers.in/docs/)
- [Dhan API](https://dhanhq.co/docs/v2/)
- [Paytm Money API](https://developer.paytmmoney.com/docs/)

### Architecture Documentation
- [Broker Abstraction Architecture](../architecture/broker-abstraction.md) — Full market data + order execution design
- [Multi-Broker Ticker Implementation Guide](../architecture/multi-broker-ticker-implementation.md) — Phase 4 step-by-step build guide
- [Multi-Broker Ticker API Reference](../api/multi-broker-ticker-api.md) — Full component interface specs
- [WebSocket Architecture](../architecture/websocket.md) — Live prices WebSocket design

### Design Patterns
- [Factory Method Pattern](https://refactoring.guru/design-patterns/factory-method)
- [Adapter Pattern](https://refactoring.guru/design-patterns/adapter)
- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy)

## Success Metrics

1. **Time to Add Broker** — Target: < 2 days (adapter + testing) once Phase 4 infrastructure is complete
2. **Code Changes for New Broker** — Target: 0 changes to existing routes/business logic
3. **User Adoption** — Target: 50% users using different brokers for data vs orders within 6 months
4. **API Cost Savings** — Target: 70% users switch from Kite (₹500/month) to free data providers
5. **Failover Reliability** — Target: < 2s data gap during broker switchover (Phase 4)
