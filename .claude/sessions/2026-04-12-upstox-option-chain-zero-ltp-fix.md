# Session: 2026-04-12-upstox-option-chain-zero-ltp-fix

**Date:** 2026-04-12 13:15 IST
**Branch:** main

---

## Working Files

| File | Status | Notes |
|------|--------|-------|
| `backend/app/services/brokers/market_data/upstox_adapter.py` | modified (committed) | Fixed `get_option_chain_quotes()`: added `token_to_symbol` param, replaced broken `trading_symbol` lookup with `instrument_key` token extraction, added `"greeks"` sub-dict from Upstox response |
| `backend/app/api/routes/optionchain.py` | modified (committed) | Pass `token_to_symbol` at call site (line 366), use Upstox pre-calculated Greeks when available (CE block ~line 492, PE block ~line 543), falling back to Newton-Raphson |
| `backend/tests/backend/brokers/test_upstox_market_data_adapter.py` | modified (committed) | Added 4 tests: `test_get_option_chain_quotes_with_token_mapping`, `_no_token_mapping`, `_market_closed`, `_includes_greeks` |
| `backend/tests/backend/routes/test_optionchain_upstox_keying.py` | created (committed) | 3 tests for Greeks usage: `test_upstox_greeks_used_when_available`, `test_fallback_to_newton_raphson_without_greeks`, `test_upstox_greeks_with_zero_iv_triggers_fallback` |
| `.claude/skills/broker-shared/SKILL.md` | modified (committed) | v2.0.0: added 13 auto-trigger words, Step 6 auto-capture rule |
| `.claude/skills/broker-shared/references/instrument-token-architecture.md` | created (committed) | Cross-broker instrument token research: NSE exchange token equivalence, tradingsymbol formats, rate limits, option chain sources |
| `backend/app/services/brokers/market_data/factory.py` | read | Traced adapter selection flow — user preference → broker-specific factory |
| `backend/app/services/brokers/market_data/market_data_base.py` | read | Verified `get_best_price()` fallback logic (LTP → close) |
| `backend/app/utils/market_hours.py` | read | Verified `get_data_freshness()` returns "LIVE"/"LAST_KNOWN" correctly |
| `backend/app/services/brokers/market_data/smartapi_adapter.py` | read | Verified SmartAPI snap path unaffected — no `get_option_chain_quotes()`, no `"greeks"` in response |
| `backend/app/models/instruments.py` | read | Unique constraint: `(instrument_token, source_broker)` — allows duplicate rows per strike |
| `backend/app/services/instrument_master.py` | read | `populate_broker_token_mappings()` correctly filters `source_broker='kite'` |
| `backend/app/services/instruments.py` | read | Legacy Kite CSV instrument loader — sets `source_broker='kite'` |

## Git State

- **Branch:** main
- **Last 5 commits:**
  - 5e2c854 docs(skills): add cross-broker instrument token architecture reference
  - 1855e93 fix(market-data): fix Upstox option chain token keying and add pre-calculated Greeks
  - c062f3a fix(market-data): return previous close prices when market is closed
  - b552dd2 fix(e2e): verify and fix Phase 1 E2E tests
  - 548f86f fix(schemas): convert dashboard P&L/metrics Decimal fields to float
- **Uncommitted changes:** yes — old session file deletions, `.claude/settings.json`, `navigation.cross-screen.spec.js` (pre-existing, unrelated)
- **Stash list:** stash@{0}: WIP: Token mapping changes before multi-broker ticker refactor

## Key Decisions

- **Approach C chosen over A and B for instrument query fix:** Create a shared `get_nfo_instruments()` helper instead of adding `source_broker` filter to 12 individual query sites (A) or redesigning the schema (B). Centralizes logic, low risk, ~1 hour to implement.
- **Upstox adapter uses `instrument_key` token, not `trading_symbol`:** The Upstox `/v2/option/chain` API does NOT return `trading_symbol`. The adapter now extracts the numeric token from `instrument_key` (e.g., `54816` from `NSE_FO|54816`) and maps to canonical symbol via caller-provided `token_to_symbol` dict.
- **Pre-calculated Greeks from Upstox used when available:** Upstox returns IV, delta, gamma, theta, vega in its option chain response. The route now checks for a `"greeks"` sub-dict before running Newton-Raphson. SmartAPI path falls back to Newton-Raphson automatically (no `"greeks"` in response).
- **NSE exchange token equivalence discovered:** SmartAPI `symboltoken` == Upstox `exchange_token` == Kite `exchange_token` (all NSE-assigned for F&O). Kite `instrument_token` is Kite-internal and different. This is the root cause of the duplicate instrument row problem.

## Task Progress

### Completed

- Investigated and confirmed root cause: Upstox `/v2/option/chain` has NO `trading_symbol` field
- Fixed `upstox_adapter.py` — token-based keying + Greeks extraction (TDD: 4 tests)
- Fixed `optionchain.py` — pass `token_to_symbol`, use Upstox Greeks with Newton-Raphson fallback
- Verified SmartAPI path is unaffected by the fix
- Compared Upstox vs SmartAPI screenshots — both show zeros (deeper issue)
- Discovered deeper root cause: duplicate instrument rows (Kite + SmartAPI `source_broker`) pollute `token_to_symbol` mapping
- Researched cross-broker instrument/token architecture (Kite, SmartAPI, Upstox)
- Brainstormed 3 approaches for the instrument query fix
- Saved research to `/broker-shared` skill with auto-trigger words
- All 56 unit tests pass, 8 regression tests pass

### In Progress

- **Implement Approach C — shared `get_nfo_instruments()` helper** — Brainstorm complete (Step 3 done, user approved Approach C), spec not yet written, implementation not started. This is the fix that will make the option chain actually show data for both Upstox and SmartAPI.

### Blocked

- None

## Relevant Docs

| Document | Relevance |
|----------|-----------|
| `.claude/skills/broker-shared/references/instrument-token-architecture.md` | Cross-broker token research — NSE exchange token equivalence, the core of the fix |
| `C:\Users\itsab\.claude\plans\glowing-stargazing-owl.md` | Plan file for the Upstox adapter fix (Step 2, completed) |
| `.claude/rules/canonical-symbol-format.md` | Kite format is the internal standard — affects which `source_broker` to prefer |
| `backend/CLAUDE.md` | Backend architecture, broker abstraction, instrument tables |

## Resume Notes

- **Start here:** Write the spec (Brainstorm Step 5) for Approach C, then implement the shared `get_nfo_instruments()` helper. The brainstorm reached Step 3 (approach chosen) — Step 4 (design) and Step 5 (spec) remain.
- **Watch out for:**
  - The `instruments` table has 696 rows for NIFTY 13-Apr-2026 (492 kite + 204 smartapi). Queries without `source_broker` filter return duplicates.
  - 12 query sites across 6 files need updating (see brainstorm findings): `optionchain.py`, `options.py`, `orders.py`, `instruments.py`, `expected_move_service.py`, `oi_analysis_service.py`
  - 6 of these are CRITICAL (option chain, orders, instrument lookup, ATM straddle)
  - User's Upstox `broker_connections` token is expired (401) — `.env` platform token works fine
  - `data_freshness` returns correctly from backend but may show `None` in some test paths (not a real bug)
- **Context needed:** Re-read `references/instrument-token-architecture.md` for the token equivalence table. Re-read the brainstorm Approach C description for the helper function design.
