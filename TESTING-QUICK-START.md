# Week 3 AI + AutoPilot Integration - Quick Start Testing Guide

**Purpose:** Fast-track validation of Week 3 implementation in 15 minutes
**Commit:** 542e039 (Core Implementation) + b9522c3 (Testing Checklist)
**Full Checklist:** See `docs/testing/week3-ai-autopilot-integration-checklist.md` for comprehensive testing

---

## 🚀 5-Minute Setup

### 1. Apply Migration (2 minutes)

```bash
cd backend
venv\Scripts\activate  # Windows - or: source venv/bin/activate (Linux/Mac)
alembic upgrade head
```

**✅ Success Check:** Look for `"Running upgrade 010 -> 011"`

---

### 2. Start Backend (1 minute)

```bash
# In backend/ directory (venv activated)
python run.py
```

**✅ Success Check:** `"Application startup complete"` with no errors

**Keep this terminal running**

---

### 3. Start Frontend (1 minute)

```bash
# New terminal
cd frontend
npm run dev
```

**✅ Success Check:** `"Local: http://localhost:5173/"`

**Keep this terminal running**

---

### 4. Quick Visual Test (1 minute)

1. Open browser: `http://localhost:5173/autopilot`
2. Login (DA1707 or your credentials)
3. **Look for AI Status Card** (5th summary card)
4. Should see one of:
   - Gray badge: "Disabled"
   - Blue badge: "Paper Trading"
   - Green badge: "Live Trading"

**✅ Success Check:** AI Status Card visible, no console errors (F12)

---

## 🎯 10-Minute Functional Tests

### Test A: AI Config Integration (3 minutes)

**Navigate to:** `http://localhost:5173/ai/settings`

**Configure:**
- ✅ Enable AI Trading
- ✅ Set Autonomy Mode: "Paper Trading"
- ✅ Base Lots: 1
- ✅ Position Sizing Mode: "Tiered"
- ✅ Max Lots Per Day: 6
- ✅ Max Strategies Per Day: 5
- ✅ Click "Save Configuration"

**Return to:** `http://localhost:5173/autopilot`

**✅ Success Check:**
- AI Status Card shows "Paper Trading" (blue badge)
- Shows "Lots Today: 0 / 6"
- Shows "Strategies Today: 0 / 5"
- Progress bars visible

---

### Test B: Position Sizing Calculation (5 minutes)

**Test HIGH Tier (85% confidence = 2.0x multiplier):**

#### Step 1: Create AI-deployed strategy via database

```sql
-- Connect to PostgreSQL and run:
INSERT INTO autopilot_strategies (
    user_id,
    name,
    description,
    status,
    underlying,
    expiry_type,
    lots,
    position_type,
    legs_config,
    entry_conditions,
    order_settings,
    risk_settings,
    schedule_config,
    trading_mode,
    ai_deployed,
    ai_confidence_score,
    ai_regime_type,
    ai_lots_tier
) VALUES (
    (SELECT id FROM users WHERE kite_user_id = 'DA1707' LIMIT 1),
    'Test AI Strategy - HIGH Tier',
    'Testing 85% confidence with 2.0x multiplier',
    'draft',
    'NIFTY',
    'current_week',
    1,  -- Base lots
    'intraday',
    '[{"id": "leg1", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": "atm", "strike_offset": 0, "quantity_multiplier": 1, "execution_order": 1}]'::jsonb,
    '{}'::jsonb,
    '{"order_type": "MARKET", "execution_style": "sequential"}'::jsonb,
    '{"max_loss": 5000, "profit_target": 3000}'::jsonb,
    '{"active_days": ["MON", "TUE", "WED", "THU", "FRI"], "start_time": "09:15", "end_time": "15:30"}'::jsonb,
    'paper',
    true,  -- AI deployed
    85.0,  -- HIGH tier confidence
    'RANGEBOUND',
    'HIGH'
);
```

#### Step 2: Check backend logs

**Look for line:**
```
INFO: AI Position Sizing: Strategy {id}, Confidence=85.0, Tier=HIGH, Multiplier=2.0x, Lots=2
```

#### Step 3: Verify in database

```sql
-- Check the strategy was created
SELECT id, name, ai_deployed, ai_confidence_score, ai_lots_tier, lots
FROM autopilot_strategies
WHERE ai_deployed = true
ORDER BY created_at DESC
LIMIT 1;

-- Expected: ai_confidence_score=85.0, ai_lots_tier='HIGH', lots=1 (base)
```

**✅ Success Check:**
- Backend logs show "Multiplier=2.0x, Lots=2"
- Strategy created in database with AI fields populated

---

### Test C: VIX Limit Enforcement (2 minutes)

**Set artificial VIX limit:**

Navigate to: `http://localhost:5173/ai/settings`

**Configure:**
- Max VIX to Trade: `10.0` (artificially low to trigger limit)
- Save configuration

**Try to activate the test strategy:**

```sql
-- Update strategy status to waiting
UPDATE autopilot_strategies
SET status = 'waiting'
WHERE ai_deployed = true
  AND name LIKE 'Test AI Strategy%'
ORDER BY created_at DESC
LIMIT 1;
```

**Wait 5-10 seconds for StrategyMonitor to process**

**Check backend logs:**
```
WARNING: AI limits exceeded for strategy {id}: VIX {XX.XX} exceeds max limit 10.0
```

**Check browser console (F12):**
Look for WebSocket message:
```javascript
{
  type: "alert",
  alert_type: "ai_limit",
  message: "AI Limit: VIX XX.XX exceeds max limit 10.00",
  ...
}
```

**✅ Success Check:**
- Strategy NOT deployed (remains in "waiting")
- Backend logs show VIX limit exceeded
- WebSocket alert received (check notifications bell icon)

---

## ✅ Success Criteria (All 3 Must Pass)

- ✅ **Setup Complete:** Migration applied, servers running, AI Status Card visible
- ✅ **Config Integration:** AI Settings save and display correctly in dashboard
- ✅ **Position Sizing OR VIX Limit:** At least one functional test passes

**If all 3 pass:** Week 3 core integration is WORKING! 🎉

---

## 🐛 Common Issues & Fixes

### Issue: Migration Fails

**Error:** `"FATAL: password authentication failed"`
**Fix:** Check `backend/.env` file, verify `DATABASE_URL` is correct

**Error:** `"revision 011 not found"`
**Fix:** Run `git pull` to ensure migration file exists

**Error:** `"column already exists"`
**Fix:** Migration already applied, run `alembic current` to check

---

### Issue: Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'app.services.ai.config_service'`
**Fix:** Ensure you pulled latest code, check `backend/app/services/ai/config_service.py` exists

**Error:** `ImportError: cannot import name 'AIConfigService'`
**Fix:** Restart Python interpreter, ensure virtual environment activated

---

### Issue: AI Status Card Not Showing

**Check:**
1. Open browser console (F12) - any errors?
2. Check Network tab - is `/api/v1/ai/config` endpoint returning 200?
3. Verify component imported in DashboardView.vue

**Fix:**
```bash
# Rebuild frontend
cd frontend
npm run build
npm run dev
```

---

### Issue: Position Sizing Not Working

**Check backend logs for:**
```
INFO: AI Position Sizing: Strategy {id}, Confidence=XX, Tier=XX, Multiplier=Xx, Lots=X
```

**If missing:**
- Verify `strategy.ai_deployed = true`
- Verify `strategy.ai_confidence_score` is set
- Check `ai_config.ai_enabled = true`

---

## 📊 Test Results Summary

**Fill in after testing:**

| Test | Status | Time | Notes |
|------|--------|------|-------|
| 1. Migration | ✅ / ❌ | ___ min | ______ |
| 2. Backend Start | ✅ / ❌ | ___ min | ______ |
| 3. Frontend Start | ✅ / ❌ | ___ min | ______ |
| 4. AI Status Card | ✅ / ❌ | ___ min | ______ |
| A. AI Config Integration | ✅ / ❌ | ___ min | ______ |
| B. Position Sizing | ✅ / ❌ | ___ min | ______ |
| C. VIX Limit | ✅ / ❌ | ___ min | ______ |

**Total Time:** ______ minutes

**Pass Rate:** ____ / 7 tests (___%)

---

## 🎯 Next Steps

### If All Tests Pass ✅

**Week 3 Core Integration: VERIFIED WORKING!**

You can now:
1. Mark Week 3 as COMPLETE (70% done)
2. Push to GitHub (if you have remote)
3. Proceed to Week 4:
   - Strategy Recommender service
   - Daily Scheduler (APScheduler)
   - E2E test automation
4. Or: Run full test suite (`docs/testing/week3-ai-autopilot-integration-checklist.md`)

---

### If Some Tests Fail ❌

1. Note which tests failed
2. Check "Common Issues & Fixes" section above
3. Review backend logs for errors
4. Check browser console (F12) for frontend errors
5. If stuck, create GitHub issue with:
   - Which test failed
   - Error messages (backend + frontend)
   - Screenshots (if visual issue)

---

### Optional: Full Test Suite

For comprehensive testing (30 test cases, ~2-3 hours):

See: `docs/testing/week3-ai-autopilot-integration-checklist.md`

Includes:
- All 4 position sizing tiers (SKIP, LOW, MEDIUM, HIGH)
- All 8 AI limit validations
- Edge cases and performance testing
- Cross-browser compatibility
- Regression testing

---

## 📝 Database Verification Queries

**Quick verification of AI metadata:**

```sql
-- Check if AI columns exist
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'autopilot_strategies'
  AND column_name LIKE 'ai_%';

-- Check AI-deployed strategies
SELECT id, name, ai_deployed, ai_confidence_score, ai_lots_tier
FROM autopilot_strategies
WHERE ai_deployed = true;

-- Check orders with AI metadata
SELECT o.id, o.quantity, o.ai_sizing_mode, o.ai_tier_multiplier, s.ai_confidence_score
FROM autopilot_orders o
JOIN autopilot_strategies s ON o.strategy_id = s.id
WHERE s.ai_deployed = true
ORDER BY o.created_at DESC
LIMIT 10;

-- Check AI config for user
SELECT ai_enabled, autonomy_mode, sizing_mode, base_lots, max_lots_per_day
FROM ai_user_config
WHERE user_id = (SELECT id FROM users WHERE kite_user_id = 'DA1707');
```

---

## 🎉 What You're Testing

**Week 3 Implementation (613 lines of code):**

✅ **Backend Integration:**
- Confidence-based position sizing (4 tiers)
- 8 AI limit validations
- Paper/Live mode enforcement
- Full audit trail

✅ **Frontend Integration:**
- AI Status Card component
- Real-time progress bars
- Color-coded status indicators
- Navigation to AI Settings

✅ **Database:**
- Migration 011 with 7 AI fields
- Performance indexes

**This Quick Start validates the critical path is working!**

---

## ⏱️ Time Investment

- **Quick Start (this guide):** 15 minutes
- **Full Checklist:** 2-3 hours
- **Recommended:** Start with Quick Start, run full suite later

---

## 📞 Support

**If you encounter issues:**

1. Check "Common Issues & Fixes" above
2. Review backend logs: Look for errors in terminal where `python run.py` is running
3. Check browser console: Press F12, look for red errors
4. Verify git commits: `git log -3 --oneline` should show commits 542e039 and b9522c3

**Created by:** Claude Code Week 3 Implementation
**Date:** 2025-12-25
**Version:** 1.0

---

**Happy Testing! 🚀**
