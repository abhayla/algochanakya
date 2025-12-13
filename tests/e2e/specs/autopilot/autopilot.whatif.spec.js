/**
 * AutoPilot What-If Simulator - E2E Tests
 *
 * Tests for simulation and scenario comparison UI.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotDashboardPage } from '../../pages/AutoPilotDashboardPage.js';

test.describe('AutoPilot What-If Simulator - E2E', () => {
  let page;

  test.beforeEach(async ({ authenticatedPage }) => {
    page = new AutoPilotDashboardPage(authenticatedPage);
    await page.navigate();
    await page.waitForDashboardLoad();

    // Navigate to strategy detail
    await page.page.click('[data-testid="autopilot-strategy-row"]');
    await page.page.waitForSelector('[data-testid="autopilot-strategy-detail"]');
  });

  test('should open what-if simulator modal', async ({ authenticatedPage }) => {
    // Click what-if button
    await page.page.click('[data-testid="autopilot-whatif-btn"]');

    // Verify simulator modal opens
    const simulatorModal = page.page.locator('[data-testid="autopilot-whatif-modal"]');
    await expect(simulatorModal).toBeVisible();

    // Verify scenario type selection
    const scenarioTypeSelect = page.page.locator('[data-testid="autopilot-whatif-scenario-type"]');
    await expect(scenarioTypeSelect).toBeVisible();

    // Close modal
    await page.page.click('[data-testid="autopilot-whatif-modal-close"]');
    await expect(simulatorModal).not.toBeVisible();
  });

  test('should configure shift simulation', async ({ authenticatedPage }) => {
    // Open simulator
    await page.page.click('[data-testid="autopilot-whatif-btn"]');

    const simulatorModal = page.page.locator('[data-testid="autopilot-whatif-modal"]');
    await expect(simulatorModal).toBeVisible();

    // Select shift scenario
    await page.page.selectOption('[data-testid="autopilot-whatif-scenario-type"]', 'shift');

    // Verify shift configuration appears
    const shiftConfig = page.page.locator('[data-testid="autopilot-whatif-shift-config"]');
    await expect(shiftConfig).toBeVisible();

    // Select leg to shift
    const legSelect = shiftConfig.locator('[data-testid="autopilot-whatif-leg-select"]');
    await expect(legSelect).toBeVisible();

    // Configure target (by strike, delta, or amount)
    const targetModeSelect = shiftConfig.locator('[data-testid="autopilot-whatif-target-mode"]');
    await expect(targetModeSelect).toBeVisible();

    // Select "by strike"
    await page.page.selectOption('[data-testid="autopilot-whatif-target-mode"]', 'strike');

    // Enter target strike
    const targetStrikeInput = shiftConfig.locator('[data-testid="autopilot-whatif-target-strike"]');
    await expect(targetStrikeInput).toBeVisible();
    await targetStrikeInput.fill('24900');
  });

  test('should configure break trade simulation', async ({ authenticatedPage }) => {
    // Open simulator
    await page.page.click('[data-testid="autopilot-whatif-btn"]');

    // Select break trade scenario
    await page.page.selectOption('[data-testid="autopilot-whatif-scenario-type"]', 'break');

    // Verify break trade config appears
    const breakConfig = page.page.locator('[data-testid="autopilot-whatif-break-config"]');
    await expect(breakConfig).toBeVisible();

    // Select leg to break
    const legSelect = breakConfig.locator('[data-testid="autopilot-whatif-leg-select"]');
    await expect(legSelect).toBeVisible();

    // Select premium split mode
    const splitModeSelect = breakConfig.locator('[data-testid="autopilot-whatif-split-mode"]');
    await expect(splitModeSelect).toBeVisible();

    // Options: equal or weighted
    await page.page.selectOption('[data-testid="autopilot-whatif-split-mode"]', 'equal');
  });

  test('should display before/after comparison', async ({ authenticatedPage }) => {
    // Open simulator
    await page.page.click('[data-testid="autopilot-whatif-btn"]');

    // Configure and run simulation
    await page.page.selectOption('[data-testid="autopilot-whatif-scenario-type"]', 'shift');

    // Fill configuration
    await page.page.selectOption('[data-testid="autopilot-whatif-target-mode"]', 'strike');
    await page.page.fill('[data-testid="autopilot-whatif-target-strike"]', '24900');

    // Click simulate button
    await page.page.click('[data-testid="autopilot-whatif-simulate-btn"]');

    // Wait for results
    await page.page.waitForSelector('[data-testid="autopilot-whatif-results"]', { timeout: 5000 });

    // Verify before/after comparison is displayed
    const beforeSection = page.page.locator('[data-testid="autopilot-whatif-before"]');
    const afterSection = page.page.locator('[data-testid="autopilot-whatif-after"]');

    await expect(beforeSection).toBeVisible();
    await expect(afterSection).toBeVisible();

    // Verify metrics are shown
    const beforeDelta = beforeSection.locator('[data-testid="autopilot-whatif-delta"]');
    const afterDelta = afterSection.locator('[data-testid="autopilot-whatif-delta"]');

    await expect(beforeDelta).toBeVisible();
    await expect(afterDelta).toBeVisible();

    // Verify impact section
    const impactSection = page.page.locator('[data-testid="autopilot-whatif-impact"]');
    await expect(impactSection).toBeVisible();
  });

  test('should execute from simulator', async ({ authenticatedPage }) => {
    // Open simulator
    await page.page.click('[data-testid="autopilot-whatif-btn"]');

    // Configure simulation
    await page.page.selectOption('[data-testid="autopilot-whatif-scenario-type"]', 'shift');
    await page.page.selectOption('[data-testid="autopilot-whatif-target-mode"]', 'strike');
    await page.page.fill('[data-testid="autopilot-whatif-target-strike"]', '24900');

    // Run simulation
    await page.page.click('[data-testid="autopilot-whatif-simulate-btn"]');

    // Wait for results
    await page.page.waitForSelector('[data-testid="autopilot-whatif-results"]');

    // Execute button should appear if simulation successful
    const executeBtn = page.page.locator('[data-testid="autopilot-whatif-execute-btn"]');

    if (await executeBtn.isVisible()) {
      // Click execute
      await executeBtn.click();

      // Confirmation dialog should appear
      const confirmDialog = page.page.locator('[data-testid="autopilot-execute-confirm-dialog"]');
      await expect(confirmDialog).toBeVisible();

      // Cancel for now
      await page.page.click('[data-testid="autopilot-execute-cancel-btn"]');
      await expect(confirmDialog).not.toBeVisible();
    }
  });

  test('should clear simulation results', async ({ authenticatedPage }) => {
    // Open simulator
    await page.page.click('[data-testid="autopilot-whatif-btn"]');

    // Configure and run simulation
    await page.page.selectOption('[data-testid="autopilot-whatif-scenario-type"]', 'exit');

    // Run simulation
    await page.page.click('[data-testid="autopilot-whatif-simulate-btn"]');

    // Wait for results
    await page.page.waitForSelector('[data-testid="autopilot-whatif-results"]', { timeout: 5000 });

    // Results should be visible
    const results = page.page.locator('[data-testid="autopilot-whatif-results"]');
    await expect(results).toBeVisible();

    // Click clear button
    const clearBtn = page.page.locator('[data-testid="autopilot-whatif-clear-btn"]');

    if (await clearBtn.isVisible()) {
      await clearBtn.click();

      // Results should be hidden
      await expect(results).not.toBeVisible();
    }
  });
});
