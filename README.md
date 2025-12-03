# AlgoChanakya

Options Trading Platform (like Sensibull) - A comprehensive platform for options trading strategies, market analysis, and portfolio management.

## Tech Stack

- **Frontend**: Vue.js 3 + Vite + Tailwind CSS + Pinia + Vue Router
- **Backend**: FastAPI + Python 3.11+
- **Database**: PostgreSQL (VPS Server)
- **Cache**: Redis (VPS Server)
- **Broker Integration**: Zerodha Kite Connect API

## Project Structure

```
algochanakya/
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
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── requirements.txt
│   └── run.py
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
   Backend will run at: http://localhost:8000

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

## Features (Planned)

- Broker authentication (Zerodha, Upstox, Angel One, Fyers)
- Options chain visualization
- Strategy builder (Straddle, Strangle, Iron Condor, etc.)
- Real-time market data
- Portfolio tracking
- P&L analysis
- Risk management tools
- Backtesting capabilities

## Contributing

This is a private project. For any questions or issues, contact the development team.

## License

Proprietary - All rights reserved
