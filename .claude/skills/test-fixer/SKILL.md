---
name: test-fixer
description: Diagnose and fix failing E2E and unit tests. Use when tests fail, debugging test issues, or investigating test errors in AlgoChanakya.
---

# Test Fixer

Systematically diagnose and fix failing E2E and unit tests by identifying common failure patterns.

## When to Use

- Tests are failing and need diagnosis
- User asks to fix broken tests
- User mentions test failures or errors
- User wants to investigate why tests are failing

## Failure Pattern Detection

When a test fails, follow this systematic approach:

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
await myPage.waitForPageLoad(); // Waits for networkidle + buffer
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

## References

- [Common Failure Patterns](./references/common-failure-patterns.md) - Detailed failure patterns and fixes
