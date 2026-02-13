# Implementation Plan: AutoPilot Feature Not Implemented Tests

## Overview
Implement 11 missing features and update 1 test to resolve 12 skipped "Feature Not Implemented" tests in the AutoPilot E2E test suite.

## Confirmed Requirements

| # | Feature | Choice | Description |
|---|---------|--------|-------------|
| 1 | Drawdown Analysis | C | Full analysis: chart + stats + underwater periods table |
| 2 | Template Rating | A | Simple 5-star picker modal, anonymous ratings |
| 3-4 | Spot Distance Config | B | Visual indicator + toast notification |
| 5 | Delta Bands Settings | B | Inputs + visual preview of bands |
| 6-7 | Expected Move | B | Display value + highlight strikes outside range |
| 8 | DTE Enforcement | A | Warning only (allow entry anyway) |
| 9 | Delta Neutral Entry | B | Checkbox + configurable neutral range |
| 10 | Condition Order Validation | B | Suggest optimal order, allow override |
| 11 | Multi-condition AND/OR | B | Rebuild from scratch |
| 12 | Strategy Conversion | Update Test | Fix test alignment with existing modal |

---

## Feature 1: Drawdown Analysis (Full)

### Files to Modify
- `frontend/src/views/autopilot/BacktestsView.vue` - Add drawdown section
- `frontend/src/components/autopilot/backtest/DrawdownAnalysis.vue` - **NEW** component

### Implementation
1. Create `DrawdownAnalysis.vue` component with:
   - Line chart showing drawdown % over time (use existing chart library)
   - Stats cards: Max Drawdown %, Max Drawdown Date, Duration, Recovery Time
   - Underwater periods table: Start Date, End Date, Depth %, Duration
2. Add `data-testid="autopilot-backtest-drawdown"` to container
3. Fetch data from existing `GET /api/v1/autopilot/analytics/drawdown` endpoint
4. Remove `test.skip()` from `autopilot.backtest.spec.js:104`

### Test Expected Elements
- `data-testid="autopilot-backtest-drawdown"`

---

## Feature 2: Template Rating (Simple)

### Files to Modify
- `frontend/src/views/autopilot/TemplateLibraryView.vue` - Add rating modal
- `frontend/src/components/autopilot/templates/RatingModal.vue` - **NEW** component

### Implementation
1. Create `RatingModal.vue` with:
   - 5-star picker (clickable stars)
   - Submit button
   - `data-testid` attributes as expected by test
2. Add "Rate" button to template details modal
3. Call existing `POST /api/v1/autopilot/templates/{id}/rate` endpoint
4. Remove `test.skip()` from `autopilot.templates.spec.js:94`

### Test Expected Elements
- `data-testid="autopilot-template-rating-modal"`
- `data-testid="autopilot-template-rating-star-1"` through `star-5`
- `data-testid="autopilot-template-rating-submit"`

---

## Features 3-4: Spot Distance Config (Visual + Toast)

### Files to Modify
- `frontend/src/views/autopilot/StrategyDetailView.vue` - Add spot distance display
- `frontend/src/components/autopilot/monitoring/SpotDistanceMonitor.vue` - **NEW** component
- `frontend/src/stores/autopilot.js` - Add spot distance state

### Implementation
1. Create `SpotDistanceMonitor.vue` component:
   - Display current spot price
   - Show distance to PE/CE strikes as percentage
   - Visual indicator (green/yellow/red) based on proximity
   - Threshold inputs for PE and CE side (e.g., 2%, 1%, 0.5%)
2. Add toast notification when threshold breached using existing toast system
3. Add `data-testid="autopilot-spot-distance-pe"` and `autopilot-spot-distance-ce"`
4. Update tests to remove skip conditions

### Test Expected Elements
- `data-testid="autopilot-spot-distance-config"`
- `data-testid="autopilot-spot-distance-pe-threshold"`
- `data-testid="autopilot-spot-distance-ce-threshold"`

---

## Feature 5: Delta Bands Settings (Inputs + Preview)

### Files to Modify
- `frontend/src/views/autopilot/SettingsView.vue` - Add delta bands section
- `frontend/src/components/autopilot/settings/DeltaBandsConfig.vue` - **NEW** component

### Implementation
1. Create `DeltaBandsConfig.vue` component:
   - Upper band input (e.g., 0.20)
   - Lower band input (e.g., -0.20)
   - Visual preview showing bands on a gauge/slider
2. Add to SettingsView.vue in Risk Settings section
3. Persist to user settings via existing API
4. Add required `data-testid` attributes

### Test Expected Elements
- `data-testid="autopilot-settings-delta-band-upper"`
- `data-testid="autopilot-settings-delta-band-lower"`

---

## Features 6-7: Expected Move (Display + Highlight)

### Files to Modify
- `frontend/src/components/autopilot/builder/AutoPilotLegRow.vue` - Add expected move mode
- `frontend/src/components/autopilot/builder/ExpectedMoveDisplay.vue` - **NEW** component
- `backend/app/api/v1/autopilot/router.py` - Add expected move calculation endpoint

### Implementation
1. Add "Expected Move" strike selection mode to leg row dropdown
2. Create backend endpoint to calculate expected move:
   - Formula: `Expected Move = Spot Price × ATM IV × sqrt(DTE/365)`
   - Return upper and lower range values
3. Create `ExpectedMoveDisplay.vue`:
   - Show expected move range (e.g., "24,500 - 25,500")
   - Highlight strikes outside expected range in strike picker
4. Add `data-testid="autopilot-expected-move-display"`

### Test Expected Elements
- `data-testid="autopilot-expected-move-display"`
- Strike mode option: "expected_move" in dropdown

---

## Feature 8: DTE Enforcement (Warning Only)

### Files to Modify
- `frontend/src/views/autopilot/StrategyBuilderView.vue` - Add DTE inputs
- `frontend/src/components/autopilot/builder/EntrySettings.vue` - Add DTE section

### Implementation
1. Add Min DTE and Max DTE inputs to Entry Settings tab
2. On strategy save/activate, check if current DTE is within range
3. If outside range, show warning toast but allow user to proceed
4. Add `data-testid="autopilot-settings-min-dte"` and `autopilot-settings-max-dte"`

### Test Expected Elements
- `data-testid="autopilot-settings-min-dte"`
- `data-testid="autopilot-settings-max-dte"`

---

## Feature 9: Delta Neutral Entry (Configurable Range)

### Files to Modify
- `frontend/src/views/autopilot/StrategyBuilderView.vue` - Add delta neutral section
- `frontend/src/components/autopilot/builder/EntrySettings.vue` - Add checkbox + range

### Implementation
1. Add "Require Delta Neutral Entry" checkbox
2. Add configurable range inputs (default: -0.10 to +0.10)
3. Calculate net delta from all legs
4. Warn if net delta outside range on activation
5. Add `data-testid="autopilot-settings-delta-neutral-entry"`

### Test Expected Elements
- `data-testid="autopilot-settings-delta-neutral-entry"` (checkbox)
- `data-testid="autopilot-settings-delta-neutral-min"` (range input)
- `data-testid="autopilot-settings-delta-neutral-max"` (range input)

---

## Feature 10: Condition Order Validation (Suggest + Override)

### Files to Modify
- `frontend/src/components/autopilot/builder/ConditionBuilder.vue` - Add order suggestion

### Implementation
1. Define optimal order logic:
   - TIME conditions first
   - VIX conditions second
   - SPOT conditions third
   - PREMIUM conditions last
2. When conditions are added/reordered, check against optimal order
3. If not optimal, show info banner: "Suggested order: TIME → VIX → SPOT → PREMIUM"
4. Allow user to dismiss/ignore suggestion
5. Add `data-testid="autopilot-condition-order-suggestion"`

### Test Expected Elements
- `data-testid="autopilot-condition-order-suggestion"`

---

## Feature 11: Multi-condition AND/OR (Rebuild)

### Files to Modify
- `frontend/src/components/autopilot/builder/ConditionBuilder.vue` - Rebuild logic
- `frontend/src/components/autopilot/builder/ConditionGroup.vue` - **NEW** component

### Implementation
1. Create `ConditionGroup.vue` for grouping conditions
2. Add AND/OR toggle between condition groups
3. Support nested groups: `(A AND B) OR (C AND D)`
4. Visual UI showing groupings with connectors
5. Store as JSON: `{ logic: "OR", groups: [{ logic: "AND", conditions: [...] }] }`
6. Add `data-testid="autopilot-condition-logic-toggle"`

### Test Expected Elements
- `data-testid="autopilot-condition-logic-toggle"`
- `data-testid="autopilot-condition-group-add"`

---

## Feature 12: Strategy Conversion (Update Test)

### Files to Modify
- `tests/e2e/specs/autopilot/autopilot.phase5g.spec.js` - Update test selectors

### Implementation
1. Read existing `ConversionModal.vue` to understand actual implementation
2. Update test to use correct `data-testid` attributes
3. Align test flow with actual modal behavior
4. Remove any incorrect assertions

### Current Modal Location
- `frontend/src/components/autopilot/adjustments/ConversionModal.vue`

---

## Implementation Order (By Dependency)

### Phase 1: Settings & Configuration (Foundation)
1. Feature 5: Delta Bands Settings
2. Feature 8: DTE Enforcement
3. Feature 9: Delta Neutral Entry

### Phase 2: Monitoring & Display
4. Features 3-4: Spot Distance Config
5. Features 6-7: Expected Move

### Phase 3: Condition Builder
6. Feature 10: Condition Order Validation
7. Feature 11: Multi-condition AND/OR

### Phase 4: Standalone Features
8. Feature 1: Drawdown Analysis
9. Feature 2: Template Rating

### Phase 5: Test Updates
10. Feature 12: Update Strategy Conversion test

---

## Estimated Effort

| Phase | Features | Effort |
|-------|----------|--------|
| Phase 1 | Settings (3 features) | Medium |
| Phase 2 | Monitoring (2 features) | Medium |
| Phase 3 | Condition Builder (2 features) | High |
| Phase 4 | Standalone (2 features) | Medium |
| Phase 5 | Test Update (1 feature) | Low |

---

## Files Summary

### New Components (8)
- `frontend/src/components/autopilot/backtest/DrawdownAnalysis.vue`
- `frontend/src/components/autopilot/templates/RatingModal.vue`
- `frontend/src/components/autopilot/monitoring/SpotDistanceMonitor.vue`
- `frontend/src/components/autopilot/settings/DeltaBandsConfig.vue`
- `frontend/src/components/autopilot/builder/ExpectedMoveDisplay.vue`
- `frontend/src/components/autopilot/builder/EntrySettings.vue` (may exist, modify if so)
- `frontend/src/components/autopilot/builder/ConditionGroup.vue`

### Modified Views (4)
- `frontend/src/views/autopilot/BacktestsView.vue`
- `frontend/src/views/autopilot/TemplateLibraryView.vue`
- `frontend/src/views/autopilot/SettingsView.vue`
- `frontend/src/views/autopilot/StrategyBuilderView.vue`

### Modified Components (2)
- `frontend/src/components/autopilot/builder/AutoPilotLegRow.vue`
- `frontend/src/components/autopilot/builder/ConditionBuilder.vue`

### Backend (1)
- `backend/app/api/v1/autopilot/router.py` - Add expected move calculation

### Tests (5)
- `tests/e2e/specs/autopilot/autopilot.backtest.spec.js`
- `tests/e2e/specs/autopilot/autopilot.templates.spec.js`
- `tests/e2e/specs/autopilot/autopilot.phase5b.spec.js`
- `tests/e2e/specs/autopilot/autopilot.phase5c.spec.js`
- `tests/e2e/specs/autopilot/autopilot.phase5g.spec.js`

---

*Created: December 15, 2025*
