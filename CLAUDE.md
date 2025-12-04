# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlgoChanakya is an options trading platform (similar to Sensibull) built with FastAPI backend and Vue.js 3 frontend. The platform integrates with broker APIs (starting with Zerodha Kite Connect) for authentication and trading operations.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy (async) + PostgreSQL + Redis
- Frontend: Vue.js 3 + Vite + Pinia + Vue Router + Tailwind CSS
- Broker Integration: Zerodha Kite Connect API

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

### Backend Structure

- `app/main.py` - FastAPI app initialization, CORS, lifespan events
- `app/config.py` - Pydantic Settings for environment variables
- `app/database.py` - SQLAlchemy async engine, session factory, Redis pool
- `app/models/` - SQLAlchemy ORM models (User, BrokerConnection)
- `app/schemas/` - Pydantic schemas for request/response validation
- `app/api/routes/` - FastAPI route handlers
- `app/utils/jwt.py` - JWT token creation and verification
- `app/utils/dependencies.py` - FastAPI dependencies for authentication

### Frontend Structure

- `src/router/index.js` - Vue Router with authentication guards
- `src/stores/auth.js` - Pinia store for authentication state
- `src/services/api.js` - Axios instance with interceptors for auth headers
- `src/views/` - Vue components for pages
- `src/components/` - Reusable Vue components

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

No test framework is currently configured. When adding tests, consider:
- Backend: pytest + pytest-asyncio for async tests
- Frontend: Vitest (already compatible with Vite)
