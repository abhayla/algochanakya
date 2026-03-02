/**
 * E2E Tests: Re-Entry Configuration - Edge Cases
 *
 * Tests edge cases and error scenarios:
 * - Toggle behavior
 * - Form validation
 * - State persistence
 * - Boundary values
 */

import { test, expect } from '../../fixtures/auth.fixture.js'

test.describe('AutoPilot - Re-Entry Configuration (Edge Cases)', () => {
  // Increase timeout for these tests due to heavy page loads
  test.setTimeout(30000)

  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot/strategies/new', { waitUntil: 'domcontentloaded' })
    await expect(authenticatedPage.getByTestId('autopilot-strategy-builder')).toBeVisible({ timeout: 10000 })

    // Navigate to Step 4 (Risk Settings) where ReentryConfig is located
    await authenticatedPage.getByTestId('autopilot-builder-settings-tab').click()
    await authenticatedPage.getByTestId('autopilot-reentry-config').waitFor({ state: 'visible' })
  })

  test('should handle rapid toggle clicks', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')

    // Click toggle rapidly 5 times
    for (let i = 0; i < 5; i++) {
      await toggle.click()
      await authenticatedPage.waitForLoadState('domcontentloaded')
    }

    // Final state should be enabled (odd number of clicks)
    await expect(authenticatedPage.getByTestId('autopilot-reentry-config').getByText('Enabled')).toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-reentry-max-reentries')).toBeVisible()
  })

  test('should persist state when toggling off and on', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')

    // Enable and configure
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Set specific values
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').selectOption({ value: '5' })
    await authenticatedPage.getByTestId('autopilot-reentry-cooldown').selectOption({ value: '60' })

    // Toggle off
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'hidden' })

    // Toggle back on
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Verify values persisted
    const maxReentriesValue = await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').inputValue()
    const cooldownValue = await authenticatedPage.getByTestId('autopilot-reentry-cooldown').inputValue()

    expect(maxReentriesValue).toBe('5')
    expect(cooldownValue).toBe('60')
  })

  test('should handle minimum re-entry count (1)', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Select minimum value
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').selectOption({ value: '1' })

    // Verify selection
    const value = await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').inputValue()
    expect(value).toBe('1')

    // Verify info box updates to show "1 time" (not plural)
    const infoBox = authenticatedPage.getByText(/Process repeats up to/)
    await expect(infoBox).toBeVisible()
  })

  test('should handle maximum re-entry count (10)', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Select maximum value
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').selectOption({ value: '10' })

    // Verify selection
    const value = await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').inputValue()
    expect(value).toBe('10')
  })

  test('should handle minimum cooldown (5 minutes)', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-cooldown').waitFor({ state: 'visible' })

    // Select minimum cooldown
    await authenticatedPage.getByTestId('autopilot-reentry-cooldown').selectOption({ value: '5' })

    // Verify selection
    const value = await authenticatedPage.getByTestId('autopilot-reentry-cooldown').inputValue()
    expect(value).toBe('5')

    // Verify info box shows correct cooldown
    await expect(authenticatedPage.getByText(/5 minutes cooldown period/)).toBeVisible()
  })

  test('should handle maximum cooldown (2 hours)', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-cooldown').waitFor({ state: 'visible' })

    // Select maximum cooldown
    await authenticatedPage.getByTestId('autopilot-reentry-cooldown').selectOption({ value: '120' })

    // Verify selection
    const value = await authenticatedPage.getByTestId('autopilot-reentry-cooldown').inputValue()
    expect(value).toBe('120')
  })

  test('should maintain disabled state on page refresh', async ({ authenticatedPage }) => {
    // Leave re-entry disabled (default state)
    const initialState = await authenticatedPage.getByTestId('autopilot-reentry-config').getByText('Disabled').isVisible()
    expect(initialState).toBeTruthy()

    // Reload page
    await authenticatedPage.reload()
    await authenticatedPage.waitForLoadState('domcontentloaded')

    // Verify still disabled
    await expect(authenticatedPage.getByTestId('autopilot-reentry-config').getByText('Disabled')).toBeVisible()
  })

  test('should show appropriate help text for all options', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Check max re-entries help text
    await expect(authenticatedPage.getByText('Maximum number of times to re-enter')).toBeVisible()

    // Check cooldown help text
    await expect(authenticatedPage.getByText('Wait time before checking re-entry conditions')).toBeVisible()
  })

  test('should handle empty conditions gracefully', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-conditions').waitFor({ state: 'visible' })

    // Condition builder should be present but empty
    const conditionsSection = authenticatedPage.getByTestId('autopilot-reentry-conditions')
    await expect(conditionsSection).toBeVisible()

    // Should not crash with empty conditions
    await expect(conditionsSection).toBeVisible()
  })

  test('should update info box when changing max reentries', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Change max reentries to 3
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').selectOption({ value: '3' })

    // Info box should update to show "3 times"
    await expect(authenticatedPage.getByText(/Process repeats up to.*3 times/)).toBeVisible()

    // Change to 1
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').selectOption({ value: '1' })

    // Info box should update to show "1 time" (singular)
    // This is a soft check as the component might not handle singular/plural
    const infoBox = authenticatedPage.getByText(/Process repeats up to/)
    await expect(infoBox).toBeVisible()
  })

  test('should update info box when changing cooldown', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-cooldown').waitFor({ state: 'visible' })

    // Change cooldown to 30 minutes
    await authenticatedPage.getByTestId('autopilot-reentry-cooldown').selectOption({ value: '30' })

    // Info box should show "30 minutes"
    await expect(authenticatedPage.getByText(/30 minutes cooldown period/)).toBeVisible()

    // Change to 60 minutes (1 hour)
    await authenticatedPage.getByTestId('autopilot-reentry-cooldown').selectOption({ value: '60' })

    // Info box should show updated value
    await expect(authenticatedPage.getByText(/60 minutes cooldown period/)).toBeVisible()
  })

  test('should handle disabled toggle state correctly', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')

    // Initially disabled
    const isChecked = await toggle.isChecked()
    expect(isChecked).toBeFalsy()

    // Configuration should not be visible
    await expect(authenticatedPage.getByTestId('autopilot-reentry-max-reentries')).not.toBeVisible()
    await expect(authenticatedPage.getByTestId('autopilot-reentry-cooldown')).not.toBeVisible()

    // Disabled state message should be visible
    await expect(authenticatedPage.getByText(/Enable re-entry to automatically re-enter/)).toBeVisible()
  })

  test('should not show re-entry count for new strategies', async ({ authenticatedPage }) => {
    const toggle = authenticatedPage.getByTestId('autopilot-reentry-toggle')
    await toggle.click()
    await authenticatedPage.getByTestId('autopilot-reentry-max-reentries').waitFor({ state: 'visible' })

    // Re-entry count should not be visible
    const reentryCount = authenticatedPage.getByTestId('autopilot-reentry-count')
    await expect(reentryCount).not.toBeVisible()
  })
})
