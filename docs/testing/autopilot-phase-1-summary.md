# Phase 1 Testing Summary

## Quick Start Guide

### 1. Backend Testing

```bash
# From project root
cd backend

# Test imports (check for syntax errors)
python -c "from app.services.order_executor import OrderExecutor; print('✓ Imports OK')"

# Start backend
python run.py

# In another terminal, run test script
python test_phase1_strike_selection.py
```

### 2. Frontend Testing

```bash
# From project root
cd frontend

# Start dev server
npm run dev

# Open browser
# Navigate to http://localhost:5173/autopilot/strategies/new
```

---

## What to Test

### ✅ Backend (5 minutes)

1. **Run test script:**
   ```bash
   cd backend
   python test_phase1_strike_selection.py
   ```

2. **Manual API test with curl:**
   ```bash
   # Replace YOUR_TOKEN with actual JWT
   curl "http://localhost:8000/api/v1/autopilot/strikes/preview?underlying=NIFTY&expiry=2024-12-26&option_type=CE&mode=delta_based&target_delta=0.30" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

### ✅ Frontend (10 minutes)

1. **Test StrikeSelector Component:**
   - Navigate to AutoPilot → Create Strategy
   - Add a leg
   - Switch between strike modes (Delta, Premium, SD)
   - Click quick-select presets
   - Watch preview panel update

2. **Test StrikeLadder Component:**
   - Click "Open Strike Ladder" (if button exists)
   - OR check if ladder is integrated in leg configuration
   - Filter strikes by delta range
   - Click CE/PE buttons to select strikes

### ✅ Integration (5 minutes)

1. **Create a strategy with delta-based strikes:**
   - Add 2 legs: SELL CE 0.30Δ, SELL PE 0.30Δ
   - Verify strikes are selected correctly
   - Check if preview matches actual strikes

---

## Known Issues to Watch For

### Potential Issue #1: Missing Kite Client Dependency

**Symptom:** `get_kite_client` not found error in API endpoint

**Fix:** Check that `get_kite_client` is defined in `app/utils/dependencies.py`

**Quick check:**
```bash
cd backend
grep -r "def get_kite_client" app/utils/
```

### Potential Issue #2: Frontend Axios Not Configured

**Symptom:** Preview API call fails with network error

**Fix:** Ensure `this.$axios` is configured in Vue app

**Check:** `frontend/src/services/api.js` should export configured axios instance

### Potential Issue #3: StrikeLadder Not Integrated

**Symptom:** Can't find "Open Strike Ladder" button

**Status:** StrikeLadder is a standalone component - needs to be integrated into Strategy Builder view

**Next step:** Add StrikeLadder modal/drawer to `StrategyBuilderView.vue`

---

## Quick Verification Checklist

**Before testing, verify:**
- [ ] Backend server is running (`python run.py`)
- [ ] Frontend dev server is running (`npm run dev`)
- [ ] You have a valid JWT token (login first)
- [ ] Database is up and running
- [ ] Kite Connect credentials are configured (if testing with real data)

**After testing, check:**
- [ ] No console errors in browser
- [ ] No backend errors in terminal
- [ ] API returns 200 status for valid requests
- [ ] Preview panel shows real data
- [ ] Strike selection modes switch correctly

---

## Test Results Template

```
## Phase 1 Test Results

**Date:** YYYY-MM-DD
**Tester:** Your Name
**Environment:** Local / Staging / Production

### Backend Tests
- [ ] ✅ Imports work
- [ ] ✅ API endpoint responds
- [ ] ✅ Delta mode works
- [ ] ✅ Premium mode works
- [ ] ✅ SD mode works
- [ ] ✅ Error handling works

### Frontend Tests
- [ ] ✅ StrikeSelector renders
- [ ] ✅ Mode switching works
- [ ] ✅ Presets work
- [ ] ✅ Preview updates
- [ ] ✅ API integration works

### Integration Tests
- [ ] ✅ End-to-end flow works
- [ ] ✅ Leg added with correct strike
- [ ] ✅ Multiple legs work

### Issues Found
1. [Issue description]
2. [Issue description]

### Overall Status
- [ ] ✅ Ready for Phase 2
- [ ] ⚠️ Minor fixes needed
- [ ] ❌ Major issues found
```

---

## Troubleshooting

### Issue: "StrikeFinderService not found"

**Solution:**
```bash
# Check if file exists
ls backend/app/services/strike_finder_service.py

# If missing, the service already exists in your codebase
# No action needed - we're using existing service
```

### Issue: "Preview shows mock data"

**Cause:** Frontend is calling API but API returns mock/cached data

**Solution:** Check backend logs to see if StrikeFinderService is being called

### Issue: "Cannot read property 'data' of undefined"

**Cause:** API response format mismatch

**Solution:** Check actual API response structure:
```javascript
console.log('API Response:', response)
console.log('Data:', response.data)
console.log('Inner Data:', response.data.data)
```

---

## Next Steps After Testing

**If all tests pass ✅:**
- Mark Phase 1 as complete
- Move to Phase 2 (Premium Monitoring)
- Document any minor improvements for later

**If tests fail ❌:**
- Document specific failures
- Create fix tasks
- Re-test after fixes

---

**Full Testing Guide:** See `docs/autopilot/Phase-1-Testing-Guide.md`
