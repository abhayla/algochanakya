# Fyers Endpoints Catalog

Complete REST API endpoint reference for Fyers API v3.

**Base URL:** `https://api-t1.fyers.in/api/v3`

**Auth Header:** `Authorization: {app_id}:{access_token}` (colon-separated, NOT Bearer)

**Response Envelope:** `{ "s": "ok"|"error", "code": 200|-1, "message": "", "data": {...} }`

---

## Endpoint Summary Table

| Category | Method | Endpoint | Notes |
|----------|--------|----------|-------|
| Auth | POST | `/api/v3/validate-authcode` | Exchange auth code for token |
| Profile | GET | `/api/v3/profile` | User details (fy_id, name, email) |
| Funds | GET | `/api/v3/funds` | Balances, margins, collateral |
| Depth | GET | `/api/v3/depth?symbol={sym}` | Single symbol full depth |
| Quotes | POST | `/api/v3/quotes` | Multiple quotes (max 50) |
| Historical | GET | `/api/v3/history` | OHLCV candles |
| Place Order | POST | `/api/v3/orders/sync` | Synchronous order |
| Place Order | POST | `/api/v3/orders/async` | Asynchronous order |
| Modify | PUT | `/api/v3/orders/{id}` | Modify pending order |
| Cancel | DELETE | `/api/v3/orders/{id}` | Cancel pending order |
| Orders | GET | `/api/v3/orders` | Order book |
| Trades | GET | `/api/v3/tradebook` | Trade book |
| Positions | GET | `/api/v3/positions` | Net positions |
| Convert | POST | `/api/v3/positions` | Convert product type |
| Holdings | GET | `/api/v3/holdings` | Portfolio holdings |

---

## Auth: Validate Auth Code

```
POST /api/v3/validate-authcode
Body: { "grant_type": "authorization_code", "appIdHash": "sha256_hex", "code": "auth_code" }
Response: { "s": "ok", "access_token": "eyJ...", "token_type": "Bearer" }
```

## Market Data: Depth

```
GET /api/v3/depth?symbol=NSE:NIFTY2522725000CE&ohlcv_flag=1
```

Key response fields (all prices in **RUPEES**):

| Field | Description | Field | Description |
|-------|-------------|-------|-------------|
| `lp` | Last price | `v` | Volume |
| `o`,`h`,`l`,`c` | OHLC | `oi` | Open interest |
| `ch`/`chp` | Change/% | `pdoi` | Previous day OI |
| `tbq`/`tsq` | Total buy/sell qty | `bid`/`ask` | 5-level depth arrays |

## Market Data: Quotes (Multiple)

```
POST /api/v3/quotes
Body: { "symbols": "NSE:NIFTY2522725000CE,NSE:NIFTY50-INDEX" }
```

Symbols are **comma-separated string** (not array). Max 50 per request.

## Historical Data

```
GET /api/v3/history?symbol={sym}&resolution={res}&range_from={epoch}&range_to={epoch}&date_format=1
```

**Resolutions:** `1`,`2`,`3`,`5`,`10`,`15`,`30`,`60`,`120`,`240` (minutes), `D`,`W`,`M`

| Resolution | Max Range | Resolution | Max Range |
|-----------|-----------|-----------|-----------|
| 1-3 min | 30 days | 60 min | 180 days |
| 5-10 min | 60 days | 120-240 min | 365 days |
| 15-30 min | 90 days | D/W/M | Unlimited |

**Response:** `{ "candles": [[timestamp, open, high, low, close, volume], ...] }` -- prices in **RUPEES**.

---

## Orders

### Place Order

```
POST /api/v3/orders/sync   (waits for exchange)
POST /api/v3/orders/async  (returns immediately)
```

```json
{
  "symbol": "NSE:NIFTY2522725000CE",
  "qty": 25, "type": 2, "side": 1,
  "productType": "INTRADAY", "limitPrice": 0,
  "stopPrice": 0, "validity": "DAY",
  "offlineOrder": false, "orderTag": "algochanakya"
}
```

**Order types:** `1`=Limit, `2`=Market, `3`=SL-M, `4`=SL
**Side:** `1`=Buy, `-1`=Sell (integers, NOT strings)
**Product types:** `INTRADAY` (MIS), `CNC` (Delivery), `MARGIN` (NRML), `BO`, `CO`
**Response:** `{ "s": "ok", "id": "808058117761" }`

### Modify / Cancel

```
PUT /api/v3/orders/{id}     Body: { "id": "...", "type": 1, "qty": 25, "limitPrice": 152.00 }
DELETE /api/v3/orders/{id}  Body: { "id": "808058117761" }
```

### Order Status Values

| Value | Status | Value | Status |
|-------|--------|-------|--------|
| `1` | Cancelled | `4` | Transit |
| `2` | Traded/Filled | `5` | Rejected |
| `6` | Pending | | |

---

## Positions

```
GET /api/v3/positions
```

Key fields: `symbol`, `netQty`, `buyAvg`, `sellAvg`, `pl`, `ltp`, `productType`, `realized_profit`, `unrealized_profit`. Includes `overall` summary with `pl_total`.

### Convert Position

```
POST /api/v3/positions
Body: { "symbol": "NSE:...", "positionSide": 1, "convertQty": 25, "convertFrom": "INTRADAY", "convertTo": "MARGIN" }
```

---

## Holdings

```
GET /api/v3/holdings
```

Key fields: `symbol`, `quantity`, `costPrice`, `ltp`, `profitOrLoss`, `pnlPercentage`, `isin`. Includes `overall` summary.

---

## Funds

```
GET /api/v3/funds
```

Returns `fund_limit` array with objects `{ "id": N, "title": "...", "equityAmount": N }`.

| ID | Title | ID | Title |
|----|-------|----|-------|
| 10 | Total Balance | 3 | Available Margin |
| 6 | Available Balance | 4 | Utilized Margin |
| 2 | Used Margin | 9 | Collateral |

---

## Instruments (CSV Download)

```
NSE Cash:  https://public.fyers.in/sym_details/NSE_CM.csv
NSE F&O:   https://public.fyers.in/sym_details/NSE_FO.csv
BSE Cash:  https://public.fyers.in/sym_details/BSE_CM.csv
BSE F&O:   https://public.fyers.in/sym_details/BSE_FO.csv
MCX:       https://public.fyers.in/sym_details/MCX_COM.csv
```

Cache for 12+ hours. Download daily before market open.

---

## Rate Limits

| Endpoint | Limit | Endpoint | Limit |
|----------|-------|----------|-------|
| General REST | 10 req/sec | Historical | 1 req/sec |
| Order placement | 10 orders/sec | Quotes batch | 10 req/sec (50 symbols max) |

**AlgoChanakya:** `rate_limiter.py` sets `"fyers": 10`.
