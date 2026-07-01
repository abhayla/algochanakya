# Session: 2026-07-01-screenshot-verification-campaign

**Date:** 2026-07-01 13:15 IST
**Branch:** feat/visible-views-and-hide-modules

---

## Working Files

| File | Status | Notes |
|------|--------|-------|
| frontend/src/config/features.js | created (earlier commits) | env-driven feature flag SSOT for hidden modules + brokers |
| frontend/src/views/LoginView.vue | modified (a1a8ee6) | broker dropdown filtered via isBrokerEnabled |
| frontend/src/views/SettingsView.vue | modified (f535c09) | Fyers + Paytm credential sections v-if-gated |
| frontend/src/views/OptionChainView.vue | modified (f535c09) | SENSEX added to underlying tabs |
| frontend/src/views/StrategyBuilderView.vue | modified (f535c09) | SENSEX added to underlying tabs |
| backend/app/services/brokers/market_data/smartapi_adapter.py | modified (94355f7, d751be4) | options no longer double-divided by 100 |
| backend/app/services/brokers/market_data/ticker/adapters/smartapi.py | modified (94355f7) | exchange-aware paise divisor (indices only) |
| backend/app/services/brokers/market_data/instrument_query.py | modified (c873a3d) | NFO+BFO exchange filter for SENSEX support |
| backend/app/api/routes/options.py | modified (c873a3d, 29b2c28) | SENSEX added to UNDERLYING_MAP + BFO exchange filter |
| docs/reviews/2026-07-01/{AA,UU,AU,UA}/*.png | created | 24 perfect screenshots (6 screens × 4 broker configs) |
| docs/reviews/2026-07-01/README.md | created | review index |
| docs/reviews/NEXT-SESSION-PROMPT.md | created | resume prompt for next session (headed-mode requirement) |
| backend/tests/backend/brokers/test_smartapi_convert_unified_quote.py | created (6796f9b) | pins LTP fix at code layer |
| backend/tests/backend/brokers/test_iv_solver_substance.py | created (4889024) | proves IV=0 is downstream of LTP bug |
| tests/e2e/specs/optionchain/optionchain.substance.spec.js | created (29b2c28) | substance assertions for option chain |
| tests/e2e/specs/header/hidden-modules.happy.spec.js | created (62e2407) | invariant test for hidden modules |
| .claude/sessions/overnight-2026-07-01.md | modified | full walkthrough of all iterations |
| audit-single.mjs, audit-screens.mjs, audit-login-dropdown.mjs | created (gitignored) | Playwright screenshot harnesses |

## Git State

- **Branch:** feat/visible-views-and-hide-modules (pushed to origin)
- **Last 5 commits:**
  - 51c6b19 docs(session): close-out + next-session resume prompt with headed-mode requirement
  - 846a523 auto: checkpoint 2026-07-01 13:02
  - b9eadef docs(reviews): index for 24 perfect screenshots
  - 70ed2c3 docs(reviews): all 5 UA screenshots perfect (data=AngelOne, order=Upstox dual-mix)
  - 9a0a95a docs(reviews): all 5 AU screenshots perfect (data=Upstox, order=AngelOne dual-mix)
- **Uncommitted changes:** no
- **Stash list:** 1 entry — `WIP: Token mapping changes before multi-broker ticker refactor` on main (unrelated, pre-existing)

## Key Decisions

- Hide mechanism: env-driven feature flags in `frontend/src/config/features.js` (reversible, no code deletion) — not hard route removal or role-based
- Broker matrix: 4 configs (AA/UU/AU/UA), not all 6 brokers — memory `project_org_brokers.md` says only AngelOne + Upstox are org-active
- "Perfect" rubric: (d) strictest — structural + domain-sane + external-truth + visual polish
- Fix-loop over hard-cap: user override saved to memory `feedback_fix_loop_over_cap.md`; iterate until pass or genuine blocker
- Screenshot storage: `docs/reviews/YYYY-MM-DD/{config}/{screen}.png`, committed and reviewable in PR
- LTP scale root cause: SmartAPI returns NSE/BSE indices in paise but NFO/BFO options in RUPEES; adapter now checks exchange_type before dividing
- Runtime pyc caching: uvicorn does NOT reliably invalidate bytecode; must `taskkill //F` all Python processes and purge `__pycache__` before restart

## Task Progress

### Completed

- Feature flag hide system for AutoPilot/AI/Watchlist/OFO + Paytm/Fyers (nav, router, dashboard cards, positions badge, settings dropdowns, settings sections, login dropdown)
- SmartAPI credential refresh (was stale from April 17)
- Strategy Builder `addLeg` bug — no more scary validation error after market close
- 24/24 perfect screenshots at rubric (d) across 4 broker configs, individually visually verified
- LTP 100× scale bug — fixed live and verified in browser (ATM CE ~₹175 realistic; was ~₹1.75)
- IV skew — proved downstream of LTP; solver correct given realistic input
- Substance test suite (option chain E2E, LTP unit, IV solver unit, hidden modules invariant)
- Dual-broker mix (AU + UA) end-to-end wired in Settings UI
- Login broker dropdown sibling-sweep — Paytm/Fyers filtered here too
- Session doc + next-session resume prompt

### In Progress

- (none — all tracked tasks closed this session)

### Blocked

- **SENSEX chain data end-to-end** — WebSocket `oc_snap` exchangeType=2 hardcode + `optionchain.py:765` `NFO:` prefix hardcode. Instrument lookup fixed; chain fetch still fails with "brokers offline" for SENSEX. Documented for next session.
- **Wider NFO grep sweep** — likely more `exchange == "NFO"` hardcodes exist; needs a focused pass.

## Relevant Docs

| Document | Relevance |
|----------|-----------|
| docs/reviews/NEXT-SESSION-PROMPT.md | Copy-paste this into the next session for a clean resume |
| docs/reviews/2026-07-01/README.md | Index of the 24 perfect screenshots + rubric explanation |
| .claude/sessions/overnight-2026-07-01.md | Full walkthrough of all 4 iterations (initial campaign + audit + screenshot-driven + fix-loop) |
| CLAUDE.md + backend/CLAUDE.md + frontend/CLAUDE.md | Project baseline; SmartAPI 3-key setup, dual-broker architecture, port pitfalls |

## Resume Notes

- **Start here:** Paste `docs/reviews/NEXT-SESSION-PROMPT.md` into the new session. It has infra setup commands, the rubric, the broker matrix, the headed-mode requirement, and known open issues.
- **Watch out for:**
  - pyc cache — if a backend fix "doesn't take effect", kill all Python + `rm -rf app/**/__pycache__` before restart
  - SmartAPI creds go stale — always `POST /api/smartapi/authenticate` at session start
  - Option chain cold-load latency is ~14s — screenshot script needs 25s+ wait on first fetch
  - SSH tunnel drops periodically — keepalive flags in the resume prompt help but not perfectly
- **Context needed:**
  - `docs/reviews/2026-07-01/README.md` — the baseline the new session repeats
  - `frontend/src/config/features.js` — the feature flag SSOT
  - Memory files: `feedback_fix_loop_over_cap.md`, `project_org_brokers.md`, `feedback_headed_fullscreen.md`
