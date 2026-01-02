# Production Deployment Checklist

This checklist must be followed for every production deployment to `algochanakya.com`.

---

## Pre-Deployment

### 1. Code Review
- [ ] All changes committed to `main` branch
- [ ] Code reviewed (if applicable)
- [ ] No console.log or debug statements left in code
- [ ] No hardcoded localhost URLs in frontend code

### 2. Local Testing
- [ ] Backend tests pass: `cd backend && pytest tests/ -v`
- [ ] Frontend builds without errors: `cd frontend && npm run build`
- [ ] E2E tests pass (if applicable): `npm test`

### 3. Environment Files Check
- [ ] `frontend/.env.production` exists with correct values:
  ```
  VITE_API_BASE_URL=https://algochanakya.com
  VITE_WS_URL=algochanakya.com
  ```
- [ ] No sensitive data in committed files

### 4. Database Migrations
- [ ] Check for new migrations: `cd backend && alembic history`
- [ ] If new migrations exist, note them for production execution

---

## Deployment Steps

### 5. Connect to VPS
```bash
# SSH to production server
ssh Administrator@544934-Abhayvps2.com
# Or use Remote Desktop
```

### 6. Backup (Optional but Recommended)
```powershell
# Backup current deployment
Copy-Item -Recurse C:\Apps\algochanakya\current C:\Apps\algochanakya\backups\backup-$(Get-Date -Format 'yyyy-MM-dd-HHmm')
```

### 7. Update Backend Code
```powershell
# Copy updated backend files from dev to prod
# Option A: Copy entire backend folder
Copy-Item -Recurse -Force "C:\Abhay\VideCoding\algochanakya\backend\*" "C:\Apps\algochanakya\current\backend\"

# Option B: Copy specific changed files
Copy-Item "C:\Abhay\VideCoding\algochanakya\backend\app\api\routes\orders.py" "C:\Apps\algochanakya\current\backend\app\api\routes\orders.py"
```

### 8. Run Database Migrations (If Applicable)
```powershell
cd C:\Apps\algochanakya\current\backend
.\venv\Scripts\alembic.exe upgrade head
```

### 9. Restart Backend
```powershell
pm2 restart algochanakya-backend
```

### 10. Update Frontend (If Changed)
```powershell
# Build frontend locally first
cd C:\Abhay\VideCoding\algochanakya\frontend
npm run build

# Copy dist folder to production
Copy-Item -Recurse -Force "C:\Abhay\VideCoding\algochanakya\frontend\dist\*" "C:\Apps\algochanakya\current\frontend\dist\"

# Restart frontend (static file server)
pm2 restart algochanakya-frontend
```

---

## Post-Deployment Verification

### 11. Health Checks
- [ ] Backend health: `curl https://algochanakya.com/api/health`
  - Expected: `{"status":"healthy","database":"connected","redis":"connected"}`
- [ ] Frontend loads: Open `https://algochanakya.com` in browser

### 12. Authentication Test
- [ ] Run Playwright login test:
  ```bash
  cd C:\Abhay\VideCoding\algochanakya
  node tests/e2e/prod-login-test.js
  ```
- [ ] Verify login completes successfully
- [ ] Check dashboard loads after login

### 13. Feature Verification
- [ ] Test the specific feature that was deployed
- [ ] Check browser console for errors (F12 → Console)
- [ ] Verify WebSocket connection (green dot in header)

### 14. Check Logs for Errors
```powershell
# View recent backend logs
pm2 logs algochanakya-backend --lines 50

# View error logs only
pm2 logs algochanakya-backend --err --lines 50
```

---

## Rollback Procedure

If deployment fails or causes issues:

### Quick Rollback
```powershell
# 1. Restore from backup
Copy-Item -Recurse -Force "C:\Apps\algochanakya\backups\backup-YYYY-MM-DD-HHMM\*" "C:\Apps\algochanakya\current\"

# 2. Restart services
pm2 restart algochanakya-backend
pm2 restart algochanakya-frontend

# 3. Verify
curl https://algochanakya.com/api/health
```

### Database Rollback (If Migration Applied)
```powershell
cd C:\Apps\algochanakya\current\backend
.\venv\Scripts\alembic.exe downgrade -1
```

---

## Common Issues & Solutions

### Issue: 502 Bad Gateway after restart
**Cause:** Backend still starting up
**Solution:** Wait 10-15 seconds and retry

### Issue: API calls failing with CORS errors
**Cause:** Frontend build missing `.env.production`
**Solution:** Ensure `frontend/.env.production` exists, rebuild, and redeploy

### Issue: WebSocket not connecting
**Cause:** `VITE_WS_URL` not set correctly
**Solution:** Check `frontend/.env.production` has `VITE_WS_URL=algochanakya.com`

### Issue: OAuth callback fails
**Cause:** `FRONTEND_URL` or `KITE_REDIRECT_URL` misconfigured
**Solution:** Check backend environment variables match production domain

### Issue: "Insufficient permission" errors from Kite API
**Cause:** Market is closed (expected) OR Kite access token expired
**Solution:**
- If market closed: Normal behavior, no action needed
- If token expired: User needs to re-login via Zerodha OAuth

---

## Production Environment Reference

| Component | Location |
|-----------|----------|
| App Root | `C:\Apps\algochanakya\current` |
| Backend | `C:\Apps\algochanakya\current\backend` |
| Frontend Dist | `C:\Apps\algochanakya\current\frontend\dist` |
| PM2 Config | `C:\Apps\algochanakya\current\ecosystem.config.js` |
| Logs | `C:\Apps\algochanakya\logs\` |
| Backups | `C:\Apps\algochanakya\backups\` |

| Service | PM2 Name | Port |
|---------|----------|------|
| Backend | `algochanakya-backend` | 8000 |
| Frontend | `algochanakya-frontend` | 3000 (proxied via Nginx) |

| URL | Purpose |
|-----|---------|
| `https://algochanakya.com` | Production site |
| `https://algochanakya.com/api/health` | Backend health check |
| `wss://algochanakya.com/ws/ticks` | WebSocket endpoint |

---

## PM2 Commands Reference

```powershell
# View all services
pm2 list

# Restart specific service
pm2 restart algochanakya-backend
pm2 restart algochanakya-frontend

# View logs
pm2 logs algochanakya-backend
pm2 logs algochanakya-frontend

# View logs with timestamps
pm2 logs algochanakya-backend --timestamp

# Save PM2 process list (persist across reboots)
pm2 save

# Monitor all processes
pm2 monit
```

---

## Deployment Log Template

Use this template to log each deployment:

```
## Deployment: YYYY-MM-DD HH:MM

**Deployer:** [Name]
**Changes:**
- [Brief description of changes]

**Pre-deployment checklist:** ✅ Complete
**Deployment steps:** ✅ Complete
**Post-deployment verification:** ✅ Complete

**Issues encountered:** None / [Description]
**Rollback required:** No / Yes - [Reason]

**Notes:**
[Any additional notes]
```
