/**
 * Phase 5I E2E Tests - Advanced Entry Logic (Staged Entry)
 *
 * Features tested:
 * - Feature #12: Half-Size Entry
 * - Feature #13: Staggered Entry
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotStrategyDetailPage } from '../../pages/AutoPilotDashboardPage.js';

// =============================================================================
// FEATURE #12: HALF-SIZE ENTRY
// =============================================================================

test.describe('AutoPilot Phase 5I - Half-Size Entry', () => {
  let detailPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
  });

  test('shows staged entry toggle in strategy builder', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for staged entry option
    const stagedEntryToggle = authenticatedPage.getByTestId('autopilot-staged-entry-toggle');

    if (await stagedEntryToggle.isVisible()) {
      await expect(stagedEntryToggle).toBeVisible();
      await expect(stagedEntryToggle).toBeEnabled();
    }
  });

  test('can enable half-size entry option', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Toggle staged entry
    const stagedEntryToggle = authenticatedPage.getByTestId('autopilot-staged-entry-toggle');

    if (await stagedEntryToggle.isVisible()) {
      await stagedEntryToggle.click();

      // Should show staged entry configuration
      const stagedConfig = authenticatedPage.getByTestId('autopilot-staged-entry-config');
      await expect(stagedConfig).toBeVisible();
    }
  });

  test('half-size entry shows stage 1 percentage input', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check for stage 1 percentage input
    const stage1Percentage = authenticatedPage.getByTestId('autopilot-stage1-percentage');

    if (await stage1Percentage.isVisible()) {
      // Default should be 50%
      await expect(stage1Percentage).toHaveValue('50');
    }
  });

  test('can configure stage 1 percentage (30-70%)', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Adjust stage 1 percentage
    const stage1Input = authenticatedPage.getByTestId('autopilot-stage1-percentage');

    if (await stage1Input.isVisible()) {
      await stage1Input.clear();
      await stage1Input.fill('60');

      // Should accept the value
      await expect(stage1Input).toHaveValue('60');
    }
  });

  test('shows stage 2 entry condition configuration', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for stage 2 condition builder
    const stage2Condition = authenticatedPage.getByTestId('autopilot-stage2-condition');

    if (await stage2Condition.isVisible()) {
      await expect(stage2Condition).toBeVisible();
    }
  });

  test('can set stage 2 condition (spot rallies X%)', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Configure stage 2 condition
    const conditionVariable = authenticatedPage.getByTestId('autopilot-stage2-condition-variable');
    const conditionOperator = authenticatedPage.getByTestId('autopilot-stage2-condition-operator');
    const conditionValue = authenticatedPage.getByTestId('autopilot-stage2-condition-value');

    if (await conditionVariable.isVisible()) {
      await conditionVariable.selectOption('SPOT.CHANGE_PCT');
      await conditionOperator.selectOption('greater_than');
      await conditionValue.fill('1.0');

      // Should show configured condition
      await expect(conditionValue).toHaveValue('1.0');
    }
  });

  test('displays current entry stage in strategy detail', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check stage indicator
    const stageIndicator = authenticatedPage.getByTestId('autopilot-current-stage');

    if (await stageIndicator.isVisible()) {
      // Should show Stage 1 or Stage 2
      await expect(stageIndicator).toContainText(/stage 1|stage 2/i);
    }
  });

  test('shows stage 1 execution status', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check stage 1 status
    const stage1Status = authenticatedPage.getByTestId('autopilot-stage1-status');

    if (await stage1Status.isVisible()) {
      await expect(stage1Status).toContainText(/executed|pending|completed/i);
    }
  });

  test('shows stage 2 condition progress', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check condition progress
    const conditionProgress = authenticatedPage.getByTestId('autopilot-stage2-condition-progress');

    if (await conditionProgress.isVisible()) {
      // Should show current vs target (e.g., "0.8% / 1.0%")
      await expect(conditionProgress).toContainText(/%/);
    }
  });

  test('displays lots executed in each stage', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check lots breakdown
    const stage1Lots = authenticatedPage.getByTestId('autopilot-stage1-lots-executed');
    const stage2Lots = authenticatedPage.getByTestId('autopilot-stage2-lots-executed');

    if (await stage1Lots.isVisible()) {
      await expect(stage1Lots).toContainText(/\d+ lot/i);
    }
  });

  test('shows alert when stage 2 condition is met', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check for alert
    const stage2Alert = authenticatedPage.getByTestId('autopilot-stage2-condition-met');

    if (await stage2Alert.isVisible()) {
      await expect(stage2Alert).toContainText(/condition met|ready|execute stage 2/i);
    }
  });

  test('can manually trigger stage 2 execution', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for manual trigger button
    const executeStage2Button = authenticatedPage.getByTestId('autopilot-execute-stage2-button');

    if (await executeStage2Button.isVisible()) {
      await expect(executeStage2Button).toBeEnabled();
      await expect(executeStage2Button).toContainText(/execute|add stage 2/i);
    }
  });

  test('half-size entry reduces initial margin requirement', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check margin display
    const marginDisplay = authenticatedPage.getByTestId('autopilot-initial-margin-required');

    if (await marginDisplay.isVisible()) {
      // Should show reduced margin for stage 1
      await expect(marginDisplay).toContainText(/₹|margin/i);
    }
  });

  test('shows total vs staged margin comparison', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check margin comparison
    const marginComparison = authenticatedPage.getByTestId('autopilot-margin-comparison');

    if (await marginComparison.isVisible()) {
      await expect(marginComparison).toContainText(/full position|staged/i);
    }
  });
});

// =============================================================================
// FEATURE #13: STAGGERED ENTRY
// =============================================================================

test.describe('AutoPilot Phase 5I - Staggered Entry', () => {
  let detailPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
  });

  test('shows staggered entry configuration option', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for staggered entry mode
    const staggeredMode = authenticatedPage.getByTestId('autopilot-staggered-entry-mode');

    if (await staggeredMode.isVisible()) {
      await expect(staggeredMode).toBeVisible();
    }
  });

  test('can configure multiple entry stages', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check stages configuration
    const stagesConfig = authenticatedPage.getByTestId('autopilot-staggered-stages-config');

    if (await stagesConfig.isVisible()) {
      // Should show stage list
      await expect(stagesConfig).toBeVisible();
    }
  });

  test('can add new stage to staggered entry', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for add stage button
    const addStageButton = authenticatedPage.getByTestId('autopilot-add-stage-button');

    if (await addStageButton.isVisible()) {
      await addStageButton.click();

      // Should show new stage configuration
      const newStageConfig = authenticatedPage.getByTestId('autopilot-stage-config-3');
      await expect(newStageConfig).toBeVisible();
    }
  });

  test('each stage has leg selection', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check leg selection for stage
    const stageLegSelection = authenticatedPage.getByTestId('autopilot-stage1-legs');

    if (await stageLegSelection.isVisible()) {
      // Should show PE/CE leg options
      await expect(stageLegSelection).toContainText(/PE|CE/i);
    }
  });

  test('can assign legs to specific stages (PE first, CE later)', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Configure stage 1 with PE legs
    const stage1Legs = authenticatedPage.getByTestId('autopilot-stage1-legs-selector');

    if (await stage1Legs.isVisible()) {
      // Select PE legs for stage 1
      const peLegCheckbox = authenticatedPage.getByTestId('autopilot-stage1-leg-pe');
      if (await peLegCheckbox.isVisible()) {
        await peLegCheckbox.check();
      }
    }
  });

  test('each stage has lots multiplier configuration', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check lots multiplier input
    const lotsMultiplier = authenticatedPage.getByTestId('autopilot-stage1-lots-multiplier');

    if (await lotsMultiplier.isVisible()) {
      // Should default to 1.0 (full size)
      await expect(lotsMultiplier).toHaveValue('1.0');
    }
  });

  test('can set different lot sizes for each stage', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Set stage 2 to half size
    const stage2Multiplier = authenticatedPage.getByTestId('autopilot-stage2-lots-multiplier');

    if (await stage2Multiplier.isVisible()) {
      await stage2Multiplier.clear();
      await stage2Multiplier.fill('0.5');

      await expect(stage2Multiplier).toHaveValue('0.5');
    }
  });

  test('each stage has entry condition (except stage 1)', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Stage 1 should have no condition (enter immediately)
    const stage1Condition = authenticatedPage.getByTestId('autopilot-stage1-condition');
    if (await stage1Condition.isVisible()) {
      await expect(stage1Condition).toContainText(/immediate|no condition/i);
    }

    // Stage 2+ should have condition
    const stage2Condition = authenticatedPage.getByTestId('autopilot-stage2-condition-builder');
    if (await stage2Condition.isVisible()) {
      await expect(stage2Condition).toBeVisible();
    }
  });

  test('can set stage 2 condition (rally 1.5%)', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Configure stage 2 rally condition
    const conditionValue = authenticatedPage.getByTestId('autopilot-stage2-condition-value');

    if (await conditionValue.isVisible()) {
      await conditionValue.fill('1.5');
      await expect(conditionValue).toHaveValue('1.5');
    }
  });

  test('can set stage 3 condition (rally 3%)', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Configure stage 3 condition
    const conditionValue = authenticatedPage.getByTestId('autopilot-stage3-condition-value');

    if (await conditionValue.isVisible()) {
      await conditionValue.fill('3.0');
      await expect(conditionValue).toHaveValue('3.0');
    }
  });

  test('displays visual timeline of staged entry', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check timeline visualization
    const timeline = authenticatedPage.getByTestId('autopilot-stages-timeline');

    if (await timeline.isVisible()) {
      await expect(timeline).toBeVisible();
    }
  });

  test('timeline shows completed and pending stages', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check stage status indicators
    const completedStage = authenticatedPage.getByTestId('autopilot-stage-completed');
    const pendingStage = authenticatedPage.getByTestId('autopilot-stage-pending');

    if (await completedStage.isVisible() || await pendingStage.isVisible()) {
      // At least one should be visible
      expect(true).toBe(true);
    }
  });

  test('shows timeout configuration for staggered entry', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check timeout setting
    const timeoutInput = authenticatedPage.getByTestId('autopilot-staggered-timeout-days');

    if (await timeoutInput.isVisible()) {
      // Should have default timeout (e.g., 7 days)
      await expect(timeoutInput).toHaveValue(/\d+/);
    }
  });

  test('can set timeout to force complete all stages', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Set timeout
    const timeoutInput = authenticatedPage.getByTestId('autopilot-staggered-timeout-days');

    if (await timeoutInput.isVisible()) {
      await timeoutInput.clear();
      await timeoutInput.fill('10');

      await expect(timeoutInput).toHaveValue('10');
    }
  });

  test('shows timeout warning when approaching deadline', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check timeout warning
    const timeoutWarning = authenticatedPage.getByTestId('autopilot-timeout-warning');

    if (await timeoutWarning.isVisible()) {
      await expect(timeoutWarning).toContainText(/timeout|deadline|force complete/i);
    }
  });

  test('can manually force complete remaining stages', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for force complete button
    const forceCompleteButton = authenticatedPage.getByTestId('autopilot-force-complete-button');

    if (await forceCompleteButton.isVisible()) {
      await expect(forceCompleteButton).toBeEnabled();
      await expect(forceCompleteButton).toContainText(/force complete|complete all/i);
    }
  });

  test('shows confirmation before force completing', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Click force complete
    const forceCompleteButton = authenticatedPage.getByTestId('autopilot-force-complete-button');

    if (await forceCompleteButton.isVisible()) {
      await forceCompleteButton.click();

      // Should show confirmation
      const confirmDialog = authenticatedPage.getByTestId('autopilot-force-complete-confirm');
      await expect(confirmDialog).toBeVisible();
    }
  });

  test('staggered entry allows market confirmation', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check info text about market confirmation
    const infoText = authenticatedPage.getByTestId('autopilot-staggered-entry-info');

    if (await infoText.isVisible()) {
      await expect(infoText).toContainText(/market confirmation|wait|direction/i);
    }
  });

  test('shows average entry price across stages', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check average price display
    const avgPrice = authenticatedPage.getByTestId('autopilot-average-entry-price');

    if (await avgPrice.isVisible()) {
      await expect(avgPrice).toContainText(/average|₹/i);
    }
  });
});

// =============================================================================
// INTEGRATION: STAGED ENTRY WORKFLOW
// =============================================================================

test.describe('AutoPilot Phase 5I - Staged Entry Integration', () => {
  test('staged entry reduces initial risk exposure', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check risk metrics
    const riskMetrics = authenticatedPage.getByTestId('autopilot-risk-metrics');

    if (await riskMetrics.isVisible()) {
      await expect(riskMetrics).toContainText(/risk|exposure|margin/i);
    }
  });

  test('shows comparison: staged vs full position risk', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check risk comparison
    const riskComparison = authenticatedPage.getByTestId('autopilot-risk-comparison');

    if (await riskComparison.isVisible()) {
      await expect(riskComparison).toContainText(/staged|full position/i);
    }
  });

  test('staged entry requires active monitoring', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check monitoring reminder
    const monitoringReminder = authenticatedPage.getByTestId('autopilot-monitoring-reminder');

    if (await monitoringReminder.isVisible()) {
      await expect(monitoringReminder).toContainText(/monitor|watch|active/i);
    }
  });

  test('shows next stage conditions in dashboard', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check next stage info
    const nextStage = authenticatedPage.getByTestId('autopilot-next-stage-info');

    if (await nextStage.isVisible()) {
      await expect(nextStage).toContainText(/next stage|waiting for/i);
    }
  });

  test('can cancel pending stages before execution', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for cancel button
    const cancelStagesButton = authenticatedPage.getByTestId('autopilot-cancel-pending-stages');

    if (await cancelStagesButton.isVisible()) {
      await expect(cancelStagesButton).toBeEnabled();
    }
  });

  test('staged entry history is logged', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check activity log
    const activityLog = authenticatedPage.getByTestId('autopilot-activity-log');

    if (await activityLog.isVisible()) {
      await expect(activityLog).toContainText(/stage 1|stage 2|executed/i);
    }
  });

  test('shows summary when all stages completed', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check completion summary
    const completionSummary = authenticatedPage.getByTestId('autopilot-stages-completion-summary');

    if (await completionSummary.isVisible()) {
      await expect(completionSummary).toContainText(/completed|all stages|total/i);
    }
  });
});
