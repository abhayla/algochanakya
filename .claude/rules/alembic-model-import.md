---
description: >
  New SQLAlchemy models MUST be imported in both models/__init__.py AND alembic/env.py,
  or alembic autogenerate will silently skip them.
globs: ["backend/app/models/**/*.py", "backend/alembic/**/*.py"]
synthesized: true
private: false
---

# Alembic Model Import Rule

## The Problem

Alembic autogenerate discovers tables by inspecting `Base.metadata`. If a model file exists
but is not imported anywhere that runs before autogenerate, the model class is never registered
with `Base`, and the migration will be empty.

## Required Steps When Adding a New Model

1. Create model file: `backend/app/models/<name>.py` (inherit from `Base`)
2. Import in `backend/app/models/__init__.py`:
   ```python
   from app.models.<name> import NewModel
   ```
3. Add to `__all__` list in `__init__.py`
4. Import in `backend/alembic/env.py` (add to the existing import block):
   ```python
   from app.models import NewModel  # Must be in the import block
   ```
5. Generate migration: `alembic revision --autogenerate -m "add new_model table"`
6. Verify the generated migration is not empty
7. Apply: `alembic upgrade head`

## Common Mistake

Forgetting step 3 or 4 results in:
- `alembic revision --autogenerate` produces an empty migration
- No error is shown — it silently succeeds
- The table is never created in the database

## Current Model Registry

All models are imported in `backend/app/models/__init__.py` — check that file for the
current list before adding a new model to avoid duplicates.

