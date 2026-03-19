---
name: dhan-expert
description: Dhan expert — broker overview, products, pricing, DhanHQ API,
  and AlgoChanakya adapter guidance. Use for any Dhan question.
version: "3.1"
last_verified: "2026-03-18"
---

# Dhan Expert

Dhan (Raise Financial Services) is a fast-growing Indian fintech broker founded in 2021, focused on derivatives traders with a mobile-first UX and deep market data. Dhan's trading API is called **DhanHQ** — a modern REST + Little Endian binary WebSocket API with unique features: **200-level market depth** (unique in India), **security_id-based** instrument identification (numeric IDs only), and a **two-tier pricing model** (Trading APIs FREE, Data APIs require 25 F&O trades/month OR ₹499/month).

In AlgoChanakya, all 3 Dhan adapters (market data, order execution, ticker/WebSocket) are **fully implemented**. Key differentiator: deepest market depth data, multi-tier rate limiting, Super Order (bracket), Kill Switch, and P&L-based auto-exit built into the API. Dhan sits in the platform failover chain for market data: SmartAPI → **Dhan** → Fyers → Paytm → Upstox → Kite.

## When to Use

- Any question about Dhan as a broker (products, pricing, account types)
- Implementing or debugging the Dhan market data, order, or ticker adapter
- Debugging Dhan API errors or authentication issues
- Understanding Dhan's security_id format (numeric-only, no string symbols)
- Working with Little Endian binary WebSocket (unique `struct.unpack('<...')`)
- Understanding 20-depth and 200-depth market data
- Working with Forever Orders (GTT) via `/v2/forever/orders`
- Working with Super Orders (bracket orders with entry + target + SL)
- Working with Trader's Control (Kill Switch, P&L-based auto-exit)
- Working with Dhan Option Chain API (`/v2/optionchain`)
- Configuring Postback (webhook) or Live Order Update WebSocket
- Comparing Dhan capabilities with other brokers
- Auditing code that calls Dhan API for correctness

## When NOT to Use

- General broker abstraction questions (read docs/architecture/broker-abstraction.md instead)
- Cross-broker comparison (use broker-shared/comparison-matrix.md instead)
- AngelOne/SmartAPI issues (use angelone-expert)
- Kite/Upstox/Fyers/Paytm issues (use their respective expert skills)

---

## 1. Dhan Overview

Dhan (Raise Financial Services Private Limited), est. 2021, is a SEBI-registered stockbroker focused on derivatives traders. It offers trading across NSE, BSE, and MCX segments with a mobile-first approach and deep market data capabilities.

**Account types:** Individual, Joint, HUF, Corporate, NRI.

See [dhan-overview.md](./references/dhan-overview.md) for complete company profile, products table, and differentiators.

## 2. Brokerage & Pricing

### Trading Charges

| Segment | Brokerage |
|---------|-----------|
| Equity Delivery | ₹0 (FREE) |
| Equity Intraday | ₹20/order or 0.03% (lower) |
| F&O (Options) | ₹20/order (flat) |
| F&O (Futures) | ₹20/order or 0.03% (lower) |
| Currency / Commodity | ₹20/order or 0.03% (lower) |

**Other:** Account opening FREE, no AMC.

### API Costs

| Product | Cost | Capability |
|---------|------|------------|
| **Trading API** | FREE | Order execution, positions, holdings, margins |
| **Data API** | FREE (with 25 F&O trades/mo) OR ₹499/month | Market data WebSocket, historical data, option chain |

**AlgoChanakya impact:** Since SmartAPI provides free market data, AlgoChanakya uses Dhan as a failover data source. Trading API is free for all users. Data API requires either active F&O trading (25 trades/month) or ₹499/month subscription.

See [dhan-overview.md](./references/dhan-overview.md) for detailed charges and exchange support.

---

## 3. DhanHQ API

### API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://dhanhq.co/docs/v2/ |
| **API Version** | v2 |
| **Python SDK** | `dhanhq` v2.1.0 (`pip install dhanhq`) |
| **Pricing** | Trading API: FREE \| Data API: FREE (with 25 F&O trades/mo) OR ₹499/mo |
| **REST Base URL** | `https://api.dhan.co/v2` |
| **WebSocket URL (Market Data)** | `wss://api-feed.dhan.co` |
| **WebSocket URL (Order Updates)** | `wss://api-order-update.dhan.co` |
| **Auth Method** | Dual: API Key+Secret (permanent) + Access Token (24h JWT) |
| **Token Validity** | Access Token: **24 hours**. API Key: permanent (until revoked) |

### Authentication Flow

Dhan has a **dual credential system** — both generated from `web.dhan.co` (NOT `developer.dhanhq.co`). For the three-tier credential architecture (platform data API vs user login vs user personal API), see [authentication.md](../../../docs/architecture/authentication.md#three-tier-credential-architecture).

#### Credentials Overview

| Credential | Expiry | Generated Via |
|-----------|--------|--------------|
| **API Key + Secret** | Permanent | Dashboard → DhanHQ Trading APIs → toggle to "API Key" |
| **Access Token** (JWT) | **24 hours** | Dashboard → DhanHQ Trading APIs → "Access Token" tab |
| **TOTP** (optional) | Permanent | Dashboard → DhanHQ Trading APIs → "Set-up TOTP" |
| **Static IP** (optional) | Permanent (7-day change cooldown) | Dashboard → DhanHQ Trading APIs → "Static IP Setting" |

#### Step-by-Step

```
1. Login to Dhan dashboard (https://login.dhan.co → Select "Dhan" platform)
2. Click "Show login with Mobile" → Enter phone → OTP/TOTP → PIN
3. Profile icon (top-right) → "DhanHQ Trading APIs"
4. Access Token tab: Enter app name → "Generate Access Token" (24h JWT)
5. Toggle to API Key tab: Enter app name + redirect URL → "Generate API Key" (permanent)
6. Optional: Set up TOTP (for automated login) and Static IP (for order security)
```

#### Auth Header

```
access-token: {access_token}
Content-Type: application/json
```

**Note:** Header name is `access-token` (hyphenated, lowercase), NOT `Authorization: Bearer`.

**IMPORTANT:** The DhanHQ Developer Portal (`developer.dhanhq.co`) is a SEPARATE system. It shows "Invalid Email" errors during registration. All credential generation is done from the trading dashboard (`web.dhan.co`).

See [auth-flow.md](./references/auth-flow.md) for complete details.

### Key Endpoints Quick Reference

| Category | Method | Endpoint | Notes |
|----------|--------|----------|-------|
| **Profile** | GET | `/v2/profile` | User details |
| **Margins** | GET | `/v2/fundlimit` | Fund limits — note `availabelBalance` typo |
| **Margin Calc** | POST | `/v2/margincalculator` | Margin for single order |
| **Quote** | POST | `/v2/marketfeed/ltp` | LTP for instruments (max 1000) |
| **OHLC** | POST | `/v2/marketfeed/ohlc` | OHLC data |
| **Depth (20)** | POST | `/v2/marketfeed/quote` | 20-level depth |
| **Historical** | POST | `/v2/charts/historical` | OHLCV candles (daily, back to inception) |
| **Intraday** | POST | `/v2/charts/intraday` | Minute candles (1/5/15/25/60m, max 90 days) |
| **Place Order** | POST | `/v2/orders` | Place order — requires static IP whitelist |
| **Modify Order** | PUT | `/v2/orders/{order_id}` | Modify pending — requires static IP whitelist |
| **Cancel Order** | DELETE | `/v2/orders/{order_id}` | Cancel pending — requires static IP whitelist |
| **Slice Order** | POST | `/v2/orders/slicing` | Auto-slice for freeze quantity limit |
| **Orders** | GET | `/v2/orders` | All orders |
| **Trades** | GET | `/v2/trades` | All trades today |
| **Positions** | GET | `/v2/positions` | Current positions |
| **Holdings** | GET | `/v2/holdings` | Portfolio holdings |
| **Super Order** | POST/PUT/DELETE/GET | `/v2/super/orders` | Bracket orders (entry+target+SL) — NOT yet in AlgoChanakya |
| **Forever Orders** | POST/GET/PUT/DELETE | `/v2/forever/orders` | GTT orders — NOT yet in AlgoChanakya |
| **Kill Switch** | POST/GET | `/v2/killswitch` | Disable all trading — NOT yet in AlgoChanakya |
| **P&L Exit** | POST/DELETE/GET | `/v2/pnlExit` | Auto-exit on P&L threshold — NOT yet in AlgoChanakya |
| **Option Chain** | POST | `/v2/optionchain` | Option chain with Greeks — NOT yet in AlgoChanakya |
| **Expiry List** | GET | `/v2/expirylist` | Expiry dates — NOT yet in AlgoChanakya |
| **Instruments** | Download | `https://images.dhan.co/api-data/api-scrip-master.csv` | Instrument master CSV |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete schemas.

### Symbol Format (security_id)

#### Numeric IDs Only

Dhan uses **numeric security_id** values. There are NO string trading symbols in the API.

**Examples:**

| Instrument | security_id | exchange_segment |
|-----------|-------------|-----------------|
| NIFTY 50 | `13` | `IDX_I` |
| NIFTY BANK | `25` | `IDX_I` |
| NIFTY 25000 CE | `12345` | `NSE_FNO` |
| Reliance | `2885` | `NSE_EQ` |

#### Exchange Segments

| Segment | Code | Description |
|---------|------|-------------|
| `NSE_EQ` | `NSE_EQ` | NSE Cash |
| `NSE_FNO` | `NSE_FNO` | NSE F&O |
| `BSE_EQ` | `BSE_EQ` | BSE Cash |
| `BSE_FNO` | `BSE_FNO` | BSE F&O |
| `MCX_COMM` | `MCX_COMM` | MCX Commodities |
| `IDX_I` | `IDX_I` | Indices |

#### Canonical Conversion

Conversion is **high complexity** because Dhan uses only numeric IDs:

```python
from app.services.brokers.market_data.token_manager import token_manager

# security_id → Canonical
canonical = await token_manager.get_canonical_symbol(12345, "dhan")

# Canonical → security_id
security_id = await token_manager.get_broker_token("NIFTY2522725000CE", "dhan")
```

See [symbol-format.md](./references/symbol-format.md) for instrument CSV format.

### WebSocket Protocol (Little Endian Binary)

#### Unique: Little Endian

Dhan is the **only Indian broker** using Little Endian byte order (`struct.unpack('<...')`). All others use Big Endian.

#### Connection URL (v2)

```
wss://api-feed.dhan.co?version=2&token={access_token}&clientId={client_id}&authType=2
```

Auth is via **query parameters** in the URL (not headers). `authType=2` is the default.

#### Heartbeat

Server sends a **ping every 10 seconds**. Client must respond with pong (handled automatically by most WebSocket libraries). Connection drops after **40 seconds** of no response.

#### Graceful Disconnect

Send `{"RequestCode": 12}` to cleanly close the connection before disconnecting.

#### Subscription Modes

| Mode | Description | Data |
|------|-------------|------|
| **Ticker** | LTP + change | ~20 bytes |
| **Quote** | OHLC + volume + OI + 20-depth | ~500 bytes |
| **Full** | All quote data + timestamps | ~700 bytes |
| **200-Depth** | 200-level depth | **1 instrument/connection** (unique in India) |

#### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max instruments per connection | **5000** total; 100 per subscription JSON message (Ticker/Quote), **1** (200-Depth) |
| Max connections | **5** (exceeding 5 disconnects the oldest) |
| Message format | Little Endian binary |
| 200-Depth limit | **1 instrument per connection** |

See [websocket-protocol.md](./references/websocket-protocol.md) for byte offsets and parsing.

### Super Orders

Dhan's **Super Order** combines entry + target + stop-loss into a single API call with optional trailing stop-loss. Different from Forever Orders — Super Orders execute within the same trading session.

**Endpoints:** POST/PUT/DELETE/GET `/v2/super/orders`

**Key fields:** `price` (entry), `targetPrice`, `stopLossPrice`, `trailingJump` (pass `0` to disable trailing).

**Leg names for modify/cancel:** `ENTRY_LEG`, `TARGET_LEG`, `STOP_LOSS_LEG`

**Constraints:**
- All 4 endpoints require **static IP whitelisting**
- Product types: `CNC`, `INTRADAY`, `MARGIN`, `MTF` (not CO/BO)
- Once entry is `TRADED`, only target/SL prices and trail are modifiable
- Cancelling a leg prevents re-adding it; cancelling the order ID cancels all legs
- `CLOSED` status = entry + one exit leg fully executed

**AlgoChanakya status:** NOT yet implemented. Planned for AutoPilot bracket order support.

See [super-order.md](./references/super-order.md) for full request/response schemas.

### Trader's Control (Kill Switch & P&L Exit)

Dhan provides two risk management APIs under the "Trader's Control" category:

#### Kill Switch

Disables ALL trading for the current day. **Prerequisite:** All positions closed and no pending orders.

```
POST /v2/killswitch?killSwitchStatus=ACTIVATE   # Disable all trading
POST /v2/killswitch?killSwitchStatus=DEACTIVATE # Re-enable trading
GET  /v2/killswitch                              # Check current status
```

**Important:** You MUST close all positions and cancel all orders BEFORE calling `ACTIVATE`. Attempting to activate with open positions/orders will fail.

#### P&L Exit

Automatically exits all positions when a profit or loss threshold is hit.

```
POST   /v2/pnlExit    # Configure thresholds
DELETE /v2/pnlExit    # Stop P&L exit
GET    /v2/pnlExit    # Get current configuration
```

**Key fields:** `profitValue`, `lossValue`, `productType` (array: `["INTRADAY", "DELIVERY"]`), `enableKillSwitch` (boolean — auto-activates kill switch when threshold hit).

**Warning:** If `profitValue` is set below current unrealized profit, exit triggers immediately.

**Duration:** Active only for the current trading day; resets at session end.

**AlgoChanakya status:** NOT yet integrated. Planned for AutoPilot risk management.

See [traders-control.md](./references/traders-control.md) for full schemas and integration notes.

### Forever Orders (GTT)

Dhan's GTT equivalent is called **"Forever Orders"** — orders that persist until triggered or manually cancelled (up to 365 days). Supports two types: `SINGLE` (one trigger) and `OCO` (target + stop loss, one cancels other).

**Endpoints:** POST/GET/PUT/DELETE `/v2/forever/orders`  — all require **static IP whitelisting**

**Required fields:** `dhanClientId`, `orderFlag` (`SINGLE`/`OCO`), `transactionType`, `exchangeSegment`, `productType` (`CNC`/`MTF` only), `orderType`, `validity`, `securityId`, `quantity`, `price`, `triggerPrice`

**OCO extra fields:** `price1`, `triggerPrice1`, `quantity1`

**AlgoChanakya status:** NOT yet implemented in `backend/app/services/brokers/dhan_order_adapter.py`. Current adapter supports standard orders only.

See [gtt-orders.md](./references/gtt-orders.md) for full request/response schemas and OCO details.

### Option Chain API

Dhan provides a dedicated Option Chain API returning full strike list with Greeks (delta, gamma, theta, vega, IV).

**Endpoints:**
- `POST /v2/optionchain` — full option chain with Greeks
- `GET /v2/expirylist` — available expiry dates for an underlying

**AlgoChanakya status:** NOT yet integrated. AlgoChanakya currently uses SmartAPI for option chain data.

See [option-chain.md](./references/option-chain.md) for request/response schemas and supported underlyings.

### Postback / Webhook & Live Order Updates

Dhan provides two mechanisms for real-time order notifications:

1. **Postback (webhook):** Dhan sends HTTP POST to your configured URL on every order update (trade, rejection, cancellation). Configure in Dhan web portal (no code required for setup).

2. **Live Order Update WebSocket:** `wss://api-order-update.dhan.co` — real-time WebSocket stream of order status changes.

**AlgoChanakya status:** Neither is currently used. AlgoChanakya polls the REST order book for status updates.

See [webhook.md](./references/webhook.md) for postback payload schema, WebSocket connection code, and integration notes.

### Rate Limits (Multi-Tier)

| Resource | Per Second | Per Minute | Per Hour | Per Day |
|----------|-----------|-----------|---------|---------|
| **Order APIs** (place/modify/cancel) | **10** | **250** | **1,000** | **7,000** |
| **Data APIs** (historical, option chain) | **5** | — | — | **100,000** |
| **Quote APIs** (LTP/OHLC/quote REST) | **1** | — | — | — |
| **Non-Trading APIs** (profile, positions, orders-read) | **20** | — | — | — |
| **Option Chain** | 1 per 3 seconds (unique underlying) | — | — | — |

**AlgoChanakya Configuration:** `rate_limiter.py` sets `"dhan": 10` (10 req/sec for orders).

**Note:** Place + Modify + Cancel each count against ALL four order tiers. Hit any one tier → HTTP 429. Max 25 modifications per order total.

### Price Normalization

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** | **RUPEES** | No conversion |
| **WebSocket** | **RUPEES** | No conversion (prices as float) |
| **Historical** | **RUPEES** | No conversion |

Dhan returns all prices in RUPEES. No paise conversion needed.

### Error Codes Quick Reference

| HTTP Status | Error | Cause | Retryable |
|-------------|-------|-------|-----------|
| `400` | Bad Request | Invalid parameters | No |
| `401` | Unauthorized | Invalid/expired token | No |
| `403` | Forbidden | Permissions issue | No |
| `429` | Rate Limited | Exceeded rate limit | Yes - backoff |
| `500` | Server Error | Dhan server issue | Yes - retry |

See [error-codes.md](./references/error-codes.md) for complete error catalog.

---

## 4. AlgoChanakya Integration

### Implementation Status

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

---

## 5. Common Gotchas

1. **Two-tier pricing model** - Trading APIs are FREE, but Data APIs (market data WebSocket) require 25 F&O trades/month OR ₹499/month subscription. Common confusion point.

2. **Little Endian binary** - Use `struct.unpack('<...')` NOT `'>'`. This is unique among Indian brokers.

3. **Numeric IDs only** - No string trading symbols. Must maintain instrument mapping table.

4. **Auth header format** - `access-token: {token}` (hyphenated, lowercase). Not `Authorization: Bearer`.

5. **WebSocket auth via URL params** - Market data WS auth is in query string (`?version=2&token=...&clientId=...&authType=2`), NOT in headers. The Live Order Update WS uses a JSON auth message (`MsgCode: 42`).

6. **WebSocket heartbeat** - Server pings every 10 seconds. Client must respond (most libs handle automatically). Connection drops after 40 seconds of no response.

7. **5000 instruments per WS connection** - Total per connection. Per-subscription-message limit is 100 (Ticker/Quote) but total cap is 5000. Exceeding 5 total connections disconnects the oldest.

8. **200-Depth limit** - Only 1 instrument per connection. Need 5 connections for 5 instruments.

9. **Multi-tier order limits** - Check ALL 4 limits (10/sec, 250/min, 1000/hr, 7000/day). Also max 25 modifications per order.

10. **Static IP whitelisting** - Required for ALL order write operations: `/v2/orders` (POST/PUT/DELETE), `/v2/super/orders` (all 4 methods), `/v2/forever/orders` (create/modify/delete). GET (read) endpoints do NOT require IP whitelisting.

11. **Kill Switch prerequisite** - Cannot activate unless ALL positions are closed and NO pending orders exist. Call sequence: cancel orders → close positions → activate kill switch.

12. **P&L Exit immediate trigger** - Setting `profitValue` below current unrealized P&L triggers exit immediately on the API call.

13. **Data API unlock requirement** - Must execute 25 F&O trades monthly to unlock free data access, otherwise ₹499/month subscription required.

14. **Instrument CSV download** - `https://images.dhan.co/api-data/api-scrip-master.csv` — download daily before market open (~8:30 AM IST).

15. **Exchange segment format** - Uses `NSE_FNO` not `NFO`. Different from Kite/SmartAPI naming.

16. **`availabelBalance` typo** - The `GET /v2/fundlimit` response has a misspelled field: `availabelBalance` (missing second 'l'). This is a known bug that has never been fixed. You MUST use the exact misspelled field name in code.

17. **Historical intraday 90-day limit** - `/v2/charts/intraday` only allows polling 90 days at a time (up to 5 years total, but request max = 90 days).

18. **Option Chain OI lag** - OI data updates slower than LTP. This is why the rate limit is 1 unique request per 3 seconds.

19. **Super Order vs Forever Order** - Super Order = bracket order, same session. Forever Order = GTT, persists until triggered or cancelled (up to 365 days).

---

## 6. Related Skills

| Skill | When to Use |
|-------|-------------|
| `/upstox-expert` | Both modern free-tier APIs — compare unique WS features (Dhan: 200-depth, Upstox: Greeks) |
| `/angelone-expert` | Compare auth approaches — Dhan static token vs SmartAPI auto-TOTP |
| `/fyers-expert` | Compare unique features — Fyers has dual WS + order updates, Dhan has deep depth |
| `/auto-verify` | After any Dhan adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, comparison matrix, CHANGELOG |

**Cross-Broker Comparison:** See [comparison-matrix.md](../broker-shared/comparison-matrix.md) for pricing, rate limits, WebSocket capabilities, and symbol format differences across all 6 brokers.

---

## 7. Maintenance & Auto-Improvement

### Freshness Tracking

| Reference File | Last Verified | Check Frequency |
|---|---|---|
| SKILL.md | 2026-03-18 | Quarterly |
| dhan-overview.md | 2026-03-04 | Quarterly |
| endpoints-catalog.md | 2026-02-26 | Quarterly |
| auth-flow.md | 2026-02-25 | Quarterly |
| error-codes.md | 2026-02-25 | Quarterly |
| websocket-protocol.md | 2026-02-26 | Quarterly |
| symbol-format.md | 2026-02-25 | Quarterly |
| gtt-orders.md | 2026-02-26 | Quarterly |
| option-chain.md | 2026-02-26 | Quarterly |
| webhook.md | 2026-02-26 | Quarterly |
| super-order.md | 2026-02-26 | Quarterly |
| traders-control.md | 2026-02-26 | Quarterly |
| maintenance-log.md | 2026-02-26 | Quarterly |

### Auto-Update Trigger Rules

1. **Error-driven update**: If this skill is invoked 3+ times with FAILED/UNKNOWN outcome for the same error_type (tracked via `post_skill_learning.py` hook → `knowledge.db`), `reflect deep` mode should propose a skill update.
2. **Staleness alert**: If `last_verified` exceeds 90 days, check https://dhanhq.co/docs/v2/ for API changes.
3. **Quarterly review**: Next scheduled review: **June 2026**.

### Version Changelog

| Version | Date | Changes |
|---|---|---|
| 3.1 | 2026-03-18 | Auth flow corrected: dual credential system (API Key permanent + Access Token 24h), TOTP support documented, Static IP whitelisting documented, DevPortal vs trading dashboard clarified, Playwright-based token regeneration flow added, .env configuration documented with all 7 Dhan env vars. Updated SKILL.md auth section and auth-flow.md reference. |
| 3.0 | 2026-03-04 | Restructured: Dhan overview + pricing sections added, DhanHQ API content reorganized as subsection. New `dhan-overview.md` reference file. All existing API content preserved. |
| 2.6 | 2026-02-26 | Added Super Order section + `super-order.md` reference, Trader's Control section + `traders-control.md` reference; corrected WS connection URL (query params, not headers), added heartbeat/disconnect details, corrected 5000 instruments/connection limit; corrected rate limits to 4-tier table (Order/Data/Quote/Non-Trading); added 9 new gotchas; updated `gtt-orders.md`, `webhook.md`, `option-chain.md`, `websocket-protocol.md`, `endpoints-catalog.md` |
| 2.5 | 2026-02-25 | Added Forever Orders (GTT) section, Option Chain section, Postback/Webhook section, Live Order Update WebSocket, `availabelBalance` typo gotcha, corrected multi-tier rate limits (10/sec, 250/min, 1000/hr, 7000/day), expanded Maintenance section with all 9 reference files, added 3 new reference files |
| 2.0 | 2026-02-25 | Implementation status corrected: all 3 adapters fully Implemented (was Planned), auth route + frontend + tests added to status table, maintenance section added |
| 1.0 | 2026-02-16 | Initial creation |

---

## References

- [Dhan Overview](./references/dhan-overview.md) - Company profile, products, pricing, exchanges, differentiators
- [Authentication Flow](./references/auth-flow.md) - Dual credentials (API Key + Access Token), TOTP setup, Static IP, Playwright automation
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints
- [WebSocket Protocol](./references/websocket-protocol.md) - Little Endian binary protocol
- [Error Codes](./references/error-codes.md) - Error code reference
- [Symbol Format](./references/symbol-format.md) - security_id format
- [Super Order](./references/super-order.md) - Bracket order (entry + target + SL + trail)
- [Trader's Control](./references/traders-control.md) - Kill Switch and P&L Exit APIs
- [Forever Orders (GTT)](./references/gtt-orders.md) - GTT/GTC order management
- [Option Chain](./references/option-chain.md) - Option chain API with Greeks
- [Webhook / Postback](./references/webhook.md) - Order update notifications
- [Maintenance Log](./references/maintenance-log.md) - API change tracker and review history
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
