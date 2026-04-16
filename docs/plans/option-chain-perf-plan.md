# Implementation Plan: Option Chain Performance Optimization

**Created:** 2026-04-15
**Spec:** [docs/specs/option-chain-performance-spec.md](../specs/option-chain-performance-spec.md)
**Estimated total time:** ~67 min (with 20% buffer)
**Critical path:** Task 1 → 2 → 3 → 4 → 5 → 10

## Summary

5-component optimization: Redis response cache (after-hours) + request coalescing + platform adapter singleton + background fan-out prefetch + frontend parallel fetch.

**Target:** After-hours cache hit < 50ms (currently 1-3s). 1000 concurrent users = 1 broker API call.

---

## Atomic Plan 1: Market Hours Utility + Cache Foundation

- [ ] **Task 1:** Add `get_next_market_open()` to `market_hours.py`
  - Files: `backend/app/utils/market_hours.py` (modify)
  - Returns next market open datetime (9:15 IST), skipping weekends + NSE holidays
  - Verify: `cd backend && PYTHONPATH=. python -c "from app.utils.market_hours import get_next_market_open; print('OK')"`
  - Time: ~5m | Depends on: None

- [ ] **Task 2:** Create `option_chain_cache.py` — Redis cache + coalescing + adapter singleton
  - Files: `backend/app/services/options/option_chain_cache.py` (create)
  - Contains: `get_cache_ttl_seconds()`, `get_or_compute()`, `get_cached_platform_adapter()`
  - Cache key: `optionchain:{underlying}:{expiry}`, TTL = seconds until next market open
  - Request coalescing via `_inflight` dict of asyncio.Futures
  - Verify: `cd backend && PYTHONPATH=. python -c "from app.services.options.option_chain_cache import get_or_compute; print('OK')"`
  - Time: ~9m | Depends on: Task 1

## Atomic Plan 2: Route Integration + Prefetch

- [ ] **Task 3:** Extract compute logic from `/chain` into `_compute_option_chain()`
  - Files: `backend/app/api/routes/optionchain.py` (modify)
  - Move lines 305-730 into standalone async function
  - Route handler becomes: validation → `get_or_compute(underlying, expiry, compute)` → return
  - Verify: `cd backend && PYTHONPATH=. python -c "from app.api.routes.optionchain import _compute_option_chain; print('OK')"`
  - Time: ~13m | Depends on: Task 2

- [ ] **Task 4:** Use `get_cached_platform_adapter()` in extracted compute function
  - Files: `backend/app/api/routes/optionchain.py` (modify)
  - After-hours: use platform singleton (no per-user adapter)
  - Live market: try user adapter → fallback to platform singleton
  - Verify: `cd backend && PYTHONPATH=. python -c "import inspect; from app.api.routes.optionchain import _compute_option_chain; assert 'get_cached_platform_adapter' in inspect.getsource(_compute_option_chain); print('OK')"`
  - Time: ~5m | Depends on: Task 3

- [ ] **Task 5:** Create `option_chain_prefetch.py` — background fan-out
  - Files: `backend/app/services/options/option_chain_prefetch.py` (create)
  - First after-hours request triggers: ALL 5 indexes x ALL active expiries
  - Throttled: asyncio.Semaphore(1) + 2s delay between NSE calls
  - Deduplication: `_prefetch_done_for_session` tracks last trading close
  - Wired into route via `asyncio.create_task(trigger_prefetch_if_needed())`
  - Verify: `cd backend && PYTHONPATH=. python -c "from app.services.options.option_chain_prefetch import trigger_prefetch_if_needed; print('OK')"`
  - Time: ~13m | Depends on: Task 3

## Atomic Plan 3: Frontend Optimization

- [ ] **Task 6:** Add expiry cache to optionchain store
  - Files: `frontend/src/stores/optionchain.js` (modify)
  - `_expiryCache` object keyed by underlying, populated on first fetch, served from memory on re-visit
  - Verify: `cd frontend && npm run lint -- --no-fix src/stores/optionchain.js`
  - Time: ~5m | Depends on: None (parallelizable with backend)

- [ ] **Task 7:** Parallel fetch on tab switch
  - Files: `frontend/src/stores/optionchain.js` (modify), `frontend/src/views/OptionChainView.vue` (modify)
  - `setUnderlying()` no longer calls `fetchExpiries()` internally
  - `handleUnderlyingChange()` uses `Promise.all([fetchExpiries(), fetchOptionChain()])`
  - Verify: `cd frontend && npm run lint -- --no-fix src/views/OptionChainView.vue`
  - Time: ~8m | Depends on: Task 6

## Atomic Plan 4: Testing & Verification

- [ ] **Task 8:** Unit tests — `get_next_market_open()` + `get_cache_ttl_seconds()`
  - Files: `backend/tests/test_option_chain_cache.py` (create)
  - Cases: weekday evening, weekend, holiday, pre-market, long weekend, during market
  - Verify: `cd backend && PYTHONPATH=. pytest tests/test_option_chain_cache.py -v -p no:cov -o "addopts="`
  - Time: ~8m | Depends on: Task 1, Task 2

- [ ] **Task 9:** Integration tests — cache hit/miss + coalescing
  - Files: `backend/tests/test_option_chain_cache.py` (modify)
  - Mock Redis, verify compute_fn called once on miss, zero on hit, once on N concurrent misses
  - Verify: `cd backend && PYTHONPATH=. pytest tests/test_option_chain_cache.py::TestGetOrCompute -v -p no:cov -o "addopts="`
  - Time: ~8m | Depends on: Task 2

- [ ] **Task 10:** Manual end-to-end verification
  - Start dev stack, navigate to option chain
  - Verify: (a) first request caches, (b) second request < 50ms, (c) tab switch ~1-2s, (d) Redis keys exist
  - Check: `cd backend && PYTHONPATH=. python -c "import asyncio, redis.asyncio as r; asyncio.run((lambda: r.from_url('redis://103.118.16.189:6379/1').keys('optionchain:*'))())"`
  - Time: ~11m | Depends on: All

---

## Dependency Graph

```
Task 1 (market_hours) → Task 2 (cache module) → Task 3 (extract compute) → Task 4 (adapter singleton)
                                                        ↓
                                                  Task 5 (prefetch)
                                                        ↓
                                                  Task 10 (e2e verify)

Task 6 (expiry cache) → Task 7 (parallel fetch) ────→ Task 10

Task 2 → Task 8 (unit tests) ───────────────────────→ Task 10
Task 2 → Task 9 (integration tests) ────────────────→ Task 10
```

**Critical path:** 1 → 2 → 3 → 4 → 5 → 10 = ~56m (buffered: ~67m)
**Parallel tracks:** Frontend (Tasks 6-7, ~13m) | Tests (Tasks 8-9, ~16m)

## New Files Created

| File | Purpose |
|---|---|
| `backend/app/services/options/option_chain_cache.py` | Redis cache, TTL, coalescing, adapter singleton |
| `backend/app/services/options/option_chain_prefetch.py` | Background fan-out prefetch |
| `backend/tests/test_option_chain_cache.py` | Unit + integration tests |

## Modified Files

| File | Change |
|---|---|
| `backend/app/utils/market_hours.py` | Add `get_next_market_open()` |
| `backend/app/api/routes/optionchain.py` | Extract `_compute_option_chain()`, integrate cache layer |
| `frontend/src/stores/optionchain.js` | Expiry cache, remove fetchExpiries from setUnderlying |
| `frontend/src/views/OptionChainView.vue` | `Promise.all` for tab switch |
