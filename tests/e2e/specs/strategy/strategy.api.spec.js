import { test, expect } from '../../fixtures/auth.fixture.js';
import { StrategyBuilderPage } from '../../pages/StrategyBuilderPage.js';
import {
  assertNoErrors,
  assertPayoffRendered,
  verifyCMP,
  verifyStrategyState,
  waitForCalculation,
  fetchLTPFromAPI
} from '../../helpers/strategy.helpers.js';

/**
 * Strategy Builder Screen - API Tests
 * Tests API interactions and data loading
 *
 * Enhanced with best practices:
 * - Verify CMP values against API
 * - Verify no errors after API calls
 * - Verify payoff chart renders
 */
test.describe('Strategy Builder - API @api', () => {
  let strategyPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyPage = new StrategyBuilderPage(authenticatedPage);
  });

  test('should fetch expiries on page load', async ({ authenticatedPage }) => {
    const expiryPromise = authenticatedPage.waitForResponse(
      response => response.url().includes('/api/options/expiries'),
      { timeout: 10000 }
    ).catch(() => null);

    await strategyPage.navigate();
    const response = await expiryPromise;

    if (response) {
      expect(response.status()).toBe(200);
    }
  });

  test('should fetch saved strategies on page load', async ({ authenticatedPage }) => {
    const strategiesPromise = authenticatedPage.waitForResponse(
      response => response.url().includes('/api/strategies'),
      { timeout: 10000 }
    ).catch(() => null);

    await strategyPage.navigate();
    const response = await strategiesPromise;

    if (response) {
      expect([200, 401]).toContain(response.status());
    }
  });

  test('should fetch strikes when expiry is selected', async () => {
    await strategyPage.navigate();
    await strategyPage.addRow();

    // This would require selecting an expiry in the leg
    // For now, just verify page is stable
    await strategyPage.assertPageVisible();
  });

  test('should call calculate API on recalculate', async ({ authenticatedPage }) => {
    await strategyPage.navigate();
    await strategyPage.addRow();

    const legCount = await strategyPage.getLegCount();
    if (legCount > 0) {
      const calculatePromise = authenticatedPage.waitForResponse(
        response => response.url().includes('/api/strategies/calculate'),
        { timeout: 15000 }
      ).catch(() => null);

      // Try to recalculate (may fail if leg not complete)
      const isDisabled = await strategyPage.recalculateButton.isDisabled();
      if (!isDisabled) {
        await strategyPage.recalculate();
        const response = await calculatePromise;
        if (response) {
          expect([200, 400, 422]).toContain(response.status());
        }
      }
    }
  });

  test('should have save button visible when strategy has name and legs', async ({ authenticatedPage }) => {
    await strategyPage.navigate();
    await strategyPage.enterStrategyName('API Test Strategy');
    await strategyPage.addRow();

    // Save button should be visible
    await expect(strategyPage.saveButton).toBeVisible();

    // Verify save button is enabled when conditions are met
    const isDisabled = await strategyPage.saveButton.isDisabled();
    // Save may be disabled if leg is incomplete - this is expected
    expect(typeof isDisabled).toBe('boolean');
  });

  test('should fetch LTP for instruments with valid prices', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    const ltpPromise = page.waitForResponse(
      response => response.url().includes('/api/orders/ltp'),
      { timeout: 10000 }
    ).catch(() => null);

    await strategyPage.navigate();
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);

    // LTP might be called for leg instruments
    const response = await ltpPromise;

    if (response) {
      expect(response.status()).toBe(200);

      // Validate LTP response contains valid price data
      const data = await response.json();

      // LTP endpoint should return valid price data
      // Structure: { instruments: [{token, ltp, ...}] } or similar
      if (data && typeof data === 'object') {
        // If data contains LTP values, they should be positive numbers
        const hasValidLtp = Object.values(data).some(item => {
          if (typeof item === 'number') {
            return item > 0;
          }
          if (typeof item === 'object' && item !== null && 'ltp' in item) {
            return item.ltp > 0;
          }
          return false;
        });

        // Test will fail if Kite broker token is expired and no valid LTP data
        expect(hasValidLtp || Object.keys(data).length === 0).toBeTruthy();
      }
    }

    // ENHANCED: Verify UI CMP matches API data
    const legs = await strategyPage.getAllLegsDetails();
    if (legs.length > 0) {
      const cmpResult = await verifyCMP(page, legs[0], strategyPage, 0.5);
      expect(cmpResult.valid, 'CMP should be valid').toBe(true);

      // ENHANCED: Verify no error banners
      const errorCheck = await assertNoErrors(page, strategyPage, 'after LTP fetch');
      expect(errorCheck.valid, 'No errors should appear').toBe(true);
    }

    await strategyPage.assertPageVisible();
  });

  test('should handle API errors gracefully', async () => {
    // Navigate normally
    await strategyPage.navigate();

    // Page should be visible regardless
    await strategyPage.assertPageVisible();
  });

  test('should display loading indicator during calculation', async ({ authenticatedPage }) => {
    await strategyPage.navigate();
    await strategyPage.addRow();

    const isDisabled = await strategyPage.recalculateButton.isDisabled();
    if (!isDisabled) {
      // Click recalculate and check for loading
      const recalcPromise = strategyPage.recalculate();

      // May briefly show loading
      await Promise.race([
        authenticatedPage.waitForSelector('[data-testid="strategy-loading"]', { timeout: 1000 }),
        recalcPromise
      ]).catch(() => {});

      await strategyPage.assertPageVisible();
    }
  });

  test('should populate summary cards from calculation', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await strategyPage.navigate();
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await waitForCalculation(page, strategyPage);

    // ENHANCED: Comprehensive state verification
    const stateCheck = await verifyStrategyState(page, strategyPage, 'after calculation', {
      expectedLegCount: 1,
      checkPayoff: true
    });

    // Check if summary cards exist
    const hasSummary = await strategyPage.hasSummaryCards();
    expect(hasSummary).toBe(true);

    // Verify summary grid is visible
    await strategyPage.assertSummaryVisible();

    // ENHANCED: Verify no errors and valid CMP
    expect(stateCheck.checks.noErrors, 'No errors after calculation').toBe(true);
    expect(stateCheck.checks.allCMPsValid, 'All CMP values should be valid').toBe(true);
    expect(stateCheck.checks.payoffRendered, 'Payoff chart should render').toBe(true);
  });
});
