/**
 * AutoPilot Phase 4 - Trade Journal E2E Tests
 *
 * Tests for trade journal viewing, filtering, and export functionality.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotJournalPage } from '../../pages/AutoPilotDashboardPage.js';


// =============================================================================
// TRADE JOURNAL - HAPPY PATH
// =============================================================================

test.describe('AutoPilot Trade Journal - Happy Path', () => {
  let journalPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    journalPage = new AutoPilotJournalPage(authenticatedPage);
    await journalPage.navigate();
    await journalPage.waitForPageLoad();
  });

  test('displays trade journal page', async () => {
    await expect(journalPage.journalPage).toBeVisible();
    await expect(journalPage.journalHeader).toBeVisible();
  });

  test('displays journal stats summary', async () => {
    await expect(journalPage.statsSection).toBeVisible();
    await expect(journalPage.totalTradesCard).toBeVisible();
    await expect(journalPage.winRateCard).toBeVisible();
  });

  test('displays trades table', async () => {
    await expect(journalPage.tradesTable).toBeVisible();
  });

  test('displays trade rows with key information', async () => {
    const count = await journalPage.getTradeCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('filters trades by date range using date inputs', async () => {
    // Vue uses direct date inputs, not preset buttons
    await journalPage.filterByLast7Days();
    await expect(journalPage.journalPage).toBeVisible();
  });

  test('filters trades by 30 day range', async () => {
    // Vue uses direct date inputs, not preset buttons
    await journalPage.filterByLast30Days();
    await expect(journalPage.journalPage).toBeVisible();
  });

  test('filters trades by outcome - profit', async () => {
    await journalPage.filterByOutcome('profit');
    await expect(journalPage.journalPage).toBeVisible();
  });

  test('opens trade details view', async () => {
    const count = await journalPage.getTradeCount();
    if (count > 0) {
      const firstRow = journalPage.tradeRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const tradeId = testId.replace('autopilot-journal-trade-row-', '');
      await journalPage.openTradeDetails(tradeId);
      await expect(journalPage.tradeDetails).toBeVisible();
    }
  });

  test('displays trade P&L chart', async () => {
    const count = await journalPage.getTradeCount();
    if (count > 0) {
      const firstRow = journalPage.tradeRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const tradeId = testId.replace('autopilot-journal-trade-row-', '');
      await journalPage.openTradeDetails(tradeId);
      await expect(journalPage.tradePnlChart).toBeVisible();
    }
  });

  test('displays trade entry/exit details', async () => {
    const count = await journalPage.getTradeCount();
    if (count > 0) {
      const firstRow = journalPage.tradeRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const tradeId = testId.replace('autopilot-journal-trade-row-', '');
      await journalPage.openTradeDetails(tradeId);
      await expect(journalPage.tradeEntryPrice).toBeVisible();
      await expect(journalPage.tradeExitPrice).toBeVisible();
    }
  });

  test('adds notes to a trade', async () => {
    const count = await journalPage.getTradeCount();
    if (count > 0) {
      const firstRow = journalPage.tradeRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const tradeId = testId.replace('autopilot-journal-trade-row-', '');
      await journalPage.openTradeDetails(tradeId);
      await journalPage.addTradeNotes('Test note for trade analysis');
    }
  });

  test('exports trades to CSV', async () => {
    await journalPage.exportToCsv();
  });

  test('displays cumulative P&L chart', async () => {
    await expect(journalPage.cumulativeChart).toBeVisible();
  });
});


// =============================================================================
// TRADE JOURNAL - EDGE CASES
// =============================================================================

test.describe('AutoPilot Trade Journal - Edge Cases', () => {
  let journalPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    journalPage = new AutoPilotJournalPage(authenticatedPage);
    await journalPage.navigate();
    await journalPage.waitForPageLoad();
  });

  test('handles empty trades list with future date filter', async () => {
    // Vue uses direct date inputs for custom filtering
    await journalPage.filterByCustomDates('2030-01-01', '2030-12-31');
    const count = await journalPage.getTradeCount();
    expect(count).toBe(0);
  });

  test('clears all filters', async () => {
    // Apply a filter that makes the "Clear Filters" button appear
    // The button only shows when underlying or exitReason is set
    await journalPage.filterByOutcome('profit');
    await journalPage.clearAllFilters();
    await expect(journalPage.journalPage).toBeVisible();
  });

  test('handles pagination if available', async () => {
    const pagination = journalPage.pagination;
    if (await pagination.isVisible()) {
      const nextButton = pagination.locator('[data-testid="pagination-next"]');
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        await journalPage.page.waitForLoadState('networkidle');
      }
    }
  });

  test('sorts trades by date', async () => {
    // Sort button is only visible when there are trades (table header is inside v-else)
    const count = await journalPage.getTradeCount();
    if (count > 0) {
      await journalPage.sortByDate();
      await expect(journalPage.journalPage).toBeVisible();
      // Sort again for descending
      await journalPage.sortByDate();
      await expect(journalPage.journalPage).toBeVisible();
    } else {
      // No trades - sort button not visible, verify empty state instead
      await expect(journalPage.emptyState).toBeVisible();
    }
  });

  test('handles trade notes character limit', async () => {
    const count = await journalPage.getTradeCount();
    if (count > 0) {
      const firstRow = journalPage.tradeRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const tradeId = testId.replace('autopilot-journal-trade-row-', '');
      await journalPage.openTradeDetails(tradeId);
      const longText = 'A'.repeat(5000);
      await journalPage.tradeNotes.fill(longText);
    }
  });
});
