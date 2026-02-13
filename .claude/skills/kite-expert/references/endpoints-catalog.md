# Kite Connect Endpoints Catalog

Complete REST API endpoint reference for Zerodha Kite Connect v3.

**Base URL:** `https://api.kite.trade`

**Auth Header:** `Authorization: token {api_key}:{access_token}`

**Standard Response Envelope:**
```json
{
  "status": "success"|"error",
  "data": { ... },
  "message": "",
  "error_type": ""
}
```

---

## Authentication

### Generate Session (Exchange request_token)

```
POST /session/token
Content-Type: application/x-www-form-urlencoded
```

**Body:**
```
api_key={api_key}&request_token={request_token}&checksum={sha256(api_key+request_token+api_secret)}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "user_id": "AB1234",
    "user_name": "John Doe",
    "access_token": "xyz789",
    "public_token": "pub456",
    "login_time": "2025-02-27 09:15:00",
    "exchanges": ["NSE", "BSE", "NFO", "BFO", "MCX"],
    "products": ["CNC", "NRML", "MIS", "BO", "CO"],
    "order_types": ["MARKET", "LIMIT", "SL", "SL-M"]
  }
}
```

### Invalidate Session

```
DELETE /session/token
```

**Body:** `api_key={api_key}&access_token={access_token}`

---

## User

### Get Profile

```
GET /user/profile
```

**Response:**
```json
{
  "data": {
    "user_id": "AB1234",
    "user_name": "John Doe",
    "user_shortname": "JD",
    "email": "john@example.com",
    "user_type": "individual",
    "broker": "ZERODHA",
    "exchanges": ["NSE", "BSE", "NFO"],
    "products": ["CNC", "NRML", "MIS"],
    "order_types": ["MARKET", "LIMIT", "SL", "SL-M"]
  }
}
```

### Get Margins

```
GET /user/margins
GET /user/margins/{segment}  # equity or commodity
```

**Response:**
```json
{
  "data": {
    "equity": {
      "enabled": true,
      "net": 500000.0,
      "available": {
        "adhoc_margin": 0,
        "cash": 300000.0,
        "opening_balance": 500000.0,
        "live_balance": 300000.0,
        "collateral": 0,
        "intraday_payin": 0
      },
      "utilised": {
        "debits": 200000.0,
        "exposure": 100000.0,
        "m2m_unrealised": -5000.0,
        "m2m_realised": 2000.0,
        "option_premium": 30000.0,
        "payout": 0,
        "span": 150000.0,
        "holding_sales": 0,
        "turnover": 0
      }
    }
  }
}
```

---

## Market Data (Quotes)

### Full Quote

```
GET /quote?i={exchange}:{tradingsymbol}&i={exchange}:{tradingsymbol}
```

**Example:** `GET /quote?i=NFO:NIFTY2522725000CE&i=NSE:RELIANCE`

**Response (per instrument):**
```json
{
  "data": {
    "NFO:NIFTY2522725000CE": {
      "instrument_token": 12345678,
      "timestamp": "2025-02-27T14:30:00+05:30",
      "last_trade_time": "2025-02-27T14:30:00+05:30",
      "last_price": 150.25,
      "last_quantity": 50,
      "buy_quantity": 250000,
      "sell_quantity": 300000,
      "volume": 1250000,
      "average_price": 149.50,
      "oi": 500000,
      "oi_day_high": 520000,
      "oi_day_low": 480000,
      "net_change": 0,
      "lower_circuit_limit": 0.05,
      "upper_circuit_limit": 500.0,
      "ohlc": {
        "open": 145.0,
        "high": 155.5,
        "low": 142.0,
        "close": 148.75
      },
      "depth": {
        "buy": [
          {"price": 150.2, "quantity": 500, "orders": 3},
          {"price": 150.15, "quantity": 750, "orders": 5},
          {"price": 150.1, "quantity": 1000, "orders": 8},
          {"price": 150.05, "quantity": 1200, "orders": 10},
          {"price": 150.0, "quantity": 2000, "orders": 15}
        ],
        "sell": [
          {"price": 150.3, "quantity": 400, "orders": 2},
          {"price": 150.35, "quantity": 600, "orders": 4},
          {"price": 150.4, "quantity": 800, "orders": 6},
          {"price": 150.45, "quantity": 900, "orders": 7},
          {"price": 150.5, "quantity": 1500, "orders": 12}
        ]
      }
    }
  }
}
```

### LTP Only

```
GET /quote/ltp?i={exchange}:{tradingsymbol}
```

**Response:**
```json
{
  "data": {
    "NFO:NIFTY2522725000CE": {
      "instrument_token": 12345678,
      "last_price": 150.25
    }
  }
}
```

### OHLC

```
GET /quote/ohlc?i={exchange}:{tradingsymbol}
```

**Response:**
```json
{
  "data": {
    "NFO:NIFTY2522725000CE": {
      "instrument_token": 12345678,
      "last_price": 150.25,
      "ohlc": {
        "open": 145.0,
        "high": 155.5,
        "low": 142.0,
        "close": 148.75
      }
    }
  }
}
```

**Note:** All REST quote prices are in **RUPEES** (float). No paise conversion needed.

---

## Historical Data

### Get Candle Data

```
GET /instruments/historical/{instrument_token}/{interval}?from={from}&to={to}&continuous={0|1}&oi={0|1}
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `instrument_token` | int (path) | Kite instrument token |
| `interval` | string (path) | Candle interval (see below) |
| `from` | string (query) | Start datetime `YYYY-MM-DD HH:MM:SS` |
| `to` | string (query) | End datetime `YYYY-MM-DD HH:MM:SS` |
| `continuous` | int (query) | `1` for continuous futures data |
| `oi` | int (query) | `1` to include open interest |

**Interval Values:**

| Value | Description |
|-------|-------------|
| `minute` | 1-minute |
| `3minute` | 3-minute |
| `5minute` | 5-minute |
| `10minute` | 10-minute |
| `15minute` | 15-minute |
| `30minute` | 30-minute |
| `60minute` | 1-hour |
| `day` | Daily |

**Response - Prices in RUPEES:**
```json
{
  "data": {
    "candles": [
      ["2025-02-27T09:15:00+0530", 145.0, 148.5, 144.0, 147.25, 500000, 200000],
      ["2025-02-27T09:20:00+0530", 147.25, 149.0, 146.5, 148.0, 350000, 205000]
    ]
  }
}
```

**Array format:** `[timestamp, open, high, low, close, volume, oi(optional)]`

---

## Instruments

### Get All Instruments

```
GET /instruments
GET /instruments/{exchange}
```

**Returns:** CSV file (not JSON!)

**CSV Columns:**
```
instrument_token, exchange_token, tradingsymbol, name, last_price, expiry, strike,
tick_size, lot_size, instrument_type, segment, exchange
```

**Example Row:**
```
12345678,12345,NIFTY2522725000CE,NIFTY,150.25,2025-02-27,25000.0,0.05,25,CE,NFO-OPT,NFO
```

**File Size:** ~80 MB for all exchanges. Cache for 24 hours.

---

## Orders

### Place Order

```
POST /orders/{variety}
Content-Type: application/x-www-form-urlencoded
```

**Varieties:** `regular`, `amo`, `co`, `iceberg`

**Body (form-encoded):**
```
tradingsymbol=NIFTY2522725000CE
exchange=NFO
transaction_type=BUY
order_type=MARKET
quantity=25
product=NRML
validity=DAY
price=0
trigger_price=0
disclosed_quantity=0
tag=autopilot_1
```

**Parameters:**

| Field | Required | Values |
|-------|----------|--------|
| `tradingsymbol` | Yes | Kite symbol |
| `exchange` | Yes | NSE, BSE, NFO, BFO, MCX |
| `transaction_type` | Yes | BUY, SELL |
| `order_type` | Yes | MARKET, LIMIT, SL, SL-M |
| `quantity` | Yes | Number of shares/lots |
| `product` | Yes | CNC, NRML, MIS |
| `validity` | Yes | DAY, IOC, TTL |
| `price` | For LIMIT/SL | Limit price |
| `trigger_price` | For SL/SL-M | Trigger price |
| `tag` | Optional | Custom tag (max 20 chars) |

**Response:**
```json
{
  "data": {
    "order_id": "210227000000001"
  }
}
```

### Modify Order

```
PUT /orders/{variety}/{order_id}
```

**Body:** Same fields as place order (only changed fields needed).

### Cancel Order

```
DELETE /orders/{variety}/{order_id}
```

### Get Orders

```
GET /orders
```

**Response:**
```json
{
  "data": [
    {
      "order_id": "210227000000001",
      "parent_order_id": null,
      "exchange_order_id": "1000000000001",
      "placed_by": "AB1234",
      "variety": "regular",
      "status": "COMPLETE",
      "tradingsymbol": "NIFTY2522725000CE",
      "exchange": "NFO",
      "instrument_token": 12345678,
      "transaction_type": "BUY",
      "order_type": "MARKET",
      "product": "NRML",
      "validity": "DAY",
      "price": 0,
      "quantity": 25,
      "trigger_price": 0,
      "average_price": 150.25,
      "filled_quantity": 25,
      "pending_quantity": 0,
      "cancelled_quantity": 0,
      "disclosed_quantity": 0,
      "order_timestamp": "2025-02-27 09:30:00",
      "exchange_timestamp": "2025-02-27 09:30:00",
      "tag": "autopilot_1"
    }
  ]
}
```

### Get Order History

```
GET /orders/{order_id}
```

Returns array of order state transitions.

### Get Trades

```
GET /trades
GET /orders/{order_id}/trades
```

---

## Positions

### Get Positions

```
GET /portfolio/positions
```

**Response:**
```json
{
  "data": {
    "net": [
      {
        "tradingsymbol": "NIFTY2522725000CE",
        "exchange": "NFO",
        "instrument_token": 12345678,
        "product": "NRML",
        "quantity": 25,
        "overnight_quantity": 0,
        "multiplier": 1,
        "average_price": 150.25,
        "close_price": 148.75,
        "last_price": 152.5,
        "value": -3756.25,
        "pnl": 56.25,
        "m2m": 56.25,
        "unrealised": 56.25,
        "realised": 0,
        "buy_quantity": 25,
        "buy_price": 150.25,
        "buy_value": 3756.25,
        "sell_quantity": 0,
        "sell_price": 0,
        "sell_value": 0
      }
    ],
    "day": [...]
  }
}
```

### Convert Position

```
PUT /portfolio/positions
```

**Body:**
```
tradingsymbol=NIFTY2522725000CE&exchange=NFO&transaction_type=BUY&position_type=day&quantity=25&old_product=MIS&new_product=NRML
```

---

## Holdings

### Get Holdings

```
GET /portfolio/holdings
```

**Response:**
```json
{
  "data": [
    {
      "tradingsymbol": "RELIANCE",
      "exchange": "NSE",
      "instrument_token": 738561,
      "isin": "INE002A01018",
      "product": "CNC",
      "quantity": 10,
      "t1_quantity": 0,
      "realised_quantity": 10,
      "authorised_quantity": 0,
      "average_price": 2500.0,
      "last_price": 2550.0,
      "close_price": 2540.0,
      "pnl": 500.0,
      "day_change": 10.0,
      "day_change_percentage": 0.39
    }
  ]
}
```

---

## GTT (Good Till Triggered)

### Create GTT Trigger

```
POST /gtt/triggers
Content-Type: application/x-www-form-urlencoded
```

**Body:**
```
type=single&condition={"exchange":"NSE","tradingsymbol":"RELIANCE","trigger_values":[2400.0],"last_price":2550.0}&orders=[{"exchange":"NSE","tradingsymbol":"RELIANCE","transaction_type":"BUY","quantity":10,"order_type":"LIMIT","product":"CNC","price":2400.0}]
```

### Get GTT Triggers

```
GET /gtt/triggers
```

### Get/Modify/Delete GTT

```
GET /gtt/triggers/{trigger_id}
PUT /gtt/triggers/{trigger_id}
DELETE /gtt/triggers/{trigger_id}
```

---

## Basket Orders

### Place Basket (Iceberg)

```
POST /orders/iceberg
```

Creates multiple child orders from a parent.

---

## Rate Limits by Endpoint

| Endpoint | Rate Limit |
|----------|-----------|
| All endpoints (default) | 3 req/sec |
| All endpoints (premium) | 10 req/sec |
| Order placement | 10 orders/sec |
| Quote (REST) | 1 req/sec |
| Historical | 3 req/sec |
| Instruments download | Once/day |

**AlgoChanakya rate_limiter.py:** `"kite": 3` (3 req/sec)
