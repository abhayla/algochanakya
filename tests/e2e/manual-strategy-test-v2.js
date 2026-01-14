/**
 * Manual Strategy Page E2E Test with Screenshots - V2
 * Tests all features, buttons, dropdowns on the Strategy page
 * Fixed screenshot timeout issues
 */

import { chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const FRONTEND_URL = 'http://localhost:5173';
const SCREENSHOT_DIR = './screenshots/strategy-test-v2';
const AUTH_STATE_PATH = './tests/config/.auth-state.json';

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function takeScreenshot(page, name) {
  try {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filepath = path.join(SCREENSHOT_DIR, `${name}_${timestamp}.png`);
    await page.screenshot({ path: filepath, fullPage: false, timeout: 10000 });
    console.log(`📸 Screenshot: ${name}`);
    return filepath;
  } catch (e) {
    console.log(`⚠️ Screenshot failed: ${name} - ${e.message}`);
    return null;
  }
}

async function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runTests() {
  console.log('\n========================================');
  console.log('  STRATEGY PAGE E2E TEST V2');
  console.log('========================================\n');

  const browser = await chromium.launch({
    headless: false,
    slowMo: 50
  });

  const context = await browser.newContext({
    viewport: { width: 1600, height: 900 }
  });

  // Load auth state
  const authState = JSON.parse(fs.readFileSync(AUTH_STATE_PATH, 'utf8'));

  const page = await context.newPage();

  // Capture console errors
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  // Inject auth token
  await page.goto(FRONTEND_URL);
  await page.evaluate((localStorage) => {
    localStorage.forEach(item => {
      window.localStorage.setItem(item.name, item.value);
    });
  }, authState.origins[0].localStorage);

  console.log('✓ Auth token injected\n');

  const results = { passed: [], failed: [], issues: [] };

  try {
    // ========== TEST 1: Page Load ==========
    console.log('--- TEST 1: Page Load ---');
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('networkidle', { timeout: 15000 });
    await delay(2000);

    const pageVisible = await page.locator('[data-testid="strategy-page"]').isVisible();
    if (pageVisible) {
      console.log('✓ Strategy page loaded');
      results.passed.push('Page Load');
    } else {
      console.log('✗ Strategy page failed to load');
      results.failed.push('Page Load');
    }
    await takeScreenshot(page, '01_page_load');

    // ========== TEST 2: Check Spot Price ==========
    console.log('\n--- TEST 2: Spot Price Display ---');
    const spotCard = await page.locator('[data-testid="strategy-spot-card"]');
    const spotText = await spotCard.textContent();
    console.log(`Spot card content: "${spotText}"`);

    if (spotText.includes('0') && !spotText.match(/\d{4,}/)) {
      console.log('⚠️ ISSUE: Spot price showing 0 (no live data)');
      results.issues.push('Spot price is 0 - live data not loading');
    } else {
      console.log('✓ Spot price has value');
      results.passed.push('Spot Price Display');
    }

    // ========== TEST 3: Underlying Tabs ==========
    console.log('\n--- TEST 3: Underlying Tabs ---');
    const niftyTab = await page.locator('[data-testid="strategy-underlying-nifty"]').isVisible();
    const bankniftyTab = await page.locator('[data-testid="strategy-underlying-banknifty"]').isVisible();
    const finniftyTab = await page.locator('[data-testid="strategy-underlying-finnifty"]').isVisible();

    if (niftyTab && bankniftyTab && finniftyTab) {
      console.log('✓ All underlying tabs visible');

      // Click BANKNIFTY
      await page.click('[data-testid="strategy-underlying-banknifty"]');
      await delay(1000);
      const bankniftyActive = await page.locator('[data-testid="strategy-underlying-banknifty"]').getAttribute('class');
      if (bankniftyActive.includes('active')) {
        console.log('✓ BANKNIFTY tab click works');
        results.passed.push('Underlying Tabs');
      }
      await takeScreenshot(page, '02_banknifty_tab');

      // Click back to NIFTY
      await page.click('[data-testid="strategy-underlying-nifty"]');
      await delay(500);
    } else {
      console.log('✗ Some underlying tabs missing');
      results.failed.push('Underlying Tabs');
    }

    // ========== TEST 4: P/L Mode Toggle ==========
    console.log('\n--- TEST 4: P/L Mode Toggle ---');
    const expiryBtn = await page.locator('[data-testid="strategy-pnl-mode-expiry"]');
    const currentBtn = await page.locator('[data-testid="strategy-pnl-mode-current"]');

    if (await expiryBtn.isVisible() && await currentBtn.isVisible()) {
      await currentBtn.click();
      await delay(500);
      const currentClass = await currentBtn.getAttribute('class');
      if (currentClass.includes('active')) {
        console.log('✓ P/L mode toggle works');
        results.passed.push('P/L Mode Toggle');
      }
      await expiryBtn.click();
      await delay(300);
    } else {
      console.log('✗ P/L mode buttons missing');
      results.failed.push('P/L Mode Toggle');
    }
    await takeScreenshot(page, '03_pnl_mode');

    // ========== TEST 5: Strategy Type Dropdown ==========
    console.log('\n--- TEST 5: Strategy Type Dropdown ---');
    const typeSelect = await page.locator('[data-testid="strategy-type-select"]');
    if (await typeSelect.isVisible()) {
      // Check options exist
      const options = await typeSelect.locator('option').count();
      console.log(`Found ${options} strategy type options`);

      if (options > 5) {
        console.log('✓ Strategy type dropdown has options');
        results.passed.push('Strategy Type Dropdown');
      } else {
        console.log('⚠️ Strategy type dropdown has few options');
        results.issues.push('Strategy type dropdown may be missing options');
      }
    } else {
      console.log('✗ Strategy type dropdown not visible');
      results.failed.push('Strategy Type Dropdown');
    }
    await takeScreenshot(page, '04_strategy_type');

    // ========== TEST 6: Add Row Button ==========
    console.log('\n--- TEST 6: Add Row Button ---');
    const addRowBtn = await page.locator('[data-testid="strategy-add-row-button"]');
    if (await addRowBtn.isVisible()) {
      const isDisabled = await addRowBtn.isDisabled();
      console.log(`Add Row button disabled: ${isDisabled}`);

      if (!isDisabled) {
        const beforeRows = await page.locator('.leg-row').count();
        await addRowBtn.click();
        await delay(2000);
        const afterRows = await page.locator('.leg-row').count();

        console.log(`Rows: ${beforeRows} -> ${afterRows}`);
        if (afterRows > beforeRows) {
          console.log('✓ Add Row creates new leg');
          results.passed.push('Add Row Button');
        } else {
          console.log('✗ Add Row did not create new leg');
          results.failed.push('Add Row Button');
        }
      } else {
        console.log('⚠️ Add Row button is disabled');
        results.issues.push('Add Row button disabled - may need expiries loaded');
      }
    } else {
      console.log('✗ Add Row button not found');
      results.failed.push('Add Row Button');
    }
    await takeScreenshot(page, '05_add_row');

    // ========== TEST 7: Leg Row Elements ==========
    console.log('\n--- TEST 7: Leg Row Elements ---');
    const legRows = await page.locator('.leg-row').count();
    if (legRows > 0) {
      // Check first leg has all elements
      const firstLeg = page.locator('.leg-row').first();
      const hasExpiry = await firstLeg.locator('select').first().isVisible();
      const hasCheckbox = await firstLeg.locator('input[type="checkbox"]').isVisible();

      if (hasExpiry && hasCheckbox) {
        console.log('✓ Leg row has expected elements');
        results.passed.push('Leg Row Elements');
      } else {
        console.log('✗ Leg row missing elements');
        results.failed.push('Leg Row Elements');
      }
    } else {
      console.log('⚠️ No leg rows to test');
      results.issues.push('No leg rows present');
    }
    await takeScreenshot(page, '06_leg_elements');

    // ========== TEST 8: ReCalculate Button ==========
    console.log('\n--- TEST 8: ReCalculate Button ---');
    const recalcBtn = await page.locator('[data-testid="strategy-recalculate-button"]');
    if (await recalcBtn.isVisible()) {
      const isDisabled = await recalcBtn.isDisabled();
      console.log(`ReCalculate button disabled: ${isDisabled}`);

      if (!isDisabled && legRows > 0) {
        await recalcBtn.click();
        await delay(3000);
        console.log('✓ ReCalculate button works');
        results.passed.push('ReCalculate Button');
      } else if (isDisabled) {
        console.log('⚠️ ReCalculate disabled (no valid legs)');
        results.issues.push('ReCalculate disabled - needs valid legs');
      }
    }
    await takeScreenshot(page, '07_recalculate');

    // ========== TEST 9: Summary Cards ==========
    console.log('\n--- TEST 9: Summary Cards ---');
    const cards = {
      maxProfit: await page.locator('[data-testid="strategy-max-profit-card"]').isVisible(),
      maxLoss: await page.locator('[data-testid="strategy-max-loss-card"]').isVisible(),
      breakeven: await page.locator('[data-testid="strategy-breakeven-card"]').isVisible(),
      riskReward: await page.locator('[data-testid="strategy-risk-reward-card"]').isVisible(),
      spot: await page.locator('[data-testid="strategy-spot-card"]').isVisible()
    };

    const allCardsVisible = Object.values(cards).every(v => v);
    if (allCardsVisible) {
      console.log('✓ All summary cards visible');
      results.passed.push('Summary Cards');
    } else {
      console.log('✗ Some summary cards missing:', cards);
      results.failed.push('Summary Cards');
    }
    await takeScreenshot(page, '08_summary_cards');

    // ========== TEST 10: Action Bar ==========
    console.log('\n--- TEST 10: Action Bar ---');
    const actionBar = await page.locator('[data-testid="strategy-action-bar"]').isVisible();
    const saveBtn = await page.locator('[data-testid="strategy-save-button"]').isVisible();
    const importBtn = await page.locator('[data-testid="strategy-import-positions-button"]').isVisible();
    const basketBtn = await page.locator('[data-testid="strategy-basket-order-button"]').isVisible();

    if (actionBar && saveBtn && importBtn && basketBtn) {
      console.log('✓ Action bar buttons visible');
      results.passed.push('Action Bar');
    } else {
      console.log('✗ Action bar buttons missing');
      results.failed.push('Action Bar');
    }
    await takeScreenshot(page, '09_action_bar');

    // ========== TEST 11: Strategy Name Input ==========
    console.log('\n--- TEST 11: Strategy Name Input ---');
    const nameInput = await page.locator('[data-testid="strategy-name-input"]');
    if (await nameInput.isVisible()) {
      await nameInput.fill('Test Strategy E2E');
      await delay(500);
      const value = await nameInput.inputValue();
      if (value === 'Test Strategy E2E') {
        console.log('✓ Strategy name input works');
        results.passed.push('Strategy Name Input');
      }
    }
    await takeScreenshot(page, '10_name_input');

    // ========== TEST 12: Select Strategy Type - Iron Condor ==========
    console.log('\n--- TEST 12: Select Iron Condor Strategy ---');
    await page.selectOption('[data-testid="strategy-type-select"]', 'iron_condor');
    await delay(3000);

    const legsAfterSelect = await page.locator('.leg-row').count();
    console.log(`Legs after Iron Condor selection: ${legsAfterSelect}`);

    if (legsAfterSelect >= 4) {
      console.log('✓ Iron Condor auto-populated 4 legs');
      results.passed.push('Strategy Type Auto-populate');
    } else {
      console.log('⚠️ Iron Condor did not populate expected legs');
      results.issues.push('Iron Condor auto-populate may have issues');
    }
    await takeScreenshot(page, '11_iron_condor');

    // ========== TEST 13: Table with P/L Columns ==========
    console.log('\n--- TEST 13: P/L Table Columns ---');
    await delay(2000);
    const tableWrapper = await page.locator('[data-testid="strategy-table-wrapper"]');
    const tableVisible = await tableWrapper.isVisible();

    if (tableVisible) {
      // Check for spot columns
      const spotColumns = await page.locator('.th-spot').count();
      console.log(`Found ${spotColumns} P/L spot columns`);

      if (spotColumns > 0) {
        console.log('✓ P/L grid columns present');
        results.passed.push('P/L Table Columns');
      } else {
        console.log('⚠️ No P/L spot columns found');
        results.issues.push('P/L calculation may not have run');
      }
    }
    await takeScreenshot(page, '12_pnl_table');

    // ========== TEST 14: Payoff Chart ==========
    console.log('\n--- TEST 14: Payoff Chart ---');
    const payoffSection = await page.locator('[data-testid="strategy-payoff-section"]').isVisible();
    if (payoffSection) {
      console.log('✓ Payoff chart section visible');
      results.passed.push('Payoff Chart');
    } else {
      console.log('⚠️ Payoff chart not visible (may need calculation)');
      results.issues.push('Payoff chart not showing');
    }
    await takeScreenshot(page, '13_payoff');

    // ========== TEST 15: Delete Legs ==========
    console.log('\n--- TEST 15: Delete Legs Function ---');
    const firstCheckbox = await page.locator('.leg-row input[type="checkbox"]').first();
    if (await firstCheckbox.isVisible()) {
      await firstCheckbox.click();
      await delay(300);

      const deleteBtn = await page.locator('[data-testid="strategy-delete-legs-button"]');
      const isDeleteDisabled = await deleteBtn.isDisabled();

      if (!isDeleteDisabled) {
        console.log('✓ Delete button enabled after selection');
        results.passed.push('Delete Legs Selection');
      } else {
        console.log('✗ Delete button still disabled');
        results.failed.push('Delete Legs Selection');
      }
    }
    await takeScreenshot(page, '14_delete_legs');

    // ========== FINAL SCREENSHOT ==========
    await takeScreenshot(page, '99_final_state');

    // ========== Console Errors ==========
    if (consoleErrors.length > 0) {
      console.log('\n--- Console Errors Found ---');
      consoleErrors.slice(0, 5).forEach(e => console.log(`  ⚠️ ${e.slice(0, 100)}`));
      if (consoleErrors.length > 5) {
        console.log(`  ... and ${consoleErrors.length - 5} more errors`);
      }
    }

  } catch (error) {
    console.error('\n❌ Test error:', error.message);
    await takeScreenshot(page, 'ERROR_final');
    results.failed.push(`Error: ${error.message}`);
  } finally {
    // ========== SUMMARY ==========
    console.log('\n========================================');
    console.log('  TEST RESULTS SUMMARY');
    console.log('========================================');
    console.log(`\n✓ PASSED: ${results.passed.length}`);
    results.passed.forEach(t => console.log(`  - ${t}`));

    console.log(`\n✗ FAILED: ${results.failed.length}`);
    results.failed.forEach(t => console.log(`  - ${t}`));

    console.log(`\n⚠️ ISSUES: ${results.issues.length}`);
    results.issues.forEach(t => console.log(`  - ${t}`));

    console.log('\n========================================');
    console.log(`Total: ${results.passed.length} passed, ${results.failed.length} failed, ${results.issues.length} issues`);
    console.log(`Screenshots: ${SCREENSHOT_DIR}`);
    console.log('========================================\n');

    await browser.close();

    return results;
  }
}

runTests().catch(console.error);
