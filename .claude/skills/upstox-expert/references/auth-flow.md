# Upstox Authentication Flow

> Source: [Upstox API Docs](https://upstox.com/developer/api-documentation/open-api) | Last verified: 2026-03-20

Complete OAuth 2.0 authentication sequence for Upstox API.

## Overview

Upstox uses **OAuth 2.0 authorization_code** grant with an optional **extended token** for long-lived read-only access.

---

## Step 1: Redirect to Upstox Login

### Login URL

```
https://api.upstox.com/v2/login/authorization/dialog
  ?client_id={api_key}
  &redirect_uri={redirect_url}
  &response_type=code
```

### Login Page Flow (at login.upstox.com)

Tested via Playwright on 2026-03-18:

1. Enter phone number
2. Click "Get OTP" (or use TOTP if enabled)
3. Enter OTP/TOTP code
4. Enter 6-digit PIN
5. Redirects to `{redirect_url}?code={authorization_code}`

---

## Step 1.5: TOTP Setup (Optional, Enables Auto-Login)

> Verified: 2026-03-18

Upstox supports Time-based OTP (TOTP) as an alternative to SMS OTP. With TOTP enabled, the entire login flow can be automated without SMS dependency.

### Setup Location

account.upstox.com → Profile → sidebar → "Time-based OTP (TOTP)"

### Setup Steps

1. Navigate to TOTP settings page
2. Complete SMS OTP verification (required first)
3. QR code and secret key are displayed
4. Click "Unable to scan? Click to copy the key" to get the base32 secret
5. Enter a generated TOTP code to confirm setup

**Warning:** Enabling TOTP logs out all active sessions.

### Auto-Login Requirements

With TOTP enabled, fully automated OAuth login is possible using:
- API Key (`UPSTOX_API_KEY`)
- API Secret (`UPSTOX_API_SECRET`)
- Phone number (`UPSTOX_LOGIN_PHONE`)
- TOTP secret (`UPSTOX_TOTP_SECRET`)
- 6-digit PIN (`UPSTOX_LOGIN_PIN`)

```python
import pyotp
totp = pyotp.TOTP(os.environ["UPSTOX_TOTP_SECRET"])
code = totp.now()  # 6-digit TOTP code for login
```

### Environment Variables

```env
UPSTOX_API_KEY=your-api-key-uuid
UPSTOX_API_SECRET=your-api-secret
UPSTOX_REDIRECT_URL=http://localhost:8001/api/auth/upstox/callback
UPSTOX_LOGIN_PHONE=your-phone-number
UPSTOX_LOGIN_PIN=your-6-digit-pin
UPSTOX_USER_ID=your-user-id
UPSTOX_TOTP_SECRET=your-totp-base32-secret
```

| Key | Purpose | Where to Find |
|-----|---------|---------------|
| `UPSTOX_API_KEY` | OAuth client_id | My Apps → App Details |
| `UPSTOX_API_SECRET` | OAuth client_secret | My Apps → App Details |
| `UPSTOX_REDIRECT_URL` | OAuth redirect URI | Must match My Apps config exactly |
| `UPSTOX_LOGIN_PHONE` | Auto-login: phone number | Your registered phone |
| `UPSTOX_LOGIN_PIN` | Auto-login: 6-digit PIN | Set during account creation |
| `UPSTOX_USER_ID` | User identifier | Profile page or API profile response |
| `UPSTOX_TOTP_SECRET` | Auto-login: TOTP base32 secret | TOTP setup page (copy key) |

---

## Step 2: Receive Authorization Code

After login, Upstox redirects:
```
{redirect_url}?code={authorization_code}
```

---

## Step 3: Exchange for Access Token

### Request

```http
POST https://api.upstox.com/v2/login/authorization/token
Content-Type: application/x-www-form-urlencoded
Accept: application/json

code={authorization_code}&client_id={api_key}&client_secret={api_secret}&redirect_uri={redirect_url}&grant_type=authorization_code
```

### Successful Response

```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ...",
    "extended_token": "eyJ...",
    "user_id": "AB1234",
    "user_name": "John Doe",
    "user_type": "individual",
    "email": "john@example.com",
    "broker": "UPSTOX",
    "exchanges": ["NSE", "BSE", "NFO", "MCX"],
    "products": ["D", "I", "CO", "OC"],
    "is_active": true
  }
}
```

---

## Step 4: Use Tokens

### REST API

```http
Authorization: Bearer {access_token}
```

### Extended Token (Unique Feature)

```http
Authorization: Bearer {extended_token}
```

Extended token properties:
- **Validity:** 1 year (renewable)
- **Scope:** Read-only (market data, instruments, portfolio view)
- **Cannot:** Place/modify/cancel orders
- **Use case:** Market data adapter that doesn't need daily re-auth

---

## Token Compatibility: Orders + Market Data

The same `access_token` obtained from Upstox OAuth works for BOTH:
- **REST API** (orders, positions, holdings) — `Authorization: Bearer {access_token}`
- **WebSocket Market Feed V3** (live market data streaming) — same token for authentication

**No separate market data token is needed.** A single OAuth flow gives access to everything.

### Important: V3 Migration
Market Data Feeder V2 WebSocket was discontinued on August 22, 2025. All implementations must use V3 WebSocket.

### AlgoChanakya Implication
If a user logs in with Upstox OAuth, the `access_token` stored in `broker_connections` can be reused for market data in `broker_api_credentials`. No separate Settings OAuth is needed — the token is copied automatically when the user selects "Use for market data" in Settings.

### Token Expiry
- Token expires around ~6:30 AM next trading day
- No refresh mechanism — user must re-authenticate daily
- Extended token (1 year) is read-only and cannot be used for orders

Source: https://upstox.com/developer/api-documentation/get-market-data-feed/

---

## Token Validity

```
Login: access_token valid until ~6:30 AM next trading day
       extended_token valid for 1 year
                    ↓
~6:30 AM: access_token expires → must re-do OAuth
           extended_token remains valid for read operations
```

- Access token is a JWT — check the `exp` claim to verify validity
- No refresh token is available from the Upstox API
- Daily re-authentication is required for order execution

---

## Automated Token Refresh Options (Researched March 2026)

Four approaches exist for automated daily token refresh. Listed in order of recommendation.

### Option 1: HTTP-Based TOTP Login (RECOMMENDED)

Pure HTTP flow, no browser needed. Uses Upstox internal login endpoints (6 steps):

| Step | Method | Endpoint | Body / Notes |
|------|--------|----------|--------------|
| 1 | GET | `https://api.upstox.com/v2/login/authorization/dialog?client_id=...&redirect_uri=...&response_type=code` | Follow redirect, extract `user_id` from redirect URL |
| 2 | POST | `https://service.upstox.com/login/open/v6/auth/1fa/otp/generate` | `{"data": {"mobileNumber": phone, "userId": user_id}}` — returns `validateOTPToken` |
| 3 | POST | `https://service.upstox.com/login/open/v4/auth/1fa/otp-totp/verify` | `{"data": {"otp": totp_code, "validateOtpToken": token}}` |
| 4 | POST | `https://service.upstox.com/login/open/v3/auth/2fa` | `{"data": {"twoFAMethod": "SECRET_PIN", "inputText": base64_encoded_pin}}` |
| 5 | POST | `https://service.upstox.com/login/v2/oauth/authorize` | `{"data": {"userOAuthApproval": true}}` — extract `code` from redirect |
| 6 | POST | `https://api.upstox.com/v2/login/authorization/token` | Standard OAuth code exchange (same as Step 3 above) |

**Advantages:** No browser binary, fast (~2-3 seconds), reliable, no UI breakage risk.
**Requires:** `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`, `UPSTOX_REDIRECT_URL`, `UPSTOX_LOGIN_PHONE`, `UPSTOX_LOGIN_PIN`, `UPSTOX_TOTP_SECRET`

### Option 2: V3 Access Token Request API (Push Notification)

Uses Upstox push notification mechanism:

```
POST https://api.upstox.com/v3/login/auth/token/request/{client_id}
Body: { "client_secret": "..." }
```

- Sends push notification to user's Upstox app + WhatsApp
- User must approve manually on their device
- Token delivered to a webhook URL configured in the app
- **NOT fully automated** — requires human approval each time
- Useful for multi-user platforms where each user approves their own token

### Option 3: Playwright/Selenium Browser Automation (Legacy)

Headless browser fills in the login forms programmatically:
- Uses Playwright or Selenium to navigate login.upstox.com
- Fills phone, TOTP code, PIN in sequence
- Extracts authorization code from redirect URL
- **Fragile** — breaks when Upstox changes their login UI
- **Heavy** — requires browser binary (Chromium) on server
- **Superseded** by Option 1 (HTTP-based approach)

### Option 4: upstox-totp Python Package (Third-Party)

`pip install upstox-totp` — third-party library implementing the same HTTP-based flow as Option 1.

- Source: https://github.com/batpool/upstox-totp
- Docs: https://upstox-totp.readthedocs.io
- Uses `curl_cffi` with Chrome impersonation to avoid bot detection
- Convenient if you want a pre-built solution, but adds an external dependency
- AlgoChanakya uses its own implementation (Option 1) instead

### AlgoChanakya Implementation

The HTTP-based approach (Option 1) is implemented in AlgoChanakya:

| Component | Location |
|-----------|----------|
| Auth class | `backend/app/services/brokers/platform_token_refresh.py` — `UpstoxHttpAuth` class |
| Startup hook | Called automatically on backend startup via `main.py` lifespan |
| Token storage | Saved to `.env` as `UPSTOX_ACCESS_TOKEN` and updated in-memory via `os.environ` |

**Flow on backend startup:**
1. `UpstoxHttpAuth` reads credentials from environment
2. Executes the 6-step HTTP login flow
3. Saves new `access_token` to `.env` file and updates `os.environ`
4. Platform market data adapter picks up the fresh token automatically

---

## Sandbox Tokens (Jan 2025+)

For testing without real money:
1. Create a "Sandbox" app in Upstox developer portal (separate from production app)
2. Generate a **30-day token** directly from the portal — no OAuth flow needed
3. Use this token with the same base URL `https://api.upstox.com`
4. **Scope:** Order placement, modification, cancellation only (no market data sandbox)
5. Token is valid 30 days; regenerate from portal when expired

---

## Access Token Flow for Users (Beta, Jan 2025)

For multi-client applications (platform serving multiple users):
- Allows generating tokens for multiple users without individual OAuth
- Requires special app type approval from Upstox
- Contact Upstox developer support to enable

---

## IP Whitelisting

> **Critical for production deployments:** Without IP whitelisting, order placement returns `403 Forbidden`.

1. Go to Upstox developer portal → My Apps → your app → Settings
2. Add your server's public IP address to the whitelist
3. Changes take effect within minutes
4. **Common mistake:** Dynamic IPs (cloud auto-scaling, VPN) — whitelist entire CIDR range or use static IP

---

## Common Auth Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401 Unauthorized` | Token expired | Re-authenticate (access_token) |
| `Invalid redirect_uri` | URL mismatch | Register exact URL in Upstox dashboard |
| `Invalid code` | Authorization code used/expired | Get new auth code (each code is single-use) |
| Extended token rejected on order | Read-only token | Use access_token for orders |
| `403 Forbidden` on order | IP not whitelisted | Add server IP to My Apps → IP Whitelist |
| `UDAPI100050` on valid order | Post-reauth session issue | Re-authenticate fully, retry |
| `UDAPI100014` | Wrong api_key or secret | Verify credentials in My Apps |
