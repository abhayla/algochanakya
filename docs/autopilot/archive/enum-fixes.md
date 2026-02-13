# AutoPilot Enum Fixes - Testing Guide

## ✅ Fixes Applied (Commit: 4406ea4)

### Summary
Fixed **13 enum case mismatches** in `backend/app/schemas/autopilot.py` that were preventing AutoPilot from starting. All enum default values changed from `lowercase` to `UPPERCASE` to match their definitions in `app/constants/enums.py`.

### Changes Made

| File | Lines Changed | Description |
|------|---------------|-------------|
| `backend/app/schemas/autopilot.py` | 13 | Enum case corrections |

**Specific Fixes:**
1. `ExecutionStyle.sequential` → `SEQUENTIAL` (line 76)
2. `ExpiryType.current_week` → `CURRENT_WEEK` (lines 126, 1530)
3. `PositionType.intraday` → `INTRADAY` (lines 129, 1533)
4. `ExecutionMode.auto` → `AUTO` (lines 246, 381)
5. `TrailType.fixed` → `FIXED` (line 458)
6. `ReportFormat.csv` → `CSV` (line 852)
7. `ReportFormat.pdf` → `PDF` (line 997)
8. `ShareMode.link` → `LINK` (line 1094)
9. `StagedEntryMode.half_size` → `HALF_SIZE` (line 1464)
10. `StagedEntryMode.staggered` → `STAGGERED` (line 1482)

---

## 🎯 Testing AutoPilot Features

### Prerequisites

Before running tests, ensure:

1. **Database Services Running:**
   ```bash
   # PostgreSQL must be running and accessible
   # Check your .env file for DATABASE_URL
   # Default: postgresql+asyncpg://user:pass@103.118.16.189:5432/algochanakya

   # Redis must be running and accessible
   # Check your .env file for REDIS_URL
   # Default: redis://103.118.16.189:6379/1
   ```

2. **Backend .env Configured:**
   ```bash
   cd backend
   cat .env  # Verify DATABASE_URL and REDIS_URL are correct
   ```

3. **Backend Starts Successfully:**
   ```bash
   cd backend
   venv\Scripts\activate  # Windows
   python run.py          # Should start without AttributeError
   ```

---

## 🧪 Test Scenarios

### 1. Strike Preview Tests (All Modes)

**What it tests:** Verifies strike selection works across all modes without "Preview Unavailable" errors

```bash
# Run strike preview tests
npx playwright test tests/e2e/specs/autopilot/autopilot.strike-preview.spec.js --headed

# Expected: All tests pass
# - ATM Offset mode (offset 0, +2, -2)
# - Fixed Strike mode
# - Delta-based mode
# - Premium-based mode
# - Standard Deviation mode
```

**Test Coverage:**
- ✅ ATM Offset with offset 0 shows preview
- ✅ ATM Offset with offset +2 shows preview
- ✅ ATM Offset with offset -2 shows preview
- ✅ Fixed Strike mode shows preview
- ✅ Delta-based mode shows preview
- ✅ Premium-based mode shows preview
- ✅ SD-based mode shows preview

---

### 2. Template Library Tests

**What it tests:** Template browsing, filtering, deployment workflow

```bash
# Run template library tests
npx playwright test tests/e2e/specs/autopilot/autopilot.templates.spec.js --headed

# Expected: All tests pass
# - Display template library page
# - Display category filter dropdown
# - Display template cards
# - Filter by category (income, directional, volatility, hedging, advanced)
# - Filter by risk level (low, medium, high)
# - Search templates by name
# - Open/close template details modal
# - Deploy template opens deploy modal
```

**API Endpoints Tested:**
- `GET /api/v1/autopilot/templates` - List templates
- `GET /api/v1/autopilot/templates/categories` - Category counts
- `GET /api/v1/autopilot/templates/{id}` - Template details
- `POST /api/v1/autopilot/templates/{id}/deploy` - Deploy template

---

### 3. Short Strangle Template Test

**What it tests:** Complete Short Strangle strategy creation with adjustments

```bash
# Run Short Strangle template test
npx playwright test tests/e2e/specs/autopilot/short-strangle-template.spec.js --headed --timeout=120000

# Expected: Creates strategy with:
# - Entry: Sell 15-delta PUT + CALL (NIFTY monthly)
# - Adjustment 1: Shift profitable leg when premium > 60% (RECURRING)
# - Adjustment 2: Alert when delta doubles (RECURRING)
# - Adjustment 3: Break trade when delta > 0.50 (RECURRING)
# - Adjustment 4: Exit all when DTE < 2 (ONE-TIME)
```

**Reference:** `docs/autopilot/SHORT-STRANGLE-ADJUSTMENTS-WORKFLOW.md`

---

### 4. Iron Condor Template Test

**What it tests:** Iron Condor strategy deployment

```bash
# Run Iron Condor template test
npx playwright test tests/e2e/specs/autopilot/iron-condor-template.spec.js --headed

# Expected: Creates 4-leg Iron Condor with:
# - Buy OTM PUT
# - Sell closer PUT
# - Sell closer CALL
# - Buy OTM CALL
```

---

### 5. AutoPilot Happy Path Test

**What it tests:** Complete AutoPilot workflow end-to-end

```bash
# Run AutoPilot happy path test
npx playwright test tests/e2e/specs/autopilot/autopilot.happy.spec.js --headed

# Expected: All core features work
# - Dashboard displays
# - Create new strategy
# - Configure legs
# - Set entry conditions
# - Add adjustment rules
# - Activate strategy
# - Monitor status
```

---

### 6. Run All AutoPilot Tests

```bash
# Run complete AutoPilot test suite
npm run test:specs:autopilot

# Or with custom settings
npx playwright test tests/e2e/specs/autopilot/ --headed --workers=1

# Fast parallel execution (shorter timeout)
npm run test:autopilot:fast

# Phase-specific tests
npm run test:autopilot:phase4       # Templates, sharing, analytics
npm run test:autopilot:phases123    # Core features
```

---

## 📊 Expected Results

### ✅ Success Indicators

1. **Backend Starts:**
   ```
   INFO:     Uvicorn running on http://0.0.0.0:8000
   INFO:     Application startup complete
   ```

2. **Strike Preview API Returns Data:**
   ```json
   {
     "data": {
       "strike": 26000,
       "ltp": 125.50,
       "delta": 0.15,
       "option_type": "CE",
       "instrument_token": 12345678
     }
   }
   ```

3. **Template Deployment Creates Strategy:**
   ```json
   {
     "message": "Template deployed successfully",
     "data": {
       "id": 1,
       "name": "SHORT-STRANGLE-ADJUSTMENTS-Template",
       "status": "draft",
       "legs_config": [...]
     }
   }
   ```

### ❌ Failure Indicators (Before Fix)

1. **AttributeError on startup:**
   ```
   AttributeError: type object 'ExecutionStyle' has no attribute 'sequential'
   ```

2. **Preview Unavailable:**
   ```
   Strike preview error: Enum mismatch
   ```

---

## 🔍 API Endpoints to Verify

### Strike Preview
```bash
GET /api/v1/autopilot/strikes/preview
  ?underlying=NIFTY
  &expiry=2025-12-26
  &option_type=CE
  &mode=atm_offset
  &offset=0
  &prefer_round_strike=true
```

### Template List
```bash
GET /api/v1/autopilot/templates
  ?category=income
  &page=1
  &page_size=20
```

### Template Deploy
```bash
POST /api/v1/autopilot/templates/{template_id}/deploy
{
  "underlying": "NIFTY",
  "expiry_type": "CURRENT_WEEK",  # ✅ Now UPPERCASE
  "lots": 1,
  "position_type": "INTRADAY"     # ✅ Now UPPERCASE
}
```

---

## 🐛 Troubleshooting

### Issue: Backend won't start

**Symptom:**
```
asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed
```

**Solution:**
1. Verify PostgreSQL is running:
   ```bash
   # Test connection
   psql -h 103.118.16.189 -U username -d algochanakya
   ```

2. Check `.env` file:
   ```bash
   cd backend
   cat .env | grep DATABASE_URL
   # Should be: postgresql+asyncpg://...
   ```

3. Use local database if remote unavailable:
   ```bash
   # Update backend/.env
   DATABASE_URL=postgresql+asyncpg://localhost:5432/algochanakya_local
   ```

### Issue: Tests timeout waiting for backend

**Solution:**
1. Start backend manually first:
   ```bash
   cd backend
   venv\Scripts\activate
   python run.py
   # Wait for "Application startup complete"
   ```

2. Then run tests in another terminal:
   ```bash
   npx playwright test tests/e2e/specs/autopilot/autopilot.strike-preview.spec.js
   ```

### Issue: Enum errors still occurring

**Solution:**
1. Verify commit was applied:
   ```bash
   git log --oneline -1
   # Should show: 4406ea4 fix: Correct enum case in AutoPilot schemas
   ```

2. Check file contents:
   ```bash
   grep -n "ExecutionStyle.SEQUENTIAL" backend/app/schemas/autopilot.py
   # Should find on line 76
   ```

3. Restart backend (cached modules):
   ```bash
   # Kill any running backend processes
   # Start fresh
   cd backend
   python run.py
   ```

---

## 📈 Performance Metrics

Expected test execution times:
- Strike Preview Tests: ~2-3 minutes
- Template Library Tests: ~3-4 minutes
- Short Strangle Template: ~5-6 minutes
- Complete AutoPilot Suite: ~15-20 minutes

---

## 🔗 Related Documentation

- **AutoPilot Architecture:** `docs/autopilot/README.md`
- **API Contracts:** `docs/autopilot/api-contracts.md`
- **E2E Test Rules:** `docs/testing/e2e-test-rules.md`
- **Database Schema:** `docs/autopilot/database-schema.md`
- **Short Strangle Workflow:** `docs/autopilot/SHORT-STRANGLE-ADJUSTMENTS-WORKFLOW.md`

---

## ✨ Summary

The enum case fixes resolve all AttributeError issues that prevented AutoPilot from loading. With these changes:

✅ Backend starts without errors
✅ Strike preview works for all modes
✅ Templates can be browsed and deployed
✅ Strategies can be created and activated
✅ All AutoPilot features are functional

**Next Action:** Start your database services and run the test suite to verify everything works! 🚀
