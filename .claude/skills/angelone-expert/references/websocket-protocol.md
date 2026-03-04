# SmartAPI WebSocket V2 Protocol

Complete WebSocket binary protocol reference for Angel One SmartAPI.

## Connection

### URL Format

```
wss://smartapisocket.angelone.in/smart-stream
  ?clientCode={client_id}
  &feedToken={feed_token}
  &apiKey={api_key}
```

### Connection Parameters

| Parameter | Source | Example |
|-----------|--------|---------|
| `clientCode` | Angel One client ID | `A12345` |
| `feedToken` | From login response `data.feedToken` | `eyJ...` |
| `apiKey` | From Angel One developer dashboard | `abc123` |

### Connection Limits

| Limit | Value |
|-------|-------|
| Max connections per client | **3** |
| Max tokens per connection | **3000** |
| Heartbeat interval | **30 seconds** |
| Reconnect backoff | Exponential (1s, 2s, 4s, 8s, max 30s) |

## Subscription

### Subscribe Request (JSON)

```json
{
  "action": 1,
  "params": {
    "mode": 2,
    "tokenList": [
      {
        "exchangeType": 2,
        "tokens": ["99926000", "12345", "67890"]
      }
    ]
  }
}
```

### Unsubscribe Request

```json
{
  "action": 2,
  "params": {
    "mode": 2,
    "tokenList": [
      {
        "exchangeType": 2,
        "tokens": ["12345"]
      }
    ]
  }
}
```

### Heartbeat (Send every 30 seconds)

```json
{
  "action": 3,
  "params": {}
}
```

### Action Codes

| Code | Action |
|------|--------|
| `1` | Subscribe |
| `2` | Unsubscribe |
| `3` | Heartbeat / Ping |

## Exchange Segment Codes

| Exchange | Code | Description |
|----------|------|-------------|
| `nse_cm` | `1` | NSE Cash Market (Equity) |
| `nse_fo` | `2` | NSE Futures & Options |
| `bse_cm` | `3` | BSE Cash Market |
| `bse_fo` | `4` | BSE Futures & Options |
| `mcx_fo` | `5` | MCX Commodities F&O |
| `ncx_fo` | `7` | NCX |
| `cde_fo` | `13` | CDE |

**Important:** Exchange type must match the token's actual exchange. Sending an NSE token with `exchangeType: 2` (NFO) will produce no data or incorrect data.

## Subscription Modes

| Mode | Code | Description | Approx Size |
|------|------|-------------|-------------|
| **LTP** | `1` | Last traded price only | ~50 bytes |
| **Quote** | `2` | OHLC, volume, OI, best bid/ask | ~130 bytes |
| **Snap Quote** | `3` | Full 5-level depth + all fields | ~450 bytes |

## Binary Message Format

All responses are **binary** (not JSON). Parse using `struct.unpack()`.

### Common Header (First 2 bytes of every message)

| Offset | Bytes | Type | Field |
|--------|-------|------|-------|
| 0 | 1 | uint8 | Subscription Mode (1=LTP, 2=Quote, 3=Snap) |
| 1 | 1 | uint8 | Exchange Type |

### Token Identification (Bytes 2-26)

| Offset | Bytes | Type | Field |
|--------|-------|------|-------|
| 2 | 25 | char[25] | Token (null-padded string) |

### LTP Mode (Mode 1) - After Header

| Offset | Bytes | Type | Field | Notes |
|--------|-------|------|-------|-------|
| 0 | 1 | uint8 | Mode (=1) | |
| 1 | 1 | uint8 | Exchange Type | |
| 2 | 25 | char[25] | Token | Null-padded |
| 27 | 1 | uint8 | Sequence Number | |
| 28 | 4 | int32 | Exchange Timestamp | Epoch seconds |
| 32 | 4 | int32 | **LTP** | **In PAISE** |

**Total: ~36 bytes**

### Quote Mode (Mode 2) - After Header

| Offset | Bytes | Type | Field | Notes |
|--------|-------|------|-------|-------|
| 0-35 | 36 | - | Same as LTP | All LTP fields |
| 36 | 4 | int32 | Last Traded Quantity | |
| 40 | 4 | int32 | Average Traded Price | In PAISE |
| 44 | 4 | int32 | Total Volume | |
| 48 | 4 | int32 | Total Buy Quantity | |
| 52 | 4 | int32 | Total Sell Quantity | |
| 56 | 4 | int32 | **Open** | **In PAISE** |
| 60 | 4 | int32 | **High** | **In PAISE** |
| 64 | 4 | int32 | **Low** | **In PAISE** |
| 68 | 4 | int32 | **Close** | **In PAISE** |
| 72 | 4 | int32 | Last Traded Timestamp | Epoch seconds |
| 76 | 4 | int32 | Open Interest | |
| 80 | 4 | int32 | OI Change % | Scaled |
| 84 | 20 | - | Best Bid/Ask | 4 bytes each: price, qty |

**Total: ~104 bytes**

### Snap Quote Mode (Mode 3) - After Quote Fields

Extends Quote mode with 5-level market depth:

| Offset | Bytes | Type | Field | Notes |
|--------|-------|------|-------|-------|
| 0-103 | 104 | - | Same as Quote | All Quote fields |
| 104+ | 200 | - | Buy Depth (5 levels) | Each: price(4), qty(4), orders(4), padding(4) × 5 |
| 184+ | 200 | - | Sell Depth (5 levels) | Same as Buy Depth |
| 384 | 4 | int32 | Upper Circuit | In PAISE |
| 388 | 4 | int32 | Lower Circuit | In PAISE |
| 392 | 4 | int32 | 52 Week High | In PAISE |
| 396 | 4 | int32 | 52 Week Low | In PAISE |

**Total: ~400+ bytes**

### Depth Level Structure (per level)

| Offset | Bytes | Type | Field |
|--------|-------|------|-------|
| 0 | 4 | int32 | Price (PAISE) |
| 4 | 4 | int32 | Quantity |
| 8 | 2 | int16 | Number of Orders |
| 10 | 2 | - | Padding |

## Parsing Example (Python)

```python
import struct

def parse_smartapi_tick(data: bytes) -> dict:
    """Parse SmartAPI V2 binary tick data."""
    mode = struct.unpack('B', data[0:1])[0]
    exchange_type = struct.unpack('B', data[1:2])[0]
    token = data[2:27].decode('utf-8').rstrip('\x00')
    sequence = struct.unpack('B', data[27:28])[0]
    exchange_ts = struct.unpack('>i', data[28:32])[0]

    # LTP is always present (PAISE - divide by 100!)
    ltp_paise = struct.unpack('>i', data[32:36])[0]
    ltp = ltp_paise / 100.0

    result = {
        'mode': mode,
        'exchange_type': exchange_type,
        'token': token,
        'ltp': ltp,
        'exchange_timestamp': exchange_ts,
    }

    if mode >= 2:  # Quote mode
        result.update({
            'last_traded_qty': struct.unpack('>i', data[36:40])[0],
            'avg_traded_price': struct.unpack('>i', data[40:44])[0] / 100.0,
            'volume': struct.unpack('>i', data[44:48])[0],
            'total_buy_qty': struct.unpack('>i', data[48:52])[0],
            'total_sell_qty': struct.unpack('>i', data[52:56])[0],
            'open': struct.unpack('>i', data[56:60])[0] / 100.0,
            'high': struct.unpack('>i', data[60:64])[0] / 100.0,
            'low': struct.unpack('>i', data[64:68])[0] / 100.0,
            'close': struct.unpack('>i', data[68:72])[0] / 100.0,
            'last_traded_ts': struct.unpack('>i', data[72:76])[0],
            'oi': struct.unpack('>i', data[76:80])[0],
        })

    if mode == 3:  # Snap Quote mode
        # Parse 5-level depth...
        result['depth'] = parse_depth(data[104:])

    return result
```

## PAISE Conversion (CRITICAL)

**ALL WebSocket prices are in PAISE (integer).** You MUST divide by 100 to get rupees.

```python
# CORRECT
ltp_rupees = raw_ltp / 100.0  # 15025 → 150.25

# WRONG - will show prices 100x too large
ltp = raw_ltp  # BUG: 15025 displayed as ₹15,025 instead of ₹150.25
```

Fields in PAISE: `ltp`, `open`, `high`, `low`, `close`, `avg_traded_price`, all depth prices, circuit limits, 52-week high/low.

Fields NOT in PAISE: `volume`, `oi`, `quantity`, `orders` (count), timestamps.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid feed token | Connection closes immediately |
| Token limit exceeded | Subscription silently ignored |
| Network disconnect | Auto-reconnect with backoff |
| Server maintenance | Connection dropped, retry later |
| Invalid token ID | No data received (silent failure) |
| Wrong exchange type | No data or incorrect data |

## AlgoChanakya Integration

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/services/legacy/smartapi_ticker.py` | WebSocket V2 ticker service |
| `backend/app/services/brokers/market_data/ticker_base.py` | Unified ticker interface |
| `backend/app/api/routes/websocket.py` | WS route for frontend |

### Frontend WebSocket Connection

```javascript
// Dev: ws://localhost:8001/ws/ticks?token={jwt}
// Prod: wss://algochanakya.com/ws/ticks?token={jwt}
const ws = new WebSocket(`ws://localhost:8001/ws/ticks?token=${jwt}`)
ws.onmessage = (e) => {
  const data = JSON.parse(e.data)  // Backend converts binary to JSON
  console.log(data)
}
ws.send(JSON.stringify({
  action: 'subscribe',
  tokens: [256265],  // Kite tokens - backend maps to SmartAPI tokens
  mode: 'quote'
}))
```

**Note:** The backend handles binary→JSON conversion. Frontend always receives JSON from the AlgoChanakya WebSocket, regardless of which broker's binary protocol is used underneath.
