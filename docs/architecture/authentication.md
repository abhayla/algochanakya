# Authentication Architecture

AlgoChanakya uses OAuth 2.0 with Zerodha Kite Connect for broker authentication, combined with JWT tokens for session management.

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

## Implementation Files

| File | Purpose |
|------|---------|
| `backend/app/api/routes/auth.py` | OAuth endpoints |
| `backend/app/utils/jwt.py` | JWT creation/verification |
| `backend/app/utils/dependencies.py` | Auth dependencies |
| `frontend/src/stores/auth.js` | Auth state management |
| `frontend/src/services/api.js` | Axios interceptors |

## Related Documentation

- [Overview](overview.md) - System architecture
- [Broker Abstraction](broker-abstraction.md) - Multi-broker credential management
- [Database](database.md) - User and BrokerConnection models
- [WebSocket](websocket.md) - JWT authentication for WebSocket connections

**See also:**
- [CLAUDE.md - Authentication](../../CLAUDE.md#authentication-error-handling) for error handling patterns
- [backend/CLAUDE.md - Encryption](../../backend/CLAUDE.md#encryption-for-credentials) for credential storage
