---
description: >
  Frontend API interceptor distinguishes auth endpoint 401 (triggers logout) from broker
  endpoint 401 (preserves app session). Prevents false logouts on stale broker credentials.
globs: ["frontend/src/services/**/*.js", "frontend/src/stores/auth.js"]
synthesized: true
private: true
---

# 401 Response Handling Strategy

## The Problem

The app connects to multiple brokers (Zerodha, AngelOne, Upstox, etc.) whose
sessions expire independently of the app's JWT. A 401 from a broker endpoint
(e.g., `/api/optionchain/...`) means "broker credentials expired" — NOT
"user is logged out."

Treating all 401s as "logout" would kick users out whenever a single broker
session expires, even though their app JWT is still valid.

## The Rule: Auth 401 vs Broker 401

The Axios response interceptor in `frontend/src/services/api.js` distinguishes:

| Endpoint pattern | 401 means | Action |
|-----------------|-----------|--------|
| `/api/auth/*` | JWT expired/invalid | **Logout**: clear token, redirect to `/login` |
| `/api/user/*` | JWT expired/invalid | **Logout**: clear token, redirect to `/login` |
| All other endpoints | Broker session expired | **Preserve session**: reject promise, let UI handle |

```javascript
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || ''
      const isAuthEndpoint = url.includes('/api/auth/') || url.includes('/api/user/')
      if (isAuthEndpoint) {
        localStorage.removeItem('access_token')
        window.location.href = '/login'
      }
      // Broker 401s: just reject — component shows "broker session expired" message
    }
    return Promise.reject(error)
  }
)
```

## When Adding New Endpoints

New backend endpoints that use the app JWT for authentication (not broker tokens)
MUST be added to the `isAuthEndpoint` check if their 401 means "app auth failed."

Endpoints that proxy to broker APIs (market data, orders, positions) MUST NOT
trigger logout on 401 — their 401 means "broker credentials need refresh."

## MUST NOT

- MUST NOT add blanket 401→logout handling — it breaks multi-broker session management
- MUST NOT treat broker 401 as app auth failure — they are independent sessions
- MUST NOT silently swallow broker 401 errors — let the UI show a re-authentication prompt
- MUST NOT remove the `isAuthEndpoint` check in api.js without understanding this pattern
