# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlgoChanakya is an options trading platform (similar to Sensibull) built with FastAPI backend and Vue.js 3 frontend. The platform integrates with broker APIs (starting with Zerodha Kite Connect) for authentication and trading operations.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy (async) + PostgreSQL + Redis
- Frontend: Vue.js 3 + Vite + Pinia + Vue Router + Tailwind CSS
- Broker Integration: Zerodha Kite Connect API
- Testing: Playwright (E2E with 160 tests)

**Detailed Documentation:** See [docs/](docs/README.md) for comprehensive documentation including:
- [Architecture](docs/architecture/) - System design, auth, WebSocket, database
- [API Reference](docs/api/) - Endpoint documentation
- [Guides](docs/guides/) - Setup and troubleshooting
- [Testing](docs/testing/) - E2E test architecture

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

# Run by category
npm run test:happy      # All happy path tests
npm run test:edge       # All edge case tests
npm run test:visual     # All visual regression tests
npm run test:api:new    # All API tests

# Legacy individual tests
npm run test:positions      # F&O positions tests
npm run test:optionchain    # Option chain tests
npm run test:iron-condor    # Iron Condor strategy test
npm run test:overflow       # All screens horizontal overflow test

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

**User (`users` table):**
- Stores user account information
- Can have multiple broker connections
- Email is optional (supports broker-only users)

**BrokerConnection (`broker_connections` table):**
- Links users to broker accounts (Zerodha, Upstox, etc.)
- Stores broker access tokens and metadata
- `is_active` flag indicates current connection status
- Multiple connections per user are supported

**Watchlist (`watchlists` table):**
- User-created watchlists with custom names
- Links to instruments via `watchlist_instruments` junction table
- Supports position ordering for instruments

**Instrument (`instruments` table):**
- Master instrument data (populated from Kite instruments dump)
- Contains token, symbol, exchange, instrument type, etc.
- Used for search and watchlist functionality

**Strategy (`strategies` table):**
- User-created options strategies with underlying (NIFTY/BANKNIFTY/FINNIFTY)
- Supports shareable links via `share_code`
- Status tracking (open/closed)

**StrategyLeg (`strategy_legs` table):**
- Individual legs of a strategy (strike, expiry, contract type)
- Transaction type (BUY/SELL), lots, entry/exit prices
- Links to instrument via `instrument_token`
- Order tracking via `order_id` and `position_status`

### Strategy Builder

The platform includes a comprehensive options Strategy Builder:

1. **P/L Calculation (`app/services/pnl_calculator.py`):**
   - Two modes: "At Expiry" (intrinsic value) and "Current" (Black-Scholes)
   - Uses scipy for accurate Black-Scholes pricing (with pure Python fallback)
   - Calculates P/L grid across multiple spot prices
   - Returns max profit, max loss, and breakeven points
   - Lot sizes: NIFTY=75, BANKNIFTY=15, FINNIFTY=25

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

7. **Frontend Components (`src/components/strategy/`):**
   - `StrategyHeader.vue` - Underlying selector, P/L mode toggle
   - `StrategyLegRow.vue` - Editable leg row with dropdowns, CMP display, Exit P/L calculation
   - `StrategyActions.vue` - Action buttons
   - `SaveStrategyModal.vue` - Save strategy dialog
   - `ShareStrategyModal.vue` - Share link dialog
   - `BasketOrderModal.vue` - Order confirmation

### Backend Structure

- `app/main.py` - FastAPI app initialization, CORS, lifespan events
- `app/config.py` - Pydantic Settings for environment variables
- `app/database.py` - SQLAlchemy async engine, session factory, Redis pool
- `app/models/` - SQLAlchemy ORM models (User, BrokerConnection, Watchlist, Instrument, Strategy, StrategyLeg)
- `app/schemas/` - Pydantic schemas for request/response validation
- `app/api/routes/` - FastAPI route handlers
  - `health.py` - Health check endpoint (DB + Redis connectivity)
  - `auth.py` - Zerodha OAuth login/callback
  - `watchlist.py` - Watchlist CRUD operations
  - `instruments.py` - Instrument search
  - `options.py` - Options expiries, strikes, chain data
  - `optionchain.py` - Full option chain with OI, IV, Greeks
  - `strategy.py` - Strategy CRUD, P/L calculation, sharing
  - `orders.py` - Basket orders, positions, imports
  - `positions.py` - F&O positions with live P&L, exit/add orders
  - `websocket.py` - WebSocket endpoint for live prices
- `app/services/` - Business logic services
  - `kite_ticker.py` - KiteTickerService for live price streaming
  - `kite_orders.py` - Basket orders via Kite API
  - `pnl_calculator.py` - Black-Scholes P/L calculations
  - `instruments.py` - Instrument data management
- `app/utils/jwt.py` - JWT token creation and verification
- `app/utils/dependencies.py` - FastAPI dependencies for authentication

### Frontend Structure

- `src/router/index.js` - Vue Router with authentication guards
- `src/stores/` - Pinia stores (auth, watchlist, strategy, optionchain, positions)
- `src/composables/` - Vue composables for reusable logic
- `src/services/api.js` - Axios instance with interceptors for auth headers
- `src/views/` - Page components (Login, Dashboard, Watchlist, OptionChain, StrategyBuilder, Positions)
- `src/components/` - Reusable components
  - `layout/` - KiteLayout, KiteHeader, WatchlistSidebar
  - `watchlist/` - IndexHeader, InstrumentRow, InstrumentSearch
  - `strategy/` - StrategyHeader, StrategyLegRow, StrategyActions, modals

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
- `/strategy/:id` - Load saved strategy by ID
- `/strategy/shared/:shareCode` - Public access for shared strategies (no auth required)

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

## Key Dependencies

**Backend:**
- `fastapi` - Web framework
- `sqlalchemy[asyncio]` - Async ORM
- `asyncpg` - PostgreSQL async driver
- `redis[asyncio]` - Redis async client
- `alembic` - Database migrations
- `pydantic-settings` - Settings management
- `kiteconnect` - Zerodha API client
- `PyJWT` - JWT token handling
- `scipy` - Black-Scholes calculations for P/L

**Frontend:**
- `vue` - UI framework
- `vue-router` - Routing
- `pinia` - State management
- `axios` - HTTP client
- `tailwindcss` - CSS framework

## Testing

**See [docs/testing/README.md](docs/testing/README.md) for complete documentation.**

160 tests across 24 spec files covering all 7 screens. Test commands are in the Development Commands section above.

**Test Architecture:**
- **Page Object Model** - `tests/e2e/pages/` with BasePage.js and 6 screen-specific POMs
- **Auth Fixture** - `tests/e2e/fixtures/auth.fixture.js` for token injection (bypasses OAuth)
- **Single Browser Window** - Login once with TOTP, reuse auth for all tests
- **Self-Healing Selectors** - All Vue components use `data-testid` attributes
- **Organized Specs** - `tests/e2e/specs/{screen}/` with happy, edge, visual, api tests

**Test Categories:**
- `*.happy.spec.js` - Happy path tests (57 total)
- `*.edge.spec.js` - Edge case tests (40 total)
- `*.visual.spec.js` - Visual regression tests (30 total)
- `*.api.spec.js` / `*.websocket.spec.js` - API/WebSocket tests (33 total)

**data-testid Convention:**
```
data-testid="[screen]-[component]-[element]"
Examples:
  data-testid="login-zerodha-button"
  data-testid="strategy-add-row-button"
  data-testid="positions-exit-modal"
  data-testid="optionchain-strike-row-24500"
```
