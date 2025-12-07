# WebSocket Live Prices

AlgoChanakya streams live market prices via WebSocket, connecting to Zerodha's Kite WebSocket for real-time tick data.

## Architecture

```
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│    Browser     │    │    Backend     │    │  Kite WebSocket│
│   (Vue App)    │    │   (FastAPI)    │    │   (Zerodha)    │
└───────┬────────┘    └───────┬────────┘    └───────┬────────┘
        │                     │                     │
        │ ws://localhost:8000 │                     │
        │  /ws/ticks?token=   │                     │
        │─────────────────────>                     │
        │                     │                     │
        │                     │ Validate JWT        │
        │                     │ Get Kite token      │
        │                     │                     │
        │                     │ Connect (singleton) │
        │                     │─────────────────────>
        │                     │                     │
        │ {"action":"subscribe"                     │
        │  "tokens":[256265]} │                     │
        │─────────────────────>                     │
        │                     │                     │
        │                     │ Subscribe to tokens │
        │                     │─────────────────────>
        │                     │                     │
        │                     │    Tick data        │
        │                     │<─────────────────────
        │                     │                     │
        │  {"type":"ticks",   │                     │
        │   "data":[...]}     │                     │
        │<─────────────────────                     │
        │                     │                     │
```

## Connection Flow

1. **Frontend connects** to `ws://localhost:8000/ws/ticks?token=<jwt>`
2. **Backend authenticates** JWT and retrieves user's Kite access token
3. **KiteTickerService** connects to Kite WebSocket (singleton - one connection for all users)
4. **Client subscribes** with message: `{"action": "subscribe", "tokens": [256265], "mode": "quote"}`
5. **Service broadcasts** relevant ticks to subscribed clients

## KiteTickerService

Singleton service managing the Kite WebSocket connection.

### Features

| Feature | Description |
|---------|-------------|
| **Singleton** | Single connection shared by all users |
| **Thread-safe** | Uses `asyncio.run_coroutine_threadsafe` for async broadcast |
| **Per-user subscriptions** | Only sends ticks user subscribed to |
| **Auto-reconnect** | Reconnects automatically on disconnect |
| **Tick caching** | Caches latest ticks for immediate delivery |

### Implementation

```python
# app/services/kite_ticker.py

class KiteTickerService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self, access_token: str):
        """Connect to Kite WebSocket"""
        ...

    async def subscribe(self, client_id: str, tokens: list, mode: str):
        """Subscribe client to instrument tokens"""
        ...

    async def broadcast_tick(self, tick: dict):
        """Broadcast tick to subscribed clients"""
        ...
```

## Message Types

### Client → Server

```javascript
// Subscribe to instruments
{
  "action": "subscribe",
  "tokens": [256265, 260105],
  "mode": "quote"  // or "full", "ltp"
}

// Unsubscribe
{
  "action": "unsubscribe",
  "tokens": [256265]
}

// Keepalive
{
  "action": "ping"
}
```

### Server → Client

```javascript
// Connection confirmed
{
  "type": "connected",
  "message": "WebSocket connected"
}

// Subscription confirmed
{
  "type": "subscribed",
  "tokens": [256265, 260105]
}

// Live tick data
{
  "type": "ticks",
  "data": [
    {
      "token": 256265,
      "ltp": 24500.50,
      "change": 125.30,
      "change_percent": 0.51,
      "volume": 1234567,
      "oi": 9876543,
      "bid": 24499.50,
      "ask": 24501.00,
      "timestamp": "2024-12-07T10:30:00"
    }
  ]
}

// Keepalive response
{
  "type": "pong"
}

// Error
{
  "type": "error",
  "message": "Invalid token format"
}
```

## Index Tokens

| Index | Token | Symbol |
|-------|-------|--------|
| NIFTY 50 | `256265` | NSE:NIFTY 50 |
| NIFTY BANK | `260105` | NSE:NIFTY BANK |
| FINNIFTY | `257801` | NSE:NIFTY FIN SERVICE |

## Subscription Modes

| Mode | Data Included |
|------|---------------|
| `ltp` | Last traded price only |
| `quote` | LTP + OHLC + volume + bid/ask |
| `full` | Quote + market depth |

## Frontend Usage

```javascript
// stores/watchlist.js

const ws = new WebSocket(`ws://localhost:8000/ws/ticks?token=${token}`)

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    tokens: [256265, 260105],
    mode: 'quote'
  }))
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'ticks') {
    updatePrices(data.data)
  }
}
```

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `Invalid JWT` | Expired/invalid token | Re-authenticate |
| `No broker connection` | User not logged in | Redirect to login |
| `Kite disconnected` | Network issue | Auto-reconnect |
| `Invalid token` | Wrong instrument token | Check token format |

## Implementation Files

| File | Purpose |
|------|---------|
| `backend/app/services/kite_ticker.py` | KiteTickerService singleton |
| `backend/app/api/routes/websocket.py` | WebSocket endpoint |
| `frontend/src/stores/watchlist.js` | WebSocket client logic |

## LTP Fallback

When WebSocket is unavailable, use HTTP endpoint:

```http
GET /api/orders/ltp?instruments=NFO:NIFTY24DEC24500CE,NFO:NIFTY24DEC24500PE
Authorization: Bearer <token>
```

## Related Documentation

- [Overview](overview.md) - System architecture
- [Authentication](authentication.md) - JWT tokens
