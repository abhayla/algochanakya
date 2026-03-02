/**
 * Watchlist Screen - Style & Accessibility Audit
 *
 * Validates CSS properties, fonts, colors, spacing, and WCAG compliance.
 * Tag: @audit
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { WatchlistPage } from '../../pages/WatchlistPage.js';
import { StyleAudit, DESIGN_TOKENS } from '../../helpers/style-audit.helper.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Watchlist - Style & Accessibility Audit @audit', () => {
  let watchlistPage;
  let audit;

  test.beforeEach(async ({ authenticatedPage }) => {
    watchlistPage = new WatchlistPage(authenticatedPage);
    audit = new StyleAudit(authenticatedPage);
    await authenticatedPage.goto(FRONTEND_URL + '/watchlist');
    await watchlistPage.waitForPageLoad();
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
      exclude: ['[data-testid*="ltp"]', '[data-testid*="change"]'], // Live prices may be dynamic
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

  test('search input has proper styling @audit', async ({ authenticatedPage }) => {
    const searchInput = authenticatedPage.locator('[data-testid="watchlist-search-input"]');
    if (await searchInput.count() > 0) {
      const borderColor = await searchInput.evaluate(el =>
        window.getComputedStyle(el).borderColor
      );
      expect(borderColor).not.toBe('rgba(0, 0, 0, 0)');
    }
  });

  test('tabs have consistent styling @audit', async ({ authenticatedPage }) => {
    const tabs = authenticatedPage.locator('[data-testid="watchlist-tabs"] button');
    const count = await tabs.count();

    if (count > 0) {
      // All tabs should have consistent font size
      const fontSizes = [];
      for (let i = 0; i < count; i++) {
        const fontSize = await tabs.nth(i).evaluate(el =>
          window.getComputedStyle(el).fontSize
        );
        fontSizes.push(fontSize);
      }
      // All font sizes should be the same
      expect(new Set(fontSizes).size).toBe(1);
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
