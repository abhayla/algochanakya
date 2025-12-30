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
> I found AutoPilot has one at `backend/app/api/v1/autopilot/kill_switch.py`.
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

# Run tests by screen (positions, optionchain, strategy, autopilot, ai, etc.)
npm run test:specs:positions

# Database migration (from backend/)
alembic revision --autogenerate -m "description" && alembic upgrade head

# Backend tests
cd backend && pytest tests/ -v
```

## Project Overview

AlgoChanakya is an options trading platform (similar to Sensibull) with FastAPI backend and Vue.js 3 frontend, integrating with Zerodha Kite Connect for broker operations.

**Tech Stack:** FastAPI + async SQLAlchemy + PostgreSQL + Redis | Vue 3 + Vite + Pinia + Tailwind CSS | Playwright (~360 E2E tests) + Vitest + pytest

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
npm test                           # All tests (login once with TOTP)
npm run test:specs:{screen}        # By screen: login, dashboard, positions, watchlist, optionchain, strategy, strategylibrary, autopilot, ai
npm run test:happy                 # All happy path tests
npm run test:edge                  # All edge case tests
npm run test:headed                # With visible browser
npm run test:debug                 # Debug mode
npx playwright test path/to/spec  # Single file
```

## Architecture Overview

**Key Modules:**
- **Authentication** - Zerodha OAuth → JWT in localStorage + Redis. Use `get_current_user` / `get_current_broker_connection` dependencies.
- **WebSocket Live Prices** - `ws://localhost:8000/ws/ticks?token=<jwt>`. KiteTickerService is singleton. Index tokens: NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801
- **Option Chain** - IV via Newton-Raphson, Greeks via Black-Scholes. Max Pain, PCR calculated.
- **Strategy Builder** - P/L modes: "At Expiry" (intrinsic) and "Current" (Black-Scholes via scipy)
- **AutoPilot** - Automated execution with conditions, adjustments, kill switch. 16 database tables. See [docs/autopilot/](docs/autopilot/)
- **AI Module** - Market regime (6 types), risk states (GREEN/YELLOW/RED), trust ladder (Sandbox→Supervised→Autonomous). See [docs/ai/](docs/ai/)

**Database:** Async PostgreSQL (asyncpg) + Redis for sessions. Run `alembic upgrade head` after git pull.

**Key Services:**
- `app/services/kite_ticker.py` - Singleton WebSocket for live prices
- `app/services/pnl_calculator.py` - Black-Scholes P/L calculations
- `app/services/condition_engine.py` - AutoPilot entry/adjustment evaluation

**Key AI Services:**
- `app/services/ai/market_regime.py` - 6 market regime types detection
- `app/services/ai/risk_state_engine.py` - GREEN/YELLOW/RED risk states
- `app/services/ai/strategy_recommender.py` - Strategy recommendations
- `app/services/ai/deployment_executor.py` - AI-driven trade execution
- `app/services/ai/ml/` - ML models and training pipeline

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

**Backend (`backend/.env`):** `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `KITE_API_KEY`, `KITE_API_SECRET`, `ANTHROPIC_API_KEY` (for AI)

**Frontend (`frontend/.env`):** `VITE_API_BASE_URL=http://localhost:8000`

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
| `vitest-generator` | Generate unit tests | On demand |
| `vue-component-generator` | Create Vue components | On demand |
| `autopilot-assistant` | AutoPilot config guidance | On demand |
| `trading-constants-manager` | Enforce trading constants | On demand |

## Claude Chrome Integration

**Setup:** `claude --chrome` | **Verify:** `/chrome`

**Use Chrome for:** Debug failing tests, WebSocket testing, visual verification, live UI debugging
**Use Playwright for:** CI/CD, running all E2E tests

**Key URLs:** Dashboard `/dashboard`, Watchlist `/watchlist`, Positions `/positions`, Option Chain `/optionchain`, Strategy `/strategy`, AutoPilot `/autopilot`, AI `/ai`

**Console Prefixes:** `[AutoPilot WS]`, `[OptionChain]`, `[Strategy]`, `[AI Regime]`, `[AI Risk]`

## Testing

~112 E2E spec files. See [docs/testing/README.md](docs/testing/README.md) for complete documentation.

**Config:** 30s timeout, 2 workers, auth state reused via `./tests/config/.auth-state.json`. Projects: `setup` (login), `chromium` (main), `isolated` (fresh context).

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

## Debug Commands

```bash
curl http://localhost:8000/api/health          # Check backend health
npx playwright test path/to/spec --debug       # Debug E2E test
npx playwright show-trace trace.zip            # View trace
```

```javascript
// Browser console - test WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/ticks?token=YOUR_JWT')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
ws.send(JSON.stringify({action: 'subscribe', tokens: [256265], mode: 'quote'}))
```
