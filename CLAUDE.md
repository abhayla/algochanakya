# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Mandatory Behaviors

### 0. Production vs Development - NEVER TOUCH PRODUCTION

**Development folder:** `C:\Abhay\VideCoding\algochanakya` - Work ONLY here
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

**IMPORTANT:** Production runs on port 8000. Development defaults to port **8001**.

```bash
# Start dev backend (from backend/) - defaults to port 8001
venv\Scripts\activate && python run.py    # Windows
source venv/bin/activate && python run.py # Linux/Mac

# Start frontend (from frontend/) - defaults to localhost:5173
npm run dev

# Run all E2E tests (from root) - uses dev backend on 8001
npm test

# Run single test file
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js

# Run tests by screen
npm run test:specs:positions    # By screen: positions, optionchain, strategy, strategylibrary, autopilot, navigation, audit, login, dashboard, watchlist, ofo, header
npm run test:specs:header       # Header component tests (index prices, etc.)
npm run test:main-features      # Dashboard, OptionChain, OFO, Strategy, StrategyLibrary together
npm run test:deploy             # Tests with @deploy tag (strategy deployment)
npm run test:visual             # Visual regression tests
npm run test:visual:update      # Update visual snapshots

# Database migration (from backend/)
alembic revision --autogenerate -m "description" && alembic upgrade head

# Backend tests
cd backend && pytest tests/ -v
```

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

| Broker | Market Data | Order Execution | Status |
|--------|-------------|-----------------|--------|
| **Angel One** (SmartAPI) | FREE | FREE | In Progress (Default for data) |
| **Zerodha** (Kite Connect) | ₹500/mo | FREE | Implemented (orders only) |
| **Upstox** | FREE | FREE | Planned |
| **Fyers** | FREE | FREE | Planned |
| **Alice Blue** (ANT API) | FREE | FREE | Planned |
| **Kotak** (Neo API) | FREE | FREE | Planned |
| **Dhan** | FREE or ₹499/mo* | FREE | Planned |
| **Paytm Money** | FREE | FREE | Planned |
| **Samco** | FREE | FREE | Planned |
| **Shoonya/Finvasia** | FREE | FREE | Planned (Zero brokerage) |
| **Pocketful** | FREE | FREE | Planned |
| **TradeSmart** | FREE | FREE | Planned |
| **ICICI Direct** (Breeze) | FREE (limited) | FREE | Planned |

**Notes:**
- **Zerodha:** "Connect" tier (₹500/mo for data+orders) vs "Personal" tier (FREE for orders only)
- **Dhan:** FREE if 25 F&O trades/month, else ₹499/month + taxes
- All order execution APIs are FREE (use user's funded broker account)

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

**🚧 Phase 3-5 To Be Implemented:**
- Refactor routes to use broker factories instead of hardcoded services
- Create `KiteMarketDataAdapter` (for users who want to pay ₹500/mo for Kite data)
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
- **SmartAPI Integration** (Default Market Data) - AngelOne SmartAPI is the **default market data source** for live WebSocket prices and historical OHLC. Kite remains for order execution. Uses auto-TOTP (no manual TOTP entry). Credentials stored encrypted in `smartapi_credentials` table. Key files: `backend/app/services/smartapi_auth.py` (auth with auto-TOTP), `smartapi_ticker.py` (WebSocket V2), `smartapi_historical.py` (OHLC), `backend/app/api/routes/smartapi.py` (endpoints), `frontend/src/components/settings/SmartAPISettings.vue` (UI). API: `POST /api/smartapi/authenticate`, `GET/POST /api/smartapi/credentials`, `POST /api/smartapi/test-connection`.

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
  - `app/services/smartapi_ticker.py` - SmartAPI WebSocket V2 (default)
  - `app/services/kite_ticker.py` - Kite WebSocket (singleton, legacy)
  - `app/services/smartapi_historical.py` - Historical OHLCV data

- **Core Services:**
  - `app/services/pnl_calculator.py` - Black-Scholes P/L calculations
  - `app/services/condition_engine.py` - AutoPilot entry/adjustment evaluation

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

## Important Patterns

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
// Frontend (loaded from API on init)
import { getLotSize, getStrikeStep } from '@/constants/trading'
```

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

**Backend (`backend/.env`):** `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `KITE_API_KEY`, `KITE_API_SECRET`, `ANTHROPIC_API_KEY` (for AI), `ANGEL_API_KEY` (for SmartAPI market data)

**Frontend (`frontend/.env`):** `VITE_API_BASE_URL=http://localhost:8001` (dev port), `VITE_WS_URL=ws://localhost:8001` (optional, defaults to API URL)

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

## Documentation

**⭐ PRIMARY DOCS FOR IMPLEMENTATION:**
1. **[Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md)** - All docs organized by task (NEW - use this first!)
2. **[Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md)** - Current implementation tasks with docs links
3. **[Broker Abstraction Architecture](docs/architecture/broker-abstraction.md)** - Primary architecture (multi-broker)

**Feature Registry:** `docs/feature-registry.yaml` maps code files to features. After code changes, use `docs-maintainer` skill to update docs automatically.

**Feature Docs:** `docs/features/{feature}/` with README.md, REQUIREMENTS.md, CHANGELOG.md for each feature.

**Architecture Docs:** `docs/architecture/` - Complete system design (authentication, WebSocket, database, broker abstraction)

## Claude Code Skills

Use these skills for faster, consistent results:

| Skill | Usage | Proactive? |
|-------|-------|------------|
| `auto-verify` | After ANY code change | **YES** |
| `docs-maintainer` | After code changes | **YES** |
| `test-fixer` | Diagnose failing tests | On demand |
| `e2e-test-generator` | Generate Playwright tests | On demand |
| `vitest-generator` | Generate Vitest unit tests | On demand |
| `vue-component-generator` | Create Vue 3 components/Pinia stores | On demand |
| `autopilot-assistant` | AutoPilot strategy config guidance | On demand |
| `trading-constants-manager` | Enforce centralized trading constants | On demand |
| `save-session` | Save context for later: /save-session [name] | On demand |
| `start-session` | Resume saved session: /start-session [name] | On demand |

## Key URLs

Dashboard `/dashboard`, Watchlist `/watchlist`, Positions `/positions`, Option Chain `/optionchain`, Strategy `/strategy`, Strategy Library `/strategies`, AutoPilot `/autopilot`, AI `/ai`, OFO `/ofo`, Settings `/settings`

**Console Prefixes:** `[AutoPilot WS]`, `[OptionChain]`, `[Strategy]`, `[AI Regime]`, `[AI Risk]`

## Testing

~190 test files (123 E2E spec files + 67 backend pytest files). See [docs/testing/README.md](docs/testing/README.md) for complete documentation.

**Config:** 180s timeout, 1 worker (sequential), auth state reused via `./tests/config/.auth-state.json`. Auth token stored in `./tests/config/.auth-token`. Projects: `setup` (SmartAPI auto-login), `chromium` (main), `isolated` (fresh context). **SmartAPI auto-TOTP** - no manual TOTP entry required.

### E2E Test Rules (CRITICAL)

- **Use `data-testid` ONLY** - no CSS classes, tags, or text selectors
- **Import from `auth.fixture.js`** (NOT `@playwright/test`)
- **Use `authenticatedPage` fixture** for authenticated tests
- **Extend `BasePage.js`** for Page Objects with `this.url` property
- **data-testid convention:** `[screen]-[component]-[element]` (e.g., `positions-exit-modal`)

### Test Categories

- `*.happy.spec.js` - Normal flows
- `*.edge.spec.js` - Error/boundary cases
- `*.visual.spec.js` - Screenshots
- `*.api.spec.js` - API validation
- `*.audit.spec.js` - a11y/CSS audits

## Common Pitfalls

### Backend
- **Direct broker API usage** - NEVER import `KiteConnect` or `SmartAPI` directly. Use broker adapters from `app.services.brokers/` and market data adapters from `app.services.brokers.market_data/`
- **Hardcoded broker assumptions** - Don't assume Kite or SmartAPI; code should work with any broker via abstraction
- **Bypassing market data abstraction** - Use `get_market_data_adapter()` instead of directly calling `SmartAPIMarketData`, `SmartAPIHistorical`, etc.
- **Symbol format confusion** - Always use canonical format (Kite format) internally; use `SymbolConverter` for broker-specific symbols
- **Token lookup without TokenManager** - Use `token_manager.get_broker_token()` instead of manual lookups; it handles caching and cross-broker mapping
- **Forgot to import model in `alembic/env.py`** - Autogenerate won't detect it
- **Sync database operations** - All SQLAlchemy must use `async/await`
- **Hardcoded trading constants** - Use `app.constants.trading` instead
- **Mixing broker concerns** - Keep market data separate from order execution (dual system)

### Frontend
- **Missing `data-testid`** - Required for E2E tests; use `[screen]-[component]-[element]`
- **WebSocket not cleaned up** - Close subscriptions in `onUnmounted()`
- **Direct Kite API calls** - All broker operations go through backend

### Testing
- **Wrong import** - Use `auth.fixture.js`, NOT `@playwright/test`
- **CSS/text selectors** - Use `data-testid` only

## CI/CD

GitHub Actions runs automatically on push/PR to `main` and `develop`:

| Workflow | File | Description |
|----------|------|-------------|
| **Backend Tests** | `.github/workflows/backend-tests.yml` | pytest with PostgreSQL/Redis services |
| **E2E Tests** | `.github/workflows/e2e-tests.yml` | Playwright with full stack (30min timeout) |

Allure reports deploy to GitHub Pages on main branch merges.

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

## Production Debugging

**IMPORTANT:** Production runs on the SAME machine as development. **NEVER interfere with production processes or files.**

| Environment | Path | Port |
|-------------|------|------|
| **Development** | `C:\Abhay\VideCoding\algochanakya` | Backend: 8001, Frontend: 5173 |
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

**Full deployment docs:** `C:\Apps\shared\docs\ALGOCHANAKYA-SETUP.md` on VPS
