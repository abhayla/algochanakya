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
