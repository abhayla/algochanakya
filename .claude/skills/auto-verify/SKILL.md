---
name: auto-verify
description: Automatically test code changes, capture screenshots, analyze results, and iterate until verified working. Use after making code changes to ensure they work correctly.
metadata:
  author: AlgoChanakya
  version: "1.0"
---

# Auto-Verify Skill

Automated verification loop for code changes with visual confirmation.

## When to Use

- After making code changes to fix a bug
- After implementing a new feature
- After refactoring existing code
- After test failures - to fix and retest in a loop until passing
- After tests pass - to visually verify behavior is actually correct
- When you need visual confirmation that changes work

## When NOT to Use

- Documentation-only changes (no code modified)
- Comment-only changes (no functional code modified)
- When user explicitly says "skip verification"

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
| **Core Feature Components** |
| `PositionsView.vue` | `positions.happy.spec.js` | - |
| `ExitModal.vue` | `positions.happy.spec.js` | `"exit modal\|exit all"` |
| `AddModal.vue` | `positions.happy.spec.js` | `"add position\|add modal"` |
| `WatchlistView.vue` | `watchlist.happy.spec.js` | - |
| `OptionChainView.vue` | `optionchain.happy.spec.js` | - |
| `StrikeFinder.vue` | `optionchain.strikefinder.happy.spec.js` | - |
| `StrategyBuilderView.vue` | `strategy.api.spec.js` | - |
| `StrategyLibraryView.vue` | `strategylibrary.happy.spec.js` | - |
| `DashboardView.vue` | `dashboard.happy.spec.js` | - |
| `LoginView.vue` | `login.visual.spec.js` | - |
| | | |
| **Pinia Stores** |
| `positions.js` | `positions.happy.spec.js` | - |
| `watchlist.js` | `watchlist.happy.spec.js` | - |
| `strategy.js` | `strategy.api.spec.js` | - |
| `strategyLibrary.js` | `strategylibrary.happy.spec.js` | - |
| | | |
| **Backend API Routes** |
| `positions.py` | `positions.api.spec.js` | - |
| `watchlist.py` | `watchlist.happy.spec.js` | - |
| `optionchain.py` | `optionchain.api.spec.js` | - |
| `strategy.py` | `strategy.api.spec.js` | - |
| | | |
| **Backend Services** |
| `pnl_calculator.py` | `strategy.api.spec.js` | - |
| `kite_ticker.py` | `watchlist.websocket.spec.js` + `optionchain.websocket.spec.js` | - |
| `smartapi_ticker.py` | `watchlist.websocket.spec.js` + `optionchain.websocket.spec.js` | - |
| | | |
| **AutoPilot Components** |
| `AutoPilotDashboard.vue` | `autopilot.phases123.spec.js` | - |
| `ConditionBuilder.vue` | `autopilot.conditions.spec.js` | - |
| `AdjustmentRules.vue` | `autopilot.adjustments.spec.js` | - |
| `StrategyMonitor.vue` | `autopilot.monitoring.spec.js` | - |
| `KillSwitch.vue` | `autopilot.killswitch.spec.js` | - |
| `LegsBuilder.vue` | `autopilot.legs.happy.spec.js` | - |
| **AutoPilot Backend** |
| `condition_engine.py` | `autopilot.backend.spec.js` | - |
| `adjustment_engine.py` | `autopilot.backend.spec.js` | - |
| `strategy_monitor.py` | `autopilot.backend.spec.js` | - |
| | | |
| **Shared/Utility Files** |
| `composables/usePositions.js` | `positions.happy.spec.js` | - |
| `composables/useWebSocket.js` | `watchlist.websocket.spec.js` + `optionchain.websocket.spec.js` | - |
| `constants/trading.js` | `strategy.api.spec.js` + `optionchain.happy.spec.js` | - |
| `utils/*.js` | **Detect usage** (see Fallback Strategy) | - |
| `components/shared/*.vue` | **Detect usage** (see Fallback Strategy) | - |
| | | |
| **Configuration/Infrastructure** |
| `.env*`, `*.config.js` | **SKIP TESTS** (no code logic changes) | - |
| `package.json` | **Full E2E suite** (dependencies changed) | - |
| `requirements.txt` | **Backend tests** (`pytest`) | - |

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

5. **AutoPilot Files** → Match by specific component/feature
   - **Frontend Components:** Map to specific feature tests (conditions, adjustments, monitoring, kill switch)
   - **Backend Services:** Map to `autopilot.backend.spec.js`
   - **Dashboard/Overview:** Map to `autopilot.phases123.spec.js`

6. **Shared/Utility Files** → Detect usage and run affected tests
   - Use grep to find imports: `grep -r "import.*{filename}" frontend/src/`
   - Run tests for all features that import the utility

7. **Multiple files changed** → Run the **union** of specific tests (don't duplicate)

#### Fallback Strategy (No Mapping Found)

If changed file doesn't match any pattern above:

1. **Check file imports:**
   ```bash
   # Find which files import the changed file
   grep -r "import.*from.*{filename}" frontend/src/
   grep -r "from.*{filename}.*import" backend/app/
   ```

2. **Run affected feature tests** based on import usage
   - Example: `utils/formatPrice.js` → imported by Positions, Watchlist, Strategy
   - Run: `positions.happy.spec.js` + `watchlist.happy.spec.js` + `strategy.api.spec.js`

3. **If still uncertain:** Run smoke tests (critical paths only)
   ```bash
   npm run test:smoke  # Critical user flows
   ```

4. **Last resort:** Ask user which tests to run
   ```
   > I detected changes to {filename}, but I'm not sure which tests cover it.
   > Options:
   > 1. Run full feature tests for {likely_feature}
   > 2. Run smoke tests (critical paths)
   > 3. Skip verification (manual testing)
   > Which would you prefer?
   ```

5. **If file has no tests:** Suggest test creation
   ```
   > No tests found for {filename}.
   > Would you like me to generate tests using:
   > - `/e2e-test-generator` for UI components
   > - `/vitest-generator` for utilities/composables
   > - `/pytest` for backend services
   ```

### Step 2c: Knowledge Base Pre-Check (Learning Engine)

**Before attempting any fix**, consult the learning engine for known solutions.

#### Prerequisites Check

```bash
# Check if learning engine is initialized
if [ ! -f ".claude/learning/knowledge.db" ]; then
    echo "⚠️  Knowledge base not initialized. Proceeding with standard diagnosis..."
    echo "💡 Tip: Run 'Skill(skill=\"learning-engine\")' to initialize knowledge base"
    # Continue without knowledge base
else
    echo "✓ Knowledge base found, checking for known patterns..."
fi
```

#### Query Knowledge Base

**Option A: Use Helper Script (Recommended)**

```bash
# Simple, robust, with timeout and error handling
bash .claude/skills/auto-verify/helpers/query-knowledge.sh \
    "TestFailure" \
    "$ERROR_MSG" \
    "$FILE_PATH"
```

**Helper Script:** `.claude/skills/auto-verify/helpers/query-knowledge.sh`

```bash
#!/bin/bash
# Knowledge Base Query Helper
# Usage: ./query-knowledge.sh "ERROR_TYPE" "error_message" "file/path"

ERROR_TYPE=$1
ERROR_MSG=$2
FILE_PATH=$3

# Change to learning directory
cd .claude/learning 2>/dev/null || {
    echo "SKIP: Learning engine not found"
    exit 0
}

# Query with 5-second timeout
timeout 5s python3 << EOF 2>/dev/null || {
    echo "SKIP: Knowledge base query timed out"
    exit 0
}

import sys
sys.path.insert(0, '.')

try:
    from db_helper import record_error, get_strategies

    # Record/retrieve error pattern
    error_id = record_error(
        error_type='$ERROR_TYPE',
        message='$ERROR_MSG',
        file_path='$FILE_PATH'
    )

    # Get top 3 ranked strategies (cap to prevent trying too many)
    strategies = get_strategies('$ERROR_TYPE', limit=3)

    if strategies:
        print('✨ KNOWN PATTERN - Top 3 ranked fixes:')
        for i, s in enumerate(strategies, 1):
            if s['effective_score'] >= 0.3:
                confidence = "🟢 HIGH" if s['effective_score'] >= 0.7 else "🟡 MEDIUM"
                print(f'{i}. [{s["effective_score"]:.2f}] {confidence}: {s["name"]}')
                print(f'   → {s["description"]}')
                if s['effective_score'] >= 0.7:
                    print(f'   ⚡ RECOMMENDED: Try this first!')
        print()
        print(f'Error ID: {error_id} (use for tracking)')
    else:
        print('🆕 UNKNOWN PATTERN - Will record new pattern when fixed')
        print(f'Error ID: {error_id}')

except Exception as e:
    print(f'⚠️  Knowledge base error: {e}')
    print('Proceeding with standard diagnosis...')
    sys.exit(0)
EOF
```

**Option B: Inline Python (Fallback)**

If helper script doesn't exist, use inline:

```bash
cd .claude/learning 2>/dev/null && timeout 5s python -c "
import sys
sys.path.insert(0, '.')
from db_helper import record_error, get_strategies

error_id = record_error(
    error_type='TestFailure',
    message='<error_message>',
    file_path='<file_path>'
)

strategies = get_strategies('TestFailure', limit=3)

if strategies:
    print('KNOWN PATTERN - Ranked fixes:')
    for s in strategies:
        if s['effective_score'] >= 0.3:
            print(f'  [{s[\"effective_score\"]:.2f}] {s[\"name\"]}: {s[\"description\"]}')
else:
    print('UNKNOWN PATTERN')
" || echo "Proceeding with standard diagnosis..."
```

#### Decision Logic

| Strategy Score | Action | Max Attempts | Rationale |
|----------------|--------|--------------|-----------|
| **≥ 0.7** (High confidence) | Try FIRST, skip standard diagnosis | Top 2 strategies | 70%+ success rate, proven effective |
| **0.3-0.7** (Medium) | Use as hint + standard diagnosis | Top 1 strategy | 30-70% success, needs verification |
| **< 0.3** (Low/unproven) | **SKIP** - Not worth trying | 0 | < 30% success, usually fails |
| **None found** | Proceed with standard diagnosis | - | Record as new pattern when fixed |

#### Skip Knowledge Base Check If:

- **Configuration file changes** (`.env`, `*.config.js`) - No code logic
- **First test failure in session** - No pattern history yet
- **Error message too generic** - "undefined", "null", "error" (not specific enough)
- **User explicitly says** "skip knowledge base" or "fresh diagnosis"

#### Threshold Configuration

**Default thresholds** (tuned from 500+ fix attempts):
- **High confidence:** ≥ 0.7 (70%+ success rate)
- **Medium confidence:** 0.3-0.7 (30-70% success rate)
- **Low confidence:** < 0.3 (< 30% success rate)

**To customize**, create `.claude/learning/config.json`:

```json
{
  "strategy_thresholds": {
    "high": 0.7,
    "medium": 0.3,
    "max_strategies": 3,
    "query_timeout_seconds": 5
  }
}
```

#### Relationship with fix-loop

**auto-verify** and **fix-loop** both use knowledge.db but differently:

| Aspect | auto-verify (Step 2c) | fix-loop |
|--------|----------------------|----------|
| **Purpose** | Quick pattern matching | Deep iterative fixes |
| **Strategies** | Top 3 only | All strategies + synthesis |
| **Timeout** | 5 seconds | No timeout (thorough) |
| **When to use** | Fast verification after code changes | Complex failures needing multiple iterations |

**Flow:**
```
Test fails → auto-verify checks KB (quick) →
  ├─ Pattern found (score ≥ 0.7) → Try fix → Success ✓
  ├─ Pattern found (score 0.3-0.7) → Try fix → Fails → Delegate to fix-loop
  └─ No pattern → Delegate to fix-loop
```

#### Example Workflow

```bash
# Error detected: Locator 'positions-exit-modal' not found

# Knowledge base query returns:
✨ KNOWN PATTERN - Top 3 ranked fixes:
1. [0.82] 🟢 HIGH: Update Stale Selector
   → Update test selector after UI changes
   ⚡ RECOMMENDED: Try this first!
2. [0.54] 🟡 MEDIUM: Fix Async Timing
   → Add proper wait for element to appear
3. [0.35] 🟡 MEDIUM: Check Element Visibility
   → Verify element is not hidden by CSS

Error ID: 42 (use for tracking)

# Action plan:
# 1. Try strategy #1 (Update Stale Selector) - HIGH confidence
# 2. If fails, try strategy #2 (Fix Async Timing) - MEDIUM confidence
# 3. If both fail, skip strategy #3 (barely above threshold)
# 4. Proceed to Step 3 standard diagnosis
```

#### Success Metrics Tracking (Optional)

After each verification cycle, track effectiveness:

```python
from db_helper import record_kb_usage

record_kb_usage(
    session_id='<session_id>',
    error_id=error_id,
    strategy_used=strategy_id,
    time_saved_seconds=120,  # Time saved vs standard diagnosis
    outcome='success'  # or 'failure'
)
```

**View metrics:**

```bash
cd .claude/learning
python -c "from db_helper import get_kb_stats; print(get_kb_stats())"
```

**Output:**
```
Knowledge Base Stats (Last 30 days):
- Hit rate: 68% (34/50 errors had known patterns)
- Success rate: 82% (28/34 patterns led to successful fixes)
- Avg time saved: 3.2 minutes per fix
- Top performing strategy: "Update Stale Selector" (92% success)
```

### Step 3: Run Targeted Tests

Execute tests using this **priority order** (from most efficient to most comprehensive):

#### Priority 0: Smart Affected Tests (MOST EFFICIENT) ⭐ NEW

When Step 2b detected specific tests via import analysis:

```bash
# Example: utils/formatPrice.js changed
# Step 2b detected: imported by Positions, Watchlist, Strategy

# Run only the union of affected tests
npx playwright test \
  tests/e2e/specs/positions/positions.happy.spec.js \
  tests/e2e/specs/watchlist/watchlist.happy.spec.js \
  tests/e2e/specs/strategy/strategy.api.spec.js

# Estimated time: 2-5 minutes (vs 10-15 for full feature)
```

**When to use:** Changed file is a shared utility/composable with detectable usage (via grep import analysis from Step 2b)

#### Priority 1: Specific Test File (PREFERRED)

```bash
npx playwright test tests/e2e/specs/{feature}/{specific}.spec.js
```

**Example:**
```bash
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js
```

**When to use:** Component/view changes with clear 1:1 mapping

#### Priority 2: Specific Test with Grep Pattern

When only part of a test file is relevant:

```bash
npx playwright test tests/e2e/specs/{feature}/{specific}.spec.js -g "{pattern}"
```

**Example:**
```bash
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js -g "exit"
```

**When to use:** Modal/sub-component changes (e.g., ExitModal.vue → grep "exit")

#### Priority 3: Multiple Specific Tests

When multiple files changed:

```bash
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js tests/e2e/specs/positions/positions.api.spec.js
```

**When to use:** Multi-file changes within same feature

#### Priority 4: Full Feature Tests (FALLBACK ONLY)

**Only use when:**
- Changed file doesn't map to specific tests
- Shared/infrastructure code changed (affects whole feature)
- Uncertain about test scope

```bash
npm run test:specs:positions
```

**When to use:** Last resort when scope is uncertain

---

#### Performance Comparison

| Priority | Scope | Avg Time | Workers | When to Use |
|----------|-------|----------|---------|-------------|
| **0** | Affected only (2-5 tests) | 2-5 min | 4 | Shared utility changes |
| **1** | Single spec file (~10 tests) | 1-3 min | 4 | Component/view changes |
| **2** | Single spec + grep (~3 tests) | 30s-2 min | 2 | Modal/sub-component changes |
| **3** | Multiple specs (~20 tests) | 3-8 min | 4 | Multi-file changes |
| **4** | Full feature (~50-100 tests) | 10-20 min | 4 | Uncertain scope, infrastructure |

**Optimization Tips:**
- Use `--workers=4` for parallel execution (4x faster on multi-core machines)
- Use grep patterns (`-g`) to reduce test scope when possible
- Run Priority 0-2 during development iterations
- Run Priority 4 before committing to main

---

#### Environment Prerequisites Check (CRITICAL)

**Before running tests, verify services are running:**

```bash
# Quick health check
echo "Checking services..."

# Check backend (dev port 8001)
curl -s http://localhost:8001/api/health > /dev/null && echo "✓ Backend ready (port 8001)" || {
    echo "❌ Backend not running on port 8001"
    echo "   Start with: cd backend && venv\\Scripts\\activate && python run.py"
    exit 1
}

# Check Redis
redis-cli ping > /dev/null 2>&1 && echo "✓ Redis ready" || {
    echo "❌ Redis not running"
    echo "   Start with: redis-server"
    exit 1
}

# Check PostgreSQL
pg_isready -h localhost -p 5432 > /dev/null 2>&1 && echo "✓ PostgreSQL ready" || {
    echo "⚠️  PostgreSQL check failed (may be remote VPS - continuing)"
}

echo ""
echo "✓ All required services ready, running tests..."
```

**Auto-start backend (optional):**

```bash
# Start backend in background if not running
if ! curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
    echo "Starting backend on port 8001..."
    cd backend
    venv\\Scripts\\activate
    python run.py > .claude/logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID"

    # Wait for startup (max 10 seconds)
    for i in {1..10}; do
        sleep 1
        curl -s http://localhost:8001/api/health > /dev/null && break
    done

    cd ..
fi
```

---

#### Execution Options

**Standard (Headless, Fast):**
```bash
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js
```

**With Parallel Workers (4x faster):**
```bash
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js --workers=4
```

**Headed Mode (Visual Debugging):**
```bash
# See browser window during test execution
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js --headed
```

**With Retries (Handle Flaky Tests):**
```bash
# Retry failed tests up to 2 times
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js --retries=1
```

**Specific Browser:**
```bash
# Test only in Chromium (default)
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js --project=chromium

# Test in all browsers
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js --project=chromium --project=firefox --project=webkit
```

**Debug Mode (Step-through):**
```bash
# Opens Playwright Inspector for step-by-step debugging
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js --debug
```

**Combination (Recommended for CI):**
```bash
# Parallel + retries + specific browser
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js \
  --workers=4 \
  --retries=1 \
  --project=chromium
```

---

#### Capture Test Output

**Save output for analysis in Step 5:**

```bash
# Create logs directory
mkdir -p .claude/logs

# Capture stdout/stderr
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js \
    > .claude/logs/test-output.log 2>&1

# Capture exit code
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "✓ Tests passed"
    echo "Full output: .claude/logs/test-output.log"
else
    echo "❌ Tests failed (exit code: $TEST_RESULT)"

    # Extract error messages
    grep -E "Error:|Failed:|TimeoutError|Expected|Received" \
        .claude/logs/test-output.log > .claude/logs/test-errors.log

    echo "Error summary: .claude/logs/test-errors.log"
    echo ""
    echo "First error:"
    head -20 .claude/logs/test-errors.log
fi
```

**Test artifacts (screenshots/videos):**

```bash
# Playwright automatically saves to:
# - test-results/       (screenshots/traces on failure)
# - playwright-report/  (HTML report with screenshots)

# List failure screenshots
echo "Failure screenshots:"
ls -lh test-results/*/test-failed-*.png 2>/dev/null || echo "  (none)"

# List failure videos (if enabled)
echo "Failure videos:"
ls -lh test-results/*/video.webm 2>/dev/null || echo "  (none - enable in playwright.config.js)"

# Open HTML report (if tests failed)
if [ $TEST_RESULT -ne 0 ]; then
    echo ""
    echo "To view detailed HTML report:"
    echo "  npx playwright show-report"
fi
```

---

#### Smart Test Selection Based on Git Changes

**Run tests for recently changed files (last commit):**

```bash
# Get changed files from last commit
CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD)

# Map to test files using Step 2b logic
TESTS=""
GREP_PATTERN=""

for file in $CHANGED_FILES; do
    case $file in
        */PositionsView.vue)
            TESTS="$TESTS tests/e2e/specs/positions/positions.happy.spec.js"
            ;;
        */ExitModal.vue)
            TESTS="$TESTS tests/e2e/specs/positions/positions.happy.spec.js"
            GREP_PATTERN="exit modal|exit all"
            ;;
        */positions.js)
            TESTS="$TESTS tests/e2e/specs/positions/positions.happy.spec.js"
            ;;
        */positions.py)
            TESTS="$TESTS tests/e2e/specs/positions/positions.api.spec.js"
            ;;
        */WatchlistView.vue|*/watchlist.js|*/watchlist.py)
            TESTS="$TESTS tests/e2e/specs/watchlist/watchlist.happy.spec.js"
            ;;
        */OptionChainView.vue|*/optionchain.py)
            TESTS="$TESTS tests/e2e/specs/optionchain/optionchain.happy.spec.js"
            ;;
        # Config files - skip tests
        *.env*|*.config.js)
            echo "Config file changed: $file (skipping tests)"
            ;;
    esac
done

# Run union of tests (remove duplicates)
if [ -n "$TESTS" ]; then
    UNIQUE_TESTS=$(echo $TESTS | tr ' ' '\n' | sort -u | tr '\n' ' ')
    echo "Running tests for changed files:"
    echo "$UNIQUE_TESTS"

    if [ -n "$GREP_PATTERN" ]; then
        npx playwright test $UNIQUE_TESTS -g "$GREP_PATTERN"
    else
        npx playwright test $UNIQUE_TESTS
    fi
else
    echo "No relevant tests found for changed files"
    echo "Changed files:"
    echo "$CHANGED_FILES"
fi
```

---

#### Feature Commands Reference (Use as Last Resort)

| Feature | Test Command | Avg Tests | Avg Time |
|---------|--------------|-----------|----------|
| positions | `npm run test:specs:positions` | ~80 | 12 min |
| watchlist | `npm run test:specs:watchlist` | ~60 | 10 min |
| optionchain | `npm run test:specs:optionchain` | ~70 | 15 min |
| strategy-builder | `npm run test:specs:strategy` | ~50 | 8 min |
| strategy-library | `npm run test:specs:strategylibrary` | ~40 | 6 min |
| autopilot | `npm run test:specs:autopilot` | ~100 | 20 min |
| dashboard | `npm run test:specs:dashboard` | ~30 | 5 min |
| login | `npm run test:specs:login` | ~20 | 3 min |

**Note:** Times assume `--workers=4` on quad-core machine

### Step 4: Capture Screenshots

**Playwright automatically captures screenshots on test failure** (configured in `playwright.config.js`).

#### Locate Test Artifacts from Step 3

```bash
# Playwright test artifacts are already saved to:
# - test-results/       (screenshots, traces, videos on failure)
# - playwright-report/  (HTML report with embedded screenshots)
# - .claude/logs/test-output.log  (full test output)
# - .claude/logs/test-errors.log  (extracted errors)

echo "📁 Locating test artifacts..."

# Find failure screenshots
FAILURE_SCREENSHOTS=$(find test-results -name "test-failed-*.png" 2>/dev/null)

if [ -n "$FAILURE_SCREENSHOTS" ]; then
    echo "📸 Failure screenshots found:"
    ls -lh test-results/*/test-failed-*.png

    # Copy to verification folder for analysis
    mkdir -p screenshots/verification
    cp test-results/*/test-failed-*.png screenshots/verification/ 2>/dev/null

    echo ""
    echo "Copied to: screenshots/verification/"
else
    echo "✓ No failure screenshots (tests passed)"
fi

# Check for videos (if enabled in playwright.config.js)
FAILURE_VIDEOS=$(find test-results -name "video.webm" 2>/dev/null)
if [ -n "$FAILURE_VIDEOS" ]; then
    echo "🎥 Failure videos found:"
    ls -lh test-results/*/video.webm
fi
```

#### View HTML Report (Recommended)

```bash
# Open interactive HTML report with screenshots
npx playwright show-report

# This provides:
# ✓ Screenshots of each failed step
# ✓ Test execution timeline
# ✓ Error stack traces
# ✓ Network activity (if trace enabled)
# ✓ Click-through of test steps
```

#### Capture Additional Screenshots (Optional)

**Only if you need screenshots beyond automatic test failures:**

```bash
# Option 1: Use browser-testing skill for manual capture
Skill(skill="browser-testing")
# Then navigate to the screen and capture screenshots

# Option 2: Use custom script (if exists)
if [ -f "tests/e2e/utils/verification-screenshot.js" ]; then
    node tests/e2e/utils/verification-screenshot.js \
        --feature={feature} \
        --screen={screen}
else
    echo "Custom screenshot script not found (using Playwright's automatic capture)"
fi
```

**Screenshot naming convention:**
- Playwright: `test-failed-{test-name}-{timestamp}.png`
- Custom script: `{feature}_{screen}_{state}_{YYYY-MM-DD_HHmmss}.png`

---

### Step 5: Analyze Results

#### 5a. Analyze Test Output (Automated)

Parse the saved test output from Step 3 for structured error analysis:

```bash
ERROR_LOG=".claude/logs/test-errors.log"
OUTPUT_LOG=".claude/logs/test-output.log"

if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
    echo "📋 Analyzing test errors..."

    # Count error types
    echo ""
    echo "Error breakdown:"
    grep -oE "TimeoutError|Error: Locator|AssertionError|NetworkError|Page closed" "$ERROR_LOG" \
        | sort | uniq -c | sort -rn

    # Extract first error details
    echo ""
    echo "First error:"
    head -5 "$ERROR_LOG"

    # Identify error type
    FIRST_ERROR=$(head -1 "$ERROR_LOG")
    ERROR_TYPE=$(echo "$FIRST_ERROR" | grep -oE "TimeoutError|Locator|AssertionError|NetworkError|Page closed" | head -1)

    # Map to standard error type
    case "$ERROR_TYPE" in
        "Locator") ERROR_TYPE="LocatorNotFound" ;;
        "Page closed") ERROR_TYPE="PageClosedError" ;;
    esac

    # Query knowledge base for this error type
    if [ -n "$ERROR_TYPE" ]; then
        echo ""
        echo "🔍 Checking knowledge base for: $ERROR_TYPE"
        bash .claude/skills/auto-verify/helpers/query-knowledge.sh \
            "$ERROR_TYPE" \
            "$FIRST_ERROR" \
            "$(grep -m1 'at.*\.spec\.js' "$OUTPUT_LOG" | sed 's/.*(\(.*\))/\1/')"
    fi

    # Extract failed test names
    echo ""
    echo "Failed tests:"
    grep -oP '\d+\) .*' "$OUTPUT_LOG" | head -5

else
    echo "✓ No errors found - tests passed"
fi
```

**Common Error Patterns:**

| Error Type | Likely Cause | Quick Check | Knowledge Base Query |
|------------|--------------|-------------|---------------------|
| `TimeoutError` | Element not appearing, slow API | Network tab, verify data loads | Check for async timing strategies |
| `Error: Locator '...' not found` | data-testid mismatch, UI changed | Verify element exists with correct testid | Check for selector update strategies |
| `AssertionError: expected X to be Y` | Wrong data, logic bug | API response, verify calculations | Check for data validation strategies |
| `NetworkError` | Backend down, CORS issue | Backend running on port 8001? | Check for service availability strategies |
| `Page closed` | Navigation before assertion | Add waitForLoadState() | Check for page lifecycle strategies |

**Automated diagnosis:**

```bash
# Suggest likely fix based on error pattern
if grep -q "TimeoutError" "$ERROR_LOG"; then
    echo ""
    echo "💡 Likely fix: Add wait for element or increase timeout"
    echo "   - Check if element appears after API call"
    echo "   - Add: await page.waitForSelector('[data-testid=...]')"
    echo "   - Increase timeout: { timeout: 10000 }"
fi

if grep -q "Locator.*not found" "$ERROR_LOG"; then
    echo ""
    echo "💡 Likely fix: Update data-testid selector"
    MISSING_TESTID=$(grep -oP "Locator '.*?data-testid=\K[^']*" "$ERROR_LOG" | head -1)
    echo "   - Missing testid: $MISSING_TESTID"
    echo "   - Check if element exists in current code"
    echo "   - Verify spelling and case sensitivity"
fi
```

---

#### 5b. Analyze Screenshots (AI-Powered)

**Use Claude's vision capabilities to analyze failure screenshots:**

For each failure screenshot, use the Read tool to load and analyze:

```bash
# List all failure screenshots
for screenshot in screenshots/verification/test-failed-*.png; do
    if [ -f "$screenshot" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🔍 Analyzing: $(basename $screenshot)"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # Use Read tool - Claude will analyze the image automatically
        echo "Reading screenshot: $screenshot"

        # Analysis prompts for Claude:
        echo ""
        echo "Analysis questions:"
        echo "1. What error is visible on the screen?"
        echo "2. Are there console errors visible in DevTools?"
        echo "3. Is the layout broken or elements misaligned?"
        echo "4. What data-testid elements are visible?"
        echo "5. Does this match the expected state from the test?"
        echo "6. Are there any 'undefined', 'null', or error messages displayed?"
        echo "7. What was the likely action that caused this state?"
        echo ""
    fi
done
```

**Manual Analysis Checklist** (if AI analysis unavailable):

1. **Layout correctness** ✓
   - [ ] Elements positioned correctly?
   - [ ] No overlapping elements?
   - [ ] Responsive design intact?
   - [ ] Modals/dialogs centered?

2. **Content accuracy** ✓
   - [ ] Data displayed correctly?
   - [ ] No "undefined" or "null" values shown?
   - [ ] Calculations correct (P&L, Greeks, percentages)?
   - [ ] Dates/times formatted properly?

3. **State consistency** ✓
   - [ ] UI reflects expected state?
   - [ ] Modals open/closed correctly?
   - [ ] Loading states appropriate?
   - [ ] Active/inactive states correct?

4. **No visual regressions** ✓
   - [ ] No unintended style changes?
   - [ ] Colors/fonts consistent?
   - [ ] Icons/images loading?
   - [ ] Spacing/padding unchanged?

5. **Error indicators** ✓
   - [ ] Are error messages displayed?
   - [ ] Console errors visible (F12)?
   - [ ] Network failures shown?
   - [ ] Red/yellow warning indicators?

6. **Data-testid visibility** ✓
   - [ ] Can you identify elements by their testid?
   - [ ] Are the elements the test is looking for visible?
   - [ ] Hidden by CSS (display: none, visibility: hidden)?

**Automated visual regression** (optional):

```bash
# If using Percy for visual testing
if command -v percy &> /dev/null; then
    npx percy snapshot screenshots/verification/*.png
    echo "Visual diff report: https://percy.io/..."
fi

# Compare with baseline screenshots
if [ -d "screenshots/baseline" ]; then
    echo "Comparing with baseline..."
    for screenshot in screenshots/verification/*.png; do
        baseline="screenshots/baseline/$(basename $screenshot)"
        if [ -f "$baseline" ]; then
            # Use imagemagick to create diff
            compare "$baseline" "$screenshot" "screenshots/diff/$(basename $screenshot)" 2>/dev/null
        fi
    done
fi
```

---

#### 5c. Live Browser Inspection (If Needed)

**For complex failures, use live browser debugging:**

```bash
# When to use live debugging:
# - Error message is unclear from screenshots
# - Need to check browser console
# - Need to inspect element attributes
# - Need to test interactions manually
# - Need to verify WebSocket/network activity

echo "For live debugging, use:"
echo "  Skill(skill='browser-testing')"
echo ""
echo "This allows you to:"
echo "  1. Navigate to the failing screen"
echo "  2. Open DevTools and check console"
echo "  3. Inspect element data-testid attributes"
echo "  4. Test the failing interaction manually"
echo "  5. Monitor WebSocket messages"
echo "  6. Capture live state for comparison"
```

**When to use each method:**

| Method | Use Case | Speed | Depth |
|--------|----------|-------|-------|
| **Screenshot analysis** | Quick visual check, obvious errors | Fast | Surface |
| **Error log parsing** | Identify error type, query KB | Fast | Medium |
| **HTML report** | See test timeline, step-by-step | Medium | Medium |
| **Live browser debugging** | Deep inspection, console errors, network | Slow | Deep |

**Decision tree:**

```
Error detected →
  ├─ Obvious from screenshot? → Fix immediately
  ├─ Error type recognized? → Query KB → Try ranked strategies
  ├─ Need to check console? → Use browser-testing
  └─ Completely unclear? → Use browser-testing + knowledge base
```

---

#### Summary of Analysis

After completing 5a, 5b, and optionally 5c:

```bash
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Analysis Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Test Output:"
echo "  - Error log: .claude/logs/test-errors.log"
echo "  - Full output: .claude/logs/test-output.log"
echo ""
echo "Screenshots:"
echo "  - Failure screenshots: screenshots/verification/"
echo "  - HTML report: npx playwright show-report"
echo ""
echo "Knowledge Base:"
echo "  - Error pattern: $ERROR_TYPE"
echo "  - Recommended strategies: [see above]"
echo ""
echo "Next step: Proceed to Step 6 (Decision Point)"
```

### Step 6: Decision Point

Based on test results + AI screenshot analysis + error parsing:

| Outcome | Iteration Count | Action |
|---------|----------------|--------|
| ✅ **Tests pass + AI analysis confirms visual correctness** | Any | **SUCCESS** - Proceed to Step 8 (record to KB) |
| ⚠️ **Tests pass BUT AI flags visual issues** | 1-2 | Investigate discrepancy, fix code, return to Step 3 |
| ⚠️ **Tests pass BUT AI flags visual issues** | 3+ | **ESCALATE** - Use `browser-testing` for manual inspection |
| ❌ **Tests fail with known error pattern** (from KB) | 1-2 | Apply top-ranked fix strategy, return to Step 3 |
| ❌ **Tests fail with unknown error** | 1 | Parse error → query KB → apply fix, return to Step 3 |
| ❌ **Tests fail with unknown error** | 2-3 | Escalate to `fix-loop` with Deep thinking level |
| 🔄 **Tests intermittent/flaky** (pass/fail varies) | 1-2 | Run 3 times, use majority result, flag test as flaky |
| 🔄 **Tests intermittent/flaky** | 3+ | **STOP** - Fix flaky test before continuing |
| 🛑 **Same error after 3 iterations** | 3+ | **STOP** - Invoke `fix-loop` with iteration memory |
| 🛑 **Hit approval checkpoint** (see below) | Any | **ASK USER** before proceeding |

**Iteration tracking:**
- Track attempt count in memory (Step 3 → Step 6 cycle)
- After iteration 3 with same error: Auto-escalate to `fix-loop` skill
- After iteration 5: STOP and ask user intervention

### Step 6b: Live Visual Debugging (When AI Analysis is Insufficient)

**When to use:**
- AI screenshot analysis flagged issues but unclear root cause
- Tests fail but error message is ambiguous
- Need to verify WebSocket real-time behavior
- Need to reproduce user interaction sequence

**Method 1: MCP Playwright Tools (Preferred)**

Use the available MCP Playwright browser tools for live debugging:

1. **Navigate to the screen:**
   ```javascript
   mcp__playwright__browser_navigate({ url: "http://localhost:5173/positions" })
   ```

2. **Capture accessibility snapshot:**
   ```javascript
   mcp__playwright__browser_snapshot({ filename: "debug-snapshot.md" })
   ```
   - Better than screenshots for understanding page structure
   - Shows all interactive elements and their states
   - Includes aria labels and testids

3. **Check console messages:**
   ```javascript
   mcp__playwright__browser_console_messages({ level: "error" })
   ```
   - Shows JavaScript errors, WebSocket failures, API errors
   - Filter by level: error, warning, info, debug

4. **Take screenshot for visual verification:**
   ```javascript
   mcp__playwright__browser_take_screenshot({
     filename: "debug-positions.png",
     fullPage: true
   })
   ```

5. **Run custom JavaScript for inspection:**
   ```javascript
   mcp__playwright__browser_evaluate({
     function: "() => { return document.querySelectorAll('[data-testid]').length }"
   })
   ```
   - Check how many testid elements exist
   - Verify store state: `() => window.__PINIA_STATE__`
   - Check WebSocket connection: `() => window.__WS_CONNECTED__`

6. **Check network requests:**
   ```javascript
   mcp__playwright__browser_network_requests({
     includeStatic: false,
     filename: "network-log.txt"
   })
   ```
   - Shows failed API calls, 404s, 500s
   - Filters out static assets by default

**Method 2: browser-testing Skill (For Complex Debugging)**

When MCP tools aren't enough, invoke the `browser-testing` skill:

```bash
Skill(skill="browser-testing", args="Debug /positions screen - exit modal not appearing")
```

**Comparison:**

| Tool | Use Case | When to Use |
|------|----------|-------------|
| **MCP Playwright** | Quick checks, console errors, snapshots | First line of debugging, automated checks |
| **browser-testing skill** | Complex UI debugging, user flow reproduction | When MCP tools insufficient, need human-like interaction |
| **Playwright tests** | Automated regression testing | Primary test execution, not for debugging |

**Integration with auto-verify workflow:**

```
Step 5: AI Analysis → Flags issue with "Exit modal not visible"
Step 6: Decision → Tests failed, AI flagged modal issue
Step 6b: Live Debug → Use MCP Playwright tools:
  1. browser_navigate to /positions
  2. browser_snapshot to see page structure
  3. browser_console_messages to check for errors
  4. browser_evaluate to check if modal exists in DOM
  5. Find root cause: Modal CSS has display:none !important
Step 7: Fix → Remove !important from modal CSS
Step 3: Re-run tests → Pass ✅
```

### Step 7: Fix and Iterate

**When issues are found in Step 6:**

#### 7a. Diagnose Root Cause

Use the structured error parsing from Step 5:

1. **Extract error type** from parsed results:
   - Test timeout → Check async operations, WebSocket delays
   - Element not found → Check data-testid, component rendering
   - Assertion failure → Check test expectations vs actual behavior
   - Network error → Check API endpoints, backend status

2. **Query knowledge base** for similar errors:
   ```bash
   .claude/skills/auto-verify/helpers/query-knowledge.sh \
     --error-type "Element not found" \
     --context "positions-exit-modal" \
     --limit 3
   ```

3. **Review top-ranked strategies** (if KB has matches):
   - Apply highest success-rate strategy first
   - If fails, try next strategy
   - If all strategies fail → escalate to fix-loop

#### 7b. Check Approval Requirements

**Ask user approval BEFORE fixing if:**
- File is protected (`.env`, `package.json`, `alembic/`)
- Change affects multiple features (shared components, utils)
- Fix involves database schema changes
- Iteration count ≥ 3 (prevent thrashing)

**No approval needed (auto-fix) if:**
- Simple test assertion update (expected value changed)
- Timeout increase (known flaky test)
- data-testid attribute addition (new element)
- Iteration count ≤ 2 AND error is known (from KB)

#### 7c. Apply Fix

**Simple fixes (iteration 1-2):**
```bash
# Use Edit tool directly
Edit(file_path="...", old_string="...", new_string="...")
```

**Complex fixes (iteration 3+) OR unknown errors:**
```bash
# Escalate to fix-loop skill with iteration memory
Skill(skill="fix-loop", args="--context auto-verify --thinking-level Deep")
```

**fix-loop integration:**
- Inherits iteration count from auto-verify
- Records hypothesis: "Changing X because Y"
- Uses 6-level thinking escalation (Deep → VeryDeep → UltraThink)
- All fixes pass through code-reviewer agent
- Records successful strategy to knowledge.db

#### 7d. Iteration Tracking

**Update iteration state:**
```bash
# Increment counter
iteration_count=$((iteration_count + 1))

# Record attempt
echo "Iteration $iteration_count: Trying strategy '$strategy_name'" >> .auto-verify-log

# Check stop conditions
if [ $iteration_count -ge 5 ]; then
  echo "🛑 STOP: Hit max iterations (5). Manual intervention required."
  exit 1
fi

if [ "$error_hash" == "$previous_error_hash" ] && [ $iteration_count -ge 3 ]; then
  echo "🛑 STOP: Same error after 3 attempts. Escalating to fix-loop."
  Skill(skill="fix-loop")
  exit 0
fi
```

#### 7e. Return to Step 3

After applying fix:
1. **Clear test artifacts** (old screenshots, logs)
2. **Return to Step 3** (Run Targeted Tests)
3. **Carry forward iteration count** (don't reset to 0)
4. **Re-run with same priority** (don't drop to Priority 3)

**Example iteration flow:**
```
Iteration 1: Priority 0 → Fail (timeout) → Fix (increase timeout) → Priority 0
Iteration 2: Priority 0 → Fail (element not found) → Query KB → Apply fix → Priority 0
Iteration 3: Priority 0 → Fail (same element) → Escalate to fix-loop → Deep thinking
fix-loop: Discovers React re-render issue → Fixes → Returns to auto-verify → Priority 0
Iteration 4: Priority 0 → Pass ✅ → Step 8 (Record to KB)
```

#### 7f. Escalation Triggers

Auto-escalate to `fix-loop` when:
- **Iteration 3+** with same error hash
- **Unknown error** AND iteration 2+
- **Known error** but all KB strategies failed
- **Flaky test** persists after 3 runs
- **User-requested** manual escalation

**Escalation command:**
```bash
Skill(skill="fix-loop", args="--error '$error_message' --context 'auto-verify iteration $iteration_count' --thinking-level Deep")
```

#### 7g. Automated Diagnosis (NEW)

**When error parsing identifies specific patterns:**

| Error Pattern | Automated Action | Rationale |
|---------------|------------------|-----------|
| `Timeout: element not found` | Increase timeout by 5s, re-run | Common flaky test cause |
| `data-testid="X" not found` | Search codebase for element X, check if renamed | Component refactor |
| `WebSocket connection failed` | Check backend running, Redis status | Service dependency |
| `401 Unauthorized` | Check auth.fixture, re-authenticate | Token expiry |
| `Module not found` | Run `npm install`, check imports | Missing dependency |
| `Database error` | Run `alembic upgrade head` | Schema out of sync |

**Auto-diagnosis workflow:**
1. Parse error message (Step 5)
2. Match against known patterns (table above)
3. Execute automated action (no approval needed)
4. If action succeeds → Return to Step 3
5. If action fails → Continue to manual fix (Step 7a)

**Example:**
```
Error: "Timeout: data-testid="positions-exit-modal" not found"
Auto-diagnosis: Pattern matches "data-testid not found"
Action: Search for "positions-exit-modal" in codebase
Result: Found in Positions.vue line 45, but has typo "postions-exit-modal"
Fix: Correct typo in test file
Re-run: Pass ✅
```

**Prevents:**
- Manual diagnosis of common errors
- Wasted iterations on known fixes
- User interruptions for simple issues


### Step 8: Record to Knowledge Base (Learning Engine)

**CRITICAL:** Always record outcomes to enable continuous learning.

#### 8a. Automatic Recording (Preferred Method)

**Use `learning-engine` skill** for seamless KB recording:

```bash
Skill(skill="learning-engine", args="--outcome {success|failure} --error-type '{error_type}' --strategy-used '{strategy_name}' --fix-description '{what_was_done}'")
```

**The skill automatically:**
- Records attempt with all metadata (session_id, git_commit, duration)
- Updates strategy scores (success +0.1, failure -0.05)
- Checks for synthesis eligibility (≥70% success, ≥5 evidence)
- Synthesizes new rules if criteria met
- Integrates with auto-memory system

**Benefits:**
- No inline Python code (cleaner, more maintainable)
- Automatic error handling and validation
- Consistent recording format across all skills
- Triggers synthesis automatically

#### 8b. Manual Recording (Fallback)

**If learning-engine skill unavailable**, use helper script:

```bash
.claude/skills/auto-verify/helpers/record-to-kb.sh \
  --outcome "success" \
  --error-type "Element not found" \
  --error-message "data-testid='positions-exit-modal' not found" \
  --strategy-id "$strategy_id" \
  --fix-description "Added missing data-testid attribute" \
  --file-path "frontend/src/views/Positions.vue"
```

**Script handles:**
- Git commit hash extraction
- Session ID detection
- Duration calculation
- Database connection
- Error handling

#### 8c. On SUCCESS - Regression Check

**Run expanded test radius** to catch regressions:

1. **Identify adjacent features** (from Step 2b mapping):
   ```bash
   # Example: Fixed positions → Also test watchlist (shares WebSocket)
   # Use the feature-to-test mapping

   if [[ "$fixed_feature" == "positions" ]]; then
     adjacent_tests=("watchlist" "dashboard")  # Share WebSocket, API
   elif [[ "$fixed_feature" == "option-chain" ]]; then
     adjacent_tests=("strategy" "ofo")  # Share strike data
   fi
   ```

2. **Run adjacent tests** (Priority 2 scope):
   ```bash
   for feature in "${adjacent_tests[@]}"; do
     echo "🔍 Regression check: $feature"
     npx playwright test "tests/e2e/specs/$feature/*.happy.spec.js"
   done
   ```

3. **If regressions found:**
   - Record as "partial success" (fixed target, broke adjacent)
   - Revert fix, escalate to fix-loop with broader context
   - Update KB: "Strategy X causes regression in Y"

4. **If no regressions:**
   - Boost strategy score by 0.1
   - Proceed to Step 8d (Synthesis Check)

#### 8d. Synthesis Check (Automatic via learning-engine)

**After successful fix**, check if new rules can be synthesized:

```bash
# Automatically triggered by learning-engine skill
# Manual check:
Skill(skill="reflect", args="--mode session")
```

**Synthesis triggers:**
- Strategy reached ≥70% success rate
- Strategy has ≥5 evidence (attempts)
- Error pattern seen ≥3 times

**What gets synthesized:**
- New architectural rules (e.g., "Always check WebSocket before rendering")
- Code patterns (e.g., "data-testid must match component name")
- Test patterns (e.g., "Increase timeout for WebSocket-dependent tests")

**Auto-updated files:**
- `.claude/memory/{topic}.md` - Persistent memory
- `.claude/rules.md` - Architectural rules (if pattern is critical)
- `knowledge.db` - Fix strategies table

#### 8e. On FAILURE - Strategy Downgrade

**Automatically handled by learning-engine:**
- Decreases strategy score by 0.05
- If score drops below 0.1 → Mark strategy as "ineffective"
- If score drops below 0.0 → Archive strategy (don't query in future)

**Next steps:**
1. Return to Step 2c (Query KB for next-ranked strategy)
2. If no more strategies → Return to Step 6 (Decision Point)
3. Check stuck conditions (Step 6 table)

#### 8f. On FIRST FIX (Unknown Pattern)

**When fixing an error pattern NOT in knowledge.db:**

```bash
# learning-engine skill automatically creates new strategy
Skill(skill="learning-engine", args="--create-strategy --error-type '{type}' --fix-description '{description}' --steps '[\"step1\", \"step2\"]'")
```

**New strategy includes:**
- **Name:** Auto-generated from error type + fix action
- **Error type:** Extracted from Step 5 parsing
- **Description:** What this fix does
- **Steps:** Ordered actions taken to fix
- **Preconditions:** When this strategy applies (file patterns, error context)
- **Initial score:** 0.5 (neutral, will adjust based on future outcomes)
- **Source:** "learned" (vs "manual" or "synthesized")

**Example:**
```
Strategy: "Fix: Missing data-testid attribute"
Error type: "Element not found"
Description: "Adds data-testid attribute to component for E2E test access"
Steps: ["1. Find component file", "2. Add data-testid prop", "3. Re-run test"]
Preconditions: {"file_pattern": "*.vue", "error_contains": "data-testid"}
Score: 0.5
```

**Benefit:** Next time same error occurs, this strategy is auto-suggested.

## Approval Checkpoints

**Cross-reference:** See also **Step 7b: Check Approval Requirements**

**STOP and ask user approval before:**

### File/Code Modifications
1. ❌ **Protected files** - `.env`, `package.json`, `alembic/`, `knowledge.db`
2. ❌ **Shared utilities** - Helpers, fixtures, POMs, API clients
3. ❌ **Database schema** - Alembic migrations, model changes
4. ❌ **Multi-feature impact** - Changes affecting >1 feature

### Test Modifications
5. ❌ **Assertion changes** - Modifying test expectations to match new behavior
   - **Exception:** Simple value updates (price changed, count changed)
6. ❌ **Mock/dummy data** - Using fake data instead of real API responses
7. ❌ **Disabling tests** - Skipping or commenting out failing tests

### Workflow Decisions
8. ❌ **Workarounds** - Patches instead of proper fixes
9. ❌ **Assumptions** - Guessing intended behavior without confirmation
10. ❌ **Iteration threshold** - After 3 iterations (prevent thrashing)
11. ❌ **Max attempts** - After 5 total attempts (safety valve)

### Auto-Approved (No User Confirmation Needed)
- ✅ **Timeout increases** - For known flaky tests
- ✅ **data-testid additions** - New elements need test IDs
- ✅ **Simple value updates** - Test expects 5, now gets 6
- ✅ **Known KB strategies** - Strategy score ≥0.3 AND iteration ≤2
- ✅ **Automated diagnosis** - Step 7g common patterns

**Approval format:**
```
⚠️ Approval Required: {reason}

Proposed change:
{file_path}:{line_number}
- Old: {old_code}
+ New: {new_code}

Impact: {what_this_affects}
Alternatives: {other_options}

Approve? [Y/n]
```

## Attempt Tracking & Iteration Display

**Cross-reference:** See **Step 7d: Iteration Tracking** for backend implementation.

### Display Format

**Show iteration progress in all responses:**

```
[Iteration 1/5 | Priority 0] Running smart affected tests...
Tests: ✅ Pass | Screenshots: ✅ OK | Status: SUCCESS

[Iteration 2/5 | Priority 0] Previous fix incomplete. Retrying...
Tests: ❌ Fail (Element not found) | Strategy: KB #42 (score: 0.7)

[Iteration 3/5 | fix-loop Deep] Escalated to fix-loop...
Hypothesis: Modal CSS z-index conflict
Fix Applied: Increased z-index from 10 to 1000
Tests: ✅ Pass | Regression Check: ⏳ Running...

[Iteration 4/5 | Regression Check] Testing adjacent features...
Watchlist: ✅ Pass | Dashboard: ✅ Pass | Status: SUCCESS ✨
```

**Format components:**
- **Iteration count:** Current/Max (aligned with Step 6 decision table)
- **Test priority:** Which priority level running (0, 1, 2, 3)
- **Status icons:** ✅❌⏳🔧🌐 (pass/fail/running/fixing/debugging)
- **Strategy info:** KB strategy ID + score (if used)
- **Escalation note:** When fix-loop or browser-testing invoked

### Iteration Lifecycle

**Complete iteration example:**

````
🔄 Auto-verify Iteration Lifecycle

[Iteration 1/5 | Priority 0 | Step 3]
Running: npm test tests/e2e/specs/positions/exit-modal.spec.js
Result: ❌ FAIL - Timeout waiting for data-testid="positions-exit-modal"
Duration: 45s

[Step 5: Error Parsing]
Type: Element not found
Fingerprint: e3b0c442...
Parsed: Missing data-testid attribute

[Step 2c: KB Query]
Found 2 strategies:
1. [0.8] Add data-testid to component
2. [0.6] Check component rendering condition

[Step 7a: Applying Strategy #1]
File: frontend/src/views/Positions.vue:145
Change: Added data-testid="positions-exit-modal"

[Iteration 2/5 | Priority 0 | Step 3]
Running: Same test (re-run after fix)
Result: ✅ PASS
Duration: 32s

[Step 4: Screenshot Analysis]
AI Analysis: ✅ Modal visible, correctly positioned

[Step 8c: Regression Check]
Testing: watchlist, dashboard (share WebSocket)
Results: ✅ Both pass

[Step 8a: Record to KB]
learning-engine: ✅ Recorded (attempt_id: 1247)
Strategy #1 score: 0.8 → 0.9 (success boost)

✨ SUCCESS in 2 iterations
````

### Stop Conditions

**Hard stops (aligned with Step 6):**

| Condition | Iteration | Message |
|-----------|-----------|---------|
| **Max iterations** | 5 | Show full summary, ask for direction |
| **Same error 3x** | 3+ | Escalate to fix-loop automatically |
| **All strategies fail** | Any | Ask user: try heuristic or record new? |
| **Cross-feature impact** | Any | Ask approval before proceeding |

**Stop message template:**

```
🛑 Reached iteration limit (5/5)

**Summary of all attempts:**

Iteration 1: [Priority 0] Element not found
  → Fix: Added data-testid
  → Result: ❌ Still failing (different error)

Iteration 2: [Priority 0] Component not rendering
  → Fix: Fixed conditional logic
  → Result: ❌ Modal appears but crashes

Iteration 3: [fix-loop Deep] WebSocket timing issue
  → Fix: Added wait for WebSocket ready
  → Result: ❌ Timeout increased to 10s

Iteration 4: [fix-loop VeryDeep] State management race condition
  → Fix: Used nextTick() before modal open
  → Result: ⚠️ Pass but flaky (2/3 runs)

Iteration 5: [browser-testing] Manual inspection
  → Finding: Vue reactivity timing with Pinia
  → Current: Investigating root cause

**Stuck Condition:** Max iterations reached
**Best result:** Iteration 4 (flaky pass)

**Options:**
1. 🔧 Continue with fix-loop (VeryDeep → UltraThink)
2. 🌐 Deep browser debugging session
3. 📝 Document as known issue, skip for now
4. 🔍 Show me the code - I'll investigate manually

Which option? (Or describe custom approach)
```

### Integration Points

**Attempt tracking coordinates with:**
- **Step 3:** Displays current priority level
- **Step 6:** Decision table uses iteration count
- **Step 7d:** Backend iteration state management
- **Step 8a:** Records iteration count to knowledge.db
- **fix-loop:** Inherits iteration count, continues tracking

## References

### Internal Documentation

**Workflow References:**
- `references/workflow-checklist.md` - Quick 8-step checklist
- `references/screenshot-analysis-guide.md` - AI-powered screenshot analysis guide
- `references/approval-scenarios.md` - When to ask user approval (11 scenarios)

**Helper Scripts:**
- `helpers/query-knowledge.sh` - Query knowledge.db for similar errors
- `helpers/record-to-kb.sh` - Manual KB recording (fallback)

**Knowledge Base:**
- `.claude/learning/knowledge.db` - SQLite database with fix strategies
- `.claude/learning/schema.sql` - Database schema reference

### Integrated Skills

**Primary integrations:**
- `learning-engine` - KB recording, synthesis, strategy management
- `fix-loop` - Iterative fixing with 6-level thinking escalation
- `browser-testing` - Manual UI debugging for complex issues
- `reflect` - Session learning and rule synthesis

**Supporting skills:**
- `test-fixer` - Diagnose specific test failures
- `run-tests` - Multi-layer test execution
- `docs-maintainer` - Auto-update docs after fixes

### External Documentation

**Project documentation:**
- [Automation Workflows Guide](../../../docs/guides/AUTOMATION_WORKFLOWS.md) - Complete automation system
- [Testing Guide](../../../docs/testing/README.md) - E2E test architecture
- [Feature Registry](../../../docs/feature-registry.yaml) - File-to-feature mapping

**Architectural Decision Records:**
- [ADR-003: Ticker Architecture](../../../docs/decisions/003-multi-broker-ticker-architecture.md)
- [Broker Abstraction](../../../docs/architecture/broker-abstraction.md)

### Quick Command Reference

**Common workflows:**
```bash
# Run auto-verify (after code changes)
Skill(skill="auto-verify")

# Query knowledge base
.claude/skills/auto-verify/helpers/query-knowledge.sh \
  --error-type "Element not found" \
  --limit 5

# Record to knowledge base
Skill(skill="learning-engine", args="--outcome success --error-type '...'")

# Check synthesis eligibility
Skill(skill="reflect", args="--mode session")

# Escalate to fix-loop
Skill(skill="fix-loop", args="--thinking-level Deep")

# Manual browser debugging
Skill(skill="browser-testing", args="Debug /positions screen")
```

### MCP Playwright Tools Reference

**Browser navigation:**
- `mcp__playwright__browser_navigate` - Navigate to URL
- `mcp__playwright__browser_snapshot` - Capture accessibility snapshot

**Debugging:**
- `mcp__playwright__browser_console_messages` - Get console errors
- `mcp__playwright__browser_evaluate` - Run custom JavaScript
- `mcp__playwright__browser_network_requests` - Check API calls

**Visual verification:**
- `mcp__playwright__browser_take_screenshot` - Capture screenshots
- `mcp__playwright__browser_click` - Interact with elements
