/**
 * Positions Edge Case Tests
 *
 * Tests for error states, edge cases, and boundary conditions.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { PositionsPage } from '../../pages/PositionsPage.js';

test.describe('Positions - Edge Cases @edge', () => {
  let positionsPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    positionsPage = new PositionsPage(authenticatedPage);
  });

  test('empty state displays correctly when no positions', async ({ authenticatedPage }) => {
    await positionsPage.navigate();
    await positionsPage.waitForPageLoad();

    const isEmpty = await positionsPage.isEmpty();
    const hasPositions = await positionsPage.hasPositions();

    // One must be true
    expect(isEmpty || hasPositions).toBe(true);

    // If empty, check message
    if (isEmpty) {
      await expect(positionsPage.emptyState).toContainText('No Open Positions');
    }
  });

  test('empty state link navigates to Option Chain', async ({ authenticatedPage }) => {
    await positionsPage.navigate();
    await positionsPage.waitForPageLoad();

    const isEmpty = await positionsPage.isEmpty();

    if (isEmpty) {
      const link = positionsPage.emptyState.locator('a');
      await link.click();
      await authenticatedPage.waitForURL('**/optionchain**');
      expect(authenticatedPage.url()).toContain('/optionchain');
    }
  });

  test('no horizontal overflow at any viewport', async ({ authenticatedPage }) => {
    await positionsPage.navigate();
    await positionsPage.waitForPageLoad();

    const viewports = [
      { width: 1920, height: 1080 },
      { width: 1440, height: 900 },
      { width: 1024, height: 768 }
    ];

    for (const viewport of viewports) {
      await positionsPage.setViewportSize(viewport.width, viewport.height);
      const hasOverflow = await positionsPage.hasHorizontalOverflow();
      expect(hasOverflow, `Horizontal overflow at ${viewport.width}x${viewport.height}`).toBe(false);
    }
  });

  test('Exit modal opens and closes correctly', async ({ authenticatedPage }) => {
    await positionsPage.navigate();
    await positionsPage.waitForPageLoad();

    const hasPositions = await positionsPage.hasPositions();

    if (hasPositions) {
      // Click first exit button
      const exitBtn = authenticatedPage.locator('[data-testid^="positions-exit-button-"]').first();
      await exitBtn.click();

      // Modal should open
      await expect(positionsPage.exitModal).toBeVisible();

      // Close modal
      const closeBtn = positionsPage.exitModal.locator('[data-testid="positions-exit-modal-close"]');
      await closeBtn.click();

      // Modal should close
      await expect(positionsPage.exitModal).not.toBeVisible();
    } else {
      // No positions — empty state must be visible (always assert something)
      await expect(positionsPage.emptyState).toBeVisible();
    }
  });

  test('Add modal opens and closes correctly', async ({ authenticatedPage }) => {
    await positionsPage.navigate();
    await positionsPage.waitForPageLoad();

    const hasPositions = await positionsPage.hasPositions();

    if (hasPositions) {
      // Click first add button
      const addBtn = authenticatedPage.locator('[data-testid^="positions-add-button-"]').first();
      await addBtn.click();

      // Modal should open
      await expect(positionsPage.addModal).toBeVisible();

      // Close modal
      const closeBtn = positionsPage.addModal.locator('[data-testid="positions-add-modal-close"]');
      await closeBtn.click();

      // Modal should close
      await expect(positionsPage.addModal).not.toBeVisible();
    } else {
      // No positions — empty state must be visible (always assert something)
      await expect(positionsPage.emptyState).toBeVisible();
    }
  });

  test('Exit modal has Market/Limit toggle', async ({ authenticatedPage }) => {
    await positionsPage.navigate();
    await positionsPage.waitForPageLoad();

    const hasPositions = await positionsPage.hasPositions();

    if (hasPositions) {
      const exitBtn = authenticatedPage.locator('[data-testid^="positions-exit-button-"]').first();
      await exitBtn.click();

      // Check for order type buttons
      const marketBtn = positionsPage.exitModal.getByText('Market');
      const limitBtn = positionsPage.exitModal.getByText('Limit');

      await expect(marketBtn).toBeVisible();
      await expect(limitBtn).toBeVisible();
    } else {
      // No positions — empty state must be visible (always assert something)
      await expect(positionsPage.emptyState).toBeVisible();
    }
  });
});
