# Fyers Option Chain Reference

> Source: Fyers API v3 Docs (https://myapi.fyers.in/docs/) | Last verified: 2026-02-25

## Overview

Fyers v3 provides an Option Chain API with market data and Greeks.

## Endpoint

**GET** `/api/v3/optionchain`

### Request Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `symbol` | Yes | Underlying Fyers symbol (e.g., `NSE:NIFTY50-INDEX`) |
| `strikecount` | No | Number of strikes on each side (default: all) |
| `timestamp` | No | Data timestamp |

### Request Example

```python
from fyers_apiv3 import fyersModel

fyers = fyersModel.FyersModel(
    client_id=app_id,
    token=f"{app_id}:{access_token}"
)

data = {
    "symbol": "NSE:NIFTY50-INDEX",
    "strikecount": 10,
    "timestamp": ""
}
response = fyers.optionchain(data=data)
```

## Response Format

```json
{
  "s": "ok",
  "code": 200,
  "data": {
    "expiryData": [
      {
        "expiry": "2025-02-27",
        "optionsChain": [
          {
            "strike_price": 22000.0,
            "call_options": {
              "symbol": "NSE:NIFTY25FEB22000CE",
              "id": "23000",
              "ltp": 325.0,
              "open_price": 318.0,
              "high_price": 340.0,
              "low_price": 305.0,
              "prev_close_price": 318.0,
              "volume": 32000,
              "oi": 980000,
              "prev_oi": 955000,
              "bid_price": 324.5,
              "ask_price": 325.5,
              "iv": 17.8,
              "delta": 0.65,
              "theta": -14.2,
              "gamma": 0.0025,
              "vega": 9.1,
              "rho": 0.05,
              "vanna": 0.001,
              "charm": -0.0005
            },
            "put_options": {
              "symbol": "NSE:NIFTY25FEB22000PE",
              "id": "23001",
              "ltp": 122.5,
              "open_price": 118.0,
              "high_price": 135.0,
              "low_price": 115.0,
              "prev_close_price": 118.0,
              "volume": 45000,
              "oi": 1250000,
              "prev_oi": 1265000,
              "bid_price": 122.0,
              "ask_price": 123.0,
              "iv": 18.5,
              "delta": -0.35,
              "theta": -12.5,
              "gamma": 0.0025,
              "vega": 8.75,
              "rho": -0.04,
              "vanna": -0.001,
              "charm": 0.0004
            }
          }
        ]
      }
    ]
  }
}
```

## Market Data Fields

| Field | Description | Unit |
|-------|-------------|------|
| `ltp` | Last traded price | Rupees |
| `volume` | Today's volume | Contracts |
| `oi` | Open interest | Contracts |
| `prev_oi` | Previous day OI | Contracts |
| `bid_price` | Best bid | Rupees |
| `ask_price` | Best ask | Rupees |

## Greeks Fields

| Field | Description |
|-------|-------------|
| `iv` | Implied Volatility (%) |
| `delta` | Delta (0 to +/-1) |
| `theta` | Theta (daily time decay) |
| `gamma` | Gamma |
| `vega` | Vega |
| `rho` | Rho (interest rate sensitivity) |
| `vanna` | Vanna (dDelta/dIV) |
| `charm` | Charm (dDelta/dTime) |

## Supported Underlyings

| Fyers Symbol | Underlying | Notes |
|-------------|-----------|-------|
| `NSE:NIFTY50-INDEX` | NIFTY 50 | |
| `NSE:NIFTYBANK-INDEX` | Bank NIFTY | |
| `NSE:FINNIFTY-INDEX` | Fin NIFTY | |
| `BSE:SENSEX-INDEX` | SENSEX | BSE options |
| `BSE:BANKEX-INDEX` | BANKEX | BSE options |

## MCX Limitation

MCX (commodity) option chains are **NOT supported** by this API.

## AlgoChanakya Integration

- Fyers Option Chain API is **NOT currently used** in AlgoChanakya
- AlgoChanakya uses SmartAPI as primary option chain source
- Fyers option chain could serve as a secondary/fallback source
