# Resume prompt — Screenshot Verification Campaign (Headed Playwright)

**Copy everything below the `---` line into a fresh Claude session on this repo.**

The next session will independently produce a fresh 24-screenshot review at today's date, using a visible (headed) browser. Same rubric, same fix-loop discipline, same broker matrix. If any screen fails, iterate until it passes or a genuine blocker hits.

---

I want to repeat the same visual verification campaign that was completed in the previous session on 2026-07-01. Read the prior review artifacts first, then run the fresh campaign in **HEADED mode** so the browser is visible on screen.

## What was already done (prior session, 2026-07-01)

Branch: `feat/visible-views-and-hide-modules` (already pushed to origin).

- **Hide system**: AutoPilot, AI module, Watchlist, OFO views + Paytm and Fyers brokers hidden via env feature flags (`frontend/src/config/features.js`, `.env.local`). Nav / router / dashboard cards / positions badge / settings dropdowns / settings sections / login broker dropdown are all filtered.
- **6 visible screens**: Login, Dashboard, Option Chain, Strategy Builder, Positions, Settings.
- **LTP 100× scale bug fixed**: SmartAPI options were being divided by 100 twice. Root cause + fix in commit `94355f7` — but requires **pyc cache purge + true process kill** to take effect at runtime. If runtime shows 100× wrong LTPs, that's the failure mode.
- **SENSEX partially wired**: expiries endpoint fixed, chain endpoint's instrument lookup opened to BFO, but WebSocket `oc_snap` subscribe still hardcodes exchangeType=2 (NFO only), and `optionchain.py:765` still hardcodes `NFO:` prefix. Chain endpoint returns "brokers offline" for SENSEX until these are fixed too.
- **24/24 perfect screenshots** committed at `docs/reviews/2026-07-01/{AA,UU,AU,UA}/{login,dashboard,optionchain,strategy,positions,settings}.png`. **Read the index at `docs/reviews/2026-07-01/README.md` before starting the fresh run.**
- **Session doc**: `.claude/sessions/overnight-2026-07-01.md` — full walkthrough of all iterations.

## What to do THIS session

1. **Read `docs/reviews/2026-07-01/README.md` + the session doc** — understand what "perfect" looked like last time.
2. **Confirm branch + infrastructure**:
   - Branch is `feat/visible-views-and-hide-modules`.
   - SSH tunnel to VPS Postgres: `ssh -i ~/.ssh/ipodhan_vps -o ServerAliveInterval=30 -o ServerAliveCountMax=4 -N -L 15432:127.0.0.1:5432 Administrator@103.118.16.189`.
   - Backend: `cd backend && DATABASE_URL=$(grep "^DATABASE_URL=" .env | cut -d= -f2- | sed 's|@103\.118\.16\.189:5432|@127.0.0.1:15432|') venv/Scripts/python.exe run.py`.
   - Frontend: `cd frontend && npm run dev`.
   - Refresh SmartAPI: `POST /api/smartapi/authenticate` with JWT (SmartAPI creds go stale hourly, always refresh at session start).
3. **Rubric (d)** — same strictest bar. A screenshot passes ONLY if:
   - **Structural**: all sections render, no `--` placeholders in live-data fields, zero console errors, no hidden-module leaks (AutoPilot/AI/Watchlist/OFO/Paytm/Fyers absent from nav + URL + dropdowns + dashboard cards)
   - **Domain-sane**: NIFTY in [20k-30k], BANKNIFTY in [30k-90k], ATM strike within one strike step of spot, CE+PE at ATM ≥ |spot-ATM|, ATM IVs in [3-80]% and CE/PE within 30pp of each other, OI positive integers
   - **External-truth**: spot-check header prices against a live source (WebSearch NIFTY / SENSEX current)
   - **Visual polish**: no cramped layouts, no misalignment, no obvious CSS bugs
4. **Fix-loop discipline** — if a screenshot fails, iterate (analyze → fix code → restart backend if backend code changed → re-screenshot) until it passes OR a genuine blocker hits (credentials, destructive op, product fork). NEVER cap fix attempts at an arbitrary N — this is a user-locked preference at `~/.claude/projects/D--Abhay-VibeCoding-algochanakya/memory/feedback_fix_loop_over_cap.md`.
5. **HEADED mode** — the browser MUST be visible. Modify or write a Playwright script with `chromium.launch({ headless: false, args: ['--start-maximized'] })` and `viewport: null` so it uses the OS window. The prior session used headless — that's what THIS session changes.
6. **Broker matrix — 4 configs**:
   - `AA` — Market Data Source = AngelOne SmartAPI, Order Broker = AngelOne (`smartapi/angel`)
   - `UU` — data + order = Upstox (`upstox/upstox`)
   - `AU` — data = Upstox, order = AngelOne (`upstox/angel`)
   - `UA` — data = AngelOne SmartAPI, order = Upstox (`smartapi/upstox`)
   Switch prefs via `PUT /api/user/preferences/` before each config's screenshots.
7. **Storage** — put perfect screenshots at `docs/reviews/{TODAY'S_DATE_YYYY-MM-DD}/{config}/{screen}.png`. Don't overwrite the 2026-07-01 folder — that's a historical artifact. This session gets its own dated folder. `.gitignore` already allows `docs/reviews/**/*.png`.
8. **Every action** — take a screenshot at each meaningful state (initial load, after underlying tab switch, after strategy leg added, etc.) if the state reveals data. Retain only the "perfect" one per screen per config; delete failed attempts.
9. **Commit + push each config's 5-6 screenshots** as they land. One commit per broker config is fine.
10. **At end** — write a README index at `docs/reviews/{TODAY}/README.md` matching the format of `docs/reviews/2026-07-01/README.md`, then push.

## Known open issues (from prior session — NOT deferred; iterate if they surface)

- **SENSEX chain data path** — the tab and expiries work; the chain data fetch fails with "brokers offline". Task #28 documented the remaining sites: `smartapi_adapter.py:389` WebSocket `oc_snap` subscribes with `exchangeType=2` (NFO only) and `optionchain.py:765` hardcodes `f"NFO:{canonical_symbol}"` prefix. Fix both if you touch SENSEX.
- **Option chain cold-load latency** — first fetch is ~14 seconds. If a screenshot catches "Loading option chain..." spinner, wait longer (25s+) or trigger the fetch once before the audit and re-screenshot.
- **Pyc cache issue** — if a code fix "doesn't take effect" after backend restart, do `find backend/app -name "__pycache__" -exec rm -rf {} +` and a hard `taskkill //F` on all Python processes before restarting. Uvicorn does not reliably invalidate bytecode.

## Non-negotiable rules

- Push before clearing session. Don't leave uncommitted work.
- Never delete `docs/reviews/2026-07-01/` — historical baseline.
- Never touch `C:\Apps\algochanakya` (production).
- Never touch `D:\Abhay\VibeCoding\5Wealths\` from this repo.
- Use fix-loop, not fix-attempt caps.
- Read every PNG you save; a "structural pass" from the audit script is NOT enough. Full rubric (d) requires opening the file.
- Every substantive turn must render the full prompt-auto-enhance pipeline block (Enhanced line + step log + diagnosis + score table with Reviewer-after column + Overall row + Original→Improved + Role).

Begin now: read the prior README, get infra up, take the first screenshot (Login for AA config), apply rubric, iterate if it fails.
