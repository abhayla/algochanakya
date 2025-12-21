# Database Connection Issue - Resolution Guide

## 🎯 Current Status

### ✅ What's Working
1. **Enum Fixes Applied Successfully** - All 13 enum case errors fixed (Commit: 4406ea4)
2. **Backend Code Valid** - No Python errors, imports work correctly
3. **PostgreSQL Server Reachable** - Port 5432 is open on 103.118.16.189
4. **Dependencies Installed** - asyncpg, FastAPI, SQLAlchemy all present

### ❌ What's Blocking
**PostgreSQL Connection Rejected by Firewall**

```
asyncpg.exceptions.InvalidAuthorizationSpecificationError:
no pg_hba.conf entry for host "116.74.178.159",
user "algochanakya_user", database "algochanakya", no encryption
```

**Issue:** The PostgreSQL server's `pg_hba.conf` file does not allow connections from your current IP address (116.74.178.159).

---

## 🔧 Solutions

### Option 1: Add Your IP to PostgreSQL Server (Recommended for VPS)

If you have SSH access to the VPS server (103.118.16.189):

```bash
# 1. SSH into the VPS
ssh user@103.118.16.189

# 2. Edit PostgreSQL configuration
sudo nano /etc/postgresql/*/main/pg_hba.conf

# 3. Add this line to allow your IP (change to your IP)
host    algochanakya    algochanakya_user    116.74.178.159/32    md5

# 4. Reload PostgreSQL
sudo systemctl reload postgresql

# 5. Test connection from your machine
```

### Option 2: Use Local PostgreSQL Database (Recommended for Testing)

**Install PostgreSQL locally:**

```bash
# Windows (using Chocolatey)
choco install postgresql

# Or download from: https://www.postgresql.org/download/windows/

# Start PostgreSQL service
# Default runs on localhost:5432
```

**Create local database:**

```bash
# Open psql
psql -U postgres

# Create database and user
CREATE DATABASE algochanakya_local;
CREATE USER algochanakya_user WITH PASSWORD 'AlgoChanakya2024Secure';
GRANT ALL PRIVILEGES ON DATABASE algochanakya_local TO algochanakya_user;
\q
```

**Update backend/.env:**

```ini
# Change from remote
# DATABASE_URL=postgresql+asyncpg://algochanakya_user:AlgoChanakya2024Secure@103.118.16.189:5432/algochanakya

# To local
DATABASE_URL=postgresql+asyncpg://algochanakya_user:AlgoChanakya2024Secure@localhost:5432/algochanakya_local
```

**Run migrations:**

```bash
cd backend
venv/Scripts/activate
alembic upgrade head
```

### Option 3: Use Docker PostgreSQL (Quick Setup)

```bash
# Start PostgreSQL in Docker
docker run --name algochanakya-postgres \
  -e POSTGRES_USER=algochanakya_user \
  -e POSTGRES_PASSWORD=AlgoChanakya2024Secure \
  -e POSTGRES_DB=algochanakya_local \
  -p 5432:5432 \
  -d postgres:15

# Update backend/.env
DATABASE_URL=postgresql+asyncpg://algochanakya_user:AlgoChanakya2024Secure@localhost:5432/algochanakya_local

# Run migrations
cd backend
alembic upgrade head
```

### Option 4: Connect from Allowed IP

If the VPS only allows specific IPs, you can:

1. **Use VPN** to get an allowed IP address
2. **Use SSH Tunnel** to forward PostgreSQL port:
   ```bash
   ssh -L 5432:localhost:5432 user@103.118.16.189

   # Then update .env
   DATABASE_URL=postgresql+asyncpg://algochanakya_user:AlgoChanakya2024Secure@localhost:5432/algochanakya
   ```

---

## 📋 Setup Redis (If Using Local Database)

### Option 1: Install Redis Locally (Windows)

```bash
# Using Chocolatey
choco install redis-64

# Or download from: https://github.com/microsoftarchive/redis/releases

# Start Redis
redis-server

# Update backend/.env
REDIS_URL=redis://localhost:6379/1
```

### Option 2: Use Docker Redis

```bash
docker run --name algochanakya-redis -p 6379:6379 -d redis:7

# Update backend/.env
REDIS_URL=redis://localhost:6379/1
```

---

## ✅ Verification Steps

Once you've set up the database:

### 1. Test Database Connection

```bash
cd backend
venv/Scripts/python.exe -c "
import asyncio
import asyncpg

async def test():
    # Update these values based on your setup
    conn = await asyncpg.connect(
        host='localhost',  # or 103.118.16.189 if using VPS
        port=5432,
        user='algochanakya_user',
        password='AlgoChanakya2024Secure',
        database='algochanakya_local',  # or 'algochanakya'
        timeout=10
    )
    print('Database connected!')
    version = await conn.fetchval('SELECT version()')
    print(f'PostgreSQL: {version}')
    await conn.close()

asyncio.run(test())
"
```

**Expected Output:**
```
Database connected!
PostgreSQL: PostgreSQL 15.x on ...
```

### 2. Start Backend

```bash
cd backend
venv/Scripts/python.exe run.py
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXX] using WatchFiles
INFO:     Started server process [YYYY]
INFO:     Waiting for application startup.
INFO:     Application startup complete.  # ✅ SUCCESS!
```

### 3. Run AutoPilot Tests

```bash
# Test strike preview
npx playwright test tests/e2e/specs/autopilot/autopilot.strike-preview.spec.js --headed

# Test templates
npx playwright test tests/e2e/specs/autopilot/autopilot.templates.spec.js --headed

# Run all AutoPilot tests
npm run test:specs:autopilot
```

---

## 🐛 Troubleshooting

### Error: "role 'algochanakya_user' does not exist"

```bash
# Connect to PostgreSQL
psql -U postgres -d algochanakya_local

# Create user
CREATE USER algochanakya_user WITH PASSWORD 'AlgoChanakya2024Secure';
GRANT ALL PRIVILEGES ON DATABASE algochanakya_local TO algochanakya_user;

# For PostgreSQL 15+, also grant schema privileges
GRANT ALL PRIVILEGES ON SCHEMA public TO algochanakya_user;
```

### Error: "database 'algochanakya_local' does not exist"

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE algochanakya_local;
GRANT ALL PRIVILEGES ON DATABASE algochanakya_local TO algochanakya_user;
```

### Error: "Connection refused"

```bash
# Check if PostgreSQL is running
# Windows:
sc query postgresql-x64-15  # or your PostgreSQL service name

# Linux:
sudo systemctl status postgresql

# Start if not running:
# Windows:
net start postgresql-x64-15

# Linux:
sudo systemctl start postgresql
```

### Error: "fe_sendauth: no password supplied"

This means the connection requires a password. Verify your .env file has the correct password:

```ini
DATABASE_URL=postgresql+asyncpg://algochanakya_user:AlgoChanakya2024Secure@localhost:5432/algochanakya_local
#                                                  ^ Password must be here ^
```

---

## 📊 Current Configuration (from .env)

```ini
# Remote VPS (CURRENTLY BLOCKED by pg_hba.conf)
DATABASE_URL=postgresql+asyncpg://algochanakya_user:AlgoChanakya2024Secure@103.118.16.189:5432/algochanakya
REDIS_URL=redis://103.118.16.189:6379/1

# Your IP trying to connect: 116.74.178.159
# VPS Server IP: 103.118.16.189
# Port: 5432 (OPEN - reachable)
# Issue: pg_hba.conf doesn't allow your IP
```

---

## 🚀 Recommended Next Steps

1. **Choose a solution** from the options above (I recommend Option 2: Local PostgreSQL for testing)
2. **Set up the database** following the chosen option
3. **Run migrations** to create tables: `alembic upgrade head`
4. **Start backend** and verify it starts successfully
5. **Run tests** to verify AutoPilot functionality

---

## 💡 Summary

| Component | Status | Issue |
|-----------|--------|-------|
| Enum Fixes | ✅ Complete | All 13 fixes applied |
| Backend Code | ✅ Valid | No Python/import errors |
| VPS Reachable | ✅ Yes | Port 5432 is open |
| Database Auth | ❌ Blocked | pg_hba.conf firewall |
| **Solution** | **Required** | **Set up local DB or fix VPS firewall** |

**Once database is configured, all AutoPilot tests should pass!** 🎉
