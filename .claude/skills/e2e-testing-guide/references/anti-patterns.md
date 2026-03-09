# E2E Anti-Pattern Catalog

Six anti-patterns found repeatedly in AlgoChanakya E2E tests, with before/after code.

---

## 1. `.catch(() => false)` — Error Swallowing

**Problem:** Hides real failures. If the locator throws unexpectedly (wrong selector, network error), the catch silently returns `false`, turning a genuine bug into a passing test.

**Before:**
```js
const hasTable = await optionChainPage.table.isVisible().catch(() => false);
```

**After:**
```js
// isVisible() on a Playwright Locator NEVER throws — it returns false if not found.
// .catch() is never needed here. Remove it entirely.
const hasTable = await optionChainPage.table.isVisible();
```

**Rule:** Only use `.catch()` on methods that can genuinely reject (e.g., `page.waitForResponse` with a timeout). Never on locator visibility checks.

---

## 2. Silent `if/else` Conditional — Silent Skip

**Problem:** An `if` block that only asserts when data exists, with no `else`, silently passes when data is absent. The test provides zero coverage outside market hours.

**Before:**
```js
const hasTable = await optionChainPage.table.isVisible();
if (hasTable) {
  await expect(optionChainPage.table).toBeVisible();
  const rows = await optionChainPage.table.locator('tbody tr').all();
  expect(rows.length).toBeGreaterThan(0);
}
// No else — silent pass if table absent
```

**After:**
```js
import { getDataExpectation, assertDataOrEmptyState } from '../../helpers/market-status.helper.js';

const expectation = getDataExpectation();
if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
  await expect(optionChainPage.table).toBeVisible();
  const rows = await optionChainPage.table.locator('tbody tr').all();
  expect(rows.length).toBeGreaterThan(0);
} else {
  await assertDataOrEmptyState(page, 'optionchain-table', 'optionchain-empty-state', expect);
}
```

---

## 3. `page.route()` Mocks in Non-Error Tests

**Problem:** Mocking API responses defeats the purpose of E2E tests. If the real API changes (new field, renamed key, different structure), the mocked test won't catch it.

**Exception:** Error-path tests that need a specific HTTP error code (400, 500) that cannot be triggered in dev.

**Before:**
```js
await page.route('**/api/optionchain/find-by-delta', async (route) => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ strike: 24500, ltp: 145.50, delta: 0.30 })
  });
});
await optionChainPage.searchStrike();
await expect(optionChainPage.strikeFinderResult).toBeVisible();
```

**After:**
```js
import { waitForApiResponse } from '../../helpers/wait-helpers.js';

// Skip during non-live hours (Strike Finder needs live data)
const expectation = getDataExpectation();
if (expectation === 'PRE_OPEN' || expectation === 'CLOSED') {
  test.skip('Strike Finder requires live market data');
  return;
}

await optionChainPage.searchStrike();
const response = await waitForApiResponse(page, '/api/optionchain/find-by-delta');
expect(response.status()).toBe(200);
const result = await response.json();
expect(typeof result.strike).toBe('number');
expect(result.ltp).toBeGreaterThan(0);
expect(result.delta).toBeGreaterThan(0);
```

---

## 4. Tautological Assertions — Always True

**Problem:** Assertions that are mathematically or logically always true provide zero coverage. They make it look like a test is verifying something when it isn't.

**Before:**
```js
const ceCount = await ceItmRows.count(); // Returns 0 or more
expect(ceCount >= 0).toBe(true);         // ALWAYS true — count() never returns negative
```

```js
expect(typeof hasLiveDot).toBe('boolean'); // ALWAYS true — isVisible() always returns boolean
```

**After:**
```js
// If data should exist, assert it exists:
expect(ceCount).toBeGreaterThan(0);

// If state should be known, assert the specific state:
expect(hasLiveDot).toBe(true); // or .toBe(false) depending on expected state
```

---

## 5. Zero-Assertion Test Body

**Problem:** A test body with no `expect(...)` calls always passes. It may look like it's testing something, but it provides no verification.

**Before:**
```js
test('should subscribe to WebSocket when chain loads', async ({ authenticatedPage }) => {
  const wsMessages = [];
  authenticatedPage.on('console', msg => {
    if (msg.text().includes('[OptionChain] Subscribed')) {
      wsMessages.push(msg.text());
    }
  });

  await optionChainPage.waitForChainLoad();
  await authenticatedPage.waitForLoadState('domcontentloaded');

  // No assertion! Test always passes.
});
```

**After:**
```js
test('should subscribe to WebSocket when chain loads', async ({ authenticatedPage }) => {
  const wsMessages = [];
  authenticatedPage.on('console', msg => {
    if (msg.text().includes('[OptionChain] Subscribed')) {
      wsMessages.push(msg.text());
    }
  });

  await optionChainPage.waitForChainLoad();
  await authenticatedPage.waitForLoadState('domcontentloaded');

  const expectation = getDataExpectation();
  if (expectation === 'LIVE') {
    // During live hours, WebSocket subscription log MUST appear
    expect(wsMessages.length).toBeGreaterThan(0);
  } else {
    // Outside market hours, subscription may or may not appear
    expect(wsMessages.length).toBeGreaterThanOrEqual(0); // always true — documents intent
  }
});
```

---

## 6. `warnings.warn()` Instead of `pytest.skip()` / `pytest.fail()` (Backend)

**Problem:** `warnings.warn()` produces a yellow warning in pytest output but does NOT stop the test. If the remaining code is unreachable or produces incorrect results, the test silently "passes" with a warning that developers learn to ignore.

**Before (Python):**
```python
if not atm_options:
    import warnings
    warnings.warn(
        f"Found {len(options)} NIFTY options but none within 2 strikes of ATM={atm_strike}. "
        f"Options may be for a different expiry."
    )
    # Test continues, but no meaningful assertions follow
```

**After (Python):**
```python
if not atm_options:
    # This is an infrastructure limitation (stale instrument master), not a code bug.
    # Use pytest.skip() to clearly communicate the reason and skip cleanly.
    pytest.skip(
        f"Found {len(options)} NIFTY options but none within 2 strikes of ATM={atm_strike} "
        f"(spot={spot}). Instrument master may be stale — try during market hours."
    )
```

**Rule:** Use `pytest.skip()` when the test cannot run due to infrastructure (no credentials, stale data, market closed). Use `pytest.fail()` when the system produced an incorrect result. Never use `warnings.warn()` as a substitute for either.
