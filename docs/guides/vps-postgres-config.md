# VPS PostgreSQL Configuration Verification

## Current Error

```
InvalidAuthorizationSpecificationError: no pg_hba.conf entry for host "116.74.178.159",
user "algochanakya_user", database "algochanakya", no encryption
```

**Your IP:** `116.74.178.159`
**VPS Server:** `103.118.16.189:5432`
**Status:** Connection rejected by PostgreSQL

---

## Steps to Fix on VPS

### 1. SSH into the VPS

```bash
ssh user@103.118.16.189
```

### 2. Edit pg_hba.conf

```bash
# Find the pg_hba.conf file
sudo find /etc/postgresql -name pg_hba.conf

# Edit it (adjust path based on PostgreSQL version)
sudo nano /etc/postgresql/15/main/pg_hba.conf
# or
sudo nano /var/lib/pgsql/data/pg_hba.conf
```

### 3. Add Entry for Your IP

Add this line to the file (near other `host` entries):

```conf
# Allow connection from client IP
host    algochanakya    algochanakya_user    116.74.178.159/32    md5
```

Or to allow from any IP (less secure, but useful for testing):

```conf
# Allow from anywhere (TESTING ONLY)
host    algochanakya    algochanakya_user    0.0.0.0/0    md5
```

### 4. Reload PostgreSQL

```bash
# Ubuntu/Debian
sudo systemctl reload postgresql

# Or restart if reload doesn't work
sudo systemctl restart postgresql

# CentOS/RHEL
sudo systemctl reload postgresql-15
```

### 5. Verify Configuration

```bash
# Check pg_hba.conf syntax
sudo -u postgres psql -c "SELECT pg_reload_conf();"

# View current settings
sudo -u postgres psql -c "SHOW hba_file;"
sudo cat $(sudo -u postgres psql -t -c "SHOW hba_file;")
```

---

## Alternative: Use Local Database for Testing

If you can't access the VPS or want to test immediately:

### Quick Local Setup (5 minutes)

```bash
# 1. Install PostgreSQL
# Download from: https://www.postgresql.org/download/windows/
# Or use Chocolatey: choco install postgresql

# 2. Create database
psql -U postgres
CREATE DATABASE algochanakya_local;
CREATE USER algochanakya_user WITH PASSWORD 'AlgoChanakya2024Secure';
GRANT ALL PRIVILEGES ON DATABASE algochanakya_local TO algochanakya_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO algochanakya_user;
\q

# 3. Update backend/.env
# Change:
DATABASE_URL=postgresql+asyncpg://algochanakya_user:AlgoChanakya2024Secure@103.118.16.189:5432/algochanakya
# To:
DATABASE_URL=postgresql+asyncpg://algochanakya_user:AlgoChanakya2024Secure@localhost:5432/algochanakya_local

# 4. Run migrations
cd backend
venv/Scripts/activate
alembic upgrade head

# 5. Start testing!
python run.py
```

---

## Test Connection After Fix

```bash
cd backend
venv/Scripts/python.exe -c "
import asyncio, asyncpg
async def test():
    conn = await asyncpg.connect(
        host='103.118.16.189',  # or 'localhost' if using local
        port=5432,
        user='algochanakya_user',
        password='AlgoChanakya2024Secure',
        database='algochanakya',  # or 'algochanakya_local'
        timeout=10
    )
    print('✅ SUCCESS: Connected to database!')
    print('PostgreSQL:', await conn.fetchval('SELECT version()'))
    await conn.close()
asyncio.run(test())
"
```

**Expected output:**
```
✅ SUCCESS: Connected to database!
PostgreSQL: PostgreSQL 15.x on ...
```

---

## Which Option Should You Choose?

| Option | Pros | Cons | Time |
|--------|------|------|------|
| **Fix VPS pg_hba.conf** | Production database, no migration needed | Requires SSH access | 2-3 min |
| **Local PostgreSQL** | Full control, instant setup | Need to migrate data later | 5 min |
| **Docker PostgreSQL** | Isolated, easy cleanup | Requires Docker installed | 2 min |

**Recommendation:** If you have SSH access to the VPS, fix pg_hba.conf (Option 1). Otherwise, use local PostgreSQL for testing.
