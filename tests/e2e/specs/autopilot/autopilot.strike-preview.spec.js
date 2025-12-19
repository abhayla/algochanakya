/**
 * AutoPilot Strike Preview - Comprehensive Test
 *
 * Tests all strike selection modes to verify "Preview unavailable" bug is fixed
 */

import { test, expect } from '../../fixtures/auth.fixture';
import { AutoPilotStrategyBuilderPage } from '../../pages/AutoPilotDashboardPage.js';

test.describe('AutoPilot Strike Preview - All Modes', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.goto('/autopilot/strategies/new');

    // Fill basic info and navigate to legs step
    await builderPage.page.fill('input[data-testid="autopilot-builder-name-input"]', 'Strike Preview Test');
    await builderPage.page.click('button[data-testid="autopilot-builder-next-btn"]');

    // Wait for legs table
    await builderPage.page.waitForSelector('[data-testid="autopilot-legs-table"]', { timeout: 10000 });

    // Add a leg
    await builderPage.page.click('button[data-testid="autopilot-legs-add-row-button"]');
    await builderPage.page.waitForTimeout(1000); // Wait for leg to be added
  });

  test('should show preview for ATM Offset mode with offset 0', async () => {
    // ATM Offset should be default mode
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Check that mode is set to ATM Offset
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await expect(modeDropdown).toHaveValue('atm_offset');

    // Wait for preview to load
    await builderPage.page.waitForTimeout(2000);

    // Should NOT show "Preview unavailable"
    const errorText = strikeCell.locator('.preview-error-inline');
    await expect(errorText).not.toBeVisible();

    // Should show preview with arrow, strike, and price
    const preview = strikeCell.locator('.preview-inline');
    await expect(preview).toBeVisible();

    // Check preview contains expected elements
    const previewText = await preview.textContent();
    expect(previewText).toContain('→');
    expect(previewText).toMatch(/\d+/); // Contains strike number
    expect(previewText).toContain('CE'); // Option type
  });

  test('should show preview for ATM Offset mode with offset +2', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change offset to +2
    const offsetInput = strikeCell.locator('input[type="number"]').first();
    await offsetInput.clear();
    await offsetInput.fill('2');

    // Wait for preview to update
    await builderPage.page.waitForTimeout(2000);

    // Should NOT show error
    const errorText = strikeCell.locator('.preview-error-inline');
    await expect(errorText).not.toBeVisible();

    // Should show preview
    const preview = strikeCell.locator('.preview-inline');
    await expect(preview).toBeVisible();

    const previewText = await preview.textContent();
    expect(previewText).toContain('→');
    expect(previewText).toMatch(/\d+/);
  });

  test('should show preview for ATM Offset mode with offset -2', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change offset to -2
    const offsetInput = strikeCell.locator('input[type="number"]').first();
    await offsetInput.clear();
    await offsetInput.fill('-2');

    // Wait for preview to update
    await builderPage.page.waitForTimeout(2000);

    // Should NOT show error
    const errorText = strikeCell.locator('.preview-error-inline');
    await expect(errorText).not.toBeVisible();

    // Should show preview
    const preview = strikeCell.locator('.preview-inline');
    await expect(preview).toBeVisible();
  });

  test('should show preview for Fixed Strike mode', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to Fixed Strike mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('fixed');

    // Wait for mode change
    await builderPage.page.waitForTimeout(1000);

    // Enter a fixed strike value
    const strikeInput = strikeCell.locator('input[type="number"]').first();
    await strikeInput.clear();
    await strikeInput.fill('26000');

    // Wait for preview to load
    await builderPage.page.waitForTimeout(2000);

    // Should NOT show error
    const errorText = strikeCell.locator('.preview-error-inline');
    await expect(errorText).not.toBeVisible();

    // Should show preview
    const preview = strikeCell.locator('.preview-inline');
    await expect(preview).toBeVisible();

    const previewText = await preview.textContent();
    expect(previewText).toContain('26000');
  });

  test('should show preview for Delta mode with 0.30 delta', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to Delta mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('delta_based');

    // Wait for mode change and presets to appear
    await builderPage.page.waitForTimeout(1000);

    // Click 0.30 preset
    const preset030 = strikeCell.locator('button.preset-chip').filter({ hasText: '0.3' });
    await preset030.click();

    // Wait for preview to load
    await builderPage.page.waitForTimeout(2000);

    // Should NOT show error
    const errorText = strikeCell.locator('.preview-error-inline');
    await expect(errorText).not.toBeVisible();

    // Should show preview
    const preview = strikeCell.locator('.preview-inline');
    await expect(preview).toBeVisible();
  });

  test('should show preview for Delta mode with 0.15 delta', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to Delta mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('delta_based');

    // Wait for mode change
    await builderPage.page.waitForTimeout(1000);

    // Click 0.15 preset
    const preset015 = strikeCell.locator('button.preset-chip').filter({ hasText: '0.15' });
    await preset015.click();

    // Wait for preview to load
    await builderPage.page.waitForTimeout(2000);

    // Should NOT show error
    const errorText = strikeCell.locator('.preview-error-inline');
    await expect(errorText).not.toBeVisible();

    // Should show preview
    const preview = strikeCell.locator('.preview-inline');
    await expect(preview).toBeVisible();
  });

  test('should show preview for Premium mode with ₹100', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to Premium mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('premium_based');

    // Wait for mode change
    await builderPage.page.waitForTimeout(1000);

    // Click ₹100 preset
    const preset100 = strikeCell.locator('button.preset-chip').filter({ hasText: '₹100' });
    await preset100.click();

    // Wait for preview to load
    await builderPage.page.waitForTimeout(2000);

    // Should NOT show error
    const errorText = strikeCell.locator('.preview-error-inline');
    await expect(errorText).not.toBeVisible();

    // Should show preview
    const preview = strikeCell.locator('.preview-inline');
    await expect(preview).toBeVisible();
  });

  test('should show preview for Premium mode with ₹50', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to Premium mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('premium_based');

    // Wait for mode change
    await builderPage.page.waitForTimeout(1000);

    // Click ₹50 preset
    const preset50 = strikeCell.locator('button.preset-chip').filter({ hasText: '₹50' });
    await preset50.click();

    // Wait for preview to load
    await builderPage.page.waitForTimeout(2000);

    // Should NOT show error
    const errorText = strikeCell.locator('.preview-error-inline');
    await expect(errorText).not.toBeVisible();

    // Should show preview
    const preview = strikeCell.locator('.preview-inline');
    await expect(preview).toBeVisible();
  });

  test('should show preview for SD mode with 1.0σ', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to SD mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('sd_based');

    // Wait for mode change
    await builderPage.page.waitForTimeout(1000);

    // Click 1.0σ preset
    const preset10 = strikeCell.locator('button.preset-chip').filter({ hasText: '1σ' });
    await preset10.click();

    // Wait for preview to load
    await builderPage.page.waitForTimeout(2000);

    // Should NOT show error
    const errorText = strikeCell.locator('.preview-error-inline');
    await expect(errorText).not.toBeVisible();

    // Should show preview
    const preview = strikeCell.locator('.preview-inline');
    await expect(preview).toBeVisible();
  });

  test('should show preview for SD mode with 2.0σ', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to SD mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('sd_based');

    // Wait for mode change
    await builderPage.page.waitForTimeout(1000);

    // Click 2.0σ preset
    const preset20 = strikeCell.locator('button.preset-chip').filter({ hasText: '2σ' });
    await preset20.click();

    // Wait for preview to load
    await builderPage.page.waitForTimeout(2000);

    // Should NOT show error
    const errorText = strikeCell.locator('.preview-error-inline');
    await expect(errorText).not.toBeVisible();

    // Should show preview
    const preview = strikeCell.locator('.preview-inline');
    await expect(preview).toBeVisible();
  });

  test('should switch between modes without showing errors', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    const errorText = strikeCell.locator('.preview-error-inline');
    const preview = strikeCell.locator('.preview-inline');

    // Start with ATM Offset
    await expect(modeDropdown).toHaveValue('atm_offset');
    await builderPage.page.waitForTimeout(2000);
    await expect(errorText).not.toBeVisible();
    await expect(preview).toBeVisible();

    // Switch to Fixed
    await modeDropdown.selectOption('fixed');
    await builderPage.page.waitForTimeout(1000);

    // Enter strike
    const strikeInput = strikeCell.locator('input[type="number"]').first();
    await strikeInput.fill('26000');
    await builderPage.page.waitForTimeout(2000);
    await expect(errorText).not.toBeVisible();

    // Switch to Delta
    await modeDropdown.selectOption('delta_based');
    await builderPage.page.waitForTimeout(2000);
    await expect(errorText).not.toBeVisible();

    // Switch to Premium
    await modeDropdown.selectOption('premium_based');
    await builderPage.page.waitForTimeout(2000);
    await expect(errorText).not.toBeVisible();

    // Switch to SD
    await modeDropdown.selectOption('sd_based');
    await builderPage.page.waitForTimeout(2000);
    await expect(errorText).not.toBeVisible();

    // Switch back to ATM Offset
    await modeDropdown.selectOption('atm_offset');
    await builderPage.page.waitForTimeout(2000);
    await expect(errorText).not.toBeVisible();
    await expect(preview).toBeVisible();
  });
});
