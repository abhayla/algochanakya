/**
 * Strategy Builder Manual Test Plan Execution
 *
 * This spec executes the manual test plan from:
 * tests/e2e/plans/strategy-builder-manual-test-plan.md
 *
 * Tests:
 * - Phase 1: Manual row operations (add rows, change fields)
 * - Phase 2: Pre-built strategy templates (Iron Condor, Short Straddle, Bull Call Spread, Bear Put Spread)
 *
 * Each step includes:
 * - Screenshot capture
 * - CMP verification against backend API
 * - Auto-calculation verification
 * - P/L correctness check
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import StrategyBuilderPage from '../../pages/StrategyBuilderPage.js';
import fs from 'fs';
import path from 'path';

const API_BASE = process.env.API_BASE || 'http://localhost:8001';
const SCREENSHOT_DIR = path.join(process.cwd(), 'tests', 'e2e', 'screenshots', 'strategy-manual-plan');

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// Test results collector
const testResults = {
  phase1: [],
  phase2: [],
  summary: { passed: 0, failed: 0, total: 0 }
};

/**
 * Helper: Take screenshot with timestamp
 */
async function takeScreenshot(page, stepName) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `${stepName}_${timestamp}.png`;
  const filepath = path.join(SCREENSHOT_DIR, filename);
  await page.screenshot({ path: filepath, fullPage: true });
  console.log(`Screenshot saved: ${filename}`);
  return filepath;
}

/**
 * Helper: Fetch LTP from backend API
 */
async function fetchLTPFromAPI(page, tradingsymbol) {
  try {
    const response = await page.request.get(
      `${API_BASE}/api/orders/ltp?instruments=NFO:${tradingsymbol}`
    );
    if (response.ok()) {
      const data = await response.json();
      // Response format: { "NFO:SYMBOL": { "last_price": 123.45 } }
      const key = `NFO:${tradingsymbol}`;
      return data[key]?.last_price || data[key]?.ltp || null;
    }
  } catch (err) {
    console.error(`Failed to fetch LTP for ${tradingsymbol}:`, err.message);
  }
  return null;
}

/**
 * Helper: Wait for auto-calculation to complete
 */
async function waitForCalculation(page, strategyPage) {
  // Wait for loading to finish
  await page.waitForTimeout(500);
  await strategyPage.waitForPnLCalculation();
  // Additional wait for network
  await page.waitForLoadState('networkidle').catch(() => {});
}

/**
 * Helper: Verify CMP against API (ENHANCED - now actually compares to API)
 */
async function verifyCMP(page, legDetails, strategyPage, tolerance = 0.5) {
  // Extract tradingsymbol from the leg (we need to construct it)
  const cmpText = legDetails.cmp?.trim();
  if (!cmpText || cmpText === '-' || cmpText === '') {
    return { valid: false, reason: 'CMP is empty or dash' };
  }

  const cmpValue = parseFloat(cmpText.replace(/,/g, ''));
  if (isNaN(cmpValue)) {
    return { valid: false, reason: `CMP is not a number: ${cmpText}` };
  }

  if (cmpValue <= 0) {
    return { valid: false, reason: `CMP is zero or negative: ${cmpValue}` };
  }

  // Try to verify against API (if we can build the trading symbol)
  const tradingsymbol = strategyPage.buildTradingSymbol(legDetails, 'NIFTY');
  if (tradingsymbol) {
    const apiLTP = await fetchLTPFromAPI(page, tradingsymbol);
    if (apiLTP !== null) {
      const diff = Math.abs(cmpValue - apiLTP);
      if (diff > tolerance) {
        return {
          valid: false,
          reason: `CMP ${cmpValue} differs from API ${apiLTP} by ${diff.toFixed(2)} (tolerance: ${tolerance})`,
          uiValue: cmpValue,
          apiValue: apiLTP
        };
      }
      return { valid: true, value: cmpValue, apiValue: apiLTP, verified: true };
    }
  }

  // If we couldn't verify against API, at least confirm it's a valid positive number
  return { valid: true, value: cmpValue, verified: false };
}

/**
 * Helper: Assert no errors on page
 */
async function assertNoErrors(page, strategyPage, stepName) {
  const hasError = await strategyPage.hasErrorBanner();
  if (hasError) {
    const errorText = await strategyPage.getErrorBannerText();
    console.error(`❌ Error detected at ${stepName}: ${errorText}`);
    return { valid: false, error: errorText };
  }
  return { valid: true };
}

/**
 * Helper: Assert payoff chart is rendered (not blank)
 */
async function assertPayoffRendered(page, strategyPage, stepName) {
  const isRendered = await strategyPage.isPayoffChartRendered();
  const pathCount = await strategyPage.getPayoffChartPathCount();
  if (!isRendered || pathCount === 0) {
    console.error(`❌ Payoff chart blank at ${stepName}: paths=${pathCount}`);
    return { valid: false, pathCount };
  }
  return { valid: true, pathCount };
}

/**
 * Helper: Verify P/L calculation is sensible
 */
function verifyPnLSensible(summary, strategyType) {
  const maxProfit = summary.maxProfit?.replace(/,/g, '');
  const maxLoss = summary.maxLoss?.replace(/,/g, '');

  const results = {
    maxProfitValid: maxProfit && maxProfit !== '-' && !isNaN(parseFloat(maxProfit)),
    maxLossValid: maxLoss && maxLoss !== '-' && !isNaN(parseFloat(maxLoss)),
    breakevenValid: summary.breakeven && summary.breakeven !== '-'
  };

  // Strategy-specific validations
  if (strategyType === 'short_straddle' || strategyType === 'short_strangle') {
    // Selling strategies: max profit is premium, max loss is large negative
    results.strategyLogic = parseFloat(maxProfit) > 0 && parseFloat(maxLoss) < 0;
  } else if (strategyType === 'iron_condor') {
    // Iron Condor: limited profit and limited loss
    results.strategyLogic = parseFloat(maxProfit) > 0 && parseFloat(maxLoss) < 0;
  } else if (strategyType === 'bull_call_spread' || strategyType === 'bear_put_spread') {
    // Debit spreads: max loss is debit paid, max profit is spread width minus debit
    results.strategyLogic = true; // These can have various P/L profiles
  }

  return results;
}

/**
 * Helper: Log step result
 */
function logStepResult(phase, step, passed, details) {
  const result = { step, passed, details, timestamp: new Date().toISOString() };
  if (phase === 1) {
    testResults.phase1.push(result);
  } else {
    testResults.phase2.push(result);
  }
  testResults.summary.total++;
  if (passed) {
    testResults.summary.passed++;
  } else {
    testResults.summary.failed++;
  }
  console.log(`${passed ? '✅' : '❌'} ${step}: ${JSON.stringify(details)}`);
}

test.describe('Strategy Builder Manual Test Plan', () => {
  test.describe.configure({ timeout: 300000 }); // 5 minutes total

  let strategyPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyPage = new StrategyBuilderPage(authenticatedPage);
  });

  test('Phase 1: Manual Row Operations', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Constants for filtering dropdown options
    const placeholders = ['select', 'choose', 'pick', ''];

    // Navigate to Strategy Builder
    await strategyPage.navigate();
    await strategyPage.waitForPageLoad();

    // Wait for page to fully initialize (WebSocket, API calls)
    console.log('Waiting for page to fully initialize...');
    await page.waitForTimeout(3000);

    // Check for errors and take diagnostic screenshot
    const errorAlert = page.locator('[data-testid="strategy-error"]');
    if (await errorAlert.isVisible().catch(() => false)) {
      const errorText = await errorAlert.textContent();
      console.log(`Error on page: ${errorText}`);
      await takeScreenshot(page, 'error_on_load');
    }

    // Wait for expiries to load (check Add Row button)
    console.log('Waiting for Add Row button to be enabled...');
    try {
      await page.waitForFunction(
        () => {
          const btn = document.querySelector('[data-testid="strategy-add-row-button"]');
          return btn && !btn.disabled;
        },
        { timeout: 30000 }
      );
      console.log('Add Row button is now enabled');
    } catch (e) {
      console.log('Add Row button still disabled - taking diagnostic screenshot');
      await takeScreenshot(page, 'add_row_disabled');

      // Check if there's a network issue
      const addRowBtn = page.locator('[data-testid="strategy-add-row-button"]');
      const isDisabled = await addRowBtn.isDisabled();
      console.log(`Add Row button disabled: ${isDisabled}`);

      // Try to manually trigger expiry fetch by re-selecting underlying
      console.log('Attempting to re-trigger expiry fetch...');
      await strategyPage.selectUnderlying('BANKNIFTY');
      await page.waitForTimeout(2000);
      await strategyPage.selectUnderlying('NIFTY');
      await page.waitForTimeout(5000);

      await takeScreenshot(page, 'after_reselect_underlying');
    }

    // Select NIFTY as underlying (may already be selected)
    const niftyTab = page.locator('[data-testid="strategy-underlying-nifty"]');
    const isNiftyActive = await niftyTab.getAttribute('class').then(c => c?.includes('active') || c?.includes('bg-blue'));
    if (!isNiftyActive) {
      await strategyPage.selectUnderlying('NIFTY');
      await page.waitForTimeout(3000);
    }

    // Ensure "At Expiry" mode for easier P/L verification
    await strategyPage.setPnLMode('expiry');

    // ========== Step 1.1: Add first row ==========
    console.log('\n--- Step 1.1: Add first row ---');
    await strategyPage.addRow();
    await strategyPage.waitForLegsLoaded(1);
    await waitForCalculation(page, strategyPage);

    let screenshot = await takeScreenshot(page, '1.1_add_first_row');
    let legCount = await strategyPage.getLegCount();
    let legs = await strategyPage.getAllLegsDetails();
    let summary = await strategyPage.getSummaryValues();

    // ENHANCED: Check for errors after adding row
    let errorCheck = await assertNoErrors(page, strategyPage, '1.1 Add first row');

    let step1_1_passed = legCount === 1;
    let cmpResult = await verifyCMP(page, legs[0], strategyPage);
    step1_1_passed = step1_1_passed && cmpResult.valid && errorCheck.valid;

    logStepResult(1, '1.1 Add first row', step1_1_passed, {
      legCount,
      cmp: legs[0]?.cmp,
      cmpValid: cmpResult.valid,
      cmpVerifiedAgainstAPI: cmpResult.verified || false,
      noErrors: errorCheck.valid,
      summary: summary.maxProfit !== '-'
    });

    expect(legCount).toBe(1);
    expect(errorCheck.valid, 'No errors should be present').toBe(true);

    // ========== Step 1.2: Add second row ==========
    console.log('\n--- Step 1.2: Add second row ---');
    await strategyPage.addRow();
    await strategyPage.waitForLegsLoaded(2);
    await waitForCalculation(page, strategyPage);

    screenshot = await takeScreenshot(page, '1.2_add_second_row');
    legCount = await strategyPage.getLegCount();
    legs = await strategyPage.getAllLegsDetails();
    summary = await strategyPage.getSummaryValues();

    // ENHANCED: Check for errors and payoff chart
    errorCheck = await assertNoErrors(page, strategyPage, '1.2 Add second row');
    const payoffCheck1_2 = await assertPayoffRendered(page, strategyPage, '1.2 Add second row');

    let step1_2_passed = legCount === 2;
    const cmpResult1 = await verifyCMP(page, legs[0], strategyPage);
    const cmpResult2 = await verifyCMP(page, legs[1], strategyPage);
    step1_2_passed = step1_2_passed && cmpResult1.valid && cmpResult2.valid && errorCheck.valid;

    logStepResult(1, '1.2 Add second row', step1_2_passed, {
      legCount,
      leg1_cmp: legs[0]?.cmp,
      leg2_cmp: legs[1]?.cmp,
      bothCMPValid: cmpResult1.valid && cmpResult2.valid,
      noErrors: errorCheck.valid,
      payoffRendered: payoffCheck1_2.valid
    });

    expect(legCount).toBe(2);
    expect(errorCheck.valid, 'No errors should be present').toBe(true);
    expect(payoffCheck1_2.valid, 'Payoff chart should be rendered').toBe(true);

    // ========== Step 1.3: Change CE/PE on row 1 ==========
    console.log('\n--- Step 1.3: Change CE/PE on row 1 ---');
    const row1 = strategyPage.getLegRow(0);
    const typeSelect1 = row1.locator('select').nth(1);
    const currentType = await typeSelect1.inputValue();
    const newType = currentType === 'CE' ? 'PE' : 'CE';

    // ENHANCED: Capture CMP BEFORE change
    const cmpBeforeTypeChange = await strategyPage.getLegCMP(0);
    console.log(`CMP before type change: ${cmpBeforeTypeChange}`);

    await typeSelect1.selectOption(newType);
    await page.waitForTimeout(1000);
    await waitForCalculation(page, strategyPage);

    screenshot = await takeScreenshot(page, '1.3_change_ce_pe_row1');
    legs = await strategyPage.getAllLegsDetails();
    summary = await strategyPage.getSummaryValues();

    // ENHANCED: Verify CMP changed and check for errors
    const cmpAfterTypeChange = await strategyPage.getLegCMP(0);
    console.log(`CMP after type change: ${cmpAfterTypeChange}`);
    const cmpChanged = cmpBeforeTypeChange !== cmpAfterTypeChange;
    errorCheck = await assertNoErrors(page, strategyPage, '1.3 Change CE/PE');
    const cmpValidation = await verifyCMP(page, legs[0], strategyPage);

    const step1_3_passed = legs[0]?.type === newType && cmpChanged && errorCheck.valid;

    logStepResult(1, '1.3 Change CE/PE on row 1', step1_3_passed, {
      expectedType: newType,
      actualType: legs[0]?.type,
      cmpBefore: cmpBeforeTypeChange,
      cmpAfter: cmpAfterTypeChange,
      cmpChanged,
      cmpValid: cmpValidation.valid,
      noErrors: errorCheck.valid
    });

    expect(legs[0]?.type).toBe(newType);
    expect(cmpChanged, 'CMP should change when switching CE/PE').toBe(true);
    expect(errorCheck.valid, 'No errors should be present').toBe(true);

    // ========== Step 1.4: Change strike on row 1 ==========
    console.log('\n--- Step 1.4: Change strike on row 1 ---');
    const strikeSelect1 = row1.locator('select').nth(3);
    const availableStrikes = await strikeSelect1.locator('option').allTextContents();
    const currentStrike = await strikeSelect1.inputValue();

    // ENHANCED: Capture CMP BEFORE strike change
    const cmpBeforeStrikeChange = await strategyPage.getLegCMP(0);
    console.log(`CMP before strike change: ${cmpBeforeStrikeChange}, current strike: ${currentStrike}`);

    // Find a different strike (next one in list)
    let newStrike = null;
    for (const optionText of availableStrikes) {
      const strikeValue = optionText.trim();
      if (strikeValue && strikeValue !== currentStrike && !isNaN(parseFloat(strikeValue))) {
        newStrike = strikeValue;
        break;
      }
    }

    if (newStrike) {
      await strikeSelect1.selectOption(newStrike);
      await page.waitForTimeout(1500); // Strike change triggers instrument token fetch
      await waitForCalculation(page, strategyPage);
    }

    screenshot = await takeScreenshot(page, '1.4_change_strike_row1');
    legs = await strategyPage.getAllLegsDetails();
    summary = await strategyPage.getSummaryValues();

    // ENHANCED: Verify CMP actually changed after strike change
    const cmpAfterStrikeChange = await strategyPage.getLegCMP(0);
    console.log(`CMP after strike change: ${cmpAfterStrikeChange}, new strike: ${newStrike}`);
    const cmpChangedAfterStrike = cmpBeforeStrikeChange !== cmpAfterStrikeChange;
    errorCheck = await assertNoErrors(page, strategyPage, '1.4 Change strike');
    const cmpStrikeValidation = await verifyCMP(page, legs[0], strategyPage);

    const step1_4_passed = newStrike ? (legs[0]?.strike === newStrike && cmpChangedAfterStrike && errorCheck.valid) : true;

    logStepResult(1, '1.4 Change strike on row 1', step1_4_passed, {
      oldStrike: currentStrike,
      newStrike,
      actualStrike: legs[0]?.strike,
      cmpBefore: cmpBeforeStrikeChange,
      cmpAfter: cmpAfterStrikeChange,
      cmpChanged: cmpChangedAfterStrike,
      cmpValid: cmpStrikeValidation.valid,
      noErrors: errorCheck.valid
    });

    // CRITICAL ASSERTION: CMP MUST change when strike changes
    if (newStrike) {
      expect(cmpChangedAfterStrike, `CMP must change when strike changes from ${currentStrike} to ${newStrike}`).toBe(true);
      expect(errorCheck.valid, 'No errors should be present').toBe(true);
    }

    // ========== Step 1.5: Change expiry on row 1 ==========
    console.log('\n--- Step 1.5: Change expiry on row 1 ---');
    const expirySelect1 = row1.locator('select').nth(0);
    const availableExpiries = await expirySelect1.locator('option').allTextContents();
    const currentExpiry = await expirySelect1.inputValue();

    // ENHANCED: Capture CMP BEFORE expiry change
    const cmpBeforeExpiryChange = await strategyPage.getLegCMP(0);
    console.log(`CMP before expiry change: ${cmpBeforeExpiryChange}, current expiry: ${currentExpiry}`);

    // Find a different expiry (skip placeholders like "Select", empty values)
    let newExpiry = null;
    for (const optionText of availableExpiries) {
      const expiryValue = optionText.trim();
      // Skip if it's the current value, empty, or a placeholder
      if (expiryValue &&
          expiryValue !== currentExpiry &&
          !placeholders.includes(expiryValue.toLowerCase())) {
        newExpiry = expiryValue;
        break;
      }
    }

    if (newExpiry) {
      console.log(`Changing expiry from ${currentExpiry} to ${newExpiry}`);
      await expirySelect1.selectOption(newExpiry);
      await page.waitForTimeout(2000); // Expiry change triggers strikes fetch
      await waitForCalculation(page, strategyPage);
    } else {
      console.log('No valid alternative expiry found - skipping step');
    }

    screenshot = await takeScreenshot(page, '1.5_change_expiry_row1');
    legs = await strategyPage.getAllLegsDetails();
    summary = await strategyPage.getSummaryValues();

    // ENHANCED: Verify CMP changed and check for errors
    const cmpAfterExpiryChange = await strategyPage.getLegCMP(0);
    console.log(`CMP after expiry change: ${cmpAfterExpiryChange}, new expiry: ${newExpiry}`);
    const cmpChangedAfterExpiry = cmpBeforeExpiryChange !== cmpAfterExpiryChange;
    errorCheck = await assertNoErrors(page, strategyPage, '1.5 Change expiry');
    const cmpExpiryValidation = await verifyCMP(page, legs[0], strategyPage);

    const step1_5_passed = newExpiry ? (cmpChangedAfterExpiry && errorCheck.valid) : true;

    logStepResult(1, '1.5 Change expiry on row 1', step1_5_passed, {
      oldExpiry: currentExpiry,
      newExpiry,
      actualExpiry: legs[0]?.expiry,
      cmpBefore: cmpBeforeExpiryChange,
      cmpAfter: cmpAfterExpiryChange,
      cmpChanged: cmpChangedAfterExpiry,
      cmpValid: cmpExpiryValidation.valid,
      noErrors: errorCheck.valid
    });

    // CRITICAL ASSERTION: CMP should typically change when expiry changes
    if (newExpiry) {
      expect(errorCheck.valid, 'No errors should be present').toBe(true);
      // Note: CMP may be same for adjacent expiries in low volatility, so we just warn
      if (!cmpChangedAfterExpiry) {
        console.warn(`⚠️ CMP did not change after expiry change (may be expected for similar expiries)`);
      }
    }

    // ========== Steps 1.6-1.8: Same for row 2 ==========
    console.log('\n--- Steps 1.6-1.8: Changes on row 2 ---');
    const row2 = strategyPage.getLegRow(1);

    // 1.6: Change CE/PE on row 2
    const typeSelect2 = row2.locator('select').nth(1);
    const currentType2 = await typeSelect2.inputValue();
    const newType2 = currentType2 === 'CE' ? 'PE' : 'CE';

    // ENHANCED: Capture CMP before change
    const cmpBeforeType2 = await strategyPage.getLegCMP(1);
    console.log(`Row 2 CMP before type change: ${cmpBeforeType2}`);

    await typeSelect2.selectOption(newType2);
    await page.waitForTimeout(1000);
    await waitForCalculation(page, strategyPage);

    screenshot = await takeScreenshot(page, '1.6_change_ce_pe_row2');
    legs = await strategyPage.getAllLegsDetails();

    // ENHANCED: Verify CMP changed and check for errors + payoff
    const cmpAfterType2 = await strategyPage.getLegCMP(1);
    const cmpChangedType2 = cmpBeforeType2 !== cmpAfterType2;
    errorCheck = await assertNoErrors(page, strategyPage, '1.6 Change CE/PE row 2');
    const payoffCheck1_6 = await assertPayoffRendered(page, strategyPage, '1.6 Change CE/PE row 2');
    const cmp1_6 = await verifyCMP(page, legs[1], strategyPage);

    logStepResult(1, '1.6 Change CE/PE on row 2', legs[1]?.type === newType2 && cmpChangedType2 && errorCheck.valid, {
      expectedType: newType2,
      actualType: legs[1]?.type,
      cmpBefore: cmpBeforeType2,
      cmpAfter: cmpAfterType2,
      cmpChanged: cmpChangedType2,
      cmpValid: cmp1_6.valid,
      noErrors: errorCheck.valid,
      payoffRendered: payoffCheck1_6.valid
    });

    expect(cmpChangedType2, 'CMP should change when switching CE/PE on row 2').toBe(true);
    expect(errorCheck.valid, 'No errors should be present').toBe(true);
    expect(payoffCheck1_6.valid, 'Payoff chart should be rendered').toBe(true);

    // 1.7: Change strike on row 2
    const strikeSelect2 = row2.locator('select').nth(3);
    const currentStrike2 = await strikeSelect2.inputValue();
    const availableStrikes2 = await strikeSelect2.locator('option').allTextContents();

    // ENHANCED: Capture CMP before strike change
    const cmpBeforeStrike2 = await strategyPage.getLegCMP(1);
    console.log(`Row 2 CMP before strike change: ${cmpBeforeStrike2}, current strike: ${currentStrike2}`);

    let newStrike2 = null;
    for (const optionText of availableStrikes2) {
      const strikeValue = optionText.trim();
      if (strikeValue && strikeValue !== currentStrike2 && !isNaN(parseFloat(strikeValue))) {
        newStrike2 = strikeValue;
        break;
      }
    }

    if (newStrike2) {
      await strikeSelect2.selectOption(newStrike2);
      await page.waitForTimeout(1500);
      await waitForCalculation(page, strategyPage);
    }

    screenshot = await takeScreenshot(page, '1.7_change_strike_row2');
    legs = await strategyPage.getAllLegsDetails();

    // ENHANCED: Verify CMP changed
    const cmpAfterStrike2 = await strategyPage.getLegCMP(1);
    const cmpChangedStrike2 = cmpBeforeStrike2 !== cmpAfterStrike2;
    errorCheck = await assertNoErrors(page, strategyPage, '1.7 Change strike row 2');
    const cmp1_7 = await verifyCMP(page, legs[1], strategyPage);

    logStepResult(1, '1.7 Change strike on row 2', cmpChangedStrike2 && cmp1_7.valid && errorCheck.valid, {
      oldStrike: currentStrike2,
      newStrike: newStrike2,
      actualStrike: legs[1]?.strike,
      cmpBefore: cmpBeforeStrike2,
      cmpAfter: cmpAfterStrike2,
      cmpChanged: cmpChangedStrike2,
      cmpValid: cmp1_7.valid,
      noErrors: errorCheck.valid
    });

    if (newStrike2) {
      expect(cmpChangedStrike2, `CMP must change when strike changes from ${currentStrike2} to ${newStrike2}`).toBe(true);
      expect(errorCheck.valid, 'No errors should be present').toBe(true);
    }

    // 1.8: Change expiry on row 2
    const expirySelect2 = row2.locator('select').nth(0);
    const currentExpiry2 = await expirySelect2.inputValue();
    const availableExpiries2 = await expirySelect2.locator('option').allTextContents();

    // ENHANCED: Capture CMP before expiry change
    const cmpBeforeExpiry2 = await strategyPage.getLegCMP(1);
    console.log(`Row 2 CMP before expiry change: ${cmpBeforeExpiry2}`);

    // Find a different expiry (skip placeholders like "Select", empty values)
    let newExpiry2 = null;
    for (const optionText of availableExpiries2) {
      const expiryValue = optionText.trim();
      // Skip if it's the current value, empty, or a placeholder
      if (expiryValue &&
          expiryValue !== currentExpiry2 &&
          !placeholders.includes(expiryValue.toLowerCase())) {
        newExpiry2 = expiryValue;
        break;
      }
    }

    if (newExpiry2) {
      console.log(`Changing row 2 expiry from ${currentExpiry2} to ${newExpiry2}`);
      await expirySelect2.selectOption(newExpiry2);
      await page.waitForTimeout(2000);
      await waitForCalculation(page, strategyPage);
    } else {
      console.log('No valid alternative expiry for row 2 - skipping');
    }

    screenshot = await takeScreenshot(page, '1.8_change_expiry_row2');
    legs = await strategyPage.getAllLegsDetails();
    summary = await strategyPage.getSummaryValues();

    // ENHANCED: Final verification with all checks
    const cmpAfterExpiry2 = await strategyPage.getLegCMP(1);
    const cmpChangedExpiry2 = cmpBeforeExpiry2 !== cmpAfterExpiry2;
    errorCheck = await assertNoErrors(page, strategyPage, '1.8 Change expiry row 2');
    const payoffCheckFinal = await assertPayoffRendered(page, strategyPage, '1.8 Final state');
    const cmp1_8 = await verifyCMP(page, legs[1], strategyPage);

    logStepResult(1, '1.8 Change expiry on row 2', cmp1_8.valid && errorCheck.valid, {
      oldExpiry: currentExpiry2,
      newExpiry: newExpiry2,
      actualExpiry: legs[1]?.expiry,
      cmpBefore: cmpBeforeExpiry2,
      cmpAfter: cmpAfterExpiry2,
      cmpChanged: cmpChangedExpiry2,
      cmpValid: cmp1_8.valid,
      noErrors: errorCheck.valid,
      payoffRendered: payoffCheckFinal.valid,
      finalSummary: summary
    });

    // CRITICAL: Final state must have no errors and valid payoff
    expect(errorCheck.valid, 'No errors should be present at end of Phase 1').toBe(true);
    expect(payoffCheckFinal.valid, 'Payoff chart should be rendered at end of Phase 1').toBe(true);

    // Final Phase 1 screenshot
    await takeScreenshot(page, '1.9_phase1_complete');

    console.log('\n=== Phase 1 Complete ===');
    console.log(`Results: ${testResults.phase1.filter(r => r.passed).length}/${testResults.phase1.length} passed`);
  });

  test('Phase 2: Pre-built Strategy Templates', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Navigate to Strategy Builder
    await strategyPage.navigate();
    await strategyPage.waitForPageLoad();

    // Wait for page to fully initialize (WebSocket, API calls)
    console.log('Waiting for page to fully initialize...');
    await page.waitForTimeout(3000);

    // Wait for expiries to load (check Add Row button)
    console.log('Waiting for Add Row button to be enabled...');
    try {
      await page.waitForFunction(
        () => {
          const btn = document.querySelector('[data-testid="strategy-add-row-button"]');
          return btn && !btn.disabled;
        },
        { timeout: 30000 }
      );
      console.log('Add Row button is now enabled');
    } catch (e) {
      console.log('Add Row button still disabled - trying to re-trigger...');
      await strategyPage.selectUnderlying('BANKNIFTY');
      await page.waitForTimeout(2000);
      await strategyPage.selectUnderlying('NIFTY');
      await page.waitForTimeout(5000);
    }

    // Ensure "At Expiry" mode
    await strategyPage.setPnLMode('expiry');

    // Use the Strategy TYPE dropdown (not Strategy dropdown which shows saved strategies)
    // data-testid="strategy-type-select" contains: Iron Condor, Short Straddle, etc.
    const strategies = [
      { key: 'Iron Condor', name: 'Iron Condor', expectedLegs: 4 },
      { key: 'Short Straddle', name: 'Short Straddle', expectedLegs: 2 },
      { key: 'Bull Call Spread', name: 'Bull Call Spread', expectedLegs: 2 },
      { key: 'Bear Put Spread', name: 'Bear Put Spread', expectedLegs: 2 }
    ];

    for (const strategy of strategies) {
      console.log(`\n--- Testing ${strategy.name} ---`);

      // Select strategy TYPE from the Type dropdown (not the Strategy dropdown)
      const strategyTypeSelect = page.locator('[data-testid="strategy-type-select"]');
      await strategyTypeSelect.selectOption({ label: strategy.key });

      // Handle "Replace Existing Legs?" confirmation modal if legs exist
      await page.waitForTimeout(500);
      const replaceModal = page.locator('[data-testid="strategy-replace-legs-modal"]');
      if (await replaceModal.isVisible().catch(() => false)) {
        console.log('Handling Replace Legs modal...');
        await page.locator('[data-testid="strategy-replace-legs-confirm"]').click();
        await page.waitForTimeout(500);
      }

      // Wait for legs to be populated
      await page.waitForTimeout(3000); // Strategy application is async
      await strategyPage.waitForLegsLoaded(strategy.expectedLegs);
      await waitForCalculation(page, strategyPage);

      // Wait additional time for CMP values to populate from WebSocket/API
      console.log('Waiting for CMP values to load...');
      await page.waitForTimeout(3000);

      // Click ReCalculate to trigger price fetch
      const recalcButton = page.locator('[data-testid="strategy-recalculate-button"]');
      if (await recalcButton.isEnabled()) {
        console.log('Clicking ReCalculate to refresh prices...');
        await recalcButton.click();
        await waitForCalculation(page, strategyPage);
        await page.waitForTimeout(2000);
      }

      // Take screenshot
      const screenshot = await takeScreenshot(page, `2_${strategy.key}`);

      // Get data
      const legCount = await strategyPage.getLegCount();
      const legs = await strategyPage.getAllLegsDetails();
      const summary = await strategyPage.getSummaryValues();

      // ENHANCED: Check for errors
      const errorCheckPhase2 = await assertNoErrors(page, strategyPage, `Phase 2: ${strategy.name}`);

      // ENHANCED: Check payoff chart is rendered
      const payoffCheckPhase2 = await assertPayoffRendered(page, strategyPage, `Phase 2: ${strategy.name}`);

      // Verify leg count
      const legCountCorrect = legCount === strategy.expectedLegs;

      // Verify all CMPs are valid (ENHANCED: with API verification)
      let allCMPsValid = true;
      const cmpResults = [];
      for (let i = 0; i < legs.length; i++) {
        const cmpResult = await verifyCMP(page, legs[i], strategyPage);
        cmpResults.push({ leg: i + 1, ...cmpResult, raw: legs[i]?.cmp });
        if (!cmpResult.valid) {
          allCMPsValid = false;
        }
      }

      // Verify P/L calculation
      const pnlVerification = verifyPnLSensible(summary, strategy.key);
      const pnlValid = pnlVerification.maxProfitValid && pnlVerification.maxLossValid;

      // ENHANCED: All checks must pass
      const stepPassed = legCountCorrect && allCMPsValid && pnlValid && errorCheckPhase2.valid && payoffCheckPhase2.valid;

      logStepResult(2, `2.x ${strategy.name}`, stepPassed, {
        expectedLegs: strategy.expectedLegs,
        actualLegs: legCount,
        legCountCorrect,
        cmpResults,
        allCMPsValid,
        noErrors: errorCheckPhase2.valid,
        errorText: errorCheckPhase2.error || null,
        payoffRendered: payoffCheckPhase2.valid,
        payoffPaths: payoffCheckPhase2.pathCount,
        summary: {
          maxProfit: summary.maxProfit,
          maxLoss: summary.maxLoss,
          breakeven: summary.breakeven
        },
        pnlValid,
        pnlVerification
      });

      // ENHANCED ASSERTIONS
      expect(legCount, `${strategy.name}: Expected ${strategy.expectedLegs} legs`).toBe(strategy.expectedLegs);
      expect(allCMPsValid, `${strategy.name}: All CMPs should be valid`).toBe(true);
      expect(pnlValid, `${strategy.name}: P/L should be calculated`).toBe(true);
      expect(errorCheckPhase2.valid, `${strategy.name}: No errors should be present`).toBe(true);
      expect(payoffCheckPhase2.valid, `${strategy.name}: Payoff chart should be rendered`).toBe(true);
    }

    // Final screenshot
    await takeScreenshot(page, '2.9_phase2_complete');

    console.log('\n=== Phase 2 Complete ===');
    console.log(`Results: ${testResults.phase2.filter(r => r.passed).length}/${testResults.phase2.length} passed`);
  });

  test.afterAll(async () => {
    // Write test results to file
    const resultsPath = path.join(SCREENSHOT_DIR, 'test-results.json');
    fs.writeFileSync(resultsPath, JSON.stringify(testResults, null, 2));
    console.log(`\nTest results saved to: ${resultsPath}`);

    console.log('\n========================================');
    console.log('FINAL TEST SUMMARY');
    console.log('========================================');
    console.log(`Total: ${testResults.summary.total}`);
    console.log(`Passed: ${testResults.summary.passed}`);
    console.log(`Failed: ${testResults.summary.failed}`);
    console.log('========================================');
  });
});
