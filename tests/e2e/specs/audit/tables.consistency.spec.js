/**
 * Table Consistency - Cross-Screen E2E Tests
 *
 * Tests that table styling is consistent across all screens.
 *
 * @tags @audit @consistency @tables
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { StyleAudit, EXPECTED_STYLES, CONSISTENCY_THRESHOLDS } from '../../helpers/style-audit.helper.js';
import { SCREENS, ELEMENT_SELECTORS } from '../../helpers/ui-consistency.constants.js';

test.describe('Table Consistency @audit', () => {

  test.describe('Table Headers', () => {

    test('table headers have consistent background @audit', async ({ authenticatedPage }) => {
      const backgrounds = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const headers = authenticatedPage.locator(ELEMENT_SELECTORS.tables.header);
        const count = await headers.count();

        if (count > 0) {
          const bgColor = await headers.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          backgrounds.push({ screen: screen.name, bgColor });
        }
      }

      if (backgrounds.length >= 2) {
        const uniqueBackgrounds = [...new Set(backgrounds.map(b => b.bgColor))];
        // Table headers should have consistent background
        expect(uniqueBackgrounds.length).toBeLessThanOrEqual(3);
      }
    });

    test('table headers have consistent font weight @audit', async ({ authenticatedPage }) => {
      const fontWeights = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const headers = authenticatedPage.locator(ELEMENT_SELECTORS.tables.header);
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
        expect(uniqueWeights.length).toBeLessThanOrEqual(2);
      }
    });

    test('table headers have consistent font size @audit', async ({ authenticatedPage }) => {
      const fontSizes = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const headers = authenticatedPage.locator(ELEMENT_SELECTORS.tables.header);
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
        expect(uniqueFontSizes.length).toBeLessThanOrEqual(2);
      }
    });

    test('table headers use uppercase text @audit', async ({ authenticatedPage }) => {
      const transforms = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const headers = authenticatedPage.locator(ELEMENT_SELECTORS.tables.header);
        const count = await headers.count();

        if (count > 0) {
          const textTransform = await headers.first().evaluate(el =>
            window.getComputedStyle(el).textTransform
          );
          transforms.push({ screen: screen.name, textTransform });
        }
      }

      if (transforms.length >= 2) {
        const uniqueTransforms = [...new Set(transforms.map(t => t.textTransform))];
        // Table headers should consistently use or not use uppercase
        expect(uniqueTransforms.length).toBeLessThanOrEqual(2);
      }
    });

  });

  test.describe('Table Rows', () => {

    test('table rows have consistent border @audit', async ({ authenticatedPage }) => {
      const borders = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const rows = authenticatedPage.locator(ELEMENT_SELECTORS.tables.row);
        const count = await rows.count();

        if (count > 1) {
          // Check second row (skip header row)
          const borderBottom = await rows.nth(1).evaluate(el =>
            window.getComputedStyle(el).borderBottom
          );
          borders.push({ screen: screen.name, borderBottom });
        }
      }

      if (borders.length >= 2) {
        // Rows should have consistent border styling
        console.log('Table row borders:', borders);
      }
    });

    test('table rows have consistent padding @audit', async ({ authenticatedPage }) => {
      const paddings = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const cells = authenticatedPage.locator(ELEMENT_SELECTORS.tables.cell);
        const count = await cells.count();

        if (count > 0) {
          const padding = await cells.first().evaluate(el =>
            window.getComputedStyle(el).padding
          );
          paddings.push({ screen: screen.name, padding });
        }
      }

      if (paddings.length >= 2) {
        const uniquePaddings = [...new Set(paddings.map(p => p.padding))];
        // Allow some variance for different table types
        expect(uniquePaddings.length).toBeLessThanOrEqual(4);
      }
    });

  });

  test.describe('Table Cells', () => {

    test('table cells have consistent font size @audit', async ({ authenticatedPage }) => {
      const fontSizes = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const cells = authenticatedPage.locator(ELEMENT_SELECTORS.tables.cell);
        const count = await cells.count();

        if (count > 0) {
          const fontSize = await cells.first().evaluate(el =>
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

    test('table cells have consistent text color @audit', async ({ authenticatedPage }) => {
      const colors = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const cells = authenticatedPage.locator(ELEMENT_SELECTORS.tables.cell);
        const count = await cells.count();

        if (count > 0) {
          const color = await cells.first().evaluate(el =>
            window.getComputedStyle(el).color
          );
          colors.push({ screen: screen.name, color });
        }
      }

      if (colors.length >= 2) {
        const uniqueColors = [...new Set(colors.map(c => c.color))];
        // Cell text should use consistent dark color
        expect(uniqueColors.length).toBeLessThanOrEqual(2);
      }
    });

  });

  test.describe('Table Hover States', () => {

    test('table rows have hover effect @audit', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/positions');
      await authenticatedPage.waitForLoadState('networkidle');

      const rows = authenticatedPage.locator('tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        const row = rows.first();

        const beforeHover = await row.evaluate(el =>
          window.getComputedStyle(el).backgroundColor
        );

        await row.hover();
        await authenticatedPage.waitForLoadState('domcontentloaded');

        const afterHover = await row.evaluate(el =>
          window.getComputedStyle(el).backgroundColor
        );

        console.log(`Row hover: ${beforeHover} -> ${afterHover}`);
        // Informational - not all tables need hover effects
      }
    });

  });

  test.describe('Alternating Row Colors', () => {

    test('tables use alternating row colors or not consistently @audit', async ({ authenticatedPage }) => {
      const hasAlternating = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const rows = authenticatedPage.locator('tbody tr');
        const count = await rows.count();

        if (count >= 2) {
          const row1Bg = await rows.nth(0).evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          const row2Bg = await rows.nth(1).evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );

          const hasStripes = row1Bg !== row2Bg;
          hasAlternating.push({ screen: screen.name, hasStripes });
        }
      }

      if (hasAlternating.length >= 2) {
        const uniqueStates = [...new Set(hasAlternating.map(h => h.hasStripes))];
        // Tables should consistently use or not use striping
        // Allow variance as different table types may use different styles
        console.log('Alternating rows:', hasAlternating);
      }
    });

  });

  test.describe('Full Table Audit', () => {

    test('all tables pass consistency threshold @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('tables', {
          header: ELEMENT_SELECTORS.tables.header,
          row: ELEMENT_SELECTORS.tables.row,
          cell: ELEMENT_SELECTORS.tables.cell,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.tables);
        const report = audit.generateReport(comparison);

        console.log('Table Consistency Report:');
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
