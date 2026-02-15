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
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js --retries=2
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

Based on analysis:

| Outcome | Action |
|---------|--------|
| Tests pass + Screenshots look correct | **SUCCESS** - Proceed to Step 8 (record to knowledge base) |
| Tests fail | Analyze error, fix code, go to Step 3 |
| Tests pass but screenshots show issues | Fix code, go to Step 3 |
| **Hit stuck condition** | **STOP** - Ask user (see Troubleshooting section below) |

### Step 6b: Visual Debugging with Claude Chrome (PRIMARY METHOD)

**IMPORTANT:** Use Claude Chrome as the PRIMARY tool for visual verification and debugging.

After Playwright tests complete (pass or fail), use Claude Chrome for live debugging:

1. **Start Chrome session** (if not already started):
   ```bash
   claude --chrome
   ```

2. **Open the failing screen** using `/open-in-chrome`:
   ```
   /open-in-chrome /positions   # Or whichever screen was tested
   ```

3. **Visual verification workflow**:
   ```
   1. Navigate to the screen that was tested
   2. Open DevTools console
   3. Check for errors (especially WebSocket, API, React errors)
   4. Verify data-testid elements exist
   5. Test the user flow manually
   6. Capture screenshot or GIF of the issue
   7. Report findings
   ```

4. **Common debugging commands**:
   ```
   "Go to localhost:5173/positions and check console for errors"
   "Verify that positions-exit-modal element exists"
   "Click the exit button and see if the modal appears"
   "Monitor WebSocket messages for 10 seconds"
   "Take a screenshot of the current state"
   ```

5. **When to use Chrome vs Playwright**:

   | Scenario | Tool |
   |----------|------|
   | Running automated tests | Playwright |
   | Visual verification of test results | **Claude Chrome** |
   | Debugging failing tests | **Claude Chrome** |
   | Checking console errors | **Claude Chrome** |
   | Verifying data-testid elements | **Claude Chrome** |
   | Testing WebSocket real-time | **Claude Chrome** |
   | Recording demo GIFs | **Claude Chrome** |

6. **Integration with Playwright results**:
   ```
   Example workflow:
   1. Run Playwright test → Test fails at line 45
   2. Use Chrome to navigate to the tested URL
   3. Reproduce the failure manually
   4. Check console for errors
   5. Inspect DOM state
   6. Identify root cause
   7. Fix the code
   8. Re-run Playwright test to verify
   9. Use Chrome again to visually confirm
   ```

### Step 7: Fix and Iterate

If issues found:
1. Identify the root cause (using Chrome debugging if needed)
2. **Check approval requirements** (see below)
3. Make the fix
4. Increment attempt counter
5. Return to Step 3


### Step 8: Record to Knowledge Base (Learning Engine)

**After EVERY fix attempt** (success or failure), record to knowledge base:

```bash
cd .claude/learning
python -c "
import sys
import subprocess
sys.path.insert(0, '.')
from db_helper import record_attempt, update_strategy_score

# Get current git commit hash (first 7 chars)
try:
    commit_hash = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True, text=True
    ).stdout.strip()[:7]
except:
    commit_hash = None

# Record the attempt
attempt_id = record_attempt(
    error_pattern_id={error_id},  # From Step 2c
    strategy_id={strategy_id},    # Or None if no strategy used
    outcome='success',            # or 'failure'
    session_id='{session_id}',    # Current Claude session
    file_path='{file_path}',
    error_message='{full_error}',
    fix_description='{what_was_done}',
    duration_seconds={elapsed_time},
    git_commit_hash=commit_hash
)

# Update strategy score if one was used
if {strategy_id}:
    update_strategy_score({strategy_id})

print(f'✓ Recorded attempt #{attempt_id} to knowledge base')
"
```

**On SUCCESS:**

1. **Run verification loop** (expand test radius):
   ```bash
   # Run adjacent feature tests to check for regressions
   # Example: If fixed positions, also run watchlist tests
   npx playwright test tests/e2e/specs/watchlist/watchlist.happy.spec.js
   ```

2. **If verification passes**, boost strategy score:
   ```python
   # Boost score by 0.1 for verified fix
   from db_helper import get_connection
   conn = get_connection()
   conn.execute(
       "UPDATE fix_strategies SET current_score = MIN(current_score + 0.1, 1.0) WHERE id = ?",
       ({strategy_id},)
   )
   conn.commit()
   conn.close()
   ```

3. **Check for synthesis** - If strategy now meets criteria (≥70% success, ≥5 evidence):
   ```bash
   cd .claude/learning
   python -c "
   from db_helper import synthesize_rules
   new_rules = synthesize_rules(min_confidence=0.7, min_evidence=5)
   if new_rules:
       print(f'✨ {len(new_rules)} new rules synthesized!')
   "
   ```

**On FAILURE:**

1. **Decrease strategy score** (automatic in `update_strategy_score()`)
2. **Try next ranked strategy** from Step 2c
3. **If no more strategies**, check stuck conditions (Step 6)

**On FIRST FIX for unknown pattern:**

1. **Create new strategy** in knowledge base:
   ```python
   from db_helper import get_connection
   import json
   from datetime import datetime

   conn = get_connection()
   conn.execute(
       """INSERT INTO fix_strategies
          (name, error_type, description, steps, preconditions, created_at, source)
          VALUES (?, ?, ?, ?, ?, ?, 'learned')""",
       (
           'Fix: {descriptive_name}',
           '{error_type}',
           '{what_this_fix_does}',
           json.dumps(['{step_1}', '{step_2}', ...]),
           json.dumps({precondition_dict}),
           datetime.utcnow().isoformat()
       )
   )
   conn.commit()
   conn.close()
   print('✓ New strategy recorded for future use')
   ```

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

## Troubleshooting

### Stuck Conditions

**STOP and ask user when ANY of these conditions are met:**

1. **Same fingerprinted error 3x** - Same error pattern with 3 different strategies all failing
2. **All strategies exhausted** - All known strategies have score < 0.1 (proven ineffective)
3. **20 total attempts in session** - Safety valve to prevent infinite loops
4. **Fix scope exceeds feature** - Fix requires modifying files outside current feature
5. **Completely unknown error** - No matching error_type in knowledge base strategies

### Stuck Message Template

```
I'm stuck on this error. Here's what I know:

**Error:** {error_type} - {error_message_summary}
**Fingerprint:** {fingerprint} (seen {occurrence_count} times in knowledge base)
**File:** {file_path}

**Knowledge Base Context:**
- Total patterns: {total_patterns}
- This error pattern: {known/unknown}
- Best available strategy: {strategy_name} (score: {score})
- Threshold for trying: 0.3

**Strategies attempted:**
1. [{score}] {strategy_name} - {outcome}
2. [{score}] {strategy_name} - {outcome}
...

Would you like me to:
1. Try a different heuristic approach (describe what)
2. Record this as a new learned pattern
3. Skip and move to other verification tasks
```

### Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Can't find test file for changed code | File not mapped in feature-registry.yaml | Add file pattern to registry OR run full feature tests as fallback |
| Screenshots directory missing | `.claude/logs/evidence/` not created | Create: `mkdir -p .claude/logs/evidence/` |
| Chrome debugging not working | Chrome extension not connected | Restart with `claude --chrome` |
| Knowledge base returns no strategies | `knowledge.db` not initialized | Run `/reflect` once to initialize |

---

## References

- `references/workflow-checklist.md` - Quick checklist version
- `references/screenshot-analysis-guide.md` - How to analyze screenshots
- `references/approval-scenarios.md` - Detailed approval scenarios
