import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation } from '../../helpers/market-status.helper.js';
import { waitForApiResponse } from '../../helpers/wait-helpers.js';

/**
 * Option Chain - Strike Finder Happy Path Tests
 * Tests Strike Finder functionality under normal conditions
 */
test.describe('Option Chain - Strike Finder Happy Path @happy', () => {
  let optionChainPage;

  test.beforeEach(async ({ page }) => {
    optionChainPage = new OptionChainPage(page);
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();
  });

  test('should display Strike Finder button in header', async () => {
    await expect(optionChainPage.strikeFinderBtn).toBeVisible();
    await expect(optionChainPage.strikeFinderBtn).toContainText(/Find Strike/i);
  });

  test('should open Strike Finder panel when clicking button', async () => {
    await optionChainPage.openStrikeFinder();
    const isVisible = await optionChainPage.isStrikeFinderVisible();
    expect(isVisible).toBe(true);
  });

  test('should close Strike Finder panel when clicking close button', async () => {
    await optionChainPage.openStrikeFinder();
    await optionChainPage.closeStrikeFinder();
    const isVisible = await optionChainPage.isStrikeFinderVisible();
    expect(isVisible).toBe(false);
  });

  test('should default to Delta mode', async () => {
    await optionChainPage.openStrikeFinder();
    const modeValue = await optionChainPage.strikeFinderMode.inputValue();
    expect(modeValue).toBe('delta');
  });

  test('should switch between Delta and Premium modes', async () => {
    await optionChainPage.openStrikeFinder();

    // Switch to Premium mode
    await optionChainPage.setStrikeFinderMode('premium');
    let modeValue = await optionChainPage.strikeFinderMode.inputValue();
    expect(modeValue).toBe('premium');

    // Switch back to Delta mode
    await optionChainPage.setStrikeFinderMode('delta');
    modeValue = await optionChainPage.strikeFinderMode.inputValue();
    expect(modeValue).toBe('delta');
  });

  test('should show delta input when Delta mode selected', async () => {
    await optionChainPage.openStrikeFinder();
    await optionChainPage.setStrikeFinderMode('delta');
    await expect(optionChainPage.strikeFinderDeltaInput).toBeVisible();
  });

  test('should show premium input when Premium mode selected', async () => {
    await optionChainPage.openStrikeFinder();
    await optionChainPage.setStrikeFinderMode('premium');
    await expect(optionChainPage.strikeFinderPremiumInput).toBeVisible();
  });

  test('should search strike by delta', async ({ page }) => {
    const expectation = getDataExpectation();
    if (expectation === 'PRE_OPEN' || expectation === 'CLOSED') {
      test.skip('Strike Finder requires live market data');
      return;
    }

    await optionChainPage.openStrikeFinder();
    await optionChainPage.setStrikeFinderMode('delta');
    await optionChainPage.setStrikeFinderType('CE');
    await optionChainPage.enterTargetDelta(0.30);

    const responsePromise = waitForApiResponse(page, '/api/optionchain/find-by-delta', { timeout: 10000 });
    await optionChainPage.searchStrike();
    const response = await responsePromise;
    expect(response.status()).toBe(200);

    // Verify result is shown
    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });
    const result = await response.json();
    expect(typeof result.strike === 'number' || !isNaN(parseInt(result.strike))).toBe(true);
    expect(result.ltp).toBeGreaterThan(0);
  });

  test('should search strike by premium', async ({ page }) => {
    const expectation = getDataExpectation();
    if (expectation === 'PRE_OPEN' || expectation === 'CLOSED') {
      test.skip('Strike Finder requires live market data');
      return;
    }

    await optionChainPage.openStrikeFinder();
    await optionChainPage.setStrikeFinderMode('premium');
    await optionChainPage.setStrikeFinderType('PE');
    await optionChainPage.enterTargetPremium(180);

    const responsePromise = waitForApiResponse(page, '/api/optionchain/find-by-premium', { timeout: 10000 });
    await optionChainPage.searchStrike();
    const response = await responsePromise;
    expect(response.status()).toBe(200);

    // Verify result is shown
    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });
    const result = await response.json();
    expect(typeof result.strike === 'number' || !isNaN(parseInt(result.strike))).toBe(true);
    expect(result.ltp).toBeGreaterThan(0);
  });

  test('should display strike result with all details', async ({ page }) => {
    const expectation = getDataExpectation();
    if (expectation === 'PRE_OPEN' || expectation === 'CLOSED') {
      test.skip('Strike Finder requires live market data');
      return;
    }

    await optionChainPage.openStrikeFinder();
    await optionChainPage.setStrikeFinderMode('delta');
    await optionChainPage.setStrikeFinderType('CE');
    await optionChainPage.enterTargetDelta(0.30);

    const responsePromise = waitForApiResponse(page, '/api/optionchain/find-by-delta', { timeout: 10000 });
    await optionChainPage.searchStrike();
    const response = await responsePromise;
    expect(response.status()).toBe(200);

    const result = await response.json();

    // Verify result panel is shown
    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });

    // Validate result fields with regex patterns
    const strikeText = await optionChainPage.getStrikeFinderResultStrike();
    expect(strikeText).toMatch(/\d+/); // strike is a numeric value

    const resultText = await optionChainPage.strikeFinderResult.textContent();
    // LTP should be a decimal number
    expect(resultText).toMatch(/\d+\.\d+/);
    // Delta should be present (0.xx format)
    expect(result.delta).toBeGreaterThan(0);
    expect(result.delta).toBeLessThanOrEqual(1);
    // IV should be present and positive
    expect(result.iv).toBeGreaterThan(0);
  });
});
