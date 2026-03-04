# E2E Migration Patterns — Before/After Examples

Detailed code examples for each of the 7 migration rules. Used by the e2e-migration-assistant skill during automated fixes.

## Rule 1: CSS/Text Selectors → data-testid

### Pattern A: CSS Class Selector
```javascript
// ❌ Before
const button = page.locator('.btn-primary.submit-order');
await button.click();

// ✅ After
const button = page.getByTestId('submit-order-btn');
await button.click();
```

### Pattern B: Text Selector
```javascript
// ❌ Before
await page.getByText('Place Order').click();
await page.locator(':has-text("Exit All")').click();

// ✅ After
await page.getByTestId('place-order-btn').click();
await page.getByTestId('exit-all-btn').click();
```

### Pattern C: Tag Selector
```javascript
// ❌ Before
const rows = page.locator('table tbody tr');
const input = page.locator('input[type="number"]');

// ✅ After
const rows = page.getByTestId('positions-table').locator('[data-testid^="position-row-"]');
const input = page.getByTestId('quantity-input');
```

### Pattern D: Nested CSS
```javascript
// ❌ Before
const price = page.locator('.position-card .price-display .value');

// ✅ After
const price = page.getByTestId('position-card').getByTestId('price-value');
```

**Component side:** If `data-testid` doesn't exist yet, flag for manual addition:
```vue
<!-- Add to Vue component -->
<button data-testid="submit-order-btn" class="btn-primary" @click="submitOrder">
  Place Order
</button>
```

## Rule 2: Import Source

### Standard Spec File
```javascript
// ❌ Before
import { test, expect } from '@playwright/test';

test('should load dashboard', async ({ page }) => {
  // ...
});

// ✅ After
import { test, expect, authenticatedPage } from '../fixtures/auth.fixture.js';

test('should load dashboard', async ({ authenticatedPage: page }) => {
  // page is already authenticated via storageState
});
```

### Isolated Spec File (Exception)
```javascript
// ✅ OK — isolated specs CAN import from @playwright/test
// File: login.isolated.spec.js
import { test, expect } from '@playwright/test';

test('should show login page for unauthenticated user', async ({ page }) => {
  // No auth needed — testing the login flow itself
});
```

## Rule 3: Wait Patterns

### Pattern A: API Response Wait
```javascript
// ❌ Before
await page.click('[data-testid="refresh-btn"]');
await page.waitForTimeout(2000);
const data = await page.getByTestId('data-table');

// ✅ After
import { waitForApiResponse } from '../helpers/wait-helpers.js';

await page.click('[data-testid="refresh-btn"]');
await waitForApiResponse(page, '/api/positions');
const data = await page.getByTestId('data-table');
```

### Pattern B: Element Appearance Wait
```javascript
// ❌ Before
await page.waitForTimeout(1000);
await expect(page.getByTestId('toast')).toBeVisible();

// ✅ After
import { waitForToast } from '../helpers/wait-helpers.js';

await waitForToast(page, 'Order placed successfully');
```

### Pattern C: Navigation Wait
```javascript
// ❌ Before
await page.click('[data-testid="nav-positions"]');
await page.waitForTimeout(3000);

// ✅ After
import { waitForNavigation } from '../helpers/wait-helpers.js';

await page.click('[data-testid="nav-positions"]');
await waitForNavigation(page, '/positions');
```

### Pattern D: Data Load Wait
```javascript
// ❌ Before
await page.goto('/dashboard');
await page.waitForTimeout(5000); // Wait for data

// ✅ After
import { waitForDataLoad } from '../helpers/wait-helpers.js';

await page.goto('/dashboard');
await waitForDataLoad(page, 'dashboard-content');
```

## Rule 4: POM Export Style

```javascript
// ❌ Before — tests/e2e/pages/WatchlistPage.js
export default class WatchlistPage {
  constructor(page) {
    this.page = page;
  }
  // ...
}

// Usage in spec:
import WatchlistPage from '../pages/WatchlistPage.js';

// ✅ After
export class WatchlistPage {
  constructor(page) {
    this.page = page;
  }
  // ...
}

// Usage in spec:
import { WatchlistPage } from '../pages/WatchlistPage.js';
```

## Rule 5: Skip Reasons

```javascript
// ❌ Before
test.skip();
test.skip(true);
test.skip(process.env.CI);

// ✅ After
test.skip('Blocked by #123: WebSocket mock not available in CI');
test.skip(!!process.env.CI, 'Requires live broker connection, skip in CI');
test.skip(!process.env.BROKER_TOKEN, 'Requires broker auth token');
```

## Rule 6: URL Configuration

```javascript
// ❌ Before
await page.goto('http://localhost:5173/dashboard');
await page.waitForResponse('http://localhost:8001/api/positions');

// ✅ After
import { BASE_URL, API_URL } from '../helpers/config.helper.js';

await page.goto(`${BASE_URL}/dashboard`);
await page.waitForResponse(`${API_URL}/positions`);
```

**WebSocket URLs:**
```javascript
// ❌ Before
page.evaluate(() => new WebSocket('ws://localhost:8001/ws/ticks'));

// ✅ After
import { WS_URL } from '../helpers/config.helper.js';

page.evaluate((wsUrl) => new WebSocket(`${wsUrl}/ticks`), WS_URL);
```

## Rule 7: Assert Patterns

```javascript
// ❌ Before — test with no assertions
test('dashboard loads', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForTimeout(2000);
  // No expect() — test always passes!
});

// ✅ After — meaningful assertions
test('dashboard loads', async ({ authenticatedPage: page }) => {
  await page.goto('/dashboard');
  await waitForDataLoad(page, 'dashboard-content');

  // Verify page loaded correctly
  await expect(page.getByTestId('dashboard-header')).toBeVisible();
  await expect(page.getByTestId('portfolio-summary')).toBeVisible();
});
```

## Grep Quick Reference

All detection patterns in one place for batch scanning:

```bash
# Rule 1: CSS/Text selectors
rg "page\.locator\('[.#]" tests/e2e/specs/
rg "getByText\(" tests/e2e/specs/
rg ":has-text\(" tests/e2e/specs/

# Rule 2: Direct @playwright/test import
rg "from '@playwright/test'" tests/e2e/specs/ --glob '!*.isolated.spec.js'

# Rule 3: waitForTimeout
rg "waitForTimeout\(" tests/e2e/specs/

# Rule 4: Default exports in POMs
rg "export default class" tests/e2e/pages/

# Rule 5: Bare test.skip
rg "test\.skip\(\s*\)" tests/e2e/specs/
rg "test\.skip\(\s*true\s*\)" tests/e2e/specs/

# Rule 6: Hardcoded URLs
rg "http://localhost:" tests/e2e/specs/
rg "ws://localhost:" tests/e2e/specs/

# Rule 7: Files without expect()
for f in tests/e2e/specs/**/*.spec.js; do
  grep -qL "expect(" "$f" && echo "NO ASSERT: $f"
done
```
