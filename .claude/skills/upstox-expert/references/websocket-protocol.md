# Upstox WebSocket Protocol (MarketDataFeedV3)

Protobuf-based WebSocket protocol reference for Upstox.

## Connection Flow

Unlike other brokers, Upstox requires a **REST call** to get an authorized WebSocket URL:

```
1. GET /v2/feed/market-data-feed/authorize → returns authorized WS URL
2. Connect to the authorized URL
3. Subscribe via Protobuf binary message
```

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

### Step 2: Connect

```python
import websocket
ws = websocket.WebSocketApp(authorized_url, on_message=on_message)
ws.run_forever()
```

## Subscription

### Subscribe Request (Binary Protobuf)

```python
from google.protobuf import json_format
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

## Subscription Modes

| Mode | Description | Fields |
|------|-------------|--------|
| `ltpc` | LTP + Change | ltp, close, change, change_percent |
| `full` | Full quote | OHLC, volume, OI, depth (5-level), bid/ask, timestamps |
| `option_greeks` | Greeks + full | Full + delta, gamma, theta, vega, implied_volatility |

## Protobuf Schema

Upstox publishes .proto schemas. Key message types:

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
  MarketDepth depth = 2;
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
  double iv = 5;
}
```

### Parsing Example

```python
from upstox_client.feeder import MarketDataStreamer

def on_message(message):
    # SDK auto-deserializes Protobuf
    feed_response = message  # Already parsed FeedResponse object
    for instrument_key, feed in feed_response.feeds.items():
        ltp = feed.ltpc.ltp          # float, RUPEES
        if feed.ff:
            volume = feed.ff.volume
            oi = feed.ff.oi
        if feed.og:
            delta = feed.og.delta
            iv = feed.og.iv
```

## Price Format

**ALL prices are in RUPEES (float).** No paise conversion needed.

## Connection Limits

| Limit | Value |
|-------|-------|
| Max connections | **1** per access_token |
| Max instruments | Plan-dependent (~1500 basic, 5000+ pro) |
| Message format | Protocol Buffers (binary) |
| Heartbeat | Automatic (SDK managed) |
| Reconnect | SDK handles auto-reconnect |

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid authorized URL | Connection refused |
| Token expired | Disconnect |
| Instrument not found | No data for that key |
| Connection limit exceeded | Previous connection dropped |

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

streamer.on("open", on_open)
streamer.on("message", on_message)
streamer.connect()
```

## Comparison with Other Brokers

| Feature | Upstox | SmartAPI | Kite |
|---------|--------|---------|------|
| Format | Protobuf | Custom binary | Custom binary |
| Price unit | Rupees | Paise | Paise |
| Auth | REST → URL | Query params | Query params |
| Greeks WS | Yes | No | No |
| Max connections | 1 | 3 | 3 |
