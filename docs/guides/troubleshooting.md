# Troubleshooting Guide

Common issues and their solutions when working with AlgoChanakya.

## Authentication Issues

### Zerodha Token Expired

**Symptoms:**
- API calls return 401 Unauthorized
- "Token expired" error in console
- Redirected to login page

**Solution:**
1. Zerodha access tokens expire at 6:00 AM IST daily
2. User must re-login through Zerodha OAuth
3. Clear localStorage: `localStorage.removeItem('token')`

**Prevention:**
- Check token expiry before market hours
- Handle 401 errors with automatic redirect to login

### OAuth Callback Failed

**Symptoms:**
- Stuck on callback page
- "Invalid request token" error

**Solution:**
1. Check `KITE_API_KEY` and `KITE_API_SECRET` in `.env`
2. Verify `FRONTEND_URL` matches your frontend URL
3. Check Kite Connect app settings for correct redirect URL

### AngelOne Login Timeout (Fixed Jan 2026)

**Symptoms:**
- Click "Angel One" button → Shows "Connecting..." for 10 seconds
- Error appears: "Failed to login with Angel One. Make sure SmartAPI credentials are configured in Settings."
- Browser console shows: `timeout of 10000ms exceeded`
- Backend logs show successful authentication but frontend times out

**Root Cause:**
AngelOne authentication with auto-TOTP takes 20-25 seconds (measured: 22.8s). Default axios timeout is only 10 seconds, causing request to abort before backend finishes.

**Solution (FIXED in commit e23306a):**
The fix is already applied in `frontend/src/stores/auth.js` - no action needed for new deployments.

**Verification Steps:**
1. Check backend is running on correct port:
   ```bash
   curl http://localhost:8001/
   # Should return: {"message":"Welcome to AlgoChanakya API",...}
   ```

2. Check `.env.local` configuration:
   ```bash
   cat frontend/.env.local
   # Should show: VITE_API_BASE_URL=http://localhost:8001
   ```

3. Test AngelOne endpoint directly:
   ```bash
   time curl -X POST http://localhost:8001/api/auth/angelone/login
   # Should complete in ~22 seconds with success response
   ```

**Related Issues:**
- Backend not running on port 8001
- `.env.local` pointing to wrong port (8005 or 8000)
- Database connection blocked (IP not whitelisted)

**See:** [docs/troubleshooting/ANGELONE-LOGIN-TIMEOUT.md](../troubleshooting/ANGELONE-LOGIN-TIMEOUT.md) for complete analysis.

### CORS Errors

**Symptoms:**
- "Access-Control-Allow-Origin" error in browser console
- API calls blocked

**Solution:**
1. Verify `FRONTEND_URL` in backend `.env`
2. Check CORS configuration in `app/main.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[settings.FRONTEND_URL],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
3. For development, ensure frontend runs on expected port (5173)

## Database Issues

### IP Not Whitelisted (Remote Database)

**Symptoms:**
- Backend won't start with error:
  ```
  asyncpg.exceptions.InvalidAuthorizationSpecificationError:
  no pg_hba.conf entry for host "XXX.XXX.XXX.XXX", user "algochanakya_user",
  database "algochanakya", no encryption
  ```
- Backend startup shows: `ERROR:    Application startup failed. Exiting.`

**Root Cause:**
Remote PostgreSQL server is blocking connections from your current IP address.

**Solution:**
1. Identify your current public IP:
   ```bash
   curl ifconfig.me
   ```

2. Contact database administrator to whitelist your IP in `pg_hba.conf` on the PostgreSQL server

3. Test connection once whitelisted:
   ```bash
   psql -h <DB_HOST> -U algochanakya_user -d algochanakya
   # Should connect successfully
   ```

**Note:** This commonly occurs when:
- Working from a new location
- ISP changes your IP address
- VPN connection changes your exit IP

### Connection Refused (Local Database)

**Symptoms:**
- "Connection refused" error on startup
- Health check fails for database

**Solution:**
1. Verify PostgreSQL is running:
   ```bash
   # Windows
   pg_isready -h localhost -p 5432

   # Linux
   sudo systemctl status postgresql
   ```
2. Check `DATABASE_URL` in `.env`
3. Verify PostgreSQL accepts connections (pg_hba.conf)

### Migration Errors

**Symptoms:**
- `alembic upgrade head` fails
- "Relation already exists" error

**Solution:**
1. Check current revision:
   ```bash
   alembic current
   ```
2. View migration history:
   ```bash
   alembic history
   ```
3. If stuck, manually fix `alembic_version` table
4. For fresh start:
   ```bash
   alembic downgrade base
   alembic upgrade head
   ```

### asyncpg vs psycopg2

**Symptoms:**
- "asyncpg" errors during migration
- Alembic can't connect

**Solution:**
- Alembic uses `psycopg2` (sync driver)
- `alembic/env.py` auto-converts URL
- Ensure both drivers are installed:
  ```bash
  pip install asyncpg psycopg2-binary
  ```

## Redis Issues

### Connection Failed

**Symptoms:**
- "Connection refused" for Redis
- Session storage not working

**Solution:**
1. Verify Redis is running:
   ```bash
   redis-cli ping  # Should return PONG
   ```
2. Check `REDIS_URL` in `.env`
3. For remote Redis, check firewall rules

### Session Lost

**Symptoms:**
- Users logged out unexpectedly
- JWT validation fails

**Solution:**
1. Check Redis memory usage: `redis-cli info memory`
2. Verify `JWT_EXPIRY_HOURS` setting
3. Check Redis persistence configuration

## WebSocket Issues

### Connection Drops

**Symptoms:**
- "WebSocket closed" in console
- Prices stop updating

**Solution:**
1. Check network stability
2. Verify backend WebSocket endpoint is reachable
3. KiteTickerService auto-reconnects, wait 5 seconds
4. Fallback to HTTP `/api/orders/ltp` endpoint

### No Tick Data

**Symptoms:**
- Connected but no prices
- "subscribed" message received but no ticks

**Solution:**
1. Verify instrument tokens are correct
2. Check market hours (9:15 AM - 3:30 PM IST)
3. Ensure Kite access token is valid
4. Check Kite WebSocket status on Zerodha

### "Invalid mode" Error

**Symptoms:**
- Subscription fails with mode error

**Solution:**
- Valid modes: `"ltp"`, `"quote"`, `"full"`
- Check message format:
  ```json
  {"action": "subscribe", "tokens": [256265], "mode": "quote"}
  ```

## Frontend Issues

### Blank Page After Login

**Symptoms:**
- OAuth succeeds but page is blank
- Console shows errors

**Solution:**
1. Check browser console for errors
2. Verify token is stored: `localStorage.getItem('token')`
3. Check Vue devtools for store state
4. Clear cache and retry

### API Base URL Wrong

**Symptoms:**
- "Network Error" on all API calls
- Wrong URL in network tab

**Solution:**
1. Check `VITE_API_BASE_URL` in frontend `.env`
2. Restart Vite dev server after `.env` changes
3. For production, check built config

### Production API Calls Going to localhost:8000

**Symptoms:**
- "Login with Zerodha" button shows "Connecting..." spinner but never redirects
- Browser DevTools Network tab shows failed requests to `http://localhost:8000/api/*`
- Console shows `net::ERR_ABORTED` or connection refused errors

**Root Cause:**
The production frontend was built without `.env.production`, so `VITE_API_BASE_URL` defaults to `http://localhost:8000` (the development fallback in `services/api.js`).

**Solution:**
```bash
# On production server (VPS)
# 1. Create .env.production with correct API URL
echo "VITE_API_BASE_URL=https://algochanakya.com" > frontend/.env.production

# 2. Rebuild frontend
cd frontend
npm run build

# 3. Restart PM2 (if using PM2)
pm2 restart algochanakya-frontend

# 4. Verify fix - should show algochanakya.com, not localhost
grep -o "algochanakya.com" frontend/dist/assets/index-*.js | head -1
```

**Prevention:**
- Always create `.env.production` before building for production
- Add to deployment checklist/script
- The GitHub Actions deploy workflow should include this step

### Production WebSocket Connecting to localhost:8000

**Symptoms:**
- Positions page shows "Loading positions..." indefinitely
- Option Chain prices don't update
- Browser console shows `WebSocket connection to 'wss://localhost:8000/ws/ticks?token=...' failed`
- `net::ERR_SSL_PROTOCOL_ERROR` because localhost doesn't have SSL

**Root Cause:**
The production frontend was built without `VITE_WS_URL` in `.env.production`, so the WebSocket URL defaults to `localhost:8000`.

**Solution:**
```bash
# On production server (VPS)
# 1. Add VITE_WS_URL to .env.production
cat > frontend/.env.production << EOF
VITE_API_BASE_URL=https://algochanakya.com
VITE_WS_URL=algochanakya.com
EOF

# 2. Rebuild frontend
cd frontend
npm run build

# 3. Restart PM2
pm2 restart algochanakya-frontend
```

**Verification:**
- Positions page should load (shows positions or "No Open Positions")
- Option Chain prices should update live
- Browser console should show WebSocket connecting to `wss://algochanakya.com/ws/ticks`

### Horizontal Overflow

**Symptoms:**
- Page scrolls horizontally
- Content extends beyond viewport

**Solution:**
1. Run overflow test: `npm run test:overflow`
2. Check for elements with fixed widths
3. Use `overflow-x-hidden` on container
4. Ensure Tailwind classes use responsive breakpoints

## Strategy Builder Issues

### P/L Calculation Wrong

**Symptoms:**
- Incorrect max profit/loss
- Breakeven points off

**Solution:**
1. Verify lot sizes: NIFTY=75, BANKNIFTY=15, FINNIFTY=25
2. Check entry prices are correct
3. Verify P/L mode (At Expiry vs Current)
4. Check scipy is installed for accurate Black-Scholes

### CMP Not Loading

**Symptoms:**
- CMP shows "-" or loading
- Exit P/L not calculated

**Solution:**
1. Check WebSocket connection
2. Fallback to LTP API:
   ```http
   GET /api/orders/ltp?instruments=NFO:NIFTY24DEC24500CE
   ```
3. Verify instrument token is correct

## Option Chain Issues

### Greeks Not Showing

**Symptoms:**
- IV, Delta, Gamma columns empty
- Greeks toggle does nothing

**Solution:**
1. IV calculation needs valid LTP and spot price
2. Check if market is open
3. Verify scipy is installed
4. Check console for calculation errors

### OI Data Missing

**Symptoms:**
- OI bars not displaying
- Zero OI values

**Solution:**
1. OI updates every 3 minutes
2. Check Kite API for OI availability
3. Verify option chain endpoint works:
   ```http
   GET /api/optionchain/chain?underlying=NIFTY&expiry=2024-12-26
   ```

## Environment Issues

### Module Not Found

**Symptoms:**
- `ModuleNotFoundError` on startup
- Missing package errors

**Solution:**
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Port Already in Use

**Symptoms:**
- "Address already in use" error
- Server won't start

**Solution:**
```bash
# Find process using port (Windows)
netstat -ano | findstr :8000

# Kill process
taskkill /PID <pid> /F

# Linux/Mac
lsof -i :8000
kill -9 <pid>
```

## Getting Help

1. Check browser console and terminal for errors
2. Search existing issues on GitHub
3. Provide error messages and steps to reproduce
4. Include environment details (OS, Python/Node versions)

## Related Documentation

- [Database Setup](database-setup.md) - Configuration guide
- [Architecture Overview](../architecture/overview.md) - System design
- [WebSocket](../architecture/websocket.md) - Live price streaming
