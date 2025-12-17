# Phase 3: Re-Entry & Advanced Adjustments

**Implementation Date:** December 2024
**Status:** ✅ Complete

## Overview

Phase 3 adds automatic re-entry capabilities and visual adjustment rule building to AutoPilot, enabling strategies to automatically re-enter after exit conditions trigger and execute complex adjustment rules based on market conditions.

## Features Implemented

### 1. Backend: Re-Entry System

**Files Modified:**
- `backend/app/models/autopilot.py` - Added REENTRY_WAITING status and reentry_config column
- `backend/app/services/strategy_monitor.py` - Implemented re-entry logic
- `backend/alembic/versions/007_autopilot_phase3_reentry.py` - Database migration

#### New Status: REENTRY_WAITING

Strategies can now enter `REENTRY_WAITING` status after exit, waiting for re-entry conditions to be met.

```python
class StrategyStatus(str, enum.Enum):
    DRAFT = "draft"
    WAITING = "waiting"
    ACTIVE = "active"
    PAUSED = "paused"
    REENTRY_WAITING = "reentry_waiting"  # Phase 3: New status
    COMPLETED = "completed"
    ERROR = "error"
```

#### Re-Entry Configuration Structure

```python
reentry_config = {
    "enabled": True,
    "max_reentries": 2,
    "cooldown_minutes": 15,
    "conditions": {
        "logic": "AND",
        "conditions": [
            {"variable": "TIME.CURRENT", "operator": ">=", "value": "10:00"},
            {"variable": "SPOT.NIFTY.CHANGE_PCT", "operator": "<", "value": 0.5},
            {"variable": "VIX.VALUE", "operator": "<", "value": 18}
        ]
    },
    "reentry_count": 0  # Incremented on each re-entry
}
```

#### Re-Entry Logic Flow

```python
async def _check_reentry(self, db: AsyncSession, strategy: AutoPilotStrategy):
    """
    Re-entry check flow:
    1. Check if re-entry enabled
    2. Check max re-entries limit
    3. Check cooldown period
    4. Evaluate re-entry conditions
    5. Execute re-entry if all checks pass
    """
```

**Implementation Details:**

1. **Max Re-Entries Limit**
   - Configurable (1-10 times)
   - When limit reached, strategy marks as COMPLETED
   - Counter persists across re-entries

2. **Cooldown Period**
   - Configurable (5 minutes to 2 hours)
   - Calculated from `completed_at` timestamp
   - Prevents immediate re-entry after exit

3. **Condition Evaluation**
   - Uses existing ConditionEngine
   - Supports same variable types as entry conditions
   - Saves evaluation to `autopilot_condition_eval` table

4. **Re-Entry Execution**
   - Changes status back to WAITING
   - Increments `reentry_count`
   - Clears `completed_at` timestamp
   - Logs event and sends WebSocket update

### 2. Frontend: ReentryConfig Component

**File:** `frontend/src/components/autopilot/builder/ReentryConfig.vue` (215 lines)

Visual configuration interface for re-entry settings.

#### Features

- **Enable/Disable Toggle** - Main on/off switch with visual slider
- **Max Re-entries Dropdown** - Options: 1, 2, 3, 5, 10 times
- **Cooldown Selector** - Options: 5min, 10min, 15min, 30min, 1hr, 2hr
- **Condition Builder Integration** - Uses existing ConditionBuilder for re-entry conditions
- **Info Box** - Explains how re-entry works step-by-step
- **Disabled State** - Empty state with explanation when disabled

#### Usage

```vue
<ReentryConfig
  v-model="strategy.reentry_config"
/>
```

#### Props

```typescript
interface ReentryConfigProps {
  modelValue: {
    enabled: boolean
    max_reentries: number
    cooldown_minutes: number
    conditions: ConditionGroup
    reentry_count: number
  }
}
```

### 3. Frontend: AdjustmentRuleBuilder Component

**File:** `frontend/src/components/autopilot/builder/AdjustmentRuleBuilder.vue` (610 lines)

Visual builder for creating adjustment rules with drag-drop reordering.

#### Features

**Trigger Types:**
- 💰 **P&L Based** - Trigger on profit/loss amount or %
- **Δ Delta Based** - Trigger when net delta exceeds threshold
- ⏰ **Time Based** - Trigger at specific time or after duration
- 📊 **Premium Based** - Trigger on premium captured %
- 📈 **VIX Based** - Trigger when VIX crosses threshold
- 🎯 **Spot Based** - Trigger when spot price moves by %

**Action Types:**
- 🚪 **Exit All** - Close all positions immediately
- 🛡️ **Add Hedge** - Add hedge on both sides
- ❌ **Close Leg** - Close specific leg(s)
- 🔄 **Roll Strike** - Roll to new strikes
- 📅 **Roll Expiry** - Roll to next expiry
- 📉 **Scale Down** - Reduce position size
- 📈 **Scale Up** - Increase position size

#### Rule Display

Each rule card shows:
- **WHEN → THEN** flow visualization with icons
- Trigger summary (e.g., "P&L > 50%")
- Action summary (e.g., "Exit All")
- Cooldown period
- Max executions
- Execution count (if executed)
- Enable/Disable status badge

#### Rule Management

- **Add Rule** - Opens modal editor
- **Edit Rule** - Click to modify existing rule
- **Delete Rule** - Confirmation before deletion
- **Move Up/Down** - Reorder rules with ▲▼ buttons
- **Enable/Disable** - Toggle in editor modal

#### Modal Editor

Form fields:
- Rule Name (text input)
- Trigger Condition (dropdown with descriptions)
- Action (dropdown with descriptions)
- Cooldown (number input, seconds)
- Max Executions (number input)
- Enabled checkbox

### 4. Frontend: RollWizard Component

**File:** `frontend/src/components/autopilot/adjustments/RollWizard.vue` (655 lines)

Interactive wizard for rolling options positions to new strikes or expiries.

#### Features

**Roll Modes:**

1. **📅 Next Week (Same Strikes)**
   - Keep strike prices
   - Roll to next expiry
   - Simplest roll option

2. **🎯 Same Expiry (New Strikes)**
   - Keep current expiry
   - Adjust strike prices
   - Useful for delta adjustments

3. **🔄 Next Week + New Strikes**
   - Roll to next expiry
   - Adjust strike prices
   - Maximum flexibility

#### Wizard Flow

1. **Display Current Position**
   - Shows active CE/PE positions
   - Current premium values
   - Delta values

2. **Select Roll Mode**
   - Radio button selection with descriptions
   - Icons for visual identification

3. **Select Target Expiry** (if applicable)
   - Dropdown of available expiries
   - Auto-selects next available expiry

4. **Select New Strikes** (if applicable)
   - Separate dropdowns for CE and PE
   - Shows premium below each strike
   - Auto-populated with current strikes

5. **View Estimated Net**
   - Close Current: +₹X (credit received)
   - Open New: -₹Y (premium paid)
   - Net: Credit or Debit with color coding

6. **Execute Roll**
   - Preview Payoff button (placeholder)
   - Cancel button
   - Execute Roll button (disabled until valid selection)

#### Premium Calculation

```javascript
// Current premium (what we receive for closing)
currentPremium = currentCE + currentPE

// New premium (what we pay for opening)
newPremium = newCE + newPE

// Net credit/debit
estimatedCredit = currentPremium - newPremium
```

**Color Coding:**
- Green: Net Credit (profitable roll)
- Red: Net Debit (paying to roll)
- Gray: Break-even

## Database Migration

**File:** `backend/alembic/versions/007_autopilot_phase3_reentry.py`

Changes:
1. Add `reentry_waiting` value to `autopilot_strategy_status` enum
2. Add `reentry_config` JSONB column to `autopilot_strategies` table

**Migration Command:**
```bash
cd backend
alembic upgrade head
```

**Note:** PostgreSQL enums cannot remove values after adding them. Downgrade only drops the column.

## Integration Points

### Strategy Monitor Integration

Modified `_process_strategies()` to query `reentry_waiting` strategies:

```python
# Get all waiting, active, waiting_staged_entry, and reentry_waiting strategies
result = await db.execute(
    select(AutoPilotStrategy).where(
        AutoPilotStrategy.status.in_(["waiting", "active", "waiting_staged_entry", "reentry_waiting"])
    )
)
```

Added processing branch:

```python
elif strategy.status == "reentry_waiting":
    # Phase 3: Check re-entry conditions
    await self._check_reentry(db, strategy)
```

### WebSocket Updates

Re-entry events send WebSocket updates:
- `condition_evaluated` - When re-entry conditions checked
- `strategy_update` - When status changes (REENTRY_WAITING ↔ WAITING)
- `reentry_triggered` - When re-entry executes

### Logging

Re-entry events logged to `autopilot_logs`:
- `reentry_limit_reached` - When max re-entries hit
- `reentry_triggered` - When re-entry executes
- `reentry_conditions_not_met` - When conditions fail (debug level)

## Usage Examples

### 1. Configure Re-Entry in Strategy Builder

```vue
<template>
  <div class="strategy-builder">
    <!-- Other configuration sections -->

    <!-- Re-Entry Configuration -->
    <ReentryConfig
      v-model="strategy.reentry_config"
    />
  </div>
</template>

<script setup>
const strategy = ref({
  name: 'Daily Iron Condor',
  reentry_config: {
    enabled: true,
    max_reentries: 2,
    cooldown_minutes: 15,
    conditions: {
      logic: 'AND',
      conditions: [
        { variable: 'TIME.CURRENT', operator: '>=', value: '10:00' },
        { variable: 'VIX.VALUE', operator: '<', value: 18 }
      ]
    },
    reentry_count: 0
  }
})
</script>
```

### 2. Configure Adjustment Rules

```vue
<template>
  <AdjustmentRuleBuilder
    v-model="strategy.adjustment_rules"
  />
</template>

<script setup>
const strategy = ref({
  adjustment_rules: [
    {
      name: 'Delta Hedge',
      trigger_type: 'delta_based',
      trigger_config: { threshold: 0.3 },
      action_type: 'add_hedge',
      action_config: { both_sides: true },
      cooldown_seconds: 300,
      max_executions: 2,
      enabled: true
    },
    {
      name: 'Profit Book',
      trigger_type: 'pnl_based',
      trigger_config: { threshold: 50, threshold_type: 'pct', comparison: 'greater_than' },
      action_type: 'exit_all',
      action_config: {},
      cooldown_seconds: 0,
      max_executions: 1,
      enabled: true
    }
  ]
})
</script>
```

### 3. Use Roll Wizard

```vue
<template>
  <RollWizard
    :show="showRollWizard"
    :strategy-id="strategy.id"
    :current-positions="strategy.position_legs"
    :underlying="strategy.underlying"
    :current-expiry="strategy.expiry_date"
    @close="showRollWizard = false"
    @roll-executed="handleRollExecuted"
  />
</template>

<script setup>
const showRollWizard = ref(false)

const handleRollExecuted = (rollConfig) => {
  console.log('Roll executed:', rollConfig)
  // Refresh strategy data
  fetchStrategy()
}
</script>
```

## API Endpoints (Future)

While the UI is complete, these endpoints are placeholders for full implementation:

```
POST /api/v1/autopilot/strategies/{id}/roll
Body: {
  mode: "next_week_new_strikes",
  target_expiry: "2024-12-27",
  new_ce_strike: 24300,
  new_pe_strike: 23900
}

GET /api/v1/autopilot/strategies/{id}/roll-preview
Query: ?mode=next_week_new_strikes&ce_strike=24300&pe_strike=23900
Response: Payoff curve data for preview
```

## Testing Checklist

### Backend Testing

- [ ] Re-entry status transitions correctly
- [ ] Max re-entries limit enforced
- [ ] Cooldown period calculated correctly
- [ ] Re-entry conditions evaluated properly
- [ ] Logs created for re-entry events
- [ ] WebSocket updates sent on status change

### Frontend Testing

**ReentryConfig Component:**
- [ ] Toggle enables/disables configuration
- [ ] Max reentries dropdown works
- [ ] Cooldown selector works
- [ ] Condition builder integrates correctly
- [ ] Info box displays properly
- [ ] Disabled state shows correctly

**AdjustmentRuleBuilder Component:**
- [ ] Add rule opens modal
- [ ] Edit rule loads correct data
- [ ] Delete rule shows confirmation
- [ ] Move up/down reorders rules
- [ ] Trigger types show descriptions
- [ ] Action types show descriptions
- [ ] Empty state displays correctly

**RollWizard Component:**
- [ ] Current position displays correctly
- [ ] Roll modes switch properly
- [ ] Expiry selector populates
- [ ] Strike selectors populate
- [ ] Premium values fetch correctly
- [ ] Net credit/debit calculates correctly
- [ ] Color coding applies (green/red/gray)
- [ ] Execute button disabled until valid
- [ ] Loading state shows during execution

## Known Limitations

1. **Re-Entry History** - No separate table tracking re-entry history. All logged to `autopilot_logs`.

2. **Roll Execution** - RollWizard UI complete but backend endpoint placeholder. Requires:
   - Order sequencing logic (close old, open new)
   - Slippage handling
   - Partial fill scenarios
   - Position tracking updates

3. **Adjustment Rule Execution** - Rules are created/stored but execution requires:
   - `AdjustmentEngine` enhancement
   - Action-specific execution logic
   - Cooldown tracking in runtime state

4. **Payoff Preview** - RollWizard preview button is placeholder. Requires:
   - P&L calculator integration
   - Chart rendering for new strikes/expiry
   - Comparison with current payoff

5. **Trigger Config Details** - AdjustmentRuleBuilder modal shows basic fields only. Each trigger type needs specific config UI:
   - P&L: amount vs %, threshold value
   - Delta: threshold, comparison
   - Time: specific time vs duration
   - Premium: captured %
   - VIX/Spot: threshold, comparison

## Future Enhancements

### Phase 3.5: Advanced Rule Execution

1. **Conditional Execution**
   - IF condition THEN action ELSE alternative action
   - Multiple actions per rule
   - Action priority/sequencing

2. **Dynamic Cooldowns**
   - Cooldown based on market conditions
   - Accelerated cooldown if conditions worsen
   - Reset cooldown on manual intervention

3. **Backtesting**
   - Test adjustment rules on historical data
   - Optimize trigger thresholds
   - Compare rule effectiveness

4. **ML-Based Adjustments**
   - Learn optimal adjustment timing
   - Predict when adjustment needed
   - Suggest rule improvements

### Phase 3.6: Roll Enhancements

1. **Smart Strike Selection**
   - AI-suggested strikes based on IV
   - Delta-neutral roll recommendations
   - Cost-optimized roll paths

2. **Multi-Leg Rolls**
   - Roll only one side (CE or PE)
   - Partial rolls (roll 1 of 2 lots)
   - Asymmetric rolls (different expiries per side)

3. **Roll Scheduling**
   - Schedule rolls for specific time/date
   - Auto-roll X days before expiry
   - Roll based on VIX levels

## Related Documentation

- [AutoPilot Full Plan](../plans/AutoPilot-Redesign-Implementation-Plan-Full.md) - Complete 4-phase plan
- [Phase 2: Premium Monitoring](./Phase2-Premium-Monitoring.md) - Previous phase
- [Database Schema](./database-schema.md) - Full database structure
- [Condition Engine](./condition-engine.md) - Condition evaluation system

## Changelog

| Date | Change | Files |
|------|--------|-------|
| 2024-12-17 | Added REENTRY_WAITING status | autopilot.py |
| 2024-12-17 | Created migration for re-entry | 007_autopilot_phase3_reentry.py |
| 2024-12-17 | Implemented re-entry logic | strategy_monitor.py |
| 2024-12-17 | Created ReentryConfig component | ReentryConfig.vue |
| 2024-12-17 | Created AdjustmentRuleBuilder component | AdjustmentRuleBuilder.vue |
| 2024-12-17 | Created RollWizard component | RollWizard.vue |
| 2024-12-17 | Completed Phase 3 documentation | Phase3-ReEntry-Adjustments.md |

---

**Next Phase:** Phase 4 - UX Polish & Dashboard Enhancements (see full plan for details)
