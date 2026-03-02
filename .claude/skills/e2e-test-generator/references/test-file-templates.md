# Test File Templates

Complete templates for all test categories in AlgoChanakya E2E testing.

## Directory Structure

```
tests/e2e/specs/
└── myscreen/
    ├── myscreen.happy.spec.js
    ├── myscreen.edge.spec.js
    ├── myscreen.visual.spec.js
    ├── myscreen.api.spec.js
    └── myscreen.audit.spec.js
```

---

## 1. Happy Path Test Template

**File:** `myscreen.happy.spec.js`

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
    await expect(myScreenPage.headerTitle).toContainText('My Screen');
  });

  test('should submit form successfully', async ({ authenticatedPage }) => {
    // Arrange
    const formData = {
      name: 'Test User',
      email: 'test@example.com'
    };

    // Act
    await myScreenPage.fillForm(formData);
    await myScreenPage.clickSubmit();

    // Assert
    await expect(myScreenPage.successMessage).toBeVisible();
    await expect(myScreenPage.successMessage).toContainText('Success');
  });

  test('should filter items', async ({ authenticatedPage }) => {
    // Arrange
    const initialCount = await myScreenPage.getItemCount();

    // Act
    await myScreenPage.applyFilter('active');

    // Assert
    const filteredCount = await myScreenPage.getItemCount();
    expect(filteredCount).toBeLessThan(initialCount);
  });

  test('should navigate to detail page', async ({ authenticatedPage }) => {
    // Act
    await myScreenPage.clickFirstItem();

    // Assert
    await myScreenPage.waitForUrl('/myscreen/1');
    await expect(myScreenPage.detailContainer).toBeVisible();
  });
});
```

---

## 2. Edge Case Test Template

**File:** `myscreen.edge.spec.js`

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
    await authenticatedPage.route('**/api/myscreen/submit', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });

    // Act
    await myScreenPage.clickSubmit();

    // Assert - Page should show error but remain functional
    await expect(myScreenPage.errorMessage).toBeVisible();
    await expect(myScreenPage.errorMessage).toContainText('error');
    await expect(myScreenPage.pageContainer).toBeVisible();
  });

  test('should validate required fields', async ({ authenticatedPage }) => {
    // Act - Submit without filling required fields
    await myScreenPage.clickSubmit();

    // Assert
    await expect(myScreenPage.validationError).toBeVisible();
    await expect(myScreenPage.validationError).toContainText('required');
  });

  test('should handle empty state', async ({ authenticatedPage }) => {
    // Mock empty response
    await authenticatedPage.route('**/api/myscreen/items', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] })
      });
    });

    // Navigate to trigger data fetch
    await myScreenPage.navigate();
    await myScreenPage.waitForPageLoad();

    // Assert
    await expect(myScreenPage.emptyState).toBeVisible();
    await expect(myScreenPage.emptyState).toContainText('No items');
  });

  test('should handle network timeout', async ({ authenticatedPage }) => {
    // Mock slow response
    await authenticatedPage.route('**/api/myscreen/submit', route => {
      return new Promise(resolve => {
        setTimeout(() => {
          route.fulfill({
            status: 408,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Request timeout' })
          });
          resolve();
        }, 5000);
      });
    });

    await myScreenPage.clickSubmit();

    // Should show timeout error
    await expect(myScreenPage.errorMessage).toBeVisible({ timeout: 10000 });
  });

  test('should prevent duplicate submissions', async ({ authenticatedPage }) => {
    // Act - Click submit multiple times rapidly
    await myScreenPage.submitButton.click();
    await myScreenPage.submitButton.click();
    await myScreenPage.submitButton.click();

    // Wait for completion
    await expect(myScreenPage.successMessage).toBeVisible();

    // Assert - Only one request should have been sent
    // (Verify via network logs or UI state)
  });
});
```

---

## 3. Visual Regression Test Template

**File:** `myscreen.visual.spec.js`

```javascript
import { test, expect } from '../../fixtures/auth.fixture.js';
import { MyScreenPage } from '../../pages/MyScreenPage.js';
import {
  prepareForVisualTest,
  getVisualCompareOptions,
  VIEWPORTS
} from '../../helpers/visual.helper.js';

test.describe('MyScreen - Visual @visual', () => {
  let myScreenPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    myScreenPage = new MyScreenPage(authenticatedPage);
    await myScreenPage.navigate();
    await myScreenPage.waitForPageLoad();
    await prepareForVisualTest(authenticatedPage); // Masks dynamic content
  });

  test('should match default state baseline', async ({ authenticatedPage }) => {
    await expect(authenticatedPage).toHaveScreenshot(
      'myscreen-default.png',
      getVisualCompareOptions()
    );
  });

  test('should match modal state baseline', async ({ authenticatedPage }) => {
    await myScreenPage.openModal();
    await expect(myScreenPage.modal).toBeVisible();

    await expect(authenticatedPage).toHaveScreenshot(
      'myscreen-modal.png',
      getVisualCompareOptions()
    );
  });

  test('should match error state baseline', async ({ authenticatedPage }) => {
    // Trigger error state
    await authenticatedPage.route('**/api/myscreen/submit', route => {
      route.fulfill({ status: 500, body: JSON.stringify({ detail: 'Error' }) });
    });

    await myScreenPage.clickSubmit();
    await expect(myScreenPage.errorMessage).toBeVisible();

    await expect(authenticatedPage).toHaveScreenshot(
      'myscreen-error.png',
      getVisualCompareOptions()
    );
  });

  test('should match mobile viewport', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.mobile);
    await prepareForVisualTest(authenticatedPage);

    await expect(authenticatedPage).toHaveScreenshot(
      'myscreen-mobile.png',
      getVisualCompareOptions()
    );
  });
});
```

---

## 4. API Test Template

**File:** `myscreen.api.spec.js`

**Note:** API tests use `@playwright/test` directly (not auth.fixture.js)

```javascript
import { test, expect } from '@playwright/test';
import { getApiBase } from '../../helpers/config.helper.js';

const API_BASE = getApiBase();

test.describe('MyScreen API @api', () => {
  let authToken;

  test.beforeAll(async ({ request }) => {
    // Get auth token if needed for authenticated endpoints
    // (Use existing token from env or generate)
    authToken = process.env.TEST_AUTH_TOKEN;
  });

  test('GET /api/myscreen/items should return data', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/myscreen/items`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    expect(response.ok()).toBe(true);
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('items');
    expect(Array.isArray(data.items)).toBe(true);
  });

  test('POST /api/myscreen/create should validate input', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/myscreen/create`, {
      headers: { 'Authorization': `Bearer ${authToken}` },
      data: {
        // Invalid data - missing required field
        name: ''
      }
    });

    expect(response.status()).toBe(422); // Validation error
    const error = await response.json();
    expect(error).toHaveProperty('detail');
  });

  test('POST /api/myscreen/create should create item', async ({ request }) => {
    const newItem = {
      name: 'Test Item',
      description: 'Test Description'
    };

    const response = await request.post(`${API_BASE}/api/myscreen/create`, {
      headers: { 'Authorization': `Bearer ${authToken}` },
      data: newItem
    });

    expect(response.ok()).toBe(true);
    expect(response.status()).toBe(201);

    const data = await response.json();
    expect(data).toHaveProperty('id');
    expect(data.name).toBe(newItem.name);
  });

  test('DELETE /api/myscreen/{id} should delete item', async ({ request }) => {
    const itemId = 'test-id';

    const response = await request.delete(`${API_BASE}/api/myscreen/${itemId}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    expect(response.ok()).toBe(true);
    expect(response.status()).toBe(204);
  });
});
```

---

## 5. Audit Test Template

**File:** `myscreen.audit.spec.js`

```javascript
import { test, expect } from '../../fixtures/auth.fixture.js';
import { MyScreenPage } from '../../pages/MyScreenPage.js';

test.describe('MyScreen - Audit @audit', () => {
  let myScreenPage;

  test.beforeEach(async ({ auditablePage }) => {
    myScreenPage = new MyScreenPage(auditablePage);
    await myScreenPage.navigate();
    await myScreenPage.waitForPageLoad();
  });

  test('should have no accessibility violations', async ({ auditablePage }) => {
    const violations = await auditablePage.styleAudit.checkAccessibility();
    expect(violations.length).toBe(0);
  });

  test('should use correct fonts', async ({ auditablePage }) => {
    const fonts = await auditablePage.styleAudit.checkFonts();
    expect(fonts.isValid).toBe(true);
  });

  test('should have no horizontal overflow', async ({ auditablePage }) => {
    const hasOverflow = await myScreenPage.hasHorizontalOverflow();
    expect(hasOverflow).toBe(false);
  });

  test('should use design system colors', async ({ auditablePage }) => {
    const colors = await auditablePage.styleAudit.checkColors();
    expect(colors.isValid).toBe(true);
  });
});
```

---

## Common Patterns

### Mocking API Responses

```javascript
await authenticatedPage.route('**/api/endpoint', route => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ data: 'mocked' })
  });
});
```

### Waiting for Elements

```javascript
// Wait for element to appear
await expect(myScreenPage.element).toBeVisible();

// Wait for element to disappear
await expect(myScreenPage.loadingSpinner).not.toBeVisible();

// Wait for specific text
await expect(myScreenPage.message).toContainText('Expected text');
```

### Test Data

```javascript
// Arrange phase - create test data
const testUser = {
  name: 'Test User',
  email: 'test@example.com'
};

const testStrategy = {
  underlying: 'NIFTY',
  lots: 2,
  legs: [...]
};
```
