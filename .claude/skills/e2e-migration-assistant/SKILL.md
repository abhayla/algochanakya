---
name: e2e-migration-assistant
description: Migrate legacy E2E tests to AlgoChanakya conventions. Scans for anti-patterns, reports violations, and applies automated fixes. Use when cleaning up old tests or onboarding new test files.
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: testing
  created_by: skill-evolver
---

# E2E Migration Assistant

Automated migration of legacy Playwright E2E tests to AlgoChanakya conventions. Scans for 7 anti-patterns, reports violations, and applies fixes with user approval.

## When to Use

- Migrating old E2E tests to current conventions
- Cleaning up tests after bulk import or copy-paste
- Pre-PR audit of test file quality
- When `health-check` or `test-fixer` flags convention violations
- Onboarding tests from a different project or framework version

## When NOT to Use

- **Writing new tests** → Use `/e2e-test-generator` instead
- **Fixing failing tests** → Use `/test-fixer` instead
- **Single quick fix** → Just fix it manually
- **Backend/Vitest tests** → This skill is Playwright E2E only

## Migration Rules

### Rule 1: CSS/Text Selectors → data-testid

**Anti-pattern:** Using CSS selectors, `getByText()`, or `:has-text()` to find elements.

```bash
# Detection grep patterns
grep -rnE "page\.locator\('[.#]" tests/e2e/specs/       # CSS class/id selectors
grep -rnE "getByText\(" tests/e2e/specs/                 # Text selectors
grep -rnE ":has-text\(" tests/e2e/specs/                 # Text pseudo-selectors
grep -rnE "page\.locator\('(div|span|button|a|input)\b" tests/e2e/specs/  # Tag selectors
```

**Fix:** Replace with `page.locator('[data-testid="..."]')` or `page.getByTestId('...')`.

See `references/migration-patterns.md` for before/after examples.

### Rule 2: @playwright/test Import → auth.fixture.js

**Anti-pattern:** Importing `test` and `expect` directly from `@playwright/test`.

```bash
# Detection
grep -rnE "from '@playwright/test'" tests/e2e/specs/
grep -rnE 'from "@playwright/test"' tests/e2e/specs/
```

**Fix:** Import from the auth fixture instead:
```javascript
// Before
import { test, expect } from '@playwright/test';

// After
import { test, expect, authenticatedPage } from '../fixtures/auth.fixture.js';
```

**Exception:** Files ending in `.isolated.spec.js` intentionally skip auth and MAY import from `@playwright/test`.

### Rule 3: waitForTimeout() → wait-helpers.js

**Anti-pattern:** Using raw `waitForTimeout()` with arbitrary delays.

```bash
# Detection
grep -rnE "waitForTimeout\(" tests/e2e/specs/
```

**Fix:** Replace with specific wait helpers from `tests/e2e/helpers/wait-helpers.js`:
- `waitForTimeout(1000)` → `waitForApiResponse(page, '/api/...')` or `waitForElement(page, selector)`
- `waitForTimeout(2000)` → `waitForNetworkIdle(page)` or `waitForDataLoad(page)`
- `waitForTimeout(5000)` → `waitForNavigation(page, url)` or explicit `waitForSelector`

Available helpers in `wait-helpers.js`:
- `waitForApiResponse(page, urlPattern)`
- `waitForElement(page, selector, options)`
- `waitForNetworkIdle(page, options)`
- `waitForDataLoad(page, testId)`
- `waitForNavigation(page, urlPattern)`
- `waitForWebSocket(page, options)`
- `waitForToast(page, message)`
- `waitForModalClose(page)`
- `waitForTableLoad(page, tableTestId)`
- `waitForChartRender(page, chartTestId)`

### Rule 4: Default POM Exports → Named Exports

**Anti-pattern:** Using `export default class` in Page Object Models.

```bash
# Detection in POM files
grep -rnE "export default class" tests/e2e/pages/
```

**Fix:** Use named exports for better tree-shaking and IDE support:
```javascript
// Before
export default class WatchlistPage { ... }

// After
export class WatchlistPage { ... }
```

**Note:** This rule applies to `tests/e2e/pages/` files only, not spec files.

### Rule 5: Bare test.skip() → Skip with Reason

**Anti-pattern:** Calling `test.skip()` without a reason string.

```bash
# Detection
grep -rnE "test\.skip\(\s*\)" tests/e2e/specs/
grep -rnE "test\.skip\(\s*true\s*\)" tests/e2e/specs/
```

**Fix:** Always provide a reason:
```javascript
// Before
test.skip();

// After
test.skip('Blocked by #123: API not yet implemented');
```

### Rule 6: Hardcoded URLs → config.helper.js

**Anti-pattern:** Hardcoding `localhost` URLs in spec files.

```bash
# Detection
grep -rnE "http://localhost:" tests/e2e/specs/
grep -rnE "ws://localhost:" tests/e2e/specs/
```

**Fix:** Import from config helper:
```javascript
// Before
await page.goto('http://localhost:5173/dashboard');

// After
import { BASE_URL } from '../helpers/config.helper.js';
await page.goto(`${BASE_URL}/dashboard`);
```

### Rule 7: Silent Tests → Always Assert

**Anti-pattern:** Tests that navigate and interact but never call `expect()`.

```bash
# Detection — find spec files without any expect() calls
for f in tests/e2e/specs/**/*.spec.js; do
  if ! grep -q "expect(" "$f"; then
    echo "⚠ No assertions: $f"
  fi
done
```

**Fix:** Every test MUST have at least one `expect()` call. Common patterns:
```javascript
// Verify page loaded
await expect(page.getByTestId('page-title')).toBeVisible();

// Verify data loaded
await expect(page.getByTestId('data-table')).toHaveCount(1);

// Verify action succeeded
await expect(page.getByTestId('success-toast')).toBeVisible();
```

## Workflow

### Step 1: Scan

Run all 7 detection patterns against the target directory:

```bash
# Full scan
/e2e-migration-assistant scan

# Scan specific directory
/e2e-migration-assistant scan tests/e2e/specs/positions/

# Scan single file
/e2e-migration-assistant scan tests/e2e/specs/watchlist/watchlist.happy.spec.js
```

### Step 2: Report

Display violations grouped by rule and file:

```
📋 E2E Migration Report
═══════════════════════

Target: tests/e2e/specs/ (42 spec files)

Rule 1: CSS/Text Selectors          12 violations in 5 files
Rule 2: @playwright/test Import      8 violations in 8 files
Rule 3: waitForTimeout()             6 violations in 4 files
Rule 4: Default POM Exports          3 violations in 3 files
Rule 5: Bare test.skip()             2 violations in 2 files
Rule 6: Hardcoded URLs               4 violations in 3 files
Rule 7: Silent Tests                 1 violation in 1 file

Total: 36 violations across 15 files

Top offenders:
  1. positions/exit.spec.js         — 8 violations
  2. watchlist/watchlist.happy.spec.js — 6 violations
  3. strategy/strategy.edge.spec.js — 5 violations
```

### Step 3: User Decision

Ask user how to proceed:

| Option | Description |
|--------|-------------|
| **Migrate all** | Fix all violations automatically |
| **Per-file** | Review and approve each file individually |
| **Dry-run** | Show proposed changes without applying |
| **Skip** | Cancel migration |

### Step 4: Apply Fixes

For each violation:
1. Read the source file
2. Apply the fix pattern from `references/migration-patterns.md`
3. Write the modified file
4. Track changes for summary

### Step 5: Verify

After applying fixes:
```bash
# Run affected test files
npx playwright test [modified-files] --reporter=line

# If tests fail, offer to revert
```

### Step 6: Summary

```
✅ Migration Complete
═══════════════════

Fixed: 34/36 violations
Skipped: 2 (manual review needed)
Files modified: 14

Manual review needed:
  - positions/exit.spec.js:45 — Complex CSS selector, needs data-testid added to component first
  - strategy/strategy.edge.spec.js:89 — Custom wait logic, review replacement

Next steps:
  1. Add missing data-testid attributes to Vue components (2 needed)
  2. Run full E2E suite: npm test
  3. Review skipped violations manually
```

## Integration Points

- **health-check Step 8:** data-testid audit identifies components needing `data-testid` before Rule 1 can fully migrate
- **e2e-test-generator:** Generates new tests already following all 7 rules
- **test-fixer:** Fixes test failures that may occur after migration
- **docs/testing/e2e-test-rules.md:** SSOT for E2E conventions (this skill enforces those rules)

## Cross-References (NOT duplicated here)

- **E2E Test Rules (SSOT):** `docs/testing/e2e-test-rules.md`
- **Wait Helpers:** `tests/e2e/helpers/wait-helpers.js` (10+ helpers)
- **Auth Fixture:** `tests/e2e/fixtures/auth.fixture.js`
- **Base Page Object:** `tests/e2e/pages/BasePage.js`
- **TestID Audit Script:** `tests/e2e/scripts/audit-testids.js`
- **Config Helper:** `tests/e2e/helpers/config.helper.js`
- **Migration Patterns:** `references/migration-patterns.md` (detailed before/after examples)
