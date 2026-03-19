# Authentication Architecture

AlgoChanakya supports 6 broker authentication flows, each producing a unified JWT session token. The platform uses broker-specific OAuth/credential flows combined with JWT tokens for session management.

## OAuth Flow with Zerodha

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │ Frontend │     │ Backend  │     │ Zerodha  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ Click Login    │                │                │
     │───────────────>│                │                │
     │                │                │                │
     │                │ GET /api/auth/ │                │
     │                │  zerodha/login │                │
     │                │───────────────>│                │
     │                │                │                │
     │                │  Login URL     │                │
     │                │<───────────────│                │
     │                │                │                │
     │        Redirect to Zerodha      │                │
     │<────────────────────────────────│                │
     │                                 │                │
     │           Authenticate          │                │
     │────────────────────────────────────────────────>│
     │                                 │                │
     │      Redirect with request_token                │
     │<────────────────────────────────────────────────│
     │                                 │                │
     │ GET /api/auth/zerodha/callback  │                │
     │  ?request_token=xxx             │                │
     │────────────────────────────────>│                │
     │                                 │                │
     │                                 │ Exchange token │
     │                                 │───────────────>│
     │                                 │                │
     │                                 │ Access token   │
     │                                 │<───────────────│
     │                                 │                │
     │                                 │ Create User &  │
     │                                 │ BrokerConnection
     │                                 │ Store in DB    │
     │                                 │                │
     │                                 │ Generate JWT   │
     │                                 │ Store in Redis │
     │                                 │                │
     │   Redirect to frontend with JWT │                │
     │<────────────────────────────────│                │
     │                                 │                │
```

### Flow Steps

1. **User clicks login** → Frontend calls `GET /api/auth/zerodha/login`
2. **Backend generates** Kite Connect login URL with API key
3. **User authenticates** on Zerodha (enters credentials + TOTP)
4. **Zerodha redirects** to `GET /api/auth/zerodha/callback` with `request_token`
5. **Backend exchanges** request token for access token via Kite API
6. **Backend creates/updates** User and BrokerConnection in database
7. **JWT token generated** and stored in Redis
8. **User redirected** to frontend with JWT token in URL

## Session Management

### JWT Token Structure

```json
{
  "user_id": 123,
  "broker_connection_id": 456,
  "exp": 1702000000
}
```

### Token Storage

| Location | Purpose |
|----------|---------|
| **Frontend localStorage** | Client-side persistence |
| **Redis** | Server-side session validation |

### Token Flow

1. JWT stored in `localStorage` after OAuth callback
2. Axios interceptor adds `Authorization: Bearer <token>` header
3. Backend validates token and checks Redis session
4. Sessions expire based on `JWT_EXPIRY_HOURS` (default: 8 hours)

## Protected Routes

### Backend

```python
from app.utils.dependencies import get_current_user, get_current_broker_connection

# User authentication only
@router.get("/watchlist")
async def get_watchlist(user: User = Depends(get_current_user)):
    ...

# Broker-specific operations (needs active connection)
@router.post("/orders/basket")
async def place_order(
    connection: BrokerConnection = Depends(get_current_broker_connection)
):
    ...
```

### Frontend

```javascript
// router/index.js
{
  path: '/watchlist',
  component: WatchlistView,
  meta: { requiresAuth: true }
}

// Navigation guard
router.beforeEach((to) => {
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return '/login'
  }
})
```

## Route Patterns

| Route | Auth Required | Description |
|-------|---------------|-------------|
| `/login` | No | Login page |
| `/auth/callback` | No | OAuth callback |
| `/dashboard` | Yes | Dashboard |
| `/watchlist` | Yes | Watchlist |
| `/optionchain` | Yes | Option chain |
| `/strategy` | Yes | Strategy builder |
| `/strategy/shared/:code` | No | Public shared strategy |
| `/positions` | Yes | F&O positions |

## API Endpoints

### Login

```http
GET /api/auth/zerodha/login
```

Returns Kite Connect login URL.

### Callback

```http
GET /api/auth/zerodha/callback?request_token=xxx&status=success
```

Exchanges token, creates session, redirects to frontend.

### Logout

```http
POST /api/auth/logout
Authorization: Bearer <token>
```

Invalidates session in Redis.

### Current User

```http
GET /api/auth/me
Authorization: Bearer <token>
```

Returns current user info.

## Multi-Broker Authentication Summary

All 6 brokers are supported. Each follows a different auth pattern but produces the same result: a JWT session token stored in localStorage.

| Broker | Auth Type | Flow | Token Lifetime | Route File |
|--------|-----------|------|----------------|------------|
| **Zerodha (Kite)** | OAuth 2.0 | Redirect → callback → exchange token | ~24h access token | `auth.py` |
| **AngelOne (SmartAPI)** | API Key + TOTP | POST credentials → auto-TOTP → token | ~8h session | `auth.py` |
| **Upstox** | OAuth 2.0 | Redirect → callback → exchange token | ~1 year access token | `upstox_auth.py` |
| **Fyers** | OAuth 2.0 | Redirect → callback → exchange token | ~24h access token | `fyers_auth.py` |
| **Dhan** | Static Token | POST client_id + access_token | Until manually revoked | `dhan_auth.py` |
| **Paytm Money** | OAuth 2.0 (3 JWTs) | Redirect → callback → 3 tokens (access, read, public) | Varies per token | `paytm_auth.py` |

### Zerodha (Kite Connect) — OAuth 2.0

Standard OAuth redirect flow. User authenticates on Kite login page, Zerodha redirects with `request_token`, backend exchanges for `access_token`.

- **Login:** `GET /api/auth/zerodha/login` → returns Kite login URL
- **Callback:** `GET /api/auth/zerodha/callback?request_token=xxx`
- **Cost:** Kite Connect API costs ₹500/month

### AngelOne (SmartAPI) — Inline Credentials

No browser redirect. User enters Client ID, PIN, and 6-digit TOTP (from their authenticator app) on the login page. Backend authenticates directly with SmartAPI.

- **Login:** `POST /api/auth/angelone/login` with `{client_id, pin, totp}` (user-provided)
- **Credentials:** NOT stored — used once for authentication
- **Note:** The platform's universal SmartAPI connection (`.env`) is separate from individual user login
- **Cost:** FREE

### Upstox — OAuth 2.0

Standard OAuth redirect. Notable for very long-lived tokens (~1 year). TOTP supported for automated login.

- **Login:** `GET /api/auth/upstox/login` → returns Upstox OAuth URL
- **Callback:** `GET /api/auth/upstox/callback?code=xxx`
- **Disconnect:** `DELETE /api/auth/upstox/disconnect`
- **Cost:** FREE (API pricing changed from ₹499/month to free in 2025)
- **Note:** The platform's universal Upstox connection (`.env` — `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`, etc.) is separate from individual user OAuth login. Platform credentials serve backend market data operations for all users; user login produces a per-user `access_token` stored in `broker_connections`.
- **OAuth login tested and working:** 2026-03-19

### Fyers — OAuth 2.0

Standard OAuth redirect with authorization code exchange.

- **Login:** `GET /api/auth/fyers/login` → returns Fyers OAuth URL
- **Callback:** `GET /api/auth/fyers/callback?auth_code=xxx`
- **Disconnect:** `DELETE /api/auth/fyers/disconnect`
- **Cost:** FREE

### Dhan — Static Token

No OAuth flow. User provides their client ID and a static access token (generated from Dhan developer portal). Simplest auth flow.

- **Login:** `POST /api/auth/dhan/login` with `{client_id, access_token}`
- **Disconnect:** `DELETE /api/auth/dhan/disconnect`
- **Cost:** FREE (Trading API) / conditional (Data API)

### Paytm Money — OAuth 2.0 (3 JWTs)

OAuth redirect similar to others, but returns 3 separate JWT tokens: access token (for trading), read token (for data), and public token (for market data).

- **Login:** `GET /api/auth/paytm/login` → returns Paytm OAuth URL
- **Callback:** `GET /api/auth/paytm/callback?requestToken=xxx`
- **Public Token:** `GET /api/auth/paytm/public-token`
- **Disconnect:** `DELETE /api/auth/paytm/disconnect`
- **Cost:** FREE

### Auth Fallback Chain

When a broker token expires, the system follows this fallback: refresh token → OAuth re-login → API key/secret (last resort). The frontend auth store tracks per-broker loading states.

## Two Credential Systems: Login vs Market Data API

AlgoChanakya has two distinct credential flows that serve different purposes. Understanding this distinction is critical.

### 1. Login Credentials (Login Page → Order Execution)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Authenticate user for order execution with their broker |
| **Entry point** | Login page — broker dropdown + credential fields |
| **Stored?** | **NO** — used once to get session token, then discarded |
| **What's stored** | Only the session token (JWT in localStorage + Redis) |
| **Used for** | Placing orders, viewing positions/holdings, managing funds |
| **Expiry** | Varies by broker (8h to 1 year). User must re-login when expired |

**Login page flow:**
1. User selects broker from dropdown
2. Enters credentials (OAuth redirect, or inline Client ID + PIN + TOTP, or Client ID + Access Token)
3. Backend authenticates with broker API, gets broker session token
4. Backend generates AlgoChanakya JWT, stores in Redis
5. Frontend stores JWT in localStorage — credentials are NOT persisted

### 2. Market Data API Credentials (Settings Page → Live Data)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Provide live market data from user's own broker API (optional upgrade) |
| **Entry point** | Settings page — per-broker API credential fields |
| **Stored?** | **YES** — encrypted in database (needed for ongoing data fetching) |
| **What's stored** | API keys, access tokens, secrets — encrypted via `app.utils.encryption` |
| **Used for** | Live quotes, option chain, OHLC, WebSocket ticks |
| **Default** | Platform-level universal API (SmartAPI) serves all users without configuration |

**Market data architecture:**
- **Platform Default (universal):** A shared AngelOne SmartAPI connection stored in `.env` provides market data to ALL users. No per-user setup needed.
- **User Upgrade (optional):** Users can configure their own broker's API credentials in Settings to use their own data connection. The broker's API can be free or paid — the platform doesn't differentiate.
- **Switching:** Settings → Market Data Source dropdown controls which source is active.

### Key Distinction

| | Login Page | Settings Page |
|---|-----------|---------------|
| **Purpose** | Authenticate for order execution | Configure market data API |
| **Credential type** | Login credentials (OAuth, PIN, TOTP) | API credentials (API key, access token) |
| **Stored in DB?** | No — JWT only | Yes — encrypted |
| **When needed** | Every session (daily re-login) | One-time setup |
| **Required?** | Yes — must login to use the app | No — platform default provides data |

### Platform-Level Market Data (Universal API)

The platform maintains a shared SmartAPI (AngelOne) connection configured in `backend/.env`. This is NOT tied to any individual user — it serves as the default market data source for ALL users.

- **Credentials:** `ANGEL_API_KEY`, `ANGEL_HIST_API_KEY`, `ANGEL_TRADE_API_KEY`, `ANGEL_CLIENT_ID`, `ANGEL_PIN`, `ANGEL_TOTP_SECRET`
- **Auto-TOTP:** Generates TOTP codes automatically via `pyotp` for unattended operation
- **Failover chain:** SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite
- **No user interaction:** This runs entirely on the backend without any user involvement

## Implementation Files

| File | Purpose |
|------|---------|
| `backend/app/api/routes/auth.py` | Core auth (Zerodha OAuth, AngelOne TOTP, logout, /me) |
| `backend/app/api/routes/upstox_auth.py` | Upstox OAuth flow |
| `backend/app/api/routes/fyers_auth.py` | Fyers OAuth flow |
| `backend/app/api/routes/dhan_auth.py` | Dhan static token flow |
| `backend/app/api/routes/paytm_auth.py` | Paytm 3-token OAuth flow |
| `backend/app/utils/jwt.py` | JWT creation/verification |
| `backend/app/utils/dependencies.py` | Auth dependencies |
| `backend/app/utils/encryption.py` | Credential encryption (SmartAPI) |
| `frontend/src/stores/auth.js` | Auth state management (all 6 brokers) |
| `frontend/src/services/api.js` | Axios interceptors (401 handling) |

## Related Documentation

- [Overview](overview.md) - System architecture
- [Broker Abstraction](broker-abstraction.md) - Multi-broker credential management
- [Database](database.md) - User and BrokerConnection models
- [WebSocket](websocket.md) - JWT authentication for WebSocket connections

**See also:**
- [CLAUDE.md - Authentication](../../CLAUDE.md#authentication-error-handling) for error handling patterns
- [backend/CLAUDE.md - Encryption](../../backend/CLAUDE.md#encryption-for-credentials) for credential storage
