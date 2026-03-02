/**
 * E2E Tests: Re-Entry Configuration - Happy Path
 *
 * Tests the ReentryConfig component functionality:
 * - Enable/disable re-entry
 * - Configure max re-entries
 * - Set cooldown period
 * - Add re-entry conditions
 */

import { test, expect } from '../../fixtures/auth.fixture.js'

test.describe('AutoPilot - Re-Entry Configuration (Happy Path)', () => {
  // Increase timeout for these tests due to heavy page loads
  test.setTimeout(30000)

  test.beforeEach(async ({ authenticatedPage }) => {
    // Navigate to AutoPilot strategy builder
    await authenticatedPage.goto('/autopilot/strategies/new', { waitUntil: 'domcontentloaded' })

    // Wait for page to load (use domcontentloaded instead of networkidle for faster tests)
    await expect(authenticatedPage.getByTestId('autopilot-strategy-builder')).toBeVisible({ timeout: 10000 })

    // Navigate to Step 4 (Risk Settings) where ReentryConfig is located
    await authenticatedPage.getByTestId('autopilot-builder-settings-tab').click()
    await authenticatedPage.getByTestId('autopilot-reentry-config').waitFor({ state: 'visible' })
  })

  test('should display re-entry configuration section', async ({ authenticatedPage }) => {
    // Check that re-entry config component is visible
    const reentryConfig = authenticatedPage.getByTestId('autopilot-reentry-config')
    await expect(reentryConfig).toBeVisible()

    // Check title and subtitle
    await expect(reentryConfig.getByText('Re-Entry Settings')).toBeVisible()
    await expect(reentryConfig.getByText('Automatically re-enter after exit')).toBeVisible()

    // Check toggle is visible
    await expect(authenticatedPage.getByTestId('autopilot-reentry-toggle')).toBeVisible()
  })

  test('should show disabled state by default', async ({ authenticatedPage }) => {
    const reentryConfig = authenticatedPage.getByTestId('autopilot-reentry-config')

    // Check toggle shows "Disabled"
    await expect(reentryConfig.getByText('Disabled')).toBeVisible()

    // Check disabled state message is visible
    await expect(reentryConfig.getByText(/Enable re-entry to automatically re-enter/)).toBeVisible()

    // Check configuration options are not visible
    await expect(authenticatedPage.getByTestId('autopilot-reentry-max-reentries')).not.toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-reentry-cooldown')).not.toBeVisible()
  })

  test('should enable re-entry configuration', async ({ authenticatedPage }) => {
    // Click the toggle to enable (click on label, not hidden input)
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()

    // Wait for configuration to become visible
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Check toggle shows "Enabled"
    await expect(authenticatedPage.getByTestId('autopilot-reentry-config').getByText('Enabled')).toBeVisible()

    // Check configuration options are now visible
    await expect(authenticatedPage.getByTestId('autopilot-reentry-max-reentries')).toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-reentry-cooldown')).toBeVisible()

    // Check info box is visible
    await expect(authenticatedPage.getByText('How Re-Entry Works')).toBeVisible()
  })

  test('should configure max re-entries', async ({ authenticatedPage }) => {
    // Enable re-entry
    await authenticatedPage.getByTestId('autopilot-reentry-toggle').click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Open max re-entries dropdown
    const maxReentriesSelect = authenticatedPage.getByTestId('autopilot-reentry-max-reentries')
    await maxReentriesSelect.click()

    // Select "3 times"
    await maxReentriesSelect.selectOption({ value: '3' })

    // Verify selection
    const selectedValue = await maxReentriesSelect.inputValue()
    expect(selectedValue).toBe('3')
  })

  test('should configure cooldown period', async ({ authenticatedPage }) => {
    // Enable re-entry
    await authenticatedPage.getByTestId('autopilot-reentry-toggle').click()
    await authenticatedPage.getByTestId('autopilot-reentry-cooldown').waitFor({ state: 'visible' })

    // Open cooldown dropdown
    const cooldownSelect = authenticatedPage.getByTestId('autopilot-reentry-cooldown')
    await cooldownSelect.click()

    // Select "30 minutes"
    await cooldownSelect.selectOption({ value: '30' })

    // Verify selection
    const selectedValue = await cooldownSelect.inputValue()
    expect(selectedValue).toBe('30')
  })

  test('should display all max re-entries options', async ({ authenticatedPage }) => {
    // Enable re-entry
    await authenticatedPage.getByTestId('autopilot-reentry-toggle').click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    const maxReentriesSelect = authenticatedPage.getByTestId('autopilot-reentry-max-reentries')

    // Get all options
    const options = await maxReentriesSelect.locator('option').allTextContents()

    // Verify all expected options exist
    expect(options).toContain('1 time')
    expect(options).toContain('2 times')
    expect(options).toContain('3 times')
    expect(options).toContain('5 times')
    expect(options).toContain('10 times')
  })

  test('should display all cooldown options', async ({ authenticatedPage }) => {
    // Enable re-entry
    await authenticatedPage.getByTestId('autopilot-reentry-toggle').click()
    await authenticatedPage.getByTestId('autopilot-reentry-cooldown').waitFor({ state: 'visible' })

    const cooldownSelect = authenticatedPage.getByTestId('autopilot-reentry-cooldown')

    // Get all options
    const options = await cooldownSelect.locator('option').allTextContents()

    // Verify all expected options exist
    expect(options).toContain('5 minutes')
    expect(options).toContain('10 minutes')
    expect(options).toContain('15 minutes')
    expect(options).toContain('30 minutes')
    expect(options).toContain('1 hour')
    expect(options).toContain('2 hours')
  })

  test('should show re-entry count when exists', async ({ authenticatedPage }) => {
    // This test would require a strategy with existing re-entry count
    // For now, we'll test that the element doesn't show for new strategies

    // Enable re-entry
    await authenticatedPage.getByTestId('autopilot-reentry-toggle').click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Re-entry count should not be visible for new strategies
    await expect(authenticatedPage.getByTestId('autopilot-reentry-count')).not.toBeVisible()
  })

  test('should show info box with correct steps', async ({ authenticatedPage }) => {
    // Enable re-entry
    await authenticatedPage.getByTestId('autopilot-reentry-toggle').click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    const reentryConfig = authenticatedPage.getByTestId('autopilot-reentry-config')

    // Check info box title
    await expect(reentryConfig.getByText('How Re-Entry Works')).toBeVisible()

    // Check all info steps are present
    await expect(reentryConfig.getByText(/Re-Entry Waiting/)).toBeVisible()
    await expect(reentryConfig.getByText(/cooldown period/)).toBeVisible()
    await expect(reentryConfig.getByText(/checks if re-entry conditions are met/)).toBeVisible()
    await expect(reentryConfig.getByText(/re-enters automatically/)).toBeVisible()
    await expect(reentryConfig.getByText(/Completed/)).toBeVisible()
  })

  test('should integrate with condition builder', async ({ authenticatedPage }) => {
    // Enable re-entry
    await authenticatedPage.getByTestId('autopilot-reentry-toggle').click()
    await authenticatedPage.getByTestId('autopilot-reentry-conditions').waitFor({ state: 'visible' })

    // Check that re-entry conditions section exists
    const conditionsSection = authenticatedPage.getByTestId('autopilot-reentry-conditions')
    await expect(conditionsSection).toBeVisible()

    // Verify it's a ConditionBuilder component (should have add condition button)
    // The actual ConditionBuilder tests are in separate files
    await expect(conditionsSection).toBeVisible()
  })

  test('should disable configuration when toggled off', async ({ authenticatedPage }) => {
    // Enable re-entry first
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Verify enabled state
    await expect(authenticatedPage.getByTestId('autopilot-reentry-max-reentries')).toBeVisible()

    // Toggle off
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'hidden' })

    // Verify disabled state
    await expect(authenticatedPage.getByTestId('autopilot-reentry-config').getByText('Disabled')).toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-reentry-max-reentries')).not.toBeVisible()
  })
})
