---
name: paytm-expert
description: Use when implementing Paytm Money adapter, debugging Paytm API errors, understanding Paytm's 3-token system, or auditing code calling Paytm API. Paytm Money API expert for AlgoChanakya.
metadata:
  author: AlgoChanakya
  version: "2.0"
  last_verified: "2026-02-25"
---

# Paytm Money API Expert

Paytm Money offers a **FREE** trading API with a unique **3 JWT token** system (access_token, public_access_token for WebSocket, read_access_token for read-only). It's the least mature API among the 6 supported brokers, with limited F&O coverage and occasional breaking changes. All 3 AlgoChanakya adapters (market data, order execution, ticker/WebSocket) are **fully implemented**. Key differentiator: three separate token types and the `public_access_token` specifically for WebSocket authentication.

**Maturity Warning:** Paytm Money API is the least mature among Indian broker APIs. Expect limited documentation, occasional breaking changes, and less community support. Test thoroughly before production use.

## When to Use

- Implementing or debugging the Paytm Money market data, order, or ticker adapter
- Debugging Paytm API errors or authentication issues
- Understanding Paytm's 3-token system (access, public_access, read_access)
- Working with Paytm WebSocket (public_access_token auth)
- Comparing Paytm capabilities with other brokers
- Auditing code that calls Paytm API for correctness

## When NOT to Use

- General broker abstraction questions (read docs/architecture/broker-abstraction.md instead)
- Cross-broker comparison (use broker-shared/comparison-matrix.md instead)
- SmartAPI/Kite/Upstox/Dhan/Fyers issues (use their respective expert skills)

## API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://developer.paytmmoney.com/docs/ |
| **API Version** | v1 |
| **Python SDK** | `pyPMClient` (`pip install pyPMClient`) |
| **Pricing** | **FREE** (market data + orders) |
| **REST Base URL** | `https://developer.paytmmoney.com` |
| **WebSocket URL** | `wss://developer-ws.paytmmoney.com/broadcast/user/v1/data` |
| **Auth Method** | OAuth 2.0 (authorization_code) |
| **Token Validity** | access_token: ~24h, public_access_token: ~24h |

## Authentication Flow

Paytm Money uses OAuth 2.0 with **3 different JWT token types**.

### Step-by-Step Authentication

```
1. Redirect user → https://login.paytmmoney.com/merchant-login
   ?apiKey={api_key}&state={state}
2. User logs in on Paytm website
3. Paytm redirects → {redirect_url}?requestToken={token}&state={state}
4. POST /accounts/v2/gettoken with api_key, api_secret_key, request_token
5. Response: { access_token, public_access_token, read_access_token }
6. Use appropriate token per endpoint
```

### Token Types (3 JWTs)

| Token | Purpose | Validity | Used For |
|-------|---------|----------|----------|
| `access_token` | Full API access | ~24 hours | Orders, positions, holdings |
| `public_access_token` | WebSocket only | ~24 hours | **WebSocket authentication** |
| `read_access_token` | Read-only REST | ~24 hours | Market data, quotes, instruments |

### Auth Header

```
x-jwt-token: {access_token|read_access_token}
```

**Note:** Header is `x-jwt-token` (not `Authorization: Bearer`).

See [auth-flow.md](./references/auth-flow.md) for complete request/response examples.

## Key Endpoints Quick Reference

| Category | Method | Endpoint | Token Type |
|----------|--------|----------|------------|
| **Auth** | POST | `/accounts/v2/gettoken` | None (api_key/secret) |
| **Profile** | GET | `/accounts/v1/user/details` | access_token |
| **Margins** | GET | `/accounts/v1/funds/summary` | access_token |
| **Quote** | GET | `/data/v1/price/live` | read_access_token |
| **OHLC** | GET | `/data/v1/price/ohlc` | read_access_token |
| **Historical** | GET | `/data/v1/price/historical` | read_access_token |
| **Place Order** | POST | `/orders/v1/place/regular` | access_token |
| **Modify Order** | PUT | `/orders/v1/modify/regular` | access_token |
| **Cancel Order** | DELETE | `/orders/v1/cancel/regular` | access_token |
| **Orders** | GET | `/orders/v1/order-book` | access_token |
| **Positions** | GET | `/orders/v1/position` | access_token |
| **Holdings** | GET | `/holdings/v1/get-user-holdings` | access_token |
| **Instruments** | Download | Script master CSV | read_access_token |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete schemas.

## Symbol Format

### Paytm Instrument IDs

Paytm uses a combination of `security_id` (numeric) and exchange-specific identifiers.

**Examples:**

| Instrument | security_id | exchange | Symbol |
|-----------|-------------|----------|--------|
| NIFTY 50 | `13` | `NSE` | `NIFTY` |
| NIFTY 25000 CE | `12345` | `NSE` | `NIFTY2522725000CE` |
| Reliance | `2885` | `NSE` | `RELIANCE` |

### Canonical Conversion

Conversion requires instrument master lookup:

```python
from app.services.brokers.market_data.token_manager import token_manager

# Paytm security_id → Canonical
canonical = await token_manager.get_canonical_symbol(12345, "paytm")

# Canonical → Paytm security_id
paytm_id = await token_manager.get_broker_token("NIFTY2522725000CE", "paytm")
```

See [symbol-format.md](./references/symbol-format.md) for instrument master details.

## WebSocket Protocol

### Connection with public_access_token

```python
# WebSocket uses public_access_token (NOT access_token)
ws_url = f"wss://developer-ws.paytmmoney.com/broadcast/user/v1/data?x_jwt_token={public_access_token}"
```

### Subscription

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

### Modes

| Mode | Code | Description |
|------|------|-------------|
| LTP | `1` | Last price only |
| Full | `2` | OHLC + volume + OI + depth |

### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max instruments | **200** per connection |
| Max connections | **1** per token |
| Auth token | **public_access_token** (specific) |
| Message format | JSON |

See [websocket-protocol.md](./references/websocket-protocol.md) for detailed protocol.

## Rate Limits

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| REST API (general) | **10 requests/second** | Per access_token |
| Order placement | **10 orders/second** | Per user |
| Historical data | **5 requests/second** | Separate limit |
| WebSocket | **Unlimited ticks** | After subscription |

**AlgoChanakya Configuration:** `rate_limiter.py` sets `"paytm": 10` (10 req/sec).

## Price Normalization

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** | **RUPEES** | No conversion |
| **WebSocket** | **RUPEES** | No conversion |
| **Historical** | **RUPEES** | No conversion |

Paytm returns all prices in RUPEES. No paise conversion needed.

## AlgoChanakya Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Market Data Adapter | **✅ Implemented** | `backend/app/services/brokers/market_data/paytm_adapter.py` (581 lines) |
| Order Execution Adapter | **✅ Implemented** | `backend/app/services/brokers/paytm_order_adapter.py` (437 lines) |
| Ticker (WebSocket) Adapter | **✅ Implemented** | `backend/app/services/brokers/market_data/ticker/adapters/paytm.py` (618 lines) |
| Auth Route | **✅ Implemented** | `backend/app/api/routes/paytm_auth.py` (246 lines) |
| Frontend Settings | **✅ Implemented** | `frontend/src/components/settings/PaytmSettings.vue` |
| Tests | **✅ Complete** | `test_paytm_market_data_adapter.py` (509 lines), `test_paytm_ticker_adapter.py` (914 lines) |

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

## Common Gotchas

1. **3 token types** - Must use the correct token for each endpoint. WebSocket requires `public_access_token`, not `access_token`. Read endpoints use `read_access_token`.

2. **Least mature API** - Limited documentation, occasional breaking changes. Test thoroughly.

3. **Limited F&O coverage** - Not all F&O instruments may be available. Verify before depending on it.

4. **Header name** - `x-jwt-token` (not `Authorization: Bearer`). Custom header format.

5. **pyPMClient SDK quality** - Lower quality than kiteconnect or smartapi-python. May need workarounds.

6. **Breaking changes** - Paytm has changed API endpoints and response formats without deprecation notices.

7. **WebSocket auth** - Uses `public_access_token` as query parameter, not header. Different from REST auth.

8. **Script master** - Instrument data may be less complete than other brokers. Verify coverage.

## Error Codes Quick Reference

| HTTP Status | Cause | Retryable |
|-------------|-------|-----------|
| `400` | Bad request / invalid params | No |
| `401` | Invalid/expired token | No - re-auth |
| `403` | Insufficient permissions | No |
| `429` | Rate limit exceeded | Yes - backoff |
| `500` | Server error | Yes - retry |

See [error-codes.md](./references/error-codes.md) for complete error catalog.

## Related Skills

| Skill | When to Use |
|-------|-------------|
| `/smartapi-expert` | Compare 3-token auth systems — both SmartAPI and Paytm use 3 tokens (jwt/feed/refresh vs access/public/read) |
| `/kite-expert` | Compare API maturity — Kite is most mature, use as quality benchmark for Paytm adapter |
| `/fyers-expert` | Both use JSON WebSocket — compare message formats and subscription models |
| `/auto-verify` | After any Paytm adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, comparison matrix, CHANGELOG |

**Maturity Warning:** Paytm Money API is the least mature of all 6 brokers (sporadic SDK maintenance, limited F&O coverage). Consider implementing with extra defensive error handling.

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
2. **Staleness alert**: If `last_verified` exceeds 90 days, check https://developer.paytmmoney.com/docs/ for API changes.
3. **Quarterly review**: Next scheduled review: **May 2026**. Check for breaking changes (common with Paytm).

### Version Changelog

| Version | Date | Changes |
|---|---|---|
| 2.0 | 2026-02-25 | Implementation status corrected: all 3 adapters fully Implemented (was Planned), auth route + frontend + tests added to status table, maintenance section added |
| 1.0 | 2026-02-16 | Initial creation |

## References

- [Authentication Flow](./references/auth-flow.md) - 3-token OAuth flow
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints
- [WebSocket Protocol](./references/websocket-protocol.md) - public_access_token WS
- [Error Codes](./references/error-codes.md) - Error code reference
- [Symbol Format](./references/symbol-format.md) - Paytm instrument IDs
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
