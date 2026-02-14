# Tester Agent Memory

**Purpose:** Track flaky tests, coverage trends, and execution time patterns
**Agent:** tester
**Last Updated:** 2026-02-14

---

## Patterns Observed

### Test Execution Patterns

<!-- Track test execution trends -->

#### E2E Tests
- Total specs: ~122 files
- Execution time: Varies (30min timeout in CI)
- Common failures: None tracked yet

#### Backend Tests
- Total files: ~67 pytest files
- Execution time: Fast (< 2min typically)
- Common failures: None tracked yet

#### Frontend Tests
- Total files: Vitest unit tests
- Execution time: Fast (< 1min typically)
- Common failures: None tracked yet

---

## Decisions Made

### Test Data Management

<!-- Decisions about test data and fixtures -->

#### Authentication
- Uses `.auth-state.json` for Playwright persistence
- Token stored in `.auth-token` files
- SmartAPI auto-TOTP (20-25s timeout)

#### Test Isolation
- Each E2E spec should be independent
- Use `authenticatedPage` fixture for auth tests
- Clean up state in `afterEach` hooks

### Timeout Policies

<!-- Timeout values for different test scenarios -->

- Default E2E: 30s (playwright.config.js)
- AngelOne login: 35s (auto-TOTP delay)
- CI full suite: 30min (GitHub Actions)

---

## Common Issues

### Flaky Tests

<!-- Tests that fail intermittently -->

#### By Screen
- None tracked yet

#### By Root Cause
- None tracked yet

### Coverage Gaps

<!-- Areas with insufficient test coverage -->

- None tracked yet

### Performance Issues

<!-- Tests that are slow or resource-intensive -->

- None tracked yet

---

## Execution Time Trends

### Regression Detection

<!-- Track if test execution time is increasing -->

- None tracked yet

---

## Last Updated

2026-02-14: Agent memory system initialized
