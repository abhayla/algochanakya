# Spec: Data Source Auto-Refresh on Login and 401

**Author:** Claude Code
**Date:** 2026-04-15
**Status:** DRAFT
**Approach:** A+B (Login Warmup + Lazy Retry Middleware)

---

## Problem Statement

When a user logs into AlgoChanakya via any broker (e.g., Zerodha OAuth), the market
data source broker (e.g., Upstox or AngelOne) may have an expired token. The login
succeeds, the dashboard loads, but option chain/positions/WebSocket ticks show all
zeros because the data source returns 401 and there is no retry mechanism.

Currently:
- Platform tokens (Upstox, AngelOne) are only refreshed at **server startup**
- If a token expires mid-session (AngelOne: 8h, Upstox: ~1 year), no auto-refresh occurs
- `broker_instrument_tokens` mappings go stale when new weekly expiries appear (every Thursday)
- Login and market data initialization are completely disconnected

Impact: Every user sees zero prices until the backend is manually restarted.

## Chosen Approach: Proactive Warmup + Reactive Retry

**Proactive (A):** On every user login, a background task verifies and refreshes
platform data source tokens. By the time the frontend loads (~2-3s), data sources
are ready.

**Reactive (B):** Every market data adapter method retries once on 401 after
refreshing the token. Handles mid-session token expiry (AngelOne 8h JWT).

Why not just reactive? First request after login takes 3-5s to refresh. Traders
notice this delay.

Why not just proactive? Doesn't handle mid-session token expiry. AngelOne JWT
expires after 8h — a trader who logged in at 9:15 AM hits 401 at 5:15 PM.

---

## Design

### Layer 1: Reactive — Adapter Token Retry (covers all consumers)

**File:** `backend/app/services/brokers/market_data/market_data_base.py`

Add `_with_token_refresh(operation, *args, **kwargs)` to `MarketDataBrokerAdapter`:
1. Execute operation normally
2. On `AuthenticationError` → check `token_policy.classify_auth_error()`
3. If RETRYABLE or RETRYABLE_ONCE → acquire Redis lock `data_source:refresh_lock:{broker}` (30s TTL)
4. Call `_try_refresh_token()` (implemented by each refreshable adapter)
5. Retry the operation exactly once
6. If retry fails → raise original error (no infinite loops)

**Refreshable adapters:**
- `UpstoxMarketDataAdapter._try_refresh_token()` → calls `platform_token_refresh.refresh_upstox_token()`
- `SmartAPIMarketDataAdapter` — already has auto-refresh via `get_valid_smartapi_credentials(auto_refresh=True)`

**Non-refreshable adapters (Kite, Dhan, Fyers, Paytm):**
- `_can_auto_refresh()` returns False → 401 raises immediately → failover handles it

**Concurrency protection:**
- Redis lock `data_source:refresh_lock:{broker}` with 30s TTL prevents concurrent refresh storms
- If lock is held, second caller waits up to 10s for the first refresh to complete, then retries

### Layer 2: Proactive — Login Callback Warmup

**New file:** `backend/app/services/brokers/data_source_warmup.py`

```
async def warm_data_sources(db_factory) -> dict:
    """Background task: ensure platform data sources are ready.
    
    Called after every user login. Non-blocking — runs as asyncio.create_task().
    
    Returns dict of {broker: status} for logging.
    """
    results = {}
    for broker in ORG_ACTIVE_BROKERS:  # ["angelone", "upstox"]
        try:
            adapter = _create_platform_adapter(broker, db)
            await adapter.get_best_price(["NIFTY"])  # lightweight health check
            results[broker] = "healthy"
        except AuthenticationError:
            refreshed = await _refresh_platform_token(broker)
            results[broker] = "refreshed" if refreshed else "failed"
        except Exception as e:
            results[broker] = f"error: {e}"
    
    # Check instrument mapping freshness
    await _ensure_instrument_mappings_fresh(db)
    return results
```

**Integration in auth callbacks:**
- `auth.py` Zerodha callback: add `asyncio.create_task(warm_data_sources(...))`
- `auth.py` AngelOne callback: same
- `auth.py` Upstox callback: same
- `auth.py` Dhan callback: same

All callbacks get the same one-liner. The warmup is fire-and-forget — login
redirect happens immediately.

### Layer 3: Instrument Mapping Freshness

**File:** `backend/app/services/instrument_master.py`

New method: `ensure_mappings_fresh(db)`

1. Query distinct expiries in `broker_instrument_tokens` for broker='smartapi'
2. Calculate current trading expiries (this week's Thursday + current month-end)
3. If any current expiry is missing → re-run `populate_broker_token_mappings(db)`
4. Cache freshness check result in Redis for 1 hour to avoid repeated DB queries

Called from:
- `data_source_warmup.warm_data_sources()` (on login)
- `main.py` lifespan (on startup, after existing populate call)

### Layer 4: Failover Notification

When any market data consumer falls back to a different broker due to auth failure:

**Backend:** Set Redis key `data_source:failover:{user_id}` with JSON payload:
```json
{"from": "upstox", "to": "smartapi", "reason": "token_expired", "ts": "2026-04-15T09:20:00Z"}
```

**API:** Add response header `X-Data-Source-Failover: upstox->smartapi` on responses
that used a fallback adapter.

**Frontend:** Axios response interceptor reads `X-Data-Source-Failover` header →
shows non-blocking toast: "Market data switched to AngelOne (Upstox session expired)".
Toast auto-dismisses after 10s. Only shown once per failover event.

---

## Requirement Tiers

### Must Have (this PR)
- REQ-M001: Adapter retry on 401 for Upstox and SmartAPI (reactive layer)
- REQ-M002: Login callback triggers data source warmup (proactive layer)
- REQ-M003: Redis lock prevents concurrent token refresh storms
- REQ-M004: `populate_broker_token_mappings` re-runs when current expiry missing
- REQ-M005: Non-refreshable brokers (Kite, Dhan) fail fast to failover

### Nice to Have (follow-up)
- REQ-N001: Frontend failover banner via `X-Data-Source-Failover` header
- REQ-N002: Dashboard widget shows data source health status (green/yellow/red)
- REQ-N003: Admin endpoint to force-refresh any broker token

### Out of Scope
- REQ-W001: Making Kite/Dhan/Fyers/Paytm auto-refreshable (requires OAuth re-auth)
- REQ-W002: User-level data source token refresh (only platform-level in this PR)
- REQ-W003: Background polling loop (replaced by login-triggered + on-demand approach)
- REQ-W004: Automatic broker preference switching based on reliability metrics

---

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `services/brokers/market_data/market_data_base.py` | Add `_with_token_refresh`, `_can_auto_refresh`, `_try_refresh_token` | ~40 |
| `services/brokers/market_data/upstox_adapter.py` | Implement `_try_refresh_token`, wrap key methods | ~25 |
| `services/brokers/data_source_warmup.py` | NEW — warmup service | ~80 |
| `api/routes/auth.py` | Add warmup task to 4 callbacks | ~8 (2 lines each) |
| `services/instrument_master.py` | Add `ensure_mappings_fresh` | ~30 |
| `api/routes/optionchain.py` | Wrap adapter calls with retry | ~10 |
| **Total** | | ~193 |

## Success Criteria

1. User logs in via Zerodha → option chain shows live prices within 5 seconds
2. AngelOne JWT expires after 8h → next request auto-refreshes, user sees no error
3. Upstox token expired → login warmup refreshes it before dashboard loads
4. New Thursday expiry → instrument mappings auto-refresh on first login
5. Two simultaneous requests hit 401 → only one refresh occurs (Redis lock)
6. Kite/Dhan token expires → immediate failover to next broker, no hang

## Open Questions

None — all decisions made based on trading platform requirements and codebase analysis.

---

## Test Plan

### Unit Tests (TDD — write first)
- `test_adapter_retries_on_401_after_refresh` — mock 401 → refresh → 200
- `test_adapter_no_retry_for_non_refreshable` — Kite 401 → immediate raise
- `test_concurrent_refresh_uses_lock` — two 401s → one refresh call
- `test_warmup_refreshes_expired_token` — expired Upstox → refresh called
- `test_warmup_skips_healthy_token` — valid token → no refresh
- `test_instrument_mappings_refresh_on_new_expiry` — missing Thursday → re-populate

### Integration Tests
- `test_login_callback_triggers_warmup` — mock auth callback → warmup task created
- `test_option_chain_with_expired_token_retries` — 401 → refresh → valid data
- `test_failover_on_unrefreshable_broker` — Kite 401 → falls back to SmartAPI
