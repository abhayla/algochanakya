---
name: add-e2e-test-screen
description: >
  Add E2E tests for a new screen with page objects, fixtures, and proper
  auth setup following the project test conventions.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<screen-name>"
version: "1.0.0"
synthesized: true
private: false
---

# Add E2E Test Screen

## STEP 1: Create Page Object

Create `tests/e2e/pages/<Screen>Page.js` extending BasePage:

```javascript
import { BasePage } from './BasePage.js'

export class <Screen>Page extends BasePage {
  constructor(page) {
    super(page)
    this.mainContent = '[data-testid=<screen>-main]'
    // Define selectors using data-testid only
  }

  async navigate() {
    await this.page.goto('/<screen>')
  }
}
```

## STEP 2: Create Spec Directory

Create `tests/e2e/specs/<screen>/` with test files following naming convention:
- `<screen>.happy.spec.js` -- happy path tests
- `<screen>.edge.spec.js` -- edge cases
- `<screen>.api.spec.js` -- API integration tests
- `<screen>.audit.spec.js` -- accessibility audits
- `<screen>.visual.spec.js` -- visual regression

## STEP 3: Write Tests with Auth Fixture

```javascript
import { authFixture } from '../../fixtures/auth.fixture.js'
// NEVER import from @playwright/test directly

test('shows main content', async ({ authenticatedPage }) => {
  const screenPage = new <Screen>Page(authenticatedPage)
  await screenPage.navigate()
  await expect(authenticatedPage.locator('[data-testid=<screen>-main]')).toBeVisible()
})
```

## STEP 4: Add data-testid to Components

In Vue components, add data-testid to all interactive and key display elements:
```vue
<div data-testid="<screen>-<component>-<element>">
```

## STEP 5: Add npm Script

In root `package.json`, add:
```json
"test:specs:<screen>": "npx playwright test tests/e2e/specs/<screen>/"
```

## STEP 6: Create Fixture (if needed)

For complex mock data, create `tests/e2e/fixtures/<screen>.fixture.js`.

## CRITICAL RULES

- ONLY data-testid selectors (no CSS classes, tags, or text)
- Import from auth.fixture.js, NEVER from @playwright/test
- Use authenticatedPage fixture for authenticated tests
- data-testid naming: [screen]-[component]-[element]
- Place specs in screen subdirectory, never at specs root
