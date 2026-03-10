# Upstox Option Chain API

> Source: [Upstox API Docs](https://upstox.com/developer/api-documentation/open-api) | Last verified: 2026-02-25

Complete reference for Upstox Option Chain API — includes real-time market data and Greeks for all strikes.

---

## Overview

| Property | Value |
|----------|-------|
| API Version | v2 |
| Endpoints | 2 (option/contract + option/chain) |
| Greeks | delta, gamma, theta, vega, IV, PoP |
| MCX | Not available |
| Real-time | Yes (snapshot at request time) |

---

## Endpoint 1: Get Option Contracts

Returns available option contracts for a given underlying + expiry date.

```
GET /v2/option/contract
  ?instrument_key=NSE_INDEX|Nifty 50
  &expiry_date=2025-03-27
Authorization: Bearer {access_token}
```

### Request Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `instrument_key` | Yes | string | Underlying instrument key (index or equity) |
| `expiry_date` | Yes | string | ISO format: `YYYY-MM-DD` |

### Response

```json
{
  "status": "success",
  "data": [
    {
      "instrument_key": "NSE_FO|56789",
      "trading_symbol": "NIFTY2532725000CE",
      "exchange": "NSE",
      "name": "NIFTY",
      "expiry": "2025-03-27",
      "strike_price": 25000,
      "option_type": "CE",
      "lot_size": 75,
      "tick_size": 0.05,
      "weekly": false,
      "minimum_lot": 1
    },
    {
      "instrument_key": "NSE_FO|56790",
      "trading_symbol": "NIFTY2532725000PE",
      "exchange": "NSE",
      "name": "NIFTY",
      "expiry": "2025-03-27",
      "strike_price": 25000,
      "option_type": "PE",
      "lot_size": 75,
      "tick_size": 0.05,
      "weekly": false,
      "minimum_lot": 1
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `instrument_key` | string | Upstox key for this option contract |
| `trading_symbol` | string | Readable symbol |
| `expiry` | string | Expiry date (YYYY-MM-DD) |
| `strike_price` | float | Strike price in RUPEES |
| `option_type` | string | `CE` or `PE` |
| `lot_size` | int | Contract lot size |
| `tick_size` | float | Minimum price movement |
| `weekly` | boolean | `true` for weekly expiry |

---

## Endpoint 2: Get Put/Call Option Chain

Returns full option chain with real-time market data AND Greeks for all strikes.

```
GET /v2/option/chain
  ?instrument_key=NSE_INDEX|Nifty 50
  &expiry_date=2025-03-27
Authorization: Bearer {access_token}
```

### Request Parameters

Same as Get Option Contracts: `instrument_key` + `expiry_date`.

### Response

```json
{
  "status": "success",
  "data": [
    {
      "strike_price": 25000,
      "underlying_key": "NSE_INDEX|Nifty 50",
      "underlying_spot_price": 25150.75,
      "call_options": {
        "instrument_key": "NSE_FO|56789",
        "trading_symbol": "NIFTY2532725000CE",
        "bid_ask_spread": 0.3,
        "market_data": {
          "ltp": 150.25,
          "volume": 125000,
          "oi": 500000,
          "prev_oi": 480000,
          "oi_day_high": 520000,
          "oi_day_low": 460000,
          "net_change": 2.5,
          "bid_price": 150.1,
          "ask_price": 150.4,
          "bid_qty": 75,
          "ask_qty": 150,
          "ohlc": {
            "open": 145.0,
            "high": 155.5,
            "low": 142.0,
            "close": 148.75
          }
        },
        "option_greeks": {
          "delta": 0.45,
          "gamma": 0.002,
          "theta": -12.5,
          "vega": 8.3,
          "iv": 18.5,
          "pop": 45.0,
          "rho": 0.05,
          "vanna": 0.001,
          "charm": -0.002
        }
      },
      "put_options": {
        "instrument_key": "NSE_FO|56790",
        "trading_symbol": "NIFTY2532725000PE",
        "bid_ask_spread": 0.25,
        "market_data": {
          "ltp": 148.75,
          "volume": 98000,
          "oi": 450000,
          "prev_oi": 430000,
          "bid_price": 148.6,
          "ask_price": 148.9,
          "bid_qty": 75,
          "ask_qty": 225
        },
        "option_greeks": {
          "delta": -0.55,
          "gamma": 0.002,
          "theta": -11.8,
          "vega": 8.1,
          "iv": 17.9,
          "pop": 55.0
        }
      }
    }
  ]
}
```

### Market Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `ltp` | float | Last traded price (RUPEES) |
| `volume` | int | Volume for the day |
| `oi` | int | Current open interest |
| `prev_oi` | int | Previous day's OI |
| `bid_price` / `ask_price` | float | Best bid/ask |
| `bid_qty` / `ask_qty` | int | Bid/ask quantities |
| `net_change` | float | Change from prev close |

### Option Greeks Fields

| Field | Type | Description |
|-------|------|-------------|
| `delta` | float | Rate of change of option price vs underlying |
| `gamma` | float | Rate of change of delta |
| `theta` | float | Time decay (RUPEES/day) |
| `vega` | float | Sensitivity to implied volatility |
| `iv` | float | Implied Volatility (percentage) |
| `pop` | float | Probability of Profit (percentage) |
| `rho` | float | Sensitivity to interest rate |
| `vanna` | float | Rate of change of delta vs IV |
| `charm` | float | Rate of change of delta vs time |

---

## Error Codes

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100011` | 400 | Invalid expiry date | Use ISO format `YYYY-MM-DD` |
| `UDAPI1088` | 400 | Option Chain not available | MCX instruments not supported; use NSE/BSE |

---

## AlgoChanakya Integration Notes

- Option chain data fetches use the `upstox_adapter.py` market data adapter
- Greeks from this API complement the real-time Greeks from WebSocket (`option_greeks` mode)
- `PoP` (Probability of Profit) is unique to Upstox — not available from other brokers' APIs
- Use `prev_oi` vs `oi` to detect OI buildup/unwinding in strategy logic
- MCX instruments do NOT support option chain — guard against MCX instrument keys

## AlgoChanakya Token Resolution (Internal)

### Upstox instrument_key Format

Upstox uses a composite `instrument_key` format: `NSE_FO|{numeric_token}` (e.g., `NSE_FO|56789`). This is **NOT** the symbol name — it's a numeric token with an exchange prefix. Do NOT pass Kite tokens to Upstox APIs.

### broker_instrument_tokens Table

When Upstox is integrated as a data source, `broker_instrument_tokens` must be populated with:

| Column | Value |
|--------|-------|
| `canonical_symbol` | Kite-format symbol (e.g., `NIFTY25FEB22000CE`) |
| `broker` | `upstox` |
| `broker_token` | Upstox instrument key (e.g., `NSE_FO|56789`) |
| `broker_symbol` | Same as `broker_token` for Upstox |

### Current Status

Upstox ticker adapter is implemented as a stub in `backend/app/services/brokers/market_data/ticker/adapters/upstox.py` (raises `NotImplementedError`). Token map loading for Upstox WebSocket subscriptions is deferred until the adapter is fully implemented.

### Future: Native Option Chain Integration

Use `/v2/option/chain` instead of assembling from quotes — it returns full Greeks + PoP natively, includes bid/ask depth, and is the richest option chain API among all 6 brokers. The native endpoint eliminates the need for in-house Black-Scholes Greeks calculation.
