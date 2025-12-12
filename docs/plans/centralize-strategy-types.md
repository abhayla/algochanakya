# Plan: Centralize Strategy Types & Add Strategy Type Dropdown

## Goal
1. Create a single source of truth for strategy types with leg configurations
2. Add "Strategy Type" dropdown to **both** Strategy Builders (regular + AutoPilot) that auto-populates legs
3. Sync strategy types across all screens (Strategy Builder, Strategy Library, AutoPilot)

## User Requirements (Confirmed)
- **Scope**: Add dropdown to BOTH regular Strategy Builder AND AutoPilot Builder
- **Strike Logic**: Use fixed offsets (e.g., ATM ± 100/200 points)
- **Replace Behavior**: Show confirmation dialog before replacing existing legs

## Current State (Problem)

Strategy types are scattered across 6+ files with inconsistent naming:

| Location | Format | Example |
|----------|--------|---------|
| `backend/scripts/seed_strategies.py` | snake_case | `iron_condor` |
| `backend/app/models/strategies.py` | Mixed case string | `"Iron Condor"` |
| `frontend/src/stores/strategy.js` | Hardcoded array | `['Naked Put', 'Iron Condor']` |
| `frontend/src/stores/strategyLibrary.js` | Category config only | `{ bullish: {...} }` |

## Implementation Plan

### Phase 1: Backend - Create Centralized Constants

**File: `backend/app/constants/strategy_types.py`** (NEW)

```python
# Single source of truth for all strategy types
STRATEGY_TYPES = {
    "iron_condor": {
        "display_name": "Iron Condor",
        "category": "neutral",
        "legs": [
            {"type": "PE", "action": "BUY", "strike_offset": -200},
            {"type": "PE", "action": "SELL", "strike_offset": -100},
            {"type": "CE", "action": "SELL", "strike_offset": 100},
            {"type": "CE", "action": "BUY", "strike_offset": 200}
        ]
    },
    "short_straddle": {
        "display_name": "Short Straddle",
        "category": "neutral",
        "legs": [
            {"type": "CE", "action": "SELL", "strike_offset": 0},
            {"type": "PE", "action": "SELL", "strike_offset": 0}
        ]
    },
    # ... all 20 strategy types (see full list below)
}

CATEGORIES = {
    "bullish": {"name": "Bullish", "color": "#00b386", "icon": "trending-up"},
    "bearish": {"name": "Bearish", "color": "#e74c3c", "icon": "trending-down"},
    "neutral": {"name": "Neutral", "color": "#6c757d", "icon": "minus"},
    "volatile": {"name": "Volatile", "color": "#9b59b6", "icon": "activity"},
    "income": {"name": "Income", "color": "#f39c12", "icon": "dollar-sign"},
    "advanced": {"name": "Advanced", "color": "#3498db", "icon": "target"}
}
```

### Phase 2: Backend - Create API Endpoint

**File: `backend/app/api/routes/constants.py`** (NEW)

```python
@router.get("/strategy-types")
async def get_strategy_types():
    """Return all strategy types with leg configurations"""
    return {
        "strategy_types": STRATEGY_TYPES,
        "categories": CATEGORIES
    }
```

**Update: `backend/app/main.py`**
- Include new constants router

### Phase 3: Frontend - Create Centralized Store/Constants

**File: `frontend/src/constants/strategyTypes.js`** (NEW)

```javascript
// Fetched from backend on app init, cached locally
export const strategyTypes = ref({})
export const categories = ref({})

export async function loadStrategyTypes() {
  const response = await api.get('/api/constants/strategy-types')
  strategyTypes.value = response.data.strategy_types
  categories.value = response.data.categories
}
```

### Phase 4: Add Strategy Type Dropdown to Both Builders

#### 4a. AutoPilot Strategy Builder
**File: `frontend/src/views/autopilot/StrategyBuilderView.vue`**

Add Strategy Type dropdown in Basic Information section (after Underlying field):

```vue
<div class="form-field">
  <label class="form-label">Strategy Type</label>
  <select v-model="selectedStrategyType" @change="onStrategyTypeChange"
          data-testid="autopilot-builder-strategy-type">
    <option value="">Custom (Manual)</option>
    <optgroup v-for="cat in categories" :label="cat.name">
      <option v-for="type in getTypesByCategory(cat.key)" :value="type.key">
        {{ type.display_name }}
      </option>
    </optgroup>
  </select>
</div>
```

#### 4b. Regular Strategy Builder
**File: `frontend/src/views/StrategyBuilderView.vue`**

Add same dropdown in the strategy header section.

#### 4c. Shared Logic - Auto-populate Legs with Confirmation
```javascript
async function onStrategyTypeChange(strategyType) {
  if (!strategyType) return // Custom - don't change legs

  // Check if legs already exist - show confirmation
  if (store.legs.length > 0) {
    const confirmed = await showConfirmDialog({
      title: 'Replace Existing Legs?',
      message: 'Changing strategy type will replace your current legs. Continue?',
      confirmText: 'Replace',
      cancelText: 'Cancel'
    })
    if (!confirmed) {
      selectedStrategyType.value = previousStrategyType // Revert selection
      return
    }
  }

  const template = strategyTypes[strategyType]
  store.legs = template.legs.map(leg => ({
    action: leg.action,
    option_type: leg.type,
    strike_offset: leg.strike_offset,  // Fixed offset from ATM
    lots: store.lots || 1,
    // Calculate actual strike when spot price available
  }))
}
```

### Phase 5: Update Other Screens to Use Centralized Data

**Files to update:**
1. `frontend/src/stores/strategy.js` - Remove hardcoded `strategyTypes` array, import from constants
2. `frontend/src/stores/strategyLibrary.js` - Remove `categoryConfig`, import from constants
3. `frontend/src/stores/autopilot.js` - Use centralized strategy types

### Phase 6: Refactor Backend Seed Script

**File: `backend/scripts/seed_strategies.py`**
- Import from `backend/app/constants/strategy_types.py` instead of hardcoding

---

## Files to Modify

| File | Action |
|------|--------|
| `backend/app/constants/strategy_types.py` | CREATE - Single source of truth |
| `backend/app/constants/__init__.py` | CREATE - Package init |
| `backend/app/api/routes/constants.py` | CREATE - API endpoint |
| `backend/app/main.py` | MODIFY - Include constants router |
| `backend/scripts/seed_strategies.py` | MODIFY - Import from constants |
| `frontend/src/constants/strategyTypes.js` | CREATE - Frontend constants with API fetch |
| `frontend/src/views/StrategyBuilderView.vue` | MODIFY - Add Strategy Type dropdown |
| `frontend/src/views/autopilot/StrategyBuilderView.vue` | MODIFY - Add Strategy Type dropdown |
| `frontend/src/stores/strategy.js` | MODIFY - Remove hardcoded array, use constants |
| `frontend/src/stores/strategyLibrary.js` | MODIFY - Use centralized categories |
| `frontend/src/stores/autopilot.js` | MODIFY - Add strategy_type field to builder |
| `frontend/src/components/common/ConfirmDialog.vue` | CREATE or REUSE - Confirmation modal |

---

## Strategy Types to Include (20 total from seed_strategies.py)

### Bullish (3)
- `bull_call_spread` - 2 legs: Buy ATM CE, Sell ATM+100 CE
- `bull_put_spread` - 2 legs: Sell ATM PE, Buy ATM-100 PE
- `synthetic_long` - 2 legs: Buy ATM CE, Sell ATM PE

### Bearish (3)
- `bear_put_spread` - 2 legs: Buy ATM PE, Sell ATM-100 PE
- `bear_call_spread` - 2 legs: Sell ATM CE, Buy ATM+100 CE
- `synthetic_short` - 2 legs: Buy ATM PE, Sell ATM CE

### Neutral (5)
- `iron_condor` - 4 legs: Buy ATM-200 PE, Sell ATM-100 PE, Sell ATM+100 CE, Buy ATM+200 CE
- `iron_butterfly` - 4 legs: Buy ATM-100 PE, Sell ATM PE, Sell ATM CE, Buy ATM+100 CE
- `short_straddle` - 2 legs: Sell ATM CE, Sell ATM PE
- `short_strangle` - 2 legs: Sell ATM+100 CE, Sell ATM-100 PE
- `jade_lizard` - 3 legs: Sell ATM-100 PE, Sell ATM+100 CE, Buy ATM+200 CE

### Volatile (3)
- `long_straddle` - 2 legs: Buy ATM CE, Buy ATM PE
- `long_strangle` - 2 legs: Buy ATM+100 CE, Buy ATM-100 PE
- `reverse_iron_condor` - 4 legs: Sell ATM-200 PE, Buy ATM-100 PE, Buy ATM+100 CE, Sell ATM+200 CE

### Income (3)
- `covered_call` - 2 legs: Buy EQ, Sell ATM+100 CE
- `cash_secured_put` - 1 leg: Sell ATM-100 PE
- `wheel_strategy` - 1 leg: Sell ATM-100 PE (cycles with covered call)

### Advanced (3)
- `calendar_spread` - 2 legs: Sell ATM CE (current), Buy ATM CE (next month)
- `diagonal_spread` - 2 legs: Sell ATM+100 CE (current), Buy ATM CE (next month)
- `butterfly_spread` - 4 legs: Buy ATM-100 CE, Sell 2x ATM CE, Buy ATM+100 CE
- `ratio_backspread_call` - 3 legs: Sell ATM-100 CE, Buy 2x ATM CE
- `ratio_backspread_put` - 3 legs: Sell ATM+100 PE, Buy 2x ATM PE

### Custom
- `custom` - Manual entry (no auto-populate)

---

## UX Flow After Implementation

### Flow 1: New Strategy Creation
1. User opens Strategy Builder (regular or AutoPilot)
2. Selects "Strategy Type: Iron Condor" from dropdown
3. System auto-populates 4 legs with correct buy/sell, CE/PE configuration
4. Strike offsets shown (ATM-200, ATM-100, ATM+100, ATM+200)
5. User adjusts if needed and proceeds

### Flow 2: Changing Strategy Type (with existing legs)
1. User has already added 2 legs manually
2. User changes Strategy Type to "Short Straddle"
3. **Confirmation dialog appears**: "Replace Existing Legs? Changing strategy type will replace your current legs. Continue?"
4. User clicks "Replace" → legs replaced with 2 straddle legs
5. OR User clicks "Cancel" → dropdown reverts, legs unchanged

---

## Implementation Order

1. **Backend first** - Create constants file and API endpoint
2. **Frontend constants** - Create constants file with API fetch
3. **AutoPilot Builder** - Add dropdown with auto-populate logic
4. **Regular Strategy Builder** - Add same dropdown (reuse logic)
5. **Refactor stores** - Remove hardcoded arrays, use centralized data
6. **Seed script** - Import from constants instead of hardcoding

---

## Testing Checklist

- [ ] API endpoint returns all strategy types with leg configs
- [ ] Dropdown shows strategies grouped by category
- [ ] Selecting strategy auto-populates correct number of legs
- [ ] Confirmation dialog appears when replacing existing legs
- [ ] "Cancel" reverts dropdown selection
- [ ] "Custom" option allows manual leg entry
- [ ] Strategy types consistent across all screens
