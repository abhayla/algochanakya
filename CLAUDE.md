# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Last Updated:** February 2026
**Primary Implementation Status:** Phase 3 Complete (Multi-broker abstraction for market data + order execution)

## Documentation Structure

This project uses **modular CLAUDE.md files** that load on-demand:
- **This file (root):** Cross-cutting rules, mandatory behaviors, pitfalls, troubleshooting
- **[backend/CLAUDE.md](backend/CLAUDE.md):** Backend architecture, broker code examples, database patterns, production debugging
- **[frontend/CLAUDE.md](frontend/CLAUDE.md):** Frontend conventions, E2E test rules, WebSocket patterns
- **[Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md):** Command cheatsheets, doc links by role

## Table of Contents

1. [Critical: Mandatory Behaviors](#critical-mandatory-behaviors)
2. [Quick Start](#quick-start)
3. [Core Purpose: Multi-Broker Architecture](#core-purpose-multi-broker-architecture)
4. [Project Overview](#project-overview)
5. [Important Patterns](#important-patterns)
6. [Documentation](#documentation)
7. [Claude Code Skills](#claude-code-skills)
8. [Key URLs](#key-urls)
9. [Testing](#testing)
10. [Common Pitfalls](#common-pitfalls)
11. [Troubleshooting Common Errors](#troubleshooting-common-errors)
12. [CI/CD](#cicd)

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

**IMPORTANT:** Frontend development uses `.env.local` which overrides `.env`. Ensure `frontend/.env.local` points to dev backend (port 8001), not production (8000).

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

**Port Reference:**

| Service | Development | Production (DO NOT TOUCH) |
|---------|-------------|---------------------------|
| Backend API | `localhost:8001` | `localhost:8000` |
| Frontend | `localhost:5173` | `localhost:3004` |
| WebSocket | `ws://localhost:8001/ws/ticks` | `wss://algochanakya.com/ws/ticks` |
| Database | `localhost:5432` | `localhost:5432` |
| Redis | `localhost:6379` | `localhost:6379` |

---

## Core Purpose: Multi-Broker Architecture

**Primary Goal:** AlgoChanakya is designed as a **broker-agnostic platform** where adding a new broker requires **zero code changes** - only adapter implementation and factory registration.

### Why Multi-Broker Support?

Indian broker APIs vary significantly:
- **Pricing:** Zerodha charges Rs.500/month for market data; many others offer FREE APIs
- **Cost Optimization:** Users can mix FREE data providers with their funded broker for orders
- **Flexibility:** Switch brokers without reinstalling, test multiple providers for reliability/latency
- **User Choice:** No lock-in to a single broker

**Example FREE Setup:** SmartAPI (FREE data) + Zerodha Personal API (FREE orders) = Rs.0/month

### Two Independent Broker Systems

The platform maintains **two separate abstractions** for maximum flexibility:

#### 1. Market Data Brokers
**Purpose:** Live prices, historical OHLC, WebSocket ticks, instrument data. Many brokers offer free market data but charge for trading APIs.

**Interface:** `MarketDataBrokerAdapter` | **Factory:** `get_market_data_adapter(broker_type, credentials)`

#### 2. Order Execution Brokers
**Purpose:** Placing orders, managing positions, account margins. Requires funded broker account.

**Interface:** `BrokerAdapter` (`backend/app/services/brokers/base.py`) | **Factory:** `get_broker_adapter(broker_type, credentials)`

### Supported Brokers

| Broker | Market Data | Orders | Status |
|--------|-------------|--------|--------|
| **Angel One** (SmartAPI) | FREE | FREE | Default for data |
| **Zerodha** (Kite Connect) | Rs.500/mo | FREE | Orders only |
| **Upstox/Fyers/Dhan/Others** | FREE | FREE | Planned |

**Current Setup:** SmartAPI (FREE data) + Zerodha (FREE orders) = Rs.0/month

**Implementation status, code examples, and adding new brokers:** See [backend/CLAUDE.md](backend/CLAUDE.md#broker-abstraction-code-examples)

**Architecture docs:** [Broker Abstraction Architecture](docs/architecture/broker-abstraction.md) | [ADR-002](docs/decisions/002-broker-abstraction.md) | [ADR-003: Ticker Architecture](docs/decisions/003-multi-broker-ticker-architecture.md)

---

## Project Overview

AlgoChanakya is an options trading platform (similar to Sensibull) with FastAPI backend and Vue.js 3 frontend. Uses **AngelOne SmartAPI** as the default for all market data (live prices, historical OHLC) with auto-TOTP authentication. Zerodha Kite Connect is used for order execution only.

**Tech Stack:** FastAPI + async SQLAlchemy + PostgreSQL + Redis | Vue 3 + Vite + Pinia + Tailwind CSS 4 | Playwright (100+ E2E spec files) + Vitest + pytest

**Production:** https://algochanakya.com (Windows Server 2022, PM2, Nginx/Cloudflare) - App not production-ready yet

**Documentation:** See [docs/README.md](docs/README.md) for architecture, API reference, and testing guides.

**Full architecture details:** [backend/CLAUDE.md](backend/CLAUDE.md#architecture-overview) (service catalog, key services, AI endpoints)

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

**PRIMARY DOCS FOR IMPLEMENTATION:**
1. **[Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md)** - All docs organized by task (use this first!)
2. **[Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md)** - Current implementation tasks with docs links
3. **[Broker Abstraction Architecture](docs/architecture/broker-abstraction.md)** - Primary architecture (multi-broker)
4. **[Multi-Broker Ticker Architecture](docs/decisions/003-multi-broker-ticker-architecture.md)** - ADR for ticker refactoring (Proposed)
   - [Implementation Guide](docs/architecture/multi-broker-ticker-implementation.md) | [API Reference](docs/api/multi-broker-ticker-api.md)

**Stale Docs Warning:** `docs/IMPLEMENTATION-CHECKLIST.md` may be outdated. CLAUDE.md contains the authoritative implementation status.

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

AlgoChanakya has a fully autonomous testing system with slash commands, hooks, sub-agents, and self-learning capabilities. This system enforces test-driven development, prevents broken commits, and continuously improves fix strategies.

**Full documentation:** [.claude/AUTONOMOUS-WORKFLOW-IMPLEMENTATION.md](.claude/AUTONOMOUS-WORKFLOW-IMPLEMENTATION.md)

**Key commands:** `/implement` (7-step workflow), `/fix-loop` (iterative fix cycle), `/post-fix-pipeline` (verification + commit), `/run-tests` (multi-layer runner), `/reflect` (learning + self-modification)

**Key files:** Commands in `.claude/commands/`, hooks in `.claude/hooks/`, agents in `.claude/agents/`, learning in `.claude/learning/knowledge.db`

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
