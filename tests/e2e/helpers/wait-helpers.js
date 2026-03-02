/**
 * Wait Helpers — Event-Driven Replacements for waitForTimeout
 *
 * These helpers replace waitForTimeout calls with deterministic,
 * event-driven waits that are both faster and more reliable.
 *
 * Rule: NEVER use waitForTimeout in tests. Use these helpers instead.
 *
 * Usage:
 *   import { waitForApiResponse, waitForDataInTestId, waitForSearchResults } from '../helpers/wait-helpers.js';
 */

/**
 * Wait for an API response matching a URL pattern.
 * Use after actions that trigger API calls (form submits, button clicks).
 *
 * Replaces: await page.waitForTimeout(1000-2000) after API-triggering actions
 *
 * @param {import('@playwright/test').Page} page
 * @param {string|RegExp} urlPattern - URL pattern to match (e.g. '/api/strategy', /api\/health/)
 * @param {Object} options
 * @param {number} [options.timeout=10000] - Max wait in ms
 * @returns {Promise<import('@playwright/test').Response>}
 *
 * @example
 *   await saveButton.click();
 *   await waitForApiResponse(page, '/api/strategies');
 */
export async function waitForApiResponse(page, urlPattern, { timeout = 10000 } = {}) {
  return await page.waitForResponse(
    (response) => {
      const url = response.url();
      if (typeof urlPattern === 'string') {
        return url.includes(urlPattern);
      }
      return urlPattern.test(url);
    },
    { timeout }
  );
}

/**
 * Wait for an element with a data-testid to contain non-empty text.
 * Use for live data loading — waits until the element has actual content.
 *
 * Replaces: await page.waitForTimeout(2000-3000) after navigating to data screens
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} testId - data-testid attribute value (exact match)
 * @param {Object} options
 * @param {number} [options.timeout=10000] - Max wait in ms
 * @returns {Promise<void>}
 *
 * @example
 *   await positionsPage.navigate();
 *   await waitForDataInTestId(page, 'positions-ltp-12345');
 */
export async function waitForDataInTestId(page, testId, { timeout = 10000 } = {}) {
  const locator = page.locator(`[data-testid="${testId}"]`);
  await locator.waitFor({ state: 'visible', timeout });
  await locator.waitFor({
    state: 'visible',
    timeout,
  });
  // Wait until text is non-empty (not just rendered)
  await page.waitForFunction(
    (id) => {
      const el = document.querySelector(`[data-testid="${id}"]`);
      return el && el.textContent.trim().length > 0;
    },
    testId,
    { timeout }
  );
}

/**
 * Wait for a data-testid prefix to have visible items.
 * Use when waiting for a list of items with dynamic testids (e.g. positions-ltp-*)
 *
 * Replaces: await page.waitForTimeout(2000) before locating ^="testid-" elements
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} testIdPrefix - The testid prefix (matched with ^= selector)
 * @param {Object} options
 * @param {number} [options.minCount=1] - Minimum number of matching elements
 * @param {number} [options.timeout=10000] - Max wait in ms
 * @returns {Promise<void>}
 */
export async function waitForTestIdPrefix(page, testIdPrefix, { minCount = 1, timeout = 10000 } = {}) {
  await page.waitForFunction(
    ({ prefix, min }) => {
      return document.querySelectorAll(`[data-testid^="${prefix}"]`).length >= min;
    },
    { prefix: testIdPrefix, min: minCount },
    { timeout }
  );
}

/**
 * Wait for search results to appear in a dropdown.
 * Handles debounce automatically — waits for the dropdown to become visible.
 *
 * Replaces: await page.waitForTimeout(500-600) after typing in search inputs
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} dropdownTestId - data-testid of the dropdown/results container
 * @param {Object} options
 * @param {number} [options.timeout=8000] - Max wait in ms
 * @returns {Promise<void>}
 *
 * @example
 *   await watchlistPage.searchInput.fill('NIFTY');
 *   await waitForSearchResults(page, 'watchlist-search-dropdown');
 */
export async function waitForSearchResults(page, dropdownTestId, { timeout = 8000 } = {}) {
  await page.locator(`[data-testid="${dropdownTestId}"]`).waitFor({
    state: 'visible',
    timeout,
  });
}

/**
 * Wait for a WebSocket connection to be established.
 * Detects an active WebSocket by waiting for a message event on the URL pattern.
 *
 * Replaces: await page.waitForTimeout(2000-3000) after page load for WS screens
 *
 * @param {import('@playwright/test').Page} page
 * @param {string|RegExp} urlPattern - WebSocket URL pattern
 * @param {Object} options
 * @param {number} [options.timeout=10000] - Max wait in ms
 * @returns {Promise<void>}
 *
 * @example
 *   await watchlistPage.navigate();
 *   await waitForWebSocket(page, '/ws/ticks');
 */
export async function waitForWebSocket(page, urlPattern, { timeout = 10000 } = {}) {
  await page.waitForEvent('websocket', {
    predicate: (ws) => {
      if (typeof urlPattern === 'string') return ws.url().includes(urlPattern);
      return urlPattern.test(ws.url());
    },
    timeout,
  });
}

/**
 * Wait for EITHER of two elements to become visible.
 * Use for "table OR empty state" checks without silent skips.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} testId1 - First element's data-testid
 * @param {string} testId2 - Second element's data-testid
 * @param {Object} options
 * @param {number} [options.timeout=10000] - Max wait in ms
 * @returns {Promise<{first: boolean, second: boolean}>} Which element is visible
 *
 * @example
 *   const { first: hasPositions } = await waitForEitherTestId(page, 'positions-table', 'positions-empty');
 *   if (hasPositions) {
 *     await expect(page.locator('[data-testid="positions-table"]')).toBeVisible();
 *   } else {
 *     await expect(page.locator('[data-testid="positions-empty"]')).toBeVisible();
 *   }
 */
export async function waitForEitherTestId(page, testId1, testId2, { timeout = 10000 } = {}) {
  await page.waitForFunction(
    ({ id1, id2 }) => {
      const el1 = document.querySelector(`[data-testid="${id1}"]`);
      const el2 = document.querySelector(`[data-testid="${id2}"]`);
      const isVisible = (el) => el && el.offsetParent !== null;
      return isVisible(el1) || isVisible(el2);
    },
    { id1: testId1, id2: testId2 },
    { timeout }
  );

  const first = await page.locator(`[data-testid="${testId1}"]`).isVisible().catch(() => false);
  const second = await page.locator(`[data-testid="${testId2}"]`).isVisible().catch(() => false);
  return { first, second };
}

/**
 * Wait for a modal dialog to become visible.
 * Use after clicking buttons that open modals.
 *
 * Replaces: await page.waitForTimeout(300-500) after modal-opening clicks
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} modalTestId - data-testid of the modal element
 * @param {Object} options
 * @param {number} [options.timeout=5000] - Max wait in ms
 * @returns {Promise<import('@playwright/test').Locator>} The modal locator
 *
 * @example
 *   await exitButton.click();
 *   const modal = await waitForModal(page, 'positions-exit-modal');
 */
export async function waitForModal(page, modalTestId, { timeout = 5000 } = {}) {
  const modal = page.locator(`[data-testid="${modalTestId}"]`);
  await modal.waitFor({ state: 'visible', timeout });
  return modal;
}

/**
 * Wait for a dropdown option list to appear and be populated.
 * Use after clicking a select/dropdown that loads options dynamically.
 *
 * Replaces: await page.waitForTimeout(500-1000) after clicking dropdowns
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} optionTestIdPrefix - Prefix of option data-testids
 * @param {Object} options
 * @param {number} [options.timeout=8000] - Max wait in ms
 * @returns {Promise<void>}
 *
 * @example
 *   await underlyingDropdown.click();
 *   await waitForDropdownOptions(page, 'underlying-option-');
 */
export async function waitForDropdownOptions(page, optionTestIdPrefix, { timeout = 8000 } = {}) {
  await page.waitForFunction(
    (prefix) => document.querySelectorAll(`[data-testid^="${prefix}"]`).length > 0,
    optionTestIdPrefix,
    { timeout }
  );
}

/**
 * Wait for a page section to finish loading (spinner gone + content visible).
 * More precise than waitForLoadState for SPA sections.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} contentTestId - data-testid of the content that appears when loaded
 * @param {string} [spinnerTestId] - data-testid of loading spinner (optional)
 * @param {Object} options
 * @param {number} [options.timeout=10000] - Max wait in ms
 * @returns {Promise<void>}
 */
export async function waitForSectionLoad(page, contentTestId, spinnerTestId = null, { timeout = 10000 } = {}) {
  if (spinnerTestId) {
    // Wait for spinner to disappear first
    const spinner = page.locator(`[data-testid="${spinnerTestId}"]`);
    const isVisible = await spinner.isVisible().catch(() => false);
    if (isVisible) {
      await spinner.waitFor({ state: 'hidden', timeout });
    }
  }
  // Then wait for content
  await page.locator(`[data-testid="${contentTestId}"]`).waitFor({ state: 'visible', timeout });
}
