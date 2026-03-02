import { test, expect } from '../../fixtures/auth.fixture.js';
import { OFOPage } from '../../pages/OFOPage.js';

/**
 * OFO (Options For Options) Screen - Happy Path Tests
 * Tests core functionality under normal conditions
 */
test.describe('OFO - Happy Path @happy', () => {
  let ofoPage;

  test.beforeEach(async ({ page }) => {
    ofoPage = new OFOPage(page);
    await ofoPage.navigate();
  });

  test('should display OFO page', async () => {
    await ofoPage.assertPageVisible();
  });

  // ============ Kite Layout & Stylesheet Tests ============
  test.describe('Kite Layout Integration', () => {
    test('should display Kite header', async ({ page }) => {
      await expect(page.getByTestId('kite-header')).toBeVisible();
    });

    test('should display Kite header logo', async ({ page }) => {
      await expect(page.getByTestId('kite-header-logo')).toBeVisible();
    });

    test('should display Kite header navigation', async ({ page }) => {
      await expect(page.getByTestId('kite-header-nav')).toBeVisible();
    });

    test('should have OFO link in navigation', async ({ page }) => {
      await expect(page.getByTestId('kite-header-nav-ofo')).toBeVisible();
    });

    test('should highlight OFO as active in navigation', async ({ page }) => {
      const ofoNavItem = page.getByTestId('kite-header-nav-ofo');
      await expect(ofoNavItem).toHaveAttribute('aria-current', 'page');
    });

    test('should display index prices in header', async ({ page }) => {
      await expect(page.getByTestId('kite-header-index-prices')).toBeVisible();
    });

    test('should display NIFTY 50 index', async ({ page }) => {
      await expect(page.getByTestId('kite-header-index-nifty50')).toBeVisible();
    });

    test('should display NIFTY BANK index', async ({ page }) => {
      await expect(page.getByTestId('kite-header-index-niftybank')).toBeVisible();
    });

    test('should display user menu', async ({ page }) => {
      await expect(page.getByTestId('kite-header-user-menu')).toBeVisible();
    });

    test('should display user avatar', async ({ page }) => {
      await expect(page.getByTestId('kite-header-user-avatar')).toBeVisible();
    });

    test('should display connection status indicator', async ({ page }) => {
      await expect(page.getByTestId('kite-header-connection-status')).toBeVisible();
    });

    test('should have correct header height (48px)', async ({ page }) => {
      const header = page.getByTestId('kite-header');
      const box = await header.boundingBox();
      expect(box.height).toBe(48);
    });

    test('should have header fixed at top', async ({ page }) => {
      const header = page.getByTestId('kite-header');
      const box = await header.boundingBox();
      expect(box.y).toBe(0);
    });

    test('should open user dropdown on click', async ({ page }) => {
      await page.getByTestId('kite-header-user-menu').click();
      await expect(page.getByTestId('kite-header-user-dropdown')).toBeVisible();
    });

    test('should display user name in dropdown', async ({ page }) => {
      await page.getByTestId('kite-header-user-menu').click();
      await expect(page.getByTestId('kite-header-user-name')).toBeVisible();
    });

    test('should display settings button in dropdown', async ({ page }) => {
      await page.getByTestId('kite-header-user-menu').click();
      await expect(page.getByTestId('kite-header-settings-button')).toBeVisible();
    });

    test('should display logout button in dropdown', async ({ page }) => {
      await page.getByTestId('kite-header-user-menu').click();
      await expect(page.getByTestId('kite-header-logout-button')).toBeVisible();
    });

    test('should have white background for header', async ({ page }) => {
      const header = page.getByTestId('kite-header');
      const bgColor = await header.evaluate(el => window.getComputedStyle(el).backgroundColor);
      // rgb(255, 255, 255) is white
      expect(bgColor).toBe('rgb(255, 255, 255)');
    });

    test('should have bottom border on header', async ({ page }) => {
      const header = page.getByTestId('kite-header');
      const borderBottom = await header.evaluate(el => window.getComputedStyle(el).borderBottomWidth);
      // Accept both 1px and sub-pixel values (browser may report 0.8px due to scaling)
      const borderWidth = parseFloat(borderBottom);
      expect(borderWidth).toBeGreaterThanOrEqual(0.5);
      expect(borderWidth).toBeLessThanOrEqual(1.5);
    });

    test('should have correct content padding below header', async ({ page }) => {
      const ofoPage = page.getByTestId('ofo-page');
      const ofoBox = await ofoPage.boundingBox();
      // Content should start at or after header (48px)
      expect(ofoBox.y).toBeGreaterThanOrEqual(48);
    });
  });

  test('should display page header with title', async ({ page }) => {
    await ofoPage.assertHeaderVisible();
    // The page has "OFO" title and "Options For Options" subtitle in the header
    const header = page.getByTestId('ofo-header');
    await expect(header).toContainText('OFO');
    await expect(header).toContainText('Options For Options');
  });

  test('should display underlying tabs', async () => {
    await expect(ofoPage.underlyingTabs).toBeVisible();
    await expect(ofoPage.niftyTab).toBeVisible();
    await expect(ofoPage.bankniftyTab).toBeVisible();
    await expect(ofoPage.finniftyTab).toBeVisible();
  });

  test('should display spot price', async () => {
    await expect(ofoPage.spotPrice).toBeVisible();
  });

  test('should display expiry selector', async () => {
    await expect(ofoPage.expirySelect).toBeVisible();
  });

  test('should display strategy multi-select', async () => {
    await expect(ofoPage.strategySelect).toBeVisible();
    await expect(ofoPage.strategyTrigger).toBeVisible();
  });

  test('should display strike range selector', async () => {
    await expect(ofoPage.strikeRangeSelect).toBeVisible();
  });

  test('should display lots input', async () => {
    await expect(ofoPage.lotsInput).toBeVisible();
  });

  test('should display calculate button', async () => {
    await expect(ofoPage.calculateButton).toBeVisible();
  });

  test('should display auto-refresh toggle', async () => {
    await expect(ofoPage.autoRefreshToggle).toBeVisible();
  });

  test('should switch underlying tabs', async () => {
    await ofoPage.selectUnderlying('BANKNIFTY');
    await expect(ofoPage.bankniftyTab).toHaveAttribute('aria-current', 'page');
  });

  test('should open strategy dropdown when clicked', async () => {
    await ofoPage.openStrategyDropdown();
    await expect(ofoPage.strategyDropdown).toBeVisible();
  });

  test('should show strategy options in dropdown', async () => {
    await ofoPage.openStrategyDropdown();

    // Check that some strategy options are visible
    await expect(ofoPage.getStrategyOption('iron_condor')).toBeVisible();
    await expect(ofoPage.getStrategyOption('short_straddle')).toBeVisible();
    await expect(ofoPage.getStrategyOption('bull_call_spread')).toBeVisible();
  });

  test('should have select all and clear all buttons in dropdown', async () => {
    await ofoPage.openStrategyDropdown();
    await expect(ofoPage.selectAllStrategiesBtn).toBeVisible();
    await expect(ofoPage.clearAllStrategiesBtn).toBeVisible();
  });

  test('should toggle strategy selection', async () => {
    await ofoPage.openStrategyDropdown();

    // Clear all first
    await ofoPage.clearAllStrategiesBtn.click();

    // Toggle iron condor
    await ofoPage.getStrategyOption('iron_condor').click();

    // Check it's selected (checkbox should be checked)
    const checkbox = ofoPage.getStrategyOption('iron_condor').locator('input[type="checkbox"]');
    await expect(checkbox).toBeChecked();
  });

  test('should select all strategies', async () => {
    await ofoPage.openStrategyDropdown();
    await ofoPage.clearAllStrategiesBtn.click();
    await ofoPage.selectAllStrategiesBtn.click();

    // Verify multiple strategies are selected by checking the trigger text
    await ofoPage.closeStrategyDropdown();
    const count = await ofoPage.getSelectedStrategiesCount();
    expect(count).toBeGreaterThan(0);
  });

  test('should clear all strategies', async () => {
    await ofoPage.openStrategyDropdown();
    await ofoPage.selectAllStrategiesBtn.click();
    await ofoPage.clearAllStrategiesBtn.click();

    await ofoPage.closeStrategyDropdown();
    // After clearing, trigger should show "Select Strategies"
    await expect(ofoPage.strategyTrigger).toContainText('Select Strategies');
  });

  test('should change strike range', async () => {
    await ofoPage.setStrikeRange(15);
    await expect(ofoPage.strikeRangeSelect).toHaveValue('15');
  });

  test('should change lots', async () => {
    await ofoPage.setLots(2);
    await expect(ofoPage.lotsInput).toHaveValue('2');
  });

  test('should have default lots of 1', async () => {
    await expect(ofoPage.lotsInput).toHaveValue('1');
  });

  test('should have default strike range of 10', async () => {
    await expect(ofoPage.strikeRangeSelect).toHaveValue('10');
  });

  test('should display empty state when no strategies selected', async ({ page }) => {
    await ofoPage.openStrategyDropdown();
    await ofoPage.clearAllStrategiesBtn.click();
    await ofoPage.closeStrategyDropdown();

    // Calculate button should be disabled when no strategies selected
    await expect(ofoPage.calculateButton).toBeDisabled();

    // Should show empty state prompting to select strategies
    const emptyState = page.getByTestId('ofo-empty');
    await expect(emptyState).toBeVisible();
    await expect(emptyState).toContainText('Select Strategies');
  });

  test('should have no horizontal overflow', async () => {
    const hasOverflow = await ofoPage.hasHorizontalOverflow();
    expect(hasOverflow).toBe(false);
  });
});
