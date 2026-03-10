import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation, assertDataOrEmptyState } from '../../helpers/market-status.helper.js';

/**
 * Option Chain Screen - Happy Path Tests
 * Tests core functionality under normal conditions
 */
test.describe('Option Chain - Happy Path @happy', () => {
  test.describe.configure({ timeout: 120000 });
  let optionChainPage;

  test.beforeEach(async ({ page }) => {
    optionChainPage = new OptionChainPage(page);
    await optionChainPage.navigate();
  });

  test('should display option chain page', async () => {
    await optionChainPage.assertPageVisible();
  });

  test('should display underlying tabs', async () => {
    await expect(optionChainPage.underlyingTabs).toBeVisible();
    await expect(optionChainPage.niftyTab).toBeVisible();
    await expect(optionChainPage.bankniftyTab).toBeVisible();
    // FINNIFTY was delisted by NSE in Nov 2024 — tab may not render if no instruments available
    const finniftyCount = await optionChainPage.finniftyTab.count();
    if (finniftyCount > 0) {
      await expect(optionChainPage.finniftyTab).toBeVisible();
    }
  });

  test('should display expiry selector', async () => {
    await expect(optionChainPage.expirySelect).toBeVisible();
  });

  test('should display spot price box', async () => {
    await expect(optionChainPage.spotBox).toBeVisible();
  });

  test('should display DTE box', async () => {
    await expect(optionChainPage.dteBox).toBeVisible();
  });

  test('should display Greeks toggle', async () => {
    await expect(optionChainPage.greeksToggle).toBeVisible();
  });

  test('should display live toggle', async () => {
    await expect(optionChainPage.liveToggle).toBeVisible();
  });

  test('should display refresh button', async () => {
    await expect(optionChainPage.refreshButton).toBeVisible();
  });

  test('should display summary bar with PCR and Max Pain', async () => {
    await optionChainPage.waitForChainLoad();
    await expect(optionChainPage.summaryBar).toBeVisible();
  });

  test('should display option chain table or empty state', async ({ page }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();
    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      await expect(optionChainPage.table).toBeVisible();
    } else {
      await assertDataOrEmptyState(page, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });

  test('should switch underlying tabs', async () => {
    await optionChainPage.selectUnderlying('BANKNIFTY');
    await expect(optionChainPage.bankniftyTab).toHaveAttribute('aria-selected', 'true');
  });

  test('should have no horizontal overflow', async () => {
    const hasOverflow = await optionChainPage.hasHorizontalOverflow();
    expect(hasOverflow).toBe(false);
  });
});
