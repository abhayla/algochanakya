/**
 * Shared Playwright assertion helpers for E2E tests.
 *
 * Eliminates repeated assertion patterns across spec files.
 *
 * Usage:
 *   import { assertOneOfVisible, assertNoHorizontalScroll, assertValidPrice } from '../helpers/assertions.js'
 */

import { expect } from '@playwright/test'

// ─────────────────────────────────────────────────────────────────────────────
// Visibility
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Assert that at least one of the given locators is visible.
 * Useful for "shows table OR empty state" patterns.
 *
 * @param  {...import('@playwright/test').Locator} locators
 *
 * Usage:
 *   await assertOneOfVisible(page.locator('[data-testid="positions-table"]'), page.locator('[data-testid="positions-empty"]'))
 */
export async function assertOneOfVisible(...locators) {
  const results = await Promise.all(
    locators.map((l) => l.isVisible().catch(() => false))
  )
  const anyVisible = results.some(Boolean)
  expect(anyVisible, `Expected at least one of ${locators.length} elements to be visible`).toBe(true)
}

/**
 * Assert that none of the given locators are visible.
 *
 * @param  {...import('@playwright/test').Locator} locators
 */
export async function assertNoneVisible(...locators) {
  for (const locator of locators) {
    const visible = await locator.isVisible().catch(() => false)
    expect(visible, `Expected element to be hidden but it was visible`).toBe(false)
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Layout / overflow
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Assert there is no horizontal scrollbar (content fits viewport).
 *
 * @param {import('@playwright/test').Page} page
 */
export async function assertNoHorizontalScroll(page) {
  const hasOverflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth
  })
  expect(hasOverflow, 'Page has horizontal overflow (content wider than viewport)').toBe(false)
}

/**
 * Assert there are no JavaScript console errors on the page.
 * Call this at the end of critical happy path tests.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string[]} allowList - Error substrings to ignore
 */
export async function assertNoConsoleErrors(page, allowList = []) {
  const errors = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text()
      if (!allowList.some((allowed) => text.includes(allowed))) {
        errors.push(text)
      }
    }
  })
  // Give the page a moment to emit any pending errors
  await page.waitForTimeout(500)
  expect(errors, `Console errors found:\n${errors.join('\n')}`).toHaveLength(0)
}

// ─────────────────────────────────────────────────────────────────────────────
// Price / data quality
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Assert that a text value represents a real numeric price (not a placeholder).
 *
 * Fails if value is: "--", "0.00", "N/A", "null", "undefined", or empty.
 *
 * @param {string} text - Raw text content from the page
 * @param {string} context - Descriptive label for failure messages
 */
export function assertValidPrice(text, context = 'price') {
  const cleaned = (text || '').replace(/[₹,\s]/g, '').trim()
  expect(cleaned, `${context}: text is empty`).not.toBe('')
  expect(cleaned, `${context}: "${text}" looks like a placeholder`).not.toMatch(
    /^(-{1,2}|0\.00|N\/A|undefined|null|loading)$/i
  )
  const num = parseFloat(cleaned)
  expect(isNaN(num), `${context}: "${text}" is not a valid number`).toBe(false)
  expect(num, `${context}: price=${num} is not > 0`).toBeGreaterThan(0)
}

/**
 * Get the text content of a locator and assert it is a valid price.
 *
 * @param {import('@playwright/test').Locator} locator
 * @param {string} context - Descriptive label for failure messages
 */
export async function assertLocatorIsValidPrice(locator, context = 'price') {
  const text = await locator.textContent()
  assertValidPrice(text, context)
}

// ─────────────────────────────────────────────────────────────────────────────
// Navigation
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Assert page navigates to expected URL (supports partial match).
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} urlFragment - Substring expected in URL
 */
export async function assertNavigatedTo(page, urlFragment) {
  await expect(page).toHaveURL(new RegExp(urlFragment.replace(/\//g, '\\/')))
}

/**
 * Assert the page title matches.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string|RegExp} expected
 */
export async function assertPageTitle(page, expected) {
  await expect(page).toHaveTitle(expected)
}
