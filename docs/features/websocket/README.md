# WebSocket Live Data Streaming

## Overview

Real-time market data streaming service using WebSocket connections to Zerodha Kite Connect. Provides live price updates for indices and instruments across multiple features.

## Features

- **Real-time Tick Data**: Live LTP, change%, volume
- **Kite WebSocket Integration**: Direct connection to Kite streaming API
- **Multi-user Support**: Per-user subscription management
- **Auto Reconnection**: Automatic reconnect on disconnect
- **Tick Caching**: Latest ticks cached for immediate delivery on subscribe

## Used By Features

- Watchlist - Live instrument prices
- Positions - Real-time P&L calculation
- Option Chain - Live option prices
- Strategy Builder - Current Market Price (CMP)
- AutoPilot - Position monitoring and condition evaluation

## Technical Implementation

### Backend

**WebSocket Route:**
- `WS /ws/ticks?token={jwt}` - WebSocket connection endpoint

**Kite Ticker Service** (`app/services/kite_ticker.py`):
- Singleton service managing Kite WebSocket connection
- Thread-safe async tick broadcasting using `asyncio.run_coroutine_threadsafe`
- Per-user subscription tracking
- Automatic reconnection on disconnect
- Tick caching for instant delivery

**Message Types:**

| Type | Direction | Description |
|------|-----------|-------------|
| `connected` | Server → Client | Connection confirmation |
| `subscribe` | Client → Server | Subscribe to tokens |
| `subscribed` | Server → Client | Subscription confirmation |
| `ticks` | Server → Client | Live price data |
| `ping` | Client → Server | Keepalive |
| `pong` | Server → Client | Keepalive response |
| `error` | Server → Client | Error messages |

**Subscribe Message Format:**
```json
{
  "action": "subscribe",
  "tokens": [256265, 260105],
  "mode": "quote"
}
```

**Tick Data Format:**
```json
{
  "type": "ticks",
  "data": [{
    "token": 256265,
    "ltp": 24567.80,
    "change": 123.45,
    "change_percent": 0.50,
    "volume": 1234567,
    ...
  }]
}
```

### Frontend

**WebSocket Usage:**

Each store manages its own WebSocket connection:

```javascript
// In store
const ws = new WebSocket(`ws://localhost:8000/ws/ticks?token=${token}`)

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    tokens: [256265],
    mode: 'quote'
  }))
}

ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  if (message.type === 'ticks') {
    updatePrices(message.data)
  }
}
```

## Index Tokens

| Index | Token |
|-------|-------|
| NIFTY 50 | 256265 |
| NIFTY BANK | 260105 |
| FINNIFTY | 257801 |
| SENSEX | 265 |

## Configuration

**Subscription Modes:**
- `quote` - LTP, volume, OI, change (recommended)
- `ltp` - Last Traded Price only
- `full` - Complete market depth

**Max Tokens per Connection:**
- 3000 tokens (Kite limit)

## Related

- [WebSocket Architecture](../../architecture/websocket.md) - Detailed WebSocket flow
- [Kite Ticker Service](../../architecture/kite-ticker-service.md) - Service implementation
