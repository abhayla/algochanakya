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
- **Pricing**: Zerodha charges ₹500/month for market data API (₹2K before 2025); SmartAPI, Fyers, Paytm offer free APIs; Upstox charges ₹499/month
- **Data Quality**: Different latency, reliability, and coverage
- **Features**: Not all brokers support all order types or exchanges
- **Account Funding**: Users may have accounts with different brokers

## Decision

We will implement a **dual broker abstraction architecture** with two independent systems:

### 1. Market Data Broker System (Platform-Default + Optional User Upgrade)
**Purpose:** Live prices, historical OHLC, WebSocket ticks, instrument data

**Interface:** `MarketDataBrokerAdapter` (implemented)

**Factory:** `get_market_data_adapter(broker_type, credentials)`

**Architecture:** Platform-level shared credentials serve ALL users by default (zero setup). Users can optionally upgrade to their own broker API for lower latency, encouraged via persistent banner. See [Working Doc](../architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md).

**Platform Failover Chain:** SmartAPI (primary, FREE) → Dhan (FREE†) → Fyers (FREE) → Paytm (FREE) → Upstox (₹499/mo) → Kite Connect (₹500/mo, last resort)

### 2. Order Execution Broker System
**Purpose:** Placing orders, managing positions, account margins

**Interface:** `BrokerAdapter` (already exists in `backend/app/services/brokers/base.py`)

**Factory:** `get_broker_adapter(broker_type, credentials)` (already exists)

**User Configuration:** Users connect any of 6 brokers for order execution (all supported from Phase 1)

**Auth Fallback Chain:** refresh_token → OAuth re-login → API key/secret (last resort)

### Design Patterns

| Pattern | Usage |
|---------|-------|
| **Abstract Factory** | Broker adapter instantiation based on broker type |
| **Adapter** | Wrap broker-specific APIs behind unified interfaces |
| **Strategy** | Runtime selection of broker implementation |
| **Singleton** | Shared WebSocket ticker services per broker |

### Unified Data Models

All broker adapters convert to/from: `UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote`, `NormalizedTick`.

**Complete model definitions:** [Broker Abstraction Architecture](../architecture/broker-abstraction.md) | [TICKER-DESIGN-SPEC.md](TICKER-DESIGN-SPEC.md) (for NormalizedTick with Decimal precision)

### Supported Brokers

**Snapshot at decision time (Feb 2026) — see [broker-abstraction.md](../architecture/broker-abstraction.md) for current status:**

| Broker | Market Data | Orders | Platform Data Role | Order Status |
|--------|-------------|--------|-------------------|--------------|
| **Angel One** (SmartAPI) | ✅ FREE | ✅ FREE | #1 Primary | Phase 1 |
| **Dhan** | ✅ FREE† | ✅ FREE | #2 Fallback | Phase 1 |
| **Fyers** | ✅ FREE | ✅ FREE | #3 Fallback | Phase 1 |
| **Paytm Money** | ✅ FREE | ✅ FREE | #4 Fallback | Phase 1 |
| **Upstox** | ₹499/mo | ₹499/mo | #5 Fallback | Phase 1 |
| **Zerodha** (Kite Connect) | ₹500/mo* | ✅ FREE | #6 Last Resort | ✔️ Production |

*Kite Personal API is FREE (orders only, no market data). Connect API with data costs ₹500/mo.
†Dhan Trading API is FREE. Data API requires 25 F&O trades/mo OR ₹499/mo subscription.

**Future Candidates:** Kotak NEO, Samco, Shoonya/Finvasia, Alice Blue, Pocketful, TradeSmart, ICICI Direct Breeze

## Consequences

### Positive

1. **Zero Code Changes for New Brokers**
   - Add new broker by creating adapter class and registering in factory
   - No changes to routes, services, or business logic
   - Faster onboarding of new brokers

2. **Cost Optimization**
   - Platform provides free market data to all users (SmartAPI primary, multi-broker failover)
   - Users connect any of 6 brokers for order execution (most free; Upstox ₹499/mo)
   - Users can optionally upgrade to own broker API for lower latency (free for SmartAPI, Fyers, Dhan, Paytm; ₹499/mo for Upstox)

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

**Why rejected:** Platform needs separate market data (platform-default, shared) and order execution (per-user). Users can independently choose data source and order broker. Single interface prevents this flexibility.

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

**Snapshot at decision time (Jan 2026):** Phases 1-3 complete.

**Current status:** [Broker Abstraction Architecture - Implementation Status](../architecture/broker-abstraction.md) | [backend/CLAUDE.md - Implementation Status](../../backend/CLAUDE.md#current-implementation-status)

---

## Broker API Technical Details

The following tables document broker API characteristics used during the design decision. For the most current comparison, see [Broker Abstraction Architecture](../architecture/broker-abstraction.md).

### Broker API Comparison Matrix

| Broker | Auth Method | WS Protocol | Price Unit | Symbol Format | Rate Limit | Pricing |
|--------|------------|-------------|------------|---------------|------------|---------|
| **SmartAPI** (Angel One) | Auto-TOTP (3 tokens: jwt, refresh, feed) | Custom binary (big-endian) | Paise (÷100) | `NIFTY27FEB2525000CE` | 1 req/sec | FREE |
| **Kite Connect** (Zerodha) | OAuth 2.0 (access_token) | Custom binary (big-endian) | Paise WS (÷100), Rupees REST | `NIFTY25FEB25000CE` (canonical) | 3 req/sec | FREE (Personal) / ₹500/mo (Connect) |
| **Upstox** | OAuth 2.0 (+1yr extended token) | Protobuf over WebSocket | Rupees | `NSE_FO\|12345` (instrument_key) | 25 req/sec | ₹499/mo |
| **Dhan** | Static access token (no expiry) | Binary (little-endian) | Rupees | Numeric security_id only | 10 req/sec | FREE† (Trading), ₹499/mo (Data) |
| **Fyers** | OAuth 2.0 (access_token) | JSON (dual WS: data + orders) | Rupees | `NSE:NIFTY25FEB25000CE` | 10 req/sec | FREE |
| **Paytm Money** | OAuth 2.0 (3 JWTs: access, read, public) | JSON | Rupees | Numeric security_id + exchange | 10 req/sec | FREE |

### Symbol Format Conversion Complexity

| Rank | Broker | Method |
|------|--------|--------|
| 1 | **Kite** | Identity (canonical = Kite) |
| 2 | **Fyers** | Prefix strip/add (`NSE:` + tradingsymbol) |
| 3 | **SmartAPI** | Date format rewrite (`DDMONYY` → `YYMON`) |
| 4 | **Upstox** | Instrument key lookup (`broker_instrument_tokens` table) |
| 5 | **Dhan** | Full CSV mapping (numeric security_id) |
| 6 | **Paytm** | Full CSV mapping (numeric + exchange) |

**Implementation:** `SymbolConverter` handles all conversions. The `broker_instrument_tokens` database table stores pre-computed mappings populated by `TokenManager`.

### Authentication Flow Comparison

| Capability | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|-----------|---------|------|--------|------|-------|-------|
| **Auto-login** | ✅ Auto-TOTP | ❌ OAuth | ✅ Extended (1yr) | ✅ Static | ✅ Refresh | ✅ Refresh |
| **Token lifetime** | ~24h jwt, 15d refresh | ~6h | 1 year | No expiry | ~24h | ~24h |
| **System credentials** | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |

**Platform Credential Strategy:** SmartAPI primary, Dhan/Upstox easiest fallbacks, Kite last resort. See [Working Doc](../architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md).

### WebSocket Protocol Details

| Feature | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|---------|---------|------|--------|------|-------|-------|
| **Protocol** | Custom binary | Custom binary | Protobuf | Custom binary | JSON | JSON |
| **Byte order** | Big-endian | Big-endian | N/A | Little-endian | N/A | N/A |
| **Max tokens/conn** | 3000 | 3000 | Unlimited | 100 | 5,000 | 200 |
| **Max connections** | 3 | 3 | 1 | 5 | 1 | 1 |
| **Threading** | Daemon + asyncio bridge | KiteTicker + asyncio bridge | asyncio-native | Daemon | asyncio-native | asyncio-native |

---

## Related Decisions

- [ADR-001: Tech Stack Selection](001-tech-stack.md) — FastAPI + Python chosen for async and scipy (relevant for broker API integration)
- [TICKER-DESIGN-SPEC.md](TICKER-DESIGN-SPEC.md) — Current 5-component ticker/WebSocket architecture (Phase 4, Feb 14, 2026)
- ~~[ADR-003 v2: Multi-Broker Ticker Architecture](003-multi-broker-ticker-architecture.md)~~ — Superseded by TICKER-DESIGN-SPEC (historical reference)

## References

### Broker API Documentation
- [Angel One SmartAPI](https://smartapi.angelbroking.com/docs/)
- [Zerodha Kite Connect](https://kite.trade/docs/connect/v3/)
- [Upstox API](https://upstox.com/developer/api-documentation/)
- [Fyers API](https://myapi.fyers.in/docs/)
- [Dhan API](https://dhanhq.co/docs/v2/)
- [Paytm Money API](https://developer.paytmmoney.com/docs/)

### Architecture Documentation
- [Broker Abstraction Architecture](../architecture/broker-abstraction.md) — Full market data + order execution design (updated Feb 16, 2026)
- [Multi-Broker Ticker Implementation Guide](../guides/TICKER-IMPLEMENTATION-GUIDE.md) — Phase 4 step-by-step build guide (current, 3,868 lines)
- [Multi-Broker Ticker API Reference](../api/multi-broker-ticker-api.md) — Full component interface specs (v2.1.0)
- [Ticker Documentation Index](ticker-documentation-index.md) — Navigation guide for all ticker docs
- [WebSocket Architecture](../architecture/websocket.md) — Live prices WebSocket design (legacy)

### Design Patterns
- [Factory Method Pattern](https://refactoring.guru/design-patterns/factory-method)
- [Adapter Pattern](https://refactoring.guru/design-patterns/adapter)
- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy)

## Success Metrics

1. **Time to Add Broker** — Target: < 2 days (adapter + testing) once Phase 4 infrastructure is complete
2. **Code Changes for New Broker** — Target: 0 changes to existing routes/business logic
3. **User Adoption** — Target: 30% users upgrade to own broker API within 6 months (from platform default)
4. **Platform Cost** — Target: ₹0/month (all free brokers in failover chain, Kite Connect only as absolute last resort)
5. **Failover Reliability** — Target: < 2s data gap during broker switchover (Phase 4)
