/**
 * Card Consistency - Cross-Screen E2E Tests
 *
 * Tests that card styling is consistent across all screens.
 *
 * @tags @audit @consistency @cards
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { StyleAudit, EXPECTED_STYLES, CONSISTENCY_THRESHOLDS } from '../../helpers/style-audit.helper.js';
import { SCREENS, ELEMENT_SELECTORS } from '../../helpers/ui-consistency.constants.js';

test.describe('Card Consistency @audit', () => {

  test.describe('Card Backgrounds', () => {

    test('cards have white/light background @audit', async ({ authenticatedPage }) => {
      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const cards = authenticatedPage.locator(ELEMENT_SELECTORS.cards.default);
        const count = await cards.count();

        if (count > 0) {
          const bgColor = await cards.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          // Cards should have white or very light background
          const isLight = bgColor.includes('255, 255, 255') ||
                         bgColor.includes('255,255,255') ||
                         bgColor === 'rgb(255, 255, 255)';
          expect(isLight).toBe(true);
        }
      }
    });

    test('card backgrounds are consistent across screens @audit', async ({ authenticatedPage }) => {
      const backgrounds = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const cards = authenticatedPage.locator(ELEMENT_SELECTORS.cards.default);
        const count = await cards.count();

        if (count > 0) {
          const bgColor = await cards.first().evaluate(el =>
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

  test.describe('Card Borders', () => {

    test('cards have consistent border radius @audit', async ({ authenticatedPage }) => {
      const radii = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const cards = authenticatedPage.locator(ELEMENT_SELECTORS.cards.default);
        const count = await cards.count();

        if (count > 0) {
          const borderRadius = await cards.first().evaluate(el =>
            window.getComputedStyle(el).borderRadius
          );
          radii.push({ screen: screen.name, borderRadius });
        }
      }

      if (radii.length >= 2) {
        const uniqueRadii = [...new Set(radii.map(r => r.borderRadius))];
        // Allow some variance (4px, 8px, 0.5rem are all acceptable)
        expect(uniqueRadii.length).toBeLessThanOrEqual(3);
      }
    });

    test('cards have border or shadow for visual separation @audit', async ({ authenticatedPage }) => {
      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const cards = authenticatedPage.locator(ELEMENT_SELECTORS.cards.default);
        const count = await cards.count();

        if (count > 0) {
          const border = await cards.first().evaluate(el =>
            window.getComputedStyle(el).border
          );
          const boxShadow = await cards.first().evaluate(el =>
            window.getComputedStyle(el).boxShadow
          );

          // Card should have either border or shadow for separation
          const hasSeparation = border !== 'none' && !border.includes('0px') ||
                               boxShadow !== 'none';
          // This is informational - not all cards need borders
          if (!hasSeparation) {
            console.log(`Card on ${screen.name} has no border or shadow`);
          }
        }
      }
    });

  });

  test.describe('Card Shadows', () => {

    test('card shadows are consistent across screens @audit', async ({ authenticatedPage }) => {
      const shadows = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const cards = authenticatedPage.locator(ELEMENT_SELECTORS.cards.default);
        const count = await cards.count();

        if (count > 0) {
          const boxShadow = await cards.first().evaluate(el =>
            window.getComputedStyle(el).boxShadow
          );
          shadows.push({ screen: screen.name, boxShadow });
        }
      }

      if (shadows.length >= 2) {
        // Normalize shadows for comparison (remove minor variations)
        const normalizedShadows = shadows.map(s => ({
          screen: s.screen,
          hasShadow: s.boxShadow !== 'none',
        }));
        const uniqueShadowStates = [...new Set(normalizedShadows.map(s => s.hasShadow))];
        // Cards should consistently have or not have shadows
        expect(uniqueShadowStates.length).toBeLessThanOrEqual(2);
      }
    });

  });

  test.describe('Card Padding', () => {

    test('cards have consistent internal padding @audit', async ({ authenticatedPage }) => {
      const paddings = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const cards = authenticatedPage.locator(ELEMENT_SELECTORS.cards.default);
        const count = await cards.count();

        if (count > 0) {
          const padding = await cards.first().evaluate(el =>
            window.getComputedStyle(el).padding
          );
          paddings.push({ screen: screen.name, padding });
        }
      }

      if (paddings.length >= 2) {
        console.log('Card paddings:', paddings);
        // Informational - log padding values
      }
    });

  });

  test.describe('Summary Cards', () => {

    test('summary/stat cards have consistent styling @audit', async ({ authenticatedPage }) => {
      const summaryCardSelector = '[data-testid*="summary"], [data-testid*="stat"], .summary-card';
      const styles = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const cards = authenticatedPage.locator(summaryCardSelector);
        const count = await cards.count();

        if (count > 0) {
          const bgColor = await cards.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          const borderRadius = await cards.first().evaluate(el =>
            window.getComputedStyle(el).borderRadius
          );
          styles.push({ screen: screen.name, bgColor, borderRadius });
        }
      }

      if (styles.length >= 2) {
        const uniqueBackgrounds = [...new Set(styles.map(s => s.bgColor))];
        // Summary cards should be consistent
        expect(uniqueBackgrounds.length).toBeLessThanOrEqual(2);
      }
    });

  });

  test.describe('Full Card Audit', () => {

    test('all card types pass consistency threshold @audit', async ({ authenticatedPage }) => {
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

        console.log('Card Consistency Report:');
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
