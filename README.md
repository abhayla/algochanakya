# AlgoChanakya

Options Trading Platform (like Sensibull) - A comprehensive platform for options trading strategies, market analysis, and portfolio management.

## Documentation

Comprehensive documentation is available in the [docs/](docs/README.md) folder:

- **[Architecture](docs/architecture/)** - System design, authentication, WebSocket, database
- **[API Reference](docs/api/)** - Endpoint documentation and OpenAPI spec
- **[Guides](docs/guides/)** - Setup, database configuration, troubleshooting
- **[Testing](docs/testing/)** - E2E test architecture (~184 test files: 121 E2E + 63 backend)

## Tech Stack

- **Frontend**: Vue.js 3 + Vite + Tailwind CSS + Pinia + Vue Router
- **Backend**: FastAPI + Python 3.11+
- **Database**: PostgreSQL (VPS Server)
- **Cache**: Redis (VPS Server)
- **Broker Integration**: Zerodha Kite Connect API

## Project Structure

```
algochanakya/
├── docs/               # Documentation
│   ├── architecture/   # System design docs
│   ├── api/            # API reference
│   ├── guides/         # Setup guides
│   ├── features/       # Feature documentation
│   ├── testing/        # Test architecture
│   └── decisions/      # Architecture Decision Records
├── frontend/           # Vue.js 3 frontend application
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   ├── services/
│   │   └── router/
│   └── package.json
├── backend/            # FastAPI backend application
│   ├── app/
│   │   ├── api/routes/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── alembic/        # Database migrations
│   └── requirements.txt
├── tests/              # Playwright E2E tests
├── CHANGELOG.md        # Version history
└── README.md
```

## Setup Instructions

### Prerequisites

- Node.js 20+
- Python 3.11+
- Git

### Backend Setup

1. Navigate to backend directory:
   ```bash
   cd backend
   ```

2. Create and activate virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update database and Redis credentials

5. Start the backend server:
   ```bash
   python run.py
   ```
   Backend will run at: http://localhost:8001 (dev) or http://localhost:8000 (prod)

### Frontend Setup

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update API base URL if needed

4. Start the development server:
   ```bash
   npm run dev
   ```
   Frontend will run at: http://localhost:5173

## API Endpoints

- **Health Check**: GET `/api/health` - Check backend, database, and Redis connectivity
- **Broker Login**: POST `/api/auth/broker/login` - Initiate broker OAuth flow
- **Broker Callback**: GET `/api/auth/broker/callback` - Handle broker OAuth callback
- **Logout**: POST `/api/auth/logout` - User logout

## Remote Database Configuration

The application uses remote PostgreSQL and Redis servers:

- **PostgreSQL**: 103.118.16.189:5432
- **Redis**: 103.118.16.189:6379

## Development

### Backend Commands

```bash
# Start backend server
cd backend
python run.py

# Or with uvicorn directly
uvicorn app.main:app --reload

# Install new dependency
pip install <package>
pip freeze > requirements.txt
```

### Frontend Commands

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Features

### Implemented

- **Broker Authentication** - Zerodha Kite Connect OAuth
- **Watchlist** - Real-time price streaming via WebSocket
- **Option Chain** - Full chain with OI, IV, Greeks, Max Pain
- **Strategy Builder** - P/L calculator, payoff charts, breakeven analysis
- **Positions** - Live F&O positions with P&L tracking
- **Order Placement** - Basket orders via Kite API

### In Progress

- **Multi-broker abstraction** - SmartAPI (Angel One) implemented for market data, Kite for orders
- Additional brokers planned: Upstox, Fyers, Dhan
- Backtesting capabilities
- Advanced risk management tools

## Contributing

This is a private project. For any questions or issues, contact the development team.

## License

Proprietary - All rights reserved
