/**
 * Strategy Library - Details Modal Tests
 *
 * Tests the educational content displayed in the Strategy Details modal:
 * - Description text
 * - When to Use section
 * - Pros / Cons sections
 * - Exit Rules section
 * - Common Mistakes section
 * - Deploy button visibility and navigation
 * - Modal open/close lifecycle
 * - Title accuracy
 *
 * All tests use iron_condor as the primary subject because it is the only
 * well-known strategy guaranteed to have ALL optional sections populated
 * (pros, cons, exit_rules, common_mistakes).
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { StrategyLibraryPage } from '../../pages/StrategyLibraryPage.js';

test.describe('Strategy Library - Details Modal @happy', () => {
  let strategyLibraryPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyLibraryPage = new StrategyLibraryPage(authenticatedPage);
    await strategyLibraryPage.navigate();
  });

  // ==================== Content Visibility Tests ====================

  test('should display strategy description', async () => {
    await strategyLibraryPage.openStrategyDetails('iron_condor');
    await strategyLibraryPage.assertDetailsModalVisible();

    const description = strategyLibraryPage.detailsDescription;
    await expect(description).toBeVisible();
    const text = await description.textContent();
    expect(text.trim().length).toBeGreaterThan(10);
  });

  test('should display when-to-use section', async () => {
    await strategyLibraryPage.openStrategyDetails('iron_condor');
    await strategyLibraryPage.assertDetailsModalVisible();

    const whenToUse = strategyLibraryPage.detailsWhenToUse;
    await expect(whenToUse).toBeVisible();
    const text = await whenToUse.textContent();
    expect(text.trim().length).toBeGreaterThan(0);
  });

  test('should display pros section', async () => {
    await strategyLibraryPage.openStrategyDetails('iron_condor');
    await strategyLibraryPage.assertDetailsModalVisible();

    const pros = strategyLibraryPage.detailsPros;
    await expect(pros).toBeVisible();
    // Pros are rendered as a list — verify at least one item exists
    const items = await pros.locator('li').all();
    expect(items.length).toBeGreaterThan(0);
  });

  test('should display cons section', async () => {
    await strategyLibraryPage.openStrategyDetails('iron_condor');
    await strategyLibraryPage.assertDetailsModalVisible();

    const cons = strategyLibraryPage.detailsCons;
    await expect(cons).toBeVisible();
    const items = await cons.locator('li').all();
    expect(items.length).toBeGreaterThan(0);
  });

  test('should display exit rules section', async () => {
    await strategyLibraryPage.openStrategyDetails('iron_condor');
    await strategyLibraryPage.assertDetailsModalVisible();

    const exitRules = strategyLibraryPage.detailsExitRules;
    await expect(exitRules).toBeVisible();
    const text = await exitRules.textContent();
    expect(text.trim().length).toBeGreaterThan(0);
  });

  test('should display common mistakes section', async () => {
    await strategyLibraryPage.openStrategyDetails('iron_condor');
    await strategyLibraryPage.assertDetailsModalVisible();

    const commonMistakes = strategyLibraryPage.detailsCommonMistakes;
    await expect(commonMistakes).toBeVisible();
    const text = await commonMistakes.textContent();
    expect(text.trim().length).toBeGreaterThan(0);
  });

  // ==================== Deploy Button Tests ====================

  test('should display deploy button in details modal', async () => {
    await strategyLibraryPage.openStrategyDetails('iron_condor');
    await strategyLibraryPage.assertDetailsModalVisible();

    await expect(strategyLibraryPage.detailsDeployButton).toBeVisible();
  });

  test('should navigate to deploy from details', async () => {
    await strategyLibraryPage.openStrategyDetails('iron_condor');
    await strategyLibraryPage.assertDetailsModalVisible();

    await strategyLibraryPage.openDeployFromDetails();
    await strategyLibraryPage.assertDeployModalVisible();
  });

  // ==================== Lifecycle Tests ====================

  test('should close details modal', async () => {
    await strategyLibraryPage.openStrategyDetails('iron_condor');
    await strategyLibraryPage.assertDetailsModalVisible();

    await strategyLibraryPage.closeDetails();

    await expect(strategyLibraryPage.detailsModal).toBeHidden();
    await strategyLibraryPage.assertPageVisible();
  });

  // ==================== Title Accuracy Test ====================

  test('should display correct strategy name in title', async () => {
    await strategyLibraryPage.openStrategyDetails('iron_condor');
    await strategyLibraryPage.assertDetailsModalVisible();

    const titleText = await strategyLibraryPage.detailsModalTitle.textContent();
    // The display name for iron_condor contains "Iron Condor" (case-insensitive check
    // guards against capitalisation differences between template data and render)
    expect(titleText.toLowerCase()).toContain('iron condor');
  });
});
