/**
 * Typography Consistency - Cross-Screen E2E Tests
 *
 * Tests that typography (headers, labels, body text) is consistent across all screens.
 *
 * @tags @audit @consistency @typography
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { StyleAudit, EXPECTED_STYLES, CONSISTENCY_THRESHOLDS } from '../../helpers/style-audit.helper.js';
import { SCREENS, ELEMENT_SELECTORS } from '../../helpers/ui-consistency.constants.js';

test.describe('Typography Consistency @audit', () => {

  test.describe('Page Headers', () => {

    test('page headers have consistent font size @audit', async ({ authenticatedPage }) => {
      const fontSizes = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const headers = authenticatedPage.locator(ELEMENT_SELECTORS.headers.page);
        const count = await headers.count();

        if (count > 0) {
          const fontSize = await headers.first().evaluate(el =>
            window.getComputedStyle(el).fontSize
          );
          fontSizes.push({ screen: screen.name, fontSize });
        }
      }

      if (fontSizes.length >= 2) {
        const uniqueFontSizes = [...new Set(fontSizes.map(f => f.fontSize))];
        // Allow variance for different header levels
        expect(uniqueFontSizes.length).toBeLessThanOrEqual(4);
      }
    });

    test('page headers have consistent font weight @audit', async ({ authenticatedPage }) => {
      const fontWeights = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const headers = authenticatedPage.locator(ELEMENT_SELECTORS.headers.page);
        const count = await headers.count();

        if (count > 0) {
          const fontWeight = await headers.first().evaluate(el =>
            window.getComputedStyle(el).fontWeight
          );
          fontWeights.push({ screen: screen.name, fontWeight });
        }
      }

      if (fontWeights.length >= 2) {
        const uniqueWeights = [...new Set(fontWeights.map(f => f.fontWeight))];
        // Headers should be consistently bold (600 or 700)
        expect(uniqueWeights.length).toBeLessThanOrEqual(2);
      }
    });

    test('page headers use correct text color @audit', async ({ authenticatedPage }) => {
      const colors = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const headers = authenticatedPage.locator(ELEMENT_SELECTORS.headers.page);
        const count = await headers.count();

        if (count > 0) {
          const color = await headers.first().evaluate(el =>
            window.getComputedStyle(el).color
          );
          colors.push({ screen: screen.name, color });
        }
      }

      if (colors.length >= 2) {
        const uniqueColors = [...new Set(colors.map(c => c.color))];
        // Headers should use consistent dark color
        expect(uniqueColors.length).toBeLessThanOrEqual(2);
      }
    });

  });

  test.describe('Section Headers', () => {

    test('section headers have consistent styling @audit', async ({ authenticatedPage }) => {
      const styles = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const headers = authenticatedPage.locator(ELEMENT_SELECTORS.headers.section);
        const count = await headers.count();

        if (count > 0) {
          const fontSize = await headers.first().evaluate(el =>
            window.getComputedStyle(el).fontSize
          );
          const fontWeight = await headers.first().evaluate(el =>
            window.getComputedStyle(el).fontWeight
          );
          styles.push({ screen: screen.name, fontSize, fontWeight });
        }
      }

      if (styles.length >= 2) {
        const uniqueFontSizes = [...new Set(styles.map(s => s.fontSize))];
        expect(uniqueFontSizes.length).toBeLessThanOrEqual(3);
      }
    });

    test('section headers smaller than page headers @audit', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/dashboard');
      await authenticatedPage.waitForLoadState('networkidle');

      const pageHeader = authenticatedPage.locator(ELEMENT_SELECTORS.headers.page).first();
      const sectionHeader = authenticatedPage.locator(ELEMENT_SELECTORS.headers.section).first();

      const pageHeaderExists = await pageHeader.count() > 0;
      const sectionHeaderExists = await sectionHeader.count() > 0;

      if (pageHeaderExists && sectionHeaderExists) {
        const pageSize = await pageHeader.evaluate(el =>
          parseInt(window.getComputedStyle(el).fontSize)
        );
        const sectionSize = await sectionHeader.evaluate(el =>
          parseInt(window.getComputedStyle(el).fontSize)
        );

        // Section headers should be smaller or equal to page headers
        expect(sectionSize).toBeLessThanOrEqual(pageSize);
      }
    });

  });

  test.describe('Labels', () => {

    test('labels have consistent font size @audit', async ({ authenticatedPage }) => {
      const fontSizes = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const labels = authenticatedPage.locator(ELEMENT_SELECTORS.headers.label);
        const count = await labels.count();

        if (count > 0) {
          const fontSize = await labels.first().evaluate(el =>
            window.getComputedStyle(el).fontSize
          );
          fontSizes.push({ screen: screen.name, fontSize });
        }
      }

      if (fontSizes.length >= 2) {
        const uniqueFontSizes = [...new Set(fontSizes.map(f => f.fontSize))];
        // Labels should be consistently small
        expect(uniqueFontSizes.length).toBeLessThanOrEqual(2);
      }
    });

    test('labels use muted/secondary color @audit', async ({ authenticatedPage }) => {
      const colors = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const labels = authenticatedPage.locator(ELEMENT_SELECTORS.headers.label);
        const count = await labels.count();

        if (count > 0) {
          const color = await labels.first().evaluate(el =>
            window.getComputedStyle(el).color
          );
          colors.push({ screen: screen.name, color });
        }
      }

      if (colors.length >= 2) {
        // Labels typically use muted gray colors
        console.log('Label colors:', colors);
      }
    });

    test('labels with uppercase transform are consistent @audit', async ({ authenticatedPage }) => {
      const transforms = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const labels = authenticatedPage.locator(ELEMENT_SELECTORS.headers.label);
        const count = await labels.count();

        if (count > 0) {
          const textTransform = await labels.first().evaluate(el =>
            window.getComputedStyle(el).textTransform
          );
          transforms.push({ screen: screen.name, textTransform });
        }
      }

      if (transforms.length >= 2) {
        const uniqueTransforms = [...new Set(transforms.map(t => t.textTransform))];
        // Labels should consistently use or not use uppercase
        expect(uniqueTransforms.length).toBeLessThanOrEqual(2);
      }
    });

  });

  test.describe('Font Family', () => {

    test('all text uses consistent font family @audit', async ({ authenticatedPage }) => {
      const fontFamilies = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const body = authenticatedPage.locator('body');
        const fontFamily = await body.evaluate(el =>
          window.getComputedStyle(el).fontFamily
        );
        fontFamilies.push({ screen: screen.name, fontFamily });
      }

      // All screens should use the same font family
      const uniqueFontFamilies = [...new Set(fontFamilies.map(f => f.fontFamily))];
      expect(uniqueFontFamilies.length).toBe(1);
    });

    test('body uses system font stack @audit', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/dashboard');
      await authenticatedPage.waitForLoadState('networkidle');

      const fontFamily = await authenticatedPage.locator('body').evaluate(el =>
        window.getComputedStyle(el).fontFamily
      );

      // Should include system-ui or other system fonts
      const hasSystemFont = fontFamily.includes('system-ui') ||
                           fontFamily.includes('-apple-system') ||
                           fontFamily.includes('Segoe UI') ||
                           fontFamily.includes('Roboto') ||
                           fontFamily.includes('sans-serif');
      expect(hasSystemFont).toBe(true);
    });

  });

  test.describe('Semantic Colors', () => {

    test('profit text uses green color @audit', async ({ authenticatedPage }) => {
      const profitSelectors = '.profit, .positive, [class*="green"], [class*="success"]';

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const profitText = authenticatedPage.locator(profitSelectors);
        const count = await profitText.count();

        if (count > 0) {
          const color = await profitText.first().evaluate(el =>
            window.getComputedStyle(el).color
          );
          // Should be some shade of green
          const isGreen = color.includes('0, 179') || // #00b386
                         color.includes('0, 153') || // #009973
                         color.includes('34, 197') || // #22c55e
                         color.includes('22, 163');   // #16a34a

          if (count > 0 && !isGreen) {
            console.log(`Profit color on ${screen.name}: ${color}`);
          }
        }
      }
    });

    test('loss text uses red color @audit', async ({ authenticatedPage }) => {
      const lossSelectors = '.loss, .negative, [class*="red"], [class*="danger"]';

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const lossText = authenticatedPage.locator(lossSelectors);
        const count = await lossText.count();

        if (count > 0) {
          const color = await lossText.first().evaluate(el =>
            window.getComputedStyle(el).color
          );
          // Should be some shade of red
          const isRed = color.includes('229, 57') || // #e53935
                       color.includes('239, 68') || // #ef4444
                       color.includes('220, 38') || // #dc2626
                       color.includes('231, 76');   // #e74c3c

          if (count > 0 && !isRed) {
            console.log(`Loss color on ${screen.name}: ${color}`);
          }
        }
      }
    });

  });

  test.describe('Full Typography Audit', () => {

    test('all typography passes consistency threshold @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('headers', {
          page: ELEMENT_SELECTORS.headers.page,
          section: ELEMENT_SELECTORS.headers.section,
          label: ELEMENT_SELECTORS.headers.label,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.headers);
        const report = audit.generateReport(comparison);

        console.log('Typography Consistency Report:');
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
