# Session: login-workflow-analysis-and-broker-switch-test
**Saved:** 2026-03-20
**Auto-generated:** false

## Summary

Long session covering two major areas:
1. **Broker switch E2E test creation** — wrote `live.broker-switch-flow.spec.js` testing AngelOne → Upstox → AngelOne market data switch while logged in with Zerodha for orders.
2. **Manual broker switch flow execution** — used MCP Playwright browser to live-test the flow, discovered the Upstox platform token expires daily with no auto-refresh, and reconnected Upstox OAuth to get a fresh token.
3. **Deep architecture analysis** — mapped out the full login/credential/market-data workflow, created comprehensive graph with 8 identified gaps. This is the most important output of the session.

The session ended mid-fix on the Upstox token expiry problem. The analysis work (workflow graph + gaps) should drive the next session's implementation plan.

## Working Files

- `backend/app/api/routes/websocket.py` (modified) — Added Upstox JWT expiry check + fallback to user's broker_connections token. **This change is incomplete/wrong** — broker_connections is the order execution table, not market data. Should be reverted or replaced with proper Tier 3 fix.
- `tests/e2e/specs/live/live.broker-switch-flow.spec.js` (created) — New E2E test for broker switch flow (AngelOne → Upstox → back). Not yet committed.
- `docs/architecture/authentication.md` (read) — Three-tier credential architecture SSOT.
- `backend/app/api/routes/auth.py` (read) — Zerodha + AngelOne login flows.
- `backend/app/api/routes/upstox_auth.py` (read) — Upstox OAuth callback, issues new JWT on reconnect.
- `backend/app/api/routes/user_preferences.py` (read) — market_data_source + order_broker preferences.
- `backend/app/api/routes/smartapi.py` (read) — SmartAPI credentials + market-data-source live switch.
- `backend/app/services/brokers/market_data/ticker/pool.py` (read) — Lazy adapter creation, ref-counted subscriptions.
- `backend/app/services/brokers/market_data/ticker/failover.py` (read) — AngelOne → Upstox failover chain.

## Recent Changes (Uncommitted)

### `backend/app/api/routes/websocket.py` — partial Upstox fix (REVIEW BEFORE COMMITTING)
- Early-exit cache skip now excludes Upstox (re-checks expiry each connection)
- Added `_jwt_expired()` inline helper to check JWT exp claim
- If platform `UPSTOX_ACCESS_TOKEN` is expired → clears pool cache → tries user's `broker_connections` upstox token as fallback
- **Problem:** `broker_connections` is the wrong table for market data — it's the order execution table. This is a workaround, not the proper fix.

### `tests/e2e/specs/live/live.broker-switch-flow.spec.js` (new file)
- 11 tests across 3 describe blocks: happy path, WebSocket badge, edge cases
- Tests AngelOne baseline → switch to Upstox → verify all screens → switch back
- Uses `authenticatedPage` fixture with Zerodha as login broker

## Key Decisions & Findings

### Architecture Gap Map (the main output of this session)

The full workflow graph with 8 gaps is in the conversation. Key gaps:

| Gap | Description |
|-----|-------------|
| **A** | "Platform Default" in UI says "zero setup" but actually requires user's own SmartAPI creds in DB. Platform `.env` AngelOne account is NEVER used for WebSocket ticks — only for instrument downloads. |
| **B** | Kite market data path: no JWT expiry check before using `broker_connections` token |
| **C** | Upstox market data reads from `broker_connections` (order execution table) — wrong table |
| **D** | No auto-refresh for Upstox platform token in `.env` (expires daily, all auto-login creds ARE present) |
| **E** | Dhan/Fyers/Paytm: no expiry handling, stale tokens fail silently |
| **F** | No fallback to platform default when upstox/dhan/fyers/paytm creds fail |
| **G** | Two routes update `market_data_source`: only `/api/smartapi/market-data-source` triggers live switch; `/api/user/preferences/` does NOT |
| **H** | Settings "Reconnect Upstox" issues a new login JWT → overwrites user's Zerodha session |
| **I** | AngelOne stored-credentials login (`auth.py:402`) runs `select(SmartAPICredentials)` with NO `user_id` filter — throws `MultipleResultsFound` when 2+ users have saved SmartAPI creds. Only affects the auto-login path (no inline credentials). |
| **J** | Remove Mode B (stored-creds auto-login) from AngelOne login entirely. Login should always use inline credentials (Mode A). Stored `smartapi_credentials` should only be used for market data token refresh, not login. Mode B mixes login and API credential concerns, violating Three-Tier Architecture. Fixes Gap I as a side effect. |
| **K** | Replace Dhan static-token login with proper OAuth flow. Current `dhan_auth.py` asks user to paste `client_id` + `access_token` manually. DhanHQ v2 has a 3-step OAuth flow: generate consent → browser login with 2FA → consume consent → 24h access token. Should follow same redirect pattern as Zerodha/Upstox/Fyers/Paytm. |

### Key Insight: Platform Default vs Platform .env
- `.env` `ANGEL_*` keys = used ONLY for instrument downloads at startup (not for user WebSocket ticks)
- User WebSocket ticks require the user to have saved their OWN SmartAPI credentials in Settings
- The pool IS shared (singleton) so once one user sets up SmartAPI, others benefit — but if ZERO users have configured it, platform data stops working
- `ORG_ACTIVE_BROKERS = ["angelone", "upstox"]` drives FailoverController between these two

### Upstox Token Reality
- Upstox access tokens expire daily (~midnight IST), NOT 1 year as documented
- Platform has all auto-login creds (`UPSTOX_LOGIN_PHONE`, `UPSTOX_LOGIN_PIN`, `UPSTOX_TOTP_SECRET`) but no scheduler to auto-refresh
- Fresh token obtained via MCP Playwright Upstox OAuth — valid 17h at time of save

### Two Market Data Source Update Endpoints (Gap G)
- `PUT /api/smartapi/market-data-source` — validates creds + updates DB + triggers live `switch_user_broker()`
- `PUT /api/user/preferences/` — updates DB only, NO live switch
- Frontend Settings page uses which one? Needs verification.

## Relevant Docs
- [Authentication Architecture](../../docs/architecture/authentication.md) — Three-tier credential architecture SSOT. Gap analysis is directly relevant.
- [Broker Abstraction Architecture](../../docs/architecture/broker-abstraction.md) — Market data adapter design.
- [TICKER-DESIGN-SPEC.md](../../docs/decisions/TICKER-DESIGN-SPEC.md) — 5-component ticker architecture (TickerPool/Router/HealthMonitor/FailoverController/Adapters).
- [E2E Test Rules](../../docs/testing/e2e-test-rules.md) — Used when writing broker-switch-flow spec.

## Where I Left Off

### Completed this session:
- ✅ Created `live.broker-switch-flow.spec.js` (11 tests, not yet committed)
- ✅ Ran manual broker switch flow in MCP browser (AngelOne → Upstox)
- ✅ Discovered Upstox platform token expiry problem and root cause
- ✅ Reconnected Upstox OAuth to get fresh 17h token
- ✅ Created comprehensive login/market-data workflow graph with 8 gaps
- ✅ Applied partial workaround fix to `websocket.py` (incomplete — see notes)

### In Progress / Blocked:
- 🔄 Upstox market data WebSocket still failing (even with reconnect) — root cause: the `websocket.py` fix is correct logically but the fresh token from `broker_connections` may not be working because `broker_connections` is the wrong table conceptually (Gap C)
- 🔄 Manual broker switch test not fully verified (stopped at Upstox screen verification due to WebSocket issues)

### What to do next session:

**Option 1 (Quick fix):** Auto-refresh the platform Upstox token in `.env` at startup using the existing auto-login credentials. This unblocks the immediate test without architecture changes.

**Option 2 (Proper fix):** Implement the full architecture fix:
1. Revert `websocket.py` change
2. Create `upstox_credentials` table (Tier 3, like `smartapi_credentials`)
3. Add Upstox credential management to Settings page
4. Update `websocket.py` to load from `upstox_credentials` table
5. Fix Settings "Reconnect Upstox" to NOT issue new JWT (Gap H)
6. Fix Gap G: make `user_preferences` route also trigger live switch
7. Fix Gap A: add platform `.env` SmartAPI as final fallback for WebSocket ticks

**Before doing either:** Discuss with user which approach they want. The workflow graph analysis was the key output requested — the next step is to agree on which gaps to fix and in what order.

## Resume Prompt

We did a deep analysis of the login and market data credential workflow and created a comprehensive graph with 8 identified gaps. The key findings:

1. "Platform Default" market data does NOT use the platform .env AngelOne account for WebSocket ticks — it uses the individual user's saved SmartAPI credentials. This contradicts the "zero setup required" UI label (Gap A).
2. Upstox tokens expire daily (not 1 year as documented), and there's no auto-refresh despite having all the necessary credentials in .env (Gap D).
3. Settings "Reconnect Upstox" wrongly issues a new login JWT, overwriting the user's Zerodha session (Gap H).
4. Two routes update market_data_source but only one triggers the live WebSocket switch (Gap G).

The websocket.py has an uncommitted partial fix for Upstox expiry that uses broker_connections (wrong table — it's for order execution). This needs to either be reverted or replaced with a proper Tier 3 upstox_credentials table approach.

Pending decision: which gaps to fix first, and whether to do a quick workaround (auto-refresh platform Upstox token at startup) or the proper architecture fix (Tier 3 upstox_credentials table). Please review the workflow graph in the previous session and tell me the priority order.
