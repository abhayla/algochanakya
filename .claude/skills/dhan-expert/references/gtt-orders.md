# Dhan Forever Orders (GTT) Reference

> Source: Dhan API v2 Docs (https://dhanhq.co/docs/v2/) | Last verified: 2026-02-25

## Overview

Dhan's GTT equivalent is called **"Forever Orders"** — orders that persist until triggered or manually cancelled (up to 365 days).

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/forever/orders` | Create forever order |
| GET | `/v2/forever/orders` | List all forever orders |
| PUT | `/v2/forever/orders` | Modify forever order |
| DELETE | `/v2/forever/orders` | Cancel forever order |

## Forever Order Types

| Type | Code | Description |
|------|------|-------------|
| Single | `SINGLE` | One trigger condition |
| OCO | `OCO` | Two conditions — one fires, other cancels |

## Create Forever Order

**POST** `/v2/forever/orders`

### Request Body
```json
{
  "dhanClientId": "1000000003",
  "orderFlag": "SINGLE",
  "transactionType": "BUY",
  "exchangeSegment": "NSE_EQ",
  "productType": "CNC",
  "orderType": "LIMIT",
  "validity": "DAY",
  "tradingSymbol": "RELIANCE",
  "securityId": "2885",
  "quantity": 5,
  "disclosedQuantity": 0,
  "price": 2505.0,
  "triggerPrice": 2500.0,
  "price1": 0.0,
  "triggerPrice1": 0.0
}
```

### For OCO (Two-leg)
- Set `orderFlag: "OCO"`
- `price` + `triggerPrice` = first leg (e.g., target)
- `price1` + `triggerPrice1` = second leg (e.g., stop-loss)

## Response
```json
{
  "status": "success",
  "remarks": "",
  "data": {
    "orderId": "112111182198",
    "orderStatus": "PENDING"
  }
}
```

## Forever Order Status

| Status | Description |
|--------|-------------|
| `PENDING` | Waiting for trigger |
| `TRIGGERED` | Trigger fired, order sent |
| `EXPIRED` | Past validity period |
| `CANCELLED` | Manually cancelled |

## Validity

Forever orders are valid for up to **365 days** from creation.

## Exchange Segments Supported

| Segment | Description |
|---------|-------------|
| `NSE_EQ` | NSE Cash |
| `BSE_EQ` | BSE Cash |
| `NSE_FNO` | NSE Futures & Options |
| `BSE_FNO` | BSE F&O |

## AlgoChanakya Integration

- Forever Orders are **NOT yet implemented** in AlgoChanakya's Dhan adapter
- Current adapter at `backend/app/services/brokers/dhan_order_adapter.py` supports standard orders only
- Future: Add GTT support with `/forever/orders` endpoints

## Common Errors

| Error Code | Cause | Fix |
|------------|-------|-----|
| DH-904 | Invalid security_id | Verify ID from instrument CSV |
| DH-905 | Invalid trigger price | Check price relative to LTP |
| DH-200 | Insufficient margin | Add funds |
