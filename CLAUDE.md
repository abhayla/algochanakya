# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Last Updated:** February 2026
**Primary Implementation Status:** Phase 3 Complete (Multi-broker abstraction for market data + order execution)

> **Note:** This is a comprehensive guide (~700 lines). Use Ctrl+F to search for specific topics, or check the Table of Contents. For task-specific docs, see [Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md).

## Table of Contents

1. [Quick Command Cheat Sheet](#quick-command-cheat-sheet)
2. [Critical: Mandatory Behaviors](#critical-mandatory-behaviors)
3. [Quick Start](#quick-start)
4. [Core Purpose: Multi-Broker Architecture](#core-purpose-multi-broker-architecture)
5. [Project Overview](#project-overview)
6. [Development Commands](#development-commands)
7. [Architecture Overview](#architecture-overview)
8. [Important Patterns](#important-patterns)
9. [Documentation](#documentation)
10. [Claude Code Skills](#claude-code-skills)
11. [Key URLs](#key-urls)
12. [Testing](#testing)
13. [Common Pitfalls](#common-pitfalls)
14. [Troubleshooting Common Errors](#troubleshooting-common-errors)
15. [CI/CD](#cicd)
16. [Debug Commands](#debug-commands)
17. [Production Debugging](#production-debugging)

---

## Quick Command Cheat Sheet

**Most Common Commands** - Quick reference for daily development:

| Task | Command | Location |
|------|---------|----------|
| **Start dev backend** | `venv\Scripts\activate && python run.py` | `backend/` |
| **Start frontend** | `npm run dev` | `frontend/` |
| **Run all E2E tests** | `npm test` | root |
| **Run single E2E test** | `npx playwright test path/to/spec.js` | root |
| **Database migration** | `alembic revision --autogenerate -m "msg" && alembic upgrade head` | `backend/` |
| **Apply migrations only** | `alembic upgrade head` | `backend/` |
| **Check git status** | `git status && git log --oneline -5` | root |
| **Auto-verify after changes** | `Skill(skill="auto-verify")` | Claude Code |
| **Backend tests** | `pytest tests/ -v` | `backend/` |
| **Frontend unit tests** | `npm run test` | `frontend/` |
| **Debug E2E test** | `npx playwright test path/to/spec --debug` | root |
| **Check backend health** | `curl http://localhost:8001/api/health` | terminal |

**Port Reference:**

| Service | Development | Production (DO NOT TOUCH) |
|---------|-------------|---------------------------|
| Backend API | `localhost:8001` | `localhost:8000` |
| Frontend | `localhost:5173` | `localhost:3004` |
| WebSocket | `ws://localhost:8001/ws/ticks` | `wss://algochanakya.com/ws/ticks` |
| Database | `localhost:5432` | `localhost:5432` |
| Redis | `localhost:6379` | `localhost:6379` |

---

## CRITICAL: Mandatory Behaviors

### 0. Production vs Development - NEVER TOUCH PRODUCTION

**Development folder:** `D:\Abhay\VibeCoding\algochanakya` - Work ONLY here
**Production folder:** `C:\Apps\algochanakya` - **NEVER read, modify, or interact with this folder**

Production runs on the same machine. NEVER:
- Kill, restart, or interfere with production processes
- Read or modify files in `C:\Apps\algochanakya`
- Copy files to/from production
- Run commands that affect the production folder

If the backend at localhost:8000 is the production instance, start the dev backend separately or ask the user how to proceed.

### 0.1. Protected Files - DO NOT MODIFY

The `notes` file in the project root is a personal file. **NEVER read, modify, or commit changes to this file.**

### 1. Auto-Verification After Code Changes

After making ANY code change (bug fix, feature, refactor), IMMEDIATELY invoke `auto-verify`:
```
Skill(skill="auto-verify")
```
**Skip only for:** Documentation-only changes, comment-only changes, or when user says "skip verification".

### 2. Check Current Work First

Always run before starting:
```bash
git status && git log --oneline -5
```

### 3. Clarify Before Implementing

Before implementing features, refactors, or architectural changes:
1. **State understanding** in 2-3 sentences
2. **Research codebase** for existing patterns
3. **Check relevant documentation:**
   - [Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md) for task-specific docs
   - [Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md) for ongoing work
   - [Broker Abstraction](docs/architecture/broker-abstraction.md) for multi-broker design
4. **Ask questions** if gaps exist (scope, design, integration)

**Skip clarification for:** Doc changes, obvious bug fixes, explicit user instructions.

**Example - Good Response:**
> I understand you want to add a kill switch to Strategy Builder.
> I found AutoPilot has one at `backend/app/services/kill_switch.py`.
> Questions: Exit positions or cancel orders? Add to StrategyActions or new button?

**Bad Response:**
> I'll add a kill switch. Let me create a new component...

## Quick Start

**Requirements:** Python 3.11+ | Node.js 20+ | PostgreSQL | Redis

**IMPORTANT:** Frontend development uses `.env.local` which overrides `.env`. Ensure `frontend/.env.local` points to dev backend (port 8001), not production (8000). See [Port Reference](#quick-command-cheat-sheet) for all service ports.

```bash
# Start dev backend (from backend/)
venv\Scripts\activate && python run.py    # Windows
source venv/bin/activate && python run.py # Linux/Mac

# Start frontend (from frontend/)
npm run dev

# Run E2E tests (from root)
npm test                                   # All tests
npx playwright test path/to/spec.js       # Single file

# Database migration (from backend/)
alembic revision --autogenerate -m "description" && alembic upgrade head
```

See [Development Commands](#development-commands) for complete command reference.

---

## Core Purpose: Multi-Broker Architecture

**Primary Goal:** AlgoChanakya is designed as a **broker-agnostic platform** where adding a new broker requires **zero code changes** - only adapter implementation and factory registration.

### Why Multi-Broker Support?

Indian broker APIs vary significantly:
- **Pricing:** Zerodha charges ₹500/month for market data; many others offer FREE APIs
- **Cost Optimization:** Users can mix FREE data providers with their funded broker for orders
- **Flexibility:** Switch brokers without reinstalling, test multiple providers for reliability/latency
- **User Choice:** No lock-in to a single broker

**Example FREE Setup:** SmartAPI (FREE data) + Zerodha Personal API (FREE orders) = ₹0/month

### Two Independent Broker Systems

The platform maintains **two separate abstractions** for maximum flexibility:

#### 1. Market Data Brokers
**Purpose:** Live prices, historical OHLC, WebSocket ticks, instrument data

**Why Separate:** Many brokers offer free market data but charge for trading APIs. Users can use a free provider while executing orders through their funded broker.

**Interface:** `MarketDataBrokerAdapter` (to be implemented)

**Factory:** `get_market_data_adapter(broker_type, credentials)`

#### 2. Order Execution Brokers
**Purpose:** Placing orders, managing positions, account margins

**Why Separate:** Requires funded broker account. Separating allows users to keep existing broker while using cheaper data sources.

**Interface:** `BrokerAdapter` (implemented in `backend/app/services/brokers/base.py`)

**Factory:** `get_broker_adapter(broker_type, credentials)` (implemented)

### Supported Brokers

| Broker | Market Data | Orders | Status |
|--------|-------------|--------|--------|
| **Angel One** (SmartAPI) | ✅ FREE | ✅ FREE | Default for data |
| **Zerodha** (Kite Connect) | ₹500/mo | ✅ FREE | Orders only |
| **Upstox/Fyers/Dhan/Others** | FREE | FREE | Planned |

**Current Setup:** SmartAPI (FREE data) + Zerodha (FREE orders) = ₹0/month

See [Broker Abstraction Architecture](docs/architecture/broker-abstraction.md) for complete broker list with pricing details.

### Current Implementation Status

**✅ Phase 1 & 2 Complete (Jan 2026):**
- **Order Execution Abstraction:**
  - `BrokerAdapter` interface (`backend/app/services/brokers/base.py`)
  - `KiteAdapter` for Zerodha order execution
  - Unified data models: `UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote`
  - Factory: `get_broker_adapter()` in `backend/app/services/brokers/factory.py`

- **Market Data Abstraction (NEW):**
  - `MarketDataBrokerAdapter` interface (`backend/app/services/brokers/market_data/market_data_base.py`)
  - `SmartAPIMarketDataAdapter` implementation (`backend/app/services/brokers/market_data/smartapi_adapter.py`)
  - Factory: `get_market_data_adapter()` in `backend/app/services/brokers/market_data/factory.py`
  - `TickerServiceBase` interface for unified WebSocket (`backend/app/services/brokers/market_data/ticker_base.py`)
  - **Infrastructure:**
    - `TokenManager` - Cross-broker token/symbol mapping (`token_manager.py`)
    - `RateLimiter` - Per-broker API rate limiting (`rate_limiter.py`)
    - `SymbolConverter` - Canonical ↔ broker-specific symbols (`symbol_converter.py`)
  - **Database:** `broker_instrument_tokens` table for token mapping across brokers

- **Legacy SmartAPI Services (to be wrapped by adapter):**
  - `smartapi_auth.py` - Auto-TOTP authentication
  - `smartapi_ticker.py` - WebSocket V2 live prices
  - `smartapi_market_data.py` - REST quotes
  - `smartapi_historical.py` - OHLCV data
  - `smartapi_instruments.py` - Instrument lookup

**✅ Phase 3 Complete (Jan 2026):**
- All routes refactored to use broker factories instead of hardcoded services
- `KiteMarketDataAdapter` implemented for Kite market data
- Routes updated: `optionchain.py`, `ofo.py`, `orders.py`, `strategy_wizard.py`, `websocket.py`

**🚧 Phase 4-5 To Be Implemented:**
- Remove dead WebSocket stubs from `MarketDataBrokerAdapter` (moved to `MultiTenantTickerService`)
- Create `AngelAdapter` for Angel One order execution
- Complete user settings UI for broker selection (market data + order execution)
- Migrate legacy ticker services to implement `TickerServiceBase` interface

**📚 Documentation:**
- [Broker Abstraction Architecture](docs/architecture/broker-abstraction.md) - Complete technical design
- [ADR-002: Multi-Broker Abstraction](docs/decisions/002-broker-abstraction.md) - Decision rationale and alternatives

### Adding a New Broker (Future State)

Once abstraction is complete, adding a broker will require:
1. Create adapter class implementing `BrokerAdapter` or `MarketDataBrokerAdapter`
2. Register in factory (`_BROKER_ADAPTERS` dict)
3. Add credentials table (if needed) + migration
4. Update frontend settings dropdown

**Zero changes** to routes, services, or business logic required.

---

## Project Overview

AlgoChanakya is an options trading platform (similar to Sensibull) with FastAPI backend and Vue.js 3 frontend. Uses **AngelOne SmartAPI** as the default for all market data (live prices, historical OHLC) with auto-TOTP authentication. Zerodha Kite Connect is used for order execution only.

**Tech Stack:** FastAPI + async SQLAlchemy + PostgreSQL + Redis | Vue 3 + Vite + Pinia + Tailwind CSS 4 | Playwright (100+ E2E spec files) + Vitest + pytest

**Production:** https://algochanakya.com (Windows Server 2022, PM2, Nginx/Cloudflare) - App not production-ready yet

**Documentation:** See [docs/README.md](docs/README.md) for architecture, API reference, and testing guides.

## Development Commands

### Backend (from `backend/`)

```bash
venv\Scripts\activate          # Activate venv (Windows)
python run.py                  # Start server (auto-downloads instruments if DB empty)
alembic upgrade head           # Apply migrations (run after git pull)
pytest tests/ -v               # Run backend tests
pytest tests/ -v --cov=app     # With coverage
pytest tests/ -m unit -v       # Unit tests only
pytest tests/ -m "not slow" -v # Skip slow tests
pytest tests/test_file.py::test_function -v  # Single test function
# Markers: @unit, @api, @integration, @slow
```

### Frontend (from `frontend/`)

```bash
npm run dev           # Development server
npm run build         # Production build
npm run test          # Unit tests (watch mode)
npm run test:run      # Unit tests (once)
npm run test:coverage # Unit tests with coverage
```

### E2E Tests (from project root)

```bash
npm test                           # All tests (auto-login via SmartAPI)
npm run test:specs:{screen}        # By screen: login, dashboard, positions, watchlist, optionchain, strategy, strategylibrary, autopilot, navigation, audit, ofo
npm run test:happy                 # All happy path tests
npm run test:edge                  # All edge case tests
npm run test:headed                # With visible browser
npm run test:debug                 # Debug mode
npm run test:ui                    # Interactive UI mode for debugging
npm run test:audit                 # Accessibility audits
npm run test:isolated              # Tests needing fresh context (login, OAuth)
npx playwright test path/to/spec  # Single file

# AutoPilot-specific tests
npm run test:autopilot:fast        # Fast AutoPilot tests (4 workers, 15s timeout)
npm run test:autopilot:phase4      # Phase 4 tests
npm run test:autopilot:phases123   # Phases 1-3 tests

# Allure reporting
npm run test:allure                # Run tests + generate Allure report + open
npm run allure:serve               # Serve existing allure results

# Test generation
npm run generate:test              # Generate new test from template
```

## Architecture Overview

**Key Modules:**
- **Broker Abstraction** - Dual system: Market data brokers (SmartAPI, planned: Kite/Upstox) + Order execution brokers (Kite implemented, planned: Angel/Upstox). Factory pattern with unified data models (`UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote`). See [Multi-Broker Architecture](#core-purpose-multi-broker-architecture).
- **Authentication** - SmartAPI with auto-TOTP (default) or Zerodha OAuth. JWT stored in localStorage + Redis. Use `get_current_user` / `get_current_broker_connection` dependencies. SmartAPI credentials stored encrypted in `smartapi_credentials` table.
- **WebSocket Live Prices** - Dev: `ws://localhost:8001/ws/ticks?token=<jwt>` | Prod: `wss://algochanakya.com/ws/ticks?token=<jwt>`. SmartAPI ticker (default) and KiteTickerService (both singleton). Index tokens: NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801, SENSEX=265
- **Option Chain** - IV via Newton-Raphson, Greeks via Black-Scholes. Max Pain, PCR calculated.
- **Strategy Builder** - P/L modes: "At Expiry" (intrinsic) and "Current" (Black-Scholes via scipy)
- **AutoPilot** - Automated execution with conditions, adjustments, kill switch. 16 database tables. See [docs/autopilot/](docs/autopilot/)
- **AI Module** - Market regime (6 types), risk states (GREEN/YELLOW/RED), trust ladder (Sandbox→Supervised→Autonomous). Paper trading graduation: 15 days + 25 trades + 55% win rate. Key tables: `ai_user_config`, `ai_decisions_log`, `ai_model_registry`, `ai_learning_reports`. See [docs/ai/](docs/ai/)
- **SmartAPI Integration** (Default Market Data) - AngelOne SmartAPI is the **default market data source** for live WebSocket prices and historical OHLC. Kite remains for order execution. Uses auto-TOTP (no manual TOTP entry). Credentials stored encrypted in `smartapi_credentials` table. Key files: `backend/app/services/legacy/smartapi_auth.py` (auth with auto-TOTP), `legacy/smartapi_ticker.py` (WebSocket V2), `legacy/smartapi_historical.py` (OHLC), `backend/app/api/routes/smartapi.py` (endpoints), `frontend/src/components/settings/SmartAPISettings.vue` (UI). API: `POST /api/smartapi/authenticate`, `GET/POST /api/smartapi/credentials`, `POST /api/smartapi/test-connection`.

**Database:** Async PostgreSQL (asyncpg) + Redis for sessions. Run `alembic upgrade head` after git pull.

**Key Services:**
- **Broker Adapters (Order Execution):**
  - `app/services/brokers/base.py` - `BrokerAdapter` interface, unified data models
  - `app/services/brokers/factory.py` - `get_broker_adapter()` factory
  - `app/services/brokers/kite_adapter.py` - Zerodha order execution adapter

- **Market Data Abstraction (NEW - Phase 2 Complete):**
  - `app/services/brokers/market_data/market_data_base.py` - `MarketDataBrokerAdapter` interface
  - `app/services/brokers/market_data/ticker_base.py` - `TickerServiceBase` interface
  - `app/services/brokers/market_data/factory.py` - `get_market_data_adapter()` factory
  - `app/services/brokers/market_data/smartapi_adapter.py` - SmartAPI implementation
  - `app/services/brokers/market_data/token_manager.py` - Cross-broker token/symbol mapping
  - `app/services/brokers/market_data/rate_limiter.py` - Per-broker rate limiting
  - `app/services/brokers/market_data/symbol_converter.py` - Canonical ↔ broker symbols
  - `app/services/brokers/market_data/exceptions.py` - Market data errors

- **Legacy Market Data Services (to be replaced by adapters):**
  - `app/services/legacy/smartapi_ticker.py` - SmartAPI WebSocket V2 (default)
  - `app/services/legacy/kite_ticker.py` - Kite WebSocket (singleton, legacy)
  - `app/services/legacy/smartapi_historical.py` - Historical OHLCV data

- **AutoPilot Services (26 files):**
  - `app/services/autopilot/condition_engine.py` - Entry/adjustment condition evaluation
  - `app/services/autopilot/order_executor.py` - Order placement and execution
  - `app/services/autopilot/strategy_monitor.py` - Real-time strategy monitoring
  - `app/services/autopilot/kill_switch.py` - Emergency position exit
  - `app/services/autopilot/adjustment_engine.py` - Strategy adjustment logic
  - `app/services/autopilot/suggestion_engine.py` - Adjustment suggestions
  - (20 more services in `autopilot/` directory)

- **Options Calculation Services (8 files):**
  - `app/services/options/pnl_calculator.py` - Black-Scholes P/L calculations
  - `app/services/options/greeks_calculator.py` - Delta, gamma, theta, vega calculations
  - `app/services/options/payoff_calculator.py` - Strategy payoff diagrams
  - `app/services/options/iv_metrics_service.py` - Implied volatility metrics
  - (4 more services in `options/` directory)

**Key AI Services:**
- `app/services/ai/market_regime.py` - 6 market regime types (TRENDING_BULLISH, TRENDING_BEARISH, RANGEBOUND, VOLATILE, PRE_EVENT, EVENT_DAY)
- `app/services/ai/risk_state_engine.py` - GREEN/YELLOW/RED risk states
- `app/services/ai/strategy_recommender.py` - Strategy recommendations with regime-strategy scoring
- `app/services/ai/deployment_executor.py` - AI-driven trade execution
- `app/services/ai/kelly_calculator.py` - Kelly Criterion position sizing
- `app/services/ai/ml/` - XGBoost/LightGBM models, feature extraction, training pipeline

**OFO (Options Flow Order):** A position sizing and order flow analysis module. Backend: `app/api/routes/ofo.py`, `app/schemas/ofo.py`, `app/services/ofo_calculator.py`. Frontend: `src/components/ofo/`, `src/stores/ofo.js`, `src/views/OFOView.vue`.

**Key AI Endpoints:**
- `GET /api/v1/ai/regime/current` - Current market regime
- `GET /api/v1/ai/config/` - AI user configuration
- `GET /api/v1/ai/recommendations/` - Strategy recommendations
- `GET /api/v1/ai/risk-state/` - Current risk state (GREEN/YELLOW/RED)
- `POST /api/v1/ai/deploy/` - Deploy AI-recommended strategy
- `GET /api/v1/ai/analytics/performance` - Performance metrics
- `POST /api/v1/ai/backtest/run` - Run historical backtest

---

## Important Patterns

### Folder Structure Rules (ENFORCED by hooks)

**Backend Services Organization** (`backend/app/services/`):
- **Allowed at root:** ONLY `__init__.py`, `instruments.py`, `ofo_calculator.py`, `option_chain_service.py`
- **All other services MUST be in subdirectories:**
  - `autopilot/` - AutoPilot services (26 files): kill_switch, condition_engine, order_executor, strategy_monitor, adjustment_engine, etc.
  - `options/` - Options calculation services (8 files): greeks_calculator, pnl_calculator, payoff_calculator, iv_metrics_service, theta_curve_service, gamma_risk_service, expected_move_service, oi_analysis_service
  - `legacy/` - Legacy broker services (8 files, to be deprecated): smartapi_auth, smartapi_ticker, smartapi_market_data, smartapi_historical, smartapi_instruments, kite_orders, kite_ticker, market_data
  - `ai/` - AI services: market_regime, risk_state_engine, strategy_recommender, deployment_executor, etc.
  - `brokers/` - Broker adapters: base, factory, kite_adapter, market_data/

**Frontend Organization**:
- **CSS files:** MUST be in `frontend/src/assets/styles/` (NOT `assets/css/`)
- **Image files:** MUST be in `frontend/src/assets/logos/` (NOT `assets/` root)
- **API code:** MUST be in `frontend/src/services/` (NOT `composables/` unless it's a Vue composable)

**Test Organization**:
- **E2E tests:** MUST be in `tests/e2e/specs/{screen}/` subdirectories (NOT `tests/e2e/specs/` root)
- **Manual scripts:** MUST be in `tests/e2e/scripts/` (NOT `tests/e2e/` root)
- **Backend tests:** MUST be in `tests/backend/{module}/` (NOT `backend/` root)

**Enforcement:**
- Git pre-commit hook (`.git/hooks/pre-commit`) blocks commits violating rules
- See `.claude/recommended-hooks.json` for Claude Code PostToolUse hook configuration
- CI/CD pipelines validate folder structure before deployment

### Broker Abstraction (CRITICAL)

**NEVER directly use broker-specific APIs (KiteConnect, SmartAPI client).** Always use broker adapters and factories:

```python
# Backend - Order Execution
from app.services.brokers.factory import get_broker_adapter
adapter = get_broker_adapter(user.order_broker_type, credentials)
order = await adapter.place_order(...)  # Returns UnifiedOrder

# Backend - Market Data (Phase 2 Complete - Use This!)
from app.services.brokers.market_data.factory import get_market_data_adapter
data_adapter = get_market_data_adapter(user.market_data_broker_type, credentials)
quote = await data_adapter.get_live_quote(symbol)  # Returns UnifiedQuote
historical = await data_adapter.get_historical_data(symbol, from_date, to_date, interval)

# Backend - Token/Symbol Conversion (NEW)
from app.services.brokers.market_data.token_manager import token_manager
broker_token = await token_manager.get_broker_token("NIFTY 26 DEC 24000 CE", "smartapi")
canonical_symbol = await token_manager.get_canonical_symbol(256265, "smartapi")
```

**Unified Data Models** - All broker adapters convert to/from these broker-agnostic models:
- `UnifiedOrder` - Normalized order structure (order_id, tradingsymbol, side, status, etc.)
- `UnifiedPosition` - Normalized position (tradingsymbol, quantity, pnl, average_price, etc.)
- `UnifiedQuote` - Normalized quote (last_price, ohlc, volume, bid/ask, etc.)

See `backend/app/services/brokers/base.py` and `backend/app/services/brokers/market_data/market_data_base.py` for complete definitions.

**Important:** All symbol references must use **canonical format** (Kite format) internally. Use `SymbolConverter` to translate broker-specific symbols.

### Trading Constants (CRITICAL)

**NEVER hardcode lot sizes, strike steps, or index tokens.** Always use centralized constants:

```python
# Backend
from app.constants.trading import get_lot_size, get_strike_step
lot_size = get_lot_size("NIFTY")  # 25
```

```javascript
// Frontend - loaded from backend API on app init
// File: frontend/src/constants/trading.js
import { getLotSize, getStrikeStep, useTradingConstants } from '@/constants/trading'

// Direct function calls
const lotSize = getLotSize('NIFTY')  // 25

// Or use the composable for reactive access
const { LOT_SIZES, STRIKE_STEPS, loadTradingConstants } = useTradingConstants()
```

**Note:** Frontend constants are fetched from `/api/constants/trading` on app initialization. The file contains fallback defaults that match backend values.

### Adding New Database Models

1. Create in `backend/app/models/<name>.py` (inherit from `Base`)
2. Import in `backend/app/models/__init__.py`
3. Import in `backend/alembic/env.py` (required for autogenerate)
4. Run: `alembic revision --autogenerate -m "description" && alembic upgrade head`

### Broker Abstraction Database Tables

**`broker_instrument_tokens`** (NEW - Added Jan 2026) - Cross-broker token/symbol mapping:
- Stores canonical symbol (Kite format) mapped to broker-specific symbols and tokens
- Enables token/symbol conversion across all supported brokers
- Indexed on `canonical_symbol`, `broker`, `broker_symbol`, `broker_token`, `expiry`
- Unique constraint: `(canonical_symbol, broker)`
- Used by `TokenManager` for efficient lookups

**`user_preferences`** - User broker selection (columns added):
- `market_data_source` - Which broker for market data (smartapi, kite, upstox, dhan, fyers, paytm)
- Constraint updated to support 6 brokers (migration: `bc0dd372730d`)

**`smartapi_credentials`** - Encrypted SmartAPI credentials for auto-TOTP authentication

### Adding New API Routes

1. Create `backend/app/api/routes/<name>.py` with `router = APIRouter()`
2. Include in `backend/app/main.py`
3. Use `Depends(get_current_user)` for authentication

### Environment Variables

**Setup:** Copy `.env.example` files to `.env` and update with actual values:
- `backend/.env.example` → `backend/.env`
- `frontend/.env.example` → `frontend/.env`

**Backend (`backend/.env`):** `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_HOURS`, `KITE_API_KEY`, `KITE_API_SECRET`, `KITE_REDIRECT_URL`, `ANTHROPIC_API_KEY` (for AI), `ANGEL_API_KEY` (for SmartAPI market data), `FRONTEND_URL`

**Frontend (`frontend/.env`):** `VITE_API_BASE_URL=http://localhost:8001` (dev port), `VITE_WS_URL=ws://localhost:8001` (optional, defaults to API URL)

**Frontend Local Override (`frontend/.env.local`):** Overrides `.env` for local development. **CRITICAL:** Must point to `http://localhost:8001` for dev backend. Common mistake: pointing to wrong port (8005, 8000). This file is git-ignored. **Note:** `.env.example` shows port 8000 (production default) - manually change to 8001 for development.

**Production Build:** Create `frontend/.env.production` with `VITE_API_BASE_URL=https://algochanakya.com` before `npm run build` - without this, API calls default to localhost!

### Encryption for Credentials

Use `backend/app/utils/encryption.py` for encrypting sensitive stored credentials:

```python
from app.utils.encryption import encrypt, decrypt
encrypted = encrypt("sensitive_data")
decrypted = decrypt(encrypted)
```

### Rate Limiting for Broker APIs (NEW)

Market data adapters automatically handle broker-specific rate limits via `RateLimiter`:

```python
from app.services.brokers.market_data.rate_limiter import RateLimiter

# Automatically enforced by adapters - no manual intervention needed
# SmartAPI: 1 request per second
# Kite: 3 requests per second
# Upstox/Dhan/Fyers: 10 requests per second

# Rate limiter is singleton per broker, handles concurrent requests automatically
```

**Important:** Don't bypass the adapter to avoid rate limiting - it will cause API bans!

### Authentication Error Handling

**Backend:** All authenticated endpoints use `get_current_user` / `get_current_broker_connection` dependencies that return 401 on:
- Invalid/expired JWT token
- Invalid/expired Kite access token (broker `access_token` fails)

**Frontend:** The axios interceptor in `frontend/src/services/api.js` handles 401 responses by:
1. Clearing `access_token` from localStorage
2. Redirecting to `/login`

**Key Files:**
- `backend/app/utils/dependencies.py` - Auth dependencies (`get_current_user`, `get_current_broker_connection`)
- `frontend/src/services/api.js` - HTTP interceptor (lines 27-35)
- `frontend/src/stores/auth.js` - Auth state management

### Learning Engine (Autonomous Fix Loop)

The learning engine at `.claude/learning/knowledge.db` records every error and fix attempt, ranks strategies by success rate with time decay, and auto-synthesizes rules when patterns reach ≥70% confidence with ≥5 evidence instances.

**Three Core Loops:**
- **Pre-check:** Before fixing, query knowledge.db for ranked strategies
- **Post-record:** After every fix attempt, record outcome and update scores
- **Feedback:** On session start, check git for reverts that invalidate past fixes

**Stuck Conditions (Stop and ask user):**
- Same error 3x with different strategies failing
- All strategies exhausted (scores < 0.1)
- 20 total attempts in session
- Fix requires modifying files outside feature scope
- Error type completely unknown

**Commands:**
```bash
/learning-engine status          # Show knowledge DB stats
/learning-engine query {type}    # Show strategies for error type
/learning-engine risk-report     # Top 10 error-prone files
/learning-engine synthesize      # Force rule synthesis check
```

**Integration:** Automatically integrated with `auto-verify` (Step 2c, Step 8) and `test-fixer` (Step 0, post-fix recording). Runs on session start (feedback loop) and end (synthesis check).

**Storage:** SQLite database at `.claude/learning/knowledge.db` with 6 tables: error_patterns, fix_strategies, fix_attempts, file_risk_scores, synthesized_rules, session_metrics.

---

## Documentation

**⭐ PRIMARY DOCS FOR IMPLEMENTATION:**
1. **[Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md)** - All docs organized by task (NEW - use this first!)
2. **[Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md)** - Current implementation tasks with docs links
3. **[Broker Abstraction Architecture](docs/architecture/broker-abstraction.md)** - Primary architecture (multi-broker)
4. **[Multi-Broker Ticker Architecture](docs/decisions/003-multi-broker-ticker-architecture.md)** - ADR for ticker refactoring (Proposed)
   - [Implementation Guide](docs/architecture/multi-broker-ticker-implementation.md) - Step-by-step implementation plan
   - [API Reference](docs/api/multi-broker-ticker-api.md) - Complete API documentation for ticker system

**⚠️ Stale Docs Warning:** `docs/IMPLEMENTATION-CHECKLIST.md` may be outdated. CLAUDE.md contains the authoritative implementation status.

**Feature Registry:** `docs/feature-registry.yaml` maps code files to features. After code changes, use `docs-maintainer` skill to update docs automatically.

**Feature Docs:** `docs/features/{feature}/` with README.md, REQUIREMENTS.md, CHANGELOG.md for each feature.

**Architecture Docs:** `docs/architecture/` - Complete system design (authentication, WebSocket, database, broker abstraction)

## Claude Code Skills

Use these skills for faster, consistent results:

| Skill | Usage | Proactive? |
|-------|-------|------------|
| `auto-verify` | After ANY code change | **YES** |
| `docs-maintainer` | After code changes | **YES** |
| `learning-engine` | Autonomous fix loop with knowledge base | **YES** (integrated with auto-verify/test-fixer) |
| `health-check` | Proactive codebase health scan (7 steps) | On demand + session start |
| `test-fixer` | Diagnose failing tests | On demand |
| `e2e-test-generator` | Generate Playwright tests | On demand |
| `vitest-generator` | Generate Vitest unit tests | On demand |
| `vue-component-generator` | Create Vue 3 components/Pinia stores | On demand |
| `autopilot-assistant` | AutoPilot strategy config guidance | On demand |
| `trading-constants-manager` | Enforce centralized trading constants | On demand |
| `claude-chrome-testing` | Browser-based debugging with Playwright MCP | On demand |
| `save-session` | Save context for later: /save-session [name] | On demand |
| `start-session` | Resume saved session: /start-session [name] | On demand |
| `smartapi-expert` | SmartAPI (Angel One) API guidance | On demand |
| `kite-expert` | Kite Connect (Zerodha) API guidance | On demand |
| `upstox-expert` | Upstox API guidance | On demand |
| `dhan-expert` | Dhan API guidance | On demand |
| `fyers-expert` | Fyers API guidance | On demand |
| `paytm-expert` | Paytm Money API guidance | On demand |

> **Broker API Experts:** 6 consultative skills for API guidance, code auditing, and cross-broker comparison. Shared comparison matrix at `.claude/skills/broker-shared/comparison-matrix.md`.

---

## Autonomous Testing Workflow

**AlgoChanakya has a fully autonomous testing system** with slash commands, hooks, sub-agents, and self-learning capabilities. This system enforces test-driven development, prevents broken commits, and continuously improves fix strategies.

### Slash Commands (Orchestration)

Commands orchestrate skills and agents to execute complex workflows:

| Command | Usage | Skills Called | Agents Called |
|---------|-------|---------------|---------------|
| `/implement` | 7-step mandatory workflow for features | auto-verify, e2e-test-generator, vitest-generator, fix-loop, post-fix-pipeline, docs-maintainer | code-reviewer, debugger, git-manager |
| `/fix-loop` | Iterative fix cycle with thinking escalation | test-fixer | code-reviewer, debugger |
| `/post-fix-pipeline` | Final verification + commit | fix-loop (on failure), docs-maintainer | tester, git-manager |
| `/run-tests` | Multi-layer test runner (E2E, backend, frontend) | fix-loop (on failure), post-fix-pipeline (if fixes), reflect | - |
| `/fix-issue` | Fix GitHub issue with full workflow | implement, fix-loop, post-fix-pipeline | planner-researcher (complex), all from /implement |
| `/reflect` | Learning + self-modification (4 modes) | - | - |

**Invoke commands via Skill tool:**
```
Skill("implement")
Skill("fix-loop")
Skill("reflect", args="session")
```

### Sub-Agents (Specialized Tasks)

Agents are invoked by commands for specific tasks:

| Agent | Model | Purpose | Invoked By |
|-------|-------|---------|------------|
| `tester` | sonnet | Run/analyze all 3 test layers, detect flaky tests, report coverage | /post-fix-pipeline, /run-tests |
| `code-reviewer` | inherit | Quality gate - validates broker abstraction, trading constants, folder structure, security | /fix-loop (every fix) |
| `debugger` | sonnet | Root cause analysis with ThinkHard/UltraThink escalation | /fix-loop (attempt 2+) |
| `git-manager` | haiku | Safe commits with conventional format, secret scanning, protected files | /post-fix-pipeline |
| `planner-researcher` | opus | Design implementation plans for complex features, architecture decisions | /implement (complex), user ad-hoc |

**Agents are read-only** (except git-manager for git operations).

### Hook Enforcement

**PreToolUse hooks BLOCK:**
- Write/Edit test files before Step 1 (requirements) complete
- Write/Edit code files before Step 2 (tests) complete
- `git commit` before all 7 steps complete AND post-fix-pipeline invoked
- `git commit` if tests failed but fix-loop never invoked
- `git commit` if fixes applied but post-fix-pipeline never invoked

**PostToolUse hooks RECORD:**
- Test results (pass/fail counts, layers, targets)
- Skill invocations (success/failure, duration)
- Independently re-run tests to verify claims (blocks false positives)
- Auto-resize screenshots > 1800px
- Scan for unfixed auto-fix patterns from knowledge.db
- Route skill outcomes to learning systems

**Hook scripts:** `.claude/hooks/*.py` (9 Python scripts)

### Workflow State

Hooks maintain workflow state in `.claude/workflow-state.json`:
- **Session tracking:** sessionId, activeCommand, lastActivity
- **Step completion:** 7 steps (requirements, tests, implement, runTests, fixLoop, screenshots, verify)
- **Skill invocations:** fixLoopInvoked, fixLoopCount, fixLoopSucceeded, postFixPipelineInvoked
- **Evidence:** testRuns with timestamps, commands, results, independent verification

Workflow state enables commit gates: hooks check state to enforce that:
1. All 7 steps completed before commit
2. fix-loop invoked if tests ever failed
3. post-fix-pipeline invoked before commit

### Hybrid Learning System

**Two complementary learning stores:**

1. **knowledge.db (SQLite)** - Authoritative, structured learning:
   - 6 tables: error_patterns, fix_strategies, fix_attempts, file_risk_scores, synthesized_rules, session_metrics
   - 11 seeded strategies with success rates (time-decayed)
   - Strategy ranking: Recent outcomes weighted 2x more than old
   - Synthesis: Auto-generates rules when patterns reach ≥70% confidence with ≥5 evidence instances
   - Queried by: /fix-loop (pre-check), /reflect (synthesis)

2. **failure-index.json** - Fast JSON overlay for hooks:
   - Per-skill failure tracking with occurrences, workarounds, thresholds
   - Escalation: Flags patterns with 5+ failures for manual review
   - Auto-fix eligibility: Patterns with ≥70% success rate
   - Queried by: Hooks (fast lookups), /implement (pre-execution)

**/reflect command** reconciles both stores:
- **session mode** (default): Capture outcomes, update knowledge.db, synthesize rules (safe, no file mods)
- **deep mode**: Analyze gaps + modify commands/hooks with safety protocol (git stash, validation, revert on fail)
- **meta mode**: High-level convergence analysis, pattern detection across modifications
- **test-run mode**: Dry-run of deep mode (propose but don't apply)

### Autonomous Features Summary

✅ **Zero manual intervention** - Hooks enforce workflow automatically
✅ **Test-driven** - Cannot write code before tests (enforced by hooks)
✅ **Self-verifying** - Independent test re-runs catch false positives
✅ **Self-learning** - Strategies improve via knowledge.db with time decay
✅ **Self-modifying** - /reflect deep mode can update hooks/commands (with safety)
✅ **Quality gates** - code-reviewer validates every fix before applying
✅ **Safe commits** - Secret scanning, protected files, conventional format
✅ **Escalation** - 5+ failures trigger manual review prompt

**Key files:**
- Commands: `.claude/commands/*.md` (6 files)
- Hooks: `.claude/hooks/*.py` (9 files)
- Agents: `.claude/agents/*.md` (5 files)
- Learning: `.claude/learning/knowledge.db`, `.claude/logs/learning/failure-index.json`
- State: `.claude/workflow-state.json`, `.claude/logs/workflow-sessions.log`

---

## Key URLs

Dashboard `/dashboard`, Watchlist `/watchlist`, Positions `/positions`, Option Chain `/optionchain`, Strategy `/strategy`, Strategy Library `/strategies`, AutoPilot `/autopilot`, AI `/ai`, OFO `/ofo`, Settings `/settings`

**Console Prefixes:** `[AutoPilot WS]`, `[OptionChain]`, `[Strategy]`, `[AI Regime]`, `[AI Risk]`

---

## Testing

~186 test files (123 E2E spec files + 63 backend pytest files). See [docs/testing/README.md](docs/testing/README.md) for complete documentation.

**Config:** 30s default timeout (playwright.config.js), 2 parallel workers for stability, auth state reused via `./tests/config/.auth-state.json`. Auth token stored in `./tests/config/.auth-token`. Projects: `setup` (SmartAPI auto-login), `chromium` (main), `isolated` (fresh context). **SmartAPI auto-TOTP** - no manual TOTP entry required. **Note:** Some legacy tests use longer timeouts (180s-600s) specified in npm scripts.

### E2E Test Rules (CRITICAL)

- **Use `data-testid` ONLY** - no CSS classes, tags, or text selectors
- **Import from `auth.fixture.js`** (NOT `@playwright/test`)
- **Use `authenticatedPage` fixture** for authenticated tests
- **Extend `BasePage.js`** for Page Objects with `this.url` property
- **data-testid convention:** `[screen]-[component]-[element]` (e.g., `positions-exit-modal`)
- **Headless mode:** `playwright.config.js` sets `headless: false` by default for better debugging. Use `--headed` flag is not needed in npm scripts.

### Test Categories

- `*.happy.spec.js` - Normal flows
- `*.edge.spec.js` - Error/boundary cases
- `*.visual.spec.js` - Screenshots
- `*.api.spec.js` - API validation
- `*.audit.spec.js` - a11y/CSS audits

---

## Common Pitfalls

### Git & File System
- **File path encoding issues** - If `git status` shows files with escaped characters (e.g., `\357\200\272`), this indicates UTF-8 encoding issues in Windows paths with colons. Use `git status --porcelain` for cleaner output or investigate file system encoding.

### Backend
- **Direct broker API usage** - NEVER import `KiteConnect` or `SmartAPI` directly. Use broker adapters from `app.services.brokers/` and market data adapters from `app.services.brokers.market_data/`
- **Hardcoded broker assumptions** - Don't assume Kite or SmartAPI; code should work with any broker via abstraction
- **Bypassing market data abstraction** - Use `get_market_data_adapter()` instead of directly calling `SmartAPIMarketData`, `SmartAPIHistorical`, etc.
- **Symbol format confusion** - Always use canonical format (Kite format) internally; use `SymbolConverter` for broker-specific symbols
- **Token lookup without TokenManager** - Use `token_manager.get_broker_token()` instead of manual lookups; it handles caching and cross-broker mapping
- **Broker name mismatch** - BrokerConnection stores 'zerodha'/'angelone' but BrokerType uses 'kite'/'angel'. Use the broker name mapping utility when converting between DB values and enum values.
- **Forgot to import model in `alembic/env.py`** - Autogenerate won't detect it
- **Sync database operations** - All SQLAlchemy must use `async/await`
- **Hardcoded trading constants** - Use `app.constants.trading` instead
- **Mixing broker concerns** - Keep market data separate from order execution (dual system)

### Frontend
- **Missing `data-testid`** - Required for E2E tests; use `[screen]-[component]-[element]`
- **WebSocket not cleaned up** - Close subscriptions in `onUnmounted()`
- **Direct Kite API calls** - All broker operations go through backend
- **Wrong backend port in `.env.local`** - Frontend `.env.local` overrides `.env`. Must point to `http://localhost:8001` for dev, not 8005 or 8000
- **AngelOne login timeout** - AngelOne auth with auto-TOTP takes 20-25 seconds. Default axios timeout (10s) is too short. Use `timeout: 35000` in POST request to `/api/auth/angelone/login`

### Testing
- **Wrong import** - Use `auth.fixture.js`, NOT `@playwright/test`
- **CSS/text selectors** - Use `data-testid` only

---

## Troubleshooting Common Errors

**Error Messages and Solutions** - Quick fixes for frequently encountered issues:

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `ModuleNotFoundError: No module named 'app'` | Backend venv not activated | Run `venv\Scripts\activate` in `backend/` |
| `Connection refused [Errno 61]` or `[Errno 111]` | Backend not running | Start backend: `cd backend && python run.py` |
| `401 Unauthorized` | Expired JWT or broker token | Re-login via `/login` in frontend |
| `403 Forbidden` on broker API | Invalid/expired broker credentials | Re-authenticate (SmartAPI auto-refreshes, Kite needs OAuth) |
| `Incorrect api_key or access_token` | SmartAPI/Kite token expired | SmartAPI: auto-refreshes. Kite: re-login via OAuth |
| `Target page, context or browser has been closed` | Playwright test timeout | Increase timeout or fix test. Check `playwright.config.js` |
| `ECONNREFUSED 127.0.0.1:5432` | PostgreSQL not running | Start PostgreSQL service |
| `ECONNREFUSED 127.0.0.1:6379` | Redis not running | Start Redis service: `redis-server` |
| `relation "table_name" does not exist` | Missing database migration | Run `alembic upgrade head` in `backend/` |
| `no pg_hba.conf entry for host` | PostgreSQL blocking IP | Whitelist IP in PostgreSQL `pg_hba.conf` |
| File path encoding issues (e.g., `\357\200\272`) | UTF-8 encoding in Windows paths | Use `git status --porcelain` or fix file system encoding |
| `npm ERR! ENOENT: no such file or directory` | node_modules not installed | Run `npm install` in `frontend/` |
| `Cannot find module '@/...'` | Frontend path alias not resolved | Check Vite config, restart dev server |
| `WebSocket connection failed` | Wrong WS URL or backend down | Check `.env.local` has correct WS URL, ensure backend running |
| `Database connection pool exhausted` | Too many concurrent connections | Check for unclosed connections, increase pool size |
| `Rate limit exceeded` | Too many broker API calls | Adapters handle this automatically - don't bypass them |
| `alembic.util.exc.CommandError` | Alembic config issue | Check `alembic.ini` and `DATABASE_URL` in `.env` |
| `playwright: command not found` | Playwright not installed | Run `npm install` in project root |
| Backend starts on wrong port (8000 instead of 8001) | Wrong `.env` configuration | Check `backend/.env` has correct `PORT=8001` |
| Frontend API calls fail with 404 | Wrong API base URL | Check `frontend/.env.local` has `VITE_API_BASE_URL=http://localhost:8001` |

**General Debugging Steps:**
1. Check if all services are running (backend, PostgreSQL, Redis)
2. Verify environment variables (`.env`, `.env.local`) have correct values
3. Run `git status && git log --oneline -5` to check current state
4. Check browser console and network tab for frontend issues
5. Check backend logs for detailed error messages
6. Use `/health-check` skill for automated codebase health scan

---

## CI/CD

GitHub Actions runs automatically on push/PR to `main` and `develop`:

| Workflow | File | Description |
|----------|------|-------------|
| **Backend Tests** | `.github/workflows/backend-tests.yml` | pytest with PostgreSQL/Redis services |
| **E2E Tests** | `.github/workflows/e2e-tests.yml` | Playwright with full stack (30min timeout) |

Allure reports deploy to GitHub Pages on main branch merges.

---

## Debug Commands

```bash
curl http://localhost:8001/api/health          # Check dev backend health (8001)
npx playwright test path/to/spec --debug       # Debug E2E test
npx playwright show-trace trace.zip            # View trace
```

```javascript
// Browser console - test WebSocket (dev on port 8001)
const ws = new WebSocket('ws://localhost:8001/ws/ticks?token=YOUR_JWT')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
ws.send(JSON.stringify({action: 'subscribe', tokens: [256265], mode: 'quote'}))

// Production (use wss:// for HTTPS, port 8000)
const ws = new WebSocket('wss://algochanakya.com/ws/ticks?token=YOUR_JWT')
```

---

## Production Debugging

**IMPORTANT:** Production runs on the SAME machine as development. **NEVER interfere with production processes or files.**

| Environment | Path | Port |
|-------------|------|------|
| **Development** | `D:\Abhay\VibeCoding\algochanakya` | Backend: 8001, Frontend: 5173 |
| **Production** | `C:\Apps\algochanakya` (DO NOT TOUCH) | Backend: 8000, Frontend: 3004 |

**Server:** Windows Server 2022 (544934-ABHAYVPS) | https://algochanakya.com

**PM2 Logs (read-only observation only):**
```bash
pm2 logs algochanakya-backend    # Backend logs
pm2 logs algochanakya-frontend   # Frontend logs (static serve)
# NEVER run pm2 restart - ask user to do it manually
```

**Common Production Issues:**
- **API calls fail:** Check `frontend/.env.production` has `VITE_API_BASE_URL=https://algochanakya.com`
- **OAuth fails:** Verify Kite redirect URL = `https://algochanakya.com/api/auth/zerodha/callback`
- **"Incorrect api_key or access_token":** SmartAPI token expired (8h) or Kite access token expired (24h). SmartAPI auto-refreshes via stored credentials; Kite requires re-login via OAuth.
- **WebSocket won't connect:** Check `VITE_WS_URL` in `.env.production`, ensure wss:// for HTTPS
- **Backend won't start - Database connection refused:** PostgreSQL server blocking your IP. Error: `no pg_hba.conf entry for host`. Solution: Whitelist your current IP in PostgreSQL `pg_hba.conf` on the database server.
- **AngelOne login shows "Failed to login":** Either backend not running on correct port (check 8001 not 8005/8000), or request timeout (login takes 20-25s, needs 35s timeout)

**Full deployment docs:** `C:\Apps\shared\docs\ALGOCHANAKYA-SETUP.md` on VPS
