# Implementation Plan: Data Source Auto-Refresh

**Created:** 2026-04-15
**Spec:** [data-source-auto-refresh-spec.md](../specs/data-source-auto-refresh-spec.md)
**Approach:** A+B (Reactive Retry + Proactive Login Warmup)
**Estimated total time:** ~45m | With buffer: ~54m

## Atomic Plan 1: Reactive Layer — Base Class + Upstox Refresh [REQ-M001, REQ-M003, REQ-M005]

- [x] **Task 1:** Write failing tests for `_with_token_refresh()` retry logic
  - Files: `backend/tests/backend/brokers/test_token_refresh_retry.py` (create)
  - Tests: retry on AuthenticationError for refreshable, fail fast for non-refreshable, single refresh via lock
  - Verify: `pytest tests/backend/brokers/test_token_refresh_retry.py -v` — all fail (RED)

- [x] **Task 2:** Implement `_with_token_refresh()`, `_can_auto_refresh()`, `_try_refresh_token()` on base class
  - Files: `backend/app/services/brokers/market_data/market_data_base.py` (modify)
  - Verify: `pytest tests/backend/brokers/test_token_refresh_retry.py -v` — all pass (GREEN)

- [x] **Task 3:** Implement `_try_refresh_token()` on UpstoxMarketDataAdapter + wrap key methods
  - Files: `backend/app/services/brokers/market_data/upstox_adapter.py` (modify)
  - Verify: `pytest tests/backend/brokers/test_token_refresh_retry.py -v` — still green

## Atomic Plan 2: Proactive Layer — Login Warmup [REQ-M002]

- [x] **Task 4:** Write failing tests for data_source_warmup service
  - Files: `backend/tests/backend/brokers/test_data_source_warmup.py` (create)
  - Verify: `pytest tests/backend/brokers/test_data_source_warmup.py -v` — all fail (RED)

- [x] **Task 5:** Implement `data_source_warmup.py` service
  - Files: `backend/app/services/brokers/data_source_warmup.py` (create)
  - Verify: `pytest tests/backend/brokers/test_data_source_warmup.py -v` — all pass (GREEN)

- [x] **Task 6:** Wire warmup into auth callbacks
  - Files: `backend/app/api/routes/auth.py`, `backend/app/api/routes/upstox_auth.py`, `backend/app/api/routes/dhan_auth.py` (modify)
  - Verify: `pytest tests/backend/brokers/test_data_source_warmup.py -v` — integration tests pass

## Atomic Plan 3: Instrument Mapping Freshness [REQ-M004]

- [x] **Task 7:** Write failing test for `ensure_mappings_fresh()`
  - Files: `backend/tests/backend/test_instrument_freshness.py` (create)
  - Verify: `pytest tests/backend/test_instrument_freshness.py -v` — fails (RED)

- [x] **Task 8:** Implement `ensure_mappings_fresh()` on InstrumentMasterService
  - Files: `backend/app/services/instrument_master.py` (modify)
  - Verify: `pytest tests/backend/test_instrument_freshness.py -v` — passes (GREEN)

## Dependency Graph

```
Task 1 → Task 2 → Task 3  (critical path: reactive layer)
Task 4 → Task 5 → Task 6  (proactive layer, independent of reactive)
Task 7 → Task 8            (instrument freshness, independent)
```

Tasks 1, 4, 7 can run in parallel. Tasks 2, 5, 8 can run in parallel.
Critical path: Task 1 → Task 2 → Task 3 → Task 6 (warmup needs refresh to exist)

## Success Criteria

1. `AuthenticationError` on refreshable broker → auto-refresh → retry succeeds
2. `AuthenticationError` on non-refreshable broker → immediate raise (fail fast)
3. Concurrent 401s → single refresh call (asyncio lock)
4. Login callback fires warmup task (fire-and-forget)
5. Missing expiry in broker_instrument_tokens → auto-repopulate
