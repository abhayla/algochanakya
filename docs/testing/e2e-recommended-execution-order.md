# E2E Test Suite — Execution Order Analysis

**Last Updated:** 2026-03-02

Optimal execution order for the Playwright E2E test suite, based on dependency analysis of auth state, data preconditions, side effects, and isolation requirements.

---

## Infrastructure Summary

| Setting | Value |
|---------|-------|
| **Total spec files** | ~110 across 18 screen directories |
| **Workers** | 4 local, 2 CI |
| **fullyParallel** | `true` (default) |
| **Global setup** | `global-setup.js` — AngelOne auto-TOTP login, saves `.auth-state.json` + `.auth-token`, pre-warms SmartAPI instruments |
| **Auth model** | Shared `storageState` injected at context creation; `authenticatedPage` fixture validates token is live |
| **Projects** | `chromium` (with auth, skips `*.isolated.spec.js`) and `isolated` (no auth, fresh context) |
| **Serial suites** | 9 (header x2, autopilot x5, ai x1, strategy x1) |

---

## Per-Screen Analysis

### 1. `login/` — 4 specs

| Spec | Auth | Dependencies | Side Effects | Parallel? |
|------|------|-------------|--------------|-----------|
| `login.isolated.spec.js` | **None** (isolated project) | Frontend running | None | Yes |
| `login.edge.spec.js` | Uses raw `page` | Frontend running | **Clears localStorage** | Caution |
| `login.api.spec.js` | `TEST_AUTH_TOKEN` env | Backend `/api/auth/*` | None (reads only) | Yes |
| `login.audit.spec.js` | `authenticatedPage` | Frontend running | None | Yes |

**Flags:**
- `login.isolated.spec.js` — **MUST run in isolation** (separate Playwright project, fresh context)
- `login.edge.spec.js` — Calls `localStorage.clear()`. Safe because it uses raw `page` (not `authenticatedPage`), but **could poison other tests in the same worker** if Playwright shares contexts

---

### 2. `dashboard/` — 3 specs

| Spec | Auth | Dependencies | Side Effects | Parallel? |
|------|------|-------------|--------------|-----------|
| `dashboard.happy.spec.js` | `authenticatedPage` | None | None (navigation clicks) | Yes |
| `dashboard.edge.spec.js` | Raw `page` | None | **Clears localStorage** (tests redirect) | Caution |
| `dashboard.audit.spec.js` | `authenticatedPage` | None | None | Yes |

**Flags:**
- `dashboard.edge.spec.js` — Same localStorage concern as `login.edge`. Tests unauthenticated redirect by clearing storage.

---

### 3. `watchlist/` — 5 specs

| Spec | Auth | Dependencies | Side Effects | Parallel? |
|------|------|-------------|--------------|-----------|
| `watchlist.happy.spec.js` | Raw `page` | Frontend + backend | None (search, modal open/cancel) | Yes |
| `watchlist.edge.spec.js` | Raw `page` | Frontend + backend | None | Yes |
| `watchlist.visual.spec.js` | `authenticatedPage` | Frontend | None | Yes |
| `watchlist.audit.spec.js` | `authenticatedPage` | Frontend | None | Yes |
| `watchlist.websocket.spec.js` | `authenticatedPage` | Backend + SmartAPI WebSocket | None (reads ticks) | Yes |

**Flags:** All safe to parallel. No DB mutations. WebSocket spec needs live SmartAPI session.

---

### 4. `optionchain/` — 6 specs

| Spec | Auth | Dependencies | Side Effects | Parallel? |
|------|------|-------------|--------------|-----------|
| `optionchain.happy.spec.js` | Raw `page` | Backend `/api/optionchain/*` | None | Yes |
| `optionchain.edge.spec.js` | Raw `page` | Backend | None | Yes |
| `optionchain.api.spec.js` | **Skipped** | — | — | — |
| `optionchain.audit.spec.js` | `authenticatedPage` | Frontend | None | Yes |
| `strikefinder.happy.spec.js` | `authenticatedPage` | **Mocked** (`route.fulfill`) | None | Yes |
| `strikefinder.edge.spec.js` | `authenticatedPage` | **Mocked** | None | Yes |

**Flags:** All safe to parallel. Strike finder tests are fully mocked (best isolation). API spec is skipped.

---

### 5. `positions/` — 5 specs

| Spec | Auth | Dependencies | Side Effects | Parallel? |
|------|------|-------------|--------------|-----------|
| `positions.happy.spec.js` | `authenticatedPage` | Backend + live broker positions | None (reads only) | Yes |
| `positions.edge.spec.js` | `authenticatedPage` | Backend | None | Yes |
| `positions.api.spec.js` | `TEST_AUTH_TOKEN` | Backend `/api/positions/` | None (GET only) | Yes |
| `positions.visual.spec.js` | `authenticatedPage` | Frontend | None | Yes |
| `positions.audit.spec.js` | `authenticatedPage` | Frontend | None | Yes |

**Flags:** All safe to parallel. LTP assertions use soft checks (may skip outside market hours). No writes.

---

### 6. `strategy/` — 6 specs

| Spec | Auth | Dependencies | Side Effects | Parallel? |
|------|------|-------------|--------------|-----------|
| `strategy.happy.spec.js` | `authenticatedPage` | Backend (expiries, option chain) | **Adds legs via UI** (in-memory, not saved) | Yes |
| `strategy.edge.spec.js` | `authenticatedPage` | Backend | **Tests save validation** (disabled button, modals). 2 tests skipped (flaky save). | Yes |
| `strategy.api.spec.js` | `TEST_AUTH_TOKEN` | Backend | Conditional | Conditional |
| `strategy.bugfix.spec.js` | `authenticatedPage` | Backend | Unknown | Yes |
| `strategy.audit.spec.js` | `auditablePage` | Frontend | None (serial: timeout 60s) | Serial |
| `strategy.manual-plan.spec.js` | `authenticatedPage` | Backend | Unknown (timeout 300s!) | Serial |

**Flags:**
- Happy/edge tests add legs in UI but **don't click Save** (skip flaky save tests). No DB writes.
- `strategy.audit` and `strategy.manual-plan` have custom timeouts (60s, 300s).
- `strategy.edge` tests "underlying change confirmation" modal — verifies legs are cleared when switching. In-memory only.

---

### 7. `strategylibrary/` — 10 specs

| Spec | Auth | Dependencies | Side Effects | Parallel? |
|------|------|-------------|--------------|-----------|
| `strategylibrary.happy.spec.js` | `authenticatedPage` | Backend `/api/strategy-library/*` | **CREATES strategies** via deploy (Iron Condor, Bull Call, Short Strangle). Navigates to `/strategy/{id}`. | **No** |
| `strategylibrary.edge.spec.js` | `authenticatedPage` | **Mocked** (route.fulfill) | None | Yes |
| `strategylibrary.api.spec.js` | `TEST_AUTH_TOKEN` | Backend | **POSTs** to wizard, deploy, compare endpoints | **No** |
| `strategylibrary.audit.spec.js` | `authenticatedPage` | Frontend | None | Yes |
| `deploy.bullish.spec.js` | `authenticatedPage` | Backend + option chain data | **CREATES strategies** (bull_call, bull_put, synthetic_long) | **No** |
| `deploy.bearish.spec.js` | `authenticatedPage` | Backend | **CREATES strategies** | **No** |
| `deploy.neutral.spec.js` | `authenticatedPage` | Backend | **CREATES strategies** | **No** |
| `deploy.volatile.spec.js` | `authenticatedPage` | Backend | **CREATES strategies** | **No** |
| `deploy.income.spec.js` | `authenticatedPage` | Backend | **CREATES strategies** | **No** |

**Flags:**
- **6 specs create strategies in the DB** via `POST /api/strategy-library/deploy`. These are the **highest side-effect tests** in the suite.
- Deploy specs use unique strategy names with timestamps (`Date.now()`) to avoid collisions, but parallel deploy of the same template to the same underlying could race.
- `strategylibrary.edge.spec.js` is fully mocked — safe to parallel.
- **Recommendation:** Run deploy specs serially or in a dedicated worker.

---

### 8. `autopilot/` — ~35 specs (largest category)

| Spec Group | Auth | Side Effects | Parallel? |
|------------|------|--------------|-----------|
| `autopilot.happy.spec.js` | `authenticatedPage` | None (reads dashboard) | Yes |
| `autopilot.edge.spec.js` | `authenticatedPage` | None | Yes |
| `autopilot.api.spec.js` | `authenticatedPage` | **POST/PUT/DELETE strategies** (cleanup in beforeAll) | **No** (serial) |
| `autopilot.phases123.spec.js` | `authenticatedPage` | **Serial** (2 suites). Re-entry config, adjustment rules. | **Serial** |
| `autopilot.phase4.spec.js` | `authenticatedPage` | Template deployment? | Conditional |
| `autopilot.phase5a.spec.js` | `authenticatedPage` | Conditional (many skipped) | Yes |
| `autopilot.phase5b-5i.spec.js` | — | **All tests skipped** (not implemented) | Skip |
| `iron-condor-template.spec.js` | `authenticatedPage` | **Serial, 120s timeout. CREATES strategies.** | **Serial** |
| `short-strangle-template.spec.js` | `authenticatedPage` | **Serial, 120s timeout. CREATES strategies.** | **Serial** |
| `autopilot.legs.*.spec.js` (3 files) | `authenticatedPage` | Conditional (skips if no strategies) | Yes |
| `reentry-config.*.spec.js` (2 files) | `authenticatedPage` | Configures re-entry rules | Conditional |
| `adjustment-rules.happy.spec.js` | `authenticatedPage` | Configures adjustment rules | Conditional |
| `roll-wizard.happy.spec.js` | `authenticatedPage` | Conditional (skips) | Yes |
| `autopilot.dropdowns.spec.js` | `authenticatedPage` | None | Yes |
| `strike-ladder-*.spec.js` (2 files) | `authenticatedPage` | **Mocked** (route.fulfill/abort) | Yes |
| `autopilot.backtest.spec.js` | `authenticatedPage` | Conditional (1 skipped) | Yes |
| Other (journal, reports, sharing, etc.) | `authenticatedPage` | Read-only or conditional | Yes |

**Flags:**
- `autopilot.api.spec.js` **beforeAll deletes test strategies** — if run parallel with other autopilot tests that depend on strategy existence, those tests break.
- Template deploy specs (iron-condor, short-strangle) are serial with 120s timeouts — DB writes.
- Phase 5b-5i are entirely skipped (not yet implemented).
- `strike-ladder-*` specs use route mocking — safe to parallel.
- **Recommendation:** Run `autopilot.api.spec.js` first (cleanup), then template deploys serially, then read-only autopilot tests in parallel.

---

### 9. `header/` — 3 specs

| Spec | Auth | Side Effects | Parallel? |
|------|------|--------------|-----------|
| `header.happy.spec.js` | `authenticatedPage` | None | **Serial** (browser context creation timeouts) |
| `header.index.spec.js` | `authenticatedPage` | None (reads index prices) | **Serial** |
| `header.audit.spec.js` | `authenticatedPage` | None | Yes |

**Flags:** Happy and index specs are serial due to browser context creation issues, not data dependencies.

---

### 10. `navigation/` — 3 specs

| Spec | Auth | Side Effects | Parallel? |
|------|------|--------------|-----------|
| `navigation.happy.spec.js` | `authenticatedPage` | None (nav link clicks) | Yes |
| `navigation.cross-screen.spec.js` | `authenticatedPage` | None | Yes |
| `navigation.audit.spec.js` | `authenticatedPage` | None | Yes |

**Flags:** All read-only. Safe to parallel.

---

### 11. `ofo/` — 5 specs

| Spec | Auth | Side Effects | Parallel? |
|------|------|--------------|-----------|
| `ofo.happy.spec.js` | Raw `page` | None | Yes |
| `ofo.edge.spec.js` | `authenticatedPage` | None | Yes |
| `ofo.api.spec.js` | `TEST_AUTH_TOKEN` | **POST /api/ofo/calculate** (idempotent calc, no DB write) | Yes |
| `ofo.calculate.spec.js` | `authenticatedPage` | None | Yes |
| `ofo.step1-test.spec.js` | `authenticatedPage` | None | Yes |

**Flags:** All safe to parallel. The POST to `/api/ofo/calculate` is a stateless calculation — no DB mutation.

---

### 12. `broker-abstraction/` — 2 specs

| Spec | Auth | Side Effects | Parallel? |
|------|------|--------------|-----------|
| `broker-settings.happy.spec.js` | `authenticatedPage` | **Fully mocked** (route.fulfill on `/api/user/preferences/**`) | Yes |
| `broker-banner.edge.spec.js` | `authenticatedPage` | **Fully mocked** | Yes |

**Flags:** Best isolation in the suite. API responses are entirely faked. Safe anywhere.

---

### 13. `auth/` — 1 spec

| Spec | Auth | Side Effects | Parallel? |
|------|------|--------------|-----------|
| `token-expiry-redirect.spec.js` | Raw `page` | **Sets invalid token, verifies cleared after redirect** | Caution |

**Flags:** Manipulates localStorage with invalid tokens. Uses raw `page`, not `authenticatedPage`, so won't break the shared auth state. But could affect other tests in same worker context.

---

### 14. `ai/` — 3 specs

| Spec | Auth | Side Effects | Parallel? |
|------|------|--------------|-----------|
| `ai-implementation.spec.js` | `TEST_AUTH_TOKEN` | **POST to AI endpoints** (conditional, 9 skips) | Conditional |
| `ai-paper-trading.spec.js` | `authenticatedPage` | Conditional | Conditional |
| `ai-autopilot-comprehensive.spec.js` | `authenticatedPage` | **Serial suite** (shared state complexity) | **Serial** |

**Flags:** AI comprehensive test is serial. Implementation spec skips most tests without `TEST_AUTH_TOKEN`.

---

### 15-18. `audit/`, `integration/`, `live/`

| Directory | Specs | Side Effects | Parallel? |
|-----------|-------|--------------|-----------|
| `audit/` (6 files) | Style consistency audits across all screens | None (read-only) | Yes |
| `integration/` (1 file: `oauth-full-flow`) | Full OAuth login flow | **Performs real login** (headed, manual TOTP) | **Isolated** |
| `live/` (1 file: `broker-screens`) | Tests against live broker data | None (reads only) | Market-hours only |

---

## Recommended Execution Order

### Phase 0: Global Setup (automatic)
Runs once. AngelOne auto-TOTP login -> saves auth state -> pre-warms SmartAPI instruments.

### Phase 1: Isolated Project (parallel, separate project)
```
login.isolated.spec.js          — Fresh browser context, no auth
```

### Phase 2: Read-Only Screens (fully parallel, 4 workers)
No DB writes, no state mutation. Safe to run all simultaneously.
```
dashboard.happy, dashboard.audit
watchlist.happy, watchlist.edge, watchlist.visual, watchlist.audit, watchlist.websocket
optionchain.happy, optionchain.edge, optionchain.audit
optionchain.strikefinder.happy, optionchain.strikefinder.edge    [mocked]
positions.happy, positions.edge, positions.api, positions.visual, positions.audit
ofo.happy, ofo.edge, ofo.api, ofo.calculate, ofo.step1-test
navigation.happy, navigation.cross-screen, navigation.audit
broker-abstraction.broker-settings, broker-abstraction.broker-banner  [mocked]
header.happy, header.index                                       [serial within suite]
header.audit
```

### Phase 3: UI-Only Write-Adjacent (parallel, no actual DB writes)
Tests that manipulate UI state (add legs, toggle fields) but don't save to DB.
```
strategy.happy, strategy.edge, strategy.bugfix
strategy.audit                                                   [serial, 60s timeout]
strategy.manual-plan                                             [serial, 300s timeout]
strategylibrary.edge                                             [mocked — safe]
strategylibrary.audit
autopilot.happy, autopilot.edge
autopilot.dropdowns, autopilot.strike-preview
autopilot.legs.happy, autopilot.legs.edge, autopilot.legs.actions  [conditional skips]
strike-ladder-phase2, strike-ladder-integration                  [mocked]
autopilot.backtest, autopilot.journal, autopilot.reports, etc.
```

### Phase 4: DB-Mutating Tests (serial or single-worker)
These create/modify/delete records. Run sequentially to avoid race conditions.
```
autopilot.api.spec.js            — beforeAll DELETES test strategies (cleanup first)
iron-condor-template.spec.js     — serial, 120s, creates strategies
short-strangle-template.spec.js  — serial, 120s, creates strategies
autopilot.phases123.spec.js      — serial (2 suites), re-entry + adjustment config
strategylibrary.happy.spec.js    — deploys Iron Condor, Bull Call, Short Strangle
strategylibrary.deploy.bullish   — deploys 3 bullish strategies
strategylibrary.deploy.bearish   — deploys bearish strategies
strategylibrary.deploy.neutral   — deploys neutral strategies
strategylibrary.deploy.volatile  — deploys volatile strategies
strategylibrary.deploy.income    — deploys income strategies
strategylibrary.api.spec.js      — POSTs to wizard/deploy/compare
ai-implementation.spec.js        — POSTs to AI endpoints (conditional)
ai-autopilot-comprehensive.spec.js  — serial suite
```

### Phase 5: Auth-Manipulating Tests (run last)
These clear or corrupt localStorage. Run after all other tests.
```
login.edge.spec.js               — clears localStorage
dashboard.edge.spec.js           — clears localStorage
auth/token-expiry-redirect.spec.js  — sets invalid token
```

### Phase 6: Special / Manual (run separately)
```
integration/oauth-full-flow.spec.js  — needs headed browser + manual TOTP
live/broker-screens.spec.js          — needs market hours
```

---

## Summary Flags

### Must Run in Isolation (fresh context)
- `login.isolated.spec.js` — already in separate Playwright project

### Must Run Serially (9 suites)
- `header.happy.spec.js` — browser context creation
- `header.index.spec.js` — browser context creation
- `autopilot.phases123.spec.js` — 2 serial suites (re-entry, adjustment)
- `iron-condor-template.spec.js` — DB writes, 120s
- `short-strangle-template.spec.js` — DB writes, 120s
- `ai-autopilot-comprehensive.spec.js` — shared state
- `strategy.audit.spec.js` — 60s timeout
- `strategy.manual-plan.spec.js` — 300s timeout

### Can Run Fully Parallel (safe, no side effects)
All read-only specs (~65-70 files): dashboard, watchlist, optionchain, positions, ofo, navigation, header.audit, audit/*, broker-abstraction (mocked), strike-ladder (mocked), and most autopilot UI tests.

### Have Ordering Constraints
| Spec | Must Run Before/After |
|------|----------------------|
| `autopilot.api.spec.js` (beforeAll cleanup) | **Before** any other autopilot test that reads strategies |
| `strategylibrary.deploy.*.spec.js` | **After** read-only strategylibrary tests (to not pollute list) |
| `login.edge` / `dashboard.edge` / `auth/token-expiry` | **After** all other tests (localStorage manipulation) |
| Global setup | **Before** everything (Playwright enforces this) |

### Currently Skipped (~50+ tests)
- `autopilot.phase5b` through `phase5i` — features not yet implemented
- `optionchain.api.spec.js` — entire file skipped
- `autopilot.backtest` — 1 test (drawdown analysis not implemented)
- Various conditional skips based on `TEST_AUTH_TOKEN`, empty API responses, and runtime data availability

---

## Related Documentation

- **[E2E Test Rules](e2e-test-rules.md)** — Authoring conventions, data-testid, fixture usage
- **[Test Plan](test-plan.md)** — Overall test strategy
- **[Coverage Matrix](coverage-matrix.md)** — Screen-level coverage tracking
- **[Testing README](README.md)** — Testing infrastructure overview
