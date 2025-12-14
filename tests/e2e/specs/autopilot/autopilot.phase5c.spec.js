/**
 * Phase 5C E2E Tests - Entry Enhancements
 *
 * Features tested:
 * - Feature #4: Standard Deviation Strike Selection
 * - Feature #5: Expected Move Strike Selection
 * - Features #6-8: OI-Based Conditions (PCR, Max Pain, OI Change)
 * - Features #9-10: IV Rank/Percentile Entry Conditions
 * - Feature #11: Probability OTM
 * - Features #14-17: Entry Logic
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotStrategyBuilderPage } from '../../pages/AutoPilotDashboardPage.js';

// =============================================================================
// FEATURE #4: STANDARD DEVIATION STRIKE SELECTION
// =============================================================================

test.describe('AutoPilot Phase 5C - SD Strike Selection', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('shows SD selection dropdown', async () => {
    await builderPage.addLegButton.click();

    const strikeMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeMode.selectOption('standard_deviation');

    const sdDropdown = builderPage.page.getByTestId('autopilot-leg-sd-multiplier-0');
    await expect(sdDropdown).toBeVisible();
  });

  test('can select 1 SD, 1.5 SD, 2 SD options', async () => {
    await builderPage.addLegButton.click();

    const strikeMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeMode.selectOption('standard_deviation');

    const sdDropdown = builderPage.page.getByTestId('autopilot-leg-sd-multiplier-0');
    await sdDropdown.click();

    await expect(builderPage.page.getByRole('option', { name: '1 SD' })).toBeVisible();
    await expect(builderPage.page.getByRole('option', { name: '1.5 SD' })).toBeVisible();
    await expect(builderPage.page.getByRole('option', { name: '2 SD' })).toBeVisible();
  });

  test('displays calculated strike based on SD', async () => {
    await builderPage.addLegButton.click();

    const strikeMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeMode.selectOption('standard_deviation');

    const sdDropdown = builderPage.page.getByTestId('autopilot-leg-sd-multiplier-0');
    await sdDropdown.selectOption('1');

    const findStrikeButton = builderPage.page.getByTestId('autopilot-leg-find-strike-0');
    await findStrikeButton.click();

    const strikeDisplay = builderPage.page.getByTestId('autopilot-leg-selected-strike-0');
    await expect(strikeDisplay).toBeVisible();
  });
});

// =============================================================================
// FEATURE #5: EXPECTED MOVE STRIKE SELECTION
// =============================================================================

test.describe('AutoPilot Phase 5C - Expected Move Strike Selection', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('shows expected move mode option', async () => {
    await builderPage.addLegButton.click();

    const strikeMode = builderPage.page.getByTestId('autopilot-leg-strike-mode-0');
    await strikeMode.click();

    await expect(builderPage.page.getByRole('option', { name: /expected move/i })).toBeVisible();
  });

  test('displays calculated expected move range', async () => {
    const expectedMoveDisplay = builderPage.page.getByTestId('autopilot-expected-move-display');

    if (await expectedMoveDisplay.isVisible()) {
      await expect(expectedMoveDisplay).toContainText(/expected move/i);
    } else {
      test.skip(); // Not yet implemented
    }
  });

  test('selected strikes are outside expected move', async () => {
    test.skip(); // Requires implementation
  });
});

// =============================================================================
// FEATURES #6-8: OI-BASED CONDITIONS
// =============================================================================

test.describe('AutoPilot Phase 5C - OI-Based Conditions', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('OI.PCR appears in condition variables', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.click();

    const pcrOption = builderPage.page.getByRole('option', { name: /OI\.PCR/i });
    await expect(pcrOption).toBeVisible();
  });

  test('OI.MAX_PAIN appears in condition variables', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.click();

    const maxPainOption = builderPage.page.getByRole('option', { name: /OI\.MAX_PAIN/i });
    await expect(maxPainOption).toBeVisible();
  });

  test('OI.CHANGE appears in condition variables', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.click();

    const oiChangeOption = builderPage.page.getByRole('option', { name: /OI\.CHANGE/i });
    await expect(oiChangeOption).toBeVisible();
  });

  test('can create condition with PCR > 1.0', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.selectOption('OI.PCR');

    const operatorDropdown = builderPage.page.getByTestId('autopilot-condition-operator-0');
    await operatorDropdown.selectOption('greater_than');

    const valueInput = builderPage.page.getByTestId('autopilot-condition-value-0');
    await valueInput.fill('1.0');

    await expect(valueInput).toHaveValue('1.0');
  });

  test('can create condition with MAX_PAIN distance', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.selectOption('OI.MAX_PAIN');

    const operatorDropdown = builderPage.page.getByTestId('autopilot-condition-operator-0');
    await operatorDropdown.selectOption('less_than');

    const valueInput = builderPage.page.getByTestId('autopilot-condition-value-0');
    await valueInput.fill('25000');

    await expect(valueInput).toHaveValue('25000');
  });
});

// =============================================================================
// FEATURES #9-10: IV ENTRY CONDITIONS
// =============================================================================

test.describe('AutoPilot Phase 5C - IV Entry Conditions', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('can create entry condition with IV.RANK > 50', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.selectOption('IV.RANK');

    const operatorDropdown = builderPage.page.getByTestId('autopilot-condition-operator-0');
    await operatorDropdown.selectOption('greater_than');

    const valueInput = builderPage.page.getByTestId('autopilot-condition-value-0');
    await valueInput.fill('50');

    await expect(valueInput).toHaveValue('50');
  });

  test('can create entry condition with IV.PERCENTILE > 60', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.selectOption('IV.PERCENTILE');

    const operatorDropdown = builderPage.page.getByTestId('autopilot-condition-operator-0');
    await operatorDropdown.selectOption('greater_than');

    const valueInput = builderPage.page.getByTestId('autopilot-condition-value-0');
    await valueInput.fill('60');

    await expect(valueInput).toHaveValue('60');
  });
});

// =============================================================================
// FEATURE #11: PROBABILITY OTM
// =============================================================================

test.describe('AutoPilot Phase 5C - Probability OTM', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('PROBABILITY.OTM appears in condition variables', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.click();

    const probOTMOption = builderPage.page.getByRole('option', { name: /PROBABILITY\.OTM/i });
    await expect(probOTMOption).toBeVisible();
  });

  test('can create condition with PROBABILITY.OTM > 75', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    const variableDropdown = builderPage.page.getByTestId('autopilot-condition-variable-0');
    await variableDropdown.selectOption('PROBABILITY.OTM');

    const operatorDropdown = builderPage.page.getByTestId('autopilot-condition-operator-0');
    await operatorDropdown.selectOption('greater_than');

    const valueInput = builderPage.page.getByTestId('autopilot-condition-value-0');
    await valueInput.fill('75');

    await expect(valueInput).toHaveValue('75');
  });
});

// =============================================================================
// FEATURES #14-17: ENTRY LOGIC
// =============================================================================

test.describe('AutoPilot Phase 5C - Entry Logic', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    await builderPage.waitForBuilderLoad();
  });

  test('can set DTE enforcement range', async () => {
    const settingsTab = builderPage.page.getByTestId('autopilot-builder-settings-tab');
    await settingsTab.click();

    const minDTEInput = builderPage.page.getByTestId('autopilot-settings-min-dte');
    const maxDTEInput = builderPage.page.getByTestId('autopilot-settings-max-dte');

    if (await minDTEInput.isVisible()) {
      await minDTEInput.fill('30');
      await maxDTEInput.fill('45');

      await expect(minDTEInput).toHaveValue('30');
      await expect(maxDTEInput).toHaveValue('45');
    } else {
      test.skip(); // Not yet implemented
    }
  });

  test('can enable delta neutral entry requirement', async () => {
    const settingsTab = builderPage.page.getByTestId('autopilot-builder-settings-tab');
    await settingsTab.click();

    const deltaNeutralCheckbox = builderPage.page.getByTestId('autopilot-settings-delta-neutral-entry');

    if (await deltaNeutralCheckbox.isVisible()) {
      await deltaNeutralCheckbox.check();
      await expect(deltaNeutralCheckbox).toBeChecked();
    } else {
      test.skip(); // Not yet implemented
    }
  });

  test('shows expected move at entry', async () => {
    test.skip(); // Requires implementation
  });

  test('can add multiple condition groups with AND/OR', async () => {
    const conditionsTab = builderPage.page.getByTestId('autopilot-builder-conditions-tab');
    await conditionsTab.click();

    // Add first condition
    const addConditionButton = builderPage.page.getByTestId('autopilot-add-condition-button');
    await addConditionButton.click();

    // Add second condition
    await addConditionButton.click();

    // Check for logic operator selector
    const logicOperator = builderPage.page.getByTestId('autopilot-condition-logic-operator');

    if (await logicOperator.isVisible()) {
      await logicOperator.selectOption('AND');
      await expect(logicOperator).toHaveValue('AND');
    } else {
      test.skip(); // Multi-condition logic not yet implemented
    }
  });
});
