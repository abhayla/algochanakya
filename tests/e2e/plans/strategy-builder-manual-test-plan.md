# Strategy Builder Manual Test Plan

This test plan validates the Strategy Builder's core functionality: row management, CMP updates, auto-calculation, and pre-built strategy templates.

## Quick Run Commands

```bash
# Run full test (Phase 1 + Phase 2) - ~4 minutes
npx playwright test tests/e2e/specs/strategy/strategy.manual-plan.spec.js --workers=1

# Run only Phase 2 (Strategy Templates) - ~2 minutes - RECOMMENDED for quick validation
npx playwright test tests/e2e/specs/strategy/strategy.manual-plan.spec.js --grep "Phase 2" --workers=1

# Run with visible browser (for debugging)
npx playwright test tests/e2e/specs/strategy/strategy.manual-plan.spec.js --grep "Phase 2" --headed --workers=1

# View screenshots after test
ls tests/e2e/screenshots/strategy-manual-plan/
```

## Fast Validation Checklist

For quick manual validation without running full test:

1. **Open Strategy Builder** → Select NIFTY → Wait for "Add Row" to be enabled
2. **Select "Iron Condor" from Type dropdown** → Confirm replace if prompted
3. **Verify in 10 seconds:**
   - [ ] 4 legs appear with DIFFERENT strikes (not all same)
   - [ ] All CMP columns show numbers (not "-")
   - [ ] Max Profit/Loss cards show values (not 0)
   - [ ] Payoff diagram shows Iron Condor shape (flat middle, wings down)

If all 4 checks pass → Strategy Builder is working correctly.

## Prerequisites

- Backend running (dev: port 8001, prod: port 8000)
- Frontend running (dev: port 5173)
- User authenticated with valid broker session
- Underlying selected (NIFTY/BANKNIFTY/FINNIFTY)

## Verification Methods

| Check Type | Method |
|------------|--------|
| **CMP Correctness** | Cross-reference UI value with backend API: `GET /api/orders/ltp?instruments=NFO:{tradingsymbol}` |
| **Calculation Trigger** | Verify API call to `POST /api/strategies/calculate` is made and grid updates |
| **P/L Correctness** | Verify using formulas (At Expiry mode): CE = `max(0, spot - strike)`, PE = `max(0, strike - spot)`, P/L = `(option_value - entry_price) * qty * multiplier` |
| **Summary Values** | Check Max Profit, Max Loss, Breakeven values are sensible for the strategy type |

## Test Steps

### Phase 1: Manual Row Operations

| Step | Action | Verifications | Screenshot |
|------|--------|---------------|------------|
| 1.1 | Add first row | - CMP column shows value (non-zero)<br>- CMP matches API response<br>- Auto-calculation triggers<br>- Summary cards update | Yes |
| 1.2 | Add second row | - Both rows have CMP values<br>- Auto-calculation triggers<br>- Summary reflects 2-leg strategy | Yes |
| 1.3 | Change CE/PE on row 1 | - CMP updates to new option price<br>- CMP matches API for new contract<br>- Auto-calculation triggers<br>- P/L grid recalculates | Yes |
| 1.4 | Change strike on row 1 | - CMP updates to new strike's price<br>- CMP matches API<br>- Auto-calculation triggers | Yes |
| 1.5 | Change expiry on row 1 | - CMP updates to new expiry's price<br>- CMP matches API<br>- Auto-calculation triggers | Yes |
| 1.6 | Change CE/PE on row 2 | - CMP updates correctly<br>- Auto-calculation triggers | Yes |
| 1.7 | Change strike on row 2 | - CMP updates correctly<br>- Auto-calculation triggers | Yes |
| 1.8 | Change expiry on row 2 | - CMP updates correctly<br>- Auto-calculation triggers | Yes |

### Phase 2: Pre-built Strategy Templates

| Step | Strategy | Expected Legs | Verifications | Screenshot |
|------|----------|---------------|---------------|------------|
| 2.1 | Iron Condor | 4 legs:<br>- BUY PE (OTM lower)<br>- SELL PE (OTM)<br>- SELL CE (OTM)<br>- BUY CE (OTM upper) | - All 4 legs populated<br>- All CMPs correct (API verified)<br>- Max Profit = net premium received<br>- Max Loss = spread width - premium<br>- 2 breakeven points | Yes |
| 2.2 | Short Straddle | 2 legs:<br>- SELL CE (ATM)<br>- SELL PE (ATM) | - Both legs at same ATM strike<br>- All CMPs correct<br>- Max Profit = total premium<br>- Max Loss = unlimited (large negative)<br>- 2 breakeven points | Yes |
| 2.3 | Bull Call Spread | 2 legs:<br>- BUY CE (ATM/lower)<br>- SELL CE (OTM/higher) | - Lower strike BUY, higher strike SELL<br>- All CMPs correct<br>- Max Profit = spread - debit<br>- Max Loss = net debit paid<br>- 1 breakeven point | Yes |
| 2.4 | Bear Put Spread | 2 legs:<br>- BUY PE (ATM/higher)<br>- SELL PE (OTM/lower) | - Higher strike BUY, lower strike SELL<br>- All CMPs correct<br>- Max Profit = spread - debit<br>- Max Loss = net debit paid<br>- 1 breakeven point | Yes |

## P/L Calculation Reference

### At Expiry Mode (Intrinsic Value)

```
For each leg:
  qty = lots * lot_size
  multiplier = 1 (BUY) or -1 (SELL)

  For each spot price:
    CE: option_value = max(0, spot - strike)
    PE: option_value = max(0, strike - spot)

    leg_pnl = (option_value - entry_price) * qty * multiplier

Total P/L at spot = sum of all leg P/Ls
Max Profit = max(total_pnl across all spots)
Max Loss = min(total_pnl across all spots)
```

### Current Mode (Black-Scholes)

Uses scipy-based Black-Scholes calculation with:
- Risk-free rate: 7%
- Default volatility: 15%
- Time to expiry: (expiry_date - target_date) / 365

## Pass/Fail Criteria

A test step **passes** only if ALL of the following are true:
1. UI updates without errors
2. CMP value matches backend API response (within 0.05 tolerance for rounding)
3. Auto-calculation API call completes successfully
4. P/L values are mathematically correct (spot-check at 2-3 spot prices)
5. Summary cards (Max Profit/Loss/Breakeven) are sensible for strategy type
6. Screenshot shows expected state

A test step **fails** if ANY of the above are not met.

## Timing Considerations

- **Outside market hours**: LTP returns last traded price (static). Test logic works.
- **During market hours**: WebSocket provides live updates. CMP may change between verification calls.
- **Recommendation**: Test outside market hours for reproducibility; verify WebSocket updates during market hours separately.

## Known Issues & Expected Behaviors

| Issue | Expected? | Notes |
|-------|-----------|-------|
| Short Straddle Max Loss shows small number instead of "Unlimited" | Yes | P/L grid uses finite spot range; displayed max loss is at range edge |
| CMP shows "-" initially after adding legs | Yes | Wait 2-3 seconds or click ReCalculate to fetch prices |
| "Unable to fetch instrument data" error | Intermittent | Usually resolves after clicking ReCalculate; check SmartAPI connection |
| Phase 1 test timeout on page load | Test issue | Not a code bug; retry or run Phase 2 only |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Add Row" button stays disabled | Wait for expiries to load (check network tab); refresh page if needed |
| All strategy legs have same strike | Bug was fixed 2026-01-14; ensure latest code is deployed |
| CMP values not updating | Click ReCalculate; check WebSocket connection (green dot in header) |
| Test fails with "strategy-page not found" | Page load race condition; increase timeout or retry |

## Related Files

- **Frontend View**: `frontend/src/views/StrategyBuilderView.vue`
- **Frontend Store**: `frontend/src/stores/strategy.js`
- **Strategy Types**: `frontend/src/constants/strategyTypes.js`
- **Backend Calculator**: `backend/app/services/pnl_calculator.py`
- **Backend Route**: `backend/app/api/routes/strategy.py`
- **E2E Page Object**: `tests/e2e/pages/StrategyBuilderPage.js`
- **E2E Specs**: `tests/e2e/specs/strategy/*.spec.js`

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-14 | 1.1 | Added Quick Run Commands, Fast Validation Checklist, Known Issues, Troubleshooting |
| 2026-01-14 | 1.0 | Initial test plan created |
