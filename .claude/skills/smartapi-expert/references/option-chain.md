# SmartAPI Option Chain Reference

> Source: SmartAPI (Angel One) Official Docs | Last verified: 2026-02-25

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

## Price Source Clarification

The option chain REST API returns **RUPEES** for all price fields. This is different from:

| Source | Price Unit |
|--------|-----------|
| Option Chain REST API | **RUPEES** |
| WebSocket V2 (market data) | PAISE (divide by 100) |
| Historical data REST | PAISE (divide by 100) |
| Standard quote REST | RUPEES |
