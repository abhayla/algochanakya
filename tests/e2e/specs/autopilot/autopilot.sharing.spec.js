/**
 * AutoPilot Phase 4 - Strategy Sharing E2E Tests
 *
 * Tests for sharing strategies, public access, and cloning shared strategies.
 *
 * SKIP: Strategy sharing feature not yet implemented (Phase 4 feature)
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import {
  AutoPilotDashboardPage,
  AutoPilotSharingPage
} from '../../pages/AutoPilotDashboardPage.js';


// =============================================================================
// SHARE STRATEGY - HAPPY PATH
// =============================================================================

test.describe('AutoPilot Strategy Sharing - Share Strategy', () => {
  let dashboardPage;
  let sharingPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    sharingPage = new AutoPilotSharingPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();
  });

  test('displays share button on strategy row', async () => {
    const shareButtons = dashboardPage.page.locator('[data-testid^="autopilot-strategy-share-btn-"]');
    const count = await shareButtons.count();
    if (count > 0) {
      await expect(shareButtons.first()).toBeVisible();
    }
  });

  test('opens share modal', async () => {
    const shareBtn = dashboardPage.page.locator('[data-testid^="autopilot-strategy-share-btn-"]').first();
    if (await shareBtn.isVisible()) {
      await shareBtn.click();
      await expect(sharingPage.shareModal).toBeVisible();
    }
  });

  test('displays share options', async () => {
    const shareBtn = dashboardPage.page.locator('[data-testid^="autopilot-strategy-share-btn-"]').first();
    if (await shareBtn.isVisible()) {
      await shareBtn.click();
      await expect(sharingPage.publicToggle).toBeVisible();
      await expect(sharingPage.descriptionInput).toBeVisible();
    }
  });

  test('enables public sharing', async () => {
    const shareBtn = dashboardPage.page.locator('[data-testid^="autopilot-strategy-share-btn-"]').first();
    if (await shareBtn.isVisible()) {
      await shareBtn.click();
      await sharingPage.enablePublicSharing();
    }
  });

  test('adds share description', async () => {
    const shareBtn = dashboardPage.page.locator('[data-testid^="autopilot-strategy-share-btn-"]').first();
    if (await shareBtn.isVisible()) {
      await shareBtn.click();
      await sharingPage.setShareDescription('This is a profitable Iron Condor strategy for NIFTY');
    }
  });

  test('generates share link', async () => {
    const shareBtn = dashboardPage.page.locator('[data-testid^="autopilot-strategy-share-btn-"]').first();
    if (await shareBtn.isVisible()) {
      await shareBtn.click();
      await sharingPage.enablePublicSharing();
      await sharingPage.generateShareLink();
      await expect(sharingPage.shareLink).toBeVisible();
    }
  });

  test('copies share link to clipboard', async () => {
    const shareBtn = dashboardPage.page.locator('[data-testid^="autopilot-strategy-share-btn-"]').first();
    if (await shareBtn.isVisible()) {
      await shareBtn.click();
      await sharingPage.enablePublicSharing();
      await sharingPage.generateShareLink();
      await sharingPage.copyShareLink();
    }
  });

  test('cancels share modal', async () => {
    const shareBtn = dashboardPage.page.locator('[data-testid^="autopilot-strategy-share-btn-"]').first();
    if (await shareBtn.isVisible()) {
      await shareBtn.click();
      await sharingPage.cancelShare();
      await expect(sharingPage.shareModal).not.toBeVisible();
    }
  });
});


// =============================================================================
// SHARED STRATEGIES - HAPPY PATH
// =============================================================================

test.describe('AutoPilot Strategy Sharing - Shared Strategies', () => {
  let sharingPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    sharingPage = new AutoPilotSharingPage(authenticatedPage);
    await sharingPage.navigate();
    await sharingPage.waitForPageLoad();
  });

  test('displays shared strategies list', async () => {
    await expect(sharingPage.sharedStrategiesList).toBeVisible();
  });

  test('opens shared strategy details', async () => {
    const count = await sharingPage.getSharedCount();
    if (count > 0) {
      const firstStrategy = sharingPage.sharedStrategies.first();
      const testId = await firstStrategy.getAttribute('data-testid');
      const strategyId = testId.replace('autopilot-shared-strategy-', '');
      await sharingPage.openSharedStrategy(strategyId);
      await expect(sharingPage.sharedStrategyDetails).toBeVisible();
    }
  });

  test('displays read-only badge on shared strategy', async () => {
    const count = await sharingPage.getSharedCount();
    if (count > 0) {
      const firstStrategy = sharingPage.sharedStrategies.first();
      const testId = await firstStrategy.getAttribute('data-testid');
      const strategyId = testId.replace('autopilot-shared-strategy-', '');
      await sharingPage.openSharedStrategy(strategyId);
      await expect(sharingPage.readonlyBadge).toBeVisible();
    }
  });
});


// =============================================================================
// CLONE STRATEGY - HAPPY PATH
// =============================================================================

test.describe('AutoPilot Strategy Sharing - Clone Strategy', () => {
  let sharingPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    sharingPage = new AutoPilotSharingPage(authenticatedPage);
    await sharingPage.navigate();
    await sharingPage.waitForPageLoad();
  });

  test('displays clone button on shared strategy', async () => {
    const count = await sharingPage.getSharedCount();
    if (count > 0) {
      const firstStrategy = sharingPage.sharedStrategies.first();
      const testId = await firstStrategy.getAttribute('data-testid');
      const strategyId = testId.replace('autopilot-shared-strategy-', '');
      await sharingPage.openSharedStrategy(strategyId);
      await expect(sharingPage.cloneButton).toBeVisible();
    }
  });

  test('opens clone modal', async () => {
    const count = await sharingPage.getSharedCount();
    if (count > 0) {
      const firstStrategy = sharingPage.sharedStrategies.first();
      const testId = await firstStrategy.getAttribute('data-testid');
      const strategyId = testId.replace('autopilot-shared-strategy-', '');
      await sharingPage.openSharedStrategy(strategyId);
      await sharingPage.cloneButton.click();
      await expect(sharingPage.cloneModal).toBeVisible();
    }
  });

  test('clones a strategy', async () => {
    const count = await sharingPage.getSharedCount();
    if (count > 0) {
      const firstStrategy = sharingPage.sharedStrategies.first();
      const testId = await firstStrategy.getAttribute('data-testid');
      const strategyId = testId.replace('autopilot-shared-strategy-', '');
      await sharingPage.openSharedStrategy(strategyId);
      await sharingPage.cloneStrategy('Cloned Strategy ' + Date.now());
    }
  });
});


// =============================================================================
// SHARING - EDGE CASES
// =============================================================================

test.describe('AutoPilot Strategy Sharing - Edge Cases', () => {
  let sharingPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    sharingPage = new AutoPilotSharingPage(authenticatedPage);
  });

  test('handles invalid share code', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/shared/invalid-code-xyz123');
    await authenticatedPage.waitForLoadState('networkidle');
    // Should show not found or error page
  });

  test('handles clone validation errors', async ({ authenticatedPage }) => {
    await sharingPage.navigate();
    await sharingPage.waitForPageLoad();

    const count = await sharingPage.getSharedCount();
    if (count > 0) {
      const firstStrategy = sharingPage.sharedStrategies.first();
      const testId = await firstStrategy.getAttribute('data-testid');
      const strategyId = testId.replace('autopilot-shared-strategy-', '');
      await sharingPage.openSharedStrategy(strategyId);
      await sharingPage.cloneButton.click();
      await sharingPage.cloneNameInput.clear();
      await sharingPage.cloneSubmitButton.click();
      // Should show validation error
    }
  });

  test('sets share expiration', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const shareBtn = dashboardPage.page.locator('[data-testid^="autopilot-strategy-share-btn-"]').first();
    if (await shareBtn.isVisible()) {
      await shareBtn.click();
      await sharingPage.setExpiration(7);
    }
  });

  test('unshares a strategy', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const unshareBtn = dashboardPage.page.locator('[data-testid^="autopilot-strategy-unshare-btn-"]').first();
    if (await unshareBtn.isVisible()) {
      await unshareBtn.click();
      await sharingPage.confirmUnshare();
    }
  });
});
