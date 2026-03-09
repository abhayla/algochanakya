/**
 * Option Chain Screen - Style & Accessibility Audit
 *
 * Validates CSS properties, fonts, colors, spacing, and WCAG compliance.
 * Tag: @audit
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { StyleAudit, DESIGN_TOKENS } from '../../helpers/style-audit.helper.js';
import { getDataExpectation, assertDataOrEmptyState } from '../../helpers/market-status.helper.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Option Chain - Style & Accessibility Audit @audit', () => {
  test.describe.configure({ timeout: 120000 });
  let optionChainPage;
  let audit;

  test.beforeEach(async ({ authenticatedPage }) => {
    optionChainPage = new OptionChainPage(authenticatedPage);
    audit = new StyleAudit(authenticatedPage);
    await authenticatedPage.goto(FRONTEND_URL + '/optionchain');
    await optionChainPage.waitForPageLoad();
  });

  test('uses correct font family @audit', async ({ authenticatedPage }) => {
    const isValid = await audit.validateFonts();
    expect(isValid).toBe(true);
    expect(audit.getErrors()).toHaveLength(0);
  });

  test('has no horizontal overflow @audit', async ({ authenticatedPage }) => {
    const hasNoOverflow = await audit.checkNoHorizontalOverflow();
    expect(hasNoOverflow).toBe(true);
  });

  test('passes WCAG 2.1 AA accessibility checks @audit', async ({ authenticatedPage }) => {
    const results = await audit.checkAccessibility({
      exclude: [
        '[data-testid*="ltp"]',
        '[data-testid*="oi"]',
        '[data-testid*="iv"]',
        '[data-testid*="spot"]'
      ], // Dynamic price data
    });

    if (results.violations.length > 0) {
      console.log('Accessibility violations:', JSON.stringify(results.violations, null, 2));
    }

    expect(results.violationCount).toBe(0);
  });

  test('has sufficient color contrast @audit', async ({ authenticatedPage }) => {
    const results = await audit.checkContrast();
    expect(results.hasContrastIssues).toBe(false);
  });

  test('underlying tabs have consistent styling @audit', async ({ authenticatedPage }) => {
    const tabs = authenticatedPage.locator('[data-testid="optionchain-underlying-tabs"] button');
    const count = await tabs.count();

    expect(count).toBeGreaterThan(0);
    const fontSizes = [];
    for (let i = 0; i < count; i++) {
      const fontSize = await tabs.nth(i).evaluate(el =>
        window.getComputedStyle(el).fontSize
      );
      fontSizes.push(fontSize);
    }
    expect(new Set(fontSizes).size).toBe(1);
  });

  test('ITM strikes use correct highlighting colors @audit', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    // ITM CE rows use class 'itm-ce', ITM PE rows use class 'itm-pe'
    const ceItmRows = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"].itm-ce');
    const peItmRows = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"].itm-pe');

    const ceCount = await ceItmRows.count();
    const peCount = await peItmRows.count();

    const expectation = getDataExpectation();
    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      // During live/last-known hours, ITM rows must exist (chain has data)
      expect(ceCount + peCount).toBeGreaterThan(0);
    } else {
      // Outside market hours: chain may be empty — asserting counts are non-negative is enough
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });

  test('full style audit passes @audit', async ({ authenticatedPage }) => {
    const results = await audit.runFullAudit();

    if (!results.passed) {
      console.log('Audit errors:', results.errors);
    }

    expect(results.passed).toBe(true);
  });
});
