---
name: paytm-expert
description: >
  Paytm Money broker expert — API, adapter, and AlgoChanakya integration guidance.
  INVOKE when: talking about Paytm, Paytm Money, discussing Paytm data source,
  Paytm OAuth, Paytm token, Paytm market data; editing paytm_adapter, paytm.py ticker,
  paytm_auth; debugging paytm 401, public_access_token, paytm WebSocket disconnect,
  paytm 3-token system, paytm developer console broken, NOT_REFRESHABLE Paytm.
version: "3.2"
last_verified: "2026-04-13"
---

# Paytm Money Expert

Paytm Money is an investment platform operated by **One97 Communications** (the parent company of Paytm), launched in **2019** and registered with **SEBI** as a stockbroker. As the newest entrant among AlgoChanakya's 6 supported brokers, it is the **least mature API** — expect limited documentation, occasional breaking changes without deprecation notices, and less community support compared to established players like Zerodha or AngelOne.

Despite its maturity limitations, Paytm Money offers a **FREE** trading API with a unique **3 JWT token** system (access_token, public_access_token for WebSocket, read_access_token for read-only), covering market data, order execution, and WebSocket streaming. All 3 AlgoChanakya adapters (market data, order execution, ticker/WebSocket) are **fully implemented**. Key differentiator: three separate token types and the `public_access_token` specifically for WebSocket authentication.

**BSE F&O (2025):** Paytm Money added BSE F&O instruments in 2025. Previously NSE-only F&O; BSE options now available.

## When to Use

- Any question about Paytm Money as a broker (products, pricing, account types)
- Implementing or debugging the Paytm Money market data, order, or ticker adapter
- Debugging Paytm API errors or authentication issues
- Understanding Paytm's 3-token system (access, public_access, read_access)
- Working with Paytm WebSocket (public_access_token auth)
- Implementing or researching GTT orders for Paytm
- Fetching Paytm option chain data (Heckyl-powered Greeks)
- Comparing Paytm capabilities with other brokers
- Auditing code that calls Paytm API for correctness

## When NOT to Use

- General broker abstraction questions (read docs/architecture/broker-abstraction.md instead)
- Cross-broker comparison (use broker-shared/comparison-matrix.md instead)
- AngelOne/Kite/Upstox/Dhan/Fyers issues (use their respective expert skills, e.g., `angelone-expert`)

## 1. Paytm Money Overview

Paytm Money is a **fintech-backed** investment platform, a subsidiary of **One97 Communications Limited** — the company behind Paytm, India's largest digital payments platform. Launched in 2019, Paytm Money initially focused on mutual fund investments before expanding into equity, F&O, and IPO.

### Account Types

- **Individual** — Standard demat + trading account
- **Joint** — Not widely supported via API
- **NRI** — Limited availability

### Maturity Warning

Paytm Money API is the **least mature** among Indian broker APIs. Key concerns:
- **pyPMClient SDK** last updated Jul 2024, limited maintenance
- Sporadic documentation updates
- Breaking changes without deprecation notices
- Less community support and fewer third-party integrations

See [paytm-overview.md](./references/paytm-overview.md) for full company profile, products, exchanges, and differentiators.

## 2. Brokerage & Pricing

### Trading Charges

| Segment | Brokerage | Notes |
|---------|-----------|-------|
| **Equity Delivery** | FREE | Zero brokerage |
| **Equity Intraday** | Rs 10 per executed order | Flat fee |
| **F&O (Options)** | Rs 10 per executed order | Flat fee |
| **F&O (Futures)** | Rs 10 per executed order | Flat fee |

*Standard statutory charges (STT, exchange charges, GST, SEBI fees, stamp duty) apply on top.*

### API Costs

| Item | Cost |
|------|------|
| **API Access** | **FREE** |
| **Market Data** | **FREE** (included) |
| **Historical Data** | **FREE** (included) |
| **WebSocket Ticks** | **FREE** (included) |

### Exchange Support

| Exchange | Equity | F&O | Currency | Commodity (MCX) |
|----------|--------|-----|----------|-----------------|
| **NSE** | Yes | Yes | No | No |
| **BSE** | Yes | Yes (2025) | No | No |
| **MCX** | -- | -- | -- | **No** |

**Note:** Paytm Money does **not** support MCX (commodity) or currency derivatives trading.

## 3. Paytm Money API

### API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://developer.paytmmoney.com/docs/ |
| **API Version** | v1 |
| **Python SDK** | `pyPMClient` (`pip install pyPMClient`) — last updated Jul 2024, limited maintenance |
| **Pricing** | **FREE** (market data + orders) |
| **REST Base URL** | `https://developer.paytmmoney.com` |
| **WebSocket URL** | `wss://developer-ws.paytmmoney.com/broadcast/user/v1/data` |
| **Auth Method** | OAuth 2.0 (authorization_code) |
| **Token Validity** | access_token: ~24h, public_access_token: ~24h |

### Authentication Flow

Paytm Money uses OAuth 2.0 with **3 different JWT token types**.

#### Step-by-Step Authentication

```
1. Redirect user → https://login.paytmmoney.com/merchant-login
   ?apiKey={api_key}&state={state}
2. User logs in on Paytm website
3. Paytm redirects → {redirect_url}?requestToken={token}&state={state}
4. POST /accounts/v2/gettoken with api_key, api_secret_key, request_token
5. Response: { access_token, public_access_token, read_access_token }
6. Use appropriate token per endpoint
```

#### Token Types (3 JWTs)

| Token | Purpose | Validity | Used For |
|-------|---------|----------|----------|
| `access_token` | Full API access | ~24 hours | Orders, positions, holdings, GTT |
| `public_access_token` | WebSocket only | ~24 hours | **WebSocket authentication** |
| `read_access_token` | Read-only REST | ~24 hours | Market data, quotes, instruments, option chain |

#### Auth Header

```
x-jwt-token: {access_token|read_access_token}
```

**Note:** Header is `x-jwt-token` (not `Authorization: Bearer`). Custom header format.

See [auth-flow.md](./references/auth-flow.md) for complete request/response examples.

### Key Endpoints Quick Reference

| Category | Method | Endpoint | Token Type |
|----------|--------|----------|------------|
| **Auth** | POST | `/accounts/v2/gettoken` | None (api_key/secret) |
| **Profile** | GET | `/accounts/v1/user/details` | access_token |
| **Margins** | GET | `/accounts/v1/funds/summary` | access_token |
| **Quote** | GET | `/data/v1/price/live` | read_access_token |
| **OHLC** | GET | `/data/v1/price/ohlc` | read_access_token |
| **Historical** | GET | `/data/v1/price/historical` | read_access_token |
| **Option Chain** | GET | `/data/v1/option/chain` | read_access_token |
| **Place Order** | POST | `/orders/v1/place/regular` | access_token |
| **Modify Order** | PUT | `/orders/v1/modify/regular` | access_token |
| **Cancel Order** | DELETE | `/orders/v1/cancel/regular` | access_token |
| **Orders** | GET | `/orders/v1/order-book` | access_token |
| **Positions** | GET | `/orders/v1/position` | access_token |
| **Holdings** | GET | `/holdings/v1/get-user-holdings` | access_token |
| **GTT Create** | POST | `/api/create-gtt` | access_token |
| **GTT Get** | GET | `/api/get-gtt` | access_token |
| **Instruments** | Download | Script master CSV | read_access_token |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete schemas.

### Symbol Format

#### Paytm Instrument IDs

Paytm uses a combination of `security_id` (numeric) and exchange-specific identifiers.

**Examples:**

| Instrument | security_id | exchange | Symbol |
|-----------|-------------|----------|--------|
| NIFTY 50 | `13` | `NSE` | `NIFTY` |
| NIFTY 25000 CE | `12345` | `NSE` | `NIFTY2522725000CE` |
| Reliance | `2885` | `NSE` | `RELIANCE` |

#### Canonical Conversion

Conversion requires instrument master lookup:

```python
from app.services.brokers.market_data.token_manager import token_manager

# Paytm security_id → Canonical
canonical = await token_manager.get_canonical_symbol(12345, "paytm")

# Canonical → Paytm security_id
paytm_id = await token_manager.get_broker_token("NIFTY2522725000CE", "paytm")
```

See [symbol-format.md](./references/symbol-format.md) for instrument master details.

### WebSocket Protocol

#### Connection with public_access_token

```python
# WebSocket uses public_access_token (NOT access_token)
ws_url = f"wss://developer-ws.paytmmoney.com/broadcast/user/v1/data?x_jwt_token={public_access_token}"
```

#### Subscription

```json
{
  "method": "subscribe",
  "preferences": [
    {
      "actionType": 1,
      "modeType": 2,
      "scripType": 1,
      "exchangeType": 1,
      "scripId": "12345"
    }
  ]
}
```

#### Modes

| Mode | Code | Description |
|------|------|-------------|
| LTP | `1` | Last price only |
| Full | `2` | OHLC + volume + OI + depth |

#### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max instruments | **200** per connection |
| Max connections | **1** per token |
| Auth token | **public_access_token** (specific) |
| Message format | JSON |

See [websocket-protocol.md](./references/websocket-protocol.md) for detailed protocol.

### Rate Limits

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| REST API (general) | **10 requests/second** | Per access_token |
| Order placement | **10 orders/second** | Per user |
| Historical data | **5 requests/second** | Separate limit |
| WebSocket | **Unlimited ticks** | After subscription |

**AlgoChanakya Configuration:** `rate_limiter.py` sets `"paytm": 10` (10 req/sec).

### Price Normalization

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** | **RUPEES** | No conversion |
| **WebSocket** | **RUPEES** | No conversion |
| **Historical** | **RUPEES** | No conversion |

Paytm returns all prices in RUPEES. No paise conversion needed.

### GTT Orders

Paytm Money provides GTT (Good Till Triggered) order functionality. The endpoint is available but documentation is sparse.

**Status: NOT YET IMPLEMENTED in AlgoChanakya's Paytm adapter.**

- Endpoint: `POST /api/create-gtt`
- Requires `access_token` (NOT `read_access_token`)
- Valid for up to 365 days
- Two types: Single trigger and Two-leg (OCO target + stop-loss)

See [gtt-orders.md](./references/gtt-orders.md) for endpoint details, request format, and implementation cautions.

### Option Chain

Paytm Money provides option chain data including Greeks, powered by **Heckyl Technologies** as the underlying data vendor.

**Status: NOT YET IMPLEMENTED in AlgoChanakya (uses SmartAPI for option chain).**

- Endpoint: `GET /data/v1/option/chain`
- Includes delta, gamma, theta, vega, IV
- BSE F&O option chain available since 2025 (SENSEX, BANKEX)
- Use `read_access_token`

See [option-chain.md](./references/option-chain.md) for endpoint details and response format.

### Webhooks / Order Updates

**Paytm Money does NOT support webhooks or order update push notifications.**

There is no HTTP webhook and no order update WebSocket. The only mechanism for tracking order status is **REST polling**.

AlgoChanakya handles this via AutoPilot polling at 2-second intervals for active orders.

See [webhook.md](./references/webhook.md) for polling implementation and broker comparison table.

### Error Codes Quick Reference

| HTTP Status | Cause | Retryable |
|-------------|-------|-----------|
| `400` | Bad request / invalid params | No |
| `401` | Invalid/expired token | No - re-auth |
| `403` | Insufficient permissions | No |
| `429` | Rate limit exceeded | Yes - backoff |
| `500` | Server error | Yes - retry |

See [error-codes.md](./references/error-codes.md) for complete error catalog.

### Token Auto-Refresh & Error Classification

Paytm Money is **NOT auto-refreshable** — portal authentication is broken/unreliable.

**Error classification** (`token_policy.py`):

| Error Pattern | Category | Action |
|--------------|----------|--------|
| `ACCESS_TOKEN_EXPIRED` | NOT_REFRESHABLE | Instant failover + frontend notification: "Re-login from Paytm Money portal" |
| `SESSION_EXPIRED` | NOT_REFRESHABLE | Instant failover + frontend notification |

**Health pipeline**: Adapter reports errors via `_report_auth_error()` -> Pool forwards to HealthMonitor. Auth errors trigger instant failover (health=0) since Paytm tokens cannot be auto-refreshed.

## 4. AlgoChanakya Integration

| Component | Status | File |
|-----------|--------|------|
| Market Data Adapter | **Implemented** | `backend/app/services/brokers/market_data/paytm_adapter.py` (581 lines) |
| Order Execution Adapter | **Implemented** | `backend/app/services/brokers/paytm_order_adapter.py` (437 lines) |
| Ticker (WebSocket) Adapter | **Implemented** | `backend/app/services/brokers/market_data/ticker/adapters/paytm.py` (618 lines) |
| Auth Route | **Implemented** | `backend/app/api/routes/paytm_auth.py` (246 lines) |
| Frontend Settings | **Implemented** | `frontend/src/components/settings/PaytmSettings.vue` |
| Tests | **Complete** | `test_paytm_market_data_adapter.py` (509 lines), `test_paytm_ticker_adapter.py` (914 lines) |
| GTT Orders | **NOT implemented** | See gtt-orders.md for endpoint details |
| Option Chain | **NOT implemented** | AlgoChanakya uses SmartAPI for option chain |

### Current Integration Pattern

```python
# Market data via adapter
from app.services.brokers.market_data.factory import get_market_data_adapter
adapter = get_market_data_adapter("paytm", credentials, db)
quote = await adapter.get_quote(["NIFTY2522725000CE"])  # Returns UnifiedQuote

# Order execution via adapter
from app.services.brokers.paytm_order_adapter import PaytmOrderAdapter
adapter = PaytmOrderAdapter(access_token=token)
order_id = await adapter.place_order(order_params)
```

## 5. Common Gotchas

1. **3 token types** - Must use the correct token for each endpoint. WebSocket requires `public_access_token`, not `access_token`. Read endpoints use `read_access_token`. GTT requires `access_token`.

2. **Least mature API** - Limited documentation, occasional breaking changes without notice. Test thoroughly.

3. **Limited F&O coverage** - Not all F&O instruments may be available. Verify before depending on it. BSE F&O added in 2025.

4. **Header name** - `x-jwt-token` (not `Authorization: Bearer`). Custom header format.

5. **pyPMClient SDK quality** - Last updated Jul 2024. Lower quality than kiteconnect or smartapi-python. May need workarounds or raw HTTP calls.

6. **Breaking changes** - Paytm has changed API endpoints and response formats without deprecation notices.

7. **WebSocket auth** - Uses `public_access_token` as query parameter, not header. Different from REST auth.

8. **Script master** - Instrument data may be less complete than other brokers. Verify coverage.

9. **No webhooks** - No HTTP webhooks and no order update WebSocket. REST polling is the only option.

10. **Developer Portal app creation may fail with 403** - As of March 2026, the "Create New App" flow on `developer.paytmmoney.com` returns HTTP 403 "Access Denied" from Akamai CDN when calling `POST /merchant-onboarding/merchant/v1/onboard`. This affects both manual browsers and automated (Playwright) browsers. The error is on Paytm's CDN/WAF side, not a user error. Workaround: try from a different network, mobile app, or contact support.

11. **Developer Portal login flow** - Login URL is `https://login.paytmmoney.com/?pmlEnv=developer`. Requires: mobile number → OTP → PIN (4 digits). The terms checkbox must be clicked via the UI label text "I Agree To The Above Terms" (not the checkbox element directly, which is intercepted by a presentation span). Login PIN for dev portal is separate from trading PIN.

12. **Support email `openapi.care@paytmmoney.com` is DEAD** - As of March 2026, this email bounces with "group may not exist". Use `feedback@paytmmoney.com` or raise a ticket via the Paytm Money mobile app instead. Phone: `0120-4440440`.

13. **Community forum `forum.paytmmoney.com` is DOWN** - DNS resolution fails as of March 2026. Cannot access any forum threads for troubleshooting.

14. **Developer Portal requires KYC-ready equity account** - You must have an active, KYC-verified equity trading account. F&O segment should also be activated (free, takes 30 min to 2 hours after document submission).

15. **Developer Portal app creation form fields** - App Name, Product Type (dropdown: "Rule Based Trading Platform"), Redirect URL (HTTPS required, but `http://127.0.0.1` or `http://localhost` allowed for testing), Postback URL (optional), Primary IP, Secondary IP, Description, App Logo (JPG/PNG, optional). Max 5 apps per user.

## 6. Related Skills

| Skill | When to Use |
|-------|-------------|
| `/angelone-expert` | Compare 3-token auth systems — both AngelOne and Paytm use 3 tokens (jwt/feed/refresh vs access/public/read) |
| `/zerodha-expert` | Compare API maturity — Kite is most mature, use as quality benchmark for Paytm adapter |
| `/fyers-expert` | Both use JSON WebSocket — compare message formats and subscription models |
| `/auto-verify` | After any Paytm adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, comparison matrix, CHANGELOG |

**Maturity Warning:** Paytm Money API is the least mature of all 6 brokers (sporadic SDK maintenance, limited F&O coverage, broken developer portal as of March 2026, dead support email, forum offline). Consider implementing with extra defensive error handling.

**Support Contacts (Updated March 2026):**
- ~~`openapi.care@paytmmoney.com`~~ — **DEAD** (bounces, group doesn't exist)
- `feedback@paytmmoney.com` — General feedback (works)
- Phone: `0120-4440440` — Paytm business support
- In-app: Raise ticket via Paytm Money mobile app
- ~~`forum.paytmmoney.com`~~ — **DOWN** (DNS resolution fails)

**Cross-Broker Comparison:** See [comparison-matrix.md](../broker-shared/comparison-matrix.md) for pricing, rate limits, WebSocket capabilities, and symbol format differences across all 6 brokers.

## 7. Maintenance & Auto-Improvement

### Freshness Tracking

| Reference File | Last Verified | Check Frequency |
|---|---|---|
| SKILL.md | 2026-03-18 | Quarterly |
| paytm-overview.md | 2026-03-04 | Quarterly |
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
2. **Staleness alert**: If `last_verified` exceeds 90 days, check https://developer.paytmmoney.com/docs/ for API changes.
3. **Quarterly review**: Next scheduled review: **June 2026**. Check for breaking changes (common with Paytm).

### Version Changelog

| Version | Date | Changes |
|---|---|---|
| 3.1 | 2026-03-18 | Critical updates from hands-on setup: Developer Portal "Create App" returns 403 from Akamai CDN (gotcha #10), login flow documented with checkbox workaround (gotcha #11), support email `openapi.care@paytmmoney.com` confirmed dead (gotcha #12), forum DNS down (gotcha #13), KYC+equity prerequisites documented (gotcha #14), form fields documented (gotcha #15), updated support contacts section. Login credentials saved to .env. |
| 3.0 | 2026-03-04 | Restructured: Paytm Money overview + pricing sections added, Paytm Money API content reorganized as subsection. New `paytm-overview.md` reference file. All existing API content preserved. |
| 2.5 | 2026-02-25 | Added GTT Orders section (not yet implemented), Option Chain section (Heckyl data, not implemented), Webhook section (no webhooks — REST polling only), BSE F&O 2025 note, pyPMClient last-updated note, expanded maintenance freshness table to 9 reference files, updated gotcha #9 (no webhooks) |
| 2.0 | 2026-02-25 | Implementation status corrected: all 3 adapters fully Implemented (was Planned), auth route + frontend + tests added to status table, maintenance section added |
| 1.0 | 2026-02-16 | Initial creation |

## References

- [Paytm Money Overview](./references/paytm-overview.md) - Company profile, products, pricing, exchanges, differentiators
- [Authentication Flow](./references/auth-flow.md) - 3-token OAuth flow
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints
- [WebSocket Protocol](./references/websocket-protocol.md) - public_access_token WS
- [Error Codes](./references/error-codes.md) - Error code reference
- [Symbol Format](./references/symbol-format.md) - Paytm instrument IDs
- [GTT Orders](./references/gtt-orders.md) - GTT order endpoints and cautions
- [Option Chain](./references/option-chain.md) - Option chain with Heckyl Greeks
- [Webhook](./references/webhook.md) - No webhooks; REST polling implementation
- [Maintenance Log](./references/maintenance-log.md) - API change tracker and review history
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
