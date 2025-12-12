/**
 * UI Consistency - Cross-Screen E2E Tests
 *
 * Tests that UI elements have consistent styling across all 7 screens.
 * Uses threshold-based failure (max 5 inconsistencies before failing).
 *
 * @tags @audit @consistency
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { StyleAudit, EXPECTED_STYLES, CONSISTENCY_THRESHOLDS } from '../../helpers/style-audit.helper.js';
import { SCREENS, ELEMENT_SELECTORS } from '../../helpers/ui-consistency.constants.js';

test.describe('Cross-Screen UI Consistency @audit', () => {

  test.describe('Element Presence Across Screens', () => {

    test('navigation header is present on all screens @audit', async ({ authenticatedPage }) => {
      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const header = authenticatedPage.locator('[data-testid="kite-header"]');
        await expect(header).toBeVisible({ timeout: 5000 });
      }
    });

    test('navigation items are consistent across all screens @audit', async ({ authenticatedPage }) => {
      const navCounts = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const navItems = authenticatedPage.locator('[data-testid="kite-header-nav"] a');
        const count = await navItems.count();
        navCounts.push({ screen: screen.name, count });
      }

      // All screens should have the same number of nav items
      const uniqueCounts = [...new Set(navCounts.map(n => n.count))];
      expect(uniqueCounts.length).toBe(1);
    });

  });

  test.describe('Button Consistency', () => {

    test('primary buttons have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('buttons', {
          primary: ELEMENT_SELECTORS.buttons.primary,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.buttons);
        const report = audit.generateReport(comparison);

        if (report.summary.totalIssues > 0) {
          console.log('Button inconsistencies:', JSON.stringify(report.byElement, null, 2));
        }

        expect(report.summary.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
        expect(report.summary.totalIssues).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxInconsistencies);
      }
    });

    test('secondary buttons have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('buttons', {
          secondary: ELEMENT_SELECTORS.buttons.secondary,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.buttons);
        expect(comparison.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
      }
    });

  });

  test.describe('Card Consistency', () => {

    test('cards have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('cards', {
          default: ELEMENT_SELECTORS.cards.default,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.cards);
        const report = audit.generateReport(comparison);

        if (report.summary.totalIssues > 0) {
          console.log('Card inconsistencies:', JSON.stringify(report.byElement, null, 2));
        }

        expect(report.summary.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
      }
    });

  });

  test.describe('Input Consistency', () => {

    test('text inputs have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('inputs', {
          text: ELEMENT_SELECTORS.inputs.text,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.inputs);
        expect(comparison.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
      }
    });

    test('select dropdowns have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('inputs', {
          select: ELEMENT_SELECTORS.inputs.select,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.inputs);
        expect(comparison.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
      }
    });

  });

  test.describe('Typography Consistency', () => {

    test('page headers have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('headers', {
          page: ELEMENT_SELECTORS.headers.page,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.headers);
        const report = audit.generateReport(comparison);

        if (report.summary.totalIssues > 0) {
          console.log('Header inconsistencies:', JSON.stringify(report.byElement, null, 2));
        }

        expect(report.summary.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
      }
    });

    test('section headers have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('headers', {
          section: ELEMENT_SELECTORS.headers.section,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.headers);
        expect(comparison.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
      }
    });

  });

  test.describe('Table Consistency', () => {

    test('table headers have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('tables', {
          header: ELEMENT_SELECTORS.tables.header,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.tables);
        const report = audit.generateReport(comparison);

        if (report.summary.totalIssues > 0) {
          console.log('Table header inconsistencies:', JSON.stringify(report.byElement, null, 2));
        }

        expect(report.summary.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
      }
    });

    test('table cells have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('tables', {
          cell: ELEMENT_SELECTORS.tables.cell,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.tables);
        expect(comparison.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
      }
    });

  });

  test.describe('Badge Consistency', () => {

    test('success badges have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('badges', {
          success: ELEMENT_SELECTORS.badges.success,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.badges);
        expect(comparison.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
      }
    });

    test('danger badges have consistent styling across screens @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('badges', {
          danger: ELEMENT_SELECTORS.badges.danger,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.badges);
        expect(comparison.criticalCount).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);
      }
    });

  });

  test.describe('Navigation Consistency', () => {

    test('navigation items have consistent font styling @audit', async ({ authenticatedPage }) => {
      const fontData = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const navItems = authenticatedPage.locator('[data-testid="kite-header-nav"] a');
        const count = await navItems.count();

        if (count > 0) {
          const fontSize = await navItems.first().evaluate(el =>
            window.getComputedStyle(el).fontSize
          );
          const fontWeight = await navItems.first().evaluate(el =>
            window.getComputedStyle(el).fontWeight
          );
          fontData.push({ screen: screen.name, fontSize, fontWeight });
        }
      }

      // All screens should have same nav font styling
      const uniqueFontSizes = [...new Set(fontData.map(d => d.fontSize))];
      expect(uniqueFontSizes.length).toBe(1);
    });

    test('active nav item styling is consistent @audit', async ({ authenticatedPage }) => {
      const activeStyles = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const activeItem = authenticatedPage.locator('[data-testid="kite-header-nav"] a.active');
        const count = await activeItem.count();

        if (count > 0) {
          const color = await activeItem.first().evaluate(el =>
            window.getComputedStyle(el).color
          );
          activeStyles.push({ screen: screen.name, color });
        }
      }

      // All active nav items should have same color
      if (activeStyles.length >= 2) {
        const uniqueColors = [...new Set(activeStyles.map(s => s.color))];
        expect(uniqueColors.length).toBe(1);
      }
    });

  });

  test.describe('Full Cross-Screen Audit', () => {

    test('comprehensive UI consistency check @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const allResults = {
        buttons: [],
        cards: [],
        inputs: [],
        headers: [],
        tables: [],
      };

      // Collect all styles from all screens
      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        // Buttons
        const buttonStyles = await audit.collectElementStyles('buttons', {
          primary: ELEMENT_SELECTORS.buttons.primary,
          secondary: ELEMENT_SELECTORS.buttons.secondary,
          success: ELEMENT_SELECTORS.buttons.success,
          danger: ELEMENT_SELECTORS.buttons.danger,
        });
        if (Object.keys(buttonStyles).length > 0) {
          allResults.buttons.push({ screen: screen.name, styles: buttonStyles });
        }

        // Cards
        const cardStyles = await audit.collectElementStyles('cards', {
          default: ELEMENT_SELECTORS.cards.default,
        });
        if (Object.keys(cardStyles).length > 0) {
          allResults.cards.push({ screen: screen.name, styles: cardStyles });
        }

        // Inputs
        const inputStyles = await audit.collectElementStyles('inputs', {
          text: ELEMENT_SELECTORS.inputs.text,
          select: ELEMENT_SELECTORS.inputs.select,
        });
        if (Object.keys(inputStyles).length > 0) {
          allResults.inputs.push({ screen: screen.name, styles: inputStyles });
        }

        // Headers
        const headerStyles = await audit.collectElementStyles('headers', {
          page: ELEMENT_SELECTORS.headers.page,
          section: ELEMENT_SELECTORS.headers.section,
        });
        if (Object.keys(headerStyles).length > 0) {
          allResults.headers.push({ screen: screen.name, styles: headerStyles });
        }

        // Tables
        const tableStyles = await audit.collectElementStyles('tables', {
          header: ELEMENT_SELECTORS.tables.header,
          row: ELEMENT_SELECTORS.tables.row,
          cell: ELEMENT_SELECTORS.tables.cell,
        });
        if (Object.keys(tableStyles).length > 0) {
          allResults.tables.push({ screen: screen.name, styles: tableStyles });
        }
      }

      // Compare all element types
      let totalIssues = 0;
      let criticalIssues = 0;

      for (const [elementType, results] of Object.entries(allResults)) {
        if (results.length >= 2) {
          const expectedStyles = EXPECTED_STYLES[elementType];
          if (expectedStyles) {
            const comparison = audit.compareStyles(results, expectedStyles);
            totalIssues += comparison.totalIssues;
            criticalIssues += comparison.criticalCount;

            if (comparison.totalIssues > 0) {
              console.log(`${elementType} issues:`, comparison.totalIssues);
            }
          }
        }
      }

      // Final assertions
      expect(criticalIssues).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxCriticalIssues);

      if (totalIssues > CONSISTENCY_THRESHOLDS.warnThreshold) {
        console.warn(`Warning: ${totalIssues} total inconsistencies found across screens`);
      }

      expect(totalIssues).toBeLessThanOrEqual(CONSISTENCY_THRESHOLDS.maxInconsistencies * 5); // 5 element types
    });

  });

});
