# Fyers Webhook / Order Update Reference

> Source: Fyers API v3 Docs (https://myapi.fyers.in/docs/) | Last verified: 2026-02-25

## Overview

Fyers does **NOT support traditional HTTP webhooks** (no POST to your URL on order events).

Instead, Fyers provides a **5-socket WebSocket system** for real-time updates, including a dedicated **FyersOrderSocket** for order notifications.

## 5 WebSocket Socket Types (v3)

| Socket | Class | Purpose |
|--------|-------|---------|
| **FyersDataSocket** | `data_ws.FyersDataSocket` | Market data ticks |
| **FyersOrderSocket** | `order_ws.FyersOrderSocket` | Order status updates |
| **FyersPositionSocket** | `positions_ws.FyersPositionSocket` | Real-time P&L |
| **FyersTradeSocket** | `trades_ws.FyersTradeSocket` | Trade execution updates |
| **FyersGeneralSocket** | `general_ws.FyersGeneralSocket` | General notifications |

## FyersOrderSocket (Order Updates)

```python
from fyers_apiv3.FyersWebsocket import order_ws

def on_order_update(message):
    print(f"Order {message['id']}: {message['status']}")

def on_error(message):
    print(f"Error: {message}")

def on_close(message):
    print("Connection closed")

def on_open():
    print("Connected to order socket")

order_socket = order_ws.FyersOrderSocket(
    access_token=f"{app_id}:{access_token}",
    write_to_file=False,
    log_path="",
    on_order_update=on_order_update,
    on_error=on_error,
    on_close=on_close,
    on_open=on_open
)
order_socket.connect()
```

## Order Update Message Format

```json
{
  "id": "240915000123456",
  "type": "order_update",
  "status": 2,
  "symbol": "NSE:RELIANCE-EQ",
  "qty": 5,
  "tradedQty": 5,
  "limitPrice": 2505.0,
  "tradedPrice": 2499.85,
  "side": 1,
  "productType": "CNC",
  "orderType": 1,
  "validity": "DAY",
  "message": "ORDER FILLED"
}
```

## Order Status Codes

| Code | Status | Description |
|------|--------|-------------|
| `1` | CANCELLED | Order cancelled |
| `2` | TRADED | Order fully executed |
| `4` | TRANSIT | Order in transit |
| `5` | REJECTED | Order rejected |
| `6` | PENDING | Order pending |

## FyersPositionSocket (P&L Updates)

```python
from fyers_apiv3.FyersWebsocket import positions_ws

def on_position_update(message):
    print(f"Position P&L: {message['pl']}")

position_socket = positions_ws.FyersPositionSocket(
    access_token=f"{app_id}:{access_token}",
    on_position_update=on_position_update
)
position_socket.connect()
```

## AlgoChanakya Integration

- FyersOrderSocket is **NOT currently implemented** in AlgoChanakya
- AlgoChanakya uses REST polling for order status
- Current WebSocket only implements `FyersDataSocket` for market data ticks
- Future: Add `FyersOrderSocket` to Fyers ticker adapter
- Files: `backend/app/services/brokers/market_data/ticker/adapters/fyers.py`
