# GitHub Actions Deployment Guide

This guide explains how to deploy AlgoChanakya to production using GitHub Actions.

---

## Deployment Triggers

The deployment workflow (`.github/workflows/deploy.yml`) is triggered by:

1. **Push to main branch** - Automatic deployment on every push
2. **Manual dispatch** - Trigger via GitHub Actions UI or `gh` CLI

---

## Quick Deployment Steps

### 1. Make Changes and Push

```bash
# Stage your changes
git add <files>

# Commit with descriptive message
git commit -m "feat: Description of changes"

# Push to main (triggers deployment)
git push origin main
```

### 2. Monitor Deployment

**GitHub Actions UI:**
https://github.com/abhayla/algochanakya/actions/workflows/deploy.yml

**Watch for:**
- Green checkmark = Success
- Red X = Failed (check logs)

---

## What the Deployment Does

The `deploy.yml` workflow runs these steps on the self-hosted Windows runner:

| Step | Action |
|------|--------|
| 1. Checkout | Clone repo on VPS |
| 2. Deploy Backend | Copy files to `C:\Apps\algochanakya\current\backend` |
| 3. Install Dependencies | Run `pip install -r requirements.txt` |
| 4. Database Migrations | Run `alembic upgrade head` |
| 5. Build Frontend | Run `npm ci && npm run build` |
| 6. Deploy Frontend | Copy dist to `C:\Apps\algochanakya\current\frontend\dist` |
| 7. Restart PM2 | Reload `algochanakya-backend` and `algochanakya-frontend` |
| 8. Health Check | Verify backend on :8000 and frontend on :3004 |

---

## Manual Deployment via GitHub UI

1. Go to https://github.com/abhayla/algochanakya/actions
2. Click "Deploy to VPS" workflow
3. Click "Run workflow" dropdown
4. Select "main" branch
5. Click "Run workflow" button

---

## Manual Deployment via CLI

If you have GitHub CLI installed:

```bash
# Trigger deployment
gh workflow run deploy.yml --repo abhayla/algochanakya

# Watch the run
gh run watch --repo abhayla/algochanakya

# List recent runs
gh run list --repo abhayla/algochanakya --workflow=deploy.yml
```

---

## Post-Deployment Verification

### 1. Check Backend Health

```powershell
curl https://algochanakya.com/api/health
```

Expected: `{"status":"healthy","database":"connected","redis":"connected"}`

### 2. Check PM2 Status (on VPS)

```powershell
pm2 list
pm2 logs algochanakya-backend --lines 20
```

### 3. Run Production Login Test

```powershell
cd C:\Abhay\VideCoding\algochanakya
node tests/e2e/prod-login-test.js
```

---

## Troubleshooting Failed Deployments

### Check Workflow Logs

1. Go to GitHub Actions page
2. Click the failed run
3. Click the failed step to see logs

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Port 8000 in use | Previous process didn't stop | `pm2 stop algochanakya-backend` then `pm2 start` |
| npm ci fails | Package lock mismatch | Delete `node_modules` and `package-lock.json`, reinstall |
| alembic fails | Missing migration | Run `alembic upgrade head` manually |
| Frontend 502 | Build failed | Check npm run build locally first |

### Manual Recovery (on VPS)

```powershell
# Stop and restart backend
pm2 stop algochanakya-backend
pm2 start algochanakya-backend

# If port still in use
netstat -ano | findstr :8000
taskkill /PID <pid> /F
pm2 start algochanakya-backend

# Save PM2 state
pm2 save
```

---

## Rollback Procedures

### Via Git Revert

```bash
# Revert the last commit
git revert HEAD

# Push to trigger rollback deployment
git push origin main
```

### Via GitHub UI

1. Go to the commit that broke things
2. Click "Revert" button
3. Merge the revert PR

### Manual Rollback (on VPS)

```powershell
# If backups exist
Copy-Item -Recurse -Force "C:\Apps\algochanakya\backups\backup-YYYY-MM-DD-HHMM\*" "C:\Apps\algochanakya\current\"

# Restart services
pm2 restart algochanakya-backend
pm2 restart algochanakya-frontend
```

---

## Self-Hosted Runner Requirements

The deployment runs on a self-hosted GitHub Actions runner on the VPS.

**Runner Location:** `C:\actions-runner-algochanakya`

**Service Account:** Must run as `LocalSystem` (required for PM2 access)

**Check Runner Status:**
1. Go to GitHub repo Settings > Actions > Runners
2. Verify runner is "Online"

**Restart Runner (if offline):**
```powershell
cd C:\actions-runner-algochanakya
.\run.cmd
```

---

## Related Documentation

- **Deployment Checklist:** `docs/prod/DEPLOYMENT-CHECKLIST.md`
- **VPS Setup:** `C:\Apps\shared\docs\ALGOCHANAKYA-SETUP.md`
- **GitHub Runner Setup:** `C:\Apps\shared\docs\GITHUB-ACTIONS-RUNNER-SETUP.md`
