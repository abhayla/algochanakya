# Architecture Overview

AlgoChanakya is a multi-broker options trading platform for Indian markets. The platform supports 6 brokers (Zerodha, AngelOne, Upstox, Dhan, Fyers, Paytm) through a broker-agnostic abstraction layer for both market data and order execution.

**Primary design principle:** Adding a new broker requires only an adapter implementation and factory registration — zero changes to core code, routes, or business logic.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI + SQLAlchemy (async) + PostgreSQL + Redis |
| **Frontend** | Vue.js 3 + Vite + Pinia + Vue Router + Tailwind CSS |
| **Broker Integration** | 6-broker abstraction (Zerodha, AngelOne, Upstox, Dhan, Fyers, Paytm) |
| **Market Data** | Multi-broker ticker with failover (SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite) |
| **Testing** | Playwright (E2E) + pytest (backend) + Vitest (frontend unit) |
| **AI/ML** | XGBoost, LightGBM, Claude API for market regime detection and strategy scoring |

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Frontend (Vue 3)                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  Login   │ │Dashboard │ │Watchlist │ │ Option   │ │Strategy  │      │
│  │  View    │ │  View    │ │  View    │ │  Chain   │ │ Builder  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │Positions │ │AutoPilot │ │   AI     │ │  OFO     │ │Settings  │      │
│  │  View    │ │ (12 sub) │ │  Views   │ │  View    │ │  View    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                                          │
│  11 Pinia Stores │ 5 Composables │ 86 Components │ 25 Views             │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ HTTP / WebSocket
┌──────────────────────────────▼───────────────────────────────────────────┐
│                         Backend (FastAPI)                                 │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                        API Routes (20+)                           │   │
│  │  auth │ {broker}_auth (×4) │ watchlist │ options │ optionchain   │   │
│  │  strategy │ positions │ orders │ ticker │ websocket │ ofo │ ...  │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                      API v1 (AI + AutoPilot)                      │   │
│  │  ai/{regime,config,recommendations,analytics,backtest,deploy,...} │   │
│  │  autopilot/{analytics,legs,option_chain,simulation,suggestions}   │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                         Services                                  │   │
│  │  brokers/ (6 order adapters + market data abstraction)            │   │
│  │  brokers/market_data/ticker/ (5-component multi-broker ticker)    │   │
│  │  autopilot/ (26 services)                                         │   │
│  │  ai/ (35 services including ML sub-module)                        │   │
│  │  options/ (8 calculation services)                                │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │           Models (SQLAlchemy) │ Schemas (Pydantic)                │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────────┐
│   PostgreSQL    │   │     Redis       │   │   Broker APIs (×6)      │
│   (Database)    │   │ (Sessions/Cache)│   │   via Abstraction Layer │
└─────────────────┘   └─────────────────┘   └─────────────────────────┘
```

## Broker Abstraction (Core Architecture)

The platform uses a dual-path architecture:

- **Market Data (platform-default):** Platform-level shared credentials serve all users by default. Failover chain: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite. Users can optionally upgrade to use their own broker API.
- **Order Execution (per-user):** Each user's orders execute through their own broker connection (SEBI-compliant). All 6 brokers supported.

**Key components:**
- `BrokerAdapter` — Order execution interface (`base.py`)
- `MarketDataBrokerAdapter` — Market data interface (`market_data_base.py`)
- `TickerAdapter` → `TickerPool` → `TickerRouter` → `HealthMonitor` → `FailoverController` — 5-component ticker system
- `TokenManager` — Cross-broker symbol/token mapping
- `SymbolConverter` — Canonical (Kite format) ↔ broker-specific symbols

**Full details:** [Broker Abstraction Architecture](broker-abstraction.md) | [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md) | [ADR-002](../decisions/002-broker-abstraction.md)

## Backend Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, lifespan events
│   ├── config.py               # Pydantic Settings for env variables
│   ├── database.py             # SQLAlchemy engine, session, Redis pool
│   ├── constants/trading.py    # Centralized lot sizes, strike steps, index tokens
│   │
│   ├── api/routes/             # API endpoints (20 files)
│   │   ├── auth.py             # Multi-broker OAuth login/callback
│   │   ├── {broker}_auth.py    # Per-broker auth (dhan, fyers, upstox, paytm)
│   │   ├── watchlist.py        # Watchlist CRUD
│   │   ├── instruments.py      # Instrument search
│   │   ├── options.py          # Expiries, strikes, chain
│   │   ├── optionchain.py      # Full chain with OI, IV, Greeks
│   │   ├── strategy.py         # Strategy CRUD, P/L calculation
│   │   ├── orders.py           # Basket orders, positions
│   │   ├── positions.py        # F&O positions, exit/add
│   │   ├── websocket.py        # Live price streaming (broker-agnostic)
│   │   ├── ticker.py           # Ticker health, failover status
│   │   ├── ofo.py              # Options Flow Order
│   │   └── user_preferences.py # Broker selection, settings
│   │
│   ├── api/v1/                 # Versioned API
│   │   ├── ai/                 # AI endpoints (regime, config, analytics, backtest, etc.)
│   │   └── autopilot/          # AutoPilot endpoints (analytics, legs, simulation, etc.)
│   │
│   ├── websocket/              # WebSocket handlers
│   │   ├── routes.py           # AutoPilot real-time updates
│   │   └── manager.py          # WebSocket connection management
│   │
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── users.py, broker_connections.py
│   │   ├── watchlists.py, instruments.py, strategies.py
│   │   ├── autopilot/ (16 tables)
│   │   └── ai/ (ai_user_config, ai_decisions_log, ai_model_registry, ai_learning_reports)
│   │
│   ├── schemas/                # Pydantic request/response schemas
│   │
│   ├── services/
│   │   ├── brokers/            # Broker abstraction layer
│   │   │   ├── base.py         # BrokerAdapter interface + UnifiedOrder/Position/Quote
│   │   │   ├── factory.py      # get_broker_adapter() factory (6 brokers)
│   │   │   ├── kite_adapter.py, angelone_adapter.py, upstox_order_adapter.py
│   │   │   ├── dhan_order_adapter.py, fyers_order_adapter.py, paytm_order_adapter.py
│   │   │   └── market_data/    # Market data abstraction
│   │   │       ├── ticker/     # 5-component multi-broker ticker (6 adapters)
│   │   │       ├── factory.py, token_manager.py, rate_limiter.py, symbol_converter.py
│   │   │       └── smartapi_adapter.py, kite_adapter.py, etc.
│   │   ├── autopilot/          # AutoPilot services (26 files)
│   │   ├── ai/                 # AI/ML services (35 files)
│   │   │   ├── market_regime.py, risk_state_engine.py, strategy_recommender.py
│   │   │   ├── kelly_calculator.py, backtester.py, portfolio_manager.py
│   │   │   └── ml/ (7 files — XGBoost/LightGBM models, training, registry)
│   │   ├── options/            # Options calculation (8 files)
│   │   ├── legacy/             # Legacy services (to be cleaned up)
│   │   └── deprecated/         # Deprecated ticker services
│   │
│   └── utils/
│       ├── jwt.py              # JWT handling
│       ├── dependencies.py     # FastAPI dependencies
│       └── encryption.py       # Credential encryption
│
├── alembic/                    # Database migrations
├── requirements.txt
└── run.py                      # Dev server entry point
```

## Frontend Structure

```
frontend/
├── src/
│   ├── router/index.js         # Vue Router with auth guards
│   │
│   ├── stores/                 # Pinia state management (11 stores)
│   │   ├── auth.js             # Authentication state
│   │   ├── watchlist.js        # Watchlist & WebSocket
│   │   ├── strategy.js         # Strategy builder
│   │   ├── optionchain.js      # Option chain data
│   │   ├── positions.js        # F&O positions
│   │   ├── autopilot.js        # AutoPilot state
│   │   ├── aiConfig.js         # AI configuration
│   │   ├── brokerPreferences.js # Broker selection
│   │   ├── strategyLibrary.js  # Strategy templates
│   │   ├── ofo.js              # OFO calculator
│   │   └── userPreferences.js  # User settings
│   │
│   ├── services/
│   │   ├── api.js              # Axios with interceptors
│   │   ├── priceService.js     # Price data service
│   │   └── smartapi.js         # SmartAPI WebSocket
│   │
│   ├── views/                  # 25 views
│   │   ├── LoginView.vue, AuthCallbackView.vue
│   │   ├── DashboardView.vue, WatchlistView.vue
│   │   ├── OptionChainView.vue, StrategyBuilderView.vue
│   │   ├── StrategyLibraryView.vue, PositionsView.vue
│   │   ├── OFOView.vue, SettingsView.vue
│   │   ├── autopilot/ (12 views — dashboard, builder, detail, settings, etc.)
│   │   └── ai/ (3 views — analytics, paper trading, settings)
│   │
│   ├── components/             # 86 reusable components
│   │   ├── layout/             # KiteLayout, KiteHeader
│   │   ├── common/             # BrokerUpgradeBanner, DataSourceBadge
│   │   ├── settings/           # BrokerSettings, SmartAPISettings
│   │   ├── watchlist/, strategy/, optionchain/, positions/
│   │   ├── autopilot/ (dashboard, strategy, builder, common)
│   │   └── ofo/                # OFO components
│   │
│   ├── composables/            # Reusable composition functions
│   │   ├── useToast.js, useScrollIndicator.js
│   │   └── autopilot/ (useOptionChain, usePositionLegs, useWebSocket)
│   │
│   └── constants/trading.js    # Trading constants (fetched from backend API)
│
├── tests/                      # Vitest unit tests
│   ├── stores/                 # Store tests
│   └── composables/            # Composable tests
├── package.json
└── vite.config.js
```

## Key Dependencies

### Backend

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `sqlalchemy[asyncio]` | Async ORM |
| `asyncpg` | PostgreSQL async driver |
| `redis[asyncio]` | Redis async client |
| `alembic` | Database migrations |
| `pydantic-settings` | Settings management |
| `kiteconnect` | Zerodha API client |
| `smartapi-python` | AngelOne API client |
| `PyJWT` | JWT token handling |
| `scipy` | Black-Scholes calculations |
| `xgboost`, `lightgbm` | ML strategy scoring |
| `anthropic` | Claude AI integration |

### Frontend

| Package | Purpose |
|---------|---------|
| `vue` | UI framework |
| `vue-router` | Routing |
| `pinia` | State management |
| `axios` | HTTP client |
| `tailwindcss` | CSS framework |

## Environment Variables

See [backend/CLAUDE.md](../../backend/CLAUDE.md#environment-variables) and [frontend/CLAUDE.md](../../frontend/CLAUDE.md#environment-variables) for complete variable lists.

## Related Documentation

- [Broker Abstraction Architecture](broker-abstraction.md) — Multi-broker design (SSOT)
- [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md) — 5-component ticker architecture
- [Authentication](authentication.md) — OAuth flows per broker
- [Database](database.md) — Models, migrations
- [AI Module](../ai/README.md) — AutoPilot AI services
