# Paytm Money Option Chain Reference

> Source: Paytm Money API Docs (https://developer.paytmmoney.com/docs/) | Last verified: 2026-02-25
> **Warning:** Paytm Money API maturity warning applies here. Test data accuracy.

## Overview

Paytm Money provides option chain data powered by **Heckyl Technologies** (an underlying data vendor). The data includes Greeks (delta, gamma, theta, vega, IV).

## Endpoint

**GET** `/data/v1/option/chain` (verify exact path against current Paytm docs)

### Request Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `security_id` | Yes | Underlying security_id (e.g., 13 for NIFTY) |
| `exchange` | Yes | NSE, BSE |
| `expiry_date` | Yes | Expiry date string |

### Authentication

Use `read_access_token`:
```
x-jwt-token: {read_access_token}
```

## Response Format (Approximate)

```json
{
  "status": "success",
  "data": {
    "underlying": {
      "security_id": "13",
      "symbol": "NIFTY",
      "ltp": 22000.5
    },
    "option_chain": [
      {
        "strike_price": 22000.0,
        "CE": {
          "security_id": "45679",
          "symbol": "NIFTY25FEB22000CE",
          "ltp": 325.0,
          "volume": 32000,
          "oi": 980000,
          "iv": 17.8,
          "delta": 0.65,
          "gamma": 0.0025,
          "theta": -14.2,
          "vega": 9.1
        },
        "PE": {
          "security_id": "45678",
          "symbol": "NIFTY25FEB22000PE",
          "ltp": 122.5,
          "volume": 45000,
          "oi": 1250000,
          "iv": 18.5,
          "delta": -0.35,
          "gamma": 0.0025,
          "theta": -12.5,
          "vega": 8.75
        }
      }
    ]
  }
}
```

## Greeks (via Heckyl)

Paytm Money uses **Heckyl Technologies** as its underlying data vendor for Greeks calculation.

| Field | Description |
|-------|-------------|
| `delta` | Delta |
| `gamma` | Gamma |
| `theta` | Theta |
| `vega` | Vega |
| `iv` | Implied Volatility (%) |

**Note:** Greeks accuracy may vary compared to more established brokers. Heckyl's calculations are the same source used by several Indian brokers.

## Supported Underlyings

| Underlying | security_id | Exchange |
|-----------|-------------|----------|
| NIFTY 50 | `13` | NSE |
| NIFTY BANK | `25` | NSE |
| SENSEX | `51` | BSE |

## BSE F&O (Added 2025)

Paytm Money added BSE F&O instruments in 2025. BSE option chain should also be available for SENSEX and BANKEX.

## AlgoChanakya Integration

- Paytm Option Chain API is **NOT currently used** in AlgoChanakya
- AlgoChanakya uses SmartAPI for option chain data
- Given Paytm API maturity concerns, use as tertiary fallback only

## AlgoChanakya Token Resolution (Internal)

### Paytm Security IDs vs Kite Tokens

Paytm uses numeric `security_id` values (e.g., `45679`). These are **different** from Kite instrument tokens. Do NOT pass Kite tokens to Paytm APIs.

### broker_instrument_tokens Table

When Paytm is integrated as a data source, `broker_instrument_tokens` must be populated with:

| Column | Value |
|--------|-------|
| `canonical_symbol` | Kite-format symbol (e.g., `NIFTY25FEB22000CE`) |
| `broker` | `paytm` |
| `broker_token` | Paytm security_id (int, e.g., `45679`) |
| `broker_symbol` | Paytm symbol string (e.g., `NIFTY25FEB22000CE`) |

### Current Status

Paytm ticker adapter is implemented as a stub in `backend/app/services/brokers/market_data/ticker/adapters/paytm.py` (raises `NotImplementedError`). Token map loading for Paytm is deferred until the adapter is fully implemented.

### Price Units for Paytm

Unlike the REST option chain endpoint (which returns prices in **rupees**), some Paytm WebSocket/streaming endpoints may return prices in **paisa** (×100). Always check the price unit documentation for the specific endpoint being used. See `common-gotchas.md` Section 5 for the price unit table.

## Important Caution

Paytm Money API has a history of:
- Undocumented breaking changes to response formats
- Endpoint path changes without prior notice
- Incomplete documentation

**Verify endpoint paths** against current official docs before implementation.
