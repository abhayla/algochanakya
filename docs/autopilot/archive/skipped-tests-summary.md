# AutoPilot Skipped Tests Summary

This document provides a comprehensive overview of the 55 tests that are intentionally skipped in the AutoPilot E2E test suite.

## Test Results Overview

| Metric | Count |
|--------|-------|
| **Passed** | 287 |
| **Skipped** | 55 |
| **Failed** | 0 |
| **Total** | 342 |

---

## Skipped Tests by File

### 1. Static Skips (Permanently Skipped)

| # | Test File | Test Name | Reason |
|---|-----------|-----------|--------|
| 1 | `autopilot.backtest.spec.js:104` | `displays drawdown analysis` | Drawdown component not implemented in Vue results view |
| 2 | `autopilot.edge.spec.js:59` | `shows validation error for invalid max loss` | Risk settings step requires completing legs with expiry/strike |
| 3 | `autopilot.happy.spec.js:253` | `adds leg to strategy` | Legs are now on Step 1 - no navigation needed (UI redesign) |
| 4 | `autopilot.happy.spec.js:267` | `removes leg from strategy` | Legs are now on Step 1 - no navigation needed (UI redesign) |
| 5 | `autopilot.templates.spec.js:94` | `rates a template` | Rating feature not implemented |

### 2. Condition-Based Skips - Leg Actions (10 tests)

**File:** `autopilot.legs.actions.spec.js`

| # | Test Name | Skip Conditions |
|---|-----------|-----------------|
| 6 | `should view position legs panel` | `!hasStrategies` OR `!legsPanelVisible` |
| 7 | `should open exit single leg modal` | `!hasStrategies` OR `!legsPanelVisible` |
| 8 | `should shift leg modal - by strike` | `!hasStrategies` OR `!legsPanelVisible` |
| 9 | `should shift leg modal - by delta` | `!hasStrategies` OR `!legsPanelVisible` |
| 10 | `should open roll leg modal` | `!hasStrategies` OR `!legsPanelVisible` |
| 11 | `should open break trade wizard - step navigation` | `!hasStrategies` OR `!legsPanelVisible` |
| 12 | `should show break trade wizard - preview` | `!hasStrategies` OR `!legsPanelVisible` |
| 13 | `should show action buttons visibility` | `!hasStrategies` OR `!legsPanelVisible` |
| 14 | `should display P&L with colors` | `!hasStrategies` OR `!legsPanelVisible` |
| 15 | `should display Greeks per leg` | `!hasStrategies` OR `!legsPanelVisible` |

### 3. Phase 5B - Monitoring Features (16 tests)

**File:** `autopilot.phase5b.spec.js`

| # | Test Name | Reason |
|---|-----------|--------|
| 16 | Spot distance - PE side alert | Requires implementation |
| 17 | Spot distance - CE side alert | Requires implementation |
| 18 | Delta Bands - shows delta band widget | Requires active strategy |
| 19 | Delta Bands - gauge shows current delta | Requires active strategy |
| 20 | Delta Bands - triggers adjustment | Requires active strategy with delta outside band |
| 21 | Delta Bands - settings alerts | Settings not yet implemented |
| 22 | Premium Decay - shows decay tracker | Requires active strategy |
| 23 | Premium Decay - shows decay history | Requires active strategy with history |
| 24 | Premium Decay - percentage updates | Requires live market data |
| 25 | Theta Tracking - shows daily theta | Requires active strategy |
| 26 | Theta Tracking - shows theta chart | Requires active strategy with theta tracking |
| 27 | Intraday High/Low - shows high/low tracker | Requires active strategy |
| 28 | Intraday High/Low - alerts on breach | Requires specific market conditions |
| 29 | VIX Monitoring - shows VIX widget | Requires active strategy |
| 30 | VIX Monitoring - alerts on threshold | Requires active strategy |

### 4. Phase 5C - OI-Based & Entry Conditions (6 tests)

**File:** `autopilot.phase5c.spec.js`

| # | Test Name | Reason |
|---|-----------|--------|
| 31 | Expected Move - shows expected move value | Not yet implemented |
| 32 | Expected Move - calculates expected range | Requires implementation |
| 33 | Entry Logic - DTE enforcement | Not yet implemented |
| 34 | Entry Logic - delta neutral entry | Not yet implemented |
| 35 | Entry Logic - validates condition order | Requires implementation |
| 36 | Entry Logic - multi-condition AND/OR | Multi-condition logic not yet implemented |

### 5. Phase 5D - Exit Settings (7 tests)

**File:** `autopilot.phase5d.spec.js`

| # | Test Name | Reason |
|---|-----------|--------|
| 37 | Profit-Based Exits - profit target config | Settings not visible |
| 38 | Profit-Based Exits - 50% max profit target | Checkbox not visible |
| 39 | Profit-Based Exits - 25% profit target | Checkbox not visible |
| 40 | Profit-Based Exits - premium captured % | Checkbox not visible |
| 41 | Profit-Based Exits - target return on margin | Checkbox not visible |
| 42 | Time-Based Exits - DTE exit rule | Checkbox not visible |
| 43 | Time-Based Exits - days in trade limit | Checkbox not visible |
| 44 | Time-Based Exits - optimal exit timing | Checkbox not visible |

### 6. Phase 5E - Risk-Based Exits (6 tests)

**File:** `autopilot.phase5e.spec.js`

| # | Test Name | Reason |
|---|-----------|--------|
| 45 | Gamma Risk Exit - near expiry | Requires active strategy near expiry |
| 46 | VIX Spike Exit - VIX above threshold | Requires specific market conditions |
| 47 | DTE-Aware Exits - last week suggestion | Requires active strategy |
| 48 | DTE-Aware Exits - expiry day warning | Requires active strategy on expiry day |
| 49 | DTE-Aware Exits - auto-close before expiry | Requires active strategy |
| 50 | Risk combination exit | Requires multiple risk conditions |

### 7. Phase 5F-5I - Advanced Features (5 tests)

| # | File | Test Name | Reason |
|---|------|-----------|--------|
| 51 | `autopilot.phase5f.spec.js` | Break Trade - split execution | Requires active positions |
| 52 | `autopilot.phase5f.spec.js` | Break Trade - partial exit | Requires active positions |
| 53 | `autopilot.phase5g.spec.js` | Conversion - iron condor to butterfly | Requires specific position structure |
| 54 | `autopilot.phase5h.spec.js` | Suggestion Engine - execute suggestion | Requires active suggestion |
| 55 | `autopilot.phase5i.spec.js` | Staged Entry - complete all stages | Requires staged entry in progress |

---

## Skip Condition Categories with Feature Mapping

### Category 1: No Active Strategy (18 tests)

Tests that require an active AutoPilot strategy with positions to be present.

| # | Feature | Test Case | Test File |
|---|---------|-----------|-----------|
| 1 | Delta Bands | shows delta band widget | `autopilot.phase5b.spec.js` |
| 2 | Delta Bands | gauge shows current delta | `autopilot.phase5b.spec.js` |
| 3 | Delta Bands | triggers adjustment | `autopilot.phase5b.spec.js` |
| 4 | Premium Decay | shows decay tracker | `autopilot.phase5b.spec.js` |
| 5 | Premium Decay | shows decay history | `autopilot.phase5b.spec.js` |
| 6 | Theta Tracking | shows daily theta | `autopilot.phase5b.spec.js` |
| 7 | Theta Tracking | shows theta chart | `autopilot.phase5b.spec.js` |
| 8 | Intraday High/Low | shows high/low tracker | `autopilot.phase5b.spec.js` |
| 9 | VIX Monitoring | shows VIX widget | `autopilot.phase5b.spec.js` |
| 10 | VIX Monitoring | alerts on threshold | `autopilot.phase5b.spec.js` |
| 11 | DTE-Aware Exits | last week suggestion | `autopilot.phase5e.spec.js` |
| 12 | DTE-Aware Exits | expiry day warning | `autopilot.phase5e.spec.js` |
| 13 | DTE-Aware Exits | auto-close before expiry | `autopilot.phase5e.spec.js` |
| 14 | Gamma Risk Exit | near expiry | `autopilot.phase5e.spec.js` |
| 15 | Break Trade | split execution | `autopilot.phase5f.spec.js` |
| 16 | Break Trade | partial exit | `autopilot.phase5f.spec.js` |
| 17 | Suggestion Engine | execute suggestion | `autopilot.phase5h.spec.js` |
| 18 | Staged Entry | complete all stages | `autopilot.phase5i.spec.js` |

---

### Category 2: Feature Not Implemented (12 tests)

UI components or backend functionality not yet built.

| # | Feature | Test Case | Test File |
|---|---------|-----------|-----------|
| 1 | Drawdown Analysis | displays drawdown analysis | `autopilot.backtest.spec.js` |
| 2 | Template Rating | rates a template | `autopilot.templates.spec.js` |
| 3 | Spot Distance Config | PE side alert | `autopilot.phase5b.spec.js` |
| 4 | Spot Distance Config | CE side alert | `autopilot.phase5b.spec.js` |
| 5 | Delta Bands Settings | settings alerts | `autopilot.phase5b.spec.js` |
| 6 | Expected Move | shows expected move value | `autopilot.phase5c.spec.js` |
| 7 | Expected Move | calculates expected range | `autopilot.phase5c.spec.js` |
| 8 | Entry Logic | DTE enforcement | `autopilot.phase5c.spec.js` |
| 9 | Entry Logic | delta neutral entry | `autopilot.phase5c.spec.js` |
| 10 | Entry Logic | validates condition order | `autopilot.phase5c.spec.js` |
| 11 | Entry Logic | multi-condition AND/OR | `autopilot.phase5c.spec.js` |
| 12 | Strategy Conversion | iron condor to butterfly | `autopilot.phase5g.spec.js` |

---

### Category 3: No Strategies/Legs Available (10 tests)

Runtime checks that skip when no data exists at test time.

| # | Feature | Test Case | Test File | Skip Condition |
|---|---------|-----------|-----------|----------------|
| 1 | Position Legs Panel | should view position legs panel | `autopilot.legs.actions.spec.js` | `!hasStrategies \|\| !legsPanelVisible` |
| 2 | Exit Single Leg | should open exit single leg modal | `autopilot.legs.actions.spec.js` | `!hasStrategies \|\| !legsPanelVisible` |
| 3 | Shift Leg | should shift leg modal - by strike | `autopilot.legs.actions.spec.js` | `!hasStrategies \|\| !legsPanelVisible` |
| 4 | Shift Leg | should shift leg modal - by delta | `autopilot.legs.actions.spec.js` | `!hasStrategies \|\| !legsPanelVisible` |
| 5 | Roll Leg | should open roll leg modal | `autopilot.legs.actions.spec.js` | `!hasStrategies \|\| !legsPanelVisible` |
| 6 | Break Trade Wizard | should open break trade wizard - step navigation | `autopilot.legs.actions.spec.js` | `!hasStrategies \|\| !legsPanelVisible` |
| 7 | Break Trade Wizard | should show break trade wizard - preview | `autopilot.legs.actions.spec.js` | `!hasStrategies \|\| !legsPanelVisible` |
| 8 | Action Buttons | should show action buttons visibility | `autopilot.legs.actions.spec.js` | `!hasStrategies \|\| !legsPanelVisible` |
| 9 | P&L Display | should display P&L with colors | `autopilot.legs.actions.spec.js` | `!hasStrategies \|\| !legsPanelVisible` |
| 10 | Greeks Display | should display Greeks per leg | `autopilot.legs.actions.spec.js` | `!hasStrategies \|\| !legsPanelVisible` |

---

### Category 4: Specific Market Conditions (8 tests)

Tests that require live market data or specific market scenarios.

| # | Feature | Test Case | Test File | Required Condition |
|---|---------|-----------|-----------|-------------------|
| 1 | Premium Decay | percentage updates | `autopilot.phase5b.spec.js` | Live market data |
| 2 | Intraday High/Low | alerts on breach | `autopilot.phase5b.spec.js` | Price breaching high/low |
| 3 | VIX Spike Exit | VIX above threshold | `autopilot.phase5e.spec.js` | VIX spike in market |
| 4 | Risk Combination | risk combination exit | `autopilot.phase5e.spec.js` | Multiple risk conditions met |
| 5 | Delta Bands | triggers adjustment | `autopilot.phase5b.spec.js` | Delta outside band |
| 6 | DTE-Aware Exits | expiry day warning | `autopilot.phase5e.spec.js` | Strategy on expiry day |
| 7 | Gamma Risk Exit | near expiry | `autopilot.phase5e.spec.js` | Strategy near expiry |
| 8 | Staged Entry | complete all stages | `autopilot.phase5i.spec.js` | Staged entry in progress |

---

### Category 5: UI Redesign (4 tests)

Tests skipped due to UI structure changes (builder steps merged/changed).

| # | Feature | Test Case | Test File | UI Change |
|---|---------|-----------|-----------|-----------|
| 1 | Strategy Builder | adds leg to strategy | `autopilot.happy.spec.js` | Legs moved to Step 1 |
| 2 | Strategy Builder | removes leg from strategy | `autopilot.happy.spec.js` | Legs moved to Step 1 |
| 3 | Validation | shows validation error for invalid max loss | `autopilot.edge.spec.js` | Risk settings requires legs with expiry/strike |
| 4 | Entry Conditions | multi-condition AND/OR | `autopilot.phase5c.spec.js` | Condition builder redesigned |

---

### Category 6: Settings Not Visible (8 tests)

Settings checkboxes or configuration UI elements not rendered.

| # | Feature | Test Case | Test File | Missing Element |
|---|---------|-----------|-----------|-----------------|
| 1 | Profit-Based Exits | profit target config | `autopilot.phase5d.spec.js` | Settings section |
| 2 | Profit-Based Exits | 50% max profit target | `autopilot.phase5d.spec.js` | Checkbox |
| 3 | Profit-Based Exits | 25% profit target | `autopilot.phase5d.spec.js` | Checkbox |
| 4 | Profit-Based Exits | premium captured % | `autopilot.phase5d.spec.js` | Checkbox |
| 5 | Profit-Based Exits | target return on margin | `autopilot.phase5d.spec.js` | Checkbox |
| 6 | Time-Based Exits | DTE exit rule | `autopilot.phase5d.spec.js` | Checkbox |
| 7 | Time-Based Exits | days in trade limit | `autopilot.phase5d.spec.js` | Checkbox |
| 8 | Time-Based Exits | optimal exit timing | `autopilot.phase5d.spec.js` | Checkbox |

---

## Category Summary

| Category | Count | Description |
|----------|-------|-------------|
| **No Active Strategy** | 18 | Tests require an active strategy with positions |
| **Feature Not Implemented** | 12 | UI components or backend not yet built |
| **No Strategies/Legs Available** | 10 | Runtime check - no data exists at test time |
| **Specific Market Conditions** | 8 | Requires live market data or specific scenarios |
| **Settings Not Visible** | 8 | Settings checkboxes not rendered |
| **UI Redesign** | 4 | Builder steps merged/changed |
| **Total** | **60*** | *Some tests fall into multiple categories |

> **Note:** The total exceeds 55 because some tests are categorized under multiple skip reasons.

---

## Notes

1. **Runtime Skips**: Tests in `autopilot.legs.actions.spec.js` use runtime checks (`hasStrategies`, `legsPanelVisible`) to skip gracefully when preconditions aren't met.

2. **Feature Implementation**: Many Phase 5B-5I tests are skipped because the underlying features are planned but not yet implemented.

3. **Active Strategy Requirement**: Several tests require an active AutoPilot strategy with real positions, which may not exist during automated testing.

4. **Market Hours**: Some tests require live market data which is only available during market hours.

---

*Last Updated: December 15, 2025*
