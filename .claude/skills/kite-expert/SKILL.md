---
name: kite-expert
description: Kite Connect (Zerodha) API expert. Consult for authentication, endpoints, WebSocket,
  error codes, rate limits, symbol format, and adapter guidance for AlgoChanakya.
---

# Kite Connect (Zerodha) API Expert

Zerodha's Kite Connect is used for **order execution** in AlgoChanakya. It provides a well-documented REST API and binary WebSocket (KiteTicker) for market data. Kite Connect requires a ₹500/month subscription for third-party app access, but Zerodha's personal Kite API is free. AlgoChanakya uses Kite for orders and SmartAPI for market data (₹0/month total). **Kite symbol format IS the canonical format** used throughout AlgoChanakya - no symbol conversion needed.

## When to Use

- Implementing or modifying the Kite order execution adapter
- Debugging Kite API errors, OAuth flow, or access token issues
- Understanding Kite symbol format (canonical format for AlgoChanakya)
- Working with KiteTicker WebSocket binary protocol
- Comparing Kite capabilities with other brokers
- Auditing code that calls Kite API for correctness
- Writing tests that mock Kite API responses

## API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://kite.trade/docs/connect/v3/ |
| **API Version** | v3 |
| **Python SDK** | `kiteconnect` (`pip install kiteconnect`) |
| **Pricing** | ₹500/month (Connect subscription), FREE (personal Kite API) |
| **REST Base URL** | `https://api.kite.trade` |
| **WebSocket URL** | `wss://ws.kite.trade` |
| **Auth Method** | OAuth 2.0 redirect flow (request_token + api_secret) |
| **Token Validity** | access_token: ~24h (until 6 AM next day), no auto-refresh |

## Authentication Flow

Kite uses a standard **OAuth 2.0 redirect flow**. No auto-refresh - user must re-login daily.

### Step-by-Step Authentication

```
1. Redirect user → https://kite.zerodha.com/connect/login?v=3&api_key={api_key}
2. User logs in on Zerodha's website
3. Zerodha redirects → {redirect_url}?request_token={token}&action=login&status=success
4. POST /session/token with api_key, request_token, checksum (SHA-256 of api_key + request_token + api_secret)
5. Response: { access_token, public_token, user_id }
6. Use access_token for all API calls: Authorization: token {api_key}:{access_token}
```

### Token Types

| Token | Purpose | Validity | Notes |
|-------|---------|----------|-------|
| `request_token` | Exchange for access_token | Single use, ~5 min | From OAuth redirect |
| `access_token` | REST + WebSocket auth | Until ~6 AM next day | Cannot be refreshed |
| `public_token` | Public data only | Same as access_token | Limited endpoints |

### Auth Header Format

```
Authorization: token {api_key}:{access_token}
```

**Example:** `Authorization: token abc123:xyz789`

### No Auto-Refresh

Unlike SmartAPI, Kite has **no refresh token**. When access_token expires (~6 AM), the user must complete the OAuth flow again. This is why AlgoChanakya uses SmartAPI (with auto-TOTP) as the default market data source.

See [auth-flow.md](./references/auth-flow.md) for complete request/response examples.

## Key Endpoints Quick Reference

| Category | Method | Endpoint | Notes |
|----------|--------|----------|-------|
| **Auth** | POST | `/session/token` | Exchange request_token |
| **Auth** | DELETE | `/session/token` | Invalidate session |
| **Profile** | GET | `/user/profile` | User details |
| **Margins** | GET | `/user/margins` | Available margins |
| **Margins** | GET | `/user/margins/{segment}` | Segment margins |
| **Quote** | GET | `/quote?i={exchange}:{symbol}` | Full quote |
| **LTP** | GET | `/quote/ltp?i={exchange}:{symbol}` | LTP only |
| **OHLC** | GET | `/quote/ohlc?i={exchange}:{symbol}` | OHLC + LTP |
| **Historical** | GET | `/instruments/historical/{token}/{interval}` | OHLCV candles |
| **Instruments** | GET | `/instruments` | All instruments CSV |
| **Instruments** | GET | `/instruments/{exchange}` | Exchange instruments |
| **Place Order** | POST | `/orders/{variety}` | Place order |
| **Modify Order** | PUT | `/orders/{variety}/{order_id}` | Modify pending |
| **Cancel Order** | DELETE | `/orders/{variety}/{order_id}` | Cancel pending |
| **Orders** | GET | `/orders` | All orders |
| **Trades** | GET | `/trades` | All trades |
| **Positions** | GET | `/portfolio/positions` | Positions |
| **Holdings** | GET | `/portfolio/holdings` | Holdings |
| **GTT** | POST | `/gtt/triggers` | Create GTT |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete schemas.

## Symbol Format (CANONICAL)

### Kite IS the Canonical Format

**Kite symbol format is the canonical format used throughout AlgoChanakya.** No conversion needed when working with Kite symbols.

**Format Pattern:** `{UNDERLYING}{YY}{MON_OR_DATE}{STRIKE}{CE|PE}`

**Examples:**

| Instrument | Kite Symbol (= Canonical) | Instrument Token |
|-----------|--------------------------|------------------|
| NIFTY Index | `NIFTY 50` | `256265` |
| BANKNIFTY Index | `NIFTY BANK` | `260105` |
| NIFTY 25000 CE (weekly) | `NIFTY2522725000CE` | varies |
| NIFTY 25000 CE (monthly) | `NIFTY25FEB25000CE` | varies |
| BANKNIFTY Future | `NIFTY25FEBFUT` | varies |
| Reliance Equity | `RELIANCE` | `738561` |

### Weekly vs Monthly Expiry Format

| Type | Format | Example |
|------|--------|---------|
| **Weekly** | `{UNDERLYING}{YY}{M}{DD}{STRIKE}{CE\|PE}` | `NIFTY2522725000CE` (Feb 27, 2025) |
| **Monthly** | `{UNDERLYING}{YY}{MON}{STRIKE}{CE\|PE}` | `NIFTY25FEB25000CE` (Feb monthly) |

**Month codes (weekly):** `1`=Jan, `2`=Feb, ..., `9`=Sep, `O`=Oct, `N`=Nov, `D`=Dec

### Key Index Tokens

| Index | Token | Exchange |
|-------|-------|----------|
| NIFTY 50 | `256265` | NSE |
| NIFTY BANK | `260105` | NSE |
| NIFTY FIN SERVICE | `257801` | NSE |
| SENSEX | `265` | BSE |

See [symbol-format.md](./references/symbol-format.md) for complete format details.

## WebSocket Protocol (KiteTicker)

### Binary Tick Format

KiteTicker sends **binary messages** with 3 modes:

| Mode | Bytes per Tick | Fields |
|------|---------------|--------|
| **LTP** | 8 | Token + LTP |
| **Quote** | 44 | Token + OHLC + Volume + OI + Bid/Ask |
| **Full** | 184 | Quote + 5-level depth + timestamps |

### Prices in PAISE (int32)

All prices are **int32 in paise**. Divide by 100 for rupees.

```python
ltp_paise = struct.unpack('>I', data[4:8])[0]
ltp_rupees = ltp_paise / 100.0  # 15025 → 150.25
```

### Connection URL

```
wss://ws.kite.trade?api_key={api_key}&access_token={access_token}
```

### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max tokens per connection | **3000** |
| Max connections | **3** |
| Tick rate | Real-time (exchange feed) |

See [websocket-protocol.md](./references/websocket-protocol.md) for byte offsets and parsing.

## Rate Limits

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| General API | **3 requests/second** | Default tier |
| General API (premium) | **10 requests/second** | Higher plan |
| Historical data | **3 requests/second** | Shared with general |
| Order placement | **10 orders/second** | Per user |
| Quote API | **1 request/second** | Use WebSocket for live data |
| Instruments dump | **Once per day** | ~80MB CSV, cache it |

**AlgoChanakya Configuration:** `rate_limiter.py` sets `"kite": 3` (3 req/sec).

## Price Normalization

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** (quotes, LTP) | **RUPEES** (float) | No conversion |
| **REST API** (historical) | **RUPEES** (float) | No conversion |
| **WebSocket** (all modes) | **PAISE** (int32) | Divide by 100 |

**Note:** Unlike SmartAPI where REST historical returns paise, Kite REST always returns rupees. Only WebSocket uses paise.

## AlgoChanakya Integration

### Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Order Execution Adapter | **✅ Complete** | `backend/app/services/brokers/kite_adapter.py` |
| Market Data Adapter | **✅ Complete** | `backend/app/services/brokers/market_data/kite_adapter.py` |
| WebSocket Ticker | **✅ Legacy** | `backend/app/services/legacy/kite_ticker.py` |
| Order Service | **✅ Legacy** | `backend/app/services/legacy/kite_orders.py` |
| OAuth Callback | **✅ Complete** | `backend/app/api/routes/auth.py` |
| Factory Registration | **✅ Complete** | `backend/app/services/brokers/factory.py` |

### Key Integration Points

```python
# Order execution via adapter
from app.services.brokers.factory import get_broker_adapter
adapter = get_broker_adapter("kite", credentials)
order = await adapter.place_order(unified_order)  # Returns UnifiedOrder

# Market data via adapter
from app.services.brokers.market_data.factory import get_market_data_adapter
data_adapter = get_market_data_adapter("kite", credentials, db)
quote = await data_adapter.get_quote(["NIFTY2522725000CE"])
```

### Broker Name Mapping

**Important gotcha:** Database stores `'zerodha'` but BrokerType uses `'kite'`:

```python
# BrokerConnection.broker_name = "zerodha" (database)
# BrokerType.KITE = "kite" (enum)
# Use name mapping utility when converting
```

## Common Gotchas

1. **No auto-refresh** - Access token expires ~6 AM. No refresh mechanism. User must OAuth again. This is why SmartAPI is default for market data.

2. **Symbol format IS canonical** - Don't convert Kite symbols. They ARE the canonical format. `SymbolConverter.to_canonical(symbol, "kite")` is identity.

3. **Auth header format** - `token api_key:access_token` (not `Bearer`). Common mistake: using Bearer prefix.

4. **Checksum for session** - `POST /session/token` requires SHA-256 of `api_key + request_token + api_secret`. Missing or wrong checksum = silent failure.

5. **Instrument CSV is 80MB** - Download once, cache for 24h. Don't download on every request.

6. **WebSocket prices in paise** - int32 paise. REST prices in rupees (float). Don't mix them.

7. **Order variety in URL** - `/orders/regular`, `/orders/amo`, `/orders/co`, `/orders/iceberg`. Variety is part of the URL, not the body.

8. **Exchange prefix in quotes** - Quote endpoint needs `i=NFO:NIFTY2522725000CE` format. Missing exchange prefix = 400 error.

9. **Rate limit is 3/sec** - Moderate. Use WebSocket for live data, REST only for on-demand queries.

10. **₹500/month subscription** - Kite Connect requires a paid subscription for third-party apps. Personal Kite API is free but limited.

## Error Codes Quick Reference

| HTTP Status | Exception Class | Cause | Retryable |
|-------------|----------------|-------|-----------|
| `400` | `InputException` | Invalid parameters | No |
| `403` | `TokenException` | Invalid/expired token | No - re-auth |
| `429` | `NetworkException` | Rate limit exceeded | Yes - backoff |
| `500` | `GeneralException` | Server error | Yes - retry |
| `502` | `NetworkException` | Gateway error | Yes - retry |
| `503` | `NetworkException` | Service unavailable | Yes - retry |

See [error-codes.md](./references/error-codes.md) for complete error catalog.

## Related Skills

For cross-broker work, consult these complementary skills:

| Skill | When to Use |
|-------|-------------|
| `/smartapi-expert` | Kite's default pair for market data — compare paise handling, auto-TOTP vs OAuth, WS binary formats |
| `/upstox-expert` | Next adapter to implement — compare Protobuf vs binary WS, extended token vs OAuth |
| `/trading-constants-manager` | Kite symbol format IS canonical — verify constants match when adding new instruments |
| `/auto-verify` | After any Kite adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, CHANGELOG, broker abstraction docs |

**Cross-Broker Comparison:** See [comparison-matrix.md](../broker-shared/comparison-matrix.md) for pricing, rate limits, WebSocket capabilities, and symbol format differences across all 6 brokers.

## References

- [Authentication Flow](./references/auth-flow.md) - OAuth flow with request/response examples
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints with schemas
- [WebSocket Protocol](./references/websocket-protocol.md) - KiteTicker binary format and parsing
- [Error Codes](./references/error-codes.md) - Complete error code reference
- [Symbol Format](./references/symbol-format.md) - Canonical format specification
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
