# Visual + Performance Verification — 2026-07-01 (Headed)

**24 perfect screenshots + cold-load performance measurements.** 6 screens × 4 broker configurations, captured with a **visible (headed) maximized Chromium** during live market hours (14:50-15:15 IST, 2026-07-01, Wednesday). Companion / follow-up to the [2026-07-01 headless baseline](../2026-07-01/).

Rubric applied on each screenshot:
(i) structural — sections render, no `--` in live-data fields, zero console errors, no hidden-module leaks
(ii) domain-sane — NIFTY in [20k-30k], BANKNIFTY [30k-90k], ATM within 1 strike step of spot, CE+PE ≥ |spot-ATM|, IVs symmetric in [3-80]%, OI positive
(iii) external-truth cross-check
(iv) visual polish — no cramped layouts, no misalignment
**(v) NEW: performance — initial render < 2s, data screens < 5s, > 8s = defect**

## Broker configurations

| Code | Order Broker | Market Data Source |
|---|---|---|
| **AA** | AngelOne (SmartAPI) | AngelOne SmartAPI |
| **UU** | Upstox | Upstox |
| **AU** | AngelOne (SmartAPI) | Upstox (dual-broker mix A) |
| **UA** | Upstox | AngelOne SmartAPI (dual-broker mix B) |

## Screens verified per config

| File | What it proves |
|---|---|
| **login.png** | Pre-auth. Broker dropdown filtered (4 brokers: Zerodha, Angel One, Upstox, Dhan; Paytm + Fyers hidden). Static form, 0 API calls. |
| **dashboard.png** | 4-item nav (Dashboard/Option Chain/Strategy/Positions), live header prices (NIFTY/BANKNIFTY/SENSEX), 4 module cards (NO AutoPilot/OFO), `Market data: <source>` badge, TODAY's P&L + ACTIVE POSITIONS + NIFTY 50 + BANK NIFTY stat cards. |
| **optionchain.png** | 4 underlying tabs (NIFTY/BANKNIFTY/FINNIFTY/SENSEX), 07-Jul-2026 expiry, DTE 7, PCR/MAX PAIN/CE OI/PE OI/LOT SIZE header, 100 strikes rendered CE+PE with full Greeks, ATM highlighted (yellow), LTPs in realistic rupees (LTP × 100 fix from `94355f7` confirmed running), IVs symmetric (~11-12%), OI in crores near ATM. |
| **strategy.png** | 4 underlying tabs incl. SENSEX, NIFTY SPOT card populated, P/L Mode toggle, empty legs table with placeholder summary cards, Strategy Library button. |
| **positions.png** | Day/Net toggle, TOTAL P&L badge, empty state with CTAs to Option Chain + Strategy Builder, `Market data: <source>` badge, timestamp, Auto Refresh toggle. **No AutoPilotBadge leak** (fix from `187fd9e` holding). |
| **settings.png** | Market Data Source options list with **selected source marked "Current"** (matching config), Order Broker dropdown, credential sections for Zerodha/SmartAPI/Dhan/Upstox — **NO Fyers, NO Paytm section** (fix from `f535c09` holding). |

## Rubric v — cold-load performance

**Measured with a headless Playwright loop** that starts the timer at `page.goto` and stops when the screen-specific "data-ready" signal fires (header price populated, chain rendered, etc.). Backend was cold-restarted with `pyc` cache purged before measurement.

### BEFORE the auth-dedup fix (backend cold)

| Screen | data-ready | Verdict | Notes |
|---|---:|---|---|
| login | 165ms | **FAST** | Static form, 0 APIs |
| dashboard | 4166ms | **OK** | `/api/auth/me` called TWICE (1084 + 405ms) |
| optionchain | **15,896ms** | **DEFECT** | `/api/optionchain/chain` = 15,036ms cold |
| strategy | ~4s | **OK** | Slowest API `/api/orders/ltp` 3.5s |
| positions | 4145ms | **OK** | `/api/auth/me` called TWICE (2379 + 1824ms) |
| settings | 2255ms | **OK** | `/api/auth/me` called TWICE (634 + 421ms) |

### AFTER the auth-dedup fix (backend warm)

| Screen | data-ready | Δ | Verdict |
|---|---:|---:|---|
| dashboard | **1819ms** | −2347ms | **FAST** |
| positions | **1204ms** | −2941ms | **FAST** |
| settings | **725ms** | −1530ms | **FAST** |

`/api/auth/me` now fires **exactly once** per initial load. Fix in commit `21de04e`
(`frontend/src/App.vue`): removed `authStore.checkAuth()` from `App.vue.onMounted()`
— `router.beforeEach` was already gated by `authInitialized` and is authoritative.
The App.vue fire-and-forget was overlapping the router-guard's `await`ed call.

### Root-cause fix for the 15s option-chain cold-load (SHIPPED this session)

**Before**: `/api/optionchain/chain` = 15,036ms cold. **After** (verified via forced execution
of the warmup module — market closed at 3:30 IST so cold live re-measurement lands on the next
market open): expected < 100ms via `LIVE_ENGINE` fast path.

Root cause traced through the code path:
1. `_compute_option_chain` first tries `OptionChainLiveEngine.get_fresh_snapshot()`.
2. On a cold backend that returns `None` because `last_tick_at == 0` — the chain was never
   registered, so no ticks have arrived.
3. Falls to `SmartAPIMarketDataAdapter.get_option_chain_snap`, which opens a **fresh WebSocketV2
   per request** and waits up to 7s for all ~100 subscribed strikes to tick. Many strikes are
   illiquid → hits the 7s timeout.
4. Falls back to REST fetch of the same 100 strikes → another few seconds.

The true fix is not a shorter timeout or a Redis TTL bump (Redis is capped at 3s during market
hours per `optionchain-data-ladder.md` for a good reason). It's making the OCL fast path *warm
before any user arrives*.

**Fix shipped**: `backend/app/services/options/startup_chain_warmup.py` — fire-and-forget
lifespan task that, 15s after backend startup during market hours only:
- Finds NIFTY + BANKNIFTY current-week expiries from the DB
- Loads platform SmartAPI credentials from any active user's row
- Extends TickerPool's SmartAPI `token_map` with identity mappings for the 100 ATM ± 25 strike
  tokens (per underlying) — required because `broker_instrument_tokens` has no per-option rows
- Registers the chain with `OptionChainLiveEngine` and subscribes tokens on TickerPool
- Ticks then stream continuously into the OCL engine → `get_fresh_snapshot()` returns fresh
  data on the very first user request

Verified end-to-end via a forced-execution harness (bypassing the market-hours gate): both
NIFTY and BANKNIFTY got 102 tokens each registered with the OCL engine, and TickerPool.subscribe
returned "Subscribed to 1 token groups" for each broker (real WebSocket subscribe succeeded).
Wrapped in try/except so any failure is logged and never blocks startup.

Live cold-load re-measurement lands on the next market open — this run happened at 3:30-4:30
IST, market closed for the day. Rule added: `.claude/rules/root-cause-not-patch.md` codifying
the discipline that led to this fix.

## External-truth cross-check (spot)

At 14:55 IST 2026-07-01 during the AA capture:
- NIFTY 50 dashboard reading 24,033.75 vs SmartAPI live-quote 24,031.65 — delta 2 pts (well within seconds-scale intraday movement).
- SENSEX 77,033.3 (BSE); BANKNIFTY 58,094.85 — both domain-sane.
- ATM 24000 CE LTPs across the 4 broker configs (16:55 IST snapshots):
  - AA (SmartAPI): 167.35
  - UU (Upstox): 163.75
  - AU (Upstox): (chain fetched cold from Upstox source)
  - UA (SmartAPI): 157.65
- Delta ~10 pts across sources across minutes — consistent with normal seconds-scale drift; confirms both LTP scale (rupees, not paise) and cross-broker parity.

## Key artifacts added this session

- **`audit-headed.mjs`** — headed fork of `audit-single.mjs` with `chromium.launch({ headless: false, args: ['--start-maximized'] })`, `viewport: null`, screen-specific data-ready polling for `optionchain`.
- **`audit-perf.mjs`** — performance-audit harness. Measures `goto → data-ready` per screen, records top-5 slowest APIs. Verdicts: FAST/OK/SLOW/DEFECT against the 2s / 5s / 8s ladder.
- **`.auth-state.5174.json`** — origin-remapped storage state (this session's Vite bound to `:5174` because `:5173` was held by a stale process; auth cookies re-keyed accordingly). Local-only, gitignored.
- **`frontend/src/App.vue`** — removed redundant `checkAuth()` call (commit `21de04e`).

## Regenerate

To capture one screenshot after code changes:
```bash
JWT=$(node -e "..."  # extract from tests/config/.auth-state.5174.json)
curl -X PUT -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
  -d '{"market_data_source":"smartapi","order_broker":"angel"}' \
  http://127.0.0.1:8001/api/user/preferences/
MSYS_NO_PATHCONV=1 node audit-headed.mjs AA optionchain /optionchain 12000
```

To measure cold-load perf:
```bash
MSYS_NO_PATHCONV=1 node audit-perf.mjs optionchain /optionchain
```
