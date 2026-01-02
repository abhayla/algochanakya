# Zerodha OAuth Login Issues - Troubleshooting Guide

## Overview

This document covers common issues with Zerodha/Kite OAuth login flow in AlgoChanakya, their root causes, and step-by-step resolution procedures.

---

## Issue #1: Timeout Waiting for Kite Login Page

### Symptoms
```
TimeoutError: page.waitForURL: Timeout 15000ms exceeded.
waiting for navigation to "**/kite.zerodha.com/**" until "load"
```

The E2E test clicks the "Login with Zerodha" button but the browser never navigates to `kite.zerodha.com`.

### Root Causes

| Cause | Likelihood | How to Verify |
|-------|------------|---------------|
| CORS blocking API request | High | Browser console shows CORS error |
| Backend not running | Medium | `curl http://localhost:8000/api/health` fails |
| Kite API credentials invalid | Medium | Login endpoint returns error |
| Frontend not calling API | Low | No network request in DevTools |

### Resolution Steps

#### Step 1: Verify Backend is Running
```bash
curl http://localhost:8000/api/health
```
**Expected:** `{"status":"healthy","database":"connected","redis":"connected"}`

If not running:
```bash
cd backend
./venv/Scripts/activate   # Windows
source venv/bin/activate  # Linux/Mac
python run.py
```

#### Step 2: Test Login Endpoint Directly
```bash
curl http://localhost:8000/api/auth/zerodha/login
```
**Expected:** `{"login_url":"https://kite.zerodha.com/connect/login?api_key=...","message":"..."}`

If error, check Kite API credentials in `backend/.env`.

#### Step 3: Check CORS Configuration
```bash
curl -I -H "Origin: http://localhost:5173" http://localhost:8000/api/auth/zerodha/login
```
**Expected headers:**
```
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Credentials: true
```

If missing, see [Issue #2: CORS Blocking Requests](#issue-2-cors-blocking-requests).

---

## Issue #2: CORS Blocking Requests

### Symptoms
Browser console shows:
```
Access to XMLHttpRequest at 'http://localhost:8000/api/auth/zerodha/login'
from origin 'http://localhost:5173' has been blocked by CORS policy
```

### Root Cause

The backend CORS middleware doesn't include the frontend's origin. This commonly happens when:
- Frontend runs on a different port than expected
- CORS configuration uses explicit origins list that's incomplete

### Resolution

#### Option A: Use Regex Pattern (Recommended)

Edit `backend/app/main.py`:

```python
# CORS middleware - use allow_origin_regex for more flexible matching
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",  # Allow any localhost port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Option B: Explicit Origins List

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:5174",  # Vite fallback
        "http://localhost:3000",  # Alternative
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**After changing:** Restart the backend server.

### Quick Diagnosis: Test CORS Preflight

The browser sends an OPTIONS preflight request before actual API calls. If this fails, CORS is broken.

```bash
# Test CORS preflight
curl -s -X OPTIONS \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  http://localhost:8000/api/auth/zerodha/login \
  -D - -o /dev/null 2>&1 | grep -E "HTTP|access-control"
```

**Good output (CORS working):**
```
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:5173
access-control-allow-credentials: true
```

**Bad output (CORS broken - likely stale process):**
```
HTTP/1.1 405 Method Not Allowed
```

If you see `405 Method Not Allowed` on OPTIONS requests, this typically indicates a **stale backend process** is running with old configuration. The CORS middleware isn't properly handling preflight requests. See [Issue #5: Multiple Backend Processes](#issue-5-multiple-backend-processes-with-stale-config) to kill stale processes and restart fresh.

---

## Issue #3: Callback Redirects to Wrong Port

### Symptoms
After successful Kite login and TOTP entry:
```
Request failed: http://localhost:5174/auth/callback?token=... - net::ERR_CONNECTION_REFUSED
```

The callback URL uses port `5174` but frontend runs on `5173`.

### Root Cause

The `FRONTEND_URL` environment variable in `backend/.env` has the wrong port number. The backend uses this to construct the OAuth callback redirect URL.

**Code location:** `backend/app/api/routes/auth.py:155`
```python
url=f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}"
```

### Resolution

#### Step 1: Check Current Frontend Port
```bash
# Find what port the frontend is using
netstat -ano | findstr "LISTENING" | findstr "517"
```

Or check the Vite output when starting:
```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

#### Step 2: Update Backend Environment

Edit `backend/.env`:
```env
# Ensure this matches your frontend port
FRONTEND_URL=http://localhost:5173
```

#### Step 3: Restart Backend

**Critical:** You must restart the backend for environment changes to take effect.

```powershell
# Windows - Kill all Python processes
Get-Process python* | Stop-Process -Force

# Then restart
cd backend
./venv/Scripts/python.exe run.py
```

```bash
# Linux/Mac
pkill -f "python run.py"
cd backend && python run.py
```

### Verification
```bash
# After restart, the callback should redirect to correct port
# Test by completing OAuth flow in browser
```

---

## Issue #4: Kite Redirect URL Mismatch

### Symptoms
After clicking "Login with Zerodha", Kite shows an error page or redirects fail.

### Root Cause

The redirect URL configured in Kite Developer Console doesn't match `KITE_REDIRECT_URL` in `backend/.env`.

### Resolution

#### Step 1: Check Backend Configuration
```bash
# View current setting
grep KITE_REDIRECT_URL backend/.env
```

#### Step 2: Verify Kite Dashboard
1. Go to https://kite.trade (Kite Connect Developer Console)
2. Navigate to your app settings
3. Check "Redirect URL" field

#### Step 3: Ensure They Match

**For local development:**
```env
KITE_REDIRECT_URL=http://localhost:8000/api/auth/zerodha/callback
```

**For production:**
```env
KITE_REDIRECT_URL=https://yourdomain.com/api/auth/zerodha/callback
```

**Both must match exactly** - protocol, host, port, and path.

---

## Issue #5: Multiple Backend Processes with Stale Config

### Symptoms
- Environment changes don't take effect after restart
- Port 8000 shows multiple processes listening
- Callback still uses old FRONTEND_URL

### Root Cause

Multiple Python processes are running, some with cached old environment variables. Only killing the "new" process leaves old ones serving requests.

### Diagnosis
```powershell
# Windows
netstat -ano | findstr ":8000" | findstr LISTENING

# Shows multiple PIDs:
# TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    7636
# TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    5684
```

### Resolution

#### Windows (PowerShell)
```powershell
# Kill ALL Python processes
Get-Process python* | Stop-Process -Force

# Verify port is free
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
# Should return nothing or error

# Start fresh
cd backend
./venv/Scripts/python.exe run.py
```

#### Linux/Mac
```bash
# Kill all Python processes running run.py
pkill -f "python run.py"

# Or kill by port
lsof -ti:8000 | xargs kill -9

# Verify
lsof -i:8000
# Should return nothing

# Start fresh
cd backend && python run.py
```

---

## Issue #6: Kite Broker Token Expired

### Symptoms
- E2E tests fail even with valid JWT
- Auth state validation fails with "Kite broker token is expired or invalid"
- Tests worked yesterday but fail today

### Root Cause

Kite access tokens expire daily around **6 AM IST**. The stored auth state has a valid JWT but expired Kite broker token.

### Resolution

The E2E global-setup.js handles this automatically by:
1. Validating both JWT and Kite broker token
2. If either is invalid, performing fresh login

If issues persist:
```bash
# Delete auth state files to force fresh login
rm tests/config/.auth-state.json
rm tests/config/.auth-token

# Run tests - will prompt for fresh login
npm test
```

---

## Authentication Flow Reference

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ZERODHA OAUTH FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. User clicks "Login with Zerodha"                                        │
│     └─► Frontend: LoginView.vue → authStore.initiateZerodhaLogin()          │
│                                                                              │
│  2. Frontend calls GET /api/auth/zerodha/login                              │
│     └─► Backend: auth.py:19-42 generates Kite login URL                     │
│                                                                              │
│  3. Backend returns { login_url: "https://kite.zerodha.com/connect/..." }   │
│                                                                              │
│  4. Frontend redirects: window.location.href = login_url                    │
│     └─► User sees Kite login page                                           │
│                                                                              │
│  5. User enters credentials + TOTP on Kite                                  │
│                                                                              │
│  6. Kite redirects to: KITE_REDIRECT_URL?request_token=xxx                  │
│     └─► Backend: /api/auth/zerodha/callback (auth.py:45-165)                │
│                                                                              │
│  7. Backend exchanges request_token for access_token via Kite API           │
│     └─► Creates/updates user in database                                    │
│     └─► Generates JWT token                                                 │
│     └─► Stores Kite access_token in Redis                                   │
│                                                                              │
│  8. Backend redirects to: FRONTEND_URL/auth/callback?token=jwt              │
│     └─► Frontend: AuthCallback.vue saves token to localStorage              │
│                                                                              │
│  9. Frontend redirects to /dashboard                                        │
│     └─► User is now authenticated                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Configuration Files

| File | Variables | Purpose |
|------|-----------|---------|
| `backend/.env` | `KITE_API_KEY`, `KITE_API_SECRET` | Kite Connect credentials |
| `backend/.env` | `KITE_REDIRECT_URL` | OAuth callback URL (must match Kite dashboard) |
| `backend/.env` | `FRONTEND_URL` | Where to redirect after OAuth success |
| `backend/app/main.py` | CORS middleware | Allowed origins for API requests |
| `tests/config/credentials.js` | `kite.userId`, `kite.password` | Auto-fill for E2E tests |
| `tests/config/.auth-state.json` | Browser storage state | Reused across test runs |
| `tests/config/.auth-token` | JWT token | Reused across test runs |

---

## Quick Diagnostic Commands

```bash
# 1. Check backend health
curl http://localhost:8000/api/health

# 2. Test login endpoint
curl http://localhost:8000/api/auth/zerodha/login

# 3. Check CORS headers
curl -I -H "Origin: http://localhost:5173" http://localhost:8000/api/auth/zerodha/login

# 4. Find processes on port 8000 (Windows)
netstat -ano | findstr ":8000" | findstr LISTENING

# 5. Find processes on port 8000 (Linux/Mac)
lsof -i:8000

# 6. Check frontend port
netstat -ano | findstr "LISTENING" | findstr "517"

# 7. View backend environment
grep -E "FRONTEND_URL|KITE_" backend/.env

# 8. Delete auth state for fresh login
rm tests/config/.auth-state.json tests/config/.auth-token
```

---

## Debugging E2E Login Issues

Add these debug lines to `tests/e2e/global-setup.js`:

```javascript
// Before clicking login button
const apiCheck = await page.evaluate(async () => {
  try {
    const resp = await fetch('/api/auth/zerodha/login');
    return await resp.json();
  } catch (e) {
    return { error: e.message };
  }
});
console.log('API pre-check:', JSON.stringify(apiCheck));

// Listen for console messages
page.on('console', msg => console.log('Browser console:', msg.type(), msg.text()));
page.on('pageerror', err => console.log('Page error:', err.message));

// Listen for request failures
page.on('requestfailed', request => {
  console.log(`Request failed: ${request.url()} - ${request.failure()?.errorText}`);
});
```

---

## Prevention Checklist

Before running E2E tests, verify:

- [ ] Backend is running on port 8000
- [ ] Frontend is running (note the port number)
- [ ] `FRONTEND_URL` in `backend/.env` matches frontend port
- [ ] `KITE_REDIRECT_URL` matches Kite dashboard setting
- [ ] Only ONE backend process is running
- [ ] CORS allows frontend origin

---

## Production vs Local Development

### Key Differences

| Aspect | Local Development | Production |
|--------|-------------------|------------|
| **Configuration** | `backend/.env` file | Environment variables in hosting platform |
| **CORS** | `localhost:\d+` regex | Explicit production domain only |
| **Kite Redirect URL** | `http://localhost:8000/...` | `https://yourdomain.com/...` |
| **Frontend URL** | `http://localhost:5173` | `https://yourdomain.com` |
| **Process Management** | Manual `python run.py` | Systemd, Docker, or cloud service |
| **Restart Method** | Kill Python processes | Service restart command |
| **SSL** | Not required | Required (HTTPS) |

---

## Production Troubleshooting

### Environment: VPS with Systemd

#### Configuration Location
Environment variables are set in the systemd service file, NOT in `.env`:
```
/etc/systemd/system/algochanakya-backend.service
```

#### Viewing Current Configuration
```bash
# SSH into VPS
ssh user@your-vps-ip

# View service configuration
sudo cat /etc/systemd/system/algochanakya-backend.service

# Check specific environment variables
sudo systemctl show algochanakya-backend --property=Environment
```

#### Updating Environment Variables
```bash
# Edit service file
sudo nano /etc/systemd/system/algochanakya-backend.service

# In the [Service] section, update:
Environment="FRONTEND_URL=https://algochanakya.com"
Environment="KITE_REDIRECT_URL=https://algochanakya.com/api/auth/zerodha/callback"
Environment="KITE_API_KEY=your_api_key"
Environment="KITE_API_SECRET=your_api_secret"

# Reload systemd and restart service
sudo systemctl daemon-reload
sudo systemctl restart algochanakya-backend

# Verify it's running
sudo systemctl status algochanakya-backend
```

#### Checking Logs
```bash
# View recent logs
sudo journalctl -u algochanakya-backend -n 100

# Follow logs in real-time
sudo journalctl -u algochanakya-backend -f

# View logs since last restart
sudo journalctl -u algochanakya-backend --since "10 minutes ago"
```

#### Restarting Service
```bash
# Graceful restart
sudo systemctl restart algochanakya-backend

# If that fails, force stop and start
sudo systemctl stop algochanakya-backend
sudo systemctl start algochanakya-backend

# Check status
sudo systemctl status algochanakya-backend
```

---

### Environment: Docker

#### Configuration Location
Environment variables are in:
- `docker-compose.yml` (or `docker-compose.prod.yml`)
- `.env` file referenced by docker-compose
- Dockerfile ENV instructions

#### Viewing Current Configuration
```bash
# View running container environment
docker exec algochanakya-backend env | grep -E "FRONTEND|KITE"

# View docker-compose config
cat docker-compose.prod.yml
```

#### Updating Environment Variables
```bash
# Edit docker-compose.prod.yml
nano docker-compose.prod.yml

# Update the environment section:
services:
  backend:
    environment:
      - FRONTEND_URL=https://algochanakya.com
      - KITE_REDIRECT_URL=https://algochanakya.com/api/auth/zerodha/callback

# Recreate container with new config
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend
```

#### Checking Logs
```bash
# View logs
docker logs algochanakya-backend --tail 100

# Follow logs
docker logs algochanakya-backend -f
```

#### Restarting Container
```bash
# Restart
docker-compose -f docker-compose.prod.yml restart backend

# Or recreate
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend
```

---

### Environment: Cloud Platforms (Railway, Render, Fly.io)

#### Configuration Location
Environment variables are set in the platform's dashboard or CLI.

#### Railway
```bash
# View variables
railway variables

# Set variable
railway variables set FRONTEND_URL=https://algochanakya.com

# Redeploy (automatic after variable change)
railway up
```

#### Render
1. Go to Dashboard → Your Service → Environment
2. Edit variables
3. Save → Service auto-restarts

#### Fly.io
```bash
# View secrets
fly secrets list

# Set secret
fly secrets set FRONTEND_URL=https://algochanakya.com

# Redeploy
fly deploy
```

---

### Production CORS Configuration

**IMPORTANT:** Production CORS should be strict, not permissive like development.

```python
# backend/app/main.py - Production CORS

import os

# Determine environment
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"

if IS_PRODUCTION:
    # Strict CORS for production - explicit domain only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://algochanakya.com",
            "https://www.algochanakya.com",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
else:
    # Permissive CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

---

### Production Issue: OAuth Callback Fails

#### Symptoms
User completes Kite login but gets redirected to wrong URL or sees error.

#### Diagnosis Steps

```bash
# 1. SSH into production server
ssh user@your-vps-ip

# 2. Check current environment
sudo systemctl show algochanakya-backend --property=Environment | tr ' ' '\n'

# 3. Test backend health
curl https://algochanakya.com/api/health

# 4. Test login endpoint
curl https://algochanakya.com/api/auth/zerodha/login

# 5. Check recent logs for errors
sudo journalctl -u algochanakya-backend --since "30 minutes ago" | grep -i error
```

#### Common Production Causes

| Cause | How to Verify | Fix |
|-------|---------------|-----|
| `FRONTEND_URL` wrong | Check env vars | Update systemd/docker config |
| `KITE_REDIRECT_URL` wrong | Check Kite dashboard | Update Kite dashboard + backend config |
| SSL certificate issue | `curl -v https://...` | Renew/fix SSL cert |
| Nginx proxy misconfigured | Check nginx logs | Fix proxy_pass settings |
| Service not restarted | `systemctl status` | Restart service |

#### Fix Procedure

```bash
# 1. Update environment variables
sudo nano /etc/systemd/system/algochanakya-backend.service

# 2. Ensure these are correct:
Environment="FRONTEND_URL=https://algochanakya.com"
Environment="KITE_REDIRECT_URL=https://algochanakya.com/api/auth/zerodha/callback"

# 3. Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart algochanakya-backend

# 4. Verify
curl https://algochanakya.com/api/health
curl https://algochanakya.com/api/auth/zerodha/login

# 5. Test login in browser
```

---

### Production Issue: CORS Blocking

#### Symptoms
Browser console shows CORS error on production domain.

#### Diagnosis
```bash
# Test CORS headers
curl -I -H "Origin: https://algochanakya.com" https://algochanakya.com/api/auth/zerodha/login

# Should see:
# Access-Control-Allow-Origin: https://algochanakya.com
# Access-Control-Allow-Credentials: true
```

#### Fix
1. Update `backend/app/main.py` with correct production domain
2. Redeploy backend
3. Clear browser cache and retry

---

### Kite Dashboard Configuration for Production

1. Go to https://kite.trade
2. Navigate to your app
3. Update settings:

| Field | Value |
|-------|-------|
| Redirect URL | `https://algochanakya.com/api/auth/zerodha/callback` |
| Postback URL | (optional) `https://algochanakya.com/api/webhooks/kite` |

**CRITICAL:** The redirect URL in Kite dashboard MUST exactly match `KITE_REDIRECT_URL` in your production environment.

---

### Switching Between Local and Production Kite Credentials

Kite allows only ONE redirect URL per API key. Options:

#### Option A: Two Separate API Keys (Recommended)
- Create two apps in Kite dashboard
- One for development: redirect to `http://localhost:8000/...`
- One for production: redirect to `https://algochanakya.com/...`
- Use different `KITE_API_KEY` and `KITE_API_SECRET` per environment

#### Option B: Single API Key (Not Recommended)
- Must update Kite dashboard redirect URL when switching
- Error-prone and tedious
- Can break production if forgotten

---

### Production Checklist

Before deploying or after OAuth issues:

- [ ] `FRONTEND_URL` matches production domain (with https)
- [ ] `KITE_REDIRECT_URL` matches Kite dashboard exactly
- [ ] Kite dashboard redirect URL is set to production
- [ ] CORS allows production domain
- [ ] SSL certificate is valid
- [ ] Service restarted after config changes
- [ ] Test login endpoint: `curl https://yourdomain.com/api/auth/zerodha/login`
- [ ] Test full OAuth flow in browser

---

## Summary: Local vs Production Fix Steps

### Local Development Fix
```bash
# 1. Edit local .env file
nano backend/.env

# 2. Kill all Python processes
# Windows:
Get-Process python* | Stop-Process -Force
# Linux/Mac:
pkill -f "python run.py"

# 3. Restart backend
cd backend && python run.py

# 4. Verify
curl http://localhost:8000/api/health
```

### Production Fix (Systemd)
```bash
# 1. SSH to server
ssh user@your-vps-ip

# 2. Edit systemd service
sudo nano /etc/systemd/system/algochanakya-backend.service

# 3. Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart algochanakya-backend

# 4. Verify
curl https://yourdomain.com/api/health
sudo journalctl -u algochanakya-backend -n 20
```

### Production Fix (Docker)
```bash
# 1. SSH to server
ssh user@your-vps-ip

# 2. Edit docker-compose
nano docker-compose.prod.yml

# 3. Recreate container
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend

# 4. Verify
curl https://yourdomain.com/api/health
docker logs algochanakya-backend --tail 20
```

---

## Related Documentation

- [Kite Connect API Documentation](https://kite.trade/docs/connect/v3/)
- [FastAPI CORS Middleware](https://fastapi.tiangolo.com/tutorial/cors/)
- [Playwright Authentication](https://playwright.dev/docs/auth)
- [Systemd Service Management](https://www.freedesktop.org/software/systemd/man/systemctl.html)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
