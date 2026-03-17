---
name: autopilot-strategy-lifecycle
description: >
  Create or modify an AutoPilot strategy with proper multi-table coordination across
  18 tables and 6+ service files. Covers the full lifecycle from creation through
  monitoring, execution, adjustment, and reporting. Use when adding new strategy types
  or modifying the strategy creation pipeline.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<strategy-name> [--modify]"
version: "1.0.0"
synthesized: true
private: false
source_hash: "autopilot-lifecycle-v1"
---

# AutoPilot Strategy Lifecycle

Create or modify AutoPilot strategies following the multi-table cascade pattern.

**Request:** $ARGUMENTS

---

## STEP 1: Understand the Table Graph

Read the AutoPilot model files to understand the current schema:

```bash
ls backend/app/models/autopilot*.py
```

The 18-table graph follows this dependency order:

| Layer | Tables | Purpose |
|-------|--------|---------|
| Config | `AutoPilotUserSettings` | Global user prefs, kill switch, risk limits |
| Strategy | `AutoPilotStrategy`, `AutoPilotTemplate` | Strategy definition, reusable templates |
| Conditions | `AutoPilotConditionEval` | Entry/exit condition evaluation state |
| Execution | `AutoPilotOrder`, `AutoPilotOrderBatch`, `AutoPilotPendingConfirmation` | Order placement and semi-auto confirmation |
| Positions | `AutoPilotPositionLeg` | Live position tracking per leg |
| Adjustments | `AutoPilotAdjustment*`, `AutoPilotAdjustmentLog`, `AutoPilotAdjustmentSuggestion` | Adjustment rules, history, AI recommendations |
| Reporting | `AutoPilotLog`, `AutoPilotDailySummary`, `AutoPilotTradeJournal`, `AutoPilotReport` | Audit trail, P&L rollup, journal |
| Analytics | `AutoPilotAnalyticsCache`, `AutoPilotBacktest`, `AutoPilotTemplateRating` | Cached metrics, backtests, user ratings |

## STEP 2: Create or Modify the Strategy Model

1. Read the existing strategy model:
   ```bash
   cat backend/app/models/autopilot_strategy.py
   ```

2. If creating a new strategy type, add the type to the relevant enum in `backend/app/constants/strategy_types.py`

3. The `legs_config` field is JSONB — define the leg structure:
   ```python
   legs_config = [
       {"position": "BUY", "contract_type": "CE", "strike_offset": 0, "lots": 1},
       {"position": "SELL", "contract_type": "CE", "strike_offset": 200, "lots": 1},
   ]
   ```

4. Entry conditions and adjustment rules are stored separately — do NOT embed them in `legs_config`

## STEP 3: Define Conditions and Adjustments

1. Read the condition engine: `backend/app/services/autopilot/condition_engine.py`
2. Read the adjustment engine: `backend/app/services/autopilot/adjustment_engine.py`

For new condition types:
- Add condition type to the condition enum
- Implement evaluation logic in `condition_engine.py`
- Add test in `backend/tests/backend/autopilot/`

For new adjustment types:
- Follow the offensive/defensive classification in `rules/adjustment-offensive-defensive.md`
- Implement in `adjustment_engine.py`
- Create `AutoPilotAdjustmentLog` entries for audit trail

## STEP 4: Wire Up the Service Layer

The strategy lifecycle flows through these services in order:

1. **`strategy_monitor.py`** — Polls conditions, triggers execution
2. **`condition_engine.py`** — Evaluates entry/exit conditions against market data
3. **`order_executor.py`** — Places orders via broker adapter (uses `get_broker_adapter()`)
4. **`adjustment_engine.py`** — Monitors open positions, suggests/executes adjustments
5. **`analytics.py`** — Calculates P&L, Greeks exposure, risk metrics

Each service uses `AsyncSession` from `get_db()` dependency. All database operations are async.

## STEP 5: Create API Routes

1. Read existing strategy routes: `backend/app/api/routes/strategy.py`
2. Follow the existing pattern:
   ```python
   @router.post("", response_model=StrategyResponse)
   async def create_strategy(
       strategy: StrategyCreate,
       user: User = Depends(get_current_user),
       db: AsyncSession = Depends(get_db),
   ):
   ```
3. Use `selectinload()` for relationship loading — NEVER lazy load in async context
4. Create corresponding Pydantic schemas in `backend/app/schemas/`

## STEP 6: Add Frontend Store and View

1. Create or update the Pinia store in `frontend/src/stores/` using Composition API:
   ```javascript
   export const useAutopilotStore = defineStore('autopilot', () => {
     const strategies = ref([])
     async function createStrategy(data) {
       const res = await api.post('/api/v1/autopilot/strategies', data)
       strategies.value.push(res.data)
     }
     return { strategies, createStrategy }
   })
   ```

2. Use `api` from `@/services/api` — NEVER import axios directly

## STEP 7: Test the Full Lifecycle

```bash
# Unit tests for new service logic
cd backend && pytest tests/backend/autopilot/ -v -k "test_<new_feature>"

# Integration test for the API route
pytest tests/backend/autopilot/test_strategy_routes.py -v

# Frontend unit tests
cd frontend && npm run test:run -- --grep "autopilot"
```

## STEP 8: Verify and Commit

1. Run the full AutoPilot test suite:
   ```bash
   cd backend && pytest tests/backend/autopilot/ -v
   ```
2. Verify no regressions in related services
3. Commit with conventional format: `feat(autopilot): add <strategy-type> strategy lifecycle`

---

## CRITICAL RULES

- NEVER skip the condition/adjustment separation — embedding conditions in `legs_config` breaks the condition engine
- NEVER lazy-load relationships in async context — use `selectinload()` or `joinedload()`
- ALWAYS create `AutoPilotLog` entries for state transitions — the audit trail is required for debugging live trading
- ALWAYS use `Decimal` (not `float`) for financial values in order and position records
- ALWAYS test with the async test fixtures from `conftest.py` — synchronous tests will miss async bugs
- NEVER hardcode lot sizes or strike steps — use centralized constants from `app/constants/trading.py`
