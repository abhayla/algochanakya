# Fyers Authentication Flow

Complete OAuth 2.0 authentication sequence for Fyers API v3.

## Overview

Fyers uses **OAuth 2.0 authorization_code** grant with a distinctive authentication header format. Unlike other brokers that use `Bearer` tokens, Fyers uses a **colon-separated** `{app_id}:{access_token}` format.

Key characteristics:
1. **appIdHash** - Token exchange requires SHA-256 hash of `app_id:app_secret`
2. **Colon-separated auth header** - `Authorization: {app_id}:{access_token}` (NOT Bearer)
3. **Midnight expiry** - Access tokens expire at midnight IST (not after fixed hours)

## Step 1: Redirect to Fyers Login

### Login URL

```
https://api-t1.fyers.in/api/v3/generate-authcode
  ?client_id={app_id}
  &redirect_uri={redirect_url}
  &response_type=code
  &state={random_state}
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `client_id` | Yes | Fyers App ID | `ABC123-100` |
| `redirect_uri` | Yes | Registered redirect URL | `https://algochanakya.com/api/auth/fyers/callback` |
| `response_type` | Yes | Must be `code` | `code` |
| `state` | Yes | CSRF protection token | `random_uuid_string` |

### Example URL

```
https://api-t1.fyers.in/api/v3/generate-authcode
  ?client_id=ABC123-100
  &redirect_uri=https://algochanakya.com/api/auth/fyers/callback
  &response_type=code
  &state=a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

## Step 2: Receive Authorization Code

After the user logs in on the Fyers website, Fyers redirects to the registered URL:

```
{redirect_uri}?auth_code={authorization_code}&state={state}
```

### Example Redirect

```
https://algochanakya.com/api/auth/fyers/callback
  ?auth_code=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
  &state=a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Important:** Validate the `state` parameter matches what you sent in Step 1 to prevent CSRF attacks. The `auth_code` is single-use and expires in approximately 5 minutes.

## Step 3: Compute appIdHash

Before exchanging the auth code, compute the SHA-256 hash of `app_id:app_secret`:

```python
import hashlib

app_id = "ABC123-100"
app_secret = "MY_APP_SECRET_KEY"

# Compute SHA-256 of "app_id:app_secret"
app_id_hash = hashlib.sha256(
    f"{app_id}:{app_secret}".encode()
).hexdigest()
# Result: "a3f2b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6"
```

**Warning:** The `appIdHash` is a SHA-256 hex digest of `"{app_id}:{app_secret}"` (with colon separator). Do NOT hash them separately or use a different hash algorithm.

## Step 4: Exchange for Access Token

### Request

```http
POST https://api-t1.fyers.in/api/v3/validate-authcode
Content-Type: application/json

{
  "grant_type": "authorization_code",
  "appIdHash": "a3f2b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6",
  "code": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grant_type` | string | Yes | Must be `authorization_code` |
| `appIdHash` | string | Yes | SHA-256 hex digest of `{app_id}:{app_secret}` |
| `code` | string | Yes | Authorization code from Step 2 |

### Successful Response (200)

```json
{
  "s": "ok",
  "code": 200,
  "message": "",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer"
}
```

### Error Response

```json
{
  "s": "error",
  "code": -16,
  "message": "Invalid or expired auth code"
}
```

## Step 5: Use Access Token

### Auth Header Format (UNIQUE - NOT Bearer)

```
Authorization: {app_id}:{access_token}
```

**Example:**
```
Authorization: ABC123-100:eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Critical:** This is NOT `Bearer {token}`. The app_id and access_token are separated by a colon with NO prefix keyword. This is the most common authentication error when integrating Fyers.

### Authenticated Request Example

```http
GET https://api-t1.fyers.in/api/v3/profile
Content-Type: application/json
Authorization: ABC123-100:eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Token Validity

| Token | Validity | Notes |
|-------|----------|-------|
| `auth_code` | ~5 minutes | Single use, exchange immediately |
| `access_token` | Until midnight IST | Resets daily at 00:00 IST |

**Midnight expiry:** Unlike other brokers (SmartAPI: 24h, Kite: end of day), Fyers tokens expire exactly at midnight IST. If a user authenticates at 11:55 PM, the token is valid for only 5 minutes.

## Token Compatibility: Orders + Market Data

The same `access_token` obtained from Fyers OAuth works for BOTH:
- **REST API** (orders, positions, holdings) — `Authorization: {app_id}:{access_token}`
- **Data WebSocket** (live market data streaming, up to 5,000 symbols)
- **Order WebSocket** (real-time order/trade/position updates, <50ms execution)

**No separate market data token is needed.** A single OAuth flow gives access to everything.

### AlgoChanakya Implication

If a user logs in with Fyers OAuth, the `access_token` stored in `broker_connections` can be reused for market data in `broker_api_credentials`. No separate Settings OAuth is needed — the token is copied automatically when the user selects "Use for market data" in Settings.

### Token Expiry

- Token expires at midnight IST daily
- No refresh mechanism — user must re-authenticate daily

Source: https://support.fyers.in/portal/en/kb/articles/how-can-i-use-the-data-websocket-in-api-v3-to-access-real-time-data

## Python SDK Authentication

```python
from fyers_apiv3 import fyersModel

# Step 1: Create session model for generating auth code URL
session = fyersModel.SessionModel(
    client_id=app_id,
    secret_key=app_secret,
    redirect_uri=redirect_url,
    response_type="code",
    grant_type="authorization_code"
)
auth_url = session.generate_authcode()
# Redirect user to auth_url

# Step 2: After receiving auth_code from callback
session.set_token(auth_code)
response = session.generate_token()
access_token = response["access_token"]

# Step 3: Create API model for subsequent calls
fyers = fyersModel.FyersModel(
    client_id=app_id,
    is_async=False,
    token=access_token,
    log_path=""
)

# All subsequent API calls use this fyers instance
profile = fyers.get_profile()
```

## AlgoChanakya Implementation

### Key Files (Planned)

| File | Purpose |
|------|---------|
| `backend/app/api/routes/fyers_auth.py` | OAuth callback endpoint (planned) |
| `backend/app/services/brokers/fyers_adapter.py` | Order execution adapter (planned) |
| `backend/app/services/brokers/market_data/fyers_adapter.py` | Market data adapter (planned) |
| `backend/app/utils/encryption.py` | Credential encryption (existing) |

### Credential Storage Pattern

```python
from app.utils.encryption import encrypt, decrypt

# Store Fyers credentials (encrypted)
encrypted_app_id = encrypt(app_id)
encrypted_app_secret = encrypt(app_secret)
encrypted_access_token = encrypt(access_token)

# Retrieve for API calls
app_id = decrypt(encrypted_app_id)
access_token = decrypt(encrypted_access_token)

# Build auth header
auth_header = f"{app_id}:{access_token}"
```

### Auth Header Builder

```python
def build_fyers_auth_header(app_id: str, access_token: str) -> dict:
    """Build Fyers-specific auth header (colon-separated, no Bearer)."""
    return {
        "Authorization": f"{app_id}:{access_token}",
        "Content-Type": "application/json"
    }
```

## Common Auth Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `-16` error on API calls | Using `Bearer` prefix in header | Remove `Bearer`, use `{app_id}:{access_token}` |
| `-16` error at midnight | Token expired at midnight IST | Re-authenticate user |
| `-1` on validate-authcode | Wrong appIdHash computation | Verify SHA-256 of `{app_id}:{app_secret}` |
| `-1` invalid grant | Auth code already used or expired | Request new auth code |
| Redirect fails | Redirect URI mismatch | URI must exactly match Fyers app settings |
| SDK auth fails | Wrong SDK version | Use `fyers-apiv3`, not `fyers-apiv2` |

## Security Notes

- Store `app_secret` in environment variables (`FYERS_APP_SECRET`), never in code
- Encrypt `access_token` at rest using `app.utils.encryption`
- Validate `state` parameter on callback to prevent CSRF
- The `appIdHash` can be computed once and cached (it never changes)
- Rate limit auth attempts to prevent abuse
- Log auth failures but never log tokens or secrets
