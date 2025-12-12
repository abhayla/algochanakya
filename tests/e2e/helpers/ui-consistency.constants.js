/**
 * UI Consistency Constants
 *
 * Expected styles for cross-screen consistency testing.
 * Values extracted from kite-theme.css and component styles.
 */

// =============================================================================
// EXPECTED STYLES BY ELEMENT TYPE
// =============================================================================

export const EXPECTED_STYLES = {
  /**
   * Button Styles
   * From kite-theme.css: .kite-btn, .strategy-btn
   */
  buttons: {
    primary: {
      backgroundColor: ['#387ed1', 'rgb(56, 126, 209)', '#2c6cb8', 'rgb(44, 108, 184)'],
      color: ['#ffffff', 'rgb(255, 255, 255)', 'white'],
      borderRadius: ['3px', '4px'],
      padding: ['6px 12px', '8px 16px'],
      fontSize: ['12px', '13px'],
      fontWeight: ['500', '600'],
    },
    secondary: {
      backgroundColor: ['#ffffff', 'rgb(255, 255, 255)', 'white', '#f5f5f5'],
      color: ['#394046', 'rgb(57, 64, 70)', '#212529'],
      borderRadius: ['3px', '4px'],
      border: /1px solid/,
    },
    success: {
      backgroundColor: ['#00b386', 'rgb(0, 179, 134)', '#009973'],
      color: ['#ffffff', 'rgb(255, 255, 255)', 'white'],
      borderRadius: ['3px', '4px'],
    },
    danger: {
      backgroundColor: ['#e53935', 'rgb(229, 57, 53)', '#cc3333', '#e74c3c'],
      color: ['#ffffff', 'rgb(255, 255, 255)', 'white'],
      borderRadius: ['3px', '4px'],
    },
  },

  /**
   * Card Styles
   * From kite-theme.css: .kite-card, .strategy-summary-card
   */
  cards: {
    default: {
      backgroundColor: ['#ffffff', 'rgb(255, 255, 255)', 'white'],
      borderRadius: ['4px', '8px', '0.5rem'],
      boxShadow: /0\s+\d+px\s+\d+px|none/,
      border: /1px solid/,
    },
    summary: {
      backgroundColor: ['#ffffff', 'rgb(255, 255, 255)'],
      borderRadius: ['4px'],
      padding: ['16px 20px', '16px', '20px'],
    },
  },

  /**
   * Form Input Styles
   * From kite-theme.css: .kite-input, .strategy-input
   */
  inputs: {
    text: {
      borderColor: ['#e8e8e8', 'rgb(232, 232, 232)', '#e0e0e0', 'rgb(224, 224, 224)'],
      borderRadius: ['3px', '4px'],
      fontSize: ['12px', '13px'],
      padding: ['6px 10px', '8px 12px'],
    },
    select: {
      borderColor: ['#e8e8e8', 'rgb(232, 232, 232)', '#e0e0e0'],
      borderRadius: ['3px', '4px'],
      backgroundColor: ['#ffffff', 'rgb(255, 255, 255)', 'white'],
    },
    focus: {
      borderColor: ['#387ed1', 'rgb(56, 126, 209)'],
    },
  },

  /**
   * Header/Typography Styles
   * From kite-theme.css: various font sizes
   */
  headers: {
    page: {
      fontSize: ['18px', '20px', '24px', '1.125rem', '1.25rem', '1.5rem'],
      fontWeight: ['600', '700'],
      color: ['#394046', 'rgb(57, 64, 70)', '#212529', 'rgb(33, 37, 41)'],
    },
    section: {
      fontSize: ['14px', '15px', '16px', '0.875rem', '1rem'],
      fontWeight: ['500', '600'],
      color: ['#394046', 'rgb(57, 64, 70)', '#212529'],
    },
    label: {
      fontSize: ['11px', '12px', '0.75rem'],
      fontWeight: ['500', '600'],
      color: ['#6c757d', 'rgb(108, 117, 125)', '#9aa3ad'],
      textTransform: ['uppercase', 'none'],
    },
  },

  /**
   * Table Styles
   * From kite-theme.css: .kite-table, .strategy-table
   */
  tables: {
    header: {
      backgroundColor: ['#fafafa', 'rgb(250, 250, 250)', '#fafbfc', '#f5f5f5'],
      fontWeight: ['500', '600'],
      fontSize: ['11px', '12px'],
      color: ['#6c757d', 'rgb(108, 117, 125)'],
      textTransform: ['uppercase'],
    },
    row: {
      borderBottom: /1px solid/,
      padding: ['8px 12px', '10px 12px'],
    },
    cell: {
      fontSize: ['12px', '13px'],
      color: ['#394046', 'rgb(57, 64, 70)'],
    },
    hover: {
      backgroundColor: ['#fafafa', '#f0f4f8', '#f5f8fa'],
    },
  },

  /**
   * Badge/Tag Styles
   * From kite-theme.css: .tag-buy, .tag-sell, .tag-ce, .tag-pe
   */
  badges: {
    success: {
      backgroundColor: /green|#00b386|#22c55e|#e6f9f4|rgb\(0,\s*179,\s*134\)/i,
      color: ['#ffffff', 'white', '#00875a'],
      borderRadius: ['4px', '0.25rem'],
    },
    danger: {
      backgroundColor: /red|#e53935|#ef4444|#ffebee|rgb\(229,\s*57,\s*53\)/i,
      color: ['#ffffff', 'white', '#c62828'],
      borderRadius: ['4px', '0.25rem'],
    },
    buy: {
      backgroundColor: ['#e3f2fd', 'rgb(227, 242, 253)'],
      color: ['#1565c0', 'rgb(21, 101, 192)'],
    },
    sell: {
      backgroundColor: ['#fff3e0', 'rgb(255, 243, 224)'],
      color: ['#e65100', 'rgb(230, 81, 0)'],
    },
    ce: {
      backgroundColor: ['#e6f9f4', 'rgb(230, 249, 244)'],
      color: ['#00875a', 'rgb(0, 135, 90)'],
    },
    pe: {
      backgroundColor: ['#ffebee', 'rgb(255, 235, 238)'],
      color: ['#c62828', 'rgb(198, 40, 40)'],
    },
  },

  /**
   * Modal Styles
   */
  modals: {
    overlay: {
      backgroundColor: /rgba\(0,\s*0,\s*0,\s*0\.[3-7]\)/,
    },
    container: {
      backgroundColor: ['#ffffff', 'rgb(255, 255, 255)', 'white'],
      borderRadius: ['4px', '8px', '0.5rem'],
      boxShadow: /0\s+\d+px\s+\d+px/,
    },
  },

  /**
   * Navigation Styles
   * From KiteHeader.vue
   */
  navigation: {
    item: {
      fontSize: ['13px'],
      color: ['#6c757d', 'rgb(108, 117, 125)'],
      padding: ['8px 16px'],
      borderRadius: ['3px'],
    },
    itemActive: {
      color: ['#387ed1', 'rgb(56, 126, 209)'],
      fontWeight: ['500'],
    },
    itemHover: {
      backgroundColor: ['#f5f5f5', 'rgb(245, 245, 245)'],
      color: ['#212529', 'rgb(33, 37, 41)'],
    },
  },

  /**
   * Profit/Loss Colors
   */
  semantic: {
    profit: {
      color: ['#00b386', 'rgb(0, 179, 134)', '#22c55e', '#16a34a'],
    },
    loss: {
      color: ['#e53935', 'rgb(229, 57, 53)', '#ef4444', '#dc2626', '#e74c3c'],
    },
    muted: {
      color: ['#9aa3ad', 'rgb(154, 163, 173)', '#6c757d', 'rgb(108, 117, 125)'],
    },
  },
};

// =============================================================================
// ELEMENT SELECTORS
// =============================================================================

export const ELEMENT_SELECTORS = {
  buttons: {
    primary: [
      '[data-testid*="-btn"]',
      'button[class*="primary"]',
      'button[class*="bg-blue"]',
      '.kite-btn-primary',
      '.strategy-btn-primary',
    ].join(', '),
    secondary: [
      'button[class*="secondary"]',
      'button[class*="outline"]',
      '.kite-btn-outline',
      '.strategy-btn-outline',
    ].join(', '),
    success: [
      'button[class*="success"]',
      'button[class*="bg-green"]',
      '.kite-btn-success',
      '.strategy-btn-success',
    ].join(', '),
    danger: [
      'button[class*="danger"]',
      'button[class*="bg-red"]',
      '.kite-btn-danger',
      '.strategy-btn-danger',
    ].join(', '),
  },

  cards: {
    default: [
      '[data-testid*="-card"]',
      '.kite-card',
      '.strategy-summary-card',
      '.bg-white.rounded',
      '.bg-white.shadow',
    ].join(', '),
  },

  inputs: {
    text: 'input[type="text"], input[type="number"], input:not([type])',
    select: 'select, .kite-select, .strategy-select',
    checkbox: 'input[type="checkbox"]',
  },

  headers: {
    page: 'h1, [data-testid*="-title"], [data-testid*="-header"]',
    section: 'h2, h3, [data-testid*="-section"]',
    label: '.label, [class*="label"], th',
  },

  tables: {
    container: 'table, .kite-table, .strategy-table, [data-testid*="-table"]',
    header: 'thead, th',
    row: 'tbody tr, tr',
    cell: 'td',
  },

  badges: {
    success: '.bg-green, [class*="success"], .tag-ce',
    danger: '.bg-red, [class*="danger"], .tag-pe',
    buy: '.tag-buy, [class*="buy"]',
    sell: '.tag-sell, [class*="sell"]',
  },

  modals: {
    overlay: '[class*="modal-overlay"], [class*="backdrop"], [role="dialog"]',
    container: '[class*="modal-content"], [class*="modal-container"], [role="dialog"] > div',
  },

  navigation: {
    item: '[data-testid^="kite-header-nav-"]',
  },
};

// =============================================================================
// SCREENS CONFIGURATION
// =============================================================================

export const SCREENS = [
  { name: 'Dashboard', path: '/dashboard', requiresAuth: true },
  { name: 'Watchlist', path: '/watchlist', requiresAuth: true },
  { name: 'Positions', path: '/positions', requiresAuth: true },
  { name: 'Option Chain', path: '/optionchain', requiresAuth: true },
  { name: 'Strategy Builder', path: '/strategy', requiresAuth: true },
  { name: 'Strategy Library', path: '/strategies', requiresAuth: true },
  { name: 'AutoPilot', path: '/autopilot', requiresAuth: true },
];

// =============================================================================
// THRESHOLD CONFIGURATION
// =============================================================================

export const CONSISTENCY_THRESHOLDS = {
  // Failure thresholds
  maxInconsistencies: 5,        // Total inconsistencies before test fails
  maxCriticalIssues: 0,         // Critical issues cause immediate failure
  warnThreshold: 3,             // Log warning if exceeded

  // Value tolerance
  colorTolerance: 15,           // RGB value difference allowed (0-255)
  sizeTolerance: 2,             // Pixel difference allowed (e.g., 12px vs 13px)

  // Severity classification
  severity: {
    critical: ['fontFamily', 'backgroundColor'],
    major: ['fontSize', 'color', 'padding', 'borderRadius'],
    minor: ['boxShadow', 'margin', 'border'],
  },
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Check if a value matches expected values (array, regex, or string)
 */
export function matchesExpected(actual, expected) {
  if (!actual) return false;

  if (Array.isArray(expected)) {
    return expected.some(exp => normalizeValue(actual) === normalizeValue(exp));
  }

  if (expected instanceof RegExp) {
    return expected.test(actual);
  }

  return normalizeValue(actual) === normalizeValue(expected);
}

/**
 * Normalize CSS value for comparison
 */
export function normalizeValue(value) {
  if (!value) return null;
  return value.toString().toLowerCase().replace(/\s+/g, ' ').trim();
}

/**
 * Compare RGB color values with tolerance
 */
export function colorsMatch(color1, color2, tolerance = 15) {
  const rgb1 = parseRGB(color1);
  const rgb2 = parseRGB(color2);

  if (!rgb1 || !rgb2) return false;

  return (
    Math.abs(rgb1.r - rgb2.r) <= tolerance &&
    Math.abs(rgb1.g - rgb2.g) <= tolerance &&
    Math.abs(rgb1.b - rgb2.b) <= tolerance
  );
}

/**
 * Parse RGB or hex color to {r, g, b}
 */
export function parseRGB(color) {
  if (!color) return null;

  // RGB format: rgb(r, g, b)
  const rgbMatch = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (rgbMatch) {
    return { r: parseInt(rgbMatch[1]), g: parseInt(rgbMatch[2]), b: parseInt(rgbMatch[3]) };
  }

  // Hex format: #rrggbb
  const hexMatch = color.match(/^#([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
  if (hexMatch) {
    return { r: parseInt(hexMatch[1], 16), g: parseInt(hexMatch[2], 16), b: parseInt(hexMatch[3], 16) };
  }

  return null;
}

/**
 * Get severity level for a property
 */
export function getSeverity(property) {
  const { severity } = CONSISTENCY_THRESHOLDS;
  if (severity.critical.includes(property)) return 'critical';
  if (severity.major.includes(property)) return 'major';
  return 'minor';
}
