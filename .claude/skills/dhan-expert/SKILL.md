---
name: dhan-expert
description: Use when implementing Dhan adapter, debugging Dhan API errors, understanding Dhan security_id format, or auditing code calling Dhan API. Dhan API expert for AlgoChanakya.
metadata:
  author: AlgoChanakya
  version: "2.5"
  last_verified: "2026-02-25"
---

# Dhan API Expert

Dhan offers a modern REST API with unique features: **200-level market depth** (unique in India), **Little Endian binary WebSocket**, and **security_id-based** instrument identification (numeric IDs only). Dhan has a **two-tier pricing model**: Trading APIs are FREE for all users, but Data APIs (market data WebSocket) require either executing 25 F&O trades/month OR paying ₹499/month subscription. All 3 AlgoChanakya adapters (market data, order execution, ticker/WebSocket) are **fully implemented**. Key differentiator: deepest market depth data and multi-tier rate limiting system.

## When to Use

- Implementing or debugging the Dhan market data, order, or ticker adapter
- Debugging Dhan API errors or authentication issues
- Understanding Dhan's security_id format (numeric-only, no string symbols)
- Working with Little Endian binary WebSocket (unique `struct.unpack('<...')`)
- Understanding 20-depth and 200-depth market data
- Working with Forever Orders (GTT) via `/v2/forever/orders`
- Working with Dhan Option Chain API (`/v2/optionchain`)
- Configuring Postback (webhook) or Live Order Update WebSocket
- Comparing Dhan capabilities with other brokers
- Auditing code that calls Dhan API for correctness

## When NOT to Use

- General broker abstraction questions (read docs/architecture/broker-abstraction.md instead)
- Cross-broker comparison (use broker-shared/comparison-matrix.md instead)
- SmartAPI/Kite/Upstox issues (use their respective expert skills)
- Fyers/Paytm issues (use their respective expert skills)

## API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://dhanhq.co/docs/v2/ |
| **API Version** | v2 |
| **Python SDK** | `dhanhq` v2.1.0 (`pip install dhanhq`) |
| **Pricing** | Trading API: FREE \| Data API: FREE (with 25 F&O trades/mo) OR ₹499/mo |
| **REST Base URL** | `https://api.dhan.co/v2` |
| **WebSocket URL (Market Data)** | `wss://api-feed.dhan.co` |
| **WebSocket URL (Order Updates)** | `wss://api-order-update.dhan.co` |
| **Auth Method** | API access token (from web dashboard) |
| **Token Validity** | Until manually revoked or regenerated |

## Authentication Flow

Dhan uses a simple **API token** model - no OAuth redirect needed.

### Step-by-Step

```
1. Login to Dhan web dashboard (https://trade.dhan.co)
2. Navigate to API settings
3. Generate access_token (long-lived)
4. Use token in all API calls: access-token: {token}
```

### Auth Header

```
access-token: {access_token}
Content-Type: application/json
```

**Note:** Header name is `access-token` (hyphenated, lowercase), NOT `Authorization: Bearer`.

See [auth-flow.md](./references/auth-flow.md) for complete details.

## Key Endpoints Quick Reference

| Category | Method | Endpoint | Notes |
|----------|--------|----------|-------|
| **Profile** | GET | `/v2/clients/{client_id}` | User details |
| **Margins** | GET | `/v2/fundlimit` | Fund limits — note `availabelBalance` typo |
| **Quote** | POST | `/v2/marketfeed/ltp` | LTP for instruments |
| **OHLC** | POST | `/v2/marketfeed/ohlc` | OHLC data |
| **Depth (20)** | POST | `/v2/marketfeed/quote` | 20-level depth |
| **Historical** | GET | `/v2/charts/historical` | OHLCV candles |
| **Intraday** | GET | `/v2/charts/intraday` | Today's candles |
| **Place Order** | POST | `/v2/orders` | Place order |
| **Modify Order** | PUT | `/v2/orders/{order_id}` | Modify pending |
| **Cancel Order** | DELETE | `/v2/orders/{order_id}` | Cancel pending |
| **Orders** | GET | `/v2/orders` | All orders |
| **Positions** | GET | `/v2/positions` | Current positions |
| **Holdings** | GET | `/v2/holdings` | Portfolio holdings |
| **Forever Orders** | POST/GET/PUT/DELETE | `/v2/forever/orders` | GTT orders — NOT yet in AlgoChanakya |
| **Option Chain** | POST | `/v2/optionchain` | Option chain with Greeks — NOT yet in AlgoChanakya |
| **Expiry List** | GET | `/v2/expirylist` | Expiry dates — NOT yet in AlgoChanakya |
| **Instruments** | Download | CSV from Dhan website | Instrument master |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete schemas.

## Symbol Format (security_id)

### Numeric IDs Only

Dhan uses **numeric security_id** values. There are NO string trading symbols in the API.

**Examples:**

| Instrument | security_id | exchange_segment |
|-----------|-------------|-----------------|
| NIFTY 50 | `13` | `IDX_I` |
| NIFTY BANK | `25` | `IDX_I` |
| NIFTY 25000 CE | `12345` | `NSE_FNO` |
| Reliance | `2885` | `NSE_EQ` |

### Exchange Segments

| Segment | Code | Description |
|---------|------|-------------|
| `NSE_EQ` | `NSE_EQ` | NSE Cash |
| `NSE_FNO` | `NSE_FNO` | NSE F&O |
| `BSE_EQ` | `BSE_EQ` | BSE Cash |
| `BSE_FNO` | `BSE_FNO` | BSE F&O |
| `MCX_COMM` | `MCX_COMM` | MCX Commodities |
| `IDX_I` | `IDX_I` | Indices |

### Canonical Conversion

Conversion is **high complexity** because Dhan uses only numeric IDs:

```python
from app.services.brokers.market_data.token_manager import token_manager

# security_id → Canonical
canonical = await token_manager.get_canonical_symbol(12345, "dhan")

# Canonical → security_id
security_id = await token_manager.get_broker_token("NIFTY2522725000CE", "dhan")
```

See [symbol-format.md](./references/symbol-format.md) for instrument CSV format.

## WebSocket Protocol (Little Endian Binary)

### Unique: Little Endian

Dhan is the **only Indian broker** using Little Endian byte order (`struct.unpack('<...')`). All others use Big Endian.

### Connection

```python
import websocket
ws = websocket.WebSocketApp(
    "wss://api-feed.dhan.co",
    header={"access-token": access_token},
    on_message=on_message
)
```

### Subscription Modes

| Mode | Description | Data |
|------|-------------|------|
| **Ticker** | LTP + change | ~20 bytes |
| **Quote** | OHLC + volume + OI + 20-depth | ~500 bytes |
| **Full** | All quote data + timestamps | ~700 bytes |
| **20-Depth** | 20-level market depth | Default for Quote mode |
| **200-Depth** | 200-level depth | **1 instrument/connection** (unique in India) |

### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max instruments per connection | **100** (Ticker), **50** (Quote), **1** (200-Depth) |
| Max connections | **5** |
| Message format | Little Endian binary |
| 200-Depth limit | **1 instrument per connection** |

See [websocket-protocol.md](./references/websocket-protocol.md) for byte offsets and parsing.

## Forever Orders (GTT)

Dhan's GTT equivalent is called **"Forever Orders"** — orders that persist until triggered or manually cancelled (up to 365 days). Supports two types: `SINGLE` (one trigger) and `OCO` (target + stop loss, one cancels other).

**Endpoints:** POST/GET/PUT/DELETE `/v2/forever/orders`

**AlgoChanakya status:** NOT yet implemented in `backend/app/services/brokers/dhan_order_adapter.py`. Current adapter supports standard orders only.

See [gtt-orders.md](./references/gtt-orders.md) for full request/response schemas and OCO details.

## Option Chain API

Dhan provides a dedicated Option Chain API returning full strike list with Greeks (delta, gamma, theta, vega, IV).

**Endpoints:**
- `POST /v2/optionchain` — full option chain with Greeks
- `GET /v2/expirylist` — available expiry dates for an underlying

**AlgoChanakya status:** NOT yet integrated. AlgoChanakya currently uses SmartAPI for option chain data.

See [option-chain.md](./references/option-chain.md) for request/response schemas and supported underlyings.

## Postback / Webhook & Live Order Updates

Dhan provides two mechanisms for real-time order notifications:

1. **Postback (webhook):** Dhan sends HTTP POST to your configured URL on every order update (trade, rejection, cancellation). Configure in Dhan web portal (no code required for setup).

2. **Live Order Update WebSocket:** `wss://api-order-update.dhan.co` — real-time WebSocket stream of order status changes.

**AlgoChanakya status:** Neither is currently used. AlgoChanakya polls the REST order book for status updates.

See [webhook.md](./references/webhook.md) for postback payload schema, WebSocket connection code, and integration notes.

## Rate Limits (Multi-Tier)

| Resource | Limit | Window |
|----------|-------|--------|
| Order placement | **10/second** | Per second |
| Order placement | **250/minute** | Per minute |
| Order placement | **1000/hour** | Per hour |
| Order placement | **7000/day** | Per day |
| REST API (general) | **10/second** | Per second |
| WebSocket | Unlimited ticks | After subscription |
| Historical data | **10/second** | Per second |

**AlgoChanakya Configuration:** `rate_limiter.py` sets `"dhan": 10` (10 req/sec).

**Note:** Place + Modify + Cancel operations each count against all four order tiers. Hit any tier and you get HTTP 429.

## Price Normalization

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** | **RUPEES** | No conversion |
| **WebSocket** | **RUPEES** | No conversion (prices as float) |
| **Historical** | **RUPEES** | No conversion |

Dhan returns all prices in RUPEES. No paise conversion needed.

## AlgoChanakya Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Market Data Adapter | **Implemented** | `backend/app/services/brokers/market_data/dhan_adapter.py` (813 lines) |
| Order Execution Adapter | **Implemented** | `backend/app/services/brokers/dhan_order_adapter.py` (446 lines) |
| Ticker (WebSocket) Adapter | **Implemented** | `backend/app/services/brokers/market_data/ticker/adapters/dhan.py` (575 lines) |
| Auth Route | **Implemented** | `backend/app/api/routes/dhan_auth.py` (173 lines) |
| Frontend Settings | **Implemented** | `frontend/src/components/settings/DhanSettings.vue` |
| Tests | **Complete** | `test_dhan_market_data_adapter.py` (743 lines), `test_dhan_ticker_adapter.py` (692 lines) |
| Forever Orders (GTT) | **NOT implemented** | Planned: `dhan_order_adapter.py` extension |
| Option Chain | **NOT implemented** | Planned: separate integration |
| Postback / Webhook | **NOT implemented** | Planned: `POST /api/webhooks/dhan/order-update` |

### Current Integration Pattern

```python
# Market data via adapter
from app.services.brokers.market_data.factory import get_market_data_adapter
adapter = get_market_data_adapter("dhan", credentials, db)
quote = await adapter.get_quote(["NIFTY2522725000CE"])  # Returns UnifiedQuote

# Order execution via adapter
from app.services.brokers.dhan_order_adapter import DhanOrderAdapter
adapter = DhanOrderAdapter(access_token=token, client_id=client_id)
order_id = await adapter.place_order(order_params)
```

## Common Gotchas

1. **Two-tier pricing model** - Trading APIs are FREE, but Data APIs (market data) require 25 F&O trades/month OR ₹499/month subscription. Common confusion point.

2. **Little Endian binary** - Use `struct.unpack('<...')` NOT `'>'`. This is unique among Indian brokers.

3. **Numeric IDs only** - No string trading symbols. Must maintain instrument mapping table.

4. **Auth header format** - `access-token: {token}` (hyphenated, lowercase). Not `Authorization: Bearer`.

5. **200-Depth limit** - Only 1 instrument per connection. Need 5 connections for 5 instruments.

6. **Multi-tier order limits** - Check all 4 limits (10/sec, 250/min, 1000/hr, 7000/day). Can hit daily limit even within per-second rate limit.

7. **Data API unlock requirement** - Must execute 25 F&O trades monthly to unlock free data access, otherwise ₹499/month subscription required.

8. **Instrument CSV download** - Must download from Dhan website manually or via undocumented URL.

9. **Exchange segment format** - Uses `NSE_FNO` not `NFO`. Different from Kite/SmartAPI naming.

10. **`availabelBalance` typo** - The `GET /v2/fundlimit` response has a misspelled field: `availabelBalance` (missing second 'l'). This is a known bug in the Dhan API that has never been fixed. You MUST use the exact misspelled field name in code — do not "correct" it.

## Error Codes Quick Reference

| HTTP Status | Error | Cause | Retryable |
|-------------|-------|-------|-----------|
| `400` | Bad Request | Invalid parameters | No |
| `401` | Unauthorized | Invalid/expired token | No |
| `403` | Forbidden | Permissions issue | No |
| `429` | Rate Limited | Exceeded rate limit | Yes - backoff |
| `500` | Server Error | Dhan server issue | Yes - retry |

See [error-codes.md](./references/error-codes.md) for complete error catalog.

## Related Skills

| Skill | When to Use |
|-------|-------------|
| `/upstox-expert` | Both modern free-tier APIs — compare unique WS features (Dhan: 200-depth, Upstox: Greeks) |
| `/smartapi-expert` | Compare auth approaches — Dhan static token vs SmartAPI auto-TOTP |
| `/fyers-expert` | Compare unique features — Fyers has dual WS + order updates, Dhan has deep depth |
| `/auto-verify` | After any Dhan adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, comparison matrix, CHANGELOG |

**Cross-Broker Comparison:** See [comparison-matrix.md](../broker-shared/comparison-matrix.md) for pricing, rate limits, WebSocket capabilities, and symbol format differences across all 6 brokers.

## Maintenance & Auto-Improvement

### Freshness Tracking

| Reference File | Last Verified | Check Frequency |
|---|---|---|
| SKILL.md | 2026-02-25 | Quarterly |
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
2. **Staleness alert**: If `last_verified` exceeds 90 days, check https://dhanhq.co/docs/v2/ for API changes.
3. **Quarterly review**: Next scheduled review: **May 2026**.

### Version Changelog

| Version | Date | Changes |
|---|---|---|
| 2.5 | 2026-02-25 | Added Forever Orders (GTT) section, Option Chain section, Postback/Webhook section, Live Order Update WebSocket, `availabelBalance` typo gotcha, corrected multi-tier rate limits (10/sec, 250/min, 1000/hr, 7000/day), expanded Maintenance section with all 9 reference files, added 3 new reference files |
| 2.0 | 2026-02-25 | Implementation status corrected: all 3 adapters fully Implemented (was Planned), auth route + frontend + tests added to status table, maintenance section added |
| 1.0 | 2026-02-16 | Initial creation |

## References

- [Authentication Flow](./references/auth-flow.md) - API token setup
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints
- [WebSocket Protocol](./references/websocket-protocol.md) - Little Endian binary protocol
- [Error Codes](./references/error-codes.md) - Error code reference
- [Symbol Format](./references/symbol-format.md) - security_id format
- [Forever Orders (GTT)](./references/gtt-orders.md) - GTT/GTC order management
- [Option Chain](./references/option-chain.md) - Option chain API with Greeks
- [Webhook / Postback](./references/webhook.md) - Order update notifications
- [Maintenance Log](./references/maintenance-log.md) - API change tracker and review history
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
