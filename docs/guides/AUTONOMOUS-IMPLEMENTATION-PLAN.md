# Autonomous Multi-Broker Data Implementation Plan

**Purpose:** Session-by-session plan for fully autonomous implementation of multi-broker market data (platform-level + user-level). Designed for minimal human intervention.
**Last Updated:** 2026-02-16
**Estimated Sessions:** 18-22
**Estimated Total Time:** ~60-80 hours of autonomous work

**References:**
- [Broker Data Checklist](../architecture/BROKER-DATA-IMPLEMENTATION-CHECKLIST.md) — Per-broker requirements & status
- [TICKER-DESIGN-SPEC](../decisions/TICKER-DESIGN-SPEC.md) — 5-component architecture
- [TICKER-IMPLEMENTATION-GUIDE](TICKER-IMPLEMENTATION-GUIDE.md) — Step-by-step ticker phases
- [Working Doc (Platform-Level)](../architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md) — Full architecture

---

## Table of Contents

1. [How Autonomous Execution Works](#how-autonomous-execution-works)
2. [What Requires Manual Intervention](#what-requires-manual-intervention)
3. [Session Map (Dependency Graph)](#session-map-dependency-graph)
4. [Session Definitions (S01–S22)](#session-definitions)
5. [How to Start a Session](#how-to-start-a-session)
6. [Failure Handling](#failure-handling)

---

## How Autonomous Execution Works

### The Inner Loop (Every Session)

Each session follows this fully autonomous cycle:

```
┌─ USER: "continue" or "start next session" ──────────────┐
│                                                          │
│  1. /start-session → restore context from last session   │
│  2. Read BROKER-DATA-IMPLEMENTATION-CHECKLIST.md         │
│  3. Pick next session from THIS plan                     │
│  4. For each feature in the session:                     │
│     ┌──────────────────────────────────────────┐         │
│     │  /implement (7-step workflow)             │         │
│     │  Step 1: Read requirements (broker skill) │         │
│     │  Step 2: Write tests FIRST (TDD)          │         │
│     │  Step 3: Write implementation code         │         │
│     │  Step 4: /auto-verify                      │         │
│     │    ├─ PASS → Step 6                        │         │
│     │    └─ FAIL → Step 5                        │         │
│     │  Step 5: /fix-loop (up to 12 iterations)   │         │
│     │    ├─ FIXED → Step 6                       │         │
│     │    └─ STUCK → save state, ask user  ⚠️     │         │
│     │  Step 6: Visual verify (if frontend)       │         │
│     │  Step 7: /post-fix-pipeline → commit       │         │
│     └──────────────────────────────────────────┘         │
│  5. Update checklist (⬜ → ✅)                            │
│  6. /docs-maintainer → update related docs               │
│  7. /learning-engine → record outcomes                   │
│  8. /save-session → checkpoint for next session          │
│                                                          │
└─ SESSION COMPLETE ───────────────────────────────────────┘
```

### Skills That Enable Autonomy

| Skill | Role | Autonomous? |
|-------|------|-------------|
| `/start-session` | Restore context from previous session | ✅ Fully |
| `/implement` | 7-step TDD workflow orchestrator | ✅ Mostly (asks in Step 1 only if unclear) |
| `/auto-verify` | Smart test selection + execution + screenshot analysis | ✅ Fully |
| `/fix-loop` | 12-iteration fix cycle with 6 escalation levels | ✅ Until stuck (iter 12 or same error 3×) |
| `/post-fix-pipeline` | Regression test + docs update + commit | ✅ Until hard block |
| `/learning-engine` | Record errors/fixes to knowledge.db, synthesize rules | ✅ Fully |
| `/save-session` | Checkpoint current state for next session | ✅ Fully |
| `/docs-maintainer` | Update docs after code changes | ✅ Fully |
| Broker expert skills | API-specific guidance (endpoints, formats, quirks) | ✅ Reference only |

### Cross-Session Learning

```
Session N: fix-loop records "Dhan little-endian parse error → fix: use struct.unpack('<')"
           ↓ saved to knowledge.db with score 1.0
Session N+1: auto-verify encounters similar Paytm binary issue
           ↓ knowledge.db suggests "check endianness" (score 0.8)
           ↓ fix-loop applies strategy FIRST → resolved in iteration 1
```

The learning engine ensures each session is faster than the last. Fix strategies accumulate, error patterns get pre-matched, and synthesized rules prevent regression.

---

## What Requires Manual Intervention

### Per-Session (Minimal)

| Intervention | When | How Often | User Action |
|-------------|------|-----------|-------------|
| **Start session** | Beginning of each session | Every session | Say "continue" or "start session S0X" |
| **Approve commit** | End of each session | Every session | Review commit message, approve push |

### One-Time Setup (Before First Broker Session)

| Intervention | When | User Action |
|-------------|------|-------------|
| **Add broker credentials to `.env`** | Before each new broker's session | Manually edit `backend/.env` to add `DHAN_ACCESS_TOKEN`, `FYERS_APP_ID`, etc. |
| **Install broker SDK** | Before each new broker's session | `pip install fyers-apiv3` / `pip install dhanhq` / etc. |
| **OAuth browser redirect** (Fyers, Paytm, Upstox) | First-time testing of OAuth brokers | Complete browser OAuth flow, copy callback URL |

### Edge Cases (Rare)

| Intervention | When | User Action |
|-------------|------|-------------|
| **Fix-loop stuck** | After 12 failed iterations | Choose: retry, revert, skip, or provide hint |
| **Architecture decision** | If implementation reveals design gap | Approve/modify proposed approach |
| **Broker API down** | External dependency failure | Skip broker, retry later |
| **Test suite hard block** | Full suite fails after 3 auto-fix attempts | Investigate and unblock |

**Expected manual intervention per session: ~2-3 minutes** (start + approve commit).

---

## Session Map (Dependency Graph)

```
FOUNDATION (must be sequential)
═══════════════════════════════════════════════
S01: Ticker Core Infrastructure
 ↓
S02: SmartAPI Ticker Adapter (migrate legacy)
S03: Kite Ticker Adapter (migrate legacy)        ← S02, S03 can run in parallel
 ↓
S04: WebSocket Route Refactor (use new ticker)
 ↓
S05: Health Monitor + Failover Controller
 ↓
S06: Platform Credential Manager + Auto-Refresh

NEW BROKER ADAPTERS (parallel after S06)
═══════════════════════════════════════════════
S07: Fyers Symbol Converter + Instrument Master
S08: Fyers Market Data REST Adapter
S09: Fyers Ticker (WebSocket) Adapter
S10: Fyers Auth Flow + Integration Test
 ↓
S11: Dhan Symbol Converter + Instrument Master
S12: Dhan Market Data REST + Ticker Adapter
S13: Dhan Auth + Integration Test
 ↓
S14: Paytm Symbol Converter + Instrument Master
S15: Paytm Market Data REST + Ticker Adapter
S16: Paytm Auth + Integration Test
 ↓
S17: Upstox Symbol Converter + Instrument Master
S18: Upstox Market Data REST + Ticker + Protobuf
S19: Upstox Auth + Integration Test

PLATFORM LAYER (after all brokers)
═══════════════════════════════════════════════
S20: MarketDataRouter + Instrument Sync Scheduler
 ↓
S21: Frontend — Broker Selection UI + Banner + Source Badge
 ↓
S22: End-to-End Integration Test (full failover chain)
```

**Parallelization note:** S07-S10 (Fyers), S11-S13 (Dhan), S14-S16 (Paytm), S17-S19 (Upstox) are independent broker tracks. They're listed sequentially by priority but could be reordered without breaking dependencies. Within each broker track, sessions must be sequential.

---

## Session Definitions

### FOUNDATION — Ticker Architecture (S01–S06)

---

#### S01: Ticker Core Infrastructure

**Goal:** Build the 5-component ticker skeleton that all broker adapters plug into.

**Pre-conditions:** None (first session)
**Estimated time:** 4-5 hours

**Deliverables:**
- [ ] Create directory structure: `backend/app/services/brokers/market_data/ticker/`
- [ ] `NormalizedTick` dataclass (Decimal prices, canonical tokens, IST timestamps)
- [ ] `TickerAdapter` ABC (abstract base for all broker WebSocket adapters)
- [ ] `TickerPool` (adapter lifecycle, ref-counted subscriptions, integrated credentials)
- [ ] `TickerRouter` (user fan-out, dispatch normalized ticks to subscribers)
- [ ] Unit tests for TickerPool (ref counting, lifecycle) and TickerRouter (fan-out)

**Key reference:** [TICKER-IMPLEMENTATION-GUIDE Phase T1](TICKER-IMPLEMENTATION-GUIDE.md)

**Autonomous flow:**
```
/implement → Read TICKER-DESIGN-SPEC + API Reference
  → Write TickerPool unit tests (TDD)
  → Implement NormalizedTick, TickerAdapter ABC
  → Implement TickerPool, TickerRouter
  → /auto-verify (pytest)
  → /fix-loop if needed
  → /post-fix-pipeline → commit
```

**Manual intervention:** None expected.

---

#### S02: SmartAPI Ticker Adapter

**Goal:** Migrate legacy `smartapi_ticker.py` to new `TickerAdapter` interface.

**Pre-conditions:** S01 complete
**Estimated time:** 4-5 hours

**Deliverables:**
- [x] `ticker/adapters/smartapi.py` implementing `TickerAdapter`
- [x] Extract binary parser from legacy `smartapi_ticker.py`
- [x] Paise → rupees (Decimal) normalization in tick output
- [x] SmartAPI token format → canonical token mapping
- [x] Thread → asyncio bridge (`asyncio.run_coroutine_threadsafe`)
- [x] Unit tests (mock WebSocket, verify NormalizedTick output) — 45 tests
- [ ] Integration test (connect to SmartAPI WS with platform creds)

**Key reference:** [TICKER-IMPLEMENTATION-GUIDE Phase T2](TICKER-IMPLEMENTATION-GUIDE.md) + `/smartapi-expert`

**Manual intervention:** None (platform SmartAPI creds already in `.env`).

---

#### S03: Kite Ticker Adapter

**Goal:** Migrate legacy `kite_ticker.py` to new `TickerAdapter` interface.

**Pre-conditions:** S01 complete (can run parallel with S02)
**Estimated time:** 3-4 hours

**Deliverables:**
- [ ] `ticker/adapters/kite.py` implementing `TickerAdapter`
- [ ] Wrap `KiteTicker` library behind adapter interface
- [ ] Paise → rupees (Decimal) normalization
- [ ] Kite integer tokens are already canonical (identity mapping)
- [ ] Unit tests (mock KiteTicker, verify NormalizedTick output)

**Key reference:** `/zerodha-expert`

**Manual intervention:** None (uses existing Kite adapter code).

---

#### S04: WebSocket Route Refactor

**Goal:** Refactor `websocket.py` from 494 lines to ~90 lines using new ticker system.

**Pre-conditions:** S02 + S03 complete
**Estimated time:** 3-4 hours

**Deliverables:**
- [ ] Refactored `backend/app/api/routes/websocket.py` using TickerRouter
- [ ] Remove direct SmartAPI/Kite imports from route
- [ ] Route is now broker-agnostic (talks to TickerRouter only)
- [ ] E2E test: WebSocket subscription → receive normalized ticks
- [ ] Verify existing E2E tests still pass (regression check)

**Key reference:** [TICKER-IMPLEMENTATION-GUIDE Phase T2 (route refactoring)](TICKER-IMPLEMENTATION-GUIDE.md)

**Manual intervention:** Dev servers must be running for E2E tests.

---

#### S05: Health Monitor + Failover Controller

**Goal:** Build active health monitoring and make-before-break failover.

**Pre-conditions:** S04 complete
**Estimated time:** 4-5 hours

**Deliverables:**
- [ ] `ticker/health.py` — HealthMonitor (5s heartbeat, per-broker health score)
- [ ] `ticker/failover.py` — FailoverController (make-before-break switching)
- [ ] Health score formula: weighted (tick freshness 40%, reconnect rate 30%, error rate 30%)
- [ ] Failover trigger: health score < 0.3 for 15 seconds
- [ ] Make-before-break: new connection established BEFORE old one dropped
- [ ] Unit tests (simulate health degradation → failover trigger)
- [ ] Source Indicator API: `GET /api/market-data/source`

**Key reference:** [TICKER-DESIGN-SPEC §4-5](../decisions/TICKER-DESIGN-SPEC.md) + [API Reference](../api/multi-broker-ticker-api.md)

**Manual intervention:** None expected.

---

#### S06: Platform Credential Manager + Auto-Refresh

**Goal:** Manage shared platform credentials with broker-specific refresh strategies.

**Pre-conditions:** S05 complete
**Estimated time:** 3-4 hours

**Deliverables:**
- [ ] Platform credential loading from `.env` (per-broker sections)
- [ ] Auto-refresh loops integrated into TickerPool:
  - SmartAPI: Refresh 30 min before 5 AM IST
  - Fyers: Refresh before midnight IST (placeholder — Fyers adapter in S09)
  - Upstox: ~1 year token, minimal refresh (placeholder)
  - Dhan: Static token, no refresh needed (placeholder)
  - Paytm: Daily refresh (placeholder)
  - Kite: N/A (OAuth only, no platform credentials)
- [ ] Credential rotation without dropping active connections
- [ ] Unit tests (mock clock, verify refresh triggers at correct times)

**Key reference:** [Working Doc §Platform Credentials](../architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md)

**Manual intervention:**
- ⚠️ **One-time:** Add placeholder env vars for future brokers in `.env` (user must edit `.env`)

---

### NEW BROKER ADAPTERS — Fyers (S07–S10)

**Why Fyers first:** FREE + JSON WebSocket (simplest parsing) + trivial symbol conversion (`NSE:` prefix) + 5,000 symbol capacity (second-highest).

---

#### S07: Fyers Symbol Converter + Instrument Master

**Goal:** Enable Fyers symbol/token resolution.

**Pre-conditions:** S01 complete (SymbolConverter exists)
**Estimated time:** 2-3 hours

**Deliverables:**
- [ ] `SymbolConverter.parse_fyers()` — strip `NSE:` prefix → canonical
- [ ] `SymbolConverter.format_fyers()` — add `NSE:` prefix ← canonical
- [ ] Fyers instrument master downloader (`https://public.fyers.in/sym_details/{exchange}.csv`)
- [ ] Parser: CSV → `broker_instrument_tokens` rows (Fyers symbols + tokens)
- [ ] Fyers index symbol mapping (`NSE:NIFTY50-INDEX` → canonical)
- [ ] Unit tests (symbol conversion round-trips, CSV parsing)

**Key reference:** `/fyers-expert` (symbol format section)

**Manual intervention:** None.

---

#### S08: Fyers Market Data REST Adapter

**Goal:** REST API for quotes, LTP, and historical OHLC via Fyers.

**Pre-conditions:** S07 complete
**Estimated time:** 3-4 hours

**Deliverables:**
- [ ] `market_data/fyers_adapter.py` implementing `MarketDataBrokerAdapter`
- [ ] `get_quote()` — `GET /data/quotes`, prices in rupees (no conversion)
- [ ] `get_ltp()` — extract LTP from quotes
- [ ] `get_historical()` — `GET /data/history` (rate limit: 1 req/sec for historical)
- [ ] `get_instruments()` / `search_instruments()` — uses S07 instrument master
- [ ] Fyers auth header: `{app_id}:{access_token}` (colon-separated, NOT Bearer)
- [ ] Dual rate limiting: 10 req/sec general, 1 req/sec historical
- [ ] Factory registration: add `_create_fyers_adapter()` to `market_data/factory.py`
- [ ] Unit tests (mock Fyers API responses → verify UnifiedQuote output)

**Key reference:** `/fyers-expert` (REST endpoints section)

**Manual intervention:** None (tests use mocks).

---

#### S09: Fyers Ticker (WebSocket) Adapter

**Goal:** Live ticks via Fyers WebSocket.

**Pre-conditions:** S08 + S01 complete
**Estimated time:** 3-4 hours

**Deliverables:**
- [ ] `ticker/adapters/fyers.py` implementing `TickerAdapter`
- [ ] JSON WebSocket protocol (simplest parser — no binary)
- [ ] Use `FyersDataSocket` only (not `FyersOrderSocket`)
- [ ] asyncio-native (no thread bridge needed)
- [ ] Auth: `{app_id}:{access_token}` format
- [ ] Connection limit handling: 5,000 symbols/connection (v3.0.0)
- [ ] Register in TickerPool as available adapter
- [ ] Unit tests (mock WS, verify NormalizedTick output)

**Key reference:** `/fyers-expert` (WebSocket section)

**Manual intervention:** None (tests use mocks).

---

#### S10: Fyers Auth Flow + Integration Test

**Goal:** Complete Fyers authentication and end-to-end integration test.

**Pre-conditions:** S09 complete
**Estimated time:** 2-3 hours

**Deliverables:**
- [ ] Fyers OAuth flow: `backend/app/api/routes/fyers_auth.py`
- [ ] `POST /api/auth/fyers/login` → redirect to Fyers OAuth
- [ ] `GET /api/auth/fyers/callback` → exchange code for tokens
- [ ] Credential storage: `fyers_credentials` table + encryption
- [ ] Token refresh: handle midnight IST expiry
- [ ] Integration test: auth → subscribe → receive tick → verify normalized output
- [ ] Update BROKER-DATA-IMPLEMENTATION-CHECKLIST.md (Fyers ⬜ → ✅)

**Manual intervention:**
- ⚠️ **One-time:** Add `FYERS_APP_ID`, `FYERS_SECRET_KEY` to `backend/.env`
- ⚠️ **One-time:** Complete OAuth browser redirect for integration test
- ⚠️ **One-time:** `pip install fyers-apiv3` (if SDK needed)

---

### NEW BROKER ADAPTERS — Dhan (S11–S13)

**Why Dhan second:** FREE† + static token (simplest auth — no OAuth, no refresh) + good REST rate limits (10/sec).

---

#### S11: Dhan Symbol Converter + Instrument Master

**Goal:** Enable Dhan symbol/token resolution (hardest conversion — numeric only).

**Pre-conditions:** S01 complete
**Estimated time:** 3-4 hours

**Deliverables:**
- [ ] `SymbolConverter.parse_dhan()` — numeric `security_id` → canonical (requires CSV lookup)
- [ ] `SymbolConverter.format_dhan()` — canonical → numeric `security_id` (reverse lookup)
- [ ] Dhan instrument master downloader (`https://images.dhan.co/api-data/api-scrip-master.csv`)
- [ ] Parser: CSV → `broker_instrument_tokens` rows
- [ ] Handle Dhan's numeric-only format (no string symbols)
- [ ] Unit tests (conversion round-trips, edge cases for weekly/monthly expiry mapping)

**Key reference:** `/dhan-expert` (security_id format section)

**Manual intervention:** None.

---

#### S12: Dhan Market Data REST + Ticker Adapter

**Goal:** REST API + WebSocket for Dhan (combined session — simpler REST, complex WS).

**Pre-conditions:** S11 complete
**Estimated time:** 5-6 hours

**Deliverables:**
- [ ] `market_data/dhan_adapter.py` implementing `MarketDataBrokerAdapter`
- [ ] REST: `get_quote()`, `get_ltp()`, `get_historical()` — all prices in rupees
- [ ] Rate limiting: 10 req/sec
- [ ] Factory registration
- [ ] `ticker/adapters/dhan.py` implementing `TickerAdapter`
- [ ] **Little-endian binary parser** — `struct.unpack('<...')` (unique among brokers)
- [ ] Connection limits: 100 tokens/conn × 5 conns = 500 tokens
- [ ] Thread → asyncio bridge (threading-based like SmartAPI)
- [ ] Unit tests for both REST + ticker (mock responses)

**Key reference:** `/dhan-expert` (WebSocket binary format section)

**Manual intervention:** None (tests use mocks).

---

#### S13: Dhan Auth + Integration Test

**Goal:** Dhan authentication (simplest — static token) and integration test.

**Pre-conditions:** S12 complete
**Estimated time:** 2-3 hours

**Deliverables:**
- [ ] Dhan auth: static API token (no OAuth flow — just store token)
- [ ] `POST /api/auth/dhan/credentials` → save encrypted Client ID + Access Token
- [ ] `dhan_credentials` table + encryption
- [ ] No refresh needed (static token never expires)
- [ ] Integration test: auth → subscribe → receive tick → verify
- [ ] Update BROKER-DATA-IMPLEMENTATION-CHECKLIST.md (Dhan ⬜ → ✅)

**Manual intervention:**
- ⚠️ **One-time:** Add `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN` to `backend/.env`
- ⚠️ **One-time:** `pip install dhanhq` (if SDK needed)

---

### NEW BROKER ADAPTERS — Paytm Money (S14–S16)

**Why Paytm third:** FREE + JSON WebSocket. But: lowest capacity (200), 3-JWT auth complexity.

---

#### S14: Paytm Symbol Converter + Instrument Master

**Pre-conditions:** S01 complete
**Estimated time:** 3-4 hours

**Deliverables:**
- [ ] `SymbolConverter.parse_paytm()` — RIC format `{seg}.{type}!{id}` → canonical (requires mapping)
- [ ] `SymbolConverter.format_paytm()` — canonical → RIC format (reverse mapping)
- [ ] Paytm instrument master (via API call, not static file)
- [ ] Parser: API response → `broker_instrument_tokens` rows
- [ ] Unit tests

**Key reference:** `/paytm-expert` (RIC format section)

**Manual intervention:** None.

---

#### S15: Paytm Market Data REST + Ticker Adapter

**Pre-conditions:** S14 complete
**Estimated time:** 4-5 hours

**Deliverables:**
- [ ] `market_data/paytm_adapter.py` implementing `MarketDataBrokerAdapter`
- [ ] REST: quotes, LTP, historical — prices in rupees
- [ ] Custom header: `x-jwt-token: {token}` (NOT standard Authorization)
- [ ] Rate limiting: 10 req/sec
- [ ] Factory registration
- [ ] `ticker/adapters/paytm.py` implementing `TickerAdapter`
- [ ] JSON WebSocket (simple parser, like Fyers)
- [ ] **Use `public_access_token` for WebSocket** (NOT `access_token` — critical distinction)
- [ ] Connection limit: 200 instruments/connection
- [ ] asyncio-native
- [ ] Unit tests

**Key reference:** `/paytm-expert` (3-JWT system section)

**Manual intervention:** None (tests use mocks).

---

#### S16: Paytm Auth + Integration Test

**Pre-conditions:** S15 complete
**Estimated time:** 3-4 hours

**Deliverables:**
- [ ] Paytm OAuth flow with 3 JWT tokens
- [ ] Store all 3 tokens separately: `access_token`, `read_access_token`, `public_access_token`
- [ ] `paytm_credentials` table (3 encrypted token columns)
- [ ] Daily refresh for all 3 tokens
- [ ] Integration test
- [ ] Update checklist (Paytm ⬜ → ✅)

**Manual intervention:**
- ⚠️ **One-time:** Add `PAYTM_API_KEY`, `PAYTM_API_SECRET` to `backend/.env`
- ⚠️ **One-time:** Complete OAuth browser redirect
- ⚠️ **One-time:** `pip install paytm-money` (if SDK exists)

---

### NEW BROKER ADAPTERS — Upstox (S17–S19)

**Why Upstox last among new brokers:** ₹499/month cost + Protobuf complexity (highest parsing effort).

---

#### S17: Upstox Symbol Converter + Instrument Master

**Pre-conditions:** S01 complete
**Estimated time:** 3-4 hours

**Deliverables:**
- [ ] `SymbolConverter.parse_upstox()` — `NSE_FO|{token}` → canonical (requires CSV lookup)
- [ ] `SymbolConverter.format_upstox()` — canonical → instrument_key
- [ ] Upstox instrument master downloader (gzip CSV: `assets.upstox.com/...complete.csv.gz`)
- [ ] Parser: decompress gzip → parse CSV → `broker_instrument_tokens` rows
- [ ] Unit tests

**Key reference:** `/upstox-expert` (instrument_key format section)

**Manual intervention:** None.

---

#### S18: Upstox Market Data REST + Ticker + Protobuf

**Pre-conditions:** S17 complete
**Estimated time:** 6-7 hours (longest session — Protobuf complexity)

**Deliverables:**
- [ ] `market_data/upstox_adapter.py` implementing `MarketDataBrokerAdapter`
- [ ] REST: quotes, LTP, historical — prices in rupees, 25 req/sec rate limit
- [ ] Factory registration
- [ ] `ticker/adapters/upstox.py` implementing `TickerAdapter`
- [ ] **Protobuf WebSocket parser** — requires `.proto` definition file
- [ ] Compile `.proto` → Python module (`protoc` or `grpcio-tools`)
- [ ] Handle Option Greeks in tick data (unique Upstox feature)
- [ ] Connection: 1 per token, 1,500-5,000 tokens/connection
- [ ] asyncio-native
- [ ] Unit tests (mock Protobuf messages → verify NormalizedTick)

**Key reference:** `/upstox-expert` (Protobuf WebSocket section)

**Manual intervention:**
- ⚠️ **One-time:** `pip install protobuf` + obtain Upstox `.proto` file

---

#### S19: Upstox Auth + Integration Test

**Pre-conditions:** S18 complete
**Estimated time:** 2-3 hours

**Deliverables:**
- [ ] Upstox OAuth flow (extended token ~1 year)
- [ ] `upstox_credentials` table + encryption
- [ ] Minimal refresh (annual)
- [ ] Integration test
- [ ] Update checklist (Upstox ⬜ → ✅)

**Manual intervention:**
- ⚠️ **One-time:** Add `UPSTOX_API_KEY`, `UPSTOX_API_SECRET` to `backend/.env`
- ⚠️ **One-time:** Complete OAuth browser redirect

---

### PLATFORM LAYER (S20–S22)

---

#### S20: MarketDataRouter + Instrument Sync Scheduler

**Goal:** The brain that routes requests to the right broker + daily instrument sync for all brokers.

**Pre-conditions:** All broker adapters (S01–S19) complete
**Estimated time:** 5-6 hours

**Deliverables:**
- [ ] `MarketDataRouter` — dual-path routing logic:
  - Check if user has own broker configured → use user adapter
  - Else → use platform adapter (failover chain: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite)
  - On failure → try next in chain, notify frontend
- [ ] `GET /api/market-data/source` — returns active source + failover status
- [ ] Instrument Sync Scheduler (daily, pre-market):
  - Download instrument masters for all active brokers
  - Populate `broker_instrument_tokens` table
  - Cross-reference canonical symbols across brokers
- [ ] Integration test: simulate primary failure → verify failover to next broker
- [ ] Unit tests (mock adapters, verify routing logic)

**Key reference:** [Working Doc §MarketDataRouter](../architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md)

**Manual intervention:** None expected.

---

#### S21: Frontend — Broker Selection UI + Banner + Source Badge

**Goal:** User-facing UI for broker selection and data source visibility.

**Pre-conditions:** S20 complete (source API exists)
**Estimated time:** 4-5 hours

**Deliverables:**
- [ ] **Persistent Banner** on Dashboard, Watchlist, Option Chain, Positions:
  - "Use your own API key for faster data" → links to Settings
  - Dismissible per-session, reappears next session
- [ ] **Source Indicator Badge** (header bar):
  - Shows active data source (e.g., "SmartAPI" with green dot)
  - Shows failover notification (e.g., "Switched to Fyers" with yellow dot)
  - Clicking opens source details popover
- [ ] **Settings → Broker Selection**:
  - Market Data Broker dropdown (SmartAPI, Dhan, Fyers, Paytm, Upstox, Kite)
  - Order Execution Broker dropdown (all 6)
  - "Platform Default" option (uses shared credentials)
  - Per-broker credential forms (show/hide based on selection)
  - Test Connection button per broker
- [ ] `PATCH /api/user/broker-preferences` + `GET /api/user/broker-preferences` API endpoints
- [ ] E2E tests: broker selection flow, banner visibility, source badge display
- [ ] Add `data-testid` attributes following `[screen]-[component]-[element]` convention

**Key reference:** [Working Doc §Frontend Components](../architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md)

**Manual intervention:** Dev servers must be running for E2E tests.

---

#### S22: End-to-End Integration Test (Full Failover Chain)

**Goal:** Verify the complete platform-level failover chain works end-to-end.

**Pre-conditions:** S21 complete (all components wired)
**Estimated time:** 3-4 hours

**Deliverables:**
- [ ] E2E test: Full failover chain simulation
  - Start with SmartAPI → simulate failure → verify Dhan takes over
  - Simulate Dhan failure → verify Fyers takes over
  - Continue through entire chain
  - Verify frontend source badge updates at each transition
  - Verify no tick gaps during make-before-break failover
- [ ] E2E test: User upgrade path
  - User selects own Fyers API → verify data switches to user's Fyers
  - User removes own API → verify falls back to platform default
- [ ] Performance test: measure failover latency (target: <2s)
- [ ] Update all checklists and documentation
- [ ] Final /docs-maintainer run
- [ ] Final /learning-engine synthesis

**Manual intervention:** Dev servers + all broker credentials must be available.

---

## How to Start a Session

### First Session (S01)

```
User: "Start implementing the multi-broker data system. Begin with S01."
```

Claude will:
1. Read this plan (AUTONOMOUS-IMPLEMENTATION-PLAN.md)
2. Read the checklist (BROKER-DATA-IMPLEMENTATION-CHECKLIST.md)
3. Read TICKER-DESIGN-SPEC.md + TICKER-IMPLEMENTATION-GUIDE.md
4. Execute S01 deliverables via `/implement`
5. Save session at end

### Subsequent Sessions (S02+)

```
User: "continue"
```

Claude will:
1. `/start-session` → restore context
2. Check which session is next (from this plan + checklist status)
3. Execute next session's deliverables
4. Save session at end

### Resuming a Stuck Session

```
User: "The fix-loop got stuck on the Dhan little-endian parser. Here's what I found: [hint]"
```

Claude will:
1. `/start-session` → restore context including fix-loop state
2. Apply user's hint
3. Continue fix-loop from where it stopped

---

## Failure Handling

### Fix-Loop Exhaustion (12 iterations)

```
1. Save current state (/save-session)
2. Present diagnosis to user:
   - What was tried (all 12 iterations summarized)
   - What error persists
   - Top 3 hypotheses for root cause
3. User provides direction
4. Resume with user's hint → fix-loop resets iteration count
```

### Broker API Unavailable

```
1. Mark broker session as BLOCKED
2. Skip to next independent session
3. Return to blocked session when API is available
```

### Architecture Gap Discovered

```
1. Document the gap in session notes
2. Propose solution to user
3. If approved → implement in current session
4. If needs discussion → save-session, flag for user review
```

### Context Window Exhaustion

```
1. /save-session (auto-triggered by quality_gate hook)
2. User starts new conversation
3. /start-session restores full context
4. Continue from where it stopped
```

---

## Progress Tracking

After each session, these files are updated:

| File | What's Updated |
|------|---------------|
| `BROKER-DATA-IMPLEMENTATION-CHECKLIST.md` | ⬜ → ✅ for completed items |
| `IMPLEMENTATION-CHECKLIST.md` | Phase status updates |
| `.claude/sessions/{session-name}.md` | Session checkpoint |
| `.claude/learning/knowledge.db` | Error patterns + fix strategies |
| `MEMORY.md` | Key decisions (if cross-session relevant) |

The checklist serves as the single source of truth for "what's done." Any session can read it to determine what's next.
