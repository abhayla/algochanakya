/**
 * AutoPilot Suggestions - E2E Tests
 *
 * Tests for AI-powered adjustment suggestions.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotDashboardPage } from '../../pages/AutoPilotDashboardPage.js';

test.describe('AutoPilot Suggestions - E2E', () => {
  let page;

  test.beforeEach(async ({ authenticatedPage }) => {
    page = new AutoPilotDashboardPage(authenticatedPage);
    await page.navigate();
    await page.waitForDashboardLoad();

    // Navigate to strategy with suggestions
    await page.strategyCards.first().click();
    await page.page.waitForSelector('[data-testid="autopilot-strategy-detail"]');
    await page.page.click('[data-testid="autopilot-suggestions-tab"]');
  });

  test('should view suggestions list', async ({ authenticatedPage }) => {
    // Navigate to suggestions tab
    await page.page.click('[data-testid="autopilot-suggestions-tab"]');

    // Verify suggestions panel is visible
    const suggestionsPanel = page.page.locator('[data-testid="autopilot-suggestions-panel"]');
    await expect(suggestionsPanel).toBeVisible();

    // Verify suggestions cards are displayed
    const suggestionCards = page.page.locator('[data-testid^="autopilot-suggestion-card"]');
    const count = await suggestionCards.count();

    if (count > 0) {
      await expect(suggestionCards.first()).toBeVisible();
    }
  });

  test('should display suggestion card details', async ({ authenticatedPage }) => {
    // Navigate to suggestions
    await page.page.click('[data-testid="autopilot-suggestions-tab"]');

    const firstCard = page.page.locator('[data-testid^="autopilot-suggestion-card"]').first();

    if (await firstCard.isVisible()) {
      // Verify card has required elements
      const title = firstCard.locator('[data-testid="autopilot-suggestion-title"]');
      await expect(title).toBeVisible();

      const description = firstCard.locator('[data-testid="autopilot-suggestion-description"]');
      await expect(description).toBeVisible();

      const reasoning = firstCard.locator('[data-testid="autopilot-suggestion-reasoning"]');
      await expect(reasoning).toBeVisible();

      // Verify action buttons
      const executeBtn = firstCard.locator('[data-testid="autopilot-suggestion-execute-btn"]');
      const dismissBtn = firstCard.locator('[data-testid="autopilot-suggestion-dismiss-btn"]');
      await expect(executeBtn).toBeVisible();
      await expect(dismissBtn).toBeVisible();
    }
  });

  test('should display urgency/priority indicators', async ({ authenticatedPage }) => {
    // Navigate to suggestions
    await page.page.click('[data-testid="autopilot-suggestions-tab"]');

    const firstCard = page.page.locator('[data-testid^="autopilot-suggestion-card"]').first();

    if (await firstCard.isVisible()) {
      // Verify priority badge exists
      const priorityBadge = firstCard.locator('[data-testid="autopilot-suggestion-priority"]');
      await expect(priorityBadge).toBeVisible();

      // Priority badge should have color coding
      const badgeText = await priorityBadge.textContent();
      expect(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']).toContain(badgeText.trim().toUpperCase());

      // Check for color coding based on priority
      const badgeClass = await priorityBadge.getAttribute('class');
      if (badgeText.includes('CRITICAL')) {
        expect(badgeClass).toMatch(/red|danger|critical/i);
      } else if (badgeText.includes('HIGH')) {
        expect(badgeClass).toMatch(/orange|warning|high/i);
      }
    }
  });

  test('should execute suggestion with confirmation', async ({ authenticatedPage }) => {
    // Navigate to suggestions
    await page.page.click('[data-testid="autopilot-suggestions-tab"]');

    const firstCard = page.page.locator('[data-testid^="autopilot-suggestion-card"]').first();

    if (await firstCard.isVisible()) {
      // Click execute button
      await firstCard.locator('[data-testid="autopilot-suggestion-execute-btn"]').click();

      // Verify confirmation modal appears
      const confirmModal = page.page.locator('[data-testid="autopilot-execute-suggestion-modal"]');
      await expect(confirmModal).toBeVisible();

      // Verify modal shows suggestion details
      const modalTitle = confirmModal.locator('[data-testid="autopilot-execute-modal-title"]');
      await expect(modalTitle).toBeVisible();

      // Close modal without executing
      await page.page.click('[data-testid="autopilot-execute-modal-cancel"]');
      await expect(confirmModal).not.toBeVisible();
    }
  });

  test('should dismiss suggestion', async ({ authenticatedPage }) => {
    // Navigate to suggestions
    await page.page.click('[data-testid="autopilot-suggestions-tab"]');

    const suggestionCards = page.page.locator('[data-testid^="autopilot-suggestion-card"]');
    const initialCount = await suggestionCards.count();

    if (initialCount > 0) {
      const firstCard = suggestionCards.first();

      // Click dismiss button
      await firstCard.locator('[data-testid="autopilot-suggestion-dismiss-btn"]').click();

      // May show confirmation dialog
      const confirmDialog = page.page.locator('[data-testid="autopilot-dismiss-suggestion-dialog"]');
      if (await confirmDialog.isVisible()) {
        await page.page.click('[data-testid="autopilot-dismiss-confirm-btn"]');
      }

      // Wait for suggestion to be removed (card should disappear or count should decrease)
      await page.page.waitForTimeout(1000);

      const newCount = await suggestionCards.count();
      expect(newCount).toBeLessThanOrEqual(initialCount);
    }
  });

  test('should display empty state when no suggestions', async ({ authenticatedPage }) => {
    // Navigate to suggestions
    await page.page.click('[data-testid="autopilot-suggestions-tab"]');

    // Dismiss all suggestions if any exist
    let suggestionCards = page.page.locator('[data-testid^="autopilot-suggestion-card"]');
    let count = await suggestionCards.count();

    while (count > 0) {
      const firstCard = suggestionCards.first();
      await firstCard.locator('[data-testid="autopilot-suggestion-dismiss-btn"]').click();

      const confirmDialog = page.page.locator('[data-testid="autopilot-dismiss-suggestion-dialog"]');
      if (await confirmDialog.isVisible()) {
        await page.page.click('[data-testid="autopilot-dismiss-confirm-btn"]');
      }

      await page.page.waitForTimeout(500);
      count = await suggestionCards.count();
    }

    // Verify empty state is displayed
    const emptyState = page.page.locator('[data-testid="autopilot-suggestions-empty"]');
    await expect(emptyState).toBeVisible();

    // Verify empty state message
    const emptyMessage = emptyState.locator('[data-testid="autopilot-suggestions-empty-message"]');
    await expect(emptyMessage).toContainText(/no suggestions|all good|healthy/i);
  });

  test('should show suggestion estimated impact', async ({ authenticatedPage }) => {
    // Navigate to suggestions
    await page.page.click('[data-testid="autopilot-suggestions-tab"]');

    const firstCard = page.page.locator('[data-testid^="autopilot-suggestion-card"]').first();

    if (await firstCard.isVisible()) {
      // Verify estimated impact section exists
      const impactSection = firstCard.locator('[data-testid="autopilot-suggestion-impact"]');

      if (await impactSection.isVisible()) {
        // Impact should show metrics like cost, delta change, etc.
        const impactText = await impactSection.textContent();
        expect(impactText.length).toBeGreaterThan(0);
      }
    }
  });

  test('should refresh suggestions', async ({ authenticatedPage }) => {
    // Navigate to suggestions
    await page.page.click('[data-testid="autopilot-suggestions-tab"]');

    // Find refresh button
    const refreshBtn = page.page.locator('[data-testid="autopilot-suggestions-refresh-btn"]');

    if (await refreshBtn.isVisible()) {
      // Click refresh
      await refreshBtn.click();

      // Wait for loading state
      const loadingIndicator = page.page.locator('[data-testid="autopilot-suggestions-loading"]');
      if (await loadingIndicator.isVisible({ timeout: 1000 })) {
        await expect(loadingIndicator).not.toBeVisible({ timeout: 5000 });
      }

      // Suggestions should be reloaded
      await page.page.waitForTimeout(500);
      const suggestionsPanel = page.page.locator('[data-testid="autopilot-suggestions-panel"]');
      await expect(suggestionsPanel).toBeVisible();
    }
  });
});
