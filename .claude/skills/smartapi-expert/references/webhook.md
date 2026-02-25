# SmartAPI Webhook / Order Update Reference

> Source: SmartAPI (Angel One) Official Docs | Last verified: 2026-02-25

## Overview

SmartAPI does **NOT support HTTP webhooks** for order/trade notifications. There is no "POST to your URL" push model like Upstox provides. Instead, Angel One provides a dedicated **Order Update WebSocket** for real-time order status updates.

## Order Update WebSocket

**URL:** `wss://tns.angelone.in/smart-order-update`

This is a **separate WebSocket connection** from the market data WebSocket (`smartapisocket.angelone.in`). It streams real-time order fills, rejections, modifications, and cancellations.

### Connection

```python
import websocket
import json

def on_open(ws):
    # Send authentication message
    auth_msg = {
        "task": "connect",
        "channel": "",
        "token": feed_token,   # feedToken from login response
        "user": client_id,     # Angel One client ID
        "acctid": client_id    # Same as user
    }
    ws.send(json.dumps(auth_msg))

def on_message(ws, message):
    data = json.loads(message)
    if data.get("type") == "order_feed":
        order_id = data.get("orderid")
        status = data.get("orderstatus")
        filled = data.get("filledshares")
        avg_price = data.get("averageprice")
        # Process order update

def on_error(ws, error):
    print(f"Order WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Order WebSocket closed — reconnect with backoff")

ws = websocket.WebSocketApp(
    "wss://tns.angelone.in/smart-order-update",
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)
ws.run_forever()
```

### Authentication Message

```json
{
  "task": "connect",
  "channel": "",
  "token": "{feedToken}",
  "user": "{client_id}",
  "acctid": "{client_id}"
}
```

**Auth uses `feedToken`** (same as the market data WebSocket), NOT the `jwtToken`.

### Order Update Message Format

Messages received from the WebSocket when order status changes:

```json
{
  "type": "order_feed",
  "orderid": "240915000123456",
  "uniqueorderid": "abc123def456",
  "orderstatus": "complete",
  "tradingsymbol": "SBIN-EQ",
  "symboltoken": "3045",
  "exchange": "NSE",
  "transactiontype": "BUY",
  "producttype": "DELIVERY",
  "ordertype": "MARKET",
  "price": "500.00",
  "triggerprice": "0.00",
  "quantity": "10",
  "filledshares": "10",
  "unfilledshares": "0",
  "averageprice": "499.85",
  "text": "order executed",
  "exchtime": "15-Sep-2024 10:30:00",
  "exchorderupdatetime": "15-Sep-2024 10:30:00"
}
```

### Order Status Values

| Status | Description |
|--------|-------------|
| `open` | Order is pending / open in market |
| `trigger pending` | Stop-loss trigger waiting |
| `complete` | Fully executed |
| `rejected` | Order rejected by exchange or broker |
| `cancelled` | Order cancelled by user |
| `modified` | Order was modified |
| `after market order req received` | AMO received, will process at open |

### Message Fields Reference

| Field | Description |
|-------|-------------|
| `type` | Always `"order_feed"` for order updates |
| `orderid` | Angel One order ID |
| `uniqueorderid` | Internal unique identifier |
| `orderstatus` | Current order status (see table above) |
| `tradingsymbol` | Symbol in SmartAPI format |
| `symboltoken` | SmartAPI instrument token |
| `exchange` | NSE, BSE, NFO, MCX |
| `transactiontype` | BUY or SELL |
| `producttype` | DELIVERY, CARRYFORWARD, INTRADAY, etc. |
| `ordertype` | MARKET, LIMIT, STOPLOSS_LIMIT, etc. |
| `price` | Order price |
| `quantity` | Total order quantity |
| `filledshares` | Quantity filled so far |
| `unfilledshares` | Quantity still pending |
| `averageprice` | Average fill price |
| `text` | Human-readable status message |

### Reconnection Strategy

```python
import time

def connect_order_ws(feed_token, client_id, max_retries=10):
    backoff = 1
    for attempt in range(max_retries):
        try:
            ws = websocket.WebSocketApp(
                "wss://tns.angelone.in/smart-order-update",
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.run_forever()
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(min(backoff, 30))
            backoff *= 2
```

## Alternative: REST Polling

If the Order Update WebSocket is not feasible, poll the order book:

```python
import asyncio

async def poll_order_status(order_id: str, adapter, interval: int = 2) -> str:
    """Poll order book until order reaches terminal state."""
    terminal_states = {"complete", "rejected", "cancelled"}

    while True:
        order_book = await adapter.get_order_book()
        for order in order_book.get("data", []):
            if order["orderid"] == order_id:
                status = order["orderstatus"]
                if status in terminal_states:
                    return status
                break
        await asyncio.sleep(interval)
```

**Polling endpoint:** `GET /rest/secure/angelbroking/order/v1/getOrderBook`

**Recommended polling interval:** 2 seconds during active trading hours. Do not poll faster than 1/sec (rate limit).

## Two WebSocket Connections Compared

| | Market Data WebSocket | Order Update WebSocket |
|-|-----------------------|------------------------|
| **URL** | `wss://smartapisocket.angelone.in/smart-stream` | `wss://tns.angelone.in/smart-order-update` |
| **Auth** | feedToken in URL query params | feedToken in JSON message |
| **Protocol** | Binary (custom format) | JSON text messages |
| **Purpose** | Live tick data (LTP, OHLC, depth) | Order status notifications |
| **Max connections** | 3 per client | 1 per client |
| **Max subscriptions** | 3000 tokens | N/A (all orders auto-streamed) |
| **AlgoChanakya status** | Implemented | Not yet implemented |

## AlgoChanakya Integration Notes

- Order Update WebSocket is **NOT yet implemented** in AlgoChanakya
- Currently uses REST polling for order status (2-second interval)
- Implementation target: `backend/app/services/brokers/angelone_adapter.py`
- When implementing: use `feedToken` (same as market data WebSocket auth)
- The order WebSocket uses JSON (not binary), which is simpler to implement than the market data WebSocket

## No Traditional Webhooks

Unlike Upstox which supports HTTP webhooks (POST to your URL on order events), SmartAPI does not push order notifications to external URLs. All real-time notification methods are either:

1. Pull-based (REST polling of order book)
2. WebSocket-based (Order Update WebSocket)

If you need traditional webhook-like behavior (receive a POST to your endpoint), you must implement your own bridge: connect to the Order Update WebSocket and forward events to your internal endpoint.
