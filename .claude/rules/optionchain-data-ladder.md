---
name: optionchain-data-ladder
description: >
  Option-chain serving ladder: Redis cache with market-aware TTL and request
  coalescing, live-engine fast path, lazy EOD snapshots, and the
  live → broker → EOD → 503 exhaustion order. One subsystem, four invariant groups.
globs: ["backend/app/services/options/**/*.py", "backend/app/api/routes/optionchain.py"]
synthesized: true
version: "1.0.0"
private: false
---

# Option Chain Data Ladder

Every option-chain response is served by walking a fixed ladder. Each rung has
invariants that downstream code depends on — changing one rung silently breaks
the others.

```
Request → Redis cache (3s TTL live / until-next-open + jitter after hours)
        → Live engine snapshot (market hours, WebSocket ticks)
        → Broker REST (user adapter → platform adapter → failover chain)
        → EOD snapshot (lazy, after-hours)
        → 503
```

## (a) CACHE — `option_chain_cache.py`

- TTL is **3 seconds during market hours** (`LIVE_MARKET_CACHE_TTL = 3`, line 25).
  Rationale is in the comment at lines 23-24: NSE refreshes OI every ~3 minutes,
  so 3s staleness is safe for display, NOT for order execution. MUST NOT raise
  this without revisiting that comment; MUST NOT use this cache for execution paths.
- After hours, TTL = seconds until next market open, floored at 60s, with
  **±10% jitter** (`get_cache_ttl_seconds`, lines 32-42) to prevent a cache
  stampede at market open. MUST keep the jitter when touching TTL logic.
- Concurrent identical requests MUST coalesce via `get_or_compute()`
  (lines 89-124): Redis hit → return; key in `_inflight` → await the existing
  future; otherwise compute, cache, resolve. MUST NOT call `_compute_option_chain`
  directly from a new endpoint — go through `get_or_compute()`.
- Redis read/write failures are non-fatal by design (lines 53-79 log and
  fall through). MUST NOT convert these to raises.
- The platform adapter is a module-level singleton cached for 1 hour
  (`get_cached_platform_adapter`, lines 131-145, `_ADAPTER_TTL = 3600`).
  SHOULD reuse it instead of calling `get_platform_market_data_adapter` per request.

## (b) FAST PATH — live engine, `option_chain_live_engine.py`

- Chains register with the live engine on the **first API request during market
  hours** (`register_chain`, lines 75-119). There is no eager registration at startup.
- Route handlers MUST check `engine.get_fresh_snapshot()` BEFORE any broker
  call — see `optionchain.py` lines 507-534 (`_compute_option_chain` fast path,
  guarded by `is_market_open()`).
- A snapshot that has never received ticks is STALE: `register_chain` initializes
  `"last_tick_at": 0` (line 111) and `get_fresh_snapshot` returns `None` when
  `snap["last_tick_at"] == 0` (line 160) or older than `max_age_seconds`
  (line 162). MUST serve from broker in that case — never fabricate from an
  untickled registration.
- The engine is wired as the FIRST callback in the composite tick dispatch,
  before `router.dispatch`: `main.py` line 177 wires the pool, lines 195-208
  build `_composite_tick_dispatch` (engine `on_tick` sync-first, then the
  original async `router.dispatch`) and re-assign `pool._on_tick`. MUST NOT
  reorder — the engine's snapshot freshness depends on seeing ticks before fan-out.

## (c) EOD SNAPSHOTS — `eod_snapshot_service.py`

- NEVER fetched at startup. Fetched lazily on the first after-hours request
  where the broker response looks closed: `_should_use_eod_snapshot()`
  (`optionchain.py` lines 50-61) — ≥90% of strikes with `oi == 0` (Upstox can
  return OI for 1-2 ATM strikes even when closed, hence not 100%).
- Freshness = `captured_at >= get_last_trading_close()`
  (`is_snapshot_fresh`, `eod_snapshot_service.py` lines 30-40). MUST NOT
  substitute a wall-clock age check — a Friday snapshot stays fresh all weekend.
- Fetches are locked per `(underlying, expiry)` inside `get_snapshot()`
  (lines 42+: check DB freshness → return, or fetch + store under lock).

## (d) EXHAUSTION LADDER — `optionchain.py`

- Order is FIXED: live engine → broker(s) via the failover chain → EOD
  snapshot → 503. The last rung is `_apply_exhaustion_eod_fallback()`
  (lines 81-139): empty `all_quotes` after broker exhaustion → try snapshot →
  raise `HTTP_503_SERVICE_UNAVAILABLE` if none.
- A primary-broker failure mid-session MUST restore live data via this ladder,
  not via bespoke retry code (regression fixed in commit `f8c954e`).
- Beware the all-zero-quotes trap: SmartAPI's WebSocket snap can stream
  placeholder zero ticks on an expired REST JWT, producing a non-empty dict
  that defeats both failover and EOD fallback. `_is_all_zero_quotes()`
  (lines 63-78) exists for exactly this; MUST keep it in the ladder.

## PREFETCH — `option_chain_prefetch.py` (lazy-only, NEVER cron)

- Triggered by the first after-hours request via `trigger_prefetch_if_needed()`
  (lines 116-149). MUST NOT add a cron/scheduler for this — the spec in the
  module docstring (lines 7-12) is explicit.
- Deduped once per trading session using
  `get_last_trading_close().isoformat()` as `_prefetch_session_key`, with a
  double-check after acquiring `_prefetch_lock` (lines 132-140). The fan-out
  itself runs OUTSIDE the lock (lines 143-149); failure resets the key so the
  next request retries.
- Fan-out is throttled at `_THROTTLE_SECONDS = 2.0` between requests (line 39,
  slept at line 109) — NSE rate limits. MUST NOT parallelize the fan-out.
- Uses its own `AsyncSessionLocal` (line 20, used in
  `_get_expiries_for_underlying`) because it runs outside the request
  lifecycle. MUST NOT pass a request-scoped `db` session into prefetch code.
- Prefetch failures are non-blocking: log and continue; never block startup
  or the triggering request.

## CRITICAL RULES

- MUST route all option-chain computation through `get_or_compute()` — never bypass coalescing.
- MUST check `engine.get_fresh_snapshot()` before broker calls during market hours; `last_tick_at == 0` means STALE → broker.
- MUST keep the live engine as the first callback in `_composite_tick_dispatch` (`main.py` ~195-208).
- MUST NOT fetch EOD snapshots at startup or via cron — lazy on first after-hours request only, gated by the ≥90% zero-OI check.
- MUST keep the exhaustion order live → broker → EOD → 503; the 503 in `_apply_exhaustion_eod_fallback` is the only acceptable hard failure.
- MUST NOT remove the ±10% TTL jitter, the 60s TTL floor, or the 2.0s prefetch throttle.
- MUST use `AsyncSessionLocal` (not request sessions) in any background option-chain work.
