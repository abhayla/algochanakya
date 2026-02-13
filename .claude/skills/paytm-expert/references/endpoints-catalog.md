# Paytm Money REST API Endpoints Catalog

**Base URL:** `https://developer.paytmmoney.com`

> **MATURITY WARNING:** Endpoint paths and response schemas have changed between API versions
> without deprecation periods. Always verify against the latest Paytm developer docs.

## Common Headers

```python
headers = {"x-jwt-token": token, "Content-Type": "application/json", "Accept": "application/json"}
```

## Complete Endpoint Reference

### Authentication

| Method | Endpoint | Token | Description |
|--------|----------|-------|-------------|
| POST | `/accounts/v2/gettoken` | None (api_key + api_secret) | Exchange requestToken for 3 JWTs |
| DELETE | `/accounts/v1/logout` | `access_token` | Invalidate current session |

```python
# POST /accounts/v2/gettoken
{"api_key": "...", "api_secret_key": "...", "request_token": "..."}
# => {"access_token": "eyJ...", "public_access_token": "eyJ...", "read_access_token": "eyJ..."}
```

### Profile & Margins

| Method | Endpoint | Token | Description |
|--------|----------|-------|-------------|
| GET | `/accounts/v1/user/details` | `read_access_token` | User profile and account info |
| GET | `/accounts/v1/funds/summary` | `read_access_token` | Available margins and fund details |

### Market Data (Live)

| Method | Endpoint | Token | Description |
|--------|----------|-------|-------------|
| GET | `/data/v1/price/live` | `read_access_token` | Live price for single instrument |
| POST | `/data/v1/price/live` | `read_access_token` | Batch live prices (multiple instruments) |

```python
# GET /data/v1/price/live?mode=FULL&pref_exchange=NSE&security_id=500325
# POST /data/v1/price/live  {"mode": "LTP", "pref_exchange": "NSE", "security_ids": ["500325", "532540"]}
# Modes: LTP (last price only), FULL (OHLCV + bid/ask + OI)
# Response: {security_id, last_price, open, high, low, close, volume, bid_price, ask_price, oi}
```

### Historical Data (OHLC)

| Method | Endpoint | Token | Description |
|--------|----------|-------|-------------|
| GET | `/data/v1/price/ohlc` | `read_access_token` | OHLC candles for an instrument |

```python
# GET /data/v1/price/ohlc?security_id=500325&exchange=NSE&resolution=1D&from=1704067200&to=1706745600
# Resolutions: 1, 5, 15, 30, 60 (minutes), 1D (daily)
# from/to: Unix timestamps (seconds)
# Response: {"candles": [[timestamp, open, high, low, close, volume], ...]}
```

### Orders (require `access_token` for write, `read_access_token` for read)

| Method | Endpoint | Token | Description |
|--------|----------|-------|-------------|
| POST | `/orders/v1/place/regular` | `access_token` | Place regular order |
| PUT | `/orders/v1/modify/regular` | `access_token` | Modify pending order |
| DELETE | `/orders/v1/cancel/regular` | `access_token` | Cancel pending order |
| GET | `/orders/v1/order-book` | `read_access_token` | All orders for the day |
| GET | `/orders/v1/trade-details` | `read_access_token` | Trade details for an order |

```python
# POST /orders/v1/place/regular
{
    "txn_type": "B",          # B=Buy, S=Sell
    "exchange": "NSE",        # NSE, BSE
    "segment": "E",           # E=Equity, D=Derivative
    "product": "I",           # I=Intraday, C=CNC, M=Margin
    "security_id": "500325",
    "quantity": 1,
    "validity": "DAY",        # DAY, IOC
    "order_type": "LMT",      # LMT, MKT, SL, SLM
    "price": 1825.00,
    "trigger_price": 0,       # Required for SL/SLM
    "source": "N"
}
# => {"order_no": "202401150001", "status": "PLACED"}

# PUT  /orders/v1/modify/regular  - Same fields + "order_no"
# DELETE /orders/v1/cancel/regular?order_no=202401150001&source=N
```

### Positions & Holdings

| Method | Endpoint | Token | Description |
|--------|----------|-------|-------------|
| GET | `/accounts/v1/positions` | `read_access_token` | Current day positions |
| GET | `/accounts/v1/positions/details` | `read_access_token` | Detailed position info |
| GET | `/holdings/v1/get-user-holdings` | `read_access_token` | Demat holdings |

### Instruments

| Method | Endpoint | Token | Description |
|--------|----------|-------|-------------|
| GET | `/data/v1/scrip/download/csv` | `read_access_token` | Full instrument master CSV |

> Download daily. Columns: security_id, exchange, segment, symbol, series, expiry, strike, option_type, lot_size, tick_size, isin, display_name.

## Rate Limits

| Category | Limit | Window |
|----------|-------|--------|
| REST API (general) | 10 requests | Per second |
| Order placement | 10 orders | Per second |
| Historical data | 3 requests | Per second |
| Script master download | 1 request | Per minute |

> **MATURITY WARNING:** Rate limits are not formally documented. Values above are based on
> observed 429 responses. Configure AlgoChanakya's `RateLimiter` conservatively (8 req/s).
