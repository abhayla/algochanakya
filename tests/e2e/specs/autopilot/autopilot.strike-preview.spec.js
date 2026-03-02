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

    // Fill basic info
    await builderPage.page.fill('input[data-testid="autopilot-builder-name"]', 'Strike Preview Test');

    // Wait for legs table (already visible on Step 1)
    await builderPage.page.waitForSelector('[data-testid="autopilot-legs-table"]', { timeout: 10000 });

    // Add a leg
    await builderPage.page.click('button[data-testid="autopilot-legs-add-row-button"]');
    await builderPage.page.locator('[data-testid^="autopilot-leg-row-"]').first().waitFor({ state: 'visible' });
  });

  test('should show preview for ATM Offset mode with offset 0', async () => {
    // ATM Offset should be default mode
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Check that mode is set to ATM Offset
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await expect(modeDropdown).toHaveValue('atm_offset');

    // Should NOT show "Preview unavailable"
    const errorText = strikeCell.locator('.preview-error-inline');
    const preview = strikeCell.locator('.preview-inline');

    // Wait for either preview or error to appear
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);

    await expect(errorText).not.toBeVisible();

    // Should show preview with arrow, strike, and price
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
    const preview = strikeCell.locator('.preview-inline');
    const errorText = strikeCell.locator('.preview-error-inline');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);

    // Should NOT show error
    await expect(errorText).not.toBeVisible();

    // Should show preview
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
    const preview = strikeCell.locator('.preview-inline');
    const errorText = strikeCell.locator('.preview-error-inline');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);

    // Should NOT show error
    await expect(errorText).not.toBeVisible();

    // Should show preview
    await expect(preview).toBeVisible();
  });

  test('should show preview for Fixed Strike mode', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to Fixed Strike mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('fixed');

    // Wait for mode change to settle
    const strikeInput = strikeCell.locator('input[type="number"]').first();
    await strikeInput.waitFor({ state: 'visible' });

    // Enter a fixed strike value
    await strikeInput.clear();
    await strikeInput.fill('26000');

    // Wait for preview to load
    const preview = strikeCell.locator('.preview-inline');
    const errorText = strikeCell.locator('.preview-error-inline');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);

    // Should NOT show error
    await expect(errorText).not.toBeVisible();

    // Should show preview
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
    const preset030 = strikeCell.locator('button.preset-chip').filter({ hasText: /^0\.3$/ });
    await preset030.waitFor({ state: 'visible' });

    // Click 0.30 preset (use exact match to avoid matching 0.35)
    await preset030.click();

    // Wait for preview to load
    const preview = strikeCell.locator('.preview-inline');
    const errorText = strikeCell.locator('.preview-error-inline');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);

    // Should NOT show error
    await expect(errorText).not.toBeVisible();

    // Should show preview
    await expect(preview).toBeVisible();
  });

  test('should show preview for Delta mode with 0.15 delta', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to Delta mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('delta_based');

    // Wait for presets to appear
    const preset015 = strikeCell.locator('button.preset-chip').filter({ hasText: '0.15' });
    await preset015.waitFor({ state: 'visible' });

    // Click 0.15 preset
    await preset015.click();

    // Wait for preview to load
    const preview = strikeCell.locator('.preview-inline');
    const errorText = strikeCell.locator('.preview-error-inline');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);

    // Should NOT show error
    await expect(errorText).not.toBeVisible();

    // Should show preview
    await expect(preview).toBeVisible();
  });

  test('should show preview for Premium mode with ₹100', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to Premium mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('premium_based');

    // Wait for presets to appear
    const preset100 = strikeCell.locator('button.preset-chip').filter({ hasText: '₹100' });
    await preset100.waitFor({ state: 'visible' });

    // Click ₹100 preset
    await preset100.click();

    // Wait for preview to load
    const preview = strikeCell.locator('.preview-inline');
    const errorText = strikeCell.locator('.preview-error-inline');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);

    // Should NOT show error
    await expect(errorText).not.toBeVisible();

    // Should show preview
    await expect(preview).toBeVisible();
  });

  test('should show preview for Premium mode with ₹50', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to Premium mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('premium_based');

    // Wait for presets to appear
    const preset50 = strikeCell.locator('button.preset-chip').filter({ hasText: '₹50' });
    await preset50.waitFor({ state: 'visible' });

    // Click ₹50 preset
    await preset50.click();

    // Wait for preview to load
    const preview = strikeCell.locator('.preview-inline');
    const errorText = strikeCell.locator('.preview-error-inline');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);

    // Should NOT show error
    await expect(errorText).not.toBeVisible();

    // Should show preview
    await expect(preview).toBeVisible();
  });

  test('should show preview for SD mode with 1.0σ', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to SD mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('sd_based');

    // Wait for presets to appear
    const preset10 = strikeCell.locator('button.preset-chip').filter({ hasText: '1σ' });
    await preset10.waitFor({ state: 'visible' });

    // Click 1.0σ preset
    await preset10.click();

    // Wait for preview to load
    const preview = strikeCell.locator('.preview-inline');
    const errorText = strikeCell.locator('.preview-error-inline');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);

    // Should NOT show error
    await expect(errorText).not.toBeVisible();

    // Should show preview
    await expect(preview).toBeVisible();
  });

  test('should show preview for SD mode with 2.0σ', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();

    // Change to SD mode
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    await modeDropdown.selectOption('sd_based');

    // Wait for presets to appear
    const preset20 = strikeCell.locator('button.preset-chip').filter({ hasText: '2σ' });
    await preset20.waitFor({ state: 'visible' });

    // Click 2.0σ preset
    await preset20.click();

    // Wait for preview to load
    const preview = strikeCell.locator('.preview-inline');
    const errorText = strikeCell.locator('.preview-error-inline');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);

    // Should NOT show error
    await expect(errorText).not.toBeVisible();

    // Should show preview
    await expect(preview).toBeVisible();
  });

  test('should switch between modes without showing errors', async () => {
    const strikeCell = builderPage.page.locator('td').filter({ has: builderPage.page.locator('.strike-selector-compact') }).first();
    const modeDropdown = strikeCell.locator('select.mode-dropdown');
    const errorText = strikeCell.locator('.preview-error-inline');
    const preview = strikeCell.locator('.preview-inline');

    // Start with ATM Offset
    await expect(modeDropdown).toHaveValue('atm_offset');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);
    await expect(errorText).not.toBeVisible();
    await expect(preview).toBeVisible();

    // Switch to Fixed
    await modeDropdown.selectOption('fixed');
    const strikeInput = strikeCell.locator('input[type="number"]').first();
    await strikeInput.waitFor({ state: 'visible' });

    // Enter strike
    await strikeInput.fill('26000');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);
    await expect(errorText).not.toBeVisible();

    // Switch to Delta
    await modeDropdown.selectOption('delta_based');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);
    await expect(errorText).not.toBeVisible();

    // Switch to Premium
    await modeDropdown.selectOption('premium_based');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);
    await expect(errorText).not.toBeVisible();

    // Switch to SD
    await modeDropdown.selectOption('sd_based');
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);
    await expect(errorText).not.toBeVisible();

    // Switch back to ATM Offset
    await modeDropdown.selectOption('atm_offset');

    // Wait for preview to load (with longer timeout for mode switching)
    await Promise.race([
      preview.waitFor({ state: 'visible', timeout: 6000 }).catch(() => {}),
      errorText.waitFor({ state: 'visible', timeout: 6000 }).catch(() => {})
    ]);

    // Preview should be visible without errors
    await expect(errorText).not.toBeVisible();
    await expect(preview).toBeVisible();
  });
});
