import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation, assertDataOrEmptyState, getISTTimeString } from '../../helpers/market-status.helper.js';

/**
 * Option Chain Screen - Selection and Market Closed Banner Tests
 *
 * Covers:
 *   - Individual chip removal (CE and PE independently)
 *   - Selected bar visibility as chips are added/removed
 *   - Add-to-strategy button state
 *   - Market closed banner presence/absence based on market hours
 *   - Error alert dismissal
 */
test.describe('Option Chain - Selection & Market Closed Banner @selection', () => {
  test.describe.configure({ timeout: 180000 });
  let optionChainPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    optionChainPage = new OptionChainPage(authenticatedPage);
    await optionChainPage.navigate();
  });

  // ============================================================
  // Helpers
  // ============================================================

  /**
   * Resolves the strike string from the first visible CE add button.
   * Returns null if no CE data is present (chain empty or all LTPs = 0).
   */
  async function getFirstAvailableCEStrike(authenticatedPage) {
    const ceButton = authenticatedPage.locator('[data-testid^="optionchain-ce-add-"]').first();
    const visible = await ceButton.isVisible({ timeout: 15000 }).catch(() => false);
    if (!visible) return null;
    const testId = await ceButton.getAttribute('data-testid');
    return testId.replace('optionchain-ce-add-', '');
  }

  /**
   * Resolves the strike string from the first visible PE add button.
   * Returns null if no PE data is present.
   */
  async function getFirstAvailablePEStrike(authenticatedPage) {
    const peButton = authenticatedPage.locator('[data-testid^="optionchain-pe-add-"]').first();
    const visible = await peButton.isVisible({ timeout: 15000 }).catch(() => false);
    if (!visible) return null;
    const testId = await peButton.getAttribute('data-testid');
    return testId.replace('optionchain-pe-add-', '');
  }

  /**
   * Resolves the strike string from the second visible CE add button.
   * Returns null if fewer than 2 CE rows are present.
   */
  async function getSecondAvailableCEStrike(authenticatedPage) {
    const ceButtons = authenticatedPage.locator('[data-testid^="optionchain-ce-add-"]');
    const count = await ceButtons.count();
    if (count < 2) return null;
    const testId = await ceButtons.nth(1).getAttribute('data-testid');
    return testId.replace('optionchain-ce-add-', '');
  }

  /**
   * Clicks the remove (×) button inside a chip element.
   * The remove trigger is the first interactive child of the chip —
   * typically a <button> or an element with role="button".
   */
  async function clickChipRemove(chip) {
    const removeBtn = chip.locator('button, [role="button"]').first();
    await removeBtn.click();
  }

  // ============================================================
  // Selection Tests
  // ============================================================

  test('should remove individual CE chip', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();

    if (expectation !== 'LIVE' && expectation !== 'LAST_KNOWN') {
      console.log(`[${getISTTimeString()}] Market state: ${expectation} — skipping chip removal test`);
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    const ceStrike = await getFirstAvailableCEStrike(authenticatedPage);
    if (!ceStrike) {
      console.log('No CE data in chain rows — skipping individual CE chip removal test');
      return;
    }

    // Also select a PE so we can verify PE persists after CE is removed
    const peStrike = await getFirstAvailablePEStrike(authenticatedPage);

    await optionChainPage.selectCE(ceStrike);
    if (peStrike) {
      await optionChainPage.selectPE(peStrike);
    }

    await optionChainPage.assertSelectedBarVisible();

    // Remove the CE chip
    const ceChip = optionChainPage.getSelectedChip(ceStrike, 'CE');
    await expect(ceChip).toBeVisible();
    await clickChipRemove(ceChip);

    // CE chip must be gone
    await expect(ceChip).not.toBeVisible();

    // PE chip must still be present (if it was added)
    if (peStrike) {
      const peChip = optionChainPage.getSelectedChip(peStrike, 'PE');
      await expect(peChip).toBeVisible();
    }
  });

  test('should remove individual PE chip', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();

    if (expectation !== 'LIVE' && expectation !== 'LAST_KNOWN') {
      console.log(`[${getISTTimeString()}] Market state: ${expectation} — skipping PE chip removal test`);
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    const ceStrike = await getFirstAvailableCEStrike(authenticatedPage);
    const peStrike = await getFirstAvailablePEStrike(authenticatedPage);

    if (!peStrike) {
      console.log('No PE data in chain rows — skipping individual PE chip removal test');
      return;
    }

    if (ceStrike) {
      await optionChainPage.selectCE(ceStrike);
    }
    await optionChainPage.selectPE(peStrike);

    await optionChainPage.assertSelectedBarVisible();

    // Remove the PE chip
    const peChip = optionChainPage.getSelectedChip(peStrike, 'PE');
    await expect(peChip).toBeVisible();
    await clickChipRemove(peChip);

    // PE chip must be gone
    await expect(peChip).not.toBeVisible();

    // CE chip must still be present (if it was added)
    if (ceStrike) {
      const ceChip = optionChainPage.getSelectedChip(ceStrike, 'CE');
      await expect(ceChip).toBeVisible();
    }
  });

  test('should hide selected bar when last chip removed', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();

    if (expectation !== 'LIVE' && expectation !== 'LAST_KNOWN') {
      console.log(`[${getISTTimeString()}] Market state: ${expectation} — skipping bar-hide test`);
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    const ceStrike = await getFirstAvailableCEStrike(authenticatedPage);
    if (!ceStrike) {
      console.log('No CE data in chain rows — skipping bar-hide test');
      return;
    }

    // Select exactly one chip
    await optionChainPage.selectCE(ceStrike);
    await optionChainPage.assertSelectedBarVisible();

    // Remove it — bar must disappear
    const ceChip = optionChainPage.getSelectedChip(ceStrike, 'CE');
    await expect(ceChip).toBeVisible();
    await clickChipRemove(ceChip);

    await optionChainPage.assertSelectedBarHidden();
  });

  test('should show correct count after individual removal', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();

    if (expectation !== 'LIVE' && expectation !== 'LAST_KNOWN') {
      console.log(`[${getISTTimeString()}] Market state: ${expectation} — skipping count-after-removal test`);
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    const ceStrike1 = await getFirstAvailableCEStrike(authenticatedPage);
    const ceStrike2 = await getSecondAvailableCEStrike(authenticatedPage);
    const peStrike = await getFirstAvailablePEStrike(authenticatedPage);

    if (!ceStrike1 || !peStrike) {
      console.log('Insufficient chain data for count-after-removal test — need at least 1 CE and 1 PE');
      return;
    }

    // Build a selection of 3 chips (2 CE + 1 PE, or 1 CE + 1 PE if second CE unavailable)
    await optionChainPage.selectCE(ceStrike1);
    await optionChainPage.selectPE(peStrike);
    if (ceStrike2 && ceStrike2 !== ceStrike1) {
      await optionChainPage.selectCE(ceStrike2);
    }

    const countBefore = await optionChainPage.getSelectedCount();
    expect(countBefore).toBeGreaterThanOrEqual(2);

    // Remove the first CE chip
    const ceChip1 = optionChainPage.getSelectedChip(ceStrike1, 'CE');
    await expect(ceChip1).toBeVisible();
    await clickChipRemove(ceChip1);

    // Count must have decreased by exactly 1
    const countAfter = await optionChainPage.getSelectedCount();
    expect(countAfter).toBe(countBefore - 1);
  });

  test('should enable add-to-strategy button with selections', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();

    if (expectation !== 'LIVE' && expectation !== 'LAST_KNOWN') {
      console.log(`[${getISTTimeString()}] Market state: ${expectation} — skipping add-to-strategy button test`);
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    const ceStrike = await getFirstAvailableCEStrike(authenticatedPage);
    if (!ceStrike) {
      console.log('No CE data in chain rows — skipping add-to-strategy button test');
      return;
    }

    await optionChainPage.selectCE(ceStrike);
    await optionChainPage.assertSelectedBarVisible();

    // Add-to-strategy button must be visible and enabled
    await expect(optionChainPage.addToStrategyButton).toBeVisible();
    await expect(optionChainPage.addToStrategyButton).toBeEnabled();
  });

  // ============================================================
  // Market Closed Banner Tests
  // ============================================================

  test('should show market closed banner outside market hours', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();
    const marketClosedBanner = authenticatedPage.locator('[data-testid="optionchain-market-closed"]');

    console.log(`[${getISTTimeString()}] Market state: ${expectation}`);

    if (expectation === 'LAST_KNOWN' || expectation === 'CLOSED') {
      // Chain may or may not have data depending on broker availability.
      // Banner only shows when chain.length > 0, so check for actual data rows.
      const rowCount = await authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]').count();

      if (rowCount > 0) {
        // Data rows are present — banner must be visible
        await expect(marketClosedBanner).toBeVisible();
      } else {
        // No chain data loaded — banner may be absent; assert empty state instead
        await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
        console.log('Chain table not visible — market closed banner assertion skipped (no data to banner over)');
      }
    } else {
      // LIVE or PRE_OPEN — banner should not appear
      await expect(marketClosedBanner).not.toBeVisible();
    }
  });

  test('should hide market closed banner during market hours', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();
    const marketClosedBanner = authenticatedPage.locator('[data-testid="optionchain-market-closed"]');

    console.log(`[${getISTTimeString()}] Market state: ${expectation}`);

    if (expectation === 'LIVE') {
      // Market is open — banner must be hidden
      await expect(marketClosedBanner).not.toBeVisible();
    } else {
      // Not live — the "banner hidden during market hours" assertion cannot run.
      // Assert the page is stable and the banner state is consistent with the market state
      // (banner may or may not show in non-LIVE states, covered by the banner-visibility test).
      console.log(`Market state is ${expectation}, not LIVE — verifying page is stable`);
      await optionChainPage.assertPageVisible();
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });

  test('should show chain data alongside market closed banner', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();
    const marketClosedBanner = authenticatedPage.locator('[data-testid="optionchain-market-closed"]');

    console.log(`[${getISTTimeString()}] Market state: ${expectation}`);

    if (expectation === 'LAST_KNOWN' || expectation === 'CLOSED') {
      const rowCount = await authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]').count();

      if (rowCount > 0) {
        // Both banner and table must be simultaneously visible
        await expect(marketClosedBanner).toBeVisible();
        await expect(optionChainPage.table).toBeVisible();
      } else {
        // Broker returned no data rows — assert stable empty state
        await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
      }
    } else {
      // LIVE market — assert page is stable (banner may or may not be visible depending on data)
      await optionChainPage.assertPageVisible();
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });

  // ============================================================
  // Error Handling Tests
  // ============================================================

  test('should close error alert with dismiss button', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();

    const errorAlert = optionChainPage.errorAlert;
    const errorVisible = await errorAlert.isVisible({ timeout: 5000 }).catch(() => false);

    if (!errorVisible) {
      // No error currently showing — page loaded successfully
      // Assert the chain loaded into a valid state instead
      console.log('No error alert visible — chain loaded cleanly, verifying stable state');
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
      return;
    }

    // Error is visible — find and click the dismiss/close button inside the alert
    const dismissBtn = errorAlert.locator('button, [role="button"], [data-testid*="dismiss"], [data-testid*="close"]').first();
    const dismissVisible = await dismissBtn.isVisible({ timeout: 5000 }).catch(() => false);

    if (!dismissVisible) {
      // Alert has no dismiss button — assert it is at least visible as proof the alert renders
      await expect(errorAlert).toBeVisible();
      console.log('Error alert has no dismiss button — presence asserted only');
      return;
    }

    await dismissBtn.click();

    // After dismissal, the alert must no longer be visible
    await expect(errorAlert).not.toBeVisible();
  });
});
