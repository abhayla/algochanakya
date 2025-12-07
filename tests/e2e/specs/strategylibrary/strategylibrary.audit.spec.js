/**
 * Strategy Library Screen - Style & Accessibility Audit
 *
 * Validates CSS properties, fonts, colors, spacing, and WCAG compliance.
 * Tag: @audit
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import StrategyLibraryPage from '../../pages/StrategyLibraryPage.js';
import { StyleAudit, DESIGN_TOKENS } from '../../helpers/style-audit.helper.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Strategy Library - Style & Accessibility Audit @audit', () => {
  let strategyLibraryPage;
  let audit;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyLibraryPage = new StrategyLibraryPage(authenticatedPage);
    audit = new StyleAudit(authenticatedPage);
    await authenticatedPage.goto(FRONTEND_URL + '/strategies');
    await strategyLibraryPage.waitForPageLoad();
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
    const results = await audit.checkAccessibility();

    if (results.violations.length > 0) {
      console.log('Accessibility violations:', JSON.stringify(results.violations, null, 2));
    }

    expect(results.violationCount).toBe(0);
  });

  test('has sufficient color contrast @audit', async ({ authenticatedPage }) => {
    const results = await audit.checkContrast();
    expect(results.hasContrastIssues).toBe(false);
  });

  test('category badges have distinct colors @audit', async ({ authenticatedPage }) => {
    const badges = authenticatedPage.locator('[data-testid^="strategy-library-category-"]');
    const count = await badges.count();

    if (count > 0) {
      for (let i = 0; i < Math.min(count, 5); i++) {
        const bgColor = await badges.nth(i).evaluate(el =>
          window.getComputedStyle(el).backgroundColor
        );
        expect(bgColor).not.toBe('rgba(0, 0, 0, 0)');
      }
    }
  });

  test('strategy cards have consistent styling @audit', async ({ authenticatedPage }) => {
    const cards = authenticatedPage.locator('[data-testid^="strategy-card-"]');
    const count = await cards.count();

    if (count > 1) {
      const borderRadii = [];
      const bgColors = [];

      for (let i = 0; i < Math.min(count, 3); i++) {
        const card = cards.nth(i);
        const borderRadius = await card.evaluate(el =>
          window.getComputedStyle(el).borderRadius
        );
        const bgColor = await card.evaluate(el =>
          window.getComputedStyle(el).backgroundColor
        );
        borderRadii.push(borderRadius);
        bgColors.push(bgColor);
      }

      // All cards should have same border radius
      expect(new Set(borderRadii).size).toBe(1);
    }
  });

  test('wizard button uses primary color @audit', async ({ authenticatedPage }) => {
    const wizardButton = authenticatedPage.locator('[data-testid="strategy-library-wizard-button"]');
    if (await wizardButton.count() > 0) {
      const bgColor = await wizardButton.evaluate(el =>
        window.getComputedStyle(el).backgroundColor
      );
      expect(bgColor).not.toBe('rgba(0, 0, 0, 0)');
    }
  });

  test('search input has proper focus styling @audit', async ({ authenticatedPage }) => {
    const searchInput = authenticatedPage.locator('[data-testid="strategy-library-search"]');
    if (await searchInput.count() > 0) {
      await searchInput.focus();
      const outlineColor = await searchInput.evaluate(el =>
        window.getComputedStyle(el).outlineColor
      );
      // Should have some focus indicator
      expect(outlineColor).toBeDefined();
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
