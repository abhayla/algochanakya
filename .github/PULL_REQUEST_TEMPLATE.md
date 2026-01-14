# Pull Request

## Description

<!-- Brief description of changes -->

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Refactoring (no functional changes)
- [ ] Documentation update
- [ ] Performance improvement

## Related Issues

<!-- Link to related issues, e.g., Closes #123 -->

---

## Implementation Checklist

### Code Quality

- [ ] Code follows project patterns and conventions
- [ ] No direct broker API usage (uses broker adapters from `app.services.brokers/`)
- [ ] No hardcoded trading constants (uses `app.constants.trading`)
- [ ] All database operations use `async/await`
- [ ] Proper error handling implemented

### Testing

- [ ] E2E tests added/updated (if applicable)
  - [ ] Uses `data-testid` attributes (format: `[screen]-[component]-[element]`)
  - [ ] Imports from `auth.fixture.js` (not `@playwright/test`)
  - [ ] Uses `authenticatedPage` fixture
- [ ] Backend unit tests added/updated (if applicable)
- [ ] All tests pass locally: `npm test` (E2E) or `pytest tests/ -v` (backend)

### Documentation

**⚠️ CRITICAL: Check documentation before merging**

- [ ] **Reviewed [Developer Quick Reference](../docs/DEVELOPER-QUICK-REFERENCE.md)** for relevant patterns
- [ ] **Checked [Implementation Checklist](../docs/IMPLEMENTATION-CHECKLIST.md)** - task completed or updated
- [ ] **Reviewed [Broker Abstraction docs](../docs/architecture/broker-abstraction.md)** (if touching broker code)
- [ ] Updated architecture docs (if architectural changes)
- [ ] Updated feature docs (if feature changes): `docs/features/{feature}/`
- [ ] Ran `docs-maintainer` skill after code changes (or will run after merge)
- [ ] Updated CLAUDE.md (if new patterns or gotchas discovered)

### Database Changes

- [ ] New models added to `backend/app/models/__init__.py`
- [ ] New models imported in `backend/alembic/env.py` ⚠️ **CRITICAL**
- [ ] Migration created: `alembic revision --autogenerate -m "..."`
- [ ] Migration tested: `alembic upgrade head`

### API Changes

- [ ] OpenAPI/Swagger docs accurate (check http://localhost:8001/docs)
- [ ] Authentication required endpoints use `Depends(get_current_user)`
- [ ] Error responses follow standard format

---

## Broker Abstraction Compliance

**If this PR touches broker-related code, confirm:**

- [ ] Uses `get_broker_adapter()` factory (not direct `KiteConnect` or `SmartAPI`)
- [ ] Uses unified data models (`UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote`)
- [ ] Works with any broker (not Kite/SmartAPI-specific)
- [ ] Updated [broker-abstraction.md](../docs/architecture/broker-abstraction.md) if needed

---

## Testing Instructions

<!-- How to test these changes -->

1.
2.
3.

## Screenshots (if applicable)

<!-- Add screenshots for UI changes -->

---

## Pre-Merge Checklist

- [ ] Branch is up to date with `main`/`develop`
- [ ] No merge conflicts
- [ ] CI/CD checks passing
- [ ] Code reviewed by at least one other developer
- [ ] Documentation reviewed and updated
- [ ] Ready to merge

---

## Post-Merge Actions

- [ ] Run `docs-maintainer` skill to update documentation
- [ ] Update [Implementation Checklist](../docs/IMPLEMENTATION-CHECKLIST.md) progress
- [ ] Close related issues
