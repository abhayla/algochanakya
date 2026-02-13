# Paytm Money WebSocket Protocol

## Connection

**URL:** `wss://developer-ws.paytmmoney.com/broadcast/user/v1/data?x_jwt_token={public_access_token}`

> **IMPORTANT:** Requires `public_access_token` (not `access_token` or `read_access_token`).

| Limit | Value |
|-------|-------|
| Max concurrent connections | 1 per API key |
| Max subscribed instruments | 200 |
| Reconnect behavior | Manual (no auto-reconnect from server) |
| Heartbeat/ping | Client should send ping every 30s |

## Subscription Messages (JSON)

### Subscribe / Unsubscribe / Change Mode

```json
{"actionType": "ADD",         "modeType": "LTP",  "scripType": "EQUITY", "exchangeType": "NSE", "scripId": "500325"}
{"actionType": "REMOVE",      "modeType": "LTP",  "scripType": "EQUITY", "exchangeType": "NSE", "scripId": "500325"}
{"actionType": "CHANGE_MODE", "modeType": "FULL", "scripType": "EQUITY", "exchangeType": "NSE", "scripId": "500325"}
```

### Request Fields

| Field | Values | Description |
|-------|--------|-------------|
| `actionType` | `ADD`, `REMOVE`, `CHANGE_MODE` | Subscription action |
| `modeType` | `LTP`, `FULL` | Data depth mode |
| `scripType` | `EQUITY`, `DERIVATIVE`, `INDEX` | Instrument category |
| `exchangeType` | `NSE`, `BSE` | Exchange identifier |
| `scripId` | e.g. `"500325"` | Paytm security_id |

### Modes

| Mode | Fields Received | Use Case |
|------|----------------|----------|
| `LTP` | last_price, change, change_pct | Watchlist, lightweight monitoring |
| `FULL` | last_price, ohlc, volume, bid/ask, oi, timestamps | Option chain, strategy builder |

## Tick Data (Received)

```json
// LTP mode
{"type": "tick", "data": {"security_id": "500325", "exchange": "NSE", "last_price": 1825.50, "change": 7.25, "change_pct": 0.40}}

// FULL mode
{"type": "tick", "data": {"security_id": "500325", "exchange": "NSE", "last_price": 1825.50,
  "open": 1820.00, "high": 1830.00, "low": 1815.00, "close": 1818.25, "change": 7.25,
  "change_pct": 0.40, "volume": 1234567, "oi": 0, "oi_change": 0,
  "bid_price": 1825.45, "bid_qty": 100, "ask_price": 1825.55, "ask_qty": 150,
  "last_trade_time": "2024-01-15T10:30:15", "exchange_timestamp": "2024-01-15T10:30:15"}}
```

### Connection Events

```json
{"type": "connected", "message": "Connection established"}
{"type": "subscribed", "security_id": "500325", "mode": "LTP"}
{"type": "error", "message": "Invalid security_id", "code": 4001}
{"type": "close", "code": 1000, "reason": "Session expired"}
```

## Batch Subscription

```json
[
  {"actionType": "ADD", "modeType": "FULL", "scripType": "INDEX", "exchangeType": "NSE", "scripId": "999920000"},
  {"actionType": "ADD", "modeType": "LTP", "scripType": "EQUITY", "exchangeType": "NSE", "scripId": "500325"},
  {"actionType": "ADD", "modeType": "FULL", "scripType": "DERIVATIVE", "exchangeType": "NSE", "scripId": "46498"}
]
```

## Python Client Example

```python
import asyncio, json, websockets

class PaytmTickerClient:
    WS_URL = "wss://developer-ws.paytmmoney.com/broadcast/user/v1/data"
    MAX_INSTRUMENTS = 200

    def __init__(self, public_access_token: str):
        self.token = public_access_token
        self.ws = None
        self._subscriptions: set[str] = set()

    async def connect(self):
        self.ws = await websockets.connect(f"{self.WS_URL}?x_jwt_token={self.token}")
        asyncio.create_task(self._ping_loop())

    async def subscribe(self, security_id: str, exchange="NSE", scrip_type="EQUITY", mode="LTP"):
        if len(self._subscriptions) >= self.MAX_INSTRUMENTS:
            raise ValueError(f"Max {self.MAX_INSTRUMENTS} instruments")
        await self.ws.send(json.dumps({"actionType": "ADD", "modeType": mode,
            "scripType": scrip_type, "exchangeType": exchange, "scripId": security_id}))
        self._subscriptions.add(security_id)

    async def unsubscribe(self, security_id: str, exchange="NSE", scrip_type="EQUITY", mode="LTP"):
        await self.ws.send(json.dumps({"actionType": "REMOVE", "modeType": mode,
            "scripType": scrip_type, "exchangeType": exchange, "scripId": security_id}))
        self._subscriptions.discard(security_id)

    async def listen(self):
        async for message in self.ws:
            yield json.loads(message)

    async def _ping_loop(self):
        while self.ws and self.ws.open:
            await asyncio.sleep(30)
            try: await self.ws.ping()
            except Exception: break

    async def close(self):
        if self.ws: await self.ws.close()
```

## AlgoChanakya TickerServiceBase Mapping

| TickerServiceBase Method | Paytm Implementation |
|--------------------------|---------------------|
| `connect()` | Open WebSocket with `public_access_token` |
| `subscribe(tokens, mode)` | Send `ADD` messages; map tokens via `TokenManager` |
| `unsubscribe(tokens)` | Send `REMOVE` messages |
| `on_tick(callback)` | Register callback for `type: "tick"` messages |
| `on_connect(callback)` | Register callback for `type: "connected"` |
| `on_error(callback)` | Register callback for `type: "error"` |
| `close()` | Close WebSocket |

**Mode mapping:** `ltp` -> `LTP`, `quote` -> `FULL`, `full` -> `FULL`

**Token conversion:** Use `TokenManager` to convert canonical Kite tokens to Paytm `scripId`:
```python
paytm_id = await token_manager.get_broker_token(256265, "paytm")  # "999920000"
```

> **MATURITY WARNING:** The Paytm WebSocket has been observed disconnecting without a close
> frame during high-volatility periods. Implement reconnection with exponential backoff
> (initial 1s, max 30s).
