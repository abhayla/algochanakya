---
name: add-ai-endpoint
description: >
  Add a new AI API endpoint to the v1/ai router. Creates route, service,
  schema, and wires into the centralized AI router.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<endpoint-name>"
version: "1.0.0"
synthesized: true
private: false
---

# Add AI API Endpoint

## STEP 1: Create Route File

Create `backend/app/api/v1/ai/<name>.py` with a FastAPI APIRouter. All authenticated endpoints use `Depends(get_current_user)` and `Depends(get_db)` for database sessions.

## STEP 2: Register Sub-Router

In `backend/app/api/v1/ai/router.py`, import and include:

```python
from app.api.v1.ai import new_module
router.include_router(new_module.router, prefix="/new-module", tags=["ai-new-module"])
```

Current sub-routers (16): regime, config, recommendations, analytics, backtest, risk_state, stress, drawdown, regime_drift, ml, regime_quality, autonomy, capital_risk, websocket_health, deploy.

## STEP 3: Create Service

Create `backend/app/services/ai/<name>_service.py`. Use async SQLAlchemy sessions and Decimal for financial values.

## STEP 4: Create Schemas

Create `backend/app/schemas/ai_<name>.py` with Pydantic request/response models.

## STEP 5: Write Tests

Create `backend/tests/backend/ai/test_<name>.py`. Mock broker adapters and market data.

## STEP 6: Verify Swagger

Endpoint auto-appears at `/docs`. Verify tag grouping matches prefix.

## CRITICAL RULES

- All authenticated endpoints use Depends(get_current_user)
- All DB access via Depends(get_db) async sessions
- Use Decimal for financial values, not float
- Register in router.py or endpoint will be invisible
- Follow existing pattern from regime.py or recommendations.py
