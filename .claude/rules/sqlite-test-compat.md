---
description: >
  Tests use SQLite in-memory. PostgreSQL types (JSONB, ARRAY, UUID, PgEnum, BigInteger)
  need @compiles dialect adapters in conftest.py or tests silently fail.
globs: ["backend/tests/**/*.py"]
synthesized: true
private: false
---

# SQLite Test Compatibility

## Context

Backend tests use SQLite in-memory (`sqlite+aiosqlite:///:memory:`) for speed and isolation.
Production uses PostgreSQL with types that SQLite does not support.

## Required Dialect Adapters

Every `conftest.py` that creates test databases MUST include these `@compiles` adapters:

```python
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, BigInteger
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return compiler.visit_JSON(JSON(), **kw)

@compiles(ARRAY, "sqlite")
def compile_array_sqlite(element, compiler, **kw):
    return "JSON"

@compiles(BigInteger, "sqlite")
def compile_biginteger_sqlite(element, compiler, **kw):
    return "INTEGER"

@compiles(PgUUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "TEXT"

@compiles(PgEnum, "sqlite")
def compile_pgenum_sqlite(element, compiler, **kw):
    return "VARCHAR(50)"
```

## Why This Matters

Without these adapters, `Base.metadata.create_all()` raises `CompileError` when it
encounters PostgreSQL-specific column types. The error message is often cryptic
(e.g., "Cannot compile JSONB").

## Current Test Setup

- `backend/tests/conftest.py` — root conftest with these adapters
- `backend/tests/backend/autopilot/conftest.py` — autopilot-specific conftest (also has adapters)
- Both use `StaticPool` to share the same SQLite connection across async sessions

## Test Database Pattern

```python
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)
```

