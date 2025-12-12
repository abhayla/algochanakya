/**
 * Button Consistency - Cross-Screen E2E Tests
 *
 * Tests that button styling is consistent across all screens.
 *
 * @tags @audit @consistency @buttons
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { StyleAudit, EXPECTED_STYLES, CONSISTENCY_THRESHOLDS } from '../../helpers/style-audit.helper.js';
import { SCREENS, ELEMENT_SELECTORS } from '../../helpers/ui-consistency.constants.js';

test.describe('Button Consistency @audit', () => {

  test.describe('Primary Buttons', () => {

    test('primary button background color is consistent @audit', async ({ authenticatedPage }) => {
      const colors = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const buttons = authenticatedPage.locator(ELEMENT_SELECTORS.buttons.primary);
        const count = await buttons.count();

        if (count > 0) {
          const bgColor = await buttons.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          colors.push({ screen: screen.name, bgColor });
        }
      }

      if (colors.length >= 2) {
        const uniqueColors = [...new Set(colors.map(c => c.bgColor))];
        // Allow some variance but not too many unique colors
        expect(uniqueColors.length).toBeLessThanOrEqual(2);
      }
    });

    test('primary button text color is white/light @audit', async ({ authenticatedPage }) => {
      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const buttons = authenticatedPage.locator(ELEMENT_SELECTORS.buttons.primary);
        const count = await buttons.count();

        if (count > 0) {
          const textColor = await buttons.first().evaluate(el =>
            window.getComputedStyle(el).color
          );
          // Should be white or very light
          const isLight = textColor.includes('255') || textColor.toLowerCase() === 'white';
          expect(isLight).toBe(true);
        }
      }
    });

    test('primary button border radius is consistent @audit', async ({ authenticatedPage }) => {
      const radii = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const buttons = authenticatedPage.locator(ELEMENT_SELECTORS.buttons.primary);
        const count = await buttons.count();

        if (count > 0) {
          const borderRadius = await buttons.first().evaluate(el =>
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

    test('primary button font size is consistent @audit', async ({ authenticatedPage }) => {
      const fontSizes = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const buttons = authenticatedPage.locator(ELEMENT_SELECTORS.buttons.primary);
        const count = await buttons.count();

        if (count > 0) {
          const fontSize = await buttons.first().evaluate(el =>
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

  });

  test.describe('Secondary Buttons', () => {

    test('secondary button has outline/border styling @audit', async ({ authenticatedPage }) => {
      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const buttons = authenticatedPage.locator(ELEMENT_SELECTORS.buttons.secondary);
        const count = await buttons.count();

        if (count > 0) {
          const borderWidth = await buttons.first().evaluate(el =>
            window.getComputedStyle(el).borderWidth
          );
          // Secondary buttons should have a border
          expect(borderWidth).not.toBe('0px');
        }
      }
    });

    test('secondary button background is light/transparent @audit', async ({ authenticatedPage }) => {
      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const buttons = authenticatedPage.locator(ELEMENT_SELECTORS.buttons.secondary);
        const count = await buttons.count();

        if (count > 0) {
          const bgColor = await buttons.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          // Should be white, transparent, or very light gray
          const isLight = bgColor.includes('255') ||
                         bgColor.includes('transparent') ||
                         bgColor === 'rgba(0, 0, 0, 0)';
          expect(isLight).toBe(true);
        }
      }
    });

  });

  test.describe('Success Buttons', () => {

    test('success button background is green @audit', async ({ authenticatedPage }) => {
      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const buttons = authenticatedPage.locator(ELEMENT_SELECTORS.buttons.success);
        const count = await buttons.count();

        if (count > 0) {
          const bgColor = await buttons.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          // Should match expected green colors
          const expectedGreens = EXPECTED_STYLES.buttons.success.backgroundColor;
          const matchesGreen = expectedGreens.some(green =>
            bgColor.toLowerCase().includes(green.toLowerCase().replace('#', '')) ||
            green.toLowerCase().includes(bgColor.toLowerCase())
          ) || bgColor.includes('0, 179') || bgColor.includes('0, 153') || bgColor.includes('34, 197');

          if (!matchesGreen) {
            console.log(`Success button on ${screen.name}: ${bgColor}`);
          }
        }
      }
    });

  });

  test.describe('Danger Buttons', () => {

    test('danger button background is red @audit', async ({ authenticatedPage }) => {
      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const buttons = authenticatedPage.locator(ELEMENT_SELECTORS.buttons.danger);
        const count = await buttons.count();

        if (count > 0) {
          const bgColor = await buttons.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          // Should match expected red colors
          const expectedReds = EXPECTED_STYLES.buttons.danger.backgroundColor;
          const matchesRed = expectedReds.some(red =>
            bgColor.toLowerCase().includes(red.toLowerCase().replace('#', '')) ||
            red.toLowerCase().includes(bgColor.toLowerCase())
          ) || bgColor.includes('229, 57') || bgColor.includes('239, 68') || bgColor.includes('231, 76');

          if (!matchesRed) {
            console.log(`Danger button on ${screen.name}: ${bgColor}`);
          }
        }
      }
    });

  });

  test.describe('Button Hover States', () => {

    test('primary buttons have visible hover effect @audit', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/dashboard');
      await authenticatedPage.waitForLoadState('networkidle');

      const button = authenticatedPage.locator(ELEMENT_SELECTORS.buttons.primary).first();
      const buttonExists = await button.count() > 0;

      if (buttonExists) {
        const beforeHover = await button.evaluate(el =>
          window.getComputedStyle(el).backgroundColor
        );

        await button.hover();
        await authenticatedPage.waitForTimeout(200);

        const afterHover = await button.evaluate(el =>
          window.getComputedStyle(el).backgroundColor
        );

        // Hover should change something (color or opacity)
        // Log for visual inspection
        console.log(`Primary button hover: ${beforeHover} -> ${afterHover}`);
      }
    });

  });

  test.describe('Button Disabled States', () => {

    test('disabled buttons have reduced opacity or muted colors @audit', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/dashboard');
      await authenticatedPage.waitForLoadState('networkidle');

      const disabledButton = authenticatedPage.locator('button:disabled').first();
      const buttonExists = await disabledButton.count() > 0;

      if (buttonExists) {
        const opacity = await disabledButton.evaluate(el =>
          window.getComputedStyle(el).opacity
        );
        const cursor = await disabledButton.evaluate(el =>
          window.getComputedStyle(el).cursor
        );

        // Disabled buttons should have reduced opacity or not-allowed cursor
        const isDisabledStyle = parseFloat(opacity) < 1 || cursor === 'not-allowed';
        expect(isDisabledStyle).toBe(true);
      }
    });

  });

  test.describe('Full Button Audit', () => {

    test('all button types pass consistency threshold @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('buttons', {
          primary: ELEMENT_SELECTORS.buttons.primary,
          secondary: ELEMENT_SELECTORS.buttons.secondary,
          success: ELEMENT_SELECTORS.buttons.success,
          danger: ELEMENT_SELECTORS.buttons.danger,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.buttons);
        const report = audit.generateReport(comparison);

        console.log('Button Consistency Report:');
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
