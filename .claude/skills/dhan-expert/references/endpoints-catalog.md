# Dhan REST API v2 -- Endpoints Catalog

## Base URL

```
https://api.dhan.co/v2
```

All endpoints require the `access-token` header. See `auth-flow.md` for details.

---

## Common Request Headers

| Header         | Value                     | Required |
|----------------|---------------------------|----------|
| `access-token` | API access token          | Always   |
| `Content-Type` | `application/json`        | POST/PUT |
| `Accept`       | `application/json`        | Optional |

---

## 1. Profile

### GET /profile

Retrieve user profile and account details.

```
GET https://api.dhan.co/v2/profile
```

**Response:**

```json
{
    "clientId": "1234567890",
    "name": "Abhay Kumar",
    "email": "abhay@example.com",
    "phone": "91XXXXXXXX",
    "tradingExperience": "5+",
    "dpScheme": "CDSL",
    "dpNumber": "1234567890123456",
    "bankName": "HDFC Bank",
    "bankAccount": "XXXXXXXXXX",
    "broker": "DHAN"
}
```

---

## 2. Margins / Fund Limits

### GET /fundlimit

Get available margins and fund details.

```
GET https://api.dhan.co/v2/fundlimit
```

**Response:**

```json
{
    "availabelBalance": 150000.00,
    "sodLimit": 200000.00,
    "collateralAmount": 50000.00,
    "receiveableAmount": 0.00,
    "utilisedMargin": 50000.00,
    "blockedPayoutAmount": 0.00,
    "withdrawableBalance": 100000.00
}
```

**Note:** The field `availabelBalance` has a known typo in the Dhan API (missing 'l'). Handle accordingly.

### POST /margincalculator

Calculate margin requirement for a trade.

```
POST https://api.dhan.co/v2/margincalculator
```

**Request Body:**

```json
{
    "dhanClientId": "1234567890",
    "exchangeSegment": "NSE_FNO",
    "transactionType": "BUY",
    "quantity": 50,
    "productType": "MARGIN",
    "securityId": "43854",
    "price": 150.50
}
```

---

## 3. Market Data (REST)

### POST /marketfeed/ltp

Get Last Traded Price for multiple instruments.

```
POST https://api.dhan.co/v2/marketfeed/ltp
```

**Request Body:**

```json
{
    "NSE_EQ": [1333, 11536],
    "NSE_FNO": [43854, 43855],
    "BSE_EQ": [500325]
}
```

**Response:**

```json
{
    "data": {
        "NSE_EQ": {
            "1333": {"last_price": 2450.50},
            "11536": {"last_price": 1825.00}
        },
        "NSE_FNO": {
            "43854": {"last_price": 150.25},
            "43855": {"last_price": 98.75}
        }
    }
}
```

**Limits:** Max 1000 instruments per request.

### POST /marketfeed/ohlc

Get OHLC data for instruments.

```
POST https://api.dhan.co/v2/marketfeed/ohlc
```

**Request Body:** Same format as LTP.

**Response includes:** `open`, `high`, `low`, `close`, `volume` for each instrument.

### POST /marketfeed/quote

Get full quote with 20-depth market data.

```
POST https://api.dhan.co/v2/marketfeed/quote
```

**Request Body:** Same format as LTP (exchange segment -> security_id array).

**Response includes:** LTP, OHLC, volume, OI, bid/ask arrays (20 levels each).

```json
{
    "data": {
        "NSE_FNO": {
            "43854": {
                "last_price": 150.25,
                "open": 148.00,
                "high": 155.00,
                "low": 147.50,
                "close": 149.00,
                "volume": 125000,
                "oi": 5000000,
                "last_trade_time": "2026-02-13T10:30:00",
                "bid": [
                    {"price": 150.20, "quantity": 500},
                    {"price": 150.15, "quantity": 750}
                ],
                "ask": [
                    {"price": 150.30, "quantity": 400},
                    {"price": 150.35, "quantity": 600}
                ]
            }
        }
    }
}
```

---

## 4. Historical Charts / Candle Data

### POST /charts/historical

Get historical OHLCV candle data.

```
POST https://api.dhan.co/v2/charts/historical
```

**Request Body:**

```json
{
    "securityId": "1333",
    "exchangeSegment": "NSE_EQ",
    "instrument": "EQUITY",
    "expiryCode": 0,
    "fromDate": "2026-01-01",
    "toDate": "2026-02-13"
}
```

**Response:**

```json
{
    "open": [2400.0, 2410.0, ...],
    "high": [2450.0, 2460.0, ...],
    "low": [2390.0, 2395.0, ...],
    "close": [2430.0, 2445.0, ...],
    "volume": [1500000, 1800000, ...],
    "timestamp": ["2026-01-01", "2026-01-02", ...]
}
```

**Note:** Response is arrays of values (not array of objects). Each index corresponds to one candle.

### POST /charts/intraday

Get intraday candle data.

```
POST https://api.dhan.co/v2/charts/intraday
```

**Request Body:**

```json
{
    "securityId": "1333",
    "exchangeSegment": "NSE_EQ",
    "instrument": "EQUITY",
    "interval": "5",
    "fromDate": "2026-02-13",
    "toDate": "2026-02-13"
}
```

**Interval Values:**

| Interval | Description    |
|----------|----------------|
| `1`      | 1 minute       |
| `5`      | 5 minutes      |
| `15`     | 15 minutes     |
| `25`     | 25 minutes     |
| `60`     | 1 hour         |

**Expiry Codes for F&O:**

| Code | Meaning          |
|------|------------------|
| `0`  | Near month       |
| `1`  | Next month       |
| `2`  | Far month        |

---

## 5. Orders

### POST /orders

Place a new order.

```
POST https://api.dhan.co/v2/orders
```

**Request Body:**

```json
{
    "dhanClientId": "1234567890",
    "transactionType": "BUY",
    "exchangeSegment": "NSE_FNO",
    "productType": "MARGIN",
    "orderType": "LIMIT",
    "validity": "DAY",
    "securityId": "43854",
    "quantity": 50,
    "price": 150.00,
    "triggerPrice": 0,
    "disclosedQuantity": 0,
    "afterMarketOrder": false,
    "amoTime": "",
    "boProfitValue": 0,
    "boStopLossValue": 0,
    "correlationId": "my-unique-id-123"
}
```

**Transaction Types:** `BUY`, `SELL`

**Product Types:**

| Product Type | Description           |
|--------------|-----------------------|
| `CNC`        | Cash and Carry (delivery) |
| `INTRADAY`   | Intraday              |
| `MARGIN`     | F&O margin            |
| `MTF`        | Margin Trading Facility |
| `CO`         | Cover Order           |
| `BO`         | Bracket Order         |

**Order Types:** `LIMIT`, `MARKET`, `STOP_LOSS`, `STOP_LOSS_MARKET`

**Validity:** `DAY`, `IOC` (Immediate or Cancel)

**Response:**

```json
{
    "orderId": "1234567890123",
    "orderStatus": "TRANSIT"
}
```

### PUT /orders/{order_id}

Modify an existing order.

```
PUT https://api.dhan.co/v2/orders/1234567890123
```

**Request Body:**

```json
{
    "dhanClientId": "1234567890",
    "orderId": "1234567890123",
    "orderType": "LIMIT",
    "legName": "",
    "quantity": 50,
    "price": 152.00,
    "triggerPrice": 0,
    "disclosedQuantity": 0,
    "validity": "DAY"
}
```

### DELETE /orders/{order_id}

Cancel an order.

```
DELETE https://api.dhan.co/v2/orders/1234567890123
```

### GET /orders

Get all orders for the day.

```
GET https://api.dhan.co/v2/orders
```

**Response:** Array of order objects with fields: `orderId`, `exchangeOrderId`, `transactionType`,
`exchangeSegment`, `productType`, `orderType`, `validity`, `securityId`, `tradingSymbol`,
`quantity`, `price`, `triggerPrice`, `filledQty`, `remainingQuantity`, `averagePrice`,
`orderStatus`, `createTime`, `updateTime`, `legName`, `correlationId`.

### GET /orders/{order_id}

Get details of a specific order.

```
GET https://api.dhan.co/v2/orders/1234567890123
```

### GET /orders/{order_id}/trades

Get trade fills for a specific order.

```
GET https://api.dhan.co/v2/orders/1234567890123/trades
```

### POST /orders/slicing

Place a large order with automatic slicing into smaller orders (for freeze quantity limits).

```
POST https://api.dhan.co/v2/orders/slicing
```

**Request Body:** Same as regular order. Dhan automatically slices into exchange-allowed quantities.

---

## 6. Positions

### GET /positions

Get all open positions.

```
GET https://api.dhan.co/v2/positions
```

**Response:**

```json
[
    {
        "dhanClientId": "1234567890",
        "tradingSymbol": "NIFTY-Feb2026-24000-CE",
        "securityId": "43854",
        "positionType": "LONG",
        "exchangeSegment": "NSE_FNO",
        "productType": "MARGIN",
        "buyAvg": 150.25,
        "sellAvg": 0,
        "netQty": 50,
        "buyQty": 50,
        "sellQty": 0,
        "realizedProfit": 0,
        "unrealizedProfit": 250.00,
        "dayBuyQty": 50,
        "daySellQty": 0,
        "dayBuyValue": 7512.50,
        "daySellValue": 0,
        "multiplier": 1,
        "crossCurrency": false
    }
]
```

### POST /positions/convert

Convert position product type (e.g., INTRADAY to CNC).

```
POST https://api.dhan.co/v2/positions/convert
```

**Request Body:**

```json
{
    "dhanClientId": "1234567890",
    "fromProductType": "INTRADAY",
    "toProductType": "CNC",
    "exchangeSegment": "NSE_EQ",
    "positionType": "LONG",
    "securityId": "1333",
    "convertQty": 10
}
```

---

## 7. Holdings

### GET /holdings

Get all holdings (delivery positions).

```
GET https://api.dhan.co/v2/holdings
```

**Response:**

```json
[
    {
        "exchange": "NSE",
        "tradingSymbol": "HDFCBANK",
        "securityId": "1333",
        "isin": "INE040A01034",
        "totalQty": 100,
        "dpQty": 100,
        "t1Qty": 0,
        "availableQty": 100,
        "collateralQty": 0,
        "avgCostPrice": 1650.50
    }
]
```

---

## 8. Trade History

### GET /trades

Get all executed trades for the day.

```
GET https://api.dhan.co/v2/trades
```

### GET /trades/{order_id}

Get trades for a specific order.

```
GET https://api.dhan.co/v2/trades/1234567890123
```

---

## 9. Forever Orders (GTT / GTC)

### POST /forever/orders

Create a forever order (Good Till Triggered).

```
POST https://api.dhan.co/v2/forever/orders
```

**Request Body:**

```json
{
    "dhanClientId": "1234567890",
    "orderFlag": "SINGLE",
    "transactionType": "BUY",
    "exchangeSegment": "NSE_EQ",
    "productType": "CNC",
    "orderType": "LIMIT",
    "securityId": "1333",
    "quantity": 10,
    "price": 1600.00,
    "triggerPrice": 1605.00,
    "price1": 0,
    "triggerPrice1": 0,
    "quantity1": 0
}
```

**Order Flags:** `SINGLE` (GTT), `OCO` (One Cancels Other - target + stop loss)

### PUT /forever/orders/{order_id}

Modify a forever order.

### DELETE /forever/orders/{order_id}

Cancel a forever order.

### GET /forever/orders

Get all forever orders.

---

## 10. EDIS (Electronic Delivery Instruction Slip)

### POST /edis/form

Generate EDIS T-PIN form for sell delivery.

```
POST https://api.dhan.co/v2/edis/form
```

### GET /edis/inquiry

Check EDIS status.

```
GET https://api.dhan.co/v2/edis/inquiry
```

---

## 11. Option Chain

### GET /v2/expirylist

Get available expiry dates for an underlying.

```
GET https://api.dhan.co/v2/expirylist?UnderlyingScrip=13&UnderlyingSeg=IDX_I
```

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `UnderlyingScrip` | int | Underlying security_id | `13` (NIFTY) |
| `UnderlyingSeg` | string | Exchange segment | `IDX_I` |

**Response:**

```json
{
  "status": "success",
  "data": ["2025-02-27", "2025-03-06", "2025-03-27", "2025-04-24"]
}
```

### POST /v2/optionchain

Get full option chain with Greeks for an underlying and expiry.

```
POST https://api.dhan.co/v2/optionchain
```

**Request Body:**

```json
{
  "UnderlyingScrip": 13,
  "UnderlyingSeg": "IDX_I",
  "Expiry": "2025-02-27"
}
```

**Response includes:** Strike list with `call_options` and `put_options` for each strike. Each leg includes: `security_id`, `trading_symbol`, `last_price`, OHLC, `volume`, `open_interest`, `oi_change`, `iv`, `delta`, `theta`, `gamma`, `vega`.

**AlgoChanakya status:** NOT yet implemented. See [option-chain.md](./option-chain.md) for full schema.

---

## 12. WebSockets

### Market Data WebSocket

**URL:** `wss://api-feed.dhan.co`

Binary (little-endian) WebSocket for real-time market data ticks. Supports Ticker, Quote, Full, and 200-Depth modes.

See [websocket-protocol.md](./websocket-protocol.md) for subscription format and binary parsing.

### Live Order Update WebSocket

**URL:** `wss://api-order-update.dhan.co`

Real-time JSON WebSocket stream for order status updates. Authentication via JSON message on connect.

```python
# Auth message sent after connection
auth_msg = {
    "access-token": access_token,
    "dhan-client-id": client_id
}
```

**Response format:** JSON with `orderId`, `orderStatus`, and full order details.

**AlgoChanakya status:** NOT currently used. AlgoChanakya polls REST for order status. See [webhook.md](./webhook.md).

---

## Endpoint Summary Table

| Category         | Method | Endpoint                        | Description                    |
|------------------|--------|---------------------------------|--------------------------------|
| Profile          | GET    | `/profile`                      | User profile                   |
| Margins          | GET    | `/fundlimit`                    | Fund limits (`availabelBalance` typo) |
| Margins          | POST   | `/margincalculator`             | Margin requirement calc        |
| Market Data      | POST   | `/marketfeed/ltp`               | Last traded price              |
| Market Data      | POST   | `/marketfeed/ohlc`              | OHLC data                      |
| Market Data      | POST   | `/marketfeed/quote`             | Full quote with 20-depth       |
| Charts           | POST   | `/charts/historical`            | Historical candles             |
| Charts           | POST   | `/charts/intraday`              | Intraday candles               |
| Orders           | POST   | `/orders`                       | Place order                    |
| Orders           | PUT    | `/orders/{id}`                  | Modify order                   |
| Orders           | DELETE | `/orders/{id}`                  | Cancel order                   |
| Orders           | GET    | `/orders`                       | List all orders                |
| Orders           | GET    | `/orders/{id}`                  | Order details                  |
| Orders           | GET    | `/orders/{id}/trades`           | Trades for order               |
| Orders           | POST   | `/orders/slicing`               | Place sliced order             |
| Positions        | GET    | `/positions`                    | All positions                  |
| Positions        | POST   | `/positions/convert`            | Convert position type          |
| Holdings         | GET    | `/holdings`                     | All holdings                   |
| Trades           | GET    | `/trades`                       | All trades today               |
| Trades           | GET    | `/trades/{order_id}`            | Trades for order               |
| Forever Orders   | POST   | `/forever/orders`               | Create GTT/GTC order (NOT in AlgoChanakya) |
| Forever Orders   | PUT    | `/forever/orders/{id}`          | Modify forever order           |
| Forever Orders   | DELETE | `/forever/orders/{id}`          | Cancel forever order           |
| Forever Orders   | GET    | `/forever/orders`               | List forever orders            |
| Option Chain     | POST   | `/optionchain`                  | Option chain with Greeks (NOT in AlgoChanakya) |
| Option Chain     | GET    | `/expirylist`                   | Expiry dates for underlying    |
| EDIS             | POST   | `/edis/form`                    | Generate EDIS form             |
| EDIS             | GET    | `/edis/inquiry`                 | Check EDIS status              |
| WebSocket (data) | WS     | `wss://api-feed.dhan.co`        | Market data binary stream      |
| WebSocket (orders) | WS   | `wss://api-order-update.dhan.co`| Live order updates (NOT in AlgoChanakya) |

---

## Key Differences from Other Brokers

1. **security_id (numeric)** -- Dhan uses numeric IDs, not trading symbols, in API payloads
2. **Market data is POST** -- LTP/OHLC/Quote endpoints use POST with body (not GET with params)
3. **Array-based historical response** -- Candle data returns parallel arrays, not array of objects
4. **Order slicing built-in** -- The `/orders/slicing` endpoint handles freeze quantity limits automatically
5. **No separate login/session** -- Single long-lived token, no session management
6. **Fund limit typo** -- `availabelBalance` is misspelled in the official API response (missing second 'l'). Use the exact misspelled field name in code.
7. **Option Chain has Greeks** -- `/v2/optionchain` returns delta, gamma, theta, vega, IV — unusual for a broker REST API
8. **Dual WebSocket** -- Separate WebSocket URLs for market data (`api-feed`) and order updates (`api-order-update`)
