# SmartAPI GTT Orders Reference

> Source: SmartAPI (Angel One) Official Docs | Last verified: 2026-02-25

## Overview

SmartAPI's GTT (Good Till Triggered) orders allow placing orders that execute when a price condition is met. Rules remain active until triggered, cancelled, or expired (max 365 days).

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/rest/secure/angelbroking/gtt/v1/createRule` | Create GTT rule |
| GET | `/rest/secure/angelbroking/gtt/v1/ruleDetails` | Get GTT rule details |
| PUT | `/rest/secure/angelbroking/gtt/v1/modifyRule` | Modify existing GTT rule |
| POST | `/rest/secure/angelbroking/gtt/v1/cancelRule` | Cancel GTT rule |
| POST | `/rest/secure/angelbroking/gtt/v1/ruleList` | List all GTT rules |

**Base URL:** `https://apiconnect.angelbroking.com`

## Request Headers

All GTT endpoints require standard authenticated headers:

```
Authorization: Bearer {jwtToken}
X-UserType: USER
X-SourceID: WEB
X-ClientLocalIP: {client_ip}
X-ClientPublicIP: {client_ip}
X-MACAddress: {mac_address}
X-PrivateKey: {api_key}
Content-Type: application/json
```

## Create GTT Rule

**POST** `/rest/secure/angelbroking/gtt/v1/createRule`

### Request Body

```json
{
  "tradingsymbol": "SBIN-EQ",
  "symboltoken": "3045",
  "exchange": "NSE",
  "transactiontype": "BUY",
  "producttype": "DELIVERY",
  "price": "500.00",
  "qty": "10",
  "disclosedqty": "0",
  "triggerprice": "490.00",
  "timeperiod": "365"
}
```

### Response

```json
{
  "status": true,
  "message": "SUCCESS",
  "errorcode": "",
  "data": {
    "id": "GTT123456"
  }
}
```

## Get GTT Rule Details

**GET** `/rest/secure/angelbroking/gtt/v1/ruleDetails?id={gtt_rule_id}`

### Response

```json
{
  "status": true,
  "message": "SUCCESS",
  "data": {
    "id": "GTT123456",
    "status": "ACTIVE",
    "tradingsymbol": "SBIN-EQ",
    "symboltoken": "3045",
    "exchange": "NSE",
    "transactiontype": "BUY",
    "producttype": "DELIVERY",
    "price": "500.00",
    "qty": "10",
    "disclosedqty": "0",
    "triggerprice": "490.00",
    "timeperiod": "365",
    "createdon": "2025-02-01 09:15:00",
    "updatedon": "2025-02-01 09:15:00"
  }
}
```

## List GTT Rules

**POST** `/rest/secure/angelbroking/gtt/v1/ruleList`

### Request Body

```json
{
  "status": ["NEW", "CANCELLED", "ACTIVE", "SENTTOEXCHANGE", "FORALL"],
  "page": 1,
  "count": 10
}
```

Use `"FORALL"` in the status array to retrieve all rules regardless of status.

### Response

```json
{
  "status": true,
  "message": "SUCCESS",
  "data": [
    {
      "id": "GTT123456",
      "status": "ACTIVE",
      "tradingsymbol": "SBIN-EQ",
      "triggerprice": "490.00",
      "price": "500.00",
      "qty": "10"
    }
  ]
}
```

## Modify GTT Rule

**PUT** `/rest/secure/angelbroking/gtt/v1/modifyRule`

### Request Body

```json
{
  "id": "GTT123456",
  "tradingsymbol": "SBIN-EQ",
  "symboltoken": "3045",
  "exchange": "NSE",
  "transactiontype": "BUY",
  "producttype": "DELIVERY",
  "price": "505.00",
  "qty": "10",
  "disclosedqty": "0",
  "triggerprice": "495.00",
  "timeperiod": "365"
}
```

## Cancel GTT Rule

**POST** `/rest/secure/angelbroking/gtt/v1/cancelRule`

### Request Body

```json
{
  "id": "GTT123456",
  "symboltoken": "3045",
  "exchange": "NSE"
}
```

## Rule Status Values

| Status | Description |
|--------|-------------|
| `NEW` | Rule just created, not yet active |
| `ACTIVE` | Rule is live and monitoring price |
| `SENTTOEXCHANGE` | Trigger hit, order sent to exchange |
| `FORALL` | Filter value for list API (not a real status) |
| `CANCELLED` | Rule cancelled by user |
| `EXECUTED` | Order fully executed |
| `FAILED` | Order placement failed after trigger |

## Request Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tradingsymbol` | string | Yes | Trading symbol in SmartAPI format (e.g., `SBIN-EQ`) |
| `symboltoken` | string | Yes | SmartAPI instrument token (from instrument master) |
| `exchange` | string | Yes | NSE, BSE, NFO, MCX |
| `transactiontype` | string | Yes | `BUY` or `SELL` |
| `producttype` | string | Yes | `DELIVERY`, `INTRADAY`, `MARGIN`, `CARRYFORWARD` |
| `price` | string | Yes | Limit order price (what price to buy/sell at) |
| `qty` | string | Yes | Number of shares/contracts |
| `disclosedqty` | string | No | Disclosed quantity (usually "0") |
| `triggerprice` | string | Yes | Price condition to trigger the order |
| `timeperiod` | string | Yes | Days rule is valid (1-365) |

## GTT Rule Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Single** | One trigger price | Buy below ₹490 or Sell above ₹510 |
| **OCO** (One Cancels Other) | Two triggers — when one fires, the other cancels | Set profit target + stop loss simultaneously |

## Validity

GTT rules are valid for up to **365 days** from creation. The `timeperiod` field specifies the number of days.

## Price Behavior

- `triggerprice`: When LTP reaches this price, the order is placed
- `price`: The limit order price used when the order is placed
- If `triggerprice == price`: Equivalent to a limit order that waits for the price
- For BUY GTT: `triggerprice` is usually slightly above current price (buy on breakout) or below (buy on dip)
- For SELL GTT: `triggerprice` is usually below current price (stop loss) or above (take profit)

## Integration Notes

- GTT is **NOT yet implemented** in AlgoChanakya's SmartAPI order adapter
- AlgoChanakya currently only supports standard order types (NORMAL, STOPLOSS, AMO)
- Implementation target: `backend/app/services/brokers/angelone_adapter.py`
- The `AngelOneAdapter` (428 lines) handles standard orders — GTT would extend this

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Invalid token | `jwtToken` expired | Re-authenticate |
| Invalid symbol | Wrong `symboltoken` for exchange | Look up in instrument master |
| Invalid price | Price outside circuit limits | Use a valid price within daily range |
| Rule not found | Wrong GTT `id` | Fetch rule list first to get valid IDs |
| Cannot modify | Rule in terminal state | Cannot modify EXECUTED or CANCELLED rules |
