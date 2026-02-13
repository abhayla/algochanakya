# Upstox Endpoints Catalog

Complete REST API endpoint reference for Upstox API v2.

**Base URL:** `https://api.upstox.com/v2`
**Auth Header:** `Authorization: Bearer {access_token}`

---

## Authentication

### Exchange Authorization Code

```
POST /v2/login/authorization/token
Content-Type: application/x-www-form-urlencoded
```

**Body:** `code={code}&client_id={api_key}&client_secret={secret}&redirect_uri={url}&grant_type=authorization_code`

---

## User / Margins

### Get Profile
```
GET /v2/user/profile
```

### Get Funds and Margin
```
GET /v2/user/get-funds-and-margin
GET /v2/user/get-funds-and-margin?segment=SEC  # SEC or COM
```

**Response:**
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

---

## Market Data (Quotes)

### Full Quote
```
GET /v2/market-quote/quotes?instrument_key=NSE_FO|12345,NSE_INDEX|Nifty 50
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

### Historical Candles
```
GET /v2/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}
```

**Intervals:** `1minute`, `30minute`, `day`, `week`, `month`

**Example:** `GET /v2/historical-candle/NSE_FO|12345/day/2025-02-27/2025-01-01`

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
**Note:** Candles are in **descending order** (newest first).

### Intraday Candles
```
GET /v2/historical-candle/intraday/{instrument_key}/{interval}
```

---

## Instruments

### Get Instruments
```
GET /v2/market-quote/instruments?exchange=NSE
```

Returns JSON array of all instruments for the exchange.

---

## Orders

### Place Order
```
POST /v2/order/place
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
  "is_amo": false
}
```

**Products:** `D` (Delivery/CNC), `I` (Intraday/MIS), `CO` (Cover Order), `OC` (OCO/Bracket)

### Modify Order
```
PUT /v2/order/modify
```

### Cancel Order
```
DELETE /v2/order/cancel?order_id={order_id}
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

## WebSocket Authorization

### Get Authorized WS URL
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

Use this URL to establish WebSocket connection.

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| General REST | 25 req/sec |
| Historical | 6 req/sec |
| Orders | 25 req/sec |
| WebSocket auth | 1 req/min |
