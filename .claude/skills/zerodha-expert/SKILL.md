---
name: zerodha-expert
description: Zerodha expert — broker overview, products, pricing, Kite Connect API,
  and AlgoChanakya adapter guidance. Use for any Zerodha or Kite Connect question.
version: "3.0"
last_verified: "2026-03-03"
---

# Zerodha Expert

Zerodha is India's largest retail stockbroker (14M+ active clients), founded in 2010 by Nithin and Nikhil Kamath. It pioneered discount broking in India with flat ₹20/order pricing and free equity delivery. Zerodha's trading API is called **Kite Connect** — a well-documented REST + binary WebSocket API costing ₹500/month (or FREE via Personal API for orders only).

In AlgoChanakya, Zerodha/Kite Connect is used for **order execution** (fully implemented). Kite symbol format IS the canonical format used throughout the platform — no symbol conversion needed. Market data comes from SmartAPI by default (free), with Kite Connect as the last resort in the platform failover chain.

## When to Use

- Any question about Zerodha as a broker (products, pricing, account types)
- Implementing or modifying the Kite order execution adapter
- Debugging Kite API errors, OAuth flow, or access token issues
- Understanding Kite symbol format (canonical format for AlgoChanakya)
- Working with KiteTicker WebSocket binary protocol
- Comparing Zerodha/Kite capabilities with other brokers
- Auditing code that calls Kite API for correctness
- Writing tests that mock Kite API responses
- GTT (Good Till Triggered) order questions

## When NOT to Use

- General broker abstraction questions (read docs/architecture/broker-abstraction.md instead)
- Cross-broker comparison (use broker-shared/comparison-matrix.md instead)
- SmartAPI issues (use angelone-expert)
- Upstox/Dhan/Fyers/Paytm issues (use their respective expert skills)

---

## 1. Zerodha Overview

Zerodha Broking Limited (SEBI: INZ000031633) is headquartered in Bengaluru. It offers trading across NSE, BSE, MCX, and CDS segments. Key platforms include Kite (trading), Console (back-office), Coin (mutual funds), and Varsity (education).

**Account types:** Individual, Joint, HUF, Corporate, NRI (NRE/NRO).

See [zerodha-overview.md](./references/zerodha-overview.md) for complete company profile, products table, and differentiators.

## 2. Brokerage & Pricing

### Trading Charges

| Segment | Brokerage |
|---------|-----------|
| Equity Delivery | ₹0 (FREE) |
| Equity Intraday | ₹20/order or 0.03% (lower) |
| F&O (Options) | ₹20/order (flat) |
| F&O (Futures) | ₹20/order or 0.03% (lower) |
| Currency / Commodity | ₹20/order or 0.03% (lower) |

**Other:** Account opening FREE, AMC ₹300/year, DP charges ₹15.93/scrip on sell.

### API Costs

| Product | Cost | Capability |
|---------|------|------------|
| **Kite Connect** | ₹500/month | Full API: REST + WebSocket + market data + historical data |
| **Personal API** | FREE | Order execution only — NO market data |

**AlgoChanakya impact:** Since SmartAPI provides free market data, AlgoChanakya uses Kite only for order execution. Users with Personal API (free) can execute orders; Kite Connect (₹500/month) is only needed if using Kite as a data source.

See [zerodha-overview.md](./references/zerodha-overview.md) for detailed charges and exchange support.

### Kite Connect App Setup

For step-by-step instructions on creating a Kite Connect app, getting API keys, and configuring `.env`, see **[kite-app-setup.md](./references/kite-app-setup.md)**. Key points:

- Use **Personal (Free)** type for OAuth login — no paid plan needed
- Register redirect URL: `http://localhost:8001/api/auth/zerodha/callback` (dev)
- App is restricted to a single Zerodha Client ID
- SEBI static IP requirement coming April 2026

---

## 3. Kite Connect API

### API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://kite.trade/docs/connect/v3/ |
| **API Version** | v3 |
| **Python SDK** | `kiteconnect` v5.0.1 (`pip install kiteconnect`) |
| **Pricing** | ₹500/month (Connect: market data + historical data included), FREE (Personal API: orders only, no market data) |
| **REST Base URL** | `https://api.kite.trade` |
| **WebSocket URL** | `wss://ws.kite.trade` |
| **Auth Method** | OAuth 2.0 redirect flow (request_token + api_secret) |
| **Token Validity** | access_token: ~24h (until 6 AM next day), no auto-refresh |
| **Sandbox** | Yes — see [Sandbox Environment](#sandbox-environment) |

### Authentication Flow

Kite uses a standard **OAuth 2.0 redirect flow**. No auto-refresh - user must re-login daily.

#### Step-by-Step Authentication

```
1. Redirect user → https://kite.zerodha.com/connect/login?v=3&api_key={api_key}
2. User logs in on Zerodha's website
3. Zerodha redirects → {redirect_url}?request_token={token}&action=login&status=success
4. POST /session/token with api_key, request_token, checksum (SHA-256 of api_key + request_token + api_secret)
5. Response: { access_token, public_token, user_id }
6. Use access_token for all API calls: Authorization: token {api_key}:{access_token}
```

#### Token Types

| Token | Purpose | Validity | Notes |
|-------|---------|----------|-------|
| `request_token` | Exchange for access_token | Single use, ~5 min | From OAuth redirect |
| `access_token` | REST + WebSocket auth | Until ~6 AM next day | Cannot be refreshed |
| `public_token` | Public data only | Same as access_token | Limited endpoints |

#### Auth Header Format

```
Authorization: token {api_key}:{access_token}
```

**Example:** `Authorization: token abc123:xyz789`

#### No Auto-Refresh

Unlike SmartAPI, Kite has **no refresh token**. When access_token expires (~6 AM), the user must complete the OAuth flow again. This is why AlgoChanakya uses SmartAPI (with auto-TOTP) as the default market data source.

See [auth-flow.md](./references/auth-flow.md) for complete request/response examples including sandbox setup.

### Key Endpoints Quick Reference

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
| **Historical** | GET | `/instruments/historical/{token}/{interval}` | OHLCV candles (max 60 days/request for minute) |
| **Instruments** | GET | `/instruments` | All instruments CSV |
| **Instruments** | GET | `/instruments/{exchange}` | Exchange instruments |
| **Place Order** | POST | `/orders/{variety}` | Place order |
| **Modify Order** | PUT | `/orders/{variety}/{order_id}` | Modify pending |
| **Cancel Order** | DELETE | `/orders/{variety}/{order_id}` | Cancel pending |
| **Orders** | GET | `/orders` | All orders |
| **Trades** | GET | `/trades` | All trades |
| **Positions** | GET | `/portfolio/positions` | Positions |
| **Holdings** | GET | `/portfolio/holdings` | Holdings |
| **GTT Create** | POST | `/gtt/triggers` | Create GTT order |
| **GTT List** | GET | `/gtt/triggers` | List all GTTs |
| **GTT Get** | GET | `/gtt/triggers/{id}` | Get specific GTT |
| **GTT Modify** | PUT | `/gtt/triggers/{id}` | Modify GTT |
| **GTT Delete** | DELETE | `/gtt/triggers/{id}` | Delete GTT |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete schemas.

### Symbol Format (CANONICAL)

#### Kite IS the Canonical Format

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

#### Weekly vs Monthly Expiry Format

| Type | Format | Example |
|------|--------|---------|
| **Weekly** | `{UNDERLYING}{YY}{M}{DD}{STRIKE}{CE\|PE}` | `NIFTY2522725000CE` (Feb 27, 2025) |
| **Monthly** | `{UNDERLYING}{YY}{MON}{STRIKE}{CE\|PE}` | `NIFTY25FEB25000CE` (Feb monthly) |

**Month codes (weekly):** `1`=Jan, `2`=Feb, ..., `9`=Sep, `O`=Oct, `N`=Nov, `D`=Dec

#### Key Index Tokens

| Index | Token | Exchange |
|-------|-------|----------|
| NIFTY 50 | `256265` | NSE |
| NIFTY BANK | `260105` | NSE |
| NIFTY FIN SERVICE | `257801` | NSE |
| SENSEX | `265` | BSE |

See [symbol-format.md](./references/symbol-format.md) for complete format details.

### WebSocket Protocol (KiteTicker)

#### Binary Tick Format

KiteTicker sends **binary messages** with 3 modes:

| Mode | Bytes per Tick | Fields |
|------|---------------|--------|
| **LTP** | 8 | Token + LTP |
| **Quote** | 44 | Token + OHLC + Volume + OI + Bid/Ask |
| **Full** | 184 | Quote + 5-level depth + timestamps |

#### Prices in PAISE (int32)

All prices are **int32 in paise**. Divide by 100 for rupees.

```python
ltp_paise = struct.unpack('>I', data[4:8])[0]
ltp_rupees = ltp_paise / 100.0  # 15025 → 150.25
```

#### Connection URL

```
wss://ws.kite.trade?api_key={api_key}&access_token={access_token}
```

#### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max tokens per connection | **3000** |
| Max connections | **3** |
| Tick rate | Real-time (exchange feed) |

See [websocket-protocol.md](./references/websocket-protocol.md) for byte offsets and parsing.

### Rate Limits

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| General API | **10 requests/second** | Standard tier |
| Historical data | **10 requests/second** | Shared with general |
| Order placement | **10 orders/second** | Per user |
| Quote API | **1 request/second** | Use WebSocket for live data |
| Instruments dump | **Once per day** | ~80MB CSV, cache it |

**AlgoChanakya Configuration:** `rate_limiter.py` currently sets `"kite": 3` — this is **INCORRECT** and should be updated to `"kite": 10`. See [maintenance-log.md](./references/maintenance-log.md) for details.

### GTT Orders

Kite supports **Good Till Triggered (GTT)** orders — orders that execute automatically when a price condition is met. GTTs persist for up to 1 year.

| GTT Type | Code | Triggers | Description |
|----------|------|----------|-------------|
| Single | `single` | 1 | Fires when price crosses one level |
| Two-Leg OCO | `two-leg` | 2 | Target + stop-loss, one fires and cancels the other |

GTT is **not yet implemented** in AlgoChanakya's Kite adapter. Standard orders are fully supported.

See [gtt-orders.md](./references/gtt-orders.md) for complete GTT reference including request/response examples and status values.

### No Webhook Support

Kite Connect does **NOT support HTTP webhooks** for order or trade notifications. There is no mechanism to register a URL that Zerodha will call when orders execute.

**Alternatives:**
- Use KiteTicker WebSocket for live market data (not order updates)
- Poll `/orders` endpoint to check order status
- AlgoChanakya's AutoPilot module handles order polling internally

See [webhook.md](./references/webhook.md) for details and comparison with other brokers.

### No Dedicated Option Chain API

Kite Connect does **NOT** have a dedicated option chain endpoint. To build an option chain, you must query individual strike quotes in batches using the `/quote` endpoint (max 500 instruments per request).

**Greeks are NOT available** from Kite's quote API. AlgoChanakya uses SmartAPI for option chain data (which provides delta, gamma, theta, vega, IV).

See [option-chain.md](./references/option-chain.md) for the batched quote approach and performance considerations.

### Sandbox Environment

Kite Connect provides a **test/sandbox environment** for development:

- **Sandbox docs:** https://kite.trade/docs/connect/v3/#sandbox
- Sandbox allows testing API calls without real trades
- Use sandbox API key/secret from the Kite developer console
- Sandbox base URL differs from production — check auth-flow.md for setup

See [auth-flow.md](./references/auth-flow.md) for sandbox configuration details.

### Price Normalization

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** (quotes, LTP) | **RUPEES** (float) | No conversion |
| **REST API** (historical) | **RUPEES** (float) | No conversion |
| **WebSocket** (all modes) | **PAISE** (int32) | Divide by 100 |

**Note:** Unlike SmartAPI where REST historical returns paise, Kite REST always returns rupees. Only WebSocket uses paise.

### Error Codes Quick Reference

| HTTP Status | Exception Class | Cause | Retryable |
|-------------|----------------|-------|-----------|
| `400` | `InputException` | Invalid parameters | No |
| `403` | `TokenException` | Invalid/expired token | No - re-auth |
| `429` | `NetworkException` | Rate limit exceeded | Yes - backoff |
| `500` | `GeneralException` | Server error | Yes - retry |
| `502` | `NetworkException` | Gateway error | Yes - retry |
| `503` | `NetworkException` | Service unavailable | Yes - retry |

See [error-codes.md](./references/error-codes.md) for complete error catalog including GTT-specific errors.

---

## 4. AlgoChanakya Integration

### Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Order Execution Adapter | **Implemented** | `backend/app/services/brokers/kite_adapter.py` |
| Market Data Adapter | **Implemented** | `backend/app/services/brokers/market_data/kite_adapter.py` (422 lines) |
| Ticker (WebSocket) Adapter | **Implemented** | `backend/app/services/brokers/market_data/ticker/adapters/kite.py` (313 lines) |
| Order Service | **Legacy** | `backend/app/services/legacy/kite_orders.py` |
| OAuth Callback | **Implemented** | `backend/app/api/routes/auth.py` |
| Frontend Settings | **Implemented** | `frontend/src/components/settings/KiteSettings.vue` |
| Factory Registration | **Implemented** | `backend/app/services/brokers/factory.py` |
| Tests | **Complete** | `test_kite_ticker_adapter.py` (598 lines) |

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

---

## 5. Common Gotchas

1. **No auto-refresh** - Access token expires ~6 AM. No refresh mechanism. User must OAuth again. This is why SmartAPI is default for market data.

2. **Personal API has no market data** - Free Personal API (since March 2025) provides order execution only. For live quotes/historical data, need ₹500/month Connect subscription.

3. **Historical data now included** - Since Feb 2025, historical data (up to 10 years intraday) is bundled with ₹500/month subscription, no separate charge.

4. **Symbol format IS canonical** - Don't convert Kite symbols. They ARE the canonical format. `SymbolConverter.to_canonical(symbol, "kite")` is identity.

5. **Auth header format** - `token api_key:access_token` (not `Bearer`). Common mistake: using Bearer prefix.

6. **Checksum for session** - `POST /session/token` requires SHA-256 of `api_key + request_token + api_secret`. Missing or wrong checksum = silent failure.

7. **Instrument CSV is 80MB** - Download once, cache for 24h. Don't download on every request. BSE instruments are in a separate CSV.

8. **WebSocket prices in paise** - int32 paise. REST prices in rupees (float). Don't mix them.

9. **Order variety in URL** - `/orders/regular`, `/orders/amo`, `/orders/co`, `/orders/iceberg`. Variety is part of the URL, not the body.

10. **Exchange prefix in quotes** - Quote endpoint needs `i=NFO:NIFTY2522725000CE` format. Missing exchange prefix = 400 error.

11. **Rate limit is 10/sec** - The standard rate limit is 10 req/sec (NOT 3/sec as previously documented). `rate_limiter.py` setting `"kite": 3` is incorrect and should be updated to 10.

12. **Historical data: max 60 days per request for minute data** - When fetching `minute` interval, each request can span a maximum of 60 days. For longer ranges, make multiple requests.

13. **No webhooks** - Kite has no push webhook mechanism. Use polling or KiteTicker WebSocket for real-time updates.

14. **No option chain API** - No dedicated endpoint. Must batch-query individual strikes via `/quote`. Greeks are not available.

15. **₹500/month subscription** - Kite Connect requires a paid subscription for third-party apps. Personal Kite API is free but limited to orders only.

---

## 6. Related Skills

| Skill | When to Use |
|-------|-------------|
| `/angelone-expert` | Zerodha's default pair for market data — compare paise handling, auto-TOTP vs OAuth, WS binary formats |
| `/upstox-expert` | Both fully implemented — compare Protobuf vs binary WS, extended token vs OAuth |
| `/trading-constants-manager` | Kite symbol format IS canonical — verify constants match when adding new instruments |
| `/auto-verify` | After any Kite adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, CHANGELOG, broker abstraction docs |

**Cross-Broker Comparison:** See [comparison-matrix.md](../broker-shared/comparison-matrix.md) for pricing, rate limits, WebSocket capabilities, and symbol format differences across all 6 brokers.

---

## 7. Maintenance & Auto-Improvement

### Freshness Tracking

| Reference File | Last Verified | Check Frequency |
|---|---|---|
| SKILL.md | 2026-03-03 | Quarterly |
| zerodha-overview.md | 2026-03-03 | Quarterly |
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
2. **Staleness alert**: If `last_verified` exceeds 90 days, check https://kite.trade/docs/connect/v3/ for API changes.
3. **Quarterly review**: Next scheduled review: **June 2026**.

### Version Changelog

| Version | Date | Changes |
|---|---|---|
| 3.0 | 2026-03-04 | Renamed from `kite-expert` to `zerodha-expert`. Restructured: Zerodha overview + pricing sections added, Kite Connect API content reorganized as subsection. New `zerodha-overview.md` reference file. All existing API content preserved. |
| 2.5 | 2026-02-25 | CRITICAL rate limit fix (3/sec → 10/sec), added GTT section + reference, added No Webhook section + reference, added No Option Chain API section + reference, added Sandbox section, updated SDK version to v5.0.1, added historical data 60-day limit note, expanded Maintenance section to all 9 reference files |
| 2.0 | 2026-02-25 | Implementation status corrected (ticker adapter added, all adapters Implemented), updated Related Skills (removed outdated "next to implement" note), maintenance section added |
| 1.0 | 2026-02-16 | Initial creation as `kite-expert` |

---

## References

- [Zerodha Overview](./references/zerodha-overview.md) - Company profile, products, pricing, exchanges, differentiators
- [Authentication Flow](./references/auth-flow.md) - OAuth flow with request/response examples, sandbox setup
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints with schemas
- [WebSocket Protocol](./references/websocket-protocol.md) - KiteTicker binary format and parsing
- [Error Codes](./references/error-codes.md) - Complete error code reference
- [Symbol Format](./references/symbol-format.md) - Canonical format specification
- [GTT Orders](./references/gtt-orders.md) - Good Till Triggered orders reference
- [Option Chain](./references/option-chain.md) - Building option chains without dedicated API
- [Webhook](./references/webhook.md) - No webhook support; alternatives documented
- [Maintenance Log](./references/maintenance-log.md) - API change tracker and review history
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
