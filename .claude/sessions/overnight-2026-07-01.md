# Overnight Campaign Status — 2026-07-01

**Branch:** `feat/visible-views-and-hide-modules` (cut fresh from `origin/main`)
**Commits landed:**
- `1a36629` feat(frontend): hide AutoPilot/AI/Watchlist/OFO + Paytm/Fyers via feature flags
- `62e2407` fix(frontend): extract goToSettings handler so build parses

---

## TL;DR for Abhay (read first)

🟢 **Phase 1 SHIPPED.** AutoPilot, AI module, Watchlist, OFO views and Paytm + Fyers brokers are HIDDEN — no nav entry, no route registered (URL surface gone), no Settings dropdown entry. Reversible by flipping a flag in `frontend/.env.local`. Build green. The hide system is covered by a new `tests/e2e/specs/header/hidden-modules.happy.spec.js` so it can't silently regress.

🔴 **Phases 2-5 BLOCKED — needs your action.** The dev backend cannot start because PostgreSQL on the production VPS (`103.118.16.189:5432`) is unreachable from this dev machine. Without backend, E2E tests cannot authenticate, so the per-broker AngelOne / Upstox / mix-broker verifications cannot run.

## What I need from you (single line)

**Whitelist this dev machine's public IP in `pg_hba.conf` on `103.118.16.189` (PostgreSQL).** Alternatives: (a) stand up a local PostgreSQL on `127.0.0.1:5432` with `alembic upgrade head` applied and override `DATABASE_URL` in `backend/.env`; (b) point dev to a separate staging DB.

Once the DB is reachable, I can resume autonomously — Phases 2-5 below are pre-staged as tasks and pre-credentialed (AngelOne + Upstox full credential sets are present in `backend/.env`).

---

## Locked decision tree (from the grill)

| Branch | Decision |
|---|---|
| Broker scope | AngelOne + Upstox tonight; Paytm/Fyers hidden; Kite/Dhan deferred (paid). |
| Hide mechanism | env-driven feature flags via `frontend/src/config/features.js`. |
| "Working e2e" | `npm run test:specs:<view>` green + screenshot verification pass. |
| Autonomy bounds | dev-only (8001/5173), current branch, conventional commits, no push, no PR. |
| Credentials | AngelOne (full 3-key set + TOTP) + Upstox (full + TOTP + access token) staged in `backend/.env`. |
| Market-closed overnight | REST + EOD paths only; live WebSocket tick verification deferred to 09:15 IST market open. |
| Hidden Settings entries | Paytm + Fyers filtered from broker dropdowns alongside hidden modules. |
| Kite / Dhan | Deferred — paid integrations, separate decision tomorrow. |

---

## Phase 1 — DONE

| Item | File | Status |
|---|---|---|
| Feature flag config | `frontend/src/config/features.js` | ✅ |
| Flag entries | `frontend/.env`, `.env.local`, `.env.example` | ✅ |
| Router gating (URL not registered) | `frontend/src/router/index.js` | ✅ |
| Nav filter | `frontend/src/components/layout/KiteHeader.vue` | ✅ |
| Settings broker dropdown filter | `frontend/src/components/settings/BrokerSettings.vue` | ✅ |
| Build green | `npm run build` | ✅ |
| Hidden assertion spec | `tests/e2e/specs/header/hidden-modules.happy.spec.js` | ✅ (written; not yet run due to backend block) |
| Commit | `1a36629`, `62e2407` | ✅ |

### What flips to re-enable

```bash
# frontend/.env.local
VITE_ENABLE_AUTOPILOT=true   # show AutoPilot again
VITE_ENABLE_AI=true          # show AI module again
VITE_ENABLE_WATCHLIST=true   # show Watchlist again
VITE_ENABLE_OFO=true         # show OFO again
VITE_ENABLE_BROKER_PAYTM=true
VITE_ENABLE_BROKER_FYERS=true
```
Restart Vite. No code change.

---

## Phases 2-5 — pre-staged, blocked on DB

| # | Phase | Stop condition |
|---|---|---|
| 15 | Phase 2: AngelOne login + all 6 views (data source + order broker = AngelOne) | all 6 `test:specs:*` green |
| 16 | Phase 3: Upstox login + all 6 views (data source + order broker = Upstox) | all 6 `test:specs:*` green |
| 17 | Phase 4 (MIX A): AngelOne login + Upstox as market_data_source | all 6 views render Upstox data |
| 18 | Phase 5 (MIX B): Upstox login + AngelOne as market_data_source | all 6 views render AngelOne data |

The dual-broker mix tests (#17, #18) exercise the core architectural promise of AlgoChanakya — independent `order_broker` and `market_data_source` per `BrokerAdapter` vs `MarketDataBrokerAdapter` adapter hierarchies (see CLAUDE.md "Dual-broker system").

Live WebSocket tick verification will run in tomorrow's 09:15-15:30 IST session. REST/EOD paths will be exercised overnight once DB is reachable.

---

## Resume protocol for next session

1. Confirm DB reachable: `curl http://localhost:8001/api/health` returns 200 after `cd backend && venv/Scripts/python.exe run.py`.
2. Continue at task #15 (Phase 2). Tasks are pre-created in `TaskList`.
3. Use `/fix-loop` on red tests; cap 5 attempts per failure; if stuck, log to this file and move on.
4. After Phase 5, append final verdict + open items to this file and commit with `docs(session): overnight campaign final summary`.
