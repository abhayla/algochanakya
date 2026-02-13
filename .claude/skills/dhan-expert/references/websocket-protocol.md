# Dhan WebSocket Protocol

## Overview

Dhan uses a **binary WebSocket** protocol with **little-endian** byte ordering. This is unique
among Indian brokers -- most others (Zerodha Kite, Angel SmartAPI) use big-endian or JSON.

**Key characteristic:** Binary frames use `struct.unpack('<...')` (little-endian) instead of
`struct.unpack('>...')` (big-endian).

---

## Connection Details

| Property            | Value                                    |
|---------------------|------------------------------------------|
| WebSocket URL       | `wss://api-feed.dhan.co`                 |
| Protocol            | Binary (little-endian) + JSON control    |
| Max Connections      | 5 concurrent connections per user        |
| Heartbeat           | Ping/Pong (standard WebSocket)           |
| Reconnection        | Client-managed; no auto-reconnect        |
| Authentication      | Via JSON subscription message            |

---

## Subscription Modes

Dhan supports four subscription modes, each with different data depth and instrument limits:

| Mode       | Max Instruments | Data Included                                  | Use Case                     |
|------------|-----------------|------------------------------------------------|------------------------------|
| `Ticker`   | 100             | LTP, LTQ, LTT, volume, OI                     | Watchlist, portfolio tracking |
| `Quote`    | 50              | Ticker + OHLC + 20-depth bid/ask               | Option chain, detailed view  |
| `Full`     | 50              | Quote + extended stats (avg price, total B/S)  | Full instrument analysis     |
| `200-Depth`| 1               | 200 levels of bid/ask depth                    | Deep order book analysis     |

**Important:** 200-Depth mode allows only **1 instrument per connection**. You need a dedicated
connection for each instrument requiring 200-depth data.

---

## Connection Flow

### Step 1: Establish WebSocket Connection

```python
import websockets
import json
import struct

WS_URL = "wss://api-feed.dhan.co"

async def connect():
    async with websockets.connect(WS_URL) as ws:
        # Step 2: Subscribe
        await subscribe(ws)
        # Step 3: Receive binary data
        async for message in ws:
            if isinstance(message, bytes):
                parse_binary(message)
            else:
                handle_json(json.loads(message))
```

### Step 2: Subscribe via JSON Message

Subscription is sent as a JSON text frame:

```python
subscribe_msg = {
    "RequestCode": 21,            # 21 = Subscribe, 22 = Unsubscribe
    "InstrumentCount": 3,
    "InstrumentList": [
        {
            "ExchangeSegment": "NSE_EQ",
            "SecurityId": "1333"
        },
        {
            "ExchangeSegment": "NSE_FNO",
            "SecurityId": "43854"
        },
        {
            "ExchangeSegment": "IDX_I",
            "SecurityId": "13"       # NIFTY 50 index
        }
    ]
}

await ws.send(json.dumps(subscribe_msg))
```

### Step 3: Receive Binary Responses

After subscription, the server sends binary frames. The first 2 bytes indicate the response type.

---

## Request Codes

| Code | Action          | Description                              |
|------|-----------------|------------------------------------------|
| 21   | Subscribe       | Subscribe to instruments                 |
| 22   | Unsubscribe     | Unsubscribe from instruments             |

---

## Response Types (First 2 bytes, little-endian uint16)

| Response Code | Meaning              | Payload Size          |
|---------------|----------------------|-----------------------|
| 2             | Ticker data          | 32 bytes per packet   |
| 3             | Quote data           | Variable (with depth) |
| 4             | Full data            | Variable (extended)   |
| 5             | 200-Depth data       | Variable (large)      |
| 50            | Disconnect message   | Variable              |
| 100           | Server heartbeat     | Minimal               |

---

## Binary Parsing -- Little Endian

### Critical: Little-Endian Byte Order

Dhan uses **little-endian** (`<`) for all binary data. This is the opposite of Zerodha Kite
which uses big-endian (`>`).

```python
# CORRECT for Dhan (little-endian)
value = struct.unpack('<I', data[0:4])[0]   # unsigned int, little-endian

# WRONG for Dhan (big-endian -- this is Kite's format)
value = struct.unpack('>I', data[0:4])[0]   # DO NOT USE for Dhan
```

### Ticker Mode Packet (32 bytes)

```python
def parse_ticker_packet(data: bytes) -> dict:
    """Parse a Dhan Ticker mode binary packet (little-endian)."""
    # Byte offsets and formats (all little-endian)
    response_code = struct.unpack('<H', data[0:2])[0]     # uint16 - response type
    exchange_segment = struct.unpack('<B', data[2:3])[0]   # uint8  - exchange
    security_id = struct.unpack('<I', data[3:7])[0]        # uint32 - security ID
    ltp = struct.unpack('<f', data[7:11])[0]               # float32 - last traded price
    ltq = struct.unpack('<H', data[11:13])[0]              # uint16 - last traded qty
    ltt = struct.unpack('<I', data[13:17])[0]              # uint32 - last trade time (epoch)
    volume = struct.unpack('<I', data[17:21])[0]           # uint32 - total volume
    oi = struct.unpack('<I', data[21:25])[0]               # uint32 - open interest
    change = struct.unpack('<f', data[25:29])[0]           # float32 - price change
    change_pct = struct.unpack('<f', data[29:33])[0]       # float32 - change percentage (if present)

    return {
        "response_code": response_code,
        "exchange_segment": EXCHANGE_MAP.get(exchange_segment, "UNKNOWN"),
        "security_id": security_id,
        "ltp": round(ltp, 2),
        "ltq": ltq,
        "ltt": ltt,
        "volume": volume,
        "oi": oi,
        "change": round(change, 2),
    }
```

### Quote Mode Packet (with 20-depth)

```python
def parse_quote_packet(data: bytes) -> dict:
    """Parse a Dhan Quote mode binary packet with 20-depth bid/ask."""
    # Header (same as Ticker)
    result = parse_ticker_header(data)

    # OHLC values after ticker fields
    offset = 33  # After ticker data
    result["open"] = struct.unpack('<f', data[offset:offset+4])[0]
    result["high"] = struct.unpack('<f', data[offset+4:offset+8])[0]
    result["low"] = struct.unpack('<f', data[offset+8:offset+12])[0]
    result["close"] = struct.unpack('<f', data[offset+12:offset+16])[0]

    # 20-depth bid/ask
    depth_offset = offset + 16
    result["depth"] = {"buy": [], "sell": []}

    for i in range(20):
        bid_start = depth_offset + (i * 12)  # 12 bytes per level (price + qty + orders)
        bid_price = struct.unpack('<f', data[bid_start:bid_start+4])[0]
        bid_qty = struct.unpack('<I', data[bid_start+4:bid_start+8])[0]
        bid_orders = struct.unpack('<H', data[bid_start+8:bid_start+10])[0]
        # 2 bytes padding
        result["depth"]["buy"].append({
            "price": round(bid_price, 2),
            "quantity": bid_qty,
            "orders": bid_orders,
        })

    ask_offset = depth_offset + (20 * 12)
    for i in range(20):
        ask_start = ask_offset + (i * 12)
        ask_price = struct.unpack('<f', data[ask_start:ask_start+4])[0]
        ask_qty = struct.unpack('<I', data[ask_start+4:ask_start+8])[0]
        ask_orders = struct.unpack('<H', data[ask_start+8:ask_start+10])[0]
        result["depth"]["sell"].append({
            "price": round(ask_price, 2),
            "quantity": ask_qty,
            "orders": ask_orders,
        })

    return result
```

### 200-Depth Packet

```python
def parse_200_depth_packet(data: bytes) -> dict:
    """Parse 200-depth data. Only 1 instrument per connection."""
    result = parse_ticker_header(data)
    result["depth"] = {"buy": [], "sell": []}

    depth_offset = 33  # After header
    for i in range(200):
        bid_start = depth_offset + (i * 12)
        bid_price = struct.unpack('<f', data[bid_start:bid_start+4])[0]
        bid_qty = struct.unpack('<I', data[bid_start+4:bid_start+8])[0]
        bid_orders = struct.unpack('<H', data[bid_start+8:bid_start+10])[0]
        if bid_price > 0:
            result["depth"]["buy"].append({
                "price": round(bid_price, 2),
                "quantity": bid_qty,
                "orders": bid_orders,
            })

    ask_offset = depth_offset + (200 * 12)
    for i in range(200):
        ask_start = ask_offset + (i * 12)
        ask_price = struct.unpack('<f', data[ask_start:ask_start+4])[0]
        ask_qty = struct.unpack('<I', data[ask_start+4:ask_start+8])[0]
        ask_orders = struct.unpack('<H', data[ask_start+8:ask_start+10])[0]
        if ask_price > 0:
            result["depth"]["sell"].append({
                "price": round(ask_price, 2),
                "quantity": ask_qty,
                "orders": ask_orders,
            })

    return result
```

---

## Exchange Segment Byte Mapping

| Byte Value | Exchange Segment |
|------------|------------------|
| 0          | NSE_EQ           |
| 1          | NSE_FNO          |
| 2          | NSE_CURRENCY     |
| 3          | BSE_EQ           |
| 4          | BSE_FNO          |
| 5          | BSE_CURRENCY     |
| 6          | MCX_COMM         |
| 7          | IDX_I            |

```python
EXCHANGE_MAP = {
    0: "NSE_EQ",
    1: "NSE_FNO",
    2: "NSE_CURRENCY",
    3: "BSE_EQ",
    4: "BSE_FNO",
    5: "BSE_CURRENCY",
    6: "MCX_COMM",
    7: "IDX_I",
}
```

---

## Unsubscription

```python
unsubscribe_msg = {
    "RequestCode": 22,            # 22 = Unsubscribe
    "InstrumentCount": 1,
    "InstrumentList": [
        {
            "ExchangeSegment": "NSE_FNO",
            "SecurityId": "43854"
        }
    ]
}

await ws.send(json.dumps(unsubscribe_msg))
```

---

## Connection Management

### Multiple Connections Strategy

Since 200-Depth is limited to 1 instrument per connection, manage connections as follows:

```python
class DhanWebSocketManager:
    """Manage up to 5 Dhan WebSocket connections."""

    MAX_CONNECTIONS = 5

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.connections: list = []

    async def subscribe_ticker(self, security_ids: list[dict]):
        """Subscribe in Ticker mode (max 100 instruments per connection)."""
        # Use shared connection for ticker/quote
        conn = await self._get_or_create_shared_connection()
        await conn.send(json.dumps({
            "RequestCode": 21,
            "InstrumentCount": len(security_ids),
            "InstrumentList": security_ids,
        }))

    async def subscribe_200_depth(self, exchange_segment: str, security_id: str):
        """Subscribe to 200-depth (requires dedicated connection)."""
        if len(self.connections) >= self.MAX_CONNECTIONS:
            raise ConnectionError("Max 5 connections reached")
        conn = await self._create_dedicated_connection()
        await conn.send(json.dumps({
            "RequestCode": 21,
            "InstrumentCount": 1,
            "InstrumentList": [{
                "ExchangeSegment": exchange_segment,
                "SecurityId": security_id,
            }],
        }))
```

### Reconnection Logic

```python
async def connect_with_reconnect(
    access_token: str,
    instruments: list[dict],
    max_retries: int = 5,
    backoff_base: float = 1.0,
):
    """Connect with exponential backoff reconnection."""
    retries = 0
    while retries < max_retries:
        try:
            async with websockets.connect(WS_URL) as ws:
                retries = 0  # Reset on successful connection
                await ws.send(json.dumps({
                    "RequestCode": 21,
                    "InstrumentCount": len(instruments),
                    "InstrumentList": instruments,
                }))
                async for message in ws:
                    if isinstance(message, bytes):
                        yield parse_binary(message)
        except websockets.ConnectionClosed:
            retries += 1
            wait_time = backoff_base * (2 ** retries)
            await asyncio.sleep(min(wait_time, 30))
        except Exception as e:
            retries += 1
            await asyncio.sleep(min(backoff_base * (2 ** retries), 30))

    raise ConnectionError(f"Failed to connect after {max_retries} retries")
```

---

## AlgoChanakya Integration Notes

### TickerServiceBase Implementation

When implementing `DhanTickerService`, map Dhan modes to AlgoChanakya modes:

| AlgoChanakya Mode | Dhan Mode   | Notes                              |
|--------------------|-------------|------------------------------------|
| `ltp`              | `Ticker`    | LTP only                           |
| `quote`            | `Quote`     | LTP + OHLC + 20-depth             |
| `full`             | `Full`      | All data                           |
| (special)          | `200-Depth` | Requires dedicated connection      |

### Data Normalization

Convert Dhan binary data to `UnifiedQuote` format:

```python
def dhan_tick_to_unified_quote(tick: dict) -> UnifiedQuote:
    """Convert Dhan WebSocket tick to UnifiedQuote."""
    return UnifiedQuote(
        tradingsymbol=token_manager.get_canonical_symbol(
            tick["security_id"], "dhan"
        ),
        last_price=tick["ltp"],
        volume=tick.get("volume", 0),
        oi=tick.get("oi", 0),
        ohlc={
            "open": tick.get("open", 0),
            "high": tick.get("high", 0),
            "low": tick.get("low", 0),
            "close": tick.get("close", 0),
        },
        depth=normalize_depth(tick.get("depth")),
        timestamp=tick.get("ltt"),
    )
```

---

## Comparison with Other Broker WebSockets

| Feature           | Dhan                    | Zerodha Kite           | Angel SmartAPI         |
|-------------------|-------------------------|------------------------|------------------------|
| Protocol          | Binary (little-endian)  | Binary (big-endian)    | Binary + JSON          |
| Byte Order        | `<` (little-endian)     | `>` (big-endian)       | Mixed                  |
| Subscription      | JSON text frame         | Binary frame           | JSON text frame        |
| Max Instruments   | 100 (Ticker)            | 3000                   | 1000                   |
| Max Connections   | 5                       | 3                      | 3                      |
| Depth Levels      | 20 (Quote), 200 (special) | 5                   | 5 (Full), 20 (SnapQuote) |
| Auth in WS        | Via subscribe message   | Via connect URL        | Via connect message    |
