# Session: credential-flow-analysis-and-gap-identification
**Saved:** 2026-03-20
**Auto-generated:** false

## Summary

Deep analysis session mapping all 5 credential/login/market-data flows in AlgoChanakya. Identified 17 architecture gaps (A through Q) covering login, credential storage, market data source selection, WebSocket connections, and token expiry. Made key design decisions including unified `broker_api_credentials` table, login token reuse for market data, and separate OAuth callbacks for Settings vs Login. All findings documented in `docs/architecture/credential-flow-analysis.md`.

## Working Files

- `docs/architecture/credential-flow-analysis.md` (created) — **PRIMARY OUTPUT.** Complete analysis document with all 5 flows, 17 gaps, design decisions, and 4-phase implementation plan. This is the authoritative reference for implementation.
- `backend/app/api/routes/websocket.py` (modified, from prior session) — Has uncommitted partial Upstox fix from previous session. Should be reverted — will be properly rewritten in Phase 3 (Gap P).
- `backend/app/api/routes/auth.py` (read) — Analyzed Zerodha + AngelOne login flows. Mode B removal planned (Gap J).
- `backend/app/api/routes/upstox_auth.py` (read) — Analyzed Upstox OAuth login flow.
- `backend/app/api/routes/dhan_auth.py` (read) — Analyzed Dhan static-token login. OAuth rewrite planned (Gap K).
- `backend/app/api/routes/fyers_auth.py` (read) — Analyzed Fyers OAuth login flow.
- `backend/app/api/routes/paytm_auth.py` (read) — Analyzed Paytm OAuth + 3 tokens login flow.
- `backend/app/api/routes/smartapi.py` (read) — Analyzed credential CRUD + market data source routes.
- `backend/app/api/routes/user_preferences.py` (read) — Analyzed preferences route (Gap G — no live switch).
- `backend/app/models/smartapi_credentials.py` (read) — Current AngelOne-only Tier 3 table. Will be migrated to `broker_api_credentials` (Gap M).
- `backend/app/models/broker_connections.py` (read) — Login/order execution tokens. Must NOT be used for market data.
- `backend/app/utils/smartapi_utils.py` (read) — Auto-refresh logic. Pattern to replicate for new table.
- `backend/app/services/brokers/market_data/ticker/pool.py` (read) — TickerPool credential caching. Gap Q identified.
- `.claude/skills/dhan-expert/references/auth-flow.md` (modified) — Added DhanHQ v2 OAuth flow + token compatibility info.
- `.claude/skills/zerodha-expert/references/auth-flow.md` (modified) — Added token compatibility for market data.
- `.claude/skills/upstox-expert/references/auth-flow.md` (modified) — Added token compatibility for market data.
- `.claude/skills/fyers-expert/references/auth-flow.md` (modified) — Added token compatibility for market data.
- `.claude/skills/paytm-expert/references/auth-flow.md` (modified) — Added token compatibility (separate `public_access_token`).
- `tests/e2e/specs/live/live.broker-switch-flow.spec.js` (created, prior session) — Uncommitted E2E test from previous session.

## Recent Changes (Uncommitted)

### New Files
- `docs/architecture/credential-flow-analysis.md` — Complete 5-flow analysis + 17 gaps + implementation plan
- `.claude/sessions/2026-03-20-login-workflow-analysis-and-broker-switch-test.md` — Prior session doc (gap list A-K, outdated — use credential-flow-analysis.md instead)
- `tests/e2e/specs/live/live.broker-switch-flow.spec.js` — Broker switch E2E test (from prior session)
- `false)` and `during` — Stray files in root, should be deleted

### Modified Files
- 5 broker skill auth-flow.md files — Added token compatibility and DhanHQ OAuth info
- `backend/app/api/routes/websocket.py` — Partial Upstox fix from prior session (should be reverted, will be rewritten in Gap P)

## Key Decisions

1. **Unified `broker_api_credentials` table** (Gap L) — Single table for all 6 brokers' market data API credentials, replacing per-broker tables like `smartapi_credentials`. Unique constraint on `(user_id, broker)`.

2. **Login tokens ≠ Market data tokens** — `broker_connections` is for login/orders ONLY. `broker_api_credentials` is for market data ONLY. Never mix them.

3. **Login token reuse optimization** — For brokers where the same `access_token` works for both orders and market data (Zerodha, Upstox, Dhan, Fyers), the login token can be copied to `broker_api_credentials` automatically. Still stored separately for clean separation.

4. **Remove AngelOne Mode B** (Gap J) — Login should always use inline credentials. Stored `smartapi_credentials` are for market data token refresh only, not login.

5. **Dhan needs OAuth rewrite** (Gap K) — DhanHQ v2 has a proper 3-step OAuth consent flow. Current static-token approach is outdated.

6. **Separate Settings OAuth callbacks** (Gap N) — Login callbacks (`/auth/{broker}/callback`) create sessions. Settings callbacks (`/api/settings/{broker}/connect-callback`) only store market data tokens.

7. **Consolidate market data source to one endpoint** (Gap O) — `PUT /api/user/preferences/market-data-source` with mandatory live WebSocket switch.

8. **TickerPool cache must check expiry** (Gap Q) — Currently caches forever. Must validate `token_expiry` before reusing.

## Relevant Docs

- [Credential Flow Analysis](../../docs/architecture/credential-flow-analysis.md) — **THE PRIMARY REFERENCE** for all implementation work. Contains all 5 flows, 17 gaps, design decisions, and implementation plan.
- [Three-Tier Credential Architecture](../../docs/architecture/authentication.md) — Design intent (SSOT for credential tiers).
- [Broker Abstraction Architecture](../../docs/architecture/broker-abstraction.md) — Market data adapter design.
- [TICKER-DESIGN-SPEC.md](../../docs/decisions/TICKER-DESIGN-SPEC.md) — 5-component ticker architecture.

## Where I Left Off

### Completed this session:
- ✅ Mapped all 5 credential flows (Login, Save API Creds, Select Market Data Source, WebSocket Connects, Token Expiry)
- ✅ Identified 17 gaps (A through Q)
- ✅ Made all key design decisions (unified table, token separation, OAuth callbacks, etc.)
- ✅ Created implementation priority plan (4 phases)
- ✅ Updated all 5 broker skills with token compatibility info
- ✅ Discovered DhanHQ v2 OAuth flow (was using outdated static-token approach)
- ✅ Completed full token audit — confirmed no overlaps

### What to do next session:

**Start Phase 1 implementation:**

1. **Gap L** — Create `broker_api_credentials` SQLAlchemy model + Alembic migration
   - Use schema from `credential-flow-analysis.md` → Flow 2 → "Decision: Unified table"
   - Unique constraint on `(user_id, broker)`

2. **Gap M** — Migrate `smartapi_credentials` data into new table
   - Write data migration in Alembic
   - Update all code that imports/queries `SmartAPICredentials` to use new model
   - Keep old table temporarily for backward compatibility

3. **Gap J** — Remove Mode B from AngelOne login
   - Delete the `else` branch in `auth.py:401-421` (stored-creds auto-login)
   - Make `client_id`, `pin`, `totp_code` required fields in `AngelOneLoginRequest`
   - Remove lines 500-509 (stored_credentials token update + user_id overwrite)

**Also:** Clean up stray files (`false)`, `during`) from root directory.

## Resume Prompt

We completed a deep analysis of all 5 credential/login/market-data flows and identified 17 architecture gaps (A-Q). All findings are in `docs/architecture/credential-flow-analysis.md` — read that file first, it's the single reference for everything.

Key decisions made: unified `broker_api_credentials` table replacing per-broker tables, strict separation of login tokens (`broker_connections`) from market data tokens (`broker_api_credentials`), separate OAuth callbacks for Settings vs Login, and a 4-phase implementation plan.

Start with **Phase 1**: Create `broker_api_credentials` table (Gap L), migrate `smartapi_credentials` data (Gap M), and remove Mode B from AngelOne login (Gap J). See the "Implementation Priority" section at the bottom of `credential-flow-analysis.md` for the full plan.
