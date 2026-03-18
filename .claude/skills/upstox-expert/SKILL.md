---
name: upstox-expert
description: Upstox expert — broker overview, products, pricing, Upstox API,
  and AlgoChanakya adapter guidance. Use for any Upstox question.
version: "3.1"
last_verified: "2026-03-18"
---

# Upstox Expert

Upstox is a leading Indian discount stockbroker, known for its modern trading platforms and developer-friendly API. It offers trading across NSE, BSE, MCX, and CDS segments with competitive flat-fee pricing. Upstox's trading API provides OAuth 2.0 authentication, Protobuf-based WebSocket (MarketDataFeedV3 v3), and SDKs in 6 languages. API access is **FREE (₹0)** — pricing changed from ₹499/month to free in 2025.

In AlgoChanakya, Upstox is used for both **market data** and **order execution** (all 3 adapters fully implemented with 1,883 lines of production code and 1,738 lines of tests). Key differentiators: **extended token** for long-lived read-only access, **Protocol Buffers** for efficient WebSocket messaging, and **real-time Greeks** via WebSocket (unique among Indian brokers). V3 API is current (v2 WebSocket discontinued Aug 22, 2025). Upstox is positioned in the platform failover chain for market data: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite.

## When to Use

- Any question about Upstox as a broker (products, pricing, account types)
- Implementing or debugging the Upstox market data, order, or ticker adapter
- Debugging Upstox API errors, OAuth flow, or auth issues (UDAPI100050 is the most common)
- Understanding Upstox instrument_key format (`NSE_FO|12345`)
- Working with Protobuf-based WebSocket (MarketDataFeedV3 v3)
- Using GTT Orders, Option Chain API, Webhooks, or Sandbox environment
- Comparing Upstox capabilities with other brokers

## When NOT to Use

- General broker abstraction questions (read docs/architecture/broker-abstraction.md instead)
- Cross-broker comparison (use broker-shared/comparison-matrix.md instead)
- AngelOne/Kite issues (use angelone-expert or zerodha-expert)
- Dhan/Fyers/Paytm issues (use their respective expert skills)

---

## 1. Upstox Overview

Upstox (RKSV Securities India Pvt. Ltd.) is a discount broker headquartered in Mumbai. It offers trading across NSE, BSE, MCX, and CDS segments. Key platforms include Upstox Pro (trading), Upstox API (developer platform), and a comprehensive mobile app.

**Account types:** Individual, Joint, HUF, Corporate, NRI.

See [upstox-overview.md](./references/upstox-overview.md) for complete company profile, products table, and differentiators.

## 2. Brokerage & Pricing

### Trading Charges

| Segment | Brokerage |
|---------|-----------|
| Equity Delivery | ₹0 (FREE) |
| Equity Intraday | 0.05% (max ₹20) |
| F&O (Options) | Flat ₹20/order |
| F&O (Futures) | Flat ₹20/order |
| Currency / Commodity | Flat ₹20/order |

**API brokerage (promotional):** ₹10/order via API (till Mar 2026; standard ₹20/order after).

**Other:** No demat charges for Upstox. Zero brokerage promotional period ended Aug 2024 — new users get 90 days free, then standard rates.

See [Pricing](https://upstox.com/pricing/) and [Brokerage Calculator](https://upstox.com/calculator/brokerage-calculator/).

### API Costs

| Product | Cost | Capability |
|---------|------|------------|
| **Upstox API** | **FREE (₹0)** | Full API: REST + WebSocket + market data + historical data |

**AlgoChanakya impact:** Upstox API is completely free — no monthly charges for any trading or data APIs. This makes Upstox an attractive option in the platform failover chain.

### Upstox Plans (Basic vs Plus)

| Feature | Basic | Plus |
|---------|-------|------|
| Brokerage (API) | ₹20/order | ₹30/order |
| WS Connections | 2 | 5 |
| D30 Market Depth | No | Yes (50 instruments/connection) |
| Price Alerts | 100 | 500 |
| Watchlists | 10x100 | 20x200 |

**Note:** Brokerage is higher on Plus (₹30 vs ₹20). Plus benefits are more WS connections, D30 depth, and more alerts/watchlists.

See [Upstox Plus page](https://upstox.com/plus/) for current pricing and benefits.

---

## 3. Upstox API

### API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://upstox.com/developer/api-documentation/open-api |
| **Community Forum** | https://community.upstox.com/ |
| **Dev API Forum** | https://community.upstox.com/c/developer-api/15 |
| **API Features & Pricing** | https://upstox.com/trading-api/ |
| **API Version** | v2 / v3 (dual — v3 for orders, historical, quotes, WebSocket) |
| **Python SDK** | `upstox-python-sdk` (`pip install upstox-python-sdk`) |
| **All SDKs** | Python, JavaScript, .NET, Java, C#, PHP |
| **Pricing** | **FREE (₹0)** for all trading + data APIs. ₹10/order brokerage via API (till Mar 2026). |
| **REST Base URL v2** | `https://api.upstox.com/v2` |
| **REST Base URL v3** | `https://api.upstox.com/v3` |
| **WebSocket URL** | Authorized URL via REST endpoint (v3 only — v2 discontinued Aug 2025) |
| **Auth Method** | OAuth 2.0 (authorization_code grant) |
| **Token Validity** | access_token: until ~6:30 AM next day; extended_token: 1 year |
| **Order Latency** | <45ms |
| **Uptime SLA** | 99.9% |

### Authentication Flow

Upstox uses standard **OAuth 2.0 authorization_code** flow with an optional **extended token** for long-lived access. **TOTP is supported** for automated login.

```
1. Redirect user → https://api.upstox.com/v2/login/authorization/dialog
   ?client_id={api_key}&redirect_uri={redirect_url}&response_type=code
2. User logs in at login.upstox.com:
   a. Enter phone number → Get OTP
   b. Enter OTP (or TOTP if enabled) → Enter 6-digit PIN
   c. Upstox redirects → {redirect_url}?code={authorization_code}
3. POST /v2/login/authorization/token with code, client_id, client_secret, redirect_uri, grant_type
4. Response: { access_token, extended_token (if requested) }
5. Use: Authorization: Bearer {access_token}
```

#### TOTP Support (Verified 2026-03-18)

Upstox supports Time-based OTP (TOTP) as an alternative to SMS OTP during login. This enables **fully automated login** without SMS dependency.

**Setup location:** account.upstox.com → Profile → sidebar → "Time-based OTP (TOTP)"

**Setup steps:**
1. Navigate to TOTP settings page
2. SMS OTP verification is required first
3. QR code + secret key are displayed
4. Click "Unable to scan? Click to copy the key" to get the base32 secret
5. Enter a generated TOTP code to confirm setup
6. **Warning:** Enabling TOTP logs out all active sessions

**Auto-login flow** (with TOTP secret saved): API Key + API Secret + Phone + TOTP Secret + PIN enables fully automated OAuth login via Playwright or similar browser automation. Use `pyotp` to generate TOTP codes:

```python
import pyotp
totp = pyotp.TOTP(totp_secret)
code = totp.now()  # 6-digit TOTP code
```

#### Token Types

| Token | Purpose | Validity | Notes |
|-------|---------|----------|-------|
| `access_token` | Full API access | Until ~6:30 AM next day | Standard OAuth token |
| `extended_token` | Read-only access | 1 year (renewable) | Long-lived, market data only |

**Extended Token:** Valid 1 year, read-only (market data, instruments, portfolio view). Cannot place/modify/cancel orders. Ideal for market data adapter — no daily re-auth.

See [auth-flow.md](./references/auth-flow.md) for complete request/response examples, TOTP setup, sandbox tokens, IP whitelisting, and Access Token Flow (Beta).

### Environment Configuration

Required `.env` keys for Upstox integration (use placeholder values, never commit real credentials):

```env
UPSTOX_API_KEY=your-api-key-uuid
UPSTOX_API_SECRET=your-api-secret
UPSTOX_REDIRECT_URL=http://localhost:8001/api/auth/upstox/callback
UPSTOX_LOGIN_PHONE=your-phone-number
UPSTOX_LOGIN_PIN=your-6-digit-pin
UPSTOX_USER_ID=your-user-id
UPSTOX_TOTP_SECRET=your-totp-base32-secret
```

| Key | Purpose | Where to Find |
|-----|---------|---------------|
| `UPSTOX_API_KEY` | OAuth client_id | My Apps → App Details |
| `UPSTOX_API_SECRET` | OAuth client_secret | My Apps → App Details |
| `UPSTOX_REDIRECT_URL` | OAuth redirect URI | Must match My Apps config exactly |
| `UPSTOX_LOGIN_PHONE` | Auto-login: phone number | Your registered phone |
| `UPSTOX_LOGIN_PIN` | Auto-login: 6-digit PIN | Set during account creation |
| `UPSTOX_USER_ID` | User identifier | Profile page or API profile response |
| `UPSTOX_TOTP_SECRET` | Auto-login: TOTP base32 secret | TOTP setup page (copy key) |

### Key Endpoints Quick Reference

| Category | Method | Endpoint | Notes |
|----------|--------|----------|-------|
| **Auth** | POST | `/v2/login/authorization/token` | Exchange auth code |
| **Profile** | GET | `/v2/user/profile` | User details |
| **Funds** | GET | `/v2/user/get-funds-and-margin` | Fund details (equity+commodity combined Jul 2025) |
| **Quote** | GET | `/v3/market-quote/quotes?instrument_key=` | Full quote (v3) |
| **LTP** | GET | `/v2/market-quote/ltp?instrument_key=` | LTP only |
| **OHLC** | GET | `/v2/market-quote/ohlc?instrument_key=` | OHLC data |
| **Historical** | GET | `/v3/historical-candle/{key}/{interval}/{to}/{from}` | OHLCV (v3, custom time units) |
| **Intraday** | GET | `/v2/historical-candle/intraday/{key}/{interval}` | Today's candles |
| **Instruments** | GET | `/v2/market-quote/instruments` | JSON format (CSV deprecated Apr 2024) |
| **Place Order v3** | POST | `/v3/order/place` | With order slicing + latency tracking |
| **Modify Order v3** | PUT | `/v3/order/modify` | Preferred over v2 |
| **Cancel Order v3** | DELETE | `/v3/order/cancel` | Preferred over v2 |
| **Orders** | GET | `/v2/order/retrieve-all` | All orders |
| **Multi-Order Place** | POST | `/v2/order/multi/place` | Place multiple orders |
| **Multi-Order Cancel** | DELETE | `/v2/order/multi/cancel` | Cancel all open |
| **Multi-Order Exit** | POST | `/v2/order/multi/exit` | Exit all positions |
| **GTT Place** | POST | `/v3/order/gtt/place` | GTT order (v3) |
| **GTT Modify** | PUT | `/v3/order/gtt/modify` | Modify GTT |
| **GTT Cancel** | DELETE | `/v3/order/gtt/cancel` | Cancel GTT |
| **GTT Details** | GET | `/v3/order/gtt/details` | Get GTT list |
| **Option Contracts** | GET | `/v2/option/contract` | Option contracts for expiry |
| **Option Chain** | GET | `/v2/option/chain` | Full chain with Greeks + PoP |
| **Positions** | GET | `/v2/portfolio/short-term-positions` | Positions |
| **Holdings** | GET | `/v2/portfolio/long-term-holdings` | Holdings |
| **Charges** | GET | `/v2/charges/brokerage` | Brokerage calculator |
| **Trade P&L** | GET | `/v2/trade/profit-loss/metadata` | P&L metadata |
| **Trade P&L Report** | GET | `/v2/trade/profit-loss/report` | Full P&L report |
| **WS Auth** | GET | `/v2/feed/market-data-feed/authorize` | Get authorized WS URL (v3) |
| **Portfolio WS Auth** | GET | `/v2/feed/portfolio-stream-feed/authorize` | Portfolio stream WS |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete schemas.

### Symbol Format

#### instrument_key Format

`{EXCHANGE}_{SEGMENT}|{instrument_token_or_name}`

| Instrument | instrument_key | Notes |
|-----------|---------------|-------|
| NIFTY 50 Index | `NSE_INDEX\|Nifty 50` | Indices use name |
| NIFTY 25000 CE | `NSE_FO\|12345` | F&O uses token |
| Reliance Equity | `NSE_EQ\|2885` | Equity uses token |
| MCX Gold | `MCX_FO\|34567` | MCX token |

**Segments:** `NSE_EQ`, `NSE_FO`, `NSE_INDEX`, `BSE_EQ`, `BSE_FO`, `BSE_INDEX`, `MCX_FO`

**Note:** Instrument master is JSON only (CSV deprecated Apr 2024). Instruments carry a `weekly` boolean field for weekly options.

See [symbol-format.md](./references/symbol-format.md) for complete format details and conversion utilities.

### WebSocket Protocol (Protobuf)

#### MarketDataFeedV3 (V3 ONLY — V2 discontinued Aug 22, 2025)

Connection flow:
1. `GET /v2/feed/market-data-feed/authorize` → returns authorized WS URL
2. Connect to URL (binary Protobuf)
3. Subscribe with instrument keys and mode

#### Subscription Modes

| Mode | Description | Data Included |
|------|-------------|---------------|
| `ltpc` | LTP + Change | LTP, close, change, change% |
| `full` | Full quote | OHLC, volume, OI, depth, bid/ask |
| `option_greeks` | Greeks + quote | Full + delta, gamma, theta, vega, IV |

#### Connection Limits

| Plan | Max WS Connections | D30 Depth | Notes |
|------|--------------------|-----------|-------|
| Basic | 2 | No | Up to ~1500 instruments |
| Plus | 5 | Yes (50/connection) | Plus subscription required |

#### Portfolio Stream WebSocket

Stream portfolio updates (positions, holdings) in real-time:
- Auth: `GET /v2/feed/portfolio-stream-feed/authorize`
- Events: position updates, holding updates, order updates
- **Known issue:** NXDOMAIN errors reported by community — retry with backoff

See [websocket-protocol.md](./references/websocket-protocol.md) for Protobuf schema, parsing, and V2→V3 migration.

### Rate Limits

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| REST API (general) | **50 req/sec, 500/min, 2000/30min** | Per access_token |
| Multi-Order APIs | **4 req/sec, 40/min, 160/30min** | Stricter limit |
| Order placement | **50 orders/second** | Per user |
| Historical data | **50 req/sec** | Same as general |
| WebSocket | Unlimited ticks | After subscription |

**AlgoChanakya Config:** Update `rate_limiter.py` `"upstox"` from `25` → `50` to match current limits.

### Price Normalization

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| REST API (all) | **RUPEES** | No conversion |
| WebSocket (all modes) | **RUPEES** | No conversion |
| Historical data | **RUPEES** | No conversion |

**Upstox always returns prices in RUPEES.** No paise conversion needed (unlike SmartAPI and Kite WS).

### GTT Orders (Good Till Triggered)

- **4 endpoints** (v3 API): Place, Modify, Cancel, Get Details
- **Types:** SINGLE (1 rule) or MULTIPLE (2–3 rules, OCO-style)
- **Rule types:** ENTRY, TARGET, STOPLOSS with ABOVE/BELOW/IMMEDIATE triggers
- **Products:** I (Intraday/MIS), D (Delivery/CNC), MTF
- **Trailing Stop Loss** (Beta, Jun 2025): Adjusts stop dynamically as price moves
- **Error codes:** UDAPI1126–UDAPI1151

See [gtt-orders.md](./references/gtt-orders.md) for complete schemas, examples, and all error codes.

### Option Chain API

- `GET /v2/option/contract` — get option contracts for a given underlying + expiry
- `GET /v2/option/chain` — full put/call option chain with real-time data + Greeks
- **FREE** — confirmed working 2026-03-18: 133 strikes with full Greeks, no charges
- **Greeks available:** delta, gamma, theta, vega, IV, PoP (Probability of Profit)
- **Market data:** ltp, volume, OI, prev_OI, bid/ask
- **MCX:** Option Chain not available for MCX instruments
- **Note:** Upstox is one of only 2 brokers (with AngelOne) offering free option chain data with Greeks

See [option-chain.md](./references/option-chain.md) for complete response schemas.

### Webhook

- **Setup:** Configured in My Apps dashboard (no code, no auth required on receiver)
- **Events:** Order Updates (default), GTT Updates (opt-in)
- **Requirements:** Receiver must return 2XX within timeout; POST only
- **Payload format:** snake_case fields (lowercase deprecated)

See [webhook.md](./references/webhook.md) for payload formats and event types.

### Sandbox Environment

- **Available since:** Jan 2025
- **App creation:** Create a "Sandbox" app in Upstox developer portal
- **Token:** 30-day token generated from portal (no OAuth flow needed)
- **Scope:** Order placement/modification/cancellation APIs only (no market data)
- **URL:** Same base URL, sandbox app credentials
- **Use for:** Testing order flows without real money

### MCP Integration (Claude Desktop / VS Code)

- **MCP URL:** `https://mcp.upstox.com/mcp`
- **Scope:** Read-only (portfolio, market data, positions, holdings)
- **Setup:** Add to Claude Desktop config or VS Code MCP settings
- **Cannot:** Place orders or modify account settings via MCP

### Error Codes Quick Reference

| HTTP Status | Error Code | Cause | Retryable |
|-------------|-----------|-------|-----------|
| `401` | `UDAPI100010` | Invalid token | No — re-auth |
| `401` | `UDAPI100011` | Token expired | No — re-auth |
| `401/400` | `UDAPI100050` | Invalid instrument key OR auth/order failure | Check both |
| `403` | IP not whitelisted | Server IP not in app settings | No — whitelist IP |
| `429` | `UDAPI100030` | Rate limit exceeded | Yes — backoff |
| `400` | `UDAPI1126` | GTT: Invalid GTT order | No — fix params |
| `400` | `UDAPI1151` | GTT: Trigger already fired | No |
| `500` | `UDAPI100040` | Internal server error | Yes — retry |

See [error-codes.md](./references/error-codes.md) for complete error catalog including all GTT codes.

---

## 4. AlgoChanakya Integration

### Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Market Data Adapter | **Implemented** | `backend/app/services/brokers/market_data/upstox_adapter.py` (568 lines) |
| Order Execution Adapter | **Implemented** | `backend/app/services/brokers/upstox_order_adapter.py` (494 lines) |
| Ticker (WebSocket) Adapter | **Implemented** | `backend/app/services/brokers/market_data/ticker/adapters/upstox.py` (821 lines) |
| Auth Route | **Implemented** | `backend/app/api/routes/upstox_auth.py` (190 lines) |
| Frontend Settings | **Implemented** | `frontend/src/components/settings/UpstoxSettings.vue` |
| Tests | **Complete** | `test_upstox_ticker_adapter.py`, `test_upstox_market_data_adapter.py` (1,738 lines) |
| GTT Orders | **Not Yet** | Adapter supports standard orders only |
| Webhook Integration | **Not Yet** | Could enhance order status tracking |

### Current Integration Pattern

```python
# Market data via adapter (implemented)
from app.services.brokers.market_data.factory import get_market_data_adapter
adapter = get_market_data_adapter("upstox", credentials, db)
quote = await adapter.get_quote(["NIFTY2522725000CE"])  # Returns UnifiedQuote

# Order execution via adapter (implemented)
from app.services.brokers.upstox_order_adapter import UpstoxOrderAdapter
adapter = UpstoxOrderAdapter(access_token=token)
order_id = await adapter.place_order(order_params)
```

---

## 5. Common Gotchas

1. **API is FREE** — Old pricing ₹499/month no longer applies. Free for all trading + data APIs since 2025.

2. **V2 WebSocket is discontinued** — As of Aug 22, 2025, `market-data-feed/v2` is offline. Only `v3` works. All Upstox docs now show v3.

3. **IP whitelisting required** — If you get `403 Forbidden` on order placement, check that your server IP is whitelisted in the My Apps dashboard. Most common production issue.

4. **UDAPI100050** — Has dual meaning: (a) invalid instrument key format, AND (b) auth/order placement failure after re-login (community-reported). Re-authenticate if this appears on a valid instrument.

5. **CSV instruments deprecated** — Apr 2024, the CSV instrument master download was removed. Use `GET /v2/market-quote/instruments` (JSON) only.

6. **Fund API changed Jul 2025** — `equity` object now contains both equity and commodity funds combined. Old code expecting separate `commodity` object will break.

7. **Portfolio WS NXDOMAIN** — Community reports host resolution failures on `portfolio-stream-feed`. Implement retry with exponential backoff.

8. **Extended token is read-only** — Cannot place orders with extended token. Need full access_token for trading.

9. **WS URL from REST** — Must call REST to get authorized WebSocket URL. Cannot hardcode WS URL (expires with token).

10. **Protobuf dependency** — WebSocket requires `protobuf` package and .proto schemas. Different from JSON or raw binary used by other brokers.

11. **Historical data descending** — Returns candles newest first. Other brokers return ascending. Reverse before processing.

12. **Index instrument_key** — Indices use name string (`NSE_INDEX|Nifty 50`) not numeric token. Don't mix with F&O format.

13. **Pipe separator URL-encoding** — `|` must be URL-encoded as `%7C` in query parameters.

14. **Zero brokerage ended Aug 2024** — New users get 90 days free brokerage, then standard rates apply.

15. **Brokerage higher on Plus** — ₹30/order on Plus vs ₹20/order on Basic. Plus has other benefits (5 WS, D30) but higher per-order cost.

---

## 6. Related Skills

| Skill | When to Use |
|-------|-------------|
| `/angelone-expert` | Compare SmartAPI vs Upstox — paise handling, auto-TOTP vs OAuth, WS binary formats |
| `/zerodha-expert` | Order execution reference — Kite adapter is the model |
| `/dhan-expert` | Compare unique WS features — Dhan has 200-depth, Upstox has Greeks via WS |
| `/auto-verify` | After any Upstox adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, comparison matrix |

**Cross-Broker Comparison:** See [comparison-matrix.md](../broker-shared/comparison-matrix.md) for pricing, rate limits, WebSocket capabilities, and symbol format differences across all 6 brokers.

---

## 7. Maintenance & Auto-Improvement

### Freshness Tracking

| Reference File | Last Verified | Check Frequency |
|---|---|---|
| SKILL.md | 2026-03-18 | Quarterly |
| upstox-overview.md | 2026-03-04 | Quarterly |
| endpoints-catalog.md | 2026-02-25 | Monthly |
| auth-flow.md | 2026-02-25 | Quarterly |
| error-codes.md | 2026-02-25 | Monthly |
| websocket-protocol.md | 2026-02-25 | Monthly |
| symbol-format.md | 2026-02-25 | Quarterly |
| gtt-orders.md | 2026-02-25 | Quarterly |
| option-chain.md | 2026-02-25 | Quarterly |
| webhook.md | 2026-02-25 | Quarterly |
| maintenance-log.md | 2026-02-25 | Monthly |

### Auto-Update Trigger Rules

1. **Error-driven update**: If this skill is invoked 3+ times with FAILED/UNKNOWN outcome for the same error_type (tracked via `post_skill_learning.py` hook → `knowledge.db`), `reflect deep` mode should propose a skill update targeting the failing area.

2. **Staleness alert**: If `last_verified` date for any reference file exceeds 90 days, the `health-check` skill should flag it. On next invocation, check the [Announcements page](https://upstox.com/developer/api-documentation/announcements/) for API changes.

3. **Quarterly review**: Next scheduled review: **June 2026**. Check:
   - [Upstox API Announcements](https://upstox.com/developer/api-documentation/announcements/) for new/deprecated endpoints
   - [Developer API Forum](https://community.upstox.com/c/developer-api/15) for recurring issues
   - [Community Home](https://community.upstox.com/) for trending pain points
   - Upstox Python SDK (`pip show upstox-python-sdk`) for version bumps
   - Rate limit changes, pricing changes, new features

4. **Community monitoring**: When debugging Upstox issues, check the [Developer API Forum](https://community.upstox.com/c/developer-api/15) for known issues and workarounds before deep-diving.

### Version Changelog

| Version | Date | Changes |
|---|---|---|
| 3.1 | 2026-03-18 | Added TOTP support (setup location, auto-login flow with pyotp), .env configuration section with all 7 keys, OAuth login flow details (Playwright-tested), confirmed free option chain with Greeks (133 strikes). Updated freshness dates. |
| 3.0 | 2026-03-04 | Restructured: Upstox overview + pricing sections added, API content reorganized as subsection. New `upstox-overview.md` reference file. File renamed from `skill.md` to `SKILL.md`. All existing API content preserved. |
| 2.0 | 2026-02-25 | Comprehensive overhaul: pricing FREE, v3 API, GTT/Option Chain/Webhook/Sandbox/MCP, implementation status updated to Implemented, rate limits corrected (50/sec), auto-improvement system added, 3 new reference files, 8 external URLs |
| 1.0 | 2026-02-16 | Initial creation with broker skills batch |

### Knowledge Base Integration

This skill integrates with the AlgoChanakya learning system:
- **Automatic**: `post_skill_learning.py` hook fires after every invocation → captures outcome to `knowledge.db` and `failure-index.json`
- **On failure**: Error patterns are fingerprinted and stored. Fix strategies are ranked by success rate.
- **Self-modification**: `reflect deep` mode can propose edits to this skill (with user approval) when gap analysis detects recurring failures.
- **Cross-reference**: Upstox-specific error patterns in `knowledge.db` inform `fix-loop` and `test-fixer` skills.

---

## References

- [Upstox Overview](./references/upstox-overview.md) - Company profile, products, pricing, exchanges, differentiators
- [Authentication Flow](./references/auth-flow.md) - OAuth 2.0 flow, extended token, IP whitelisting, sandbox
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints with schemas (v2 + v3)
- [WebSocket Protocol](./references/websocket-protocol.md) - Protobuf-based MarketDataFeedV3 v3, Portfolio WS
- [Error Codes](./references/error-codes.md) - Complete error catalog including GTT codes
- [Symbol Format](./references/symbol-format.md) - instrument_key format and conversion
- [GTT Orders](./references/gtt-orders.md) - Good Till Triggered order reference
- [Option Chain](./references/option-chain.md) - Option Chain API with Greeks + PoP
- [Webhook](./references/webhook.md) - Webhook setup and payload formats
- [Maintenance Log](./references/maintenance-log.md) - API change tracker, community issues
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
- [Upstox Announcements](https://upstox.com/developer/api-documentation/announcements/) - Official API change log
