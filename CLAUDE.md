# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlgoChanakya is an options trading platform (similar to Sensibull) built with FastAPI backend and Vue.js 3 frontend. The platform integrates with broker APIs (starting with Zerodha Kite Connect) for authentication and trading operations.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy (async) + PostgreSQL + Redis
- Frontend: Vue.js 3 + Vite + Pinia + Vue Router + Tailwind CSS
- Broker Integration: Zerodha Kite Connect API
- Testing: Playwright (E2E)

## Development Commands

### Backend

From `backend/` directory:

```bash
# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Start development server (preferred)
python run.py

# Or with uvicorn directly
uvicorn app.main:app --reload

# Install new dependency
pip install <package>
pip freeze > requirements.txt

# Database migrations (Alembic)
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Run specific migration
alembic upgrade <revision>
```

### Frontend

From `frontend/` directory:

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Install new dependency
npm install <package>
```

### Testing (Playwright)

From project root:

```bash
# Run all tests
npm test

# Run specific test file
npm run test:login
npm run test:api
npm run test:oauth
npm run test:watchlist
npm run test:ws

# Run with UI
npm run test:ui

# Run headed (visible browser)
npm run test:headed

# Debug mode
npm run test:debug
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

### Backend Structure

- `app/main.py` - FastAPI app initialization, CORS, lifespan events
- `app/config.py` - Pydantic Settings for environment variables
- `app/database.py` - SQLAlchemy async engine, session factory, Redis pool
- `app/models/` - SQLAlchemy ORM models (User, BrokerConnection, Watchlist, Instrument)
- `app/schemas/` - Pydantic schemas for request/response validation
- `app/api/routes/` - FastAPI route handlers
  - `auth.py` - Zerodha OAuth login/callback
  - `watchlist.py` - Watchlist CRUD operations
  - `instruments.py` - Instrument search
  - `websocket.py` - WebSocket endpoint for live prices
- `app/services/` - Business logic services
  - `kite_ticker.py` - KiteTickerService for live price streaming
  - `instruments.py` - Instrument data management
- `app/utils/jwt.py` - JWT token creation and verification
- `app/utils/dependencies.py` - FastAPI dependencies for authentication

### Frontend Structure

- `src/router/index.js` - Vue Router with authentication guards
- `src/stores/auth.js` - Pinia store for authentication state
- `src/stores/watchlist.js` - Pinia store for watchlist and WebSocket management
- `src/services/api.js` - Axios instance with interceptors for auth headers
- `src/views/` - Vue components for pages
  - `LoginView.vue` - Login page with Zerodha OAuth button
  - `AuthCallbackView.vue` - OAuth callback handler
  - `WatchlistView.vue` - Watchlist page with live prices
- `src/components/` - Reusable Vue components
  - `watchlist/IndexHeader.vue` - NIFTY/BANK NIFTY live prices header
  - `watchlist/InstrumentRow.vue` - Individual instrument row with live data
  - `watchlist/InstrumentSearch.vue` - Search and add instruments

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

**Frontend:**
- `vue` - UI framework
- `vue-router` - Routing
- `pinia` - State management
- `axios` - HTTP client
- `tailwindcss` - CSS framework

## Testing

**Playwright E2E Tests** (from project root):
- `tests/e2e/login.spec.js` - Login page tests
- `tests/e2e/api.spec.js` - API endpoint tests
- `tests/e2e/oauth-flow.spec.js` - Full OAuth flow (requires manual Zerodha login)
- `tests/e2e/watchlist.spec.js` - Watchlist functionality tests
- `tests/e2e/websocket-verify.spec.js` - WebSocket live prices verification

Test screenshots are saved to `tests/screenshots/` (gitignored).

**Running Tests:**
```bash
# Install Playwright browsers (first time only)
npx playwright install

# Run all tests
npm test

# Run specific test with visible browser
npm run test:ws  # WebSocket verification
npm run test:oauth  # OAuth flow
```
