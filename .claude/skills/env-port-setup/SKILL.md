---
name: env-port-setup
description: >
  Verify and fix dev environment port configuration across 5 files. Prevents the #1
  most common mistake: wrong port causing API calls, WebSocket connections, and tests
  to fail or accidentally hit production. Use after cloning or when debugging connection issues.
type: workflow
allowed-tools: "Bash Read Edit Grep Glob"
argument-hint: "[--check] [--fix]"
version: "1.0.0"
synthesized: true
private: false
source_hash: "env-port-setup-v1"
---

# Environment Port Setup

Verify and fix the dev environment port configuration that coordinates across 5 files.

**Request:** $ARGUMENTS

---

## STEP 1: Read Current Port Configuration

Check all 5 files that must agree on port 8001:

| File | Key | Expected Value | What breaks if wrong |
|------|-----|----------------|----------------------|
| `backend/.env` | `PORT` | `8001` | Backend starts on wrong port |
| `frontend/.env.local` | `VITE_API_BASE_URL` | `http://localhost:8001` | All API calls fail |
| `backend/run.py` | `port` param | `8001` (from env) | Backend starts on wrong port |
| `frontend/src/services/api.js` | `baseURL` default | `http://localhost:8001` | API calls fail if env missing |
| `playwright.config.js` | `webServer.url` | `http://localhost:8001` | E2E tests timeout waiting for backend |

```bash
# Quick check all 5 files
echo "=== backend/.env ===" && grep -i "^PORT=" backend/.env 2>/dev/null || echo "NOT SET"
echo "=== frontend/.env.local ===" && grep "VITE_API_BASE_URL" frontend/.env.local 2>/dev/null || echo "NOT SET"
echo "=== backend/run.py ===" && grep "port" backend/run.py
echo "=== frontend/src/services/api.js ===" && grep "baseURL\|localhost" frontend/src/services/api.js
echo "=== playwright.config.js ===" && grep "8001\|url:" playwright.config.js
```

## STEP 2: Diagnose Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Frontend shows "Network Error" on all API calls | `VITE_API_BASE_URL` points to wrong port | Fix `frontend/.env.local` |
| WebSocket never connects | Backend not running on expected port | Check `backend/.env` PORT |
| E2E tests timeout at startup | `playwright.config.js` webServer URL mismatch | Fix playwright config |
| API calls hit production (port 8000) | `.env` still has `PORT=8000` from `.env.example` | Change to `PORT=8001` |
| Frontend `.env` overridden by `.env.local` | `.env.local` takes precedence in Vite | Check `.env.local` first |

### Production collision danger

```
⚠ CRITICAL: Port 8000 = PRODUCTION (C:\Apps\algochanakya)
             Port 8001 = DEVELOPMENT (C:\Abhay\VideCoding\algochanakya)

If backend/.env has PORT=8000, your dev server may conflict with
or be mistaken for production. ALWAYS use 8001 for development.
```

## STEP 3: Apply Fixes (if --fix or issues found)

### Fix 1: backend/.env

Read `backend/.env` and ensure PORT is set to 8001:

```bash
grep -q "^PORT=" backend/.env && sed -i 's/^PORT=.*/PORT=8001/' backend/.env || echo "PORT=8001" >> backend/.env
```

### Fix 2: frontend/.env.local

Ensure `.env.local` exists and has the correct API base URL:

```bash
# .env.local overrides .env in Vite — this is the file that matters
grep -q "VITE_API_BASE_URL" frontend/.env.local 2>/dev/null && \
  sed -i 's|VITE_API_BASE_URL=.*|VITE_API_BASE_URL=http://localhost:8001|' frontend/.env.local || \
  echo "VITE_API_BASE_URL=http://localhost:8001" >> frontend/.env.local
```

### Fix 3: Verify run.py reads from env

`backend/run.py` should read PORT from environment:
```python
port = int(os.getenv("PORT", 8001))
```

If it hardcodes a different port, update it.

## STEP 4: Verify the Fix

After applying fixes, verify everything is consistent:

```bash
echo "Checking port consistency..."
BACKEND_PORT=$(grep "^PORT=" backend/.env | cut -d= -f2)
FRONTEND_URL=$(grep "VITE_API_BASE_URL" frontend/.env.local | cut -d= -f2)

echo "Backend PORT: $BACKEND_PORT"
echo "Frontend URL: $FRONTEND_URL"

if [ "$BACKEND_PORT" = "8001" ] && echo "$FRONTEND_URL" | grep -q "8001"; then
  echo "✓ Port configuration is consistent (8001)"
else
  echo "✗ Port mismatch detected — review manually"
fi
```

## STEP 5: Test Connectivity

Start the stack and verify end-to-end:

```bash
# Terminal 1: Start backend
cd backend && venv\Scripts\activate && python run.py

# Terminal 2: Verify backend responds
curl -s http://localhost:8001/docs | head -5

# Terminal 3: Start frontend
cd frontend && npm run dev

# Verify frontend can reach backend (check browser console for errors)
```

---

## CRITICAL RULES

- ALWAYS use port 8001 for development — port 8000 is production and MUST NOT be used
- ALWAYS check `frontend/.env.local` (not `.env`) — `.env.local` overrides `.env` in Vite
- NEVER modify `C:\Apps\algochanakya` or any production configuration
- ALWAYS verify after fixing — a fix that doesn't restore connectivity is not a fix
- NEVER commit `.env` or `.env.local` files — they contain credentials and are gitignored
- ALWAYS check both HTTP API and WebSocket connectivity — they use the same port but different protocols
