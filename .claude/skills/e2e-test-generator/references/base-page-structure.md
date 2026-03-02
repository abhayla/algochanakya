# BasePage Structure

All Page Objects in AlgoChanakya extend `BasePage` class which provides common methods.

## File Location
`tests/e2e/pages/BasePage.js`

## Common Methods

### Navigation
| Method | Description |
|--------|-------------|
| `navigate()` | Navigate to `this.url` and wait for domcontentloaded |
| `goto(url)` | Navigate to specific URL |
| `waitForLoad()` | Wait for domcontentloaded + 500ms Vue rendering buffer |
| `waitForUrl(path)` | Wait for URL to contain path |

### Selectors
| Method | Description |
|--------|-------------|
| `getByTestId(testId)` | Get locator by data-testid |
| `waitForTestId(testId)` | Wait for element with data-testid to appear |
| `clickTestId(testId)` | Click element by data-testid |
| `isTestIdVisible(testId)` | Check if element with data-testid is visible |
| `getTestIdText(testId)` | Get text content by data-testid |

### Screenshots
| Method | Description |
|--------|-------------|
| `screenshot(name)` | Take viewport screenshot |
| `screenshotFullPage(name)` | Take full page screenshot |

### Utilities
| Method | Description |
|--------|-------------|
| `getUrl()` | Get current page URL |
| `urlContains(path)` | Check if URL contains path |
| `hasHorizontalOverflow()` | Detect horizontal overflow (CSS audit) |
| `getPageDimensions()` | Get scrollWidth, scrollHeight, etc. |

## Required Property

Every Page Object MUST set `this.url` in constructor:

```javascript
export class MyPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/mypage'; // REQUIRED
  }
}
```

## Page Object Structure

### 1. Selectors (Getters)

Return locators using `getByTestId()`:

```javascript
// Static selectors
get submitButton() { return this.getByTestId('myscreen-submit-button'); }
get errorMessage() { return this.getByTestId('myscreen-error-message'); }

// Dynamic selectors (methods)
getItemRow(itemId) {
  return this.getByTestId(`myscreen-item-${itemId}`);
}

getLegStrike(index) {
  return this.getByTestId(`strategy-leg-strike-${index}`);
}
```

### 2. Actions (Async Methods)

Encapsulate user interactions:

```javascript
async waitForPageLoad() {
  await this.waitForTestId('myscreen-page');
  await this.waitForLoad();
}

async clickSubmit() {
  await this.submitButton.click();
}

async fillForm(data) {
  await this.nameInput.fill(data.name);
  await this.emailInput.fill(data.email);
}

async selectOption(value) {
  await this.dropdown.selectOption(value);
}
```

### 3. Data Getters (Async Methods)

Return data from the page:

```javascript
async getItemCount() {
  return await this.page.locator('[data-testid^="myscreen-item-"]').count();
}

async getItems() {
  const items = await this.itemList.locator('[data-testid^="myscreen-item-"]').all();
  return items;
}

async getErrorText() {
  return await this.errorMessage.textContent();
}
```

### 4. Complex Interactions

For multi-step operations:

```javascript
async deployStrategy(strategyId, lots) {
  await this.getStrategyCard(strategyId).click();
  await this.deployButton.click();
  await this.waitForTestId('strategy-deploy-modal');
  await this.deployLotsInput.fill(lots.toString());
  await this.deployConfirmButton.click();
  await this.waitForTestId('deploy-success-message');
}
```

## Example Page Object

```javascript
import { BasePage } from './BasePage.js';

export class PositionsPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/positions';
  }

  // ============ Selectors ============
  get pageContainer() { return this.getByTestId('positions-page'); }
  get dayButton() { return this.getByTestId('positions-day-button'); }
  get netButton() { return this.getByTestId('positions-net-button'); }
  get positionsTable() { return this.getByTestId('positions-table'); }
  get exitModal() { return this.getByTestId('positions-exit-modal'); }
  get exitConfirmButton() { return this.getByTestId('positions-exit-confirm-button'); }

  getExitButton(tradingsymbol) {
    return this.getByTestId(`positions-exit-button-${tradingsymbol}`);
  }

  getPositionRow(tradingsymbol) {
    return this.getByTestId(`positions-row-${tradingsymbol}`);
  }

  // ============ Actions ============
  async waitForPageLoad() {
    await this.waitForTestId('positions-page');
    await this.waitForLoad();
  }

  async switchToDay() {
    await this.dayButton.click();
  }

  async switchToNet() {
    await this.netButton.click();
  }

  async clickExit(tradingsymbol) {
    await this.getExitButton(tradingsymbol).click();
  }

  async confirmExit() {
    await this.exitConfirmButton.click();
  }

  // ============ Data Getters ============
  async getPositionCount() {
    return await this.page.locator('[data-testid^="positions-row-"]').count();
  }

  async isPositionVisible(tradingsymbol) {
    return await this.getPositionRow(tradingsymbol).isVisible();
  }
}
```

## Do's and Don'ts

### ✅ DO
- Extend BasePage
- Set `this.url` property
- Use `getByTestId()` for all selectors
- Return locators from getter methods
- Create action methods for interactions
- Use async/await for all page interactions

### ❌ DON'T
- Hardcode selectors (use `getByTestId()`)
- Add `expect()` assertions in Page Objects
- Use CSS classes or text selectors
- Create Page Objects without `this.url`
- Use synchronous methods for page interactions
