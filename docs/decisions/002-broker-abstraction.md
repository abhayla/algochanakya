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
```

### Supported Brokers

**Priority 1 (Current):**
- Angel One (SmartAPI) - Market data (in progress)
- Zerodha (Kite Connect) - Order execution (implemented)

**Priority 2 (Next 6 months):**
- Upstox, Fyers, Alice Blue, Dhan

**Priority 3 (Future):**
- Kotak NEO, Samco, Shoonya/Finvasia, Pocketful, TradeSmart, ICICI Direct Breeze

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

## Implementation Plan

### Phase 1: Complete SmartAPI Integration (Current)
- ✅ SmartAPI authentication with auto-TOTP
- ✅ SmartAPI WebSocket ticker
- ✅ Historical data fetching
- ✅ Instrument lookup

### Phase 2: Market Data Abstraction (Next)
- Create `MarketDataBrokerAdapter` interface
- Wrap SmartAPI services in adapter
- Create `KiteMarketDataAdapter`
- Update routes to use factory

### Phase 3: Order Execution Completion
- Create `AngelAdapter` for Angel One orders
- Refactor routes to use `get_broker_adapter()` factory
- Remove hardcoded `KiteOrderService` usage

### Phase 4: Ticker Abstraction
- Create `TickerService` interface
- Implement by existing ticker services
- Unified WebSocket management

### Phase 5: Additional Brokers
- Add Upstox, Fyers, Alice Blue, Dhan (1 per sprint)
- Prioritize by user demand from surveys

## Related Decisions

- [ADR-001: Tech Stack Selection](001-tech-stack.md) - FastAPI + Python chosen for async and scipy (relevant for broker API integration)

## References

### Broker API Documentation
- [Angel One SmartAPI](https://smartapi.angelbroking.com/docs/)
- [Zerodha Kite Connect](https://kite.trade/docs/connect/v3/)
- [Upstox API](https://upstox.com/developer/api-documentation/)
- [Fyers API](https://api-docs.fyers.in/)

### Design Patterns
- [Factory Method Pattern](https://refactoring.guru/design-patterns/factory-method)
- [Adapter Pattern](https://refactoring.guru/design-patterns/adapter)
- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy)

### Market Research
- [Best Brokers with Free APIs in India](https://www.pocketful.in/blog/trading/best-brokers-offering-free-trading-api/)
- [Algo Trading Broker Comparison](https://stratzy.in/blog/best-broker-for-algo-trading-india-hinglish/)

## Success Metrics

1. **Time to Add Broker** - Target: < 2 days (adapter + testing) once abstraction complete
2. **Code Changes for New Broker** - Target: 0 changes to existing routes/business logic
3. **User Adoption** - Target: 50% users using different brokers for data vs orders within 6 months
4. **API Cost Savings** - Target: 70% users switch from Kite (₹500/month) to free data providers
