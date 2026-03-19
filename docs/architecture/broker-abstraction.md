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

### 1. Market Data Brokers (Dual-Path: Platform-Default + Optional User Upgrade)
**Purpose:** Live prices, historical OHLC, WebSocket ticks, instrument data

**REST Interface:** `MarketDataBrokerAdapter` (`backend/app/services/brokers/market_data/market_data_base.py`)
**WebSocket Interface:** `TickerAdapter` (`backend/app/services/brokers/market_data/ticker/adapter_base.py`)
**Factory:** `get_market_data_adapter(broker_type, credentials)`
**Router:** `MarketDataRouter` — Directs to platform-level (default) or user-level (optional upgrade)

**Why Separate:** Many brokers offer free market data APIs but charge for trading APIs.

#### Market Data: Two Modes (Platform-Default Architecture)

All users get market data via platform-level shared credentials by default:

| Mode | Description | Target | Cost |
|------|-------------|--------|------|
| **Platform-Level (Default)** | Shared platform credentials via Redis Pub/Sub. All users get data immediately, zero setup. | All users (default) | ₹0/month |
| **User-Level (Optional Upgrade)** | User connects their own broker API. Dedicated connection, lower latency (~20-50ms), full control. User chooses any supported broker. | Users wanting better performance | Varies by broker (Dhan†, Fyers, Paytm, SmartAPI, Upstox: FREE; Kite: ₹500/mo) |

**Why platform-default works:**
- **Zero friction** — Users get data immediately, no API setup required
- **Mostly FREE brokers** — Platform uses SmartAPI (primary, FREE), Dhan, Fyers, Paytm, Upstox (all FREE fallbacks)
- **Proven scalability** — 1 broker WebSocket → Redis Pub/Sub → 10K+ users
- **Multi-broker failover** — SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite Connect (₹500/mo, last resort)

**Optional user upgrade benefits:**
- Lower latency: ~20-50ms (direct) vs ~50-200ms (shared via Redis)
- Dedicated connection, full control over subscriptions
- Encouraged via persistent banner on all data screens
- Most broker APIs are FREE (SmartAPI, Fyers, Dhan, Paytm) — low cost barrier

**How users configure their own market data API:**
- Navigate to **Settings → Broker API section** for the desired broker
- Enter API credentials (API key, access token, etc.) — these are **stored encrypted** in the database
- Switch the **Market Data Source** dropdown from "Platform Default" to their broker
- These are **API credentials for data access**, NOT login credentials (login credentials are never stored)

See [Working Doc](Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md) for complete dual-path architecture.
See [Authentication Architecture](authentication.md#two-credential-systems-login-vs-market-data-api) for the distinction between login credentials and API credentials.

### 2. Order Execution Brokers (Always Per-User)
**Purpose:** Placing orders, managing positions, account margins

**Interface:** `BrokerAdapter` (`backend/app/services/brokers/base.py`)
**Factory:** `get_broker_adapter(broker_type, credentials)`

**Why Separate:** Order execution requires a funded broker account with per-user OAuth. Always per-user, SEBI-compliant.

## Architecture Diagrams

### Market Data Flow (Dual-Path)

```
    Frontend (Watchlist, Option Chain, Strategy Builder)
                          │
                          ▼
              ┌───────────────────────┐
              │   MarketDataRouter    │
              │  (user pref + creds)  │
              └───────────────────────┘
                    │             │
         ┌─────────┘             └──────────┐
         ▼                                  ▼
┌──────────────────────────┐  ┌──────────────────────┐
│ PLATFORM DEFAULT PATH    │  │ USER UPGRADE PATH    │
│ (All users — default)    │  │ (Optional upgrade)   │
│                          │  │                      │
│ Platform credentials     │  │ User's own broker    │
│ (SmartAPI → Redis →      │  │ API credentials      │
│  fan-out to users)       │  │ → Direct connection  │
│ → ~50-200ms latency      │  │ → ~20-50ms latency   │
└──────────────────────────┘  └──────────────────────┘
         │                                  │
  Failover chain:                    User's choice:
  SmartAPI → Dhan →              Dhan, Fyers,
  Fyers → Paytm →               Kite, Paytm,
  Upstox → Kite(₹500)          SmartAPI, Upstox
```

### Order Execution Flow (All 6 Brokers from Phase 1)

```
    Frontend (Strategy Deploy, Position Exit, AutoPilot)
                          │
                          ▼
              ┌───────────────────────┐
              │    OrderBroker        │
              │      Factory          │
              └───────────────────────┘
                          │
    ┌─────────┬─────────┬─┴───────┬─────────┬─────────┐
    ▼         ▼         ▼         ▼         ▼         ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│ Kite  │ │ Angel │ │Upstox │ │ Dhan  │ │ Fyers │ │Paytm  │
│Adapter│ │Adapter│ │Adapter│ │Adapter│ │Adapter│ │Adapter│
└───────┘ └───────┘ └───────┘ └───────┘ └───────┘ └───────┘

Auth fallback: refresh_token → OAuth re-login → API key/secret
```

### Example: Default Setup (Platform Data — All Users)

```
  market_data: "platform" (shared)   ← Platform SmartAPI credentials (FREE, default)
  order_broker: any of 6 brokers     ← User connects their preferred broker
  Result: ₹0/month, ~50-200ms latency, zero setup for data
```

### Example: Upgraded Setup (User's Own API — Optional)

```
  market_data: "own_api" (SmartAPI)  ← User connects their own FREE SmartAPI
  order_broker: any of 6 brokers     ← Independent choice from data broker
  Result: ₹0/month, ~20-50ms latency, dedicated connection
  → User opted in via persistent upgrade banner
```

---

## Supported Brokers — Comprehensive Comparison

### Broker API Comparison Matrix

| Broker | API Name | Auth Method | WS Protocol | Price Unit | Symbol Format | Rate Limit | Market Data | Orders | Status |
|--------|----------|-------------|-------------|------------|---------------|------------|-------------|--------|--------|
| **Angel One** | SmartAPI | Auto-TOTP (3 tokens) | Custom binary (big-endian) | Paise (÷100) | `NIFTY27FEB2525000CE` | 1/sec | FREE | FREE | Platform primary (#1) |
| **Dhan** | DhanHQ API | Static token | Little-endian binary | Rupees | Numeric ID only | 10/sec | FREE† | FREE | Platform fallback (#2) |
| **Fyers** | Fyers API | OAuth 2.0 | JSON (dual WS) | Rupees | `NSE:NIFTY25FEB25000CE` | 10/sec | FREE | FREE | Platform fallback (#3) |
| **Paytm** | Open API | OAuth 2.0 (3 JWTs) | JSON | Rupees | Numeric ID + exchange | 10/sec | FREE | FREE | Platform fallback (#4) |
| **Upstox** | Upstox API | OAuth 2.0 (+1yr ext) | Protobuf | Rupees | `NSE_FO\|12345` | 50/sec | FREE | FREE | Platform fallback (#5) |
| **Zerodha** | Kite Connect | OAuth 2.0 | Custom binary (big-endian) | Paise WS (÷100) | `NIFTY25FEB25000CE` (canonical) | 3/sec | ₹500/mo | FREE | Platform last resort (#6) |

**Pricing Notes (Updated Feb 16, 2026):**
- **Upstox:** FREE (pricing changed from ₹499/month to free in 2025). All trading + data APIs at no cost.
- **Kite Connect:** ₹500/mo includes market data + historical data (bundled since Feb 2025). Personal API is free but orders only.
- **Dhan:** †Trading API always free. Data API requires 25 F&O trades/month OR ₹499/mo subscription.
- **Fyers:** FREE. v3.0.0 (Feb 2026) upgraded WebSocket capacity from 200 to 5,000 symbols.

### Per-Broker API Details

#### Angel One (SmartAPI) — Primary Platform Market Data

- **REST Base URL**: `https://apiconnect.angelbroking.com`
- **Key Endpoints**: `POST /rest/secure/angelbroking/order/v1/placeOrder`, `GET /rest/secure/angelbroking/order/v1/getLtpData`, `POST /rest/secure/angelbroking/historical/v1/getCandleData`
- **Rate Limits**: 1 request/second overall. Historical: 3/sec.
- **Instrument Master**: `https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json` (JSON, ~50MB)
- **Token Format**: String tokens (e.g., `"99926000"` for NIFTY index). Options use symbol-based lookup.
- **Auth Flow**: Client ID + PIN + TOTP → `POST /rest/auth/angelbroking/user/v1/loginByPassword` → returns `jwtToken`, `refreshToken`, `feedToken`
- **Pricing**: Completely FREE (all APIs)

#### Zerodha (Kite Connect) — Order Execution + Last Resort Platform Data

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
- **Rate Limits**: 50 requests/second
- **Instrument Master**: `https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz`
- **Token Format**: `NSE_FO|{instrument_token}` (instrument_key format)
- **Auth Flow**: OAuth 2.0. Extended token valid ~1 year (simplifies system credentials).
- **Pricing**: **FREE (₹0)** for all trading + data APIs (pricing changed from ₹499/month to free in 2025). Platform-level credentials in `.env` (`UPSTOX_API_KEY`, `UPSTOX_API_SECRET`, etc.) serve as the universal API for backend market data operations — separate from individual user OAuth login.

#### Dhan

- **REST Base URL**: `https://api.dhan.co/v2`
- **Key Endpoints**: `POST /orders`, `GET /positions`, `GET /marketfeed/ltp`, `GET /charts/historical`
- **Rate Limits**: 10 requests/second per endpoint
- **Instrument Master**: `https://images.dhan.co/api-data/api-scrip-master.csv` (CSV)
- **Token Format**: Numeric `security_id` only — requires full CSV mapping to convert
- **Auth Flow**: Static API token from dashboard. Never expires unless revoked.
- **Pricing**: Trading API: FREE. Data API: FREE with 25+ F&O trades/month, otherwise ₹499/month + taxes.

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
| Upstox | 50 req/sec | Unlimited (1 connection) | 1 per token |
| Dhan | 10 req/sec | 100 tokens/connection | 5 connections |
| Fyers | 10 req/sec | 5,000 symbols (v3.0.0) | Variable |
| Paytm | 10 req/sec | 200 instruments | Variable |

Rate limiting is automatic — adapters handle this internally. **Never bypass the adapter to avoid rate limiting** — it will cause API bans.

---

## Broker Name Mismatch (Known Issue)

`BrokerConnection.broker` column stores display names (`"zerodha"`, `"angelone"`) while `BrokerType` enum uses different values (`"kite"`, `"angel"`).

**Mapping**:
- `"zerodha"` → `BrokerType.KITE`
- `"angelone"` → `BrokerType.ANGEL`

**Workaround**: Mapping is currently handled inline in factory functions and adapter code. A dedicated `broker_name_mapper.py` utility is planned. Long-term fix: Alembic migration to normalize `broker_connections.broker` values.

---

## Current Implementation Status

### Phase 1-3: COMPLETE (Jan 2026)

| Component | Status | Files |
|-----------|--------|-------|
| Order execution abstraction | ✅ | `brokers/base.py`, `brokers/factory.py` |
| Order adapters (all 6) | ✅ | `kite_adapter.py`, `angelone_adapter.py`, `upstox_order_adapter.py`, `dhan_order_adapter.py`, `fyers_order_adapter.py`, `paytm_order_adapter.py` |
| Market data REST abstraction | ✅ | `market_data/market_data_base.py`, `market_data/factory.py` |
| Market data adapters (all 6) | ✅ | `smartapi_adapter.py`, `kite_adapter.py`, `upstox_adapter.py`, `dhan_adapter.py`, `fyers_adapter.py`, `paytm_adapter.py` |
| Token/symbol mapping | ✅ | `market_data/token_manager.py`, `market_data/symbol_converter.py` |
| Rate limiting | ✅ | `market_data/rate_limiter.py` |
| Route refactoring | ✅ | All routes use `get_market_data_adapter()` / `get_broker_adapter()` |

### Phase 4: COMPLETE (Feb 2026) — 5-Component Ticker Architecture

| Component | Status | Files |
|-----------|--------|-------|
| TickerAdapter ABC | ✅ | `ticker/adapter_base.py` (236 lines) |
| TickerPool (with integrated credentials) | ✅ | `ticker/pool.py` (341 lines) |
| TickerRouter | ✅ | `ticker/router.py` (326 lines) |
| HealthMonitor | ✅ | `ticker/health.py` (299 lines) |
| FailoverController | ✅ | `ticker/failover.py` (256 lines) |
| Ticker adapters (all 6) | ✅ | `ticker/adapters/smartapi.py`, `kite.py`, `upstox.py`, `dhan.py`, `fyers.py`, `paytm.py` |
| websocket.py refactor (494→292 lines) | ✅ | `api/routes/websocket.py` |
| Test coverage | ✅ | 8 test files, 5,100+ lines |

5-component architecture with integrated credential management in TickerPool. NormalizedTick uses `Decimal` (not `float`) for precision.

See: [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md) | [Implementation Guide](../guides/TICKER-IMPLEMENTATION-GUIDE.md) | [API Reference](../api/multi-broker-ticker-api.md)

**Note:** ~~ADR-003 v2~~ is superseded by TICKER-DESIGN-SPEC.md. The old ADR-003 v2 described a 6-component system with separate SystemCredentialManager - this has been merged into TickerPool.

### Phase 5: COMPLETE (Feb 2026) — All Broker Ticker Adapters

All 6 broker ticker adapters fully implemented (SmartAPI, Kite, Upstox, Dhan, Fyers, Paytm). 3,100+ lines of adapter code total.

### Phase 6: MOSTLY COMPLETE (Mar 2026) — Order Execution All 6 Brokers

| Component | Status | Notes |
|-----------|--------|-------|
| All 6 order adapters | ✅ | Kite, AngelOne, Upstox, Dhan, Fyers, Paytm |
| Factory registration | ✅ | All 6 in `_BROKER_ADAPTERS` dict |
| Auth per broker | ✅ | SmartAPI (PIN+TOTP), Kite (OAuth), Upstox (OAuth ~1yr), Dhan (static), Fyers (OAuth), Paytm (OAuth 3 JWTs) |
| `get_kite_client()` migration | 🔄 In Progress | ~64 usages in 18 files (concentrated in AutoPilot v1 routes + AI services) |
| Frontend broker selection UI | 📋 Planned | Settings page shows Kite+SmartAPI; remaining 4 brokers need UI |

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

### NormalizedTick (Updated Feb 14, 2026)
```python
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

@dataclass(slots=True)
class NormalizedTick:
    token: int                # Canonical instrument token (Kite format)
    ltp: Decimal              # Last traded price (₹, NOT paise)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    change: Decimal           # Change from previous close
    change_percent: Decimal
    volume: int
    oi: int                   # Open interest
    timestamp: datetime
    broker_type: str          # Source broker ("kite", "smartapi", etc.)

    # Optional depth fields
    bid: Optional[Decimal]
    ask: Optional[Decimal]
    bid_qty: Optional[int]
    ask_qty: Optional[int]
```

**Key Changes from Original ADR-003 v2:**
- **`Decimal` instead of `float`** - Eliminates floating-point precision errors for price calculations
- Added `timestamp` - Enables staleness detection
- Added `broker_type` - Tracks tick source for debugging/failover

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
| Fyers | JSON | No | Low (simplest) | 5,000 symbols (v3.0.0) |
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
**Chosen**: Two separate systems — platform provides data to all users by default (mostly FREE brokers) + users connect any of 6 brokers for orders. Users can independently choose data source and order broker.

### Why Platform-Default Market Data? (Updated Feb 16, 2026)
**Alternative**: User-first (encourage all users to connect their own API).
**Rejected**: Adds friction for new users, requires API setup before getting any data.
**Chosen**: Platform-level as default for all users (zero setup). Users can optionally upgrade to their own broker API for better latency — encouraged via persistent banner. Platform uses mostly FREE brokers (SmartAPI primary, multi-broker failover chain; Kite ₹500/mo as the only paid fallback). Benefits: zero-friction onboarding, multi-broker resilience, optional user upgrade path.

### Why Factory Pattern?
**Alternative**: Dependency injection container.
**Rejected**: Overkill for Python/FastAPI.
**Chosen**: Simple factory with broker type enum — Pythonic, easy to understand.

### Why `Decimal` for Tick Prices (Updated Feb 14, 2026)?
**Alternative**: `float` for performance.
**Rejected**: While `float` is faster, it introduces precision errors that compound in calculations (Greeks, P&L, strategy analysis). These errors are unacceptable for financial calculations.
**Chosen**: `Decimal` for all price fields in `NormalizedTick`. Performance impact is negligible with proper optimization (pre-computed constants, batch conversions). Order pricing uses `Decimal` via `UnifiedOrder` for consistency.

**Previous Design (ADR-003 v2):** Used `float` based on display-only assumption. This was incorrect - ticks are used in real-time P&L calculations, option Greeks, and strategy analysis where precision is critical.

---

## Related Documentation

**Current as of Mar 2, 2026:**

- [ADR-002: Multi-Broker Abstraction](../decisions/002-broker-abstraction.md) — Decision rationale
- [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md) — **Current ticker architecture** (5-component design)
- [Multi-Broker Ticker Implementation Guide](../guides/TICKER-IMPLEMENTATION-GUIDE.md) — Step-by-step build guide with complete code
- [Multi-Broker Ticker API Reference](../api/multi-broker-ticker-api.md) — Full interface specs
- [WebSocket Architecture](./websocket.md) — Connection flow and message protocol
- [Authentication Architecture](./authentication.md) — Broker OAuth/credential storage
- [Database Schema](./database.md) — Broker-related tables

**Historical (superseded):**
- ~~[ADR-003 v2: Multi-Broker Ticker Architecture](../decisions/003-multi-broker-ticker-architecture.md)~~ — Original 6-component design (superseded by TICKER-DESIGN-SPEC)

## Instrument Master Population

The `InstrumentMasterService` (`backend/app/services/instrument_master.py`) uses the download-to-DB-on-startup model to populate the `instruments` table:

1. **On startup**, `refresh_instrument_master_startup()` in `main.py` checks if instruments need refreshing (empty table or >24h stale)
2. **Platform adapter** is obtained via `get_platform_market_data_adapter(db)` using the platform fallback chain (SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite)
3. **`InstrumentMasterService.refresh_from_adapter()`** calls `adapter.get_instruments("NFO")`, filters to CE/PE options with future expiry, and batch-upserts into the `instruments` table
4. **DB schema** includes `source_broker` column tracking which broker populated the data, and `option_type` for explicit CE/PE storage
5. **Fallback**: If no platform adapter is available, falls back to Kite CSV download via `InstrumentService`

All 6 broker adapters implement `get_instruments(exchange) -> List[Instrument]` returning the standardized `Instrument` dataclass with `option_type`, `strike`, `expiry`, and `underlying` fields populated.

## References

- [Angel One SmartAPI Docs](https://smartapi.angelbroking.com/docs/)
- [Zerodha Kite Connect Docs](https://kite.trade/docs/connect/v3/)
- [Upstox API Docs](https://upstox.com/developer/api-documentation/)
- [Fyers API Docs](https://api-docs.fyers.in/)
- [Dhan API Docs](https://dhanhq.co/docs/v2/)
- [Paytm Money API Docs](https://developer.paytmmoney.com/)
