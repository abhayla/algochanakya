# AngelOne Login Timeout Issue

## Issue: AngelOne Login Fails with "Failed to login" Error

**Date Resolved:** January 23, 2026
**Commit:** `e23306a`

---

## Symptoms

When clicking the "Angel One" button on the login page:
1. Button shows "Connecting..." for 10 seconds
2. Error appears: "Failed to login with Angel One. Make sure SmartAPI credentials are configured in Settings."
3. User is NOT redirected to dashboard
4. Browser console shows: `timeout of 10000ms exceeded`

---

## Root Cause

**Primary Issue:** Request timeout mismatch

AngelOne authentication with auto-TOTP generation takes **22-25 seconds** to complete, but the frontend axios instance has a default **10-second timeout**. The request is aborted before the backend finishes processing.

### Why AngelOne Auth Takes So Long

The backend performs these operations sequentially:
1. Fetch encrypted SmartAPI credentials from database
2. Decrypt PIN and TOTP secret using encryption utilities
3. **Generate time-based TOTP code** from secret
4. Authenticate with SmartAPI servers (network round-trip)
5. Exchange credentials for JWT token (network round-trip)
6. Fetch user profile from SmartAPI API (network round-trip)
7. Query database for existing user and broker connection
8. Create or update user record
9. Create or update broker connection record
10. Generate application JWT token
11. Attempt Redis session storage (optional, can timeout)

**Measured time:** 22.778 seconds (via `time curl`)

---

## Verification Steps

### 1. Check Backend is Running on Correct Port

```bash
curl http://localhost:8001/
# Should return: {"message":"Welcome to AlgoChanakya API",...}
```

If returns `{"message":"Welcome to KYBH-MVP",...}` - wrong backend is running.

### 2. Test AngelOne Endpoint Directly

```bash
curl -X POST http://localhost:8001/api/auth/angelone/login \
  -H "Content-Type: application/json"
```

Should return (in ~22 seconds):
```json
{
  "success": true,
  "token": "eyJhbGc...",
  "redirect_url": "http://localhost:5173/auth/callback?token=...",
  "user": {
    "id": "...",
    "broker_user_id": "MAAW1001",
    "name": "MAAW1001",
    "email": null
  }
}
```

### 3. Check Frontend Configuration

```bash
cat frontend/.env.local
# Should show:
# VITE_API_BASE_URL=http://localhost:8001
# VITE_WS_URL=ws://localhost:8001
```

**Common mistake:** `.env.local` pointing to `http://localhost:8005` or `http://localhost:8000`

### 4. Check Database Connection

Backend startup failure with:
```
asyncpg.exceptions.InvalidAuthorizationSpecificationError:
no pg_hba.conf entry for host "XXX.XXX.XXX.XXX"
```

**Solution:** Whitelist your IP in PostgreSQL server's `pg_hba.conf`

---

## The Fix

### File: `frontend/src/stores/auth.js`

**Before:**
```javascript
async function initiateAngelOneLogin() {
  angelOneLoading.value = true
  try {
    const response = await api.post('/api/auth/angelone/login')
    // ... rest of code
```

**After:**
```javascript
async function initiateAngelOneLogin() {
  angelOneLoading.value = true
  try {
    // AngelOne auth with auto-TOTP can take 20-30 seconds
    const response = await api.post('/api/auth/angelone/login', {}, {
      timeout: 35000  // 35 second timeout
    })
    // ... rest of code
```

**Key change:** Added explicit `timeout: 35000` (35 seconds) to the axios POST request.

---

## Configuration Issues Found

### 1. Frontend Port Configuration

**File:** `frontend/.env.local` (git-ignored)

**Issue:** Was pointing to wrong port
```env
# WRONG
VITE_API_BASE_URL=http://localhost:8005
VITE_WS_URL=ws://localhost:8005
```

**Fixed:**
```env
# CORRECT - Dev backend runs on 8001
VITE_API_BASE_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
```

### 2. Backend Not Running

**Symptom:** `curl http://localhost:8001/` returns connection refused or wrong app name

**Check:**
```bash
ps aux | grep python | grep run.py
# Should show: python run.py running in algochanakya/backend/
```

**Fix:**
```bash
cd backend/
source venv/bin/activate  # or venv\Scripts\activate on Windows
python run.py
# Wait 30 seconds for startup (downloads SmartAPI instruments)
```

---

## Related Files

| File | Purpose | Change Required |
|------|---------|-----------------|
| `frontend/src/stores/auth.js` | Auth state management | ✅ Added 35s timeout |
| `frontend/.env.local` | Local dev config | ⚠️ User must set to port 8001 |
| `frontend/src/services/api.js` | Axios instance | No change (default 10s timeout stays) |
| `backend/app/api/routes/auth.py` | AngelOne login endpoint | No change needed |

---

## Testing the Fix

### Manual Test

1. Start backend: `cd backend && python run.py`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to `http://localhost:5173/login`
4. Click "Angel One" button
5. Wait 20-25 seconds (button shows "Connecting...")
6. Should redirect to dashboard with user "MAAW1001" in header

### Automated Test

```bash
# From project root
npx playwright test tests/login.happy.spec.js --grep "AngelOne"
```

---

## Performance Optimization Opportunities

While the fix works, the 22-second login time is legitimately slow. Potential improvements:

1. **Cache TOTP Generation** - Pre-generate next TOTP code
2. **Parallel Operations** - Fetch profile while creating user record
3. **Database Connection Pooling** - Reduce query latency
4. **Skip Optional Operations** - Make Redis session storage truly optional
5. **WebSocket Pre-connection** - Start WebSocket while auth completes

**Current:** 22.8s
**Target:** <10s (would allow default 10s axios timeout)

However, these optimizations are lower priority since the 35s timeout fix resolves the user-facing issue.

---

## Related Issues

- **Backend startup failure:** Database IP whitelist issue (separate problem)
- **Redis timeout warning:** "Timeout connecting to server" - non-blocking, login still succeeds
- **WebSocket connection errors:** Double slash in URL (`ws://ws//localhost`) - separate issue

---

## Key Takeaways

1. **Always measure actual request time** before setting timeouts
   ```bash
   time curl -X POST http://localhost:8001/api/auth/angelone/login
   ```

2. **Frontend `.env.local` overrides `.env`** - always check local overrides first

3. **Auto-TOTP authentication is inherently slower** than OAuth redirects because:
   - OAuth: User waits on external site (time not measured by our app)
   - Auto-TOTP: Backend waits for SmartAPI (time measured and limited by our timeout)

4. **10-second default timeouts are reasonable** - only increase for specific endpoints that legitimately need more time

---

## Documentation Updates

- ✅ Updated `CLAUDE.md` - Added to Common Pitfalls
- ✅ Updated `CLAUDE.md` - Added `.env.local` configuration warning
- ✅ Updated `CLAUDE.md` - Added database connection troubleshooting
- ✅ Created this troubleshooting doc

---

## Commit Reference

```
commit e23306a
Author: Abhay + Claude Sonnet 4.5
Date:   Thu Jan 23 09:51:42 2026 +0530

    fix: Increase timeout for AngelOne login to 35 seconds

    AngelOne authentication with auto-TOTP generation takes 20-25 seconds
    to complete. The previous 10-second axios timeout caused the request
    to abort before completion, showing "Failed to login" error.

    Changes:
    - Set timeout to 35000ms (35s) for POST /api/auth/angelone/login
    - Added comment explaining why AngelOne auth needs longer timeout
    - Login now completes successfully and redirects to dashboard

    Root cause: SmartAPI auto-TOTP authentication process is legitimately
    slow (~22s measured) due to token generation, exchange, and profile fetch.
```
