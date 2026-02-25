# Debugger Agent Memory

**Purpose:** Track root causes, successful fix strategies, and escalation patterns
**Agent:** debugger
**Last Updated:** 2026-02-25

---

## Patterns Observed

### Root Causes by Category

#### Selector/Locator Errors
- Missing `data-testid` on Vue component — add attribute, use `[screen]-[component]-[element]` convention
- Selector changed after component refactor — check git diff for renamed testids
- Dynamic content not rendered yet — add `await expect(...).toBeVisible()` before interacting

#### Timeout Errors
- AngelOne login takes 20-25s (auto-TOTP generation) — use `timeout: 35000` on login POST
- WebSocket connection timeout — check if backend is running on correct port (8001 dev, 8000 prod)
- Playwright test timeout (30s default) — check if waiting for network idle on slow operations
- SmartAPI auth token expires after 8h — credentials auto-refresh via stored encrypted creds

#### Import/Module Errors
- Missing model import in `alembic/env.py` — autogenerate won't detect new tables
- Circular import in broker adapters — use late imports or restructure
- `from app.services.brokers.factory import get_broker_adapter` fails — check `__init__.py` chain

#### Database Errors
- `asyncpg.exceptions.UndefinedTableError` — run `alembic upgrade head`
- Connection refused — PostgreSQL on VPS (103.118.16.189) may need IP whitelist in `pg_hba.conf`
- `IntegrityError` on duplicate user — same email connecting multiple brokers (fixed in commit 9047335)

#### API/Broker Errors
- "Incorrect api_key or access_token" — SmartAPI token expired (8h) or Kite token expired (24h)
- Kite 403 — access token needs refresh via OAuth re-login
- Rate limit exceeded — check `RateLimiter` per-broker settings (SmartAPI: 1 req/s, Kite: 10 req/s)

---

## Decisions Made

### Successful Fix Strategies

#### E2E Test Fixes
- Always check `data-testid` exists in Vue template before writing test selector
- Use `authenticatedPage` fixture, never raw `page` for authenticated screens
- Import from `auth.fixture.js`, not `@playwright/test`
- For flaky waits: use `await expect(locator).toBeVisible()` not `page.waitForTimeout()`

#### Backend Test Fixes
- Mock broker APIs with `mocker.patch('app.services.brokers.factory.get_broker_adapter')`
- Use `AsyncClient(app=app, base_url="http://test")` for API tests
- Add `@pytest.mark.asyncio` on all async test functions
- SQLite test DB needs ARRAY/UUID/BigInteger/ENUM compiler overrides (see root `conftest.py`)

#### Integration Fixes
- Port mismatch: verify `backend/.env` has `PORT=8001` and `frontend/.env.local` has `VITE_API_BASE_URL=http://localhost:8001`
- CORS errors: check `FRONTEND_URL` in backend `.env` matches actual frontend origin

### Failed Approaches

- Retrying flaky tests without investigating root cause — leads to wasted iterations
- Hardcoding `page.waitForTimeout(5000)` instead of proper Playwright selectors
- Using `git add .` to include untracked files — can stage .env or other secrets

---

## Common Issues

### Recurring Error Patterns

- Wrong port configuration is the #1 cause of "API calls fail" issues
- Missing `await` on DB operations causes `RuntimeWarning: coroutine was never awaited`
- `json.JSONDecodeError` in hooks when workflow-state.json is corrupted — hook_utils handles gracefully

### Flaky Tests

- Login tests: SmartAPI auto-TOTP timing varies (20-25s), can timeout at 30s boundary
- WebSocket tests: connection race condition if backend restart is slow
- Dashboard data tests: depend on market hours for live data availability

### Environmental Issues

- Dev and prod share same PostgreSQL server — use different database names
- Dev and prod share same Redis — use different key prefixes
- Production at `C:\Apps\algochanakya` — NEVER touch, NEVER read, NEVER restart

---

## Escalation Patterns

### When to Use ThinkHard

- Async race conditions in WebSocket ticker pool
- Cross-broker symbol conversion edge cases
- AutoPilot condition engine logic with multiple nested conditions

### When to Recommend Human Review

- Production database schema changes (shared with dev)
- Broker API credential issues (encrypted, can't inspect)
- PM2 process management (production only)

---

## Last Updated

2026-02-14: Agent memory system initialized
2026-02-25: Populated with baseline data from codebase history and common issues
