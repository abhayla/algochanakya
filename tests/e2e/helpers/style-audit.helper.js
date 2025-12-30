/**
 * Style Audit Helper - CSS validation and accessibility checks
 *
 * Usage:
 *   import { StyleAudit, DESIGN_TOKENS } from '../helpers/style-audit.helper.js';
 *   const audit = new StyleAudit(page);
 *   await audit.validateFonts();
 *   await audit.validateColors();
 *   await audit.checkAccessibility();
 *
 * Cross-screen consistency:
 *   await audit.collectElementStyles('buttons', { primary: 'button.primary' });
 *   audit.compareStyles(collectedStyles, EXPECTED_STYLES.buttons);
 */

import AxeBuilder from '@axe-core/playwright';
import {
  EXPECTED_STYLES,
  CONSISTENCY_THRESHOLDS,
  matchesExpected,
  colorsMatch,
  getSeverity,
} from './ui-consistency.constants.js';

/**
 * Design tokens extracted from Tailwind config and global CSS
 * These define the expected styles for the application
 */
export const DESIGN_TOKENS = {
  fonts: {
    primary: ['system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
  },
  colors: {
    primary: {
      50: '#f0f9ff',
      100: '#e0f2fe',
      200: '#bae6fd',
      300: '#7dd3fc',
      400: '#38bdf8',
      500: '#0ea5e9',
      600: '#0284c7',
      700: '#0369a1',
      800: '#075985',
      900: '#0c4a6e',
    },
    // Tailwind defaults used in app
    green: { 500: '#22c55e', 600: '#16a34a' }, // profit colors
    red: { 500: '#ef4444', 600: '#dc2626' },   // loss colors
    gray: { 50: '#f9fafb', 100: '#f3f4f6', 500: '#6b7280', 900: '#111827' },
  },
  spacing: {
    // Common Tailwind spacing values (in pixels)
    1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32,
  },
  fontSizes: {
    xs: '12px', sm: '14px', base: '16px', lg: '18px', xl: '20px', '2xl': '24px',
  },
};

export class StyleAudit {
  constructor(page) {
    this.page = page;
    this.errors = [];
  }

  /**
   * Clear errors for fresh audit
   */
  reset() {
    this.errors = [];
  }

  /**
   * Get computed style of an element
   */
  async getComputedStyle(selector, property) {
    return await this.page.evaluate(({ sel, prop }) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      return window.getComputedStyle(el)[prop];
    }, { sel: selector, prop: property });
  }

  /**
   * Validate that body uses the correct font family
   */
  async validateFonts() {
    const bodyFont = await this.getComputedStyle('body', 'fontFamily');
    if (!bodyFont) {
      this.errors.push('Could not read body font-family');
      return false;
    }

    // Check if system-ui or one of fallbacks is present
    const hasValidFont = DESIGN_TOKENS.fonts.primary.some(font =>
      bodyFont.toLowerCase().includes(font.toLowerCase().replace(/['"]/g, ''))
    );

    if (!hasValidFont) {
      this.errors.push(`Invalid body font: ${bodyFont}. Expected system-ui stack.`);
      return false;
    }
    return true;
  }

  /**
   * Validate color usage on specific elements
   * @param {Array<{selector: string, property: string, expectedColors: string[]}>} rules
   */
  async validateColors(rules = []) {
    for (const rule of rules) {
      const color = await this.getComputedStyle(rule.selector, rule.property);
      if (!color) continue;

      const normalized = this.normalizeColor(color);
      const isValid = rule.expectedColors.some(expected =>
        this.normalizeColor(expected) === normalized
      );

      if (!isValid) {
        this.errors.push(
          `Color mismatch on ${rule.selector}.${rule.property}: got ${color}, expected one of ${rule.expectedColors.join(', ')}`
        );
      }
    }
    return this.errors.length === 0;
  }

  /**
   * Normalize color to hex format for comparison
   */
  normalizeColor(color) {
    if (!color) return null;
    // Simple RGB to Hex conversion
    const rgbMatch = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    if (rgbMatch) {
      const [, r, g, b] = rgbMatch;
      return `#${[r, g, b].map(x => parseInt(x).toString(16).padStart(2, '0')).join('')}`;
    }
    return color.toLowerCase();
  }

  /**
   * Run axe-core accessibility audit
   * @param {Object} options - AxeBuilder options
   * @returns {Object} { violations, passes }
   */
  async checkAccessibility(options = {}) {
    const builder = new AxeBuilder({ page: this.page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa']); // WCAG 2.1 AA compliance

    // Exclude dynamic content if specified
    if (options.exclude) {
      options.exclude.forEach(selector => builder.exclude(selector));
    }

    const results = await builder.analyze();

    // Add violations to errors
    results.violations.forEach(violation => {
      this.errors.push(
        `A11y: ${violation.id} - ${violation.description} (${violation.nodes.length} occurrences)`
      );
    });

    return {
      violations: results.violations,
      passes: results.passes,
      violationCount: results.violations.length,
    };
  }

  /**
   * Check contrast specifically for text elements (WCAG AA compliance - 4.5:1 ratio)
   * Note: Uses 'color-contrast' rule which checks WCAG AA, not 'color-contrast-enhanced' (WCAG AAA)
   */
  async checkContrast() {
    const builder = new AxeBuilder({ page: this.page })
      .withRules(['color-contrast']); // WCAG AA contrast check only (4.5:1 ratio)

    const results = await builder.analyze();
    return {
      violations: results.violations,
      hasContrastIssues: results.violations.length > 0,
    };
  }

  /**
   * Validate no horizontal overflow on page
   */
  async checkNoHorizontalOverflow() {
    const hasOverflow = await this.page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });

    if (hasOverflow) {
      this.errors.push('Page has horizontal overflow');
    }
    return !hasOverflow;
  }

  /**
   * Validate Tailwind spacing classes are applied correctly
   * @param {Array<{selector: string, property: string, expectedValue: string}>} rules
   */
  async validateSpacing(rules = []) {
    for (const rule of rules) {
      const value = await this.getComputedStyle(rule.selector, rule.property);
      if (value !== rule.expectedValue) {
        this.errors.push(
          `Spacing mismatch on ${rule.selector}.${rule.property}: got ${value}, expected ${rule.expectedValue}`
        );
      }
    }
    return this.errors.length === 0;
  }

  /**
   * Run full style audit and return summary
   */
  async runFullAudit(options = {}) {
    this.reset();

    const results = {
      fonts: await this.validateFonts(),
      overflow: await this.checkNoHorizontalOverflow(),
      accessibility: await this.checkAccessibility(options),
      contrast: await this.checkContrast(),
      errors: this.errors,
    };

    return {
      passed: this.errors.length === 0,
      ...results,
    };
  }

  /**
   * Get all errors from this audit
   */
  getErrors() {
    return this.errors;
  }

  // ===========================================================================
  // CROSS-SCREEN CONSISTENCY METHODS
  // ===========================================================================

  /**
   * Collect element styles from the current page
   * @param {string} elementType - Type of element (buttons, cards, inputs, etc.)
   * @param {Object} selectors - Object mapping variant names to CSS selectors
   * @returns {Object} Styles for each variant found on the page
   */
  async collectElementStyles(elementType, selectors) {
    const styles = {};

    for (const [variant, selector] of Object.entries(selectors)) {
      try {
        const elements = this.page.locator(selector);
        const count = await elements.count();

        if (count > 0) {
          // Get styles from the first matching element
          styles[variant] = await this.extractStyles(elements.first());
          styles[variant]._count = count;
          styles[variant]._selector = selector;
        }
      } catch (error) {
        // Element not found on this page, skip
        continue;
      }
    }

    return styles;
  }

  /**
   * Extract all relevant CSS properties from an element
   * @param {Locator} element - Playwright locator
   * @returns {Object} CSS properties
   */
  async extractStyles(element) {
    return await element.evaluate(el => {
      const computed = window.getComputedStyle(el);
      return {
        // Colors
        backgroundColor: computed.backgroundColor,
        color: computed.color,
        borderColor: computed.borderColor,

        // Typography
        fontSize: computed.fontSize,
        fontWeight: computed.fontWeight,
        fontFamily: computed.fontFamily,
        textTransform: computed.textTransform,

        // Spacing
        padding: computed.padding,
        margin: computed.margin,

        // Borders & Shadows
        borderRadius: computed.borderRadius,
        borderWidth: computed.borderWidth,
        boxShadow: computed.boxShadow,

        // Layout
        display: computed.display,
        alignItems: computed.alignItems,
        justifyContent: computed.justifyContent,
      };
    });
  }

  /**
   * Compare collected styles against expected styles
   * @param {Array} screenResults - Array of { screen, styles } objects
   * @param {Object} expectedStyles - Expected styles from EXPECTED_STYLES
   * @returns {Object} Comparison results with inconsistencies
   */
  compareStyles(screenResults, expectedStyles) {
    const inconsistencies = [];
    const screenComparisons = [];

    for (const { screen, styles } of screenResults) {
      const screenIssues = [];

      for (const [variant, variantStyles] of Object.entries(styles)) {
        if (!expectedStyles[variant]) continue;

        const expected = expectedStyles[variant];

        for (const [property, expectedValue] of Object.entries(expected)) {
          const actualValue = variantStyles[property];

          if (!actualValue) continue;

          // Check if actual matches expected
          const matches = this.valueMatches(actualValue, expectedValue, property);

          if (!matches) {
            const severity = getSeverity(property);
            screenIssues.push({
              screen,
              variant,
              property,
              expected: expectedValue,
              actual: actualValue,
              severity,
            });
          }
        }
      }

      screenComparisons.push({
        screen,
        issues: screenIssues,
        passed: screenIssues.length === 0,
      });

      inconsistencies.push(...screenIssues);
    }

    // Cross-screen comparison: check if same element varies across screens
    const crossScreenIssues = this.detectCrossScreenVariance(screenResults);
    inconsistencies.push(...crossScreenIssues);

    return {
      inconsistencies,
      screenComparisons,
      totalIssues: inconsistencies.length,
      criticalCount: inconsistencies.filter(i => i.severity === 'critical').length,
      majorCount: inconsistencies.filter(i => i.severity === 'major').length,
      minorCount: inconsistencies.filter(i => i.severity === 'minor').length,
      passed: inconsistencies.length <= CONSISTENCY_THRESHOLDS.maxInconsistencies,
      passedCritical: inconsistencies.filter(i => i.severity === 'critical').length <= CONSISTENCY_THRESHOLDS.maxCriticalIssues,
    };
  }

  /**
   * Check if an actual value matches the expected value
   * @param {string} actual - Actual CSS value
   * @param {*} expected - Expected value (string, array, or regex)
   * @param {string} property - CSS property name
   * @returns {boolean}
   */
  valueMatches(actual, expected, property) {
    // Skip internal properties
    if (property.startsWith('_')) return true;

    // Color properties need special handling with tolerance
    const colorProperties = ['backgroundColor', 'color', 'borderColor'];
    if (colorProperties.includes(property)) {
      if (Array.isArray(expected)) {
        return expected.some(exp => colorsMatch(actual, exp, CONSISTENCY_THRESHOLDS.colorTolerance));
      }
      if (expected instanceof RegExp) {
        return expected.test(actual);
      }
      return colorsMatch(actual, expected, CONSISTENCY_THRESHOLDS.colorTolerance);
    }

    // Use the matchesExpected helper for other properties
    return matchesExpected(actual, expected);
  }

  /**
   * Detect variance in styles across different screens
   * @param {Array} screenResults - Array of { screen, styles } objects
   * @returns {Array} Cross-screen variance issues
   */
  detectCrossScreenVariance(screenResults) {
    const issues = [];
    const propertyValues = {}; // { 'buttons.primary.fontSize': { '/dashboard': '13px', '/watchlist': '14px' } }

    for (const { screen, styles } of screenResults) {
      for (const [variant, variantStyles] of Object.entries(styles)) {
        for (const [property, value] of Object.entries(variantStyles)) {
          if (property.startsWith('_')) continue;

          const key = `${variant}.${property}`;
          if (!propertyValues[key]) {
            propertyValues[key] = {};
          }
          propertyValues[key][screen] = value;
        }
      }
    }

    // Check for variance
    for (const [key, screens] of Object.entries(propertyValues)) {
      const values = Object.values(screens);
      const uniqueValues = [...new Set(values.map(v => this.normalizeForComparison(v)))];

      if (uniqueValues.length > 1) {
        const [variant, property] = key.split('.');
        const severity = getSeverity(property);

        // Only report if not a minor issue
        if (severity !== 'minor') {
          issues.push({
            type: 'cross-screen-variance',
            variant,
            property,
            values: screens,
            severity,
            message: `${key} varies across screens: ${JSON.stringify(screens)}`,
          });
        }
      }
    }

    return issues;
  }

  /**
   * Normalize a CSS value for comparison
   * @param {string} value - CSS value
   * @returns {string} Normalized value
   */
  normalizeForComparison(value) {
    if (!value) return '';
    return value.toString().toLowerCase().replace(/\s+/g, ' ').trim();
  }

  /**
   * Generate a detailed consistency report
   * @param {Object} comparisonResults - Results from compareStyles
   * @returns {Object} Formatted report
   */
  generateReport(comparisonResults) {
    const { inconsistencies, screenComparisons, totalIssues, criticalCount, majorCount, minorCount } = comparisonResults;

    // Group by element type
    const byElement = {};
    const byScreen = {};

    for (const issue of inconsistencies) {
      const element = issue.variant || 'unknown';
      const screen = issue.screen || 'cross-screen';

      if (!byElement[element]) byElement[element] = [];
      byElement[element].push(issue);

      if (!byScreen[screen]) byScreen[screen] = [];
      byScreen[screen].push(issue);
    }

    return {
      summary: {
        totalIssues,
        criticalCount,
        majorCount,
        minorCount,
        passed: comparisonResults.passed,
        passedCritical: comparisonResults.passedCritical,
      },
      byElement,
      byScreen,
      screenComparisons,
      details: inconsistencies,
    };
  }

  /**
   * Run a full cross-screen consistency check
   * @param {Array} screens - Array of { name, path } objects
   * @param {string} elementType - Element type to check
   * @param {Object} selectors - CSS selectors for element variants
   * @param {Object} expectedStyles - Expected styles
   * @returns {Object} Full consistency report
   */
  async runCrossScreenAudit(screens, elementType, selectors, expectedStyles) {
    const results = [];

    for (const screen of screens) {
      await this.page.goto(screen.path);
      await this.page.waitForLoadState('networkidle');

      const styles = await this.collectElementStyles(elementType, selectors);
      results.push({ screen: screen.name, path: screen.path, styles });
    }

    const comparison = this.compareStyles(results, expectedStyles);
    return this.generateReport(comparison);
  }
}

// ===========================================================================
// EXPORTED CONSTANTS FROM UI-CONSISTENCY
// ===========================================================================

export { EXPECTED_STYLES, CONSISTENCY_THRESHOLDS };

/**
 * Quick audit function for use in tests
 */
export async function quickStyleAudit(page, options = {}) {
  const audit = new StyleAudit(page);
  return await audit.runFullAudit(options);
}
