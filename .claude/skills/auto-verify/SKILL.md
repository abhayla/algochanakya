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
