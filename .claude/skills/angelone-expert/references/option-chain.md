# SmartAPI Option Chain Reference

> Source: SmartAPI (Angel One) Official Docs + Community Research | Last verified: 2026-03-12

## Overview

SmartAPI provides an Option Chain API that returns all strikes for a given index with market data including Greeks. Prices are returned in **RUPEES** (unlike the WebSocket which returns PAISE).

## Endpoint

**GET** `/rest/secure/angelbroking/marketData/v1/optionChain`

**Base URL:** `https://apiconnect.angelbroking.com`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Underlying name (e.g., "NIFTY", "BANKNIFTY") |
| `expirydate` | string | Yes | Expiry date in DDMMMYYYY format (e.g., "27FEB2025") |

### Example Request

```
GET https://apiconnect.angelbroking.com/rest/secure/angelbroking/marketData/v1/optionChain?name=NIFTY&expirydate=27FEB2025
```

### Request Headers

```
Authorization: Bearer {jwtToken}
X-UserType: USER
X-SourceID: WEB
X-ClientLocalIP: {ip}
X-ClientPublicIP: {ip}
X-MACAddress: {mac}
X-PrivateKey: {api_key}
```

## Response Format

```json
{
  "status": true,
  "message": "SUCCESS",
  "errorcode": "",
  "data": {
    "fetched": [
      {
        "strikePrice": "22000",
        "expiryDate": "27FEB2025",
        "PE": {
          "token": "45678",
          "symbol": "NIFTY25FEB22000PE",
          "name": "NIFTY",
          "expiry": "27FEB2025",
          "lotSize": "25",
          "strikePrice": "22000.00",
          "tick_size": "0.05",
          "open": "120.00",
          "high": "135.00",
          "low": "115.00",
          "close": "118.00",
          "ltp": "122.50",
          "volume": "45000",
          "oi": "1250000",
          "impliedVolatility": "18.5",
          "delta": "-0.35",
          "gamma": "0.0025",
          "theta": "-12.50",
          "vega": "8.75"
        },
        "CE": {
          "token": "45679",
          "symbol": "NIFTY25FEB22000CE",
          "name": "NIFTY",
          "expiry": "27FEB2025",
          "lotSize": "25",
          "strikePrice": "22000.00",
          "tick_size": "0.05",
          "open": "320.00",
          "high": "340.00",
          "low": "305.00",
          "close": "318.00",
          "ltp": "325.00",
          "volume": "32000",
          "oi": "980000",
          "impliedVolatility": "17.8",
          "delta": "0.65",
          "gamma": "0.0025",
          "theta": "-14.20",
          "vega": "9.10"
        }
      }
    ]
  }
}
```

## Market Data Fields

| Field | Description | Unit | Notes |
|-------|-------------|------|-------|
| `ltp` | Last traded price | Rupees | **RUPEES** (not paise) |
| `open` | Today's open price | Rupees | |
| `high` | Today's high price | Rupees | |
| `low` | Today's low price | Rupees | |
| `close` | Previous close price | Rupees | |
| `volume` | Today's volume | Number of contracts | |
| `oi` | Open interest | Number of contracts | |
| `impliedVolatility` | IV percentage | % | e.g., "18.5" = 18.5% IV |
| `lotSize` | Contract lot size | Shares/units per contract | |
| `tick_size` | Minimum price movement | Rupees | e.g., "0.05" |

## Greeks Fields

| Field | Description | Range | Notes |
|-------|-------------|-------|-------|
| `delta` | Rate of option price change per ₹1 underlying move | -1 to +1 | CE: 0 to 1, PE: -1 to 0 |
| `gamma` | Rate of delta change per ₹1 underlying move | 0 to +∞ | Always positive |
| `theta` | Time decay per day (rupees lost per day) | Negative | Always negative for long options |
| `vega` | Sensitivity to 1% IV change | Positive | Always positive for long options |

**Note:** Greeks accuracy may vary. SmartAPI calculates these server-side. For critical trading decisions, consider calculating Greeks independently using a library like `mibian` or `py_vollib`.

## Supported Underlyings

| Name | Exchange | Segment | Notes |
|------|----------|---------|-------|
| `NIFTY` | NSE | NFO | NIFTY 50 index options |
| `BANKNIFTY` | NSE | NFO | Bank NIFTY index options |
| `FINNIFTY` | NSE | NFO | Financial NIFTY index options |
| `SENSEX` | BSE | BFO | BSE SENSEX options |
| `MIDCPNIFTY` | NSE | NFO | Midcap NIFTY 50 options |

## Expiry Date Format

The `expirydate` parameter uses `DDMMMYYYY` format (4-digit year):

| Expiry | Format | Example |
|--------|--------|---------|
| Weekly | `DDMMMYYYY` | `27FEB2025` |
| Monthly | `DDMMMYYYY` | `27MAR2025` |

**Note:** Unlike the instrument master (which uses 4-digit year in `expiry` field) and SmartAPI symbols (2-digit year), the option chain API always uses 4-digit year.

## Getting Available Expiry Dates

The option chain API requires a specific expiry date. To get available expiries:

1. Download the instrument master JSON
2. Filter by `name == "NIFTY"` and `instrumenttype == "OPTIDX"`
3. Extract unique `expiry` field values (already in DDMMMYYYY format)

```python
import requests

# Download instrument master (cached 12h)
master = requests.get(
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
).json()

# Get NIFTY expiries
nifty_expiries = sorted(set(
    item["expiry"]
    for item in master
    if item["name"] == "NIFTY" and item["instrumenttype"] == "OPTIDX"
))
# → ["27FEB2025", "06MAR2025", "27MAR2025", ...]
```

## AlgoChanakya Integration Notes

- Option Chain is used in the frontend `/optionchain` page
- Backend endpoint: `GET /api/option-chain/data` calls SmartAPI under the hood as platform default
- Market data for option chain is sourced via SmartAPI (platform default) — no user auth needed for display
- REST prices from this endpoint are in **RUPEES** (unlike WebSocket ticks which are PAISE)
- Rate limit: 1 req/sec (shared with all REST endpoints) — use caching for high-frequency refresh

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Empty `fetched` array | Wrong underlying name or expiry date | Verify `name` is uppercase and `expirydate` uses 4-digit year |
| No data for expiry | Expiry not yet listed or already expired | Fetch available expiries from instrument master |
| `AB8050` Data Not Found | Invalid underlying or date | Check supported underlyings list above |
| Rate limit hit | 1 req/sec limit exceeded | Use a caching layer; do not poll faster than 1/sec |
| Data delay during peak | REST is not real-time | LTP from this API may lag by ~15 sec; use WebSocket for live LTP |

---

## ⚠️ CRITICAL: Why LTP Returns 0 for Many Strikes (Community Research 2026-03-12)

This section documents confirmed findings from the SmartAPI community forum and GitHub.

### Root Cause: No Trades = No Data from REST API

SmartAPI's REST `marketData` and `get_quote` endpoints **only return data when a trade has occurred** on that strike during the current session. For strikes with zero activity (deep OTM, deep ITM, low-liquidity), the API returns `ltp: 0`. This is confirmed by SmartAPI moderators.

**Official moderator statement (forum topic 4518):**
> "We provide Option Chain data in the Websocket. You can look for the specific tokens on the Scrip Master Json file and subscribe the requisite tokens in Websocket Streaming. In the full mode in websocket, you get the option chain data."

### Other Confirmed Causes of Zero LTP

| Cause | Description | Fix |
|-------|-------------|-----|
| No trades on strike today | Strike is illiquid/inactive — no exchange tick pushed | Use WebSocket Snap Quote (Mode 3) instead |
| Wrong token series | Using BL series tokens (not active in NSE) | Use `EQ` or `OPTIDX`/`OPTSTK` series from scrip master |
| `marketData` single-token limit | REST API officially supports 1 token per request | Pass arrays but officially unsupported; use WebSocket |
| ~500 request rate cap | REST stops responding after ~500 calls in a session | Re-authenticate or use WebSocket |
| Non-trading day | Blank responses on weekends/holidays | Check trading calendar before calls |

### The Correct Approach: WebSocket V2 Snap Quote (Mode 3)

For reliable option chain LTP data, **use WebSocket V2 with Snap Quote mode** instead of REST batch calls:

```python
# Step 1: Get tokens from scrip master
import requests
master = requests.get(
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
).json()
token_list = [
    item["token"] for item in master
    if item["name"] == "NIFTY"
    and item["instrumenttype"] == "OPTIDX"
    and item["expiry"] == "17MAR2026"  # DDMMMYYYY
]

# Step 2: Subscribe via WebSocket V2, mode=3 (Snap Quote)
# exchangeType=2 for NFO
TOKENS_AND_PROPERTIES = [{"exchangeType": 2, "tokens": token_list}]
sws.subscribe("oc_snap", mode=3, token_list=TOKENS_AND_PROPERTIES)
# Collect ticks until all tokens respond or timeout
```

**Reference implementation:** [markov404/AngelOneOptionChainSmartApi](https://github.com/markov404/AngelOneOptionChainSmartApi) — opens WebSocket, subscribes all option tokens at once with Snap Quote mode, collects until all respond (or 3-min cycle).

### WebSocket Limits for Option Chain Use

| Limit | Value |
|-------|-------|
| Max tokens per connection | **3000** |
| Max connections per client | **3** |
| Subscription counting | LTP + Quote + Snap = 3 separate subscriptions per token |
| Mode for option chain | **Mode 3 (Snap Quote)** — includes OI, depth, OHLC |

### AlgoChanakya Current Approach vs Recommended

| Approach | Speed | Completeness | Notes |
|----------|-------|--------------|-------|
| **Current**: `adapter.get_quote()` REST batches | ~12-37s | Partial (only active strikes) | After perf fix: ~12s, but 0 LTP for inactive strikes |
| **Recommended**: WebSocket Snap Quote (Mode 3) | ~2-5s | Full (all strikes) | Subscribe all tokens, collect ticks until complete |
| **Alternative**: Dedicated `/optionChain` endpoint | ~3-5s | Full (with Greeks) | Includes IV, Greeks server-side — try this first |

### Action Item: Try `/optionChain` Endpoint First

AlgoChanakya currently uses `adapter.get_quote()` for individual tokens. The **dedicated `/optionChain` endpoint** documented above returns all strikes in one call including live LTP, OI, and Greeks. This should be tested as a replacement for the token-by-token REST approach:

```python
# Test this endpoint first before switching to WebSocket:
GET /rest/secure/angelbroking/marketData/v1/optionChain?name=NIFTY&expirydate=17MAR2026
# If this returns non-zero LTP for all strikes → use this
# If it also returns 0 for illiquid strikes → switch to WebSocket Snap Quote
```

## Price Source Clarification

The option chain REST API returns **RUPEES** for all price fields. This is different from:

| Source | Price Unit |
|--------|-----------|
| Option Chain REST API | **RUPEES** |
| WebSocket V2 (market data) | PAISE (divide by 100) |
| Historical data REST | PAISE (divide by 100) |
| Standard quote REST | RUPEES |

## AlgoChanakya Token Resolution (Internal)

### The Paise/Rupees Trap for NFO Quote REST API

The `SmartAPIMarketDataAdapter.get_quote()` calls `SmartAPIMarketData.get_quote(exchange="NFO", tokens=[...], mode="FULL")`. This REST API returns prices **in PAISE** — the adapter's `_convert_to_unified_quote()` divides by 100. This is different from the dedicated Option Chain endpoint above (which returns rupees).

**CRITICAL**: Do NOT bypass `adapter.get_quote()` with `adapter._market_data.get_quote()` directly — you will get raw paise values without conversion.

### broker_instrument_tokens Table

The `broker_instrument_tokens` table maps canonical symbols (kite format) to SmartAPI tokens. Without rows in this table, `TokenManager.get_token()` returns None and `get_quote()` returns empty results → all LTPs = 0.

**Symptom**: Option chain loads correctly (spot price shows) but all strike LTPs are 0.

**Fix**: At startup, `InstrumentMasterService.populate_broker_token_mappings()` in `backend/app/services/instrument_master.py` is called to populate this table using `SmartAPIInstruments.lookup_token()`.

### lookup_token Fallback

`SmartAPIMarketDataAdapter.get_quote()` uses `TokenManager.get_token()` first. If that returns None, it falls back to `SmartAPIInstruments.lookup_token(symbol, "NFO")` directly. This multi-tier lookup handles the case where `broker_instrument_tokens` is empty or has missing rows.

**Source**: `backend/app/services/brokers/market_data/smartapi_adapter.py` lines ~139-155

### Token Format

SmartAPI tokens are string integers (e.g., `"37806"`). Kite tokens are also integers but different values (e.g., `11612162`). Do NOT pass Kite tokens to the SmartAPI REST quote API — it won't recognize them and returns empty results.

Near-term weekly expiries often only have Kite tokens in the instruments table. The `lookup_token()` fallback resolves the correct SmartAPI token by parsing the canonical symbol and matching via underlying+expiry+strike+option_type.
