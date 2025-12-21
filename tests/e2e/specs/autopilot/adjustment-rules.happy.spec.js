/**
 * E2E Tests: Adjustment Rule Builder - Happy Path
 *
 * Tests the AdjustmentRuleBuilder component functionality:
 * - Add new rules
 * - Edit existing rules
 * - Delete rules
 * - Reorder rules
 * - Configure trigger and action types
 */

import { test, expect } from '../../fixtures/auth.fixture.js'

test.describe('AutoPilot - Adjustment Rule Builder (Happy Path)', () => {
  // Increase timeout for these tests due to heavy page loads
  test.setTimeout(30000)

  test.beforeEach(async ({ authenticatedPage }) => {
    // Navigate to AutoPilot strategy builder
    await authenticatedPage.goto('/autopilot/strategies/new', { waitUntil: 'domcontentloaded' })

    // Wait for page to load (use domcontentloaded instead of networkidle for faster tests)
    await expect(authenticatedPage.getByTestId('autopilot-strategy-builder')).toBeVisible({ timeout: 10000 })

    // Navigate to Step 3 (Monitoring & Adjustments) where AdjustmentRuleBuilder is located
    await authenticatedPage.getByTestId('autopilot-builder-monitoring-tab').click()
    await authenticatedPage.waitForTimeout(500)
  })

  test('should display adjustment rule builder section', async ({ authenticatedPage }) => {
    // Check that rule builder component is visible
    const ruleBuilder = authenticatedPage.getByTestId('autopilot-adjustment-rule-builder')
    await expect(ruleBuilder).toBeVisible()

    // Check title and subtitle (use role selector to avoid strict mode violation)
    await expect(ruleBuilder.getByRole('heading', { name: 'Adjustment Rules' })).toBeVisible()
    await expect(ruleBuilder.getByText('Automatic actions based on market conditions')).toBeVisible()

    // Check add rule button is visible
    await expect(authenticatedPage.getByTestId('autopilot-add-rule-btn')).toBeVisible()
  })

  test('should show empty state when no rules configured', async ({ authenticatedPage }) => {
    const ruleBuilder = authenticatedPage.getByTestId('autopilot-adjustment-rule-builder')

    // Check empty state is visible
    await expect(ruleBuilder.getByText('No adjustment rules configured')).toBeVisible()
    await expect(ruleBuilder.getByText(/Add rules to automatically adjust/)).toBeVisible()

    // Check "Add First Rule" button
    await expect(authenticatedPage.getByTestId('autopilot-add-first-rule-btn')).toBeVisible()
  })

  test('should open rule modal when clicking add rule', async ({ authenticatedPage }) => {
    // Click add rule button
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()

    // Check modal is visible
    const modal = authenticatedPage.getByTestId('autopilot-rule-modal')
    await expect(modal).toBeVisible()

    // Check modal title (use role to avoid strict mode violation - "Add Rule" also exists as button text)
    await expect(modal.getByRole('heading', { name: 'Add Rule' })).toBeVisible()

    // Check form fields are visible
    await expect(authenticatedPage.getByTestId('autopilot-rule-name')).toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-rule-trigger-type')).toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-rule-action-type')).toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-rule-cooldown')).toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-rule-max-executions')).toBeVisible()
  })

  test('should create a new rule with all fields', async ({ authenticatedPage }) => {
    // Click add rule button
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()

    // Fill in rule details
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Delta Hedge Rule')

    // Select trigger type
    const triggerSelect = authenticatedPage.getByTestId('autopilot-rule-trigger-type')
    await triggerSelect.selectOption({ value: 'delta_based' })

    // Select action type
    const actionSelect = authenticatedPage.getByTestId('autopilot-rule-action-type')
    await actionSelect.selectOption({ value: 'add_hedge' })

    // Set cooldown
    await authenticatedPage.getByTestId('autopilot-rule-cooldown').fill('300')

    // Set max executions
    await authenticatedPage.getByTestId('autopilot-rule-max-executions').fill('2')

    // Enable the rule
    await authenticatedPage.getByTestId('autopilot-rule-enabled').check()

    // Save the rule
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Verify modal closed
    await expect(authenticatedPage.getByTestId('autopilot-rule-modal')).not.toBeVisible()

    // Verify rule card is displayed
    const ruleCard = authenticatedPage.getByTestId('autopilot-rule-card-0')
    await expect(ruleCard).toBeVisible()

    // Verify rule details
    await expect(ruleCard.getByText('Delta Hedge Rule')).toBeVisible()
    await expect(ruleCard.getByText('Enabled')).toBeVisible()
  })

  test('should display all trigger types in dropdown', async ({ authenticatedPage }) => {
    // Open add rule modal
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()

    const triggerSelect = authenticatedPage.getByTestId('autopilot-rule-trigger-type')
    const options = await triggerSelect.locator('option').allTextContents()

    // Verify all trigger types are present
    expect(options.some(opt => opt.includes('P&L Based'))).toBeTruthy()
    expect(options.some(opt => opt.includes('Delta Based'))).toBeTruthy()
    expect(options.some(opt => opt.includes('Time Based'))).toBeTruthy()
    expect(options.some(opt => opt.includes('Premium Based'))).toBeTruthy()
    expect(options.some(opt => opt.includes('VIX Based'))).toBeTruthy()
    expect(options.some(opt => opt.includes('Spot Based'))).toBeTruthy()
  })

  test('should display all action types in dropdown', async ({ authenticatedPage }) => {
    // Open add rule modal
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()

    const actionSelect = authenticatedPage.getByTestId('autopilot-rule-action-type')
    const options = await actionSelect.locator('option').allTextContents()

    // Verify all action types are present
    expect(options.some(opt => opt.includes('Exit All'))).toBeTruthy()
    expect(options.some(opt => opt.includes('Add Hedge'))).toBeTruthy()
    expect(options.some(opt => opt.includes('Close Leg'))).toBeTruthy()
    expect(options.some(opt => opt.includes('Roll Strike'))).toBeTruthy()
    expect(options.some(opt => opt.includes('Roll Expiry'))).toBeTruthy()
    expect(options.some(opt => opt.includes('Scale Down'))).toBeTruthy()
    expect(options.some(opt => opt.includes('Scale Up'))).toBeTruthy()
  })

  test('should cancel rule creation', async ({ authenticatedPage }) => {
    // Open add rule modal
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()

    // Fill some data
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Test Rule')

    // Click cancel
    await authenticatedPage.getByTestId('autopilot-rule-cancel').click()

    // Verify modal closed
    await expect(authenticatedPage.getByTestId('autopilot-rule-modal')).not.toBeVisible()

    // Verify no rule was created (empty state still visible)
    await expect(authenticatedPage.getByText('No adjustment rules configured')).toBeVisible()
  })

  test('should edit an existing rule', async ({ authenticatedPage }) => {
    // First, create a rule
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Original Rule')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Wait for rule card to appear
    const ruleCard = authenticatedPage.getByTestId('autopilot-rule-card-0')
    await expect(ruleCard).toBeVisible()

    // Click edit button
    await authenticatedPage.getByTestId('autopilot-edit-rule-0').click()

    // Verify modal opened with existing data
    const modal = authenticatedPage.getByTestId('autopilot-rule-modal')
    await expect(modal).toBeVisible()
    await expect(modal.getByText('Edit Rule')).toBeVisible()

    // Verify name field has existing value
    const nameInput = authenticatedPage.getByTestId('autopilot-rule-name')
    const nameValue = await nameInput.inputValue()
    expect(nameValue).toBe('Original Rule')

    // Change the name
    await nameInput.fill('Updated Rule')

    // Save changes
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Verify modal closed
    await expect(modal).not.toBeVisible()

    // Verify rule card shows updated name
    await expect(ruleCard.getByText('Updated Rule')).toBeVisible()
  })

  test('should delete a rule with confirmation', async ({ authenticatedPage }) => {
    // Create a rule first
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Rule to Delete')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Verify rule exists
    await expect(authenticatedPage.getByTestId('autopilot-rule-card-0')).toBeVisible()

    // Set up dialog handler for confirmation
    authenticatedPage.on('dialog', async dialog => {
      expect(dialog.message()).toContain('Delete "Rule to Delete"?')
      await dialog.accept()
    })

    // Click delete button
    await authenticatedPage.getByTestId('autopilot-delete-rule-0').click()

    // Verify rule was deleted (empty state returns)
    await expect(authenticatedPage.getByText('No adjustment rules configured')).toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-rule-card-0')).not.toBeVisible()
  })

  test('should create multiple rules', async ({ authenticatedPage }) => {
    // Create first rule
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Rule 1')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Create second rule
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Rule 2')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Create third rule
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Rule 3')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Verify all three rule cards exist
    await expect(authenticatedPage.getByTestId('autopilot-rule-card-0')).toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-rule-card-1')).toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-rule-card-2')).toBeVisible()

    // Verify rule numbers
    const card0 = authenticatedPage.getByTestId('autopilot-rule-card-0')
    const card1 = authenticatedPage.getByTestId('autopilot-rule-card-1')
    const card2 = authenticatedPage.getByTestId('autopilot-rule-card-2')

    await expect(card0.getByText('Rule 1')).toBeVisible()
    await expect(card1.getByText('Rule 2')).toBeVisible()
    await expect(card2.getByText('Rule 3')).toBeVisible()
  })

  test('should move rule up in order', async ({ authenticatedPage }) => {
    // Create two rules
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('First Rule')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Second Rule')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Verify initial order
    let card0 = authenticatedPage.getByTestId('autopilot-rule-card-0')
    let card1 = authenticatedPage.getByTestId('autopilot-rule-card-1')
    await expect(card0.getByText('First Rule')).toBeVisible()
    await expect(card1.getByText('Second Rule')).toBeVisible()

    // Move second rule up
    await authenticatedPage.getByTestId('autopilot-move-rule-up-1').click()

    // Verify order changed
    card0 = authenticatedPage.getByTestId('autopilot-rule-card-0')
    card1 = authenticatedPage.getByTestId('autopilot-rule-card-1')
    await expect(card0.getByText('Second Rule')).toBeVisible()
    await expect(card1.getByText('First Rule')).toBeVisible()
  })

  test('should move rule down in order', async ({ authenticatedPage }) => {
    // Create two rules
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('First Rule')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Second Rule')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Move first rule down
    await authenticatedPage.getByTestId('autopilot-move-rule-down-0').click()

    // Verify order changed
    const card0 = authenticatedPage.getByTestId('autopilot-rule-card-0')
    const card1 = authenticatedPage.getByTestId('autopilot-rule-card-1')
    await expect(card0.getByText('Second Rule')).toBeVisible()
    await expect(card1.getByText('First Rule')).toBeVisible()
  })

  test('should display rule with WHEN->THEN flow', async ({ authenticatedPage }) => {
    // Create a rule with specific trigger and action
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Test Flow')

    const triggerSelect = authenticatedPage.getByTestId('autopilot-rule-trigger-type')
    await triggerSelect.selectOption({ value: 'pnl_based' })

    const actionSelect = authenticatedPage.getByTestId('autopilot-rule-action-type')
    await actionSelect.selectOption({ value: 'exit_all' })

    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Verify rule card shows WHEN and THEN
    const ruleCard = authenticatedPage.getByTestId('autopilot-rule-card-0')
    await expect(ruleCard.getByText('WHEN')).toBeVisible()
    await expect(ruleCard.getByText('THEN')).toBeVisible()

    // Verify icons are present (checking for emoji/icon content)
    await expect(ruleCard.getByText('💰')).toBeVisible() // P&L icon
    await expect(ruleCard.getByText('🚪')).toBeVisible() // Exit All icon
  })

  test('should display rule metadata', async ({ authenticatedPage }) => {
    // Create a rule with specific cooldown and max executions
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Meta Test')
    await authenticatedPage.getByTestId('autopilot-rule-cooldown').fill('300')
    await authenticatedPage.getByTestId('autopilot-rule-max-executions').fill('3')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Verify metadata is displayed
    const ruleCard = authenticatedPage.getByTestId('autopilot-rule-card-0')
    await expect(ruleCard.getByText(/Cooldown: 5min/)).toBeVisible() // 300 seconds = 5 min
    await expect(ruleCard.getByText(/Max: 3 times/)).toBeVisible()
  })

  test('should not show move up button for first rule', async ({ authenticatedPage }) => {
    // Create one rule
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Only Rule')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Verify move up button is not visible
    await expect(authenticatedPage.getByTestId('autopilot-move-rule-up-0')).not.toBeVisible()
  })

  test('should not show move down button for last rule', async ({ authenticatedPage }) => {
    // Create one rule
    await authenticatedPage.getByTestId('autopilot-add-rule-btn').click()
    await authenticatedPage.getByTestId('autopilot-rule-name').fill('Only Rule')
    await authenticatedPage.getByTestId('autopilot-rule-save').click()

    // Verify move down button is not visible
    await expect(authenticatedPage.getByTestId('autopilot-move-rule-down-0')).not.toBeVisible()
  })
})
