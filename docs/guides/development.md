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
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=localhost:8000
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
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

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

## Troubleshooting

See [Troubleshooting Guide](./troubleshooting.md) for common issues.

## Next Steps

- [Database Setup Details](./database-setup.md) - Advanced database configuration
- [Testing Guide](../testing/README.md) - E2E test architecture
- [Architecture Overview](../architecture/overview.md) - System design
