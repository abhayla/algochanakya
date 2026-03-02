# AlgoChanakya Backend

FastAPI backend for the AlgoChanakya options trading platform.

## Tech Stack

- **FastAPI** - Modern async web framework
- **SQLAlchemy** - Async ORM with PostgreSQL
- **Redis** - Session storage and caching
- **Kite Connect** - Zerodha broker integration
- **Alembic** - Database migrations

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate (Windows)
venv\Scripts\activate
# Or (Linux/Mac)
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 5. Run migrations
alembic upgrade head

# 6. Start server
python run.py
```

Server runs at: http://localhost:8001

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan
│   ├── config.py            # Pydantic Settings
│   ├── database.py          # SQLAlchemy engine, Redis pool
│   │
│   ├── api/routes/          # API endpoints
│   │   ├── auth.py          # Zerodha OAuth
│   │   ├── watchlist.py     # Watchlist CRUD
│   │   ├── instruments.py   # Instrument search
│   │   ├── options.py       # Expiries, strikes, chain
│   │   ├── optionchain.py   # Full chain with OI, IV, Greeks
│   │   ├── strategy.py      # Strategy CRUD, P/L calc
│   │   ├── orders.py        # Basket orders, positions
│   │   ├── positions.py     # F&O positions, exit/add
│   │   ├── websocket.py     # Live price streaming
│   │   └── health.py        # Health check
│   │
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── users.py         # User accounts
│   │   ├── broker_connections.py  # Broker tokens
│   │   ├── watchlists.py    # User watchlists
│   │   ├── instruments.py   # Master instruments
│   │   └── strategies.py    # Strategies & legs
│   │
│   ├── schemas/             # Pydantic schemas
│   │   └── ...              # Request/response models
│   │
│   ├── services/            # Business logic
│   │   ├── kite_ticker.py   # WebSocket price streaming
│   │   ├── kite_orders.py   # Order placement
│   │   ├── pnl_calculator.py # Black-Scholes P/L
│   │   └── instruments.py   # Instrument data
│   │
│   └── utils/               # Utilities
│       ├── jwt.py           # JWT handling
│       └── dependencies.py  # FastAPI dependencies
│
├── alembic/                 # Database migrations
├── requirements.txt         # Python dependencies
└── run.py                   # Development server
```

## Development Commands

```bash
# Start development server
python run.py

# Or with uvicorn directly
uvicorn app.main:app --reload

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Install new dependency
pip install <package>
pip freeze > requirements.txt
```

## Environment Variables

Create `.env` from `.env.example`:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection (postgresql+asyncpg://...) |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET` | Secret for JWT signing |
| `JWT_EXPIRY_HOURS` | Token expiry (default: 8) |
| `KITE_API_KEY` | Zerodha API key |
| `KITE_API_SECRET` | Zerodha API secret |
| `FRONTEND_URL` | Frontend URL for CORS/redirects |

## API Documentation

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json

## Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/auth/zerodha/login` | GET | Initiate OAuth |
| `/api/auth/zerodha/callback` | GET | OAuth callback |
| `/api/watchlist` | GET/POST | Watchlist CRUD |
| `/api/instruments/search` | GET | Search instruments |
| `/api/optionchain/chain` | GET | Full option chain |
| `/api/strategies` | GET/POST | Strategy CRUD |
| `/api/strategies/calculate` | POST | P/L calculation |
| `/api/positions` | GET | F&O positions |
| `/ws/ticks` | WebSocket | Live prices |

## Adding New Features

### New Model

1. Create in `app/models/<name>.py`
2. Import in `app/models/__init__.py`
3. Import in `alembic/env.py`
4. Generate migration: `alembic revision --autogenerate -m "add <name>"`
5. Apply: `alembic upgrade head`

### New API Route

1. Create in `app/api/routes/<name>.py`
2. Define `router = APIRouter()`
3. Include in `app/main.py`

## Testing

```bash
# Run from project root
npm test

# Or specific tests
npm run test:api:new
npm run test:specs:positions
```

## Documentation

- [Architecture Overview](../docs/architecture/overview.md)
- [Database Models](../docs/architecture/database.md)
- [API Reference](../docs/api/README.md)
- [Troubleshooting](../docs/guides/troubleshooting.md)
