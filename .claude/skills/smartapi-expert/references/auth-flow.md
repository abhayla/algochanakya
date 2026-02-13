# SmartAPI Authentication Flow

Complete authentication sequence for Angel One SmartAPI with auto-TOTP.

## Overview

SmartAPI uses a **3-token system**:
1. **JWT Token** (`jwtToken`) - For all REST API calls
2. **Feed Token** (`feedToken`) - For WebSocket authentication
3. **Refresh Token** (`refreshToken`) - To refresh expired JWT

Authentication requires: `client_id` (Angel One login ID), `password` (PIN), and `TOTP` (auto-generated).

## Step 1: Generate TOTP

AlgoChanakya uses **auto-TOTP** via the `pyotp` library. The TOTP secret is stored encrypted in the `smartapi_credentials` database table.

```python
import pyotp

# TOTP secret stored encrypted in smartapi_credentials table
totp_secret = decrypt(stored_encrypted_totp_secret)
totp_code = pyotp.TOTP(totp_secret).now()  # 6-digit code, valid 30 seconds
```

**Important:** System clock must be NTP-synced. TOTP codes have a 30-second window. Clock drift >30s causes authentication failure.

## Step 2: Login

### Request

```http
POST https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword
Content-Type: application/json
Accept: application/json
X-UserType: USER
X-SourceID: WEB
X-ClientLocalIP: {client_ip}
X-ClientPublicIP: {public_ip}
X-MACAddress: {mac_address}
X-PrivateKey: {api_key}

{
  "clientcode": "A12345",
  "password": "1234",
  "totp": "123456"
}
```

### Required Headers

| Header | Value | Notes |
|--------|-------|-------|
| `Content-Type` | `application/json` | Required |
| `Accept` | `application/json` | Required |
| `X-UserType` | `USER` | Fixed value |
| `X-SourceID` | `WEB` | Fixed value |
| `X-ClientLocalIP` | Client's local IP | e.g., `192.168.1.100` |
| `X-ClientPublicIP` | Client's public IP | e.g., `203.0.113.1` |
| `X-MACAddress` | Client's MAC address | e.g., `00:1B:44:11:3A:B7` |
| `X-PrivateKey` | API key | From Angel One dashboard |

### Successful Response (200)

```json
{
  "status": true,
  "message": "SUCCESS",
  "errorcode": "",
  "data": {
    "jwtToken": "eyJhbGciOiJIUzUxMiJ9...",
    "refreshToken": "eyJhbGciOiJIUzUxMiJ9...",
    "feedToken": "eyJhbGciOiJIUzUxMiJ9..."
  }
}
```

### Error Responses

| Error Code | Message | Cause |
|-----------|---------|-------|
| `AG8001` | Invalid Token | API key invalid |
| `AG8002` | Invalid Client Code | Wrong client ID |
| `AG8003` | Invalid TOTP | Expired/wrong TOTP code |
| `AB1012` | Session expired | Previous session issue |

## Step 3: Use Tokens

### REST API Calls

```http
GET https://apiconnect.angelbroking.com/rest/secure/angelbroking/user/v1/getProfile
Authorization: Bearer {jwtToken}
Content-Type: application/json
X-UserType: USER
X-SourceID: WEB
X-ClientLocalIP: {client_ip}
X-ClientPublicIP: {public_ip}
X-MACAddress: {mac_address}
X-PrivateKey: {api_key}
```

### WebSocket Connection

```
wss://smartapisocket.angelone.in/smart-stream
  ?clientCode={client_id}
  &feedToken={feed_token}
  &apiKey={api_key}
```

## Step 4: Token Refresh

When JWT expires (~24 hours), use the refresh token:

### Request

```http
POST https://apiconnect.angelbroking.com/rest/auth/angelbroking/jwt/v1/generateTokens
Content-Type: application/json
Authorization: Bearer {expired_jwtToken}
X-PrivateKey: {api_key}

{
  "refreshToken": "eyJhbGciOiJIUzUxMiJ9..."
}
```

### Response

```json
{
  "status": true,
  "message": "SUCCESS",
  "data": {
    "jwtToken": "eyJhbGciOiJIUzUxMiJ9...(new)",
    "refreshToken": "eyJhbGciOiJIUzUxMiJ9...(new)",
    "feedToken": "eyJhbGciOiJIUzUxMiJ9...(new)"
  }
}
```

**Note:** Refresh token is valid for 15 days. After that, full re-login required.

## Step 5: Logout

```http
POST https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/logout
Content-Type: application/json
Authorization: Bearer {jwtToken}
X-PrivateKey: {api_key}

{
  "clientcode": "A12345"
}
```

## AlgoChanakya Implementation

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/services/legacy/smartapi_auth.py` | Auth with auto-TOTP |
| `backend/app/api/routes/smartapi.py` | Auth API endpoints |
| `backend/app/utils/encryption.py` | Credential encryption |
| `frontend/src/components/settings/SmartAPISettings.vue` | Credentials UI |

### Credential Storage

Credentials are stored in `smartapi_credentials` table, encrypted with AES:

```python
from app.utils.encryption import encrypt, decrypt

# Store
encrypted_password = encrypt(user_password)
encrypted_totp = encrypt(totp_secret)

# Retrieve
password = decrypt(encrypted_password)
totp_secret = decrypt(encrypted_totp)
```

### Authentication Flow in Codebase

```python
# backend/app/services/legacy/smartapi_auth.py (simplified)
class SmartAPIAuth:
    async def authenticate(self, client_id: str, password: str, totp_secret: str):
        # 1. Generate TOTP
        totp = pyotp.TOTP(totp_secret).now()

        # 2. Create SmartConnect instance
        obj = SmartConnect(api_key=self.api_key)

        # 3. Login
        data = obj.generateSession(client_id, password, totp)

        # 4. Extract tokens
        jwt_token = data['data']['jwtToken']
        feed_token = data['data']['feedToken']
        refresh_token = data['data']['refreshToken']

        return jwt_token, feed_token, refresh_token
```

### Common Auth Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `AG8003` Invalid TOTP | Clock drift or wrong secret | Sync NTP, verify TOTP secret |
| Login takes 25+ seconds | Normal - SmartAPI is slow | Set axios timeout to 35000ms |
| `AG8001` after hours | JWT expired (24h validity) | Auto-refresh via refresh token |
| Auth works in Postman but not code | Missing required headers | Add all X- headers |
| TOTP always fails | TOTP secret is base32-encoded wrong | Re-scan QR code, store raw base32 |

## Token Validity Timeline

```
Hour  0: Login → jwt (24h), feed (24h), refresh (15 days)
Hour 24: JWT expires → use refresh token
Hour 48: New JWT via refresh → valid 24h more
...
Day  15: Refresh token expires → full re-login required
```

## Security Notes

- Never log or expose tokens in console/responses
- Store TOTP secret encrypted at rest (AES)
- API key should be in environment variables, not in code
- Refresh tokens should be stored securely (not in localStorage)
- Rate limit auth attempts to prevent TOTP enumeration
