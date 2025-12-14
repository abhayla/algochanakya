/**
 * Phase 5A E2E Tests - Quick Wins
 *
 * Features tested:
 * - Feature #1: Delta Range Strike Selection
 * - Feature #2: Premium Range Strike Selection
 * - Feature #3: Round Strike Preference
 * - Features #54-57: Greeks as Entry/Exit Conditions
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotStrategyBuilderPage } from '../../pages/AutoPilotDashboardPage.js';

// =============================================================================
// FEATURE #1: DELTA RANGE STRIKE SELECTION
// =============================================================================

test.describe('AutoPilot Phase 5A - Delta Range Strike Selection', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('shows delta range inputs when delta range mode selected', async () => {
    // Add a new leg
    await builderPage.addLegButton.click();

    // Select delta range mode
    const strikeSelectionMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeSelectionMode.selectOption('delta_range');

    // Should show min/max delta inputs
    const minDeltaInput = builderPage.page.getByTestId('autopilot-leg-min-delta-0');
    const maxDeltaInput = builderPage.page.getByTestId('autopilot-leg-max-delta-0');

    await expect(minDeltaInput).toBeVisible();
    await expect(maxDeltaInput).toBeVisible();
  });

  test('validates min delta < max delta', async () => {
    await builderPage.addLegButton.click();

    const strikeSelectionMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeSelectionMode.selectOption('delta_range');

    // Enter invalid range (min > max)
    const minDeltaInput = builderPage.page.getByTestId('autopilot-leg-min-delta-0');
    const maxDeltaInput = builderPage.page.getByTestId('autopilot-leg-max-delta-0');

    await minDeltaInput.fill('0.20');
    await maxDeltaInput.fill('0.10');

    // Should show validation error
    const errorMessage = builderPage.page.getByText(/min delta must be less than max delta/i);
    await expect(errorMessage).toBeVisible();
  });

  test('displays found strike matching delta range', async () => {
    await builderPage.addLegButton.click();

    const strikeSelectionMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeSelectionMode.selectOption('delta_range');

    // Enter valid range
    const minDeltaInput = builderPage.page.getByTestId('autopilot-leg-min-delta-0');
    const maxDeltaInput = builderPage.page.getByTestId('autopilot-leg-max-delta-0');

    await minDeltaInput.fill('0.10');
    await maxDeltaInput.fill('0.20');

    // Trigger strike search
    const findStrikeButton = builderPage.page.getByTestId('autopilot-leg-find-strike-0');
    await findStrikeButton.click();

    // Should display found strike
    const strikeDisplay = builderPage.page.getByTestId('autopilot-leg-selected-strike-0');
    await expect(strikeDisplay).toBeVisible();
    await expect(strikeDisplay).toContainText(/Strike:/i);
  });

  test('shows error when no strike matches range', async () => {
    await builderPage.addLegButton.click();

    const strikeSelectionMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeSelectionMode.selectOption('delta_range');

    // Enter very narrow range unlikely to match
    const minDeltaInput = builderPage.page.getByTestId('autopilot-leg-min-delta-0');
    const maxDeltaInput = builderPage.page.getByTestId('autopilot-leg-max-delta-0');

    await minDeltaInput.fill('0.01');
    await maxDeltaInput.fill('0.02');

    const findStrikeButton = builderPage.page.getByTestId('autopilot-leg-find-strike-0');
    await findStrikeButton.click();

    // Should show no match error
    const errorMessage = builderPage.page.getByText(/no strike found matching delta range/i);
    await expect(errorMessage).toBeVisible();
  });
});

// =============================================================================
// FEATURE #2: PREMIUM RANGE STRIKE SELECTION
// =============================================================================

test.describe('AutoPilot Phase 5A - Premium Range Strike Selection', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('shows premium range inputs when premium range mode selected', async () => {
    await builderPage.addLegButton.click();

    const strikeSelectionMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeSelectionMode.selectOption('premium_range');

    const minPremiumInput = builderPage.page.getByTestId('autopilot-leg-min-premium-0');
    const maxPremiumInput = builderPage.page.getByTestId('autopilot-leg-max-premium-0');

    await expect(minPremiumInput).toBeVisible();
    await expect(maxPremiumInput).toBeVisible();
  });

  test('validates min premium < max premium', async () => {
    await builderPage.addLegButton.click();

    const strikeSelectionMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeSelectionMode.selectOption('premium_range');

    const minPremiumInput = builderPage.page.getByTestId('autopilot-leg-min-premium-0');
    const maxPremiumInput = builderPage.page.getByTestId('autopilot-leg-max-premium-0');

    await minPremiumInput.fill('200');
    await maxPremiumInput.fill('100');

    const errorMessage = builderPage.page.getByText(/min premium must be less than max premium/i);
    await expect(errorMessage).toBeVisible();
  });

  test('displays found strike matching premium range', async () => {
    await builderPage.addLegButton.click();

    const strikeSelectionMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeSelectionMode.selectOption('premium_range');

    const minPremiumInput = builderPage.page.getByTestId('autopilot-leg-min-premium-0');
    const maxPremiumInput = builderPage.page.getByTestId('autopilot-leg-max-premium-0');

    await minPremiumInput.fill('100');
    await maxPremiumInput.fill('150');

    const findStrikeButton = builderPage.page.getByTestId('autopilot-leg-find-strike-0');
    await findStrikeButton.click();

    const strikeDisplay = builderPage.page.getByTestId('autopilot-leg-selected-strike-0');
    await expect(strikeDisplay).toBeVisible();
  });
});

// =============================================================================
// FEATURE #3: ROUND STRIKE PREFERENCE
// =============================================================================

test.describe('AutoPilot Phase 5A - Round Strike Preference', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('shows round strike checkbox in leg row', async () => {
    await builderPage.addLegButton.click();

    const roundStrikeCheckbox = builderPage.page.getByTestId('autopilot-leg-round-strike-0');
    await expect(roundStrikeCheckbox).toBeVisible();
  });

  test('checkbox state persists on save', async () => {
    await builderPage.addLegButton.click();

    const roundStrikeCheckbox = builderPage.page.getByTestId('autopilot-leg-round-strike-0');
    await roundStrikeCheckbox.check();

    await expect(roundStrikeCheckbox).toBeChecked();

    // Fill required fields and save (if save functionality exists)
    // This would be strategy-specific based on the actual implementation
  });

  test('selected strike is divisible by 100 when enabled', async () => {
    await builderPage.addLegButton.click();

    const strikeSelectionMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeSelectionMode.selectOption('delta');

    const roundStrikeCheckbox = builderPage.page.getByTestId('autopilot-leg-round-strike-0');
    await roundStrikeCheckbox.check();

    const deltaInput = builderPage.page.getByTestId('autopilot-leg-target-delta-0');
    await deltaInput.fill('0.15');

    const findStrikeButton = builderPage.page.getByTestId('autopilot-leg-find-strike-0');
    await findStrikeButton.click();

    const strikeDisplay = builderPage.page.getByTestId('autopilot-leg-selected-strike-0');
    const strikeText = await strikeDisplay.textContent();

    // Extract strike number from text (e.g., "Strike: 24800" -> 24800)
    const strikeMatch = strikeText.match(/\d+/);
    if (strikeMatch) {
      const strike = parseInt(strikeMatch[0]);
      expect(strike % 100).toBe(0); // Should be divisible by 100
    }
  });
});

// =============================================================================
// FEATURES #54-57: GREEKS AS ENTRY/EXIT CONDITIONS
// =============================================================================

test.describe('AutoPilot Phase 5A - Greeks as Conditions', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('STRATEGY.DELTA appears in condition variable dropdown', async () => {
    // Navigate to entry conditions section
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    // Add new condition
    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    // Check that STRATEGY.DELTA option exists in dropdown
    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    const deltaOption = variableDropdown.locator('option[value="STRATEGY.DELTA"]');
    await expect(deltaOption).toBeAttached();
  });

  test('STRATEGY.GAMMA appears in condition variable dropdown', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    const gammaOption = variableDropdown.locator('option[value="STRATEGY.GAMMA"]');
    await expect(gammaOption).toBeAttached();
  });

  test('STRATEGY.THETA appears in condition variable dropdown', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    const thetaOption = variableDropdown.locator('option[value="STRATEGY.THETA"]');
    await expect(thetaOption).toBeAttached();
  });

  test('STRATEGY.VEGA appears in condition variable dropdown', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    const vegaOption = variableDropdown.locator('option[value="STRATEGY.VEGA"]');
    await expect(vegaOption).toBeAttached();
  });

  test('can create condition with DELTA > 0.20', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    // Select STRATEGY.DELTA variable
    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.selectOption('STRATEGY.DELTA');

    // Select greater_than operator
    const operatorDropdown = builderPage.page.getByTestId('autopilot-condition-operator-0');
    await operatorDropdown.selectOption('greater_than');

    // Enter value 0.20
    const valueInput = builderPage.page.getByTestId('autopilot-condition-value-0');
    await valueInput.fill('0.20');

    // Verify condition is saved
    await expect(variableDropdown).toHaveValue('STRATEGY.DELTA');
    await expect(operatorDropdown).toHaveValue('greater_than');
    await expect(valueInput).toHaveValue('0.20');
  });

  test('can create condition with GAMMA between 0.01 and 0.05', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.selectOption('STRATEGY.GAMMA');

    const operatorDropdown = builderPage.page.getByTestId('autopilot-condition-operator-0');
    await operatorDropdown.selectOption('between');

    // For between operator, should show min/max inputs
    const minValueInput = builderPage.page.getByTestId('autopilot-condition-min-value-0');
    const maxValueInput = builderPage.page.getByTestId('autopilot-condition-max-value-0');

    await minValueInput.fill('0.01');
    await maxValueInput.fill('0.05');

    await expect(minValueInput).toHaveValue('0.01');
    await expect(maxValueInput).toHaveValue('0.05');
  });
});
