# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Mandatory Behaviors

### 0. Protected Files - DO NOT MODIFY

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
3. **Ask questions** if gaps exist (scope, design, integration)

**Skip clarification for:** Doc changes, obvious bug fixes, explicit user instructions.

**Example - Good Response:**
> I understand you want to add a kill switch to Strategy Builder.
> I found AutoPilot has one at `backend/app/services/kill_switch.py`.
> Questions: Exit positions or cancel orders? Add to StrategyActions or new button?

**Bad Response:**
> I'll add a kill switch. Let me create a new component...

## Quick Start

**Requirements:** Python 3.11+ | Node.js 20+ | PostgreSQL | Redis

```bash
# Start backend (from backend/)
venv\Scripts\activate && python run.py    # Windows
source venv/bin/activate && python run.py # Linux/Mac

# Start frontend (from frontend/)
npm run dev

# Run all E2E tests (from root)
npm test

# Run single test file
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js

# Run tests by screen
npm run test:specs:positions    # positions, optionchain, strategy, strategylibrary, autopilot, navigation, audit, login, dashboard, watchlist, ofo

# Database migration (from backend/)
alembic revision --autogenerate -m "description" && alembic upgrade head

# Backend tests
cd backend && pytest tests/ -v
```

## Project Overview

AlgoChanakya is an options trading platform (similar to Sensibull) with FastAPI backend and Vue.js 3 frontend. Uses **AngelOne SmartAPI** as the default for all market data (live prices, historical OHLC) with auto-TOTP authentication. Zerodha Kite Connect is used for order execution only.

**Tech Stack:** FastAPI + async SQLAlchemy + PostgreSQL + Redis | Vue 3 + Vite + Pinia + Tailwind CSS 4 | Playwright (100+ E2E spec files) + Vitest + pytest

**Production:** https://algochanakya.com (Windows Server 2022, PM2, Nginx/Cloudflare)

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
- **Authentication** - SmartAPI with auto-TOTP (default) or Zerodha OAuth. JWT stored in localStorage + Redis. Use `get_current_user` / `get_current_broker_connection` dependencies. SmartAPI credentials stored encrypted in `smartapi_credentials` table.
- **WebSocket Live Prices** - `ws://localhost:8000/ws/ticks?token=<jwt>`. KiteTickerService is singleton. Index tokens: NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801, SENSEX=265
- **Option Chain** - IV via Newton-Raphson, Greeks via Black-Scholes. Max Pain, PCR calculated.
- **Strategy Builder** - P/L modes: "At Expiry" (intrinsic) and "Current" (Black-Scholes via scipy)
- **AutoPilot** - Automated execution with conditions, adjustments, kill switch. 16 database tables. See [docs/autopilot/](docs/autopilot/)
- **AI Module** - Market regime (6 types), risk states (GREEN/YELLOW/RED), trust ladder (Sandbox→Supervised→Autonomous). Paper trading graduation: 15 days + 25 trades + 55% win rate. Key tables: `ai_user_config`, `ai_decisions_log`, `ai_model_registry`, `ai_learning_reports`. See [docs/ai/](docs/ai/)
- **SmartAPI Integration** (Default) - AngelOne SmartAPI is the **default market data source** for live WebSocket prices and historical OHLC. Kite remains for order execution. Uses auto-TOTP (no manual TOTP entry). Key files: `backend/app/services/smartapi_*.py`, `frontend/src/components/settings/SmartAPISettings.vue`. See `docs/plans/smartapi-integration-plan.md`.

**Database:** Async PostgreSQL (asyncpg) + Redis for sessions. Run `alembic upgrade head` after git pull.

**Key Services:**
- `app/services/kite_ticker.py` - Singleton WebSocket for live prices
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

### Adding New API Routes

1. Create `backend/app/api/routes/<name>.py` with `router = APIRouter()`
2. Include in `backend/app/main.py`
3. Use `Depends(get_current_user)` for authentication

### Environment Variables

**Backend (`backend/.env`):** `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `KITE_API_KEY`, `KITE_API_SECRET`, `ANTHROPIC_API_KEY` (for AI), `ANGEL_API_KEY` (for SmartAPI market data)

**Frontend (`frontend/.env`):** `VITE_API_BASE_URL=http://localhost:8000`, `VITE_WS_URL=ws://localhost:8000` (optional, defaults to API URL)

**Production Build:** Create `frontend/.env.production` with `VITE_API_BASE_URL=https://algochanakya.com` before `npm run build` - without this, API calls default to localhost!

### Encryption for Credentials

Use `backend/app/utils/encryption.py` for encrypting sensitive stored credentials:

```python
from app.utils.encryption import encrypt, decrypt
encrypted = encrypt("sensitive_data")
decrypted = decrypt(encrypted)
```

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

**Feature Registry:** `docs/feature-registry.yaml` maps code files to features. After code changes, use `docs-maintainer` skill to update docs automatically.

**Feature Docs:** `docs/features/{feature}/` with README.md, REQUIREMENTS.md, CHANGELOG.md for each feature.

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

## Key URLs

Dashboard `/dashboard`, Watchlist `/watchlist`, Positions `/positions`, Option Chain `/optionchain`, Strategy `/strategy`, Strategy Library `/strategies`, AutoPilot `/autopilot`, AI `/ai`, OFO `/ofo`, Settings `/settings`

**Console Prefixes:** `[AutoPilot WS]`, `[OptionChain]`, `[Strategy]`, `[AI Regime]`, `[AI Risk]`

## Testing

~184 test files (121 E2E spec files + 63 backend pytest files). See [docs/testing/README.md](docs/testing/README.md) for complete documentation.

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
- **Forgot to import model in `alembic/env.py`** - Autogenerate won't detect it
- **Sync database operations** - All SQLAlchemy must use `async/await`
- **Hardcoded trading constants** - Use `app.constants.trading` instead

### Frontend
- **Missing `data-testid`** - Required for E2E tests; use `[screen]-[component]-[element]`
- **WebSocket not cleaned up** - Close subscriptions in `onUnmounted()`
- **Direct Kite API calls** - All broker operations go through backend

### Testing
- **Wrong import** - Use `auth.fixture.js`, NOT `@playwright/test`
- **CSS/text selectors** - Use `data-testid` only

## SmartAPI (Default Market Data Source)

SmartAPI is the **default market data source** for all live prices and historical OHLC. Uses **auto-TOTP** - no manual TOTP entry required.

**Credentials:** Stored encrypted in `smartapi_credentials` table (client_id, encrypted PIN, encrypted TOTP secret).

**Authentication Flow:**
1. User saves credentials via Settings → SmartAPI Settings
2. PIN and TOTP secret are encrypted with Fernet (using JWT_SECRET-derived key)
3. On authentication, TOTP secret is decrypted and `pyotp.TOTP(secret).now()` generates the code automatically
4. Code is used with `SmartConnect.generateSession(client_id, pin, totp_code)`

**E2E Tests:** Use SmartAPI for authentication (no manual TOTP needed). The `global-setup.js` authenticates via `/api/smartapi/authenticate` endpoint.

**Manual TOTP Generation (for debugging):**
```bash
cd backend && venv\Scripts\activate && python generate_totp.py
```

**Key Files:**
- `backend/app/services/smartapi_auth.py` - Auth service with auto-TOTP
- `backend/app/services/smartapi_ticker.py` - WebSocket V2 for live prices
- `backend/app/services/smartapi_historical.py` - Historical OHLC data
- `backend/app/api/routes/smartapi.py` - Credential management endpoints
- `frontend/src/components/settings/SmartAPISettings.vue` - Settings UI

**API Endpoints:**
- `POST /api/smartapi/authenticate` - Authenticate with stored credentials (auto-TOTP)
- `GET /api/smartapi/credentials` - Check if credentials exist
- `POST /api/smartapi/credentials` - Store encrypted credentials
- `POST /api/smartapi/test-connection` - Test connection before saving

## Debug Commands

```bash
curl http://localhost:8000/api/health          # Check backend health
npx playwright test path/to/spec --debug       # Debug E2E test
npx playwright show-trace trace.zip            # View trace
```

```javascript
// Browser console - test WebSocket (local)
const ws = new WebSocket('ws://localhost:8000/ws/ticks?token=YOUR_JWT')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
ws.send(JSON.stringify({action: 'subscribe', tokens: [256265], mode: 'quote'}))

// Production (use wss:// for HTTPS)
const ws = new WebSocket('wss://algochanakya.com/ws/ticks?token=YOUR_JWT')
```

## Production Debugging

**Server:** Windows Server 2022 (544934-ABHAYVPS) | https://algochanakya.com

**PM2 Logs:**
```bash
pm2 logs algochanakya-backend    # Backend logs
pm2 logs algochanakya-frontend   # Frontend logs (static serve)
pm2 restart algochanakya-backend # Restart backend
```

**Common Production Issues:**
- **API calls fail:** Check `frontend/.env.production` has `VITE_API_BASE_URL=https://algochanakya.com`
- **OAuth fails:** Verify Kite redirect URL = `https://algochanakya.com/api/auth/zerodha/callback`
- **"Incorrect api_key or access_token":** SmartAPI token expired (8h) or Kite access token expired (24h). SmartAPI auto-refreshes via stored credentials; Kite requires re-login via OAuth.
- **WebSocket won't connect:** Check `VITE_WS_URL` in `.env.production`, ensure wss:// for HTTPS

**Full deployment docs:** `C:\Apps\shared\docs\ALGOCHANAKYA-SETUP.md` on VPS
