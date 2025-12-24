---
name: auto-verify
description: Automatically test code changes, capture screenshots, analyze results, and iterate until verified working. Use after making code changes to ensure they work correctly.
---

# Auto-Verify Skill

Automated verification loop for code changes with visual confirmation.

## When to Use

- After making code changes to fix a bug
- After implementing a new feature
- After refactoring existing code
- When you need visual confirmation that changes work

## Workflow

### Step 0: Cleanup Old Screenshots

Before starting, clean up screenshots older than 24 hours:

```powershell
# Create folder if not exists
if (-not (Test-Path "screenshots/verification")) {
    New-Item -ItemType Directory -Path "screenshots/verification" -Force
}

# Delete files older than 24 hours
Get-ChildItem "screenshots/verification" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddHours(-24) } |
    Remove-Item -Force
```

### Step 1: Identify Changed Files

List files modified in this session or use git to identify changes:

```bash
git diff --name-only HEAD
git diff --name-only --cached
```

### Step 2: Detect Affected Feature

Use `docs/feature-registry.yaml` to map changed files to features:

1. Read `docs/feature-registry.yaml`
2. Match changed file paths against `auto_detect_patterns`
3. Identify the feature (e.g., `positions`, `autopilot`, `watchlist`)

**If uncertain:** Ask user which feature/tests to run.

### Step 2b: Map to Specific Test Files

**IMPORTANT:** Instead of running all feature tests, identify the **specific test file(s)** that test the changed code:

#### Common File-to-Test Mappings

| Changed File Pattern | Specific Test File | Grep Pattern (if needed) |
|---------------------|-------------------|--------------------------|
| `PositionsView.vue` | `positions.happy.spec.js` | - |
| `ExitModal.vue` | `positions.happy.spec.js` | `"exit"` |
| `AddModal.vue` | `positions.happy.spec.js` | `"add"` |
| `positions.js` (store) | `positions.happy.spec.js` | - |
| `positions.py` (API) | `positions.api.spec.js` | - |
| `WatchlistView.vue` | `watchlist.happy.spec.js` | - |
| `watchlist.js` (store) | `watchlist.happy.spec.js` | - |
| `watchlist.py` (API) | `watchlist.happy.spec.js` | - |
| `OptionChainView.vue` | `optionchain.happy.spec.js` | - |
| `StrikeFinder.vue` | `optionchain.strikefinder.happy.spec.js` | - |
| `optionchain.py` (API) | `optionchain.api.spec.js` | - |
| `StrategyBuilderView.vue` | `strategy.api.spec.js` | - |
| `strategy.js` (store) | `strategy.api.spec.js` | - |
| `strategy.py` (API) | `strategy.api.spec.js` | - |
| `StrategyLibraryView.vue` | `strategylibrary.happy.spec.js` | - |
| `strategyLibrary.js` (store) | `strategylibrary.happy.spec.js` | - |
| `DashboardView.vue` | `dashboard.happy.spec.js` | - |
| `LoginView.vue` | `login.visual.spec.js` | - |

#### Intelligent Mapping Logic

1. **Vue Components** → Look for test file testing that component
   - Check component's `data-testid` attributes to find matching test assertions
   - Example: `ExitModal.vue` → search for "exit modal" or "positions-exit-modal" in test files

2. **Pinia Stores** → Tests that use that store's functionality
   - `positions.js` → `positions.happy.spec.js` (tests the UI that uses the store)
   - `watchlist.js` → `watchlist.happy.spec.js`

3. **Backend API Routes** → `.api.spec.js` files for that feature
   - `positions.py` → `positions.api.spec.js`
   - `optionchain.py` → `optionchain.api.spec.js`

4. **Backend Services** → API tests + happy path tests
   - `pnl_calculator.py` → `strategy.api.spec.js`
   - `kite_ticker.py` → `watchlist.websocket.spec.js` + `optionchain.websocket.spec.js`

5. **AutoPilot Files** → Match by component/feature name
   - `DashboardView.vue` (autopilot) → `autopilot.phases123.spec.js`
   - `StrategyBuilderView.vue` (autopilot) → `autopilot.phases123.spec.js`
   - `StrategyDetailView.vue` → `autopilot.phases123.spec.js`
   - Adjustment files → `adjustment-rules.happy.spec.js`
   - Legs files → `autopilot.legs.happy.spec.js`

6. **Multiple files changed** → Run the **union** of specific tests (don't duplicate)

### Step 3: Run Targeted Tests

Execute tests using this **priority order**:

#### Priority 1: Specific Test File (PREFERRED)
```bash
npx playwright test tests/e2e/specs/{feature}/{specific}.spec.js
```
Example:
```bash
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js
```

#### Priority 2: Specific Test with Grep Pattern
When only part of a test file is relevant:
```bash
npx playwright test tests/e2e/specs/{feature}/{specific}.spec.js -g "{pattern}"
```
Example:
```bash
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js -g "exit"
```

#### Priority 3: Multiple Specific Tests
When multiple files changed:
```bash
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js tests/e2e/specs/positions/positions.api.spec.js
```

#### Priority 4: Full Feature Tests (FALLBACK ONLY)
**Only use when:**
- Changed file doesn't map to specific tests
- Shared/infrastructure code changed (affects whole feature)
- Uncertain about test scope

```bash
npm run test:specs:positions
```

#### Feature Commands Reference (Use as Last Resort)

| Feature | Test Command |
|---------|--------------|
| positions | `npm run test:specs:positions` |
| watchlist | `npm run test:specs:watchlist` |
| optionchain | `npm run test:specs:optionchain` |
| strategy-builder | `npm run test:specs:strategy` |
| strategy-library | `npm run test:specs:strategylibrary` |
| autopilot | `npm run test:specs:autopilot` |
| dashboard | `npm run test:specs:dashboard` |
| login | `npm run test:specs:login` |

### Step 4: Capture Screenshots

After tests complete (pass or fail), capture screenshots of affected screens:

1. Analyze test file to identify which views/modals/states are tested
2. Run the verification screenshot script:

```bash
node tests/e2e/utils/verification-screenshot.js --feature={feature} --screen={screen}
```

Screenshot naming convention:
- `{feature}_{screen}_{state}_{YYYY-MM-DD_HHmmss}.png`
- Example: `positions_exit-modal_open_2025-12-22_143052.png`

### Step 5: Analyze Results

#### 5a. Analyze Test Output
- Check for passed/failed tests
- Read error messages for failed tests
- Identify the root cause

#### 5b. Analyze Screenshots
Use the Read tool to view screenshots and verify:

1. **Layout correctness** - Elements positioned correctly?
2. **Content accuracy** - Data displayed correctly?
3. **State consistency** - UI reflects expected state?
4. **No visual regressions** - No unintended changes?

See `references/screenshot-analysis-guide.md` for detailed checklist.

### Step 6: Decision Point

Based on analysis:

| Outcome | Action |
|---------|--------|
| Tests pass + Screenshots look correct | **SUCCESS** - Verification complete |
| Tests fail | Analyze error, fix code, go to Step 3 |
| Tests pass but screenshots show issues | Fix code, go to Step 3 |
| Reached 5 attempts | **STOP** - Ask user for guidance |

### Step 7: Fix and Iterate

If issues found:
1. Identify the root cause
2. **Check approval requirements** (see below)
3. Make the fix
4. Increment attempt counter
5. Return to Step 3

## Approval Checkpoints

**STOP and ask user approval before:**

1. **Using mock/dummy data** instead of real API data
2. **Making assumptions** about intended behavior
3. **Modifying test assertions** to match new behavior
4. **Modifying shared utilities** (helpers, fixtures, POMs)
5. **Stopping after 5 attempts** - ask for guidance
6. **Using workarounds** instead of proper fixes

## Attempt Tracking

Track attempts in your responses:
```
[Attempt 1/5] Running tests for positions feature...
[Attempt 2/5] Previous fix didn't work. Trying alternative approach...
```

After 5 failed attempts, STOP and ask:
> "I've attempted 5 fixes but the issue persists. Here's what I've tried:
> 1. [First approach]
> 2. [Second approach]
> ...
> Would you like me to continue with a different strategy, or would you prefer to investigate manually?"

## References

- `references/workflow-checklist.md` - Quick checklist version
- `references/screenshot-analysis-guide.md` - How to analyze screenshots
- `references/approval-scenarios.md` - Detailed approval scenarios
