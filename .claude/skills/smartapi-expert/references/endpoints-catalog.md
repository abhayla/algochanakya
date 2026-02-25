# SmartAPI Endpoints Catalog

Complete REST API endpoint reference for Angel One SmartAPI.

**Base URL:** `https://apiconnect.angelbroking.com`

**Common Headers (required on all authenticated requests):**
```
Authorization: Bearer {jwtToken}
Content-Type: application/json
Accept: application/json
X-UserType: USER
X-SourceID: WEB
X-ClientLocalIP: {client_ip}
X-ClientPublicIP: {public_ip}
X-MACAddress: {mac_address}
X-PrivateKey: {api_key}
```

**Standard Response Envelope:**
```json
{
  "status": true|false,
  "message": "SUCCESS"|"error message",
  "errorcode": ""|"AG8001",
  "data": { ... }
}
```

---

## Authentication

### Login

```
POST /rest/auth/angelbroking/user/v1/loginByPassword
```

**Body:**
```json
{
  "clientcode": "A12345",
  "password": "1234",
  "totp": "123456"
}
```

**Response Data:**
```json
{
  "jwtToken": "eyJ...",
  "refreshToken": "eyJ...",
  "feedToken": "eyJ..."
}
```

### Refresh Token

```
POST /rest/auth/angelbroking/jwt/v1/generateTokens
```

**Body:**
```json
{
  "refreshToken": "eyJ..."
}
```

**Response:** Same as login (new jwt, refresh, feed tokens).

### Logout

```
POST /rest/auth/angelbroking/user/v1/logout
```

**Body:**
```json
{
  "clientcode": "A12345"
}
```

---

## User Profile

### Get Profile

```
GET /rest/secure/angelbroking/user/v1/getProfile
```

**Response Data:**
```json
{
  "clientcode": "A12345",
  "name": "John Doe",
  "email": "john@example.com",
  "mobileno": "9876543210",
  "exchanges": ["NSE", "BSE", "NFO", "MCX"],
  "products": ["DELIVERY", "MARGIN", "INTRADAY"],
  "broker": "ANGEL"
}
```

### Get RMS (Risk Management / Margins)

```
GET /rest/secure/angelbroking/user/v1/getRMS
```

**Response Data:**
```json
{
  "net": "500000.00",
  "availablecash": "300000.00",
  "availableintradaypayin": "200000.00",
  "availablelimitmargin": "100000.00",
  "collateral": "0.00",
  "m2munrealized": "-5000.00",
  "m2mrealized": "2000.00",
  "utiliseddebits": "200000.00",
  "utilisedspan": "150000.00",
  "utilisedoptionpremium": "30000.00",
  "utilisedexposure": "20000.00"
}
```

---

## Market Data (REST)

### Get Quote (Full / LTP / OHLC)

```
POST /rest/secure/angelbroking/market/v1/quote/
```

**Body:**
```json
{
  "mode": "FULL",
  "exchangeTokens": {
    "NFO": ["12345", "67890"],
    "NSE": ["2885"]
  }
}
```

**Mode Values:** `FULL`, `LTP`, `OHLC`

**Response Data (FULL mode) - Prices in RUPEES:**
```json
{
  "fetched": [
    {
      "exchange": "NFO",
      "tradingSymbol": "NIFTY27FEB2525000CE",
      "symbolToken": "12345",
      "ltp": "150.25",
      "open": "145.00",
      "high": "155.50",
      "low": "142.00",
      "close": "148.75",
      "lastTradeQty": "50",
      "exchFeedTime": "27-Feb-2025 14:30:00",
      "exchTradeTime": "27-Feb-2025 14:30:00",
      "netChange": "1.50",
      "percentChange": "1.01",
      "avgPrice": "149.50",
      "tradeVolume": "1250000",
      "opnInterest": "500000",
      "lowerCircuit": "0.05",
      "upperCircuit": "500.00",
      "totBuyQuan": "250000",
      "totSellQuan": "300000",
      "52WeekLow": "50.00",
      "52WeekHigh": "500.00",
      "depth": {
        "buy": [
          {"price": "150.20", "quantity": "500", "orders": "3"},
          {"price": "150.15", "quantity": "750", "orders": "5"}
        ],
        "sell": [
          {"price": "150.30", "quantity": "400", "orders": "2"},
          {"price": "150.35", "quantity": "600", "orders": "4"}
        ]
      }
    }
  ],
  "unfetched": []
}
```

**Response Data (LTP mode):**
```json
{
  "fetched": [
    {
      "exchange": "NFO",
      "tradingSymbol": "NIFTY27FEB2525000CE",
      "symbolToken": "12345",
      "ltp": "150.25"
    }
  ]
}
```

### Get Index Quote

Uses the same quote endpoint but with index tokens:

| Index | Exchange | Token |
|-------|----------|-------|
| NIFTY 50 | NSE | `99926000` |
| NIFTY BANK | NSE | `99926009` |
| NIFTY FIN SERVICE | NSE | `99926037` |
| SENSEX | BSE | `99919000` |

---

## Historical Data

### Get Candle Data

```
POST /rest/secure/angelbroking/apiconnect/hist/v2/getCandleData
```

**Body:**
```json
{
  "exchange": "NFO",
  "symboltoken": "12345",
  "interval": "FIVE_MINUTE",
  "fromdate": "2025-02-01 09:15",
  "todate": "2025-02-27 15:30"
}
```

**Interval Values:**

| Value | Description | Max Days Per Request |
|-------|-------------|---------------------|
| `ONE_MINUTE` | 1-minute candles | 30 days |
| `THREE_MINUTE` | 3-minute candles | 60 days |
| `FIVE_MINUTE` | 5-minute candles | 100 days |
| `TEN_MINUTE` | 10-minute candles | 100 days |
| `FIFTEEN_MINUTE` | 15-minute candles | 200 days |
| `THIRTY_MINUTE` | 30-minute candles | 200 days |
| `ONE_HOUR` | 1-hour candles | 400 days |
| `ONE_DAY` | Daily candles | 2000 days |

**Response Data - Prices in PAISE (divide by 100!):**
```json
{
  "data": [
    ["2025-02-27T09:15:00+05:30", 15025, 15530, 14200, 14875, 1250000]
  ]
}
```

**Array format:** `[timestamp, open, high, low, close, volume]`

**CRITICAL:** Historical prices are in **PAISE**. Divide by 100 for rupees.

---

## Instruments

### Search Scrip

```
POST /rest/secure/angelbroking/order/v1/searchScrip
```

**Body:**
```json
{
  "exchange": "NFO",
  "searchscrip": "NIFTY 25000 CE"
}
```

**Response Data:**
```json
{
  "data": [
    {
      "exchange": "NFO",
      "tradingsymbol": "NIFTY27FEB2525000CE",
      "symboltoken": "12345"
    }
  ]
}
```

### Instrument Master (Download)

Not a REST endpoint - direct file download:

```
GET https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
```

Returns ~50MB JSON array. See [symbol-format.md](./symbol-format.md) for format details.

---

## Orders

### Place Order

```
POST /rest/secure/angelbroking/order/v1/placeOrder
```

**Body:**
```json
{
  "variety": "NORMAL",
  "tradingsymbol": "NIFTY27FEB2525000CE",
  "symboltoken": "12345",
  "transactiontype": "BUY",
  "exchange": "NFO",
  "ordertype": "MARKET",
  "producttype": "CARRYFORWARD",
  "duration": "DAY",
  "price": "0",
  "squareoff": "0",
  "stoploss": "0",
  "quantity": "25"
}
```

**Variety Values:** `NORMAL`, `STOPLOSS`, `AMO`, `ROBO` (bracket)

**Order Types:** `MARKET`, `LIMIT`, `STOPLOSS_LIMIT`, `STOPLOSS_MARKET`

**Product Types:** `DELIVERY`, `CARRYFORWARD` (NRML), `MARGIN` (MIS), `INTRADAY`, `BO`

**Duration:** `DAY`, `IOC`

**Response:**
```json
{
  "data": {
    "script": "NIFTY27FEB2525000CE",
    "orderid": "210227000000001",
    "uniqueorderid": "abc123"
  }
}
```

### Modify Order

```
POST /rest/secure/angelbroking/order/v1/modifyOrder
```

**Body:**
```json
{
  "variety": "NORMAL",
  "orderid": "210227000000001",
  "ordertype": "LIMIT",
  "producttype": "CARRYFORWARD",
  "duration": "DAY",
  "price": "150.00",
  "quantity": "25",
  "tradingsymbol": "NIFTY27FEB2525000CE",
  "symboltoken": "12345",
  "exchange": "NFO"
}
```

### Cancel Order

```
POST /rest/secure/angelbroking/order/v1/cancelOrder
```

**Body:**
```json
{
  "variety": "NORMAL",
  "orderid": "210227000000001"
}
```

### Get Order Book

```
GET /rest/secure/angelbroking/order/v1/getOrderBook
```

**Response Data:**
```json
{
  "data": [
    {
      "variety": "NORMAL",
      "ordertype": "MARKET",
      "producttype": "CARRYFORWARD",
      "duration": "DAY",
      "price": "0.00",
      "triggerprice": "0.00",
      "quantity": "25",
      "disclosedquantity": "0",
      "squareoff": "0.00",
      "stoploss": "0.00",
      "trailingstoploss": "0.00",
      "tradingsymbol": "NIFTY27FEB2525000CE",
      "transactiontype": "BUY",
      "exchange": "NFO",
      "symboltoken": "12345",
      "instrumenttype": "",
      "strikeprice": "-1.00",
      "optiontype": "",
      "expirydate": "",
      "lotsize": "25",
      "cancelsize": "0",
      "averageprice": "150.25",
      "filledshares": "25",
      "unfilledshares": "0",
      "orderid": "210227000000001",
      "text": "",
      "status": "complete",
      "orderstatus": "complete",
      "updatetime": "27-Feb-2025 14:30:00",
      "exchtime": "27-Feb-2025 14:30:00",
      "exchorderupdatetime": "27-Feb-2025 14:30:00",
      "fillid": "",
      "filltime": "",
      "parentorderid": ""
    }
  ]
}
```

### Get Trade Book

```
GET /rest/secure/angelbroking/order/v1/getTradeBook
```

Returns list of executed trades with fill details.

---

## Positions

### Get Positions

```
GET /rest/secure/angelbroking/order/v1/getPosition
```

**Response Data:**
```json
{
  "data": [
    {
      "exchange": "NFO",
      "symboltoken": "12345",
      "producttype": "CARRYFORWARD",
      "tradingsymbol": "NIFTY27FEB2525000CE",
      "symbolname": "NIFTY",
      "instrumenttype": "OPTIDX",
      "priceden": "1",
      "pricenum": "1",
      "genden": "1",
      "gennum": "1",
      "precision": "2",
      "multiplier": "-1",
      "boardlotsize": "25",
      "buyqty": "25",
      "sellqty": "0",
      "buyamount": "3756.25",
      "sellamount": "0.00",
      "symbolgroup": "",
      "strikeprice": "-1.00",
      "optiontype": "",
      "expirydate": "",
      "lotsize": "25",
      "cfbuyqty": "0",
      "cfsellqty": "0",
      "cfbuyamount": "0.00",
      "cfsellamount": "0.00",
      "buyavgprice": "150.25",
      "sellavgprice": "0.00",
      "avgnetprice": "150.25",
      "netvalue": "-3756.25",
      "netqty": "25",
      "totalbuyvalue": "3756.25",
      "totalsellvalue": "0.00",
      "cfbuyavgprice": "0.00",
      "cfsellavgprice": "0.00",
      "totalbuyavgprice": "150.25",
      "totalsellavgprice": "0.00",
      "netprice": "150.25",
      "ltp": "152.50",
      "close": "148.75",
      "unrealised": "56.25",
      "realised": "0.00",
      "pnl": "56.25"
    }
  ]
}
```

### Convert Position

```
POST /rest/secure/angelbroking/order/v1/convertPosition
```

**Body:**
```json
{
  "exchange": "NFO",
  "symboltoken": "12345",
  "producttype": "MARGIN",
  "newproducttype": "CARRYFORWARD",
  "tradingsymbol": "NIFTY27FEB2525000CE",
  "symbolname": "NIFTY",
  "instrumenttype": "OPTIDX",
  "priceden": "1",
  "pricenum": "1",
  "genden": "1",
  "gennum": "1",
  "precision": "2",
  "multiplier": "-1",
  "boardlotsize": "25",
  "buyqty": "25",
  "sellqty": "0",
  "buyamount": "3756.25",
  "sellamount": "0.00",
  "transactiontype": "BUY",
  "quantity": "25",
  "type": "DAY"
}
```

---

## Holdings

### Get Holdings

```
GET /rest/secure/angelbroking/portfolio/v1/getHolding
```

**Response Data:**
```json
{
  "data": [
    {
      "tradingsymbol": "RELIANCE-EQ",
      "exchange": "NSE",
      "isin": "INE002A01018",
      "t1quantity": "0",
      "realisedquantity": "10",
      "quantity": "10",
      "authorisedquantity": "0",
      "product": "DELIVERY",
      "collateralquantity": "0",
      "collateraltype": "",
      "haircut": "0.00",
      "averageprice": "2500.00",
      "ltp": "2550.00",
      "symboltoken": "2885",
      "close": "2540.00",
      "profitandloss": "500.00",
      "pnlpercentage": "2.00"
    }
  ]
}
```

---

## GTT (Good Till Triggered)

### Create GTT Rule

```
POST /rest/secure/angelbroking/gtt/v1/createRule
```

**Body:**
```json
{
  "tradingsymbol": "RELIANCE-EQ",
  "symboltoken": "2885",
  "exchange": "NSE",
  "producttype": "DELIVERY",
  "transactiontype": "BUY",
  "price": "2400.00",
  "qty": "10",
  "disclosedqty": "0",
  "triggerprice": "2400.00",
  "timeperiod": "365"
}
```

### Get GTT Rule List

```
POST /rest/secure/angelbroking/gtt/v1/ruleList
```

**Body:**
```json
{
  "status": ["NEW", "CANCELLED", "ACTIVE", "SENTTOEXCHANGE", "FORALL"],
  "page": 1,
  "count": 10
}
```

### Get GTT Rule Details

```
GET /rest/secure/angelbroking/gtt/v1/ruleDetails?id={gtt_rule_id}
```

**Response Data:**
```json
{
  "data": {
    "id": "GTT123456",
    "status": "ACTIVE",
    "tradingsymbol": "SBIN-EQ",
    "symboltoken": "3045",
    "exchange": "NSE",
    "transactiontype": "BUY",
    "producttype": "DELIVERY",
    "price": "500.00",
    "qty": "10",
    "triggerprice": "490.00",
    "timeperiod": "365",
    "createdon": "2025-02-01 09:15:00",
    "updatedon": "2025-02-01 09:15:00"
  }
}
```

### Modify GTT Rule

```
PUT /rest/secure/angelbroking/gtt/v1/modifyRule
```

**Body:** Same fields as createRule plus `id` (the GTT rule ID to modify).

### Cancel GTT Rule

```
POST /rest/secure/angelbroking/gtt/v1/cancelRule
```

**Body:**
```json
{
  "id": "GTT123456",
  "symboltoken": "3045",
  "exchange": "NSE"
}
```

**GTT Rule Statuses:** `NEW`, `ACTIVE`, `SENTTOEXCHANGE`, `FORALL`, `CANCELLED`, `EXECUTED`

See [gtt-orders.md](./gtt-orders.md) for complete GTT reference and AlgoChanakya integration notes.

---

## Option Chain

### Get Option Chain

```
GET /rest/secure/angelbroking/marketData/v1/optionChain?name={underlying}&expirydate={date}
```

**Query Parameters:**

| Parameter | Required | Example |
|-----------|----------|---------|
| `name` | Yes | `NIFTY`, `BANKNIFTY`, `FINNIFTY`, `SENSEX` |
| `expirydate` | Yes | `27FEB2025` (DDMMMYYYY format) |

**Response Data (prices in RUPEES):**
```json
{
  "data": {
    "fetched": [
      {
        "strikePrice": "22000",
        "expiryDate": "27FEB2025",
        "PE": {
          "token": "45678",
          "symbol": "NIFTY25FEB22000PE",
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

**Note:** Option Chain REST prices are in **RUPEES** (unlike WebSocket which is paise).

See [option-chain.md](./option-chain.md) for complete Greeks reference and supported underlyings.

---

## Order Update WebSocket

**URL:** `wss://tns.angelone.in/smart-order-update`

This is separate from the market data WebSocket. It streams real-time order status updates.

**Auth:** Use `feedToken` from login response.

**Connection message:**
```json
{
  "task": "connect",
  "channel": "",
  "token": "{feedToken}",
  "user": "{client_id}",
  "acctid": "{client_id}"
}
```

**Order update message format:**
```json
{
  "type": "order_feed",
  "orderid": "240915000123456",
  "orderstatus": "complete",
  "tradingsymbol": "SBIN-EQ",
  "filledshares": "10",
  "averageprice": "499.85"
}
```

See [webhook.md](./webhook.md) for complete connection setup, all message fields, and REST polling alternative.

---

## Rate Limits by Endpoint

| Endpoint Category | Rate Limit | Notes |
|-------------------|-----------|-------|
| All REST endpoints | 1 request/second (shared) | Per API key |
| Order placement | **20 orders/second** | Increased from 10 in Feb 2025 |
| Historical data | 1 request/second | Shared with general limit |
| Instrument master download | Cache for 12+ hours | ~50MB file |
| Option Chain | 1 request/second | Shared with general limit |
| GTT operations | 1 request/second | Shared with general limit |

**AlgoChanakya rate_limiter.py:** `"smartapi": 1` (1 req/sec global REST limit). The 20 orders/sec is broker-side enforcement; AlgoChanakya adapter does not need per-order throttling.
