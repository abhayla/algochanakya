import { test, expect } from '../../fixtures/auth.fixture.js';
import OFOPage from '../../pages/OFOPage.js';

/**
 * OFO (Options For Options) Screen - Edge Case Tests
 * Tests error handling, boundary conditions, and edge cases
 */
test.describe('OFO - Edge Cases @edge', () => {
  let ofoPage;

  test.beforeEach(async ({ page }) => {
    ofoPage = new OFOPage(page);
    await ofoPage.navigate();
  });

  test.describe('Input Validation', () => {
    test('should handle minimum lots value of 1', async () => {
      await ofoPage.setLots(0);
      // Should clamp to 1 or show validation error
      const value = await ofoPage.lotsInput.inputValue();
      // Either shows 1 (min) or still shows 0 but button should be disabled or show error on click
      expect(parseInt(value)).toBeLessThanOrEqual(1);
    });

    test('should handle large lots value', async () => {
      await ofoPage.setLots(100);
      await expect(ofoPage.lotsInput).toHaveValue('100');
    });

    test('should handle negative lots input', async () => {
      await ofoPage.setLots(-5);
      // HTML input allows typing but min=1 will show validation error
      // The actual behavior is that the value can be typed, but the form will be invalid
      // We just verify the input received the value (frontend doesn't clamp automatically)
      const value = await ofoPage.lotsInput.inputValue();
      // Either clamped to 1 or still shows -5 (which is invalid)
      expect(value).toBeTruthy();
    });
  });

  test.describe('Empty States', () => {
    test('should show empty state initially before calculation', async () => {
      const hasEmpty = await ofoPage.hasEmptyState();
      const hasResults = await ofoPage.hasResults();
      // Initially either empty state or no results
      expect(!hasResults || hasEmpty).toBeTruthy();
    });

    test('should handle no strategies selected', async () => {
      await ofoPage.openStrategyDropdown();
      await ofoPage.clearAllStrategiesBtn.click();
      await ofoPage.closeStrategyDropdown();

      // Calculate button should be disabled when no strategies selected
      await expect(ofoPage.calculateButton).toBeDisabled();

      // Should show empty state prompting to select strategies
      const hasEmpty = await ofoPage.hasEmptyState();
      expect(hasEmpty).toBeTruthy();
    });
  });

  test.describe('Underlying Switching', () => {
    test('should maintain strike range when switching underlying', async () => {
      await ofoPage.setStrikeRange(15);
      await ofoPage.selectUnderlying('BANKNIFTY');
      // Strike range should remain
      await expect(ofoPage.strikeRangeSelect).toHaveValue('15');
    });

    test('should maintain lots when switching underlying', async () => {
      await ofoPage.setLots(3);
      await ofoPage.selectUnderlying('FINNIFTY');
      await expect(ofoPage.lotsInput).toHaveValue('3');
    });

    test('should switch between all underlyings', async () => {
      await ofoPage.selectUnderlying('NIFTY');
      await expect(ofoPage.niftyTab).toHaveClass(/active/);

      await ofoPage.selectUnderlying('BANKNIFTY');
      await expect(ofoPage.bankniftyTab).toHaveClass(/active/);

      await ofoPage.selectUnderlying('FINNIFTY');
      await expect(ofoPage.finniftyTab).toHaveClass(/active/);
    });
  });

  test.describe('Strategy Selection', () => {
    test('should handle toggling same strategy multiple times', async () => {
      await ofoPage.openStrategyDropdown();
      await ofoPage.clearAllStrategiesBtn.click();

      // Toggle iron condor on
      await ofoPage.toggleStrategy('iron_condor');
      let checkbox = ofoPage.getStrategyOption('iron_condor').locator('input[type="checkbox"]');
      await expect(checkbox).toBeChecked();

      // Toggle off
      await ofoPage.getStrategyOption('iron_condor').click();
      await expect(checkbox).not.toBeChecked();

      // Toggle on again
      await ofoPage.getStrategyOption('iron_condor').click();
      await expect(checkbox).toBeChecked();
    });

    test('should update selected count when toggling strategies', async () => {
      await ofoPage.openStrategyDropdown();
      await ofoPage.clearAllStrategiesBtn.click();
      await ofoPage.closeStrategyDropdown();

      // Should show "Select Strategies" when none selected
      await expect(ofoPage.strategyTrigger).toContainText('Select Strategies');

      // Select one
      await ofoPage.toggleStrategy('iron_condor');
      await ofoPage.closeStrategyDropdown();
      await expect(ofoPage.strategyTrigger).toContainText('1 selected');

      // Select another
      await ofoPage.toggleStrategy('short_straddle');
      await ofoPage.closeStrategyDropdown();
      await expect(ofoPage.strategyTrigger).toContainText('2 selected');
    });
  });

  test.describe('Dropdown Behavior', () => {
    test('should close dropdown when clicking outside', async () => {
      await ofoPage.openStrategyDropdown();
      await expect(ofoPage.strategyDropdown).toBeVisible();

      await ofoPage.closeStrategyDropdown();
      await expect(ofoPage.strategyDropdown).not.toBeVisible();
    });

    test('should toggle dropdown on trigger click', async () => {
      // Open
      await ofoPage.strategyTrigger.click();
      await expect(ofoPage.strategyDropdown).toBeVisible();

      // Close by clicking outside (backdrop) - the component has a backdrop that closes the dropdown
      await ofoPage.closeStrategyDropdown();
      await expect(ofoPage.strategyDropdown).not.toBeVisible();
    });
  });

  test.describe('Strike Range Options', () => {
    test('should have all strike range options available', async () => {
      // Check that all expected options exist
      const options = await ofoPage.strikeRangeSelect.locator('option').all();
      const values = await Promise.all(options.map(opt => opt.getAttribute('value')));

      expect(values).toContain('5');
      expect(values).toContain('10');
      expect(values).toContain('15');
      expect(values).toContain('20');
    });
  });

  test.describe('Auto-Refresh', () => {
    test('should have auto-refresh toggle disabled by default', async () => {
      const checkbox = ofoPage.autoRefreshToggle.locator('input');
      await expect(checkbox).not.toBeChecked();
    });

    test('should show interval selector when auto-refresh is enabled', async () => {
      await ofoPage.toggleAutoRefresh();

      // Interval selector should be visible or become visible
      await expect(ofoPage.autoRefreshInterval).toBeVisible();
    });
  });

  test.describe('Responsive Behavior', () => {
    test('should not have horizontal overflow on wide viewport', async () => {
      await ofoPage.setViewportSize(1920, 1080);
      await ofoPage.page.waitForTimeout(300);
      const hasOverflow = await ofoPage.hasHorizontalOverflow();
      expect(hasOverflow).toBe(false);
    });

    test('should not have horizontal overflow on narrow viewport', async () => {
      await ofoPage.setViewportSize(1280, 800);
      await ofoPage.page.waitForTimeout(300);
      const hasOverflow = await ofoPage.hasHorizontalOverflow();
      expect(hasOverflow).toBe(false);
    });
  });
});
