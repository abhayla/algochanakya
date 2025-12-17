/**
 * AutoPilot Phases 1, 2, 3 E2E Tests
 *
 * Tests for:
 * - Phase 1: Strike Selection Integration
 * - Phase 2: Premium Monitoring Charts
 * - Phase 3: Re-Entry & Advanced Adjustments
 *
 * @tags @autopilot @phases123
 */

import { test, expect } from '../../fixtures/auth.fixture.js'
import { AutoPilotDashboardPage } from '../../pages/AutoPilotDashboardPage.js'

// Phase 1: Strike Selection tests REMOVED
// Reason: AutoPilot uses template-based wizard, not leg-by-leg configuration
// Components (StrikeSelector, StrikeLadder) exist but are unused in current architecture

test.describe('AutoPilot Phase 2: Premium Monitoring Charts', () => {
  let dashboardPage

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage)
    await dashboardPage.goto()
  })

  test('should navigate to strategy detail view', async ({ authenticatedPage }) => {
    // Click on first strategy card (if exists)
    const strategyCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first()
    const cardExists = await strategyCard.count() > 0

    if (cardExists) {
      await strategyCard.click()

      // Verify navigation to detail view
      await expect(authenticatedPage).toHaveURL(/\/autopilot\/strategies\/\d+/)
    }
  })

  test('should display Charts tab button', async ({ authenticatedPage }) => {
    // Navigate to a strategy detail (use test strategy ID)
    await authenticatedPage.goto('/autopilot/strategies/1')

    // Verify Charts tab is visible
    const chartsTab = authenticatedPage.locator('[data-testid="strategy-detail-charts-tab"]')
    await expect(chartsTab).toBeVisible()
  })

  test('should switch to Charts tab', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/1')

    // Click Charts tab
    await authenticatedPage.click('[data-testid="strategy-detail-charts-tab"]')

    // Verify Charts section is visible
    const chartsSection = authenticatedPage.locator('[data-testid="strategy-detail-charts-section"]')
    await expect(chartsSection).toBeVisible()
  })

  test('should display Straddle Premium Chart component', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/1')
    await authenticatedPage.click('[data-testid="strategy-detail-charts-tab"]')

    // Verify chart component is rendered
    const premiumChart = authenticatedPage.locator('[data-testid="straddle-premium-chart"]')
    await expect(premiumChart).toBeVisible()
  })

  test('should display Theta Decay Chart component', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/1')
    await authenticatedPage.click('[data-testid="strategy-detail-charts-tab"]')

    // Verify chart component is rendered
    const decayChart = authenticatedPage.locator('[data-testid="theta-decay-chart"]')
    await expect(decayChart).toBeVisible()
  })

  test('should display chart title for Premium Monitor', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/1')
    await authenticatedPage.click('[data-testid="strategy-detail-charts-tab"]')

    // Verify chart title
    await expect(authenticatedPage.locator('text=Premium Monitor')).toBeVisible()
  })

  test('should display chart title for Theta Decay', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/1')
    await authenticatedPage.click('[data-testid="strategy-detail-charts-tab"]')

    // Verify chart title
    await expect(authenticatedPage.locator('text=Theta Decay - Expected vs Actual')).toBeVisible()
  })

  test('should show loading state when strategy data missing', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/9999') // Non-existent strategy
    await authenticatedPage.click('[data-testid="strategy-detail-charts-tab"]')

    // Verify loading text
    const loadingText = authenticatedPage.locator('text=Loading strategy data...')
    await expect(loadingText).toBeVisible()
  })

  test('should have proper chart container styling', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/1')
    await authenticatedPage.click('[data-testid="strategy-detail-charts-tab"]')

    // Verify chart content has min-height
    const chartContent = authenticatedPage.locator('.chart-content').first()
    const styles = await chartContent.evaluate(el => {
      const computed = window.getComputedStyle(el)
      return {
        minHeight: computed.minHeight,
        padding: computed.padding
      }
    })

    expect(styles.minHeight).toBe('300px')
  })
})

test.describe('AutoPilot Phase 3: Re-Entry Configuration', () => {
  let dashboardPage

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage)

    // Navigate directly to strategy builder
    await authenticatedPage.goto('/autopilot/strategies/new')
    await authenticatedPage.waitForLoadState('networkidle')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-builder-form"]', { timeout: 10000 })
  })

  test('should display Re-Entry Configuration section', async ({ authenticatedPage }) => {
    const reentrySection = authenticatedPage.locator('[data-testid="autopilot-reentry-config"]')
    await expect(reentrySection).toBeVisible()
  })

  test('should have re-entry toggle switch', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.locator('[data-testid="autopilot-reentry-toggle"]')
    await expect(toggle).toBeVisible()
  })

  test('should enable re-entry when toggle is clicked', async ({ authenticatedPage }) => {
    // Click toggle
    await authenticatedPage.click('[data-testid="autopilot-reentry-toggle"]')

    // Verify toggle is checked
    const toggleInput = authenticatedPage.locator('[data-testid="autopilot-reentry-toggle"] input')
    await expect(toggleInput).toBeChecked()

    // Verify configuration options appear
    const maxReentriesSelect = authenticatedPage.locator('[data-testid="autopilot-reentry-max-reentries"]')
    await expect(maxReentriesSelect).toBeVisible()
  })

  test('should display max re-entries dropdown when enabled', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-reentry-toggle"]')

    const select = authenticatedPage.locator('[data-testid="autopilot-reentry-max-reentries"]')
    await expect(select).toBeVisible()

    // Verify options are available
    const options = await select.locator('option').count()
    expect(options).toBeGreaterThan(0)
  })

  test('should select max re-entries value', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-reentry-toggle"]')

    // Select 3 times
    await authenticatedPage.selectOption('[data-testid="autopilot-reentry-max-reentries"]', '3')

    // Verify selection
    const value = await authenticatedPage.inputValue('[data-testid="autopilot-reentry-max-reentries"]')
    expect(value).toBe('3')
  })

  test('should display cooldown period dropdown', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-reentry-toggle"]')

    const select = authenticatedPage.locator('[data-testid="autopilot-reentry-cooldown"]')
    await expect(select).toBeVisible()
  })

  test('should select cooldown period', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-reentry-toggle"]')

    // Select 30 minutes
    await authenticatedPage.selectOption('[data-testid="autopilot-reentry-cooldown"]', '30')

    // Verify selection
    const value = await authenticatedPage.inputValue('[data-testid="autopilot-reentry-cooldown"]')
    expect(value).toBe('30')
  })

  test('should display re-entry conditions section', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-reentry-toggle"]')

    // Verify ConditionBuilder is present
    const conditionBuilder = authenticatedPage.locator('[data-testid="autopilot-reentry-conditions"]')
    await expect(conditionBuilder).toBeVisible()
  })

  test('should display info box explaining re-entry workflow', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-reentry-toggle"]')

    // Verify info box is visible
    const infoBox = authenticatedPage.locator('.reentry-info-box')
    await expect(infoBox).toBeVisible()

    // Verify it contains helpful text
    await expect(infoBox).toContainText('How Re-Entry Works')
  })

  test('should hide configuration when toggle is disabled', async ({ authenticatedPage }) => {
    // Enable first
    await authenticatedPage.click('[data-testid="autopilot-reentry-toggle"]')

    // Verify config is visible
    const maxReentries = authenticatedPage.locator('[data-testid="autopilot-reentry-max-reentries"]')
    await expect(maxReentries).toBeVisible()

    // Disable
    await authenticatedPage.click('[data-testid="autopilot-reentry-toggle"]')

    // Verify config is hidden
    await expect(maxReentries).not.toBeVisible()
  })

  test('should show disabled state message when toggle off', async ({ authenticatedPage }) => {
    // Verify disabled message
    const disabledMessage = authenticatedPage.locator('text=Enable re-entry to automatically re-enter')
    await expect(disabledMessage).toBeVisible()
  })

  test('should display re-entry count when editing existing strategy', async ({ authenticatedPage }) => {
    // Navigate to edit existing strategy with re-entry count
    // This would require a test strategy with reentry_count > 0
    await authenticatedPage.goto('/autopilot/strategies/1/edit')

    // Check if re-entry count is displayed (if strategy has re-entry enabled)
    const countDisplay = authenticatedPage.locator('[data-testid="autopilot-reentry-count"]')
    const exists = await countDisplay.count() > 0

    if (exists) {
      await expect(countDisplay).toBeVisible()
      await expect(countDisplay).toContainText('/')
    }
  })
})

test.describe('AutoPilot Phase 3: Adjustment Rule Builder', () => {
  let dashboardPage

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage)

    // Navigate directly to strategy builder
    await authenticatedPage.goto('/autopilot/strategies/new')
    await authenticatedPage.waitForLoadState('networkidle')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-builder-form"]', { timeout: 10000 })
  })

  test('should display Adjustment Rule Builder section', async ({ authenticatedPage }) => {
    const builder = authenticatedPage.locator('[data-testid="autopilot-adjustment-rule-builder"]')
    await expect(builder).toBeVisible()
  })

  test('should have Add Rule button', async ({ authenticatedPage }) => {
    const addBtn = authenticatedPage.locator('[data-testid="autopilot-add-rule-btn"]')
    await expect(addBtn).toBeVisible()
  })

  test('should show empty state when no rules', async ({ authenticatedPage }) => {
    const emptyState = authenticatedPage.locator('text=No adjustment rules configured')
    await expect(emptyState).toBeVisible()
  })

  test('should open rule modal when Add Rule clicked', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')

    // Verify modal is visible
    const modal = authenticatedPage.locator('[data-testid="autopilot-rule-modal"]')
    await expect(modal).toBeVisible()
  })

  test('should display rule form fields in modal', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')

    // Verify form fields
    await expect(authenticatedPage.locator('[data-testid="autopilot-rule-name"]')).toBeVisible()
    await expect(authenticatedPage.locator('[data-testid="autopilot-rule-trigger-type"]')).toBeVisible()
    await expect(authenticatedPage.locator('[data-testid="autopilot-rule-action-type"]')).toBeVisible()
    await expect(authenticatedPage.locator('[data-testid="autopilot-rule-cooldown"]')).toBeVisible()
    await expect(authenticatedPage.locator('[data-testid="autopilot-rule-max-executions"]')).toBeVisible()
  })

  test('should have 6 trigger types in dropdown', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')

    // Count trigger type options
    const triggerSelect = authenticatedPage.locator('[data-testid="autopilot-rule-trigger-type"]')
    const options = await triggerSelect.locator('option').count()

    expect(options).toBe(6) // pnl, delta, time, premium, vix, spot
  })

  test('should have 7 action types in dropdown', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')

    // Count action type options
    const actionSelect = authenticatedPage.locator('[data-testid="autopilot-rule-action-type"]')
    const options = await actionSelect.locator('option').count()

    expect(options).toBe(7) // exit_all, add_hedge, close_leg, roll_strike, roll_expiry, scale_down, scale_up
  })

  test('should create new rule', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')

    // Fill form
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'Delta Hedge Test')
    await authenticatedPage.selectOption('[data-testid="autopilot-rule-trigger-type"]', 'delta_based')
    await authenticatedPage.selectOption('[data-testid="autopilot-rule-action-type"]', 'add_hedge')
    await authenticatedPage.fill('[data-testid="autopilot-rule-cooldown"]', '300')
    await authenticatedPage.fill('[data-testid="autopilot-rule-max-executions"]', '2')

    // Save
    await authenticatedPage.click('[data-testid="autopilot-rule-save"]')

    // Verify rule card appears
    const ruleCard = authenticatedPage.locator('[data-testid="autopilot-rule-card-0"]')
    await expect(ruleCard).toBeVisible()
    await expect(ruleCard).toContainText('Delta Hedge Test')
  })

  test('should display rule with WHEN → THEN flow', async ({ authenticatedPage }) => {
    // Create a rule first
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'Test Rule')
    await authenticatedPage.click('[data-testid="autopilot-rule-save"]')

    // Verify flow display
    const ruleCard = authenticatedPage.locator('[data-testid="autopilot-rule-card-0"]')
    await expect(ruleCard).toContainText('WHEN')
    await expect(ruleCard).toContainText('THEN')
    await expect(ruleCard).toContainText('→')
  })

  test('should display rule metadata (cooldown, max executions)', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'Test Rule')
    await authenticatedPage.fill('[data-testid="autopilot-rule-cooldown"]', '600')
    await authenticatedPage.fill('[data-testid="autopilot-rule-max-executions"]', '3')
    await authenticatedPage.click('[data-testid="autopilot-rule-save"]')

    const ruleCard = authenticatedPage.locator('[data-testid="autopilot-rule-card-0"]')
    await expect(ruleCard).toContainText('Cooldown:')
    await expect(ruleCard).toContainText('Max:')
  })

  test('should edit existing rule', async ({ authenticatedPage }) => {
    // Create rule
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'Original Name')
    await authenticatedPage.click('[data-testid="autopilot-rule-save"]')

    // Edit rule
    await authenticatedPage.click('[data-testid="autopilot-edit-rule-0"]')
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'Updated Name')
    await authenticatedPage.click('[data-testid="autopilot-rule-save"]')

    // Verify update
    const ruleCard = authenticatedPage.locator('[data-testid="autopilot-rule-card-0"]')
    await expect(ruleCard).toContainText('Updated Name')
  })

  test('should delete rule with confirmation', async ({ authenticatedPage }) => {
    // Create rule
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'To Delete')
    await authenticatedPage.click('[data-testid="autopilot-rule-save"]')

    // Setup dialog handler
    authenticatedPage.on('dialog', dialog => dialog.accept())

    // Delete rule
    await authenticatedPage.click('[data-testid="autopilot-delete-rule-0"]')

    // Verify rule is gone
    const ruleCard = authenticatedPage.locator('[data-testid="autopilot-rule-card-0"]')
    await expect(ruleCard).not.toBeVisible()
  })

  test('should move rule up', async ({ authenticatedPage }) => {
    // Create 2 rules
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'Rule 1')
    await authenticatedPage.click('[data-testid="autopilot-rule-save"]')

    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'Rule 2')
    await authenticatedPage.click('[data-testid="autopilot-rule-save"]')

    // Move Rule 2 up
    await authenticatedPage.click('[data-testid="autopilot-move-rule-up-1"]')

    // Verify order changed
    const firstRule = authenticatedPage.locator('[data-testid="autopilot-rule-card-0"]')
    await expect(firstRule).toContainText('Rule 2')
  })

  test('should move rule down', async ({ authenticatedPage }) => {
    // Create 2 rules
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'Rule 1')
    await authenticatedPage.click('[data-testid="autopilot-rule-save"]')

    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'Rule 2')
    await authenticatedPage.click('[data-testid="autopilot-rule-save"]')

    // Move Rule 1 down
    await authenticatedPage.click('[data-testid="autopilot-move-rule-down-0"]')

    // Verify order changed
    const secondRule = authenticatedPage.locator('[data-testid="autopilot-rule-card-1"]')
    await expect(secondRule).toContainText('Rule 1')
  })

  test('should cancel rule creation', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="autopilot-add-rule-btn"]')
    await authenticatedPage.fill('[data-testid="autopilot-rule-name"]', 'Cancelled Rule')

    // Cancel
    await authenticatedPage.click('[data-testid="autopilot-rule-cancel"]')

    // Verify modal closed and no rule added
    const modal = authenticatedPage.locator('[data-testid="autopilot-rule-modal"]')
    await expect(modal).not.toBeVisible()

    const emptyState = authenticatedPage.locator('text=No adjustment rules configured')
    await expect(emptyState).toBeVisible()
  })
})

// Phase 3: Roll Wizard tests REMOVED
// Reason: RollWizard.vue component exists but has no trigger point in UI

// Phase 1: Strike Preview API tests REMOVED
// Reason: API endpoint exists but is unused by frontend (architecture mismatch)
