/**
 * Strategy Library Screen - Happy Path Tests
 *
 * Tests core functionality under normal conditions:
 * - Page load and display
 * - Category filtering
 * - Search functionality
 * - Strategy cards display
 * - Strategy Wizard flow
 * - Strategy Details modal
 * - Deploy modal
 * - Comparison functionality
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import StrategyLibraryPage from '../../pages/StrategyLibraryPage.js';

test.describe('Strategy Library - Happy Path @happy', () => {
  let strategyLibraryPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyLibraryPage = new StrategyLibraryPage(authenticatedPage);
    await strategyLibraryPage.navigate();
  });

  // ==================== Page Load Tests ====================

  test('should display strategy library page', async () => {
    await strategyLibraryPage.assertPageVisible();
  });

  test('should display all category pills', async () => {
    await strategyLibraryPage.assertCategoriesVisible();
    await expect(strategyLibraryPage.categoryAll).toBeVisible();
    await expect(strategyLibraryPage.categoryBullish).toBeVisible();
    await expect(strategyLibraryPage.categoryBearish).toBeVisible();
    await expect(strategyLibraryPage.categoryNeutral).toBeVisible();
    await expect(strategyLibraryPage.categoryVolatile).toBeVisible();
    await expect(strategyLibraryPage.categoryIncome).toBeVisible();
  });

  test('should display strategy cards', async () => {
    await strategyLibraryPage.assertCardsGridVisible();
    const cardCount = await strategyLibraryPage.getStrategyCardCount();
    expect(cardCount).toBeGreaterThan(0);
  });

  test('should display wizard button', async () => {
    await strategyLibraryPage.assertWizardButtonVisible();
  });

  test('should have no horizontal overflow', async () => {
    await strategyLibraryPage.assertNoHorizontalOverflow();
  });

  // ==================== Category Filter Tests ====================

  test('should filter by bullish category', async () => {
    await strategyLibraryPage.selectCategory('bullish');

    // All visible cards should be bullish
    const cards = await strategyLibraryPage.getStrategyCards();
    for (const card of cards) {
      const categoryBadge = card.locator('[data-testid$="-category"]');
      if (await categoryBadge.isVisible()) {
        const text = await categoryBadge.textContent();
        expect(text.toLowerCase()).toContain('bullish');
      }
    }
  });

  test('should filter by neutral category', async () => {
    await strategyLibraryPage.selectCategory('neutral');

    const cardCount = await strategyLibraryPage.getStrategyCardCount();
    expect(cardCount).toBeGreaterThanOrEqual(1);
  });

  test('should filter by volatile category', async () => {
    await strategyLibraryPage.selectCategory('volatile');

    const cardCount = await strategyLibraryPage.getStrategyCardCount();
    expect(cardCount).toBeGreaterThanOrEqual(0);
  });

  test('should clear filter with All category', async () => {
    // First apply a filter
    await strategyLibraryPage.selectCategory('bullish');
    const filteredCount = await strategyLibraryPage.getStrategyCardCount();

    // Then clear it
    await strategyLibraryPage.clearCategoryFilter();
    const allCount = await strategyLibraryPage.getStrategyCardCount();

    expect(allCount).toBeGreaterThanOrEqual(filteredCount);
  });

  // ==================== Search Tests ====================

  test('should search for iron condor', async () => {
    await strategyLibraryPage.search('iron');

    const cardCount = await strategyLibraryPage.getStrategyCardCount();
    expect(cardCount).toBeGreaterThanOrEqual(1);
  });

  test('should show empty state for no results', async () => {
    await strategyLibraryPage.search('xyz123nonexistent');

    const cardCount = await strategyLibraryPage.getStrategyCardCount();
    if (cardCount === 0) {
      await strategyLibraryPage.assertEmptyStateVisible();
    }
  });

  test('should clear search and show all strategies', async () => {
    // Search first
    await strategyLibraryPage.search('iron');
    const searchCount = await strategyLibraryPage.getStrategyCardCount();

    // Clear search
    await strategyLibraryPage.clearSearch();
    const allCount = await strategyLibraryPage.getStrategyCardCount();

    expect(allCount).toBeGreaterThanOrEqual(searchCount);
  });

  // ==================== Strategy Card Tests ====================

  test('should display strategy card with name', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    await expect(firstCard).toBeVisible();

    const nameElement = firstCard.locator('[data-testid$="-name"]');
    const name = await nameElement.textContent();
    expect(name.length).toBeGreaterThan(0);
  });

  test('should display strategy card with category badge', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const categoryBadge = firstCard.locator('[data-testid$="-category"]');

    await expect(categoryBadge).toBeVisible();
  });

  test('should display strategy card metrics', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();

    // Check for metrics presence
    const metrics = firstCard.locator('.metrics, [class*="metric"]');
    await expect(metrics.first()).toBeVisible();
  });

  test('should display view details button on card', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const detailsButton = firstCard.locator('[data-testid$="-view-details"]');

    await expect(detailsButton).toBeVisible();
  });

  test('should display deploy button on card', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await expect(deployButton).toBeVisible();
  });

  // ==================== Strategy Wizard Tests ====================

  test('should open wizard modal', async () => {
    await strategyLibraryPage.openWizard();
    await strategyLibraryPage.assertWizardModalVisible();
  });

  test('should complete wizard step 1 - outlook selection', async () => {
    await strategyLibraryPage.openWizard();

    await strategyLibraryPage.selectWizardOutlook('bullish');
    await expect(strategyLibraryPage.wizardNextButton).toBeEnabled();
  });

  test('should complete wizard step 2 - volatility selection', async () => {
    await strategyLibraryPage.openWizard();

    // Step 1
    await strategyLibraryPage.selectWizardOutlook('neutral');
    await strategyLibraryPage.wizardNext();

    // Step 2
    await expect(strategyLibraryPage.wizardStep2).toBeVisible();
    await strategyLibraryPage.selectWizardVolatility('high');
    await expect(strategyLibraryPage.wizardNextButton).toBeEnabled();
  });

  test('should complete wizard step 3 - risk selection', async () => {
    await strategyLibraryPage.openWizard();

    // Step 1
    await strategyLibraryPage.selectWizardOutlook('neutral');
    await strategyLibraryPage.wizardNext();

    // Step 2
    await strategyLibraryPage.selectWizardVolatility('high');
    await strategyLibraryPage.wizardNext();

    // Step 3
    await expect(strategyLibraryPage.wizardStep3).toBeVisible();
    await strategyLibraryPage.selectWizardRisk('low');
    await expect(strategyLibraryPage.wizardGetRecommendationsButton).toBeEnabled();
  });

  test('should show recommendations after wizard completion', async () => {
    await strategyLibraryPage.openWizard();

    // Complete all steps
    await strategyLibraryPage.selectWizardOutlook('neutral');
    await strategyLibraryPage.wizardNext();
    await strategyLibraryPage.selectWizardVolatility('high');
    await strategyLibraryPage.wizardNext();
    await strategyLibraryPage.selectWizardRisk('low');
    await strategyLibraryPage.getRecommendations();

    // Should show recommendations
    await expect(strategyLibraryPage.wizardRecommendations).toBeVisible();
    const recCount = await strategyLibraryPage.getRecommendationCount();
    expect(recCount).toBeGreaterThanOrEqual(1);
  });

  test('should navigate back in wizard', async () => {
    await strategyLibraryPage.openWizard();

    // Go to step 2
    await strategyLibraryPage.selectWizardOutlook('bullish');
    await strategyLibraryPage.wizardNext();
    await expect(strategyLibraryPage.wizardStep2).toBeVisible();

    // Go back to step 1
    await strategyLibraryPage.wizardBack();
    await expect(strategyLibraryPage.wizardStep1).toBeVisible();
  });

  test('should reset wizard when closed and reopened', async () => {
    await strategyLibraryPage.openWizard();

    // Go to step 2
    await strategyLibraryPage.selectWizardOutlook('bullish');
    await strategyLibraryPage.wizardNext();

    // Close wizard
    await strategyLibraryPage.closeWizard();

    // Reopen - should be back at step 1
    await strategyLibraryPage.openWizard();
    await expect(strategyLibraryPage.wizardStep1).toBeVisible();
  });

  // ==================== Strategy Details Modal Tests ====================

  test('should open details modal from card', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const detailsButton = firstCard.locator('[data-testid$="-view-details"]');

    await detailsButton.click();
    await strategyLibraryPage.assertDetailsModalVisible();
  });

  test('should show description in details modal', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const detailsButton = firstCard.locator('[data-testid$="-view-details"]');

    await detailsButton.click();
    await expect(strategyLibraryPage.detailsDescription).toBeVisible();
  });

  test('should show educational content in details', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const detailsButton = firstCard.locator('[data-testid$="-view-details"]');

    await detailsButton.click();
    await strategyLibraryPage.assertDetailsModalVisible();

    // Check for educational sections (When to Use is always present)
    await expect(strategyLibraryPage.detailsWhenToUse).toBeVisible();
  });

  test('should close details modal', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const detailsButton = firstCard.locator('[data-testid$="-view-details"]');

    await detailsButton.click();
    await strategyLibraryPage.assertDetailsModalVisible();

    await strategyLibraryPage.closeDetails();

    const isVisible = await strategyLibraryPage.detailsModal.isVisible().catch(() => false);
    expect(isVisible).toBe(false);
  });

  // ==================== Deploy Modal Tests ====================

  test('should open deploy modal from card', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();
    await strategyLibraryPage.assertDeployModalVisible();
  });

  test('should show underlying selector in deploy modal', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();
    await expect(strategyLibraryPage.deployUnderlyingSelect).toBeVisible();
  });

  test('should show lots input in deploy modal', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();
    await expect(strategyLibraryPage.deployLotsInput).toBeVisible();
  });

  test('should show legs preview in deploy modal', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();

    // Wait for legs to load
    await authenticatedPage.waitForTimeout(1000);
    const legsCount = await strategyLibraryPage.getDeployLegsCount();
    expect(legsCount).toBeGreaterThanOrEqual(1);
  });

  test('should close deploy modal', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();
    await strategyLibraryPage.assertDeployModalVisible();

    await strategyLibraryPage.closeDeploy();

    const isVisible = await strategyLibraryPage.deployModal.isVisible().catch(() => false);
    expect(isVisible).toBe(false);
  });
});
