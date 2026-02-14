# Broker Abstraction Architecture

## Vision

AlgoChanakya is designed as a **broker-agnostic platform** where adding a new broker requires **zero code changes** - only configuration and adapter implementation. Users can mix-and-match brokers for cost optimization and reliability.

### Design Principles

1. **Separation of Concerns** - Market data and order execution are independent systems
2. **Abstraction via Interfaces** - All broker-specific logic encapsulated behind common interfaces
3. **Factory Pattern** - Runtime broker selection without conditional logic
4. **Unified Data Models** - Broker-agnostic data structures (UnifiedOrder, UnifiedQuote, NormalizedTick)
5. **Canonical Token Format** - All tokens/symbols use Kite format internally; adapters handle translation

## Two Independent Broker Systems

The platform maintains **two separate broker abstractions** to allow maximum flexibility:

### 1. Market Data Brokers
**Purpose:** Live prices, historical OHLC, WebSocket ticks, instrument data

**REST Interface:** `MarketDataBrokerAdapter` (`backend/app/services/brokers/market_data/market_data_base.py`)
**WebSocket Interface:** `TickerAdapter` (`backend/app/services/brokers/market_data/ticker/adapter_base.py`)
**Factory:** `get_market_data_adapter(broker_type, credentials)`

**Why Separate:** Many brokers offer free market data APIs but charge for trading APIs.

### 2. Order Execution Brokers
**Purpose:** Placing orders, managing positions, account margins

**Interface:** `BrokerAdapter` (`backend/app/services/brokers/base.py`)
**Factory:** `get_broker_adapter(broker_type, credentials)`

**Why Separate:** Order execution requires a funded broker account with per-user OAuth.

## Architecture Diagrams

### Market Data Flow

```
    Frontend (Watchlist, Option Chain, Strategy Builder)
                          │
                          ▼
              ┌───────────────────────┐
              │  MarketDataBroker     │
              │      Factory          │
              └───────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  SmartAPI   │   │    Kite     │   │   Upstox    │
│  Adapter    │   │   Adapter   │   │   Adapter   │
│  (Default)  │   │             │   │  (Planned)  │
└─────────────┘   └─────────────┘   └─────────────┘
         │                │                │
         ▼                ▼                ▼
   Angel One API    Zerodha API      Upstox API
     (FREE)         (₹500/mo)          (FREE)
```

### Order Execution Flow

```
    Frontend (Strategy Deploy, Position Exit, AutoPilot)
                          │
                          ▼
              ┌───────────────────────┐
              │    OrderBroker        │
              │      Factory          │
              └───────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│    Kite     │   │   Angel     │   │   Upstox    │
│   Adapter   │   │   Adapter   │   │   Adapter   │
│(Implemented)│   │  (Planned)  │   │  (Planned)  │
└─────────────┘   └─────────────┘   └─────────────┘
```

### Example: Completely FREE Setup

```
  market_data_broker: "smartapi"  ← FREE data from Angel One
  order_broker: "kite"            ← FREE orders via Zerodha Personal API
  Result: ₹0/month
```

---

## Supported Brokers — Comprehensive Comparison

### Broker API Comparison Matrix

| Broker | API Name | Auth Method | WS Protocol | Price Unit | Symbol Format | Rate Limit | Market Data | Orders | Status |
|--------|----------|-------------|-------------|------------|---------------|------------|-------------|--------|--------|
| **Angel One** | SmartAPI | Auto-TOTP (3 tokens) | Custom binary (big-endian) | Paise (÷100) | `NIFTY27FEB2525000CE` | 1/sec | FREE | FREE | Default for data |
| **Zerodha** | Kite Connect | OAuth 2.0 | Custom binary (big-endian) | Paise WS (÷100) | `NIFTY25FEB25000CE` (canonical) | 3/sec | ₹500/mo | FREE | Orders only |
| **Upstox** | Upstox API | OAuth 2.0 (+1yr ext) | Protobuf | Rupees | `NSE_FO\|12345` | 25/sec | FREE | FREE | Planned |
| **Dhan** | DhanHQ API | Static token | Little-endian binary | Rupees | Numeric ID only | 10/sec | FREE (25 trades/mo) | FREE | Planned |
| **Fyers** | Fyers API | OAuth 2.0 | JSON (dual WS) | Rupees | `NSE:NIFTY25FEB25000CE` | 10/sec | FREE | FREE | Planned |
| **Paytm** | Open API | OAuth 2.0 (3 JWTs) | JSON | Rupees | Numeric ID + exchange | 10/sec | FREE | FREE | Planned |

### Per-Broker API Details

#### Angel One (SmartAPI) — Default Market Data

- **REST Base URL**: `https://apiconnect.angelbroking.com`
- **Key Endpoints**: `POST /rest/secure/angelbroking/order/v1/placeOrder`, `GET /rest/secure/angelbroking/order/v1/getLtpData`, `POST /rest/secure/angelbroking/historical/v1/getCandleData`
- **Rate Limits**: 1 request/second overall. Historical: 3/sec.
- **Instrument Master**: `https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json` (JSON, ~50MB)
- **Token Format**: String tokens (e.g., `"99926000"` for NIFTY index). Options use symbol-based lookup.
- **Auth Flow**: Client ID + PIN + TOTP → `POST /rest/auth/angelbroking/user/v1/loginByPassword` → returns `jwtToken`, `refreshToken`, `feedToken`
- **Pricing**: Completely FREE (all APIs)

#### Zerodha (Kite Connect) — Default Order Execution

- **REST Base URL**: `https://api.kite.trade`
- **Key Endpoints**: `POST /orders/{variety}`, `GET /portfolio/positions`, `GET /market-data/quote`, `GET /instruments/historical/{token}/{interval}`
- **Rate Limits**: 3 requests/second for orders. 1/sec for quotes. 3/sec for historical.
- **Instrument Master**: `https://api.kite.trade/instruments` (CSV, ~10MB)
- **Token Format**: Integer tokens (e.g., `256265` for NIFTY). This is the **canonical format**.
- **Auth Flow**: API key + redirect URL → browser OAuth → callback with `request_token` → `POST /session/token` → `access_token`
- **Pricing**: "Personal" tier: FREE (orders only). "Connect" tier: ₹500/month (market data + orders).

#### Upstox

- **REST Base URL**: `https://api.upstox.com/v2`
- **Key Endpoints**: `POST /order/place`, `GET /portfolio/positions`, `GET /market-quote/quotes`, `GET /historical-candle/{instrument_key}/{interval}/{to_date}`
- **Rate Limits**: 25 requests/second
- **Instrument Master**: `https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz`
- **Token Format**: `NSE_FO|{instrument_token}` (instrument_key format)
- **Auth Flow**: OAuth 2.0. Extended token valid ~1 year (simplifies system credentials).
- **Pricing**: FREE

#### Dhan

- **REST Base URL**: `https://api.dhan.co/v2`
- **Key Endpoints**: `POST /orders`, `GET /positions`, `GET /marketfeed/ltp`, `GET /charts/historical`
- **Rate Limits**: 10 requests/second per endpoint
- **Instrument Master**: `https://images.dhan.co/api-data/api-scrip-master.csv` (CSV)
- **Token Format**: Numeric `security_id` only — requires full CSV mapping to convert
- **Auth Flow**: Static API token from dashboard. Never expires unless revoked.
- **Pricing**: FREE if 25+ F&O trades/month, otherwise ₹499/month + taxes

#### Fyers

- **REST Base URL**: `https://api-t1.fyers.in/api/v3`
- **Key Endpoints**: `POST /orders/sync`, `GET /positions`, `GET /data/quotes`, `GET /data/history`
- **Rate Limits**: 10 requests/second
- **Instrument Master**: `https://public.fyers.in/sym_details/{exchange}.csv`
- **Token Format**: `NSE:{symbol}` prefix (e.g., `NSE:NIFTY50-INDEX`). Strip `NSE:` for canonical.
- **Auth Flow**: OAuth 2.0. `{app_id}:{access_token}` for WS auth.
- **Pricing**: FREE

#### Paytm Money

- **REST Base URL**: `https://developer.paytmmoney.com`
- **Key Endpoints**: `POST /accounts/v2/order/place`, `GET /accounts/v1/positions`, `GET /accounts/v1/scrip/margins`
- **Rate Limits**: 10 requests/second
- **Instrument Master**: Available via API call
- **Token Format**: `{exchange_segment}.{exchange_type}!{security_id}` (RIC format). Numeric security_id requires lookup.
- **Auth Flow**: OAuth 2.0 with 3 JWTs (access_token for REST, read_access_token for portfolio, public_access_token for WS).
- **Pricing**: FREE

---

## Symbol/Token Mapping

### Canonical Format

All internal code uses **Kite format** as the canonical symbol/token format:
- **Tokens**: Integer (e.g., `256265` for NIFTY)
- **Symbols**: `NIFTY25FEB25000CE` format

### Conversion Complexity Ranking

| Rank | Broker | Conversion | Difficulty |
|------|--------|-----------|------------|
| 1 | **Kite** | Identity (canonical = Kite) | None |
| 2 | **Fyers** | Strip `NSE:` prefix | Trivial |
| 3 | **SmartAPI** | Reformat date: `DDMONYY` → `YYMON` | Simple string transform |
| 4 | **Upstox** | `NSE_FO\|{token}` — instrument_key lookup | Requires instrument master |
| 5 | **Dhan** | Numeric `security_id` only | Full CSV mapping required |
| 6 | **Paytm** | `{seg}.{type}!{security_id}` (RIC) | Full CSV mapping required |

### Implementation

- **Table**: `broker_instrument_tokens` — maps canonical symbol ↔ broker-specific tokens
- **Service**: `TokenManager` (`backend/app/services/brokers/market_data/token_manager.py`) — handles lookups with caching
- **Service**: `SymbolConverter` (`backend/app/services/brokers/market_data/symbol_converter.py`) — string conversion rules

```python
from app.services.brokers.market_data.token_manager import token_manager

# Canonical → broker token
broker_token = await token_manager.get_broker_token("NIFTY 26 DEC 24000 CE", "smartapi")
# Returns: "99926000" (for index) or "12345" (from DB lookup)

# Broker token → canonical
canonical = await token_manager.get_canonical_symbol(256265, "smartapi")
```

---

## Error Handling Matrix

Broker-specific errors are normalized to the exception hierarchy in `backend/app/services/brokers/market_data/exceptions.py`:

| Exception | SmartAPI Code | Kite Exception | Upstox HTTP | Dhan HTTP | Fyers Code |
|-----------|--------------|----------------|-------------|-----------|------------|
| `RateLimitError` | AG8001 | HTTP 429 | HTTP 429 | HTTP 429 | -1 (check message) |
| `AuthenticationError` | AG8002 (invalid session) | `TokenException` | HTTP 401 | HTTP 401 | -16 |
| `InvalidSymbolError` | AG8003 | `InputException` | HTTP 400 | HTTP 400 | -1 |
| `BrokerAPIError` | Other AG* codes | `NetworkException` | HTTP 5xx | HTTP 5xx | -1 |
| `ConnectionError` | WS disconnect | WS close | WS close | WS close | WS close |

Adapters catch broker-specific exceptions and re-raise as the appropriate normalized exception.

---

## Rate Limiting

Market data adapters enforce per-broker rate limits via `RateLimiter` (`backend/app/services/brokers/market_data/rate_limiter.py`):

| Broker | REST Limit | WS Subscription Limit | Connection Limit |
|--------|-----------|----------------------|-----------------|
| SmartAPI | 1 req/sec | 3000 tokens | 3 connections |
| Kite | 3 req/sec | 3000 tokens | 3 connections |
| Upstox | 25 req/sec | Unlimited (1 connection) | 1 per token |
| Dhan | 10 req/sec | 100 tokens/connection | 5 connections |
| Fyers | 10 req/sec | 200 symbols | Variable |
| Paytm | 10 req/sec | 200 instruments | Variable |

Rate limiting is automatic — adapters handle this internally. **Never bypass the adapter to avoid rate limiting** — it will cause API bans.

---

## Broker Name Mismatch (Known Issue)

`BrokerConnection.broker` column stores display names (`"zerodha"`, `"angelone"`) while `BrokerType` enum uses different values (`"kite"`, `"angel"`).

**Mapping**:
- `"zerodha"` → `BrokerType.KITE`
- `"angelone"` → `BrokerType.ANGEL`

**Plan**: Alembic migration to normalize `broker_connections.broker` values. Until then, use `broker_name_mapper.py` utility:

```python
from app.services.brokers.broker_name_mapper import get_broker_type
broker_type = get_broker_type("zerodha")  # Returns BrokerType.KITE
```

---

## Current Implementation Status

### Phase 1-3: COMPLETE (Jan 2026)

| Component | Status | Files |
|-----------|--------|-------|
| Order execution abstraction | ✅ | `brokers/base.py`, `brokers/factory.py`, `brokers/kite_adapter.py` |
| Market data REST abstraction | ✅ | `market_data/market_data_base.py`, `market_data/factory.py`, `market_data/smartapi_adapter.py` |
| Token/symbol mapping | ✅ | `market_data/token_manager.py`, `market_data/symbol_converter.py` |
| Rate limiting | ✅ | `market_data/rate_limiter.py` |
| Route refactoring | ✅ | All routes use `get_market_data_adapter()` / `get_broker_adapter()` |
| KiteMarketDataAdapter | ✅ | `market_data/kite_adapter.py` |

### Phase 4: NEW ARCHITECTURE (ADR-003 v2) — Ticker/WebSocket Refactoring

| Component | Status | Files |
|-----------|--------|-------|
| TickerAdapter ABC | 📋 Planned | `ticker/adapter_base.py` |
| TickerPool | 📋 Planned | `ticker/pool.py` |
| TickerRouter | 📋 Planned | `ticker/router.py` |
| HealthMonitor | 📋 Planned | `ticker/health.py` |
| FailoverController | 📋 Planned | `ticker/failover.py` |
| SystemCredentialManager | 📋 Planned | `ticker/credential_manager.py` |
| SmartAPITickerAdapter | 📋 Planned | `ticker/adapters/smartapi.py` |
| KiteTickerAdapter | 📋 Planned | `ticker/adapters/kite.py` |
| websocket.py refactor (495→~90 lines) | 📋 Planned | `api/routes/websocket.py` |

See: [ADR-003 v2](../decisions/003-multi-broker-ticker-architecture.md) | [Implementation Guide](./multi-broker-ticker-implementation.md) | [API Reference](../api/multi-broker-ticker-api.md)

### Phase 5: Additional Broker Adapters

- Upstox, Dhan, Fyers, Paytm ticker adapters (stubs → full implementation)
- Per-broker instrument master download + token mapping population

### Phase 6: Order Execution Expansion

- `AngelAdapter` for Angel One order execution
- Stub order adapters for Upstox, Dhan, Fyers, Paytm
- Migrate ~40 `get_kite_client()` usages to broker-agnostic adapter methods
- Frontend broker selection UI completion

---

## Unified Data Models

All broker adapters convert broker-specific responses to these unified models:

### UnifiedOrder
```python
@dataclass
class UnifiedOrder:
    order_id: str              # Broker's order ID
    tradingsymbol: str         # NFO symbol (e.g., "NIFTY2540125000CE")
    exchange: str              # "NFO", "NSE", etc.
    side: OrderSide            # BUY/SELL
    order_type: OrderType      # MARKET/LIMIT/SL/SL-M
    product: ProductType       # NRML/MIS
    quantity: int
    price: Optional[Decimal]
    status: OrderStatus        # PENDING/OPEN/COMPLETE/CANCELLED/REJECTED
    filled_quantity: int
    average_price: Optional[Decimal]
```

### UnifiedPosition
```python
@dataclass
class UnifiedPosition:
    tradingsymbol: str
    exchange: str
    product: ProductType
    quantity: int              # Net quantity (can be negative)
    average_price: Decimal
    last_price: Decimal
    pnl: Decimal              # Realized + Unrealized P&L
```

### NormalizedTick (NEW — ADR-003 v2)
```python
@dataclass(slots=True)
class NormalizedTick:
    token: int              # Canonical instrument token (Kite format)
    ltp: float              # Last traded price (₹, NOT paise)
    change: float           # Change from previous close
    change_percent: float
    volume: int
    oi: int
    open: float
    high: float
    low: float
    close: float
```

Full definitions in `backend/app/services/brokers/base.py` and `ticker/models.py`.

---

## Adding a New Broker

### For Market Data (REST)

1. Create adapter in `backend/app/services/brokers/market_data/{broker}_adapter.py` implementing `MarketDataBrokerAdapter`
2. Register in `market_data/factory.py`
3. Add credentials table if needed + migration
4. Update frontend settings dropdown

### For Market Data (WebSocket / Ticker)

1. Create adapter in `backend/app/services/brokers/market_data/ticker/adapters/{broker}.py` implementing `TickerAdapter`
2. Register in `TickerPool.ADAPTER_MAP`
3. Add system credentials config + DB record
4. Extend `SymbolConverter` with broker-specific conversion rules
5. Populate `broker_instrument_tokens` table via instrument master download

**Zero changes** to routes, TickerPool, TickerRouter, HealthMonitor, or FailoverController.

### For Order Execution

1. Create adapter in `backend/app/services/brokers/{broker}_adapter.py` implementing `BrokerAdapter`
2. Register in `brokers/factory.py`
3. Add OAuth flow in `auth.py`
4. Update frontend settings dropdown

---

## Authentication Flow Comparison

| Broker | Auth Type | System Cred Support | Auto-Login | Token Lifetime |
|--------|-----------|-------------------|------------|----------------|
| SmartAPI | Auto-TOTP (3 tokens) | Yes | Yes (auto-TOTP) | Until 5 AM IST |
| Kite | OAuth 2.0 | No (user only) | No (browser required) | 1 trading day |
| Upstox | OAuth 2.0 + extended token | Yes | Yes (extended ~1yr) | ~1 year |
| Dhan | Static API token | Yes | Yes (never expires) | Never |
| Fyers | OAuth 2.0 | Yes | Partial (refresh token) | Until midnight IST |
| Paytm | OAuth 2.0 (3 JWTs) | Yes | Partial (refresh token) | 1 trading day |

---

## WebSocket Protocol Details

| Broker | WS Protocol | Binary? | Parser Complexity | Connection Limits |
|--------|------------|---------|-------------------|-------------------|
| SmartAPI | Custom binary (big-endian) | Yes | Medium (SmartWebSocketV2 library handles) | 3000 tokens, 3 connections |
| Kite | Custom binary (big-endian) | Yes | Medium (KiteTicker library handles) | 3000 tokens, 3 connections |
| Upstox | Protobuf | Yes | High (requires proto definition) | 1 connection per token |
| Dhan | Little-endian binary | Yes | High (manual `struct.unpack('<...')`) | 100 tokens/conn, 5 connections |
| Fyers | JSON | No | Low (simplest) | 200 symbols |
| Paytm | JSON | No | Low | 200 instruments |

---

## Testing Strategy

### Unit Tests
- Mock broker APIs using `unittest.mock`
- Test adapter conversion logic (broker-specific → unified models)
- Test ref-counting in TickerPool
- Test health score calculation

### Integration Tests
- Test against broker sandbox/test APIs
- Test WebSocket subscribe → tick flow → unsubscribe
- Test failover sequence end-to-end

### E2E Tests
- Test broker selection in Settings UI
- Test tick display in Watchlist, Option Chain
- Test failover notification in frontend

---

## Key Design Decisions

### Why Two Separate Systems?
**Alternative**: Single unified broker interface handling both data and orders.
**Rejected**: Forces users to have same broker for both concerns, limiting cost optimization.
**Chosen**: Two separate systems — most users want free data provider + their funded broker for orders.

### Why Factory Pattern?
**Alternative**: Dependency injection container.
**Rejected**: Overkill for Python/FastAPI.
**Chosen**: Simple factory with broker type enum — Pythonic, easy to understand.

### Why `float` for Tick Prices (not `Decimal`)?
**Alternative**: `Decimal` for precision.
**Rejected**: Ticks are display-only, not used for order pricing. `Decimal` is 10-50x slower on the hot path (thousands of ticks/sec).
**Chosen**: `float` with `round()` for display. Order pricing uses `Decimal` via `UnifiedOrder`.

---

## Related Documentation

- [ADR-002: Multi-Broker Abstraction](../decisions/002-broker-abstraction.md) — Decision rationale
- [ADR-003 v2: Multi-Broker Ticker Architecture](../decisions/003-multi-broker-ticker-architecture.md) — Ticker/WebSocket design
- [Multi-Broker Ticker Implementation Guide](./multi-broker-ticker-implementation.md) — Step-by-step build guide
- [Multi-Broker Ticker API Reference](../api/multi-broker-ticker-api.md) — Full interface specs
- [WebSocket Architecture](./websocket.md) — Connection flow and message protocol
- [Authentication Architecture](./authentication.md) — Broker OAuth/credential storage
- [Database Schema](./database.md) — Broker-related tables

## References

- [Angel One SmartAPI Docs](https://smartapi.angelbroking.com/docs/)
- [Zerodha Kite Connect Docs](https://kite.trade/docs/connect/v3/)
- [Upstox API Docs](https://upstox.com/developer/api-documentation/)
- [Fyers API Docs](https://api-docs.fyers.in/)
- [Dhan API Docs](https://dhanhq.co/docs/v2/)
- [Paytm Money API Docs](https://developer.paytmmoney.com/)
