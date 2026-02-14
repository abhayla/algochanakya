# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**AlgoChanakya:** Multi-broker options trading platform (Indian markets)
**Last Updated:** February 2026

## 🚨 Critical First Steps

1. **Check current work:** `git status && git log --oneline -5`
2. **Never touch production:** Work in `D:\Abhay\VibeCoding\algochanakya` ONLY (not `C:\Apps\algochanakya`)
3. **Auto-verify all changes:** Run `Skill(skill="auto-verify")` after ANY code change
4. **Check ports:** Dev backend=8001, Dev frontend=5173 (production=8000/3004 - DO NOT TOUCH)

## 📚 Quick Navigation

- **Backend work?** → [backend/CLAUDE.md](backend/CLAUDE.md)
- **Frontend work?** → [frontend/CLAUDE.md](frontend/CLAUDE.md)
- **Quick commands?** → [Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md)
- **Current tasks?** → [Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md)

## Implementation Status

✅ **Complete:** Multi-broker abstraction, SmartAPI integration, Auto-TOTP, E2E test suite (189 files)
🚧 **In Progress:** ADR-003 v2 ticker architecture (designed, implementation ready)
📋 **Planned:** Additional broker integrations (Upstox, Fyers, Dhan, Paytm)

## 🔄 Ongoing Redesigns (Feb 14, 2026)

- **[Workflow Redesign](.claude/WORKFLOW-DESIGN-SPEC.md)** - 9→4 hooks, 395s→110s timeout, 3,100→1,200 lines
- **[Ticker Redesign](docs/decisions/TICKER-DESIGN-SPEC.md)** - 6→5 components, 495→90 line websocket.py

## Table of Contents

**Essential:**
1. [Critical Behaviors](#critical-mandatory-behaviors) - Must follow
2. [Quick Start](#quick-start) - Commands to get running
3. [Core Architecture](#core-purpose-multi-broker-architecture) - Multi-broker design

**Reference:**
4. [Common Tasks](#common-tasks) - Quick how-to guides
5. [Important Patterns](#important-patterns) - Broker abstraction, constants, DB
6. [Testing](#testing) - E2E and backend tests
7. [Troubleshooting](#troubleshooting-common-errors) - Error messages and fixes

**Advanced:**
8. [Documentation](#documentation) - Where to find detailed docs
9. [Skills](#claude-code-skills) - Automated workflows
10. [Pitfalls](#common-pitfalls) - What to avoid
11. [CI/CD](#cicd) - GitHub Actions

---

## CRITICAL: Mandatory Behaviors

### 0. Production vs Development - NEVER TOUCH PRODUCTION

- **✅ Work here:** `D:\Abhay\VibeCoding\algochanakya`
- **❌ NEVER touch:** `C:\Apps\algochanakya` (production folder on same machine)

**NEVER:**
- Kill, restart, or interfere with production processes
- Read or modify files in `C:\Apps\algochanakya`
- Copy files to/from production
- Run commands affecting production

**Note:** If backend at localhost:8000 is production, start dev backend on 8001 separately.

### 1. Auto-Verification After Code Changes

After **ANY** code change (bug fix, feature, refactor):
```bash
Skill(skill="auto-verify")
```
**Skip only for:** Docs-only, comments-only, or when user says "skip verification".

### 2. Check Current Work First

Always run before starting:
```bash
git status && git log --oneline -5
```

### 3. Clarify Before Implementing

Before features/refactors/architecture changes:
1. **State understanding** (2-3 sentences)
2. **Research codebase** for existing patterns
3. **Check docs:** [Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md) | [Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md) | [Broker Abstraction](docs/architecture/broker-abstraction.md)
4. **Ask questions** if gaps exist

**Skip for:** Docs changes, obvious bugs, explicit instructions.

**Good response:**
> I understand you want a kill switch in Strategy Builder. AutoPilot has one at `backend/app/services/kill_switch.py`.
> Questions: Exit positions or just cancel orders? Add to StrategyActions or new button?

**Bad response:**
> I'll add a kill switch. Let me create a new component...

## Quick Start

**Requirements:** Python 3.11+ | Node.js 20+ | PostgreSQL | Redis

```bash
# Start dev backend (from backend/)
venv\Scripts\activate && python run.py    # Windows

# Start frontend (from frontend/)
npm run dev

# Run E2E tests (from root)
npm test

# Database migration (from backend/)
alembic revision --autogenerate -m "description" && alembic upgrade head
```

**Full command reference:** [Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md#quick-commands) | [backend/CLAUDE.md](backend/CLAUDE.md#development-commands) | [frontend/CLAUDE.md](frontend/CLAUDE.md#development-commands)

## Development Environment

| Component | Port | URL | Notes |
|-----------|------|-----|-------|
| **Dev Backend** | 8001 | `http://localhost:8001` | Set in `backend/.env` |
| **Dev Frontend** | 5173 | `http://localhost:5173` | Vite default |
| **Dev WebSocket** | 8001 | `ws://localhost:8001/ws/ticks` | Same as backend |
| PostgreSQL | 5432 | `localhost:5432` | Shared with production |
| Redis | 6379 | `localhost:6379` | Shared with production |

**⚠️ Production (DO NOT TOUCH):** Backend=8000, Frontend=3004, Location=`C:\Apps\algochanakya`

**CRITICAL:** Frontend `.env.local` overrides `.env` and must point to dev backend (`http://localhost:8001`), not production (8000)

---

## Core Purpose: Multi-Broker Architecture

**Primary Goal:** Broker-agnostic platform where adding a new broker requires **zero core code changes** - only adapter implementation and factory registration.

### Why Multi-Broker Support?

- **Cost savings:** Zerodha charges Rs.500/month for data; others are FREE
- **Flexibility:** Mix FREE data providers with funded broker for orders
- **No lock-in:** Switch brokers instantly without reinstalling

**Example:** SmartAPI (FREE data) + Zerodha Personal API (FREE orders) = Rs.0/month

### Two Independent Abstractions

**1. Market Data Brokers** - Live prices, historical OHLC, WebSocket ticks
- Interface: `MarketDataBrokerAdapter`
- Factory: `get_market_data_adapter(broker_type, credentials)`

**2. Order Execution Brokers** - Place orders, manage positions, margins
- Interface: `BrokerAdapter`
- Factory: `get_broker_adapter(broker_type, credentials)`

### Supported Brokers

| Broker | Market Data | Orders | Status |
|--------|-------------|--------|--------|
| **Angel One** (SmartAPI) | ✅ FREE | ✅ FREE | Production |
| **Zerodha** (Kite) | Rs.500/mo | ✅ FREE | Production |
| **Upstox/Fyers/Dhan/Paytm** | FREE | FREE | Planned |

**Details:** [backend/CLAUDE.md](backend/CLAUDE.md#broker-abstraction-code-examples) | [Broker Abstraction Architecture](docs/architecture/broker-abstraction.md) | [ADR-002](docs/decisions/002-broker-abstraction.md)

---

## Project Overview

AlgoChanakya is an options trading platform (similar to Sensibull) for Indian markets with multi-broker support.

**Current Setup:** SmartAPI (FREE market data) + Zerodha Kite (FREE order execution) = Rs.0/month

**Tech Stack:**
- **Backend:** FastAPI + async SQLAlchemy + PostgreSQL + Redis
- **Frontend:** Vue 3 + Vite + Pinia + Tailwind CSS 4
- **Testing:** Playwright (122 E2E specs) + Vitest + pytest (67 backend tests)

**Key Features:**
- Multi-broker abstraction (swap brokers without code changes)
- Auto-TOTP authentication for SmartAPI
- Real-time WebSocket data feeds
- AI-powered regime detection and risk analysis
- AutoPilot automated trading

**Production:** https://algochanakya.com (Windows Server 2022) - Not production-ready yet

**Architecture details:** [backend/CLAUDE.md](backend/CLAUDE.md#architecture-overview) | [docs/README.md](docs/README.md)

---

## Common Tasks

### Add a New Broker

1. Create adapter: `backend/app/services/brokers/{broker}_adapter.py`
2. Implement `BrokerAdapter` and/or `MarketDataBrokerAdapter` interfaces
3. Register in factory: `get_broker_adapter()` / `get_market_data_adapter()`
4. Add credentials model to database (if needed)
5. See [Broker Abstraction docs](docs/architecture/broker-abstraction.md) for detailed guide

### Add a New API Endpoint

1. Create router: `backend/app/api/routes/{feature}.py`
2. Add to `main.py`: `app.include_router({feature}.router)`
3. Use `Depends(get_current_user)` for authentication
4. Add E2E test: `tests/e2e/specs/{screen}/{feature}.spec.js`
5. Update feature registry: `docs/feature-registry.yaml`

### Fix a Failing E2E Test

1. Run locally: `npm test -- {test-file}` (from root)
2. Check `data-testid` attributes match code
3. Ensure using `authenticatedPage` fixture (from `auth.fixture.js`)
4. For AngelOne login, use `timeout: 35000` (auto-TOTP takes 20-25s)
5. Or invoke: `Skill(skill="test-fixer")`

### Add a Database Model

1. Create model: `backend/app/models/{model_name}.py`
2. Import in `backend/app/models/__init__.py`
3. Import in `backend/alembic/env.py` (CRITICAL - autogenerate won't work without this)
4. Generate migration: `alembic revision --autogenerate -m "Add {model_name}"`
5. Review migration, then apply: `alembic upgrade head`

### Debug WebSocket Issues

1. Check backend logs for connection errors
2. Verify `.env.local` has correct WebSocket URL (`ws://localhost:8001/ws/ticks`)
3. Ensure Redis is running (`redis-server`)
4. Check browser console for WebSocket errors
5. Verify `onUnmounted()` cleanup in Vue components

---

## Important Patterns

### Folder Structure Rules (ENFORCED by hooks)

**Backend:** Services MUST be in subdirectories under `app/services/` (autopilot/, options/, legacy/, ai/, brokers/). Only `__init__.py`, `instruments.py`, `ofo_calculator.py`, `option_chain_service.py` allowed at root. See [backend/CLAUDE.md](backend/CLAUDE.md#folder-structure-rules-enforced-by-hooks) for full details.

**Frontend:** CSS in `src/assets/styles/`, images in `src/assets/logos/`, API code in `src/services/`. See [frontend/CLAUDE.md](frontend/CLAUDE.md#folder-structure-rules-enforced-by-hooks).

**Tests:** E2E in `tests/e2e/specs/{screen}/` subdirectories. Backend tests in `tests/backend/{module}/`.

### Broker Abstraction (CRITICAL)

**NEVER directly use broker-specific APIs (KiteConnect, SmartAPI client).** Always use broker adapters and factories. **All symbol references must use canonical format (Kite format) internally.** Use `SymbolConverter` for broker-specific symbols.

**Code examples and unified data models:** See [backend/CLAUDE.md](backend/CLAUDE.md#broker-abstraction-code-examples)

### Trading Constants (CRITICAL)

**NEVER hardcode lot sizes, strike steps, or index tokens.** Always use centralized constants:
- **Backend:** `from app.constants.trading import get_lot_size, get_strike_step`
- **Frontend:** `import { getLotSize, getStrikeStep } from '@/constants/trading'`

**Full examples:** [backend/CLAUDE.md](backend/CLAUDE.md#trading-constants-backend) | [frontend/CLAUDE.md](frontend/CLAUDE.md#trading-constants-frontend)

### Database Patterns

- **Adding models:** Create in `models/`, import in `__init__.py` + `alembic/env.py`, run migration
- **Adding routes:** Create router in `api/routes/`, include in `main.py`, use `Depends(get_current_user)`
- **Encryption:** Use `app/utils/encryption.py` for sensitive stored credentials

**Full details:** [backend/CLAUDE.md](backend/CLAUDE.md#database-patterns)

### Environment Variables

**Setup:** Copy `.env.example` files to `.env` and update with actual values.

**CRITICAL:** Frontend `.env.local` overrides `.env`. Must point to `http://localhost:8001` for dev backend. Common mistake: pointing to wrong port (8005, 8000).

**Full variable lists:** [backend/CLAUDE.md](backend/CLAUDE.md#environment-variables) | [frontend/CLAUDE.md](frontend/CLAUDE.md#environment-variables)

### Authentication Error Handling

**Backend:** `get_current_user` / `get_current_broker_connection` dependencies return 401 on invalid/expired tokens.
**Frontend:** Axios interceptor in `src/services/api.js` clears token and redirects to `/login` on 401.

**Details:** [frontend/CLAUDE.md](frontend/CLAUDE.md#authentication-frontend)

---

## Documentation

**Start here:**
1. **[Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md)** - All docs organized by task
2. **[Broker Abstraction Architecture](docs/architecture/broker-abstraction.md)** - Primary architecture (multi-broker)
3. **[Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md)** - Current implementation tasks
4. **[Automation Workflows Guide](docs/guides/AUTOMATION_WORKFLOWS.md)** - Complete automation system documentation (14 hooks, 6 commands, 5 agents, 21 skills)

**Automation System (NEW - Feb 2026):**
- **[Automation Workflows Guide](docs/guides/AUTOMATION_WORKFLOWS.md)** - Unified guide to all automation (2,291 lines)
- **[Automation Gap Report](docs/guides/AUTOMATION-GAP-REPORT.md)** - Comparison with best practices, identified gaps
- **[Automation Feature Proposals](docs/guides/AUTOMATION-FEATURE-PROPOSALS.md)** - 7 proposed improvements (P0-P2 prioritized)

**Architecture Decision Records:**
- **[ADR-002: Broker Abstraction](docs/decisions/002-broker-abstraction.md)** - Why and how we abstract brokers
- **[ADR-003: Ticker Architecture](docs/decisions/003-multi-broker-ticker-architecture.md)** - Multi-broker WebSocket design
  - [Implementation Guide](docs/architecture/multi-broker-ticker-implementation.md)
  - [API Reference](docs/api/multi-broker-ticker-api.md)

**Organized by topic:**
- **Architecture:** `docs/architecture/` - System design (auth, WebSocket, database, brokers)
- **Features:** `docs/features/{feature}/` - Per-feature docs (README, REQUIREMENTS, CHANGELOG)
- **Testing:** `docs/testing/` - Test guides and patterns
- **API Reference:** `docs/api/` - Endpoint documentation
- **Guides:** `docs/guides/` - Comprehensive guides (automation workflows, etc.)

**Maintenance:**
- After code changes, run `Skill(skill="docs-maintainer")` to auto-update docs
- Feature registry: `docs/feature-registry.yaml` maps code files to features

## Claude Code Skills

**Automatic (run after every code change):**
- `auto-verify` - Test changes immediately ⚡
- `docs-maintainer` - Keep docs in sync 📚
- `learning-engine` - Record fix patterns 🧠

**Testing & Debugging:**
- `test-fixer` - Diagnose test failures
- `health-check` - Scan for code issues (7 steps, also runs on session start)
- `e2e-test-generator` - Generate Playwright tests
- `vitest-generator` - Generate Vitest unit tests

**Code Generation:**
- `vue-component-generator` - Create Vue 3 components/Pinia stores
- `trading-constants-manager` - Enforce centralized trading constants

**Workflow Commands:**
- `/implement` - 7-step implementation workflow
- `/fix-loop` - Iterative fix cycle
- `/run-tests` - Multi-layer test runner
- `/reflect` - Learning + self-modification
- `/post-fix-pipeline` - Verification + commit

**Broker API Experts:**
- `smartapi-expert` - SmartAPI (Angel One) API guidance
- `kite-expert` - Kite Connect (Zerodha) API guidance
- `upstox-expert` - Upstox API guidance
- `dhan-expert` - Dhan API guidance
- `fyers-expert` - Fyers API guidance
- `paytm-expert` - Paytm Money API guidance

> 6 consultative skills for API guidance, code auditing, and cross-broker comparison. Shared comparison matrix at `.claude/skills/broker-shared/comparison-matrix.md`.

**Other:**
- `autopilot-assistant` - AutoPilot strategy config guidance
- `save-session` / `start-session` - Save/resume context

---

## Key URLs

Dashboard `/dashboard`, Watchlist `/watchlist`, Positions `/positions`, Option Chain `/optionchain`, Strategy `/strategy`, Strategy Library `/strategies`, AutoPilot `/autopilot`, AI `/ai`, OFO `/ofo`, Settings `/settings`

**Console Prefixes:** `[AutoPilot WS]`, `[OptionChain]`, `[Strategy]`, `[AI Regime]`, `[AI Risk]`

---

## Testing

~189 test files (122 E2E spec files + 67 backend pytest files). See [docs/testing/README.md](docs/testing/README.md) for complete documentation.

### E2E Test Rules (CRITICAL)

- **Use `data-testid` ONLY** - no CSS classes, tags, or text selectors
- **Import from `auth.fixture.js`** (NOT `@playwright/test`)
- **Use `authenticatedPage` fixture** for authenticated tests
- **data-testid convention:** `[screen]-[component]-[element]` (e.g., `positions-exit-modal`)

**Full test config, categories, and commands:** [frontend/CLAUDE.md](frontend/CLAUDE.md#e2e-test-rules-critical)

---

## Common Pitfalls

### Git & File System
- **File path encoding issues** - Escaped characters in `git status` indicate UTF-8 encoding issues. Use `git status --porcelain`.

### Backend
- **Direct broker API usage** - NEVER import `KiteConnect` or `SmartAPI` directly; use adapters
- **Hardcoded broker assumptions** - Code should work with any broker via abstraction
- **Bypassing market data abstraction** - Use `get_market_data_adapter()`, not legacy services
- **Symbol format confusion** - Use canonical format (Kite) internally; `SymbolConverter` for broker-specific
- **Broker name mismatch** - BrokerConnection stores 'zerodha'/'angelone' but BrokerType uses 'kite'/'angel'
- **Forgot model import in `alembic/env.py`** - Autogenerate won't detect it
- **Sync database operations** - All SQLAlchemy must use `async/await`
- **Hardcoded trading constants** - Use `app.constants.trading` instead

### Frontend
- **Missing `data-testid`** - Required for E2E tests; use `[screen]-[component]-[element]`
- **WebSocket not cleaned up** - Close subscriptions in `onUnmounted()`
- **Wrong backend port in `.env.local`** - Must point to `http://localhost:8001` for dev
- **AngelOne login timeout** - Use `timeout: 35000` (auto-TOTP takes 20-25s)

**Detailed pitfalls with code examples:** [backend/CLAUDE.md](backend/CLAUDE.md#backend-specific-pitfalls) | [frontend/CLAUDE.md](frontend/CLAUDE.md#frontend-specific-pitfalls)

---

## Troubleshooting Common Errors

### Quick Diagnosis

1. **Services not responding?** → Check if backend/PostgreSQL/Redis are running
2. **Auth errors (401/403)?** → Re-login or check broker credentials
3. **Tests failing?** → Check `data-testid`, timeouts, or run `Skill(skill="test-fixer")`
4. **Wrong data/endpoints?** → Verify `.env` and `.env.local` point to correct ports (dev=8001)
5. **Database errors?** → Run `alembic upgrade head` or check model imports in `alembic/env.py`

### Connection Errors

| Error | Quick Fix |
|-------|-----------|
| `Connection refused [Errno 61/111]` | Start backend: `cd backend && python run.py` |
| `ECONNREFUSED 127.0.0.1:5432` | Start PostgreSQL service |
| `ECONNREFUSED 127.0.0.1:6379` | Start Redis: `redis-server` |
| `WebSocket connection failed` | Check `.env.local` WebSocket URL + backend running |
| `Database connection pool exhausted` | Check for unclosed connections, increase pool size |

### Authentication Errors

| Error | Quick Fix |
|-------|-----------|
| `401 Unauthorized` | Re-login via `/login` in frontend |
| `403 Forbidden` on broker API | Re-authenticate (SmartAPI auto-refreshes, Kite needs OAuth) |
| `Incorrect api_key or access_token` | SmartAPI auto-refreshes; Kite needs re-login via OAuth |

### Python/Backend Errors

| Error | Quick Fix |
|-------|-----------|
| `ModuleNotFoundError: No module named 'app'` | Activate venv: `venv\Scripts\activate` in `backend/` |
| `relation "table_name" does not exist` | Run: `alembic upgrade head` in `backend/` |
| `alembic.util.exc.CommandError` | Check `alembic.ini` and `DATABASE_URL` in `.env` |
| Backend starts on port 8000 (not 8001) | Check `backend/.env` has `PORT=8001` |

### Frontend/Node Errors

| Error | Quick Fix |
|-------|-----------|
| `npm ERR! ENOENT: no such file or directory` | Run `npm install` in `frontend/` |
| `Cannot find module '@/...'` | Check Vite config, restart dev server |
| Frontend API calls fail with 404 | Check `frontend/.env.local` has `VITE_API_BASE_URL=http://localhost:8001` |

### Test Errors

| Error | Quick Fix |
|-------|-----------|
| `Target page, context or browser has been closed` | Increase timeout or fix test. Check `playwright.config.js` |
| `playwright: command not found` | Run `npm install` in project root |
| AngelOne login timeout | Use `timeout: 35000` (auto-TOTP takes 20-25s) |

### Other Errors

| Error | Quick Fix |
|-------|-----------|
| File path encoding (e.g., `\357\200\272`) | Use `git status --porcelain` or fix file system encoding |
| `Rate limit exceeded` | Adapters handle this - don't bypass them |
| `no pg_hba.conf entry for host` | Whitelist IP in PostgreSQL `pg_hba.conf` |

**General Debugging Steps:**
1. Check if all services are running (backend, PostgreSQL, Redis)
2. Verify environment variables (`.env`, `.env.local`) have correct values
3. Run `git status && git log --oneline -5` to check current state
4. Check browser console and network tab for frontend issues
5. Check backend logs for detailed error messages
6. Use `/health-check` skill for automated codebase health scan
7. For broker-specific API errors, consult the relevant broker expert skill

**Debug commands and production debugging:** [backend/CLAUDE.md](backend/CLAUDE.md#debug-commands) | [backend/CLAUDE.md](backend/CLAUDE.md#production-debugging)

---

## CI/CD

GitHub Actions runs automatically on push/PR to `main` and `develop`:

| Workflow | File | Description |
|----------|------|-------------|
| **Backend Tests** | `.github/workflows/backend-tests.yml` | pytest with PostgreSQL/Redis services |
| **E2E Tests** | `.github/workflows/e2e-tests.yml` | Playwright with full stack (30min timeout) |
| **Deploy** | `.github/workflows/deploy.yml` | Production deployment pipeline |

Allure reports deploy to GitHub Pages on main branch merges.
