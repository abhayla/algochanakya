/**
 * AutoPilot Dropdown Options - Comprehensive Test
 *
 * Tests all dropdown options on AutoPilot strategy builder
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotStrategyBuilderPage } from '../../pages/AutoPilotDashboardPage.js';

test.describe('AutoPilot Dropdown Options', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.goto('/autopilot/strategies/new');
    await builderPage.page.waitForSelector('[data-testid="autopilot-legs-table"]', { timeout: 10000 });
  });

  test('should support all Underlying options', async () => {
    const underlyingDropdown = builderPage.page.locator('[data-testid="autopilot-builder-underlying"]');

    const underlyings = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX'];

    for (const underlying of underlyings) {
      await underlyingDropdown.selectOption(underlying);
      await builderPage.page.waitForLoadState('domcontentloaded');
      await expect(underlyingDropdown).toHaveValue(underlying);
    }
  });

  test('should support all Strategy Type options', async () => {
    const strategyTypeDropdown = builderPage.page.locator('[data-testid="autopilot-builder-strategy-type"]');

    const strategyTypes = [
      'custom',
      'bull_call_spread',
      'bull_put_spread',
      'synthetic_long',
      'bear_put_spread',
      'bear_call_spread',
      'synthetic_short',
      'iron_condor',
      'iron_butterfly',
      'short_straddle',
      'short_strangle'
    ];

    for (const strategyType of strategyTypes) {
      await strategyTypeDropdown.selectOption(strategyType);
      await builderPage.page.waitForLoadState('domcontentloaded');
      await expect(strategyTypeDropdown).toHaveValue(strategyType);
    }
  });

  test('should support all Expiry Type options', async () => {
    const expiryTypeDropdown = builderPage.page.locator('[data-testid="autopilot-builder-expiry-type"]');

    const expiryTypes = [
      'current_week',
      'next_week',
      'monthly'
    ];

    for (const expiryType of expiryTypes) {
      await expiryTypeDropdown.selectOption(expiryType);
      await builderPage.page.waitForLoadState('domcontentloaded');
      await expect(expiryTypeDropdown).toHaveValue(expiryType);
    }
  });

  test('should support all Position Type options', async () => {
    const positionTypeDropdown = builderPage.page.locator('[data-testid="autopilot-builder-position-type"]');

    const positionTypes = ['intraday', 'positional'];

    for (const positionType of positionTypes) {
      await positionTypeDropdown.selectOption(positionType);
      await builderPage.page.waitForLoadState('domcontentloaded');
      await expect(positionTypeDropdown).toHaveValue(positionType);
    }
  });

  test('should support all Strike Mode options with a leg', async () => {
    // Add a leg first
    await builderPage.page.click('button[data-testid="autopilot-legs-add-row-button"]');
    // Wait for the leg row to appear
    await builderPage.page.locator('[data-testid="autopilot-leg-row-0"]').waitFor({ state: 'visible' });

    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('[data-testid="autopilot-strike-selector"]') }).first();
    const modeDropdown = strikeCell.locator('[data-testid="autopilot-strike-mode-dropdown"]');

    const strikeModes = [
      'atm_offset',
      'fixed',
      'delta_based',
      'premium_based',
      'sd_based'
    ];

    for (const mode of strikeModes) {
      await modeDropdown.selectOption(mode);
      await builderPage.page.waitForLoadState('domcontentloaded');
      await expect(modeDropdown).toHaveValue(mode);

      // Verify mode-specific inputs appear
      if (mode === 'fixed') {
        const fixedInput = strikeCell.locator('input[type="number"]').first();
        await expect(fixedInput).toBeVisible();
      } else if (mode === 'atm_offset') {
        const offsetInput = strikeCell.locator('input[type="number"]').first();
        await expect(offsetInput).toBeVisible();
      }
    }
  });

  test('should support all Action options (BUY/SELL) with a leg', async () => {
    // Add a leg first
    await builderPage.page.click('button[data-testid="autopilot-legs-add-row-button"]');
    // Wait for the leg row to appear
    await builderPage.page.locator('[data-testid="autopilot-leg-row-0"]').waitFor({ state: 'visible' });

    const actionDropdown = builderPage.page.locator('tbody tr').first().locator('select').first();

    await actionDropdown.selectOption('BUY');
    await expect(actionDropdown).toHaveValue('BUY');

    await actionDropdown.selectOption('SELL');
    await expect(actionDropdown).toHaveValue('SELL');
  });

  test('should support all Option Type options (CE/PE) with a leg', async () => {
    // Add a leg first
    await builderPage.page.click('button[data-testid="autopilot-legs-add-row-button"]');
    // Wait for the leg row to appear
    await builderPage.page.locator('[data-testid="autopilot-leg-row-0"]').waitFor({ state: 'visible' });

    // Get the option type dropdown (4th select in the row after action, expiry, strike mode)
    const optionTypeDropdown = builderPage.page.locator('tbody tr').first().locator('select').nth(3);

    await optionTypeDropdown.selectOption('CE');
    await expect(optionTypeDropdown).toHaveValue('CE');

    await optionTypeDropdown.selectOption('PE');
    await expect(optionTypeDropdown).toHaveValue('PE');
  });

  test('should support changing lots value', async () => {
    const lotsInput = builderPage.page.locator('[data-testid="autopilot-builder-lots"]');

    await lotsInput.fill('5');
    await expect(lotsInput).toHaveValue('5');

    await lotsInput.fill('1');
    await expect(lotsInput).toHaveValue('1');
  });
});
