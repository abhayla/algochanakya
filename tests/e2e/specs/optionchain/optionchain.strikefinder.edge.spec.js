import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';

/**
 * Option Chain - Strike Finder Edge Case Tests
 * Tests boundary conditions and error handling for Strike Finder
 */
test.describe('Option Chain - Strike Finder Edge Cases @edge', () => {
  let optionChainPage;

  test.beforeEach(async ({ page }) => {
    optionChainPage = new OptionChainPage(page);
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();
    await optionChainPage.openStrikeFinder();
  });

  test('should disable search button for invalid delta > 1', async () => {
    await optionChainPage.setStrikeFinderMode('delta');
    await optionChainPage.setStrikeFinderType('CE');
    await optionChainPage.enterTargetDelta(1.5);

    // Button should be disabled for invalid input
    await expect(optionChainPage.strikeFinderSearchBtn).toBeDisabled();
  });

  test('should disable search button for invalid delta < 0', async () => {
    await optionChainPage.setStrikeFinderMode('delta');
    await optionChainPage.setStrikeFinderType('CE');
    await optionChainPage.enterTargetDelta(-0.2);

    // Button should be disabled for invalid input
    await expect(optionChainPage.strikeFinderSearchBtn).toBeDisabled();
  });

  test('should disable search button for zero premium', async () => {
    await optionChainPage.setStrikeFinderMode('premium');
    await optionChainPage.setStrikeFinderType('PE');
    await optionChainPage.enterTargetPremium(0);

    // Button should be disabled for invalid input
    await expect(optionChainPage.strikeFinderSearchBtn).toBeDisabled();
  });

  test('should disable search button for negative premium', async () => {
    await optionChainPage.setStrikeFinderMode('premium');
    await optionChainPage.setStrikeFinderType('PE');
    await optionChainPage.enterTargetPremium(-100);

    // Button should be disabled for invalid input
    await expect(optionChainPage.strikeFinderSearchBtn).toBeDisabled();
  });

  test('should disable search button when input is empty', async () => {
    // Delta mode with empty input
    await optionChainPage.setStrikeFinderMode('delta');
    await optionChainPage.strikeFinderDeltaInput.fill('');
    await expect(optionChainPage.strikeFinderSearchBtn).toBeDisabled();

    // Premium mode with empty input
    await optionChainPage.setStrikeFinderMode('premium');
    await optionChainPage.strikeFinderPremiumInput.fill('');
    await expect(optionChainPage.strikeFinderSearchBtn).toBeDisabled();
  });

  test('should handle API error gracefully', async ({ page }) => {
    // Mock API error response
    await page.route('**/api/optionchain/find-by-delta', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'No strikes found matching the criteria'
        })
      });
    });

    await optionChainPage.setStrikeFinderMode('delta');
    await optionChainPage.setStrikeFinderType('CE');
    await optionChainPage.enterTargetDelta(0.99);
    await optionChainPage.searchStrike();

    // Should display error message
    await expect(optionChainPage.strikeFinderError).toBeVisible({ timeout: 5000 });
    const errorText = await optionChainPage.getStrikeFinderErrorText();
    expect(errorText).toBeTruthy();
  });

  test('should clear previous result when searching again', async ({ page }) => {
    // Mock first successful search
    await page.route('**/api/optionchain/find-by-delta', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          strike: 24500,
          ltp: 145.50,
          delta: 0.30,
          iv: 0.1523,
          distance_from_target: 0.001
        })
      });
    });

    await optionChainPage.setStrikeFinderMode('delta');
    await optionChainPage.setStrikeFinderType('CE');
    await optionChainPage.enterTargetDelta(0.30);
    await optionChainPage.searchStrike();

    // Verify first result
    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });
    let strikeText = await optionChainPage.getStrikeFinderResultStrike();
    expect(strikeText).toContain('24500');

    // Mock second search with different result
    await page.route('**/api/optionchain/find-by-delta', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          strike: 24600,
          ltp: 120.75,
          delta: 0.25,
          iv: 0.1445,
          distance_from_target: 0.001
        })
      });
    });

    await optionChainPage.enterTargetDelta(0.25);
    await optionChainPage.searchStrike();

    // Verify second result replaced first
    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });
    strikeText = await optionChainPage.getStrikeFinderResultStrike();
    expect(strikeText).toContain('24600');
  });
});
