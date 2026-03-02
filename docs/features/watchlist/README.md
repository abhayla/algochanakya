# Watchlist Feature - Implementation Summary

This document outlines the complete implementation of the Watchlist feature with Live Prices for AlgoChanakya.

## What Was Built

### Backend Components

#### 1. Database Models
- **Watchlist Model** (`backend/app/models/watchlists.py`)
  - Stores user watchlists with JSONB array of instruments
  - Supports up to 5 watchlists per user
  - Each watchlist can hold up to 100 instruments

- **Instrument Model** (`backend/app/models/instruments.py`)
  - Stores Kite instrument master data
  - Indexed on instrument_token, tradingsymbol, and exchange
  - Supports stocks, futures, and options

#### 2. Database Migration
- **Alembic Migration** (`backend/alembic/versions/4b82c9f6a120_add_watchlists_and_instruments_tables.py`)
  - Creates `watchlists` and `instruments` tables
  - Run migration: `alembic upgrade head`

#### 3. API Endpoints

**Watchlist Routes** (`backend/app/api/routes/watchlist.py`):
- `GET /api/watchlists` - Get all user watchlists
- `POST /api/watchlists` - Create new watchlist
- `PUT /api/watchlists/{id}` - Update watchlist
- `DELETE /api/watchlists/{id}` - Delete watchlist
- `POST /api/watchlists/{id}/instruments` - Add instrument
- `DELETE /api/watchlists/{id}/instruments/{token}` - Remove instrument

**Instrument Routes** (`backend/app/api/routes/instruments.py`):
- `GET /api/instruments/search?q=NIFTY` - Search instruments
- `GET /api/instruments/indices` - Get NIFTY 50 & BANK NIFTY tokens
- `POST /api/instruments/refresh` - Refresh instrument master

**WebSocket Route** (`backend/app/api/routes/websocket.py`):
- `WS /ws/ticks?token=JWT` - Live price streaming

#### 4. Services

**Instrument Service** (`backend/app/services/instruments.py`):
- Downloads Kite instrument master from API
- Parses and stores ~200,000 instruments in database
- Provides search functionality
- Caches data in Redis

**Kite Ticker Service** (`backend/app/services/kite_ticker.py`):
- Connects to Kite WebSocket for live market data
- Manages subscriptions to instrument tokens
- Broadcasts ticks to connected clients
- Auto-reconnects on disconnect

### Frontend Components

#### 1. Pinia Store
**Watchlist Store** (`frontend/src/stores/watchlist.js`):
- Manages watchlist state
- Handles WebSocket connections
- Subscribes/unsubscribes to instrument tokens
- Stores live tick data
- Provides computed properties for active instruments

#### 2. Vue Components

**IndexHeader** (`frontend/src/components/watchlist/IndexHeader.vue`):
- Shows NIFTY 50 & NIFTY BANK prices
- Live price updates with color coding
- Connection status indicator

**InstrumentRow** (`frontend/src/components/watchlist/InstrumentRow.vue`):
- Displays instrument with LTP, change, change %
- Click to expand for Buy/Sell/Chart/Option Chain/Delete
- Color coding (green for positive, red for negative)

**InstrumentSearch** (`frontend/src/components/watchlist/InstrumentSearch.vue`):
- Search modal with debounced search (300ms)
- Filter by All/Cash/F&O
- Shows "Already Added" badge
- Click to add instruments to watchlist

**WatchlistView** (`frontend/src/views/WatchlistView.vue`):
- Main watchlist page
- Tabbed interface for multiple watchlists
- Empty state with "Add Instruments" CTA
- List of instruments with live prices

#### 3. Router Updates
- `/watchlist` route added
- Made default route after login
- Protected with authentication guard

## How to Set Up and Test

### Step 1: Run Database Migration

```bash
cd backend
alembic upgrade head
```

### Step 2: Download Instrument Master (Optional - happens automatically)

The instrument master will be downloaded on first search. To manually download:

```bash
# Start backend server first
cd backend
python run.py
```

Then in another terminal:
```bash
curl -X POST http://localhost:8001/api/instruments/refresh \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Step 3: Start Backend Server

```bash
cd backend
python run.py
```

Backend will run at: http://localhost:8001

### Step 4: Start Frontend Server

```bash
cd frontend
npm run dev
```

Frontend will run at: http://localhost:5174

### Step 5: Test the Feature

1. **Login**: Go to http://localhost:5174 and login with Zerodha
2. **Watchlist Page**: After login, you'll be redirected to `/watchlist`
3. **Index Header**: Check NIFTY 50 & NIFTY BANK showing "---" (will update once instruments are added)
4. **Add Instruments**:
   - Click "+ Add Instrument"
   - Search for "NIFTY" or "RELIANCE"
   - Click "+ Add" to add to watchlist
5. **Live Prices**: Watch the WebSocket connect and prices start updating
6. **Multiple Watchlists**: Click "+ Add Watchlist" to create more
7. **Remove Instrument**: Click on an instrument row to expand, then "✕ Remove"

## WebSocket Flow

1. **Connection**: Frontend connects to `ws://localhost:8001/ws/ticks?token=JWT`
2. **Authentication**: Server validates JWT token
3. **Kite Connect**: Server connects to Kite WebSocket with broker access token
4. **Subscribe**: Frontend sends `{"action": "subscribe", "tokens": [256265]}`
5. **Broadcast**: Server receives ticks from Kite and broadcasts to frontend
6. **Update UI**: Frontend updates tick data in Pinia store, Vue components react

## Data Flow

```
Zerodha Kite API
     ↓
Kite WebSocket (backend/app/services/kite_ticker.py)
     ↓
Backend WebSocket (backend/app/api/routes/websocket.py)
     ↓
Frontend WebSocket (frontend/src/stores/watchlist.js)
     ↓
Vue Components (IndexHeader, InstrumentRow)
```

## Environment Variables Needed

### Backend (.env)
```env
# Already configured
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
KITE_API_KEY=dh9lojp9j9tnq3h4
KITE_API_SECRET=99q72gnpothxdsi3jo0o789dvyt6rco3
```

### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8001
VITE_WS_URL=localhost:8001  # WebSocket URL (without protocol)
```

## Known Limitations & Future Enhancements

### Current Limitations:
1. Instrument master must be downloaded manually (can be automated with cron job)
2. WebSocket reconnection uses simple retry logic (can be improved with exponential backoff)
3. Buy/Sell/Chart/Option Chain buttons are placeholders
4. No drag-and-drop reordering of instruments yet
5. Max 100 instruments per watchlist (Kite limit: 3000 tokens per connection)

### Future Enhancements:
1. **Scheduled Instrument Refresh**: Auto-refresh instrument master daily at 8 AM IST
2. **Better Error Handling**: Toast notifications for errors
3. **Drag-and-Drop**: Reorder instruments within watchlist
4. **Multiple Broker Support**: Add Upstox, Angel One, Fyers
5. **Advanced Features**:
   - Option Chain view
   - Chart integration
   - Order placement (Buy/Sell)
   - Market depth
   - Historical data
6. **Performance**:
   - Virtual scrolling for large watchlists
   - Optimized WebSocket message handling
7. **User Experience**:
   - Keyboard shortcuts
   - Right-click context menu
   - Customizable columns

## Troubleshooting

### Issue: WebSocket not connecting
**Solution**: Check if access token is valid. Kite tokens expire daily at 7:30 AM IST.

### Issue: No live prices showing
**Solution**:
1. Check WebSocket connection status in IndexHeader (green dot = connected)
2. Verify instruments are subscribed (check browser console)
3. Check if market is open (9:15 AM - 3:30 PM IST on weekdays)

### Issue: Search returns no results
**Solution**: Instrument master needs to be downloaded. Click "Refresh" in instruments API.

### Issue: Database connection error during migration
**Solution**: VPS PostgreSQL needs to whitelist your IP address in pg_hba.conf

### Issue: CORS errors
**Solution**: Ensure CORS_ORIGINS in backend config includes your frontend URL

## Files Created/Modified

### Backend Files Created:
- `backend/app/models/watchlists.py`
- `backend/app/models/instruments.py`
- `backend/app/schemas/watchlists.py`
- `backend/app/schemas/instruments.py`
- `backend/app/services/instruments.py`
- `backend/app/services/kite_ticker.py`
- `backend/app/api/routes/watchlist.py`
- `backend/app/api/routes/instruments.py`
- `backend/app/api/routes/websocket.py`
- `backend/alembic/versions/4b82c9f6a120_add_watchlists_and_instruments_tables.py`

### Backend Files Modified:
- `backend/app/models/__init__.py`
- `backend/app/schemas/__init__.py`
- `backend/app/main.py`
- `backend/alembic/env.py`

### Frontend Files Created:
- `frontend/src/stores/watchlist.js`
- `frontend/src/components/watchlist/IndexHeader.vue`
- `frontend/src/components/watchlist/InstrumentRow.vue`
- `frontend/src/components/watchlist/InstrumentSearch.vue`
- `frontend/src/views/WatchlistView.vue`

### Frontend Files Modified:
- `frontend/src/router/index.js`
- `frontend/src/views/AuthCallbackView.vue`

## Next Steps

1. **Test End-to-End**: Login → Add Instruments → Verify Live Prices
2. **Run Migrations**: Apply database migrations on VPS
3. **Deploy**: Deploy backend and frontend to production
4. **Monitor**: Check logs for WebSocket connections and tick updates
5. **Iterate**: Gather user feedback and implement enhancements

## Support

For issues or questions:
- Check browser console for errors
- Check backend logs for API errors
- Verify Kite API credentials are correct
- Ensure database and Redis are accessible
