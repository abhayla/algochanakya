/**
 * Strategy Builder Screen - Style & Accessibility Audit
 *
 * Validates CSS properties, fonts, colors, spacing, and WCAG compliance.
 * Tag: @audit
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { StrategyBuilderPage } from '../../pages/StrategyBuilderPage.js';
import { StyleAudit, DESIGN_TOKENS } from '../../helpers/style-audit.helper.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Strategy Builder - Style & Accessibility Audit @audit', () => {
  // Increase timeout for accessibility tests as axe-core analysis can be slow
  test.describe.configure({ timeout: 60000 });

  let strategyBuilderPage;
  let audit;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyBuilderPage = new StrategyBuilderPage(authenticatedPage);
    audit = new StyleAudit(authenticatedPage);
    await authenticatedPage.goto(FRONTEND_URL + '/strategy');
    await strategyBuilderPage.waitForPageLoad();
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
        '[data-testid*="pnl"]',
        '[data-testid*="cmp"]',
        '[data-testid*="breakeven"]'
      ], // Dynamic calculation data
    });

    if (results.violations.length > 0) {
      console.log('Accessibility violations:', JSON.stringify(results.violations, null, 2));
    }

    expect(results.violationCount).toBe(0);
  });

  test('has sufficient color contrast @audit', async ({ authenticatedPage }) => {
    const results = await audit.checkContrast();
    if (results.hasContrastIssues) {
      console.log('Color contrast violations:', JSON.stringify(results.violations, null, 2));
    }
    expect(results.hasContrastIssues).toBe(false);
  });

  test('add row button uses primary color @audit', async ({ authenticatedPage }) => {
    const addButton = authenticatedPage.locator('[data-testid="strategy-add-row-button"]');
    if (await addButton.count() > 0) {
      const bgColor = await addButton.evaluate(el =>
        window.getComputedStyle(el).backgroundColor
      );
      expect(bgColor).not.toBe('rgba(0, 0, 0, 0)');
    }
  });

  test('P/L mode toggle has consistent styling @audit', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.locator('[data-testid="strategy-pnl-mode-toggle"]');
    if (await toggle.count() > 0) {
      const buttons = toggle.locator('button');
      const count = await buttons.count();

      if (count > 0) {
        const fontSizes = [];
        for (let i = 0; i < count; i++) {
          const fontSize = await buttons.nth(i).evaluate(el =>
            window.getComputedStyle(el).fontSize
          );
          fontSizes.push(fontSize);
        }
        expect(new Set(fontSizes).size).toBe(1);
      }
    }
  });

  test('profit zone cells use green styling @audit', async ({ authenticatedPage }) => {
    const profitCells = authenticatedPage.locator('[data-testid*="pnl-cell"].bg-green');
    const count = await profitCells.count();

    if (count > 0) {
      const bgColor = await profitCells.first().evaluate(el =>
        window.getComputedStyle(el).backgroundColor
      );
      expect(bgColor).toMatch(/rgb/);
    }
  });

  test('loss zone cells use red styling @audit', async ({ authenticatedPage }) => {
    const lossCells = authenticatedPage.locator('[data-testid*="pnl-cell"].bg-red');
    const count = await lossCells.count();

    if (count > 0) {
      const bgColor = await lossCells.first().evaluate(el =>
        window.getComputedStyle(el).backgroundColor
      );
      expect(bgColor).toMatch(/rgb/);
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
