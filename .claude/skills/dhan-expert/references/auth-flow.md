# Dhan Authentication Flow

## Overview

Dhan has a **dual credential system**: an **API Key + Secret** (permanent, for OAuth-style app registration) and an **Access Token** (24-hour JWT, for API calls). Both are generated from the Dhan trading dashboard (web.dhan.co), NOT the DhanHQ Developer Portal (developer.dhanhq.co).

Dhan also supports **TOTP** for automated login (no SMS OTP needed), **Static IP whitelisting** for order API security, and **DhanHQ v2 OAuth** for proper programmatic authentication (3-step consent flow).

### Authentication Methods Summary

| Method | Use Case | Token Lifetime | Automation |
|--------|----------|---------------|------------|
| **Manual Dashboard** | Quick setup, testing | 24h | No (requires UI) |
| **OAuth Consent Flow** | Production apps, multi-user | 24h | Yes (server-to-server + browser redirect) |
| **Direct TOTP Login** | Headless automation | 24h | Yes (fully programmatic, no browser) |
| **Playwright Regen** | Fallback automation | 24h | Yes (browser automation) |

---

## Credential Types

### 1. API Key + API Secret (Permanent)

| Property            | Value                                              |
|---------------------|----------------------------------------------------|
| Type                | OAuth-style app credentials                        |
| Generation          | Dashboard → DhanHQ Trading APIs → toggle to "API Key" |
| Expiry              | **Permanent** (until manually revoked)             |
| Required fields     | Application Name, Redirect URL                     |
| Use case            | OAuth flow, app identification                     |

### 2. Access Token (24-hour JWT)

| Property            | Value                                              |
|---------------------|----------------------------------------------------|
| Type                | Static API access token (JWT)                      |
| Generation          | Dashboard → DhanHQ Trading APIs → "Access Token" tab |
| Expiry              | **24 hours** from generation                       |
| Refresh Mechanism   | Must regenerate daily from dashboard               |
| Required fields     | Application Name only (Postback URL optional)      |
| Use case            | All API calls (header: `access-token`)             |

### 3. TOTP (Optional, Recommended)

| Property            | Value                                              |
|---------------------|----------------------------------------------------|
| Type                | Time-based One-Time Password                       |
| Setup               | Dashboard → DhanHQ Trading APIs → "Set-up TOTP"   |
| Authenticator apps  | Google Authenticator, Microsoft, Authy             |
| Use case            | Automated login without SMS OTP                    |

---

## Complete Setup Flow (Tested 2026-03-18)

### Step 1: Log in to Dhan Trading Dashboard

1. Navigate to `https://login.dhan.co` → Select **"Dhan"** platform
2. Click **"Show login with Mobile"** (default shows QR code login)
3. Enter phone number → Click **"Proceed"**
4. Enter 6-digit OTP sent to phone (or TOTP if already set up)
5. Enter trading **PIN** (6 digits)
6. You are now on the Dhan dashboard (`web.dhan.co/index/home`)

**IMPORTANT:** The DhanHQ Developer Portal (`developer.dhanhq.co`) is a SEPARATE system with its own registration. It shows "Invalid Email" errors during registration. You do NOT need it — all token/key generation is available directly from the trading dashboard.

### Step 2: Navigate to API Section

1. Click the **profile icon** (top-right corner, `#userProfileDropdown`)
2. Click **"DhanHQ Trading APIs"** from the dropdown menu
3. This opens the "Trading & Investing APIs" section within the profile page
4. Your **Client ID** is visible on the profile page (numeric, e.g., `1234567890`)

### Step 3: Generate Access Token (24-hour)

The page defaults to the **"Generate Access Token / API Key"** tab with **"Access Token"** selected.

1. Enter **Application Name** (e.g., "AlgoChanakya")
2. Token validity is fixed at **24 Hours** (not configurable)
3. Optionally enter a **Postback URL** for order update webhooks
4. Click **"Generate Access Token"**
5. The token appears in a table below — it **remains visible** (not shown only once)
6. You can have multiple tokens; each can be individually **revoked**
7. Table shows: Application Name | Access Token | Time to Expiry | Status | Action(Revoke)

### Step 4: Generate API Key + Secret (Permanent)

On the same page, toggle the **"Access Token ↔ API Key"** switch to **API Key** side.

1. Enter **Application Name** (e.g., "AlgoChanakya")
2. Enter **Redirect URL** (e.g., `http://localhost:8001/api/auth/dhan/callback`)
3. Optionally enter a **Postback URL**
4. Click **"Generate API Key"**
5. Table shows: Application Name | **API Key** | **API Secret** | Status | Action(Revoke)
6. API Key is a short string (e.g., `abcd1234`)
7. API Secret is a UUID (e.g., `89d57475-1e29-4f0f-b584-7259f21c218e`)
8. These are **permanent** — no daily regeneration needed

### Step 5: Set Up TOTP (Optional, Recommended)

Below the token table, under **"Optional Settings:"**:

1. Click **"Add TOTP"**
2. A dialog opens: "Setup TOTP" → Click **"Enable TOTP"**
3. An OTP is sent to registered mobile & email → Enter OTP → Click **"Verify OTP"**
4. A QR code and **Setup Code** (base32 string) are displayed
5. Scan QR in authenticator app OR copy the Setup Code
6. Enter the 6-digit code from authenticator → Click **"Enable TOTP Login"**
7. **Save the Setup Code** (TOTP secret) to `.env` — this enables auto-TOTP generation for future logins

**CRITICAL:** Save the TOTP secret (base32 string like `ABCD1234EFGH5678...`) immediately. It is only shown during setup.

### Step 6: Set Up Static IP (Optional)

Below TOTP, under **"Static IP Setting"**:

1. Click **"Add IP Setting"**
2. Two IP address slots are available:
   - **IP Address 1:** Click "Fetch default IP Address" to auto-detect current IP, or enter manually
   - **IP Address 2:** Click "Edit" → Enter IP → Click "Save"
3. **7-day cooldown** between IP changes
4. Static IP is required for **order write operations** (place/modify/cancel orders)

**Recommended setup:**
- IP 1: Development machine IP (dynamic — will need updating)
- IP 2: VPS/production server IP (static)

---

## Tabs on the API Page

The DhanHQ Trading APIs section has 3 sub-tabs:

| Tab | What It Shows |
|-----|--------------|
| **Generate Access Token / API Key** | Token/key generation with Access Token ↔ API Key toggle |
| **Trading APIs** | Status (Active/Inactive), features list, pricing (FREE) |
| **Data APIs** | Status, features list, pricing (₹499/mo or 25 F&O trades/mo for free) |

- **Trading APIs** are **FREE** and automatically active for all accounts
- **Data APIs** require either 25 F&O trades/month OR ₹499/month subscription
- Both use the **same access token** — there are no separate tokens per API type

---

## .env Configuration

```bash
# ── Dhan ──────────────────────────────────────────────────────────────────────
DHAN_CLIENT_ID=your-dhan-client-id              # Numeric UID from profile
DHAN_ACCESS_TOKEN=eyJ0eXAi...                   # 24-hour JWT, must regenerate daily
DHAN_LOGIN_PHONE=your-phone-number              # For automated login via Playwright
DHAN_LOGIN_PIN=your-trading-pin                 # Trading PIN for login
DHAN_TOTP_SECRET=your-totp-base32-secret        # Base32 TOTP secret for auto-OTP
DHAN_API_KEY=your-api-key                       # Permanent API key (short string)
DHAN_API_SECRET=your-api-secret-uuid            # Permanent API secret (UUID)
DHAN_REDIRECT_URL=http://localhost:8001/api/auth/dhan/callback
```

---

## Automated Token Regeneration (via Playwright)

Since the access token expires every 24 hours, automated regeneration is possible:

1. Navigate to `https://login.dhan.co` → Select "Dhan"
2. Click "Show login with Mobile" → Enter `DHAN_LOGIN_PHONE`
3. Enter TOTP code (generate from `DHAN_TOTP_SECRET` using pyotp) — **no SMS OTP needed**
4. Enter `DHAN_LOGIN_PIN`
5. Profile icon → "DhanHQ Trading APIs"
6. Click "Generate" under "Generate new Access Token"
7. Copy token from table → Update `DHAN_ACCESS_TOKEN` in `.env`

```python
# Auto-generate TOTP code
import pyotp
totp = pyotp.TOTP(os.getenv("DHAN_TOTP_SECRET"))
code = totp.now()  # 6-digit code valid for 30 seconds
```

---

## DhanHQ v2 OAuth Flow (3-Step Consent)

> **Source:** https://dhanhq.co/docs/v2/authentication/

The DhanHQ v2 API supports a proper OAuth-style consent flow for programmatic token generation. This is the recommended approach for production applications that need to authenticate multiple users without manual dashboard interaction.

**Prerequisites:** An API Key + API Secret generated from the Dhan dashboard (see Step 4 above).

### Step 1: Generate Consent

Request a consent ID from Dhan's auth server. This is a server-to-server call (no browser needed).

```
POST https://auth.dhan.co/app/generate-consent?client_id={dhanClientId}
```

| Header       | Value                                |
|-------------|--------------------------------------|
| `app_id`    | Your API Key (from dashboard)        |
| `app_secret`| Your API Secret (UUID from dashboard)|

**Response (success):**
```json
{
  "consentAppId": "abc123-def456-...",
  "consentAppStatus": "GENERATED",
  "status": "success"
}
```

**Rate limit:** Maximum **25 consent IDs per day** per application.

### Step 2: Browser Login (User-Facing)

Redirect the user to Dhan's login page with the consent ID:

```
https://auth.dhan.co/login/consentApp-login?consentAppId={consentAppId}
```

The user completes:
1. Enter Dhan credentials (phone/email + password)
2. Complete 2FA (OTP or TOTP)
3. Approve the consent

On success, Dhan redirects to the configured redirect URL with a `tokenId` query parameter:

```
{redirect_URL}/?tokenId={Token ID}
```

The `redirect_URL` must match the one configured when generating the API Key in Step 4 of the dashboard setup (e.g., `http://localhost:8001/api/auth/dhan/callback`).

### Step 3: Consume Consent

Exchange the `tokenId` for an access token. This is a server-to-server call.

```
POST https://auth.dhan.co/app/consumeApp-consent?tokenId={Token ID}
```

| Header       | Value                                |
|-------------|--------------------------------------|
| `app_id`    | Your API Key                         |
| `app_secret`| Your API Secret                      |

**Response (success):**
```json
{
  "dhanClientId": "1234567890",
  "dhanClientName": "User Name",
  "accessToken": "eyJ0eXAiOiJKV1Q...",
  "expiryTime": "2026-03-21T06:00:00"
}
```

The `accessToken` is valid for **24 hours** (aligned with SEBI guidelines).

### Token Renewal

Renew an **active** (not yet expired) token for another 24 hours:

```
GET https://api.dhan.co/v2/RenewToken
```

| Header         | Value                    |
|---------------|--------------------------|
| `access-token`| Current active token     |
| `dhanClientId`| User's Dhan client ID    |

**Important:** Token renewal only works on tokens that have NOT yet expired. Once expired, a full re-authentication (OAuth flow or TOTP login) is required.

### Direct TOTP Login (Alternative — No Browser Redirect)

For fully headless/automated flows where no browser redirect is possible:

```
POST https://auth.dhan.co/app/generateAccessToken?dhanClientId={clientId}&pin={tradingPin}&totp={totpCode}
```

This generates a 24-hour access token directly without the browser consent flow. Requires:
- `dhanClientId` — numeric user ID
- `pin` — user's trading PIN
- `totp` — current TOTP code (TOTP must be enabled on the Dhan account)

```python
import pyotp
import requests

totp = pyotp.TOTP(os.getenv("DHAN_TOTP_SECRET"))
response = requests.post(
    "https://auth.dhan.co/app/generateAccessToken",
    params={
        "dhanClientId": os.getenv("DHAN_CLIENT_ID"),
        "pin": os.getenv("DHAN_LOGIN_PIN"),
        "totp": totp.now(),
    },
)
access_token = response.json().get("accessToken")
```

### Profile Verification

After obtaining a token, verify it is valid and check account status:

```
GET https://api.dhan.co/v2/profile
```

| Header         | Value                |
|---------------|----------------------|
| `access-token`| The access token     |

Returns user profile data including account setup status, segment permissions, and KYC status.

### Partner Flow (Different Endpoints)

Partners (platforms aggregating multiple users) use separate endpoints with different credentials:

| Step | Individual Endpoint | Partner Endpoint |
|------|-------------------|-----------------|
| Generate consent | `POST /app/generate-consent` | `POST /partner/generate-consent` |
| Browser login | `/login/consentApp-login?consentAppId=...` | `/consent-login?consentId=...` |
| Consume consent | `POST /app/consumeApp-consent?tokenId=...` | `POST /partner/consume-consent?tokenId=...` |

Partner flow uses `partner_id` + `partner_secret` headers instead of `app_id` + `app_secret`.

### Token Validity Summary

| Credential | Validity | Renewal |
|-----------|----------|---------|
| API Key | 12 months (renewable) | Regenerate from dashboard before expiry |
| API Secret | 12 months (same as API Key) | Regenerated with API Key |
| Access Token | 24 hours | `GET /v2/RenewToken` (active tokens only) |

### AlgoChanakya Implementation Note

**Current state:** Uses static token approach — user manually copies `client_id` + `access_token` from the Dhan dashboard. This is implemented in the `DhanAdapter` which accepts these as constructor parameters.

**Gap identified (Gap K):** Should be replaced with proper OAuth consent flow to match the authentication UX of other brokers (Zerodha Kite Connect OAuth, AngelOne TOTP auto-login). The OAuth flow would allow users to click "Connect Dhan" and complete authentication via browser redirect, rather than manually pasting tokens.

**Recommended migration path:**
1. Implement `/api/auth/dhan/initiate` — calls generate-consent, returns redirect URL
2. Implement `/api/auth/dhan/callback` — receives `tokenId`, calls consume-consent, stores encrypted token
3. Add token renewal cron job — calls `/v2/RenewToken` before expiry
4. Keep Direct TOTP Login as fallback for headless/automated scenarios

See `docs/architecture/credential-flow-analysis.md` for the full gap analysis across all brokers.

---

## Token Compatibility: Orders + Market Data

The same `access_token` obtained from Dhan OAuth (or static token) works for BOTH:
- **REST API** (orders, positions, holdings) — Header: `access-token: {token}`, `client-id: {client_id}`
- **WebSocket Live Market Feed** — `wss://api-feed.dhan.co?version=2&token={access_token}&clientId={client_id}&authType=2`

**No separate market data token is needed.** A single access token gives access to everything.

### AlgoChanakya Implication
If a user logs in with Dhan, the `access_token` stored in `broker_connections` can be reused for market data in `broker_api_credentials`. No separate Settings OAuth is needed — the token is copied automatically when the user selects "Use for market data" in Settings.

### Token Renewal
- Token validity: 24 hours
- Can be renewed using `GET /v2/RenewToken` while still active (before expiry)
- Renewal fails on already-expired tokens — user must re-authenticate

Source: https://dhanhq.co/docs/v2/live-market-feed/

---

## API Request Headers

### Required Headers for All Authenticated Requests

| Header         | Value                  | Required |
|----------------|------------------------|----------|
| `access-token` | The API access token   | Yes      |
| `Content-Type` | `application/json`     | Yes (for POST/PUT) |

**Note:** Header name is `access-token` (hyphenated, lowercase), NOT `Authorization: Bearer`.

### Example: Authenticated Request

```python
import requests

DHAN_BASE_URL = "https://api.dhan.co/v2"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOi..."  # From dashboard

headers = {
    "access-token": ACCESS_TOKEN,
    "Content-Type": "application/json",
}

# Get fund limits
response = requests.get(f"{DHAN_BASE_URL}/fundlimit", headers=headers)
print(response.json())
```

### Example: Using aiohttp (Async)

```python
import aiohttp

async def get_fund_limits(access_token: str) -> dict:
    headers = {
        "access-token": access_token,
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.dhan.co/v2/fundlimit",
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
```

---

## AlgoChanakya Integration

### Credential Storage

Dhan credentials are stored in the `broker_credentials` table (or a dedicated `dhan_credentials` table):

| Column         | Type    | Description                              |
|----------------|---------|------------------------------------------|
| `user_id`      | Integer | FK to users table                        |
| `client_id`    | String  | Dhan numeric UID                         |
| `access_token` | String  | Encrypted API token (use `encrypt()`)    |
| `created_at`   | DateTime| When credentials were stored             |
| `updated_at`   | DateTime| Last update timestamp                    |

### Encryption

Always encrypt the access token before storing:

```python
from app.utils.encryption import encrypt, decrypt

# Store
encrypted_token = encrypt(raw_access_token)

# Retrieve
raw_token = decrypt(encrypted_token)
```

### Adapter Authentication

The `DhanAdapter` (both market data and order execution) receives credentials at construction:

```python
from app.services.brokers.factory import get_broker_adapter
from app.services.brokers.market_data.factory import get_market_data_adapter

# Order execution
order_adapter = get_broker_adapter("dhan", {
    "client_id": "1234567890",
    "access_token": "eyJ0eXAiOiJKV1Q...",
})

# Market data
data_adapter = get_market_data_adapter("dhan", {
    "client_id": "1234567890",
    "access_token": "eyJ0eXAiOiJKV1Q...",
})
```

### Token Validation

Dhan does not have a dedicated "validate token" endpoint. To verify a token is valid,
use the v2 profile endpoint (preferred) or fund limit endpoint as a lightweight check:

```python
async def validate_dhan_token(access_token: str) -> bool:
    """Validate Dhan access token by calling a lightweight endpoint."""
    headers = {"access-token": access_token}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.dhan.co/v2/fundlimit",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False
```

---

## Comparison with Other Brokers

| Feature             | Dhan              | Zerodha (Kite)       | Angel One (SmartAPI)   |
|---------------------|-------------------|----------------------|------------------------|
| Auth Type           | OAuth Consent Flow / API Key + Token | OAuth 2.0 | Client + MPIN + TOTP |
| Token Expiry        | **24 hours**      | 1 day (midnight)     | ~8 hours               |
| Permanent Key       | Yes (API Key)     | Yes (API Key)        | Yes (API Key)          |
| Refresh Required    | Daily regen       | Daily re-login       | Auto-TOTP refresh      |
| TOTP Support        | Yes (optional)    | No                   | Yes (required)         |
| Static IP           | Yes (optional)    | No                   | No                     |
| Setup Complexity    | Simple            | Moderate (OAuth)     | Moderate (TOTP setup)  |
| Headers             | `access-token`    | `Authorization`      | `Authorization`        |
| Trading API Cost    | FREE              | FREE                 | FREE                   |
| Data API Cost       | ₹499/mo or 25 trades/mo | ₹500/mo (data) | FREE                  |

---

## Error Handling for Auth

| HTTP Status | Meaning                          | Action                               |
|-------------|----------------------------------|--------------------------------------|
| 401         | Invalid or expired token         | Prompt user to regenerate token      |
| 403         | Token lacks required permissions | Check API permissions on dashboard   |
| 429         | Rate limit exceeded              | Implement backoff (see error-codes)  |

### AlgoChanakya Exception Mapping

```python
from app.services.brokers.market_data.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)

def handle_dhan_auth_error(status_code: int, response_body: dict) -> None:
    if status_code == 401:
        raise AuthenticationError(
            broker="dhan",
            message="Dhan access token is invalid or expired. "
                    "Please regenerate from the Dhan dashboard.",
        )
    elif status_code == 403:
        raise PermissionDeniedError(
            broker="dhan",
            message="Dhan token lacks required permissions.",
        )
    elif status_code == 429:
        raise RateLimitError(
            broker="dhan",
            message="Dhan API rate limit exceeded.",
        )
```

---

## Security Considerations

1. **Never log the access token** -- even partially. Use `token[:8]...` for debugging at most.
2. **Always encrypt at rest** using `app.utils.encryption`.
3. **Do not embed tokens in URLs** -- Dhan uses headers, not query parameters.
4. **Rotate tokens periodically** -- access tokens expire daily, API keys are permanent but can be revoked.
5. **Static IP whitelisting** -- required for order write operations. 7-day cooldown between IP changes.
6. **TOTP secret** -- store securely in `.env`, never commit to git. Enables automated login without SMS OTP.
