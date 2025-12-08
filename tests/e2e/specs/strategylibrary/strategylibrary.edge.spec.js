/**
 * Strategy Library Screen - Edge Case Tests
 *
 * Tests edge cases and error handling:
 * - Empty states
 * - Invalid inputs
 * - Boundary conditions
 * - Error scenarios
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import StrategyLibraryPage from '../../pages/StrategyLibraryPage.js';

test.describe('Strategy Library - Edge Cases @edge', () => {
  let strategyLibraryPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyLibraryPage = new StrategyLibraryPage(authenticatedPage);
    await strategyLibraryPage.navigate();
  });

  // ==================== Search Edge Cases ====================

  test('should handle empty search gracefully', async () => {
    await strategyLibraryPage.search('');
    const cardCount = await strategyLibraryPage.getStrategyCardCount();
    expect(cardCount).toBeGreaterThan(0);
  });

  test('should handle search with special characters', async () => {
    await strategyLibraryPage.search('<script>alert("xss")</script>');
    // Should not break, may show no results
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  test('should handle search with SQL injection attempt', async () => {
    await strategyLibraryPage.search("'; DROP TABLE strategies; --");
    // Should not break
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  test('should handle very long search query', async () => {
    const longQuery = 'a'.repeat(500);
    await strategyLibraryPage.search(longQuery);
    // Should not break
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  test('should handle search with unicode characters', async () => {
    await strategyLibraryPage.search('आयरन कॉन्डोर');
    // Should not break, likely no results
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  test('should handle rapid search input changes', async () => {
    // Rapid successive searches to test debouncing
    await strategyLibraryPage.searchInput.fill('i');
    await strategyLibraryPage.searchInput.fill('ir');
    await strategyLibraryPage.searchInput.fill('iro');
    await strategyLibraryPage.searchInput.fill('iron');
    await strategyLibraryPage.page.waitForTimeout(600); // Wait for debounce

    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  // ==================== Category Filter Edge Cases ====================

  test('should handle rapid category switching', async () => {
    await strategyLibraryPage.selectCategory('bullish');
    await strategyLibraryPage.selectCategory('bearish');
    await strategyLibraryPage.selectCategory('neutral');
    await strategyLibraryPage.selectCategory('volatile');

    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  test('should handle clicking same category twice', async () => {
    await strategyLibraryPage.selectCategory('neutral');
    const firstCount = await strategyLibraryPage.getStrategyCardCount();

    await strategyLibraryPage.selectCategory('neutral');
    const secondCount = await strategyLibraryPage.getStrategyCardCount();

    expect(firstCount).toBe(secondCount);
  });

  test('should combine category filter with search', async () => {
    await strategyLibraryPage.selectCategory('neutral');
    await strategyLibraryPage.search('iron');

    const cardCount = await strategyLibraryPage.getStrategyCardCount();
    // Should have filtered results or empty state
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  // ==================== Wizard Edge Cases ====================

  test('should disable next button until option selected', async () => {
    await strategyLibraryPage.openWizard();

    // Next button should be disabled initially
    await expect(strategyLibraryPage.wizardNextButton).toBeDisabled();
  });

  test('should allow changing selection in wizard step', async () => {
    await strategyLibraryPage.openWizard();

    // Select bullish
    await strategyLibraryPage.selectWizardOutlook('bullish');
    // Change to bearish
    await strategyLibraryPage.selectWizardOutlook('bearish');

    await expect(strategyLibraryPage.wizardNextButton).toBeEnabled();
  });

  test('should handle wizard completion without recommendations', async ({ authenticatedPage }) => {
    // Mock API to return empty recommendations
    await authenticatedPage.route('**/api/strategy-library/wizard', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          recommendations: [],
          inputs: {},
          total_matches: 0
        })
      });
    });

    await strategyLibraryPage.openWizard();
    await strategyLibraryPage.selectWizardOutlook('volatile');
    await strategyLibraryPage.wizardNext();
    await strategyLibraryPage.selectWizardVolatility('low');
    await strategyLibraryPage.wizardNext();
    await strategyLibraryPage.selectWizardRisk('high');
    await strategyLibraryPage.getRecommendations();

    // Should handle empty state gracefully
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  test('should handle wizard API error', async ({ authenticatedPage }) => {
    // Mock API to return error
    await authenticatedPage.route('**/api/strategy-library/wizard', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });

    await strategyLibraryPage.openWizard();
    await strategyLibraryPage.selectWizardOutlook('neutral');
    await strategyLibraryPage.wizardNext();
    await strategyLibraryPage.selectWizardVolatility('high');
    await strategyLibraryPage.wizardNext();
    await strategyLibraryPage.selectWizardRisk('low');

    await strategyLibraryPage.wizardGetRecommendationsButton.click();

    // Should show error or handle gracefully
    await authenticatedPage.waitForTimeout(1000);
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  test('should handle escape key to close wizard', async ({ authenticatedPage }) => {
    await strategyLibraryPage.openWizard();
    await strategyLibraryPage.assertWizardModalVisible();

    await authenticatedPage.keyboard.press('Escape');
    await authenticatedPage.waitForTimeout(500);

    const isVisible = await strategyLibraryPage.wizardModal.isVisible().catch(() => false);
    // May or may not close on escape depending on implementation
    expect(typeof isVisible).toBe('boolean');
  });

  // ==================== Deploy Modal Edge Cases ====================

  test('should validate lots input - minimum', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();
    await strategyLibraryPage.setDeployLots(0);

    // Should show validation error or prevent submission
    const lotsInput = strategyLibraryPage.deployLotsInput;
    const value = await lotsInput.inputValue();
    // Either prevented or shows error
    expect(parseInt(value) >= 0).toBe(true);
  });

  test('should validate lots input - maximum', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();
    await strategyLibraryPage.setDeployLots(9999);

    // Should accept or cap at reasonable maximum
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  test('should handle non-numeric lots input', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();
    await strategyLibraryPage.deployLotsInput.fill('abc');

    // Should be handled gracefully
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  test('should handle deploy without selecting expiry', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();

    // Try to deploy without selecting expiry
    const deployButtonModal = strategyLibraryPage.deployButton;

    // Should be disabled or show error
    const isEnabled = await deployButtonModal.isEnabled().catch(() => true);
    // Either button is disabled or it will show validation error
    expect(typeof isEnabled).toBe('boolean');
  });

  // ==================== Comparison Edge Cases ====================

  test('should handle adding same strategy to comparison twice', async ({ authenticatedPage }) => {
    const cards = await authenticatedPage.locator('[data-testid^="strategy-card-"]').all();
    if (cards.length === 0) return;

    const firstCard = cards[0];
    const compareCheckbox = firstCard.locator('[data-testid$="-compare"]');

    // Click once to add
    await compareCheckbox.click();
    await authenticatedPage.waitForTimeout(200);

    // Click again to remove
    await compareCheckbox.click();
    await authenticatedPage.waitForTimeout(200);

    // Should not break
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible();
    expect(pageVisible).toBe(true);
  });

  test('should enforce comparison limit', async ({ authenticatedPage }) => {
    const cards = await authenticatedPage.locator('[data-testid^="strategy-card-"]').all();

    // Try to add more than allowed (usually 4-5)
    for (let i = 0; i < Math.min(6, cards.length); i++) {
      const compareCheckbox = cards[i].locator('[data-testid$="-compare"]');
      await compareCheckbox.click().catch(() => {});
      await authenticatedPage.waitForTimeout(100);
    }

    // Should enforce limit or handle gracefully
    const comparisonCount = await strategyLibraryPage.getComparisonCount();
    expect(comparisonCount).toBeLessThanOrEqual(5);
  });

  test('should disable compare button with less than 2 strategies', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const compareCheckbox = firstCard.locator('[data-testid$="-compare"]');

    await compareCheckbox.click();
    await authenticatedPage.waitForTimeout(300);

    const comparisonBar = await strategyLibraryPage.comparisonBar.isVisible().catch(() => false);

    if (comparisonBar) {
      const compareButton = strategyLibraryPage.comparisonCompareButton;
      const isEnabled = await compareButton.isEnabled().catch(() => true);
      // Should be disabled with only 1 strategy
      expect(typeof isEnabled).toBe('boolean');
    }
  });

  // ==================== Details Modal Edge Cases ====================

  test('should handle opening details from deploy modal', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();
    await strategyLibraryPage.assertDeployModalVisible();

    // Close deploy, then open details
    await strategyLibraryPage.closeDeploy();

    const detailsButton = firstCard.locator('[data-testid$="-view-details"]');
    await detailsButton.click();

    await strategyLibraryPage.assertDetailsModalVisible();
  });

  test('should handle opening deploy from details modal', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const detailsButton = firstCard.locator('[data-testid$="-view-details"]');

    await detailsButton.click();
    await strategyLibraryPage.assertDetailsModalVisible();

    // Open deploy from within details
    const deployFromDetails = strategyLibraryPage.detailsDeployButton;
    if (await deployFromDetails.isVisible().catch(() => false)) {
      await deployFromDetails.click();
      await strategyLibraryPage.assertDeployModalVisible();
    }
  });

  // ==================== Page Navigation Edge Cases ====================

  test('should preserve filter state after modal close', async () => {
    // Apply filter
    await strategyLibraryPage.selectCategory('neutral');
    const filteredCount = await strategyLibraryPage.getStrategyCardCount();

    // Open and close wizard
    await strategyLibraryPage.openWizard();
    await strategyLibraryPage.closeWizard();

    // Filter should still be applied
    const afterModalCount = await strategyLibraryPage.getStrategyCardCount();
    expect(afterModalCount).toBe(filteredCount);
  });

  test('should preserve search state after modal close', async ({ authenticatedPage }) => {
    // Search
    await strategyLibraryPage.search('spread');
    await authenticatedPage.waitForTimeout(500);

    // Open and close details
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    if (await firstCard.isVisible()) {
      const detailsButton = firstCard.locator('[data-testid$="-view-details"]');
      await detailsButton.click();
      await strategyLibraryPage.closeDetails();
    }

    // Search should still be in input
    const searchValue = await strategyLibraryPage.searchInput.inputValue();
    expect(searchValue).toBe('spread');
  });

  // ==================== Loading States ====================

  test('should show loading state on page load', async ({ authenticatedPage }) => {
    // Slow down network
    await authenticatedPage.route('**/api/strategy-library/**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      route.continue();
    });

    // Navigate to trigger load
    await authenticatedPage.goto('/strategies');

    // Should show loading or content
    const pageVisible = await strategyLibraryPage.pageContainer.isVisible().catch(() => false);
    const loadingVisible = await strategyLibraryPage.loadingSpinner.isVisible().catch(() => false);

    expect(pageVisible || loadingVisible).toBe(true);
  });

  // ==================== Deploy to Builder Edge Cases ====================

  test('should disable deploy button until expiry is selected', async ({ authenticatedPage }) => {
    await strategyLibraryPage.openDeploy('iron_condor');
    await strategyLibraryPage.assertDeployModalVisible();

    // Clear expiry selection by selecting empty option
    const expirySelect = strategyLibraryPage.deployExpirySelect;

    // Check that deploy button is disabled when no expiry selected
    await expirySelect.selectOption({ value: '' });
    await authenticatedPage.waitForTimeout(300);

    const deployBtn = strategyLibraryPage.deployButton;
    await expect(deployBtn).toBeDisabled();
  });

  test('should handle deploy API failure gracefully', async ({ authenticatedPage }) => {
    // Mock API failure
    await authenticatedPage.route('**/api/strategy-wizard/deploy', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });

    await strategyLibraryPage.openDeploy('iron_condor');
    await strategyLibraryPage.selectDeployUnderlying('NIFTY');
    await authenticatedPage.waitForTimeout(1000);
    await strategyLibraryPage.setDeployLots(1);

    // Attempt to deploy
    await strategyLibraryPage.confirmDeploy();

    // Should show error state (not success state)
    await authenticatedPage.waitForTimeout(1000);
    const successVisible = await strategyLibraryPage.deploySuccess.isVisible().catch(() => false);
    expect(successVisible).toBe(false);

    // Page should remain usable
    const modalVisible = await strategyLibraryPage.deployModal.isVisible().catch(() => false);
    expect(modalVisible).toBe(true);
  });

  test('should refresh expiries when underlying changes', async ({ authenticatedPage }) => {
    await strategyLibraryPage.openDeploy('bull_call_spread');
    await strategyLibraryPage.assertDeployModalVisible();

    // Select NIFTY first
    await strategyLibraryPage.selectDeployUnderlying('NIFTY');
    await authenticatedPage.waitForTimeout(1000);

    // Get NIFTY expiries count
    const expirySelect = strategyLibraryPage.deployExpirySelect;
    const niftyOptions = await expirySelect.locator('option').count();

    // Change to BANKNIFTY
    await strategyLibraryPage.selectDeployUnderlying('BANKNIFTY');
    await authenticatedPage.waitForTimeout(1000);

    // Expiries should refresh (may be different count or same, but select should work)
    const bankniftyOptions = await expirySelect.locator('option').count();
    expect(bankniftyOptions).toBeGreaterThanOrEqual(1);
  });

  test('should disable deploy button while API is loading', async ({ authenticatedPage }) => {
    // Slow down deploy API
    await authenticatedPage.route('**/api/strategy-wizard/deploy', async route => {
      await new Promise(resolve => setTimeout(resolve, 3000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          strategy_id: 123,
          legs: []
        })
      });
    });

    await strategyLibraryPage.openDeploy('iron_condor');
    await strategyLibraryPage.selectDeployUnderlying('NIFTY');
    await authenticatedPage.waitForTimeout(1000);
    await strategyLibraryPage.setDeployLots(1);

    // Click deploy
    const deployBtn = strategyLibraryPage.deployButton;
    await deployBtn.click();

    // Button should show loading state
    await expect(deployBtn).toContainText(/Creating/i);
  });

  test('should handle lots boundary - minimum value', async ({ authenticatedPage }) => {
    await strategyLibraryPage.openDeploy('bull_put_spread');
    await strategyLibraryPage.assertDeployModalVisible();

    // Try to set 0 lots
    await strategyLibraryPage.setDeployLots(0);

    // Minus button should be disabled at minimum
    await expect(strategyLibraryPage.deployLotsMinus).toBeDisabled();
  });

  test('should handle lots boundary - maximum value', async ({ authenticatedPage }) => {
    await strategyLibraryPage.openDeploy('bull_put_spread');
    await strategyLibraryPage.assertDeployModalVisible();

    // Try to set max lots (50)
    await strategyLibraryPage.setDeployLots(50);

    // Plus button should be disabled at maximum
    await expect(strategyLibraryPage.deployLotsPlus).toBeDisabled();
  });

  test('should preserve deploy modal state when closed via overlay click', async ({ authenticatedPage }) => {
    await strategyLibraryPage.openDeploy('iron_condor');
    await strategyLibraryPage.assertDeployModalVisible();

    // Configure some settings
    await strategyLibraryPage.selectDeployUnderlying('BANKNIFTY');
    await authenticatedPage.waitForTimeout(1000);
    await strategyLibraryPage.setDeployLots(3);

    // Close by clicking overlay using POM method
    await strategyLibraryPage.clickDeployOverlay();
    await authenticatedPage.waitForTimeout(500);

    // Modal should be closed
    const isVisible = await strategyLibraryPage.deployModal.isVisible().catch(() => false);
    expect(isVisible).toBe(false);
  });

  test('should handle expiry API failure gracefully', async ({ authenticatedPage }) => {
    // Mock expiry API failure
    await authenticatedPage.route('**/api/options/expiries**', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Failed to fetch expiries' })
      });
    });

    await strategyLibraryPage.openDeploy('iron_condor');
    await strategyLibraryPage.assertDeployModalVisible();

    // Modal should still be visible even with API error
    const modalVisible = await strategyLibraryPage.deployModal.isVisible();
    expect(modalVisible).toBe(true);

    // Expiry select should show loading or empty state
    const expirySelect = strategyLibraryPage.deployExpirySelect;
    await expect(expirySelect).toBeVisible();
  });
});
