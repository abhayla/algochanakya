# Kite Connect App Setup Guide

Step-by-step guide for creating a Kite Connect app on the Zerodha developer portal for OAuth login in AlgoChanakya.

## Prerequisites

- A Zerodha trading account (Client ID, e.g., DA1707)
- Account on the Kite Connect developer portal: https://developers.kite.trade

## Step 1: Log in to Developer Portal

1. Go to https://developers.kite.trade
2. Enter your email and password (this is your Kite Connect developer account, may differ from your Kite trading login)
3. If you don't have an account, click "Signup" to create one

## Step 2: Create a New App

1. Click **"Create new app"** on the My Apps page
2. Fill in the form:

| Field | Value | Notes |
|-------|-------|-------|
| **Type** | **Personal** (Free) | Sufficient for OAuth login + order execution. "Connect" (₹500/month) only needed for historical data + WebSocket from Zerodha |
| **App name** | `AlgoChanakya Dev` | Must be unique across your apps. If "AlgoChanakya" is taken (by a cancelled app), use a variant |
| **Zerodha Client ID** | Your Kite Client ID (e.g., `DA1707`) | The app is restricted to this single user ID. For multi-user, email Zerodha |
| **Redirect URL** | `http://localhost:8001/api/auth/zerodha/callback` | For local development. Production: `https://algochanakya.com/api/auth/zerodha/callback` |
| **Postback URL** | (leave empty) | Optional — for real-time order status updates via webhook |
| **Description** | `Multi-broker options trading platform for Indian markets` | Required field |

3. Click **"Create"**

### Which App Type to Choose?

| Type | Cost | Use Case |
|------|------|----------|
| **Personal** | FREE | OAuth login + order execution APIs. **This is what AlgoChanakya needs for login.** |
| **Connect** | ₹500/month | Everything in Personal + historical chart data + live market quotes via WebSocket. Only needed if using Zerodha as market data source |
| **Publisher** | FREE | HTML/JS order buttons only. No API access. **NOT suitable for AlgoChanakya** |

**Recommendation:** Use **Personal (Free)** unless you specifically need Zerodha market data (AlgoChanakya uses SmartAPI for market data by default).

## Step 3: Get API Key and Secret

After creating the app:

1. You'll be redirected to the "My Apps" page showing your new app as **Active**
2. Click on the app name to open its details
3. Note the **API Key** (shown directly, e.g., `pp2fa8b4e0uta9ne`)
4. Click **"Show API secret"** to reveal the API Secret (e.g., `of90r1f3qy52ctaen7l1vryl8o5v71ad`)
5. If you need a new secret later, click **"Re-generate API secret"** (old secret stops working immediately)

## Step 4: Save to .env

Update `backend/.env` with the new credentials:

```bash
# ── Zerodha (Kite Connect) ────────────────────────────────────────────────────
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here
KITE_REDIRECT_URL=http://localhost:8001/api/auth/zerodha/callback
```

**Important:** Restart the backend after updating `.env` for changes to take effect.

## Step 5: Verify

1. Start the backend: `cd backend && python run.py`
2. Start the frontend: `cd frontend && npm run dev`
3. Go to http://localhost:5173/login
4. Select "Zerodha" from the dropdown → Click "Login with Zerodha"
5. You should be redirected to `kite.zerodha.com/connect/login?api_key=YOUR_KEY`
6. The Zerodha login page should show "Login to {Your App Name}"
7. Enter your Zerodha trading password → Complete login
8. You should be redirected back to the AlgoChanakya dashboard

## Managing Your App

### App Settings (on the app details page)

| Setting | Description |
|---------|-------------|
| **Redirect URL** | Change when deploying to production |
| **Status** | Active/Paused — paused apps stop working |
| **Re-generate API secret** | Creates new secret, old one invalidated immediately |
| **Delete this app** | Permanent deletion — requires typing "I UNDERSTAND" |

### Changing Redirect URL for Production

When deploying to production, update the Redirect URL on the Kite developer portal:

1. Go to https://developers.kite.trade/apps → Click your app
2. Change Redirect URL to: `https://algochanakya.com/api/auth/zerodha/callback`
3. Click **Save**
4. Update `KITE_REDIRECT_URL` in production `.env` to match

### SEBI Static IP Requirement (April 2026+)

Starting April 1, 2026, API orders not placed from a registered static IP will be rejected per SEBI regulations. Register your static IP:

1. Go to https://developers.kite.trade/profile
2. Add your server's static IP address
3. For local development, this may not apply (check latest SEBI guidelines)

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "Invalid api_key" on Kite login page | API key expired or app cancelled | Create new app or check status on developer portal |
| "App with same name already exists" | Cancelled app still holds the name | Use a different name (e.g., add "Dev" suffix) |
| Redirect URL mismatch | URL in code doesn't match portal | Ensure `KITE_REDIRECT_URL` matches exactly what's registered |
| Old API key still used after .env update | Backend using cached config | Restart the backend process completely |
| App shows "Cancelled" | Subscription expired (for Connect type) or manually cancelled | Create a new app — cancelled apps cannot be reactivated |

## App Types Comparison

| Feature | Personal (Free) | Connect (₹500/mo) |
|---------|----------------|-------------------|
| OAuth Login | Yes | Yes |
| Place/Modify/Cancel Orders | Yes | Yes |
| Portfolio/Positions/Holdings | Yes | Yes |
| Historical Chart Data | **No** | Yes |
| Live Market Quotes (REST) | **No** | Yes |
| WebSocket (KiteTicker) | **No** | Yes |
| GTT Orders | Yes | Yes |
