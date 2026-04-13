# Credential & Login Flow Analysis

> **Purpose:** Maps the actual current data flows for login, credential storage, and market data token usage. Identifies gaps between current implementation and intended architecture.
> **Status:** Complete — all 17 gaps (A–Q) resolved on 2026-03-20.
> **Related:** [Three-Tier Credential Architecture](authentication.md) | [Broker Abstraction](broker-abstraction.md)

## Database Tables Involved

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User identity | `id`, `email`, `first_name`, `last_login` |
| `broker_connections` | Login session tokens (order execution) | `user_id`, `broker`, `broker_user_id`, `access_token`, `is_active`, `broker_metadata` |
| `smartapi_credentials` | AngelOne market data API creds (Tier 3) | `user_id`, `client_id`, `encrypted_pin`, `encrypted_totp_secret`, `jwt_token`, `feed_token` |
| `user_preferences` | Which broker for market data | `user_id`, `market_data_source` (default: `"platform"`) |

## Flow 1: Login (All 6 Brokers)

### 1A: Zerodha Login

**Route:** `GET /auth/zerodha/callback` (`auth.py`) — OAuth redirect
**Auth method:** OAuth 2.0 (user logs in on Kite's site)

**Steps:**
1. Kite redirects back with `request_token`
2. Exchange for `access_token` using `.env` `KITE_API_KEY` + `KITE_API_SECRET`
3. `kite.profile()` → `resolve_or_create_user(broker="zerodha")`
4. Upsert `broker_connections` (filter: `user_id` + `broker="zerodha"` + `broker_user_id`)
5. Create JWT (`user_id` + `broker_connection_id`) → Redis → redirect frontend

**Stored:**

| Table | Field | Value |
|-------|-------|-------|
| `users` | `last_login` | now |
| `broker_connections` | `broker` | `"zerodha"` |
| `broker_connections` | `access_token` | Kite access token (expires ~6 AM IST) |
| `broker_connections` | `is_active` | `True` |
| Redis | `session:{user_id}` | JWT (expires per `JWT_EXPIRY_HOURS`) |

**Issues:** None — cleanest flow.

---

### 1B: AngelOne Login

**Route:** `POST /auth/angelone/login` (`auth.py`) — Inline credentials only (Mode A)
**Auth method:** Direct credential auth (`client_id` + `pin` + `totp_code`)

**Steps:**
1. User enters `client_id` + `pin` + `totp_code` on login page
2. Authenticates with SmartAPI — credentials used once, NOT stored
3. Get profile → `resolve_or_create_user(broker="angelone")`
4. Upsert `broker_connections` (filter: `user_id` + `broker="angelone"` + `broker_user_id`)
5. Create JWT → Redis → return token

**Stored:**

| Table | Field | Value |
|-------|-------|-------|
| `broker_connections` | `broker` | `"angelone"` |
| `broker_connections` | `access_token` | SmartAPI `jwt_token` (expires 5 AM IST) |
| Redis | `session:{user_id}` | JWT |

**Current bugs:**
- **Mode B (stored-creds auto-login) exists but should be removed (Gap J).** It uses `smartapi_credentials` for login, which mixes login and API credential concerns.
- **Gap I:** Mode B's query `select(SmartAPICredentials)` has no `user_id` filter — crashes with `MultipleResultsFound` when 2+ users have saved SmartAPI creds. Fixed automatically by removing Mode B (Gap J).
- **Mode B side effect:** Line 509 overwrites `smartapi_credentials.user_id` to whoever logged in.

---

### 1C: Upstox Login

**Route:** `GET /auth/upstox/callback` (`upstox_auth.py`) — OAuth redirect
**Auth method:** OAuth 2.0

**Steps:**
1. OAuth code exchange → `access_token` via HTTP POST to Upstox
2. Get profile → `resolve_or_create_user(broker="upstox")`
3. Upsert `broker_connections` (filter: `user_id` + `broker="upstox"` + `broker_user_id`)
4. Create JWT → Redis → redirect frontend

**Stored:**

| Table | Field | Value |
|-------|-------|-------|
| `broker_connections` | `broker` | `"upstox"` |
| `broker_connections` | `access_token` | Upstox access token (expires ~midnight IST daily) |
| Redis | `session:{user_id}` | JWT |

**Issues:** None in login itself. Token expiry issues are in the market data flow (Gap D).

---

### 1D: Dhan Login (NEEDS REWRITE — Gap K)

**Route:** `POST /auth/dhan/login` (`dhan_auth.py`) — Static token auth
**Auth method:** User manually pastes `client_id` + `access_token` from Dhan developer console

**Current (wrong) steps:**
1. User goes to Dhan developer console, copies `client_id` + `access_token`
2. Pastes into login form
3. Validates by calling `GET https://api.dhan.co/v2/orders`
4. `resolve_or_create_user(broker="dhan")`
5. Upsert `broker_connections` + stores `client_id` in `broker_metadata`
6. Create JWT → Redis → return JSON (not redirect — inconsistent with other brokers)

**What DhanHQ v2 actually supports (should use instead):**

3-step OAuth flow:
1. `POST https://auth.dhan.co/app/generate-consent?client_id={dhanClientId}` (headers: `app_id`, `app_secret`) → returns `consentAppId`
2. Browser redirect to `https://auth.dhan.co/login/consentApp-login?consentAppId=...` → user logs in with 2FA → redirects back with `tokenId`
3. `POST https://auth.dhan.co/app/consumeApp-consent?tokenId=...` (headers: `app_id`, `app_secret`) → returns `accessToken` (24h validity)

Additional Dhan endpoints:
- Token renewal: `GET https://api.dhan.co/v2/RenewToken` — refreshes active token for another 24h
- Direct TOTP: `POST https://auth.dhan.co/app/generateAccessToken?dhanClientId=...&pin=...&totp=...` — 24h token

**Gap K:** Replace static-token login with proper OAuth flow. Response should be HTTP redirect (not JSON) for consistency.

---

### 1E: Fyers Login

**Route:** `GET /auth/fyers/callback` (`fyers_auth.py`) — OAuth with appIdHash
**Auth method:** OAuth 2.0 with SHA256 appIdHash

**Steps:**
1. OAuth code exchange with `SHA256(app_id:secret_key)` as `appIdHash`
2. Get profile → `resolve_or_create_user(broker="fyers")`
3. Upsert `broker_connections` (filter: `user_id` + `broker="fyers"` + `broker_user_id`)
4. Stores `client_id` (app_id) in `broker_metadata`
5. Create JWT → Redis → redirect frontend

**Stored:**

| Table | Field | Value |
|-------|-------|-------|
| `broker_connections` | `broker` | `"fyers"` |
| `broker_connections` | `access_token` | Fyers access token (expires midnight IST) |
| `broker_connections` | `broker_metadata.client_id` | Fyers app_id |
| Redis | `session:{user_id}` | JWT |

**Issues:** None in login itself.

---

### 1F: Paytm Login

**Route:** `GET /auth/paytm/callback` (`paytm_auth.py`) — OAuth with 3 tokens
**Auth method:** OAuth returning 3 separate tokens

**Steps:**
1. Exchange `requestToken` for 3 tokens: `access_token`, `public_access_token`, `read_access_token`
2. Get profile → `resolve_or_create_user(broker="paytm")`
3. Upsert `broker_connections` (filter: `user_id` + `broker="paytm"` + `broker_user_id`)
4. Stores extra tokens in `broker_metadata`
5. Create JWT → Redis → redirect frontend

**Additional endpoint:** `POST /auth/paytm/public-token` — manually save `public_access_token` for WebSocket

**Stored:**

| Table | Field | Value |
|-------|-------|-------|
| `broker_connections` | `broker` | `"paytm"` |
| `broker_connections` | `access_token` | Main Paytm access token |
| `broker_connections` | `broker_metadata.read_token` | `public_access_token` (confusing name) |
| `broker_connections` | `broker_metadata.edge_token` | `read_access_token` (confusing name) |
| Redis | `session:{user_id}` | JWT |

**Issues:** `broker_metadata` field names are misleading — `read_token` stores `public_access_token`, `edge_token` stores `read_access_token`.

---

### Login Flow Summary

| Broker | Auth Method | Route Type | Response Type | Extra Tables |
|--------|------------|------------|---------------|-------------|
| Zerodha | OAuth redirect | GET callback | HTTP redirect | — |
| AngelOne | Inline creds | POST | JSON | `smartapi_credentials` (Mode B — to be removed) |
| Upstox | OAuth redirect | GET callback | HTTP redirect | — |
| Dhan | Static token (WRONG — Gap K) | POST | JSON (inconsistent) | — |
| Fyers | OAuth + appIdHash | GET callback | HTTP redirect | — |
| Paytm | OAuth + 3 tokens | GET callback | HTTP redirect | — |

**Common pattern:** All flows write to `broker_connections` and Redis. All use `resolve_or_create_user()`. All create JWT with `user_id` + `broker_connection_id`.

**Inconsistencies:** Dhan returns JSON instead of redirect. AngelOne Mode B touches `smartapi_credentials` (to be removed).

---

## Gap List

| Gap | Description | Status |
|-----|-------------|--------|
| **A** | "Platform Default" in UI says "zero setup" — fixed label to accurately describe shared AngelOne + Upstox connection | **Resolved** (2026-03-20) |
| **B** | Kite market data path: no JWT expiry check before using `broker_connections` token | **Resolved** by Gap P — Kite now reads from `broker_api_credentials` with expiry check |
| **C** | Upstox market data reads from `broker_connections` (order execution table) — wrong table | **Resolved** by Gap P — Upstox now reads from `broker_api_credentials` first |
| **D** | No auto-refresh for Upstox platform token in `.env` (expires daily) | **Resolved** (2026-03-20) — expired tokens skipped, falls back to .env |
| **E** | Dhan/Fyers/Paytm: no expiry handling, stale tokens fail silently | **Resolved** (2026-03-20) — `_creds_not_expired()` check on all brokers |
| **F** | No fallback to platform default when upstox/dhan/fyers/paytm creds fail | **Resolved** (2026-03-20) — `_try_fallback_brokers()` iterates `ORG_ACTIVE_BROKERS` |
| **G** | Two routes update `market_data_source`: only one triggers live switch | **Resolved** by Gap O — both endpoints now trigger live switch |
| **H** | Settings "Reconnect" issues a new login JWT → overwrites user's session | **Resolved** (2026-03-20) — Settings uses `/api/settings/{broker}/connect` |
| **I** | AngelOne stored-credentials login has no `user_id` filter — crashes with multiple users | **Resolved** by Gap J — Mode B removed entirely |
| **J** | Remove Mode B (stored-creds auto-login) from AngelOne login | **Resolved** (2026-03-20) — all 3 fields required, no DB query |
| **K** | Replace Dhan static-token login with proper OAuth flow | **Resolved** (2026-03-20) — DhanHQ v2 3-step consent flow added |
| **L** | Unified `broker_api_credentials` table for all 6 brokers | **Resolved** (2026-03-20) — table created with data migration |
| **M** | Migrate `smartapi_credentials` into unified table, update all code | **Resolved** (2026-03-20) — 15 files updated |
| **N** | Separate OAuth callbacks for Settings (don't create sessions) | **Resolved** (2026-03-20) — `/api/settings/{broker}/connect-callback` |
| **O** | Consolidate market data source to single endpoint with live switch | **Resolved** (2026-03-20) — preferences endpoint now triggers switch |
| **P** | WebSocket loads from `broker_api_credentials` for all brokers | **Resolved** (2026-03-20) — user creds → .env → fallback chain |
| **Q** | TickerPool credential cache expiry checks | **Resolved** (2026-03-20) — `credentials_valid()` + `clear_expired_credentials()` |

---

## Flow 2: Save API Credentials (Settings Page)

### Current State: Only AngelOne Has Tier 3 UI

**AngelOne (SmartAPI):**
- Routes: `POST/GET/DELETE /api/smartapi/credentials`, `POST /api/smartapi/test-connection`, `POST /api/smartapi/authenticate`
- Table: `smartapi_credentials` (dedicated, `unique` constraint on `user_id`)
- Stores: `client_id` (plain), `encrypted_pin`, `encrypted_totp_secret`, `jwt_token`, `feed_token`, `token_expiry`
- Auto-refresh: `get_valid_smartapi_credentials()` checks 5 AM IST flush, re-authenticates using stored PIN + TOTP

**All Other Brokers (Upstox, Zerodha, Dhan, Fyers, Paytm):**
- No Tier 3 credential table or Settings page exists
- Market data uses `.env` platform tokens or `broker_connections` (login tokens — wrong table)

### Decision: Unified `broker_api_credentials` Table (Gap L)

A new unified table `broker_api_credentials` will store market data API credentials for ALL 6 brokers. This replaces the per-broker table approach (`smartapi_credentials` will be migrated into this table).

**Table design:**

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID PK | Row identifier |
| `user_id` | UUID FK → users | Owner |
| `broker` | VARCHAR(50) | Broker name: "angelone", "zerodha", "upstox", "dhan", "fyers", "paytm" |
| `api_key` | TEXT (encrypted) | Permanent API key/app ID |
| `api_secret` | TEXT (encrypted) | Permanent API secret |
| `encrypted_pin` | TEXT (nullable) | Trading PIN — only AngelOne/Dhan/Upstox need this |
| `encrypted_totp_secret` | TEXT (nullable) | TOTP secret for auto-login — only AngelOne/Dhan/Upstox |
| `client_id` | VARCHAR(100) | Broker-specific client/user ID |
| `access_token` | TEXT (nullable) | Session token after auth |
| `feed_token` | TEXT (nullable) | WebSocket feed token (AngelOne) |
| `refresh_token` | TEXT (nullable) | Refresh token if broker supports it |
| `token_expiry` | TIMESTAMPTZ (nullable) | When access_token expires |
| `is_active` | BOOLEAN | Whether credentials are configured and working |
| `last_auth_at` | TIMESTAMPTZ (nullable) | Last successful authentication |
| `last_error` | TEXT (nullable) | Last error message |
| `broker_metadata` | JSONB (nullable) | Broker-specific extras (e.g. Paytm's 3 tokens) |
| `created_at` | TIMESTAMPTZ | Row creation |
| `updated_at` | TIMESTAMPTZ | Last update |
| **Unique constraint** | `(user_id, broker)` | One credential set per user per broker |

**Why unified over per-broker:** Adding a new broker means zero schema changes — just insert a row with `broker="newbroker"`. Matches how `broker_connections` already works.

**Migration plan:** Migrate existing `smartapi_credentials` data into `broker_api_credentials` with `broker="angelone"`. Keep `smartapi_credentials` table temporarily for backward compatibility, then drop after all code references are updated.

### CRITICAL: Separation of Login Tokens vs Market Data API Tokens

| Concern | Table | Purpose |
|---------|-------|---------|
| **Login session** (order execution) | `broker_connections` | Stores OAuth/login access tokens. Used for placing orders, fetching positions. Created during login flow. |
| **Market data API** (live prices) | `broker_api_credentials` (NEW) | Stores user's own API credentials + session tokens for market data. Configured in Settings. Independent from login. |

**Example scenario:** User logs in with Zerodha OAuth → `broker_connections` gets Zerodha `access_token` for orders. User then goes to Settings, enters their Zerodha API key + secret, clicks "Connect" → OAuth redirect → gets a DIFFERENT `access_token` stored in `broker_api_credentials` for market data. These two tokens are completely independent and may have different expiry times.

### Settings UI Requirements Per Broker

Each broker card in Settings needs:
1. **Input fields** for permanent credentials (API key, secret, etc.)
2. **"Connect" button** — triggers OAuth redirect or direct auth
3. **Red/Green indicator** — shows if connection is active (verified via profile API call)
4. **"Test Connection" button** — calls verification endpoint on demand
5. **Token status** — shows expiry time, last connected timestamp

**Two auth patterns:**

| Pattern | Brokers | How "Connect" Works |
|---------|---------|-------------------|
| **OAuth redirect** | Zerodha, Upstox, Dhan, Fyers, Paytm | Click → redirect to broker's login page → redirect back → token saved |
| **Direct auth** | AngelOne | Click → backend authenticates using stored PIN + auto-TOTP → token saved |

**Per-broker credential fields:**

| Broker | Fields User Provides | Stored Where |
|--------|---------------------|-------------|
| AngelOne | `client_id`, `pin`, `totp_secret` | `broker_api_credentials` (encrypted) |
| Upstox | `api_key`, `api_secret` | `broker_api_credentials` (encrypted) |
| Zerodha | `api_key`, `api_secret` | `broker_api_credentials` (encrypted) |
| Dhan | `api_key`, `api_secret` | `broker_api_credentials` (encrypted) |
| Fyers | `app_id`, `app_secret` | `broker_api_credentials` (encrypted) |
| Paytm | `api_key`, `api_secret` | `broker_api_credentials` (encrypted) |

**Token verification endpoints (for red/green indicator):**

| Broker | Verification Call | Expected Success |
|--------|------------------|-----------------|
| AngelOne | `getProfile` via SmartAPI | 200 with profile data |
| Upstox | `GET /v2/profile` | 200 with user data |
| Zerodha | `GET /user/profile` via KiteConnect | Profile dict returned |
| Dhan | `GET /v2/profile` | 200 with profile |
| Fyers | `GET /v3/profile` | Status "ok" |
| Paytm | Any authenticated endpoint | 200 response |

**Token expiry and auto-refresh:**

| Broker | Token Lifetime | Auto-Refresh Possible? | What Happens on Expiry |
|--------|---------------|----------------------|----------------------|
| AngelOne | ~24h (5 AM IST flush) | **Yes** — refresh token (15 days) + re-auth with stored PIN+TOTP | Auto-refreshes silently |
| Upstox | ~6:30 AM next day | **No** | Red indicator, user clicks "Connect" again |
| Zerodha | ~6 AM next day | **No** | Red indicator, user clicks "Connect" again |
| Dhan | 24h | **Partial** — `RenewToken` while still active | Try auto-renew, else red indicator |
| Fyers | Midnight IST | **No** | Red indicator, user clicks "Connect" again |
| Paytm | ~24h | **No** | Red indicator, user clicks "Connect" again |

---

### Decision: Login Token Reuse for Market Data (Optimization)

For most brokers, the OAuth `access_token` obtained during login is the SAME token used for market data (REST + WebSocket). This means if a user is logged in with the same broker they want market data from, we can skip the separate Settings OAuth step.

**Token compatibility per broker:**

| Broker | Same token for orders + market data? | Details |
|--------|--------------------------------------|---------|
| **Zerodha** | **Yes** | Same `access_token` for REST API AND WebSocket (`wss://ws.kite.trade?api_key=X&access_token=Y`) |
| **Upstox** | **Yes** | Same `access_token` for REST orders AND WebSocket market feed (V3) |
| **Dhan** | **Yes** | Same `access_token` in REST headers AND WebSocket query param |
| **Fyers** | **Yes** | Same `access_token` for REST AND data/order WebSockets |
| **Paytm** | **Partially** | `access_token` for orders, separate `public_access_token` for WebSocket — but both come from same OAuth flow |
| **AngelOne** | **No** | `jwt_token` for REST, separate `feed_token` for WebSocket — both returned from same login call |

**Chosen approach:** If the user is logged in with the same broker they want market data from, we copy the login token from `broker_connections` into `broker_api_credentials` automatically — no re-auth needed. The user sees a "Use your login connection for market data" option in Settings.

**Why still store separately in `broker_api_credentials`:**
- Clear token source: market data table is the single source for market data tokens
- Independence: if login token refreshes/expires, market data entry can track separately
- Persistence: if user later logs in with a different broker, market data connection persists
- No confusion: `broker_connections` = login/orders, `broker_api_credentials` = market data (always)

**When separate Settings OAuth IS needed:**
- User wants market data from a broker they are NOT logged in with (e.g. logged in with Zerodha, wants Upstox market data)
- User wants market data from a broker that uses different tokens for market data (AngelOne needs `feed_token`, Paytm needs `public_access_token`)
- User's login token expired but they want to keep market data active via Settings re-auth

**Settings UI flow (updated):**

1. User opens Settings → Broker API section
2. For each broker, system checks:
   - Does user have active login with this broker? (`broker_connections`)
   - Does user have saved API credentials? (`broker_api_credentials`)
3. If logged in with same broker AND token is compatible:
   - Show "Connected via login" with green indicator
   - Offer "Use for market data" button → copies token to `broker_api_credentials`
4. If NOT logged in or token incompatible:
   - Show credential input fields (API key, secret, etc.)
   - "Connect" button triggers OAuth redirect or direct auth
5. Red/green indicator always reflects `broker_api_credentials` token validity

---

## Flow 3: Select Market Data Source (Settings Page)

### Current State: Two Endpoints, Only One Triggers Live Switch (Gap G)

| Route | File | What It Does | Live Switch? |
|-------|------|-------------|--------------|
| `PUT /api/smartapi/market-data-source` | `smartapi.py:336` | Validates creds exist → updates `user_preferences.market_data_source` | **YES** — calls `ticker_router.switch_user_broker()` |
| `PUT /api/user/preferences/` | `user_preferences.py:55` | Updates `user_preferences.market_data_source` (among other prefs) | **NO** — DB only |

### What `user_preferences.market_data_source` Stores

One of: `"platform"`, `"smartapi"`, `"kite"`, `"upstox"`, `"dhan"`, `"fyers"`, `"paytm"`

### What Happens on WebSocket Connect (`websocket.py:53-63`)

1. Reads `user_preferences.market_data_source`
2. If `"platform"` → resolves to `"smartapi"` (hardcoded default)
3. Uses this to decide which broker's credentials to load for market data

### Problems

1. **Gap G:** Two routes update the same field, but only one triggers the live WebSocket switch
2. `"platform"` → `"smartapi"` mapping is hardcoded — should use the FailoverController's active broker chain
3. The route is under `/api/smartapi/` but handles all broker selections — misplaced
4. Only validates SmartAPI and Kite credentials — doesn't check Upstox/Dhan/Fyers/Paytm

### Decision: Consolidate to One Endpoint (Gap O)

**New endpoint:** `PUT /api/user/preferences/market-data-source`

**Behavior:**
1. Validate that the selected broker has active credentials in `broker_api_credentials` for the current user
2. Update `user_preferences.market_data_source`
3. **Always** trigger `ticker_router.switch_user_broker()` for live WebSocket switch
4. Return the updated source with credential status for all brokers

**Remove:** `PUT /api/smartapi/market-data-source` (superseded)

**`"platform"` resolution:** Instead of hardcoding `"smartapi"`, resolve `"platform"` using FailoverController's active broker chain (`ORG_ACTIVE_BROKERS`). Currently AngelOne → Upstox.

### Token Source for WebSocket (Updated)

After the `broker_api_credentials` table is implemented (Gap L), `websocket.py`'s `_ensure_broker_credentials()` will be updated to:

1. Read `user_preferences.market_data_source` for the user
2. Load credentials from `broker_api_credentials` WHERE `user_id` AND `broker` = selected source
3. If no credentials found → fall back to platform `.env` credentials
4. If platform `.env` also unavailable → try next broker in FailoverController chain
5. Set credentials on TickerPool

This replaces the current approach where WebSocket loads from a mix of `smartapi_credentials`, `broker_connections`, and `.env` depending on the broker.

---

## Flow 4: WebSocket Connects (Live Market Data)

**Route:** `WS /ws/ticks?token=<jwt>` (`websocket.py:235`)

### Current Steps

1. **Authenticate:** Decode JWT → load `users` row from DB
2. **Get source:** Load `user_preferences.market_data_source` → default `"platform"` → resolves to `"smartapi"` (hardcoded)
3. **Load credentials** (`_ensure_broker_credentials`):

| Source | Where Creds Come From Today | Problem |
|--------|---------------------------|---------|
| `smartapi` | `smartapi_credentials` via `get_valid_smartapi_credentials()` | Correct table, but will move to `broker_api_credentials` (Gap P) |
| `kite` | `broker_connections` WHERE `broker="zerodha"` | **Wrong table** — uses login token for market data (Gap B) |
| `upstox` | `.env` first, falls back to `broker_connections` | **Wrong table** for fallback, `.env` expires daily (Gap C, D) |
| `dhan` | `.env` only | No user-level option |
| `fyers` | `.env` only | No user-level option |
| `paytm` | `.env` only | No user-level option |

4. **Caching:** Once credentials are set in `TickerPool._credentials[broker_type]`, they're reused forever — **except** Upstox which re-checks JWT expiry each connection (Gap Q)
5. **Fallback:** If preferred broker fails → tries SmartAPI↔Kite swap only. No fallback for others (Gap F).
6. **Token map:** For SmartAPI, loads canonical↔broker token map from `broker_instrument_tokens` table. Without this, SmartAPI subscribes to nothing.

### What It Should Look Like (After Gaps L, O, P, Q)

1. **Authenticate:** Same — decode JWT, load user
2. **Get source:** Load `user_preferences.market_data_source` → resolve `"platform"` via FailoverController chain (not hardcoded)
3. **Load credentials from `broker_api_credentials`:**
   ```sql
   SELECT * FROM broker_api_credentials
   WHERE user_id = :uid AND broker = :selected_source AND is_active = true
   ```
4. **Fallback chain:**
   - User's `broker_api_credentials` for selected source
   - Platform `.env` credentials for selected source
   - FailoverController chain (try next `ORG_ACTIVE_BROKER`)
   - Send error if all fail
5. **Token validation:** Before using cached credentials, always check expiry:
   - SmartAPI: check `last_auth_at` vs 5 AM IST (auto-refresh if stored creds exist)
   - Dhan: try `RenewToken` if near expiry
   - All others: check `token_expiry` field — if expired, clear cache, try fallback
6. **Token map:** Same as today for SmartAPI. Other brokers handle token mapping in their own adapters.

---

## Flow 5: Token Expiry & Refresh

### Current State Per Broker

| Broker | Token Lifetime | Auto-Refresh Today? | What Happens on Expiry |
|--------|---------------|---------------------|----------------------|
| **SmartAPI (AngelOne)** | ~24h (5 AM IST flush) | **Yes** — `get_valid_smartapi_credentials()` re-authenticates using stored PIN+TOTP | Works automatically via refresh_token (15 days) or full re-auth |
| **Kite (Zerodha)** | ~6 AM IST daily | **No** | Token in `broker_connections` goes stale. WebSocket silently fails. User must re-login. |
| **Upstox** | ~midnight IST daily | **Partial** — `websocket.py` checks JWT expiry on `.env` token only | If `.env` expired AND `broker_connections` expired → no data, no error to user |
| **Dhan** | 24h | **No** | `.env` token never expires (static). User tokens would expire if they existed. |
| **Fyers** | Midnight IST | **No** | `.env` token goes stale silently |
| **Paytm** | ~24h | **No** | `.env` token goes stale silently |

### What It Should Look Like

After `broker_api_credentials` is implemented, the refresh strategy per broker:

| Broker | Refresh Strategy | Implementation |
|--------|-----------------|----------------|
| **AngelOne** | Auto-refresh using stored PIN + TOTP secret | `get_valid_smartapi_credentials()` pattern — already works. Migrate to read from `broker_api_credentials`. |
| **Zerodha** | Cannot auto-refresh (OAuth only). Show red indicator in Settings, user clicks "Reconnect". | Check `token_expiry` in `broker_api_credentials`. If expired → update `is_active = false` → frontend shows red indicator. |
| **Upstox** | Cannot auto-refresh (OAuth only). Same as Zerodha. | Same pattern — check expiry, show red indicator. |
| **Dhan** | Partial auto-refresh via `GET /v2/RenewToken` while token is still active. | Add renewal check before expiry. If renewal fails → red indicator. |
| **Fyers** | Cannot auto-refresh (OAuth only). Same as Zerodha. | Same pattern — check expiry, show red indicator. |
| **Paytm** | Cannot auto-refresh (OAuth only). Same as Zerodha. | Same pattern — check expiry, show red indicator. |

### Runtime Auto-Refresh (Ticker System)

When a ticker adapter encounters an expired credential:

1. Adapter calls `_report_auth_error(error_code, error_msg)`
2. Pool forwards to `HealthMonitor.record_auth_failure()`
3. `token_policy.classify_auth_error()` determines category
4. If RETRYABLE and broker is auto-refreshable:
   - `refresh_broker_token(broker)` attempts credential refresh
   - SmartAPI: pyotp TOTP + refresh_token
   - Upstox: upstox-totp HTTP login (no browser)
5. If refresh succeeds: adapter reconnects with new credentials
6. If refresh fails: failover to secondary broker

Key file: `backend/app/services/brokers/platform_token_refresh.py`

### TickerPool Credential Cache Expiry (Gap Q)

**Current problem:** `TickerPool._credentials[broker_type]` is set once and never checked again (except Upstox partial check). If a token expires mid-session:
- WebSocket adapter silently stops receiving data
- No error message sent to frontend
- User sees stale prices with no indication

**Fix:** Before using cached credentials, TickerPool should:
1. Check `token_expiry` timestamp stored alongside credentials
2. If expired: clear cache → reload from `broker_api_credentials` → try auto-refresh (AngelOne/Dhan) → if still expired, trigger failover
3. Send WebSocket message `{"type": "token_expired", "broker": "..."}` to frontend so it can show a notification

### Frontend Indicator Behavior

| State | Indicator | User Action |
|-------|-----------|-------------|
| Token valid, data flowing | Green dot | None |
| Token expiring within 1 hour | Yellow dot + "Expiring soon" | Optional: click "Reconnect" |
| Token expired, no data | Red dot + "Expired — Reconnect" | Click "Reconnect" → OAuth redirect or auto-refresh |
| No credentials configured | Grey dot + "Not configured" | Click "Configure" → Settings page |

---

## Implementation Priority

### Dependency Graph

```
Gap L (unified broker_api_credentials table)
  ├── Gap M (migrate smartapi_credentials into it)
  ├── Gap N (separate OAuth callbacks for Settings)
  ├── Gap O (consolidate market data source endpoint)
  ├── Gap P (websocket.py loads from new table)
  │     └── Gap Q (TickerPool cache expiry)
  └── Gap L also unblocks fixes for B, C, D, E, F

Gap J (remove Mode B from AngelOne login)
  └── Fixes Gap I automatically

Gap K (Dhan OAuth login) — independent
Gap H (Reconnect Upstox JWT overwrite) — independent
Gap G — fixed by Gap O
Gap A — documentation/UI fix, independent
```

### Phase 1: Foundation (Everything Depends On This)

| Order | Gap | What | Effort |
|-------|-----|------|--------|
| 1 | **L** | Create `broker_api_credentials` table + model + migration | New SQLAlchemy model, Alembic migration |
| 2 | **M** | Migrate existing `smartapi_credentials` data into new table | Data migration script, update all code references |
| 3 | **J** | Remove Mode B from AngelOne login (delete stored-creds auto-login) | Delete ~40 lines from `auth.py`, fixes Gap I |

### Phase 2: Settings UI (User-Facing)

| Order | Gap | What | Effort |
|-------|-----|------|--------|
| 4 | **N** | Create separate OAuth callback endpoints for Settings (`/api/settings/{broker}/connect-callback`) | 5 new callback routes (one per OAuth broker) |
| 5 | **L** (cont.) | Build Settings UI — broker cards with credential inputs, Connect button, red/green indicator, Test Connection | Vue component, Pinia store, API routes for CRUD + test-connection |

### Phase 3: WebSocket Pipeline (Market Data Works With New Table)

| Order | Gap | What | Effort |
|-------|-----|------|--------|
| 6 | **P** | Update `websocket.py` `_ensure_broker_credentials()` to load from `broker_api_credentials` | Rewrite credential loading logic |
| 7 | **O** | Consolidate market data source to `PUT /api/user/preferences/market-data-source`, always trigger live switch | New route, remove old SmartAPI route |
| 8 | **Q** | TickerPool credential cache expiry checks + `token_expired` WebSocket message | TickerPool changes, frontend notification |
| 9 | **F** | Proper fallback chain for all 6 brokers via FailoverController | Extend fallback beyond SmartAPI↔Kite swap |

### Phase 4: Broker-Specific Fixes

| Order | Gap | What | Effort |
|-------|-----|------|--------|
| 10 | **K** | Replace Dhan static-token login with DhanHQ v2 OAuth consent flow | Rewrite `dhan_auth.py` |
| 11 | **H** | Fix "Reconnect Upstox" so it doesn't overwrite login JWT | Fix `upstox_auth.py` reconnect flow |
| 12 | **D** | Upstox platform token auto-refresh using `.env` auto-login credentials | Add startup/scheduled refresh |
| 13 | **E** | Dhan/Fyers/Paytm token expiry handling | Add expiry checks per broker |
| 14 | **A** | Fix "Platform Default" UI label — clarify it uses user's own creds, not platform `.env` | Frontend copy change |

### Gaps Resolved By Others (No Separate Work)

| Gap | Resolved By |
|-----|-------------|
| **I** | Gap J (removing Mode B eliminates the unfiltered query) |
| **G** | Gap O (consolidating to one endpoint) |
| **B** | Gap P (WebSocket reads from `broker_api_credentials` instead of `broker_connections`) |
| **C** | Gap P (same — Upstox no longer reads from `broker_connections`) |
