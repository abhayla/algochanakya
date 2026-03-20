# Paytm Money Authentication Flow

> **MATURITY WARNING:** Paytm Money API is in a relatively early stage compared to Kite/SmartAPI.
> Breaking changes have been observed without prior deprecation notices. Pin your integration
> to specific behavior and verify auth flow after any SDK or API version bump.

## Overview

Paytm Money uses **OAuth 2.0 authorization code flow** with a unique **3-token system**.
Unlike Kite (1 access token) or SmartAPI (1 JWT), Paytm issues three separate JWTs,
each scoped to a different permission level.

## Token Types

| Token | Header Key | Scope | Use Cases |
|-------|-----------|-------|-----------|
| `access_token` | `x-jwt-token` | Full read + write | Place/modify/cancel orders, positions, holdings |
| `public_access_token` | Used in WS URL param | WebSocket only | Live tick subscriptions via broadcast WebSocket |
| `read_access_token` | `x-jwt-token` | Read-only REST | Market data, margins, profile, order book (no writes) |

## Auth Flow (Step by Step)

### Step 1: Redirect User to Paytm Login

Construct the login URL and redirect the user's browser:

```
https://login.paytmmoney.com/merchant-login?apiKey={api_key}&state={random_state}
```

**Parameters:**
- `apiKey` - Your registered Paytm Money API key
- `state` - Random string for CSRF protection (verify on callback)

### Step 2: User Authenticates on Paytm

The user logs in with their Paytm Money credentials on Paytm's hosted login page.
After successful authentication, Paytm redirects to your registered callback URL.

### Step 3: Receive Callback with requestToken

Paytm redirects to:
```
{your_redirect_url}?requestToken={request_token}&state={state}
```

**Backend handler pseudocode:**
```python
@router.get("/api/auth/paytm/callback")
async def paytm_callback(requestToken: str, state: str):
    # 1. Verify state matches what we sent
    if state != stored_state:
        raise HTTPException(400, "Invalid state parameter")

    # 2. Exchange requestToken for access tokens
    tokens = await exchange_request_token(requestToken)

    # 3. Store tokens and create session
    return tokens
```

### Step 4: Exchange requestToken for 3 Tokens

```python
import requests

def exchange_request_token(api_key: str, api_secret: str, request_token: str) -> dict:
    """Exchange the one-time requestToken for 3 JWT tokens."""
    url = "https://developer.paytmmoney.com/accounts/v2/gettoken"

    payload = {
        "api_key": api_key,
        "api_secret_key": api_secret,
        "request_token": request_token
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()
    data = response.json()

    # Response contains all 3 tokens
    return {
        "access_token": data["access_token"],           # Full access
        "public_access_token": data["public_access_token"],  # WebSocket only
        "read_access_token": data["read_access_token"],      # Read-only REST
    }
```

**Response structure:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "public_access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "read_access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Using Tokens in Requests

### REST API (Full Access)

```python
headers = {
    "x-jwt-token": access_token,
    "Content-Type": "application/json"
}
response = requests.post(
    "https://developer.paytmmoney.com/orders/v1/place/regular",
    headers=headers,
    json=order_payload
)
```

### REST API (Read-Only)

```python
headers = {
    "x-jwt-token": read_access_token,
    "Content-Type": "application/json"
}
response = requests.get(
    "https://developer.paytmmoney.com/accounts/v1/user/details",
    headers=headers
)
```

### WebSocket (Public Access Token)

```python
ws_url = (
    f"wss://developer-ws.paytmmoney.com/broadcast/user/v1/data"
    f"?x_jwt_token={public_access_token}"
)
```

## Token Validity and Refresh

| Aspect | Detail |
|--------|--------|
| Token lifetime | ~24 hours (expires end of day or next trading day morning) |
| Refresh mechanism | None. Must re-authenticate via full OAuth flow. |
| Concurrent sessions | Only 1 active session per API key |
| Token storage | Store encrypted in `broker_credentials` table |

> **MATURITY WARNING:** Token expiry behavior is not precisely documented by Paytm.
> Observed behavior suggests ~24h validity, but tokens have been seen expiring earlier
> during Paytm platform maintenance windows. Implement proactive re-auth on 401.

## Token Compatibility: Orders vs Market Data

Paytm Money returns **3 separate tokens** from a single OAuth flow:
- `access_token` — for REST API (orders, positions, holdings). Header: `x-jwt-token: {access_token}`
- `public_access_token` — for **WebSocket market data streaming**. This is the token needed for live ticks.
- `read_access_token` — for read-only API access

**The `access_token` CANNOT be used for WebSocket market data.** The `public_access_token` is required.

However, both tokens come from the same OAuth flow — no separate authorization is needed.

### AlgoChanakya Implication

When a user logs in with Paytm OAuth, all 3 tokens are returned. Currently stored in `broker_connections`:
- `access_token` in the main `access_token` field
- `public_access_token` in `broker_metadata.read_token` (confusing name — should be `public_token`)
- `read_access_token` in `broker_metadata.edge_token` (confusing name — should be `read_token`)

For market data, the `public_access_token` must be copied to `broker_api_credentials`. The naming in `broker_metadata` is misleading and should be fixed.

### Additional Endpoint

`POST /auth/paytm/public-token` — allows manual saving of `public_access_token` for WebSocket (separate from OAuth flow).

### Token Expiry

- All 3 tokens expire in ~24 hours
- No refresh mechanism — user must re-authenticate daily

## AlgoChanakya Integration Notes

### Token-to-Adapter Mapping

```python
# In PaytmMoneyAdapter, store all 3 tokens
class PaytmCredentials:
    api_key: str
    api_secret: str
    access_token: str           # For order execution adapter
    public_access_token: str    # For ticker/WebSocket adapter
    read_access_token: str      # For market data adapter (read-only)
```

### Which Token for Which Adapter

| AlgoChanakya Adapter | Paytm Token | Reason |
|---------------------|-------------|--------|
| `BrokerAdapter` (orders) | `access_token` | Needs write permission |
| `MarketDataBrokerAdapter` (REST) | `read_access_token` | Read-only market data |
| `TickerServiceBase` (WebSocket) | `public_access_token` | WebSocket-specific token |

### Re-Authentication Strategy

Since Paytm has no refresh token mechanism, the adapter must:
1. Catch 401 errors on any API call
2. Mark the session as expired
3. Notify the user to re-authenticate via the OAuth flow
4. Optionally queue failed requests for retry after re-auth
