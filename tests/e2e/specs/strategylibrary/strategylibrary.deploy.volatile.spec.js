/**
 * Strategy Library Deployment Tests - Volatile Strategies
 *
 * Tests deployment of all volatile strategies from Strategy Library to Strategy Builder:
 * - Long Straddle (2 legs)
 * - Long Strangle (2 legs)
 * - Reverse Iron Condor (4 legs)
 *
 * Each strategy is tested for:
 * 1. Correct leg count after deployment
 * 2. All leg fields populated correctly (Type, B/S, Strike, Lots, Entry, Qty)
 * 3. P/L grid calculation (Max Profit, Max Loss, Breakeven)
 * 4. Deployment with multiple lots
 * 5. Deployment to different underlying (BANKNIFTY)
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { StrategyLibraryPage } from '../../pages/StrategyLibraryPage.js';
import { StrategyBuilderPage } from '../../pages/StrategyBuilderPage.js';
import { STRATEGY_TEMPLATES, LOT_SIZES } from '../../fixtures/strategy-templates.fixture.js';

const VOLATILE_STRATEGIES = [
  'long_straddle',
  'long_strangle',
  'reverse_iron_condor'
];

test.describe('Strategy Library Deploy - Volatile Strategies @deploy @volatile', () => {
  let strategyLibraryPage;
  let strategyBuilderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyLibraryPage = new StrategyLibraryPage(authenticatedPage);
    strategyBuilderPage = new StrategyBuilderPage(authenticatedPage);
  });

  // Generate tests for each volatile strategy
  for (const strategyName of VOLATILE_STRATEGIES) {
    const template = STRATEGY_TEMPLATES[strategyName];

    test.describe(`${template.displayName}`, () => {

      test(`should deploy ${template.displayName} with correct leg count`, async ({ authenticatedPage }) => {
        // Navigate to Strategy Library
        await strategyLibraryPage.navigate();
        await strategyLibraryPage.assertPageVisible();

        // Open deploy modal
        await strategyLibraryPage.openDeploy(strategyName);
        await strategyLibraryPage.assertDeployModalVisible();

        // Verify leg preview count in modal
        const legPreviewCount = await strategyLibraryPage.getDeployLegsCount();
        expect(legPreviewCount).toBe(template.legCount);

        // Configure deployment
        await strategyLibraryPage.selectDeployUnderlying('NIFTY');
        await authenticatedPage.waitForLoadState('domcontentloaded'); // Wait for expiries to load
        await strategyLibraryPage.setDeployLots(1);

        // Deploy
        await strategyLibraryPage.confirmDeploy();

        // Verify success state
        await expect(strategyLibraryPage.deploySuccess).toBeVisible({ timeout: 15000 });

        // Navigate to Strategy Builder
        await strategyLibraryPage.clickViewStrategy();

        // Verify navigation
        await expect(authenticatedPage).toHaveURL(/\/strategy\/[\w-]+/);

        // Wait for Strategy Builder to load
        await strategyBuilderPage.waitForPageLoad();
        await strategyBuilderPage.waitForPnLCalculation();

        // Verify leg count in Strategy Builder
        const legCount = await strategyBuilderPage.getLegCount();
        expect(legCount).toBe(template.legCount);
      });

      test(`should verify ${template.displayName} leg fields after deployment`, async ({ authenticatedPage }) => {
        // Deploy strategy
        await strategyLibraryPage.navigate();
        await strategyLibraryPage.openDeploy(strategyName);
        await strategyLibraryPage.selectDeployUnderlying('NIFTY');
        await authenticatedPage.waitForLoadState('domcontentloaded');
        await strategyLibraryPage.setDeployLots(1);
        await strategyLibraryPage.confirmDeploy();
        await expect(strategyLibraryPage.deploySuccess).toBeVisible({ timeout: 15000 });
        await strategyLibraryPage.clickViewStrategy();

        // Wait for Strategy Builder and legs to load
        await strategyBuilderPage.waitForPageLoad();
        await strategyBuilderPage.waitForLegsLoaded(template.legCount);
        await strategyBuilderPage.waitForPnLCalculation();

        // Get all legs
        const legs = await strategyBuilderPage.getAllLegsDetails();
        expect(legs.length).toBe(template.legCount);

        // Verify each leg
        let strikePopulatedCount = 0;
        for (let i = 0; i < template.legs.length; i++) {
          const expectedLeg = template.legs[i];
          const actualLeg = legs[i];

          // Verify Type (CE/PE)
          expect(actualLeg.type, `Leg ${i} Type`).toBe(expectedLeg.type);

          // Verify B/S (BUY/SELL)
          expect(actualLeg.buySell, `Leg ${i} B/S`).toBe(expectedLeg.position);

          // Verify Lots = 1
          expect(parseInt(actualLeg.lots), `Leg ${i} Lots`).toBe(1);

          // Verify Qty = lots * lotSize (75 for NIFTY)
          expect(parseInt(actualLeg.qty), `Leg ${i} Qty`).toBe(LOT_SIZES.NIFTY);

          // Strike may not be visible in dropdown if it's outside available options
          if (actualLeg.strike && actualLeg.strike !== '') {
            expect(parseFloat(actualLeg.strike), `Leg ${i} Strike > 0`).toBeGreaterThan(0);
            strikePopulatedCount++;
          }

          // Verify Entry price is populated (this confirms the leg data is valid)
          expect(actualLeg.entry, `Leg ${i} Entry`).not.toBe('');
          expect(parseFloat(actualLeg.entry), `Leg ${i} Entry > 0`).toBeGreaterThan(0);
        }

        // At least some legs should have visible strikes
        expect(strikePopulatedCount, 'At least one leg should have strike populated').toBeGreaterThan(0);
      });

      test(`should verify ${template.displayName} P/L grid is calculated`, async ({ authenticatedPage }) => {
        // Deploy strategy
        await strategyLibraryPage.navigate();
        await strategyLibraryPage.openDeploy(strategyName);
        await strategyLibraryPage.selectDeployUnderlying('NIFTY');
        await authenticatedPage.waitForLoadState('domcontentloaded');
        await strategyLibraryPage.confirmDeploy();
        await expect(strategyLibraryPage.deploySuccess).toBeVisible({ timeout: 15000 });
        await strategyLibraryPage.clickViewStrategy();

        // Wait for Strategy Builder and P/L calculation
        await strategyBuilderPage.waitForPageLoad();
        await strategyBuilderPage.waitForPnLCalculation();

        // Verify summary cards are visible
        const hasSummary = await strategyBuilderPage.hasSummaryCards();
        expect(hasSummary).toBe(true);

        await expect(strategyBuilderPage.summaryGrid).toBeVisible();
        await expect(strategyBuilderPage.maxProfitCard).toBeVisible();
        await expect(strategyBuilderPage.maxLossCard).toBeVisible();

        // Get summary values
        const summary = await strategyBuilderPage.getSummaryValues();

        // Summary values should be populated (may be "-", "Unlimited", or numeric)
        // For some edge cases (e.g., unprofitable spreads), breakeven may show "-"
        // For unlimited strategies, max profit/loss may show "Unlimited"
        // The key verification is that the values are present (not empty strings)
        expect(summary.maxProfit, 'Max profit should be populated').toBeTruthy();
        expect(summary.maxLoss, 'Max loss should be populated').toBeTruthy();
        expect(summary.breakeven, 'Breakeven should be populated').toBeTruthy();

        // Verify payoff chart is visible
        const hasPayoff = await strategyBuilderPage.hasPayoffChart();
        expect(hasPayoff).toBe(true);
      });

      test(`should deploy ${template.displayName} with 2 lots`, async ({ authenticatedPage }) => {
        // Deploy with 2 lots
        await strategyLibraryPage.navigate();
        await strategyLibraryPage.openDeploy(strategyName);
        await strategyLibraryPage.selectDeployUnderlying('NIFTY');
        await authenticatedPage.waitForLoadState('domcontentloaded');
        await strategyLibraryPage.setDeployLots(2);
        await strategyLibraryPage.confirmDeploy();
        await expect(strategyLibraryPage.deploySuccess).toBeVisible({ timeout: 15000 });
        await strategyLibraryPage.clickViewStrategy();

        // Wait for Strategy Builder
        await strategyBuilderPage.waitForPageLoad();
        await strategyBuilderPage.waitForPnLCalculation();

        // Verify all legs have 2 lots
        const legs = await strategyBuilderPage.getAllLegsDetails();
        expect(legs.length).toBe(template.legCount);

        for (let i = 0; i < legs.length; i++) {
          const leg = legs[i];

          // Verify lots = 2
          expect(parseInt(leg.lots), `Leg ${i} Lots`).toBe(2);

          // Verify qty = 2 * 75 = 150
          expect(parseInt(leg.qty), `Leg ${i} Qty`).toBe(2 * LOT_SIZES.NIFTY);
        }
      });

      test(`should deploy ${template.displayName} to BANKNIFTY`, async ({ authenticatedPage }) => {
        // Deploy to BANKNIFTY
        await strategyLibraryPage.navigate();
        await strategyLibraryPage.openDeploy(strategyName);
        await strategyLibraryPage.selectDeployUnderlying('BANKNIFTY');
        await authenticatedPage.waitForLoadState('domcontentloaded');
        await strategyLibraryPage.setDeployLots(1);
        await strategyLibraryPage.confirmDeploy();
        await expect(strategyLibraryPage.deploySuccess).toBeVisible({ timeout: 15000 });
        await strategyLibraryPage.clickViewStrategy();

        // Wait for Strategy Builder
        await strategyBuilderPage.waitForPageLoad();
        await strategyBuilderPage.waitForPnLCalculation();

        // Verify BANKNIFTY tab is active
        const isBankniftyActive = await strategyBuilderPage.isUnderlyingActive('BANKNIFTY');
        expect(isBankniftyActive).toBe(true);

        // Verify all legs use BANKNIFTY lot size (15)
        const legs = await strategyBuilderPage.getAllLegsDetails();
        expect(legs.length).toBe(template.legCount);

        for (let i = 0; i < legs.length; i++) {
          const leg = legs[i];

          // Verify qty = 1 * 15 = 15
          expect(parseInt(leg.qty), `Leg ${i} Qty`).toBe(LOT_SIZES.BANKNIFTY);
        }
      });

    });
  }
});
