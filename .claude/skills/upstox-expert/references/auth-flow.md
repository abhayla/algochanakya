# Upstox Authentication Flow

> Source: [Upstox API Docs](https://upstox.com/developer/api-documentation/open-api) | Last verified: 2026-03-18

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
