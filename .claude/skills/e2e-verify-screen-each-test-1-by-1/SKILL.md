---
name: e2e-verify-screen-each-test-1-by-1
description: >
  Run E2E tests for one or more screens one test at a time with visual screenshot
  verification after each. On failure, invoke fix-loop to repair, then retest.
  Processes features in logical order: foundation → data → live → edge → visual.
allowed-tools: "Bash Read Grep Glob Write Edit Skill Agent"
argument-hint: "<screen1> [screen2] [--max-fix-attempts 2] [--skip-visual] [--dry-run]"
version: "2.1.0"
type: workflow
triggers:
  - /e2e-verify-screen-each-test-1-by-1
  - "verify all e2e tests for a screen one by one"
  - "run each test individually with visual check"
  - "test screen one at a time with fix loop"
  - "sequential e2e verification"
---

# E2E Verify Screen — Each Test 1-by-1

Run E2E tests for specified screens **one test at a time**, verifying each with
a screenshot before proceeding. Failed tests trigger `/fix-loop` automatically.

**Arguments:** $ARGUMENTS

---

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `<screen>` | (required) | Screen name(s) matching `tests/e2e/specs/{screen}/` directories |
| `--max-fix-attempts` | 2 | Max fix-loop invocations per failing test before logging as known issue |
| `--skip-visual` | false | Skip screenshot verification (faster, less thorough) |
| `--dry-run` | false | List tests in order without running them |

**Examples:**
```bash
/e2e-verify-screen-each-test-1-by-1 dashboard optionchain
/e2e-verify-screen-each-test-1-by-1 positions --max-fix-attempts 3
/e2e-verify-screen-each-test-1-by-1 dashboard --dry-run
```

---

## Failure Mode Analysis

| # | Failure Mode | Prevention | Where Embedded |
|---|---|---|---|
| 1 | Screen directory doesn't exist → silent empty run | Validate `tests/e2e/specs/{screen}/` exists before proceeding | STEP 0 |
| 2 | Fix-loop changes break previously passing tests | Run auto-verify on all changed files after all features complete | STEP 3A |
| 3 | Grep extracts wrong test names → runs nothing or wrong test | Use `--grep` with exact test title string; verify match count > 0 | STEP 2 |

---

## STEP 0: Discover and Order Tests

Validate inputs and build the ordered test execution plan.

For each `<screen>` argument:

1. **Validate directory exists**: `tests/e2e/specs/{screen}/` must exist. If not, report error and skip that screen.
2. Glob `tests/e2e/specs/{screen}/*.spec.js` to find all spec files.
3. Sort spec files into logical execution order by type suffix:

| Priority | Suffix | Rationale |
|----------|--------|-----------|
| 1 | `.happy` | Core flows must work first |
| 2 | `.api` | Data loading depends on happy path |
| 3 | `.websocket` | Live updates depend on API working |
| 4 | `.strikefinder.*` | Feature-specific (option chain) |
| 5 | `.edge` | Edge cases after happy path verified |
| 6 | `.validation` | Input validation |
| 7 | `.bugs` | Regression tests |
| 8 | `.selection` | UI interactions |
| 9 | `.keyboard` | Keyboard shortcuts |
| 10 | `.greeks` | Domain-specific UI |
| 11 | `.interval` | Polling/timing |
| 12 | `.strikesrange` | Range calculations |
| 13 | `.uidetails` | UI polish |
| 14 | `.visual` | Visual regression (needs stable UI) |
| 15 | `.audit` | Accessibility (run last) |
| 16 | `.consistency` | Design system checks |

4. Within each spec file, extract individual test names:
   ```bash
   grep -n "^\s*test(" <file> | sed "s/.*test('//" | sed "s/'.*//"
   ```
5. Verify at least 1 test was extracted per spec file — if 0, warn and skip that file.
6. Group tests into **features** — one feature per spec file.

If `--dry-run`, print the ordered feature/test list and exit.

---

## STEP 1: Pre-Read Context

Read key files for the screen(s) being verified to understand the code under test.
This context enables accurate fix-loop diagnosis when tests fail.

- `tests/e2e/pages/{Screen}Page.js` — page object (if exists)
- `tests/e2e/fixtures/` — relevant fixtures
- `frontend/src/views/{Screen}View.vue` — the actual screen component
- `backend/app/api/routes/` — related backend routes

---

## STEP 2: Execute Feature-by-Feature Test Loop

Run each test individually, verify with screenshot, and fix on failure.

```
FOR each feature in sorted_features:
  LOG "── FEATURE: {feature_name} ({n} tests) ──"

  FOR each test in feature:
    LOG "  Running: {test_name}"

    # Run single test
    npx playwright test {spec_file} --grep "{test_name}" --reporter=list

    # Verify grep matched exactly 1 test — if 0, warn and skip
    IF matched_test_count == 0:
      LOG "  WARNING: grep matched no tests for '{test_name}' — skipping"
      Continue to next test

    # Capture screenshot (unless --skip-visual)
    IF NOT --skip-visual:
      Capture screenshot of the test result
      Invoke /e2e-visual-run to verify screenshot
      Use screenshot verdict as the authoritative pass/fail signal

    IF test PASSED:
      LOG "  PASSED"
      Continue to next test

    IF test FAILED:
      fix_attempts = 0
      WHILE fix_attempts < max_fix_attempts AND test still FAILING:
        fix_attempts += 1
        LOG "  FAILED — invoking /fix-loop (attempt {fix_attempts}/{max_fix_attempts})"

        Invoke /fix-loop (see STEP 2A for parameters)

        # Retest after fix
        npx playwright test {spec_file} --grep "{test_name}" --reporter=list

        IF NOT --skip-visual:
          Capture screenshot → /e2e-visual-run verify

      IF test STILL FAILING after max attempts:
        LOG "  KNOWN ISSUE: {test_name} — failed after {max_fix_attempts} fix attempts"
        Add to known_issues list
        Continue to next test (do NOT block remaining tests)

  LOG "── FEATURE COMPLETE: {passed}/{total} passed ──"

LOG "── ALL FEATURES COMPLETE ──"
```

### STEP 2A: Fix-Loop Invocation Detail

Each `/fix-loop` invocation receives:

| Parameter | Value |
|-----------|-------|
| `failure_output` | Playwright test output from the failing run |
| `retest_command` | `npx playwright test {spec_file} --grep "{test_name}"` |
| `max_iterations` | 3 (internal to fix-loop; separate from per-test max_fix_attempts) |
| `files_of_interest` | Page object, spec file, and Vue component for the screen |

After `/fix-loop` returns, retest the specific test to confirm the fix. If
`/fix-loop` reports UNRESOLVED, increment `fix_attempts` and try again with
the new failure output (which may differ after partial fixes).

---

## STEP 3: Post-Verification

Run regression checks and finalize after all features are processed.

### STEP 3A: Run Auto-Verify

Invoke `/auto-verify` on all changed files to catch regressions introduced by fixes:

```
Skill("/auto-verify", args="--files <changed_files>")
```

If `/auto-verify` reports FAILED, log the regression but do NOT re-enter the
fix loop — report it in the summary for manual triage.

### STEP 3B: Update Documentation (Conditional)

If any architecture changed during fixes (new routes, adapter modifications,
schema changes):

```
Skill("/docs-maintainer")
```

### STEP 3C: Commit (Conditional)

If any fixes were applied and `/auto-verify` passed:

```bash
git add {specific_changed_files}
git commit -m "fix(e2e): verify and fix {screen} E2E tests

Verified {total} tests across {feature_count} features.
Fixed {fixed_count} tests via fix-loop.
Known issues: {known_issue_count} tests logged for manual review."
```

---

## STEP 4: Generate Summary Report

Produce both a human-readable report and machine-readable JSON.

### Human-Readable Report

```
== E2E Verification Report ==
Screens: {screen_list}
Total tests: {total}
  Passed:        {passed} (including {fixed} fixed by fix-loop)
  Known issues:  {known_issues}
  Skipped:       {skipped}

Fixed tests:
  - {test_name} in {spec_file} — fix: {brief description}

Known issues (failed after {max_fix_attempts} fix attempts):
  - {test_name} in {spec_file} — last error: {error_summary}

Files modified:
  - {file_list}

Auto-verify: PASSED / FAILED
```

### Machine-Readable JSON

Write to `test-results/e2e-verify-screen.json`:

```json
{
  "skill": "e2e-verify-screen-each-test-1-by-1",
  "timestamp": "<ISO-8601>",
  "result": "PASSED|FAILED",
  "screens": ["<screen1>", "<screen2>"],
  "summary": {
    "total": 0,
    "passed": 0,
    "fixed": 0,
    "known_issues": 0,
    "skipped": 0
  },
  "fixed_tests": [
    {
      "test": "<test_name>",
      "spec_file": "<path>",
      "fix_attempts": 0,
      "fix_summary": "<brief description>"
    }
  ],
  "known_issues": [
    {
      "test": "<test_name>",
      "spec_file": "<path>",
      "last_error": "<error_summary>",
      "fix_attempts_exhausted": 0
    }
  ],
  "auto_verify_result": "PASSED|FAILED|SKIPPED",
  "files_modified": [],
  "duration_ms": 0
}
```

Create `test-results/` directory if it does not exist. This JSON is consumed
by stage gates — see `.claude/rules/testing.md` for the aggregator contract.

---

## Constraints

These constraints apply to ALL fixes made during the loop:

- MUST NOT import SmartConnect, SmartApi, or KiteConnect directly — use broker adapters via `app.services.brokers.factory` — Why: direct imports bypass the abstraction layer and break when users switch brokers
- MUST NOT hardcode broker names as strings — use `BrokerType` enum with `BROKER_NAME_MAP` for DB-to-enum conversion — Why: DB stores 'angelone' but enum uses 'angel'; string comparison silently fails
- MUST use `get_market_data_adapter()` from `app.services.brokers.market_data.factory` for market data — Why: factory handles credential resolution and rate limiting that direct calls skip
- MUST use `INDEX_TOKENS["NIFTY"]` from `app.constants.trading` — never hardcoded integer tokens — Why: token values change with NSE circulars; hardcoded values cause silent data mismatches
- MUST route frontend API calls through `src/services/api.js` — never raw axios — Why: api.js injects auth tokens and handles 401 broker vs auth distinction
- MUST clean up WebSocket subscriptions in `onUnmounted()` — Why: leaked subscriptions accumulate and cause memory/connection exhaustion
- MUST use correct AngelOne keys: `ANGEL_API_KEY` (live), `ANGEL_HIST_API_KEY` (history), `ANGEL_TRADE_API_KEY` (orders) — Why: wrong key returns AG8001 Invalid Token with no other diagnostic

---

## MUST DO

- Always validate screen directory exists before proceeding — Why: non-existent directories produce silent empty runs with a misleading "all passed" report
- Always run tests one at a time with `--grep` — Why: parallel execution masks failures caused by test interaction and makes screenshots unreliable
- Always capture and verify screenshot after each test (unless `--skip-visual`) — Why: screenshot verdict is authoritative; exit code alone misses visual regressions
- Always run `/auto-verify` after all features complete — Why: fix-loop changes can regress previously passing tests in other features
- Always log known issues instead of deleting or skipping tests — Why: deleted tests hide regressions; known issues are tracked and revisited
- Always commit with specific file names, not `git add -A` — Why: prevents accidentally staging unrelated changes or sensitive files

## MUST NOT DO

- MUST NOT run more than `--max-fix-attempts` fix-loops per test — move to next test instead — Why: diminishing returns after 2 attempts; 3rd+ attempts rarely succeed and waste significant time
- MUST NOT block remaining tests when one test is a known issue — continue the loop — Why: one flaky test should not prevent verification of the other 50+ tests in the screen
- MUST NOT modify files outside the screen's spec/page-object/component scope during fix-loop — flag for manual review instead — Why: cross-screen fixes have unpredictable blast radius
- MUST NOT re-enter fix-loop if `/auto-verify` fails — report for manual triage instead — Why: auto-verify failures after the main loop indicate systemic issues, not single-test fixes
- MUST NOT use `networkidle` in any waits — use `domcontentloaded` or element-specific waits instead — Why: WebSocket keeps the network permanently active, causing networkidle to timeout every time

---

## Integration with Other Skills

| Skill | When Invoked | Purpose |
|-------|-------------|---------|
| `/e2e-visual-run` | After each test (unless `--skip-visual`) | Screenshot capture and visual verification |
| `/fix-loop` | On test failure (up to `--max-fix-attempts` times) | Analyze failure, apply fix, retest |
| `/auto-verify` | After all features complete (STEP 3A) | Full regression check on changed files |
| `/docs-maintainer` | If architecture changed during fixes (STEP 3B) | Update documentation to match code |
| `/learn-n-improve` | After session ends | Capture fix patterns for future sessions |

---

## Failure Prevention Map

| # | Failure Mode | Prevention | Step | Constraint |
|---|---|---|---|---|
| 1 | Screen directory doesn't exist → silent empty run | Validate directory exists, error if missing | STEP 0 | "Always validate screen directory exists — Why: silent empty runs" |
| 2 | Fix-loop changes break other tests | Run /auto-verify on all changed files post-loop | STEP 3A | "Always run /auto-verify after all features — Why: regression detection" |
| 3 | Grep matches 0 tests → false positive pass | Verify match count > 0, warn and skip if 0 | STEP 2 | "Always verify grep matched — Why: empty grep silently passes" |

Output format locked: YES (JSON template in STEP 4)
