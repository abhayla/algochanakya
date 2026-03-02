import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';

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

  test('should search strike by delta with API mock', async ({ page }) => {
    // Mock the API response
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

    await optionChainPage.openStrikeFinder();
    await optionChainPage.setStrikeFinderMode('delta');
    await optionChainPage.setStrikeFinderType('CE');
    await optionChainPage.enterTargetDelta(0.30);
    await optionChainPage.searchStrike();

    // Wait for result
    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });
  });

  test('should search strike by premium with API mock', async ({ page }) => {
    // Mock the API response
    await page.route('**/api/optionchain/find-by-premium', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          strike: 24550,
          ltp: 180.25,
          delta: 0.35,
          iv: 0.1445,
          distance_from_target: 0.25
        })
      });
    });

    await optionChainPage.openStrikeFinder();
    await optionChainPage.setStrikeFinderMode('premium');
    await optionChainPage.setStrikeFinderType('PE');
    await optionChainPage.enterTargetPremium(180);
    await optionChainPage.searchStrike();

    // Wait for result
    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });
  });

  test('should display strike result with all details', async ({ page }) => {
    // Mock the API response
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

    await optionChainPage.openStrikeFinder();
    await optionChainPage.setStrikeFinderMode('delta');
    await optionChainPage.setStrikeFinderType('CE');
    await optionChainPage.enterTargetDelta(0.30);
    await optionChainPage.searchStrike();

    // Wait for result
    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });

    // Verify strike value is displayed
    const strikeText = await optionChainPage.getStrikeFinderResultStrike();
    expect(strikeText).toContain('24500');

    // Verify result contains LTP, Delta, and IV
    const resultText = await optionChainPage.strikeFinderResult.textContent();
    expect(resultText).toContain('145.50'); // LTP
    expect(resultText).toContain('0.30'); // Delta
    expect(resultText).toMatch(/15\.\d%/); // IV percentage
  });
});
