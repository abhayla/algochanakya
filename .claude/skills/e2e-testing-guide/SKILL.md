---
name: e2e-testing-guide
description: Reference guide for writing and reviewing AlgoChanakya E2E tests. Covers market-aware assertion patterns, required helpers, anti-patterns, and screen-specific guidance. Use when writing, reviewing, or auditing Playwright specs.
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: testing
  created_by: skill-evolver
  created_from: user-request
---

# E2E Testing Guide

**Purpose:** This skill is the single authoritative reference for E2E test quality in AlgoChanakya. It codifies patterns that prevent silent-pass tests, tautological assertions, mocked data in non-error paths, and zero-assertion tests — the four most common violations found in practice.

## When to Use

- Writing new E2E specs (after generating with `e2e-test-generator`)
- Reviewing existing specs for anti-patterns
- Auditing test files to enforce `docs/testing/e2e-test-rules.md`
- On explicit invocation: "e2e testing guide", "test patterns", "e2e review"

## When NOT to Use

- Generating new tests → use `e2e-test-generator`
- Fixing failing tests → use `test-fixer`
- Running tests → use `run-tests`

---

## Testing Philosophy

1. **Real data only.** Never mock broker data. Tests MUST exercise real API responses. The only exception: error-path tests that need a specific HTTP error code that cannot be triggered in dev (e.g., 400 from Strike Finder with delta > 1).
2. **Every path must assert.** An `if` block without an `else` is a silent skip. The else branch MUST assert something — either the empty state or a skip with `test.skip()`.
3. **Market-aware strictness.** During `LIVE` / `LAST_KNOWN` hours, data MUST be present — fail if not. During `PRE_OPEN` / `CLOSED`, accept either data or empty state using `assertDataOrEmptyState`.
4. **No error swallowing.** `.catch(() => false)` hides real failures. Use `await locator.isVisible()` (which never throws) instead.

---

## Market-Aware Assertion Pattern

This is the canonical pattern for any test that checks live data.

```js
import { getDataExpectation, assertDataOrEmptyState } from '../../helpers/market-status.helper.js';
import { assertValidPrice, assertLocatorIsValidPrice } from '../../helpers/assertions.js';
import { waitForApiResponse } from '../../helpers/wait-helpers.js';

const expectation = getDataExpectation();
// Returns: 'LIVE' | 'LAST_KNOWN' | 'PRE_OPEN' | 'CLOSED'

if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
  // Data MUST be present. Fail the test if it isn't.
  await expect(optionChainPage.table).toBeVisible();
  // ... strict data assertions
} else {
  // PRE_OPEN or CLOSED — either data or empty state is acceptable
  await assertDataOrEmptyState(page, 'optionchain-table', 'optionchain-empty-state', expect);
}
```

### Expectation meanings

| Value | When | Test behaviour |
|-------|------|----------------|
| `LIVE` | Market open (9:15–15:30 IST, weekday, non-holiday) | Data MUST be present. Hard fail if empty. |
| `LAST_KNOWN` | After close on a trading day | Previous session data available. Fail if empty. |
| `PRE_OPEN` | 9:00–9:15 IST on trading day | Data may be partial. Accept data OR empty. |
| `CLOSED` | Weekend or holiday | Historical only. Accept data OR empty. |

---

## Required Helpers

All helpers live in `tests/e2e/helpers/`. Import them directly — do not re-implement inline.

### `assertDataOrEmptyState(page, dataTestId, emptyTestId, expect)`
Source: `market-status.helper.js`

Asserts that EITHER the data element OR the empty-state element is visible. Throws a descriptive error (including market state) if neither is visible. Use this as the `else` branch in market-aware checks.

```js
await assertDataOrEmptyState(page, 'optionchain-table', 'optionchain-empty-state', expect);
```

### `assertValidPrice(text, context)`
Source: `assertions.js`

Asserts a string is a real numeric price — not `--`, `0.00`, `N/A`, `null`, `undefined`, or empty. Fails with a descriptive message naming the `context`.

```js
const spotText = await optionChainPage.spotPrice.textContent();
assertValidPrice(spotText, 'spot price');
```

### `assertLocatorIsValidPrice(locator, context)`
Source: `assertions.js`

Reads text content of a locator and calls `assertValidPrice`. Cleaner for single-locator cases.

```js
await assertLocatorIsValidPrice(optionChainPage.spotPrice, 'spot price');
```

### `waitForApiResponse(page, urlPattern, options?)`
Source: `wait-helpers.js`

Waits for a real API response matching a URL pattern. Replaces mocked routes in non-error tests.

```js
await optionChainPage.searchStrike();
const response = await waitForApiResponse(page, '/api/optionchain/find-by-delta', { timeout: 10000 });
expect(response.status()).toBe(200);
```

---

## Anti-Pattern Quick Reference

| Anti-pattern | Fix |
|---|---|
| `.catch(() => false)` | Use `await locator.isVisible()` — never throws |
| `if (hasData) { assert }` with no else | Add `else { assertDataOrEmptyState(...) }` |
| `page.route()` in non-error tests | Remove mock; use `waitForApiResponse` with live API |
| `expect(count >= 0).toBe(true)` | `expect(count).toBeGreaterThan(0)` |
| `expect(typeof x).toBe('boolean')` | Assert the actual value: `.toBe(true)` or `.toBe(false)` |
| Zero assertions in test body | Add at least one `expect(...)` call |
| `warnings.warn(...)` instead of skip | `pytest.skip(...)` for infrastructure limits |

Full before/after examples: [`references/anti-patterns.md`](references/anti-patterns.md)

---

## Screen: Option Chain

### Spot Price
```js
// WRONG
expect(spotPriceText.length).toBeGreaterThan(0); // passes for "--"

// RIGHT
assertValidPrice(spotPriceText, 'spot price');
// OR
await assertLocatorIsValidPrice(optionChainPage.spotPrice, 'spot price');
```

### PCR / Max Pain
```js
const pcrValue = parseFloat(pcrText);
// WRONG: expect(pcrValue).toBeGreaterThan(0); — fails outside market hours
// RIGHT (market-aware):
if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
  expect(pcrValue).toBeGreaterThan(0);
  expect(pcrValue).toBeLessThan(10); // PCR > 10 is anomalous
} else {
  // PRE_OPEN/CLOSED: accept any numeric value including 0
  expect(isNaN(pcrValue)).toBe(false);
}
```

### ATM Detection
```js
// WRONG
const hasTable = await optionChainPage.table.isVisible().catch(() => false);
if (hasTable) { /* assert ATM */ }  // silent pass if no table

// RIGHT
const expectation = getDataExpectation();
if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
  await expect(optionChainPage.table).toBeVisible();
  const atmRow = optionChainPage.table.locator('[data-atm-row]');
  const atmBadge = optionChainPage.table.locator('[data-testid="optionchain-atm-badge"]');
  const hasAtm = await atmRow.count() > 0 || await atmBadge.count() > 0;
  expect(hasAtm).toBe(true);
} else {
  await assertDataOrEmptyState(page, 'optionchain-table', 'optionchain-empty-state', expect);
}
```

### WebSocket Live Dot
```js
// WRONG
expect(typeof hasLiveDot).toBe('boolean'); // always passes

// RIGHT
const expectation = getDataExpectation();
if (expectation === 'LIVE') {
  expect(hasLiveDot).toBe(true);
} else {
  // Outside market hours WebSocket may not be streaming — either is valid
  expect(typeof hasLiveDot).toBe('boolean'); // allowed only here
}
```

### Strike Finder (live API)
```js
// WRONG — uses page.route() mock
await page.route('**/api/optionchain/find-by-delta', async (route) => {
  await route.fulfill({ status: 200, body: JSON.stringify({ strike: 24500, ... }) });
});

// RIGHT — live API with waitForApiResponse
const expectation = getDataExpectation();
if (expectation === 'PRE_OPEN' || expectation === 'CLOSED') {
  test.skip('Strike Finder requires live market data');
}
await optionChainPage.searchStrike();
const response = await waitForApiResponse(page, '/api/optionchain/find-by-delta');
expect(response.status()).toBe(200);
const result = await response.json();
expect(result.strike).toMatch(/^\d+$/);         // numeric string or number
expect(result.ltp).toBeGreaterThan(0);
```

---

## Output Format

When reviewing a spec file, produce a violation report:

```
FILE: tests/e2e/specs/optionchain/optionchain.happy.spec.js
VIOLATIONS:
  Line 58-60: .catch(() => false) + silent conditional — replace with market-aware pattern
  Line 85:    expect(ceCount >= 0).toBe(true) — tautological; always passes

FIXES APPLIED: 2
```

---

## Integration

- **Upstream:** `e2e-test-generator` (generates test stubs that this guide helps fill out correctly)
- **Downstream:** `test-fixer` (when tests fail after applying these patterns), `post-fix-pipeline`
- **Data:** None (no knowledge.db tables)

---

## References

- `tests/e2e/helpers/market-status.helper.js` — `getDataExpectation`, `assertDataOrEmptyState`
- `tests/e2e/helpers/assertions.js` — `assertValidPrice`, `assertLocatorIsValidPrice`
- `tests/e2e/helpers/wait-helpers.js` — `waitForApiResponse`
- `docs/testing/e2e-test-rules.md` — project E2E rules (SSOT)
- Anti-pattern catalog: [`references/anti-patterns.md`](references/anti-patterns.md)
