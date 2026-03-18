# Dhan Authentication Flow

## Overview

Dhan has a **dual credential system**: an **API Key + Secret** (permanent, for OAuth-style app registration) and an **Access Token** (24-hour JWT, for API calls). Both are generated from the Dhan trading dashboard (web.dhan.co), NOT the DhanHQ Developer Portal (developer.dhanhq.co).

Dhan also supports **TOTP** for automated login (no SMS OTP needed) and **Static IP whitelisting** for order API security.

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
4. Your **Client ID** is visible on the profile page (numeric, e.g., `1103574530`)

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
6. API Key is a short string (e.g., `44cd031f`)
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

**CRITICAL:** Save the TOTP secret (base32 string like `TVD4U5TNWBXC326UA2Y25MG2CQUS6Z7X`) immediately. It is only shown during setup.

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
DHAN_CLIENT_ID=1103574530
DHAN_ACCESS_TOKEN=eyJ0eXAi...          # 24-hour JWT, must regenerate daily
DHAN_LOGIN_PHONE=7767009136            # For automated login via Playwright
DHAN_LOGIN_PIN=258369                  # Trading PIN for login
DHAN_TOTP_SECRET=TVD4U5TNWBXC326...   # Base32 TOTP secret for auto-OTP
DHAN_API_KEY=44cd031f                  # Permanent API key
DHAN_API_SECRET=89d57475-1e29-...      # Permanent API secret (UUID)
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
totp = pyotp.TOTP("TVD4U5TNWBXC326UA2Y25MG2CQUS6Z7X")
code = totp.now()  # 6-digit code valid for 30 seconds
```

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
make a lightweight call to the profile or fund limit endpoint:

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
| Auth Type           | API Key + Token   | OAuth 2.0            | Client + MPIN + TOTP   |
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
