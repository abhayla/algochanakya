# Session: 2026-04-13-header-prices-and-datasource-badge

**Date:** 2026-04-13 00:00
**Branch:** main

---

## Working Files

| File | Status | Notes |
|------|--------|-------|
| `backend/app/api/routes/orders.py` | modified | Added platform adapter fallback to `/ltp`, `/quote`, `/ohlc` endpoints |
| `backend/app/services/brokers/market_data/upstox_adapter.py` | modified | Added close-price fallback in `get_quote` when LTP is 0 (market closed) |
| `backend/app/utils/dependencies.py` | modified | Fixed `MultipleResultsFound` crash — `scalar_one_or_none()` → `first()` |
| `frontend/src/services/priceService.js` | modified | Added all-zero LTP detection + OHLC fallback in `fetchIndexPrices` |
| `frontend/src/stores/brokerPreferences.js` | modified | Clear `activeSource` on `market_data_source` update to fix stale badge |
| `frontend/tests/stores/brokerPreferences.test.js` | modified | Added 3 regression tests for activeSource clearing behavior |
| `backend/app/utils/market_hours.py` | modified | Added `get_last_trading_close()` and `_is_trading_day()` for EOD snapshot |
| `backend/app/models/eod_option_snapshot.py` | created | SQLAlchemy model for EOD option snapshots |
| `backend/app/models/__init__.py` | modified | Registered `EODOptionSnapshot` model |
| `backend/alembic/env.py` | modified | Import `EODOptionSnapshot` for autogenerate |
| `backend/app/services/options/nse_fetcher.py` | created | NSE v3 API client + parser for option chain data |
| `backend/app/services/options/eod_snapshot_service.py` | created | Orchestration: check freshness → fetch/store → serve EOD data |
| `backend/app/api/routes/optionchain.py` | modified | EOD snapshot fallback when market closed + zero OI |
| `frontend/src/components/common/MarketStatusBanner.vue` | modified | Added "EOD_SNAPSHOT" banner text |
| `frontend/src/views/OptionChainView.vue` | modified | E2E test support changes |
| `backend/tests/conftest.py` | modified | Added EODOptionSnapshot import + cleanup |
| `backend/tests/backend/utils/test_market_hours_eod.py` | created | 8 tests for `get_last_trading_close` |
| `backend/tests/backend/options/test_nse_fetcher.py` | created | 12 tests for NSE fetcher |
| `backend/tests/backend/options/test_eod_snapshot_model.py` | created | 4 tests for model |
| `backend/tests/backend/options/test_eod_snapshot_service.py` | created | 10 tests for service |
| `backend/tests/backend/options/test_optionchain_eod_integration.py` | created | 7 integration tests |
| `tests/e2e/specs/optionchain/optionchain.crossverify.api.spec.js` | created | NSE cross-verification E2E tests |

## Git State

- **Branch:** main
- **Last 5 commits:**
  - 9781129 fix(tests): fix Upstox cross-verification tests — spot match, graceful skips
  - ab7077c fix(tests): use NSE v3 API for cross-verification tests (works on weekends)
  - edc47b9 fix(instruments): add source_broker filtering to prevent duplicate instrument rows
  - 5e2c854 docs(skills): add cross-broker instrument token architecture reference
  - 1855e93 fix(market-data): fix Upstox option chain token keying and add pre-calculated Greeks
- **Uncommitted changes:** Yes — extensive (EOD snapshot feature + header prices fix + data source badge fix)
- **Stash list:** stash@{0}: WIP: Token mapping changes before multi-broker ticker refactor

## Key Decisions

- **EOD snapshot upsert uses DELETE+INSERT**: Chose over `ON CONFLICT` for SQLite test compatibility. Transaction wraps both operations.
- **asyncio.Lock per (underlying, expiry)**: Prevents multiple concurrent NSE fetches for the same option chain. First caller fetches, others wait on lock then read from DB.
- **NSE failure returns stale DB data**: Better to serve stale data than show zeros. Returns None only on cold DB + NSE failure.
- **`activeSource` cleared on preference save**: The `activeSourceLabel` getter prioritizes WebSocket-reported `activeSource` over saved preference. Clearing it on save ensures the badge immediately reflects the new preference, before WebSocket reconnects.
- **Platform adapter fallback on orders endpoints**: When user's preferred broker fails (e.g., expired Upstox token), fall back to `get_platform_market_data_adapter()` for `/ltp`, `/quote`, `/ohlc`.
- **`first()` over `scalar_one_or_none()`**: In `get_current_broker_connection`, multiple active broker connections caused `MultipleResultsFound` crash that bypassed CORS headers.

## Task Progress

### Completed

- EOD snapshot caching (market hours, model, NSE fetcher, service, route integration, frontend banner)
- All 41 EOD-related backend tests passing
- Header index prices blank fix (Upstox zero LTP fallback + platform adapter fallback on orders endpoints)
- `MultipleResultsFound` crash fix in `dependencies.py`
- Market data source badge not updating fix (`brokerPreferences.js` — clear `activeSource` on save)
- 3 regression tests for data source badge behavior
- Live browser verification of badge fix (5 consecutive switches, all correct)

### In Progress

- None — all tasks completed

### Blocked

- None

## Relevant Docs

| Document | Relevance |
|----------|-----------|
| `docs/architecture/broker-abstraction.md` | Multi-broker adapter pattern used in fallback logic |
| `backend/CLAUDE.md` | Backend patterns, ticker architecture, credential loading order |

## Resume Notes

- **Start here:** All tasks are complete. Consider committing the changes in logical groups: (1) EOD snapshot feature, (2) header prices fix, (3) data source badge fix
- **Watch out for:** The uncommitted changes span 3 independent features — split into separate commits
- **Context needed:** `frontend/src/stores/brokerPreferences.js` for the badge fix, `backend/app/api/routes/orders.py` for the platform fallback pattern
