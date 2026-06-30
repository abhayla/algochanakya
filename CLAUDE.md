# 5 Wealths portfolio context — READ FIRST

This repo is one project inside Abhay's 5 Wealths portfolio. Before doing any strategic, scoping, or governance work in this session, read the three files below in order. They explain the portfolio, the boundary rule, the immutable principles, and the glossary used across all of Abhay's projects.

@./5W-CONTEXT.md
@./5W-PRINCIPLES.md
@./5W-GLOSSARY.md

**If the @-import syntax is not honored by your client (e.g., not running inside Claude Code), use the Read tool to load the three files manually before proceeding:**

- `./5W-CONTEXT.md` — what 5 Wealths is, where it lives, the L-042 boundary rule, cross-reference protocol
- `./5W-PRINCIPLES.md` — the four immutable principles (productize, scale, automate, continuously update)
- `./5W-GLOSSARY.md` — decoded shorthand (entities, regulators, sister projects, terms)

**Boundary reminder (non-negotiable):** Never write into `D:\Abhay\VibeCoding\5Wealths\` from this repo. Strategic decisions surfaced here get captured as `TODO(5W):` notes; Abhay carries them across in a separate 5 Wealths session.

---

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**AlgoChanakya:** Multi-broker options trading platform (Indian markets)
**Stack:** Vue 3 + Vite (frontend) · FastAPI + Python 3.13 (backend) · PostgreSQL + Redis

## Quick Reference

```bash
# ALWAYS check status first
git status && git log --oneline -5

# Start full dev stack (two terminals)
cd backend && source venv/Scripts/activate && python run.py  # Terminal 1 → http://localhost:8001
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

**Dual-broker system:** Market data and order execution are independent — a user can use AngelOne for live prices and Zerodha for placing orders simultaneously. Two separate adapter hierarchies: `BrokerAdapter` (orders) and `MarketDataBrokerAdapter` (data).

**Three test layers:** Backend pytest (`backend/tests/`), Frontend Vitest (`frontend/tests/`), E2E Playwright (`tests/e2e/`).

**Key pitfalls:**
- Backend port is **8001** in dev (not 8000 — that's production)
- `frontend/.env.local` must point to `http://localhost:8001` (not 8000 or 8005)
- New models need imports in both `backend/app/models/__init__.py` AND `backend/alembic/env.py`
- DB stores `'zerodha'`/`'angelone'` but `BrokerType` enum uses `'kite'`/`'angel'` — use `BROKER_NAME_MAP`
- AngelOne has 3 API keys: `ANGEL_API_KEY` (live data), `ANGEL_HIST_API_KEY` (history), `ANGEL_TRADE_API_KEY` (orders)
- Never import broker SDKs directly — always use `app.services.brokers.factory`
- Instrument queries MUST filter by `source_broker` — kite vs smartapi share strikes but use different tokens; unfiltered selects crash `scalar_one_or_none()` (see `instrument-source-broker-filter` rule)
- Tests use SQLite in-memory; PostgreSQL types (JSONB, ARRAY, UUID, BigInteger) need `@compiles` dialect adapters in `conftest.py` — see `sqlite-test-compat` rule

## Git

**Commit convention:** `type(scope): description` — types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`

## Workflow

- After code changes: invoke `/auto-verify`. To fix failures: `/test-fixer` or `/fix-loop`.
- See the hub-managed "Rules for Claude" section below for bug-fixing and rules-loading conventions.

<!-- hub:best-practices:start -->

<!-- PROTECTED SECTION — managed by claude-best-practices hub. -->
<!-- Do NOT condense, rewrite, reorganize, or remove.          -->
<!-- Any /init or optimization request must SKIP this section.  -->

## Rules for Claude

1. **Bug Fixing**: Use `/fix-loop` or `/fix-github-issue`. Start by writing a test that reproduces the bug, then fix and prove with a passing test.
2. **Rules**: Path-scoped rules live in `.claude/rules/` and auto-load via `globs:` frontmatter when matching files are opened. Browse with `ls .claude/rules/` — enumerating each rule here would cost ~4k tokens per session for zero enforcement benefit.

## Claude Code Configuration

The `.claude/` directory contains 189 skills, 55 agents, and 56 rules for Claude Code.

<!-- hub:best-practices:end -->
