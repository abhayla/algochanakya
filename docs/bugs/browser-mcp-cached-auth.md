# Bug: Playwright MCP browser auto-logs-in via cached E2E test auth

**Date logged:** 2026-04-17
**Severity:** Low (dev-experience)
**Area:** E2E / MCP browser integration

## Symptom

When opening the app via Playwright MCP (e.g., `mcp__playwright__browser_navigate`
to `http://localhost:5173/login`), the browser **auto-redirects to `/dashboard`**
instead of presenting the login screen. This blocks any flow that requires
picking a specific broker (Zerodha / AngelOne / etc.) interactively.

## Root Cause

`tests/config/.auth-state.json` contains a valid JWT in `localStorage.access_token`
(written by `tests/e2e/global-setup.js`). The Playwright MCP browser appears to
inherit this storage state from the shared user-data-dir, so the app's
`router.beforeEach` guard sees a token and skips `/login`.

```json
// tests/config/.auth-state.json
{
  "origins": [{
    "origin": "http://localhost:5173",
    "localStorage": [{ "name": "access_token", "value": "eyJhbGciOi..." }]
  }]
}
```

The token has a ~24h expiry (`exp: 1776402134`), so it stays valid through
multiple MCP sessions until global-setup rewrites it.

## Expected Behavior

When using MCP browser for manual testing (not E2E suite execution), the
browser should start with a clean storage state so the user can pick a broker
and log in fresh.

## Workarounds

1. **Clear localStorage before navigating:**
   ```js
   await page.evaluate(() => localStorage.clear())
   await page.goto('/login')
   ```
2. Delete `tests/config/.auth-state.json` before manual testing (global-setup
   will re-create it next E2E run).
3. Use a separate Playwright MCP profile for manual vs E2E runs.

## Fix Ideas

- Scope the cached auth state to the Playwright test project only
  (`storageState` in `playwright.config.js`), not the MCP user profile.
- Add a `clear-session` helper or `/logout` shortcut to the MCP workflow.
- Teach the app's router to always show `/login` when URL is explicitly `/login`
  (bypass auth guard on that route even when token exists).

## Related

- `tests/e2e/global-setup.js` — writes the auth-state.json
- `frontend/src/router/index.js` — auth guard that redirects `/login` → `/dashboard`
- `frontend/src/services/api.js` — JWT interceptor
