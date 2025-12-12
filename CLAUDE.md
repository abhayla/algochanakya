# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlgoChanakya is an options trading platform (similar to Sensibull) built with FastAPI backend and Vue.js 3 frontend. The platform integrates with broker APIs (starting with Zerodha Kite Connect) for authentication and trading operations.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy (async) + PostgreSQL + Redis
- Frontend: Vue.js 3 + Vite + Pinia + Vue Router + Tailwind CSS
- Broker Integration: Zerodha Kite Connect API
- Testing: Playwright (E2E ~240 tests) + pytest (backend ~70 tests)

**Detailed Documentation:** See [docs/](docs/README.md) for comprehensive documentation including:
- [Architecture](docs/architecture/) - System design, auth, WebSocket, database
- [API Reference](docs/api/) - Endpoint documentation
- [Guides](docs/guides/) - Setup and troubleshooting
- [Testing](docs/testing/) - E2E test architecture
- [AutoPilot](docs/autopilot/) - Auto-execution system specs

## Development Commands

### Backend (from `backend/` directory)

```bash
# Activate virtual environment
venv\Scripts\activate    # Windows
source venv/bin/activate # Linux/Mac

# Start development server
python run.py

# Database migrations (Alembic)
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Frontend (from `frontend/` directory)

```bash
npm run dev      # Start development server
npm run build    # Build for production
```

### Testing (from project root)

```bash
# Run all tests (single browser, login once with TOTP)
npm test

# Run by screen
npm run test:specs:login
npm run test:specs:dashboard
npm run test:specs:positions
npm run test:specs:watchlist
npm run test:specs:optionchain
npm run test:specs:strategy
npm run test:specs:strategylibrary

# Run by category
npm run test:happy      # All happy path tests
npm run test:edge       # All edge case tests
npm run test:visual     # All visual regression tests
npm run test:api:new    # All API tests
npm run test:audit      # All style & accessibility audits
npm run test:a11y       # Alias for audit tests

# Legacy individual tests
npm run test:positions      # F&O positions tests
npm run test:optionchain    # Option chain tests
npm run test:iron-condor    # Iron Condor strategy test
npm run test:overflow       # All screens horizontal overflow test

# Run a single test file
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js

# Utilities
npm run test:headed         # Run with visible browser
npm run test:debug          # Debug mode
npm run test:visual:update  # Update visual baselines
npm run generate:test -- --screen MyScreen --path /mypath  # Generate test scaffold
```

## Architecture

### Authentication Flow

1. **OAuth Flow with Zerodha:**
   - User clicks login → Frontend calls `GET /api/auth/zerodha/login`
   - Backend generates Kite Connect login URL
   - User authenticates on Zerodha → Redirected to `GET /api/auth/zerodha/callback`
   - Backend exchanges request token for access token, creates/updates User and BrokerConnection
   - JWT token is generated and stored in Redis
   - User is redirected to frontend with JWT token

2. **Session Management:**
   - JWT tokens are stored in localStorage (frontend) and Redis (backend)
   - Tokens include `user_id` and optional `broker_connection_id`
   - Redis sessions expire based on `JWT_EXPIRY_HOURS` setting
   - Axios interceptor automatically adds `Authorization: Bearer <token>` header

3. **Protected Routes:**
   - Use `get_current_user` dependency for user authentication
   - Use `get_current_broker_connection` dependency for broker-specific operations
   - Frontend router guards check `authStore.isAuthenticated` before allowing access

### WebSocket Live Prices

The platform streams live market prices via WebSocket:

1. **Connection Flow:**
   - Frontend connects to `ws://localhost:8000/ws/ticks?token=<jwt>`
   - Backend authenticates JWT and retrieves user's Kite access token
   - KiteTickerService connects to Kite WebSocket (if not already connected)
   - Client sends subscribe messages: `{"action": "subscribe", "tokens": [256265], "mode": "quote"}`

2. **KiteTickerService (`app/services/kite_ticker.py`):**
   - Singleton service managing Kite WebSocket connection
   - Thread-safe async tick broadcasting using `asyncio.run_coroutine_threadsafe`
   - Per-user subscription management (only sends ticks user subscribed to)
   - Automatic reconnection on disconnect
   - Caches latest ticks for immediate delivery on subscribe

3. **Message Types:**
   - `connected` - Initial connection confirmation
   - `subscribed` - Subscription confirmation with tokens
   - `ticks` - Live price data: `{type: "ticks", data: [{token, ltp, change, change_percent, ...}]}`
   - `pong` - Keepalive response
   - `error` - Error messages

4. **Index Tokens:**
   - NIFTY 50: `256265`
   - NIFTY BANK: `260105`
   - FINNIFTY: `257801`

### Option Chain

Full option chain with OI, IV, Greeks, and live prices:

1. **Option Chain API (`app/api/routes/optionchain.py`):**
   - `GET /api/optionchain/chain` - Complete option chain with all data
   - `GET /api/optionchain/oi-analysis` - OI data for charts
   - Calculates IV using Newton-Raphson method
   - Calculates Greeks (Delta, Gamma, Theta, Vega) using Black-Scholes
   - Calculates Max Pain and PCR (Put-Call Ratio)

2. **Frontend (`src/views/OptionChainView.vue`):**
   - Displays CE/PE data mirrored around ATM strike
   - OI bars visualization with color coding
   - ITM highlighting (green for CE, red for PE)
   - Greeks toggle for detailed view
   - Auto-refresh with live data via store

3. **Store (`src/stores/optionchain.js`):**
   - Manages underlying, expiry, chain data
   - Fetches expiries and option chain from API
   - Integrates with Strategy Builder for adding legs

### Positions

Live F&O positions view with real-time P&L:

1. **Positions API (`app/api/routes/positions.py`):**
   - `GET /api/positions/` - Get all F&O positions with live P&L (day/net toggle)
   - `POST /api/positions/exit` - Exit a position (place opposite order)
   - `POST /api/positions/add` - Add to existing position
   - `POST /api/positions/exit-all` - Exit all open positions at market
   - `GET /api/positions/grouped` - Positions grouped by underlying or expiry

2. **Frontend (`src/views/PositionsView.vue`):**
   - Day/Net position toggle
   - Total P&L summary box with color coding
   - Summary bar: positions count, quantity, realized/unrealized P&L, margin
   - Positions table with instrument, qty, avg price, LTP, day change, P&L
   - Exit modal (Market/Limit order type)
   - Add modal (Buy/Sell at limit price)
   - Exit All confirmation dialog
   - Auto-refresh toggle (5 second interval)
   - Empty state with link to Option Chain

3. **Store (`src/stores/positions.js`):**
   - Manages positions list and summary data
   - Day/Net position type toggle
   - Exit and Add modal state
   - Auto-refresh functionality
   - API calls for exit, add, exit-all operations

### Database Models

Models in `backend/app/models/`: User, BrokerConnection, Watchlist, Instrument, Strategy, StrategyLeg, StrategyTemplate

Key relationships:
- User → BrokerConnection (one-to-many)
- User → Watchlist → Instruments (via junction table `watchlist_instruments`)
- User → Strategy → StrategyLeg (strategy legs linked to instruments)

### Strategy Builder

The platform includes a comprehensive options Strategy Builder:

1. **P/L Calculation (`app/services/pnl_calculator.py`):**
   - Two modes: "At Expiry" (intrinsic value) and "Current" (Black-Scholes)
   - Uses scipy for accurate Black-Scholes pricing (with pure Python fallback)
   - Calculates P/L grid across multiple spot prices
   - Returns max profit, max loss, and breakeven points
   - Lot sizes: NIFTY=25, BANKNIFTY=15, FINNIFTY=25, SENSEX=10

2. **P/L Grid Display (`src/views/StrategyBuilderView.vue`):**
   - Dynamic columns showing P/L at different spot prices
   - **Breakeven columns** - Breakeven points (e.g., 25758, 26242) are always included as separate columns
   - **Strike price columns** - Strike prices from legs are included as columns
   - **Current spot column** - Highlighted with blue ring
   - **Linear interpolation** - P/L values for breakeven/strike columns are interpolated when not in backend's spot array
   - Color coding: Green for profit zones, Red for loss zones

3. **Live Data Columns:**
   - **CMP (Current Market Price)** - Shows live option prices via WebSocket or LTP API fallback
   - **Exit P/L** - Calculated as `(CMP - Entry) × Qty × BuySellMultiplier`, click to manually override
   - **P/L per leg** - Shows current P/L for each leg based on CMP

4. **Options Data API (`app/api/routes/options.py`):**
   - `GET /api/options/expiries` - Available expiry dates
   - `GET /api/options/strikes` - Strike prices for expiry
   - `GET /api/options/chain` - Full option chain
   - `GET /api/options/instrument` - Get instrument by parameters

5. **Strategy API (`app/api/routes/strategy.py`):**
   - CRUD operations for strategies and legs
   - `POST /api/strategies/calculate` - P/L grid calculation
   - `POST /api/strategies/{id}/share` - Generate share link
   - `GET /api/strategies/shared/{share_code}` - Public strategy access

6. **Orders API (`app/api/routes/orders.py`):**
   - `POST /api/orders/basket` - Place basket order via Kite
   - `GET /api/orders/positions` - Get positions from broker
   - `POST /api/orders/import-positions` - Import positions as strategy
   - `GET /api/orders/ltp` - Get LTP for instruments (fallback when WebSocket unavailable)

7. **Frontend Components:** `src/components/strategy/` - StrategyHeader, StrategyLegRow, StrategyActions, modals

### Strategy Templates & Wizard

Pre-built strategy templates with AI-powered recommendations:

1. **Strategy Template Model (`app/models/strategy_templates.py`):**
   - 20+ pre-defined option strategies with educational content
   - Categories: bullish, bearish, neutral, volatile, income, advanced
   - Legs configuration (JSON), risk/reward characteristics, Greeks exposure
   - Educational fields: when_to_use, pros, cons, common_mistakes, exit_rules

2. **Strategy Wizard API (`app/api/routes/strategy_wizard.py`):**
   - `GET /api/strategy-wizard/templates` - List all templates with filters
   - `GET /api/strategy-wizard/templates/categories` - Category counts
   - `POST /api/strategy-wizard/wizard` - AI recommendation based on outlook/volatility/risk
   - `POST /api/strategy-wizard/deploy` - Deploy template with live prices
   - `POST /api/strategy-wizard/compare` - Compare multiple strategies
   - `GET /api/strategy-wizard/popular` - Most popular strategies

3. **Frontend (`src/views/StrategyLibraryView.vue`, `src/stores/strategyLibrary.js`):**
   - Category-based browsing with search
   - Strategy wizard modal (3-question flow)
   - One-click deploy to Strategy Builder
   - Strategy comparison tool
   - Details modal with educational content

4. **Seeding Templates:** `backend/scripts/seed_strategies.py` - Seeds 20+ strategy templates

### AutoPilot (Auto-Execution System)

Automated strategy execution with conditional entry, adjustments, and risk management:

1. **Database Tables (`backend/alembic/versions/001_autopilot_initial.py`):**
   - `autopilot_strategies` - Strategy configurations with entry conditions, adjustment rules
   - `autopilot_orders` - Order history with slippage tracking
   - `autopilot_logs` - Activity logs with event types and severity
   - `autopilot_templates` - Pre-built strategy templates
   - `autopilot_user_settings` - User risk limits and preferences
   - `autopilot_daily_summary` - Daily P&L and execution stats
   - `autopilot_condition_eval` - Condition evaluation snapshots

2. **AutoPilot API (`backend/app/api/v1/autopilot/`):**
   - `GET/POST /api/v1/autopilot/strategies` - Strategy CRUD
   - `POST /api/v1/autopilot/strategies/{id}/activate` - Start monitoring
   - `POST /api/v1/autopilot/strategies/{id}/pause` - Pause strategy
   - `POST /api/v1/autopilot/strategies/{id}/exit` - Force exit all positions
   - `GET /api/v1/autopilot/dashboard/summary` - Dashboard overview
   - `GET /api/v1/autopilot/orders` - Order history
   - `GET /api/v1/autopilot/logs` - Activity logs
   - `POST /api/v1/autopilot/kill-switch` - Emergency stop all

3. **AutoPilot Services (`backend/app/services/`):**
   - `market_data.py` - Market data fetching (LTP, spot prices, VIX) with caching
   - `condition_engine.py` - Entry condition evaluation (TIME, SPOT, VIX, PREMIUM variables)
   - `order_executor.py` - Order placement via Kite with sequential/simultaneous execution
   - `strategy_monitor.py` - Background service polling strategies, executing entries/exits

4. **AutoPilot WebSocket (`backend/app/websocket/`):**
   - `manager.py` - ConnectionManager for real-time updates to frontend
   - Message types: STRATEGY_UPDATE, PNL_UPDATE, CONDITION_EVALUATED, ORDER_PLACED, RISK_ALERT
   - Per-user connection tracking and strategy subscriptions

5. **Frontend (`frontend/src/views/autopilot/`):**
   - `DashboardView.vue` - Active strategies, P&L summary, activity feed
   - `StrategyBuilderView.vue` - Visual strategy configuration
   - `StrategyDetailView.vue` - Real-time monitoring, condition progress
   - `SettingsView.vue` - Risk limits, notifications, preferences

6. **Frontend Components (`frontend/src/components/autopilot/`):**
   - `dashboard/` - Summary cards, activity feed, risk gauges
   - `strategy/` - Strategy list, status badges, action buttons
   - `builder/` - Condition builder, leg configurator, schedule picker
   - `common/` - Shared widgets, confirmation dialogs

7. **Documentation:** See [docs/autopilot/README.md](docs/autopilot/README.md) for complete specs

### Key Backend Files

- `app/main.py` - FastAPI app initialization, CORS, lifespan events
- `app/config.py` - Pydantic Settings for environment variables
- `app/database.py` - SQLAlchemy async engine, session factory, Redis pool
- `app/services/kite_ticker.py` - Singleton WebSocket service for live price streaming
- `app/services/pnl_calculator.py` - Black-Scholes P/L calculations
- `app/services/market_data.py` - Market data service (LTP, spot, VIX) for AutoPilot
- `app/services/condition_engine.py` - Entry condition evaluation engine
- `app/services/strategy_monitor.py` - Background strategy monitoring and execution
- `app/services/order_executor.py` - Order placement via Kite Connect
- `app/websocket/manager.py` - WebSocket connection manager for AutoPilot
- `app/utils/dependencies.py` - `get_current_user` and `get_current_broker_connection` dependencies

### Key Frontend Files

- `src/router/index.js` - Vue Router with authentication guards
- `src/services/api.js` - Axios instance with auth header interceptor
- `src/stores/` - Pinia stores (auth, watchlist, strategy, optionchain, positions)
- `src/composables/autopilot/useWebSocket.js` - AutoPilot WebSocket composable for real-time updates

### Database Connection

- Backend uses **async PostgreSQL** via `asyncpg` driver
- Alembic migrations use standard `psycopg2` (alembic.env.py:23 converts URL)
- Redis is used for session storage and caching
- Database tables are created via SQLAlchemy metadata (app.database.py:55)
- Production uses remote PostgreSQL (103.118.16.189:5432) and Redis (103.118.16.189:6379)

## Important Patterns

### Adding New Models

1. Create model in `backend/app/models/<name>.py` inheriting from `Base`
2. Import model in `backend/app/models/__init__.py`
3. Import model in `backend/alembic/env.py` (for autogenerate to detect it)
4. Create migration: `alembic revision --autogenerate -m "add <name> model"`
5. Review and apply migration: `alembic upgrade head`

### Adding New API Routes

1. Create route file in `backend/app/api/routes/<name>.py`
2. Define router: `router = APIRouter()`
3. Include router in `backend/app/main.py`: `app.include_router(router, prefix="/api/...", tags=[...])`
4. Use dependencies for authentication: `user: User = Depends(get_current_user)`

### Adding Frontend Routes

1. Define route in `frontend/src/router/index.js`
2. Set `meta: { requiresAuth: true/false }` for auth protection
3. Create corresponding view component in `frontend/src/views/`

### Route Patterns

- `/` redirects to `/watchlist` (default landing page)
- `/dashboard` - Dashboard with navigation cards
- `/positions` - F&O positions view
- `/strategies` - Strategy Library with templates and wizard
- `/strategy/:id` - Load saved strategy by ID
- `/strategy/shared/:shareCode` - Public access for shared strategies (no auth required)
- `/autopilot` - AutoPilot dashboard with active strategies
- `/autopilot/strategies/new` - Create new AutoPilot strategy
- `/autopilot/strategies/:id` - Strategy detail with real-time monitoring
- `/autopilot/settings` - User settings and risk limits
- `/autopilot/templates` - Pre-built AutoPilot templates

### Environment Variables

Backend requires `.env` file based on `backend/.env.example`:
- `DATABASE_URL` - PostgreSQL connection string with `postgresql+asyncpg://` scheme
- `REDIS_URL` - Redis connection string
- `JWT_SECRET` - Secure random string for JWT signing
- `KITE_API_KEY`, `KITE_API_SECRET` - Zerodha Kite Connect credentials
- `FRONTEND_URL` - Used for OAuth redirects

Frontend requires `.env` file:
- `VITE_API_BASE_URL` - Backend API URL (defaults to http://localhost:8000)
- `VITE_WS_URL` - WebSocket URL (defaults to localhost:8000)


## Testing

**See [docs/testing/README.md](docs/testing/README.md) for complete documentation.**

~310 tests total: 240 frontend E2E tests across 28 spec files covering 8 screens (Login, Dashboard, Positions, Watchlist, Option Chain, Strategy Builder, Strategy Library, Integration), plus 70 backend pytest tests.

### Frontend E2E Tests (Playwright)

**Architecture:**
- **Page Object Model** - `tests/e2e/pages/` with BasePage.js and 8 screen-specific POMs
- **Auth Fixture** - `tests/e2e/fixtures/auth.fixture.js` for token injection (bypasses OAuth)
- **Single Browser Window** - Login once with TOTP, reuse auth for all tests
- **Self-Healing Selectors** - All Vue components use `data-testid` attributes
- **Organized Specs** - `tests/e2e/specs/{screen}/` with happy, edge, visual, api tests

**Test Categories:**
- `*.happy.spec.js` - Happy path tests (82 total)
- `*.edge.spec.js` - Edge case tests (60 total)
- `*.visual.spec.js` - Visual regression tests (45 total)
- `*.api.spec.js` / `*.websocket.spec.js` - API/WebSocket tests (53 total)
- `*.audit.spec.js` - Style & accessibility audits (7 files, ~50 tests)

**Browser Configuration:**
- All tests run with **maximized browser window** (via `--start-maximized`)
- Credentials auto-filled from `tests/config/credentials.js`, only TOTP is manual

### Backend Tests (pytest)

Located in `backend/tests/`:
- `conftest.py` - Fixtures: db_session, mock templates, mock Kite client
- `test_strategy_templates.py` - Model CRUD, constraints, JSON legs (~15 tests)
- `test_strategy_wizard_api.py` - All API endpoints (~35 tests)
- `test_strategy_validation.py` - Legs config, characteristics (~15 tests)
- `test_strategy_integration.py` - Full flows, concurrent requests (~5 tests)

**Run backend tests:**
```bash
cd backend
pytest tests/ -v                    # Run all backend tests
pytest tests/test_strategy*.py -v   # Run strategy-related tests
pytest tests/ -v --cov=app          # Run with coverage
```

### data-testid Convention
```
data-testid="[screen]-[component]-[element]"
Examples:
  data-testid="login-zerodha-button"
  data-testid="strategy-add-row-button"
  data-testid="positions-exit-modal"
  data-testid="optionchain-strike-row-24500"
  data-testid="strategy-library-wizard-button"
  data-testid="strategy-card-iron_condor"
```

### E2E Test Rules (Quick Reference)

**See [docs/testing/e2e-test-rules.md](docs/testing/e2e-test-rules.md) for complete documentation.**

**Selector Rules:**
- Use `data-testid` ONLY - no CSS classes, tags, or text selectors
- All selectors via Page Object `getByTestId()` method

**Fixture Rules:**
- Import from `auth.fixture.js` (NOT `@playwright/test`)
- Use `authenticatedPage` for all authenticated tests

**Page Object Pattern:**
- Extend `BasePage.js`, set `this.url` property
- Structure: Getters → Actions → Assertions (assertions in tests, not POM)

**Test File Suffixes:**
- `.happy.spec.js` - Normal flows
- `.edge.spec.js` - Error/boundary cases
- `.visual.spec.js` - Screenshots
- `.api.spec.js` - API validation
- `.audit.spec.js` - A11y/CSS

**Adding Tests Checklist:**
1. Add `data-testid` to Vue component
2. Add selector to Page Object
3. Import from `auth.fixture.js`
4. Use POM methods (no inline selectors)
