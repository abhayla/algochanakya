# Session: 2026-04-12-instrument-dedup-and-nse-v3

**Date:** 2026-04-12 18:15 IST
**Branch:** main

---

## Working Files

| File | Status | Notes |
|------|--------|-------|
| `backend/app/services/brokers/market_data/instrument_query.py` | created (committed) | New helper: `get_nfo_instruments()`, `get_single_instrument()`, `preferred_source_brokers()` with broker-aware source_broker filtering and fallback chain |
| `backend/app/api/routes/optionchain.py` | modified (committed) | Replaced raw instrument query (line 259) with `get_nfo_instruments()` using `adapter.broker_type` |
| `backend/app/api/routes/options.py` | modified (committed) | Added `source_broker` filter to 4 queries (expiries, strikes, chain, single instrument) |
| `backend/app/api/routes/orders.py` | modified (committed) | Added `source_broker == "kite"` filter to 2 instrument_token.in_() queries |
| `backend/app/services/option_chain_service.py` | modified (committed) | Replaced raw query with `get_nfo_instruments()` |
| `backend/app/services/options/oi_analysis_service.py` | modified (committed) | Replaced raw query with `get_nfo_instruments()` |
| `backend/app/services/options/expected_move_service.py` | modified (committed) | Replaced 2 raw queries with `get_nfo_instruments()` |
| `backend/app/services/instruments.py` | modified (committed) | Changed `scalar_one_or_none()` to `.scalars().first()` to prevent crash with duplicates |
| `backend/tests/backend/services/test_instrument_query_helper.py` | created (committed) | 11 unit tests for the instrument query helper |
| `backend/tests/backend/routes/test_instrument_dedup.py` | created (committed) | 3 integration tests for deduplication verification |
| `backend/tests/live/test_live_nse_cross_verification.py` | created (committed) | 10 live tests: NSE vs Upstox/AngelOne cross-verification with v3 API |
| `backend/tests/live/conftest.py` | modified (committed) | Fixed live_db teardown to suppress asyncpg event-loop-closed errors |
| `.claude/skills/broker-shared/references/instrument-token-architecture.md` | modified (committed) | Added web research findings, index token differences, duplicate row fix docs, all 11 query sites |

## Git State

- **Branch:** main
- **Last 5 commits:**
  - 9781129 fix(tests): fix Upstox cross-verification tests — spot match, graceful skips
  - ab7077c fix(tests): use NSE v3 API for cross-verification tests (works on weekends)
  - edc47b9 fix(instruments): add source_broker filtering to prevent duplicate instrument rows
  - 5e2c854 docs(skills): add cross-broker instrument token architecture reference
  - 1855e93 fix(market-data): fix Upstox option chain token keying and add pre-calculated Greeks
- **Uncommitted changes:** yes — old session file deletions, `.claude/settings.json`, `navigation.cross-screen.spec.js` (pre-existing, unrelated)
- **Stash list:** stash@{0}: WIP: Token mapping changes before multi-broker ticker refactor

## Key Decisions

- **Approach C chosen for instrument dedup:** Shared `get_nfo_instruments()` helper with `source_broker` filter instead of modifying 12 individual query sites (A) or redesigning the schema (B). Centralizes logic, low risk.
- **Broker-to-source mapping:** `upstox → ["smartapi", "kite"]` because Upstox NSE exchange tokens == SmartAPI tokens. `kite → ["kite", "smartapi"]` because Kite uses its own internal instrument_token numbering.
- **Fallback chain pattern:** Query preferred source_broker first, fall back to next if empty. Prevents empty results when only one broker's instruments are loaded.
- **NSE v3 API over v1:** `/api/option-chain-v3` returns cached data on weekends; `/api/option-chain-indices` returns empty `{}`. Test now tries v3 first with auto-discovery of available expiry dates.
- **NSE exchange token equivalence confirmed:** Web research verified SmartAPI `symboltoken` == Upstox `exchange_token` == Kite `exchange_token` for F&O options (all NSE-assigned). Kite `instrument_token` is different (Kite-internal). Dhan `security_id` unverified.

## Task Progress

### Completed

- Implemented `instrument_query.py` helper with TDD (11 unit tests, 3 integration tests — all pass)
- Updated all 11 query sites across 7 files with source_broker filtering
- Fixed NSE cross-verification tests: v3 API, Upstox spot match, graceful skips
- Updated broker-shared skill docs with web research and implementation details
- Verified: 5/10 live NSE tests pass on Saturday, 5 skip (market closed/CSV 403)
- Verified: 816 related backend tests pass, 0 regressions
- All changes committed and pushed (3 commits: edc47b9, ab7077c, 9781129)

### In Progress

- **Monday live verification** — Run full NSE cross-verification during market hours to prove non-zero LTP values with source_broker fix

### Blocked

- None

## Relevant Docs

| Document | Relevance |
|----------|-----------|
| `.claude/skills/broker-shared/references/instrument-token-architecture.md` | Complete reference: NSE token equivalence, duplicate row fix, all 11 query sites, web research sources |
| `C:\Users\itsab\.claude\plans\radiant-singing-raccoon.md` | Implementation plan for Approach C (8 steps, all completed) |
| `backend/app/services/brokers/market_data/instrument_query.py` | The new helper — entry point for all NFO instrument queries |

## Resume Notes

- **Start here:** Run `pytest tests/live/test_live_nse_cross_verification.py -v` during market hours (Mon-Fri 9:15-15:30 IST) to verify non-zero LTP values
- **Watch out for:**
  - Upstox instrument CSV CDN returns 403 on weekends — tests skip gracefully
  - User's Upstox `broker_connections` OAuth token is expired (401) — platform `.env` token works fine
  - The `options.py` expiry/strike queries hardcode `source_broker == "kite"` since those routes don't have adapter context — if only SmartAPI instruments exist in DB, those queries return empty
- **Context needed:** Re-read `instrument-token-architecture.md` for the full token equivalence table and query site inventory
