# Live Integration Tests — Rules & Conventions

> This file governs `backend/tests/live/`. Read it before writing or modifying any live test.

## Core Rule: Tests Must Test Real Things

**Live tests MUST call endpoints that actually exist and return real data.**
They must FAIL (not skip) when the system produces wrong results.

### What is a valid skip
- Broker credentials not configured in `.env`
- External broker API rejects connection (429, connection limit)
- Instrument data not loaded yet (no expiry data in DB)
- Endpoint requires OAuth token and none is available

### What is NOT a valid skip
- Endpoint returns 404 because we called the wrong URL
- Endpoint returns 422 because we passed wrong parameters
- Test was written for a planned-but-not-yet-implemented endpoint

**Before adding `pytest.skip()`, ask: "Is this an infrastructure limitation, or did I call the wrong endpoint?"**

---

## Finding the Correct Endpoints

Before writing a test that calls an API endpoint, verify the endpoint exists:

```bash
# Find all routes registered in the app
grep -n "include_router\|prefix" backend/app/main.py

# Find routes within a file
grep -n "@router\." backend/app/api/routes/<name>.py

# Test an endpoint manually
curl http://localhost:8001/api/health
curl http://localhost:8001/api/watchlists/ -H "Authorization: Bearer <token>"
```

### Current endpoint map (update when routes change)

| Screen | Correct endpoint | Notes |
|--------|-----------------|-------|
| Watchlists | `GET /api/watchlists/` | Plural, trailing slash |
| Option Chain | `GET /api/optionchain/chain?underlying=NIFTY&expiry=YYYY-MM-DD` | Requires both params |
| Positions | `GET /api/positions/` | Trailing slash |
| Orders | `GET /api/orders/` | |
| Market Data Source | `PUT /api/smartapi/market-data-source` + `GET /api/smartapi/market-data-source` | Body: `{"source": "smartapi"}` |
| SmartAPI Quotes | `POST /api/smartapi/quote` | Body: `{"instruments": ["NSE:NIFTY 50"], "mode": "FULL"}` |

---

## NormalizedTick Field Names

`NormalizedTick` (from `app/services/brokers/market_data/ticker/models.py`) uses:

| Correct field | Wrong field (do NOT use) |
|--------------|--------------------------|
| `tick.token` | `tick.instrument_token` |
| `tick.ltp` | `tick.last_price`, `tick.price` |
| `tick.broker_type` | ✓ correct |

---

## Broker Name Mapping

The `set_broker` fixture maps test broker names to API source values:

| Test param | API `source` value | Supported |
|-----------|-------------------|-----------|
| `angelone` | `smartapi` | ✓ |
| `kite` | `kite` | ✓ |
| `upstox`, `dhan`, `fyers`, `paytm` | _(skip — not yet in API)_ | Pending |

The backend `MarketDataSourceRequest` schema currently only accepts `smartapi` and `kite`.
When adding support for more brokers, update `_BROKER_TO_SOURCE` in `test_live_screens_api.py`
AND update the schema pattern in `app/schemas/smartapi.py`.

---

## HTTP Client Setup

The `live_app_client` in `test_live_screens_api.py` uses:
- `limits=httpx.Limits(max_keepalive_connections=0)` — disables keep-alive to avoid stale
  connections after long-running requests (AngelOne login takes 20-25s)
- `timeout=60.0` — increased from default 5s
- Session-scoped with manual `aclose()` in a `try/finally` to suppress event-loop-closed errors

---

## WebSocket / Ticker Tests

AngelOne (`smartapi`) limits 1 concurrent WebSocket per API key.
If the production backend holds the connection, all WebSocket tests will get a 429.

The `_connect_or_skip()` helper:
1. Calls `connect()`
2. Waits 2 seconds for async 429 to propagate
3. Checks `adapter.is_connected` — skips if False

Do NOT remove this sleep or the 429 check. It is intentional.

---

## Option Chain Expiry

The option chain endpoint requires a valid `expiry` date that exists in the instrument DB.
The nearest upcoming Thursday is calculated dynamically. If no instruments exist for that
expiry, the test skips with a message (not fails). This is expected outside market hours
or if the instrument master hasn't been downloaded.

---

## AngelOne 3-API-Key Architecture (CRITICAL)

AngelOne uses **3 separate API keys** in `backend/.env`, each for a different data domain:

| `.env` Key | Purpose | Endpoints used |
|-----------|---------|---------------|
| `ANGEL_API_KEY` | Live market data (WebSocket ticks, live quotes) | SmartConnect WebSocket, ltpData, getMarketData |
| `ANGEL_HIST_API_KEY` | Historical candle data | `getCandleData` only |
| `ANGEL_TRADE_API_KEY` | Order execution | `placeOrder`, `cancelOrder`, `orderBook`, `position`, `rmsLimit`, `getProfile` |

**Using the wrong key for an endpoint → AG8001 Invalid Token error.**

### How keys are used in code:

- `SmartAPIMarketDataAdapter.__init__()` uses `ANGEL_API_KEY` for market data,
  `ANGEL_HIST_API_KEY` for the `SmartAPIHistorical` instance
- `AngelOneAdapter.initialize()` falls back to `ANGEL_TRADE_API_KEY` if no `api_key` passed
- `conftest.py` `angelone_credentials` exposes all 3: `api_key`, `hist_api_key`, `trade_api_key`
- `angelone_order_adapter` fixture passes `trade_api_key` to `get_broker_adapter()`

### Skip logic for AG8001:

- Historical tests: `_get_historical_or_skip()` in `test_live_market_data.py` catches
  `DataNotAvailableError` with "invalid token" / "ag8001" and skips with a clear message
- Order tests: `test_place_and_cancel_order` skips if rejected with "No response" (AG8001)

If tests skip with AG8001:
1. Check `ANGEL_HIST_API_KEY` is set in `backend/.env`
2. Check `ANGEL_TRADE_API_KEY` is set in `backend/.env`
3. Verify the keys have the correct permissions enabled in AngelOne developer console
