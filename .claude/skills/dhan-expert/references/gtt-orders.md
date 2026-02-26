# Dhan Forever Orders (GTT) Reference

> Source: Dhan API v2 Docs (https://dhanhq.co/docs/v2/forever/) | Last verified: 2026-02-26

## Overview

Dhan's GTT equivalent is called **"Forever Orders"** — orders that persist until triggered or manually cancelled (up to 365 days).

## Endpoints (all require static IP whitelisting for write operations)

| Method | Endpoint | Description | IP Whitelist? |
|--------|----------|-------------|---------------|
| POST | `/v2/forever/orders` | Create forever order | Yes |
| GET | `/v2/forever/all` | List all forever orders | No |
| PUT | `/v2/forever/orders/{order-id}` | Modify forever order | Yes |
| DELETE | `/v2/forever/orders/{order-id}` | Cancel forever order | Yes |

## Forever Order Types

| Type | Code | Description |
|------|------|-------------|
| Single | `SINGLE` | One trigger condition |
| OCO | `OCO` | Two conditions — one fires, other cancels |

## Create Forever Order

**POST** `/v2/forever/orders`

### Request Body (SINGLE)
```json
{
  "dhanClientId": "1000000003",
  "correlationId": "my-gtt-001",
  "orderFlag": "SINGLE",
  "transactionType": "BUY",
  "exchangeSegment": "NSE_EQ",
  "productType": "CNC",
  "orderType": "LIMIT",
  "validity": "DAY",
  "securityId": "2885",
  "quantity": 5,
  "disclosedQuantity": 0,
  "price": 2505.0,
  "triggerPrice": 2500.0,
  "price1": 0.0,
  "triggerPrice1": 0.0,
  "quantity1": 0
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dhanClientId` | string | Yes | User ID |
| `correlationId` | string | No | Tracking ID (max 30 chars, alphanumeric + spaces/underscores/hyphens) |
| `orderFlag` | string | Yes | `SINGLE` or `OCO` |
| `transactionType` | string | Yes | `BUY` or `SELL` |
| `exchangeSegment` | string | Yes | `NSE_EQ`, `BSE_EQ`, `NSE_FNO`, `BSE_FNO` |
| `productType` | string | Yes | `CNC` or `MTF` only (not INTRADAY/MARGIN) |
| `orderType` | string | Yes | `LIMIT`, `MARKET` |
| `validity` | string | Yes | `DAY`, `IOC` |
| `securityId` | string | Yes | Instrument ID |
| `quantity` | int | Yes | Order quantity |
| `disclosedQuantity` | int | No | Must be >30% of qty if used |
| `price` | float | Yes | Order price for leg 1 |
| `triggerPrice` | float | Yes | Trigger price for leg 1 |
| `price1` | float | OCO only | Order price for leg 2 |
| `triggerPrice1` | float | OCO only | Trigger price for leg 2 |
| `quantity1` | int | OCO only | Quantity for leg 2 |

### For OCO (Two-leg)
- Set `orderFlag: "OCO"`
- Leg 1 (`price` + `triggerPrice`) = first condition (e.g., target)
- Leg 2 (`price1` + `triggerPrice1` + `quantity1`) = second condition (e.g., stop-loss)
- When one leg triggers, the other is automatically cancelled

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
