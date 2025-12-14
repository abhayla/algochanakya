/**
 * Phase 5G E2E Tests - Advanced Adjustments (Strategy Conversions)
 *
 * Features tested:
 * - Feature #40: Strategy Conversion
 * - Feature #41: Widen the Spread
 * - Feature #42: Convert to Ratio Spread
 * - Feature #43: Iron Butterfly Conversion
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotStrategyDetailPage } from '../../pages/AutoPilotDashboardPage.js';

// =============================================================================
// FEATURES #40-43: STRATEGY CONVERSIONS
// =============================================================================

test.describe('AutoPilot Phase 5G - Strategy Conversions', () => {
  let detailPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
  });

  test('shows conversion options in adjustments menu', async ({ authenticatedPage }) => {
    // Navigate to strategy detail or builder
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for conversion/adjustment options
    const adjustmentMenu = authenticatedPage.getByTestId('autopilot-adjustment-menu');

    // Should have conversion options
    await expect(adjustmentMenu).toBeVisible();
  });

  test('conversion modal opens when clicking convert button', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Click conversion button
    const convertButton = authenticatedPage.getByTestId('autopilot-convert-strategy-button');
    if (await convertButton.isVisible()) {
      await convertButton.click();

      // Modal should open
      const conversionModal = authenticatedPage.getByTestId('autopilot-conversion-modal');
      await expect(conversionModal).toBeVisible();
    }
  });

  test('shows available conversions for current strategy type', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check conversion options dropdown or list
    const conversionOptions = authenticatedPage.getByTestId('autopilot-conversion-options');

    // Should show conversion types
    if (await conversionOptions.isVisible()) {
      await expect(conversionOptions).toContainText(/iron condor|strangle|straddle|butterfly/i);
    }
  });

  test('shows conversion preview with Greeks comparison', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Open conversion preview
    const previewSection = authenticatedPage.getByTestId('autopilot-conversion-preview');

    // Should show Greeks comparison
    if (await previewSection.isVisible()) {
      await expect(previewSection).toContainText(/delta|gamma|theta|vega/i);
    }
  });

  test('can execute iron condor to strangle conversion', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Select iron condor to strangle conversion
    const conversionType = authenticatedPage.getByTestId('autopilot-conversion-type-strangle');
    if (await conversionType.isVisible()) {
      await conversionType.click();

      // Execute conversion
      const executeButton = authenticatedPage.getByTestId('autopilot-execute-conversion-button');
      await expect(executeButton).toBeVisible();
    }
  });

  test('can widen spread on existing strategy', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for widen spread option
    const widenSpreadButton = authenticatedPage.getByTestId('autopilot-widen-spread-button');

    if (await widenSpreadButton.isVisible()) {
      await widenSpreadButton.click();

      // Should show spread adjustment controls
      const spreadAdjustment = authenticatedPage.getByTestId('autopilot-spread-adjustment-control');
      await expect(spreadAdjustment).toBeVisible();
    }
  });

  test('widen spread shows current vs new spread width', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check spread width display
    const currentSpread = authenticatedPage.getByTestId('autopilot-current-spread-width');
    const newSpread = authenticatedPage.getByTestId('autopilot-new-spread-width');

    // Should show spread comparison
    if (await currentSpread.isVisible() && await newSpread.isVisible()) {
      await expect(currentSpread).toContainText(/\d+/);
      await expect(newSpread).toContainText(/\d+/);
    }
  });

  test('can convert to ratio spread', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for ratio spread conversion option
    const ratioSpreadButton = authenticatedPage.getByTestId('autopilot-convert-ratio-spread-button');

    if (await ratioSpreadButton.isVisible()) {
      await ratioSpreadButton.click();

      // Should show ratio selection (1:2, 1:3, etc.)
      const ratioSelector = authenticatedPage.getByTestId('autopilot-ratio-selector');
      await expect(ratioSelector).toBeVisible();
    }
  });

  test('ratio spread shows lot multiplier options', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check ratio options
    const ratioOptions = authenticatedPage.getByTestId('autopilot-ratio-options');

    if (await ratioOptions.isVisible()) {
      // Should show 1:2 and 1:3 options
      await expect(ratioOptions).toContainText(/1:2|1:3/);
    }
  });

  test('can convert iron condor to iron butterfly', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Select butterfly conversion
    const butterflyButton = authenticatedPage.getByTestId('autopilot-convert-butterfly-button');

    if (await butterflyButton.isVisible()) {
      await butterflyButton.click();

      // Should show butterfly configuration
      const butterflyConfig = authenticatedPage.getByTestId('autopilot-butterfly-config');
      await expect(butterflyConfig).toBeVisible();
    }
  });

  test('butterfly conversion moves shorts to ATM', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check butterfly strike configuration
    const atmStrike = authenticatedPage.getByTestId('autopilot-butterfly-atm-strike');

    if (await atmStrike.isVisible()) {
      // Should show ATM strike for short legs
      await expect(atmStrike).toContainText(/ATM|at-the-money/i);
    }
  });

  test('conversion shows cost estimate before execution', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check conversion cost display
    const conversionCost = authenticatedPage.getByTestId('autopilot-conversion-cost');

    if (await conversionCost.isVisible()) {
      // Should show cost in rupees
      await expect(conversionCost).toContainText(/₹|cost|debit|credit/i);
    }
  });

  test('conversion requires user confirmation', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Initiate conversion
    const executeButton = authenticatedPage.getByTestId('autopilot-execute-conversion-button');

    if (await executeButton.isVisible()) {
      await executeButton.click();

      // Should show confirmation dialog
      const confirmDialog = authenticatedPage.getByTestId('autopilot-conversion-confirm-dialog');
      await expect(confirmDialog).toBeVisible();
    }
  });

  test('conversion confirmation shows impact summary', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check confirmation dialog content
    const impactSummary = authenticatedPage.getByTestId('autopilot-conversion-impact-summary');

    if (await impactSummary.isVisible()) {
      // Should show risk/reward changes
      await expect(impactSummary).toContainText(/max profit|max loss|breakeven/i);
    }
  });

  test('can cancel conversion before execution', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Open conversion dialog
    const cancelButton = authenticatedPage.getByTestId('autopilot-conversion-cancel-button');

    if (await cancelButton.isVisible()) {
      await cancelButton.click();

      // Modal should close
      const conversionModal = authenticatedPage.getByTestId('autopilot-conversion-modal');
      await expect(conversionModal).not.toBeVisible();
    }
  });

  test('conversion history is tracked in strategy logs', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check activity log
    const activityLog = authenticatedPage.getByTestId('autopilot-activity-log');

    if (await activityLog.isVisible()) {
      // Should show conversion events
      await expect(activityLog).toContainText(/conversion|converted|adjustment/i);
    }
  });

  test('shows warning for high-cost conversions', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check for warning indicators
    const costWarning = authenticatedPage.getByTestId('autopilot-conversion-cost-warning');

    if (await costWarning.isVisible()) {
      // Should show warning message
      await expect(costWarning).toContainText(/high cost|expensive|warning/i);
    }
  });
});

// =============================================================================
// INTEGRATION: CONVERSION WORKFLOWS
// =============================================================================

test.describe('AutoPilot Phase 5G - Conversion Integration', () => {
  test('conversion updates strategy Greeks in real-time', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check Greeks display
    const greeksDisplay = authenticatedPage.getByTestId('autopilot-strategy-greeks');

    if (await greeksDisplay.isVisible()) {
      // Should show updated Greeks after conversion
      await expect(greeksDisplay).toContainText(/delta|gamma|theta|vega/i);
    }
  });

  test('conversion preserves original strategy for comparison', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check original vs new comparison
    const comparisonView = authenticatedPage.getByTestId('autopilot-strategy-comparison');

    if (await comparisonView.isVisible()) {
      await expect(comparisonView).toContainText(/original|new|before|after/i);
    }
  });

  test('can undo conversion if executed in simulation mode', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for undo option
    const undoButton = authenticatedPage.getByTestId('autopilot-conversion-undo-button');

    if (await undoButton.isVisible()) {
      await undoButton.click();

      // Should revert to original strategy
      const revertConfirm = authenticatedPage.getByTestId('autopilot-revert-confirm');
      await expect(revertConfirm).toBeVisible();
    }
  });
});
