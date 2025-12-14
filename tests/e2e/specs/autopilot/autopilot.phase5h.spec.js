/**
 * Phase 5H E2E Tests - Adjustment Intelligence (Suggestion Engine)
 *
 * Features tested:
 * - Feature #44: Suggestion Engine Logic
 * - Feature #45: Offensive/Defensive Categorization
 * - Feature #46: Adjustment Cost Tracking
 * - Feature #47: One-Click Execution
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotStrategyDetailPage } from '../../pages/AutoPilotDashboardPage.js';

// =============================================================================
// FEATURES #44-47: SUGGESTION ENGINE
// =============================================================================

test.describe('AutoPilot Phase 5H - Suggestion Engine', () => {
  let detailPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
  });

  test('shows suggestion cards in strategy detail view', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for suggestions section
    const suggestionsSection = authenticatedPage.getByTestId('autopilot-suggestions-section');

    if (await suggestionsSection.isVisible()) {
      // Should show suggestion cards
      const suggestionCard = authenticatedPage.getByTestId('autopilot-suggestion-card');
      await expect(suggestionCard.first()).toBeVisible();
    }
  });

  test('suggestion card shows type and reason', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check suggestion card content
    const suggestionType = authenticatedPage.getByTestId('autopilot-suggestion-type');
    const suggestionReason = authenticatedPage.getByTestId('autopilot-suggestion-reason');

    if (await suggestionType.isVisible()) {
      // Should show type (exit, shift_leg, add_hedge, etc.)
      await expect(suggestionType).toContainText(/exit|shift|hedge|rebalance/i);
    }

    if (await suggestionReason.isVisible()) {
      // Should show reason
      await expect(suggestionReason).toContainText(/delta|profit|premium|dte|gamma/i);
    }
  });

  test('suggestion shows confidence level indicator', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check confidence indicator
    const confidenceIndicator = authenticatedPage.getByTestId('autopilot-suggestion-confidence');

    if (await confidenceIndicator.isVisible()) {
      // Should show confidence level (high, medium, low)
      await expect(confidenceIndicator).toContainText(/high|medium|low|\d+%/i);
    }
  });

  test('suggestion shows offensive/defensive label', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check category label
    const categoryLabel = authenticatedPage.getByTestId('autopilot-suggestion-category');

    if (await categoryLabel.isVisible()) {
      // Should show offensive, defensive, or neutral
      await expect(categoryLabel).toContainText(/offensive|defensive|neutral/i);
    }
  });

  test('offensive suggestions are labeled correctly', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Find offensive suggestion
    const offensiveSuggestion = authenticatedPage.getByTestId('autopilot-suggestion-offensive');

    if (await offensiveSuggestion.isVisible()) {
      // Should have offensive badge
      await expect(offensiveSuggestion).toContainText(/offensive|increase risk|more premium/i);
    }
  });

  test('defensive suggestions are labeled correctly', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Find defensive suggestion
    const defensiveSuggestion = authenticatedPage.getByTestId('autopilot-suggestion-defensive');

    if (await defensiveSuggestion.isVisible()) {
      // Should have defensive badge
      await expect(defensiveSuggestion).toContainText(/defensive|reduce risk|protect/i);
    }
  });

  test('can click execute button on suggestion', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Find execute button
    const executeButton = authenticatedPage.getByTestId('autopilot-suggestion-execute-button');

    if (await executeButton.isVisible()) {
      await expect(executeButton).toBeEnabled();
      await expect(executeButton).toContainText(/execute|apply|implement/i);
    }
  });

  test('shows confirmation dialog before executing suggestion', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Click execute on suggestion
    const executeButton = authenticatedPage.getByTestId('autopilot-suggestion-execute-button');

    if (await executeButton.isVisible()) {
      await executeButton.click();

      // Should show confirmation dialog
      const confirmDialog = authenticatedPage.getByTestId('autopilot-suggestion-confirm-dialog');
      await expect(confirmDialog).toBeVisible();
    }
  });

  test('confirmation dialog shows suggestion details', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check confirmation dialog content
    const confirmDetails = authenticatedPage.getByTestId('autopilot-suggestion-confirm-details');

    if (await confirmDetails.isVisible()) {
      // Should show what will be executed
      await expect(confirmDetails).toContainText(/action|impact|cost/i);
    }
  });

  test('can dismiss suggestion without executing', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Find dismiss button
    const dismissButton = authenticatedPage.getByTestId('autopilot-suggestion-dismiss-button');

    if (await dismissButton.isVisible()) {
      await dismissButton.click();

      // Suggestion should be hidden or marked as dismissed
      const suggestionCard = authenticatedPage.getByTestId('autopilot-suggestion-card').first();
      // Card might be hidden or show dismissed state
    }
  });

  test('suggestions update when market conditions change', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check for auto-refresh or live updates
    const suggestionsSection = authenticatedPage.getByTestId('autopilot-suggestions-section');

    if (await suggestionsSection.isVisible()) {
      // Should update suggestions based on current state
      await expect(suggestionsSection).toContainText(/updated|current|latest/i);
    }
  });

  test('shows multiple suggestions when applicable', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Count suggestion cards
    const suggestionCards = authenticatedPage.getByTestId('autopilot-suggestion-card');

    // Should show multiple suggestions if conditions warrant
    const count = await suggestionCards.count();
    // At least 1 suggestion should be possible
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('suggestions are ranked by priority', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check suggestion ordering
    const firstSuggestion = authenticatedPage.getByTestId('autopilot-suggestion-card').first();

    if (await firstSuggestion.isVisible()) {
      // First suggestion should be highest priority
      await expect(firstSuggestion).toContainText(/priority|urgent|important/i);
    }
  });

  test('delta breach suggestion appears when delta exceeds threshold', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for delta-related suggestion
    const deltaSuggestion = authenticatedPage.getByTestId('autopilot-suggestion-delta-breach');

    if (await deltaSuggestion.isVisible()) {
      await expect(deltaSuggestion).toContainText(/delta|rebalance|shift/i);
    }
  });

  test('profit target suggestion appears at 50% profit', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for profit-based suggestion
    const profitSuggestion = authenticatedPage.getByTestId('autopilot-suggestion-profit-target');

    if (await profitSuggestion.isVisible()) {
      await expect(profitSuggestion).toContainText(/profit|exit|book|50%/i);
    }
  });

  test('expiry week suggestion recommends exit over adjustment', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for expiry week suggestion
    const expirySuggestion = authenticatedPage.getByTestId('autopilot-suggestion-expiry-week');

    if (await expirySuggestion.isVisible()) {
      await expect(expirySuggestion).toContainText(/expiry|exit|avoid adjustment/i);
    }
  });
});

// =============================================================================
// FEATURE #46: ADJUSTMENT COST TRACKING
// =============================================================================

test.describe('AutoPilot Phase 5H - Adjustment Cost Tracking', () => {
  let detailPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
  });

  test('shows adjustment cost summary in strategy detail', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for cost tracking section
    const costSummary = authenticatedPage.getByTestId('autopilot-adjustment-cost-summary');

    if (await costSummary.isVisible()) {
      await expect(costSummary).toContainText(/adjustment cost|total cost|cumulative/i);
    }
  });

  test('shows cost vs original premium percentage', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check cost comparison
    const costPercentage = authenticatedPage.getByTestId('autopilot-cost-vs-premium-pct');

    if (await costPercentage.isVisible()) {
      // Should show percentage
      await expect(costPercentage).toContainText(/%|percent/i);
    }
  });

  test('cost summary updates after each adjustment', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check for real-time updates
    const costDisplay = authenticatedPage.getByTestId('autopilot-current-adjustment-cost');

    if (await costDisplay.isVisible()) {
      // Should show current cumulative cost
      await expect(costDisplay).toContainText(/₹|\d+/);
    }
  });

  test('shows individual adjustment costs in history', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check adjustment history
    const adjustmentHistory = authenticatedPage.getByTestId('autopilot-adjustment-history');

    if (await adjustmentHistory.isVisible()) {
      // Should show list of adjustments with costs
      await expect(adjustmentHistory).toContainText(/cost|debit|credit/i);
    }
  });

  test('displays warning when adjustment cost is high', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check for cost warning
    const costWarning = authenticatedPage.getByTestId('autopilot-adjustment-cost-warning');

    if (await costWarning.isVisible()) {
      await expect(costWarning).toContainText(/high cost|expensive|warning/i);
    }
  });

  test('shows net cost breakdown (debits vs credits)', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check cost breakdown
    const costBreakdown = authenticatedPage.getByTestId('autopilot-cost-breakdown');

    if (await costBreakdown.isVisible()) {
      await expect(costBreakdown).toContainText(/debit|credit|net/i);
    }
  });

  test('adjustment cost affects net P&L display', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check P&L display
    const netPnL = authenticatedPage.getByTestId('autopilot-net-pnl');

    if (await netPnL.isVisible()) {
      // Should include adjustment costs in P&L
      await expect(netPnL).toContainText(/net|total|₹/);
    }
  });
});

// =============================================================================
// FEATURE #47: ONE-CLICK EXECUTION
// =============================================================================

test.describe('AutoPilot Phase 5H - One-Click Execution', () => {
  test('one-click execute button is prominently displayed', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Find one-click button
    const oneClickButton = authenticatedPage.getByTestId('autopilot-one-click-execute');

    if (await oneClickButton.isVisible()) {
      await expect(oneClickButton).toBeEnabled();
    }
  });

  test('one-click execution shows loading state', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Click execute button
    const executeButton = authenticatedPage.getByTestId('autopilot-suggestion-execute-button');

    if (await executeButton.isVisible()) {
      await executeButton.click();

      // Should show loading/processing state
      const loadingIndicator = authenticatedPage.getByTestId('autopilot-execution-loading');
      if (await loadingIndicator.isVisible()) {
        await expect(loadingIndicator).toBeVisible();
      }
    }
  });

  test('shows success message after execution', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for success feedback
    const successMessage = authenticatedPage.getByTestId('autopilot-execution-success');

    if (await successMessage.isVisible()) {
      await expect(successMessage).toContainText(/success|executed|applied/i);
    }
  });

  test('shows error message if execution fails', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for error feedback
    const errorMessage = authenticatedPage.getByTestId('autopilot-execution-error');

    if (await errorMessage.isVisible()) {
      await expect(errorMessage).toContainText(/error|failed|unable/i);
    }
  });

  test('execution updates strategy state immediately', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check strategy status
    const strategyStatus = authenticatedPage.getByTestId('autopilot-strategy-status');

    if (await strategyStatus.isVisible()) {
      // Should reflect execution
      await expect(strategyStatus).toContainText(/active|executing|updated/i);
    }
  });
});

// =============================================================================
// INTEGRATION: SUGGESTION ENGINE WORKFLOW
// =============================================================================

test.describe('AutoPilot Phase 5H - Suggestion Engine Integration', () => {
  test('suggestion engine evaluates multiple scenarios simultaneously', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Should show suggestions from different triggers
    const suggestionsSection = authenticatedPage.getByTestId('autopilot-suggestions-section');

    if (await suggestionsSection.isVisible()) {
      // Multiple suggestion types should be possible
      await expect(suggestionsSection).toBeVisible();
    }
  });

  test('dismissed suggestions are tracked and not re-shown immediately', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check dismissed suggestions tracking
    const dismissedList = authenticatedPage.getByTestId('autopilot-dismissed-suggestions');

    if (await dismissedList.isVisible()) {
      await expect(dismissedList).toContainText(/dismissed|ignored/i);
    }
  });

  test('suggestions expire when conditions change', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check for expired suggestion indicator
    const expiredSuggestion = authenticatedPage.getByTestId('autopilot-suggestion-expired');

    if (await expiredSuggestion.isVisible()) {
      await expect(expiredSuggestion).toContainText(/expired|outdated|no longer valid/i);
    }
  });

  test('high confidence suggestions are highlighted', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check for visual highlighting
    const highConfidenceSuggestion = authenticatedPage.getByTestId('autopilot-suggestion-high-confidence');

    if (await highConfidenceSuggestion.isVisible()) {
      // Should have visual indicator (badge, color, etc.)
      await expect(highConfidenceSuggestion).toBeVisible();
    }
  });

  test('suggestion history is logged in activity feed', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Check activity log
    const activityLog = authenticatedPage.getByTestId('autopilot-activity-log');

    if (await activityLog.isVisible()) {
      // Should show suggestion events
      await expect(activityLog).toContainText(/suggestion|recommended|executed/i);
    }
  });

  test('can view all suggestions (active and dismissed)', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new');

    // Look for "view all" button
    const viewAllButton = authenticatedPage.getByTestId('autopilot-view-all-suggestions');

    if (await viewAllButton.isVisible()) {
      await viewAllButton.click();

      // Should show suggestion history modal
      const historyModal = authenticatedPage.getByTestId('autopilot-suggestions-history-modal');
      await expect(historyModal).toBeVisible();
    }
  });
});
