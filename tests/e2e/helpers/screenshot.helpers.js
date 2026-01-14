/**
 * Screenshot Helper for E2E Tests
 *
 * Best practice: Take screenshots at each verification step and analyze them
 * to ensure data correctness before marking the test as passed.
 */

import fs from 'fs';
import path from 'path';

const SCREENSHOT_DIR = 'tests/e2e/screenshots';

/**
 * Take a screenshot with timestamp and step name
 * @param {Page} page - Playwright page
 * @param {string} stepName - Name of the step (used in filename)
 * @param {string} subfolder - Optional subfolder for organization
 * @returns {string} Path to the saved screenshot
 */
export async function takeStepScreenshot(page, stepName, subfolder = 'test-run') {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const sanitizedName = stepName.replace(/[^a-zA-Z0-9_-]/g, '_');
  const filename = `${sanitizedName}_${timestamp}.png`;

  const dir = path.join(SCREENSHOT_DIR, subfolder);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  const filepath = path.join(dir, filename);
  await page.screenshot({ path: filepath, fullPage: false });

  console.log(`📸 Screenshot saved: ${filepath}`);
  return filepath;
}

/**
 * Take screenshot and verify specific UI elements are correct
 * @param {Page} page - Playwright page
 * @param {string} stepName - Step name
 * @param {Object} checks - Verification checks to perform
 * @returns {Object} Screenshot info and verification results
 */
export async function takeAndVerifyScreenshot(page, stepName, checks = {}) {
  const screenshot = await takeStepScreenshot(page, stepName);

  const results = {
    screenshot,
    stepName,
    timestamp: new Date().toISOString(),
    checks: {}
  };

  // Perform checks
  if (checks.noErrorBanner) {
    const errorBanner = page.locator('[data-testid="strategy-error"], .bg-red-100.border-red');
    const hasError = await errorBanner.isVisible().catch(() => false);
    results.checks.noErrorBanner = !hasError;
    if (hasError) {
      results.errorText = await errorBanner.textContent().catch(() => 'Unknown error');
    }
  }

  if (checks.hasPayoffChart) {
    const canvas = page.locator('.payoff-chart canvas');
    results.checks.hasPayoffChart = await canvas.isVisible().catch(() => false);
  }

  if (checks.legCount !== undefined) {
    const rows = await page.locator('[data-testid="strategy-table"] tbody tr.leg-row').count();
    results.checks.legCount = rows === checks.legCount;
    results.actualLegCount = rows;
  }

  if (checks.hasSummaryCards) {
    const summaryCards = page.locator('[data-testid="strategy-summary-section"], .summary-cards');
    results.checks.hasSummaryCards = await summaryCards.isVisible().catch(() => false);
  }

  // Log verification results
  const allPassed = Object.values(results.checks).every(v => v === true);
  console.log(`${allPassed ? '✅' : '❌'} ${stepName}: ${JSON.stringify(results.checks)}`);

  return results;
}

/**
 * Create a test report with all screenshots and verifications
 * @param {string} testName - Name of the test
 * @param {Array} steps - Array of step results
 * @param {string} subfolder - Subfolder for the report
 */
export function createTestReport(testName, steps, subfolder = 'test-run') {
  const dir = path.join(SCREENSHOT_DIR, subfolder);
  const reportPath = path.join(dir, 'test-report.json');

  const report = {
    testName,
    timestamp: new Date().toISOString(),
    totalSteps: steps.length,
    passedSteps: steps.filter(s => Object.values(s.checks || {}).every(v => v === true)).length,
    failedSteps: steps.filter(s => !Object.values(s.checks || {}).every(v => v === true)).length,
    steps
  };

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`📋 Test report saved: ${reportPath}`);

  return report;
}
