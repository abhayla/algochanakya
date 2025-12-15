# Fix AutoPilot Strike Finder Errors

**Date:** 2025-12-15
**Status:** Ready for Implementation

## Problem Summary
All 4 strike finder methods in AutoPilot Strategy Builder are failing:
1. **Delta Range** - "Error finding strike"
2. **Premium Range** - "Error finding strike"
3. **Standard Deviation** - "Not Found"
4. **Expected Move** - "Not Found"

Additionally, the **Expected Move Range display** shows stale values (23,991 - 25,009) instead of current values based on live spot price (26,027.3).

---

## Root Cause Analysis

| Issue | Root Cause | Type |
|-------|------------|------|
| Expected Move Range stale | Frontend uses hardcoded spot (24,500), IV (15%), DTE (7) | Frontend bug |
| Delta Range error | **Frontend/Backend mismatch** - Backend returns array of objects, frontend expects array of numbers | Bug |
| Premium Range error | **Same as Delta Range** - Frontend processes response incorrectly | Bug |
| Standard Deviation "Not Found" | **API endpoint missing** - frontend calls `/strike-by-sd/` but it doesn't exist | Missing endpoint |
| Expected Move "Not Found" | **API endpoint missing** - frontend calls `/strike-by-expected-move/` but it doesn't exist | Missing endpoint |

---

## Files to Modify

### Backend
1. `backend/app/api/v1/autopilot/option_chain.py` - Add 3 missing endpoints

### Frontend
1. `frontend/src/components/autopilot/builder/AutoPilotLegRow.vue` - Fix 4 strike finder functions
2. `frontend/src/components/autopilot/builder/AutoPilotLegsTable.vue` - Fix Expected Move Range display

---

## Implementation Plan

### Step 1: Add Missing Backend API Endpoints

**File:** `backend/app/api/v1/autopilot/option_chain.py`

Add 3 new endpoints:

```python
# 1. Strike by Standard Deviation
@router.get("/strike-by-sd/{underlying}/{expiry}")
async def find_strike_by_sd(
    underlying: str,
    expiry: date,
    option_type: str = Query(..., regex="^(CE|PE)$"),
    sd_multiplier: float = Query(..., ge=0.5, le=3.0),
    prefer_round_strike: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """Find strike at X standard deviations from ATM."""
    service = StrikeFinderService(kite, db)
    result = await service.find_strike_by_standard_deviation(
        underlying=underlying.upper(),
        expiry=expiry,
        option_type=option_type.upper(),
        standard_deviations=sd_multiplier,
        prefer_round_strike=prefer_round_strike
    )
    if not result:
        raise HTTPException(404, "No strike found for this SD")
    return result

# 2. Strike by Expected Move
@router.get("/strike-by-expected-move/{underlying}/{expiry}")
async def find_strike_by_expected_move(
    underlying: str,
    expiry: date,
    option_type: str = Query(..., regex="^(CE|PE)$"),
    position: str = Query(..., regex="^(above|below)$"),
    prefer_round_strike: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """Find strike outside expected move range."""
    service = StrikeFinderService(kite, db)
    result = await service.find_strike_by_expected_move(
        underlying=underlying.upper(),
        expiry=expiry,
        option_type=option_type.upper(),
        outside=True,
        outside_sd=1.0,
        prefer_round_strike=prefer_round_strike
    )
    if not result:
        raise HTTPException(404, "No strike found outside expected move")
    return result

# 3. Expected Move Range (for display)
@router.get("/expected-move-range/{underlying}/{expiry}")
async def get_expected_move_range(
    underlying: str,
    expiry: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """Get expected move range for display."""
    from app.services.expected_move_service import ExpectedMoveService
    service = ExpectedMoveService(kite, db)
    result = await service.get_expected_move_range(underlying.upper(), expiry)
    return result
```

---

### Step 2: Fix Delta/Premium Range Strike Finding

**Root Cause:** Frontend/Backend data format mismatch

**Backend returns (line 549-569 of strike_finder_service.py):**
```python
result.append({
    'strike': opt['strike'],           # Number
    'tradingsymbol': opt['tradingsymbol'],
    'instrument_token': opt['instrument_token'],
    'ltp': opt.get('ltp'),
    'delta': opt.get('delta'),
    'iv': opt.get('iv'),
})
```

**Frontend expects (line 147-160 of AutoPilotLegRow.vue):**
```javascript
let strikes = response.data.strikes  // Frontend thinks this is [25000, 25100, 25200]
const roundStrikes = strikes.filter(s => s % 100 === 0)  // FAILS - s is an object!
const selectedStrike = strikes[0]  // Gets object, not number
emit('update', props.index, { strike_price: selectedStrike })  // Passes object, expects number
```

**Fix (Recommended):**

**File:** `frontend/src/components/autopilot/builder/AutoPilotLegRow.vue`

```javascript
// Fix lines 147-160 for Delta Range
if (response.data.strikes && response.data.strikes.length > 0) {
  let strikes = response.data.strikes

  // Apply round strike preference if enabled
  if (props.leg.prefer_round_strike) {
    const roundStrikes = strikes.filter(s => s.strike % 100 === 0)  // s.strike, not s
    if (roundStrikes.length > 0) {
      strikes = roundStrikes
    }
  }

  // Select the first (closest) strike - extract strike number from object
  const selected = strikes[0]
  emit('update', props.index, {
    strike_price: selected.strike,      // Extract number from object
    entry_price: selected.ltp,          // Auto-populate entry price
    instrument_token: selected.instrument_token,
    tradingsymbol: selected.tradingsymbol
  })
  strikeSearchError.value = ''
}

// Apply same fix to Premium Range (lines 215-228)
```

---

### Step 3: Fix Expected Move Range Display

**File:** `frontend/src/components/autopilot/builder/AutoPilotLegsTable.vue`

**Current code (lines 137-159):** Uses hardcoded values
```javascript
const spotPrices = {
  'NIFTY': 24500,  // HARDCODED - stale!
  ...
}
const iv = 0.15  // HARDCODED
const dte = 7    // HARDCODED
```

**Fix:** Fetch from backend API

```javascript
// Add to script setup
const expectedMoveData = ref({ lower: 0, upper: 0 })

// Fetch expected move range when underlying or expiry changes
watch(
  () => [store.builder.strategy.underlying, store.builder.expiry],
  async ([underlying, expiry]) => {
    if (underlying && expiry) {
      try {
        const response = await api.get(
          `/api/v1/autopilot/option-chain/expected-move-range/${underlying}/${expiry}`
        )
        expectedMoveData.value = {
          lower: response.data.lower_bound,
          upper: response.data.upper_bound
        }
      } catch (error) {
        console.error('Error fetching expected move:', error)
      }
    }
  },
  { immediate: true }
)

// Update formatExpectedMove to use API data
const formatExpectedMove = (position) => {
  if (position === 'lower') {
    return Math.round(expectedMoveData.value.lower).toLocaleString()
  } else {
    return Math.round(expectedMoveData.value.upper).toLocaleString()
  }
}
```

---

### Step 4: Update SD/EM Strike Finders

**File:** `frontend/src/components/autopilot/builder/AutoPilotLegRow.vue`

Ensure `findStrikeBySD` and `findStrikeByEM` handle the response correctly and auto-populate entry price:

```javascript
// After finding strike, also populate entry price
if (response.data.strike) {
  emit('update', props.index, {
    strike_price: response.data.strike,
    entry_price: response.data.ltp,           // Auto-populate entry
    instrument_token: response.data.instrument_token,
    tradingsymbol: response.data.tradingsymbol
  })
}
```

---

## Testing Checklist

After implementation:
- [ ] Delta Range: Enter 0.1 - 0.33 delta, click Find → Should populate strike + entry
- [ ] Premium Range: Enter 1 - 20 premium, click Find → Should populate strike + entry
- [ ] Standard Deviation: Select 2 SD, click Find → Should populate strike + entry
- [ ] Expected Move: Select "Above EM", click Find → Should populate strike + entry
- [ ] Expected Move Range display → Should show current values based on live spot price

---

## Execution Order

1. **Add backend endpoints** (Step 1)
2. **Fix Delta/Premium Range frontend** (Step 2)
3. **Fix Expected Move Range display** (Step 3)
4. **Update SD/EM strike finders** (Step 4)
5. **Test all 4 methods**

## Files Summary

| File | Changes |
|------|---------|
| `backend/app/api/v1/autopilot/option_chain.py` | Add 3 new endpoints |
| `frontend/src/components/autopilot/builder/AutoPilotLegRow.vue` | Fix 4 strike finder functions |
| `frontend/src/components/autopilot/builder/AutoPilotLegsTable.vue` | Fix Expected Move Range display |
