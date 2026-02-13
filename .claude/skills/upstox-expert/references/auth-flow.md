# Upstox Authentication Flow

Complete OAuth 2.0 authentication sequence for Upstox API v2.

## Overview

Upstox uses **OAuth 2.0 authorization_code** grant with an optional **extended token** for long-lived read-only access.

## Step 1: Redirect to Upstox Login

### Login URL

```
https://api.upstox.com/v2/login/authorization/dialog
  ?client_id={api_key}
  &redirect_uri={redirect_url}
  &response_type=code
```

## Step 2: Receive Authorization Code

After login, Upstox redirects:
```
{redirect_url}?code={authorization_code}
```

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

## Token Validity

```
Login: access_token valid until ~6:30 AM next trading day
       extended_token valid for 1 year
                    ↓
~6:30 AM: access_token expires → must re-do OAuth
           extended_token remains valid for read operations
```

## Common Auth Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401 Unauthorized` | Token expired | Re-authenticate |
| `Invalid redirect_uri` | URL mismatch | Register URL in Upstox dashboard |
| `Invalid code` | Authorization code used/expired | Get new auth code |
| Extended token rejected on order | Read-only token | Use access_token for orders |
