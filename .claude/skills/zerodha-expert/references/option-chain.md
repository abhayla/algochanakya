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

## AlgoChanakya Token Resolution (Internal)

### Identity Token Mapping

Kite uses integer instrument tokens (e.g., `11612162`) for WebSocket subscriptions. These tokens also serve as the canonical format internally — no separate `broker_instrument_tokens` lookup is needed for Kite's own data endpoints.

However, Kite tokens **cannot** be passed to other brokers' APIs (e.g., SmartAPI REST quote API). Kite tokens from the `instruments` table have `source_broker='kite'` and are **only valid for Kite WebSocket and Kite quote REST**.

### Token Flow for Option Chain

Since AlgoChanakya uses SmartAPI as the platform default for option chain data (not Kite), the Kite instrument tokens must be cross-referenced to SmartAPI tokens at startup:

1. `InstrumentMasterService.populate_broker_token_mappings()` runs at startup
2. It queries all NFO options from `instruments` table (`source_broker='kite'`)
3. For each canonical symbol, it calls `SmartAPIInstruments.lookup_token(symbol, "NFO")`
4. The resolved SmartAPI token is stored in `broker_instrument_tokens` (broker=`smartapi`)
5. `SmartAPIMarketDataAdapter.get_quote()` then uses these tokens for REST quote calls

**Symptom of empty `broker_instrument_tokens`:** All option strike LTPs = 0 while spot price shows correctly.

**Source:** `backend/app/services/instrument_master.py` — `populate_broker_token_mappings()`
