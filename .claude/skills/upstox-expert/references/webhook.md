# Upstox Webhook

> Source: [Upstox API Docs](https://upstox.com/developer/api-documentation/open-api) | Last verified: 2026-02-25

Upstox webhooks deliver real-time event notifications (order updates, GTT triggers) via HTTP POST to your endpoint.

---

## Overview

| Property | Value |
|----------|-------|
| Setup | My Apps dashboard (no code required for registration) |
| Method | HTTP POST only |
| Auth | None required on your endpoint |
| Response | Must return 2XX within timeout |
| Events | Order Updates (default), GTT Updates (opt-in) |
| Retries | Upstox retries on non-2XX responses |

---

## Setup

1. Go to Upstox developer portal → **My Apps** → select your app
2. Navigate to **Settings** → **Webhooks**
3. Enter your webhook URL (must be publicly accessible HTTPS endpoint)
4. Select event types to receive:
   - **Order Updates** — enabled by default
   - **GTT Updates** — opt-in checkbox
5. Save settings

**Requirements for your webhook endpoint:**
- Must be publicly accessible (no localhost)
- Must use HTTPS
- Must return HTTP 2XX response within timeout
- No authentication headers required by Upstox
- Implement idempotency — same event may be delivered more than once on retry

---

## Event: Order Update

Fired when an order status changes (placed, complete, rejected, cancelled, etc.).

### Payload Format

```json
{
  "event": "order_update",
  "timestamp": "2025-02-27T14:30:01+05:30",
  "data": {
    "order_id": "25022700123456",
    "status": "complete",
    "instrument_token": "NSE_FO|12345",
    "trading_symbol": "NIFTY2522725000CE",
    "exchange": "NSE",
    "transaction_type": "BUY",
    "quantity": 25,
    "price": 150.5,
    "average_price": 150.25,
    "product": "D",
    "order_type": "LIMIT",
    "validity": "DAY",
    "tag": "autopilot",
    "placed_by": "AB1234",
    "status_message": null,
    "filled_quantity": 25,
    "pending_quantity": 0,
    "is_amo": false,
    "parent_order_id": null
  }
}
```

### Order Status Values

| Status | Description |
|--------|-------------|
| `open` | Order placed, waiting to fill |
| `complete` | Fully filled |
| `rejected` | Rejected by exchange |
| `cancelled` | Manually cancelled |
| `trigger pending` | SL order waiting for trigger |
| `modify pending` | Modification in progress |

---

## Event: GTT Update (opt-in)

Fired when a GTT order is triggered (rule fires) or status changes.

### Payload Format

```json
{
  "event": "gtt_update",
  "timestamp": "2025-02-27T14:30:01+05:30",
  "data": {
    "gtt_id": "gtt_abc123def456",
    "status": "triggered",
    "instrument_token": "NSE_FO|12345",
    "trading_symbol": "NIFTY2522725000CE",
    "transaction_type": "SELL",
    "quantity": 25,
    "product": "D",
    "triggered_rule": {
      "id": "rule_1",
      "strategy_type": "TARGET",
      "trigger_price": 201.0,
      "triggered_at_price": 201.5,
      "placed_order_id": "25022700123457"
    }
  }
}
```

---

## Field Deprecation Notice

Upstox migrated webhook payload fields from **lowercase** to **snake_case** in 2025. Old field names are deprecated:

| Deprecated (old) | Current (use this) |
|------------------|--------------------|
| `orderid` | `order_id` |
| `transactiontype` | `transaction_type` |
| `instrumenttype` | `instrument_type` |
| `tradingsymbol` | `trading_symbol` |
| `averageprice` | `average_price` |

Update webhook handlers to use snake_case field names.

---

## AlgoChanakya Integration Notes

- **Not yet implemented** (Feb 2026) — webhook receiver endpoint not in codebase
- Would replace polling-based order status checks with push-based updates
- Priority: Useful for GTT order tracking once GTT adapter is implemented
- Implement idempotency using `order_id` as deduplication key (store in Redis or DB)
- Validate webhook source using IP allowlisting from Upstox (check their IP range)
- Use webhook for `complete`/`rejected` events to update `orders` table and trigger AutoPilot callbacks

---

## Sample FastAPI Webhook Handler

```python
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

@router.post("/webhooks/upstox")
async def upstox_webhook(request: Request):
    try:
        payload = await request.json()
        event = payload.get("event")
        data = payload.get("data", {})

        if event == "order_update":
            order_id = data.get("order_id")
            status = data.get("status")
            # Update order status in database
            await handle_order_update(order_id, status, data)

        elif event == "gtt_update":
            gtt_id = data.get("gtt_id")
            status = data.get("status")
            # Handle GTT trigger
            await handle_gtt_update(gtt_id, status, data)

        return {"status": "ok"}  # Must return 2XX

    except Exception as e:
        # Still return 2XX to prevent retries for bad payloads
        return {"status": "error", "message": str(e)}
```
