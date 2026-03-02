# Development Setup Guide

## Overview

Complete guide to set up AlgoChanakya development environment on Windows/Linux/Mac.

## Prerequisites

- [ ] Node.js 18+
- [ ] Python 3.11+
- [ ] PostgreSQL 14+
- [ ] Redis 7+
- [ ] Git
- [ ] Zerodha Kite Connect API credentials

## Steps

### 1. Clone Repository

```bash
git clone https://github.com/abhayla/algochanakya.git
cd algochanakya
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your settings
```

### 3. Configure Environment Variables

Edit `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/algochanakya
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secure-random-string
JWT_EXPIRY_HOURS=8
KITE_API_KEY=your-kite-api-key
KITE_API_SECRET=your-kite-api-secret
FRONTEND_URL=http://localhost:5173
```

### 4. Database Setup

```bash
# Create database (PostgreSQL)
psql -U postgres -c "CREATE DATABASE algochanakya;"
psql -U postgres -c "CREATE USER algochanakya WITH PASSWORD 'your-password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE algochanakya TO algochanakya;"

# Run migrations
alembic upgrade head
```

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
```

Edit `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8001
VITE_WS_URL=localhost:8001
```

### 6. Start Development Servers

**Terminal 1 (Backend):**

```bash
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
python run.py
```

**Terminal 2 (Frontend):**

```bash
cd frontend
npm run dev
```

### 7. Access Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8001 |
| API Docs (Swagger) | http://localhost:8001/docs |
| API Docs (ReDoc) | http://localhost:8001/redoc |

## Verification

1. Open http://localhost:5173
2. Click "Login with Zerodha"
3. Complete OAuth flow (enter Zerodha credentials + TOTP)
4. Verify dashboard loads with navigation cards
5. Check backend logs for successful authentication

## Common Development Tasks

### Run Tests

```bash
# All tests
npm test

# Specific screen
npm run test:specs:positions

# With visible browser
npm run test:headed
```

### Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Add Python Dependency

```bash
cd backend
pip install package-name
pip freeze > requirements.txt
```

### Add Frontend Dependency

```bash
cd frontend
npm install package-name
```

## Production Build

### Build for Production

The frontend uses Vite's build mode which reads environment variables from `.env.production`:

```bash
cd frontend

# Create .env.production (REQUIRED for production builds)
echo "VITE_API_BASE_URL=https://algochanakya.com" > .env.production

# Build
npm run build
```

> **CRITICAL**: Without `.env.production`, the build defaults to `http://localhost:8001` (dev URL) and API calls will fail in production!

### Verify Production Build

```bash
# Check which API URL is baked into the build
grep -o "algochanakya.com\|localhost:8001" frontend/dist/assets/index-*.js | head -1

# Should output: algochanakya.com (NOT localhost:8001)
```

### Environment Files

| File | Purpose | Used When |
|------|---------|-----------|
| `.env` | Development defaults | `npm run dev` |
| `.env.local` | Local overrides (gitignored) | `npm run dev` |
| `.env.production` | Production values | `npm run build` |
| `.env.production.local` | Local prod overrides (gitignored) | `npm run build` |

Vite loads env files in this order (later files override earlier ones).

## Troubleshooting

See [Troubleshooting Guide](./troubleshooting.md) for common issues.

## AutoPilot Setup

After completing the basic setup, if you're working on the AutoPilot feature:

```bash
# Run AutoPilot database migration
cd backend
alembic upgrade head  # Includes 001_autopilot_initial.py

# Import Postman collection for API testing
# File: tests/postman/autopilot-collection.json
```

See [AutoPilot Documentation](../autopilot/README.md) for complete specs.

## Next Steps

- [Database Setup Details](./database-setup.md) - Advanced database configuration
- [Testing Guide](../testing/README.md) - E2E test architecture
- [Architecture Overview](../architecture/overview.md) - System design
- [AutoPilot Docs](../autopilot/README.md) - Auto-execution system specs
