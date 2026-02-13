---
name: smartapi-expert
description: SmartAPI (Angel One) API expert. Consult for authentication, endpoints, WebSocket,
  error codes, rate limits, symbol format, and adapter guidance for AlgoChanakya.
---

# SmartAPI (Angel One) API Expert

Angel One's SmartAPI is the **default market data provider** for AlgoChanakya, offering FREE real-time WebSocket prices, REST quotes, and historical OHLCV data. It uses auto-TOTP authentication (no manual TOTP entry). SmartAPI is also planned as a future order execution broker. AlgoChanakya currently uses SmartAPI for all market data and Zerodha Kite Connect for order execution, achieving a ₹0/month total API cost.

## When to Use

- Implementing or modifying the SmartAPI market data adapter
- Debugging SmartAPI API errors or authentication issues (auto-TOTP, token expiry)
- Understanding SmartAPI symbol/token format or instrument master mapping
- Diagnosing **PAISE vs RUPEES** price issues (WebSocket returns paise, REST returns rupees)
- Comparing SmartAPI capabilities with other brokers
- Auditing code that calls SmartAPI API for correctness
- Writing tests that mock SmartAPI API responses

## API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://smartapi.angelbroking.com/docs/ |
| **API Version** | v1 (REST), V2 (WebSocket) |
| **Python SDK** | `smartapi-python` (`pip install smartapi-python`) |
| **Pricing** | **FREE** (market data + orders) |
| **REST Base URL** | `https://apiconnect.angelbroking.com` |
| **WebSocket URL** | `wss://smartapisocket.angelone.in/smart-stream` |
| **Auth Method** | Client ID + PIN + TOTP (auto-generated via pyotp) |
| **Token Validity** | JWT: ~24h, Feed Token: ~24h, Refresh Token: 15 days |

## Authentication Flow

SmartAPI uses a 3-token system with auto-TOTP for hands-free authentication.

### Step-by-Step Authentication

```
1. Generate TOTP → pyotp.TOTP(stored_secret).now()
2. POST /rest/auth/angelbroking/user/v1/loginByPassword
   Body: { clientcode, password, totp }
3. Response: { jwtToken, refreshToken, feedToken }
4. Use jwtToken for REST APIs (Authorization: Bearer {jwt})
5. Use feedToken for WebSocket authentication
6. On expiry → POST /rest/auth/angelbroking/jwt/v1/generateTokens with refreshToken
```

### Token Types

| Token | Purpose | Validity | Header |
|-------|---------|----------|--------|
| `jwtToken` | REST API authentication | ~24 hours | `Authorization: Bearer {jwt}` |
| `feedToken` | WebSocket authentication | ~24 hours | Query param or WS header |
| `refreshToken` | Refresh expired JWT | 15 days | Body of refresh endpoint |

### Auto-TOTP in AlgoChanakya

```python
# AlgoChanakya stores TOTP secret encrypted in smartapi_credentials table
import pyotp
totp = pyotp.TOTP(stored_totp_secret).now()  # 6-digit code, no manual entry
```

### Credential Storage

| Field | Storage | Encryption |
|-------|---------|------------|
| `client_id` | `smartapi_credentials` table | Encrypted (AES) |
| `password` | `smartapi_credentials` table | Encrypted (AES) |
| `totp_secret` | `smartapi_credentials` table | Encrypted (AES) |
| `api_key` | `backend/.env` (`ANGEL_API_KEY`) | Environment variable |

**Codebase:** `backend/app/services/legacy/smartapi_auth.py` handles authentication with auto-TOTP.

See [auth-flow.md](./references/auth-flow.md) for complete request/response examples and error scenarios.

## Key Endpoints Quick Reference

| Category | Method | Endpoint | Notes |
|----------|--------|----------|-------|
| **Auth** | POST | `/rest/auth/angelbroking/user/v1/loginByPassword` | Returns 3 tokens |
| **Auth** | POST | `/rest/auth/angelbroking/jwt/v1/generateTokens` | Refresh JWT |
| **Auth** | POST | `/rest/auth/angelbroking/user/v1/logout` | Invalidate tokens |
| **Profile** | GET | `/rest/secure/angelbroking/user/v1/getProfile` | User details |
| **Quote** | POST | `/rest/secure/angelbroking/market/v1/quote/` | Full quote (RUPEES) |
| **LTP** | POST | `/rest/secure/angelbroking/market/v1/quote/` | mode=LTP (RUPEES) |
| **Historical** | POST | `/rest/secure/angelbroking/apiconnect/hist/v2/getCandleData` | OHLCV candles |
| **Search** | POST | `/rest/secure/angelbroking/order/v1/searchScrip` | Search instruments |
| **Place Order** | POST | `/rest/secure/angelbroking/order/v1/placeOrder` | Place order |
| **Modify Order** | POST | `/rest/secure/angelbroking/order/v1/modifyOrder` | Modify pending |
| **Cancel Order** | POST | `/rest/secure/angelbroking/order/v1/cancelOrder` | Cancel pending |
| **Order Book** | GET | `/rest/secure/angelbroking/order/v1/getOrderBook` | All orders |
| **Positions** | GET | `/rest/secure/angelbroking/order/v1/getPosition` | Current positions |
| **Holdings** | GET | `/rest/secure/angelbroking/portfolio/v1/getHolding` | Delivery holdings |
| **Margins** | GET | `/rest/secure/angelbroking/user/v1/getRMS` | Risk mgmt/margins |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete request/response schemas.

## Symbol Format

### SmartAPI Symbol Format

SmartAPI uses a concatenated symbol format with instrument tokens from the instrument master file.

**Format Pattern:** `{UNDERLYING}{EXPIRY_DDMONYY}{STRIKE}{CE|PE}`

**Examples:**

| Instrument | SmartAPI Symbol | SmartAPI Token | Exchange |
|-----------|----------------|----------------|----------|
| NIFTY Index | `NIFTY` | `99926000` | `NSE` |
| NIFTY Future | `NIFTY25JANFUT` | varies | `NFO` |
| NIFTY 25000 CE | `NIFTY27FEB2525000CE` | varies | `NFO` |
| BANKNIFTY 52000 PE | `BANKNIFTY27FEB2552000PE` | varies | `NFO` |
| Reliance Equity | `RELIANCE-EQ` | `2885` | `NSE` |

### Instrument Master

- **URL:** `https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json`
- **Size:** ~50MB JSON file
- **Cache Duration:** 12 hours in AlgoChanakya
- **Format:** JSON array of objects with `token`, `symbol`, `name`, `expiry`, `strike`, `lotsize`, `instrumenttype`, `exch_seg`, `tick_size`

### Canonical Conversion (SmartAPI ↔ Kite)

AlgoChanakya uses Kite format as canonical. Conversion handled by `SymbolConverter`:

```python
from app.services.brokers.market_data.symbol_converter import SymbolConverter
converter = SymbolConverter()
canonical = converter.to_canonical("NIFTY27FEB2525000CE", "smartapi")
# → "NIFTY25FEB25000CE" (Kite canonical format)
```

See [symbol-format.md](./references/symbol-format.md) for complete conversion rules.

## WebSocket Protocol

### SmartAPI WebSocket V2 (Binary)

SmartAPI uses a **custom binary WebSocket protocol** (not JSON, not Protobuf).

**Connection:**
```
URL: wss://smartapisocket.angelone.in/smart-stream?clientCode={client_id}&feedToken={feed_token}&apiKey={api_key}
```

### Subscription Modes

| Mode | Code | Description | Data Size |
|------|------|-------------|-----------|
| LTP | `1` | Last traded price only | ~50 bytes |
| Quote | `2` | OHLC + volume + OI + best bid/ask | ~130 bytes |
| Snap Quote | `3` | Full depth (5 levels) + all fields | ~450 bytes |

### Exchange Segment Codes

| Exchange | Code | Used For |
|----------|------|----------|
| `nse_cm` | `1` | NSE Cash (Equity) |
| `nse_fo` | `2` | NSE F&O (Options, Futures) |
| `bse_cm` | `3` | BSE Cash |
| `bse_fo` | `4` | BSE F&O |
| `mcx_fo` | `5` | MCX Commodities |
| `ncx_fo` | `7` | NCX |
| `cde_fo` | `13` | CDE |

### Subscription Request (JSON)

```json
{
  "action": 1,
  "params": {
    "mode": 2,
    "tokenList": [
      { "exchangeType": 2, "tokens": ["99926000", "99926009"] }
    ]
  }
}
```

**Actions:** `1` = Subscribe, `2` = Unsubscribe, `3` = Heartbeat (every 30s)

### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max tokens per connection | **3000** |
| Max connections per client | **3** |
| Heartbeat interval | 30 seconds |
| Auto-reconnect | SDK handles |

See [websocket-protocol.md](./references/websocket-protocol.md) for complete binary parsing byte offsets.

## Rate Limits

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| REST API (general) | **1 request/second** | Per API key |
| Order placement | **10 orders/second** | Per client |
| Historical data | **1 request/second** | Shared with general |
| WebSocket | **Unlimited ticks** | After subscription |
| Instrument master | **1 per 12 hours** | Large file, cache it |

**AlgoChanakya Configuration:** `rate_limiter.py` sets `"smartapi": 1` (1 req/sec).

## Price Normalization (CRITICAL)

### PAISE vs RUPEES Rules

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** (quotes, LTP) | **RUPEES** | No conversion needed |
| **REST API** (historical) | **PAISE** | Divide by 100 |
| **WebSocket V2** (all modes) | **PAISE** | **Divide by 100** |
| **Instrument master** (strike) | **PAISE** | Divide by 100 |

**This is the #1 SmartAPI gotcha.** If prices look 100x too large, they're in paise.

```python
# CORRECT - WebSocket tick processing
ltp_rupees = Decimal(str(raw_ltp)) / 100

# WRONG - Missing paise conversion
ltp = raw_data.get('ltp', 0)  # BUG: still in paise!
```

**Codebase Reference:** See `smartapi_adapter.py` lines 319-326 (historical) and lines 522-526 (quotes) for paise→rupees conversion.

## AlgoChanakya Integration

### Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Market Data Adapter | **✅ Complete** | `backend/app/services/brokers/market_data/smartapi_adapter.py` |
| Order Execution Adapter | **🚧 Planned** | Not yet created |
| WebSocket Ticker | **✅ Legacy** | `backend/app/services/legacy/smartapi_ticker.py` |
| Auth Service | **✅ Complete** | `backend/app/services/legacy/smartapi_auth.py` |
| Historical Data | **✅ Complete** | `backend/app/services/legacy/smartapi_historical.py` |
| Instrument Lookup | **✅ Complete** | `backend/app/services/legacy/smartapi_instruments.py` |
| REST Market Data | **✅ Complete** | `backend/app/services/legacy/smartapi_market_data.py` |
| Symbol Converter | **✅ Complete** | `backend/app/services/brokers/market_data/symbol_converter.py` |
| Token Manager | **✅ Complete** | `backend/app/services/brokers/market_data/token_manager.py` |
| Rate Limiter | **✅ Complete** | `backend/app/services/brokers/market_data/rate_limiter.py` |

### Credential Storage

- **Table:** `smartapi_credentials` (encrypted with AES via `app.utils.encryption`)
- **Fields:** `client_id`, `password`, `totp_secret`, `api_key` (all encrypted)
- **Frontend:** `frontend/src/components/settings/SmartAPISettings.vue`
- **API:** `POST /api/smartapi/authenticate`, `GET/POST /api/smartapi/credentials`

### Key Integration Points

```python
# Get market data adapter
from app.services.brokers.market_data.factory import get_market_data_adapter
adapter = get_market_data_adapter("smartapi", credentials, db)

# Get quotes (prices in RUPEES)
quotes = await adapter.get_quote(["NIFTY25APR25000CE"])

# Get historical (prices in RUPEES after adapter conversion)
candles = await adapter.get_historical("NIFTY25APR25000CE", from_date, to_date, "5min")

# Token lookup
from app.services.brokers.market_data.token_manager import token_manager
token = await token_manager.get_broker_token("NIFTY25APR25000CE", "smartapi")
```

## Common Gotchas

1. **PAISE vs RUPEES** - WebSocket V2 and historical API return prices in PAISE. Always divide by 100. REST quote API returns RUPEES. This inconsistency is the #1 source of bugs.

2. **Instrument master is 50MB** - Download once, cache for 12 hours. Don't download on every request. AlgoChanakya uses `smartapi_instruments.py` singleton with 12h cache.

3. **Auto-TOTP timing** - TOTP codes are valid for 30 seconds. If system clock is off by >30s, auth fails. Use NTP-synced time. Login takes 20-25 seconds total.

4. **Exchange segment codes** - Must match token's exchange. Sending NSE token with `exchangeType: 2` (NFO) returns no data. Check instrument master's `exch_seg` field.

5. **Strike prices in paise** - Instrument master stores strikes in paise (e.g., `2500000` = ₹25000). Divide by 100.

6. **Feed token vs JWT token** - WebSocket uses `feedToken`, REST uses `jwtToken`. Mixing them up causes silent auth failure.

7. **Historical data date format** - SmartAPI expects `"YYYY-MM-DD HH:MM"` format. Missing time component causes errors.

8. **Rate limit is 1 req/sec** - Strictest among all brokers. Batch requests where possible. Use WebSocket for live data instead of polling REST.

9. **Instrument master format changes** - Angel One occasionally changes field names in the instrument master JSON. Always validate field existence.

10. **Index quotes don't need instrument master** - Use `get_index_quote()` for NIFTY/BANKNIFTY - no token lookup required. See `SmartAPIMarketDataAdapter.INDEX_SYMBOLS`.

## Error Codes Quick Reference

| Code | Message | Cause | Retryable |
|------|---------|-------|-----------|
| `AG8001` | Invalid Token | JWT expired or invalid | No - re-authenticate |
| `AG8002` | Invalid Client Code | Wrong client ID | No |
| `AG8003` | Invalid TOTP | Wrong/expired TOTP | Yes - regenerate TOTP |
| `AB1010` | Rate limit exceeded | Too many requests | Yes - wait 1 second |
| `AB1004` | Invalid exchange or token | Wrong exchange segment | No - fix mapping |
| `AB2000` | Order rejected | Various order issues | Depends on reason |
| `AB1012` | Session expired | Token expired | No - re-authenticate |
| `AB1000` | General error | Various | Depends |
| `AB8050` | Data not found | Invalid symbol/date range | No - fix parameters |
| `-1` | Connection timeout | Network issue | Yes - retry |

See [error-codes.md](./references/error-codes.md) for complete error code catalog.

## Related Skills

For cross-broker work, consult these complementary skills:

| Skill | When to Use |
|-------|-------------|
| `/kite-expert` | SmartAPI's default pair for order execution — compare auth flows, symbol formats, canonical conversion |
| `/upstox-expert` | Free data alternative to SmartAPI — compare Protobuf vs binary WS, rate limits (25/s vs 1/s) |
| `/trading-constants-manager` | When adding SmartAPI instrument tokens or lot sizes to centralized constants |
| `/auto-verify` | After any SmartAPI adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, CHANGELOG, broker abstraction docs |

**Cross-Broker Comparison:** See [comparison-matrix.md](../broker-shared/comparison-matrix.md) for pricing, rate limits, WebSocket capabilities, and symbol format differences across all 6 brokers.

## References

- [Authentication Flow](./references/auth-flow.md) - Complete auth sequence with request/response examples
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints with schemas
- [WebSocket Protocol](./references/websocket-protocol.md) - Binary format, byte offsets, parsing
- [Error Codes](./references/error-codes.md) - Complete error code reference
- [Symbol Format](./references/symbol-format.md) - Symbol construction and conversion rules
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
