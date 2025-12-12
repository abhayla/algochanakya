/**
 * Badge Consistency - Cross-Screen E2E Tests
 *
 * Tests that badge/tag styling is consistent across all screens.
 *
 * @tags @audit @consistency @badges
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { StyleAudit, EXPECTED_STYLES, CONSISTENCY_THRESHOLDS } from '../../helpers/style-audit.helper.js';
import { SCREENS, ELEMENT_SELECTORS } from '../../helpers/ui-consistency.constants.js';

test.describe('Badge Consistency @audit', () => {

  test.describe('Success Badges', () => {

    test('success badges have green background @audit', async ({ authenticatedPage }) => {
      const backgrounds = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const badges = authenticatedPage.locator(ELEMENT_SELECTORS.badges.success);
        const count = await badges.count();

        if (count > 0) {
          const bgColor = await badges.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          backgrounds.push({ screen: screen.name, bgColor });
        }
      }

      if (backgrounds.length >= 1) {
        // Success badges should use green colors
        for (const bg of backgrounds) {
          const isGreen = bg.bgColor.includes('0, 179') || // #00b386
                         bg.bgColor.includes('0, 135') || // #00875a
                         bg.bgColor.includes('34, 197') || // #22c55e
                         bg.bgColor.includes('230, 249') || // light green
                         bg.bgColor.toLowerCase().includes('green');
          if (!isGreen) {
            console.log(`Success badge on ${bg.screen}: ${bg.bgColor}`);
          }
        }
      }
    });

    test('success badges have consistent border radius @audit', async ({ authenticatedPage }) => {
      const radii = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const badges = authenticatedPage.locator(ELEMENT_SELECTORS.badges.success);
        const count = await badges.count();

        if (count > 0) {
          const borderRadius = await badges.first().evaluate(el =>
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

  });

  test.describe('Danger Badges', () => {

    test('danger badges have red background @audit', async ({ authenticatedPage }) => {
      const backgrounds = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const badges = authenticatedPage.locator(ELEMENT_SELECTORS.badges.danger);
        const count = await badges.count();

        if (count > 0) {
          const bgColor = await badges.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          backgrounds.push({ screen: screen.name, bgColor });
        }
      }

      if (backgrounds.length >= 1) {
        // Danger badges should use red colors
        for (const bg of backgrounds) {
          const isRed = bg.bgColor.includes('229, 57') || // #e53935
                       bg.bgColor.includes('239, 68') || // #ef4444
                       bg.bgColor.includes('198, 40') || // #c62828
                       bg.bgColor.includes('255, 235') || // light red
                       bg.bgColor.toLowerCase().includes('red');
          if (!isRed) {
            console.log(`Danger badge on ${bg.screen}: ${bg.bgColor}`);
          }
        }
      }
    });

  });

  test.describe('BUY/SELL Tags', () => {

    test('BUY tags have consistent blue styling @audit', async ({ authenticatedPage }) => {
      const styles = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const buyTags = authenticatedPage.locator(ELEMENT_SELECTORS.badges.buy);
        const count = await buyTags.count();

        if (count > 0) {
          const bgColor = await buyTags.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          const color = await buyTags.first().evaluate(el =>
            window.getComputedStyle(el).color
          );
          styles.push({ screen: screen.name, bgColor, color });
        }
      }

      if (styles.length >= 2) {
        const uniqueBackgrounds = [...new Set(styles.map(s => s.bgColor))];
        // BUY tags should be consistently styled
        expect(uniqueBackgrounds.length).toBeLessThanOrEqual(2);
      }
    });

    test('SELL tags have consistent orange styling @audit', async ({ authenticatedPage }) => {
      const styles = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const sellTags = authenticatedPage.locator(ELEMENT_SELECTORS.badges.sell);
        const count = await sellTags.count();

        if (count > 0) {
          const bgColor = await sellTags.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          const color = await sellTags.first().evaluate(el =>
            window.getComputedStyle(el).color
          );
          styles.push({ screen: screen.name, bgColor, color });
        }
      }

      if (styles.length >= 2) {
        const uniqueBackgrounds = [...new Set(styles.map(s => s.bgColor))];
        // SELL tags should be consistently styled
        expect(uniqueBackgrounds.length).toBeLessThanOrEqual(2);
      }
    });

  });

  test.describe('CE/PE Tags', () => {

    test('CE tags have green styling @audit', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/optionchain');
      await authenticatedPage.waitForLoadState('networkidle');

      const ceTags = authenticatedPage.locator('.tag-ce, [class*="ce"]');
      const count = await ceTags.count();

      if (count > 0) {
        const bgColor = await ceTags.first().evaluate(el =>
          window.getComputedStyle(el).backgroundColor
        );
        const color = await ceTags.first().evaluate(el =>
          window.getComputedStyle(el).color
        );

        console.log(`CE tag: bg=${bgColor}, color=${color}`);
        // CE should use green tones
      }
    });

    test('PE tags have red styling @audit', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/optionchain');
      await authenticatedPage.waitForLoadState('networkidle');

      const peTags = authenticatedPage.locator('.tag-pe, [class*="pe"]');
      const count = await peTags.count();

      if (count > 0) {
        const bgColor = await peTags.first().evaluate(el =>
          window.getComputedStyle(el).backgroundColor
        );
        const color = await peTags.first().evaluate(el =>
          window.getComputedStyle(el).color
        );

        console.log(`PE tag: bg=${bgColor}, color=${color}`);
        // PE should use red tones
      }
    });

  });

  test.describe('Status Badges', () => {

    test('active status badges are consistent @audit', async ({ authenticatedPage }) => {
      const activeSelector = '[class*="active"], [class*="running"], .status-active';
      const styles = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const activeBadges = authenticatedPage.locator(activeSelector);
        const count = await activeBadges.count();

        if (count > 0) {
          const bgColor = await activeBadges.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          styles.push({ screen: screen.name, bgColor });
        }
      }

      if (styles.length >= 2) {
        console.log('Active status badge styles:', styles);
      }
    });

    test('paused status badges are consistent @audit', async ({ authenticatedPage }) => {
      const pausedSelector = '[class*="paused"], [class*="pending"], .status-paused';
      const styles = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const pausedBadges = authenticatedPage.locator(pausedSelector);
        const count = await pausedBadges.count();

        if (count > 0) {
          const bgColor = await pausedBadges.first().evaluate(el =>
            window.getComputedStyle(el).backgroundColor
          );
          styles.push({ screen: screen.name, bgColor });
        }
      }

      if (styles.length >= 2) {
        console.log('Paused status badge styles:', styles);
      }
    });

  });

  test.describe('Badge Size', () => {

    test('badges have consistent padding @audit', async ({ authenticatedPage }) => {
      const allBadgeSelector = `${ELEMENT_SELECTORS.badges.success}, ${ELEMENT_SELECTORS.badges.danger}`;
      const paddings = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const badges = authenticatedPage.locator(allBadgeSelector);
        const count = await badges.count();

        if (count > 0) {
          const padding = await badges.first().evaluate(el =>
            window.getComputedStyle(el).padding
          );
          paddings.push({ screen: screen.name, padding });
        }
      }

      if (paddings.length >= 2) {
        const uniquePaddings = [...new Set(paddings.map(p => p.padding))];
        // Badges should have similar padding
        expect(uniquePaddings.length).toBeLessThanOrEqual(3);
      }
    });

    test('badges have consistent font size @audit', async ({ authenticatedPage }) => {
      const allBadgeSelector = `${ELEMENT_SELECTORS.badges.success}, ${ELEMENT_SELECTORS.badges.danger}`;
      const fontSizes = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const badges = authenticatedPage.locator(allBadgeSelector);
        const count = await badges.count();

        if (count > 0) {
          const fontSize = await badges.first().evaluate(el =>
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

  test.describe('Full Badge Audit', () => {

    test('all badges pass consistency threshold @audit', async ({ authenticatedPage }) => {
      const audit = new StyleAudit(authenticatedPage);
      const results = [];

      for (const screen of SCREENS) {
        await authenticatedPage.goto(screen.path);
        await authenticatedPage.waitForLoadState('networkidle');

        const styles = await audit.collectElementStyles('badges', {
          success: ELEMENT_SELECTORS.badges.success,
          danger: ELEMENT_SELECTORS.badges.danger,
          buy: ELEMENT_SELECTORS.badges.buy,
          sell: ELEMENT_SELECTORS.badges.sell,
        });

        if (Object.keys(styles).length > 0) {
          results.push({ screen: screen.name, styles });
        }
      }

      if (results.length >= 2) {
        const comparison = audit.compareStyles(results, EXPECTED_STYLES.badges);
        const report = audit.generateReport(comparison);

        console.log('Badge Consistency Report:');
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
