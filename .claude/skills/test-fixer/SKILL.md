---
name: test-fixer
description: Diagnose and fix failing E2E and unit tests. Do NOT use this to generate new tests (use e2e-test-generator or vitest-generator for that). Use when tests fail, debugging test issues, or investigating test errors in AlgoChanakya.
metadata:
  author: AlgoChanakya
  version: "1.0"
---

# Test Fixer

Systematically diagnose and fix failing E2E and unit tests by identifying common failure patterns.

## When to Use

- Tests are failing and need diagnosis
- User asks to fix broken tests
- User mentions test failures or errors
- User wants to investigate why tests are failing

## When NOT to Use

- Generating new tests (use e2e-test-generator or vitest-generator instead)
- When all tests are passing (no failures to fix)

## Failure Pattern Detection

When a test fails, follow this systematic approach:

### Step 0: Knowledge Base Lookup (Learning Engine)

**Before standard diagnosis**, check if this test failure is already known:

```bash
cd .claude/learning
python -c "
import sys
sys.path.insert(0, '.')
from db_helper import record_error, get_strategies

# Fingerprint the error from test output
error_id = record_error(
    error_type='TestFailure',
    message='<error_message_from_test_output>',
    file_path='<test_file_path>'
)

# Get ranked strategies
strategies = get_strategies('TestFailure', limit=3)

if strategies:
    print('KNOWN PATTERN - Ranked fixes:')
    for s in strategies:
        print(f'  [{s[\"effective_score\"]:.2f}] {s[\"name\"]}: {s[\"description\"]}')
        if s['effective_score'] >= 0.5:
            print(f'    PROVEN FIX - Apply this strategy')
else:
    print('UNKNOWN PATTERN - Proceed with standard diagnosis (Step 1)')
"
```

**Decision Matrix:**

| Strategy Score | Action |
|----------------|--------|
| **≥ 0.5** (Proven) | Apply strategy directly, skip to fix |
| **0.2-0.5** (Moderate) | Use as hint during standard diagnosis |
| **< 0.2** (Unproven) | Ignore, proceed with standard diagnosis |
| **None found** | Proceed with Step 1, record as new pattern after fix |

**Example:**

```
# Test failure: Locator 'positions-exit-modal' not found
# Learning engine query returns:
#   [0.82] Update Stale Selector (10/12 attempts) - PROVEN FIX
#   [0.54] Fix Async Timing (3/6 attempts)

# Action: Apply "Update Stale Selector" directly
# 1. Find data-testid in component
# 2. Update Page Object getter
# 3. Run test again
# 4. Record outcome to knowledge base
```

**If High-Confidence Strategy Found:**
1. Apply the strategy steps directly
2. Run test to verify
3. Record attempt outcome (Step 7)
4. If success, you're done
5. If failure, try next strategy or proceed to Step 1

**If No Strategy or Low Confidence:**
1. Proceed to Step 1 (standard diagnosis)
2. After resolving, record as new learned pattern

---

### Step 1: Identify the Failure Type

Read the test error message and categorize:

1. **Selector Not Found** - `Error: locator.click: Target closed` or `Timeout 10000ms exceeded`
2. **Assertion Failure** - `expect(received).toBeVisible()` failed
3. **API/Network Error** - `404`, `500`, or network timeout
4. **Timing Issue** - Element found but interaction failed
5. **State Pollution** - Test passes alone but fails in suite

### Step 2: Common Failure Patterns

## Pattern 1: Missing or Wrong data-testid

### Symptoms
- `Error: locator.click: Target closed`
- `Timeout waiting for selector [data-testid="..."]`
- Test can't find element

### Diagnosis
1. Check the Vue component - does the data-testid attribute exist?
2. Check Page Object getter - does it use the correct testid?
3. Is the testid spelled correctly?

### Fix
**Check Component:**
```vue
<!-- WRONG - Missing data-testid -->
<button class="submit-btn">Submit</button>

<!-- RIGHT - Has data-testid -->
<button data-testid="myscreen-submit-button">Submit</button>
```

**Check Page Object:**
```javascript
// Verify getter matches component
get submitButton() {
  return this.getByTestId('myscreen-submit-button'); // Must match Vue component
}
```

**Common Mistakes:**
- Typo in data-testid: `submit-buttom` vs `submit-button`
- Wrong screen prefix: `strategy-submit` in a positions screen
- Dynamic testid not matching: `item-${id}` vs `item-${index}`

---

## Pattern 2: Duplicate Getter Definitions

### Symptoms
- Test uses wrong selector
- Second definition overwrites first
- Confusion about which getter is used

### Diagnosis
Search Page Object file for duplicate getter names.

### Fix
```javascript
// WRONG - Duplicate getters (second one wins!)
class MyPage extends BasePage {
  get activeCount() { return this.getByTestId('correct-testid'); } // Line 28

  // ... 200 lines later ...

  get activeCount() { return this.getByTestId('wrong-testid'); } // Line 246 - OVERWRITES!
}

// RIGHT - Unique getter names
class MyPage extends BasePage {
  get activeStrategiesCount() { return this.getByTestId('autopilot-active-count'); }
  get riskActiveStrategies() { return this.getByTestId('risk-active-strategies'); }
}
```

**How to Find:**
1. Open the Page Object file
2. Search for `get <getterName>`
3. If multiple matches, rename or remove duplicates

---

## Pattern 3: Component Restructuring

### Symptoms
- Selector worked before but now fails
- Component UI changed
- New nested structure

### Diagnosis
1. Check if component was refactored
2. Compare old vs new component structure
3. Check if data-testid moved or was removed

### Fix Example: StrikeSelector Refactor

**Old Component:**
```vue
<select :data-testid="`strategy-leg-strike-${index}`">
  <option>24000</option>
</select>
```

**New Component (Restructured):**
```vue
<div :data-testid="`strategy-leg-strike-${index}`">
  <select data-testid="strike-selector-mode-dropdown">
    <option>Fixed</option>
  </select>
  <input data-testid="strike-selector-fixed-input" />
</div>
```

**Page Object Update:**
```javascript
// OLD - Simple selector
getLegStrike(index) {
  return this.getByTestId(`strategy-leg-strike-${index}`);
}

// NEW - Nested selectors
getLegStrikeContainer(index) {
  return this.getByTestId(`strategy-leg-strike-${index}`);
}

getLegStrikeModeDropdown(index) {
  return this.getLegStrikeContainer(index).locator('[data-testid="strike-selector-mode-dropdown"]');
}

getLegStrikeInput(index) {
  return this.getLegStrikeContainer(index).locator('[data-testid="strike-selector-fixed-input"]');
}

// Updated action
async setLegStrike(index, strike) {
  await this.getLegStrikeModeDropdown(index).selectOption('fixed');
  await this.getLegStrikeInput(index).fill(strike.toString());
}
```

---

## Pattern 4: Timing and Visibility Issues

### Symptoms
- Element exists but click fails
- Race condition - sometimes passes, sometimes fails
- `Element is not visible`

### Diagnosis
1. Is element initially hidden (loading, modal animation)?
2. Is there an async operation before element appears?
3. Does element require scroll into view?

### Fix

**Problem: Element not yet visible**
```javascript
// WRONG - No wait
await myPage.submitButton.click();

// RIGHT - Wait for visibility
await expect(myPage.submitButton).toBeVisible();
await myPage.submitButton.click();
```

**Problem: Loading state**
```javascript
// WRONG - Click before data loads
await myPage.navigate();
await myPage.clickFirstItem(); // May fail if still loading

// RIGHT - Wait for page load
await myPage.navigate();
await myPage.waitForPageLoad(); // Waits for domcontentloaded + buffer
await expect(myPage.firstItem).toBeVisible();
await myPage.clickFirstItem();
```

**Problem: Modal animation**
```javascript
// Add wait in Page Object
async clickSubmit() {
  await this.waitForTestId('myscreen-submit-button'); // Explicit wait
  await this.submitButton.click();
}
```

---

## Pattern 5: API Mock Issues

### Symptoms
- Test expects mocked data but gets real API response
- Mock not intercepting the request
- Wrong API endpoint pattern

### Diagnosis
1. Check route pattern matches actual request URL
2. Verify mock is set up before navigation
3. Check if wildcard pattern is correct

### Fix

**Problem: Route pattern doesn't match**
```javascript
// WRONG - Missing wildcard
await page.route('/api/positions', route => { ... });

// RIGHT - Wildcard to match full URL
await page.route('**/api/positions', route => { ... });
await page.route('**/api/positions/**', route => { ... }); // Matches sub-paths
```

**Problem: Mock after navigation**
```javascript
// WRONG - Mock after page loads
await myPage.navigate();
await page.route('**/api/data', route => { ... }); // Too late!

// RIGHT - Mock before navigation
await page.route('**/api/data', route => {
  route.fulfill({ status: 200, body: JSON.stringify({...}) });
});
await myPage.navigate();
```

---

## Pattern 6: Validation Not Implemented

### Symptoms
- Edge case test fails because validation is missing
- Negative values accepted
- Invalid input not rejected

### Diagnosis
Check if frontend or backend has validation logic.

### Fix

**Example: Missing negative number validation**

Backend (FastAPI):
```python
# Add validation in Pydantic schema
class RiskSettings(BaseModel):
    max_loss: Decimal = Field(gt=0)  # Must be greater than 0
```

Frontend (Vue):
```javascript
// Add validation in store
validateRiskSettings() {
  const errors = [];
  if (this.riskSettings.max_loss < 0) {
    errors.push('Max loss must be positive');
  }
  return errors;
}
```

---

## Pattern 7: State Pollution Between Tests

### Symptoms
- Test passes when run alone
- Test fails when run in suite
- Previous test affects current test

### Diagnosis
1. Check if modal/dropdown is left open
2. Check if data is not cleared
3. Check if auth state is corrupted

### Fix

**Use cleanup in fixture:**
```javascript
// auth.fixture.js already includes cleanup
async function cleanupPageState(page) {
  // Close modals
  await page.keyboard.press('Escape');
  // Close dropdowns
  // Clear state
}
```

**Add test-level cleanup:**
```javascript
test.afterEach(async ({ authenticatedPage }) => {
  // Reset any test-specific state
  await authenticatedPage.evaluate(() => {
    localStorage.removeItem('test-data');
  });
});
```

---

## Diagnostic Workflow

When a test fails:

### 1. Read the Error Message
```
Error: locator.click: Target closed
  selector: [data-testid="autopilot-waiting-count"]
```

### 2. Check the Component
```bash
# Search for the data-testid in Vue components
grep -r "autopilot-waiting-count" frontend/src/
```

### 3. Check the Page Object
```bash
# Find the getter in Page Object
grep -r "waitingCount" tests/e2e/pages/
```

### 4. Verify Match
- Component: `data-testid="autopilot-waiting-count"`
- Page Object: `this.getByTestId('autopilot-waiting-count')`
- Do they match? ✅ or ❌

### 5. Fix the Mismatch
- Add missing data-testid to component
- Fix typo in Page Object
- Update selector after component refactor

---

## Quick Fixes Checklist

- [ ] Component has data-testid attribute
- [ ] Page Object getter uses correct testid
- [ ] No typos in testid spelling
- [ ] No duplicate getters in Page Object
- [ ] Proper waits before interactions (`waitForTestId`, `toBeVisible`)
- [ ] API mocks use wildcard pattern (`**/api/...`)
- [ ] API mocks set up BEFORE navigation
- [ ] Validation logic exists (frontend or backend)
- [ ] No state pollution from previous tests

---

## Chrome-Assisted Debugging

For complex test failures, use **Claude Chrome** to debug interactively:

### When to Use Chrome

Use Claude Chrome debugging when:
- Error message is unclear
- Need to check console errors
- Need to verify element exists in DOM
- Need to test WebSocket connection
- Need to reproduce failure manually
- Need visual confirmation

### Chrome Debugging Workflow

**Step 1: Get Test URL**
```
From test file, identify the URL being tested:
- positions.happy.spec.js → localhost:5173/positions
- autopilot.phases123.spec.js → localhost:5173/autopilot
```

**Step 2: Open in Chrome**
```
/open-in-chrome /positions
```

**Step 3: Check Console**
```
"Go to localhost:5173/positions and open the console.
Check for errors, especially:
- WebSocket connection errors ([AutoPilot WS] prefix)
- API request failures
- React/Vue warnings
- data-testid element not found
Report all findings."
```

**Step 4: Verify Elements**
```
"Check if the element with data-testid='positions-table' exists in the DOM.
Use document.querySelector('[data-testid=\"positions-table\"]') and report."
```

**Step 5: Reproduce Manually**
```
"Try clicking the exit button on the first position and tell me:
1. Does the modal appear?
2. Are there any console errors?
3. Is the data-testid correct?
4. What happens?"
```

**Step 6: Check WebSocket**
```
"Open Network tab -> WS tab and check if WebSocket is connected.
Report the connection status and any error messages."
```

**Step 7: Capture Evidence**
```
"Take a screenshot of the current state showing the error."
```

### Example Debug Flow

**Scenario:** Test at `positions.happy.spec.js:45` is failing

```
Test Error:
  Error: locator.click: Target closed
  selector: [data-testid="positions-exit-modal"]
```

**Chrome Debug Steps:**

1. **Open in Chrome:**
   ```
   /open-in-chrome /positions
   ```

2. **Check console:**
   ```
   "Check console for errors"
   ```
   Result: `TypeError: Cannot read property 'symbol' of undefined`

3. **Verify element:**
   ```
   "Check if positions-exit-modal exists"
   ```
   Result: Element doesn't exist in DOM

4. **Test interaction:**
   ```
   "Click the first exit button and see what happens"
   ```
   Result: Console error occurs, modal doesn't open

5. **Identify root cause:**
   - Modal component not rendering due to data undefined error
   - Need to check positions store for data loading issue

6. **Fix and verify:**
   - Fix the data loading bug
   - Re-run Playwright test
   - Use Chrome to visually confirm fix

### Chrome vs Playwright

| Use Case | Tool |
|----------|------|
| Running automated regression tests | Playwright |
| Debugging test failures | **Claude Chrome** |
| Checking console errors | **Claude Chrome** |
| Verifying element exists | **Claude Chrome** |
| Testing WebSocket | **Claude Chrome** |
| Manual reproduction | **Claude Chrome** |
| Visual confirmation | **Claude Chrome** |

---



---

## Step 7: Record to Knowledge Base (Learning Engine)

**After resolving ANY test failure**, record to knowledge base:

```bash
cd .claude/learning
python -c "
import sys
import subprocess
sys.path.insert(0, '.')
from db_helper import record_attempt, update_strategy_score, get_connection
import json
from datetime import datetime

# Get git commit hash
try:
    commit_hash = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True, text=True
    ).stdout.strip()[:7]
except:
    commit_hash = None

# Record the attempt
attempt_id = record_attempt(
    error_pattern_id={error_id},     # From Step 0
    strategy_id={strategy_id},       # Or None if no strategy used
    outcome='success',               # or 'failure'
    session_id='{session_id}',
    file_path='{test_file_path}',
    error_message='{full_error}',
    fix_description='{what_was_done}',
    duration_seconds={elapsed_time},
    git_commit_hash=commit_hash
)

# Update strategy score if one was used
if {strategy_id}:
    update_strategy_score({strategy_id})

print(f'[OK] Recorded attempt #{attempt_id} to knowledge base')
"
```

### On Success (Fix Worked)

1. **If strategy was used**, boost its score:
   ```python
   from db_helper import get_connection
   conn = get_connection()
   conn.execute(
       "UPDATE fix_strategies SET current_score = MIN(current_score + 0.05, 1.0) WHERE id = ?",
       ({strategy_id},)
   )
   conn.commit()
   conn.close()
   ```

2. **If pattern matches existing common pattern**, boost that pattern's score

3. **Check for synthesis** - If strategy now meets criteria (≥70% success, ≥5 evidence):
   ```bash
   cd .claude/learning
   python -c "
   from db_helper import synthesize_rules
   new_rules = synthesize_rules(min_confidence=0.7, min_evidence=5)
   if new_rules:
       print(f'[OK] {len(new_rules)} new rules synthesized!')
   "
   ```

### On First Fix for Unknown Pattern

If this test failure type was NOT in knowledge base (Step 0 returned empty):

```python
from db_helper import get_connection
import json
from datetime import datetime

conn = get_connection()

# Create new learned strategy based on what you did
conn.execute(
    """INSERT INTO fix_strategies
       (name, error_type, description, steps, preconditions, created_at, source)
       VALUES (?, ?, ?, ?, ?, ?, 'learned')""",
    (
        'Test Fix: {descriptive_name}',          # e.g., "Update Stale Modal Selector"
        'TestFailure',
        '{what_this_fix_does}',                  # e.g., "Update test selector after modal refactor"
        json.dumps([
            '{step_1}',                           # e.g., "Check component for current data-testid"
            '{step_2}',                           # e.g., "Update Page Object getter"
            '{step_3}'                            # e.g., "Verify test passes"
        ]),
        json.dumps({
            'error_contains': ['{pattern}']       # e.g., ['locator', 'not found']
        }),
        datetime.utcnow().isoformat()
    )
)
conn.commit()
conn.close()

print('[OK] New strategy recorded for future test failures')
```

**Example New Strategy:**

If you fixed "Locator 'autopilot-status-chip' not found" by:
1. Finding the component was refactored
2. Updating the data-testid from `autopilot-status-chip` to `autopilot-status-badge`
3. Updating Page Object getter

Record as:
```python
name = "Test Fix: Update Refactored Component Selector"
description = "Component was refactored with new data-testid, update Page Object"
steps = [
    "Check component file for current data-testid",
    "Update Page Object getter to match",
    "Run test to verify"
]
preconditions = {'error_contains': ['locator', 'not found', 'timeout']}
```

This becomes a learned strategy for future similar test failures.

---

## References

- [Common Failure Patterns](./references/common-failure-patterns.md) - Detailed failure patterns and fixes
