# Broker Data Implementation Checklist

**Purpose:** Per-broker checklist of everything needed for market data (live ticks + OHLC) to work at both Platform-Level and User-Level.
**Last Updated:** 2026-02-16
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
| **Auth Adapter** | ✅ Done | ⬜ Todo | ⬜ Todo | ⬜ Todo | ⬜ Todo | ✅ Done |
| **MarketData Adapter** | ✅ Done | ⬜ Todo | ⬜ Todo | ⬜ Todo | ⬜ Todo | ✅ Done |
| **Ticker Adapter (WS)** | ✅ Done | ✅ Done | ✅ Done | ✅ Done | ✅ Done | ✅ Done |
| **Ticker Infrastructure** | ✅ Pool+Router+Health+Failover | — | — | — | — | — |
| **Symbol Converter** | ✅ Done | ⬜ Todo | ⬜ Todo | ⬜ Todo | ⬜ Todo | ✅ (Canonical) |
| **Token Manager** | ✅ Done | ⬜ Todo | ⬜ Todo | ⬜ Todo | ⬜ Todo | ✅ Done |
| **Instrument Master** | ✅ Done | ⬜ Todo | ⬜ Todo | ⬜ Todo | ⬜ Todo | ✅ Done |
| **Rate Limiter Config** | ✅ Done | ⬜ Todo | ⬜ Todo | ⬜ Todo | ⬜ Todo | ✅ Done |
| **Factory Registration** | ✅ Done | ⬜ Todo | ⬜ Todo | ⬜ Todo | ⬜ Todo | ✅ Done |
| **Platform Creds in .env** | ✅ Done | ⬜ Todo | ⬜ Todo | ⬜ Todo | ⬜ Todo | ❌ N/A (OAuth) |
| **Frontend Settings UI** | ✅ Done | ⬜ Todo | ⬜ Todo | ⬜ Todo | ⬜ Todo | ✅ Partial |
| **Legacy Cleanup** | ✅ Deprecated | — | — | — | — | ✅ Deprecated |

**Legend:** ✅ Done | 🟡 Stub (interface only) | ⬜ Todo | ❌ Not Applicable
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

### Not Yet Built (cross-cutting, needed before/during broker work)

| Component | Description | Blocked By |
|-----------|-------------|------------|
| **`MarketDataRouter`** | Dual-path routing (platform default → user override). Decides which adapter to use per request. | Architecture finalized in Working Doc, implementation pending |
| **Platform Credential Manager** | Reads shared credentials from `.env`, handles auto-refresh loops (e.g., SmartAPI 5 AM refresh, Fyers midnight refresh) | Needs broker-specific refresh strategies |
| **Source Indicator API** | `GET /api/market-data/source` — returns active data source + failover status | Needed for frontend badge |
| **Frontend: Persistent Banner** | "Use your own API key" banner on Dashboard, Watchlist, Option Chain, Positions | UI component, no backend dependency |
| **Frontend: Source Indicator Badge** | Shows active data source, failover notifications | Needs Source Indicator API |
| **Frontend: Broker Selection UI** | Settings → Market Data Broker / Order Broker dropdowns | Needs `PATCH /api/user/broker-preferences` API |
| **Instrument Sync Scheduler** | Daily job to download instrument masters for all active brokers and populate `broker_instrument_tokens` | Extends existing SmartAPI instrument sync |

---

## Broker #1: SmartAPI (Angel One) — Platform Primary

**Rank:** #1 | **Cost:** FREE | **Skill:** `/smartapi-expert`
**Status:** ✅ Market Data Adapter complete, ✅ Ticker Adapter complete (Phase T4)

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ✅ Done | Auto-TOTP via `smartapi_auth.py` (client_id + PIN + TOTP secret) |
| Platform credentials in `.env` | ✅ Done | `ANGEL_API_KEY`, `ANGEL_CLIENT_ID`, `ANGEL_PIN`, `ANGEL_TOTP_SECRET` |
| Token types | ✅ Done | 3 tokens: `jwtToken` (REST), `refreshToken`, `feedToken` (WebSocket) |
| Token lifetime | ✅ Done | Until 5 AM IST daily auto-logout |
| Auto-refresh loop | ⬜ Todo | Needs: refresh 30 min before 5 AM IST expiry. Currently manual re-auth. |
| User-level auth (own credentials) | ✅ Done | `SmartAPISettings.vue` UI exists, stores encrypted in `smartapi_credentials` table |

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
**Status:** ⬜ Not started — all items are Todo

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ⬜ Todo | Static API token — simplest auth (no OAuth, no TOTP) |
| Platform credentials in `.env` | ⬜ Todo | Need: `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN` |
| Token type | — | Single static access token (never expires unless revoked) |
| Token lifetime | — | **Never expires** — simplest for platform |
| Auto-refresh loop | ❌ N/A | Static token, no refresh needed |
| User-level auth UI | ⬜ Todo | Settings form: Client ID + Access Token fields |
| Credential encryption + storage | ⬜ Todo | `dhan_credentials` table with encrypted `access_token` |

### Market Data REST API

| Item | Status | Details |
|------|--------|---------|
| `DhanMarketDataAdapter` class | ⬜ Todo | File: `market_data/dhan_adapter.py` |
| `get_quote()` | ⬜ Todo | `GET /marketfeed/ltp` — prices in rupees (no conversion) |
| `get_ltp()` | ⬜ Todo | Same endpoint, extract LTP only |
| `get_historical()` | ⬜ Todo | `GET /charts/historical` |
| `get_instruments()` / `search_instruments()` | ⬜ Todo | Parse instrument master CSV |
| Price normalization | — | **Rupees** (no conversion needed) |
| Rate limiting (10 req/sec) | ⬜ Todo | Add Dhan config to RateLimiter |
| Factory registration | ⬜ Todo | Add `_create_dhan_adapter()` to `market_data/factory.py` |

### WebSocket Live Ticks

| Item | Status | Details |
|------|--------|---------|
| Ticker adapter | ⬜ Todo | File: `ticker/adapters/dhan.py` |
| Binary protocol parser | ⬜ Todo | **Little-endian** binary — use `struct.unpack('<...')` (unique among brokers) |
| Connection limits | — | 100 tokens/connection × 5 connections = **500 tokens** (lowest capacity) |
| Thread → asyncio bridge | ⬜ Todo | Threading-based, needs bridge like SmartAPI |
| Price normalization in ticks | — | Rupees (no conversion) |

### Symbol Format

| Item | Status | Details |
|------|--------|---------|
| `SymbolConverter.parse_dhan()` | ⬜ Todo | Numeric `security_id` only — **no string symbols** |
| `SymbolConverter.format_dhan()` | ⬜ Todo | Canonical → numeric security_id (requires full CSV lookup) |
| Token manager mapping | ⬜ Todo | Map Dhan `security_id` ↔ canonical symbol |
| Conversion difficulty | — | **Very High** — numeric-only, requires full instrument master CSV mapping |

### Instrument Master

| Item | Status | Details |
|------|--------|---------|
| Download URL | — | `https://images.dhan.co/api-data/api-scrip-master.csv` |
| Format | — | CSV |
| Parse + populate `broker_instrument_tokens` | ⬜ Todo | Map `security_id` to canonical symbols |

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
**Status:** 🟡 In progress — WebSocket ticker adapter complete, Auth/REST/Symbol format pending

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ⬜ Todo | OAuth 2.0 standard flow |
| Platform credentials in `.env` | ⬜ Todo | Need: `FYERS_APP_ID`, `FYERS_SECRET_KEY`, `FYERS_REDIRECT_URL` |
| Token type | — | `access_token` (standard OAuth) |
| Token lifetime | — | Until **midnight IST** (daily expiry) |
| Auto-refresh loop | ⬜ Todo | Needs: refresh token flow before midnight IST |
| Auth header format | — | **Unique:** `{app_id}:{access_token}` (colon-separated, not Bearer) |
| User-level auth UI | ⬜ Todo | Settings: OAuth redirect flow (like Kite) |
| Credential encryption + storage | ⬜ Todo | `fyers_credentials` table with encrypted tokens |

### Market Data REST API

| Item | Status | Details |
|------|--------|---------|
| `FyersMarketDataAdapter` class | ⬜ Todo | File: `market_data/fyers_adapter.py` |
| `get_quote()` | ⬜ Todo | `GET /data/quotes` — prices in rupees |
| `get_ltp()` | ⬜ Todo | Same endpoint, extract LTP |
| `get_historical()` | ⬜ Todo | `GET /data/history` — **1 req/sec** for historical (stricter than general 10/sec) |
| `get_instruments()` / `search_instruments()` | ⬜ Todo | Parse per-exchange CSV files |
| Price normalization | — | **Rupees** (no conversion needed) |
| Rate limiting | ⬜ Todo | 10 req/sec general, **1 req/sec historical** (dual rate limit) |
| Factory registration | ⬜ Todo | Add `_create_fyers_adapter()` to factory |

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
| `SymbolConverter.parse_fyers()` | ⬜ Todo | `NSE:{SYMBOL}` format (e.g., `NSE:NIFTY2522725000CE`) |
| `SymbolConverter.format_fyers()` | ⬜ Todo | Canonical → `NSE:{symbol}` (just add prefix) |
| Token manager mapping | ⬜ Todo | Map Fyers symbols ↔ canonical |
| Conversion difficulty | — | **Trivial** — just strip/add `NSE:` prefix |
| Index symbols | — | `NSE:NIFTY50-INDEX`, `NSE:NIFTYBANK-INDEX` |

### Instrument Master

| Item | Status | Details |
|------|--------|---------|
| Download URL | — | `https://public.fyers.in/sym_details/{exchange}.csv` (per exchange) |
| Format | — | CSV (per exchange: NSE, NFO, BSE, etc.) |
| Parse + populate `broker_instrument_tokens` | ⬜ Todo | Map Fyers `NSE:` format to canonical |

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
**Status:** 🟡 Partial — WebSocket ticker adapter ✅ implemented (100 tests). REST API, auth, symbol converter pending.

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ⬜ Todo | OAuth 2.0 with **3 separate JWT tokens** (most complex auth) |
| Platform credentials in `.env` | ⬜ Todo | Need: `PAYTM_API_KEY`, `PAYTM_API_SECRET`, `PAYTM_REDIRECT_URL` |
| Token types | — | **3 JWTs:** `access_token` (REST), `read_access_token` (portfolio), `public_access_token` (WebSocket) |
| Token lifetime | — | 1 trading day |
| Auto-refresh loop | ⬜ Todo | Daily refresh needed. Must refresh all 3 tokens. |
| Custom header format | — | `x-jwt-token: {token}` (not standard Authorization header) |
| User-level auth UI | ⬜ Todo | Settings: OAuth redirect flow |
| Credential encryption + storage | ⬜ Todo | `paytm_credentials` table with 3 encrypted tokens |

### Market Data REST API

| Item | Status | Details |
|------|--------|---------|
| `PaytmMarketDataAdapter` class | ⬜ Todo | File: `market_data/paytm_adapter.py` |
| `get_quote()` | ⬜ Todo | Scrip margins endpoint — prices in rupees |
| `get_ltp()` | ⬜ Todo | Extract LTP from quote |
| `get_historical()` | ⬜ Todo | `GET /accounts/v1/candle/{exchange}/{token}/{resolution}` |
| `get_instruments()` / `search_instruments()` | ⬜ Todo | Via API call (not static CSV) |
| Price normalization | — | **Rupees** (no conversion needed) |
| Rate limiting (10 req/sec) | ⬜ Todo | Add Paytm config to RateLimiter |
| Factory registration | ⬜ Todo | Add `_create_paytm_adapter()` to factory |

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
| `SymbolConverter.parse_paytm()` | ⬜ Todo | RIC format: `{exchange_segment}.{exchange_type}!{security_id}` |
| `SymbolConverter.format_paytm()` | ⬜ Todo | Canonical → RIC format (requires full mapping) |
| Token manager mapping | ⬜ Todo | Map Paytm RIC/security_id ↔ canonical |
| Conversion difficulty | — | **Very High** — RIC format requires full instrument master mapping |

### Instrument Master

| Item | Status | Details |
|------|--------|---------|
| Source | — | Via API call (not static file download) |
| Format | — | JSON API response |
| Parse + populate `broker_instrument_tokens` | ⬜ Todo | Map RIC format to canonical symbols |

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
**Status:** 🟡 Ticker adapter implemented — REST adapter, symbol converter, instrument master pending

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ⬜ Todo | OAuth 2.0 with extended token (~1 year validity) |
| Platform credentials in `.env` | ⬜ Todo | Need: `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`, `UPSTOX_REDIRECT_URL` |
| Token type | — | `access_token` (extended ~1 year for read-only) |
| Token lifetime | — | **~1 year** (extended token, simplifies credential management) |
| Auto-refresh loop | ⬜ Todo | Minimal — only needed annually. Standard OAuth refresh. |
| User-level auth UI | ⬜ Todo | Settings: OAuth redirect flow |
| Credential encryption + storage | ⬜ Todo | `upstox_credentials` table with encrypted tokens |

### Market Data REST API

| Item | Status | Details |
|------|--------|---------|
| `UpstoxMarketDataAdapter` class | ⬜ Todo | File: `market_data/upstox_adapter.py` |
| `get_quote()` | ⬜ Todo | `GET /market-quote/quotes` — prices in rupees |
| `get_ltp()` | ⬜ Todo | `GET /market-quote/ltp` |
| `get_historical()` | ⬜ Todo | `GET /historical-candle/{instrument_key}/{interval}/{to_date}` |
| `get_instruments()` / `search_instruments()` | ⬜ Todo | Parse gzip CSV instrument master |
| Price normalization | — | **Rupees** (no conversion needed) |
| Rate limiting (25 req/sec) | ⬜ Todo | Fastest rate limit — add config to RateLimiter |
| Factory registration | ⬜ Todo | Add `_create_upstox_adapter()` to factory |

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
| `SymbolConverter.parse_upstox()` | ⬜ Todo | `{EXCHANGE}_{SEGMENT}\|{instrument_token}` (e.g., `NSE_FO\|12345`) |
| `SymbolConverter.format_upstox()` | ⬜ Todo | Canonical → instrument_key (requires instrument master lookup) |
| Token manager mapping | ⬜ Todo | Map Upstox instrument_key ↔ canonical |
| Conversion difficulty | — | **High** — pipe-separated format, requires instrument master lookup |

### Instrument Master

| Item | Status | Details |
|------|--------|---------|
| Download URL | — | `https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz` |
| Format | — | **Gzip CSV** (compressed, needs decompression) |
| Parse + populate `broker_instrument_tokens` | ⬜ Todo | Decompress gzip → parse CSV → map to canonical |

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

**Rank:** #6 (Last Resort) | **Cost:** ₹500/month (Connect tier) | **Skill:** `/kite-expert`
**Status:** ✅ Market Data Adapter complete, ✅ Ticker Adapter complete (Phase T4)

### Authentication

| Item | Status | Details |
|------|--------|---------|
| Auth flow implementation | ✅ Done | OAuth 2.0 redirect flow |
| Platform credentials in `.env` | ❌ N/A | **Cannot use as platform source** — requires per-user OAuth, no auto-login |
| Token type | ✅ Done | `access_token` via OAuth callback |
| Token lifetime | — | 1 trading day (expires ~6 AM, no auto-refresh) |
| Auto-refresh loop | ❌ N/A | No refresh mechanism — user must re-login daily via OAuth |
| User-level auth UI | ✅ Done | OAuth redirect flow already implemented |
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

## Implementation Priority Recommendation

Based on the failover chain and implementation effort:

| Priority | Broker | Status | Rationale |
|----------|--------|--------|-----------|
| 1 | **SmartAPI** | ✅ Complete | Ticker adapter + all infrastructure done (Phase T1–T5) |
| 2 | **Kite** | ✅ Complete | Ticker adapter done (Phase T2). No platform use (OAuth only). |
| 3 | **Fyers** | 🟡 Stub ready | FREE + JSON WebSocket (simplest parsing) + trivial symbol conversion + 5K capacity |
| 4 | **Dhan** | 🟡 Stub ready | FREE† + static token (simplest auth, no refresh) + decent REST rate limits |
| 5 | **Paytm** | 🟡 Stub ready | FREE + JSON WebSocket. But: lowest capacity (200), complex auth (3 JWTs) |
| 6 | **Upstox** | ✅ Ticker implemented | Best rate limits + Option Greeks. Protobuf parsed via runtime descriptor. REST adapter pending. |

**Next:** Implement full adapter logic for Fyers (Priority 3) — simplest parsing, highest capacity among remaining brokers.
