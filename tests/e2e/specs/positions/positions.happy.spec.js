/**
 * Positions Happy Path Tests
 *
 * Tests for normal user flows and expected behavior.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { PositionsPage } from '../../pages/PositionsPage.js';

test.describe('Positions - Happy Path @happy', () => {
  let positionsPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    positionsPage = new PositionsPage(authenticatedPage);
    await positionsPage.navigate();
    await positionsPage.waitForPageLoad();
  });

  test('page loads successfully', async ({ authenticatedPage }) => {
    await expect(positionsPage.container).toBeVisible();
  });

  test('has correct URL', async ({ authenticatedPage }) => {
    expect(authenticatedPage.url()).toContain('/positions');
  });

  test('Day/Net toggle is visible', async () => {
    await expect(positionsPage.dayButton).toBeVisible();
    await expect(positionsPage.netButton).toBeVisible();
  });

  test('can switch between Day and Net positions', async () => {
    // Click Day
    await positionsPage.selectDayPositions();
    const isDayActive = await positionsPage.isDaySelected();
    expect(isDayActive).toBe(true);

    // Click Net
    await positionsPage.selectNetPositions();
    const isNetActive = await positionsPage.isNetSelected();
    expect(isNetActive).toBe(true);
  });

  test('P&L box is visible', async () => {
    await expect(positionsPage.pnlBox).toBeVisible();
  });

  test('shows positions table or empty state', async () => {
    // Either table is visible (has positions) or empty state is visible
    const hasTable = await positionsPage.hasPositions();
    const isEmpty = await positionsPage.isEmpty();

    expect(hasTable || isEmpty).toBe(true);
  });

  test('empty state has link to Option Chain', async ({ authenticatedPage }) => {
    // Only check if empty state is showing
    const isEmpty = await positionsPage.isEmpty();

    if (isEmpty) {
      const link = positionsPage.emptyState.locator('a[href*="optionchain"]');
      await expect(link).toBeVisible();
    }
  });

  test('summary bar shows when positions exist', async () => {
    const hasPositions = await positionsPage.hasPositions();

    if (hasPositions) {
      await expect(positionsPage.summaryBar).toBeVisible();
    } else {
      // No positions — empty state must be visible (always assert something)
      await expect(positionsPage.emptyState).toBeVisible();
    }
  });

  test('table headers are correct', async () => {
    const hasPositions = await positionsPage.hasPositions();

    if (hasPositions) {
      const headers = ['Instrument', 'Product', 'Qty', 'Avg Price', 'LTP', 'Day Chg', 'P&L', 'Actions'];
      for (const header of headers) {
        await expect(positionsPage.table.getByText(header)).toBeVisible();
      }
    } else {
      // No positions — empty state must be visible (always assert something)
      await expect(positionsPage.emptyState).toBeVisible();
    }
  });

  test('LTP column shows valid live prices', async ({ authenticatedPage }) => {
    const hasPositions = await positionsPage.hasPositions();

    if (hasPositions) {
      // Get all LTP cells in the positions table
      const ltpCells = authenticatedPage.locator('[data-testid^="positions-ltp-"]');
      await ltpCells.first().waitFor({ state: 'visible', timeout: 5000 });
      const count = await ltpCells.count();

      if (count > 0) {
        // Validate that at least the first LTP shows a valid price
        const firstLtp = await ltpCells.first().textContent();
        const ltpValue = parseFloat(firstLtp.replace(/[^\d.-]/g, ''));

        // LTP should be a valid positive number
        // Test will fail if Kite broker token is expired
        expect(ltpValue).toBeGreaterThan(0);
      }
    } else {
      // No positions — empty state must be visible (always assert something)
      await expect(positionsPage.emptyState).toBeVisible();
    }
  });

  test('Exit and Add buttons are visible for each position', async ({ authenticatedPage }) => {
    const hasPositions = await positionsPage.hasPositions();

    if (hasPositions) {
      // Check that at least one exit and add button exists
      const exitButtons = authenticatedPage.locator('[data-testid^="positions-exit-button-"]');
      const addButtons = authenticatedPage.locator('[data-testid^="positions-add-button-"]');

      await expect(exitButtons.first()).toBeVisible();
      await expect(addButtons.first()).toBeVisible();
    } else {
      // No positions — empty state must be visible (always assert something)
      await expect(positionsPage.emptyState).toBeVisible();
    }
  });

  test('auto refresh toggle works', async ({ authenticatedPage }) => {
    const autoRefreshCheckbox = authenticatedPage.locator('input[type="checkbox"]');
    await expect(autoRefreshCheckbox).toBeVisible();

    // Toggle on
    await autoRefreshCheckbox.check();
    expect(await autoRefreshCheckbox.isChecked()).toBe(true);

    // Toggle off
    await autoRefreshCheckbox.uncheck();
    expect(await autoRefreshCheckbox.isChecked()).toBe(false);
  });
});
