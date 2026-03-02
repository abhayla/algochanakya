/**
 * Login Screen - Style & Accessibility Audit
 *
 * Validates CSS properties, fonts, colors, spacing, and WCAG compliance.
 * Tag: @audit
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { LoginPage } from '../../pages/LoginPage.js';
import { StyleAudit, DESIGN_TOKENS } from '../../helpers/style-audit.helper.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Login - Style & Accessibility Audit @audit', () => {
  let loginPage;
  let audit;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    audit = new StyleAudit(page);
    await page.goto(FRONTEND_URL + '/login');
    await loginPage.waitForPageLoad();
  });

  test('uses correct font family @audit', async () => {
    const isValid = await audit.validateFonts();
    expect(isValid).toBe(true);
    expect(audit.getErrors()).toHaveLength(0);
  });

  test('has no horizontal overflow @audit', async () => {
    const hasNoOverflow = await audit.checkNoHorizontalOverflow();
    expect(hasNoOverflow).toBe(true);
  });

  test('passes WCAG 2.1 AA accessibility checks @audit', async () => {
    const results = await audit.checkAccessibility({
      exclude: ['[data-testid="login-zerodha-button"]'], // May have dynamic state
    });

    // Log violations for debugging
    if (results.violations.length > 0) {
      console.log('Accessibility violations:', JSON.stringify(results.violations, null, 2));
    }

    expect(results.violationCount).toBe(0);
  });

  test('has sufficient color contrast @audit', async () => {
    const results = await audit.checkContrast();
    expect(results.hasContrastIssues).toBe(false);
  });

  test('full style audit passes @audit', async () => {
    const results = await audit.runFullAudit();

    if (!results.passed) {
      console.log('Audit errors:', results.errors);
    }

    expect(results.passed).toBe(true);
  });
});
