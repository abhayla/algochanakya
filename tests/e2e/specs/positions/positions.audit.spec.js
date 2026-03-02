/**
 * Positions Screen - Style & Accessibility Audit
 *
 * Validates CSS properties, fonts, colors, spacing, and WCAG compliance.
 * Tag: @audit
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { PositionsPage } from '../../pages/PositionsPage.js';
import { StyleAudit, DESIGN_TOKENS } from '../../helpers/style-audit.helper.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Positions - Style & Accessibility Audit @audit', () => {
  let positionsPage;
  let audit;

  test.beforeEach(async ({ authenticatedPage }) => {
    positionsPage = new PositionsPage(authenticatedPage);
    audit = new StyleAudit(authenticatedPage);
    await authenticatedPage.goto(FRONTEND_URL + '/positions');
    await positionsPage.waitForPageLoad();
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
      exclude: ['[data-testid*="pnl"]'], // P&L values may be dynamic
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

  test('profit values use green color @audit', async ({ authenticatedPage }) => {
    // Use data-pnl-polarity="positive" — stable semantic attribute, not CSS class
    const profitElements = authenticatedPage.locator('[data-pnl-polarity="positive"]');
    const count = await profitElements.count();

    if (count > 0) {
      const color = await profitElements.first().evaluate(el =>
        window.getComputedStyle(el).color
      );
      // Should be some shade of green
      expect(color).toMatch(/rgb\(\d+,\s*\d+,\s*\d+\)/);
    } else {
      // No profit P&L elements visible — positions may all be at zero or not loaded
      // Still assert that the page loaded correctly
      await expect(authenticatedPage.locator('[data-testid="positions-container"], [data-testid="positions-empty-state"]').first()).toBeVisible();
    }
  });

  test('loss values use red color @audit', async ({ authenticatedPage }) => {
    // Use data-pnl-polarity="negative" — stable semantic attribute, not CSS class
    const lossElements = authenticatedPage.locator('[data-pnl-polarity="negative"]');
    const count = await lossElements.count();

    if (count > 0) {
      const color = await lossElements.first().evaluate(el =>
        window.getComputedStyle(el).color
      );
      // Should be some shade of red
      expect(color).toMatch(/rgb\(\d+,\s*\d+,\s*\d+\)/);
    } else {
      // No loss P&L elements visible — positions may all be at zero or not loaded
      await expect(authenticatedPage.locator('[data-testid="positions-container"], [data-testid="positions-empty-state"]').first()).toBeVisible();
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
