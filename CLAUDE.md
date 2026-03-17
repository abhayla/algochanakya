# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**AlgoChanakya:** Multi-broker options trading platform (Indian markets)
**Working Directory:** `C:\Abhay\VideCoding\algochanakya` (development)

## Quick Reference

```bash
# ALWAYS check status first
git status && git log --oneline -5

# Start full dev stack (two terminals)
cd backend && venv\Scripts\activate && python run.py  # Terminal 1 → http://localhost:8001
cd frontend && npm run dev                             # Terminal 2 → http://localhost:5173

# E2E tests (from project root)
npm test                                               # All
npm run test:specs:positions                           # Single screen
npx playwright test path/to/spec                       # Single file
npx playwright test --grep "test name"                 # Single test

# Backend tests (from backend/, venv active)
pytest tests/ -v                                       # All
pytest tests/backend/options/test_pnl_calculator.py -v # Single file
pytest tests/backend/ai/test_market_regime.py::TestRegimeClassifier::test_bullish_regime -v  # Single test

# Frontend unit tests (from frontend/)
npm run test:run                                       # Run once
npm run test                                           # Watch mode

# Database (from backend/, venv active)
alembic upgrade head                                   # Apply pending migrations
alembic revision --autogenerate -m "description"       # Create new migration
```

**After code changes** — invoke via Skill tool, not shell:
- `auto-verify` — verify changes work
- `test-fixer` — fix failing tests

## Bug Reporting Protocol

When a bug is reported, don't start by trying to fix it. Instead, start by writing a test that reproduces the bug. Then have subagents try to fix the bug and prove it with a passing test.

## Most Common Mistakes

1. **Wrong backend port:** `backend/.env` should have `PORT=8001` (NOT 8000)
2. **Wrong frontend API URL:** `frontend/.env.local` must have `VITE_API_BASE_URL=http://localhost:8001`
3. **Touching production:** NEVER modify `C:\Apps\algochanakya` - only work in dev folder
4. **Missing alembic import:** New models must be imported in `backend/alembic/env.py`
5. **Direct broker API usage:** Always use adapters from `app.services.brokers/`, never import `KiteConnect` or `SmartAPI` directly
6. **Broker name mismatch:** DB stores `'zerodha'`/`'angelone'` but BrokerType enum uses `'kite'`/`'angel'` — use the broker name mapping utility when converting
7. **AngelOne 3-key confusion → AG8001:** AngelOne uses 3 separate API keys in `backend/.env`. Using the wrong key for an endpoint returns `AG8001 Invalid Token`. See table:

| `.env` Key | Purpose |
|-----------|---------|
| `ANGEL_API_KEY` | Live market data (WebSocket, quotes) |
| `ANGEL_HIST_API_KEY` | Historical candle data only |
| `ANGEL_TRADE_API_KEY` | Order execution only |

---

## Navigation

| Working on... | Go to |
|---------------|-------|
| Backend code | [backend/CLAUDE.md](backend/CLAUDE.md) |
| Frontend code | [frontend/CLAUDE.md](frontend/CLAUDE.md) |
| Tests failing | `Skill(skill="test-fixer")` or [Testing](#testing) |
| New feature | [Mandatory Behaviors](#critical-mandatory-behaviors) first |
| Architecture | [Multi-Broker Architecture](#core-purpose-multi-broker-architecture) |
| Production issue | [Production Safety](#0-production-vs-development---never-touch-production) (read-only!) |
| Roadmap / tasks | [ROADMAP.md](docs/ROADMAP.md) · [Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md) |
| All docs by topic | [Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md) |

---

## CRITICAL: Mandatory Behaviors

### 0. Production vs Development - NEVER TOUCH PRODUCTION

- **✅ Work here:** `C:\Abhay\VideCoding\algochanakya`
- **❌ NEVER touch:** `C:\Apps\algochanakya` (production folder on same machine)

**NEVER:**
- Kill, restart, or interfere with production processes
- Read or modify files in `C:\Apps\algochanakya`
- Copy files to/from production
- Run commands affecting production

**Note:** If backend at localhost:8000 is production, start dev backend on 8001 separately.

**Production emergencies:** Notify user with symptoms, observe logs read-only (`pm2 logs algochanakya-backend --lines 50`), test fixes in dev first, and wait for explicit user approval before any production action.

### 1. Auto-Verification After Code Changes

After **ANY** code change (bug fix, feature, refactor), invoke the `auto-verify` skill.

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
> I understand you want a kill switch in Strategy Builder. AutoPilot has one at `backend/app/services/autopilot/kill_switch.py`.
> Questions: Exit positions or just cancel orders? Add to StrategyActions or new button?

**Bad response:**
> I'll add a kill switch. Let me create a new component...

## Quick Start

**Requirements:** Python 3.13+ | Node.js 24+ | PostgreSQL | Redis

```bash
# 1. Environment files
cd backend && copy .env.example .env
# IMPORTANT: Edit backend/.env → change PORT=8000 to PORT=8001
# IMPORTANT: Edit backend/.env → set DATABASE_URL to your dev database (e.g. algochanakya_dev)
cd ../frontend && copy .env.example .env.local
# IMPORTANT: Edit frontend/.env.local → set VITE_API_BASE_URL=http://localhost:8001

# 2. Database (PostgreSQL must be running)
# Create dev database: CREATE DATABASE algochanakya_dev;
cd backend && venv\Scripts\activate
alembic upgrade head              # Apply all migrations

# 3. Start dev stack (two terminals)
# Terminal 1: backend
cd backend && venv\Scripts\activate && python run.py

# Terminal 2: frontend
cd frontend && npm run dev
```

**Full command reference:** [Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md) | [backend/CLAUDE.md](backend/CLAUDE.md#development-commands) | [frontend/CLAUDE.md](frontend/CLAUDE.md#development-commands)

---

## Documentation Rules (SSOT Principle)

**Each fact lives in ONE authoritative file. Other files link, never copy.**

| Topic | Authoritative Source |
|-------|---------------------|
| Port config, dev environment | This file (`CLAUDE.md` - Development Environment) |
| Broker architecture, comparison tables | `docs/architecture/broker-abstraction.md` |
| E2E test rules | `docs/testing/e2e-test-rules.md` |
| Troubleshooting | `docs/guides/troubleshooting.md` |
| Folder structure, architectural rules | `.claude/rules.md` |
| Automation (hooks, skills, agents) | `docs/guides/AUTOMATION_WORKFLOWS.md` |
| Backend patterns, pitfalls, commands | `backend/CLAUDE.md` |
| Frontend patterns, pitfalls, commands | `frontend/CLAUDE.md` |
| Production safety | This file (`CLAUDE.md` - Production vs Development) |

**Rules:**
- When adding new information, put it in the authoritative source. Add a link (not a copy) elsewhere.
- Never hardcode volatile counts (test files, hook counts, skill counts). These change constantly.
- ADRs are frozen decisions. They record WHY, not current HOW. Mark tables as "snapshot at decision time" if they contain status info.
- Run `Skill(skill="docs-maintainer")` after code changes to keep docs in sync.

---

## Development Environment

| Component | Port | URL | Notes |
|-----------|------|-----|-------|
| **Dev Backend** | 8001 | `http://localhost:8001` | Set in `backend/.env` |
| **Dev Frontend** | 5173 | `http://localhost:5173` | Vite default |
| **Dev WebSocket** | 8001 | `ws://localhost:8001/ws/ticks` | Same as backend |
| PostgreSQL | 5432 | `localhost:5432` | Shared with production |
| Redis | 6379 | `localhost:6379` | Shared with production |

**⚠️ Production (DO NOT TOUCH):** Backend=8000, Frontend=3004, Location=`C:\Apps\algochanakya`

**CRITICAL Port Configuration:**
- Frontend `.env.local` overrides `.env` and must point to dev backend (`http://localhost:8001`)
- After copying `.env.example`, manually change `PORT=8000` to `PORT=8001` in `backend/.env`
- This is the **#1 most common mistake** - wrong port configuration causes API calls to fail

**Database Servers:** PostgreSQL and Redis hosted on VPS (103.118.16.189). Shared between dev and production - use different database names to isolate environments.

---

## Core Purpose: Multi-Broker Architecture

**Primary Goal:** Broker-agnostic platform where adding a new broker requires **zero core code changes** — only adapter implementation and factory registration.

**Key design:** Dual-path market data (platform-default for all users, optional user upgrade) + per-user order execution. Platform failover chain: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite. All 6 brokers fully implemented (order execution adapters + ticker adapters).

**Complete architecture:** [Broker Abstraction Architecture](docs/architecture/broker-abstraction.md) | [Working Doc](docs/architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md) | [ADR-002](docs/decisions/002-broker-abstraction.md)

---

## Project Overview

Multi-broker options trading platform for Indian markets. **Tech Stack:** FastAPI + Vue 3 + PostgreSQL + Redis + Playwright + pytest + Vitest. AutoPilot automated trading (26 services). AI-powered regime detection (35 AI services).

**Three test layers:** Backend unit/integration (pytest, `backend/tests/backend/{module}/`), Frontend unit (Vitest, `frontend/tests/{stores,components,composables}/`), E2E (Playwright, `tests/e2e/specs/{screen}/`).

**Details:** [backend/CLAUDE.md](backend/CLAUDE.md) | [docs/README.md](docs/README.md)

**Root directory note:** The many `tmpclaude-*` directories are temporary working dirs created by Claude Code hooks — they are gitignored and can be ignored.

---

## Important Patterns

### Architectural Rules

All rules consolidated in [`.claude/rules.md`](.claude/rules.md) (SSOT) — folder structure, cross-layer imports, broker abstraction, trading constants, protected files, security, enforcement summary. Rules are enforced by PreToolUse hooks and code-reviewer agent. When in doubt, check rules.md first.

### Key Cross-References

| Pattern | Where to look |
|---------|--------------|
| Broker abstraction & code examples | [`.claude/rules.md`](.claude/rules.md#broker-abstraction-rules) |
| Trading constants | [`.claude/rules.md`](.claude/rules.md#trading-constants-rules) |
| Database models, routes, encryption | [backend/CLAUDE.md](backend/CLAUDE.md#database-patterns) |
| Environment variables | [backend/CLAUDE.md](backend/CLAUDE.md#environment-variables) · [frontend/CLAUDE.md](frontend/CLAUDE.md#environment-variables) |
| Auth error handling | [frontend/CLAUDE.md](frontend/CLAUDE.md#authentication-frontend) |

---

## Documentation

**Start here:**
1. **[Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md)** - All docs organized by task
2. **[Broker Abstraction Architecture](docs/architecture/broker-abstraction.md)** - Primary architecture (multi-broker)
3. **[Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md)** - Current implementation tasks
4. **[Automation Workflows Guide](docs/guides/AUTOMATION_WORKFLOWS.md)** - Complete automation system documentation

**Architecture Decision Records:**
- **[ADR-002: Broker Abstraction](docs/decisions/002-broker-abstraction.md)** - Why and how we abstract brokers
- **[TICKER-DESIGN-SPEC.md](docs/decisions/TICKER-DESIGN-SPEC.md)** - Multi-broker ticker architecture (5-component design)
  - [Implementation Guide](docs/guides/TICKER-IMPLEMENTATION-GUIDE.md) | [API Reference](docs/api/multi-broker-ticker-api.md) | [Documentation Index](docs/decisions/ticker-documentation-index.md)
- ~~[ADR-003 v2: Ticker Architecture](docs/decisions/003-multi-broker-ticker-architecture.md)~~ - Superseded (historical reference)

## Testing

**E2E rules:** See [E2E Test Rules](docs/testing/e2e-test-rules.md) (SSOT) for complete guidelines. Quick summary: `data-testid` only, import from `auth.fixture.js`, use `authenticatedPage` fixture. Test files follow `{screen}.{happy|edge|visual|api|audit}.spec.js` naming.

**E2E auth model:** Auth token is injected via `storageState` in `playwright.config.js` (from `tests/config/.auth-state.json`, written by `global-setup.js`). The `authenticatedPage` fixture validates the token is live but does NOT navigate — each test's own `beforeEach` navigates to its screen. Isolated tests (`.isolated.spec.js`) skip `storageState` and get a fresh browser context.

**Playwright workers/reporters:** 1 worker locally (prevents SmartAPI rate limits), 2 in CI (`process.env.CI`), `fullyParallel: false`. Heavy reporters (JSON, JUnit, Allure) only run in CI to keep local runs fast.

**Backend test markers:** `@unit`, `@api`, `@integration`, `@slow` — see [backend/CLAUDE.md](backend/CLAUDE.md#development-commands)

**Frontend unit tests (Vitest):** Environment is `happy-dom`. Global setup in `frontend/tests/setup.js` provides localStorage mock, WebSocket mock, and `import.meta.env` stubs. Mock stores with `vi.mock('@/stores/...')` and use `setActivePinia(createPinia())` in `beforeEach`.

**Test docs:** [docs/testing/README.md](docs/testing/README.md)

---

## Proactive Skills

These skills must be invoked automatically (via the Skill tool) at the right time:
- **`auto-verify`** — after ANY code change
- **`docs-maintainer`** — after code changes that affect docs
- **`learning-engine`** — after fix completions and test outcomes

All other available skills (testing, code gen, broker experts, workflows) are listed in the system prompt and invoked on demand. Full docs: [Automation Workflows Guide](docs/guides/AUTOMATION_WORKFLOWS.md)

---

## Common Pitfalls

**Backend:** [backend/CLAUDE.md - Pitfalls](backend/CLAUDE.md#backend-specific-pitfalls) — broker API usage, symbol format, alembic imports, async ops, trading constants
**Frontend:** [frontend/CLAUDE.md - Pitfalls](frontend/CLAUDE.md#frontend-specific-pitfalls) — data-testid, WebSocket cleanup, port config, AngelOne timeout
**Git:** Use `git status --porcelain` if you see escaped characters (UTF-8 encoding issues)

---

## Troubleshooting

### Quick Diagnosis
1. **Services not responding?** → Check backend/PostgreSQL/Redis are running
2. **Auth errors (401/403)?** → Re-login or check broker credentials
3. **Tests failing?** → Run `Skill(skill="test-fixer")`
4. **Wrong data/endpoints?** → Verify `.env` and `.env.local` point to dev (port 8001)
5. **Database errors?** → Run `alembic upgrade head` or check model imports in `alembic/env.py`

**Complete troubleshooting guide:** [Troubleshooting Guide](docs/guides/troubleshooting.md)

---

## Git Workflow

**Commit convention:** [Conventional Commits](https://www.conventionalcommits.org/) — `type(scope): description` where type is `feat`, `fix`, `refactor`, `docs`, `chore`, or `test`.

**Branches:** `main` (production), `develop` (integration). Feature work branches off `main` or `develop`.

---

## CI/CD

GitHub Actions runs on push/PR to `main` and `develop`. Workflows: backend tests (pytest), E2E (Playwright, 30min timeout), hook parity, and deploy. See `.github/workflows/`. Allure reports deploy to GitHub Pages on main merges.

<!-- hub:best-practices:start -->

<!-- PROTECTED SECTION — managed by claude-best-practices hub. -->
<!-- Do NOT condense, rewrite, reorganize, or remove.          -->
<!-- Any /init or optimization request must SKIP this section.  -->

## Rules for Claude

1. **Bug Fixing**: Use `/fix-loop` or `/fix-issue`. Start by writing a test that reproduces the bug, then fix and prove with a passing test.

### Rules Reference

| Rule File | What It Covers |
|-----------|---------------|
| `rules/adjustment-offensive-defensive.md` | Adjustment Offensive Defensive |
| `rules/alembic-model-import.md` | Alembic Model Import |
| `rules/backend-services-subdirectory.md` | Backend Services Subdirectory |
| `rules/broker-adapter-only.md` | Broker Adapter Only |
| `rules/broker-name-mapping.md` | Broker Name Mapping |
| `rules/canonical-symbol-format.md` | Canonical Symbol Format |
| `rules/claude-behavior.md` | Universal behavioral rules for how Claude should approach all tasks. |
| `rules/context-management.md` | Rules for managing context window, token usage, and documentation references. |
| `rules/cross-layer-import-guard.md` | Cross Layer Import Guard |
| `rules/decimal-not-float-prices.md` | Decimal Not Float Prices |
| `rules/e2e-data-testid-only.md` | E2E Data Testid Only |
| `rules/fastapi-backend.md` | FastAPI backend development rules and patterns. |
| `rules/fastapi-database.md` | Database and migration rules for FastAPI + SQLAlchemy + Alembic. |
| `rules/sqlite-test-compat.md` | Sqlite Test Compat |
| `rules/tdd.md` | Test-driven development workflow rules for red-green-refactor cycle. |
| `rules/testing.md` | Testing conventions and best practices. |
| `rules/trading-constants-centralized.md` | Trading Constants Centralized |
| `rules/vue.md` | Vue 3 Composition API patterns and conventions. |
| `rules/workflow.md` | Development workflow guidelines for structured feature implementation and bug fixes. |

## Claude Code Configuration

The `.claude/` directory contains skills, agents, and rules for Claude Code.

<!-- hub:best-practices:end -->
