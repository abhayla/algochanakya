---
description: >
  E2E tests MUST use data-testid selectors only ([screen]-[component]-[element] convention),
  import from auth.fixture.js, and use authenticatedPage fixture.
globs: ["tests/e2e/**/*.{js,spec.js}", "frontend/**/*.vue"]
synthesized: true
private: false
---

# E2E Test Conventions

## Selectors: data-testid ONLY

```javascript
// CORRECT:
await page.locator("[data-testid=positions-exit-modal]").click()

// BLOCKED — no CSS classes, tags, or text:
await page.locator(".btn-primary").click()
await page.locator("button").click()
await page.getByText("Submit").click()
```

## Naming Convention

`data-testid` values follow: `[screen]-[component]-[element]`

Values MUST have at least 3 hyphen-separated lowercase alphanumeric segments
(`[screen]-[component]-[element]` or longer). 2-segment ids like `btn-clear`
are INVALID.

Examples:
- `positions-exit-modal`
- `dashboard-portfolio-card`
- `autopilot-kill-switch-btn`
- `optionchain-strike-row`

Backfill examples (commit 863a9bf) — how to fix 2-segment ids:
- `btn-clear` → `ai-activity-feed-clear-btn`
- `btn-show-more` → `ai-activity-feed-show-more-btn`

### Hook Enforcement

The 3-segment minimum is now BLOCKED deterministically by
`.claude/hooks/guard_testid_pattern.py` (`TESTID_PATTERN` regex, ~line 41) on
Write/Edit of files under `frontend/src/views/` and `frontend/src/components/`.

- Dynamic `:data-testid` bindings bypass the hook (the pattern cannot be
  statically validated) — reviewers MUST check those manually.
- ~55 older files with pre-convention ids are grandfathered until touched;
  fix violations in any element you edit.

## Auth Fixture

MUST import from `auth.fixture.js`, NOT from `@playwright/test`:

```javascript
// CORRECT:
import { authFixture } from "../fixtures/auth.fixture.js"

// WRONG:
import { test } from "@playwright/test"
```

Use the `authenticatedPage` fixture for tests requiring auth:
```javascript
test("shows positions", async ({ authenticatedPage }) => {
  await authenticatedPage.goto("/positions")
  // ...
})
```

## File Organization

- Page objects: `tests/e2e/pages/{Screen}Page.js`
- Specs: `tests/e2e/specs/{screen}/{feature}.{type}.spec.js`
- Types: `.happy.spec.js`, `.edge.spec.js`, `.api.spec.js`, `.audit.spec.js`, `.visual.spec.js`
- Fixtures: `tests/e2e/fixtures/{feature}.fixture.js`

## Adding data-testid to Components

When adding new Vue components, include `data-testid` on all interactive elements:
```vue
<button data-testid="autopilot-activate-btn" @click="activate">
  Activate
</button>
```

