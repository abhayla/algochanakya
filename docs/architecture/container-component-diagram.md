# Container and Component Diagram

**Last Updated:** 2026-02-16

This diagram shows AlgoChanakya's internal architecture, including containers (deployable units) and their internal components.

---

## Mermaid Diagram

```mermaid
flowchart TB
    %% Styling
    classDef frontend fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    classDef backend fill:#50C878,stroke:#2D7A4A,stroke-width:2px,color:#fff
    classDef database fill:#9370DB,stroke:#6A4CA3,stroke-width:2px,color:#fff
    classDef cache fill:#FF6B6B,stroke:#C94545,stroke-width:2px,color:#fff
    classDef component fill:#FFE5B4,stroke:#D4AF37,stroke-width:1px,color:#000

    %% Containers
    subgraph Frontend["<b>Frontend SPA Container</b><br/>Vue 3 + Vite + Pinia<br/>Port: 5173 (dev) / 3004 (prod)"]
        direction TB
        Views["<b>Views (25 screens)</b><br/>Dashboard, Watchlist, Option Chain,<br/>Positions, Strategy Builder,<br/>AutoPilot (12 sub-views), AI (3 sub-views)"]
        Stores["<b>Pinia Stores (10+)</b><br/>auth, watchlist, optionChain,<br/>strategy, positions, autopilot,<br/>ai, settings, ofo"]
        Services["<b>Services</b><br/>api.js (Axios + interceptor),<br/>feature-specific APIs"]
        Composables["<b>WebSocket Composables</b><br/>useWebSocket.js (ticks),<br/>useAutopilotWebSocket.js"]
    end

    subgraph Backend["<b>Backend API Container</b><br/>FastAPI + async SQLAlchemy + Uvicorn<br/>Port: 8001 (dev) / 8000 (prod)"]
        direction TB

        subgraph API["<b>API Layer</b><br/>18 route modules"]
            Routes["auth, positions, optionchain,<br/>strategy, autopilot, ai, ofo,<br/>settings, watchlist, instruments,<br/>ticker, websocket"]
        end

        subgraph BrokerLayer["<b>Broker Abstraction Layer</b>"]
            Interfaces["<b>Interfaces</b><br/>BrokerAdapter<br/>MarketDataBrokerAdapter"]
            Factories["<b>Factories</b><br/>get_broker_adapter()<br/>get_market_data_adapter()"]
            Adapters["<b>Adapters</b><br/>KiteAdapter, SmartAPIAdapter,<br/>SmartAPIMarketDataAdapter"]
            Utils["<b>Utils</b><br/>SymbolConverter, TokenManager,<br/>RateLimiter"]
        end

        subgraph TickerServices["<b>Legacy Ticker Services</b><br/>(to be replaced)"]
            SmartTicker["SmartAPITickerService<br/>(singleton WebSocket)"]
            KiteTicker["KiteTickerService<br/>(singleton WebSocket)"]
        end

        subgraph AutoPilot["<b>AutoPilot Engine</b><br/>26 services"]
            APCore["<b>Core</b><br/>condition_engine, order_executor,<br/>strategy_monitor, kill_switch"]
            APAdv["<b>Advanced</b><br/>adjustment_engine, suggestion_engine,<br/>trailing_stop, trade_journal"]
            APAnalytics["<b>Analytics</b><br/>analytics, reports, backtesting"]
        end

        subgraph AI["<b>AI/ML Module</b>"]
            Regime["<b>Market Regime</b><br/>6 types (BULL, BEAR, SIDEWAYS,<br/>VOLATILE, BREAKOUT, TRENDING)"]
            Risk["<b>Risk State Engine</b><br/>GREEN/YELLOW/RED states"]
            Strategy["<b>Strategy AI</b><br/>strategy_recommender,<br/>deployment_executor, kelly_calculator"]
            Models["<b>ML Models</b><br/>XGBoost, LightGBM"]
        end

        subgraph Options["<b>Options Calculation</b><br/>8 services"]
            Calc["pnl_calculator, greeks_calculator,<br/>payoff_calculator, iv_metrics,<br/>theta_curve, gamma_risk,<br/>expected_move, oi_analysis"]
        end

        subgraph Auth["<b>Auth & Security</b>"]
            JWT["JWT (HS256, 24h expiry)"]
            OAuth["OAuth 2.0 (Zerodha)"]
            TOTP["Auto-TOTP (AngelOne)"]
            Encrypt["Credential Encryption<br/>(cryptography lib, AES-256)"]
        end
    end

    subgraph Database["<b>PostgreSQL 16</b><br/>VPS 103.118.16.189:5432"]
        Tables["<b>38 Tables</b><br/>Core (5), Trading (4),<br/>AutoPilot (18), AI/ML (9),<br/>Cache (2)"]
    end

    subgraph Cache["<b>Redis 7</b><br/>VPS 103.118.16.189:6379"]
        Sessions["Session Tokens<br/>(24h expiry)"]
        DataCache["Market Data Cache"]
        RateLimit["Rate Limit Counters"]
    end

    %% Connections
    Views --> Stores
    Stores --> Services
    Services --> Composables
    Services -->|"REST API<br/>(Axios)"| Routes
    Composables -->|"WebSocket"| Routes

    Routes --> BrokerLayer
    Routes --> AutoPilot
    Routes --> AI
    Routes --> Options
    Routes --> Auth
    Routes --> TickerServices

    BrokerLayer --> TickerServices
    AutoPilot --> BrokerLayer
    AI --> BrokerLayer

    Backend -->|"async TCP<br/>(asyncpg)"| Tables
    Backend -->|"async TCP<br/>(redis-py)"| Sessions
    Backend -->|"async TCP"| DataCache
    Backend -->|"async TCP"| RateLimit

    %% Apply Styles
    class Frontend frontend
    class Backend backend
    class Database database
    class Cache cache
    class Views,Stores,Services,Composables component
    class API,BrokerLayer,TickerServices,AutoPilot,AI,Options,Auth component
```

---

## ASCII Art Version

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     FRONTEND SPA CONTAINER                              │
│                   Vue 3 + Vite + Pinia + Tailwind CSS 4                 │
│                     Port: 5173 (dev) / 3004 (prod)                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Views (25 screens)                                              │   │
│  │ - Dashboard, Watchlist, Option Chain, Positions                 │   │
│  │ - Strategy Builder, Strategy Library, OFO, Settings             │   │
│  │ - AutoPilot (12 sub-views), AI (3 sub-views)                    │   │
│  └───────────────────────┬─────────────────────────────────────────┘   │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Pinia Stores (10+)                                              │   │
│  │ auth, watchlist, optionChain, strategy, positions, autopilot,   │   │
│  │ ai, settings, ofo                                               │   │
│  └───────────────────────┬─────────────────────────────────────────┘   │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Services                                                        │   │
│  │ - api.js (Axios + interceptor)                                  │   │
│  │ - Feature-specific APIs                                         │   │
│  └───────────────────────┬─────────────────────────────────────────┘   │
│                          │                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ WebSocket Composables                                           │   │
│  │ - useWebSocket.js (ticks)                                       │   │
│  │ - useAutopilotWebSocket.js                                      │   │
│  └─────────────────────────┬───────────────────────────────────────┘   │
│                            │                                            │
└────────────────────────────┼────────────────────────────────────────────┘
                             │
                             ▼ REST API (Axios) + WebSocket
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKEND API CONTAINER                              │
│                FastAPI + async SQLAlchemy + Uvicorn                     │
│                     Port: 8001 (dev) / 8000 (prod)                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ API Layer (18 route modules)                                    │   │
│  │ /api/auth, /api/positions, /api/optionchain, /api/strategy,     │   │
│  │ /api/v1/autopilot, /api/v1/ai, /api/ofo, /api/settings,         │   │
│  │ /ws/ticks, /ws/autopilot                                        │   │
│  └───────────────────────┬─────────────────────────────────────────┘   │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Broker Abstraction Layer                                        │   │
│  │ ┌─────────────────┬──────────────────┬────────────────────────┐ │   │
│  │ │ Interfaces      │ Factories        │ Adapters              │ │   │
│  │ │ - BrokerAdapter │ - get_broker_    │ - KiteAdapter         │ │   │
│  │ │ - MarketData    │   adapter()      │ - SmartAPIAdapter     │ │   │
│  │ │   BrokerAdapter │ - get_market_    │ - SmartAPIMarketData  │ │   │
│  │ │                 │   data_adapter() │   Adapter             │ │   │
│  │ └─────────────────┴──────────────────┴────────────────────────┘ │   │
│  │ Utils: SymbolConverter, TokenManager, RateLimiter              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Legacy Ticker Services (to be replaced by 5-component arch)     │   │
│  │ - SmartAPITickerService (singleton WebSocket)                   │   │
│  │ - KiteTickerService (singleton WebSocket)                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ AutoPilot Engine (26 services)                                  │   │
│  │ - Core: condition_engine, order_executor, strategy_monitor,     │   │
│  │   kill_switch                                                   │   │
│  │ - Advanced: adjustment_engine, suggestion_engine, trailing_stop,│   │
│  │   trade_journal                                                 │   │
│  │ - Analytics: analytics, reports, backtesting                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ AI/ML Module                                                    │   │
│  │ - Market Regime (6 types: BULL, BEAR, SIDEWAYS, VOLATILE,       │   │
│  │   BREAKOUT, TRENDING)                                           │   │
│  │ - Risk State Engine (GREEN/YELLOW/RED states)                   │   │
│  │ - Strategy AI (strategy_recommender, deployment_executor,       │   │
│  │   kelly_calculator)                                             │   │
│  │ - ML Models (XGBoost, LightGBM)                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Options Calculation (8 services)                                │   │
│  │ pnl_calculator, greeks_calculator, payoff_calculator, iv_metrics,│   │
│  │ theta_curve, gamma_risk, expected_move, oi_analysis             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Auth & Security                                                 │   │
│  │ - JWT (HS256, 24h expiry)                                       │   │
│  │ - OAuth 2.0 (Zerodha)                                           │   │
│  │ - Auto-TOTP (AngelOne, pyotp)                                   │   │
│  │ - Credential Encryption (cryptography lib, AES-256)             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└────────────┬────────────────────────────┬───────────────────────────────┘
             │                            │
             │ async TCP (asyncpg)        │ async TCP (redis-py)
             ▼                            ▼
┌──────────────────────────┐    ┌────────────────────────────┐
│  PostgreSQL 16           │    │  Redis 7                   │
│  VPS 103.118.16.189:5432 │    │  VPS 103.118.16.189:6379   │
├──────────────────────────┤    ├────────────────────────────┤
│  38 Tables:              │    │  - Session Tokens (24h)    │
│  - Core (5)              │    │  - Market Data Cache       │
│  - Trading (4)           │    │  - Rate Limit Counters     │
│  - AutoPilot (18)        │    │                            │
│  - AI/ML (9)             │    │                            │
│  - Cache (2)             │    │                            │
└──────────────────────────┘    └────────────────────────────┘
```

---

## Container Details

### 1. Frontend SPA Container

**Technology Stack:**
- **Framework:** Vue 3 (Composition API)
- **Build Tool:** Vite 5
- **State Management:** Pinia
- **Styling:** Tailwind CSS 4
- **HTTP Client:** Axios
- **Charting:** Chart.js
- **WebSocket:** Native WebSocket API (composables)

**Ports:**
- Dev: 5173 (Vite default)
- Production: 3004 (static build served via PM2)

**Components:**

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Views (25)** | Screen components | Vue 3 SFC (Single File Components) |
| **Pinia Stores (10+)** | State management | Pinia (Vue official state lib) |
| **Services** | API communication | Axios with interceptors |
| **Composables** | WebSocket logic | Vue Composition API |

**Key Views:**
- Dashboard (portfolio summary)
- Watchlist (instrument monitoring)
- Option Chain (Greeks, IV, OI analysis)
- Positions (live P&L tracking)
- Strategy Builder (multi-leg builder)
- AutoPilot (12 sub-views: strategies, orders, logs, analytics, templates, etc.)
- AI (3 sub-views: regime, risk, strategy)
- OFO (Optimal F&O calculator)
- Settings (broker connections, preferences)

---

### 2. Backend API Container

**Technology Stack:**
- **Framework:** FastAPI 0.110+
- **ORM:** async SQLAlchemy 2.0
- **Server:** Uvicorn (ASGI)
- **Database Driver:** asyncpg (PostgreSQL)
- **Cache Driver:** redis-py (async)
- **Authentication:** python-jose (JWT)
- **Broker SDKs:** kiteconnect, smartapi-python
- **AI/ML:** pandas, XGBoost, LightGBM
- **TOTP:** pyotp

**Ports:**
- Dev: 8001 (configurable in `backend/.env`)
- Production: 8000 (PM2-managed)

**Architecture Layers:**

#### API Layer (18 route modules)

| Route | Purpose |
|-------|---------|
| `/api/auth` | JWT login, logout, broker OAuth |
| `/api/positions` | Live positions, P&L tracking |
| `/api/optionchain` | Option chain data, Greeks, IV |
| `/api/strategy` | Manual strategy CRUD |
| `/api/v1/autopilot/*` | AutoPilot (10+ endpoints) |
| `/api/v1/ai/*` | AI regime, risk, strategy |
| `/api/ofo` | Optimal F&O calculator |
| `/api/settings` | User preferences, broker connections |
| `/api/watchlist` | Instrument watchlist CRUD |
| `/api/instruments` | Search instruments, get tokens |
| `/api/ticker` | Start/stop ticker subscriptions |
| `/ws/ticks` | WebSocket market data feed |
| `/ws/autopilot` | WebSocket AutoPilot updates |

#### Broker Abstraction Layer

**Interfaces:**
```python
# backend/app/services/brokers/base.py
class BrokerAdapter(ABC):
    """Order execution and position management"""
    @abstractmethod
    async def place_order(...) -> Dict
    @abstractmethod
    async def get_positions(...) -> List[Dict]
    @abstractmethod
    async def cancel_order(...) -> Dict

class MarketDataBrokerAdapter(ABC):
    """Market data and historical OHLC"""
    @abstractmethod
    async def get_quote(...) -> Dict
    @abstractmethod
    async def get_historical_data(...) -> pd.DataFrame
    @abstractmethod
    async def search_instruments(...) -> List[Dict]
```

**Factories:**
- `get_broker_adapter(broker_type, credentials)` → `KiteAdapter` | `SmartAPIAdapter`
- `get_market_data_adapter(broker_type, credentials)` → `SmartAPIMarketDataAdapter` | `KiteMarketDataAdapter`

**Utilities:**
- `SymbolConverter`: Convert between broker symbol formats (Kite ↔ SmartAPI)
- `TokenManager`: Resolve instrument tokens across brokers
- `RateLimiter`: Per-broker API rate limiting

#### Legacy Ticker Services (Planned Migration)

**Current Implementation:**
- `SmartAPITickerService` (singleton WebSocket manager)
- `KiteTickerService` (singleton WebSocket manager)

**Status:** ⚠️ To be replaced by 5-component ticker architecture
- See [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md)
- See [TICKER-IMPLEMENTATION-GUIDE.md](../guides/TICKER-IMPLEMENTATION-GUIDE.md)

#### AutoPilot Engine (26 services, 18 tables)

**Core Services:**
- `condition_engine.py` - Evaluate entry/exit/adjustment conditions
- `order_executor.py` - Execute orders via broker adapters
- `strategy_monitor.py` - Monitor active strategies
- `kill_switch.py` - Emergency shutdown

**Advanced Services:**
- `adjustment_engine.py` - Auto-adjust strategies
- `suggestion_engine.py` - AI-powered suggestions
- `trailing_stop.py` - Trailing stop-loss management
- `trade_journal.py` - Trade history and notes

**Analytics Services:**
- `analytics.py` - Performance metrics
- `reports.py` - PDF/Excel report generation
- `backtesting.py` - Historical simulation

**Full list:** See [backend/CLAUDE.md](../../backend/CLAUDE.md#autopilot-services-26-files)

#### AI/ML Module (9 tables)

**Market Regime Detection:**
- 6 regime types: BULL, BEAR, SIDEWAYS, VOLATILE, BREAKOUT, TRENDING
- Uses price action, volatility, and volume analysis
- Updates every 5 minutes

**Risk State Engine:**
- 3 states: GREEN (safe), YELLOW (cautious), RED (dangerous)
- Factors: VIX, drawdown, win rate, recent losses
- Blocks AutoPilot deployment in RED state

**Strategy AI:**
- `strategy_recommender.py` - Suggest strategies based on regime
- `deployment_executor.py` - Auto-deploy strategies
- `kelly_calculator.py` - Position sizing (Kelly Criterion)

**ML Models:**
- XGBoost: Regime classification
- LightGBM: Risk scoring

#### Options Calculation (8 services)

| Service | Purpose |
|---------|---------|
| `pnl_calculator.py` | Live P&L tracking |
| `greeks_calculator.py` | Delta, Gamma, Theta, Vega |
| `payoff_calculator.py` | Strategy payoff curves |
| `iv_metrics.py` | Implied volatility analysis |
| `theta_curve.py` | Time decay visualization |
| `gamma_risk.py` | Gamma exposure risk |
| `expected_move.py` | Expected price move calculator |
| `oi_analysis.py` | Open interest analysis |

#### Auth & Security

| Component | Technology | Purpose |
|-----------|------------|---------|
| **JWT** | python-jose, HS256 | User session tokens (24h expiry) |
| **OAuth 2.0** | Zerodha Kite Connect | Broker authentication |
| **Auto-TOTP** | pyotp | AngelOne automatic 2FA |
| **Encryption** | cryptography (AES-256) | Stored broker credentials |

---

### 3. PostgreSQL 16 Container

**Location:** VPS 103.118.16.189:5432

**38 Tables (grouped by domain):**

| Domain | Tables | Count |
|--------|--------|-------|
| **Core** | users, broker_connections, user_preferences, smartapi_credentials, instruments | 5 |
| **Trading** | strategies, strategy_legs, strategy_templates, broker_instrument_tokens | 4 |
| **AutoPilot** | autopilot_user_settings, autopilot_strategies, autopilot_orders, autopilot_order_batches, autopilot_logs, autopilot_templates, autopilot_template_ratings, autopilot_condition_eval, autopilot_daily_summary, autopilot_adjustment_logs, autopilot_pending_confirmations, autopilot_trade_journal, autopilot_analytics_cache, autopilot_reports, autopilot_backtests, autopilot_position_legs, autopilot_adjustment_suggestions, autopilot_option_chain_cache | 18 |
| **AI/ML** | ai_user_config, ai_model_registry, ai_learning_reports, ai_paper_trades, ai_risk_state, ai_strategy_cooldown, ai_regime_history, ai_regime_performance, ai_decisions_log | 9 |
| **Cache** | autopilot_option_chain_cache, ai_market_snapshots | 2 |

**Connection:**
- Driver: asyncpg (async native PostgreSQL driver)
- Pool: 10 min / 20 max connections (configurable)
- Protocol: async TCP

**Full schema:** See [erd-data-model.md](erd-data-model.md)

---

### 4. Redis 7 Container

**Location:** VPS 103.118.16.189:6379

**Usage:**

| Purpose | Key Pattern | TTL |
|---------|-------------|-----|
| **Session Tokens** | `session:{token}` | 24 hours |
| **Market Data Cache** | `quote:{symbol}`, `ohlc:{symbol}:{interval}` | 1-5 minutes |
| **Rate Limit Counters** | `ratelimit:{broker}:{endpoint}` | 1 minute |

**Connection:**
- Driver: redis-py (async)
- Protocol: async TCP

---

## Data Flow

### 1. REST API Request Flow

```
User Browser
    ↓ (HTTPS POST /api/positions)
Frontend (Axios)
    ↓ (JWT token in header)
Backend API Layer (/api/positions)
    ↓ (Depends(get_current_user))
Auth Middleware (verify JWT)
    ↓
Broker Abstraction Layer (get_broker_adapter)
    ↓
KiteAdapter / SmartAPIAdapter
    ↓ (REST API call)
External Broker API
    ↓
Response flows back through layers
```

### 2. WebSocket Market Data Flow

```
External Broker WebSocket
    ↓ (binary ticks)
SmartAPITickerService / KiteTickerService
    ↓ (parse + convert to unified format)
FastAPI WebSocket Endpoint (/ws/ticks)
    ↓ (broadcast JSON)
Frontend Composable (useWebSocket)
    ↓ (update Pinia store)
Vue Component (reactive UI update)
```

### 3. AutoPilot Order Execution Flow

```
AutoPilot Strategy Monitor
    ↓ (check conditions)
Condition Engine (evaluate entry/exit)
    ↓ (condition met)
Order Executor
    ↓ (async)
Broker Abstraction Layer (get_broker_adapter)
    ↓
KiteAdapter / SmartAPIAdapter
    ↓ (place_order API call)
External Broker API
    ↓ (order placed)
Trade Journal (log trade)
    ↓
WebSocket Broadcast (/ws/autopilot)
    ↓
Frontend (real-time order update)
```

### 4. AI Regime Detection Flow

```
Scheduler (every 5 minutes)
    ↓
Market Regime Service
    ↓ (fetch OHLC)
Market Data Adapter (get_historical_data)
    ↓
External Broker API
    ↓ (price data)
ML Model (XGBoost)
    ↓ (predict regime)
Database (ai_regime_history table)
    ↓
WebSocket Broadcast (optional)
    ↓
Frontend AI View (regime indicator)
```

---

## Technology Summary

| Container | Key Technologies |
|-----------|------------------|
| **Frontend** | Vue 3, Vite, Pinia, Tailwind CSS 4, Axios, Chart.js |
| **Backend** | FastAPI, async SQLAlchemy, Uvicorn, asyncpg, redis-py |
| **Database** | PostgreSQL 16 (38 tables, 19 custom enums) |
| **Cache** | Redis 7 (sessions, data cache, rate limits) |
| **Broker SDKs** | kiteconnect, smartapi-python |
| **AI/ML** | pandas, XGBoost, LightGBM |
| **Auth** | python-jose (JWT), pyotp (TOTP) |
| **Testing** | Playwright (122 E2E specs), pytest (67 tests), Vitest |

---

## Deployment Architecture

**Development:**
- Frontend: `npm run dev` (Vite dev server, port 5173)
- Backend: `python run.py` (Uvicorn, port 8001)
- Database/Redis: VPS-hosted (shared with production, different DB names)

**Production:**
- Frontend: `pm2` serving static build (port 3004)
- Backend: `pm2` running Uvicorn (port 8000)
- Database/Redis: VPS 103.118.16.189 (isolated database names)
- Location: `C:\Apps\algochanakya` (⚠️ NEVER TOUCH from dev environment)

**CI/CD:**
- GitHub Actions (4 workflows)
- Auto-deploy on merge to `main`

---

## Related Documentation

- **[Context Diagram](context-diagram.md)** - External system dependencies
- **[ERD Data Model](erd-data-model.md)** - Database schema (38 tables)
- **[Broker Abstraction Architecture](broker-abstraction.md)** - Multi-broker implementation
- **[Ticker Architecture](../decisions/TICKER-DESIGN-SPEC.md)** - Multi-broker WebSocket design
- **[AutoPilot Documentation](../autopilot/)** - AutoPilot service details
- **[Backend CLAUDE.md](../../backend/CLAUDE.md)** - Backend development guide
- **[Frontend CLAUDE.md](../../frontend/CLAUDE.md)** - Frontend development guide
