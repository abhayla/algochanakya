# Quick Test Guide - StrikeLadder Integration

**Status:** ✅ Ready for Testing
**Date:** December 17, 2025

## Prerequisites

1. **Backend Running:**
   ```bash
   cd backend
   python run.py
   ```
   Expected: Server running on http://localhost:8000

2. **Frontend Running:**
   ```bash
   cd frontend
   npm run dev
   ```
   Expected: Dev server on http://localhost:5173

3. **Login:** You must be logged in with a valid session

---

## Testing Steps

### 1. Navigate to AutoPilot Strategy Builder

```
URL: http://localhost:5173/autopilot/strategies/new
```

### 2. Fill Basic Information

- **Strategy Name:** "Test StrikeLadder"
- **Underlying:** Select "NIFTY" (or any available)
- **Expiry Type:** Current Week
- **Lots:** 1

### 3. Add a Leg

Click **"+ Add Row"** button at the bottom

### 4. Configure Leg Details

- **Action:** SELL
- **Expiry:** Select any available expiry
- **Type:** CE

### 5. Open StrikeLadder

**Look for the green grid icon button** next to the strike mode dropdown:

```
[Strike Mode Dropdown ▼] [📊 Green Button]
```

**Click the green grid button**

### 6. Verify StrikeLadder Modal Opens

**Expected:**
- Modal overlay appears with dark background
- Modal shows "Strike Ladder - NIFTY" in header
- Strike table displays with columns:
  - CE Δ | CE LTP | Strike | PE LTP | PE Δ | Select
- **IMPORTANT:** Check the browser console for any errors
- **Check:** Spot price should be fetched from API (not hardcoded 24200)

### 7. Test Strike Selection

- Browse through strikes
- Click on **CE** or **PE** button in any row
- **Expected:**
  - Modal closes automatically
  - Strike is populated in the leg row
  - Entry price is filled with LTP

### 8. Test Multiple Legs

- Add another leg (click "+ Add Row")
- Open strike ladder for the second leg
- Select a different strike
- **Expected:** Both legs have different strikes

---

## What to Check

### ✅ Visual Checks

- [ ] Modal opens without flash/flicker
- [ ] Modal is centered on screen
- [ ] Modal has proper shadow and overlay
- [ ] Close button (×) works
- [ ] Clicking outside modal closes it
- [ ] Grid button is visible and green
- [ ] Strike table is readable
- [ ] ATM row is highlighted

### ✅ Data Checks

- [ ] **Spot Price:** Open browser DevTools → Network tab
  - Look for request to `/api/v1/autopilot/spot-price/NIFTY`
  - Should return status 200
  - Response should have `ltp`, `change`, `change_pct`
- [ ] Strike values are realistic (e.g., 24000, 24050, 24100...)
- [ ] Delta values are between 0 and 1
- [ ] LTP values are positive numbers

### ✅ Functionality Checks

- [ ] Clicking CE button selects CE strike
- [ ] Clicking PE button selects PE strike
- [ ] Selected strike appears in leg row
- [ ] Entry price is populated
- [ ] Modal closes after selection
- [ ] Multiple legs work independently

### ✅ Error Handling

**Test 1:** Open ladder without selecting underlying
- **Expected:** Should show underlying from strategy (NIFTY/BANKNIFTY)

**Test 2:** Open ladder without selecting expiry
- **Expected:** Should show expiry from leg (if selected)

**Test 3:** Disconnect network and open ladder
- **Expected:** Should fallback to approximate spot price (24200 for NIFTY)

---

## Common Issues & Solutions

### Issue 1: Modal Doesn't Open

**Symptoms:** Clicking grid button does nothing

**Check:**
1. Open browser console (F12)
2. Look for JavaScript errors
3. Check if `openStrikeLadder` function is defined

**Fix:** Verify AutoPilotLegRow.vue emits `open-strike-ladder` event

### Issue 2: Spot Price is Always 24200

**Symptoms:** Spot price doesn't change regardless of underlying

**Check:**
1. Open Network tab in DevTools
2. Look for `/api/v1/autopilot/spot-price/` request
3. Check if request succeeds (200) or fails (401/500)

**Possible causes:**
- Backend not running
- JWT token expired (need to re-login)
- Kite Connect API key not configured

**Fix:** Restart backend, check `.env` file has `KITE_API_KEY` and `KITE_API_SECRET`

### Issue 3: StrikeLadder Shows Mock Data

**Expected:** StrikeLadder currently uses mock data (this is OK for now)

**Future work:** Connect StrikeLadder to real option chain API

### Issue 4: 401 Unauthorized

**Symptoms:** API requests fail with 401 status

**Fix:**
1. Logout and login again
2. Check JWT token in localStorage
3. Restart frontend dev server

---

## API Endpoints Used

### 1. Spot Price Endpoint

```
GET /api/v1/autopilot/spot-price/{underlying}

Response:
{
  "message": "Spot price for NIFTY retrieved successfully",
  "data": {
    "symbol": "NIFTY",
    "ltp": 24187.50,
    "change": -12.30,
    "change_pct": -0.05,
    "timestamp": "2025-12-17T10:30:00"
  },
  "timestamp": "2025-12-17T10:30:00"
}
```

**Test in browser console:**
```javascript
fetch('/api/v1/autopilot/spot-price/NIFTY', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
})
.then(r => r.json())
.then(console.log)
```

---

## Success Criteria

**Phase 1.5 is successful if:**

✅ Modal opens when grid button clicked
✅ Spot price is fetched from API (not hardcoded)
✅ Strike ladder displays (even with mock data)
✅ Clicking CE/PE button populates leg
✅ Modal closes after selection
✅ No console errors
✅ Multiple legs work independently
✅ Fallback works when API fails

---

## Browser DevTools Tips

### Console Tab
- Check for errors (red text)
- Check for warnings (yellow text)
- Look for "Error fetching spot price" messages

### Network Tab
- Filter by "Fetch/XHR"
- Look for `/spot-price/` requests
- Check request/response headers and body
- Verify status codes (200 = success, 401 = unauthorized, 500 = server error)

### Vue DevTools (if installed)
- Check component tree
- Verify `showStrikeLadder` is true when modal open
- Check `currentSpotPrice` value
- Verify `currentLegIndex` is set correctly

---

## Next Steps After Testing

### If Tests Pass ✅

1. Mark Phase 1.5 as complete
2. Update documentation with test results
3. Proceed to Phase 2 (Premium Monitoring)

### If Tests Fail ❌

1. Document specific failures in GitHub issue
2. Check error messages in console
3. Verify API endpoints are accessible
4. Test with different underlyings (NIFTY, BANKNIFTY)
5. Report findings with screenshots

---

## Quick Smoke Test (1 minute)

```bash
# 1. Start backend
cd backend && python run.py

# 2. Start frontend (new terminal)
cd frontend && npm run dev

# 3. Open browser
# URL: http://localhost:5173/autopilot/strategies/new

# 4. Add leg → Click grid button → Modal should open

# 5. Check console → No errors? ✅ Success!
```

---

**Tester:** _________________
**Date:** _________________
**Result:** ⬜ Pass  ⬜ Fail  ⬜ Partial

**Notes:**
_______________________________________________
_______________________________________________
_______________________________________________
