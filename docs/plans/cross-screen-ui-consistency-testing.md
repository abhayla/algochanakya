# Plan: Cross-Screen UI/UX Consistency Testing

## Requirements Summary

| Requirement | Value |
|-------------|-------|
| **Scope** | All 7 screens (Dashboard, Watchlist, Positions, Option Chain, Strategy Builder, Strategy Library, AutoPilot) |
| **Elements** | Buttons, Cards, Inputs, Headers, Tables, Badges, Modals |
| **CSS Properties** | Colors, fonts, padding, margins, shadows, hover states |
| **Organization** | Industry best practices (centralized + per-element) |
| **Failure Mode** | Threshold-based (configurable) |

---

## Current State Analysis

### Existing Infrastructure
- **StyleAudit helper** (`tests/e2e/helpers/style-audit.helper.js`) - Has font, color, overflow validation
- **DESIGN_TOKENS** - Already defined in helper file
- **kite-theme.css** - CSS variables for colors, fonts, spacing
- **8 audit test files** - One per screen with basic checks

### Gap Analysis
| What Exists | What's Missing |
|-------------|----------------|
| Per-screen audit tests | Cross-screen consistency comparison |
| Basic font/overflow checks | Element-specific style verification |
| DESIGN_TOKENS object | Expected styles per element type |
| StyleAudit class | Cross-screen comparison methods |

---

## Implementation Plan

### Part 1: Define Expected Styles (Design Tokens)

**File:** `tests/e2e/helpers/ui-consistency.constants.js` (NEW)

Define expected CSS properties for each element type:

```javascript
export const EXPECTED_STYLES = {
  buttons: {
    primary: {
      backgroundColor: ['#387ed1', 'rgb(56, 126, 209)'],
      color: ['#ffffff', 'rgb(255, 255, 255)'],
      borderRadius: '3px',
      padding: '8px 16px',
      fontSize: '13px',
      fontWeight: ['500', '600'],
    },
    secondary: { /* ... */ },
    danger: { /* ... */ },
  },
  cards: {
    default: {
      backgroundColor: ['#ffffff', 'rgb(255, 255, 255)'],
      borderRadius: ['4px', '8px'],
      boxShadow: /0\s+\d+px\s+\d+px/,  // regex for shadow pattern
      padding: /\d+px/,
    },
  },
  inputs: {
    text: {
      borderColor: ['#e0e0e0', 'rgb(224, 224, 224)'],
      borderRadius: '3px',
      fontSize: ['12px', '13px'],
      padding: /\d+px/,
    },
  },
  headers: {
    page: {
      fontSize: ['18px', '20px', '24px'],
      fontWeight: ['600', '700'],
      color: ['#212529', '#394046'],
    },
    section: {
      fontSize: ['14px', '15px', '16px'],
      fontWeight: ['500', '600'],
    },
  },
  tables: {
    header: {
      backgroundColor: ['#f5f5f5', '#f9fafb'],
      fontWeight: ['500', '600'],
      fontSize: ['11px', '12px'],
    },
    row: {
      borderBottom: /1px solid/,
      padding: /\d+px/,
    },
  },
  badges: {
    success: {
      backgroundColor: /green|#00b386|#22c55e/i,
      color: ['#ffffff', '#fff'],
    },
    danger: {
      backgroundColor: /red|#e53935|#ef4444/i,
    },
  },
};

export const CONSISTENCY_THRESHOLDS = {
  maxInconsistencies: 5,        // Fail if more than 5 inconsistencies
  maxCriticalIssues: 0,         // Fail immediately on critical issues
  warnThreshold: 3,             // Warn if more than 3 inconsistencies
};
```

### Part 2: Enhance StyleAudit Helper

**File:** `tests/e2e/helpers/style-audit.helper.js` (MODIFY)

Add new methods for cross-screen comparison:

```javascript
// NEW: Collect element styles from a page
async collectElementStyles(elementType, selectors) {
  const styles = {};
  for (const [name, selector] of Object.entries(selectors)) {
    const elements = this.page.locator(selector);
    const count = await elements.count();
    if (count > 0) {
      styles[name] = await this.extractStyles(elements.first());
    }
  }
  return styles;
}

// NEW: Extract all relevant CSS properties
async extractStyles(element) {
  return element.evaluate(el => {
    const computed = window.getComputedStyle(el);
    return {
      backgroundColor: computed.backgroundColor,
      color: computed.color,
      borderRadius: computed.borderRadius,
      padding: computed.padding,
      margin: computed.margin,
      fontSize: computed.fontSize,
      fontWeight: computed.fontWeight,
      fontFamily: computed.fontFamily,
      boxShadow: computed.boxShadow,
      borderColor: computed.borderColor,
      borderWidth: computed.borderWidth,
    };
  });
}

// NEW: Compare styles across screens
compareStyles(screenStyles, expectedStyles) {
  const inconsistencies = [];
  // Implementation details...
  return { inconsistencies, passed: inconsistencies.length === 0 };
}

// NEW: Generate consistency report
generateReport(results) {
  return {
    totalScreens: results.length,
    totalInconsistencies: results.reduce((sum, r) => sum + r.inconsistencies.length, 0),
    byElement: /* grouped by element type */,
    byScreen: /* grouped by screen */,
  };
}
```

### Part 3: Create Cross-Screen Consistency Tests

**File:** `tests/e2e/specs/audit/ui-consistency.spec.js` (NEW)

```javascript
import { test, expect } from '../../fixtures/auth.fixture.js';
import { StyleAudit } from '../../helpers/style-audit.helper.js';
import { EXPECTED_STYLES, CONSISTENCY_THRESHOLDS } from '../../helpers/ui-consistency.constants.js';

const SCREENS = [
  { name: 'Dashboard', path: '/dashboard' },
  { name: 'Watchlist', path: '/watchlist' },
  { name: 'Positions', path: '/positions' },
  { name: 'Option Chain', path: '/optionchain' },
  { name: 'Strategy Builder', path: '/strategy' },
  { name: 'Strategy Library', path: '/strategies' },
  { name: 'AutoPilot', path: '/autopilot' },
];

const ELEMENT_SELECTORS = {
  buttons: {
    primary: '[data-testid*="-btn"], button.bg-blue, button[class*="primary"]',
    secondary: 'button.bg-gray, button[class*="secondary"]',
    danger: 'button.bg-red, button[class*="danger"]',
  },
  cards: {
    default: '[data-testid*="-card"], .bg-white.rounded, .shadow',
  },
  inputs: {
    text: 'input[type="text"], input[type="number"], input:not([type])',
  },
  // ... more selectors
};

test.describe('Cross-Screen UI Consistency @audit', () => {

  test('buttons have consistent styling across all screens', async ({ authenticatedPage }) => {
    const audit = new StyleAudit(authenticatedPage);
    const results = [];

    for (const screen of SCREENS) {
      await authenticatedPage.goto(screen.path);
      await authenticatedPage.waitForLoadState('domcontentloaded');

      const styles = await audit.collectElementStyles('buttons', ELEMENT_SELECTORS.buttons);
      results.push({ screen: screen.name, styles });
    }

    const comparison = audit.compareStyles(results, EXPECTED_STYLES.buttons);

    if (comparison.inconsistencies.length > 0) {
      console.log('Button inconsistencies:', JSON.stringify(comparison.inconsistencies, null, 2));
    }

    expect(comparison.inconsistencies.length).toBeLessThanOrEqual(
      CONSISTENCY_THRESHOLDS.maxInconsistencies
    );
  });

  // Similar tests for cards, inputs, headers, tables, badges, modals...
});
```

### Part 4: Create Element-Specific Test Files

Following industry best practices, create focused test files:

**File:** `tests/e2e/specs/audit/buttons.consistency.spec.js` (NEW)
- Primary button consistency
- Secondary button consistency
- Danger button consistency
- Button hover states
- Button disabled states

**File:** `tests/e2e/specs/audit/cards.consistency.spec.js` (NEW)
- Card backgrounds
- Card shadows
- Card borders
- Card padding

**File:** `tests/e2e/specs/audit/forms.consistency.spec.js` (NEW)
- Text input styling
- Select styling
- Checkbox styling
- Focus states
- Error states

**File:** `tests/e2e/specs/audit/typography.consistency.spec.js` (NEW)
- Page headers
- Section headers
- Body text
- Labels

**File:** `tests/e2e/specs/audit/tables.consistency.spec.js` (NEW)
- Table header styling
- Table row styling
- Table cell padding
- Alternating row colors

**File:** `tests/e2e/specs/audit/badges.consistency.spec.js` (NEW)
- Status badges (active, paused, completed)
- Tag styling (BUY/SELL, CE/PE)
- Color coding (profit/loss)

---

## Files to Create/Modify

### New Files (8)
| File | Purpose |
|------|---------|
| `tests/e2e/helpers/ui-consistency.constants.js` | Expected styles & thresholds |
| `tests/e2e/specs/audit/ui-consistency.spec.js` | Main cross-screen test |
| `tests/e2e/specs/audit/buttons.consistency.spec.js` | Button consistency |
| `tests/e2e/specs/audit/cards.consistency.spec.js` | Card consistency |
| `tests/e2e/specs/audit/forms.consistency.spec.js` | Form input consistency |
| `tests/e2e/specs/audit/typography.consistency.spec.js` | Typography consistency |
| `tests/e2e/specs/audit/tables.consistency.spec.js` | Table consistency |
| `tests/e2e/specs/audit/badges.consistency.spec.js` | Badge/tag consistency |

### Modified Files (2)
| File | Changes |
|------|---------|
| `tests/e2e/helpers/style-audit.helper.js` | Add cross-screen comparison methods |
| `package.json` | Add `test:consistency` script |

---

## Test Coverage Summary

| Element Type | Properties Checked | Screens |
|--------------|-------------------|---------|
| Buttons | backgroundColor, color, borderRadius, padding, fontSize, hover | 7 |
| Cards | backgroundColor, borderRadius, boxShadow, padding, border | 7 |
| Inputs | borderColor, borderRadius, fontSize, padding, focus | 7 |
| Headers | fontSize, fontWeight, color, margin | 7 |
| Tables | headerBg, rowBorder, cellPadding, fontSize | 7 |
| Badges | backgroundColor, color, borderRadius, padding | 7 |
| Modals | overlay, backgroundColor, borderRadius, shadow | 7 |

**Total: ~50 new tests across 8 new test files**

---

## Threshold Configuration

```javascript
CONSISTENCY_THRESHOLDS = {
  maxInconsistencies: 5,    // Total allowed before test fails
  maxCriticalIssues: 0,     // Critical = font-family, major color differences
  warnThreshold: 3,         // Log warning if exceeded

  // Per-property tolerance
  colorTolerance: 10,       // RGB value difference allowed (0-255)
  sizeTolerance: 2,         // Pixel difference allowed

  // Severity levels
  critical: ['fontFamily', 'backgroundColor'],
  major: ['fontSize', 'color', 'padding'],
  minor: ['borderRadius', 'boxShadow', 'margin'],
};
```

---

## Test Commands

```bash
# Run all consistency tests
npm run test:consistency

# Run specific element tests
npx playwright test tests/e2e/specs/audit/buttons.consistency.spec.js

# Run with report
npm run test:consistency -- --reporter=html
```

---

## Implementation Checklist

### Phase 1: Foundation
- [x] Create `ui-consistency.constants.js` with EXPECTED_STYLES
- [x] Enhance `style-audit.helper.js` with new methods
- [x] Create `tests/e2e/specs/audit/` directory

### Phase 2: Core Tests
- [x] Create `ui-consistency.spec.js` (main cross-screen test)
- [x] Create `buttons.consistency.spec.js`
- [x] Create `cards.consistency.spec.js`
- [x] Create `forms.consistency.spec.js`

### Phase 3: Additional Tests
- [x] Create `typography.consistency.spec.js`
- [x] Create `tables.consistency.spec.js`
- [x] Create `badges.consistency.spec.js`

### Phase 4: Integration
- [x] Update `package.json` with test scripts
- [ ] Run full test suite
- [ ] Fix any baseline inconsistencies found
- [ ] Document thresholds and expected styles

---

## Industry Best Practices Applied

1. **Centralized Design Tokens** - Single source of truth for expected styles
2. **Separation of Concerns** - Element-specific test files for maintainability
3. **Threshold-Based Failure** - Balanced approach between strict and lenient
4. **Cross-Screen Comparison** - Ensures consistency across entire app
5. **Severity Levels** - Critical issues fail immediately, minor issues accumulate
6. **Reusable Helper Methods** - DRY principle for style extraction
7. **Comprehensive Reporting** - Detailed output for debugging inconsistencies
