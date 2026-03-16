---
description: >
  Backend MUST NOT import from frontend, frontend MUST NOT import from backend.
  Enforced by guard_cross_feature_imports.py hook and CI validation.
globs: ["backend/**/*.py", "frontend/**/*.{js,vue}"]
synthesized: true
private: false
---

# Cross-Layer Import Guard

## Enforcement

- `guard_cross_feature_imports.py` hook (PreToolUse — blocks violating edits)
- `.github/scripts/validate-cross-imports.py` (CI — blocks PRs)

## Backend MUST NOT Import Frontend

```python
# BLOCKED:
from frontend.src.services import api
from frontend.components import MyComponent
import frontend.utils
```

Backend runs on the server. Frontend runs in the browser. They communicate via HTTP API only.

## Frontend MUST NOT Import Backend

```javascript
// BLOCKED:
import { User } from "../../backend/app/models/users"
import { get_broker_adapter } from "backend/app/services/brokers/factory"
from app.models import User
from app.services import anything
```

## Correct Communication Pattern

Frontend calls backend via API endpoints through the shared axios instance:
```javascript
import api from "@/services/api"
const response = await api.get("/positions")
```

Backend exposes data via FastAPI routes:
```python
@router.get("/positions")
async def get_positions(user: User = Depends(get_current_user)):
    ...
```

