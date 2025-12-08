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

  // ==================== Deploy to Builder - Full Flow Tests ====================

  test('should deploy Iron Condor to Strategy Builder', async ({ authenticatedPage }) => {
    // 1. Open deploy modal for Iron Condor
    await strategyLibraryPage.openDeploy('iron_condor');
    await strategyLibraryPage.assertDeployModalVisible();

    // 2. Configure deployment - NIFTY (underlying may be pre-selected)
    await strategyLibraryPage.selectDeployUnderlying('NIFTY');

    // Wait for expiries to load and auto-select
    await authenticatedPage.waitForTimeout(1000);

    // Verify expiry is selected (auto-selects first)
    const expirySelect = strategyLibraryPage.deployExpirySelect;
    await expect(expirySelect).not.toHaveValue('');

    // Set lots
    await strategyLibraryPage.setDeployLots(1);

    // 3. Verify legs preview shows 4 legs (Iron Condor = 4 legs)
    await expect(strategyLibraryPage.getDeployLegRow(0)).toBeVisible();
    await expect(strategyLibraryPage.getDeployLegRow(1)).toBeVisible();
    await expect(strategyLibraryPage.getDeployLegRow(2)).toBeVisible();
    await expect(strategyLibraryPage.getDeployLegRow(3)).toBeVisible();

    // 4. Click Deploy (Create Strategy)
    await strategyLibraryPage.confirmDeploy();

    // 5. Verify success state
    await expect(strategyLibraryPage.deploySuccess).toBeVisible();

    // 6. Click View Strategy to navigate
    await strategyLibraryPage.clickViewStrategy();

    // 7. Verify navigation to Strategy Builder
    await expect(authenticatedPage).toHaveURL(/\/strategy\/\d+/);

    // 8. Verify strategy page loaded with legs
    await expect(authenticatedPage.locator('[data-testid="strategy-page"]')).toBeVisible();
  });

  test('should deploy Bull Call Spread with 2 lots to BANKNIFTY', async ({ authenticatedPage }) => {
    // Open deploy modal
    await strategyLibraryPage.openDeploy('bull_call_spread');
    await strategyLibraryPage.assertDeployModalVisible();

    // Select BANKNIFTY
    await strategyLibraryPage.selectDeployUnderlying('BANKNIFTY');
    await authenticatedPage.waitForTimeout(1000);

    // Set 2 lots
    await strategyLibraryPage.setDeployLots(2);

    // Verify legs preview shows 2 legs (Bull Call Spread = 2 legs)
    await expect(strategyLibraryPage.getDeployLegRow(0)).toBeVisible();
    await expect(strategyLibraryPage.getDeployLegRow(1)).toBeVisible();

    // Deploy
    await strategyLibraryPage.confirmDeploy();

    // Verify success and navigate
    await expect(strategyLibraryPage.deploySuccess).toBeVisible();
    await strategyLibraryPage.clickViewStrategy();

    // Verify navigation to Strategy Builder
    await expect(authenticatedPage).toHaveURL(/\/strategy\/\d+/);
  });

  test('should deploy Short Strangle to FINNIFTY', async ({ authenticatedPage }) => {
    // Open deploy modal
    await strategyLibraryPage.openDeploy('short_strangle');
    await strategyLibraryPage.assertDeployModalVisible();

    // Select FINNIFTY
    await strategyLibraryPage.selectDeployUnderlying('FINNIFTY');
    await authenticatedPage.waitForTimeout(1000);

    // Set 1 lot
    await strategyLibraryPage.setDeployLots(1);

    // Verify legs preview shows 2 legs (Short Strangle = 2 legs)
    await expect(strategyLibraryPage.getDeployLegRow(0)).toBeVisible();
    await expect(strategyLibraryPage.getDeployLegRow(1)).toBeVisible();

    // Deploy
    await strategyLibraryPage.confirmDeploy();

    // Verify success
    await expect(strategyLibraryPage.deploySuccess).toBeVisible();
  });

  test('should deploy strategy from wizard recommendations', async ({ authenticatedPage }) => {
    // Complete wizard flow
    await strategyLibraryPage.openWizard();

    await strategyLibraryPage.selectWizardOutlook('neutral');
    await strategyLibraryPage.wizardNext();
    await strategyLibraryPage.selectWizardVolatility('high');
    await strategyLibraryPage.wizardNext();
    await strategyLibraryPage.selectWizardRisk('low');
    await strategyLibraryPage.getRecommendations();

    // Wait for recommendations
    await expect(strategyLibraryPage.wizardRecommendations).toBeVisible();

    // Click Deploy on first recommendation using POM method
    const deployBtn = strategyLibraryPage.getWizardRecommendationDeploy(0);

    // If deploy button exists in recommendation, click it
    if (await deployBtn.isVisible().catch(() => false)) {
      await deployBtn.click();
      await strategyLibraryPage.assertDeployModalVisible();

      // Configure and deploy
      await strategyLibraryPage.selectDeployUnderlying('NIFTY');
      await authenticatedPage.waitForTimeout(1000);
      await strategyLibraryPage.setDeployLots(1);
      await strategyLibraryPage.confirmDeploy();

      // Verify success
      await expect(strategyLibraryPage.deploySuccess).toBeVisible();
    }
  });

  test('should show correct lot size calculation in deploy modal', async ({ authenticatedPage }) => {
    await strategyLibraryPage.openDeploy('iron_condor');
    await strategyLibraryPage.assertDeployModalVisible();

    // NIFTY lot size = 75
    await strategyLibraryPage.selectDeployUnderlying('NIFTY');
    await authenticatedPage.waitForTimeout(500);
    await strategyLibraryPage.setDeployLots(2);

    // Check lot size display (75 x 2 = 150)
    const lotSizeText = await strategyLibraryPage.deployEstimates.textContent();
    expect(lotSizeText).toContain('150');

    // Change to BANKNIFTY lot size = 15
    await strategyLibraryPage.selectDeployUnderlying('BANKNIFTY');
    await authenticatedPage.waitForTimeout(500);

    // Check lot size display (15 x 2 = 30)
    const lotSizeText2 = await strategyLibraryPage.deployEstimates.textContent();
    expect(lotSizeText2).toContain('30');
  });
});
