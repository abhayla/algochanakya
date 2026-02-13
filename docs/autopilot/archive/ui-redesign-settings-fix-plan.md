# Implementation Plan: Fix UI Redesign & Settings Not Visible Skipped Tests

## Overview
Fix 12 skipped E2E tests across two categories:
- **UI Redesign (4 tests)**: Tests skipped due to UI structure changes
- **Settings Not Visible (8 tests)**: Tests skipped because data-testid attributes are missing

## Test Analysis Summary

### Category 1: UI Redesign (4 tests)

| Test | File | Issue | Fix Approach |
|------|------|-------|--------------|
| `adds leg to strategy` | `autopilot.happy.spec.js:253` | Test uses old param names (`optionType` vs `contract_type`) | **Update test** to use new params |
| `removes leg from strategy` | `autopilot.happy.spec.js:267` | Same - outdated leg params | **Update test** to use new params |
| `shows validation error for invalid max loss` | `autopilot.edge.spec.js:59` | Leg lacks expiry/strike, fails Step 1 validation | **Update test** to provide complete leg |
| `multi-condition AND/OR` | `autopilot.phase5c.spec.js` | Test expects `autopilot-condition-logic-operator` | Already implemented - **unskip test** |

### Category 2: Settings Not Visible (8 tests)

All in `autopilot.phase5d.spec.js`. Tests expect these testids:

**Expected vs Current:**
| Expected TestID | Current TestID | Component |
|-----------------|----------------|-----------|
| `autopilot-builder-exit-rules-tab` | None (need to add) | StrategyBuilderView.vue |
| `autopilot-profit-target-section` | `profit-target-config` | ProfitTargetConfig.vue |
| `autopilot-exit-profit-pct-enable` | `profit-target-enabled` | ProfitTargetConfig.vue |
| `autopilot-exit-profit-pct-value` | None (slider only) | ProfitTargetConfig.vue |
| `autopilot-exit-premium-captured-enable` | None | ProfitTargetConfig.vue |
| `autopilot-exit-premium-captured-value` | None | ProfitTargetConfig.vue |
| `autopilot-exit-return-on-margin-enable` | None | ProfitTargetConfig.vue |
| `autopilot-exit-return-on-margin-value` | None | ProfitTargetConfig.vue |
| `autopilot-exit-dte-enable` | `dte-exit-enabled` | DTEExitConfig.vue |
| `autopilot-exit-dte-value` | None (slider only) | DTEExitConfig.vue |
| `autopilot-exit-days-in-trade-enable` | `days-in-trade-enabled` | DTEExitConfig.vue |
| `autopilot-exit-days-in-trade-value` | None (slider only) | DTEExitConfig.vue |
| `autopilot-exit-optimal-timing-suggestion` | None | DTEExitConfig.vue |

---

## Implementation Plan

### Phase 1: Fix UI Redesign Tests (Update Tests)

#### Task 1.1: Update `autopilot.happy.spec.js` - adds/removes leg tests
**File:** `tests/e2e/specs/autopilot/autopilot.happy.spec.js`

**Changes:**
1. Line 253-262: Update `addLeg()` call to use new parameter format:
   ```javascript
   // OLD:
   await builderPage.addLeg({
     optionType: 'CE',
     strikeMethod: 'atm_offset',
     transactionType: 'SELL'
   });

   // NEW:
   await builderPage.addLeg({
     contract_type: 'CE',
     transaction_type: 'SELL',
     strike: '25000'  // Provide strike to pass validation
   });
   ```

2. Line 267-275: Same fix for `removes leg from strategy` test

3. Remove `test.skip` and replace with `test`

#### Task 1.2: Update `autopilot.edge.spec.js` - max loss validation test
**File:** `tests/e2e/specs/autopilot/autopilot.edge.spec.js`

**Changes:**
1. Line 59-72: Update test to provide complete leg params:
   ```javascript
   await builderPage.addLeg({
     contract_type: 'CE',
     transaction_type: 'SELL',
     strike: '25000'
   });
   ```
2. Remove `test.skip`

#### Task 1.3: Unskip multi-condition AND/OR test
**File:** `tests/e2e/specs/autopilot/autopilot.phase5c.spec.js`

The `autopilot-condition-logic-operator` testid already exists in StrategyBuilderView.vue.
Just need to verify the test can find it and unskip.

---

### Phase 2: Fix Settings Not Visible Tests (Add testids + UI elements)

#### Task 2.1: Add Exit Rules Tab button
**File:** `frontend/src/views/autopilot/StrategyBuilderView.vue`

Add a clickable tab/button for exit rules in Step 4:
```vue
<button
  class="tab-button"
  data-testid="autopilot-builder-exit-rules-tab"
  @click="scrollToExitRules"
>
  Exit Rules
</button>
```

#### Task 2.2: Update ProfitTargetConfig.vue testids
**File:** `frontend/src/components/autopilot/builder/ProfitTargetConfig.vue`

**Changes:**
1. Update wrapper testid: `profit-target-config` → `autopilot-profit-target-section`
2. Update enable checkbox: `profit-target-enabled` → `autopilot-exit-profit-pct-enable`
3. Add number input with testid `autopilot-exit-profit-pct-value` (in addition to slider)
4. Add Premium Captured section:
   - Checkbox: `autopilot-exit-premium-captured-enable`
   - Input: `autopilot-exit-premium-captured-value`
5. Add Return on Margin section:
   - Checkbox: `autopilot-exit-return-on-margin-enable`
   - Input: `autopilot-exit-return-on-margin-value`

#### Task 2.3: Update DTEExitConfig.vue testids
**File:** `frontend/src/components/autopilot/builder/DTEExitConfig.vue`

**Changes:**
1. Update DTE enable checkbox: `dte-exit-enabled` → `autopilot-exit-dte-enable`
2. Add number input: `autopilot-exit-dte-value` (in addition to slider)
3. Update days-in-trade enable: `days-in-trade-enabled` → `autopilot-exit-days-in-trade-enable`
4. Add number input: `autopilot-exit-days-in-trade-value`
5. Add optimal timing suggestion element:
   ```vue
   <div data-testid="autopilot-exit-optimal-timing-suggestion" class="...">
     💡 Optimal exit timing: Exit at 21 DTE or 50% profit, whichever comes first
   </div>
   ```

---

## Files to Modify

### Test Files:
1. `tests/e2e/specs/autopilot/autopilot.happy.spec.js` - Update 2 tests
2. `tests/e2e/specs/autopilot/autopilot.edge.spec.js` - Update 1 test
3. `tests/e2e/specs/autopilot/autopilot.phase5c.spec.js` - Verify/unskip 1 test

### Vue Components:
4. `frontend/src/views/autopilot/StrategyBuilderView.vue` - Add exit rules tab button
5. `frontend/src/components/autopilot/builder/ProfitTargetConfig.vue` - Update testids + add fields
6. `frontend/src/components/autopilot/builder/DTEExitConfig.vue` - Update testids + add fields

---

## TestID Mapping Reference

### ProfitTargetConfig.vue Changes:
| Current | New |
|---------|-----|
| `profit-target-config` | `autopilot-profit-target-section` |
| `profit-target-enabled` | `autopilot-exit-profit-pct-enable` |
| (add new) | `autopilot-exit-profit-pct-value` |
| (add new) | `autopilot-exit-premium-captured-enable` |
| (add new) | `autopilot-exit-premium-captured-value` |
| (add new) | `autopilot-exit-return-on-margin-enable` |
| (add new) | `autopilot-exit-return-on-margin-value` |

### DTEExitConfig.vue Changes:
| Current | New |
|---------|-----|
| `dte-exit-config` | Keep as-is (not tested) |
| `dte-exit-enabled` | `autopilot-exit-dte-enable` |
| (add new) | `autopilot-exit-dte-value` |
| `days-in-trade-enabled` | `autopilot-exit-days-in-trade-enable` |
| (add new) | `autopilot-exit-days-in-trade-value` |
| (add new) | `autopilot-exit-optimal-timing-suggestion` |

---

## Verification

After implementation, run:
```bash
npm run test:specs:autopilot
```

Expected: All 12 previously-skipped tests should now pass (or at least find their elements and not skip due to `isVisible()` checks).

---

*Created: December 15, 2025*
