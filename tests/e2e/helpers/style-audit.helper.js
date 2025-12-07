/**
 * Style Audit Helper - CSS validation and accessibility checks
 *
 * Usage:
 *   import { StyleAudit, DESIGN_TOKENS } from '../helpers/style-audit.helper.js';
 *   const audit = new StyleAudit(page);
 *   await audit.validateFonts();
 *   await audit.validateColors();
 *   await audit.checkAccessibility();
 */

import AxeBuilder from '@axe-core/playwright';

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
   * Check contrast specifically for text elements
   */
  async checkContrast() {
    const builder = new AxeBuilder({ page: this.page })
      .withTags(['cat.color']); // Color contrast checks only

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
}

/**
 * Quick audit function for use in tests
 */
export async function quickStyleAudit(page, options = {}) {
  const audit = new StyleAudit(page);
  return await audit.runFullAudit(options);
}
