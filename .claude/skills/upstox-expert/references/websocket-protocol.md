# Upstox WebSocket Protocol (MarketDataFeedV3)

> Source: [Upstox API Docs](https://upstox.com/developer/api-documentation/open-api) + [Announcements](https://upstox.com/developer/api-documentation/announcements/) | Last verified: 2026-02-25

Protobuf-based WebSocket protocol reference for Upstox.

> **⚠️ V2 DISCONTINUED:** MarketDataFeedV2 was discontinued on **Aug 22, 2025**. Only V3 works. Update all existing code using V2 to V3.

---

## Market Data Feed (V3)

### Connection Flow

1. `GET /v2/feed/market-data-feed/authorize` → returns authorized WS URL
2. Connect to the authorized URL
3. Subscribe via Protobuf binary message

### Step 1: Get Authorized URL

```http
GET https://api.upstox.com/v2/feed/market-data-feed/authorize
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "data": {
    "authorized_redirect_uri": "wss://ws.upstox.com/market-data-feed/v3?token=abc..."
  }
}
```

> **Important:** The authorized URL expires with the access_token. Re-fetch after token refresh.

### Step 2: Connect

```python
import websocket
ws = websocket.WebSocketApp(authorized_url, on_message=on_message)
ws.run_forever()
```

### Step 3: Subscribe (Binary Protobuf)

```python
from upstox_client.feeder import MarketDataStreamer

# Using SDK (recommended)
streamer = MarketDataStreamer(upstox_client.Configuration())
streamer.subscribe(["NSE_FO|12345"], "full")

# Raw binary (without SDK)
request = FeedRequest()
request.guid = "unique-id"
request.method = Method.sub
request.data.mode = Mode.full
request.data.instrument_keys.extend(["NSE_FO|12345"])
ws.send(request.SerializeToString(), opcode=websocket.ABNF.OPCODE_BINARY)
```

### Unsubscribe

```python
streamer.unsubscribe(["NSE_FO|12345"])
```

---

## Subscription Modes

| Mode | Description | Fields |
|------|-------------|--------|
| `ltpc` | LTP + Change | ltp, close, change, change_percent |
| `full` | Full quote | OHLC, volume, OI, depth (5-level), bid/ask, timestamps |
| `option_greeks` | Greeks + full | Full + delta, gamma, theta, vega, implied_volatility |

---

## Connection Limits

| Plan | Max Connections | Max Instruments | D30 Depth |
|------|-----------------|-----------------|-----------|
| Basic | **2** | ~1500 total | No |
| Plus | **5** | ~5000+ total | Yes (50 instruments/connection) |

> **D30 Mode (Plus only):** Subscribe to up to 50 instruments per connection with 30-level market depth. Requires Plus subscription.

---

## Protobuf Schema

### FeedResponse (incoming tick)

```protobuf
message FeedResponse {
  string type = 1;          // "live_feed"
  map<string, Feed> feeds = 2;
}

message Feed {
  LTPC ltpc = 1;            // Present in all modes
  FullFeed ff = 2;          // Present in full/option_greeks mode
  OptionGreeks og = 3;      // Present in option_greeks mode
}

message LTPC {
  double ltp = 1;
  double close = 2;
  double change = 3;
  double change_percent = 4;
}

message FullFeed {
  OHLC ohlc = 1;
  MarketDepth depth = 2;    // 5-level (20 for D30 mode)
  int64 volume = 3;
  int64 oi = 4;
  double avg_price = 5;
  int64 total_buy_qty = 6;
  int64 total_sell_qty = 7;
}

message OptionGreeks {
  double delta = 1;
  double gamma = 2;
  double theta = 3;
  double vega = 4;
  double iv = 5;            // Implied Volatility
}
```

### Parsing Example

```python
from upstox_client.feeder import MarketDataStreamer

def on_message(message):
    # SDK auto-deserializes Protobuf
    for instrument_key, feed in message.feeds.items():
        ltp = feed.ltpc.ltp          # float, RUPEES
        change_pct = feed.ltpc.change_percent
        if feed.ff:
            volume = feed.ff.volume
            oi = feed.ff.oi
            ohlc = feed.ff.ohlc
        if feed.og:
            delta = feed.og.delta
            iv = feed.og.iv
```

---

## Price Format

**ALL prices are in RUPEES (float).** No paise conversion needed.

---

## Python SDK Usage

```python
from upstox_client.feeder import MarketDataStreamer

configuration = upstox_client.Configuration()
configuration.access_token = "your_access_token"

streamer = MarketDataStreamer(configuration)

def on_open():
    streamer.subscribe(["NSE_FO|12345", "NSE_INDEX|Nifty 50"], "full")

def on_message(message):
    for key, feed in message.feeds.items():
        print(f"{key}: LTP={feed.ltpc.ltp}")

def on_error(error):
    print(f"WS Error: {error}")

def on_close():
    print("WS Closed")

streamer.on("open", on_open)
streamer.on("message", on_message)
streamer.on("error", on_error)
streamer.on("close", on_close)
streamer.connect()
```

---

## Portfolio Stream WebSocket

Stream real-time portfolio updates (positions, holdings, order status).

### Authorization

```http
GET https://api.upstox.com/v2/feed/portfolio-stream-feed/authorize
Authorization: Bearer {access_token}
```

Returns authorized WebSocket URL for portfolio stream.

### Event Types

| Event | Description |
|-------|-------------|
| `portfolio_update` | Position/holding value change |
| `order_update` | Order status change (filled, rejected, etc.) |
| `position_update` | Position quantity/P&L change |

### Payload Format

```json
{
  "type": "order_update",
  "data": {
    "order_id": "123456789",
    "status": "complete",
    "instrument_token": "NSE_FO|12345",
    "quantity": 25,
    "price": 150.5,
    "transaction_type": "BUY"
  }
}
```

---

## Error Handling

| Scenario | Behavior | Resolution |
|----------|----------|------------|
| Invalid authorized URL | Connection refused | Re-fetch URL |
| Token expired | Disconnect | Re-auth, re-fetch URL, reconnect |
| Instrument not found | No data for that key | Verify instrument_key |
| Connection limit exceeded | New connection fails or previous dropped | Reduce connections |
| NXDOMAIN error | DNS resolution failure | Retry with exponential backoff |

---

## Known Community Issues

| Issue | Status | Workaround |
|-------|--------|------------|
| Portfolio WS NXDOMAIN | Active (Feb 2026) | Retry with backoff; check DNS resolution |
| IP whitelisting 403 | Active (Feb 2026) | Whitelist IP in My Apps → Settings |
| V2 WS connection refused | Resolved by V3 migration | Migrate all code to V3 |

---

## Comparison with Other Brokers

| Feature | Upstox | SmartAPI | Kite |
|---------|--------|---------|------|
| Format | Protobuf | Custom binary | Custom binary |
| Price unit | Rupees | Paise | Paise |
| Auth | REST → URL | Query params | Query params |
| Greeks via WS | **Yes** | No | No |
| Max connections | 2 (Basic) / 5 (Plus) | 3 | 3 |
| Portfolio stream | Yes | No | No |
| V2/V3 split | V3 only (V2 dead) | V3 | N/A |
