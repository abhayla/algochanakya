# Findings: Option Chain Performance Optimization

## Discoveries

- Redis is deployed on VPS (103.118.16.189:6379/1), `redis.asyncio` already imported in `database.py`, `get_redis()` dependency exists but unused for option chain
- `get_platform_market_data_adapter()` already exists in `factory.py:457` — shared org-level adapter using `.env` credentials. No need to build adapter pooling from scratch.
- Market hours utility (`market_hours.py`) has `is_market_open()`, `_is_trading_day()`, `get_last_trading_close()` with 19 NSE 2026 holidays. Missing `get_next_market_open()` — needs to be added.
- Option chain route (`optionchain.py`) is 857 lines. The `/chain` endpoint (lines 267-738) is a ~470-line monolith that needs extraction into a callable function for caching.
- Adapters are stateless REST (not WebSocket) — safe to pool/singleton. Base class has `asyncio.Lock` for token refresh serialization. Concurrent-safe.
- Frontend `setUnderlying()` (optionchain.js:195) resets state AND calls `fetchExpiries()` sequentially. `fetchOptionChain()` has a 30s timeout override.
- Frontend has zero caching, zero deduplication, zero request coalescing.

## Constraints Found

- Redis is on remote VPS — ~5-20ms network round-trip per call. Minimize Redis calls per request (single GET for cache hit).
- NSE API rate-limits aggressively — fan-out must throttle at ~1 req/2s
- `_compute_option_chain()` needs to work both with and without a `user` parameter (for prefetch which runs without user context)
- Background prefetch via `asyncio.create_task()` runs outside request lifecycle — needs own DB session via `AsyncSessionLocal()`
- JSON serialization of Decimal values — response already uses float-converted prices, `json.dumps(result, default=str)` handles edge cases

## Key Code References

| File | Lines | What |
|---|---|---|
| `backend/app/database.py:54-60` | `get_redis()` — Redis pool init | Reuse for cache |
| `backend/app/utils/market_hours.py:1-102` | Full market hours utility | Extend with `get_next_market_open()` |
| `backend/app/api/routes/optionchain.py:267-738` | `/chain` endpoint | Extract into `_compute_option_chain()` |
| `backend/app/services/options/eod_snapshot_service.py:24` | `_fetch_locks` pattern | Reuse lock pattern for prefetch |
| `backend/app/services/brokers/market_data/factory.py:457` | `get_platform_market_data_adapter()` | Use as singleton base |
| `frontend/src/stores/optionchain.js:195-264` | Store actions | Modify for parallel fetch |
| `frontend/src/views/OptionChainView.vue:415-420` | Tab switch handler | Add `Promise.all` |
