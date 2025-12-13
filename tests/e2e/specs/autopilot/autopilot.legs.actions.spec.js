/**
 * AutoPilot Leg Actions - E2E Tests
 *
 * Tests for position legs panel and leg action modals.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotDashboardPage } from '../../pages/AutoPilotDashboardPage.js';

test.describe('AutoPilot Leg Actions - E2E', () => {
  let page;

  test.beforeEach(async ({ authenticatedPage }) => {
    page = new AutoPilotDashboardPage(authenticatedPage);
    await page.navigate();
    await page.waitForDashboardLoad();

    // Navigate to strategy with position legs
    await page.strategyCards.first().click();
    await page.page.waitForSelector('[data-testid="autopilot-strategy-detail"]');
    await page.page.click('[data-testid="autopilot-legs-tab"]');
    await page.page.waitForSelector('[data-testid="autopilot-legs-panel"]');
  });

  test('should view position legs panel', async ({ authenticatedPage }) => {
    // Verify legs panel is visible
    const legsPanel = page.page.locator('[data-testid="autopilot-legs-panel"]');
    await expect(legsPanel).toBeVisible();

    // Verify legs are displayed
    const legCards = page.page.locator('[data-testid^="autopilot-leg-card"]');
    await expect(legCards.first()).toBeVisible();
  });

  test('should open exit single leg modal', async ({ authenticatedPage }) => {
    // Click exit button on first leg
    await page.page.click('[data-testid^="autopilot-leg-exit-btn"]');

    // Verify modal opens
    const modal = page.page.locator('[data-testid="autopilot-exit-leg-modal"]');
    await expect(modal).toBeVisible();

    // Verify modal has execution mode selection
    const modeSelect = page.page.locator('[data-testid="autopilot-exit-mode-select"]');
    await expect(modeSelect).toBeVisible();

    // Close modal
    await page.page.click('[data-testid="autopilot-exit-modal-cancel"]');
    await expect(modal).not.toBeVisible();
  });

  test('should shift leg modal - by strike', async ({ authenticatedPage }) => {
    // Open shift modal
    await page.page.click('[data-testid^="autopilot-leg-shift-btn"]');

    // Verify modal
    const modal = page.page.locator('[data-testid="autopilot-shift-leg-modal"]');
    await expect(modal).toBeVisible();

    // Select target strike mode
    await page.page.selectOption('[data-testid="autopilot-shift-mode-select"]', 'strike');

    // Enter target strike
    await page.page.fill('[data-testid="autopilot-shift-target-strike"]', '24900');

    // Verify preview updates
    const preview = page.page.locator('[data-testid="autopilot-shift-preview"]');
    await expect(preview).toBeVisible();
  });

  test('should shift leg modal - by delta', async ({ authenticatedPage }) => {
    // Open shift modal
    await page.page.click('[data-testid^="autopilot-leg-shift-btn"]');

    // Select delta mode
    await page.page.selectOption('[data-testid="autopilot-shift-mode-select"]', 'delta');

    // Enter target delta
    await page.page.fill('[data-testid="autopilot-shift-target-delta"]', '0.18');

    // Verify preview
    const preview = page.page.locator('[data-testid="autopilot-shift-preview"]');
    await expect(preview).toBeVisible();
  });

  test('should open roll leg modal', async ({ authenticatedPage }) => {
    // Click roll button
    await page.page.click('[data-testid^="autopilot-leg-roll-btn"]');

    // Verify modal
    const modal = page.page.locator('[data-testid="autopilot-roll-leg-modal"]');
    await expect(modal).toBeVisible();

    // Verify expiry dropdown
    const expirySelect = page.page.locator('[data-testid="autopilot-roll-expiry-select"]');
    await expect(expirySelect).toBeVisible();

    // Verify optional strike input
    const strikeInput = page.page.locator('[data-testid="autopilot-roll-target-strike"]');
    await expect(strikeInput).toBeVisible();
  });

  test('should open break trade wizard - step navigation', async ({ authenticatedPage }) => {
    // Click break trade button
    await page.page.click('[data-testid^="autopilot-leg-break-btn"]');

    // Verify wizard modal
    const wizard = page.page.locator('[data-testid="autopilot-break-trade-wizard"]');
    await expect(wizard).toBeVisible();

    // Step 1: Confirmation
    const step1 = page.page.locator('[data-testid="autopilot-break-step-1"]');
    await expect(step1).toBeVisible();

    // Click next
    await page.page.click('[data-testid="autopilot-break-next-btn"]');

    // Step 2: Exit cost
    const step2 = page.page.locator('[data-testid="autopilot-break-step-2"]');
    await expect(step2).toBeVisible();
  });

  test('should show break trade wizard - preview', async ({ authenticatedPage }) => {
    // Open wizard
    await page.page.click('[data-testid^="autopilot-leg-break-btn"]');

    // Navigate to preview step
    await page.page.click('[data-testid="autopilot-break-next-btn"]');
    await page.page.click('[data-testid="autopilot-break-next-btn"]');

    // Verify preview displays
    const preview = page.page.locator('[data-testid="autopilot-break-preview"]');
    await expect(preview).toBeVisible();

    // Verify shows new strikes
    const newStrikes = page.page.locator('[data-testid="autopilot-break-new-strikes"]');
    await expect(newStrikes).toContainText(/PUT|CALL/);
  });

  test('should show action buttons visibility', async ({ authenticatedPage }) => {
    // Verify all action buttons are visible
    const exitBtn = page.page.locator('[data-testid^="autopilot-leg-exit-btn"]');
    const shiftBtn = page.page.locator('[data-testid^="autopilot-leg-shift-btn"]');
    const rollBtn = page.page.locator('[data-testid^="autopilot-leg-roll-btn"]');
    const breakBtn = page.page.locator('[data-testid^="autopilot-leg-break-btn"]');

    await expect(exitBtn).toBeVisible();
    await expect(shiftBtn).toBeVisible();
    await expect(rollBtn).toBeVisible();
    await expect(breakBtn).toBeVisible();
  });

  test('should display P&L with colors', async ({ authenticatedPage }) => {
    // Find P&L display
    const pnlDisplay = page.page.locator('[data-testid^="autopilot-leg-pnl"]').first();
    await expect(pnlDisplay).toBeVisible();

    // Check for color coding (green for profit, red for loss)
    const pnlValue = await pnlDisplay.textContent();
    if (pnlValue.includes('+') || parseFloat(pnlValue) > 0) {
      await expect(pnlDisplay).toHaveClass(/green|profit|positive/);
    } else if (pnlValue.includes('-') || parseFloat(pnlValue) < 0) {
      await expect(pnlDisplay).toHaveClass(/red|loss|negative/);
    }
  });

  test('should display Greeks per leg', async ({ authenticatedPage }) => {
    // Toggle Greeks display on
    await page.page.click('[data-testid="autopilot-legs-greeks-toggle"]');

    // Verify Greeks are displayed
    const deltaDisplay = page.page.locator('[data-testid^="autopilot-leg-delta"]').first();
    await expect(deltaDisplay).toBeVisible();

    const gammaDisplay = page.page.locator('[data-testid^="autopilot-leg-gamma"]').first();
    await expect(gammaDisplay).toBeVisible();

    const thetaDisplay = page.page.locator('[data-testid^="autopilot-leg-theta"]').first();
    await expect(thetaDisplay).toBeVisible();
  });
});
