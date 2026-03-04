# KiteTicker WebSocket Protocol

Complete WebSocket binary protocol reference for Zerodha Kite Connect.

## Connection

### URL Format

```
wss://ws.kite.trade?api_key={api_key}&access_token={access_token}
```

### Connection Parameters

| Parameter | Source | Example |
|-----------|--------|---------|
| `api_key` | Kite developer dashboard | `abc123` |
| `access_token` | From session token exchange | `xyz789` |

### Connection Limits

| Limit | Value |
|-------|-------|
| Max connections per user | **3** |
| Max tokens per connection | **3000** |
| Tick delivery | Real-time (exchange feed speed) |
| Reconnect | Auto with exponential backoff |

## Subscription

### Using kiteconnect SDK

```python
from kiteconnect import KiteTicker

kws = KiteTicker(api_key="abc123", access_token="xyz789")

def on_ticks(ws, ticks):
    for tick in ticks:
        print(f"LTP: {tick['last_price']}")  # Already in rupees (SDK converts)

def on_connect(ws, response):
    ws.subscribe([256265, 260105])  # NIFTY, BANKNIFTY
    ws.set_mode(ws.MODE_QUOTE, [256265, 260105])

kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.connect()
```

### Raw WebSocket (without SDK)

**Subscribe message (JSON text frame):**
```json
{
  "a": "subscribe",
  "v": [256265, 260105, 12345678]
}
```

**Set mode message:**
```json
{
  "a": "mode",
  "v": ["quote", [256265, 260105]]
}
```

**Modes:** `ltp`, `quote`, `full`

## Binary Message Format

KiteTicker sends **binary frames**. Each frame may contain multiple ticks.

### Frame Header

| Offset | Bytes | Type | Field |
|--------|-------|------|-------|
| 0 | 2 | int16 (BE) | Number of ticks in this frame |

After the header, tick packets follow sequentially. Each packet's length depends on the mode.

### Tick Identification

The first 4 bytes of each tick packet contain the instrument token:

| Offset | Bytes | Type | Field |
|--------|-------|------|-------|
| 0 | 4 | int32 (BE) | Instrument Token |

The **packet size** determines the mode:
- **8 bytes** → LTP mode
- **44 bytes** → Quote mode
- **184 bytes** → Full mode

## LTP Mode (8 bytes per tick)

| Offset | Bytes | Type | Field | Unit |
|--------|-------|------|-------|------|
| 0 | 4 | int32 (BE) | Instrument Token | - |
| 4 | 4 | int32 (BE) | **Last Price** | **PAISE** |

**Total: 8 bytes**

```python
import struct
token = struct.unpack('>I', data[0:4])[0]
ltp = struct.unpack('>I', data[4:8])[0] / 100.0  # paise → rupees
```

## Quote Mode (44 bytes per tick)

| Offset | Bytes | Type | Field | Unit |
|--------|-------|------|-------|------|
| 0 | 4 | int32 (BE) | Instrument Token | - |
| 4 | 4 | int32 (BE) | Last Price | PAISE |
| 8 | 4 | int32 (BE) | Last Traded Quantity | - |
| 12 | 4 | int32 (BE) | Average Traded Price | PAISE |
| 16 | 4 | int32 (BE) | Volume | - |
| 20 | 4 | int32 (BE) | Total Buy Quantity | - |
| 24 | 4 | int32 (BE) | Total Sell Quantity | - |
| 28 | 4 | int32 (BE) | Open | PAISE |
| 32 | 4 | int32 (BE) | High | PAISE |
| 36 | 4 | int32 (BE) | Low | PAISE |
| 40 | 4 | int32 (BE) | Close | PAISE |

**Total: 44 bytes**

```python
def parse_quote(data: bytes) -> dict:
    return {
        'token': struct.unpack('>I', data[0:4])[0],
        'last_price': struct.unpack('>I', data[4:8])[0] / 100.0,
        'last_quantity': struct.unpack('>I', data[8:12])[0],
        'avg_price': struct.unpack('>I', data[12:16])[0] / 100.0,
        'volume': struct.unpack('>I', data[16:20])[0],
        'buy_quantity': struct.unpack('>I', data[20:24])[0],
        'sell_quantity': struct.unpack('>I', data[24:28])[0],
        'open': struct.unpack('>I', data[28:32])[0] / 100.0,
        'high': struct.unpack('>I', data[32:36])[0] / 100.0,
        'low': struct.unpack('>I', data[36:40])[0] / 100.0,
        'close': struct.unpack('>I', data[40:44])[0] / 100.0,
    }
```

## Full Mode (184 bytes per tick)

Extends Quote mode with timestamps, OI, and 5-level market depth.

| Offset | Bytes | Type | Field | Unit |
|--------|-------|------|-------|------|
| 0-43 | 44 | - | Same as Quote mode | - |
| 44 | 4 | int32 (BE) | Last Trade Time | Unix epoch |
| 48 | 4 | int32 (BE) | OI | - |
| 52 | 4 | int32 (BE) | OI Day High | - |
| 56 | 4 | int32 (BE) | OI Day Low | - |
| 60 | 4 | int32 (BE) | Exchange Timestamp | Unix epoch |
| **64-163** | **100** | - | **Market Depth** | 10 entries × 10 bytes |
| 164 | 4 | int32 (BE) | Total Buy Quantity (Full) | - |
| 168 | 4 | int32 (BE) | Total Sell Quantity (Full) | - |
| 172 | 4 | int32 (BE) | Upper Circuit | PAISE |
| 176 | 4 | int32 (BE) | Lower Circuit | PAISE |
| 180 | 4 | int32 (BE) | Change (net) | PAISE |

**Total: 184 bytes**

### Market Depth Structure (bytes 64-163)

10 entries total: 5 buy levels + 5 sell levels. Each entry is 10 bytes:

| Offset (relative) | Bytes | Type | Field | Unit |
|-------------------|-------|------|-------|------|
| 0 | 4 | int32 (BE) | Price | PAISE |
| 4 | 4 | int32 (BE) | Quantity | - |
| 8 | 2 | int16 (BE) | Number of Orders | - |

**Layout:**
- Bytes 64-73: Buy level 1
- Bytes 74-83: Buy level 2
- Bytes 84-93: Buy level 3
- Bytes 94-103: Buy level 4
- Bytes 104-113: Buy level 5
- Bytes 114-123: Sell level 1
- Bytes 124-133: Sell level 2
- ... and so on

## Complete Parsing Example

```python
import struct
from decimal import Decimal

def parse_kite_tick(data: bytes) -> dict:
    """Parse a single Kite tick from binary data."""
    length = len(data)
    token = struct.unpack('>I', data[0:4])[0]

    # LTP mode (8 bytes)
    if length == 8:
        return {
            'instrument_token': token,
            'last_price': struct.unpack('>I', data[4:8])[0] / 100.0,
            'mode': 'ltp'
        }

    # Quote mode (44 bytes)
    if length == 44:
        return {
            'instrument_token': token,
            'last_price': struct.unpack('>I', data[4:8])[0] / 100.0,
            'last_quantity': struct.unpack('>I', data[8:12])[0],
            'average_price': struct.unpack('>I', data[12:16])[0] / 100.0,
            'volume': struct.unpack('>I', data[16:20])[0],
            'buy_quantity': struct.unpack('>I', data[20:24])[0],
            'sell_quantity': struct.unpack('>I', data[24:28])[0],
            'ohlc': {
                'open': struct.unpack('>I', data[28:32])[0] / 100.0,
                'high': struct.unpack('>I', data[32:36])[0] / 100.0,
                'low': struct.unpack('>I', data[36:40])[0] / 100.0,
                'close': struct.unpack('>I', data[40:44])[0] / 100.0,
            },
            'mode': 'quote'
        }

    # Full mode (184 bytes)
    if length == 184:
        tick = parse_quote_fields(data)  # Parse first 44 bytes as quote
        tick.update({
            'last_trade_time': struct.unpack('>I', data[44:48])[0],
            'oi': struct.unpack('>I', data[48:52])[0],
            'oi_day_high': struct.unpack('>I', data[52:56])[0],
            'oi_day_low': struct.unpack('>I', data[56:60])[0],
            'exchange_timestamp': struct.unpack('>I', data[60:64])[0],
            'depth': parse_depth(data[64:164]),
            'mode': 'full'
        })
        return tick

def parse_depth(data: bytes) -> dict:
    """Parse 5-level buy + sell depth."""
    depth = {'buy': [], 'sell': []}
    for i in range(5):
        offset = i * 10
        depth['buy'].append({
            'price': struct.unpack('>I', data[offset:offset+4])[0] / 100.0,
            'quantity': struct.unpack('>I', data[offset+4:offset+8])[0],
            'orders': struct.unpack('>H', data[offset+8:offset+10])[0],
        })
    for i in range(5):
        offset = 50 + i * 10
        depth['sell'].append({
            'price': struct.unpack('>I', data[offset:offset+4])[0] / 100.0,
            'quantity': struct.unpack('>I', data[offset+4:offset+8])[0],
            'orders': struct.unpack('>H', data[offset+8:offset+10])[0],
        })
    return depth
```

## PAISE Conversion

**ALL WebSocket prices are int32 in PAISE.** Divide by 100 for rupees.

Fields in PAISE: `last_price`, `open`, `high`, `low`, `close`, `average_price`, all depth prices, circuit limits.

Fields NOT in PAISE: `volume`, `oi`, quantities, orders count, timestamps.

## Index Tokens

Special tokens for indices (used frequently):

| Index | Token | Mode Support |
|-------|-------|--------------|
| NIFTY 50 | `256265` | LTP, Quote, Full |
| NIFTY BANK | `260105` | LTP, Quote, Full |
| NIFTY FIN SERVICE | `257801` | LTP, Quote, Full |
| SENSEX | `265` | LTP, Quote, Full |

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid token | Connection rejected |
| Token expired | Disconnect after ~6 AM |
| Network drop | Auto-reconnect (SDK) |
| Subscribe limit exceeded | Silent ignore |
| Invalid instrument token | No data for that token |

## AlgoChanakya Integration

| File | Purpose |
|------|---------|
| `backend/app/services/legacy/kite_ticker.py` | KiteTicker service (singleton) |
| `backend/app/services/brokers/market_data/ticker_base.py` | Unified ticker interface |
| `backend/app/api/routes/websocket.py` | Frontend WS bridge |

**Note:** AlgoChanakya currently uses SmartAPI as default ticker. KiteTicker is available as fallback.
