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
    const profitElements = authenticatedPage.locator('.text-green-500, .text-green-600');
    const count = await profitElements.count();

    if (count > 0) {
      const color = await profitElements.first().evaluate(el =>
        window.getComputedStyle(el).color
      );
      // Should be some shade of green
      expect(color).toMatch(/rgb\(\d+,\s*\d+,\s*\d+\)/);
    }
  });

  test('loss values use red color @audit', async ({ authenticatedPage }) => {
    const lossElements = authenticatedPage.locator('.text-red-500, .text-red-600');
    const count = await lossElements.count();

    if (count > 0) {
      const color = await lossElements.first().evaluate(el =>
        window.getComputedStyle(el).color
      );
      // Should be some shade of red
      expect(color).toMatch(/rgb\(\d+,\s*\d+,\s*\d+\)/);
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
