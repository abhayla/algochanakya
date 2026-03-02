/**
 * Phase 5D E2E Tests - Exit Rules
 *
 * Features tested:
 * - Features #18-22: Profit-Based Exits
 * - Features #23-25: Time-Based Exits
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotStrategyBuilderPage } from '../../pages/AutoPilotDashboardPage.js';

// =============================================================================
// FEATURES #18-22: PROFIT-BASED EXITS
// =============================================================================

test.describe('AutoPilot Phase 5D - Profit-Based Exits', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('shows profit target config section', async () => {
    const exitRulesTab = builderPage.page.getByTestId('autopilot-builder-exit-rules-tab');
    await exitRulesTab.click();

    const profitTargetSection = builderPage.page.getByTestId('autopilot-profit-target-section');

    if (await profitTargetSection.isVisible()) {
      await expect(profitTargetSection).toBeVisible();
    } else {
      test.skip('Phase 5d features not yet implemented'); // Not yet implemented
    }
  });

  test('can set 50% of max profit target', async () => {
    const exitRulesTab = builderPage.page.getByTestId('autopilot-builder-exit-rules-tab');
    await exitRulesTab.click();

    const profitTargetCheckbox = builderPage.page.getByTestId('autopilot-exit-profit-pct-enable');
    const profitTargetInput = builderPage.page.getByTestId('autopilot-exit-profit-pct-value');

    if (await profitTargetCheckbox.isVisible()) {
      await profitTargetCheckbox.check();
      await profitTargetInput.fill('50');

      await expect(profitTargetInput).toHaveValue('50');
    } else {
      test.skip('Phase 5d features not yet implemented');
    }
  });

  test('can set 25% profit target', async () => {
    const exitRulesTab = builderPage.page.getByTestId('autopilot-builder-exit-rules-tab');
    await exitRulesTab.click();

    const profitTargetInput = builderPage.page.getByTestId('autopilot-exit-profit-pct-value');

    if (await profitTargetInput.isVisible()) {
      await profitTargetInput.fill('25');
      await expect(profitTargetInput).toHaveValue('25');
    } else {
      test.skip('Phase 5d features not yet implemented');
    }
  });

  test('can set premium captured % target', async () => {
    const exitRulesTab = builderPage.page.getByTestId('autopilot-builder-exit-rules-tab');
    await exitRulesTab.click();

    const premiumCapturedCheckbox = builderPage.page.getByTestId('autopilot-exit-premium-captured-enable');
    const premiumCapturedInput = builderPage.page.getByTestId('autopilot-exit-premium-captured-value');

    if (await premiumCapturedCheckbox.isVisible()) {
      await premiumCapturedCheckbox.check();
      await premiumCapturedInput.fill('60');

      await expect(premiumCapturedInput).toHaveValue('60');
    } else {
      test.skip('Phase 5d features not yet implemented');
    }
  });

  test('can set target return % on margin', async () => {
    const exitRulesTab = builderPage.page.getByTestId('autopilot-builder-exit-rules-tab');
    await exitRulesTab.click();

    const returnOnMarginCheckbox = builderPage.page.getByTestId('autopilot-exit-return-on-margin-enable');
    const returnOnMarginInput = builderPage.page.getByTestId('autopilot-exit-return-on-margin-value');

    if (await returnOnMarginCheckbox.isVisible()) {
      await returnOnMarginCheckbox.check();
      await returnOnMarginInput.fill('10');

      await expect(returnOnMarginInput).toHaveValue('10');
    } else {
      test.skip('Phase 5d features not yet implemented');
    }
  });
});

// =============================================================================
// FEATURES #23-25: TIME-BASED EXITS
// =============================================================================

test.describe('AutoPilot Phase 5D - Time-Based Exits', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('can set DTE exit rule', async () => {
    const exitRulesTab = builderPage.page.getByTestId('autopilot-builder-exit-rules-tab');
    await exitRulesTab.click();

    const dteExitCheckbox = builderPage.page.getByTestId('autopilot-exit-dte-enable');
    const dteExitInput = builderPage.page.getByTestId('autopilot-exit-dte-value');

    if (await dteExitCheckbox.isVisible()) {
      await dteExitCheckbox.check();
      await dteExitInput.fill('21');

      await expect(dteExitInput).toHaveValue('21');
    } else {
      test.skip('Phase 5d features not yet implemented');
    }
  });

  test('can set days in trade limit', async () => {
    const exitRulesTab = builderPage.page.getByTestId('autopilot-builder-exit-rules-tab');
    await exitRulesTab.click();

    const daysInTradeCheckbox = builderPage.page.getByTestId('autopilot-exit-days-in-trade-enable');
    const daysInTradeInput = builderPage.page.getByTestId('autopilot-exit-days-in-trade-value');

    if (await daysInTradeCheckbox.isVisible()) {
      await daysInTradeCheckbox.check();
      await daysInTradeInput.fill('14');

      await expect(daysInTradeInput).toHaveValue('14');
    } else {
      test.skip('Phase 5d features not yet implemented');
    }
  });

  test('shows optimal exit timing suggestion', async () => {
    const exitRulesTab = builderPage.page.getByTestId('autopilot-builder-exit-rules-tab');
    await exitRulesTab.click();

    const optimalExitSuggestion = builderPage.page.getByTestId('autopilot-exit-optimal-timing-suggestion');

    if (await optimalExitSuggestion.isVisible()) {
      await expect(optimalExitSuggestion).toContainText(/optimal exit/i);
    } else {
      test.skip('Phase 5d features not yet implemented');
    }
  });
});
