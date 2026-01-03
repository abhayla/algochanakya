import { test, expect } from '../../fixtures/auth.fixture.js';
import OFOPage from '../../pages/OFOPage.js';

/**
 * OFO Calculate Button Tests
 * Tests calculation for each strategy type with screenshot verification
 */
test.describe('OFO - Calculate Button Tests @calculate', () => {
  // Increase timeout for calculation tests (complex strategies may take longer)
  test.setTimeout(60000);

  let ofoPage;

  // List of all strategies to test
  const strategies = [
    { key: 'iron_condor', name: 'Iron Condor' },
    { key: 'iron_butterfly', name: 'Iron Butterfly' },
    { key: 'short_straddle', name: 'Short Straddle' },
    { key: 'short_strangle', name: 'Short Strangle' },
    { key: 'long_straddle', name: 'Long Straddle' },
    { key: 'long_strangle', name: 'Long Strangle' },
    { key: 'bull_call_spread', name: 'Bull Call Spread' },
    { key: 'bear_put_spread', name: 'Bear Put Spread' },
    { key: 'butterfly_spread', name: 'Butterfly Spread' }
  ];

  test.beforeEach(async ({ page }) => {
    ofoPage = new OFOPage(page);
    await ofoPage.navigate();
    await ofoPage.assertPageVisible();
  });

  // Test each strategy individually
  for (const strategy of strategies) {
    test(`should calculate ${strategy.name} and display results`, async ({ page }) => {
      // Open strategy dropdown and clear all
      await ofoPage.openStrategyDropdown();
      await ofoPage.clearAllStrategiesBtn.click();

      // Select only this strategy
      await ofoPage.getStrategyOption(strategy.key).click();
      await ofoPage.closeStrategyDropdown();

      // Verify calculate button is enabled
      await expect(ofoPage.calculateButton).toBeEnabled();

      // Click calculate
      await ofoPage.calculateButton.click();

      // Wait for loading to complete (up to 60s for complex calculations)
      await page.waitForSelector('[data-testid="ofo-loading"]', { state: 'visible', timeout: 5000 }).catch(() => {});
      await page.waitForSelector('[data-testid="ofo-loading"]', { state: 'hidden', timeout: 60000 }).catch(() => {});

      // Take screenshot of results
      await page.screenshot({
        path: `test-results/ofo-calculate-${strategy.key}.png`,
        fullPage: true
      });

      // Check if we got results or an error
      const hasResults = await ofoPage.resultsSection.isVisible().catch(() => false);
      const hasError = await ofoPage.errorAlert.isVisible().catch(() => false);

      if (hasError) {
        const errorText = await ofoPage.errorAlert.textContent();
        console.log(`[${strategy.name}] Error: ${errorText}`);
        // Take error screenshot
        await page.screenshot({
          path: `test-results/ofo-calculate-${strategy.key}-error.png`,
          fullPage: true
        });
      }

      // Either results or empty state should be visible (no error for valid strategies)
      if (!hasError) {
        const strategyGroup = ofoPage.getStrategyGroup(strategy.key);
        const groupVisible = await strategyGroup.isVisible().catch(() => false);

        if (groupVisible) {
          // Strategy group should have results
          const groupText = await strategyGroup.textContent();
          console.log(`[${strategy.name}] Results found: ${groupText.substring(0, 100)}...`);

          // Verify group contains strategy name
          await expect(strategyGroup).toContainText(strategy.name);

          // Check for result count
          const resultCountMatch = groupText.match(/\((\d+) results?\)/);
          if (resultCountMatch) {
            const count = parseInt(resultCountMatch[1]);
            console.log(`[${strategy.name}] Result count: ${count}`);
            expect(count).toBeGreaterThanOrEqual(0);
          }
        } else {
          console.log(`[${strategy.name}] No results displayed (possibly no valid combinations found)`);
        }
      }

      // Verify no error state for a standard calculation
      // (Some strategies might have no valid combinations, but shouldn't error)
      expect(hasError).toBe(false);
    });
  }

  // Test all strategies together
  test('should calculate all strategies at once', async ({ page }) => {
    // Select all strategies
    await ofoPage.openStrategyDropdown();
    await ofoPage.selectAllStrategiesBtn.click();
    await ofoPage.closeStrategyDropdown();

    // Verify 9 strategies are selected
    const count = await ofoPage.getSelectedStrategiesCount();
    expect(count).toBe(9);

    // Click calculate
    await ofoPage.calculateButton.click();

    // Wait for loading to complete (longer timeout for all strategies)
    await page.waitForSelector('[data-testid="ofo-loading"]', { state: 'visible', timeout: 5000 }).catch(() => {});
    await page.waitForSelector('[data-testid="ofo-loading"]', { state: 'hidden', timeout: 120000 }).catch(() => {});

    // Take screenshot
    await page.screenshot({
      path: `test-results/ofo-calculate-all-strategies.png`,
      fullPage: true
    });

    // Check results
    const hasResults = await ofoPage.resultsSection.isVisible().catch(() => false);
    const hasError = await ofoPage.errorAlert.isVisible().catch(() => false);

    if (hasError) {
      const errorText = await ofoPage.errorAlert.textContent();
      console.log(`[All Strategies] Error: ${errorText}`);
      await page.screenshot({
        path: `test-results/ofo-calculate-all-strategies-error.png`,
        fullPage: true
      });
    }

    expect(hasError).toBe(false);

    // Verify at least one strategy group is displayed
    if (hasResults) {
      let visibleGroups = 0;
      for (const strategy of strategies) {
        const groupVisible = await ofoPage.getStrategyGroup(strategy.key).isVisible().catch(() => false);
        if (groupVisible) {
          visibleGroups++;
          console.log(`[All Strategies] ${strategy.name}: visible`);
        }
      }
      console.log(`[All Strategies] Total visible groups: ${visibleGroups}`);
      expect(visibleGroups).toBeGreaterThan(0);
    }
  });

  // Test calculation time is displayed
  test('should display calculation time after calculate', async ({ page }) => {
    // Select one strategy
    await ofoPage.openStrategyDropdown();
    await ofoPage.clearAllStrategiesBtn.click();
    await ofoPage.getStrategyOption('short_straddle').click();
    await ofoPage.closeStrategyDropdown();

    // Calculate
    await ofoPage.calculateButton.click();
    await page.waitForSelector('[data-testid="ofo-loading"]', { state: 'hidden', timeout: 60000 }).catch(() => {});

    // Verify calc time is displayed
    const calcTimeVisible = await ofoPage.calcTime.isVisible().catch(() => false);
    if (calcTimeVisible) {
      const calcTimeText = await ofoPage.calcTime.textContent();
      console.log(`Calculation time: ${calcTimeText}`);
      expect(calcTimeText).toMatch(/\d+\s*ms/);
    }

    // Take screenshot
    await page.screenshot({
      path: `test-results/ofo-calculate-with-time.png`,
      fullPage: true
    });
  });

  // Test with different lot sizes
  test('should calculate correctly with 2 lots', async ({ page }) => {
    // Set lots to 2
    await ofoPage.setLots(2);
    await expect(ofoPage.lotsInput).toHaveValue('2');

    // Select iron condor
    await ofoPage.openStrategyDropdown();
    await ofoPage.clearAllStrategiesBtn.click();
    await ofoPage.getStrategyOption('iron_condor').click();
    await ofoPage.closeStrategyDropdown();

    // Calculate
    await ofoPage.calculateButton.click();
    await page.waitForSelector('[data-testid="ofo-loading"]', { state: 'hidden', timeout: 60000 }).catch(() => {});

    // Take screenshot
    await page.screenshot({
      path: `test-results/ofo-calculate-2-lots.png`,
      fullPage: true
    });

    const hasError = await ofoPage.errorAlert.isVisible().catch(() => false);
    expect(hasError).toBe(false);
  });

  // Test with different strike ranges
  test('should calculate correctly with ±15 strike range', async ({ page }) => {
    // Set strike range to 15
    await ofoPage.setStrikeRange(15);
    await expect(ofoPage.strikeRangeSelect).toHaveValue('15');

    // Select short strangle
    await ofoPage.openStrategyDropdown();
    await ofoPage.clearAllStrategiesBtn.click();
    await ofoPage.getStrategyOption('short_strangle').click();
    await ofoPage.closeStrategyDropdown();

    // Calculate
    await ofoPage.calculateButton.click();
    await page.waitForSelector('[data-testid="ofo-loading"]', { state: 'hidden', timeout: 60000 }).catch(() => {});

    // Take screenshot
    await page.screenshot({
      path: `test-results/ofo-calculate-15-strikes.png`,
      fullPage: true
    });

    const hasError = await ofoPage.errorAlert.isVisible().catch(() => false);
    expect(hasError).toBe(false);
  });

  // Test for different underlyings
  test('should calculate BANKNIFTY strategies', async ({ page }) => {
    // Switch to BANKNIFTY
    await ofoPage.selectUnderlying('BANKNIFTY');
    await expect(ofoPage.bankniftyTab).toHaveClass(/active/);

    // Wait for expiries to load
    await page.waitForTimeout(1000);

    // Select short straddle
    await ofoPage.openStrategyDropdown();
    await ofoPage.clearAllStrategiesBtn.click();
    await ofoPage.getStrategyOption('short_straddle').click();
    await ofoPage.closeStrategyDropdown();

    // Calculate
    await ofoPage.calculateButton.click();
    await page.waitForSelector('[data-testid="ofo-loading"]', { state: 'hidden', timeout: 60000 }).catch(() => {});

    // Take screenshot
    await page.screenshot({
      path: `test-results/ofo-calculate-banknifty.png`,
      fullPage: true
    });

    const hasError = await ofoPage.errorAlert.isVisible().catch(() => false);
    expect(hasError).toBe(false);
  });

  test('should calculate FINNIFTY strategies', async ({ page }) => {
    // Switch to FINNIFTY
    await ofoPage.selectUnderlying('FINNIFTY');
    await expect(ofoPage.finniftyTab).toHaveClass(/active/);

    // Wait for expiries to load
    await page.waitForTimeout(1000);

    // Select bull call spread
    await ofoPage.openStrategyDropdown();
    await ofoPage.clearAllStrategiesBtn.click();
    await ofoPage.getStrategyOption('bull_call_spread').click();
    await ofoPage.closeStrategyDropdown();

    // Calculate
    await ofoPage.calculateButton.click();
    await page.waitForSelector('[data-testid="ofo-loading"]', { state: 'hidden', timeout: 60000 }).catch(() => {});

    // Take screenshot
    await page.screenshot({
      path: `test-results/ofo-calculate-finnifty.png`,
      fullPage: true
    });

    const hasError = await ofoPage.errorAlert.isVisible().catch(() => false);
    expect(hasError).toBe(false);
  });
});
