# Dhan Option Chain Reference

> Source: Dhan API v2 Docs (https://dhanhq.co/docs/v2/) | Last verified: 2026-02-25

## Overview

Dhan provides a dedicated Option Chain API with market data and Greeks for index options.

## Rate Limit

**1 unique request every 3 seconds** per distinct underlying instrument. OI data updates slower than LTP — this conservative throttling is intentional.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/optionchain` | Get full option chain with Greeks |
| GET | `/v2/expirylist` | Get available expiry dates |

## Get Expiry List

**GET** `/v2/expirylist?UnderlyingScrip={security_id}&UnderlyingSeg={segment}`

```
GET /v2/expirylist?UnderlyingScrip=13&UnderlyingSeg=IDX_I
```

Response:
```json
{
  "status": "success",
  "data": ["2025-02-27", "2025-03-06", "2025-03-27", "2025-04-24"]
}
```

## Get Option Chain

**POST** `/v2/optionchain`

### Request Body
```json
{
  "UnderlyingScrip": 13,
  "UnderlyingSeg": "IDX_I",
  "Expiry": "2025-02-27"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `UnderlyingScrip` | int | Underlying security_id (e.g., 13=NIFTY) |
| `UnderlyingSeg` | string | Segment (IDX_I for indices) |
| `Expiry` | string | Expiry date YYYY-MM-DD |

### Response Format

```json
{
  "status": "success",
  "data": {
    "underlying": {
      "security_id": "13",
      "trading_symbol": "NIFTY",
      "last_price": 22000.5,
      "oi": 0,
      "volume": 0
    },
    "options_chain": [
      {
        "strike_price": 22000.0,
        "call_options": {
          "security_id": "45679",
          "trading_symbol": "NIFTY-FEB2025-22000-CE",
          "last_price": 325.0,
          "open": 318.0,
          "high": 340.0,
          "low": 305.0,
          "close": 318.0,
          "volume": 32000,
          "open_interest": 980000,
          "oi_change": 25000,
          "iv": 17.8,
          "delta": 0.65,
          "theta": -14.2,
          "gamma": 0.0025,
          "vega": 9.1
        },
        "put_options": {
          "security_id": "45678",
          "trading_symbol": "NIFTY-FEB2025-22000-PE",
          "last_price": 122.5,
          "open": 118.0,
          "high": 135.0,
          "low": 115.0,
          "close": 118.0,
          "volume": 45000,
          "open_interest": 1250000,
          "oi_change": -15000,
          "iv": 18.5,
          "delta": -0.35,
          "theta": -12.5,
          "gamma": 0.0025,
          "vega": 8.75
        }
      }
    ]
  }
}
```

## Market Data Fields

| Field | Description | Unit |
|-------|-------------|------|
| `last_price` | LTP | Rupees |
| `volume` | Today's volume | Contracts |
| `open_interest` | Open interest | Contracts |
| `oi_change` | OI change from previous | Contracts |
| `iv` | Implied Volatility | % |

## Greeks Fields

| Field | Description | Notes |
|-------|-------------|-------|
| `delta` | Delta | 0 to ±1 |
| `gamma` | Gamma | Always positive |
| `theta` | Theta (daily decay) | Always negative |
| `vega` | Vega (IV sensitivity) | Always positive |

## Supported Underlyings

| Underlying | security_id | Segment |
|-----------|-------------|---------|
| NIFTY 50 | `13` | `IDX_I` |
| NIFTY BANK | `25` | `IDX_I` |
| FINNIFTY | varies | `IDX_I` |
| SENSEX | `51` | `IDX_I` |
| BANKEX | varies | `IDX_I` |

## AlgoChanakya Integration

- Dhan Option Chain API is **NOT yet integrated** into AlgoChanakya
- AlgoChanakya uses SmartAPI for option chain data (platform default)
- Future: Could use Dhan as fallback option chain source

## AlgoChanakya Token Resolution (Internal)

### Dhan Security IDs vs Kite Tokens

Dhan uses numeric `security_id` values (e.g., `45679`) for instrument identification. These are **different** from Kite instrument tokens (e.g., `11612162`). Do NOT pass Kite tokens to the Dhan API.

### broker_instrument_tokens Table

When Dhan is eventually integrated as a data source, the `broker_instrument_tokens` table must be populated with:

| Column | Value |
|--------|-------|
| `canonical_symbol` | Kite-format symbol (e.g., `NIFTY25FEB22000CE`) |
| `broker` | `dhan` |
| `broker_token` | Dhan security_id (int, e.g., `45679`) |
| `broker_symbol` | Dhan trading symbol (e.g., `NIFTY-FEB2025-22000-CE`) |

### Current Status

Dhan ticker adapter is implemented as a stub in `backend/app/services/brokers/market_data/ticker/adapters/dhan.py` (raises `NotImplementedError`). Token map loading for Dhan WebSocket subscriptions is deferred until the adapter is fully implemented.

### Future: Native Option Chain Integration

Use `/v2/optionchain` instead of assembling from individual quotes — it returns Greeks natively (no separate calculation needed), includes OI change, and requires only 1 req/3sec per underlying vs many individual quote calls.
