---
description: >
  E2E auth convention: import test/expect from auth.fixture.js (not @playwright/test), use
  authenticatedPage fixture. Test files follow .happy/.edge/.api/.audit/.visual/.isolated naming.
globs: ["tests/e2e/**/*.{js,spec.js}"]
synthesized: true
private: false
---

# E2E Auth Fixture and File Naming

## Auth Fixture: Always Import from auth.fixture.js

Every E2E test requiring authentication MUST import `test` and `expect` from the
auth fixture — never from `@playwright/test` directly:

```javascript
// CORRECT:
import { test, expect } from '../../fixtures/auth.fixture.js'

// WRONG:
import { test, expect } from '@playwright/test'  // No auth token injected
```

The fixture provides `authenticatedPage` which has the auth token pre-injected
via `storageState` from global setup.

## Global Setup: Auto-TOTP Login

`tests/e2e/global-setup.js` handles login once before all tests:

1. Checks if cached auth state is still valid (JWT not expired + SmartAPI session alive)
2. If invalid, performs AngelOne/SmartAPI login via direct API call with auto-TOTP
3. Falls back to UI-based login if API login fails
4. Saves auth state to `tests/config/.auth-state.json`
5. Pre-warms SmartAPI instrument cache (~185k instruments, 20-30s)

This means tests NEVER need to log in themselves — auth is always pre-configured.

## Fixture Types

| Fixture | Use When |
|---------|----------|
| `authenticatedPage` | Standard tests that need auth (most tests) |
| `auditablePage` | Tests that need auth + style audit utilities |

## Isolated Tests: Fresh Context

Tests that need a fresh browser context (no auth state) use the `.isolated.spec.js` suffix
and run in the `isolated` Playwright project:

```javascript
// login.isolated.spec.js — tests login flow itself, needs unauthenticated context
import { test, expect } from '@playwright/test'  // OK for isolated tests only

test('shows login page', async ({ page }) => {
  await page.goto('/login')
  // ...
})
```

## File Naming Convention

Test files MUST follow: `{feature}.{type}.spec.js`

| Suffix | Purpose | Tag | Example |
|--------|---------|-----|---------|
| `.happy.spec.js` | Happy path — core user flows work | `@happy` | `optionchain.happy.spec.js` |
| `.edge.spec.js` | Edge cases — error states, boundaries | `@edge` | `autopilot.edge.spec.js` |
| `.api.spec.js` | API integration — response validation | `@api` | `positions.api.spec.js` |
| `.audit.spec.js` | UI consistency — style/a11y checks | `@audit` | `dashboard.audit.spec.js` |
| `.visual.spec.js` | Visual regression — screenshot diffs | `@visual` | `watchlist.visual.spec.js` |
| `.isolated.spec.js` | Fresh context — no auth state | — | `login.isolated.spec.js` |
| `.bugs.spec.js` | Bug regressions — prevents known bugs | — | `strategy.bugs.spec.js` |
| `.consistency.spec.js` | Design system consistency checks | — | `buttons.consistency.spec.js` |

## Running by Type

```bash
npm run test:happy         # All happy path tests
npm run test:edge          # All edge case tests
npm run test:visual        # All visual regression tests
npm run test:audit         # All audit/a11y tests
npm test -- --grep @api    # All API tests
npm run test:isolated      # All isolated (no-auth) tests
```

## MUST NOT

- MUST NOT import from `@playwright/test` in authenticated tests — use `auth.fixture.js`
- MUST NOT add login steps in individual tests — global setup handles authentication
- MUST NOT name spec files without a type suffix — every spec needs `.happy`, `.edge`, etc.
- MUST NOT use `networkidle` in `waitForLoadState` — WebSocket keeps network active
