---
name: run-optionchain-tests
description: >
  Runs all 39 Option Chain tests across 3 phases (backend pytest, frontend Vitest,
  E2E Playwright headed) sequentially one-by-one with market-hours awareness,
  dev stack health checks, fix-loop escalation, regression detection, and summary report.
  Includes Phase 1-3 performance optimization tests (cache, vectorized IV/Greeks, live engine).
allowed-tools: "Bash Read Grep Glob Write Edit Skill Agent"
argument-hint: "[--phase backend|frontend|e2e|all] [--include-live] [--max-fix-attempts 3]"
version: "1.8.0"
type: workflow
triggers:
  - /run-optionchain-tests
  - "run all option chain tests"
  - "test option chain screen end to end"
  - "verify option chain completely"
  - "option chain full test suite"
---

# Run Option Chain Tests — Full Sequential Suite

Run all Option Chain tests across 3 phases (backend, frontend, E2E) **one test at a time**.
Each test is verified before moving to the next. Failures trigger `/fix-loop` automatically
with escalation to `/systematic-debugging` when needed.

**Arguments:** $ARGUMENTS

---

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--phase` | `all` | Which phase(s) to run: `backend`, `frontend`, `e2e`, or `all` |
| `--include-live` | false | Include `tests/live/test_live_option_chain.py` (hits real broker APIs) |
| `--max-fix-attempts` | 3 | Max `/fix-loop` cycles per failing test before escalating to `/systematic-debugging` |

---

## STEP 0: Environment and Market Status Check

Verify prerequisites before running any tests. Skipping this causes cascading failures
that waste fix-loop cycles on non-code issues.

### 0a. Detect Market Status (IST)

Determine current NSE market status using IST (UTC+5:30). This affects what "passing" means
for E2E tests — 16 of 18 specs use `getDataExpectation()` from `market-status.helper.js`.

```
Market Open:   Mon-Fri 9:15-15:30 IST, not an NSE holiday → expect live data
Market Closed: Outside hours, weekends, holidays → expect empty states or cached data
```

Log the detected status at the start:

```
[MARKET STATUS] {OPEN|CLOSED} — {Day} {Date} {Time} IST
  Implication: E2E tests will {expect live data | accept empty states}
```

### 0b. Check Credentials

Two sets of credentials are needed — one for app login, one for market data:

**Zerodha/Kite (app login):** Check `tests/config/credentials.js` exists with:
- `kite.userId` — Zerodha user ID
- `kite.password` — Zerodha password
- TOTP is entered manually during OAuth flow (browser pauses for 60s)

**AngelOne/SmartAPI (market data source):** Check `backend/.env` contains:
- `ANGEL_API_KEY` (live data)
- `ANGEL_CLIENT_ID`
- `ANGEL_PIN`
- `ANGEL_TOTP_SECRET`

If any are missing, STOP and report which credentials are missing.

### 0c. Phase-Specific Prerequisites

| Phase | Requires Dev Stack? | Requires Auth? |
|-------|-------------------|----------------|
| Backend (Phase 1) | NO — uses SQLite in-memory | NO |
| Frontend (Phase 2) | NO — unit tests with mocks | NO |
| E2E (Phase 3) | YES — backend:8001 + frontend:5173 | YES — Zerodha OAuth login |

For Phase 3 only:
1. Start backend if not running: `cd backend && source venv/Scripts/activate && python run.py`
2. Start frontend if not running: `cd frontend && npm run dev`
3. Health check: verify `http://localhost:8001/docs` returns 200
4. Health check: verify `http://localhost:5173` loads
5. If either health check fails, STOP and report — do not proceed to E2E tests

### 0d. App Login and Data Source Configuration

The app uses **dual-broker architecture**: one broker for login/orders, another for market data.

**Login via Zerodha/Kite OAuth:**

Zerodha does NOT support auto-TOTP — the user must enter password and TOTP manually
when no valid session exists.

**Step 1 — Check for existing valid token (auto-login path):**

1. Check if `tests/config/.auth-token` file exists
2. If it exists, read the JWT token from the file
3. Validate via `GET http://localhost:8001/api/auth/me` with `Authorization: Bearer <token>`
4. If valid (200 response) → **skip login entirely, reuse existing session**
   - Log: `[AUTH] Valid Zerodha token found — skipping login`
5. Also check `.auth-state.json` exists (Playwright storageState) — if missing, regenerate it
   from the valid token by writing the storageState JSON format

**Step 2 — If no valid token, open browser UI for manual Zerodha login:**

If token file is missing, expired, or validation returns non-200:

1. Open a **headed** (not headless) Chromium browser, **fullscreen/maximized**
2. Navigate to `http://localhost:5173/login`
3. Wait for login page to load (`domcontentloaded`, NOT `networkidle`)
4. Click the **Zerodha login button** (`[data-testid="login-zerodha-button"]`)
5. Browser redirects to `kite.zerodha.com` — wait for the Kite login page to load
6. **STOP AND WAIT for user** — display clear message:
   ```
   ========================================
     ZERODHA LOGIN — MANUAL INPUT REQUIRED
     Please enter your User ID, Password, and TOTP
     in the browser window (waiting up to 120s)
   ========================================
   ```
7. Wait for the browser URL to redirect back to the app (contains `/callback` or returns to
   `localhost:5173`) — timeout: **120 seconds**
   - Do NOT auto-fill any credentials — let the user enter everything manually
   - Do NOT close the browser or navigate away while waiting
8. After successful redirect back to the app:
   a. Extract token from browser localStorage: `localStorage.getItem('access_token')`
   b. Save token to `tests/config/.auth-token` (plain text JWT)
   c. Save Playwright storageState to `tests/config/.auth-state.json`
   d. Log: `[AUTH] Zerodha login successful — token saved`

**Step 3 — Handle login failure:**

If login fails (timeout after 120s, user closes browser, redirect never happens):
- STOP and report the error clearly
- Do NOT attempt to run any E2E tests without a valid session
- Suggest: "Please re-run the skill and complete the Zerodha login within 120 seconds"

**Step 4 — Verify and set SmartAPI as market data source via Settings UI:**

After login, ensure the market data source is SmartAPI (AngelOne). Check via API first,
then use the Settings UI if it needs changing.

1. Call `GET /api/preferences/` with auth token to check current `market_data_source`
2. If already `smartapi` → log `[DATA SOURCE] SmartAPI already active — skipping settings change` and skip to Step 5
3. If NOT `smartapi` (e.g., `upstox`, `platform`, or any other value):
   a. Navigate to `http://localhost:5173/settings` in the browser
   b. Wait for settings page to load (`domcontentloaded`)
   c. Click the SmartAPI source card (`[data-testid="settings-source-card-smartapi"]`)
   d. Click the Save button (`[data-testid="settings-broker-save-btn"]`)
   e. Wait for save success message (`[data-testid="settings-broker-save-success"]`) to appear
   f. Log: `[DATA SOURCE] Changed market data source to SmartAPI via Settings UI`
4. Verify SmartAPI credentials are active: `GET /api/smartapi/credentials` → `has_credentials: true, is_active: true`
5. If SmartAPI session is not active, call `POST /api/smartapi/authenticate` (uses auto-TOTP from `.env`)

**Pre-warm SmartAPI instrument cache:**
After SmartAPI is authenticated, pre-warm the instrument cache to avoid cold-start timeouts:
1. Call `GET /api/options/expiries?underlying=NIFTY` with the auth token
2. This triggers SmartAPI to download ~185k instruments (takes 20-30s)
3. Without this, the first option chain test will timeout waiting for instrument data

This ensures:
- **Login/orders:** Zerodha/Kite (OAuth with manual TOTP)
- **Market data:** AngelOne/SmartAPI (auto-TOTP, no manual intervention)
- **Instruments:** Pre-loaded before tests start

### 0e. SmartAPI Zero-Data Detection

**Known issue (observed 2026-04-16):** SmartAPI sometimes returns 0.00 LTP and 0 OI for ALL
option strikes even during market hours. This is a **broker data quality issue**, not a code bug.

**Detection:** After pre-warming the instrument cache (Step 0d), make a quick validation call:
```
GET /api/optionchain/chain?underlying=NIFTY&expiry={nearest_expiry}
```
Check if ALL `ce.ltp` and `pe.ltp` values in the response are 0.00. If so:

1. Log: `[SMARTAPI WARNING] Zero LTP for all strikes — broker may not be providing live data`
2. **Do NOT fix-loop** data-dependent E2E tests that fail due to zero data
3. Tests that fail solely because SmartAPI returns zeros should be logged as **BLOCKED (broker data)**,
   not as code failures requiring fix-loop
4. Affected specs: `crossverify.api`, `validation` (OI assertions), `uidetails` (OI bars),
   `bugs` (ATM LTP), `websocket` (live tick updates)

This check saves significant time — without it, 5+ specs trigger fix-loops that cannot
succeed because the root cause is outside the application.

### 0f. Phase Continuation Policy

Phases are independent — **always continue to the next phase** even if the previous phase
has BLOCKED tests. Backend test failures do not indicate E2E will fail (different test
isolation), and vice versa. The summary report at the end captures all results across phases.

---

## STEP 1: Run Backend Tests (Phase 1)

Run from `backend/` with venv active. Each file runs independently with `pytest <file> -v`.

**Execution order:**

| # | Test File | Focus | Tests |
|---|-----------|-------|-------|
| 1 | `tests/backend/autopilot/test_services_option_chain.py` | Service logic | ~20 |
| 2 | `tests/backend/autopilot/test_api_option_chain.py` | API routes | ~15 |
| 3 | `tests/backend/routes/test_optionchain_iv.py` | IV calculations | 6 |
| 4 | `tests/backend/routes/test_optionchain_performance.py` | Performance/caching | 4 |
| 5 | `tests/backend/routes/test_optionchain_upstox_keying.py` | Upstox symbol keying | ~5 |
| 6 | `tests/backend/options/test_option_chain_ltp_zero.py` | LTP zero edge case | 7 |
| 7 | `tests/backend/options/test_optionchain_eod_integration.py` | EOD integration | 8 |
| 8 | `tests/backend/options/test_phase1_optimizations.py` | P1: cache TTL, OTM skip, parallel spot | 14 |
| 9 | `tests/backend/options/test_phase2_vectorized_greeks.py` | P2: numpy vectorized IV/Greeks | 20 |
| 10 | `tests/backend/options/test_phase3_live_engine.py` | P3: ticker-fed live engine | 18 |
| 11 | `tests/test_option_chain_perf.py` | Perf benchmarks | ~5 |

**Conditional:** If `--include-live` is set, also run:
| 12 | `tests/live/test_live_option_chain.py` | Live broker API (requires SmartAPI session) | ~5 |

### Per-Test Process (Phase 1)

```
For each test file:
  1. Run: pytest <file> -v
  2. If PASS → log result, move to next
  3. If FAIL → invoke /fix-loop with retest_command: "pytest <file> -v" max_iterations: {max-fix-attempts}
     a. If fix-loop resolves → re-run ALL previously passing backend tests to catch regressions
        - If regression found → fix regression first, then continue
     b. If fix-loop exhausts attempts → invoke /systematic-debugging
        - After systematic-debugging fix → re-run ALL previously passing backend tests
     c. If still unresolved → log as BLOCKED, move to next test
```

---

## STEP 2: Run Frontend Unit Tests (Phase 2)

Run from `frontend/`. Each file runs with `npx vitest run <file>`.

| # | Test File | Focus |
|---|-----------|-------|
| 1 | `tests/stores/optionchain.store.test.js` | Pinia store logic |
| 2 | `tests/stores/optionchain.lot-size.test.js` | Lot size calculations |

### Per-Test Process (Phase 2)

Same process as Phase 1 but with retest command: `npx vitest run <file>`.

---

## STEP 3: Run E2E Tests (Phase 3)

Run from project root. **Always use `--headed` mode** for all E2E tests.
Browser MUST launch fullscreen/maximized.

**Command:** `npx playwright test <file> --headed`

### Execution Order (dependency-ordered: core → specialized → quality → regression)

| Tier | # | Spec File | Type | Notes |
|------|---|-----------|------|-------|
| **Core** | 1 | `optionchain.happy.spec.js` | happy | Must pass before others |
| | 2 | `optionchain.edge.spec.js` | edge | Error states, boundaries |
| **API** | 3 | `optionchain.api.spec.js` | api | API response validation |
| | 4 | `optionchain.crossverify.api.spec.js` | api | External NSE dependency — SKIPs are OK |
| **Functional** | 5 | `optionchain.greeks.spec.js` | greeks | Greeks display/calc |
| | 6 | `optionchain.websocket.spec.js` | websocket | Live tick updates |
| | 7 | `optionchain.selection.spec.js` | selection | Strike selection |
| | 8 | `optionchain.strikefinder.happy.spec.js` | happy | Strike finder core |
| | 9 | `optionchain.strikefinder.edge.spec.js` | edge | Strike finder edges |
| | 10 | `optionchain.strikefinder.select.spec.js` | select | Strike finder selection |
| | 11 | `optionchain.strikesrange.spec.js` | range | Strikes range filter |
| | 12 | `optionchain.keyboard.spec.js` | keyboard | Keyboard navigation |
| | 13 | `optionchain.interval.spec.js` | interval | Auto-refresh |
| | 14 | `optionchain.uidetails.spec.js` | ui | UI detail verification |
| | 15 | `optionchain.validation.spec.js` | validation | Input validation (serial mode) |
| **Quality** | 16 | `optionchain.audit.spec.js` | audit | UI consistency/a11y |
| | 17 | `optionchain.visual.spec.js` | visual | Visual regression |
| **Regression** | 18 | `optionchain.bugs.spec.js` | bugs | Known bug regressions |

### Core Tier Gate

If BOTH `optionchain.happy.spec.js` AND `optionchain.edge.spec.js` fail, STOP Phase 3
and report — core flows are broken, running specialized tests is wasteful.

### External Dependency Handling

`optionchain.crossverify.api.spec.js` calls NSE India's v3 API directly AND compares against
SmartAPI data. Two independent failure modes:
- If tests SKIP (NSE unreachable/rate-limited) → log as SKIP with reason, move on
- If SmartAPI returns zero data for all strikes (see Step 0e) → log as BLOCKED (broker data), move on
- Do NOT treat external-dependency skips or broker zero-data as code failures
- Do NOT attempt to fix NSE connectivity issues or SmartAPI data quality issues

### Serial Mode Spec Handling

`optionchain.validation.spec.js` uses `mode: 'serial'` — tests within it are order-dependent.
If test N fails, tests N+1, N+2... will likely cascade-fail. When this happens:
- Only fix-loop the FIRST failure in the file
- After fix, re-run the ENTIRE validation spec (not individual tests)
- Do NOT fix-loop each cascade failure independently — it wastes cycles

### Visual Regression Spec Handling

`optionchain.visual.spec.js` compares screenshots against baseline PNGs in
`optionchain.visual.spec.js-snapshots/`. Two types of failure:

| Failure Type | How to Detect | Action |
|---|---|---|
| **Visual bug** | UI element missing, broken layout, wrong colors | Fix the code via `/fix-loop` |
| **Legitimate UI change** | Layout intentionally changed, baselines are stale | Update baselines: `npx playwright test optionchain.visual.spec.js --update-snapshots` |

Ask the user if unsure whether a visual diff is a bug or a legitimate change.

### Happy Path Cold-Start Transient

`optionchain.happy.spec.js` is the first E2E spec to run. On the first run of a test suite,
SmartAPI may have cold-start latency (instrument cache warming, first authenticated request).
This can cause the happy path spec to fail on its FIRST run but pass on immediate re-run.

- If happy path fails on first run → **re-run once** before entering fix-loop
- If it passes on re-run → log as PASS (transient cold start), continue
- If it fails on re-run too → proceed to fix-loop as normal

### Chain Load Timeout Resilience

`OptionChainPage.waitForChainLoad()` uses a `Promise.race` with 30s timeout for table/empty/error
states. When SmartAPI is slow or degraded, this frequently times out in `beforeEach` hooks,
causing entire spec files to fail before any test runs.

**Known affected specs:** `uidetails`, `bugs`, `interval`, `websocket`, `audit`

When a spec fails because ALL tests timeout in `beforeEach`:
- This is a SmartAPI responsiveness issue, NOT a test code bug
- Do NOT fix-loop the timeout — it will waste all attempts
- Log as BLOCKED (SmartAPI slow) and move to next spec
- If only SOME tests timeout, the spec is partially working — fix-loop is appropriate

### User Preference vs Test Assumptions

Tests that assume specific default values (e.g., "50pt interval is default") may fail because
user preferences override defaults. The option chain store uses `userPrefsStore.pnlGridInterval`
(currently 100) as the effective default when the user hasn't explicitly selected an interval.

- Check `GET /api/preferences/` to see current user settings before debugging interval/filter tests
- Tests should verify behavior (e.g., "one radio is checked") not specific values (e.g., "50pt is checked")
- If a test hardcodes a default that conflicts with user prefs, fix the test to be preference-agnostic

### data-testid Reference for Common Elements

LTP cells in the option chain table use per-strike testids, NOT a generic class:
- **CE LTP:** `optionchain-ce-ltp-{strike}` (e.g., `optionchain-ce-ltp-24000`)
- **PE LTP:** `optionchain-pe-ltp-{strike}` (e.g., `optionchain-pe-ltp-24000`)
- **Selector for all LTP cells:** `[data-testid^="optionchain-ce-ltp-"], [data-testid^="optionchain-pe-ltp-"]`

Do NOT use `optionchain-ltp-cell` — this testid does not exist in the Vue component.

### WebSocket Spec Market-Hours Warning

`optionchain.websocket.spec.js` has a 600s (10 min) timeout block for live price update tests.
During **market closed hours**, these tests may timeout waiting for ticks that never arrive.
- If market is CLOSED and websocket tests timeout → log as SKIP (expected), not FAIL
- Do NOT attempt to fix websocket timeout during market closed hours

### Per-Test Process (Phase 3)

```
For each spec file:
  1. Run: npx playwright test tests/e2e/specs/optionchain/<file> --headed
  2. Invoke /e2e-verify-screen-each-test-1-by-1 optionchain for UI/data verification
  3. If PASS → log result, move to next
  4. If SKIP → log as SKIP with reason (market closed, NSE unreachable), move to next
  5. If FAIL → invoke /fix-loop with:
       retest_command: "npx playwright test tests/e2e/specs/optionchain/<file> --headed"
       max_iterations: {max-fix-attempts}
     a. If fix-loop resolves → re-run ALL previously passing E2E tests in current tier
        - If regression found → fix regression first, then continue
     b. If fix-loop exhausts attempts → invoke /systematic-debugging
     c. If still unresolved → log as BLOCKED, move to next test
  6. Page object changes go in tests/e2e/pages/OptionChainPage.js ONLY
     - NEVER use raw locators in spec files
     - NEVER use CSS class selectors — use data-testid via getByTestId()
```

### Screenshot Directory

All screenshots taken during this test run MUST go into a single dedicated folder:

```
D:\Abhay\VibeCoding\algochanakya\screenshots\
```

Create this directory if it does not exist at the start of Phase 3. Clear any previous contents before starting.

| Screenshot Type | Naming Convention | Example |
|---|---|---|
| Pass verification | `{spec}-{test-name}.pass.png` | `happy-should-display-option-chain.pass.png` |
| Failure evidence | `{spec}-{test-name}.fail.png` | `edge-handles-empty-chain.fail.png` |
| Fix-loop iteration | `{spec}-{test-name}.iter{N}.png` | `api-validates-response.iter2.png` |
| Visual diff | `{spec}-{test-name}.diff.png` | `visual-desktop-layout.diff.png` |

- MUST NOT save screenshots to random temp directories, project root, or desktop
- MUST NOT scatter screenshots across spec-specific folders
- All screenshots from one run go in `screenshots/` at the project root

### Browser Rules

- Always run `--headed` (never headless)
- Launch browser fullscreen/maximized
- Do NOT close the browser after testing — leave open for user inspection
- Do NOT use `networkidle` in waitForLoadState — WebSocket keeps network active

---

## STEP 4: Generate Summary Report

After all tests complete (or all phases requested are done), produce:

```
## Option Chain Test Suite — Results

**Run Date:** {date} IST
**Market Status:** {OPEN|CLOSED} — {impact on test expectations}
**Phases Run:** {backend, frontend, e2e}

### Phase 1 — Backend (pytest)
| # | Test File | Result | Fix Applied? |
|---|-----------|--------|-------------|
| 1 | test_services_option_chain.py | PASS/FAIL/BLOCKED | — / Yes: {description} |
...
**Totals:** {passed}/{total} passed, {fixed} fixed, {blocked} blocked

### Phase 2 — Frontend (Vitest)
| # | Test File | Result | Fix Applied? |
|---|-----------|--------|-------------|
...
**Totals:** {passed}/{total} passed, {fixed} fixed, {blocked} blocked

### Phase 3 — E2E (Playwright, headed)
| # | Spec File | Type | Result | Fix Applied? |
|---|-----------|------|--------|-------------|
...
**Totals:** {passed}/{total} passed, {fixed} fixed, {skipped} skipped, {blocked} blocked

### Fixes Applied
| # | File Changed | Description | Phase |
|---|-------------|-------------|-------|
...

### Regressions Caught
| Test | Broken By Fix To | Resolution |
|------|-----------------|------------|
...

### Overall
- Total tests: {N}
- Passed: {N} | Fixed: {N} | Skipped: {N} | Blocked: {N}
```

---

## Performance Optimization Test Learnings (Phase 1-3)

### New Backend Modules Created

| Module | Path | Purpose |
|--------|------|---------|
| `vectorized_greeks.py` | `app/services/options/` | NumPy/SciPy vectorized IV (Newton-Raphson) and Greeks (Black-Scholes) |
| `option_chain_live_engine.py` | `app/services/options/` | Ticker-fed in-memory snapshot cache with O(1) tick routing |

### Phase 1 Test Caveats (test_phase1_optimizations.py)

- **`calculate_iv()` converges for far OTM strikes**: The moneyness skip (`FAR_OTM_MONEYNESS_THRESHOLD = 0.10`)
  is applied in the route loop (`optionchain.py`), NOT inside `calculate_iv()` itself. Tests that expect
  `calculate_iv(tiny_premium, spot, far_otm_strike, dte, True)` to return 0 will FAIL — Newton-Raphson
  can still converge on a valid IV for deep OTM options with small premiums (e.g., 0.05 premium → 28% IV).
  Test the moneyness detection logic separately from the IV function.

- **Python operator precedence with `is False`**: `assert value <= THRESHOLD is False` evaluates as
  `assert value <= (THRESHOLD is False)`, which compares a float to `False`. Always split into:
  ```python
  result = value <= THRESHOLD
  assert result is False
  ```

### Phase 2 Test Caveats (test_phase2_vectorized_greeks.py)

- **scipy.stats.norm overhead at small N**: At 40-80 options, scipy's function call overhead can make
  vectorized Newton-Raphson SLOWER than a pure-Python scalar loop. Do NOT test relative speedup
  (vectorized vs scalar) — test absolute latency instead: `assert elapsed_ms < 50` for 80 options.
  The real-world bottleneck is I/O (SmartAPI calls), not computation.

- **Windows timing variance**: Performance tests on Windows have higher variance than Linux.
  Use generous thresholds (50ms not 20ms) and always include a warm-up call before benchmarking
  to avoid cold-start penalty from scipy module loading.

- **IV tolerance**: Vectorized and scalar IV may differ by up to 1.0 percentage point for the same
  inputs due to different convergence paths. Use `abs(vec - scalar) < 1.0` tolerance, not exact match.

- **Greeks tolerance**: Delta ±0.001, gamma ±0.0001, theta ±0.1, vega ±0.1 are appropriate tolerances
  when comparing vectorized vs scalar results.

### Phase 3 Test Caveats (test_phase3_live_engine.py)

- Tests use `MagicMock` for `NormalizedTick` objects (not real `NormalizedTick` instances).
  The mock must have `.token`, `.ltp`, `.oi`, `.volume` attributes.
- Performance tests (get_snapshot <1ms, on_tick <1ms for 10 ticks) are reliable because
  the engine is pure dict lookups — no I/O, no scipy overhead.

### Frontend SWR Tests (optionchain.store.test.js)

6 new tests in `'optionchain store — stale-while-revalidate (P1-4)'` describe block:
- `isRefreshing` exposed from store
- Chain cleared on first fetch (no stale data)
- Stale data preserved during refresh (same underlying+expiry)
- Chain cleared when underlying changes
- Chain cleared when expiry changes
- `isRefreshing` reset on error

### Integration Pattern: Pre-compute + Lookup

The vectorized IV/Greeks integration in `optionchain.py` uses a pre-compute pattern:
1. Before the main strike loop, collect all options needing local IV into `_vec_entries`
2. Batch-compute via `calculate_iv_and_greeks_batch()` → store results in `_vec_results` dict
3. In the loop, check `_vec_results[(strike, side)]` before falling back to scalar `calculate_iv()`

This minimizes risk vs rewriting the entire 130-line loop. When debugging IV/Greeks issues,
check whether the strike hit the pre-compute path or the scalar fallback — they use different code paths.

### Cache TTL Refactor (option_chain_cache.py) — Session 2026-04-16

`get_cache_ttl_seconds()` was refactored to:
- Return `LIVE_MARKET_CACHE_TTL` (3s) during market hours — NOT `None`
- Always store to Redis (with 3s TTL during market hours for dedup)
- Add ±10% jitter to after-hours TTL to prevent cache stampede at market open
- Floor at 60s minimum

Tests that assumed the old behavior (returns `None` during market, skips Redis writes) need updating.
When mocking `get_cache_ttl_seconds()` in after-hours tests, also mock `random` to control jitter.

### Interval Filter Design — Store `filteredChain` Logic

The `filteredChain` computed property in `optionchain.js` applies interval filtering BEFORE range slicing:
1. If `skipFactor > 1` (100pt on 50pt native data): filter to aligned strikes, then take N on each side
2. If `skipFactor == 1` (native interval): take N on each side directly

**Critical insight:** Both 50pt and 100pt modes show the SAME number of rows (e.g., 21 = 10+ATM+10)
because the range is applied AFTER interval filtering. The difference is in **strike spacing**, not row count.
Tests that assert `count100 < count50` will ALWAYS fail. Instead, verify that strike gaps are wider:
```javascript
// WRONG: expect(count100).toBeLessThan(count50);
// CORRECT: expect(gap100).toBeGreaterThanOrEqual(gap50);
```

### SWR Refresh Button State

`OptionChainView.vue` refresh button uses `:disabled="store.isLoading"`:
- `isLoading` = true during FIRST load (no cached data) → button disabled
- `isRefreshing` = true during SWR refresh (stale data visible) → button enabled, shows "Refreshing..."

Tests should NOT assert `toBeDisabled()` during SWR refresh — instead assert text content:
```javascript
await expect(refreshButton).toContainText(/Loading|Refreshing/);
```

### Visual Regression During Market Hours

Visual tests (`optionchain.visual.spec.js`) are inherently unstable during market hours even with
masks for dynamic data. The 66%+ pixel diff occurs because:
- Live spot prices change the ATM position, shifting which row gets the ATM badge/highlight
- OI bar widths change with live data, affecting masked area boundaries
- WebSocket ticks update between baseline capture and verification (even seconds apart)

Visual regression tests should ideally run during market CLOSED hours for stable baselines.
During market OPEN, log visual failures as BLOCKED (market hours) rather than fix-looping.

### CE OI Bar Soft-Pass Pattern

When broker provides zero OI data (SmartAPI zero-data issue), OI bar width tests fail.
Both CE and PE OI bar tests should have the same soft-pass fallback:
```javascript
if (!foundNonZero) {
  console.log('All CE OI bar widths are zero (broker not providing OI data) — soft pass');
  return;
}
```
The PE test already had this fallback; the CE test was missing it.

### market_data_source "NOT_SET" Is Valid

When `GET /api/preferences/` returns `market_data_source: NOT_SET`, the backend falls back to
the platform adapter (SmartAPI). This is a valid state — do NOT navigate to Settings to change it.
Only change if the value is explicitly a non-SmartAPI broker (e.g., `upstox`).

---

## MUST DO

- Always run STEP 0 (environment check) first — Why: skipping causes cascading failures that waste fix-loop cycles on non-code issues (e.g., backend not running)
- Always check for existing valid Zerodha token FIRST before opening the browser — Why: avoids unnecessary manual login when a valid session already exists
- If no valid token exists, open browser UI to `/login` and click Zerodha button for manual login — Why: Zerodha is the login/order broker; user must enter credentials manually
- Always verify SmartAPI is set as market data source after login — if not, navigate to Settings UI and change it. Why: option chain tests depend on SmartAPI for live prices; wrong data source (e.g., Upstox) means no data or wrong data
- Always detect market status before E2E tests — Why: 16 of 18 E2E specs adapt behavior based on market hours; misinterpreting empty states as failures triggers unnecessary fix-loops
- Always use `--headed` mode and fullscreen for E2E tests — Why: user requires visual verification and leaves browser open for inspection
- Always run tests one-by-one, never in batch — Why: batch runs hide which test caused a failure and make fix-loop targeting impossible
- Always re-run previously passing tests after a fix — Why: fixes can introduce regressions; catching them immediately is cheaper than discovering them at the end
- Always invoke `/fix-loop` before `/systematic-debugging` — Why: fix-loop handles simple failures faster; systematic-debugging is for unclear root causes
- Always log SKIP results with reasons — Why: distinguishes intentional skips (market closed, NSE unreachable) from silent failures
- Always pre-warm SmartAPI instrument cache after authentication — Why: first option chain API call downloads 185k instruments (20-30s); without pre-warm, tests timeout
- Always continue to the next phase even if previous phase has BLOCKED tests — Why: phases are independent; backend failures don't predict E2E failures
- Always leave browser open after E2E testing — Why: user needs to inspect final state
- Always run SmartAPI zero-data detection (Step 0e) before E2E Phase 3 — Why: prevents wasting 5+ fix-loop cycles on broker data quality issues that cannot be fixed in app code
- Always re-run happy path spec once before fix-looping if it fails on first run — Why: SmartAPI cold-start latency causes transient first-run failures that resolve on immediate retry
- Always check user preferences API before debugging tests that assume specific defaults — Why: user prefs override store defaults (e.g., 100pt interval vs 50pt assumed in tests)
- Always use `[data-testid^="optionchain-ce-ltp-"]` prefix selector for LTP cells, never `optionchain-ltp-cell` — Why: the Vue component uses per-strike testids, not a generic one
- Always use absolute latency thresholds (not relative speedup) for vectorized performance tests — Why: scipy overhead at small N makes relative speedup unreliable; absolute latency is what matters for UX
- Always include a warm-up call before performance benchmarks in Phase 1-3 tests — Why: scipy module loading and JIT effects cause first-call overhead that doesn't reflect real-world performance
- Always mock `random` when testing after-hours cache TTL — Why: `get_cache_ttl_seconds()` adds ±10% jitter via `random.random()`; without mocking, TTL values are non-deterministic and assertions fail
- Always verify strike **spacing** (not row count) when testing interval filter switching — Why: `filteredChain` takes N strikes AFTER interval filtering, so 50pt and 100pt show the same row count but different gaps
- Always add soft-pass fallback for OI-dependent assertions (both CE and PE) — Why: SmartAPI zero-data issue returns 0 OI for all strikes; tests that hard-assert non-zero OI will fail due to broker, not code
- Always log visual regression failures as BLOCKED during market OPEN hours — Why: live data changes between baseline capture and verification, causing 60%+ pixel diffs even with masks
- Always accept `market_data_source: NOT_SET` as valid (defaults to SmartAPI platform adapter) — Why: navigating to Settings to "fix" NOT_SET is unnecessary and wastes time

## MUST NOT

- MUST NOT run E2E tests without dev stack health check — start the stack automatically instead. Why: every E2E test fails with connection errors, wasting all fix-loop attempts
- MUST NOT use AngelOne/SmartAPI for app login — use Zerodha/Kite OAuth instead. Why: SmartAPI is the market data source only; app authentication is through Zerodha
- MUST NOT skip the token validation check — always check for existing valid token before opening the browser. Why: avoids unnecessary manual login and saves time
- MUST NOT auto-fill Zerodha credentials — let the user enter User ID, Password, and TOTP manually in the browser. Why: Kite OAuth has no auto-TOTP; user must interact with the Zerodha login page directly
- MUST NOT proceed without opening the browser UI to `/login` and clicking Zerodha when manual login is needed — the UI flow is required. Why: Zerodha OAuth starts from the app's login page, not from a direct URL
- MUST NOT treat external-dependency SKIPs as failures — log them as SKIP and move on. Why: NSE API availability is outside our control; attempting fixes is futile
- MUST NOT use raw locators in spec files — update `OptionChainPage.js` page object instead. Why: raw locators violate project conventions and create maintenance burden
- MUST NOT use `networkidle` in wait strategies — use `domcontentloaded` or element-specific waits. Why: WebSocket connections keep network permanently active, causing timeouts
- MUST NOT run headless mode for E2E — always `--headed`. Why: user requires visual verification
- MUST NOT close the browser after testing — leave open for user inspection. Why: user explicitly requires this for manual verification
- MUST NOT continue E2E Phase 3 if both core tier tests (happy + edge) fail — STOP and report. Why: specialized tests depend on core flows; running them wastes time
- MUST NOT run more than `{max-fix-attempts}` fix-loop cycles without escalating to `/systematic-debugging` — switch strategy instead. Why: repeating the same approach indicates unclear root cause
- MUST NOT fix-loop each individual failure in `optionchain.validation.spec.js` independently — fix the FIRST failure only, then re-run the whole file. Why: serial mode means failures cascade; fixing downstream symptoms wastes cycles
- MUST NOT treat websocket test timeouts during market closed hours as code failures — log as SKIP. Why: no ticks flow when market is closed; 600s timeout is expected behavior
- MUST NOT auto-update visual baselines without asking the user — ask if diff is a bug or intentional change. Why: silently updating baselines masks real visual regressions
- MUST NOT save screenshots to random locations (temp dirs, desktop, nested test folders) — use `screenshots/` at project root only. Why: scattered screenshots are impossible to review and clutter the repo
- MUST NOT fix-loop tests that fail solely due to SmartAPI zero-data — log as BLOCKED (broker data) instead. Why: fix-loop cannot resolve broker data quality issues; it wastes all attempts and produces no useful fix
- MUST NOT assume `optionchain-ltp-cell` exists as a testid — use `optionchain-ce-ltp-{strike}` / `optionchain-pe-ltp-{strike}` prefix selectors. Why: the Vue component uses per-strike testids; using the wrong one causes silent "0 elements found" failures
- MUST NOT hardcode default values (interval, strike range) in test assertions — verify behavior, not specific values. Why: user preferences override store defaults; tests break when run against a different user profile
- MUST NOT fix-loop when ALL tests in a spec timeout in beforeEach — log as BLOCKED (SmartAPI slow) and move on. Why: this indicates SmartAPI responsiveness issues, not test code bugs; fix-loop will exhaust all attempts on the same timeout
- MUST NOT test vectorized vs scalar speedup ratio — test absolute latency (<50ms for 80 options). Why: scipy overhead at small N makes vectorized appear slower than scalar in microbenchmarks despite real-world benefits from batching
- MUST NOT expect `calculate_iv()` to return 0 for far OTM strikes — it can converge on valid IV even with tiny premiums. Why: the moneyness skip is in the route loop, not in the IV function; testing this requires mocking the route context
- MUST NOT use `is False` / `is True` in compound boolean assertions — operator precedence causes `value <= X is False` to evaluate as `value <= (X is False)`. Why: Python precedence bug discovered during Phase 1 testing
- MUST NOT assert `toBeDisabled()` on refresh button during SWR refresh — the button is only disabled during initial `isLoading`, not during `isRefreshing`. Why: SWR design keeps old data interactive; use `toContainText(/Loading|Refreshing/)` instead
- MUST NOT assert `count100 < count50` for interval switching tests — the store takes N strikes AFTER filtering, so both modes show the same row count. Why: `filteredChain` applies range AFTER interval filter; the difference is strike spacing, not count
- MUST NOT assume `get_cache_ttl_seconds()` returns `None` during market hours — it returns `LIVE_MARKET_CACHE_TTL` (3s). Why: cache refactor changed behavior; tests expecting None fail during market hours
- MUST NOT assume `store_cached_response()` skips Redis during market hours — it always stores with TTL. Why: cache refactor always writes to Redis; the "skip" behavior was removed in favor of short 3s TTL
- MUST NOT fix-loop visual regression failures during market OPEN hours — log as BLOCKED (market hours). Why: live data changes between baseline capture and verification; even freshly updated baselines fail seconds later
- MUST NOT navigate to Settings to change `market_data_source` when value is `NOT_SET` — this is valid and defaults to SmartAPI platform adapter. Why: unnecessary navigation wastes time; `NOT_SET` is the expected default state
