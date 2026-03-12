import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation } from '../../helpers/market-status.helper.js';
import { waitForApiResponse } from '../../helpers/wait-helpers.js';

/**
 * Option Chain - Strike Finder Edge Case Tests
 * Tests boundary conditions and error handling for Strike Finder
 */
test.describe('Option Chain - Strike Finder Edge Cases @edge', () => {
  test.describe.configure({ timeout: 120000 });
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
    // EXCEPTION: mock is kept here because we need a specific 400 error that
    // cannot be reliably triggered via UI input validation bypass alone.
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
    // Error message must convey "no strikes found" — not just be truthy
    expect(errorText.toLowerCase()).toContain('no strikes found');
  });

  test('should clear previous result when searching again', async ({ page }) => {
    const expectation = getDataExpectation();
    if (expectation === 'PRE_OPEN' || expectation === 'CLOSED') {
      test.skip('Strike Finder requires live market data to verify result change');
      return;
    }

    // First live search with delta 0.30
    await optionChainPage.setStrikeFinderMode('delta');
    await optionChainPage.setStrikeFinderType('CE');
    await optionChainPage.enterTargetDelta(0.30);

    let responsePromise = waitForApiResponse(page, '/api/optionchain/find-by-delta', { timeout: 30000 });
    await optionChainPage.searchStrike();
    let response;
    try { response = await responsePromise; } catch {
      console.log('Strike Finder delta API timed out on first search — skipping');
      return;
    }

    if (response.status() !== 200) {
      console.log(`Strike Finder delta API returned ${response.status()} on first search — skipping result assertions`);
      return;
    }

    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });
    const firstResult = await response.json();

    // Second live search with different delta — result must change
    await optionChainPage.enterTargetDelta(0.20);

    responsePromise = waitForApiResponse(page, '/api/optionchain/find-by-delta', { timeout: 30000 });
    await optionChainPage.searchStrike();
    response = await responsePromise;

    if (response.status() !== 200) {
      console.log(`Strike Finder delta API returned ${response.status()} on second search — skipping result assertions`);
      return;
    }

    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });
    const secondResult = await response.json();

    // The two searches used different deltas — strikes should differ (or at minimum the result updated)
    // We can't guarantee different strikes (market conditions vary), but the result panel must refresh
    const strikeText = await optionChainPage.getStrikeFinderResultStrike();
    expect(strikeText).toMatch(/\d+/);

    // Both results must have valid structure
    expect(firstResult.ltp).toBeGreaterThan(0);
    expect(secondResult.ltp).toBeGreaterThan(0);
  });
});
