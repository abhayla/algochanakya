# AlgoChanakya E2E Test Rules

This document defines the centralized rules for writing E2E tests in AlgoChanakya. All new tests MUST follow these patterns.

---

## 1. Selector Rules

| Rule | Description |
|------|-------------|
| **data-testid ONLY** | Use `data-testid` attributes exclusively — no CSS classes, tags, text selectors, or `getByText()` |
| **Semantic attributes** | Use `aria-selected`, `aria-current`, `data-pnl-polarity`, `data-leg-action` for state assertions |
| **Naming convention** | `[screen]-[component]-[element]` (e.g., `positions-exit-button-NIFTY`) |
| **Via POM** | All selectors must go through Page Object methods using `getByTestId()` |

### DON'T

```javascript
// Never use CSS classes
await page.locator('.success-state').click();
await expect(el).toHaveClass(/active/);

// Never use text selectors
await page.locator('button:has-text("Deploy")').click();
await page.getByText('Submit');

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

// Use semantic attributes for state assertions
await expect(tabButton).toHaveAttribute('aria-selected', 'true');
await expect(navItem).toHaveAttribute('aria-current', 'page');
await expect(pnlCell).toHaveAttribute('data-pnl-polarity', 'positive');
```

---

## 2. Fixture Rules

| Rule | Description |
|------|-------------|
| **Import from auth.fixture.js** | Not from `@playwright/test` |
| **Use `authenticatedPage`** | For all authenticated tests |
| **Use `auditablePage`** | For accessibility/style audit tests |
| **Use `styleAudit`** | For CSS/style checking |
| **Token injection** | Auth handled via fixture + `storageState`, not manual login |

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
| **Named exports** | Use `export class MyPage` (not `export default class`) |
| **Structure** | Getters → Actions → Assertions |
| **`this.url` property** | Required on every page object |
| **No inline assertions** | Page objects return locators/data, tests do assertions |

### Page Object Template

```javascript
import { BasePage } from './BasePage.js';

export class MyPage extends BasePage {
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

### Importing in Specs

```javascript
// Named export — always use destructured import
import { MyPage } from '../../pages/MyPage.js';
```

---

## 4. Test File Structure

| Suffix | Purpose | Fixture |
|--------|---------|---------|
| `.happy.spec.js` | Normal/success flows | `authenticatedPage` |
| `.edge.spec.js` | Error/boundary cases | `authenticatedPage` |
| `.visual.spec.js` | Screenshot regression | `authenticatedPage` |
| `.api.spec.js` | API validation | `authenticatedPage` or `{ request }` |
| `.websocket.spec.js` | Live data streaming | `authenticatedPage` |
| `.deploy.spec.js` | Deploy/activation flows | `authenticatedPage` |
| `.audit.spec.js` | Accessibility/CSS | `auditablePage` |
| `.isolated.spec.js` | No auth needed | None (fresh context) |

### Directory Structure

```
tests/e2e/
├── fixtures/
│   └── auth.fixture.js          # Token injection, authenticatedPage/auditablePage/styleAudit
├── helpers/
│   ├── auth.helper.js           # Token acquisition and validation
│   ├── config.helper.js         # FRONTEND_URL, API_BASE, WS_BASE constants (single source)
│   ├── kite-login.helper.js     # Kite OAuth login flow
│   ├── market-status.helper.js  # NSE market open/closed detection
│   ├── style-audit.helper.js    # A11y/CSS validation
│   ├── visual.helper.js         # Screenshot masking
│   └── wait-helpers.js          # Event-driven wait replacements (no waitForTimeout)
├── pages/
│   ├── BasePage.js              # Common methods, all pages inherit
│   ├── AutoPilotDashboardPage.js
│   ├── BrokerSettingsPage.js
│   ├── DashboardPage.js
│   ├── KiteHeaderPage.js
│   ├── LoginPage.js
│   ├── OFOPage.js
│   ├── OptionChainPage.js
│   ├── PositionsPage.js
│   ├── StrategyBuilderPage.js
│   ├── StrategyLibraryPage.js
│   └── WatchlistPage.js
└── specs/
    ├── ai/
    ├── audit/
    ├── auth/
    ├── autopilot/
    ├── broker-abstraction/
    ├── dashboard/
    ├── header/
    ├── integration/
    ├── live/
    ├── login/
    ├── navigation/
    ├── ofo/
    ├── optionchain/
    ├── positions/
    ├── strategy/
    ├── strategylibrary/
    └── watchlist/
```

---

## 5. Configuration Rules

| Setting | Value | Notes |
|---------|-------|-------|
| **Workers (local)** | `4` | Parallel execution with `fullyParallel: true` |
| **Workers (CI)** | `2` | Reduced for stability |
| **Retries (local)** | `0` | No retries locally |
| **Retries (CI)** | `1` | `process.env.CI ? 1 : 0` |
| **Timeout** | `30 seconds` | Per-test timeout |
| **Expect timeout** | `10 seconds` | For live broker data assertions |
| **Viewport** | `1280×800` | Fixed viewport |
| **Headless (local)** | `false` | Headed browser locally |
| **Headless (CI)** | `false` | Headed in CI too (Xvfb handles display) |
| **Auth state** | `./tests/config/.auth-state.json` | Reused from `globalSetup` |

These settings are in `playwright.config.js`. Do not change workers, retries, or headless settings without a team decision.

**Two test projects:**
- `chromium` — standard tests with saved auth state; ignores `*.isolated.spec.js`
- `isolated` — matches only `*.isolated.spec.js`; fresh browser context, no auth state

---

## 6. URL Configuration

**Never hardcode URLs.** Import from the config helper:

```javascript
import { FRONTEND_URL, API_BASE, WS_BASE } from '../helpers/config.helper.js';

// FRONTEND_URL = 'http://localhost:5173' (or FRONTEND_URL env var)
// API_BASE     = 'http://localhost:8001' (dev backend — NOT 8000 which is production)
// WS_BASE      = 'ws://localhost:8001'
```

**Critical:** Port `8001` is dev. Port `8000` is production. Never hardcode `localhost:8000` in tests.

---

## 7. Wait Strategy Rules

**Never use `waitForTimeout`.** It is the #1 source of test flakiness.

```javascript
// WRONG — arbitrary sleep, brittle
await page.waitForTimeout(2000);

// WRONG — networkidle never fires when WebSocket is open
await page.waitForLoadState('networkidle');
```

Use event-driven waits from `wait-helpers.js`:

```javascript
import {
  waitForApiResponse,      // Wait for a network response matching a URL pattern
  waitForDataInTestId,     // Wait until a testid becomes non-empty
  waitForTestIdPrefix,     // Wait for N+ elements with testid prefix
  waitForSearchResults,    // Wait for search/filter dropdown
  waitForWebSocket,        // Wait for WebSocket connection
  waitForEitherTestId,     // Wait for either data OR empty-state
  waitForModal,            // Wait for modal to appear
  waitForDropdownOptions,  // Wait for dropdown options to load
} from '../helpers/wait-helpers.js';

// Prefer locator.waitFor() for single elements:
await myPage.someElement.waitFor({ state: 'visible', timeout: 5000 });

// Use waitForLoadState('domcontentloaded') instead of 'networkidle'
await page.waitForLoadState('domcontentloaded');
```

---

## 8. Real Data Strategy (No Mocks)

Tests always use **real broker data**. Never mock API responses.

Use `market-status.helper.js` to write market-aware assertions:

```javascript
import { assertDataOrEmptyState } from '../helpers/market-status.helper.js';

// Every test must assert SOMETHING regardless of market state
// DON'T do this (silent skip — zero assertions if no data):
if (hasPositions) {
  await expect(table).toBeVisible();
}

// DO this (always asserts):
if (hasPositions) {
  await expect(table).toBeVisible();
} else {
  await expect(emptyState).toBeVisible();
}

// Or use the helper:
await assertDataOrEmptyState(page, 'positions-table', 'positions-empty-state', expect);
```

---

## 9. Test Template

```javascript
import { test, expect } from '../../fixtures/auth.fixture.js';
import { MyPage } from '../../pages/MyPage.js';

test.describe('Feature Name', () => {
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

    // Assert - Verify the result (always at least one assertion)
    await expect(myPage.successMessage).toBeVisible();
    await expect(myPage.successMessage).toContainText('Success');
  });
});
```

---

## 10. Key Files Reference

| File | Purpose |
|------|---------|
| `tests/e2e/fixtures/auth.fixture.js` | Token injection, `authenticatedPage`/`auditablePage`/`styleAudit` fixtures |
| `tests/e2e/pages/BasePage.js` | Common methods, all pages inherit |
| `tests/e2e/helpers/config.helper.js` | `FRONTEND_URL`, `API_BASE`, `WS_BASE` — single source of truth for URLs |
| `tests/e2e/helpers/wait-helpers.js` | Event-driven waits replacing `waitForTimeout` |
| `tests/e2e/helpers/market-status.helper.js` | NSE market open/closed detection, `assertDataOrEmptyState` |
| `tests/e2e/helpers/style-audit.helper.js` | A11y/CSS validation |
| `tests/e2e/helpers/visual.helper.js` | Screenshot masking |
| `tests/e2e/global-setup.js` | One-time login with TOTP, populates `.auth-state.json` |
| `playwright.config.js` | Config — 4 workers local, 2 CI, 30s timeout, 10s expect |

---

## 11. Adding New Tests Checklist

When adding tests for a new feature:

1. [ ] Add `data-testid` attributes to Vue component elements
2. [ ] Add `aria-selected`/`aria-current` to tab/nav elements for state assertions
3. [ ] Add selectors to relevant Page Object (or create new POM with `export class`)
4. [ ] Import from `auth.fixture.js` (NOT `@playwright/test`)
5. [ ] Import URLs from `config.helper.js` (NOT hardcoded)
6. [ ] Use `authenticatedPage` fixture in tests
7. [ ] Use POM methods for all interactions
8. [ ] No CSS class or text selectors anywhere
9. [ ] No `waitForTimeout` — use `wait-helpers.js` or `locator.waitFor()`
10. [ ] Every test must assert something (no silent skips)
11. [ ] Follow naming: `[screen]-[component]-[element]`
12. [ ] Organize tests by category (happy, edge, api, visual)

---

## 12. data-testid Naming Examples

```
Format: [screen]-[component]-[element]

Login Screen:
  data-testid="login-zerodha-button"
  data-testid="login-error-message"

Positions Screen:
  data-testid="positions-exit-button-NIFTY"
  data-testid="positions-exit-modal"
  data-testid="positions-exit-modal-close"
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

## 13. Common Mistakes to Avoid

### 1. Using CSS Selectors or Class Assertions

```javascript
// WRONG
await page.locator('.modal-overlay').click();
await expect(el).toHaveClass(/active/);

// RIGHT
await myPage.modalOverlay.click();
await expect(tabButton).toHaveAttribute('aria-selected', 'true');
```

### 2. Importing from Wrong Package

```javascript
// WRONG
import { test, expect } from '@playwright/test';

// RIGHT
import { test, expect } from '../../fixtures/auth.fixture.js';
```

### 3. Hardcoding URLs

```javascript
// WRONG
const response = await fetch('http://localhost:8000/api/positions');
const response = await fetch('http://localhost:8001/api/positions');

// RIGHT
import { API_BASE } from '../helpers/config.helper.js';
const response = await fetch(`${API_BASE}/api/positions`);
```

### 4. Using waitForTimeout or networkidle

```javascript
// WRONG
await page.waitForTimeout(2000);
await page.waitForLoadState('networkidle');

// RIGHT
await myPage.someElement.waitFor({ state: 'visible', timeout: 5000 });
await page.waitForLoadState('domcontentloaded');
```

### 5. Silent Skips (Zero Assertions)

```javascript
// WRONG — test passes with zero assertions when no data
if (hasPositions) {
  await expect(table).toBeVisible();
}

// RIGHT — always asserts
if (hasPositions) {
  await expect(table).toBeVisible();
} else {
  await expect(emptyState).toBeVisible();
}
```

### 6. Using Default Exports in POMs

```javascript
// WRONG
export default class MyPage extends BasePage { ... }
import MyPage from '../../pages/MyPage.js';

// RIGHT
export class MyPage extends BasePage { ... }
import { MyPage } from '../../pages/MyPage.js';
```

---

## 14. Running Tests

```bash
# Run all tests
npm test

# Run by screen
npm run test:specs:strategylibrary
npm run test:specs:positions
npm run test:specs:autopilot

# Run by category
npm run test:happy
npm run test:edge
npm run test:visual
npm run test:api:new
npm run test:audit

# Run single file
npx playwright test tests/e2e/specs/strategylibrary/strategylibrary.happy.spec.js

# Run single test by name
npx playwright test --grep "should display positions table"

# Debug mode
npm run test:debug

# Headed mode (visible browser)
npm run test:headed
```

---

## 15. Adding data-testid to Vue Components

When adding testability to Vue components:

```vue
<!-- Static elements -->
<button data-testid="myscreen-submit-button">Submit</button>

<!-- State via semantic attributes (not CSS class assertions) -->
<button
  v-for="tab in tabs"
  :key="tab.id"
  :data-testid="`myscreen-tab-${tab.id}`"
  :aria-selected="activeTab === tab.id"
  @click="activeTab = tab.id"
>{{ tab.label }}</button>

<!-- Navigation items -->
<a
  :data-testid="`nav-link-${item.id}`"
  :aria-current="isActive(item.path) ? 'page' : undefined"
  :href="item.path"
>{{ item.label }}</a>

<!-- Dynamic elements with IDs -->
<div
  v-for="(item, index) in items"
  :key="item.id"
  :data-testid="`myscreen-item-${item.id}`"
>
  {{ item.name }}
</div>

<!-- P&L polarity (use data attribute, not CSS class) -->
<span
  :data-testid="`myscreen-pnl-${item.id}`"
  :data-pnl-polarity="item.pnl >= 0 ? 'positive' : 'negative'"
>{{ formatPnl(item.pnl) }}</span>

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
    <button data-testid="myscreen-modal-close" @click="closeModal">×</button>
    <!-- modal content -->
  </div>
</div>
```
