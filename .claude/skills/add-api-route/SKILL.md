---
name: add-api-route
description: >
  Scaffold a new FastAPI API route with all required artifacts: route file, Pydantic schemas,
  service layer, router registration in main.py, and test file. Ensures no step is missed
  when adding endpoints to the backend.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<route-name> [--prefix /api/v1] [--methods GET,POST]"
version: "1.0.0"
synthesized: true
private: false
---

# Add API Route

Scaffold a complete FastAPI API route with all required files and registrations.

**Arguments:** $ARGUMENTS

## STEP 1: Validate Route Name and Check for Conflicts

1. Parse the route name from arguments (e.g., `portfolio`)
2. Check if a route file already exists:
   ```bash
   ls backend/app/api/routes/${ROUTE_NAME}.py 2>/dev/null
   ```
3. Check if the router prefix is already in use in `backend/app/main.py`:
   ```bash
   grep -n "${ROUTE_NAME}" backend/app/main.py
   ```
4. If conflicts found, STOP and report. Do not overwrite existing routes.

## STEP 2: Create Pydantic Schemas

Create `backend/app/schemas/${ROUTE_NAME}.py` with request/response models:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ${RouteNamePascal}Create(BaseModel):
    """Request schema for creating a ${route_name}."""
    # Add fields based on requirements

class ${RouteNamePascal}Response(BaseModel):
    """Response schema for ${route_name}."""
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}

class ${RouteNamePascal}Update(BaseModel):
    """Request schema for updating a ${route_name}."""
    # Add optional fields for partial updates
```

Follow existing schema conventions in `backend/app/schemas/` — use `model_config = {"from_attributes": True}` for ORM models (Pydantic v2 pattern).

## STEP 3: Create Service Layer

Create `backend/app/services/${ROUTE_NAME}_service.py` with business logic:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.schemas.${ROUTE_NAME} import ${RouteNamePascal}Create, ${RouteNamePascal}Response


async def create_${route_name}(db: AsyncSession, data: ${RouteNamePascal}Create, user_id: int):
    """Create a new ${route_name}."""
    # Implement business logic
    pass

async def get_${route_name}(db: AsyncSession, ${route_name}_id: int, user_id: int):
    """Get a ${route_name} by ID."""
    pass
```

If the service belongs to an existing subdomain (brokers, autopilot, ai, options), place it in the appropriate subdirectory instead of the root `services/` directory.

## STEP 4: Create Route File

Create `backend/app/api/routes/${ROUTE_NAME}.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.api.routes.auth import get_current_user
from backend.app.schemas.${ROUTE_NAME} import ${RouteNamePascal}Create, ${RouteNamePascal}Response

router = APIRouter()


@router.post("/", response_model=${RouteNamePascal}Response)
async def create(
    data: ${RouteNamePascal}Create,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new ${route_name}."""
    # Call service layer
    pass
```

Conventions:
- MUST use `router = APIRouter()` (not `app`)
- MUST use `AsyncSession = Depends(get_db)` for database access
- MUST use `Depends(get_current_user)` for authenticated endpoints
- MUST use `response_model` for type-safe responses

## STEP 5: Register Router in main.py

Add the router import and include in `backend/app/main.py`:

1. Add import at the top with other route imports:
   ```python
   from backend.app.api.routes.${ROUTE_NAME} import router as ${route_name}_router
   ```

2. Add `include_router` call in the router registration section (after CORS middleware, with other routers):
   ```python
   app.include_router(${route_name}_router, prefix="/api/${route_name}", tags=["${route_name}"])
   ```

Place the import and include in alphabetical order with existing routes.

## STEP 6: Create Test File

Create `backend/tests/backend/routes/test_${ROUTE_NAME}.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_${route_name}(async_client: AsyncClient, auth_headers: dict):
    """Test creating a new ${route_name}."""
    response = await async_client.post(
        "/api/${route_name}/",
        json={},  # Add test data
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_${route_name}_unauthorized(async_client: AsyncClient):
    """Test that unauthenticated requests are rejected."""
    response = await async_client.post("/api/${route_name}/", json={})
    assert response.status_code == 401
```

Follow existing test patterns — check `backend/tests/conftest.py` for available fixtures (`async_client`, `auth_headers`, etc.).

## STEP 7: Verify

1. Run the new test:
   ```bash
   cd backend && python -m pytest tests/backend/routes/test_${ROUTE_NAME}.py -v
   ```
2. Verify the route appears in the OpenAPI docs by checking the import chain compiles:
   ```bash
   cd backend && python -c "from backend.app.main import app; print([r.path for r in app.routes if '${ROUTE_NAME}' in r.path])"
   ```

## CRITICAL RULES

- MUST create ALL artifacts: schema, service, route, main.py registration, and test file. Missing any one causes inconsistency.
- MUST NOT add route logic directly in the route file — delegate to the service layer. Route files handle HTTP concerns (parsing, auth, response codes); services handle business logic.
- MUST use `AsyncSession = Depends(get_db)` — never create database sessions manually in routes.
- MUST register the router AFTER CORS middleware in main.py (see `middleware-registration-order` rule).
- If the route involves a new database model, also run `/add-database-model` to create the model and migration.
