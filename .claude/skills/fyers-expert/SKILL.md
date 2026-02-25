---
name: fyers-expert
description: Use when implementing Fyers adapter, debugging Fyers API errors, understanding Fyers dual WebSocket system, or auditing code calling Fyers API. Fyers API expert for AlgoChanakya.
metadata:
  author: AlgoChanakya
  version: "2.0"
  last_verified: "2026-02-25"
---

# Fyers API Expert

Fyers offers a **FREE** API with a unique **dual WebSocket system** (FyersDataSocket for market data + FyersOrderSocket for order updates), OAuth authentication with a distinctive `appid:accesstoken` header format. **API v3.0.0** (released Feb 3, 2026) supports up to **5,000 symbols** per WebSocket connection (massive upgrade from 200) and includes a dedicated Position Socket for real-time P&L updates. All 3 AlgoChanakya adapters (market data, order execution, ticker/WebSocket) are **fully implemented**. Key differentiator: two separate WebSocket connections and exchange-prefixed symbol format (`NSE:SYMBOL`).

## When to Use

- Implementing or debugging the Fyers market data, order, or ticker adapter
- Debugging Fyers API errors or OAuth flow issues
- Understanding Fyers symbol format (`NSE:NIFTY2522725000CE`)
- Working with dual WebSocket system (Data + Order sockets)
- Setting up virtual/paper trading mode
- Comparing Fyers capabilities with other brokers
- Auditing code that calls Fyers API for correctness

## When NOT to Use

- General broker abstraction questions (read docs/architecture/broker-abstraction.md instead)
- Cross-broker comparison (use broker-shared/comparison-matrix.md instead)
- SmartAPI/Kite/Upstox/Dhan issues (use their respective expert skills)
- Paytm issues (use paytm-expert)

## API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://myapi.fyers.in/docs/ |
| **API Version** | v3.0.0 (released Feb 3, 2026) |
| **Python SDK** | `fyers-apiv3` (`pip install fyers-apiv3`) |
| **Pricing** | **FREE** (market data + orders) |
| **REST Base URL** | `https://api-t1.fyers.in/api/v3` |
| **Data WS URL** | Via SDK (FyersDataSocket) |
| **Order WS URL** | Via SDK (FyersOrderSocket) |
| **Auth Method** | OAuth 2.0 (authorization_code) |
| **Token Validity** | access_token: until ~midnight IST |

## Authentication Flow

Fyers uses OAuth 2.0 with a unique auth header format: `appid:accesstoken`.

### Step-by-Step Authentication

```
1. Redirect user → https://api-t1.fyers.in/api/v3/generate-authcode
   ?client_id={app_id}&redirect_uri={url}&response_type=code&state={state}
2. User logs in on Fyers website
3. Fyers redirects → {redirect_url}?auth_code={code}&state={state}
4. POST /api/v3/validate-authcode with appIdHash, code, etc.
5. Response: { access_token }
6. Use in header: Authorization: {app_id}:{access_token}
```

### Auth Header Format (UNIQUE)

```
Authorization: {app_id}:{access_token}
```

**Example:** `Authorization: ABC123-100:eyJ...`

**Note:** This is NOT `Bearer` format. The app_id and access_token are colon-separated.

### Token Types

| Token | Purpose | Validity |
|-------|---------|----------|
| `auth_code` | Exchange for access_token | Single use, ~5 min |
| `access_token` | All API calls | Until ~midnight IST |

See [auth-flow.md](./references/auth-flow.md) for complete request/response examples.

## Key Endpoints Quick Reference

| Category | Method | Endpoint | Notes |
|----------|--------|----------|-------|
| **Auth** | POST | `/api/v3/validate-authcode` | Exchange auth code |
| **Profile** | GET | `/api/v3/profile` | User details |
| **Margins** | GET | `/api/v3/funds` | Fund details |
| **Quote** | GET | `/api/v3/depth` | Full market depth |
| **Quotes** | POST | `/api/v3/quotes` | Multiple quotes |
| **Historical** | GET | `/api/v3/history` | OHLCV candles |
| **Place Order** | POST | `/api/v3/orders/sync` | Place order (sync) |
| **Place Order** | POST | `/api/v3/orders/async` | Place order (async) |
| **Modify Order** | PUT | `/api/v3/orders/{order_id}` | Modify pending |
| **Cancel Order** | DELETE | `/api/v3/orders/{order_id}` | Cancel pending |
| **Orders** | GET | `/api/v3/orders` | All orders |
| **Positions** | GET | `/api/v3/positions` | Current positions |
| **Holdings** | GET | `/api/v3/holdings` | Portfolio holdings |
| **Instruments** | Download | CSV from Fyers | Instrument master |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete schemas.

## Symbol Format

### Exchange-Prefixed Format

Fyers uses `{EXCHANGE}:{SYMBOL}` format with exchange prefix.

**Examples:**

| Instrument | Fyers Symbol | Notes |
|-----------|-------------|-------|
| NIFTY 50 Index | `NSE:NIFTY50-INDEX` | Index with suffix |
| NIFTY BANK Index | `NSE:NIFTYBANK-INDEX` | Index with suffix |
| NIFTY 25000 CE (weekly) | `NSE:NIFTY2522725000CE` | Same as Kite after prefix |
| NIFTY 25000 CE (monthly) | `NSE:NIFTY25FEB25000CE` | Same as Kite after prefix |
| NIFTY Future | `NSE:NIFTY25FEBFUT` | With exchange prefix |
| Reliance Equity | `NSE:RELIANCE-EQ` | With -EQ suffix |

### Canonical Conversion

**Low complexity** - Fyers symbols are Kite symbols with exchange prefix:

```python
# Fyers → Canonical: strip exchange prefix
canonical = fyers_symbol.split(":")[1]  # "NSE:NIFTY2522725000CE" → "NIFTY2522725000CE"

# Canonical → Fyers: add exchange prefix
fyers = f"NSE:{canonical}"  # For equities, also add "-EQ" suffix
```

**Special cases:**
- Indices: `NSE:NIFTY50-INDEX` → `NIFTY 50`
- Equities: `NSE:RELIANCE-EQ` → `RELIANCE`

See [symbol-format.md](./references/symbol-format.md) for complete rules.

## WebSocket Protocol (Dual System)

### Two Separate WebSocket Connections

Fyers uses **two independent WebSocket connections** - unique among Indian brokers:

| Socket | Purpose | Data |
|--------|---------|------|
| **FyersDataSocket** | Market data ticks | LTP, OHLC, volume, OI, depth |
| **FyersOrderSocket** | Order updates | Order status changes, fills |

### FyersDataSocket (Market Data)

```python
from fyers_apiv3.FyersWebsocket import data_ws

def on_message(message):
    print(f"LTP: {message['ltp']}")

data_ws = data_ws.FyersDataSocket(
    access_token=f"{app_id}:{access_token}",
    log_path="",
    litemode=False,
    write_to_file=False,
    reconnect=True,
    on_message=on_message
)
data_ws.subscribe(symbols=["NSE:NIFTY2522725000CE"], data_type="SymbolUpdate")
data_ws.keep_running()
```

### FyersOrderSocket (Order Updates)

```python
from fyers_apiv3.FyersWebsocket import order_ws

def on_order_update(message):
    print(f"Order {message['id']} status: {message['status']}")

order_ws = order_ws.FyersOrderSocket(
    access_token=f"{app_id}:{access_token}",
    write_to_file=False,
    on_order_update=on_order_update
)
order_ws.connect()
```

### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max symbols (Data WS) | **5,000** per connection (upgraded in v3.0.0, Feb 2026) |
| Max connections | **1** per token |
| Data types | SymbolUpdate, DepthUpdate |
| Message format | JSON (not binary) |

See [websocket-protocol.md](./references/websocket-protocol.md) for detailed protocol.

## Rate Limits

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| REST API (general) | **10 requests/second** | Per access_token |
| Historical data | **1 request/second** | Strictest |
| Order placement | **10 orders/second** | Per user |
| WebSocket | **Unlimited ticks** | After subscription |

**AlgoChanakya Configuration:** `rate_limiter.py` sets `"fyers": 10` (10 req/sec).

## Price Normalization

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** | **RUPEES** | No conversion |
| **WebSocket** | **RUPEES** | No conversion |
| **Historical** | **RUPEES** | No conversion |

Fyers returns all prices in RUPEES. No paise conversion needed.

## Virtual Trading (Paper Trading)

Fyers offers **built-in virtual trading** mode:

```python
fyers = fyersModel.FyersModel(
    client_id=app_id,
    token=access_token,
    is_async=False,
    log_path=""
)
# Virtual trading uses same API, different endpoint prefix
```

## AlgoChanakya Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Market Data Adapter | **✅ Implemented** | `backend/app/services/brokers/market_data/fyers_adapter.py` (695 lines) |
| Order Execution Adapter | **✅ Implemented** | `backend/app/services/brokers/fyers_order_adapter.py` (467 lines) |
| Ticker (WebSocket) Adapter | **✅ Implemented** | `backend/app/services/brokers/market_data/ticker/adapters/fyers.py` (410 lines) |
| Auth Route | **✅ Implemented** | `backend/app/api/routes/fyers_auth.py` (201 lines) |
| Frontend Settings | **✅ Implemented** | `frontend/src/components/settings/FyersSettings.vue` |
| Tests | **✅ Complete** | `test_fyers_market_data_adapter.py` (706 lines), `test_fyers_ticker_adapter.py` (718 lines) |

### Current Integration Pattern

```python
# Market data via adapter
from app.services.brokers.market_data.factory import get_market_data_adapter
adapter = get_market_data_adapter("fyers", credentials, db)
quote = await adapter.get_quote(["NIFTY2522725000CE"])  # Returns UnifiedQuote

# Order execution via adapter
from app.services.brokers.fyers_order_adapter import FyersOrderAdapter
adapter = FyersOrderAdapter(app_id=app_id, access_token=token)
order_id = await adapter.place_order(order_params)
```

## Common Gotchas

1. **v3.0.0 breaking changes** - API v3 released Feb 3, 2026 with breaking changes. Ensure using `fyers-apiv3` (not v2). WebSocket symbol capacity increased to 5,000.

2. **Auth header format** - `{app_id}:{access_token}` (colon-separated, no Bearer). Most common auth error.

3. **Exchange prefix required** - All symbols need `NSE:` or `BSE:` prefix. Forgetting it = 400 error.

4. **Dual WebSocket** - Must manage TWO WebSocket connections for full functionality. Data and order sockets are independent.

5. **Index symbol suffix** - Indices need `-INDEX` suffix: `NSE:NIFTY50-INDEX`, not `NSE:NIFTY50`.

6. **Equity suffix** - Equities need `-EQ` suffix: `NSE:RELIANCE-EQ`, not `NSE:RELIANCE`.

7. **Historical rate limit** - Only 1 req/sec for historical data. Strictest among all endpoints.

8. **Virtual trading** - Same API, different mode. Don't accidentally use virtual mode in production.

9. **Token expiry at midnight** - Unlike other brokers (~6 AM), Fyers tokens expire at midnight IST.

10. **appIdHash for auth** - Token exchange requires SHA-256 hash of `app_id:app_secret`. Don't confuse with access token.

11. **SDK version** - Use `fyers-apiv3` (v3), not older `fyers-apiv2`. V2 is deprecated.

## Error Codes Quick Reference

| Code | HTTP | Cause | Retryable |
|------|------|-------|-----------|
| `-1` | 400 | Invalid request | No |
| `-16` | 401 | Invalid/expired token | No - re-auth |
| `-300` | 429 | Rate limit exceeded | Yes - backoff |
| `-310` | 400 | Invalid symbol | No |
| `-320` | 400 | Order rejected | No |
| `-99` | 500 | Server error | Yes - retry |

See [error-codes.md](./references/error-codes.md) for complete error catalog.

## Related Skills

| Skill | When to Use |
|-------|-------------|
| `/upstox-expert` | Both free modern APIs — compare WS approaches (Fyers: JSON dual-WS, Upstox: Protobuf) |
| `/dhan-expert` | Compare unique features — Fyers has order WS + paper trading, Dhan has 200-depth |
| `/smartapi-expert` | Fyers symbol format closest to Kite canonical — compare symbol conversion approaches |
| `/auto-verify` | After any Fyers adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, comparison matrix, CHANGELOG |

**Cross-Broker Comparison:** See [comparison-matrix.md](../broker-shared/comparison-matrix.md) for pricing, rate limits, WebSocket capabilities, and symbol format differences across all 6 brokers.

## Maintenance & Auto-Improvement

### Freshness Tracking

| Reference File | Last Verified | Check Frequency |
|---|---|---|
| skill.md | 2026-02-25 | Quarterly |
| endpoints-catalog.md | 2026-02-25 | Quarterly |
| auth-flow.md | 2026-02-25 | Quarterly |
| error-codes.md | 2026-02-25 | Quarterly |
| websocket-protocol.md | 2026-02-25 | Quarterly |
| symbol-format.md | 2026-02-25 | Quarterly |

### Auto-Update Trigger Rules

1. **Error-driven update**: If this skill is invoked 3+ times with FAILED/UNKNOWN outcome for the same error_type (tracked via `post_skill_learning.py` hook → `knowledge.db`), `reflect deep` mode should propose a skill update.
2. **Staleness alert**: If `last_verified` exceeds 90 days, check https://myapi.fyers.in/docs/ for API changes.
3. **Quarterly review**: Next scheduled review: **May 2026**. Watch for v3.x updates.

### Version Changelog

| Version | Date | Changes |
|---|---|---|
| 2.0 | 2026-02-25 | Implementation status corrected: all 3 adapters fully Implemented (was Planned), auth route + frontend + tests added to status table, maintenance section added |
| 1.0 | 2026-02-16 | Initial creation |

## References

- [Authentication Flow](./references/auth-flow.md) - OAuth flow with appIdHash
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints
- [WebSocket Protocol](./references/websocket-protocol.md) - Dual WS system
- [Error Codes](./references/error-codes.md) - Error code reference
- [Symbol Format](./references/symbol-format.md) - Exchange-prefixed format
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
