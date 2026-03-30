---
description: >
  E2E spec files MUST follow {feature}.{type}.spec.js naming with type suffixes:
  .happy, .edge, .api, .audit, .visual, .isolated, .bugs, .consistency.
  Enables filtered test runs by category.
globs: ["tests/e2e/specs/**/*.spec.js"]
synthesized: true
private: false
---

# E2E Test File Naming Convention

## Required Format

```
tests/e2e/specs/{screen}/{feature}.{type}.spec.js
```

Examples:
- `tests/e2e/specs/optionchain/optionchain.happy.spec.js`
- `tests/e2e/specs/autopilot/autopilot.edge.spec.js`
- `tests/e2e/specs/dashboard/dashboard.audit.spec.js`

## Type Suffixes

| Suffix | Purpose | Run Command | Count |
|--------|---------|-------------|-------|
| `.happy` | Core user flows succeed | `npm run test:happy` | ~17 files |
| `.edge` | Error states, boundary conditions | `npm run test:edge` | ~13 files |
| `.api` | API response validation | `npm test -- --grep @api` | ~7 files |
| `.audit` | UI consistency, accessibility | `npm run test:audit` | ~8 files |
| `.visual` | Visual regression screenshots | `npm run test:visual` | ~7 files |
| `.isolated` | Fresh context, no auth state | `npm run test:isolated` | ~2 files |
| `.bugs` | Known bug regressions | — | ~2 files |
| `.consistency` | Design system checks | `npm run test:consistency` | ~6 files |

## Adding a New Test File

1. Determine the screen: `optionchain`, `autopilot`, `strategy`, `dashboard`, etc.
2. Determine the type based on what you're testing:
   - Testing that features work correctly? → `.happy`
   - Testing error handling and edge cases? → `.edge`
   - Validating API response shapes? → `.api`
   - Checking UI consistency/a11y? → `.audit`
   - Comparing screenshots to baselines? → `.visual`
   - Testing login flow or unauthenticated states? → `.isolated`
   - Preventing a specific known bug from regressing? → `.bugs`

3. Create the file: `tests/e2e/specs/{screen}/{feature}.{type}.spec.js`

## Tag Mapping

Use `@tag` in test titles for `--grep` filtering:

```javascript
test('@happy displays option chain data', async ({ authenticatedPage }) => { ... })
test('@edge handles empty option chain', async ({ authenticatedPage }) => { ... })
```

## MUST NOT

- MUST NOT create spec files without a type suffix — ambiguous tests can't be filtered
- MUST NOT mix test types in a single file — one type per file
- MUST NOT use `.test.js` extension — Playwright uses `.spec.js`
- MUST NOT put spec files directly in `tests/e2e/specs/` — organize by screen subdirectory
