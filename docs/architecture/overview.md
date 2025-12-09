# Architecture Overview

AlgoChanakya is an options trading platform (similar to Sensibull) built with FastAPI backend and Vue.js 3 frontend. The platform integrates with broker APIs (starting with Zerodha Kite Connect) for authentication and trading operations.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI + SQLAlchemy (async) + PostgreSQL + Redis |
| **Frontend** | Vue.js 3 + Vite + Pinia + Vue Router + Tailwind CSS |
| **Broker Integration** | Zerodha Kite Connect API |
| **Testing** | Playwright (E2E) |

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue 3)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Login   │ │Dashboard │ │Watchlist │ │ Option   │           │
│  │  View    │ │  View    │ │  View    │ │  Chain   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                         │
│  │Strategy  │ │Positions │ │AutoPilot │  Pinia Stores          │
│  │ Builder  │ │  View    │ │  Views   │  Vue Router            │
│  └──────────┘ └──────────┘ └──────────┘                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP/WebSocket
┌──────────────────────────────▼──────────────────────────────────┐
│                       Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Routes                             │  │
│  │  auth │ watchlist │ options │ strategy │ positions │ ws  │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Services                               │  │
│  │  KiteTickerService │ PnLCalculator │ KiteOrders          │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Models (SQLAlchemy) │ Schemas (Pydantic)    │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   PostgreSQL    │   │     Redis       │   │  Kite Connect   │
│   (Database)    │   │   (Sessions)    │   │   (Broker API)  │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

## Backend Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan events
│   ├── config.py            # Pydantic Settings for env variables
│   ├── database.py          # SQLAlchemy engine, session, Redis pool
│   │
│   ├── api/routes/          # API endpoints
│   │   ├── health.py        # Health check (DB + Redis)
│   │   ├── auth.py          # Zerodha OAuth login/callback
│   │   ├── watchlist.py     # Watchlist CRUD
│   │   ├── instruments.py   # Instrument search
│   │   ├── options.py       # Expiries, strikes, chain
│   │   ├── optionchain.py   # Full chain with OI, IV, Greeks
│   │   ├── strategy.py      # Strategy CRUD, P/L calculation
│   │   ├── orders.py        # Basket orders, positions
│   │   ├── positions.py     # F&O positions, exit/add
│   │   └── websocket.py     # Live price streaming
│   │
│   ├── api/v1/autopilot/    # AutoPilot API (v1)
│   │   ├── strategies.py    # AutoPilot strategy CRUD
│   │   ├── dashboard.py     # Dashboard summary, activity
│   │   ├── orders.py        # AutoPilot order history
│   │   ├── logs.py          # Activity logs
│   │   ├── settings.py      # User settings
│   │   └── templates.py     # Strategy templates
│   │
│   ├── websocket/           # WebSocket handlers
│   │   └── autopilot.py     # AutoPilot real-time updates
│   │
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── users.py
│   │   ├── broker_connections.py
│   │   ├── watchlists.py
│   │   ├── instruments.py
│   │   └── strategies.py
│   │
│   ├── schemas/             # Pydantic request/response schemas
│   │
│   ├── services/            # Business logic
│   │   ├── kite_ticker.py   # WebSocket price streaming
│   │   ├── kite_orders.py   # Order placement
│   │   ├── pnl_calculator.py # Black-Scholes P/L
│   │   └── instruments.py   # Instrument data
│   │
│   └── utils/
│       ├── jwt.py           # JWT handling
│       └── dependencies.py  # FastAPI dependencies
│
├── alembic/                 # Database migrations
├── requirements.txt
└── run.py                   # Dev server entry point
```

## Frontend Structure

```
frontend/
├── src/
│   ├── router/index.js      # Vue Router with auth guards
│   │
│   ├── stores/              # Pinia state management
│   │   ├── auth.js          # Authentication state
│   │   ├── watchlist.js     # Watchlist & WebSocket
│   │   ├── strategy.js      # Strategy builder
│   │   ├── optionchain.js   # Option chain data
│   │   └── positions.js     # F&O positions
│   │
│   ├── services/
│   │   └── api.js           # Axios with interceptors
│   │
│   ├── views/               # Page components
│   │   ├── LoginView.vue
│   │   ├── AuthCallbackView.vue
│   │   ├── DashboardView.vue
│   │   ├── WatchlistView.vue
│   │   ├── OptionChainView.vue
│   │   ├── StrategyBuilderView.vue
│   │   ├── PositionsView.vue
│   │   └── autopilot/       # AutoPilot views
│   │       ├── DashboardView.vue
│   │       ├── StrategyBuilderView.vue
│   │       ├── StrategyDetailView.vue
│   │       └── SettingsView.vue
│   │
│   ├── components/          # Reusable components
│   │   ├── layout/          # KiteLayout, KiteHeader
│   │   ├── watchlist/       # Watchlist components
│   │   ├── strategy/        # Strategy builder components
│   │   └── autopilot/       # AutoPilot components
│   │       ├── dashboard/   # Dashboard widgets
│   │       ├── strategy/    # Strategy list/cards
│   │       ├── builder/     # Builder form widgets
│   │       └── common/      # Shared components
│   │
│   └── composables/
│       └── autopilot/       # AutoPilot composables
│
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
| `PyJWT` | JWT token handling |
| `scipy` | Black-Scholes calculations |

### Frontend

| Package | Purpose |
|---------|---------|
| `vue` | UI framework |
| `vue-router` | Routing |
| `pinia` | State management |
| `axios` | HTTP client |
| `tailwindcss` | CSS framework |

## Environment Variables

### Backend (.env)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL (postgresql+asyncpg://...) |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET` | Secret for JWT signing |
| `JWT_EXPIRY_HOURS` | Token expiry (default: 8) |
| `KITE_API_KEY` | Zerodha API key |
| `KITE_API_SECRET` | Zerodha API secret |
| `FRONTEND_URL` | For CORS and redirects |

### Frontend (.env)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend URL (default: http://localhost:8000) |
| `VITE_WS_URL` | WebSocket URL |

## Related Documentation

- [Authentication](authentication.md) - OAuth flow, sessions
- [WebSocket](websocket.md) - Live price streaming
- [Database](database.md) - Models, migrations
