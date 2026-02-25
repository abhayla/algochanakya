# Dhan Postback / Webhook Reference

> Source: Dhan API v2 Docs (https://dhanhq.co/docs/v2/) | Last verified: 2026-02-25

## Overview

Dhan supports **Postback** — HTTP POST notifications sent to your URL when orders are executed, rejected, or cancelled. Also provides a dedicated **Live Order Update WebSocket** for real-time updates.

## Postback Setup

Configure postback URL in Dhan web portal:
1. Login to trade.dhan.co
2. Navigate to API Settings
3. Set Postback URL
4. Save

No code required for setup — Dhan calls your URL automatically.

## Postback Payload

```json
{
  "dhanClientId": "1000000003",
  "orderId": "112111182198",
  "correlationId": "123abc456def",
  "orderStatus": "TRADED",
  "transactionType": "BUY",
  "exchangeSegment": "NSE_EQ",
  "productType": "CNC",
  "orderType": "MARKET",
  "validity": "DAY",
  "tradingSymbol": "RELIANCE",
  "securityId": "2885",
  "quantity": 5,
  "disclosedQuantity": 0,
  "price": 0.0,
  "triggerPrice": 0.0,
  "afterMarketOrder": false,
  "boProfitValue": 0.0,
  "boStopLossValue": 0.0,
  "legName": "ENTRY",
  "createTime": "2025-02-25 10:30:45",
  "updateTime": "2025-02-25 10:30:46",
  "exchangeTime": "2025-02-25 10:30:46",
  "drvExpiryDate": null,
  "drvOptionType": null,
  "drvStrikePrice": 0.0,
  "omsErrorCode": null,
  "omsErrorDescription": null,
  "algoId": null,
  "remainingQuantity": 0,
  "averageTradedPrice": 2499.85,
  "filledQty": 5
}
```

## Order Status Values

| Status | Description |
|--------|-------------|
| `TRANSIT` | In transit to exchange |
| `PENDING` | Order pending |
| `TRADED` | Fully executed |
| `PART_TRADED` | Partially executed |
| `CANCELLED` | Order cancelled |
| `REJECTED` | Order rejected |
| `EXPIRED` | Day order expired |

## Live Order Update WebSocket

**URL:** `wss://api-order-update.dhan.co`

Alternative to postback — real-time WebSocket stream of order updates.

```python
import websocket
import json

def on_open(ws):
    auth_msg = {
        "access-token": access_token,
        "dhan-client-id": client_id
    }
    ws.send(json.dumps(auth_msg))

def on_message(ws, message):
    data = json.loads(message)
    order_id = data.get("orderId")
    status = data.get("orderStatus")
    print(f"Order {order_id}: {status}")

ws = websocket.WebSocketApp(
    "wss://api-order-update.dhan.co",
    on_open=on_open,
    on_message=on_message
)
ws.run_forever()
```

## Postback Requirements

- Endpoint must be **publicly accessible** (not localhost)
- Must return **2XX response** within timeout
- Dhan retries if your endpoint returns non-2XX
- No authentication required on your endpoint (Dhan calls it directly)

## AlgoChanakya Integration

- Postback and Order Update WebSocket are **NOT currently used** in AlgoChanakya
- AlgoChanakya polls REST order book for order status updates
- Future: Implement postback receiver at `POST /api/webhooks/dhan/order-update`
- Future: Connect to Live Order Update WebSocket for real-time updates
