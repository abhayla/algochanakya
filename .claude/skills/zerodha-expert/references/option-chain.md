# Kite Connect Option Chain Reference

> Source: Kite Connect v3 Official Docs | Last verified: 2026-02-25

## Overview

Kite Connect does **NOT** have a dedicated Option Chain API endpoint. To build an option chain, you must query individual strike quotes using the `/quote` endpoint.

## Approach: Build Option Chain from Quote API

```python
# Step 1: Get all option instruments for NIFTY
instruments = kite.instruments("NFO")
nifty_options = [
    inst for inst in instruments
    if inst["name"] == "NIFTY"
    and inst["instrument_type"] in ["CE", "PE"]
    and inst["expiry"] == target_expiry
]

# Step 2: Get quotes for all strikes (batched)
# Max 500 instruments per request
tokens = [f"NFO:{inst['tradingsymbol']}" for inst in nifty_options]
batches = [tokens[i:i+500] for i in range(0, len(tokens), 500)]

option_chain = {}
for batch in batches:
    quotes = kite.quote(batch)
    option_chain.update(quotes)
```

## Quote Response (per instrument)

```json
{
  "NFO:NIFTY25FEB22000CE": {
    "instrument_token": 12345678,
    "tradingsymbol": "NIFTY25FEB22000CE",
    "last_price": 325.0,
    "volume": 32000,
    "buy_quantity": 5000,
    "sell_quantity": 3500,
    "ohlc": {
      "open": 318.0,
      "high": 340.0,
      "low": 305.0,
      "close": 318.0
    },
    "net_change": 7.0,
    "oi": 980000,
    "oi_day_high": 1050000,
    "oi_day_low": 850000
  }
}
```

## Available Fields (from /quote)

| Field | Description | Notes |
|-------|-------------|-------|
| `last_price` | LTP | Rupees |
| `volume` | Today's volume | Contracts |
| `oi` | Open interest | Contracts |
| `ohlc` | OHLC data | Rupees |
| `net_change` | Change from previous close | Rupees |
| `oi_day_high` | Intraday OI high | - |
| `oi_day_low` | Intraday OI low | - |

## Greeks: NOT Available

Kite Connect's quote API does **not return Greeks** (delta, gamma, theta, vega, IV).

For Greeks, consider:
- Using SmartAPI's option chain endpoint (provides delta, gamma, theta, vega, IV)
- Calculating using Black-Scholes locally (less accurate, requires underlying price)
- Upstox Option Chain API (provides Greeks including PoP)

## AlgoChanakya Option Chain

- AlgoChanakya's `/optionchain` page uses SmartAPI as primary data source
- Kite is used for order execution (placing option orders), not option chain display
- The `GET /api/option-chain/data` backend endpoint uses SmartAPI adapter

## Performance Consideration

Building option chain from individual quotes is slow for large chains:
- NIFTY weekly expiry: ~300+ strikes
- Requires 1-2 API calls per batch (500 instruments max)
- Rate limit: 10 req/sec — manageable
- Use LTP endpoint (`/quote/ltp`) instead of full quote to reduce payload size
