# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**AlgoChanakya:** Multi-broker options trading platform (Indian markets)
**Working Directory:** `D:\Abhay\VibeCoding\algochanakya` (development)

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

# Linting (from backend/, venv active)
ruff check app/ --fix && ruff format app/
```

**After code changes:** invoke `auto-verify` skill. To fix failures: `test-fixer` skill.

## CRITICAL: Never Touch Production

- **✅ Dev:** `D:\Abhay\VibeCoding\algochanakya` (backend port 8001, frontend port 5173)
- **❌ NEVER:** `C:\Apps\algochanakya` (production — port 8000/3004)

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
