# Upstox GTT Orders (Good Till Triggered)

> Source: [Upstox API Docs](https://upstox.com/developer/api-documentation/open-api) | Last verified: 2026-02-25

GTT (Good Till Triggered) orders persist until a price condition is met, then automatically place a regular order. Launched Feb 28, 2025. Uses v3 API.

---

## Overview

| Property | Value |
|----------|-------|
| API Version | v3 |
| Base Path | `/v3/order/gtt/` |
| Availability | All users (Basic + Plus) |
| Instruments | NSE, BSE equities and F&O |
| Products | I (Intraday/MIS), D (Delivery/CNC), MTF |
| Trailing Stop Loss | Beta (Jun 2025) |

---

## GTT Types

| Type | Rules | Use Case |
|------|-------|----------|
| `SINGLE` | 1 rule | Simple trigger (entry OR target OR stoploss) |
| `MULTIPLE` | 2–3 rules (OCO) | Target + Stoploss together (One Cancels Other) |

---

## Rule Strategy Types

| Strategy Type | Trigger Direction | Use Case |
|--------------|-------------------|----------|
| `ENTRY` | `ABOVE` or `BELOW` | Enter position when price reaches level |
| `TARGET` | `ABOVE` | Exit position at profit target |
| `STOPLOSS` | `BELOW` | Exit position at loss limit |

## Trigger Types

| Trigger Type | Description |
|-------------|-------------|
| `ABOVE` | Fire when LTP goes above trigger_price |
| `BELOW` | Fire when LTP goes below trigger_price |
| `IMMEDIATE` | Fire immediately at current price |

---

## Endpoint: Place GTT Order

```
POST /v3/order/gtt/place
Content-Type: application/json
Authorization: Bearer {access_token}
```

### Request Body (SINGLE — Entry above)

```json
{
  "type": "SINGLE",
  "quantity": 25,
  "product": "D",
  "transaction_type": "BUY",
  "instrument_token": "NSE_FO|12345",
  "rules": [
    {
      "strategy_type": "ENTRY",
      "trigger_type": "ABOVE",
      "price": 150.0,
      "trigger_price": 151.0
    }
  ]
}
```

### Request Body (MULTIPLE — Target + Stoploss)

```json
{
  "type": "MULTIPLE",
  "quantity": 25,
  "product": "D",
  "transaction_type": "SELL",
  "instrument_token": "NSE_FO|12345",
  "rules": [
    {
      "strategy_type": "TARGET",
      "trigger_type": "ABOVE",
      "price": 200.0,
      "trigger_price": 201.0
    },
    {
      "strategy_type": "STOPLOSS",
      "trigger_type": "BELOW",
      "price": 100.0,
      "trigger_price": 99.0
    }
  ]
}
```

### Trailing Stop Loss (Beta, Jun 2025)

```json
{
  "type": "SINGLE",
  "quantity": 25,
  "product": "D",
  "transaction_type": "SELL",
  "instrument_token": "NSE_FO|12345",
  "rules": [
    {
      "strategy_type": "STOPLOSS",
      "trigger_type": "BELOW",
      "price": 100.0,
      "trigger_price": 99.0,
      "trailing_stop_loss": {
        "enabled": true,
        "trail_gap": 5.0
      }
    }
  ]
}
```

### Response

```json
{
  "status": "success",
  "data": {
    "id": "gtt_abc123def456"
  }
}
```

---

## Endpoint: Modify GTT Order

```
PUT /v3/order/gtt/modify
Content-Type: application/json
```

### Request Body

```json
{
  "id": "gtt_abc123def456",
  "quantity": 50,
  "product": "D",
  "transaction_type": "SELL",
  "rules": [
    {
      "id": "rule_1",
      "strategy_type": "TARGET",
      "trigger_type": "ABOVE",
      "price": 210.0,
      "trigger_price": 211.0
    },
    {
      "id": "rule_2",
      "strategy_type": "STOPLOSS",
      "trigger_type": "BELOW",
      "price": 95.0,
      "trigger_price": 94.0
    }
  ]
}
```

> **Note:** Must include `id` for each rule being modified. Rules without `id` are treated as new.

---

## Endpoint: Cancel GTT Order

```
DELETE /v3/order/gtt/cancel?id={gtt_id}
```

### Response

```json
{
  "status": "success",
  "data": {
    "id": "gtt_abc123def456"
  }
}
```

---

## Endpoint: Get GTT Orders

```
GET /v3/order/gtt/details            # All GTT orders
GET /v3/order/gtt/details?id={id}    # Specific GTT order
```

### Response

```json
{
  "status": "success",
  "data": {
    "id": "gtt_abc123def456",
    "status": "ACTIVE",
    "type": "MULTIPLE",
    "instrument_token": "NSE_FO|12345",
    "trading_symbol": "NIFTY2522725000CE",
    "quantity": 25,
    "product": "D",
    "transaction_type": "SELL",
    "created_on": "2025-02-27T10:00:00+05:30",
    "updated_on": "2025-02-27T10:00:00+05:30",
    "expiry": "2026-02-27T00:00:00+05:30",
    "rules": [
      {
        "id": "rule_1",
        "strategy_type": "TARGET",
        "trigger_type": "ABOVE",
        "price": 200.0,
        "trigger_price": 201.0,
        "status": "PENDING"
      },
      {
        "id": "rule_2",
        "strategy_type": "STOPLOSS",
        "trigger_type": "BELOW",
        "price": 100.0,
        "trigger_price": 99.0,
        "status": "PENDING"
      }
    ]
  }
}
```

### GTT Status Values

| Status | Description |
|--------|-------------|
| `ACTIVE` | Waiting for trigger |
| `TRIGGERED` | Rule fired, order placed |
| `CANCELLED` | Manually cancelled |
| `EXPIRED` | Past expiry date |
| `REJECTED` | Triggered but order rejected |

---

## Webhook Integration

GTT updates can be received via webhook (opt-in). When a GTT rule fires:
- Webhook sends event type `gtt_update`
- Includes GTT id, rule id, triggered price, placed order_id
- Configure in My Apps dashboard

See [webhook.md](./webhook.md) for webhook setup and GTT payload format.

---

## GTT Error Codes

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI1126` | 400 | Invalid GTT order type | Use `SINGLE` or `MULTIPLE` |
| `UDAPI1128` | 400 | Invalid number of rules | SINGLE: exactly 1, MULTIPLE: 2–3 |
| `UDAPI1130` | 400 | Invalid trigger type | Use `ABOVE`, `BELOW`, or `IMMEDIATE` |
| `UDAPI1132` | 400 | Invalid strategy type | Use `ENTRY`, `TARGET`, or `STOPLOSS` |
| `UDAPI1136` | 400 | GTT order not found | Verify GTT `id` |
| `UDAPI1137` | 400 | GTT cannot be modified | Status is `TRIGGERED` or `CANCELLED` |
| `UDAPI1141` | 400 | Duplicate GTT order | Same instrument + direction exists |
| `UDAPI1143` | 400 | Invalid trigger price | Check ABOVE/BELOW vs current price relationship |
| `UDAPI1151` | 400 | GTT trigger already fired | Order already executed |

---

## AlgoChanakya Implementation Notes

- **Not yet implemented** in `upstox_order_adapter.py` (standard orders only as of Feb 2026)
- GTT orders require v3 endpoint (`/v3/order/gtt/`) — different base path from v2 orders
- Map all UDAPI112x–UDAPI115x codes to `BrokerAPIError`
- For OCO strategies, use `MULTIPLE` type with TARGET + STOPLOSS rules
