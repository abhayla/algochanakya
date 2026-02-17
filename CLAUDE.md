# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**AlgoChanakya:** Multi-broker options trading platform (Indian markets)
**Last Updated:** 2026-02-16
**Working Directory:** `C:\Abhay\VideCoding\algochanakya` (development)

## ⚡ Quick Reference Card

```bash
# Check status first (ALWAYS)
git status && git log --oneline -5

# Start dev environment
cd backend && venv\Scripts\activate && python run.py  # Port 8001
cd frontend && npm run dev                             # Port 5173

# After ANY code change
Skill(skill="auto-verify")

# Fix failing tests
Skill(skill="test-fixer")

# Dev ports: Backend=8001, Frontend=5173 | Production: Backend=8000, Frontend=3004
```

## 🚨 Most Common Mistakes (Fix These First!)

1. **Wrong backend port:** `backend/.env` should have `PORT=8001` (NOT 8000)
2. **Wrong frontend API URL:** `frontend/.env.local` must have `VITE_API_BASE_URL=http://localhost:8001`
3. **Touching production:** NEVER modify `C:\Apps\algochanakya` - only work in dev folder
4. **Missing alembic import:** New models must be imported in `backend/alembic/env.py`
5. **Direct broker API usage:** Always use adapters from `app.services.brokers/`, never import `KiteConnect` or `SmartAPI` directly

---

## 📋 Specialized Guides

- **Backend:** [backend/CLAUDE.md](backend/CLAUDE.md) — AutoPilot services, broker adapters, AI/ML, pytest markers
- **Frontend:** [frontend/CLAUDE.md](frontend/CLAUDE.md) — E2E test rules, Vue patterns, data-testid conventions
- **Quick commands:** [Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md)
- **Current tasks:** [Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md)
- **Root (this file):** Cross-cutting behaviors, production safety, multi-broker architecture

## Quick Decision Tree

**What are you working on?**
- 🔴 **Production debugging?** → STOP! Check [Production vs Development](#0-production-vs-development---never-touch-production)
- 🔧 **Backend code?** → See [backend/CLAUDE.md](backend/CLAUDE.md)
- 🎨 **Frontend code?** → See [frontend/CLAUDE.md](frontend/CLAUDE.md)
- 🧪 **Tests failing?** → Run `Skill(skill="test-fixer")` or see [Testing](#testing)
- 🐛 **Bug fix?** → See [backend/CLAUDE.md](backend/CLAUDE.md) or [frontend/CLAUDE.md](frontend/CLAUDE.md)
- ✨ **New feature?** → Read [Critical Behaviors](#critical-mandatory-behaviors) first
- 📚 **Architecture questions?** → Check [Core Architecture](#core-purpose-multi-broker-architecture) or [docs/README.md](docs/README.md)

## Current Work & Roadmap

See **[docs/ROADMAP.md](docs/ROADMAP.md)** for active work, completed features, and planned roadmap.

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

**Requirements:** Python 3.13+ | Node.js 24+ | PostgreSQL | Redis

```bash
# Initial setup
cd backend && copy .env.example .env
# IMPORTANT: Edit .env and change PORT=8000 to PORT=8001
cd ../frontend && copy .env.example .env.local
# Verify .env.local has VITE_API_BASE_URL=http://localhost:8001

# Start dev backend (from backend/)
venv\Scripts\activate && python run.py    # Windows

# Start frontend (from frontend/)
npm run dev

# Run E2E tests (from root)
npm test

# Database migration (from backend/)
alembic revision --autogenerate -m "description" && alembic upgrade head
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

## Common Workflows

**Backend tasks:** [backend/CLAUDE.md](backend/CLAUDE.md) — API endpoints, database models, broker adapters, migrations
**Frontend tasks:** [frontend/CLAUDE.md](frontend/CLAUDE.md) — Vue components, E2E tests, Pinia stores
**Session management:** Use `save-session` / `start-session` skills. Sessions saved to `.claude/sessions/`

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

**Key design:** Dual-path market data (platform-default for all users, optional user upgrade) + per-user order execution. Platform failover chain: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite.

**Complete architecture:** [Broker Abstraction Architecture](docs/architecture/broker-abstraction.md) | [Working Doc](docs/architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md) | [ADR-002](docs/decisions/002-broker-abstraction.md)

---

## Project Overview

Multi-broker options trading platform for Indian markets. **Tech Stack:** FastAPI + Vue 3 + PostgreSQL + Redis + Playwright + pytest. AutoPilot automated trading (26 services). AI-powered regime detection.

**Details:** [backend/CLAUDE.md](backend/CLAUDE.md) | [docs/README.md](docs/README.md)

---

## Important Patterns

### Architectural Rules (CRITICAL)

**All architectural rules are consolidated in** [`.claude/rules.md`](.claude/rules.md):
- Folder structure rules (enforced by PreToolUse hooks)
- Cross-layer import rules (backend ↔ frontend isolation)
- Protected files (production folder, .env, knowledge.db)
- Security rules (encryption, validation)
- Complete enforcement summary (which hook/agent enforces what)

This is the **single source of truth** for architectural constraints. When in doubt, check rules.md first.

### Folder Structure Rules (ENFORCED by hooks)

All rules enforced by PreToolUse hooks. See [.claude/rules.md](.claude/rules.md) for complete rules.

### Broker Abstraction (CRITICAL)

**NEVER directly use broker-specific APIs (KiteConnect, SmartAPI client).** Always use broker adapters and factories. **All symbol references must use canonical format (Kite format) internally.** Use `SymbolConverter` for broker-specific symbols.

**Code examples and unified data models:** See [backend/CLAUDE.md](backend/CLAUDE.md#broker-abstraction-code-examples)

### Trading Constants (CRITICAL)

**NEVER hardcode lot sizes, strike steps, or index tokens.** See [backend/CLAUDE.md](backend/CLAUDE.md#trading-constants-backend) | [frontend/CLAUDE.md](frontend/CLAUDE.md#trading-constants-frontend).

### Database Patterns

See [backend/CLAUDE.md](backend/CLAUDE.md#database-patterns) for models, routes, encryption, migrations.

### Environment Variables

**Setup:** Copy `.env.example` files to `.env` and update with actual values. Port configuration: see [Most Common Mistakes](#-most-common-mistakes-fix-these-first) and [Development Environment](#development-environment).

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
4. **[Automation Workflows Guide](docs/guides/AUTOMATION_WORKFLOWS.md)** - Complete automation system documentation

**Architecture Decision Records:**
- **[ADR-002: Broker Abstraction](docs/decisions/002-broker-abstraction.md)** - Why and how we abstract brokers
- **[TICKER-DESIGN-SPEC.md](docs/decisions/TICKER-DESIGN-SPEC.md)** - Multi-broker ticker architecture (5-component design)
  - [Implementation Guide](docs/guides/TICKER-IMPLEMENTATION-GUIDE.md) | [API Reference](docs/api/multi-broker-ticker-api.md) | [Documentation Index](docs/decisions/ticker-documentation-index.md)
- ~~[ADR-003 v2: Ticker Architecture](docs/decisions/003-multi-broker-ticker-architecture.md)~~ - Superseded (historical reference)

## Testing

**E2E rules:** `data-testid` only, import from `auth.fixture.js`, use `authenticatedPage`. Full guide: [E2E Test Rules](docs/testing/e2e-test-rules.md)
**Test docs:** [docs/testing/README.md](docs/testing/README.md)

---

## Proactive Skills

These skills should be invoked automatically at the right time:
- **`auto-verify`** — after ANY code change
- **`docs-maintainer`** — after code changes that affect docs
- **`learning-engine`** — after fix completions and test outcomes

All other available skills (testing, code gen, broker experts, workflows) are listed in the system prompt and invoked on demand. Full docs: [Automation Workflows Guide](docs/guides/AUTOMATION_WORKFLOWS.md)

---

## Key URLs

Dashboard `/dashboard`, Watchlist `/watchlist`, Positions `/positions`, Option Chain `/optionchain`, Strategy `/strategy`, Strategy Library `/strategies`, AutoPilot `/autopilot`, AI `/ai`, OFO `/ofo`, Settings `/settings`

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

## CI/CD

GitHub Actions runs automatically on push/PR to `main` and `develop`:

| Workflow | File | Description |
|----------|------|-------------|
| **Backend Tests** | `.github/workflows/backend-tests.yml` | pytest with PostgreSQL/Redis services |
| **E2E Tests** | `.github/workflows/e2e-tests.yml` | Playwright with full stack (30min timeout) |
| **Hook Parity** | `.github/workflows/hook-parity.yml` | Validates hook/skill consistency |
| **Deploy** | `.github/workflows/deploy.yml` | Production deployment pipeline |

Allure reports deploy to GitHub Pages on main branch merges.
