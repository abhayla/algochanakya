---
name: angelone-expert
description: Angel One expert — broker overview, products, pricing, SmartAPI,
  and AlgoChanakya adapter guidance. Use for any Angel One or SmartAPI question.
version: "3.0"
last_verified: "2026-03-04"
---

# Angel One Expert

Angel One (formerly Angel Broking) is one of India's largest retail stockbrokers (25M+ clients), founded in 1996. It offers flat ₹20/order pricing and free equity delivery. Angel One's trading API is called **SmartAPI** — a FREE REST + binary WebSocket API with auto-TOTP authentication, option chain with Greeks, and an order update WebSocket.

In AlgoChanakya, Angel One/SmartAPI is the **platform-default market data provider** (first in failover chain), offering FREE real-time WebSocket prices, REST quotes, and historical OHLCV data. All AlgoChanakya adapters for SmartAPI are **fully implemented**. SmartAPI also provides order execution via `AngelOneAdapter`. AlgoChanakya achieves ₹0/month total API cost by using SmartAPI for market data and Kite Connect (free Personal API) for order execution.

## When to Use

- Any question about Angel One as a broker (products, pricing, account types)
- Implementing or modifying the SmartAPI market data adapter
- Debugging SmartAPI API errors or authentication issues (auto-TOTP, token expiry, static IP 403)
- Understanding SmartAPI symbol/token format or instrument master mapping
- Diagnosing **PAISE vs RUPEES** price issues (WebSocket returns paise, REST returns rupees)
- Comparing SmartAPI capabilities with other brokers
- Auditing code that calls SmartAPI API for correctness
- Writing tests that mock SmartAPI API responses
- Questions about GTT orders, option chain API, or the order update WebSocket

## When NOT to Use

- General broker abstraction questions (read docs/architecture/broker-abstraction.md instead)
- Cross-broker comparison (use broker-shared/comparison-matrix.md instead)
- Kite Connect issues (use zerodha-expert)
- Upstox/Dhan/Fyers/Paytm issues (use their respective expert skills)

---

## 1. Angel One Overview

Angel One Limited (SEBI: INZ000161534) is headquartered in Mumbai. It offers trading across NSE, BSE, MCX, and NCDEX segments. Key platforms include Angel One App (trading), SmartAPI (developer API), ARQ Prime (AI advisory), and Smart Money (education).

**Account types:** Individual, Joint, HUF, Corporate, NRI (NRE/NRO).

See [angelone-overview.md](./references/angelone-overview.md) for complete company profile, products table, and differentiators.

## 2. Brokerage & Pricing

### Trading Charges

| Segment | Brokerage |
|---------|-----------|
| Equity Delivery | ₹0 (FREE) |
| Equity Intraday | ₹20/order or 0.25% (lower) |
| F&O (Options) | ₹20/order (flat) |
| F&O (Futures) | ₹20/order or 0.25% (lower) |
| Currency / Commodity | ₹20/order or 0.25% (lower) |

**Other:** Account opening FREE, AMC ₹240/year (first year free), DP charges ₹20/scrip on sell.

### API Costs

| Product | Cost | Capability |
|---------|------|------------|
| **SmartAPI** | **FREE** | Full API: REST + WebSocket + market data + historical data + option chain with Greeks |

**AlgoChanakya impact:** SmartAPI is the platform-default market data provider — ₹0/month for live ticks, OHLC, historical data, and option chain. This is the primary reason AlgoChanakya uses SmartAPI as the default.

See [angelone-overview.md](./references/angelone-overview.md) for detailed charges and exchange support.

---

## 3. SmartAPI

### API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://smartapi.angelbroking.com/docs/ |
| **API Version** | v1 (REST), V2 (WebSocket) |
| **Python SDK** | `smartapi-python` v1.5.5 (`pip install smartapi-python`) |
| **Pricing** | **FREE** (market data + orders) |
| **REST Base URL** | `https://apiconnect.angelbroking.com` |
| **Market Data WebSocket** | `wss://smartapisocket.angelone.in/smart-stream` |
| **Order Update WebSocket** | `wss://tns.angelone.in/smart-order-update` |
| **Auth Method** | Client ID + PIN + TOTP (auto-generated via pyotp) |
| **Token Validity** | JWT: ~24h, Feed Token: ~24h, Refresh Token: 15 days |
| **Static IP Required** | Yes (since Aug 2025) — register in Angel One dashboard |

### Authentication Flow

SmartAPI uses a 3-token system with auto-TOTP for hands-free authentication. **Since August 2025, static IP registration is also required.**

#### Step-by-Step Authentication

```
1. Register your server's public IP in Angel One dashboard (one-time setup)
2. Generate TOTP → pyotp.TOTP(stored_secret).now()
3. POST /rest/auth/angelbroking/user/v1/loginByPassword
   Body: { clientcode, password, totp }
4. Response: { jwtToken, refreshToken, feedToken }
5. Use jwtToken for REST APIs (Authorization: Bearer {jwt})
6. Use feedToken for WebSocket authentication
7. On expiry → POST /rest/auth/angelbroking/jwt/v1/generateTokens with refreshToken
```

#### Token Types

| Token | Purpose | Validity | Header |
|-------|---------|----------|--------|
| `jwtToken` | REST API authentication | ~24 hours | `Authorization: Bearer {jwt}` |
| `feedToken` | WebSocket authentication | ~24 hours | Query param or WS header |
| `refreshToken` | Refresh expired JWT | 15 days | Body of refresh endpoint |

#### Auto-TOTP in AlgoChanakya

```python
# AlgoChanakya stores TOTP secret encrypted in smartapi_credentials table
import pyotp
totp = pyotp.TOTP(stored_totp_secret).now()  # 6-digit code, no manual entry
```

#### Credential Storage

| Field | Storage | Encryption |
|-------|---------|------------|
| `client_id` | `smartapi_credentials` table | Encrypted (AES) |
| `password` | `smartapi_credentials` table | Encrypted (AES) |
| `totp_secret` | `smartapi_credentials` table | Encrypted (AES) |
| `api_key` | `backend/.env` (`ANGEL_API_KEY`) | Environment variable |

**Codebase:** `backend/app/services/legacy/smartapi_auth.py` handles authentication with auto-TOTP.

See [auth-flow.md](./references/auth-flow.md) for complete request/response examples, static IP setup, and error scenarios.

### Key Endpoints Quick Reference

| Category | Method | Endpoint | Notes |
|----------|--------|----------|-------|
| **Auth** | POST | `/rest/auth/angelbroking/user/v1/loginByPassword` | Returns 3 tokens |
| **Auth** | POST | `/rest/auth/angelbroking/jwt/v1/generateTokens` | Refresh JWT |
| **Auth** | POST | `/rest/auth/angelbroking/user/v1/logout` | Invalidate tokens |
| **Profile** | GET | `/rest/secure/angelbroking/user/v1/getProfile` | User details |
| **Quote** | POST | `/rest/secure/angelbroking/market/v1/quote/` | Full quote (RUPEES) |
| **LTP** | POST | `/rest/secure/angelbroking/market/v1/quote/` | mode=LTP (RUPEES) |
| **Historical** | POST | `/rest/secure/angelbroking/apiconnect/hist/v2/getCandleData` | OHLCV candles |
| **Option Chain** | GET | `/rest/secure/angelbroking/marketData/v1/optionChain` | Strikes + Greeks |
| **Search** | POST | `/rest/secure/angelbroking/order/v1/searchScrip` | Search instruments |
| **Place Order** | POST | `/rest/secure/angelbroking/order/v1/placeOrder` | Place order |
| **Modify Order** | POST | `/rest/secure/angelbroking/order/v1/modifyOrder` | Modify pending |
| **Cancel Order** | POST | `/rest/secure/angelbroking/order/v1/cancelOrder` | Cancel pending |
| **Order Book** | GET | `/rest/secure/angelbroking/order/v1/getOrderBook` | All orders |
| **Positions** | GET | `/rest/secure/angelbroking/order/v1/getPosition` | Current positions |
| **Holdings** | GET | `/rest/secure/angelbroking/portfolio/v1/getHolding` | Delivery holdings |
| **Margins** | GET | `/rest/secure/angelbroking/user/v1/getRMS` | Risk mgmt/margins |
| **GTT Create** | POST | `/rest/secure/angelbroking/gtt/v1/createRule` | Create GTT rule |
| **GTT List** | POST | `/rest/secure/angelbroking/gtt/v1/ruleList` | List GTT rules |
| **GTT Modify** | POST | `/rest/secure/angelbroking/gtt/v1/modifyRule` | Modify GTT rule |
| **GTT Cancel** | POST | `/rest/secure/angelbroking/gtt/v1/cancelRule` | Cancel GTT rule |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete request/response schemas.

### Symbol Format

#### SmartAPI Symbol Format

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

#### Instrument Master

- **URL:** `https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json`
- **Size:** ~50MB JSON file
- **Cache Duration:** 12 hours in AlgoChanakya
- **Format:** JSON array with `token`, `symbol`, `name`, `expiry`, `strike`, `lotsize`, `instrumenttype`, `exch_seg`, `tick_size`

#### Canonical Conversion (SmartAPI ↔ Kite)

AlgoChanakya uses Kite format as canonical. Conversion handled by `SymbolConverter`:

```python
from app.services.brokers.market_data.symbol_converter import SymbolConverter
converter = SymbolConverter()
canonical = converter.to_canonical("NIFTY27FEB2525000CE", "smartapi")
# → "NIFTY25FEB25000CE" (Kite canonical format)
```

See [symbol-format.md](./references/symbol-format.md) for complete conversion rules.

### WebSocket Protocol

#### Market Data WebSocket (Binary)

SmartAPI uses a **custom binary WebSocket protocol** (not JSON, not Protobuf).

**Connection:**
```
URL: wss://smartapisocket.angelone.in/smart-stream?clientCode={client_id}&feedToken={feed_token}&apiKey={api_key}
```

#### Subscription Modes

| Mode | Code | Description | Data Size |
|------|------|-------------|-----------|
| LTP | `1` | Last traded price only | ~50 bytes |
| Quote | `2` | OHLC + volume + OI + best bid/ask | ~130 bytes |
| Snap Quote | `3` | Full depth (5 levels) + all fields | ~450 bytes |

#### Exchange Segment Codes

| Exchange | Code | Used For |
|----------|------|----------|
| `nse_cm` | `1` | NSE Cash (Equity) |
| `nse_fo` | `2` | NSE F&O (Options, Futures) |
| `bse_cm` | `3` | BSE Cash |
| `bse_fo` | `4` | BSE F&O |
| `mcx_fo` | `5` | MCX Commodities |
| `ncx_fo` | `7` | NCX |
| `cde_fo` | `13` | CDE |

#### Subscription Request (JSON)

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

#### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max tokens per connection | **3000** |
| Max connections per client | **3** |
| Heartbeat interval | 30 seconds |
| Auto-reconnect | SDK handles |

See [websocket-protocol.md](./references/websocket-protocol.md) for complete binary parsing byte offsets.

### Rate Limits

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| REST API (general) | **1 request/second** | Per API key |
| Order placement | **20 orders/second** | Per client (increased from 10 in Feb 2025) |
| Historical data | **1 request/second** | Shared with general |
| WebSocket | **Unlimited ticks** | After subscription |
| Instrument master | **1 per 12 hours** | Large file, cache it |

**AlgoChanakya Configuration:** `rate_limiter.py` sets `"smartapi": 1` (1 req/sec). The order rate limit of 20/sec is enforced by the broker side; AlgoChanakya's adapter does not currently need per-order rate limiting.

### GTT Orders

SmartAPI supports GTT (Good Till Triggered) orders — place orders that execute when a price condition is met. Rules valid for up to 365 days.

**Quick reference:**

| Action | Endpoint |
|--------|----------|
| Create rule | `POST /rest/secure/angelbroking/gtt/v1/createRule` |
| List rules | `POST /rest/secure/angelbroking/gtt/v1/ruleList` |
| Modify rule | `POST /rest/secure/angelbroking/gtt/v1/modifyRule` |
| Cancel rule | `POST /rest/secure/angelbroking/gtt/v1/cancelRule` |

**AlgoChanakya status:** GTT is NOT yet implemented in AlgoChanakya's SmartAPI order adapter.

See [gtt-orders.md](./references/gtt-orders.md) for complete request/response schemas and field reference.

### Option Chain

SmartAPI provides an Option Chain API returning all strikes for an index with market data and Greeks.

**Endpoint:** `GET /rest/secure/angelbroking/marketData/v1/optionChain`

**Parameters:** `name` (e.g., "NIFTY"), `expirydate` (e.g., "27FEB2025")

**Returns:** Array of strikes with CE/PE data including LTP, volume, OI, IV, delta, gamma, theta, vega.

**Supported underlyings:** NIFTY, BANKNIFTY, FINNIFTY, SENSEX, MIDCPNIFTY

See [option-chain.md](./references/option-chain.md) for complete response schema and Greeks reference.

### Webhooks

SmartAPI does **NOT support HTTP webhooks**. There is no "POST to your URL" push model.

Instead, use:
1. **Order Update WebSocket** (`wss://tns.angelone.in/smart-order-update`) — real-time order status stream
2. **REST polling** — `GET /rest/secure/angelbroking/order/v1/getOrderBook` at intervals

See [webhook.md](./references/webhook.md) for both approaches.

### Order Update WebSocket

A **separate** real-time WebSocket for order status notifications (not market data):

```
URL: wss://tns.angelone.in/smart-order-update
Auth: feedToken from login response
```

This WebSocket streams order fills, rejections, and modifications in real-time. AlgoChanakya currently polls REST for order status — the order update WebSocket is a future enhancement.

See [webhook.md](./references/webhook.md) for connection details, message format, and polling alternative.

### Sandbox / Paper Trading

Angel One provides **paper trading** (virtual trading environment) accessible via the SmartAPI:
- Enable paper trading mode from the Angel One developer dashboard
- Uses the same endpoints but with a separate paper trading account
- Useful for testing order placement flows without real money
- Not all endpoints are available in paper trading mode (market data is live)

### Price Normalization (CRITICAL)

#### PAISE vs RUPEES Rules

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** (quotes, LTP) | **RUPEES** | No conversion needed |
| **REST API** (historical) | **PAISE** | Divide by 100 |
| **WebSocket V2** (all modes) | **PAISE** | **Divide by 100** |
| **Instrument master** (strike) | **PAISE** | Divide by 100 |
| **Option Chain API** | **RUPEES** | No conversion needed |

**This is the #1 SmartAPI gotcha.** If prices look 100x too large, they're in paise.

```python
# CORRECT - WebSocket tick processing
ltp_rupees = Decimal(str(raw_ltp)) / 100

# WRONG - Missing paise conversion
ltp = raw_data.get('ltp', 0)  # BUG: still in paise!
```

**Codebase Reference:** See `smartapi_adapter.py` lines 319-326 (historical) and lines 522-526 (quotes) for paise→rupees conversion.

### Error Codes Quick Reference

| Code | Message | Cause | Retryable |
|------|---------|-------|-----------|
| `AG8001` | Invalid Token | JWT expired or invalid | No - re-authenticate |
| `AG8002` | Invalid Client Code | Wrong client ID | No |
| `AG8003` | Invalid TOTP | Wrong/expired TOTP | Yes - regenerate TOTP |
| `AG8008` | IP Not Registered | Static IP not in dashboard | No - register IP |
| `AB1010` | Rate limit exceeded | Too many requests | Yes - wait 1 second |
| `AB1004` | Invalid exchange or token | Wrong exchange segment | No - fix mapping |
| `AB2000` | Order rejected | Various order issues | Depends on reason |
| `AB1012` | Session expired | Token expired | No - re-authenticate |
| `AB1000` | General error | Various | Depends |
| `AB8050` | Data not found | Invalid symbol/date range | No - fix parameters |
| `-1` | Connection timeout | Network issue | Yes - retry |
| HTTP 403 | Forbidden | IP not registered (Aug 2025+) | No - register IP |

See [error-codes.md](./references/error-codes.md) for complete error code catalog.

---

## 4. AlgoChanakya Integration

### Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Market Data Adapter | **Implemented** | `backend/app/services/brokers/market_data/smartapi_adapter.py` (584 lines) |
| Order Execution Adapter | **Implemented** | `backend/app/services/brokers/angelone_adapter.py` (428 lines) |
| Ticker (WebSocket) Adapter | **Implemented** | `backend/app/services/brokers/market_data/ticker/adapters/smartapi.py` (353 lines) |
| Auth Service | **Implemented** | `backend/app/services/legacy/smartapi_auth.py` |
| Historical Data | **Implemented** | `backend/app/services/legacy/smartapi_historical.py` |
| Instrument Lookup | **Implemented** | `backend/app/services/legacy/smartapi_instruments.py` |
| REST Market Data | **Implemented** | `backend/app/services/legacy/smartapi_market_data.py` |
| Auth Route | **Implemented** | `backend/app/api/routes/smartapi.py` (410 lines) |
| Frontend Settings | **Implemented** | `frontend/src/components/settings/SmartAPISettings.vue` |
| Symbol Converter | **Implemented** | `backend/app/services/brokers/market_data/symbol_converter.py` |
| Token Manager | **Implemented** | `backend/app/services/brokers/market_data/token_manager.py` |
| Tests | **Complete** | `test_smartapi_ticker_adapter.py` (510 lines) |
| GTT Orders | **Not implemented** | Target: `backend/app/services/brokers/angelone_adapter.py` |
| Order Update WebSocket | **Not implemented** | Target: `backend/app/services/brokers/angelone_adapter.py` |

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

### Broker Name Mapping

**Important gotcha:** Database stores `'angelone'` but adapter uses `'smartapi'`:

```python
# BrokerConnection.broker_name = "angelone" (database)
# Market data adapter key = "smartapi" (factory)
# Use name mapping utility when converting
```

---

## 5. Common Gotchas

1. **PAISE vs RUPEES** - WebSocket V2 and historical API return prices in PAISE. Always divide by 100. REST quote API returns RUPEES. Option Chain API returns RUPEES. This inconsistency is the #1 source of bugs.

2. **Static IP registration required (since Aug 2025)** - You must register your server's public IPv4 address in the Angel One developer dashboard before API calls will work. Up to 5 IPv4 addresses per API key. A 403 Forbidden response almost always means the IP is not registered. See [auth-flow.md](./references/auth-flow.md#static-ip-registration) for setup steps.

3. **3 separate API keys** - Angel One uses 3 API keys in `backend/.env`: `ANGEL_API_KEY` (market data), `ANGEL_HIST_API_KEY` (historical data), `ANGEL_TRADE_API_KEY` (order execution). Using the wrong key returns `AG8001 Invalid Token`.

4. **Instrument master is 50MB** - Download once, cache for 12 hours. Don't download on every request. AlgoChanakya uses `smartapi_instruments.py` singleton with 12h cache.

5. **Auto-TOTP timing** - TOTP codes are valid for 30 seconds. If system clock is off by >30s, auth fails. Use NTP-synced time. Login takes 20-25 seconds total.

6. **Exchange segment codes** - Must match token's exchange. Sending NSE token with `exchangeType: 2` (NFO) returns no data. Check instrument master's `exch_seg` field.

7. **Strike prices in paise** - Instrument master stores strikes in paise (e.g., `2500000` = ₹25000). Divide by 100.

8. **Feed token vs JWT token** - WebSocket uses `feedToken`, REST uses `jwtToken`. Mixing them up causes silent auth failure.

9. **Historical data date format** - SmartAPI expects `"YYYY-MM-DD HH:MM"` format. Missing time component causes errors.

10. **Rate limit is 1 req/sec (REST)** - Strictest among all brokers. Batch requests where possible. Use WebSocket for live data instead of polling REST. Order placement is now 20/sec (as of Feb 2025, up from 10/sec).

11. **Instrument master format changes** - Angel One occasionally changes field names in the instrument master JSON. Always validate field existence.

12. **Index quotes don't need instrument master** - Use `get_index_quote()` for NIFTY/BANKNIFTY - no token lookup required. See `SmartAPIMarketDataAdapter.INDEX_SYMBOLS`.

---

## 6. Related Skills

| Skill | When to Use |
|-------|-------------|
| `/zerodha-expert` | Angel One's default pair for order execution — compare auth flows, symbol formats, canonical conversion |
| `/upstox-expert` | Free data alternative to SmartAPI — compare Protobuf vs binary WS, rate limits (50/s vs 1/s) |
| `/trading-constants-manager` | When adding SmartAPI instrument tokens or lot sizes to centralized constants |
| `/auto-verify` | After any SmartAPI adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, CHANGELOG, broker abstraction docs |

**Cross-Broker Comparison:** See [comparison-matrix.md](../broker-shared/comparison-matrix.md) for pricing, rate limits, WebSocket capabilities, and symbol format differences across all 6 brokers.

---

## 7. Maintenance & Auto-Improvement

### Freshness Tracking

| Reference File | Last Verified | Check Frequency |
|---|---|---|
| SKILL.md | 2026-03-04 | Quarterly |
| angelone-overview.md | 2026-03-04 | Quarterly |
| endpoints-catalog.md | 2026-02-25 | Quarterly |
| auth-flow.md | 2026-02-25 | Quarterly |
| error-codes.md | 2026-02-25 | Quarterly |
| websocket-protocol.md | 2026-02-25 | Quarterly |
| symbol-format.md | 2026-02-25 | Quarterly |
| gtt-orders.md | 2026-02-25 | Quarterly |
| option-chain.md | 2026-02-25 | Quarterly |
| webhook.md | 2026-02-25 | Quarterly |
| maintenance-log.md | 2026-02-25 | Quarterly |

### Auto-Update Trigger Rules

1. **Error-driven update**: If this skill is invoked 3+ times with FAILED/UNKNOWN outcome for the same error_type (tracked via `post_skill_learning.py` hook → `knowledge.db`), `reflect deep` mode should propose a skill update.
2. **Staleness alert**: If `last_verified` exceeds 90 days, check https://smartapi.angelbroking.com/docs/ for API changes.
3. **Quarterly review**: Next scheduled review: **June 2026**.

### Version Changelog

| Version | Date | Changes |
|---|---|---|
| 3.0 | 2026-03-04 | Renamed from `smartapi-expert` to `angelone-expert`. Restructured: Angel One overview + pricing sections added, SmartAPI content reorganized as subsection. New `angelone-overview.md` reference file. All existing API content preserved. Added 3-key API gotcha. |
| 2.5 | 2026-02-25 | Static IP registration (Aug 2025), order rate limit 20/sec, order update WebSocket, GTT orders section, option chain section, webhook section, sandbox section, AG8008 error code, 4 new reference files, maintenance log |
| 2.0 | 2026-02-25 | Implementation status corrected (all adapters Implemented), AngelOneAdapter added, ticker adapter row added, maintenance section added |
| 1.0 | 2026-02-16 | Initial creation as `smartapi-expert` |

---

## References

- [Angel One Overview](./references/angelone-overview.md) - Company profile, products, pricing, exchanges, differentiators
- [Authentication Flow](./references/auth-flow.md) - Complete auth sequence, static IP setup, request/response examples
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints with schemas
- [WebSocket Protocol](./references/websocket-protocol.md) - Binary format, byte offsets, parsing
- [Error Codes](./references/error-codes.md) - Complete error code reference
- [Symbol Format](./references/symbol-format.md) - Symbol construction and conversion rules
- [GTT Orders](./references/gtt-orders.md) - Good Till Triggered order reference
- [Option Chain](./references/option-chain.md) - Option chain API with Greeks
- [Webhook / Order Update WebSocket](./references/webhook.md) - Order update WebSocket and polling fallback
- [Maintenance Log](./references/maintenance-log.md) - API change tracker and known issues
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
