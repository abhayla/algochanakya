# Paytm Money GTT Orders Reference

> Source: Paytm Money API Docs (https://developer.paytmmoney.com/docs/) | Last verified: 2026-02-25
> **Warning:** Paytm Money API is the least mature of all 6 brokers. GTT documentation is limited. Test thoroughly before production use.

## Overview

Paytm Money provides GTT (Good Till Triggered) order functionality. The API is available but documentation is sparse. Test all GTT operations thoroughly.

## Known GTT Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/create-gtt` | Create GTT order |
| GET | `/api/get-gtt` | Get GTT orders |
| PUT | `/api/modify-gtt` | Modify GTT |
| DELETE | `/api/delete-gtt` | Cancel GTT |

**Note:** These endpoints may not be fully documented. Paytm Money has a history of breaking changes without notice.

## Authentication

Use `access_token` (NOT `read_access_token`) for GTT operations:

```
x-jwt-token: {access_token}
```

## Create GTT (Tentative)

**POST** `/api/create-gtt`

```json
{
  "security_id": "2885",
  "exchange": "NSE",
  "transaction_type": "B",
  "order_type": "RL",
  "quantity": 5,
  "price": 2505.0,
  "trigger_price": 2500.0,
  "product": "D",
  "gtt_validity_days": 365
}
```

## GTT Types

| Type | Description |
|------|-------------|
| Single | One trigger price condition |
| Two-leg | Target + Stop-loss OCO |

## Validity

GTT orders are valid for up to **365 days**.

## AlgoChanakya Integration

- GTT is **NOT implemented** in AlgoChanakya's Paytm adapter
- Standard orders supported in `backend/app/services/brokers/paytm_order_adapter.py`
- **Caution:** Given Paytm's API maturity level, implement with extra error handling and testing

## Common Issues

| Issue | Workaround |
|-------|------------|
| Endpoint not in official docs | Use pyPMClient SDK method if available |
| Breaking changes | Pin SDK version, test after Paytm API updates |
| Token confusion | GTT requires `access_token`, not `read_access_token` |
