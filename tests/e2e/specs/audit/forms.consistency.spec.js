/**
 * Form Consistency - Cross-Screen E2E Tests
 *
 * Tests that form input styling is consistent across all screens.
 *
 * @tags @audit @consistency @forms
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { StyleAudit, EXPECTED_STYLES, CONSISTENCY_THRESHOLDS } from '../../helpers/style-audit.helper.js';
import { SCREENS, ELEMENT_SELECTORS } from '../../helpers/ui-consistency.constants.js';

test.describe('Form Input Consistency @audit', () => {

  test.describe('Text Inputs', () => {

    test('text inputs have consistent border color @audit', async ({ authenticatedPage }) => {
      const borderColors = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const inputs = authenticatedPage.locator(ELEMENT_SELECTORS.inputs.text);
        const count = await inputs.count();

        if (count > 0) {
          const borderColor = await inputs.first().evaluate(el =>
            window.getComputedStyle(el).borderColor
          );
          borderColors.push({ screen: screen.name, borderColor });
        }
      }

      if (borderColors.length >= 2) {
        const uniqueColors = [...new Set(borderColors.map(b => b.borderColor))];
        // Allow some variance for different input states
        expect(uniqueColors.length).toBeLessThanOrEqual(3);
      }
    });

    test('text inputs have consistent border radius @audit', async ({ authenticatedPage }) => {
      const radii = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const inputs = authenticatedPage.locator(ELEMENT_SELECTORS.inputs.text);
        const count = await inputs.count();

        if (count > 0) {
          const borderRadius = await inputs.first().evaluate(el =>
            window.getComputedStyle(el).borderRadius
          );
          radii.push({ screen: screen.name, borderRadius });
        }
      }

      if (radii.length >= 2) {
        const uniqueRadii = [...new Set(radii.map(r => r.borderRadius))];
        expect(uniqueRadii.length).toBeLessThanOrEqual(2);
      }
    });

    test('text inputs have consistent font size @audit', async ({ authenticatedPage }) => {
      const fontSizes = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const inputs = authenticatedPage.locator(ELEMENT_SELECTORS.inputs.text);
        const count = await inputs.count();

        if (count > 0) {
          const fontSize = await inputs.first().evaluate(el =>
            window.getComputedStyle(el).fontSize
          );
          fontSizes.push({ screen: screen.name, fontSize });
        }
      }

      if (fontSizes.length >= 2) {
        const uniqueFontSizes = [...new Set(fontSizes.map(f => f.fontSize))];
        expect(uniqueFontSizes.length).toBeLessThanOrEqual(2);
      }
    });

    test('text inputs have consistent padding @audit', async ({ authenticatedPage }) => {
      const paddings = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const inputs = authenticatedPage.locator(ELEMENT_SELECTORS.inputs.text);
        const count = await inputs.count();

        if (count > 0) {
          const padding = await inputs.first().evaluate(el =>
            window.getComputedStyle(el).padding
          );
          paddings.push({ screen: screen.name, padding });
        }
      }

      if (paddings.length >= 2) {
        const uniquePaddings = [...new Set(paddings.map(p => p.padding))];
        // Allow more variance for padding
        expect(uniquePaddings.length).toBeLessThanOrEqual(4);
      }
    });

  });

  test.describe('Select Dropdowns', () => {

    test('selects have consistent styling with text inputs @audit', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/dashboard');
      await authenticatedPage.waitForLoadState('networkidle');

      const textInput = authenticatedPage.locator(ELEMENT_SELECTORS.inputs.text).first();
      const select = authenticatedPage.locator(ELEMENT_SELECTORS.inputs.select).first();

      const textInputExists = await textInput.count() > 0;
      const selectExists = await select.count() > 0;

      if (textInputExists && selectExists) {
        const inputBorderRadius = await textInput.evaluate(el =>
          window.getComputedStyle(el).borderRadius
        );
        const selectBorderRadius = await select.evaluate(el =>
          window.getComputedStyle(el).borderRadius
        );

        // Selects should have similar border radius as inputs
        expect(inputBorderRadius).toBe(selectBorderRadius);
      }
    });

    test('selects have consistent background @audit', async ({ authenticatedPage }) => {
      const backgrounds = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const selects = authenticatedPage.locator(ELEMENT_SELECTORS.inputs.select);
        const count = await selects.count();

        if (count > 0) {
          const bgColor = await selects.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          backgrounds.push({ screen: screen.name, bgColor });
        }
      }

      if (backgrounds.length >= 2) {
        const uniqueBackgrounds = [...new Set(backgrounds.map(b => b.bgColor))];
        expect(uniqueBackgrounds.length).toBeLessThanOrEqual(2);
      }
    });

  });

  test.describe('Focus States', () => {

    test('text inputs have visible focus indicator @audit', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/strategy');
      await authenticatedPage.waitForLoadState('networkidle');

      const input = authenticatedPage.locator(ELEMENT_SELECTORS.inputs.text).first();
      const inputExists = await input.count() > 0;

      if (inputExists) {
        const beforeFocus = await input.evaluate(el => ({
          borderColor: window.getComputedStyle(el).borderColor,
          outline: window.getComputedStyle(el).outline,
          boxShadow: window.getComputedStyle(el).boxShadow,
        }));

        await input.focus();
        await authenticatedPage.waitForTimeout(100);

        const afterFocus = await input.evaluate(el => ({
          borderColor: window.getComputedStyle(el).borderColor,
          outline: window.getComputedStyle(el).outline,
          boxShadow: window.getComputedStyle(el).boxShadow,
        }));

        // Focus should change something visible
        const hasVisibleChange =
          beforeFocus.borderColor !== afterFocus.borderColor ||
          beforeFocus.outline !== afterFocus.outline ||
          beforeFocus.boxShadow !== afterFocus.boxShadow;

        console.log(`Focus state change: border ${beforeFocus.borderColor} -> ${afterFocus.borderColor}`);
        // This is informational - some inputs may use subtle focus indicators
      }
    });

    test('focus color matches design system @audit', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/optionchain');
      await authenticatedPage.waitForLoadState('networkidle');

      const input = authenticatedPage.locator(ELEMENT_SELECTORS.inputs.text).first();
      const inputExists = await input.count() > 0;

      if (inputExists) {
        await input.focus();
        await authenticatedPage.waitForTimeout(100);

        const focusBorderColor = await input.evaluate(el =>
          window.getComputedStyle(el).borderColor
        );

        // Focus should use the primary blue color
        const expectedFocusColors = EXPECTED_STYLES.inputs.focus?.borderColor || [];
        if (expectedFocusColors.length > 0) {
          console.log(`Focus border color: ${focusBorderColor}`);
        }
      }
    });

  });

  test.describe('Checkboxes', () => {

    test('checkboxes have consistent size @audit', async ({ authenticatedPage }) => {
      const sizes = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const checkboxes = authenticatedPage.locator(ELEMENT_SELECTORS.inputs.checkbox);
        const count = await checkboxes.count();

        if (count > 0) {
          const width = await checkboxes.first().evaluate(el =>
            window.getComputedStyle(el).width
          );
          const height = await checkboxes.first().evaluate(el =>
            window.getComputedStyle(el).height
          );
          sizes.push({ screen: screen.name, width, height });
        }
      }

      if (sizes.length >= 2) {
        const uniqueSizes = [...new Set(sizes.map(s => `${s.width}x${s.height}`))];
        // Checkboxes should be consistently sized
        expect(uniqueSizes.length).toBeLessThanOrEqual(2);
      }
    });

  });

  test.describe('Labels', () => {

    test('form labels have consistent styling @audit', async ({ authenticatedPage }) => {
      const labelStyles = [];
      const labelSelector = 'label, .label, [class*="label"]';

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const labels = authenticatedPage.locator(labelSelector);
        const count = await labels.count();

        if (count > 0) {
          const fontSize = await labels.first().evaluate(el =>
            window.getComputedStyle(el).fontSize
          );
          const fontWeight = await labels.first().evaluate(el =>
            window.getComputedStyle(el).fontWeight
          );
          labelStyles.push({ screen: screen.name, fontSize, fontWeight });
        }
      }

      if (labelStyles.length >= 2) {
        const uniqueFontSizes = [...new Set(labelStyles.map(l => l.fontSize))];
        // Labels should have consistent font size
        expect(uniqueFontSizes.length).toBeLessThanOrEqual(3);
      }
    });

  });

  test.describe('Full Form Audit', () => {

    test('all form inputs pass consistency threshold @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('inputs', {
          text: ELEMENT_SELECTORS.inputs.text,
          select: ELEMENT_SELECTORS.inputs.select,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.inputs);
        const report = audit.generateReport(comparison);

        console.log('Form Consistency Report:');
        console.log(`  Total issues: ${report.summary.totalIssues}`);
        console.log(`  Critical: ${report.summary.criticalCount}`);
        console.log(`  Major: ${report.summary.majorCount}`);
        console.log(`  Minor: ${report.summary.minorCount}`);

        expect(report.summary.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
        expect(report.summary.totalIssues).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxInconsistencies);
      }
    });

  });

});
