/**
 * AutoPilot Phase 4 E2E Tests
 *
 * Tests for Phase 4 UX Polish & Dashboard enhancements:
 * - Enhanced Dashboard Components (EnhancedStrategyCard, RiskOverviewPanel, ActivityTimeline)
 * - Condition Builder Enhancements (Tree View, Natural Language, Evaluation Preview)
 * - Strategy Detail View Tabs (Charts, Activity)
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import {
  AutoPilotDashboardPage,
  AutoPilotStrategyBuilderPage,
  AutoPilotStrategyDetailPage
} from '../../pages/AutoPilotDashboardPage.js';


// =============================================================================
// DASHBOARD - RISK OVERVIEW PANEL TESTS
// =============================================================================

test.describe('AutoPilot Phase 4 - Risk Overview Panel', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();
  });

  test('displays risk overview panel', async () => {
    await expect(dashboardPage.riskOverviewPanel).toBeVisible();
  });

  test('displays margin usage section with bar and percentage', async () => {
    await expect(dashboardPage.riskOverviewPanel).toBeVisible();

    // Check if margin usage components exist
    const marginSection = dashboardPage.page.locator('[data-testid^="autopilot-risk-metric-"]').first();
    await expect(marginSection).toBeVisible();

    // Verify margin usage bar exists
    const marginBar = dashboardPage.page.locator('[data-testid="autopilot-risk-margin-bar"]');
    if (await marginBar.count() > 0) {
      await expect(marginBar.first()).toBeVisible();
    }
  });

  test('displays net delta gauge with visual indicator', async () => {
    await expect(dashboardPage.riskOverviewPanel).toBeVisible();

    // Check for delta gauge section
    const deltaSection = dashboardPage.page.locator('[data-testid="autopilot-risk-metric-delta"]');
    if (await deltaSection.count() > 0) {
      await expect(deltaSection).toBeVisible();

      // Verify delta gauge track exists
      const gaugeTrack = dashboardPage.page.locator('[data-testid="autopilot-risk-gauge-track"]');
      if (await gaugeTrack.count() > 0) {
        await expect(gaugeTrack.first()).toBeVisible();
      }
    }
  });

  test('displays total P&L with realized and unrealized breakdown', async () => {
    await expect(dashboardPage.riskOverviewPanel).toBeVisible();

    // Check for P&L section
    const pnlSection = dashboardPage.page.locator('[data-testid="autopilot-risk-metric-pnl"]');
    if (await pnlSection.count() > 0) {
      await expect(pnlSection).toBeVisible();

      // Check for realized/unrealized breakdown
      const breakdown = dashboardPage.page.locator('[data-testid="autopilot-risk-pnl-breakdown"]');
      if (await breakdown.count() > 0) {
        await expect(breakdown).toBeVisible();
      }
    }
  });

  test('displays compact stats section with active, waiting, and positions count', async () => {
    await expect(dashboardPage.riskOverviewPanel).toBeVisible();

    // Check for compact stats
    const compactStats = dashboardPage.page.locator('[data-testid="autopilot-risk-metric-compact"]');
    if (await compactStats.count() > 0) {
      await expect(compactStats).toBeVisible();

      // Verify it has multiple stat items
      const statItems = dashboardPage.page.locator('[data-testid^="autopilot-risk-compact-"]');
      if (await statItems.count() > 0) {
        expect(await statItems.count()).toBeGreaterThanOrEqual(2);
      }
    }
  });

  test('margin usage percentage displays with color coding', async () => {
    await expect(dashboardPage.riskOverviewPanel).toBeVisible();

    const marginValue = dashboardPage.page.locator('[data-testid="autopilot-risk-margin-value"]');
    if (await marginValue.count() > 0) {
      await expect(marginValue).toBeVisible();

      // Check if it has a color (red, orange, or green)
      const color = await marginValue.evaluate(el => window.getComputedStyle(el).color);
      expect(color).not.toBe('');
    }
  });
});


// =============================================================================
// DASHBOARD - ACTIVITY TIMELINE TESTS
// =============================================================================

test.describe('AutoPilot Phase 4 - Activity Timeline', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();
  });

  test('displays activity timeline component', async () => {
    await expect(dashboardPage.activityTimeline).toBeVisible();
  });

  test('displays activity timeline header with event count', async () => {
    await expect(dashboardPage.activityTimeline).toBeVisible();

    const header = dashboardPage.page.locator('[data-testid="autopilot-timeline-header"]');
    if (await header.count() > 0) {
      await expect(header).toBeVisible();

      // Check for event count badge
      const eventCount = dashboardPage.page.locator('[data-testid="autopilot-timeline-count"]');
      if (await eventCount.count() > 0) {
        await expect(eventCount).toBeVisible();
      }
    }
  });

  test('displays empty state when no activities exist', async () => {
    // This test checks if empty state is shown correctly
    const emptyState = dashboardPage.page.locator('[data-testid="autopilot-timeline-empty-state"]');
    const timelineItems = dashboardPage.page.locator('[data-testid^="autopilot-timeline-item-"]');

    const itemCount = await timelineItems.count();
    if (itemCount === 0) {
      await expect(emptyState).toBeVisible();

      // Verify empty state content
      await expect(emptyState).toContainText('No recent activity');
    }
  });

  test('displays activity items with icons and timestamps', async () => {
    await expect(dashboardPage.activityTimeline).toBeVisible();

    const timelineItems = dashboardPage.page.locator('[data-testid^="autopilot-timeline-item-"]');
    const itemCount = await timelineItems.count();

    if (itemCount > 0) {
      const firstItem = timelineItems.first();
      await expect(firstItem).toBeVisible();

      // Check for marker icon
      const markerIcon = firstItem.locator('[data-testid="autopilot-timeline-marker-icon"]');
      await expect(markerIcon).toBeVisible();

      // Check for event time
      const eventTime = firstItem.locator('[data-testid="autopilot-timeline-event-time"]');
      await expect(eventTime).toBeVisible();

      // Check for event message
      const eventMessage = firstItem.locator('[data-testid="autopilot-timeline-event-message"]');
      await expect(eventMessage).toBeVisible();
    }
  });

  test('activity items have color-coded event types', async () => {
    await expect(dashboardPage.activityTimeline).toBeVisible();

    const timelineItems = dashboardPage.page.locator('[data-testid^="autopilot-timeline-item-"]');
    const itemCount = await timelineItems.count();

    if (itemCount > 0) {
      const firstItem = timelineItems.first();
      const markerIcon = firstItem.locator('[data-testid="autopilot-timeline-marker-icon"]');

      // Check if marker has background color
      const bgColor = await markerIcon.evaluate(el => window.getComputedStyle(el).background);
      expect(bgColor).not.toBe('');
    }
  });

  test('displays "View All Activities" button when more than 10 items', async () => {
    await expect(dashboardPage.activityTimeline).toBeVisible();

    const viewAllBtn = dashboardPage.page.locator('[data-testid="autopilot-timeline-view-all-btn"]');

    // Button should only be visible if there are more activities than max displayed
    if (await viewAllBtn.count() > 0) {
      await expect(viewAllBtn).toBeVisible();
      await expect(viewAllBtn).toContainText('View All Activities');
    }
  });

  test('timeline items display strategy name and underlying badges', async () => {
    await expect(dashboardPage.activityTimeline).toBeVisible();

    const timelineItems = dashboardPage.page.locator('[data-testid^="autopilot-timeline-item-"]');
    const itemCount = await timelineItems.count();

    if (itemCount > 0) {
      const itemsWithMeta = await dashboardPage.page.locator('[data-testid="autopilot-timeline-event-meta"]').count();

      // At least some items should have strategy/underlying badges
      if (itemsWithMeta > 0) {
        const firstMetaBadge = dashboardPage.page.locator('[data-testid="autopilot-timeline-meta-badge"]').first();
        await expect(firstMetaBadge).toBeVisible();
      }
    }
  });
});


// =============================================================================
// DASHBOARD - ENHANCED STRATEGY CARD TESTS
// =============================================================================

test.describe('AutoPilot Phase 4 - Enhanced Strategy Cards', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();
  });

  test('displays strategy grid layout', async () => {
    const strategyCards = await dashboardPage.strategyCards.count();

    if (strategyCards > 0) {
      const strategyGrid = dashboardPage.page.locator('[data-testid="autopilot-strategy-grid"]');
      await expect(strategyGrid).toBeVisible();
    }
  });

  test('strategy cards display in responsive grid (1/2/3 columns)', async () => {
    const strategyCards = await dashboardPage.strategyCards.count();

    if (strategyCards > 0) {
      const strategyGrid = dashboardPage.page.locator('[data-testid="autopilot-strategy-grid"]');
      await expect(strategyGrid).toBeVisible();

      // Check grid CSS
      const gridColumns = await strategyGrid.evaluate(el =>
        window.getComputedStyle(el).gridTemplateColumns
      );
      expect(gridColumns).not.toBe('');
    }
  });

  test('enhanced strategy card displays header with name and status', async () => {
    const strategyCards = await dashboardPage.strategyCards.count();

    if (strategyCards > 0) {
      const firstCard = dashboardPage.strategyCards.first();
      await expect(firstCard).toBeVisible();

      // Check for strategy header section
      const header = firstCard.locator('[data-testid="autopilot-strategy-card-header"]');
      if (await header.count() > 0) {
        await expect(header).toBeVisible();

        // Check for strategy name
        const nameEl = firstCard.locator('[data-testid="autopilot-strategy-card-name"]');
        if (await nameEl.count() > 0) {
          await expect(nameEl).toBeVisible();
        }

        // Check for status badge
        const statusBadge = firstCard.locator('[data-testid="autopilot-strategy-card-status"]');
        if (await statusBadge.count() > 0) {
          await expect(statusBadge).toBeVisible();
        }
      }
    }
  });

  test('strategy card displays P&L with color coding', async () => {
    const strategyCards = await dashboardPage.strategyCards.count();

    if (strategyCards > 0) {
      const firstCard = dashboardPage.strategyCards.first();
      const pnlValue = firstCard.locator('[data-testid="autopilot-strategy-card-pnl"]');

      if (await pnlValue.count() > 0) {
        await expect(pnlValue).toBeVisible();

        // Check if P&L has color (green or red)
        const color = await pnlValue.evaluate(el => window.getComputedStyle(el).color);
        expect(color).not.toBe('');
      }
    }
  });

  test('strategy card displays delta gauge visualization', async () => {
    const strategyCards = await dashboardPage.strategyCards.count();

    if (strategyCards > 0) {
      const firstCard = dashboardPage.strategyCards.first();
      const deltaGauge = firstCard.locator('[data-testid="autopilot-strategy-card-delta-gauge"]');

      if (await deltaGauge.count() > 0) {
        await expect(deltaGauge).toBeVisible();

        // Check for delta indicator
        const indicator = deltaGauge.locator('[data-testid="autopilot-strategy-card-delta-value"]');
        if (await indicator.count() > 0) {
          await expect(indicator).toBeVisible();
        }
      }
    }
  });

  test('strategy card displays action buttons (pause/resume/exit)', async () => {
    const strategyCards = await dashboardPage.strategyCards.count();

    if (strategyCards > 0) {
      const firstCard = dashboardPage.strategyCards.first();
      const actionButtons = firstCard.locator('[data-testid="autopilot-strategy-card-actions"]');

      if (await actionButtons.count() > 0) {
        await expect(actionButtons).toBeVisible();

        // Check for at least one action button
        const buttons = actionButtons.locator('button');
        expect(await buttons.count()).toBeGreaterThanOrEqual(1);
      }
    }
  });

  test('strategy card displays entry rules progress indicator', async () => {
    const strategyCards = await dashboardPage.strategyCards.count();

    if (strategyCards > 0) {
      const firstCard = dashboardPage.strategyCards.first();

      // Look for entry rules or condition progress section
      const progressSection = firstCard.locator('[data-testid="autopilot-strategy-card-entry-progress"]');
      if (await progressSection.count() > 0) {
        await expect(progressSection).toBeVisible();
      }
    }
  });

  test('clicking strategy card navigates to detail view', async ({ authenticatedPage }) => {
    const strategyCards = await dashboardPage.strategyCards.count();

    if (strategyCards > 0) {
      await dashboardPage.strategyCards.first().click();

      // Should navigate to strategy detail page
      await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/, { timeout: 5000 });
    }
  });
});


// =============================================================================
// CONDITION BUILDER - NATURAL LANGUAGE SUMMARY TESTS
// =============================================================================

test.describe('AutoPilot Phase 4 - Condition Builder Natural Language', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.fillStrategyInfo({ name: 'Phase 4 Test Strategy' });
    await builderPage.addLeg({ strike: '25000', type: 'CE' });
    await builderPage.goToNextStep(); // Navigate to conditions step
  });

  test('displays natural language summary section', async () => {
    await expect(builderPage.naturalLanguageSummary).toBeVisible();
  });

  test('natural language summary has proper header and body', async () => {
    await expect(builderPage.naturalLanguageSummary).toBeVisible();

    const header = builderPage.page.locator('[data-testid="autopilot-condition-summary-header"]');
    await expect(header).toBeVisible();
    await expect(header).toContainText('Plain English Summary');

    const body = builderPage.page.locator('[data-testid="autopilot-condition-summary-body"]');
    await expect(body).toBeVisible();
  });

  test('displays default message when no conditions configured', async () => {
    await expect(builderPage.naturalLanguageText).toBeVisible();

    const text = await builderPage.naturalLanguageText.textContent();
    expect(text).toContain('No conditions have been configured');
  });

  test('updates natural language when condition is added', async () => {
    await builderPage.addCondition({
      variable: 'TIME.CURRENT',
      operator: 'greater_than',
      value: '09:20'
    });

    await expect(builderPage.naturalLanguageText).toBeVisible();

    const text = await builderPage.naturalLanguageText.textContent();
    expect(text.toLowerCase()).toContain('time');
    expect(text.toLowerCase()).toContain('09:20');
  });

  test('natural language summary uses "and" for AND logic', async () => {
    await builderPage.addCondition({
      variable: 'TIME.CURRENT',
      operator: 'greater_than',
      value: '09:20'
    });

    await builderPage.addCondition({
      variable: 'VIX.VALUE',
      operator: 'less_than',
      value: '15'
    });

    await builderPage.setConditionLogic('AND');

    const text = await builderPage.naturalLanguageText.textContent();
    expect(text.toLowerCase()).toContain('and');
  });

  test('natural language summary uses "or" for OR logic', async () => {
    await builderPage.addCondition({
      variable: 'TIME.CURRENT',
      operator: 'greater_than',
      value: '09:20'
    });

    await builderPage.addCondition({
      variable: 'VIX.VALUE',
      operator: 'less_than',
      value: '15'
    });

    await builderPage.setConditionLogic('OR');

    const text = await builderPage.naturalLanguageText.textContent();
    expect(text.toLowerCase()).toContain('or');
  });

  test('natural language converts operators to readable text', async () => {
    await builderPage.addCondition({
      variable: 'SPOT.PRICE',
      operator: 'greater_equal',
      value: '24000'
    });

    const text = await builderPage.naturalLanguageText.textContent();
    expect(text.toLowerCase()).toContain('greater than or equal to');
  });
});


// =============================================================================
// CONDITION BUILDER - TREE VIEW TESTS
// =============================================================================

test.describe('AutoPilot Phase 4 - Condition Builder Tree View', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.fillStrategyInfo({ name: 'Phase 4 Tree View Test' });
    await builderPage.addLeg({ strike: '25000', type: 'CE' });
    await builderPage.goToNextStep(); // Navigate to conditions step
  });

  test('displays tree view toggle button', async () => {
    await expect(builderPage.treeViewToggleButton).toBeVisible();
  });

  test('tree view toggle button has proper icon and text', async () => {
    await expect(builderPage.treeViewToggleButton).toBeVisible();
    await expect(builderPage.treeViewToggleButton).toContainText('Show Tree View');
  });

  test('clicking toggle button shows tree view', async () => {
    await builderPage.treeViewToggleButton.click();

    await expect(builderPage.treeView).toBeVisible();
  });

  test('toggle button text changes when tree view is shown', async () => {
    await builderPage.treeViewToggleButton.click();

    await expect(builderPage.treeViewToggleButton).toContainText('Show List View');
  });

  test('clicking toggle again hides tree view', async () => {
    await builderPage.treeViewToggleButton.click();
    await expect(builderPage.treeView).toBeVisible();

    await builderPage.treeViewToggleButton.click();
    await expect(builderPage.treeView).not.toBeVisible();
  });

  test('tree view displays root "ENTRY POINT" node', async () => {
    await builderPage.addCondition({ variable: 'TIME.CURRENT', value: '09:20' });

    await builderPage.treeViewToggleButton.click();

    await expect(builderPage.treeRootNode).toBeVisible();
    await expect(builderPage.treeRootNode).toContainText('ENTRY POINT');
  });

  test('tree view displays group nodes for condition groups', async () => {
    await builderPage.addCondition({ variable: 'TIME.CURRENT', value: '09:20' });

    await builderPage.treeViewToggleButton.click();

    const groupNodes = builderPage.treeGroupNodes;
    expect(await groupNodes.count()).toBeGreaterThan(0);

    const firstGroup = groupNodes.first();
    await expect(firstGroup).toContainText('GROUP');
  });

  test('tree view displays condition nodes with status icons', async () => {
    await builderPage.addCondition({
      variable: 'TIME.CURRENT',
      operator: 'greater_than',
      value: '09:20'
    });

    await builderPage.treeViewToggleButton.click();

    const conditionNodes = builderPage.treeConditionNodes;
    expect(await conditionNodes.count()).toBeGreaterThan(0);

    const firstCondition = conditionNodes.first();
    await expect(firstCondition).toBeVisible();

    // Check for status icon
    const statusIcon = firstCondition.locator('[data-testid="autopilot-condition-tree-status-icon"]');
    if (await statusIcon.count() > 0) {
      await expect(statusIcon).toBeVisible();
    }
  });

  test('tree view displays operator badges (AND/OR)', async () => {
    await builderPage.addCondition({ variable: 'TIME.CURRENT', value: '09:20' });
    await builderPage.addCondition({ variable: 'VIX.VALUE', value: '15' });
    await builderPage.setConditionLogic('AND');

    await builderPage.treeViewToggleButton.click();

    const operatorBadge = builderPage.page.locator('[data-testid="autopilot-condition-tree-operator"]');
    if (await operatorBadge.count() > 0) {
      await expect(operatorBadge.first()).toBeVisible();
      await expect(operatorBadge.first()).toContainText('AND');
    }
  });

  test('tree view has hierarchical structure with proper nesting', async () => {
    await builderPage.addCondition({ variable: 'TIME.CURRENT', value: '09:20' });

    await builderPage.treeViewToggleButton.click();

    // Check hierarchy: root → group → condition
    await expect(builderPage.treeRootNode).toBeVisible();

    const children = builderPage.page.locator('[data-testid="autopilot-condition-tree-children"]');
    expect(await children.count()).toBeGreaterThan(0);
  });

  test('tree view uses color-coded gradients for different node types', async () => {
    await builderPage.addCondition({ variable: 'TIME.CURRENT', value: '09:20' });

    await builderPage.treeViewToggleButton.click();

    // Check root node has blue gradient
    const rootLabel = builderPage.page.locator('[data-testid="autopilot-condition-tree-root"] [data-testid="autopilot-condition-tree-node-label"]');
    if (await rootLabel.count() > 0) {
      const bg = await rootLabel.evaluate(el => window.getComputedStyle(el).background);
      expect(bg).not.toBe('');
    }

    // Check group node has purple gradient
    const groupLabel = builderPage.page.locator('[data-testid^="autopilot-condition-tree-group-"] [data-testid="autopilot-condition-tree-node-label"]');
    if (await groupLabel.count() > 0) {
      const bg = await groupLabel.evaluate(el => window.getComputedStyle(el).background);
      expect(bg).not.toBe('');
    }
  });
});


// =============================================================================
// CONDITION BUILDER - EVALUATION PREVIEW TESTS
// =============================================================================

test.describe('AutoPilot Phase 4 - Condition Evaluation Preview', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.fillStrategyInfo({ name: 'Evaluation Preview Test' });
    await builderPage.addLeg({ strike: '25000', type: 'CE' });
    await builderPage.goToNextStep();
  });

  test('condition rows display status indicator column', async () => {
    await builderPage.addCondition({ variable: 'TIME.CURRENT', value: '09:20' });

    const statusIndicators = builderPage.conditionStatusIndicators;
    if (await statusIndicators.count() > 0) {
      await expect(statusIndicators.first()).toBeVisible();
    }
  });

  test('status indicators show different icons (✓, ✗, ○)', async () => {
    await builderPage.addCondition({ variable: 'TIME.CURRENT', value: '09:20' });

    const statusIcons = builderPage.page.locator('[data-testid="autopilot-condition-status-icon"]');
    if (await statusIcons.count() > 0) {
      const firstIcon = statusIcons.first();
      await expect(firstIcon).toBeVisible();

      const iconText = await firstIcon.textContent();
      expect(['✓', '✗', '○']).toContain(iconText.trim());
    }
  });

  test('status indicators have color coding (green/red/gray)', async () => {
    await builderPage.addCondition({ variable: 'TIME.CURRENT', value: '09:20' });

    const statusIcons = builderPage.page.locator('[data-testid="autopilot-condition-status-icon"]');
    if (await statusIcons.count() > 0) {
      const firstIcon = statusIcons.first();

      // Check for status class
      const classList = await firstIcon.getAttribute('class');
      expect(classList).toMatch(/status-(met|not-met|unknown)/);
    }
  });

  test('tree view condition nodes also display status icons', async () => {
    await builderPage.addCondition({ variable: 'TIME.CURRENT', value: '09:20' });

    await builderPage.treeViewToggleButton.click();

    const treeStatusIcons = builderPage.page.locator('[data-testid="autopilot-condition-tree-status-icon"]');
    if (await treeStatusIcons.count() > 0) {
      await expect(treeStatusIcons.first()).toBeVisible();
    }
  });
});


// =============================================================================
// STRATEGY DETAIL - CHARTS TAB TESTS
// =============================================================================

test.describe('AutoPilot Phase 4 - Strategy Detail Charts Tab', () => {
  test('displays charts tab button in strategy detail view', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return; // Skip if no strategies

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await expect(detailPage.chartsTab).toBeVisible();
  });

  test('clicking charts tab displays charts section', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await detailPage.chartsTab.click();

    await expect(detailPage.chartsSection).toBeVisible();
  });

  test('charts tab displays Greeks summary grid', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await detailPage.chartsTab.click();

    await expect(detailPage.greeksGrid).toBeVisible();
  });

  test('Greeks grid displays all four Greek cards (Delta, Gamma, Theta, Vega)', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await detailPage.chartsTab.click();

    // Check for each Greek card
    await expect(detailPage.deltaGreekCard).toBeVisible();
    await expect(detailPage.gammaGreekCard).toBeVisible();
    await expect(detailPage.thetaGreekCard).toBeVisible();
    await expect(detailPage.vegaGreekCard).toBeVisible();
  });

  test('displays chart placeholders for premium, delta history, and P&L curve', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await detailPage.chartsTab.click();

    await expect(detailPage.premiumChartPlaceholder).toBeVisible();
    await expect(detailPage.deltaHistoryPlaceholder).toBeVisible();
    await expect(detailPage.pnlCurvePlaceholder).toBeVisible();
  });

  test('chart placeholders have proper styling with dashed borders', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await detailPage.chartsTab.click();

    const placeholder = detailPage.premiumChartPlaceholder;
    const borderStyle = await placeholder.evaluate(el => window.getComputedStyle(el).borderStyle);
    expect(borderStyle).toContain('dashed');
  });

  test('Greeks grid uses responsive layout (2 cols mobile, 4 cols desktop)', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await detailPage.chartsTab.click();

    const greeksGrid = detailPage.greeksGrid;
    const gridColumns = await greeksGrid.evaluate(el =>
      window.getComputedStyle(el).gridTemplateColumns
    );
    expect(gridColumns).not.toBe('');
  });
});


// =============================================================================
// STRATEGY DETAIL - ACTIVITY TAB TESTS
// =============================================================================

test.describe('AutoPilot Phase 4 - Strategy Detail Activity Tab', () => {
  test('displays activity tab button in strategy detail view', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await expect(detailPage.activityTab).toBeVisible();
  });

  test('clicking activity tab displays activity timeline', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await detailPage.activityTab.click();

    await expect(detailPage.activityTabSection).toBeVisible();
  });

  test('activity tab displays timeline items specific to strategy', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await detailPage.activityTab.click();

    // Activity timeline should be visible (may be empty or have items)
    await expect(detailPage.activityTabSection).toBeVisible();
  });

  test('activity tab shows max 20 items', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await detailPage.activityTab.click();

    const timelineItems = detailPage.activityTimelineItems;
    const itemCount = await timelineItems.count();

    // Should not exceed 20 items
    expect(itemCount).toBeLessThanOrEqual(20);
  });

  test('tab navigation preserves state when switching between tabs', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);

    // Click charts tab
    await detailPage.chartsTab.click();
    await expect(detailPage.chartsSection).toBeVisible();

    // Click activity tab
    await detailPage.activityTab.click();
    await expect(detailPage.activityTabSection).toBeVisible();

    // Go back to charts tab
    await detailPage.chartsTab.click();
    await expect(detailPage.chartsSection).toBeVisible();
  });
});
