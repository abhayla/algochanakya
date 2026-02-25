# Tester Agent Memory

**Purpose:** Track flaky tests, coverage trends, and execution time patterns
**Agent:** tester
**Last Updated:** 2026-02-25

---

## Patterns Observed

### Test Execution Patterns

#### E2E Tests
- Location: `tests/e2e/specs/{screen}/`
- Screens: login, dashboard, positions, watchlist, optionchain, strategy, strategylibrary, autopilot, navigation, audit, ofo, header, legacy
- Workers: 2 (conservative for stability, consider 4 locally)
- Auth: Global setup via SmartAPI auto-TOTP, state reused across specs
- Reporters: HTML, JSON, JUnit XML, Allure

#### Backend Tests
- Location: `tests/backend/{module}/`
- Modules: autopilot, options, brokers, ai
- Markers: @unit, @api, @integration, @slow
- Async: All tests use `pytest-asyncio` with `asyncio_mode = auto`
- Coverage: `--cov=app` enabled by default, no minimum threshold enforced
- DB: SQLite with ARRAY/UUID/BigInteger/ENUM compiler overrides in root conftest.py
- Broker tests: 714 passing (413 ticker adapter + 122 core component + 179 REST adapter)

#### Frontend Tests
- Tool: Vitest with happy-dom
- Location: `frontend/src/` (co-located with source)
- Commands: `npm run test:run` (once), `npm run test` (watch), `npm run test:coverage`

---

## Decisions Made

### Test Data Management

#### Authentication
- Uses `.auth-state.json` for Playwright auth persistence
- Token stored in `.auth-token` files
- SmartAPI auto-TOTP takes 20-25s — global setup handles once, shared across specs
- OAuth tests in `isolated` project (fresh context, no auth state reuse)

#### Test Isolation
- Each E2E spec should be independent — no cross-spec dependencies
- Use `authenticatedPage` fixture for authenticated tests
- Import from `auth.fixture.js`, NOT `@playwright/test`
- Clean up WebSocket subscriptions in `onUnmounted()`

### Timeout Policies

- Default E2E: 30s per test (playwright.config.js)
- AngelOne login: 35s (auto-TOTP generation delay, needs extended timeout)
- OAuth full flow: 120s (single worker, `test:oauth:auto` script)
- CI full suite: 30min (GitHub Actions e2e-tests.yml)
- Backend CI: 15min timeout (backend-tests.yml)
- Test rerun verification: 60s E2E, 90s backend, 30s frontend (verify_test_rerun.py)

---

## Common Issues

### Flaky Tests

#### By Screen
- Login: SmartAPI auto-TOTP timing varies (20-25s), can timeout at 30s boundary
- Dashboard: Depends on market hours for live data — may show stale/empty data outside trading hours
- WebSocket tests: Connection race if backend restart is slow

#### By Root Cause
- Timing: Most flakiness from network timing and auto-TOTP delays
- State leakage: Tests sharing auth state can interfere if one test modifies user preferences
- Port mismatch: Tests hitting wrong backend port (8000 prod vs 8001 dev)

### Coverage Gaps

- AutoPilot services: 26 services, many without unit tests (integration tested via E2E)
- AI module: ML pipeline tests limited (model training, feature extraction)
- Order execution adapters (Phase 7): Only Kite adapter fully tested, 5 others have stubs
- Frontend composables: Some `use*.js` composables lack Vitest coverage

### Performance Issues

- Full E2E suite: Can take 15-20 min with 2 workers
- Backend broker tests: 714 tests run in ~30s (fast)
- Login tests: 25s+ per test due to auto-TOTP
- E2E allure report generation: Adds ~30s to test pipeline

---

## Execution Time Trends

### Regression Detection

- Baseline (Feb 2026): Full E2E ~15min, Backend ~30s, Frontend ~10s
- Watch for: Test count growth increasing CI time beyond 30min timeout
- Mitigation: Use `npm run test:main-features` for quick smoke tests (5 screens)

---

## Test Commands Quick Reference

- All E2E: `npm test`
- Single spec: `npx playwright test path/to/spec`
- By screen: `npm run test:specs:{screen}`
- Happy path only: `npm run test:happy`
- Backend all: `cd backend && pytest tests/ -v`
- Backend single: `pytest tests/module/test_file.py::test_func -v`
- Backend markers: `pytest -m unit`, `pytest -m "not slow"`
- Frontend: `cd frontend && npm run test:run`

---

## Last Updated

2026-02-14: Agent memory system initialized
2026-02-25: Populated with baseline data from test configs and codebase analysis
