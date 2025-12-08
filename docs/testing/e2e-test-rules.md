# AlgoChanakya E2E Test Rules

This document defines the centralized rules for writing E2E tests in AlgoChanakya. All new tests MUST follow these patterns.

---

## 1. Selector Rules

| Rule | Description |
|------|-------------|
| **data-testid ONLY** | Use `data-testid` attributes exclusively - no CSS classes, tags, or text selectors |
| **Naming convention** | `[screen]-[component]-[element]` (e.g., `positions-exit-button-NIFTY`) |
| **Via POM** | All selectors must go through Page Object methods using `getByTestId()` |

### DON'T

```javascript
// Never use CSS classes
await page.locator('.success-state').click();

// Never use text selectors
await page.locator('button:has-text("Deploy")').click();

// Never use tag selectors
await page.locator('.lots-control button').first();

// Never use nth-child or complex selectors
await page.locator('div.modal > button:first-child');
```

### DO

```javascript
// Always use Page Object methods with data-testid
await strategyLibraryPage.deploySuccess.click();
await strategyLibraryPage.getWizardRecommendationDeploy(0).click();
await strategyLibraryPage.deployLotsMinus.click();
```

---

## 2. Fixture Rules

| Rule | Description |
|------|-------------|
| **Import from auth.fixture.js** | Not from `@playwright/test` |
| **Use `authenticatedPage`** | For all authenticated tests |
| **Use `auditablePage`** | For accessibility/style audit tests |
| **Token injection** | Auth handled via fixture, not manual login |

### Correct Import

```javascript
// CORRECT
import { test, expect } from '../../fixtures/auth.fixture.js';

// WRONG - never import from @playwright/test
import { test, expect } from '@playwright/test';
```

---

## 3. Page Object Pattern

| Rule | Description |
|------|-------------|
| **Extend BasePage** | All page objects inherit from `BasePage.js` |
| **Structure** | Getters → Actions → Assertions |
| **`this.url` property** | Required on every page object |
| **No inline assertions** | Page objects return locators/data, tests do assertions |

### Page Object Template

```javascript
import { BasePage } from './BasePage.js';

export default class MyPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/mypage';  // Required
  }

  // ============ 1. Selectors (getters) ============

  get pageContainer() { return this.getByTestId('mypage-container'); }
  get submitButton() { return this.getByTestId('mypage-submit-button'); }
  get errorMessage() { return this.getByTestId('mypage-error-message'); }

  // Dynamic selectors
  getItemRow(itemId) {
    return this.getByTestId(`mypage-item-${itemId}`);
  }

  // ============ 2. Actions (async methods) ============

  async navigate() {
    await this.page.goto(this.url);
    await this.waitForLoad();
  }

  async clickSubmit() {
    await this.submitButton.click();
  }

  async fillForm(data) {
    await this.nameInput.fill(data.name);
    await this.emailInput.fill(data.email);
  }

  // ============ 3. Data Getters (async methods) ============

  async getCount() {
    return await this.countDisplay.textContent();
  }

  async getItems() {
    const items = await this.itemList.locator('[data-testid^="mypage-item-"]').all();
    return items;
  }

  // ============ 4. Assertions (optional, prefer in tests) ============

  async assertPageVisible() {
    const visible = await this.pageContainer.isVisible();
    if (!visible) throw new Error('Page not visible');
  }
}
```

---

## 4. Test File Structure

| Suffix | Purpose | Fixture |
|--------|---------|---------|
| `.happy.spec.js` | Normal/success flows | `authenticatedPage` |
| `.edge.spec.js` | Error/boundary cases | `authenticatedPage` |
| `.visual.spec.js` | Screenshot regression | `authenticatedPage` |
| `.api.spec.js` | API validation | `authenticatedPage` |
| `.websocket.spec.js` | Live data streaming | `authenticatedPage` |
| `.audit.spec.js` | Accessibility/CSS | `auditablePage` |
| `.isolated.spec.js` | No auth needed | None |

### Directory Structure

```
tests/e2e/
├── fixtures/
│   └── auth.fixture.js          # Token injection, authenticatedPage/auditablePage
├── helpers/
│   ├── style-audit.helper.js    # A11y/CSS validation
│   └── visual.helper.js         # Screenshot masking
├── pages/
│   ├── BasePage.js              # Common methods, all pages inherit
│   ├── LoginPage.js
│   ├── DashboardPage.js
│   ├── PositionsPage.js
│   ├── WatchlistPage.js
│   ├── OptionChainPage.js
│   ├── StrategyBuilderPage.js
│   └── StrategyLibraryPage.js
└── specs/
    ├── login/
    │   ├── login.happy.spec.js
    │   ├── login.edge.spec.js
    │   └── login.visual.spec.js
    ├── dashboard/
    │   └── ...
    ├── positions/
    │   └── ...
    └── strategylibrary/
        ├── strategylibrary.happy.spec.js
        ├── strategylibrary.edge.spec.js
        ├── strategylibrary.api.spec.js
        └── strategylibrary.visual.spec.js
```

---

## 5. Configuration Rules

| Rule | Value |
|------|-------|
| **Single worker** | `workers: 1` |
| **No parallel** | `fullyParallel: false` |
| **Maximized browser** | `--start-maximized` |
| **Auth state reuse** | `.auth-state.json` |
| **Timeout** | 180 seconds |

These settings are in `playwright.config.js` and should not be changed.

---

## 6. Test Template

```javascript
import { test, expect } from '../../fixtures/auth.fixture.js';
import MyPage from '../../pages/MyPage.js';

test.describe('Feature Name @happy', () => {
  let myPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    myPage = new MyPage(authenticatedPage);
    await myPage.navigate();
  });

  test('should do something successfully', async ({ authenticatedPage }) => {
    // Arrange - Set up test data
    await myPage.fillInput('test value');

    // Act - Perform the action
    await myPage.clickSubmit();

    // Assert - Verify the result
    await expect(myPage.successMessage).toBeVisible();
    await expect(myPage.successMessage).toContainText('Success');
  });

  test('should handle another scenario', async ({ authenticatedPage }) => {
    // Test implementation
  });
});
```

---

## 7. Key Files Reference

| File | Purpose |
|------|---------|
| `tests/e2e/fixtures/auth.fixture.js` | Token injection, authenticatedPage/auditablePage |
| `tests/e2e/pages/BasePage.js` | Common methods, all pages inherit |
| `tests/e2e/helpers/style-audit.helper.js` | A11y/CSS validation |
| `tests/e2e/helpers/visual.helper.js` | Screenshot masking |
| `tests/e2e/global-setup.js` | One-time login with TOTP |
| `playwright.config.js` | Config - single worker, maximized, auth state |

---

## 8. Adding New Tests Checklist

When adding tests for a new feature:

1. [ ] Add `data-testid` attributes to Vue component elements
2. [ ] Add selectors to relevant Page Object (or create new POM)
3. [ ] Import from `auth.fixture.js` (NOT `@playwright/test`)
4. [ ] Use `authenticatedPage` fixture in tests
5. [ ] Use POM methods for all interactions
6. [ ] No CSS class or text selectors anywhere
7. [ ] Follow naming: `[screen]-[component]-[element]`
8. [ ] Organize tests by category (happy, edge, api, visual)

---

## 9. data-testid Naming Examples

```
Format: [screen]-[component]-[element]

Login Screen:
  data-testid="login-zerodha-button"
  data-testid="login-error-message"

Positions Screen:
  data-testid="positions-exit-button-NIFTY"
  data-testid="positions-exit-modal"
  data-testid="positions-pnl-total"

Option Chain:
  data-testid="optionchain-strike-row-24500"
  data-testid="optionchain-ce-oi-24500"
  data-testid="optionchain-expiry-select"

Strategy Builder:
  data-testid="strategy-add-row-button"
  data-testid="strategy-leg-row-0"
  data-testid="strategy-pnl-chart"

Strategy Library:
  data-testid="strategy-library-wizard-button"
  data-testid="strategy-card-iron_condor"
  data-testid="strategy-deploy-modal"
  data-testid="strategy-wizard-outlook-bullish"
```

---

## 10. Common Mistakes to Avoid

### 1. Using CSS Selectors

```javascript
// WRONG
await page.locator('.modal-overlay').click();

// RIGHT
await myPage.modalOverlay.click();
```

### 2. Importing from Wrong Package

```javascript
// WRONG
import { test, expect } from '@playwright/test';

// RIGHT
import { test, expect } from '../../fixtures/auth.fixture.js';
```

### 3. Hardcoding Selectors in Tests

```javascript
// WRONG
await page.locator('[data-testid="strategy-deploy-modal"]').click();

// RIGHT
await strategyLibraryPage.deployModal.click();
```

### 4. Not Using Page Object Methods

```javascript
// WRONG
await page.fill('[data-testid="deploy-lots"]', '2');

// RIGHT
await strategyLibraryPage.setDeployLots(2);
```

### 5. Adding Assertions to Page Objects

```javascript
// WRONG (in Page Object)
async verifySuccess() {
  expect(this.successMessage).toBeVisible();  // Don't do this
}

// RIGHT (in test file)
await expect(myPage.successMessage).toBeVisible();
```

---

## 11. Running Tests

```bash
# Run all tests
npm test

# Run by screen
npm run test:specs:strategylibrary
npm run test:specs:positions

# Run by category
npm run test:happy
npm run test:edge
npm run test:visual
npm run test:api:new
npm run test:audit

# Run single file
npx playwright test tests/e2e/specs/strategylibrary/strategylibrary.happy.spec.js

# Debug mode
npm run test:debug

# Headed mode (visible browser)
npm run test:headed
```

---

## 12. Adding data-testid to Vue Components

When adding testability to Vue components:

```vue
<!-- Static elements -->
<button data-testid="myscreen-submit-button">Submit</button>

<!-- Dynamic elements with IDs -->
<div
  v-for="(item, index) in items"
  :key="item.id"
  :data-testid="`myscreen-item-${item.id}`"
>
  {{ item.name }}
</div>

<!-- Form elements -->
<input
  v-model="value"
  data-testid="myscreen-search-input"
/>

<!-- Modals -->
<div
  v-if="showModal"
  class="modal-overlay"
  data-testid="myscreen-modal-overlay"
  @click.self="closeModal"
>
  <div class="modal-content" data-testid="myscreen-modal">
    <!-- modal content -->
  </div>
</div>
```
