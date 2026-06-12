---
name: market-data-token-refresh-wrapper
description: >
  Transparent reactive token refresh for market-data adapters: get_ltp/get_quote
  are dynamically wrapped at __init__ for refreshable brokers; callers never
  write retry/refresh logic at call sites.
globs: ["backend/app/services/brokers/market_data/**/*.py"]
synthesized: true
version: "1.0.0"
private: true
---

# Market Data Token Refresh — Transparent Wrapper Only

Token refresh is REACTIVE and INVISIBLE to callers. All mechanics live in
`backend/app/services/brokers/market_data/market_data_base.py`
(`MarketDataBrokerAdapter`).

## How the wrapper works

- `__init__` (lines 180-193) creates `self._refresh_lock = asyncio.Lock()` and,
  **only if `self._can_auto_refresh()` is True**, calls
  `self._wrap_with_token_refresh()`.
- `_wrap_with_token_refresh()` (lines 251-268) replaces `get_ltp` and
  `get_quote` on the instance with `functools.wraps`-decorated closures that
  route through `_with_token_refresh()`. `get_best_price()` benefits implicitly
  because it delegates to the wrapped methods.
- `_with_token_refresh()` (lines 222-249) is the retry contract:
  1. Run the operation.
  2. On `AuthenticationError`: non-refreshable → re-raise immediately
     (fail fast → ticker/failover layer takes over).
  3. Refreshable → acquire `self._refresh_lock`, call `_try_refresh_token()`.
  4. Refresh failed → re-raise the ORIGINAL error.
  5. Refresh succeeded → retry the operation exactly ONCE. A second 401
     raises — no loops.

## Which adapters refresh

| Adapter | `_can_auto_refresh()` | Behavior on 401 |
|---|---|---|
| SmartAPI | True | lock → `_try_refresh_token()` → retry once |
| Upstox | True | lock → `_try_refresh_token()` → retry once |
| Kite, Dhan, Fyers, Paytm | False (base default, lines 205-212) | raise immediately → failover |

(The base-class docstring at lines 208-211 names Kite, Dhan, Fyers, Paytm as
the non-refreshable set — keep that docstring in sync when adding adapters.)

## Caller contract

Callers MUST use plain `adapter.get_ltp()` / `adapter.get_quote()` /
`adapter.get_best_price()`. The refresh-and-retry is already inside.

The pre-refactor pattern of explicit `*_with_refresh()` helper functions at
call sites is DEAD and MUST NOT come back (removed in commit `f8f15f5`).
If you find yourself writing `try: get_ltp() except AuthenticationError:
refresh(); get_ltp()` in route or service code, stop — that logic belongs in
the base class and already exists.

## Adding a new adapter — choose a side

1. **Refreshable** (broker exposes a refresh-token or re-login API usable
   without user interaction): override BOTH `_can_auto_refresh()` → `True`
   AND `_try_refresh_token()` (persist the new token, return `True`/`False`).
   Overriding only one of the pair is a bug — `True` + base
   `_try_refresh_token()` (lines 214-220, returns `False`) silently degrades
   to "raise the original error" after acquiring the lock on every 401.
2. **Fail-fast**: inherit the defaults, do nothing. 401 propagates and the
   failover chain handles it.

Either way, the adapter MUST also satisfy the normalization contract in the
class docstring (lines 166-178): rupees as `Decimal` (SmartAPI returns PAISE —
divide by 100), canonical Kite-format symbols, int tokens, IST datetimes,
`UnifiedQuote` returns.

## CRITICAL RULES

- Callers MUST use plain `get_ltp()`/`get_quote()` — NEVER write retry/refresh logic at call sites; `*_with_refresh()` helpers MUST NOT return (commit `f8f15f5`).
- Retry is exactly ONCE per call, under `self._refresh_lock` — MUST NOT add multi-retry loops or refresh-without-lock paths.
- A new adapter MUST either implement BOTH `_can_auto_refresh()` and `_try_refresh_token()`, or inherit fail-fast — never half of the pair.
- Non-refreshable adapters MUST raise `AuthenticationError` immediately; do not swallow 401s into empty-quote returns (that masks failover AND produces the zero-quote chains the option-chain ladder guards against).
- MUST NOT wrap additional methods in `_wrap_with_token_refresh()` without confirming they are idempotent — the wrapper re-executes the operation after refresh.
- Refresh failure MUST re-raise the original `AuthenticationError`, not a new generic exception — `token_policy.py` classification downstream depends on it.
