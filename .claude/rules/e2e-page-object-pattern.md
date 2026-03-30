---
description: >
  All E2E tests MUST use page objects extending BasePage. Page objects provide getByTestId,
  navigate, waitForTestId helpers. Specs MUST NOT use raw Playwright locators.
globs: ["tests/e2e/**/*.{js,spec.js}"]
synthesized: true
private: false
---

# E2E Page Object Pattern

## BasePage Contract

All page objects extend `BasePage` from `tests/e2e/pages/BasePage.js`:

```javascript
import { BasePage } from './BasePage.js'

export class OptionChainPage extends BasePage {
  constructor(page) {
    super(page, '/optionchain')  // URL for navigate()
  }

  // Selectors as getters
  get spotPrice() { return this.getByTestId('optionchain-spot-price') }
  get expiryTabs() { return this.getByTestId('optionchain-expiry-tabs') }

  // Actions wrap multiple interactions
  async selectUnderlying(name) {
    await this.getByTestId(`underlying-tabs-${name}`).click()
    await this.waitForTestId('optionchain-chain-table')
  }
}
```

## BasePage Helpers

| Method | Purpose |
|--------|---------|
| `navigate()` | Goes to page URL, waits for `domcontentloaded` |
| `getByTestId(id)` | Returns `page.locator('[data-testid=...]')` |
| `waitForTestId(id)` | Waits for element + returns locator |
| `clickTestId(id)` | Click by test ID |
| `assertVisible(id)` | Assert element is visible |
| `assertHidden(id)` | Assert element is hidden |
| `screenshot(name)` | Capture named screenshot |

## MUST Use `domcontentloaded`, NOT `networkidle`

`navigate()` waits for `domcontentloaded`, not `networkidle`. This is intentional —
WebSocket connections keep the network permanently active, so `networkidle` would
timeout every time.

## Spec Files: Page Objects Only

```javascript
// CORRECT — uses page object:
import { test, expect } from '../../fixtures/auth.fixture.js'
import { OptionChainPage } from '../../pages/OptionChainPage.js'

test.describe('Option Chain - Happy Path', () => {
  let page

  test.beforeEach(async ({ authenticatedPage }) => {
    page = new OptionChainPage(authenticatedPage)
    await page.navigate()
  })

  test('displays spot price', async () => {
    await expect(page.spotPrice).toBeVisible()
  })
})

// WRONG — raw locators in spec:
test('displays spot price', async ({ page }) => {
  await page.locator('[data-testid=optionchain-spot-price]').waitFor()  // NEVER
})
```

## Page Object per Screen

Each screen in the app gets its own page object:

| Screen | Page Object |
|--------|-------------|
| Option Chain | `OptionChainPage.js` |
| Strategy Builder | `StrategyBuilderPage.js` |
| AutoPilot Dashboard | `AutoPilotDashboardPage.js` |
| Positions | `PositionsPage.js` |
| Login | `LoginPage.js` |

## Adding a New Page Object

1. Create `tests/e2e/pages/{Screen}Page.js` extending `BasePage`
2. Define URL in `super(page, '/path')`
3. Add selectors as getters using `getByTestId()`
4. Add action methods for multi-step interactions
5. Import and use in spec files

## MUST NOT

- MUST NOT use `page.locator()` directly in spec files — wrap in page object methods
- MUST NOT use CSS class selectors (`.btn-primary`) — use `data-testid` via `getByTestId()`
- MUST NOT wait for `networkidle` — use `domcontentloaded` or element-specific waits
- MUST NOT duplicate selector strings across spec files — centralize in page object getters
