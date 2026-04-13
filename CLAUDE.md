# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**AlgoChanakya:** Multi-broker options trading platform (Indian markets)
**Working Directory:** Use the current working directory (varies per machine)

## Quick Reference

```bash
# ALWAYS check status first
git status && git log --oneline -5

# Start full dev stack (two terminals)
cd backend && venv\Scripts\activate && python run.py  # Terminal 1 → http://localhost:8001
cd frontend && npm run dev                             # Terminal 2 → http://localhost:5173

# E2E tests (from project root)
npm test                                               # All
npx playwright test path/to/spec                       # Single file
npx playwright test --grep "test name"                 # Single test

# Backend tests (from backend/, venv active)
pytest tests/ -v
pytest tests/path/to/test.py::ClassName::test_name -v  # Single test

# Frontend unit tests (from frontend/)
npm run test:run    # Run once
npm run test        # Watch mode

# Database (from backend/, venv active)
alembic upgrade head
alembic revision --autogenerate -m "description"

# Backend linting (from backend/, venv active)
ruff check app/ --fix && ruff format app/

# Frontend linting (from frontend/)
npm run lint:fix && npm run format

# E2E tests by screen (from project root)
npm run test:specs:optionchain                     # Single screen
npm run test:happy                                 # All happy paths
```

**After code changes:** invoke `auto-verify` skill. To fix failures: `test-fixer` skill.

## CRITICAL: Never Touch Production

- **Dev:** Current working directory (backend port 8001, frontend port 5173)
- **NEVER:** `C:\Apps\algochanakya` (production — port 8000/3004)

## Navigation

| Working on... | Go to |
|---|---|
| Backend | [backend/CLAUDE.md](backend/CLAUDE.md) |
| Frontend | [frontend/CLAUDE.md](frontend/CLAUDE.md) |
| Architecture | [docs/architecture/broker-abstraction.md](docs/architecture/broker-abstraction.md) |
| Roadmap | [docs/ROADMAP.md](docs/ROADMAP.md) |
| All docs | [docs/DEVELOPER-QUICK-REFERENCE.md](docs/DEVELOPER-QUICK-REFERENCE.md) |
| Troubleshooting | [docs/guides/troubleshooting.md](docs/guides/troubleshooting.md) |

## Architecture

Multi-broker platform where all 6 brokers (Zerodha, AngelOne, Dhan, Fyers, Paytm, Upstox) are abstracted behind a single adapter interface. Adding a broker = implement adapter + register in factory, zero core code changes.

**Three test layers:** Backend pytest (`backend/tests/`), Frontend Vitest (`frontend/tests/`), E2E Playwright (`tests/e2e/`).

**Key pitfalls:**
- Backend port is **8001** in dev (not 8000 — that's production)
- New models need imports in both `backend/app/models/__init__.py` AND `backend/alembic/env.py`
- DB stores `'zerodha'`/`'angelone'` but `BrokerType` enum uses `'kite'`/`'angel'` — use `BROKER_NAME_MAP`
- AngelOne has 3 API keys: `ANGEL_API_KEY` (live data), `ANGEL_HIST_API_KEY` (history), `ANGEL_TRADE_API_KEY` (orders)
- Never import broker SDKs directly — always use `app.services.brokers.factory`

## Git

**Commit convention:** `type(scope): description` — types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`

## Rules

All architectural constraints in `.claude/rules/` (auto-loaded per file type). SSOT: each fact in one file only.

## Rules for Claude

1. **Bug Fixing**: Use `/fix-loop` or `/fix-issue`. Start by writing a test that reproduces the bug, then fix and prove with a passing test.
2. All architectural constraints auto-load from `.claude/rules/` based on file context — no need to read them manually.

<!-- hub:best-practices:start -->

<!-- PROTECTED SECTION — managed by claude-best-practices hub. -->
<!-- Do NOT condense, rewrite, reorganize, or remove.          -->
<!-- Any /init or optimization request must SKIP this section.  -->

### Rules Reference

| Rule File | What It Covers |
|-----------|---------------|
| `rules/adjustment-offensive-defensive.md` | Adjustment Offensive Defensive |
| `rules/alembic-model-import.md` | Alembic Model Import |
| `rules/api-error-response-pattern.md` | Api Error Response Pattern |
| `rules/async-db-session-pattern.md` | Async Db Session Pattern |
| `rules/auth-401-handling.md` | Auth 401 Handling |
| `rules/backend-services-subdirectory.md` | Backend Services Subdirectory |
| `rules/broker-adapter-only.md` | Broker Adapter Only |
| `rules/broker-name-mapping.md` | Broker Name Mapping |
| `rules/canonical-symbol-format.md` | Canonical Symbol Format |
| `rules/claude-behavior.md` | Scope: global |
| `rules/configuration-ssot.md` | Scope: global |
| `rules/context-management.md` | Scope: global |
| `rules/cross-layer-import-guard.md` | Cross Layer Import Guard |
| `rules/decimal-not-float-prices.md` | Decimal Not Float Prices |
| `rules/e2e-auth-and-naming.md` | E2E Auth And Naming |
| `rules/e2e-data-testid-only.md` | E2E Data Testid Only |
| `rules/e2e-page-object-pattern.md` | E2E Page Object Pattern |
| `rules/e2e-test-naming-convention.md` | E2E Test Naming Convention |
| `rules/e2e-test-writing.md` | Nudges to e2e-best-practices skill when writing or modifying E2E tests. |
| `rules/fastapi-backend.md` | FastAPI backend development rules and patterns. |
| `rules/fastapi-database.md` | Database and migration rules for FastAPI + SQLAlchemy + Alembic. |
| `rules/frontend-data-flow.md` | Frontend Data Flow |
| `rules/middleware-registration-order.md` | Middleware Registration Order (CORS before routers) |
| `rules/pinia-store-composition.md` | Pinia Store Composition Pattern |
| `rules/prompt-auto-enhance-rule.md` | Scope: global |
| `rules/pydantic-schema-conventions.md` | Pydantic Schema Conventions |
| `rules/rule-writing-meta.md` | Meta-guidance for writing effective CLAUDE.md rules, choosing config file placement, and structuring project instructions. |
| `rules/service-initialization-order.md` | Service Initialization Order (lifespan dependency chain) |
| `rules/sqlite-test-compat.md` | Sqlite Test Compat |
| `rules/tdd.md` | Tdd |
| `rules/tdd-rule.md` | Test-driven development workflow rules for red-green-refactor cycle. |
| `rules/testing.md` | Testing conventions and best practices. |
| `rules/trading-constants-centralized.md` | Trading Constants Centralized |
| `rules/vue.md` | Vue 3 Composition API patterns and conventions. |
| `rules/websocket-ticker-architecture.md` | Websocket Ticker Architecture |
| `rules/workflow.md` | Scope: global |

## Claude Code Configuration

The `.claude/` directory contains 167 skills, 49 agents, and 34 rules for Claude Code.

<!-- hub:best-practices:end -->
