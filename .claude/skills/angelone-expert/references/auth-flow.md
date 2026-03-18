# SmartAPI Authentication Flow

Complete authentication sequence for Angel One SmartAPI with auto-TOTP.

## Overview

SmartAPI uses a **3-token system**:
1. **JWT Token** (`jwtToken`) - For all REST API calls
2. **Feed Token** (`feedToken`) - For WebSocket authentication
3. **Refresh Token** (`refreshToken`) - To refresh expired JWT

Authentication requires: `client_id` (Angel One login ID), `password` (PIN), and `TOTP` (auto-generated).

## Step 1: Generate TOTP

AlgoChanakya uses **auto-TOTP** via the `pyotp` library. **Confirmed fully working as of 2026-03-18** -- no manual input needed for login. The TOTP secret is stored both encrypted in the `smartapi_credentials` database table and in `backend/.env` as `ANGEL_TOTP_SECRET`.

```python
import pyotp

# Option 1: From .env (used by smartapi_auth.py)
totp_code = pyotp.TOTP(os.environ["ANGEL_TOTP_SECRET"]).now()  # 6-digit code, valid 30 seconds

# Option 2: From encrypted DB storage
totp_secret = decrypt(stored_encrypted_totp_secret)
totp_code = pyotp.TOTP(totp_secret).now()
```

**Required `.env` keys for auto-login:**
```
ANGEL_CLIENT_ID=your-angelone-client-id
ANGEL_PIN=your-angelone-trading-pin
ANGEL_TOTP_SECRET=your-angelone-totp-base32-secret
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

## Static IP Registration (Required Since Aug 2025)

Since August 2025, Angel One requires all API keys to have registered static IP addresses. API calls from unregistered IPs return **HTTP 403 Forbidden**.

### Setup Steps

1. Log in to the Angel One developer portal: https://smartapi.angelbroking.com/
2. Navigate to **My Apps** → select your app
3. Go to **API Key Settings** → **IP Whitelist**
4. Add your server's public IPv4 address (up to 5 IPs per API key)
5. Save and wait up to 5 minutes for propagation

### Finding Your Server's Public IP

```bash
# On the server running AlgoChanakya backend
curl -s https://api.ipify.org
# or
curl -s https://ifconfig.me
```

### Error When IP Not Registered

```json
HTTP 403 Forbidden
{
  "status": false,
  "message": "IP address not authorized",
  "errorcode": "AG8008",
  "data": null
}
```

### Key Notes

- Up to **5 IPv4 addresses** can be registered per API key
- IPv6 addresses are not supported — register the IPv4 address only
- Dynamic IPs (home internet, cloud instances with changing IPs) require updating the whitelist on each IP change
- For cloud deployments (AWS EC2, GCP, Azure): use an Elastic/Static IP
- For AlgoChanakya dev environment: register your development machine's public IP separately from the production server IP
- Changes take effect within 5 minutes

### AlgoChanakya Impact

Both dev and production environments need their IPs registered:
- Dev machine public IP → register for dev API key
- Production server IP (`103.118.16.189` or similar) → register for production API key
- If using separate API keys per environment, each key needs its own whitelist

**CRITICAL: IP whitelist is per-app, not global.** AlgoChanakya uses 3 separate apps (`AlgoChanakyaLive`, `AlgoChanakyaHist`, `AlgoChanakyaTrade`). You must whitelist the server IP in **all 3 apps** separately:
- `AlgoChanakyaLive` (ANGEL_API_KEY) → add server IP → for live quotes + WebSocket
- `AlgoChanakyaHist` (ANGEL_HIST_API_KEY) → add server IP → for `getCandleData`
- `AlgoChanakyaTrade` (ANGEL_TRADE_API_KEY) → add server IP → for `placeOrder`, `cancelOrder`, etc.

Symptom of missing IP in one app: `generateSession` succeeds (login is not IP-restricted) but data/order endpoints return AG8001 or HTTP 403. If historical or order endpoints fail but market data works, the hist/trade app is missing the IP whitelist entry.

## AngelOne 3-API-Key Architecture (AlgoChanakya)

AngelOne provides **separate API keys** for different data domains. AlgoChanakya uses 3 distinct keys:

| `.env` Variable | Purpose | Endpoints Used |
|----------------|---------|----------------|
| `ANGEL_API_KEY` | Live market data (WebSocket ticks, live quotes) | `ltpData`, `getMarketData`, SmartConnect WebSocket |
| `ANGEL_HIST_API_KEY` | Historical candle data | `getCandleData` ONLY |
| `ANGEL_TRADE_API_KEY` | Order execution | `placeOrder`, `cancelOrder`, `orderBook`, `position`, `rmsLimit`, `getProfile` |

### Critical Rule: JWT is Bound to the API Key Used for Login

When you call `loginByPassword` with `X-PrivateKey: KEY_A`, the returned JWT is **tied to KEY_A**. Any subsequent request using that JWT must also set `X-PrivateKey: KEY_A`. Using the JWT from one key with a different key's `X-PrivateKey` header returns **AG8001 Invalid Token**.

```python
# CORRECT — authenticate with hist key, use hist key for all historical calls
hist_client = SmartConnect(api_key=ANGEL_HIST_API_KEY)
session = hist_client.generateSession(client_id, pin, totp)
hist_jwt = session['data']['jwtToken']
# Now getCandleData calls use hist_client (X-PrivateKey = ANGEL_HIST_API_KEY)

# WRONG — authenticate with market key, then call historical with hist key
market_client = SmartConnect(api_key=ANGEL_API_KEY)
session = market_client.generateSession(client_id, pin, totp)
market_jwt = session['data']['jwtToken']
# getCandleData with hist_client + market_jwt → AG8001 (key mismatch)
```

### AlgoChanakya Implementation

- `SmartAPIMarketDataAdapter.__init__()` → uses `ANGEL_API_KEY` for `SmartAPIMarketData` (live quotes)
- `SmartAPIMarketDataAdapter.__init__()` → uses `ANGEL_HIST_API_KEY` for `SmartAPIHistorical`
- `AngelOneAdapter.initialize()` → uses `ANGEL_TRADE_API_KEY` for order execution
- `conftest.py` `angelone_credentials` → exposes `api_key`, `hist_api_key`, `trade_api_key`

## SmartAPI App Types (CRITICAL for AG8001 on historical/order endpoints)

AngelOne has **4 app types** when creating an app. The type determines which endpoints the API key can access. **This is the root cause of AG8001 on getCandleData and placeOrder.**

| App Type | getCandleData | placeOrder/cancelOrder | Live quotes/WebSocket |
|----------|:---:|:---:|:---:|
| **Market Feeds API** | ❌ | ❌ | ✅ |
| **Historical Data API** | ✅ | ❌ | ❌ |
| **Publisher API** | ❌ | ✅ (embedded) | ❌ |
| **Trading API** | ✅ | ✅ | ✅ |

**Trading API** is the **only type that grants all 3 capabilities** in a single API key.

### Recommended App Setup for AlgoChanakya

Create **1 app of type "Trading API"** to get a single API key that covers everything:
- Historical data (`getCandleData`)
- Order execution (`placeOrder`, `cancelOrder`, `orderBook`, `position`, `rmsLimit`)
- Live market data (WebSocket, `ltpData`, `getMarketData`)

Or create **2 separate apps** matching the current AlgoChanakya `.env` separation:
- `ANGEL_API_KEY` → **Market Feeds API** app (live quotes + WebSocket)
- `ANGEL_HIST_API_KEY` → **Historical Data API** app (getCandleData)
- `ANGEL_TRADE_API_KEY` → **Trading API** app (orders)

### How to Create / Change an App Type

1. Log in at https://smartapi.angelbroking.com/
2. Click your profile → **My Apps**
3. To create new: click **+ Create App** → choose app type → fill App Name, Redirect URL, Client ID
4. **You CANNOT change the type of an existing app** — you must create a new app with the correct type and use its API key
5. After creation, copy the new API key and update `ANGEL_HIST_API_KEY` or `ANGEL_TRADE_API_KEY` in `backend/.env`
6. Register the server's IP in the new app's IP Whitelist (required since Aug 2025)

### Diagnosing Which App Type Your Existing Keys Are

There is no API to query app type. Go to https://smartapi.angelbroking.com/ → My Apps → the app type is shown on each app card. If `ANGEL_HIST_API_KEY` belongs to a "Market Feeds API" app, it **cannot** call getCandleData.

## Security Notes

- Never log or expose tokens in console/responses
- Store TOTP secret encrypted at rest (AES)
- API key should be in environment variables, not in code
- Refresh tokens should be stored securely (not in localStorage)
- Rate limit auth attempts to prevent TOTP enumeration
- Register only known, stable server IPs — avoid wildcards or broad ranges
