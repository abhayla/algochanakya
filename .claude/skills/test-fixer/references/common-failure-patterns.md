# Common Test Failure Patterns - Detailed Reference

Real-world failure patterns from AlgoChanakya with step-by-step fixes.

## Pattern 1: Missing data-testid in Component

### Example: AutoPilot Waiting Count

**Test Failure:**
```
Error: locator.textContent: Target closed
  selector: [data-testid="autopilot-waiting-count"]
  at tests/e2e/specs/autopilot/autopilot.happy.spec.js:658
```

**Root Cause:**
Component has the count but no data-testid on the specific element.

**Current Component** (`frontend/src/views/autopilot/DashboardView.vue:580`):
```vue
<p v-if="store.dashboardSummary.waiting_strategies > 0" class="summary-subtitle">
  {{ store.dashboardSummary.waiting_strategies }} waiting
</p>
```

**Fix:**
```vue
<p v-if="store.dashboardSummary.waiting_strategies > 0" class="summary-subtitle">
  <span data-testid="autopilot-waiting-count">{{ store.dashboardSummary.waiting_strategies }}</span> waiting
</p>
```

**Verification:**
```bash
# After fix, verify with grep
grep -n "autopilot-waiting-count" frontend/src/views/autopilot/DashboardView.vue
```

---

## Pattern 2: Duplicate Getter Overwrites

### Example: ActiveStrategiesCount

**Test Failure:**
```
expect(received).toBe(expected)
Expected: "3"
Received: undefined (wrong testid used)
  at tests/e2e/specs/autopilot/autopilot.happy.spec.js:37
```

**Root Cause:**
Two getters with same name in `AutoPilotDashboardPage.js`.

**Current Code:**
```javascript
// Line 28-29 (CORRECT)
get activeStrategiesCount() {
  return this.getByTestId('autopilot-active-count');
}

// Line 246-247 (WRONG - OVERWRITES!)
get activeStrategiesCount() {
  return this.getByTestId('risk-active-strategies');
}
```

**Fix:**
```javascript
// Line 28-29 (Keep this)
get activeStrategiesCount() {
  return this.getByTestId('autopilot-active-count');
}

// Line 246-247 (Rename or remove)
get riskActiveStrategiesCount() {
  return this.getByTestId('risk-active-strategies');
}
```

**How to Find:**
```bash
# Search for duplicate getter names
grep -n "get activeStrategiesCount" tests/e2e/pages/AutoPilotDashboardPage.js
```

---

## Pattern 3: Component Restructuring

### Example: StrikeSelector Refactor

**Test Failure:**
```
Error: locator.fill: Element is not an <input>
  selector: [data-testid="autopilot-leg-strike-0"]
  at tests/e2e/specs/autopilot/autopilot.happy.spec.js:305
```

**Root Cause:**
StrikeSelector component was changed from simple select to dropdown+input combo.

**Old Component Structure:**
```vue
<select :data-testid="`autopilot-leg-strike-${index}`">
  <option value="24000">24000</option>
</select>
```

**New Component Structure** (`StrikeSelector.vue`):
```vue
<div :data-testid="`autopilot-leg-strike-${index}`">
  <select data-testid="strike-selector-mode-dropdown">
    <option value="atm">ATM</option>
    <option value="fixed">Fixed</option>
  </select>

  <input
    v-if="mode === 'fixed'"
    data-testid="strike-selector-fixed-input"
    type="number"
  />
</div>
```

**Old Page Object Method:**
```javascript
async addLeg(index, strike) {
  await this.getLegStrike(index).fill(strike); // FAILS - not an input anymore
}
```

**Updated Page Object:**
```javascript
// Updated getter
getLegStrikeContainer(index) {
  return this.getByTestId(`autopilot-leg-strike-${index}`);
}

getLegStrikeModeDropdown(index) {
  const container = this.getLegStrikeContainer(index);
  return container.locator('[data-testid="strike-selector-mode-dropdown"]');
}

getLegStrikeInput(index) {
  const container = this.getLegStrikeContainer(index);
  return container.locator('[data-testid="strike-selector-fixed-input"]');
}

// Updated action
async addLeg(index, strike) {
  // First select "fixed" mode
  await this.getLegStrikeModeDropdown(index).selectOption('fixed');

  // Wait for input to appear
  await expect(this.getLegStrikeInput(index)).toBeVisible();

  // Fill the strike
  await this.getLegStrikeInput(index).fill(strike.toString());
}
```

**Tests Fixed:**
- autopilot.happy.spec.js:305, 344, 360, 377, 391, 402, 419, 435, 454

---

## Pattern 4: Wrong Selector Name

### Example: Add Condition Button

**Test Failure:**
```
Error: locator.click: Target closed
  selector: [data-testid="autopilot-builder-add-condition"]
  at tests/e2e/pages/AutoPilotDashboardPage.js:782
```

**Root Cause:**
Page Object uses `autopilot-builder-add-condition` but component has `autopilot-add-condition-button`.

**Component** (`StrategyBuilderView.vue:722`):
```vue
<button data-testid="autopilot-add-condition-button">Add Condition</button>
```

**Page Object** (`AutoPilotDashboardPage.js:782`):
```javascript
get addConditionButton() {
  return this.getByTestId('autopilot-builder-add-condition'); // WRONG!
}
```

**Fix (Option A - Update Page Object):**
```javascript
get addConditionButton() {
  return this.getByTestId('autopilot-add-condition-button'); // Matches component
}
```

**Fix (Option B - Update Component):**
```vue
<button data-testid="autopilot-builder-add-condition">Add Condition</button>
```

**Recommendation:** Fix Page Object (Option A) - Component name is more descriptive.

---

## Pattern 5: API Mock Not Intercepting

### Example: Resume Paused Strategy

**Test Failure:**
```
Error: expect(received).toBe(expected)
Expected: "waiting"
Received: undefined
  at tests/e2e/specs/autopilot/autopilot.api.spec.js:432
```

**Root Cause:**
Previous API calls (create → activate → pause) may have failed silently.

**Current Test:**
```javascript
test('should resume paused strategy', async ({ request }) => {
  // Create
  const createResponse = await request.post(`${API_BASE}/api/v1/autopilot/strategies`, {...});

  // Activate
  const activateResponse = await request.post(`${API_BASE}/api/v1/autopilot/strategies/${id}/activate`);

  // Pause
  const pauseResponse = await request.post(`${API_BASE}/api/v1/autopilot/strategies/${id}/pause`);

  // Resume - FAILS because preceding steps failed
  const resumeResponse = await request.post(`${API_BASE}/api/v1/autopilot/strategies/${id}/resume`);

  const data = await resumeResponse.json();
  expect(data.data.status).toBe('waiting'); // undefined!
});
```

**Fix - Add Assertions After Each Step:**
```javascript
test('should resume paused strategy', async ({ request }) => {
  // Create
  const createResponse = await request.post(`${API_BASE}/api/v1/autopilot/strategies`, {...});
  expect(createResponse.ok()).toBe(true);
  const createdData = await createResponse.json();
  expect(createdData.data).toHaveProperty('id');

  // Activate
  const activateResponse = await request.post(`${API_BASE}/api/v1/autopilot/strategies/${createdData.data.id}/activate`);
  expect(activateResponse.ok()).toBe(true);
  const activatedData = await activateResponse.json();
  expect(activatedData.data.status).toBe('waiting');

  // Pause
  const pauseResponse = await request.post(`${API_BASE}/api/v1/autopilot/strategies/${createdData.data.id}/pause`);
  expect(pauseResponse.ok()).toBe(true);
  const pausedData = await pauseResponse.json();
  expect(pausedData.data.status).toBe('paused');

  // Resume
  const resumeResponse = await request.post(`${API_BASE}/api/v1/autopilot/strategies/${createdData.data.id}/resume`);
  expect(resumeResponse.ok()).toBe(true);
  const resumedData = await resumeResponse.json();
  expect(resumedData.data.status).toBe('waiting');
});
```

---

## Pattern 6: Missing Validation Logic

### Example: Negative Max Loss

**Test Failure:**
```
Expected validation error but form submitted successfully
  at tests/e2e/specs/autopilot/autopilot.edge.spec.js:59
```

**Root Cause:**
No validation preventing negative `max_loss` values.

**Current Behavior:**
```javascript
// User can set max_loss to -1000 with no error
await autopilotPage.setMaxLoss('-1000');
await autopilotPage.clickSave();
// ❌ No error, saves successfully
```

**Fix - Add Validation in Store** (`frontend/src/stores/autopilot.js`):
```javascript
validateStep(step) {
  const errors = [];

  if (step === 'monitoring') {
    const { risk_settings } = this.builder.strategy;

    // Validate max_loss is positive
    if (risk_settings?.max_loss !== null && risk_settings?.max_loss < 0) {
      errors.push('Max loss must be a positive number');
    }

    // Validate max_loss_pct is between 0-100
    if (risk_settings?.max_loss_pct !== null) {
      if (risk_settings.max_loss_pct < 0 || risk_settings.max_loss_pct > 100) {
        errors.push('Max loss percentage must be between 0 and 100');
      }
    }
  }

  return errors;
}
```

**Fix - Add Backend Validation** (`backend/app/schemas/autopilot.py`):
```python
from pydantic import BaseModel, Field
from decimal import Decimal

class RiskSettings(BaseModel):
    max_loss: Decimal | None = Field(None, gt=0, description="Max loss must be positive")
    max_loss_pct: float | None = Field(None, ge=0, le=100)
```

---

## Pattern 7: Element Visibility Timing

### Example: Capital Progress Bar

**Test Failure:**
```
Error: expect(received).toBeVisible()
Received: <hidden>
  at tests/e2e/specs/autopilot/autopilot.happy.spec.js:166
```

**Root Cause:**
Element exists in DOM but is hidden (CSS `display: none` or `visibility: hidden`).

**Current Test:**
```javascript
test('should show capital progress bar', async ({ authenticatedPage }) => {
  await expect(autopilotPage.capitalProgressBar).toBeVisible(); // FAILS
});
```

**Fix Option 1 - Add Explicit Wait:**
```javascript
test('should show capital progress bar', async ({ authenticatedPage }) => {
  // Wait for element to appear
  await autopilotPage.page.waitForSelector(
    '[data-testid="autopilot-capital-progress-bar"]',
    { state: 'visible', timeout: 5000 }
  );

  await expect(autopilotPage.capitalProgressBar).toBeVisible();
});
```

**Fix Option 2 - Check Attachment Instead:**
```javascript
test('should show capital progress bar', async ({ authenticatedPage }) => {
  // Check if element is in DOM (even if hidden)
  await expect(autopilotPage.capitalProgressBar).toBeAttached();
});
```

**Fix Option 3 - Check Component Condition:**
```vue
<!-- Component may conditionally render -->
<div v-if="hasActiveStrategies" data-testid="autopilot-capital-progress-bar">
  <!-- Only shown when strategies are active -->
</div>
```

Test should ensure condition is met:
```javascript
test('should show capital progress bar when strategies are active', async ({ authenticatedPage }) => {
  // Ensure there are active strategies first
  await autopilotPage.activateStrategy();

  // Now progress bar should be visible
  await expect(autopilotPage.capitalProgressBar).toBeVisible();
});
```

---

## Pattern 8: Tab/Step Navigation Issues

### Example: Adjustment Rules Modal

**Test Failure:**
```
Error: locator.click: Target closed
  selector: [data-testid="autopilot-builder-monitoring-tab"]
  at tests/e2e/specs/adjustment-rules/adjustment-rules.happy.spec.js:54
```

**Root Cause:**
Step 3 tab doesn't exist or navigation prevented due to incomplete previous steps.

**Current Test:**
```javascript
test('should open adjustment rules modal', async ({ authenticatedPage }) => {
  // Navigate to builder
  await autopilotPage.navigateToBuilder();

  // Try to click step 3 tab
  await autopilotPage.builderMonitoringTab.click(); // FAILS
});
```

**Fix - Complete Previous Steps First:**
```javascript
test('should open adjustment rules modal', async ({ authenticatedPage }) => {
  // Navigate to builder
  await autopilotPage.navigateToBuilder();

  // Step 1: Fill strategy details
  await autopilotPage.fillStrategyDetails({
    underlying: 'NIFTY',
    expiry_type: 'current_week',
    lots: 2
  });

  // Add at least one leg
  await autopilotPage.addLeg({
    contract_type: 'CE',
    transaction_type: 'SELL',
    strike: 24000,
    quantity: 1
  });

  // Step 2: Fill entry conditions
  await autopilotPage.builderConditionsTab.click();
  await autopilotPage.addCondition({
    variable: 'TIME.CURRENT',
    operator: 'greater_equal',
    value: '09:20'
  });

  // NOW Step 3 tab should be enabled
  await autopilotPage.builderMonitoringTab.click();
  await expect(autopilotPage.adjustmentRulesSection).toBeVisible();
});
```

---

## Debugging Checklist

When a test fails:

### 1. Check Component
```bash
# Find the component file
grep -r "data-testid=\"failing-testid\"" frontend/src/

# Verify testid exists and is spelled correctly
```

### 2. Check Page Object
```bash
# Find the getter
grep -r "get failingGetter" tests/e2e/pages/

# Check for duplicates
grep -n "get failingGetter" tests/e2e/pages/MyPage.js
```

### 3. Check Test
```bash
# Read the test file
cat tests/e2e/specs/myscreen/myscreen.happy.spec.js | grep -A 10 "failing test"

# Check if test waits before interaction
# Check if test mocks API correctly
```

### 4. Run in Debug Mode
```bash
# Run single test in debug mode
npx playwright test tests/e2e/specs/myscreen/myscreen.happy.spec.js --debug

# Run in headed mode to see browser
npm run test:headed -- tests/e2e/specs/myscreen/myscreen.happy.spec.js
```

### 5. Check Recent Changes
```bash
# Check git history of component
git log -p -- frontend/src/views/MyScreen.vue

# Check if component was refactored
git diff HEAD~5 frontend/src/views/MyScreen.vue
```

---

## Synthesized Patterns (Auto-Generated by Learning Engine)

The patterns below were automatically synthesized from successful test fixes recorded in the knowledge base. They are updated when strategies reach ≥70% confidence with ≥5 evidence instances.

<!-- LEARNING_ENGINE_SYNTHESIS_MARKER - Do not remove -->
<!-- Auto-generated rules will be inserted below this line -->

*No synthesized patterns yet. As test fixes are recorded to the learning engine, high-confidence patterns will appear here automatically.*
