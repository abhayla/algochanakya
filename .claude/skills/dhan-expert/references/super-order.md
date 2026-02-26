# Dhan Super Order Reference

> Source: Dhan API v2 Docs (https://dhanhq.co/docs/v2/super-order/) | Last verified: 2026-02-26

## Overview

Super Order combines **entry + target + stop-loss** into a single API call with optional **trailing stop-loss**. Available across all exchanges and segments. This is distinct from Forever Orders (GTT) — Super Orders execute within the same trading session.

**Key distinction:**
- **Super Order** = bracket-style same-session execution (entry fires, then target/SL compete)
- **Forever Order** = GTT that persists until triggered or cancelled (up to 365 days)

## Endpoints

| Method | Endpoint | Description | IP Whitelist? |
|--------|----------|-------------|---------------|
| POST | `/v2/super/orders` | Create super order | Yes |
| PUT | `/v2/super/orders/{order-id}` | Modify pending super order | Yes |
| DELETE | `/v2/super/orders/{order-id}/{order-leg}` | Cancel a specific leg | Yes |
| GET | `/v2/super/orders` | List all super orders for the day | Yes |

All 4 endpoints require **static IP whitelisting**.

## Create Super Order

**POST** `/v2/super/orders`

### Request Body

```json
{
  "dhanClientId": "1000000003",
  "correlationId": "my-bracket-001",
  "transactionType": "BUY",
  "exchangeSegment": "NSE_FNO",
  "productType": "MARGIN",
  "orderType": "LIMIT",
  "securityId": "43854",
  "quantity": 50,
  "price": 150.00,
  "targetPrice": 165.00,
  "stopLossPrice": 142.00,
  "trailingJump": 2.0
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dhanClientId` | string | Yes | User ID |
| `correlationId` | string | No | Tracking ID (max 30 chars, alphanumeric + spaces/underscores/hyphens) |
| `transactionType` | enum | Yes | `BUY` or `SELL` |
| `exchangeSegment` | enum | Yes | `NSE_EQ`, `NSE_FNO`, `BSE_EQ`, `BSE_FNO`, `MCX_COMM`, etc. |
| `productType` | enum | Yes | `CNC`, `INTRADAY`, `MARGIN`, `MTF` (NOT `CO` or `BO`) |
| `orderType` | enum | Yes | `LIMIT` or `MARKET` |
| `securityId` | string | Yes | Exchange instrument ID |
| `quantity` | int | Yes | Share/lot count |
| `price` | float | Yes | Entry price |
| `targetPrice` | float | Yes | Target exit price |
| `stopLossPrice` | float | Yes | Stop-loss price |
| `trailingJump` | float | Yes | Trail step size; pass `0` to disable trailing |

### Response

```json
{
  "orderId": "1234567890123",
  "orderStatus": "PENDING"
}
```

**Status values on create:** `TRANSIT`, `PENDING`, `REJECTED`

## Modify Super Order

**PUT** `/v2/super/orders/{order-id}`

Modification depends on the current state of the entry leg and which leg you're modifying.

### When entry is still pending (`PENDING` or `PART_TRADED`):

Modify `legName: "ENTRY_LEG"` — can change: `quantity`, `price`, `targetPrice`, `stopLossPrice`, `trailingJump`

```json
{
  "dhanClientId": "1000000003",
  "orderId": "1234567890123",
  "legName": "ENTRY_LEG",
  "quantity": 50,
  "price": 148.00,
  "targetPrice": 162.00,
  "stopLossPrice": 140.00,
  "trailingJump": 2.0
}
```

### After entry is executed (`TRADED`):

Only target/SL can be modified:

```json
{ "dhanClientId": "1000000003", "orderId": "...", "legName": "TARGET_LEG", "targetPrice": 168.00 }
{ "dhanClientId": "1000000003", "orderId": "...", "legName": "STOP_LOSS_LEG", "stopLossPrice": 144.00, "trailingJump": 3.0 }
```

### Leg Names for Modify

| `legName` | What changes |
|-----------|--------------|
| `ENTRY_LEG` | quantity, price, targetPrice, stopLossPrice, trailingJump (entry must be PENDING/PART_TRADED) |
| `TARGET_LEG` | targetPrice only |
| `STOP_LOSS_LEG` | stopLossPrice and trailingJump |

## Cancel Super Order

**DELETE** `/v2/super/orders/{order-id}/{order-leg}`

| `order-leg` | Effect |
|-------------|--------|
| `{order-id}` (just the order ID, no leg) | Cancels entire order (all legs) |
| `ENTRY_LEG` | Cancels entry + prevents further execution |
| `TARGET_LEG` | Cancels target leg only |
| `STOP_LOSS_LEG` | Cancels SL leg only |

**Returns:** HTTP 202 Accepted

**Warning:** Cancelling an individual leg prevents re-adding it later. You cannot add a new target/SL after cancelling one.

## List Super Orders

**GET** `/v2/super/orders`

Returns array of super orders. Each entry includes top-level order fields plus a nested `legDetails` array.

### Top-level fields per order:
`dhanClientId`, `orderId`, `correlationId`, `orderStatus`, `transactionType`, `exchangeSegment`, `productType`, `orderType`, `validity` (always `DAY`), `tradingSymbol`, `securityId`, `quantity`, `remainingQuantity`, `filledQty`, `price`, `ltp`, `averageTradedPrice`, `afterMarketOrder`, `legName`, `exchangeOrderId`, `createTime`, `updateTime`, `exchangeTime`, `omsErrorDescription`

### `legDetails` array per order:
`orderId`, `legName`, `transactionType`, `totalQuantity`, `remainingQuantity`, `triggeredQuantity`, `price`, `orderStatus`, `trailingJump`

## Order Status Values

| Status | Meaning |
|--------|---------|
| `TRANSIT` | Order in transit to exchange |
| `PENDING` | Waiting for execution |
| `TRADED` | Entry leg fully executed |
| `PART_TRADED` | Entry leg partially filled |
| `TRIGGERED` | Exit leg (target/SL) has been triggered |
| `CLOSED` | Entry + one exit leg fully executed (order complete) |
| `REJECTED` | Order rejected |
| `CANCELLED` | Order cancelled |

**`CLOSED` = final state** — entry executed AND one of target/SL also executed.

## Key Constraints

1. **Product types:** Only `CNC`, `INTRADAY`, `MARGIN`, `MTF`. NOT `CO` or `BO`.
2. **Once entry is TRADED:** Only target/SL prices and trail jump are modifiable.
3. **Leg cancellation is permanent:** Cannot re-add a cancelled leg.
4. **trailingJump = 0:** Disables trailing stop-loss (converts to regular SL).
5. **Static IP whitelist required** for all 4 endpoints.
6. **correlationId max 30 chars:** Alphanumeric + spaces/underscores/hyphens only.
7. **BUY super order:** targetPrice > entry price > stopLossPrice
8. **SELL super order:** targetPrice < entry price < stopLossPrice

## AlgoChanakya Integration

- Super Orders are **NOT yet implemented** in AlgoChanakya
- Planned use: AutoPilot bracket order execution
- Would be implemented in `backend/app/services/brokers/dhan_order_adapter.py`
- Useful for AutoPilot strategies that need automated target + stop-loss management

## Example: NIFTY Options Bracket Trade

```python
# Place a BUY bracket on NIFTY CE
super_order_payload = {
    "dhanClientId": client_id,
    "correlationId": f"autopilot-nifty-{strategy_id}",
    "transactionType": "BUY",
    "exchangeSegment": "NSE_FNO",
    "productType": "MARGIN",
    "orderType": "LIMIT",
    "securityId": "43854",   # From token_manager
    "quantity": 50,
    "price": 150.00,
    "targetPrice": 175.00,   # ~17% profit
    "stopLossPrice": 135.00, # ~10% loss
    "trailingJump": 3.0,     # Trail SL up by 3 as price rises
}

response = await dhan_client.post("/v2/super/orders", json=super_order_payload)
order_id = response["orderId"]
```
