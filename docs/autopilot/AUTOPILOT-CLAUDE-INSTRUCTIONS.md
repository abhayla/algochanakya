# AutoPilot Development Instructions

> This file provides context for Claude Code when working on the AutoPilot feature.

## Quick Reference

| Document | Location | Contents |
|----------|----------|----------|
| UI/UX Design | `docs/autopilot/ui-ux-design.md` | Screens, wireframes, user flows |
| Component Design | `docs/autopilot/component-design.md` | Vue.js 3 components, props, emits |
| Database Schema | `docs/autopilot/database-schema.md` | PostgreSQL tables, JSONB structures |
| API Contracts | `docs/autopilot/api-contracts.md` | FastAPI endpoints, Pydantic models |
| Phase 1 Guide | `docs/autopilot/AUTOPILOT-PHASE1-IMPLEMENTATION.md` | Step-by-step tasks |

## Current Phase: Phase 1 - Core Strategy Builder

### Scope

**Build:**
- Strategy CRUD API (create, read, update, delete)
- Strategy lifecycle (activate, pause, resume, clone)
- User settings API
- Dashboard summary API
- Pinia store for state management
- Dashboard view with strategy cards
- Multi-step strategy builder wizard
- Settings page

**NOT in Phase 1:**
- Real-time condition monitoring
- Order execution
- Adjustment execution
- WebSocket real-time updates
- Kill switch
- Templates
- Backtest

## Tech Stack

```
Frontend: Vue.js 3 + Composition API + Pinia + Tailwind CSS
Backend:  FastAPI + SQLAlchemy (Async) + PostgreSQL + Redis
Broker:   Kite Connect API (Zerodha)
Testing:  Playwright (E2E) + Pytest (Backend) + Postman (API)
```

## File Locations

### Backend Files to Create/Modify

```
backend/
├── alembic/versions/
│   └── 001_autopilot_initial.py     # Migration (EXISTS)
├── app/
│   ├── api/v1/autopilot/
│   │   ├── __init__.py              # CREATE
│   │   └── router.py                # CREATE - API endpoints
│   ├── models/
│   │   └── autopilot.py             # CREATE - SQLAlchemy models
│   └── schemas/
│       └── autopilot.py             # CREATE - Pydantic schemas
└── main.py                          # MODIFY - Register router
```

### Frontend Files to Create

```
frontend/src/
├── stores/
│   └── autopilot.js                 # CREATE - Pinia store
├── views/autopilot/
│   ├── DashboardView.vue            # CREATE
│   ├── StrategyBuilderView.vue      # CREATE
│   ├── StrategyDetailView.vue       # CREATE
│   └── SettingsView.vue             # CREATE
├── components/autopilot/
│   ├── dashboard/                   # CREATE - Dashboard widgets
│   ├── builder/                     # CREATE - Builder components
│   ├── strategy/                    # CREATE - Strategy cards
│   └── common/                      # CREATE - Shared components
├── composables/autopilot/
│   └── useStrategy.js               # CREATE - Composables
└── router/index.js                  # MODIFY - Add routes
```

## Coding Conventions

### Backend (Python)

```python
# Use async/await for all database operations
async def get_strategies(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.user_id == user_id
        )
    )
    return result.scalars().all()

# Use HTTPException for errors
if not strategy:
    raise HTTPException(status_code=404, detail="Strategy not found")

# Add type hints everywhere
def calculate_pnl(positions: List[Position]) -> Decimal:
    pass

# Use Pydantic for validation
class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    lots: int = Field(1, ge=1, le=50)
```

### Frontend (JavaScript/Vue)

```javascript
// Use Composition API
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'

const store = useAutopilotStore()
const loading = ref(false)

onMounted(async () => {
  await store.fetchStrategies()
})
</script>

// Use async/await for API calls
const createStrategy = async (data) => {
  try {
    await store.createStrategy(data)
    router.push('/autopilot')
  } catch (error) {
    toast.error(error.message)
  }
}

// Props with validation
const props = defineProps({
  strategy: { type: Object, required: true },
  editable: { type: Boolean, default: false }
})

// Emit events
const emit = defineEmits(['update', 'delete', 'activate'])
```

## API Patterns

### Request Flow

```
Frontend Component
    ↓
Pinia Store Action (api call)
    ↓
Axios → /api/v1/autopilot/...
    ↓
FastAPI Router
    ↓
Service Layer (business logic)
    ↓
SQLAlchemy → PostgreSQL
```

### Response Format

```json
{
  "status": "success",
  "message": "Strategy created successfully",
  "data": { ... },
  "timestamp": "2025-12-09T10:30:00Z"
}
```

### Error Format

```json
{
  "status": "error",
  "error": "STRATEGY_NOT_FOUND",
  "message": "Strategy with ID 123 not found",
  "timestamp": "2025-12-09T10:30:00Z"
}
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `autopilot_user_settings` | Risk limits, preferences |
| `autopilot_strategies` | Strategy configurations |
| `autopilot_orders` | Executed orders |
| `autopilot_logs` | Activity audit trail |
| `autopilot_templates` | Reusable templates |
| `autopilot_condition_eval` | Condition state cache |
| `autopilot_daily_summary` | Daily aggregates |

## Key JSONB Structures

### legs_config

```json
[
  {
    "id": "leg_1",
    "contract_type": "PE",
    "transaction_type": "SELL",
    "strike_selection": {
      "mode": "atm_offset",
      "offset": -200
    },
    "quantity_multiplier": 1,
    "execution_order": 1
  }
]
```

### entry_conditions

```json
{
  "logic": "AND",
  "conditions": [
    {
      "id": "cond_1",
      "enabled": true,
      "variable": "TIME.CURRENT",
      "operator": "greater_than",
      "value": "09:20"
    }
  ]
}
```

## Routes to Add

```javascript
// frontend/src/router/index.js
{
  path: '/autopilot',
  name: 'AutoPilot',
  component: () => import('@/views/autopilot/DashboardView.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/autopilot/strategies/new',
  name: 'AutoPilotStrategyBuilder',
  component: () => import('@/views/autopilot/StrategyBuilderView.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/autopilot/strategies/:id',
  name: 'AutoPilotStrategyDetail',
  component: () => import('@/views/autopilot/StrategyDetailView.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/autopilot/settings',
  name: 'AutoPilotSettings',
  component: () => import('@/views/autopilot/SettingsView.vue'),
  meta: { requiresAuth: true }
}
```

## Common Tasks

### Run Migration

```bash
cd backend
source venv/bin/activate  # Windows: .\venv\Scripts\Activate
alembic upgrade head
```

### Start Development

```bash
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Test API

Import `tests/postman/autopilot-collection.json` into Postman.

## Status Transitions

```
draft → waiting → active → completed
  ↓        ↓         ↓
  ↓        ↓      pending → active
  ↓        ↓         ↓
  ↓      paused ←←←←←┘
  ↓        ↓
  └──────→ error
```

## Checklist for Each Task

- [ ] Read relevant documentation section
- [ ] Check existing similar code for patterns
- [ ] Implement with proper error handling
- [ ] Add appropriate logging
- [ ] Test with Postman/browser
- [ ] Handle edge cases

## Questions?

1. Check documentation files first
2. Look at similar existing code
3. Ask with specific context
