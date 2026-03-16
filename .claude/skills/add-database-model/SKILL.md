---
name: add-database-model
description: >
  Add a new SQLAlchemy model to the backend with proper imports, migration,
  and test fixtures. Covers the 7-location checklist that prevents silent autogenerate failures.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<model-name>"
version: "1.0.0"
synthesized: true
private: false
---

# Add Database Model

## STEP 1: Create Model File

Create `backend/app/models/<name>.py` inheriting from `Base`:

- Use `UUID(as_uuid=True)` for primary keys (consistent with all existing models)
- Use `Numeric` (not `Float`) for financial values
- Use `JSONB` for flexible structured data
- Add `created_at` and `updated_at` timestamps

## STEP 2: Import in models/__init__.py

Add import AND `__all__` entry in `backend/app/models/__init__.py`.

## STEP 3: Import in alembic/env.py

Add to the import block in `backend/alembic/env.py`. **CRITICAL:** Without this, autogenerate produces a silently empty migration.

## STEP 4: Create Pydantic Schema

Create `backend/app/schemas/<name>.py` with Create and Response models. Use `model_config = {"from_attributes": True}`.

## STEP 5: Generate and Verify Migration

```bash
cd backend
alembic revision --autogenerate -m "add <table_name> table"
```

**Open the generated file** and verify it contains `op.create_table(...)`. If empty, you missed Step 2 or 3.

## STEP 6: Apply Migration

```bash
alembic upgrade head
```

## STEP 7: Add Test Fixtures

Add `@pytest_asyncio.fixture` to the relevant `conftest.py`. Ensure SQLite dialect adapters exist for any PostgreSQL-specific column types (see `sqlite-test-compat` rule).

## CRITICAL RULES

- NEVER skip the alembic/env.py import - autogenerate will produce an empty migration silently
- ALWAYS verify the generated migration has actual content before applying
- Use UUID primary keys, Numeric for money, JSONB for flexible data
- Add created_at/updated_at timestamps to all models
