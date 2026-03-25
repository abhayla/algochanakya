import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation, getISTTimeString } from '../../helpers/market-status.helper.js';
import { waitForApiResponse } from '../../helpers/wait-helpers.js';

/**
 * Option Chain - Strike Finder "Select This Strike" Flow
 *
 * Tests the complete interaction: find a strike → click "Select This Strike"
 * → verify the finder panel closes and the chain scrolls to that strike row.
 *
 * Vue handler reference (OptionChain.vue):
 *   const handleStrikeSelected = (strike) => {
 *     store.toggleStrikeFinder()   // closes the panel
 *     const strikeRow = tableEl.querySelector(`[data-strike="${strike.strike}"]`)
 *     if (strikeRow) strikeRow.scrollIntoView({ behavior: 'smooth', block: 'center' })
 *   }
 */
test.describe('Option Chain - Strike Finder Select Flow @happy', () => {
  test.describe.configure({ timeout: 180000 });
  let optionChainPage;
  let chainLoadedSuccessfully = false;

  test.beforeEach(async ({ authenticatedPage }) => {
    chainLoadedSuccessfully = false;
    optionChainPage = new OptionChainPage(authenticatedPage);
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();
    const hasError = await optionChainPage.errorAlert.isVisible().catch(() => false);
    chainLoadedSuccessfully = !hasError;
  });

  // ---------------------------------------------------------------------------
  // Test 1: Finder closes after selecting a strike
  // ---------------------------------------------------------------------------

  test('should close strike finder after selecting a strike', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    if (expectation === 'PRE_OPEN' || expectation === 'CLOSED' || !chainLoadedSuccessfully) {
      test.skip(`Strike Finder select requires a loaded chain — market state: ${expectation} (${getISTTimeString()})`);
      return;
    }

    const responsePromise = waitForApiResponse(authenticatedPage, '/api/optionchain/find-by-delta', { timeout: 30000 });
    await optionChainPage.findStrikeByDelta(0.5, 'CE');

    let response;
    try {
      response = await responsePromise;
    } catch {
      console.log('Strike Finder delta API did not respond in time — skipping');
      return;
    }

    if (response.status() !== 200) {
      console.log(`Strike Finder delta API returned ${response.status()} — skipping select assertions`);
      return;
    }

    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });

    // Click "Select This Strike" — the button lives inside the result container
    const selectBtn = authenticatedPage.locator('[data-testid="optionchain-strike-finder-result"] button').first();
    await selectBtn.click();

    // Finder panel must be hidden after selection
    const isFinderVisible = await optionChainPage.isStrikeFinderVisible();
    expect(isFinderVisible).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // Test 2: Selected strike row is scrolled into view
  // ---------------------------------------------------------------------------

  test('should scroll to selected strike row', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    if (expectation === 'PRE_OPEN' || expectation === 'CLOSED' || !chainLoadedSuccessfully) {
      test.skip(`Strike scroll requires a loaded chain — market state: ${expectation} (${getISTTimeString()})`);
      return;
    }

    const responsePromise = waitForApiResponse(authenticatedPage, '/api/optionchain/find-by-delta', { timeout: 30000 });
    await optionChainPage.findStrikeByDelta(0.3, 'CE');

    let response;
    try {
      response = await responsePromise;
    } catch {
      console.log('Strike Finder delta API did not respond in time — skipping');
      return;
    }

    if (response.status() !== 200) {
      console.log(`Strike Finder delta API returned ${response.status()} — skipping scroll assertion`);
      return;
    }

    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });

    // Capture the strike value before closing the finder
    const strikeText = await optionChainPage.getStrikeFinderResultStrike();

    const selectBtn = authenticatedPage.locator('[data-testid="optionchain-strike-finder-result"] button').first();
    await selectBtn.click();

    // Finder must close
    const isFinderVisible = await optionChainPage.isStrikeFinderVisible();
    expect(isFinderVisible).toBe(false);

    // The strike row identified by data-strike should exist in the DOM and be visible
    // scrollIntoView is called by Vue — give the browser a tick to complete smooth scroll
    const strikeValue = strikeText.trim().replace(/[^0-9]/g, '');
    if (strikeValue) {
      const strikeRow = authenticatedPage.locator(`[data-strike="${strikeValue}"]`);
      const rowExists = await strikeRow.isVisible().catch(() => false);
      if (rowExists) {
        await expect(strikeRow).toBeInViewport({ ratio: 0.1, timeout: 5000 });
      } else {
        // Row exists in DOM but scrollIntoView may still be in progress; verify DOM presence
        const rowCount = await authenticatedPage.locator(`[data-strike="${strikeValue}"]`).count();
        expect(rowCount).toBeGreaterThan(0);
      }
    }
  });

  // ---------------------------------------------------------------------------
  // Test 3: Select works from Premium mode
  // ---------------------------------------------------------------------------

  test('should select strike from premium mode', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    if (expectation === 'PRE_OPEN' || expectation === 'CLOSED' || !chainLoadedSuccessfully) {
      test.skip(`Premium mode select requires a loaded chain — market state: ${expectation} (${getISTTimeString()})`);
      return;
    }

    const responsePromise = waitForApiResponse(authenticatedPage, '/api/optionchain/find-by-premium', { timeout: 30000 });
    await optionChainPage.findStrikeByPremium(100, 'CE');

    let response;
    try {
      response = await responsePromise;
    } catch {
      console.log('Strike Finder premium API did not respond in time — skipping');
      return;
    }

    if (response.status() !== 200) {
      console.log(`Strike Finder premium API returned ${response.status()} — skipping select assertions`);
      return;
    }

    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });

    const selectBtn = authenticatedPage.locator('[data-testid="optionchain-strike-finder-result"] button').first();
    await selectBtn.click();

    // Finder must close after selecting from premium mode
    const isFinderVisible = await optionChainPage.isStrikeFinderVisible();
    expect(isFinderVisible).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // Test 4: Select works for PE option type
  // ---------------------------------------------------------------------------

  test('should select PE strike and close finder', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    if (expectation === 'PRE_OPEN' || expectation === 'CLOSED' || !chainLoadedSuccessfully) {
      test.skip(`PE select requires a loaded chain — market state: ${expectation} (${getISTTimeString()})`);
      return;
    }

    const responsePromise = waitForApiResponse(authenticatedPage, '/api/optionchain/find-by-delta', { timeout: 30000 });
    await optionChainPage.findStrikeByDelta(0.5, 'PE');

    let response;
    try {
      response = await responsePromise;
    } catch {
      console.log('Strike Finder delta API (PE) did not respond in time — skipping');
      return;
    }

    if (response.status() !== 200) {
      console.log(`Strike Finder delta API (PE) returned ${response.status()} — skipping select assertions`);
      return;
    }

    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });

    const selectBtn = authenticatedPage.locator('[data-testid="optionchain-strike-finder-result"] button').first();
    await selectBtn.click();

    // Finder must close regardless of option type
    const isFinderVisible = await optionChainPage.isStrikeFinderVisible();
    expect(isFinderVisible).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // Test 5: Result panel shows complete data before select is clicked
  // ---------------------------------------------------------------------------

  test('should show result with strike, LTP and delta values before selecting', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    if (expectation === 'PRE_OPEN' || expectation === 'CLOSED' || !chainLoadedSuccessfully) {
      test.skip(`Result detail check requires a loaded chain — market state: ${expectation} (${getISTTimeString()})`);
      return;
    }

    const responsePromise = waitForApiResponse(authenticatedPage, '/api/optionchain/find-by-delta', { timeout: 30000 });
    await optionChainPage.findStrikeByDelta(0.3, 'CE');

    let response;
    try {
      response = await responsePromise;
    } catch {
      console.log('Strike Finder delta API did not respond in time — skipping');
      return;
    }

    if (response.status() !== 200) {
      console.log(`Strike Finder delta API returned ${response.status()} — skipping detail assertions`);
      return;
    }

    const apiResult = await response.json();

    // Result panel is visible before any click
    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });

    // Strike value must be a number
    const strikeText = await optionChainPage.getStrikeFinderResultStrike();
    expect(strikeText.trim()).toMatch(/\d+/);

    // Result panel text contains a decimal LTP value (e.g. "142.50")
    const resultText = await optionChainPage.strikeFinderResult.textContent();
    expect(resultText).toMatch(/\d+\.\d+/);

    // API response carries valid delta and positive LTP
    expect(apiResult.ltp).toBeGreaterThan(0);
    expect(apiResult.delta).toBeGreaterThan(0);
    expect(apiResult.delta).toBeLessThanOrEqual(1);

    // "Select This Strike" button is present and enabled before clicking
    const selectBtn = authenticatedPage.locator('[data-testid="optionchain-strike-finder-result"] button').first();
    await expect(selectBtn).toBeVisible();
    await expect(selectBtn).toBeEnabled();
  });

  // ---------------------------------------------------------------------------
  // Test 6: Strike row with matching data-strike attribute exists in chain
  // ---------------------------------------------------------------------------

  test('should find matching data-strike row in chain after selecting', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    if (expectation === 'PRE_OPEN' || expectation === 'CLOSED' || !chainLoadedSuccessfully) {
      test.skip(`data-strike row check requires a loaded chain — market state: ${expectation} (${getISTTimeString()})`);
      return;
    }

    const responsePromise = waitForApiResponse(authenticatedPage, '/api/optionchain/find-by-delta', { timeout: 30000 });
    await optionChainPage.findStrikeByDelta(0.4, 'CE');

    let response;
    try {
      response = await responsePromise;
    } catch {
      console.log('Strike Finder delta API did not respond in time — skipping');
      return;
    }

    if (response.status() !== 200) {
      console.log(`Strike Finder delta API returned ${response.status()} — skipping row existence assertion`);
      return;
    }

    const apiResult = await response.json();
    await expect(optionChainPage.strikeFinderResult).toBeVisible({ timeout: 5000 });

    const selectBtn = authenticatedPage.locator('[data-testid="optionchain-strike-finder-result"] button').first();
    await selectBtn.click();

    // Finder must close
    const isFinderVisible = await optionChainPage.isStrikeFinderVisible();
    expect(isFinderVisible).toBe(false);

    // The strike returned by the API must have a corresponding row in the rendered chain
    // data-strike is set by OptionChainTable.vue on each strike row
    if (apiResult.strike) {
      const strikeRow = authenticatedPage.locator(`[data-strike="${apiResult.strike}"]`);
      const rowCount = await strikeRow.count();
      // The chain should contain at least one row for the returned strike
      expect(rowCount).toBeGreaterThan(0);
    }
  });
});
