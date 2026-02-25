# Upstox Endpoints Catalog

> Source: [Upstox API Docs](https://upstox.com/developer/api-documentation/open-api) | Last verified: 2026-02-25

Complete REST API endpoint reference for Upstox API v2 and v3.

**Base URL v2:** `https://api.upstox.com/v2`
**Base URL v3:** `https://api.upstox.com/v3` (orders, historical, quotes, WebSocket)
**Auth Header:** `Authorization: Bearer {access_token}`

**Rate Limits:**
- General REST: **50 req/sec, 500/min, 2000/30min**
- Multi-Order APIs: **4 req/sec, 40/min, 160/30min**
- Order placement: **50 orders/second**

---

## Authentication

### Exchange Authorization Code
```
POST /v2/login/authorization/token
Content-Type: application/x-www-form-urlencoded
```
**Body:** `code={code}&client_id={api_key}&client_secret={secret}&redirect_uri={url}&grant_type=authorization_code`

**Response:**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ...",
    "extended_token": "eyJ...",
    "user_id": "AB1234",
    "user_name": "John Doe",
    "email": "john@example.com",
    "broker": "UPSTOX",
    "exchanges": ["NSE", "BSE", "NFO", "MCX"],
    "products": ["D", "I", "CO", "OC"],
    "is_active": true
  }
}
```

---

## User / Funds

### Get Profile
```
GET /v2/user/profile
```

### Get Funds and Margin
```
GET /v2/user/get-funds-and-margin
GET /v2/user/get-funds-and-margin?segment=SEC  # SEC or COM
```

**Response (Jul 2025 format — equity includes commodity):**
```json
{
  "data": {
    "commodity": null,
    "equity": {
      "used_margin": 150000.0,
      "payin_amount": 500000.0,
      "span_margin": 100000.0,
      "adhoc_margin": 0,
      "notional_cash": 0,
      "available_margin": 300000.0,
      "exposure_margin": 50000.0
    }
  }
}
```

> **Note (Jul 2025):** `equity` object now includes commodity data combined. Old code expecting separate `commodity` object will get `null`.

---

## Market Data (Quotes)

### Full Quote (v3 preferred)
```
GET /v3/market-quote/quotes?instrument_key=NSE_FO|12345,NSE_INDEX|Nifty 50
```

**Response:**
```json
{
  "data": {
    "NSE_FO|12345": {
      "ohlc": {"open": 145.0, "high": 155.5, "low": 142.0, "close": 148.75},
      "depth": {
        "buy": [{"quantity": 500, "price": 150.2, "orders": 3}],
        "sell": [{"quantity": 400, "price": 150.3, "orders": 2}]
      },
      "timestamp": "2025-02-27T14:30:00+05:30",
      "instrument_token": "NSE_FO|12345",
      "symbol": "NIFTY2522725000CE",
      "last_price": 150.25,
      "volume": 1250000,
      "average_price": 149.5,
      "oi": 500000,
      "net_change": 1.5,
      "total_buy_quantity": 250000,
      "total_sell_quantity": 300000,
      "lower_circuit_limit": 0.05,
      "upper_circuit_limit": 500.0
    }
  }
}
```

### LTP Only
```
GET /v2/market-quote/ltp?instrument_key=NSE_FO|12345
```

### OHLC
```
GET /v2/market-quote/ohlc?instrument_key=NSE_FO|12345&interval=1d
```

**Note:** All REST prices are in **RUPEES**.

---

## Historical Data

### Historical Candles (v3 — supports custom time units)
```
GET /v3/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}
```

**v3 Intervals:** `1minute`, `3minute`, `5minute`, `10minute`, `15minute`, `30minute`, `1hour`, `2hour`, `4hour`, `day`, `week`, `month`

**Example:** `GET /v3/historical-candle/NSE_FO|12345/day/2025-02-27/2025-01-01`

**Response:**
```json
{
  "data": {
    "candles": [
      ["2025-02-27T00:00:00+05:30", 145.0, 155.5, 142.0, 150.25, 1250000, 500000],
      ["2025-02-26T00:00:00+05:30", 148.0, 152.0, 144.5, 145.0, 1100000, 480000]
    ]
  }
}
```

**Format:** `[timestamp, open, high, low, close, volume, oi]`
**Note:** Candles are in **descending order** (newest first). Reverse before processing.

### Intraday Candles
```
GET /v2/historical-candle/intraday/{instrument_key}/{interval}
```

---

## Instruments

### Get Instruments (JSON — CSV deprecated Apr 2024)
```
GET /v2/market-quote/instruments?exchange=NSE
```

Returns JSON array. Key fields: `instrument_key`, `trading_symbol`, `name`, `lot_size`, `instrument_type`, `expiry`, `strike`, `option_type`, `weekly` (boolean).

---

## Orders

### Place Order v3 (preferred — includes order slicing + latency tracking)
```
POST /v3/order/place
Content-Type: application/json
```

**Body:**
```json
{
  "quantity": 25,
  "product": "D",
  "validity": "DAY",
  "price": 0,
  "tag": "autopilot",
  "instrument_token": "NSE_FO|12345",
  "order_type": "MARKET",
  "transaction_type": "BUY",
  "disclosed_quantity": 0,
  "trigger_price": 0,
  "is_amo": false,
  "slice": false
}
```

**Products:** `D` (Delivery/CNC), `I` (Intraday/MIS), `CO` (Cover Order), `OC` (OCO/Bracket), `MTF`
**Order Types:** `MARKET`, `LIMIT`, `SL`, `SL-M`

**Response:**
```json
{
  "status": "success",
  "data": {
    "order_id": "123456789012345",
    "request_time": "14:30:01",
    "order_rule_id": null
  }
}
```

### Modify Order v3
```
PUT /v3/order/modify
Content-Type: application/json
```
**Body:** `{"order_id": "...", "quantity": 25, "price": 150.5, "order_type": "LIMIT", ...}`

### Cancel Order v3
```
DELETE /v3/order/cancel?order_id={order_id}
```

### Get Orders
```
GET /v2/order/retrieve-all
GET /v2/order/history?order_id={order_id}
```

### Get Trades
```
GET /v2/order/trades/get-trades-for-day
```

---

## Multi-Order APIs (Rate limit: 4/sec, 40/min)

### Place Multiple Orders
```
POST /v2/order/multi/place
Content-Type: application/json
```
**Body:** `[{"quantity": 25, "instrument_token": "...", ...}, ...]`

### Cancel All Open Orders
```
DELETE /v2/order/multi/cancel
```

### Exit All Positions
```
POST /v2/order/multi/exit
```

---

## GTT Orders (Good Till Triggered — v3)

See [gtt-orders.md](./gtt-orders.md) for complete request/response schemas and examples.

### Place GTT Order
```
POST /v3/order/gtt/place
Content-Type: application/json
```

**Body (SINGLE type):**
```json
{
  "type": "SINGLE",
  "quantity": 25,
  "product": "D",
  "transaction_type": "BUY",
  "instrument_token": "NSE_FO|12345",
  "rules": [
    {
      "strategy_type": "ENTRY",
      "trigger_type": "ABOVE",
      "price": 150.0,
      "trigger_price": 151.0
    }
  ]
}
```

**Body (MULTIPLE/OCO type):**
```json
{
  "type": "MULTIPLE",
  "quantity": 25,
  "product": "D",
  "transaction_type": "SELL",
  "instrument_token": "NSE_FO|12345",
  "rules": [
    {"strategy_type": "TARGET", "trigger_type": "ABOVE", "price": 200.0, "trigger_price": 201.0},
    {"strategy_type": "STOPLOSS", "trigger_type": "BELOW", "price": 100.0, "trigger_price": 99.0}
  ]
}
```

### Modify GTT Order
```
PUT /v3/order/gtt/modify
```
**Body:** `{"id": "gtt_id", "rules": [...], "quantity": 25, ...}`

### Cancel GTT Order
```
DELETE /v3/order/gtt/cancel?id={gtt_id}
```

### Get GTT Orders
```
GET /v3/order/gtt/details
GET /v3/order/gtt/details?id={gtt_id}
```

**Response:**
```json
{
  "data": {
    "id": "gtt_abc123",
    "status": "ACTIVE",
    "type": "MULTIPLE",
    "instrument_token": "NSE_FO|12345",
    "quantity": 25,
    "product": "D",
    "transaction_type": "SELL",
    "created_on": "2025-02-27T10:00:00+05:30",
    "rules": [
      {"id": "rule_1", "strategy_type": "TARGET", "trigger_type": "ABOVE", "price": 200.0, "status": "PENDING"},
      {"id": "rule_2", "strategy_type": "STOPLOSS", "trigger_type": "BELOW", "price": 100.0, "status": "PENDING"}
    ]
  }
}
```

---

## Option Chain

### Get Option Contracts
```
GET /v2/option/contract?instrument_key=NSE_INDEX|Nifty 50&expiry_date=2025-03-27
```

**Response:**
```json
{
  "data": [
    {
      "instrument_key": "NSE_FO|56789",
      "trading_symbol": "NIFTY2532725000CE",
      "strike_price": 25000,
      "option_type": "CE",
      "expiry": "2025-03-27",
      "lot_size": 75,
      "weekly": false
    }
  ]
}
```

### Get Put/Call Option Chain
```
GET /v2/option/chain?instrument_key=NSE_INDEX|Nifty 50&expiry_date=2025-03-27
```

**Response:**
```json
{
  "data": [
    {
      "strike_price": 25000,
      "call_options": {
        "instrument_key": "NSE_FO|56789",
        "market_data": {
          "ltp": 150.25,
          "volume": 125000,
          "oi": 500000,
          "prev_oi": 480000,
          "bid_price": 150.1,
          "ask_price": 150.4,
          "bid_qty": 75,
          "ask_qty": 150
        },
        "option_greeks": {
          "delta": 0.45,
          "gamma": 0.002,
          "theta": -12.5,
          "vega": 8.3,
          "iv": 18.5,
          "pop": 45.0
        }
      },
      "put_options": { "..." : "same structure" }
    }
  ]
}
```

> **Note:** Option Chain not available for MCX instruments.

---

## Positions / Holdings

### Get Positions
```
GET /v2/portfolio/short-term-positions
```

### Get Holdings
```
GET /v2/portfolio/long-term-holdings
```

### Convert Position
```
PUT /v2/portfolio/convert-position
```

---

## Charges & Trade P&L

### Brokerage Calculator
```
GET /v2/charges/brokerage?instrument_token=NSE_FO|12345&quantity=25&price=150.5&transaction_type=BUY&product=I
```

### Trade P&L Metadata
```
GET /v2/trade/profit-loss/metadata?from_date=2025-04-01&to_date=2025-03-31&segment=FO&financial_year=2425
```

### Trade P&L Report
```
GET /v2/trade/profit-loss/report?from_date=2025-04-01&to_date=2025-03-31&segment=FO&financial_year=2425&page_number=1&page_size=50
```

### Trade P&L Charges
```
GET /v2/trade/profit-loss/charges?from_date=2025-04-01&to_date=2025-03-31&segment=FO&financial_year=2425&page_number=1&page_size=50
```

---

## WebSocket Authorization

### Market Data Feed (v3 — V2 discontinued Aug 22, 2025)
```
GET /v2/feed/market-data-feed/authorize
```

**Response:**
```json
{
  "data": {
    "authorized_redirect_uri": "wss://ws.upstox.com/market-data-feed/v3?token=abc..."
  }
}
```

### Portfolio Stream Feed
```
GET /v2/feed/portfolio-stream-feed/authorize
```

Returns authorized URL for portfolio real-time updates stream.

---

## Expired Instruments (Upstox Plus Only)

```
GET /v2/market-quote/instruments/expired?exchange=NSE
```

Returns expired instruments. Available only to Upstox Plus subscribers.
