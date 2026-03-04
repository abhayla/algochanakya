# Kite Connect Authentication Flow

Complete OAuth 2.0 authentication sequence for Zerodha Kite Connect.

## Overview

Kite uses a standard **OAuth 2.0 redirect flow**:
1. User visits Zerodha login page
2. After login, Zerodha redirects back with a `request_token`
3. App exchanges `request_token` for `access_token` using `api_secret`

**No auto-refresh.** Token expires ~6 AM next trading day. User must re-login.

## Step 1: Redirect to Kite Login

### Login URL

```
https://kite.zerodha.com/connect/login?v=3&api_key={api_key}
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `v` | Yes | API version (always `3`) |
| `api_key` | Yes | Your Kite Connect API key |

### User Flow

1. User clicks "Login with Zerodha" in AlgoChanakya
2. Browser redirects to Zerodha login page
3. User enters Zerodha credentials + TOTP
4. Zerodha authenticates and redirects back

## Step 2: Receive Request Token

After successful login, Zerodha redirects to your registered callback URL:

```
{redirect_url}?request_token={token}&action=login&status=success
```

**Callback Parameters:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| `request_token` | `abc123...` | Single-use, expires in ~5 minutes |
| `action` | `login` | Always "login" on success |
| `status` | `success` | "success" or error status |

**AlgoChanakya Callback:**
- Dev: `http://localhost:8001/api/auth/zerodha/callback`
- Prod: `https://algochanakya.com/api/auth/zerodha/callback`

## Step 3: Exchange for Access Token

### Request

```http
POST https://api.kite.trade/session/token
Content-Type: application/x-www-form-urlencoded

api_key={api_key}&request_token={request_token}&checksum={checksum}
```

### Checksum Calculation

```python
import hashlib

checksum = hashlib.sha256(
    f"{api_key}{request_token}{api_secret}".encode()
).hexdigest()
```

**The checksum is SHA-256 of:** `api_key + request_token + api_secret` (concatenated, no separator).

### Successful Response (200)

```json
{
  "status": "success",
  "data": {
    "user_id": "AB1234",
    "user_name": "John Doe",
    "user_shortname": "JD",
    "email": "john@example.com",
    "user_type": "individual",
    "broker": "ZERODHA",
    "exchanges": ["NSE", "BSE", "NFO", "BFO", "MCX"],
    "products": ["CNC", "NRML", "MIS", "BO", "CO"],
    "order_types": ["MARKET", "LIMIT", "SL", "SL-M"],
    "access_token": "xyz789...",
    "public_token": "pub456...",
    "refresh_token": "",
    "login_time": "2025-02-27 09:15:00",
    "meta": {
      "demat_consent": "consent"
    },
    "avatar_url": ""
  }
}
```

### Error Response

```json
{
  "status": "error",
  "message": "Invalid `checksum`.",
  "error_type": "TokenException"
}
```

## Step 4: Use Access Token

### REST API Authentication

All REST requests include:

```http
Authorization: token {api_key}:{access_token}
```

**Example:**
```http
GET https://api.kite.trade/user/profile
Authorization: token abc123:xyz789
Content-Type: application/json
```

### WebSocket Authentication

```
wss://ws.kite.trade?api_key={api_key}&access_token={access_token}
```

### Using kiteconnect SDK

```python
from kiteconnect import KiteConnect

kite = KiteConnect(api_key="abc123")

# Step 1: Generate login URL
login_url = kite.login_url()
# → "https://kite.zerodha.com/connect/login?v=3&api_key=abc123"

# Step 2: After redirect, exchange request_token
data = kite.generate_session(
    request_token="request_token_from_redirect",
    api_secret="your_api_secret"
)

# Step 3: Set access token
kite.set_access_token(data["access_token"])

# Now make API calls
profile = kite.profile()
orders = kite.orders()
```

## Step 5: Token Invalidation

### Logout

```http
DELETE https://api.kite.trade/session/token
Authorization: token {api_key}:{access_token}

api_key={api_key}&access_token={access_token}
```

### SDK Logout

```python
kite.invalidate_access_token(access_token="xyz789")
```

## Token Validity

```
Login: access_token valid until ~6:00 AM next trading day
                    ↓
6:00 AM: Token expires automatically
                    ↓
User must complete OAuth flow again (no refresh)
```

**Key Points:**
- `access_token` is valid for approximately one trading day
- Expires around 6:00 AM IST the next day
- **No refresh token mechanism** - must re-do OAuth
- Weekends/holidays: token from Friday lasts until Monday ~6 AM

## AlgoChanakya Implementation

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/api/routes/auth.py` | OAuth callback handler |
| `backend/app/utils/dependencies.py` | `get_current_broker_connection` |
| `backend/app/services/brokers/kite_adapter.py` | Uses access_token for orders |
| `frontend/src/stores/auth.js` | Auth state management |

### OAuth Flow in Codebase

```python
# backend/app/api/routes/auth.py (simplified)
@router.get("/zerodha/callback")
async def zerodha_callback(request_token: str, db: AsyncSession):
    # 1. Exchange request_token for access_token
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    data = kite.generate_session(request_token, api_secret=settings.KITE_API_SECRET)

    # 2. Store access_token in BrokerConnection table
    # 3. Generate JWT for frontend
    # 4. Redirect to frontend with JWT
```

### Environment Variables

```bash
# backend/.env
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_REDIRECT_URL=http://localhost:8001/api/auth/zerodha/callback  # dev
# Production: https://algochanakya.com/api/auth/zerodha/callback
```

## Common Auth Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `TokenException: Invalid checksum` | Wrong api_secret or concatenation | Verify SHA-256 of api_key+request_token+api_secret |
| `TokenException` after hours | access_token expired | Re-do OAuth flow |
| Redirect URL mismatch | Callback URL not registered | Register URL in Kite developer dashboard |
| `InputException: Missing api_key` | Auth header format wrong | Use `token api_key:access_token` not `Bearer` |
| Token works in morning, fails at night | Normal expiry | Expected behavior, re-auth next day |

## Sandbox / Test Environment

Kite Connect provides a sandbox environment for development and testing without placing real orders.

### Sandbox Setup

- **Sandbox docs:** https://kite.trade/docs/connect/v3/#sandbox
- Obtain a sandbox API key from the [Kite Developer Console](https://developers.kite.trade/)
- The sandbox simulates authentication and order flows
- Market data endpoints may return static/simulated data in sandbox mode

### Sandbox vs Production

| Feature | Sandbox | Production |
|---------|---------|------------|
| Base URL | Check developer console for sandbox URL | `https://api.kite.trade` |
| Auth flow | Same OAuth steps | Same OAuth steps |
| Orders | Simulated (no real trades) | Real orders |
| Market data | Static/simulated | Live exchange data |
| WebSocket | May be limited | Full KiteTicker |

### AlgoChanakya Sandbox Configuration

```bash
# backend/.env (sandbox)
KITE_API_KEY=your_sandbox_api_key
KITE_API_SECRET=your_sandbox_api_secret
KITE_REDIRECT_URL=http://localhost:8001/api/auth/zerodha/callback
```

No code changes are required to switch between sandbox and production — only the API key/secret changes.

## Security Notes

- Store `api_secret` in environment variables only (never in code or DB)
- `access_token` should be stored securely (Redis or encrypted DB)
- Never log access_token in production
- Validate `request_token` has not been used before (replay attack prevention)
- Use HTTPS for all callback URLs in production
