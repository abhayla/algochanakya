# Database Setup Guide

## Issue: VPS PostgreSQL Connection Refused

The error you're seeing happens because the VPS PostgreSQL server is refusing connections from your IP address. You have two options:

## Option 1: Use Local PostgreSQL (Recommended for Development)

### Step 1: Install PostgreSQL

**Windows:**
1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Run the installer (PostgreSQL 15 or higher)
3. During installation:
   - Set password for `postgres` user (remember this!)
   - Port: 5432 (default)
   - Install pgAdmin (optional GUI tool)

**Alternative - Use Docker:**
```bash
docker run --name algochanakya-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=algochanakya -p 5432:5432 -d postgres:15
```

### Step 2: Create Database

**Using psql command line:**
```bash
# Login to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE algochanakya;

# Create user
CREATE USER algochanakya_user WITH PASSWORD 'your_password_here';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE algochanakya TO algochanakya_user;

# Exit
\q
```

**Using pgAdmin (GUI):**
1. Open pgAdmin
2. Right-click "Databases" → Create → Database
3. Name: `algochanakya`
4. Owner: postgres
5. Save

### Step 3: Install Redis Locally

**Windows:**
1. Download Redis from: https://github.com/microsoftarchive/redis/releases
2. Extract and run `redis-server.exe`
3. Redis will run on `localhost:6379`

**Alternative - Use Docker:**
```bash
docker run --name algochanakya-redis -p 6379:6379 -d redis:7
```

### Step 4: Update .env File

Update your `backend/.env` file:

```env
# Application
APP_NAME=AlgoChanakya
DEBUG=True

# PostgreSQL Database - LOCAL
DATABASE_URL=postgresql+asyncpg://algochanakya_user:your_password_here@localhost:5432/algochanakya

# Redis - LOCAL
REDIS_URL=redis://localhost:6379/1

# JWT Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# Kite Connect (Zerodha)
KITE_API_KEY=dh9lojp9j9tnq3h4
KITE_API_SECRET=99q72gnpothxdsi3jo0o789dvyt6rco3
KITE_REDIRECT_URL=http://localhost:8000/api/auth/zerodha/callback

# Frontend
FRONTEND_URL=http://localhost:5174
```

### Step 5: Run Migrations

```bash
cd backend
alembic upgrade head
```

### Step 6: Start Backend

```bash
python run.py
```

---

## Option 2: Configure VPS PostgreSQL to Allow Your IP

If you want to use the VPS database, you need to whitelist your IP address.

### Step 1: Find Your IP Address

```bash
curl ifconfig.me
```

### Step 2: SSH into VPS

```bash
ssh your_username@103.118.16.189
```

### Step 3: Edit PostgreSQL Configuration

```bash
# Edit pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Add this line (replace YOUR_IP with your actual IP)
host    algochanakya    algochanakya_user    YOUR_IP/32    md5

# Example:
# host    algochanakya    algochanakya_user    116.75.158.249/32    md5
```

### Step 4: Edit postgresql.conf

```bash
sudo nano /etc/postgresql/15/main/postgresql.conf

# Find listen_addresses and change to:
listen_addresses = '*'
```

### Step 5: Restart PostgreSQL

```bash
sudo systemctl restart postgresql
```

### Step 6: Configure Firewall

```bash
# Allow PostgreSQL port
sudo ufw allow 5432/tcp

# Allow Redis port
sudo ufw allow 6379/tcp
```

### Step 7: Test Connection

From your local machine:

```bash
# Install psql if not already installed
# Test connection
psql -h 103.118.16.189 -U algochanakya_user -d algochanakya

# If it asks for password and connects, you're good!
```

### Step 8: Update .env File

```env
DATABASE_URL=postgresql+asyncpg://algochanakya_user:your_vps_password@103.118.16.189:5432/algochanakya
REDIS_URL=redis://103.118.16.189:6379/1
```

---

## Quick Test: Is Database Accessible?

Create a test script `backend/test_db.py`:

```python
import asyncio
import asyncpg

async def test_connection():
    try:
        # Update with your credentials
        conn = await asyncpg.connect(
            host='localhost',  # or 103.118.16.189
            port=5432,
            user='algochanakya_user',
            password='your_password',
            database='algochanakya'
        )
        print("✅ Database connection successful!")
        await conn.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

asyncio.run(test_connection())
```

Run it:
```bash
python backend/test_db.py
```

---

## Recommended Setup for Development

For local development, I recommend:

1. **Use Local PostgreSQL + Redis** (Option 1)
   - Faster development
   - No network issues
   - Can work offline
   - Easy to reset/test

2. **Use VPS for Production/Staging** (Option 2)
   - Keep production data separate
   - Deploy backend to VPS
   - Frontend can be on Vercel/Netlify

---

## Using Docker Compose (Easiest Option)

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: algochanakya-db
    environment:
      POSTGRES_DB: algochanakya
      POSTGRES_USER: algochanakya_user
      POSTGRES_PASSWORD: algochanakya_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    container_name: algochanakya-redis
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

Then:

```bash
# Start databases
docker-compose up -d

# Update .env
DATABASE_URL=postgresql+asyncpg://algochanakya_user:algochanakya_pass@localhost:5432/algochanakya
REDIS_URL=redis://localhost:6379/1

# Run migrations
cd backend
alembic upgrade head

# Start backend
python run.py
```

---

## What to Do Next?

Choose one of the options above based on your preference:

1. **Quick Start** → Use Docker Compose (if you have Docker installed)
2. **No Docker** → Install PostgreSQL + Redis locally (Option 1)
3. **Use VPS** → Configure VPS PostgreSQL to allow your IP (Option 2)

After setting up the database, run:

```bash
cd backend
alembic upgrade head  # Run migrations
python run.py         # Start backend
```

You should see:
```
[SUCCESS] AlgoChanakya backend started
[SUCCESS] Database: Connected to PostgreSQL
[SUCCESS] Redis: Connected
INFO:     Uvicorn running on http://0.0.0.0:8000
```
