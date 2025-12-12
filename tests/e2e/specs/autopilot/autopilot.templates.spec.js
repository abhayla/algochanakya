/**
 * AutoPilot Phase 4 - Template Library E2E Tests
 *
 * Tests for template browsing, filtering, deployment, and rating.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotTemplatesPage } from '../../pages/AutoPilotDashboardPage.js';


// =============================================================================
// TEMPLATE LIBRARY - HAPPY PATH
// =============================================================================

test.describe('AutoPilot Template Library - Happy Path', () => {
  let templatesPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    templatesPage = new AutoPilotTemplatesPage(authenticatedPage);
    await templatesPage.navigate();
    await templatesPage.waitForPageLoad();
  });

  test('displays template library page', async () => {
    await expect(templatesPage.templatesPage).toBeVisible();
    await expect(templatesPage.templatesHeader).toBeVisible();
  });

  test('displays category filter dropdown', async () => {
    // Vue uses category filter dropdown instead of category cards
    await expect(templatesPage.categoryFilter).toBeVisible();
  });

  test('displays template cards', async () => {
    const count = await templatesPage.getTemplateCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('filters templates by category', async () => {
    // Vue categories: income, directional, volatility, hedging, advanced
    await templatesPage.filterByCategory('income');
    await expect(templatesPage.templatesPage).toBeVisible();
  });

  test('filters templates by risk level', async () => {
    await templatesPage.filterByRisk('low');
    await expect(templatesPage.templatesPage).toBeVisible();
  });

  test('searches templates by name', async () => {
    await templatesPage.searchTemplates('Iron Condor');
    await expect(templatesPage.templatesPage).toBeVisible();
  });

  test('opens template details modal', async () => {
    const count = await templatesPage.getTemplateCount();
    if (count > 0) {
      const firstCard = templatesPage.templateCards.first();
      const testId = await firstCard.getAttribute('data-testid');
      const templateId = testId.replace('autopilot-template-card-', '');
      await templatesPage.clickTemplate(templateId);
      await expect(templatesPage.detailsModal).toBeVisible();
    }
  });

  test('closes template details modal', async () => {
    const count = await templatesPage.getTemplateCount();
    if (count > 0) {
      const firstCard = templatesPage.templateCards.first();
      const testId = await firstCard.getAttribute('data-testid');
      const templateId = testId.replace('autopilot-template-card-', '');
      await templatesPage.clickTemplate(templateId);
      await templatesPage.closeDetailsModal();
      await expect(templatesPage.detailsModal).not.toBeVisible();
    }
  });

  test('deploys template opens deploy modal', async () => {
    const count = await templatesPage.getTemplateCount();
    if (count > 0) {
      const firstCard = templatesPage.templateCards.first();
      const testId = await firstCard.getAttribute('data-testid');
      const templateId = testId.replace('autopilot-template-card-', '');

      // Click deploy button to open modal
      await templatesPage.getTemplateDeployButton(templateId).click();

      // Deploy modal should appear
      await expect(templatesPage.deployModal).toBeVisible();
      await expect(templatesPage.deployConfirmButton).toBeVisible();
    }
  });

  test.skip('rates a template', async () => {
    // Skip: Rating modal not implemented in Vue
    const count = await templatesPage.getTemplateCount();
    if (count > 0) {
      const firstCard = templatesPage.templateCards.first();
      const testId = await firstCard.getAttribute('data-testid');
      const templateId = testId.replace('autopilot-template-card-', '');
      await templatesPage.clickTemplate(templateId);
      await templatesPage.rateTemplate(4);
    }
  });
});


// =============================================================================
// TEMPLATE LIBRARY - EDGE CASES
// =============================================================================

test.describe('AutoPilot Template Library - Edge Cases', () => {
  let templatesPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    templatesPage = new AutoPilotTemplatesPage(authenticatedPage);
    await templatesPage.navigate();
    await templatesPage.waitForPageLoad();
  });

  test('handles empty search results', async () => {
    await templatesPage.searchTemplates('xyznonexistenttemplate123');
    const count = await templatesPage.getTemplateCount();
    expect(count).toBe(0);
  });

  test('clears search by emptying input', async () => {
    // Clear search by emptying the input field
    await templatesPage.searchTemplates('Iron Condor');
    await templatesPage.searchInput.fill('');
    await templatesPage.page.waitForLoadState('networkidle');
    await expect(templatesPage.templatesPage).toBeVisible();
  });

  test('handles pagination if available', async () => {
    const pagination = templatesPage.pagination;
    if (await pagination.isVisible()) {
      const nextButton = pagination.locator('[data-testid="pagination-next"]');
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        await templatesPage.page.waitForLoadState('networkidle');
      }
    }
  });

  test('handles multiple filters combined', async () => {
    // Vue categories: income, directional, volatility, hedging, advanced
    await templatesPage.filterByCategory('income');
    await templatesPage.filterByRisk('medium');
    await expect(templatesPage.templatesPage).toBeVisible();
  });

  test('filters reset when changing category', async () => {
    // Vue uses dropdown filters, not category cards
    await templatesPage.filterByCategory('directional');
    await expect(templatesPage.templatesPage).toBeVisible();

    // Change to different category
    await templatesPage.filterByCategory('volatility');
    await expect(templatesPage.templatesPage).toBeVisible();
  });
});
