/**
 * Strategy Builder Test Helpers
 *
 * Best practices for Strategy Builder E2E tests:
 * 1. Always verify CMP values change after strike/expiry/type changes
 * 2. Always check for error banners after actions
 * 3. Always verify payoff chart is rendered (not blank)
 * 4. Use API verification when possible
 * 5. Skip placeholder values in dropdowns
 */

const API_BASE = process.env.API_BASE || 'http://localhost:8001';

// Placeholder values to skip when selecting dropdown options
const DROPDOWN_PLACEHOLDERS = ['select', 'choose', 'pick', ''];

/**
 * Fetch LTP from backend API
 * @param {Page} page - Playwright page
 * @param {string} tradingsymbol - NFO trading symbol
 * @returns {number|null} LTP or null if fetch failed
 */
export async function fetchLTPFromAPI(page, tradingsymbol) {
  try {
    const response = await page.request.get(
      `${API_BASE}/api/orders/ltp?instruments=NFO:${tradingsymbol}`
    );
    if (response.ok()) {
      const data = await response.json();
      const key = `NFO:${tradingsymbol}`;
      return data[key]?.last_price || data[key]?.ltp || null;
    }
  } catch (err) {
    console.error(`Failed to fetch LTP for ${tradingsymbol}:`, err.message);
  }
  return null;
}

/**
 * Wait for auto-calculation to complete
 * @param {Page} page - Playwright page
 * @param {StrategyBuilderPage} strategyPage - Page object
 */
export async function waitForCalculation(page, strategyPage) {
  await page.waitForTimeout(500);
  await strategyPage.waitForPnLCalculation();
  await page.waitForLoadState('networkidle').catch(() => {});
}

/**
 * Verify CMP value is valid and optionally matches API
 * @param {Page} page - Playwright page
 * @param {Object} legDetails - Leg details from getAllLegsDetails()
 * @param {StrategyBuilderPage} strategyPage - Page object for building symbol
 * @param {number} tolerance - Tolerance for API comparison (default 0.5)
 * @returns {Object} { valid, value, apiValue, verified, reason }
 */
export async function verifyCMP(page, legDetails, strategyPage, tolerance = 0.5) {
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

  // Try to verify against API if we can build the trading symbol
  if (strategyPage) {
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
  }

  return { valid: true, value: cmpValue, verified: false };
}

/**
 * Assert no error banners are present on the page
 * @param {Page} page - Playwright page
 * @param {StrategyBuilderPage} strategyPage - Page object
 * @param {string} stepName - Step name for error message
 * @returns {Object} { valid, error }
 */
export async function assertNoErrors(page, strategyPage, stepName) {
  const hasError = await strategyPage.hasErrorBanner();
  if (hasError) {
    const errorText = await strategyPage.getErrorBannerText();
    console.error(`❌ Error detected at ${stepName}: ${errorText}`);
    return { valid: false, error: errorText };
  }
  return { valid: true };
}

/**
 * Assert payoff chart is rendered (not blank)
 * @param {Page} page - Playwright page
 * @param {StrategyBuilderPage} strategyPage - Page object
 * @param {string} stepName - Step name for error message
 * @returns {Object} { valid, pathCount }
 */
export async function assertPayoffRendered(page, strategyPage, stepName) {
  const isRendered = await strategyPage.isPayoffChartRendered();
  const pathCount = await strategyPage.getPayoffChartPathCount();
  if (!isRendered || pathCount === 0) {
    console.error(`❌ Payoff chart blank at ${stepName}: paths=${pathCount}`);
    return { valid: false, pathCount };
  }
  return { valid: true, pathCount };
}

/**
 * Verify P/L calculation is sensible for the strategy type
 * @param {Object} summary - Summary values from getSummaryValues()
 * @param {string} strategyType - Strategy type key
 * @returns {Object} Verification results
 */
export function verifyPnLSensible(summary, strategyType) {
  const maxProfit = summary.maxProfit?.replace(/,/g, '');
  const maxLoss = summary.maxLoss?.replace(/,/g, '');

  const results = {
    maxProfitValid: maxProfit && maxProfit !== '-' && !isNaN(parseFloat(maxProfit)),
    maxLossValid: maxLoss && maxLoss !== '-' && !isNaN(parseFloat(maxLoss)),
    breakevenValid: summary.breakeven && summary.breakeven !== '-'
  };

  // Strategy-specific validations
  const strategyKey = strategyType?.toLowerCase().replace(/\s+/g, '_');
  if (strategyKey === 'short_straddle' || strategyKey === 'short_strangle') {
    results.strategyLogic = parseFloat(maxProfit) > 0 && parseFloat(maxLoss) < 0;
  } else if (strategyKey === 'iron_condor') {
    results.strategyLogic = parseFloat(maxProfit) > 0 && parseFloat(maxLoss) < 0;
  } else if (strategyKey === 'bull_call_spread' || strategyKey === 'bear_put_spread') {
    results.strategyLogic = true;
  } else {
    results.strategyLogic = true;
  }

  return results;
}

/**
 * Find a valid option value from dropdown (skips placeholders)
 * @param {Array<string>} options - Available option texts
 * @param {string} currentValue - Current selected value to exclude
 * @param {boolean} mustBeNumeric - If true, only select numeric values
 * @returns {string|null} Valid option or null if none found
 */
export function findValidOption(options, currentValue, mustBeNumeric = false) {
  for (const optionText of options) {
    const value = optionText.trim();
    // Skip if empty, placeholder, or same as current
    if (!value ||
        value === currentValue ||
        DROPDOWN_PLACEHOLDERS.includes(value.toLowerCase())) {
      continue;
    }
    // If must be numeric, check it's a valid number
    if (mustBeNumeric && isNaN(parseFloat(value))) {
      continue;
    }
    return value;
  }
  return null;
}

/**
 * Verify CMP changed after an action
 * @param {number} cmpBefore - CMP before action
 * @param {number} cmpAfter - CMP after action
 * @param {string} actionDescription - Description for logging
 * @returns {Object} { changed, before, after }
 */
export function verifyCMPChanged(cmpBefore, cmpAfter, actionDescription) {
  const changed = cmpBefore !== cmpAfter;
  if (!changed) {
    console.warn(`⚠️ CMP did not change after ${actionDescription}: before=${cmpBefore}, after=${cmpAfter}`);
  }
  return { changed, before: cmpBefore, after: cmpAfter };
}

/**
 * Comprehensive verification after a strategy action
 * Checks CMP, errors, and payoff in one call
 * @param {Page} page - Playwright page
 * @param {StrategyBuilderPage} strategyPage - Page object
 * @param {string} stepName - Step name for logging
 * @param {Object} options - Additional options
 * @returns {Object} Comprehensive verification results
 */
export async function verifyStrategyState(page, strategyPage, stepName, options = {}) {
  const { checkPayoff = true, expectedLegCount = null } = options;

  const results = {
    stepName,
    timestamp: new Date().toISOString(),
    passed: true,
    checks: {}
  };

  // Check for errors
  const errorCheck = await assertNoErrors(page, strategyPage, stepName);
  results.checks.noErrors = errorCheck.valid;
  if (!errorCheck.valid) {
    results.passed = false;
    results.errorText = errorCheck.error;
  }

  // Check leg count if specified
  if (expectedLegCount !== null) {
    const legCount = await strategyPage.getLegCount();
    results.checks.legCount = legCount === expectedLegCount;
    results.actualLegCount = legCount;
    if (!results.checks.legCount) {
      results.passed = false;
    }
  }

  // Check payoff chart
  if (checkPayoff) {
    const payoffCheck = await assertPayoffRendered(page, strategyPage, stepName);
    results.checks.payoffRendered = payoffCheck.valid;
    results.payoffPaths = payoffCheck.pathCount;
    if (!payoffCheck.valid) {
      results.passed = false;
    }
  }

  // Get and verify all leg CMPs
  const legs = await strategyPage.getAllLegsDetails();
  results.legs = [];
  for (let i = 0; i < legs.length; i++) {
    const cmpResult = await verifyCMP(page, legs[i], strategyPage);
    results.legs.push({
      index: i,
      cmp: legs[i]?.cmp,
      valid: cmpResult.valid,
      verified: cmpResult.verified || false
    });
    if (!cmpResult.valid) {
      results.passed = false;
    }
  }
  results.checks.allCMPsValid = results.legs.every(l => l.valid);

  // Get summary values
  results.summary = await strategyPage.getSummaryValues();

  return results;
}

/**
 * Log step result in consistent format
 * @param {number} phase - Phase number (1 or 2)
 * @param {string} step - Step identifier
 * @param {boolean} passed - Whether step passed
 * @param {Object} details - Additional details
 * @param {Object} testResults - Results collector object
 */
export function logStepResult(phase, step, passed, details, testResults = null) {
  const result = { step, passed, details, timestamp: new Date().toISOString() };

  if (testResults) {
    if (phase === 1) {
      testResults.phase1 = testResults.phase1 || [];
      testResults.phase1.push(result);
    } else {
      testResults.phase2 = testResults.phase2 || [];
      testResults.phase2.push(result);
    }
    testResults.summary = testResults.summary || { passed: 0, failed: 0, total: 0 };
    testResults.summary.total++;
    if (passed) {
      testResults.summary.passed++;
    } else {
      testResults.summary.failed++;
    }
  }

  console.log(`${passed ? '✅' : '❌'} ${step}: ${JSON.stringify(details)}`);
}

export { DROPDOWN_PLACEHOLDERS };
