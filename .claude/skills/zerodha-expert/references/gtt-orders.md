# Kite Connect GTT Orders Reference

> Source: Kite Connect v3 Official Docs | Last verified: 2026-02-25

## Overview

Kite Connect GTT (Good Till Triggered) allows placing orders that execute when a price condition is met. GTTs persist for up to 1 year and automatically cancel if triggered.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/gtt/triggers` | Create GTT trigger |
| GET | `/gtt/triggers` | List all GTT triggers |
| GET | `/gtt/triggers/{trigger_id}` | Get specific GTT |
| PUT | `/gtt/triggers/{trigger_id}` | Modify GTT |
| DELETE | `/gtt/triggers/{trigger_id}` | Delete GTT |

## GTT Types

| Type | Code | Rules | Description |
|------|------|-------|-------------|
| Single | `single` | 1 | Fires when price crosses one trigger |
| Two-Leg OCO | `two-leg` | 2 | One fires, the other cancels |

## Create GTT Request

POST /gtt/triggers

```json
{
  "type": "single",
  "tradingsymbol": "RELIANCE",
  "exchange": "NSE",
  "trigger_values": [2500.0],
  "last_price": 2480.0,
  "orders": [
    {
      "transaction_type": "BUY",
      "quantity": 5,
      "product": "CNC",
      "order_type": "LIMIT",
      "price": 2505.0
    }
  ]
}
```

## Two-Leg (OCO) GTT

```json
{
  "type": "two-leg",
  "tradingsymbol": "RELIANCE",
  "exchange": "NSE",
  "trigger_values": [2600.0, 2400.0],
  "last_price": 2500.0,
  "orders": [
    {
      "transaction_type": "SELL",
      "quantity": 5,
      "product": "CNC",
      "order_type": "LIMIT",
      "price": 2595.0
    },
    {
      "transaction_type": "SELL",
      "quantity": 5,
      "product": "CNC",
      "order_type": "LIMIT",
      "price": 2395.0
    }
  ]
}
```

## GTT Status Values

| Status | Description |
|--------|-------------|
| `active` | Waiting for trigger |
| `triggered` | Trigger fired, order placed |
| `disabled` | Manually disabled |
| `expired` | Past 1-year validity |
| `cancelled` | Manually cancelled |
| `rejected` | Order placement failed after trigger |
| `deleted` | Deleted by user |

## Key Rules

- **Max validity:** 1 year from creation
- **Not for F&O:** GTT is primarily for equity (NSE/BSE)
- **Trigger value must be LTP ±range** for single trigger
- **Two-leg:** First trigger_value is target (above LTP), second is stop-loss (below LTP)
- **Products:** CNC (delivery), MIS (intraday) supported; F&O uses NRML

## AlgoChanakya Integration

- GTT is **NOT yet implemented** in AlgoChanakya's Kite adapter
- Standard orders supported in `backend/app/services/brokers/kite_adapter.py`
- Future: Add GTT support to order adapter

## Error Handling

| Exception | Cause | Fix |
|-----------|-------|-----|
| `InputException` | Invalid GTT params | Check type, trigger values, price ranges |
| `TokenException` | Expired access token | Re-authenticate |
| `GeneralException` | GTT creation failed | Check margin, product type compatibility |
