---
name: e2e-test-generator
description: Generate Playwright E2E tests using AlgoChanakya Page Object Model. Use when creating tests, adding test coverage, or writing Playwright specs for screens/features.
---

# E2E Test Generator

Generate complete E2E test suites following AlgoChanakya's Page Object Model patterns, data-testid conventions, and auth fixture usage.

## When to Use

- User asks to create E2E tests for a screen or feature
- User requests test coverage or Playwright tests
- User wants to add happy path, edge case, visual, or API tests
- User mentions testing a Vue component end-to-end

## Critical Rules

### 1. Selectors
- **ONLY use data-testid** - Never CSS classes, tags, or text selectors
- **Naming:** `[screen]-[component]-[element]` (e.g., `positions-exit-modal`)
- **Access via POM:** All selectors through Page Object methods using `getByTestId()`

### 2. Fixtures
- **ALWAYS import from auth.fixture.js** - NEVER from `@playwright/test` (except API tests)
- **Use `authenticatedPage`** for all authenticated UI tests
- **Use `auditablePage`** for accessibility/style tests
- Auth token injection is automatic (no manual login in tests)

### 3. Page Objects
- **Extend BasePage** - All page objects inherit from `tests/e2e/pages/BasePage.js`
- **Required property:** `this.url = '/route-path'` in constructor
- **Structure:** Getters (selectors) → Actions (methods) → Data getters
- **No assertions in POMs** - Return locators/data, let tests do assertions

### 4. Test File Categories

| Suffix | Purpose | Tags |
|--------|---------|------|
| `.happy.spec.js` | Success flows | `@happy` |
| `.edge.spec.js` | Error/boundary cases | `@edge` |
| `.visual.spec.js` | Screenshot regression | `@visual` |
| `.api.spec.js` | API validation | `@api` |
| `.audit.spec.js` | A11y/CSS audits | `@audit` |

## Test Generation Steps

### Step 1: Identify the Screen
Ask user for screen name and route path if not provided.

### Step 2: Add data-testid to Components
Before generating tests, verify Vue component has data-testid attributes:

```vue
<!-- Static -->
<button data-testid="myscreen-submit-button">Submit</button>

<!-- Dynamic -->
<div :data-testid="`myscreen-item-${item.id}`">{{ item.name }}</div>

<!-- Forms -->
<input v-model="value" data-testid="myscreen-search-input" />

<!-- Modals -->
<div data-testid="myscreen-modal-overlay">
  <div data-testid="myscreen-modal">
    <!-- content -->
  </div>
</div>
```

### Step 3: Generate Page Object

**Template:**
```javascript
import { BasePage } from './BasePage.js';

export class MyScreenPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/myscreen';
  }

  // ============ Selectors ============
  get pageContainer() { return this.getByTestId('myscreen-page'); }
  get submitButton() { return this.getByTestId('myscreen-submit-button'); }
  get errorMessage() { return this.getByTestId('myscreen-error-message'); }

  // Dynamic selectors
  getItemRow(itemId) {
    return this.getByTestId(`myscreen-item-${itemId}`);
  }

  // ============ Actions ============
  async waitForPageLoad() {
    await this.waitForTestId('myscreen-page');
    await this.waitForLoad();
  }

  async clickSubmit() {
    await this.submitButton.click();
  }

  async fillForm(data) {
    await this.nameInput.fill(data.name);
  }

  // ============ Data Getters ============
  async getItemCount() {
    return await this.page.locator('[data-testid^="myscreen-item-"]').count();
  }
}
```

### Step 4: Generate Spec Files

**Happy Path Test Template:**
```javascript
import { test, expect } from '../../fixtures/auth.fixture.js';
import { MyScreenPage } from '../../pages/MyScreenPage.js';

test.describe('MyScreen - Happy Path @happy', () => {
  let myScreenPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    myScreenPage = new MyScreenPage(authenticatedPage);
    await myScreenPage.navigate();
    await myScreenPage.waitForPageLoad();
  });

  test('should load screen successfully', async ({ authenticatedPage }) => {
    await expect(myScreenPage.pageContainer).toBeVisible();
  });

  test('should perform action successfully', async ({ authenticatedPage }) => {
    // Arrange
    const testData = { name: 'Test' };

    // Act
    await myScreenPage.fillForm(testData);
    await myScreenPage.clickSubmit();

    // Assert
    await expect(myScreenPage.successMessage).toBeVisible();
  });
});
```

**Edge Case Test Template:**
```javascript
import { test, expect } from '../../fixtures/auth.fixture.js';
import { MyScreenPage } from '../../pages/MyScreenPage.js';

test.describe('MyScreen - Edge Cases @edge', () => {
  let myScreenPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    myScreenPage = new MyScreenPage(authenticatedPage);
    await myScreenPage.navigate();
    await myScreenPage.waitForPageLoad();
  });

  test('should handle API error gracefully', async ({ authenticatedPage }) => {
    // Mock API failure
    await authenticatedPage.route('**/api/endpoint', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal error' })
      });
    });

    await myScreenPage.performAction();

    // Verify error handling
    await expect(myScreenPage.errorMessage).toBeVisible();
    await expect(myScreenPage.pageContainer).toBeVisible(); // Page remains functional
  });

  test('should validate required fields', async ({ authenticatedPage }) => {
    await myScreenPage.clickSubmit();
    await expect(myScreenPage.validationError).toBeVisible();
  });
});
```

**Visual Regression Test:**
```javascript
import { test, expect } from '../../fixtures/auth.fixture.js';
import { MyScreenPage } from '../../pages/MyScreenPage.js';
import { prepareForVisualTest, getVisualCompareOptions } from '../../helpers/visual.helper.js';

test.describe('MyScreen - Visual @visual', () => {
  let myScreenPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    myScreenPage = new MyScreenPage(authenticatedPage);
    await myScreenPage.navigate();
    await myScreenPage.waitForPageLoad();
    await prepareForVisualTest(authenticatedPage);
  });

  test('should match visual baseline', async ({ authenticatedPage }) => {
    await expect(authenticatedPage).toHaveScreenshot(
      'myscreen-default.png',
      getVisualCompareOptions()
    );
  });
});
```

**API Test Template:**
```javascript
import { test, expect } from '@playwright/test'; // Note: Use @playwright/test for API tests

const API_BASE = process.env.API_BASE || 'http://localhost:8000';

test.describe('MyScreen API @api', () => {
  test('GET endpoint returns data', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/myscreen/data`);

    expect(response.ok()).toBe(true);
    const data = await response.json();
    expect(data).toHaveProperty('items');
    expect(Array.isArray(data.items)).toBe(true);
  });

  test('POST endpoint validates input', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/myscreen/create`, {
      data: { /* invalid data */ }
    });

    expect(response.status()).toBe(422);
  });
});
```

## Anti-Patterns (What NOT to Do)

### ❌ NEVER use CSS selectors
```javascript
// WRONG
await page.locator('.modal-overlay').click();
await page.locator('button.submit').click();

// RIGHT
await myScreenPage.modalOverlay.click();
await myScreenPage.submitButton.click();
```

### ❌ NEVER import from @playwright/test (except API tests)
```javascript
// WRONG (for UI tests)
import { test, expect } from '@playwright/test';

// RIGHT
import { test, expect } from '../../fixtures/auth.fixture.js';
```

### ❌ NEVER hardcode selectors in tests
```javascript
// WRONG
await page.locator('[data-testid="submit"]').click();

// RIGHT
await myScreenPage.submitButton.click();
```

### ❌ NEVER add assertions to Page Objects
```javascript
// WRONG (in Page Object)
async verifySuccess() {
  expect(this.successMsg).toBeVisible(); // Don't do this
}

// RIGHT (in test file)
await expect(myScreenPage.successMsg).toBeVisible();
```

## References

- [Base Page Structure](./references/base-page-structure.md) - Common methods and patterns
- [Test File Templates](./references/test-file-templates.md) - Complete templates
- [data-testid Conventions](./references/data-testid-conventions.md) - Naming examples

## Checklist for New Tests

- [ ] Vue component has all necessary data-testid attributes
- [ ] Page Object extends BasePage
- [ ] Page Object has `this.url` property
- [ ] Test imports from auth.fixture.js (not @playwright/test)
- [ ] Test uses `authenticatedPage` fixture
- [ ] All selectors use data-testid via POM methods
- [ ] Naming follows `[screen]-[component]-[element]`
- [ ] Test organized by category (happy/edge/visual/api)
