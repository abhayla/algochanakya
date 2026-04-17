/**
 * Manual Strategy Page E2E Test with Screenshots
 * Tests all features, buttons, dropdowns on the Strategy page
 */

import { chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const FRONTEND_URL = 'http://localhost:5173';
const SCREENSHOT_DIR = './screenshots/strategy-test';
const AUTH_STATE_PATH = './tests/config/.auth-state.json';

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function takeScreenshot(page, name) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filepath = path.join(SCREENSHOT_DIR, `${name}_${timestamp}.png`);
  await page.screenshot({ path: filepath, fullPage: true });
  console.log(`📸 Screenshot saved: ${filepath}`);
  return filepath;
}

async function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runTests() {
  console.log('\n========================================');
  console.log('  STRATEGY PAGE E2E TEST WITH SCREENSHOTS');
  console.log('========================================\n');

  const browser = await chromium.launch({
    headless: false,
    slowMo: 100 // Slow down for visibility
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });

  // Load auth state
  const authState = JSON.parse(fs.readFileSync(AUTH_STATE_PATH, 'utf8'));

  const page = await context.newPage();

  // Inject auth token
  await page.goto(FRONTEND_URL);
  await page.evaluate((localStorage) => {
    localStorage.forEach(item => {
      window.localStorage.setItem(item.name, item.value);
    });
  }, authState.origins[0].localStorage);

  console.log('✓ Auth token injected');

  const results = {
    passed: [],
    failed: []
  };

  try {
    // TEST 1: Page Load
    console.log('\n--- TEST 1: Page Load ---');
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('networkidle');
    await delay(2000);

    const pageVisible = await page.locator('[data-testid="strategy-page"]').isVisible();
    if (pageVisible) {
      console.log('✓ Strategy page loaded successfully');
      results.passed.push('Page Load');
    } else {
      console.log('✗ Strategy page failed to load');
      results.failed.push('Page Load');
    }
    await takeScreenshot(page, '01_page_load');

    // TEST 2: Toolbar Elements
    console.log('\n--- TEST 2: Toolbar Elements ---');
    const toolbar = await page.locator('[data-testid="strategy-toolbar"]').isVisible();
    const underlyingTabs = await page.locator('[data-testid="strategy-underlying-tabs"]').isVisible();

    if (toolbar && underlyingTabs) {
      console.log('✓ Toolbar and underlying tabs visible');
      results.passed.push('Toolbar Elements');
    } else {
      console.log('✗ Toolbar elements missing');
      results.failed.push('Toolbar Elements');
    }
    await takeScreenshot(page, '02_toolbar');

    // TEST 3: Underlying Tab Click (BANKNIFTY)
    console.log('\n--- TEST 3: Click BANKNIFTY Tab ---');
    await page.click('[data-testid="strategy-underlying-banknifty"]');
    await delay(1500);
    const bankniftyActive = await page.locator('[data-testid="strategy-underlying-banknifty"].active').isVisible();
    if (bankniftyActive) {
      console.log('✓ BANKNIFTY tab activated');
      results.passed.push('BANKNIFTY Tab Click');
    } else {
      console.log('✗ BANKNIFTY tab not activated');
      results.failed.push('BANKNIFTY Tab Click');
    }
    await takeScreenshot(page, '03_banknifty_tab');

    // Switch back to NIFTY
    await page.click('[data-testid="strategy-underlying-nifty"]');
    await delay(1000);

    // TEST 4: P/L Mode Toggle
    console.log('\n--- TEST 4: P/L Mode Toggle ---');
    const expiryMode = await page.locator('[data-testid="strategy-pnl-mode-expiry"]').isVisible();
    const currentMode = await page.locator('[data-testid="strategy-pnl-mode-current"]').isVisible();

    if (expiryMode && currentMode) {
      console.log('✓ P/L mode buttons visible');
      await page.click('[data-testid="strategy-pnl-mode-current"]');
      await delay(500);
      console.log('✓ Switched to Current mode');
      results.passed.push('P/L Mode Toggle');
    } else {
      console.log('✗ P/L mode buttons missing');
      results.failed.push('P/L Mode Toggle');
    }
    await takeScreenshot(page, '04_pnl_mode');

    // Switch back to Expiry mode
    await page.click('[data-testid="strategy-pnl-mode-expiry"]');
    await delay(500);

    // TEST 5: Strategy Selector Bar
    console.log('\n--- TEST 5: Strategy Selector Bar ---');
    const selectorBar = await page.locator('[data-testid="strategy-selector-bar"]').isVisible();
    const strategySelect = await page.locator('[data-testid="strategy-selector-saved-select"]').isVisible();
    const strategyTypeSelect = await page.locator('[data-testid="strategy-type-select"]').isVisible();

    if (selectorBar && strategySelect && strategyTypeSelect) {
      console.log('✓ Strategy selector bar elements visible');
      results.passed.push('Strategy Selector Bar');
    } else {
      console.log('✗ Strategy selector bar elements missing');
      results.failed.push('Strategy Selector Bar');
    }
    await takeScreenshot(page, '05_selector_bar');

    // TEST 6: Strategy Type Dropdown
    console.log('\n--- TEST 6: Strategy Type Dropdown ---');
    await page.click('[data-testid="strategy-type-select"]');
    await delay(500);
    await takeScreenshot(page, '06_strategy_type_dropdown');

    // Select Iron Condor
    await page.selectOption('[data-testid="strategy-type-select"]', 'iron_condor');
    await delay(2000);
    console.log('✓ Selected Iron Condor strategy type');
    results.passed.push('Strategy Type Dropdown');
    await takeScreenshot(page, '07_iron_condor_selected');

    // TEST 7: Check if legs were auto-populated
    console.log('\n--- TEST 7: Auto-populated Legs ---');
    await delay(2000);
    const legRows = await page.locator('.leg-row').count();
    console.log(`Found ${legRows} leg rows`);

    if (legRows >= 4) {
      console.log('✓ Iron Condor legs auto-populated (4 legs expected)');
      results.passed.push('Auto-populated Legs');
    } else {
      console.log('✗ Legs not auto-populated correctly');
      results.failed.push('Auto-populated Legs');
    }
    await takeScreenshot(page, '08_legs_populated');

    // TEST 8: Strategy Table
    console.log('\n--- TEST 8: Strategy Table ---');
    const table = await page.locator('[data-testid="strategy-table"]').isVisible();
    const tableWrapper = await page.locator('[data-testid="strategy-table-wrapper"]').isVisible();

    if (table && tableWrapper) {
      console.log('✓ Strategy table visible');
      results.passed.push('Strategy Table');
    } else {
      console.log('✗ Strategy table missing');
      results.failed.push('Strategy Table');
    }
    await takeScreenshot(page, '09_strategy_table');

    // TEST 9: Add Row Button
    console.log('\n--- TEST 9: Add Row Button ---');
    const addRowBtn = await page.locator('[data-testid="strategy-add-row-button"]').isVisible();
    if (addRowBtn) {
      const initialRows = await page.locator('.leg-row').count();
      await page.click('[data-testid="strategy-add-row-button"]');
      await delay(1500);
      const newRows = await page.locator('.leg-row').count();

      if (newRows > initialRows) {
        console.log(`✓ Add Row works (${initialRows} -> ${newRows} rows)`);
        results.passed.push('Add Row Button');
      } else {
        console.log('✗ Add Row did not add a new row');
        results.failed.push('Add Row Button');
      }
    } else {
      console.log('✗ Add Row button not visible');
      results.failed.push('Add Row Button');
    }
    await takeScreenshot(page, '10_add_row');

    // TEST 10: ReCalculate Button
    console.log('\n--- TEST 10: ReCalculate Button ---');
    const recalcBtn = await page.locator('[data-testid="strategy-recalculate-button"]').isVisible();
    if (recalcBtn) {
      await page.click('[data-testid="strategy-recalculate-button"]');
      await delay(3000);
      console.log('✓ ReCalculate button clicked');
      results.passed.push('ReCalculate Button');
    } else {
      console.log('✗ ReCalculate button not visible');
      results.failed.push('ReCalculate Button');
    }
    await takeScreenshot(page, '11_recalculate');

    // TEST 11: Summary Cards
    console.log('\n--- TEST 11: Summary Cards ---');
    const maxProfitCard = await page.locator('[data-testid="strategy-max-profit-card"]').isVisible();
    const maxLossCard = await page.locator('[data-testid="strategy-max-loss-card"]').isVisible();
    const breakevenCard = await page.locator('[data-testid="strategy-breakeven-card"]').isVisible();
    const spotCard = await page.locator('[data-testid="strategy-spot-card"]').isVisible();

    if (maxProfitCard && maxLossCard && breakevenCard && spotCard) {
      console.log('✓ All summary cards visible');
      results.passed.push('Summary Cards');
    } else {
      console.log('✗ Some summary cards missing');
      console.log(`  Max Profit: ${maxProfitCard}, Max Loss: ${maxLossCard}, Breakeven: ${breakevenCard}, Spot: ${spotCard}`);
      results.failed.push('Summary Cards');
    }
    await takeScreenshot(page, '12_summary_cards');

    // TEST 12: Payoff Section
    console.log('\n--- TEST 12: Payoff Chart ---');
    const payoffSection = await page.locator('[data-testid="strategy-payoff-section"]').isVisible();
    if (payoffSection) {
      console.log('✓ Payoff chart section visible');
      results.passed.push('Payoff Chart');
    } else {
      console.log('✗ Payoff chart section not visible');
      results.failed.push('Payoff Chart');
    }
    await takeScreenshot(page, '13_payoff_chart');

    // TEST 13: Action Bar Buttons
    console.log('\n--- TEST 13: Action Bar ---');
    const actionBar = await page.locator('[data-testid="strategy-action-bar"]').isVisible();
    const deleteLegsBtn = await page.locator('[data-testid="strategy-delete-legs-button"]').isVisible();
    const basketOrderBtn = await page.locator('[data-testid="strategy-basket-order-button"]').isVisible();

    if (actionBar && deleteLegsBtn && basketOrderBtn) {
      console.log('✓ Action bar buttons visible');
      results.passed.push('Action Bar');
    } else {
      console.log('✗ Action bar buttons missing');
      results.failed.push('Action Bar');
    }
    await takeScreenshot(page, '14_action_bar');

    // TEST 14: Save Button (with name)
    console.log('\n--- TEST 14: Save Strategy ---');
    await page.fill('[data-testid="strategy-name-input"]', 'Test Iron Condor');
    await delay(500);
    const saveBtn = await page.locator('[data-testid="strategy-save-button"]');
    const isDisabled = await saveBtn.isDisabled();

    if (!isDisabled) {
      console.log('✓ Save button enabled with strategy name');
      results.passed.push('Save Button');
    } else {
      console.log('✗ Save button still disabled');
      results.failed.push('Save Button');
    }
    await takeScreenshot(page, '15_save_button');

    // TEST 15: Leg Field Editing
    console.log('\n--- TEST 15: Leg Field Editing ---');
    const firstLegExpiry = await page.locator('.leg-row select').first();
    if (await firstLegExpiry.isVisible()) {
      await firstLegExpiry.click();
      await delay(500);
      console.log('✓ Leg dropdown is clickable');
      results.passed.push('Leg Field Editing');
    } else {
      console.log('✗ Leg dropdowns not accessible');
      results.failed.push('Leg Field Editing');
    }
    await takeScreenshot(page, '16_leg_editing');

    // TEST 16: Delete Selected Legs
    console.log('\n--- TEST 16: Delete Legs ---');
    // Select first leg checkbox
    const firstCheckbox = await page.locator('.leg-row input[type="checkbox"]').first();
    if (await firstCheckbox.isVisible()) {
      await firstCheckbox.click();
      await delay(500);

      const deleteBtn = await page.locator('[data-testid="strategy-delete-legs-button"]');
      const deleteBtnDisabled = await deleteBtn.isDisabled();

      if (!deleteBtnDisabled) {
        console.log('✓ Delete button enabled after selecting leg');
        results.passed.push('Delete Legs');
      } else {
        console.log('✗ Delete button still disabled after selecting leg');
        results.failed.push('Delete Legs');
      }
    } else {
      console.log('✗ Leg checkboxes not visible');
      results.failed.push('Delete Legs');
    }
    await takeScreenshot(page, '17_delete_legs');

    // TEST 17: Total Row
    console.log('\n--- TEST 17: Total Row ---');
    const totalRow = await page.locator('[data-testid="strategy-total-row"]').isVisible();
    if (totalRow) {
      console.log('✓ Total row visible');
      results.passed.push('Total Row');
    } else {
      console.log('✗ Total row not visible');
      results.failed.push('Total Row');
    }
    await takeScreenshot(page, '18_total_row');

    // FINAL SCREENSHOT - Full page state
    console.log('\n--- FINAL STATE ---');
    await takeScreenshot(page, '99_final_state');

  } catch (error) {
    console.error('\n❌ Test error:', error.message);
    await takeScreenshot(page, 'ERROR_state');
    results.failed.push(`Error: ${error.message}`);
  } finally {
    // Print Summary
    console.log('\n========================================');
    console.log('  TEST RESULTS SUMMARY');
    console.log('========================================');
    console.log(`\n✓ PASSED: ${results.passed.length}`);
    results.passed.forEach(t => console.log(`  - ${t}`));
    console.log(`\n✗ FAILED: ${results.failed.length}`);
    results.failed.forEach(t => console.log(`  - ${t}`));
    console.log('\n========================================');
    console.log(`Screenshots saved to: ${SCREENSHOT_DIR}`);
    console.log('========================================\n');

    await browser.close();

    return results;
  }
}

runTests().catch(console.error);
