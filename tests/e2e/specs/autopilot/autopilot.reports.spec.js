/**
 * AutoPilot Phase 4 - Reports E2E Tests
 *
 * Tests for report generation, viewing, and download functionality.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotReportsPage } from '../../pages/AutoPilotDashboardPage.js';


// =============================================================================
// REPORTS - HAPPY PATH
// =============================================================================

test.describe('AutoPilot Reports - Happy Path', () => {
  let reportsPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    reportsPage = new AutoPilotReportsPage(authenticatedPage);
    await reportsPage.navigate();
    await reportsPage.waitForPageLoad();
  });

  test('displays reports page', async () => {
    await expect(reportsPage.reportsPage).toBeVisible();
    await expect(reportsPage.reportsHeader).toBeVisible();
  });

  test('displays reports list', async () => {
    await expect(reportsPage.reportsList).toBeVisible();
  });

  test('displays generate report button', async () => {
    await expect(reportsPage.generateButton).toBeVisible();
  });

  test('opens generate report modal', async () => {
    await reportsPage.openGenerateModal();
    await expect(reportsPage.generateModal).toBeVisible();
  });

  test('generates a report', async () => {
    await reportsPage.generateReport({
      name: 'Test P&L Report',
      type: 'pnl', // Vue uses 'pnl', 'monthly', 'strategy', 'tax'
      startDate: '2024-01-01',
      endDate: '2024-12-31'
    });
  });

  test('views report details', async () => {
    const count = await reportsPage.getReportCount();
    if (count > 0) {
      const firstRow = reportsPage.reportRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const reportId = testId.replace('autopilot-report-row-', '');
      await reportsPage.openReport(reportId);
      await expect(reportsPage.reportDetailsPage).toBeVisible();
    }
  });

  test('displays report summary section', async () => {
    const count = await reportsPage.getReportCount();
    if (count > 0) {
      const firstRow = reportsPage.reportRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const reportId = testId.replace('autopilot-report-row-', '');
      await reportsPage.openReport(reportId);
      await expect(reportsPage.summarySection).toBeVisible();
    }
  });

  test('downloads report as PDF', async () => {
    const count = await reportsPage.getReportCount();
    if (count > 0) {
      const firstRow = reportsPage.reportRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const reportId = testId.replace('autopilot-report-row-', '');
      await reportsPage.openReport(reportId);
      await reportsPage.downloadAsPdf();
    }
  });

  test('downloads report as Excel', async () => {
    const count = await reportsPage.getReportCount();
    if (count > 0) {
      const firstRow = reportsPage.reportRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const reportId = testId.replace('autopilot-report-row-', '');
      await reportsPage.openReport(reportId);
      await reportsPage.downloadAsExcel();
    }
  });

  test('opens tax summary tab', async () => {
    await reportsPage.openTaxSummary();
    await expect(reportsPage.taxSummary).toBeVisible();
  });

  test('generates tax report', async () => {
    await reportsPage.openTaxSummary();
    await reportsPage.generateTaxReport('2024-25');
  });
});


// =============================================================================
// REPORTS - EDGE CASES
// =============================================================================

test.describe('AutoPilot Reports - Edge Cases', () => {
  let reportsPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    reportsPage = new AutoPilotReportsPage(authenticatedPage);
    await reportsPage.navigate();
    await reportsPage.waitForPageLoad();
  });

  test('cancels report generation', async () => {
    await reportsPage.openGenerateModal();
    await reportsPage.cancelGenerate();
    await expect(reportsPage.generateModal).not.toBeVisible();
  });

  test('handles invalid date range validation', async () => {
    await reportsPage.openGenerateModal();
    await reportsPage.startDate.fill('2024-12-31');
    await reportsPage.endDate.fill('2024-01-01');
    await reportsPage.submitButton.click();
    // Should show validation error
    await expect(reportsPage.validationError).toBeVisible();
  });

  test('filters reports by type', async () => {
    await reportsPage.filterByType('pnl');
    await expect(reportsPage.reportsPage).toBeVisible();
  });

  test('sorts reports by date', async () => {
    await reportsPage.sortByDate();
    await expect(reportsPage.reportsPage).toBeVisible();
  });

  test('handles pagination if available', async () => {
    const pagination = reportsPage.pagination;
    if (await pagination.isVisible()) {
      const nextButton = pagination.locator('[data-testid="pagination-next"]');
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        await reportsPage.page.waitForLoadState('networkidle');
      }
    }
  });

  test('deletes a report', async () => {
    const count = await reportsPage.getReportCount();
    if (count > 0) {
      const firstRow = reportsPage.reportRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const reportId = testId.replace('autopilot-report-row-', '');
      await reportsPage.deleteReport(reportId);
    }
  });
});
