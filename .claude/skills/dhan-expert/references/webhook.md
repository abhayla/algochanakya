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

### Authentication (Individual / SELF)

The auth message uses `MsgCode: 42` (hardcoded) and `UserType: "SELF"`:

```python
import websockets
import json

async def connect_order_updates(access_token: str, client_id: str):
    async with websockets.connect("wss://api-order-update.dhan.co") as ws:
        # Send auth immediately after connecting
        auth_msg = {
            "LoginReq": {
                "MsgCode": 42,            # Always 42 — do not change
                "ClientId": client_id,
                "Token": access_token,
            },
            "UserType": "SELF"
        }
        await ws.send(json.dumps(auth_msg))

        # Receive order update messages
        async for message in ws:
            data = json.loads(message)
            if data.get("type") == "order_alert":
                order = data["Data"]
                print(f"Order {order['OrderNo']}: {order['Status']}")
```

### Authentication (Partner — all users' orders)

```python
auth_msg = {
    "LoginReq": {"MsgCode": 42, "ClientId": "partner_id"},
    "UserType": "PARTNER",
    "Secret": "partner_secret"
}
```

### Order Update Message Fields

Key fields in `Data` object of `order_alert` messages:

| Field | Description |
|-------|-------------|
| `OrderNo` | Dhan order reference |
| `ExchOrderNo` | Exchange order reference |
| `Status` | `TRANSIT`, `PENDING`, `REJECTED`, `CANCELLED`, `TRADED`, `EXPIRED` |
| `TxnType` | `B` = Buy, `S` = Sell (short codes, not `BUY`/`SELL`) |
| `OrderType` | `LMT`, `MKT`, `SL`, `SLM` (short codes) |
| `Product` | `C`=CNC, `I`=Intraday, `M`=Margin, `F`=MTF, `V`=CO, `B`=BO |
| `TradedPrice` | Execution price |
| `TradedQty` | Filled quantity |
| `RemainingQuantity` | Unfilled quantity |
| `LegNo` | Multi-leg: `1`=Entry, `2`=Stop Loss, `3`=Target |
| `Remarks` | `"Super Order"` if part of a super order |
| `CorrelationId` | User tracking ID |
| `StrikePrice`, `ExpiryDate`, `OptType` | F&O fields |

**Note:** The WebSocket uses **short enum codes** (`B`/`S`, `LMT`/`MKT`, `C`/`I`) — different from the REST API which uses full strings (`BUY`/`SELL`, `LIMIT`/`MARKET`, `CNC`/`INTRADAY`).

## Postback Requirements

- Endpoint must be **publicly accessible** — localhost (`127.0.0.1`) and `localhost` URLs are rejected
- Must return **2XX response** within timeout
- Dhan retries if your endpoint returns non-2XX
- No signature/HMAC authentication on your endpoint (Dhan calls it directly without verification)
- Configure the Postback URL at `web.dhan.co` during access token generation

## AlgoChanakya Integration

- Postback and Order Update WebSocket are **NOT currently used** in AlgoChanakya
- AlgoChanakya polls REST order book for order status updates
- Future: Implement postback receiver at `POST /api/webhooks/dhan/order-update`
- Future: Connect to Live Order Update WebSocket for real-time updates
