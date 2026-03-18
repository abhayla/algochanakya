# Broker Data Implementation Checklist

**Purpose:** Per-broker checklist of everything needed for market data (live ticks + OHLC) to work at both Platform-Level and User-Level.
**Last Updated:** 2026-03-02
**Scope:** Documentation only — no code implementation.

**References:**
- [Broker Abstraction Architecture](broker-abstraction.md)
- [Working Doc](Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md)
- [TICKER-DESIGN-SPEC](../decisions/TICKER-DESIGN-SPEC.md)
- [Comparison Matrix](../../.claude/skills/broker-shared/comparison-matrix.md)
- [Implementation Checklist](../IMPLEMENTATION-CHECKLIST.md) (phases & tasks)
- [Autonomous Implementation Plan](../guides/AUTONOMOUS-IMPLEMENTATION-PLAN.md) (session-by-session execution plan)

---

## Table of Contents

1. [Quick Status Matrix](#quick-status-matrix)
2. [Cross-Cutting Infrastructure](#cross-cutting-infrastructure)
3. [Broker #1: SmartAPI (Angel One) — Platform Primary](#broker-1-smartapi-angel-one--platform-primary)
4. [Broker #2: Dhan — Platform Fallback #2](#broker-2-dhan--platform-fallback-2)
5. [Broker #3: Fyers — Platform Fallback #3](#broker-3-fyers--platform-fallback-3)
6. [Broker #4: Paytm Money — Platform Fallback #4](#broker-4-paytm-money--platform-fallback-4)
7. [Broker #5: Upstox — Platform Fallback #5](#broker-5-upstox--platform-fallback-5)
8. [Broker #6: Kite Connect (Zerodha) — Platform Fallback #6 (Last Resort)](#broker-6-kite-connect-zerodha--platform-fallback-6-last-resort)

---

## Quick Status Matrix

| Component | SmartAPI | Dhan | Fyers | Paytm | Upstox | Kite |
|-----------|---------|------|-------|-------|--------|------|
| **Failover Rank** | #1 (Primary) | #2 | #3 | #4 | #5 | #6 (Last Resort) |
| **Platform Cost** | FREE | FREE† | FREE | FREE | ₹499/mo | ₹500/mo |
| **Auth Adapter** | ✅ Done | ✅ Done (173L) | ✅ Done (205L) | ✅ Done (250L) | ✅ Done (194L) | ✅ Done |
| **MarketData Adapter** | ✅ Done (616L) | ✅ Done (813L) | ✅ Done (695L) | ✅ Done (581L) | ✅ Done (567L) | ✅ Done (422L) |
| **Ticker Adapter (WS)** | ✅ Done | ✅ Done | ✅ Done | ✅ Done | ✅ Done | ✅ Done |
| **Ticker Infrastructure** | ✅ Pool+Router+Health+Failover | — | — | — | — | — |
| **Order Adapter** | ✅ Done | ✅ Done (446L) | ✅ Done (467L) | ✅ Done (437L) | ✅ Done (493L) | ✅ Done (584L) |
| **Symbol Converter** | ✅ Done | ⬜ Stub | ⬜ Stub | ⬜ Stub | ⬜ Stub | ✅ (Canonical) |
| **Token Manager** | ✅ Done | ✅ Done | ✅ Done | ✅ Done | ✅ Done | ✅ Done |
| **Instrument Master** | ✅ Done | ✅ Done | ✅ Done | ✅ Done | ✅ Done | ✅ Done |
| **Rate Limiter Config** | ✅ Done | ✅ Done (10/s) | ✅ Done (10/s, 1/s hist) | ✅ Done (10/s) | ✅ Done (25/s) | ✅ Done (3/s) |
| **Factory Registration** | ✅ Done | ✅ Done | ✅ Done | ✅ Done | ✅ Done | ✅ Done |
| **Platform Creds in .env** | ✅ Done | ⬜ Todo | ⬜ Todo | ⬜ Todo | ⬜ Todo | ❌ N/A (OAuth) |
| **Frontend Settings UI** | ✅ Done | ✅ Done (194L) | ✅ Done (154L) | ✅ Done (252L) | ✅ Done (155L) | ✅ Done (148L) |
| **Legacy Cleanup** | ✅ Deprecated | — | — | — | — | ✅ Deprecated |

**Legend:** ✅ Done | ⬜ Stub (raises NotImplementedError) | ⬜ Todo | ❌ Not Applicable
**†** Dhan Data API is FREE with 25+ F&O trades/month, else ₹499/month

---

## Cross-Cutting Infrastructure

These are shared components that all brokers rely on. Most are already built but need extension for new brokers.

### Already Built (extend for new brokers)

| Component | File | What Needs Extension |
|-----------|------|---------------------|
| `MarketDataBrokerAdapter` interface | `market_data/market_data_base.py` | None — implement per broker |
| `TickerServiceBase` interface | `market_data/ticker_base.py` | None — implement per broker |
| `SymbolConverter` | `market_data/symbol_converter.py` | Add `parse_{broker}()` / `format_{broker}()` per new broker |
| `TokenManager` + `TokenManagerFactory` | `market_data/token_manager.py` | Register new broker managers |
| `RateLimiter` | `market_data/rate_limiter.py` | Add broker-specific rate limit configs |
| `MarketDataFactory` | `market_data/factory.py` | Add `_create_{broker}_adapter()` + register in factory |
| Unified Models (`UnifiedQuote`, `OHLCVCandle`, `Instrument`) | `market_data/market_data_base.py` | None — all adapters convert to these |
| Credential Dataclasses | `market_data/market_data_base.py` | Already defined for all 6 brokers |
| `broker_instrument_tokens` DB table | Alembic migration | Add broker-specific rows during instrument sync |
| Market data exceptions | `market_data/exceptions.py` | Add broker-specific error codes if needed |

### Built (Phase T1–T5)

| Component | Status | Details |
|-----------|--------|---------|
| **Failover Controller** | ✅ Done | `ticker/failover.py` — make-before-break failover with configurable priority chain |
| **Health Monitor** | ✅ Done | `ticker/health.py` — 5s heartbeat, per-adapter scoring, triggers failover |
| **Ticker Pool** | ✅ Done | `ticker/pool.py` — adapter lifecycle, ref-counted subscriptions, integrated credentials |
| **Ticker Router** | ✅ Done | `ticker/router.py` — user fan-out, maps subscriptions to correct broker adapter |
| **Ticker API Routes** | ✅ Done | `api/routes/ticker.py` — `/api/ticker/health`, `/api/ticker/failover/status` |

### Partially Built

| Component | Status | Details |
|-----------|--------|---------|
| **`MarketDataRouter`** | 🟡 Partial | Dual-path routing exists via factory pattern; full `MarketDataRouter` class with failover pending |
| **Source Indicator API** | ✅ Done | `/api/ticker/health`, `/api/ticker/failover/status` routes in `ticker.py` |
| **Frontend: Broker Selection UI** | ✅ Done | Settings page with per-broker settings components (6 Vue files) |
| **User Preferences API** | ✅ Done | `/api/settings` endpoints for broker preferences |

### Not Yet Built

| Component | Description | Blocked By |
|-----------|-------------|------------|
| **Platform Credential Manager** | Reads shared credentials from `.env`, handles auto-refresh loops (e.g., SmartAPI 5 AM refresh, Fyers midnight refresh) | Needs broker-specific refresh strategies |
| **Frontend: Source Indicator Badge** | Shows active data source + failover notifications on data screens | Needs UI design |
| **Frontend: Persistent Banner** | "Use your own API key" banner on Dashboard, Watchlist, Option Chain, Positions | UI component, no backend dependency |
| **Instrument Sync Scheduler** | Daily job to download instrument masters for all active brokers and populate `broker_instrument_tokens` | Extends existing SmartAPI instrument sync |
| **Symbol Converter (4 brokers)** | `parse_*/format_*` for Dhan, Fyers, Paytm, Upstox are stubs (`NotImplementedError`) | Needs per-broker format specs |

---

## Broker #1: SmartAPI (Angel One) — Platform Primary

**Rank:** #1 | **Cost:** FREE | **Skill:** `/angelone-expert`
**Status:** ✅ Market Data Adapter complete, ✅ Ticker Adapter complete (Phase T4)

### Authentication

> **Credential distinction:** SmartAPI has TWO separate auth paths:
> 1. **Platform-level auth** — uses `backend/.env` credentials (`ANGEL_API_KEY`, `ANGEL_CLIENT_ID`, `ANGEL_PIN`, `ANGEL_TOTP_SECRET`). Serves ALL users by default. These are NOT user login credentials.
> 2. **User-level auth** — uses encrypted credentials from `smartapi_credentials` table, configured by the user in Settings page. Optional upgrade from platform default.
>
> Login credentials (what the user types on the Login page) are used once, not stored, and produce a JWT session token.

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ✅ Done | Auto-TOTP via `smartapi_auth.py` (client_id + PIN + TOTP secret) |
| Platform credentials in `.env` | ✅ Done | `ANGEL_API_KEY`, `ANGEL_CLIENT_ID`, `ANGEL_PIN`, `ANGEL_TOTP_SECRET` — shared platform credentials, NOT user login creds |
| Token types | ✅ Done | 3 tokens: `jwtToken` (REST), `refreshToken`, `feedToken` (WebSocket) |
| Token lifetime | ✅ Done | Until 5 AM IST daily auto-logout |
| Auto-refresh loop | ⬜ Todo | Needs: refresh 30 min before 5 AM IST expiry. Currently manual re-auth. |
| User-level auth (own credentials) | ✅ Done | `SmartAPISettings.vue` UI exists, stores encrypted in `smartapi_credentials` table — optional upgrade path |

### Market Data REST API

| Item | Status | Details |
|------|--------|---------|
| `MarketDataBrokerAdapter` implementation | ✅ Done | `smartapi_adapter.py` (587 lines) |
| `get_quote()` | ✅ Done | Fetches quotes, converts paise → rupees |
| `get_ltp()` | ✅ Done | LTP endpoint |
| `get_historical()` | ✅ Done | OHLC with interval mapping |
| `get_instruments()` / `search_instruments()` | ✅ Done | Instrument master download + search |
| Price normalization (paise ÷ 100) | ✅ Done | All prices converted to rupees (Decimal) |
| Rate limiting (1 req/sec) | ✅ Done | RateLimiter configured |
| Factory registration | ✅ Done | Registered in `market_data/factory.py` |

### WebSocket Live Ticks

| Item | Status | Details |
|------|--------|---------|
| Legacy ticker (`smartapi_ticker.py`) | ✅ Deprecated | Moved to `services/deprecated/`. See [Migration Guide](../guides/TICKER-MIGRATION.md) |
| Phase 4 ticker adapter | ✅ Done | `ticker/adapters/smartapi.py` — `SmartAPITickerAdapter` implementing `TickerAdapter` ABC |
| Binary protocol parser | ✅ Done | Extracted to new adapter |
| Paise → rupees in ticks | ✅ Done | In new adapter |
| Thread → asyncio bridge | ✅ Done | In new adapter |
| Connection limits | — | 3 connections × 3,000 tokens = **9,000 tokens** |
| Subscription mode | — | Mode 2 (quote) with `[exchange_type, token]` format |

### Symbol Format

| Item | Status | Details |
|------|--------|---------|
| `SymbolConverter.parse_smartapi()` | ✅ Done | Parses `NIFTY27FEB2525000CE` (DDMONYY format) |
| `SymbolConverter.format_smartapi()` | ✅ Done | Converts canonical → SmartAPI format |
| Token manager mapping | ✅ Done | Maps SmartAPI string tokens ↔ canonical |
| Index token mapping | — | NIFTY = `"99926000"`, BANKNIFTY = `"99926009"` (string tokens) |

### Instrument Master

| Item | Status | Details |
|------|--------|---------|
| Download URL | ✅ Done | `https://margincalculator.angelbroking.com/.../OpenAPIScripMaster.json` |
| Format | — | JSON (~50MB) |
| Parse + populate `broker_instrument_tokens` | ✅ Done | Via instrument sync on startup |

### Broker-Specific Quirks

- **PAISE everywhere** — WebSocket + historical + quotes all return paise. Must ÷ 100.
- **String tokens for indices** — Unlike Kite (integer), SmartAPI uses string tokens like `"99926000"`.
- **Auto-TOTP** — Unique advantage: no manual login needed. Uses `pyotp` with stored TOTP secret.
- **Daily 5 AM expiry** — Tokens die at 5 AM IST. Platform needs pre-market refresh loop.

---

## Broker #2: Dhan — Platform Fallback #2

**Rank:** #2 | **Cost:** FREE† | **Skill:** `/dhan-expert`
**Status:** ✅ Complete — Auth, MarketData adapter (813L), Ticker adapter, Order adapter (446L), Frontend UI (194L) all done

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ✅ Done | `dhan_auth.py` (173 lines) — static API token auth |
| Platform credentials in `.env` | ⬜ Todo | Need: `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN` |
| Token type | — | Single static access token (never expires unless revoked) |
| Token lifetime | — | **Never expires** — simplest for platform |
| Auto-refresh loop | ❌ N/A | Static token, no refresh needed |
| User-level auth UI | ✅ Done | `DhanSettings.vue` (194 lines) — Client ID + Access Token fields |
| Credential encryption + storage | ✅ Done | Encrypted credentials stored via broker_connections |

### Market Data REST API

| Item | Status | Details |
|------|--------|---------|
| `DhanMarketDataAdapter` class | ✅ Done | `market_data/dhan_adapter.py` (813 lines) |
| `get_quote()` | ✅ Done | `GET /marketfeed/ltp` — prices in rupees (no conversion) |
| `get_ltp()` | ✅ Done | Same endpoint, extract LTP only |
| `get_historical()` | ✅ Done | `GET /charts/historical` |
| `get_instruments()` / `search_instruments()` | ✅ Done | Parse instrument master CSV |
| Price normalization | — | **Rupees** (no conversion needed) |
| Rate limiting (10 req/sec) | ✅ Done | Dhan config in RateLimiter |
| Factory registration | ✅ Done | Registered in `market_data/factory.py` |

### WebSocket Live Ticks

| Item | Status | Details |
|------|--------|---------|
| Ticker adapter | ✅ Done | `ticker/adapters/dhan.py` (575 lines) |
| Binary protocol parser | ✅ Done | **Little-endian** binary — `struct.unpack('<...')` (unique among brokers) |
| Connection limits | — | 100 tokens/connection × 5 connections = **500 tokens** (lowest capacity) |
| Thread → asyncio bridge | ✅ Done | Threading-based with asyncio bridge |
| Price normalization in ticks | — | Rupees (no conversion) |

### Symbol Format

| Item | Status | Details |
|------|--------|---------|
| `SymbolConverter.parse_dhan()` | ⬜ Stub | `NotImplementedError` — numeric `security_id` only, no string symbols |
| `SymbolConverter.format_dhan()` | ⬜ Stub | `NotImplementedError` — canonical → numeric security_id (requires full CSV lookup) |
| Token manager mapping | ✅ Done | Map Dhan `security_id` ↔ canonical symbol |
| Conversion difficulty | — | **Very High** — numeric-only, requires full instrument master CSV mapping |

### Instrument Master

| Item | Status | Details |
|------|--------|---------|
| Download URL | — | `https://images.dhan.co/api-data/api-scrip-master.csv` |
| Format | — | CSV |
| Parse + populate `broker_instrument_tokens` | ✅ Done | Map `security_id` to canonical symbols via adapter |

### Broker-Specific Quirks

- **Static token never expires** — Simplest credential management for platform.
- **Numeric-only symbols** — `security_id` is just a number. No string symbol at all. Full CSV lookup required for every conversion.
- **Little-endian binary WebSocket** — Only Dhan uses little-endian. All others use big-endian or JSON/Protobuf.
- **500 token capacity** — Lowest among all brokers. Best used for long-tail instruments only.
- **200-level market depth** — Unique feature (but 1 instrument per connection), useful for advanced users.
- **Data API pricing** — FREE with 25+ F&O trades/month on Dhan, otherwise ₹499/month.

---

## Broker #3: Fyers — Platform Fallback #3

**Rank:** #3 | **Cost:** FREE | **Skill:** `/fyers-expert`
**Status:** ✅ Complete — Auth (205L), MarketData adapter (695L), Ticker adapter, Order adapter (467L), Frontend UI (154L) all done

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ✅ Done | `fyers_auth.py` (205 lines) — OAuth 2.0 standard flow |
| Platform credentials in `.env` | ⬜ Todo | Need: `FYERS_APP_ID`, `FYERS_SECRET_KEY`, `FYERS_REDIRECT_URL` |
| Token type | — | `access_token` (standard OAuth) |
| Token lifetime | — | Until **midnight IST** (daily expiry) |
| Auto-refresh loop | ⬜ Todo | Needs: refresh token flow before midnight IST |
| Auth header format | — | **Unique:** `{app_id}:{access_token}` (colon-separated, not Bearer) |
| User-level auth UI | ✅ Done | `FyersSettings.vue` (154 lines) — OAuth redirect flow |
| Credential encryption + storage | ✅ Done | Encrypted credentials stored via broker_connections |

### Market Data REST API

| Item | Status | Details |
|------|--------|---------|
| `FyersMarketDataAdapter` class | ✅ Done | `market_data/fyers_adapter.py` (695 lines) |
| `get_quote()` | ✅ Done | `GET /data/quotes` — prices in rupees |
| `get_ltp()` | ✅ Done | Same endpoint, extract LTP |
| `get_historical()` | ✅ Done | `GET /data/history` — **1 req/sec** for historical (stricter than general 10/sec) |
| `get_instruments()` / `search_instruments()` | ✅ Done | Parse per-exchange CSV files |
| Price normalization | — | **Rupees** (no conversion needed) |
| Rate limiting | ✅ Done | 10 req/sec general, **1 req/sec historical** (dual rate limit) |
| Factory registration | ✅ Done | Registered in `market_data/factory.py` |

### WebSocket Live Ticks

| Item | Status | Details |
|------|--------|---------|
| Ticker adapter | ✅ Done | `ticker/adapters/fyers.py` — full implementation (2026-02-17) |
| Protocol parser | ✅ Done | JSON SymbolUpdate/DepthUpdate — `_parse_tick()` with Decimal rupees |
| Dual WebSocket system | ✅ Done | `FyersDataSocket` used; `FyersOrderSocket` out of scope for market data path |
| Connection limits | — | **5,000 symbols/connection** (v3.0.0, Feb 2026 upgrade) |
| Thread bridge | ✅ Done | `keep_running()` on daemon thread → `_dispatch_from_thread()` to asyncio |
| Auth in WebSocket | ✅ Done | `{app_id}:{access_token}` colon-separated format |
| Tests | ✅ Done | `tests/backend/brokers/test_fyers_ticker_adapter.py` — 59 tests |

### Symbol Format

| Item | Status | Details |
|------|--------|---------|
| `SymbolConverter.parse_fyers()` | ⬜ Stub | `NotImplementedError` — `NSE:{SYMBOL}` format (e.g., `NSE:NIFTY2522725000CE`) |
| `SymbolConverter.format_fyers()` | ⬜ Stub | `NotImplementedError` — canonical → `NSE:{symbol}` (just add prefix) |
| Token manager mapping | ✅ Done | Map Fyers symbols ↔ canonical |
| Conversion difficulty | — | **Trivial** — just strip/add `NSE:` prefix |
| Index symbols | — | `NSE:NIFTY50-INDEX`, `NSE:NIFTYBANK-INDEX` |

### Instrument Master

| Item | Status | Details |
|------|--------|---------|
| Download URL | — | `https://public.fyers.in/sym_details/{exchange}.csv` (per exchange) |
| Format | — | CSV (per exchange: NSE, NFO, BSE, etc.) |
| Parse + populate `broker_instrument_tokens` | ✅ Done | Map Fyers `NSE:` format to canonical via adapter |

### Broker-Specific Quirks

- **JSON WebSocket** — Simplest parsing, no binary protocol. Ideal for quick implementation.
- **5,000 symbol capacity** — v3.0.0 (Feb 2026) upgraded from 200. Second-highest capacity.
- **Dual WebSocket** — `FyersDataSocket` for prices + `FyersOrderSocket` for order updates. Only need data socket for market data path.
- **Dual rate limit** — General API: 10/sec. Historical data: **1/sec** (must handle separately).
- **Midnight expiry** — Token expires at midnight IST. Platform needs pre-midnight refresh.
- **Unique auth header** — `{app_id}:{access_token}` colon-separated, not standard Bearer format.
- **FREE** — No cost for both market data and orders.

---

## Broker #4: Paytm Money — Platform Fallback #4

**Rank:** #4 | **Cost:** FREE | **Skill:** `/paytm-expert`
**Status:** ✅ Complete — Auth (250L), MarketData adapter (581L), Ticker adapter (100 tests), Order adapter (437L), Frontend UI (252L) all done

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ✅ Done | `paytm_auth.py` (250 lines) — OAuth 2.0 with 3 JWTs |
| Platform credentials in `.env` | ⬜ Todo | Need: `PAYTM_API_KEY`, `PAYTM_API_SECRET`, `PAYTM_REDIRECT_URL` |
| Token types | — | **3 JWTs:** `access_token` (REST), `read_access_token` (portfolio), `public_access_token` (WebSocket) |
| Token lifetime | — | 1 trading day |
| Auto-refresh loop | ⬜ Todo | Daily refresh needed. Must refresh all 3 tokens. |
| Custom header format | — | `x-jwt-token: {token}` (not standard Authorization header) |
| User-level auth UI | ✅ Done | `PaytmSettings.vue` (252 lines) — OAuth redirect flow |
| Credential encryption + storage | ✅ Done | Encrypted credentials stored via broker_connections |

### Market Data REST API

| Item | Status | Details |
|------|--------|---------|
| `PaytmMarketDataAdapter` class | ✅ Done | `market_data/paytm_adapter.py` (581 lines) |
| `get_quote()` | ✅ Done | Scrip margins endpoint — prices in rupees |
| `get_ltp()` | ✅ Done | Extract LTP from quote |
| `get_historical()` | ✅ Done | `GET /accounts/v1/candle/{exchange}/{token}/{resolution}` |
| `get_instruments()` / `search_instruments()` | ✅ Done | Via API call (not static CSV) |
| Price normalization | — | **Rupees** (no conversion needed) |
| Rate limiting (10 req/sec) | ✅ Done | Paytm config in RateLimiter |
| Factory registration | ✅ Done | Registered in `market_data/factory.py` |

### WebSocket Live Ticks

| Item | Status | Details |
|------|--------|---------|
| Ticker adapter | ✅ Done | File: `ticker/adapters/paytm.py` — full implementation |
| Protocol parser | ✅ Done | **JSON** — LTP + FULL modes, batch list support |
| Connection limits | — | **200 instruments/connection** (lowest capacity among all brokers) |
| asyncio-native | ✅ Done | `_ws_receive_loop` + `_ws_ping_loop` async tasks, no thread bridge |
| WebSocket auth | ✅ Done | Uses `public_access_token` as `?x_jwt_token=` query param |
| Ping keep-alive | ✅ Done | 30s WS ping loop prevents idle disconnect |
| Unit tests | ✅ Done | 100 tests — `test_paytm_ticker_adapter.py` |

### Symbol Format

| Item | Status | Details |
|------|--------|---------|
| `SymbolConverter.parse_paytm()` | ⬜ Stub | `NotImplementedError` — RIC format: `{exchange_segment}.{exchange_type}!{security_id}` |
| `SymbolConverter.format_paytm()` | ⬜ Stub | `NotImplementedError` — canonical → RIC format (requires full mapping) |
| Token manager mapping | ✅ Done | Map Paytm RIC/security_id ↔ canonical |
| Conversion difficulty | — | **Very High** — RIC format requires full instrument master mapping |

### Instrument Master

| Item | Status | Details |
|------|--------|---------|
| Source | — | Via API call (not static file download) |
| Format | — | JSON API response |
| Parse + populate `broker_instrument_tokens` | ✅ Done | Map RIC format to canonical symbols via adapter |

### Broker-Specific Quirks

- **3 JWT tokens** — Most complex auth. Each token has different scope: REST, portfolio, WebSocket.
- **`public_access_token` for WebSocket** — Common mistake: using `access_token` instead. Will fail silently.
- **Custom header** — `x-jwt-token` instead of standard `Authorization: Bearer`.
- **200 instrument limit** — Lowest WebSocket capacity. Only viable for targeted instruments.
- **RIC format symbols** — Complex format requiring full instrument master mapping.
- **Least mature API** — Occasional breaking changes, limited F&O coverage.
- **FREE** — No cost, which compensates for complexity.

---

## Broker #5: Upstox — Platform Fallback #5

**Rank:** #5 | **Cost:** ₹499/month | **Skill:** `/upstox-expert`
**Status:** ✅ Complete — Auth (194L), MarketData adapter (567L), Ticker adapter (92 tests), Order adapter (493L), Frontend UI (155L) all done

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ✅ Done | `upstox_auth.py` (194 lines) — OAuth 2.0 with extended token (~1 year) |
| Platform credentials in `.env` | ⬜ Todo | Need: `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`, `UPSTOX_REDIRECT_URL` |
| Token type | — | `access_token` (extended ~1 year for read-only) |
| Token lifetime | — | **~1 year** (extended token, simplifies credential management) |
| Auto-refresh loop | ⬜ Todo | Minimal — only needed annually. Standard OAuth refresh. |
| User-level auth UI | ✅ Done | `UpstoxSettings.vue` (155 lines) — OAuth redirect flow |
| Credential encryption + storage | ✅ Done | Encrypted credentials stored via broker_connections |

### Market Data REST API

| Item | Status | Details |
|------|--------|---------|
| `UpstoxMarketDataAdapter` class | ✅ Done | `market_data/upstox_adapter.py` (567 lines) |
| `get_quote()` | ✅ Done | `GET /market-quote/quotes` — prices in rupees |
| `get_ltp()` | ✅ Done | `GET /market-quote/ltp` |
| `get_historical()` | ✅ Done | `GET /historical-candle/{instrument_key}/{interval}/{to_date}` |
| `get_instruments()` / `search_instruments()` | ✅ Done | Parse gzip CSV instrument master |
| Price normalization | — | **Rupees** (no conversion needed) |
| Rate limiting (25 req/sec) | ✅ Done | Fastest rate limit — config in RateLimiter |
| Factory registration | ✅ Done | Registered in `market_data/factory.py` |

### WebSocket Live Ticks

| Item | Status | Details |
|------|--------|---------|
| Ticker adapter | ✅ Done | File: `ticker/adapters/upstox.py` — full implementation, 92 tests |
| Protocol parser | ✅ Done | Protobuf parsed via runtime descriptor (inline schema, no compiled _pb2 needed) |
| Proto definition file | ✅ Done | Schema embedded inline in `upstox.py` via `google.protobuf.descriptor_pb2` |
| Protobuf Python dependency | ✅ Done | `google-protobuf` available; `httpx` used for REST auth call |
| Connection limits | — | 1 connection per token, **1,500-5,000 tokens/connection** |
| asyncio-native | ✅ Done | No thread bridge — `_ws_receive_loop()` + `_dispatch_async()` |
| Option Greeks via WebSocket | ✅ Done | **Unique feature** — Greeks parsed from `OptionGreeks` proto message |
| Token map loading | ✅ Done | `load_token_map({canonical: instrument_key_str})` — same pattern as Dhan |
| Authorized WS URL | ✅ Done | `_fetch_authorized_ws_url()` calls REST /v2/feed/market-data-feed/authorize |

### Symbol Format

| Item | Status | Details |
|------|--------|---------|
| `SymbolConverter.parse_upstox()` | ⬜ Stub | `NotImplementedError` — `{EXCHANGE}_{SEGMENT}\|{instrument_token}` (e.g., `NSE_FO\|12345`) |
| `SymbolConverter.format_upstox()` | ⬜ Stub | `NotImplementedError` — canonical → instrument_key (requires instrument master lookup) |
| Token manager mapping | ✅ Done | Map Upstox instrument_key ↔ canonical |
| Conversion difficulty | — | **High** — pipe-separated format, requires instrument master lookup |

### Instrument Master

| Item | Status | Details |
|------|--------|---------|
| Download URL | — | `https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz` |
| Format | — | **Gzip CSV** (compressed, needs decompression) |
| Parse + populate `broker_instrument_tokens` | ✅ Done | Decompress gzip → parse CSV → map to canonical via adapter |

### Broker-Specific Quirks

- **₹499/month** — Only paid broker after Kite in the fallback chain. Platform pays.
- **Protobuf WebSocket** — Unique among Indian brokers. Higher complexity but more efficient binary format.
- **Extended token (~1 year)** — Simplest refresh cycle. Good for platform credentials.
- **25 req/sec rate limit** — Fastest among all brokers. Excellent for burst requests.
- **Option Greeks in ticks** — Unique feature. Can provide real-time Greeks without calculation.
- **1 connection per token** — Cannot pool connections like SmartAPI/Kite (3 each).
- **Recently became paid** — Changed from free to ₹499/mo. Moved from #3 to #5 in failover chain.

---

## Broker #6: Kite Connect (Zerodha) — Platform Fallback #6 (Last Resort)

**Rank:** #6 (Last Resort) | **Cost:** ₹500/month (Connect tier) | **Skill:** `/zerodha-expert`
**Status:** ✅ Market Data Adapter complete, ✅ Ticker Adapter complete (Phase T4)

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ✅ Done | OAuth 2.0 redirect flow |
| Platform credentials in `.env` | ❌ N/A | **Cannot use as platform source** — requires per-user OAuth, no auto-login |
| Token type | ✅ Done | `access_token` via OAuth callback |
| Token lifetime | — | 1 trading day (expires ~6 AM, no auto-refresh) |
| Auto-refresh loop | ❌ N/A | No refresh mechanism — user must re-login daily via OAuth |
| User-level auth UI | ✅ Done | `KiteSettings.vue` (148 lines) — OAuth redirect flow |
| Kite Connect vs Personal API | — | Personal API (FREE) = orders only, **no market data**. Connect (₹500/mo) = full access. |

### Market Data REST API

| Item | Status | Details |
|------|--------|---------|
| `KiteMarketDataAdapter` class | ✅ Done | Implemented in Phase 3 |
| `get_quote()` | ✅ Done | `GET /market-data/quote` — prices in paise |
| `get_ltp()` | ✅ Done | LTP endpoint |
| `get_historical()` | ✅ Done | `GET /instruments/historical/{token}/{interval}` |
| `get_instruments()` / `search_instruments()` | ✅ Done | CSV instrument master |
| Price normalization (paise ÷ 100) | ✅ Done | All prices converted to rupees (Decimal) |
| Rate limiting (3 req/sec) | ✅ Done | RateLimiter configured |
| Factory registration | ✅ Done | Registered in factory |

### WebSocket Live Ticks

| Item | Status | Details |
|------|--------|---------|
| Legacy ticker (`kite_ticker.py`) | ✅ Deprecated | Moved to `services/deprecated/`. See [Migration Guide](../guides/TICKER-MIGRATION.md) |
| Phase 4 ticker adapter | ✅ Done | `ticker/adapters/kite.py` — `KiteTickerAdapter` implementing `TickerAdapter` ABC |
| Binary protocol parser | ✅ Done | Built into `kiteconnect` library, wrapped by adapter |
| Paise → rupees in ticks | ✅ Done | In new adapter |
| Connection limits | — | 3 connections × 3,000 tokens = **9,000 tokens** |

### Symbol Format

| Item | Status | Details |
|------|--------|---------|
| `SymbolConverter` for Kite | ✅ Done | **Kite IS the canonical format** — identity conversion (no transform needed) |
| Token manager mapping | ✅ Done | Integer tokens (e.g., 256265 for NIFTY) |
| Index tokens | — | NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801, SENSEX=265 |

### Instrument Master

| Item | Status | Details |
|------|--------|---------|
| Download URL | ✅ Done | `https://api.kite.trade/instruments` |
| Format | — | CSV (~10MB) |
| Parse + populate `broker_instrument_tokens` | ✅ Done | Maps integer tokens to canonical symbols |

### Broker-Specific Quirks

- **Cannot be platform-default** — OAuth requires per-user browser login. No system credential support.
- **Last resort only** — ₹500/month cost + OAuth limitation. Used only if all 5 other brokers fail.
- **Personal API is useless for data** — Free tier returns 403 on market data endpoints. Must use Connect tier.
- **Canonical format** — Kite symbol format IS the internal canonical format. Zero conversion overhead.
- **PAISE prices** — Like SmartAPI, returns paise. Must ÷ 100.
- **No refresh token** — Access token expires ~6 AM, user must re-login. Platform cannot auto-refresh.
- **Most mature SDK** — `kiteconnect` Python library is well-maintained with good docs.

---

## Implementation Status Summary

All 6 brokers are fully implemented with auth, market data adapters, ticker adapters, order adapters, and frontend settings UI.

| Broker | Status | Auth | MarketData | Ticker | Orders | Frontend |
|--------|--------|------|------------|--------|--------|----------|
| **SmartAPI** | ✅ Complete | ✅ Auto-TOTP | ✅ 616L | ✅ 353L | ✅ 467L | ✅ 581L |
| **Kite** | ✅ Complete | ✅ OAuth | ✅ 422L | ✅ 313L | ✅ 584L | ✅ 148L |
| **Dhan** | ✅ Complete | ✅ Static Token (173L) | ✅ 813L | ✅ 575L | ✅ 446L | ✅ 194L |
| **Fyers** | ✅ Complete | ✅ OAuth (205L) | ✅ 695L | ✅ 410L | ✅ 467L | ✅ 154L |
| **Paytm** | ✅ Complete | ✅ OAuth 3 JWTs (250L) | ✅ 581L | ✅ 618L | ✅ 437L | ✅ 252L |
| **Upstox** | ✅ Complete | ✅ OAuth ~1yr (194L) | ✅ 567L | ✅ 820L | ✅ 493L | ✅ 155L |

### Remaining Work

| Item | Scope | Priority |
|------|-------|----------|
| **Symbol Converter stubs** | `parse_*/format_*` for Dhan, Fyers, Paytm, Upstox raise `NotImplementedError` | Medium — needed for cross-broker symbol resolution |
| **Platform Credentials** | `.env` entries for Dhan, Fyers, Paytm, Upstox (platform-level shared keys) | Medium — needed for platform-default data path |
| **Auto-Refresh Loops** | Pre-market credential refresh (SmartAPI 5 AM, Fyers midnight, Paytm daily) | Medium — needed for unattended platform operation |
| **Instrument Sync Scheduler** | Daily job to download all 6 instrument masters | Low — manual sync works for now |
| **Source Indicator Badge** | Frontend badge showing active data source + failover notifications | Low — nice-to-have UX |
