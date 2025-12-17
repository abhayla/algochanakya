# AutoPilot Redesign Implementation Plan

## Overview

Complete redesign of AutoPilot screens inspired by Opstra/Tradetron patterns, focusing on:
1. **Strike Selection UI** - Delta, premium, SD-based strike pickers
2. **Premium Monitoring** - Straddle charts, decay visualization
3. **Re-Entry & Adjustments** - Auto re-entry, rule-based adjustments
4. **UX Polish** - Visual condition builder, monitoring dashboard

## Research Summary

### Industry Best Practices (Opstra/Tradetron/Sensibull)

| Platform | Key Feature |
|----------|-------------|
| **Tradetron** | `ATM`, `ATM+100`, `delta=0.30`, `premium=150` syntax, drag-drop builder |
| **Opstra** | Multi-strike straddle charts, premium decay, IV surface visualization |
| **Sensibull** | Conditional exits with payoff preview, graph interaction |
| **Dhan** | 9-condition Quant Mode for strike selection |

### Current Implementation Status

**Already Working:**
- `StrikeFinderService` with `find_strike_by_delta()`, `find_strike_by_premium()`, `find_strike_by_standard_deviation()`
- Condition engine with TIME, SPOT, VIX, Greeks, OI, IV, Probability variables
- AND/OR nested condition groups
- Adjustment engine with multiple trigger/action types
- Delta band gauge monitoring

**Key Gaps:**
- Order executor doesn't use StrikeFinderService (uses rough estimate)
- No strike selection UI (only manual input)
- No premium monitoring charts
- No re-entry logic
- No visual strike ladder during selection

---

## Phase 1: Strike Selection Enhancement (Week 1)

### 1.1 Backend: Connect OrderExecutor to StrikeFinderService

**File:** `backend/app/services/order_executor.py`

**Current (Lines 509-517):**
```python
elif mode == 'delta_based':
    target_delta = strike_selection.get('target_delta', 0.5)
    steps_away = int((0.5 - abs(target_delta)) / 0.05)  # Rough estimate
```

**Change:** Replace rough estimate with actual StrikeFinderService call:
```python
elif mode == 'delta_based':
    target_delta = strike_selection.get('target_delta', 0.3)
    strike_result = await self.strike_finder.find_strike_by_delta(
        underlying=underlying,
        expiry=expiry,
        option_type=contract_type,
        target_delta=target_delta,
        prefer_round_strike=True
    )
    if strike_result.success:
        strike = strike_result.strike
    else:
        raise ValueError(f"Could not find strike for delta {target_delta}")
```

**Similarly for:**
- `premium_based` mode → `find_strike_by_premium()`
- `sd_based` mode (new) → `find_strike_by_standard_deviation()`

### 1.2 Frontend: Strike Selection Mode Picker

**New Component:** `frontend/src/components/autopilot/builder/StrikeSelector.vue`

**UI Design (Inspired by Tradetron):**
```
┌─────────────────────────────────────────────────────────┐
│ Strike Selection Mode                                    │
│ ○ Fixed Strike   ○ ATM Offset   ● Delta   ○ Premium   ○ SD │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────┐                                      │
│ │ Target Delta    │  [0.30] ▼                            │
│ └─────────────────┘                                      │
│ Quick Select: [0.15] [0.20] [0.25] [0.30] [0.35]        │
│                                                          │
│ Preview: ~24,200 CE @ ₹142 (0.28Δ)                       │
│          ~24,800 PE @ ₹138 (0.31Δ)                       │
└─────────────────────────────────────────────────────────┘
```

**Props:**
```typescript
interface StrikeSelectorProps {
  underlying: string;
  expiry: string;
  optionType: 'CE' | 'PE';
  mode: 'fixed' | 'atm_offset' | 'delta' | 'premium' | 'sd';
  value: StrikeConfig;
}
```

### 1.3 Frontend: Visual Strike Ladder

**New Component:** `frontend/src/components/autopilot/builder/StrikeLadder.vue`

**UI Design (Inspired by Opstra Option Chain):**
```
┌──────────────────────────────────────────────────────────┐
│ Strike Ladder - NIFTY 26-Dec-2024                         │
├────────┬────────┬────────┬─────────┬────────┬────────────┤
│ CE Δ   │ CE LTP │ Strike │ PE LTP  │ PE Δ   │ Select     │
├────────┼────────┼────────┼─────────┼────────┼────────────┤
│ 0.65   │ ₹342   │ 24000  │ ₹48     │ 0.15   │ [CE] [PE]  │
│ 0.55   │ ₹248   │ 24100  │ ₹62     │ 0.22   │ [CE] [PE]  │
│ 0.45   │ ₹168   │ 24200  │ ₹85     │ 0.30   │ [CE] [PE]  │ ← ATM
│ 0.35   │ ₹108   │ 24300  │ ₹118    │ 0.38   │ [CE] [PE]  │
│ 0.25   │ ₹68    │ 24400  │ ₹162    │ 0.48   │ [CE] [PE]  │
└────────┴────────┴────────┴─────────┴────────┴────────────┘
```

**Features:**
- Real-time LTP and Delta display
- Click to select strike
- Highlight ATM row
- Show expected move range
- Filter by delta range

### 1.4 API: Strike Preview Endpoint

**New Endpoint:** `GET /api/v1/autopilot/strikes/preview`

**Request:**
```json
{
  "underlying": "NIFTY",
  "expiry": "2024-12-26",
  "mode": "delta",
  "target_delta": 0.30,
  "option_type": "CE"
}
```

**Response:**
```json
{
  "strike": 24200,
  "ltp": 142.50,
  "delta": 0.28,
  "gamma": 0.0023,
  "theta": -12.5,
  "iv": 14.2,
  "expected_move": {
    "1sd": { "lower": 24050, "upper": 24350 },
    "2sd": { "lower": 23900, "upper": 24500 }
  }
}
```

---

## Phase 2: Premium Monitoring & Visualization (Week 2)

### 2.1 Backend: Premium Tracking Service

**New File:** `backend/app/services/premium_tracker.py`

```python
class PremiumTracker:
    async def get_straddle_premium(
        self, underlying: str, expiry: str, strike: int
    ) -> StraddlePremium:
        """Get combined CE+PE premium for a strike"""

    async def get_premium_history(
        self, strategy_id: int, interval: str = "1m"
    ) -> List[PremiumSnapshot]:
        """Get premium history for charting"""

    async def get_premium_decay_curve(
        self, strategy_id: int
    ) -> DecayCurve:
        """Expected vs actual theta decay"""
```

### 2.2 Frontend: Straddle Premium Chart

**New Component:** `frontend/src/components/autopilot/monitoring/StraddlePremiumChart.vue`

**UI Design (Inspired by Opstra Straddle Charts):**
```
┌─────────────────────────────────────────────────────────┐
│ Premium Monitor - Iron Condor                            │
│                                                          │
│  ₹850 ┤                                                  │
│       │    ╭──────╮                                      │
│  ₹800 ┤   ╱        ╲    Entry: ₹842                      │
│       │  ╱          ╲                                    │
│  ₹750 ┤ ╱            ╲──────────  Current: ₹756         │
│       │╱                                                 │
│  ₹700 ┼────────────────────────────────────────────────  │
│       9:15   10:00   11:00   12:00   13:00   14:00      │
│                                                          │
│ Premium Captured: 10.2% (₹86)  |  Target: 50% (₹421)    │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- Real-time premium line chart
- Entry premium marker
- Target profit line
- Stop-loss line
- Premium captured percentage

### 2.3 Frontend: Premium Decay Visualization

**New Component:** `frontend/src/components/autopilot/monitoring/ThetaDecayChart.vue`

**UI Design:**
```
┌─────────────────────────────────────────────────────────┐
│ Theta Decay - Expected vs Actual                         │
│                                                          │
│  100% ┤ ●                                                │
│       │  ╲                                               │
│   75% ┤   ╲___  Expected (dotted)                        │
│       │    ╲__╲___                                       │
│   50% ┤     ●  ╲___╲___  Actual (solid)                  │
│       │          ╲___╲___                                │
│   25% ┤               ╲___╲___                           │
│       │                    ╲___╲___                      │
│    0% ┼────────────────────────────────────────────────  │
│       Entry      Mid-point       Expiry                  │
│                                                          │
│ Decay Rate: 1.2x faster than expected                    │
└─────────────────────────────────────────────────────────┘
```

### 2.4 Dashboard Enhancement: Premium Widgets

**Modify:** `frontend/src/views/autopilot/DashboardView.vue`

Add new widgets:
- Combined premium tracker (all active strategies)
- Top premium capturers (sorted by % captured)
- Premium at risk (strategies near SL)

---

## Phase 3: Re-Entry & Advanced Adjustments (Week 3)

### 3.1 Backend: Re-Entry Logic

**Modify:** `backend/app/models/autopilot.py`

Add new status:
```python
class StrategyStatus(str, Enum):
    # ... existing statuses
    REENTRY_WAITING = "reentry_waiting"
```

Add re-entry config to strategy:
```python
reentry_config = Column(JSONB, nullable=True, default=None)
# Structure:
# {
#     "enabled": true,
#     "max_reentries": 2,
#     "cooldown_minutes": 15,
#     "conditions": { "logic": "AND", "conditions": [...] },
#     "reentry_count": 0
# }
```

**Modify:** `backend/app/services/strategy_monitor.py`

Add re-entry evaluation:
```python
async def _check_reentry(self, db: AsyncSession, strategy: AutoPilotStrategy):
    """Check if exited strategy should re-enter"""
    if strategy.status != StrategyStatus.REENTRY_WAITING:
        return

    reentry_config = strategy.reentry_config or {}
    if not reentry_config.get('enabled'):
        return

    # Check cooldown
    if not self._cooldown_elapsed(strategy):
        return

    # Check max re-entries
    if reentry_config.get('reentry_count', 0) >= reentry_config.get('max_reentries', 1):
        return

    # Evaluate re-entry conditions
    eval_result = await self.condition_engine.evaluate(
        strategy_id=strategy.id,
        entry_conditions=reentry_config.get('conditions', {}),
        underlying=strategy.underlying,
        legs_config=strategy.legs_config
    )

    if eval_result.all_conditions_met:
        await self._execute_reentry(db, strategy)
```

### 3.2 Frontend: Re-Entry Configuration

**New Component:** `frontend/src/components/autopilot/builder/ReentryConfig.vue`

**UI Design:**
```
┌─────────────────────────────────────────────────────────┐
│ Re-Entry Settings                                        │
│                                                          │
│ [✓] Enable automatic re-entry after exit                 │
│                                                          │
│ Max Re-entries: [2] ▼                                    │
│ Cooldown after exit: [15] minutes                        │
│                                                          │
│ Re-entry Conditions:                                     │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [AND]                                                │ │
│ │  • TIME.CURRENT >= 10:00                             │ │
│ │  • SPOT.NIFTY.CHANGE_PCT < 0.5%                      │ │
│ │  • VIX.VALUE < 18                                    │ │
│ │  [+ Add Condition]                                   │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 3.3 Adjustment Rule Builder Enhancement

**Modify:** `frontend/src/components/autopilot/builder/AdjustmentRuleBuilder.vue`

Add visual rule builder with:
- Trigger condition selector (P&L, Delta, Time, Premium, VIX, Spot)
- Action selector with previews (Exit, Add Hedge, Roll, Scale)
- Cooldown and max executions
- Drag-drop reordering

**UI Design:**
```
┌─────────────────────────────────────────────────────────┐
│ Adjustment Rules                                         │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Rule 1: Delta Hedge                           [≡] [×]│ │
│ │ WHEN: Net Delta > 0.30                               │ │
│ │ THEN: Add hedge (both sides)                         │ │
│ │ Cooldown: 5 min | Max: 2 times                       │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Rule 2: Profit Book                           [≡] [×]│ │
│ │ WHEN: P&L > 50% of max profit                        │ │
│ │ THEN: Exit all positions                             │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ [+ Add Adjustment Rule]                                  │
└─────────────────────────────────────────────────────────┘
```

### 3.4 Roll Wizard

**New Component:** `frontend/src/components/autopilot/adjustments/RollWizard.vue`

**UI Design:**
```
┌─────────────────────────────────────────────────────────┐
│ Roll Strategy                                            │
│                                                          │
│ Current Position:                                        │
│  SELL 24200 CE @ ₹85 (Δ 0.35)                           │
│  SELL 24000 PE @ ₹72 (Δ 0.28)                           │
│                                                          │
│ Roll To:                                                 │
│  ○ Next Week Expiry (same strikes)                      │
│  ○ Same Expiry (new strikes)                            │
│  ● Next Week + New Strikes                              │
│                                                          │
│ New Strikes:                                             │
│  CE: [24300] ▼  (Δ 0.28, ₹62)                           │
│  PE: [23900] ▼  (Δ 0.25, ₹58)                           │
│                                                          │
│ Estimated Credit: ₹120 - ₹157 = -₹37 (debit)            │
│                                                          │
│ [Preview Payoff]  [Cancel]  [Execute Roll]              │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 4: UX Polish & Dashboard (Week 4)

### 4.1 Enhanced Condition Builder

**Modify:** `frontend/src/components/autopilot/builder/ConditionBuilder.vue`

Improvements:
- Visual expression tree (like a flowchart)
- Drag-drop condition reordering
- Inline value presets (time picker, delta slider)
- Real-time condition evaluation preview
- Natural language summary

**UI Design:**
```
┌─────────────────────────────────────────────────────────┐
│ Entry Conditions                                         │
│                                                          │
│ ┌─ AND ────────────────────────────────────────────────┐│
│ │  ┌──────────────────────────────────────────────────┐││
│ │  │ TIME.CURRENT >= [09:20] ▼              [✓] [×]   │││
│ │  └──────────────────────────────────────────────────┘││
│ │           │                                          ││
│ │  ┌── OR ──┴──────────────────────────────────────┐  ││
│ │  │  ┌────────────────────────────────────────┐   │  ││
│ │  │  │ VIX.VALUE < [15] ▼           [✓] [×]   │   │  ││
│ │  │  └────────────────────────────────────────┘   │  ││
│ │  │  ┌────────────────────────────────────────┐   │  ││
│ │  │  │ IV.RANK < [30] ▼             [✓] [×]   │   │  ││
│ │  │  └────────────────────────────────────────┘   │  ││
│ │  └───────────────────────────────────────────────┘  ││
│ └──────────────────────────────────────────────────────┘│
│                                                          │
│ Summary: "Enter after 9:20 AM when VIX < 15 OR IV < 30" │
│ Current Status: [⏳ Waiting - TIME not met]              │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Enhanced Dashboard

**Modify:** `frontend/src/views/autopilot/DashboardView.vue`

New sections:
- **Strategy Cards** with live P&L, delta gauge, premium captured
- **Activity Timeline** with order fills, adjustments, alerts
- **Risk Overview** panel with margin usage, delta exposure
- **Quick Actions** bar (pause all, kill switch, create strategy)

### 4.3 Strategy Detail View Enhancement

**Modify:** `frontend/src/views/autopilot/StrategyDetailView.vue`

Add tabs:
- **Overview** - Current status, P&L, Greeks summary
- **Positions** - Leg cards with live data
- **Charts** - Premium chart, delta history, P&L curve
- **Conditions** - Entry/exit condition status with progress
- **Activity** - Orders, adjustments, logs timeline
- **Settings** - Edit risk settings, adjustments

---

## Files to Modify

### Backend

| File | Changes |
|------|---------|
| `backend/app/services/order_executor.py` | Connect to StrikeFinderService |
| `backend/app/services/strategy_monitor.py` | Add re-entry logic |
| `backend/app/models/autopilot.py` | Add REENTRY_WAITING status, reentry_config column |
| `backend/app/api/v1/autopilot/router.py` | Add strike preview endpoint |
| `backend/app/services/premium_tracker.py` | **NEW** - Premium tracking service |

### Frontend

| File | Changes |
|------|---------|
| `frontend/src/components/autopilot/builder/StrikeSelector.vue` | **NEW** - Strike mode picker |
| `frontend/src/components/autopilot/builder/StrikeLadder.vue` | **NEW** - Visual strike ladder |
| `frontend/src/components/autopilot/builder/ReentryConfig.vue` | **NEW** - Re-entry settings |
| `frontend/src/components/autopilot/builder/AdjustmentRuleBuilder.vue` | **NEW** - Visual rule builder |
| `frontend/src/components/autopilot/monitoring/StraddlePremiumChart.vue` | **NEW** - Premium chart |
| `frontend/src/components/autopilot/monitoring/ThetaDecayChart.vue` | **NEW** - Decay visualization |
| `frontend/src/components/autopilot/adjustments/RollWizard.vue` | **NEW** - Roll wizard |
| `frontend/src/components/autopilot/builder/ConditionBuilder.vue` | Enhance with visual tree |
| `frontend/src/views/autopilot/StrategyBuilderView.vue` | Integrate new components |
| `frontend/src/views/autopilot/DashboardView.vue` | Add premium widgets |
| `frontend/src/views/autopilot/StrategyDetailView.vue` | Add charts tab |
| `frontend/src/stores/autopilot.js` | Add premium tracking, re-entry state |

### Database Migration

| Migration | Changes |
|-----------|---------|
| `backend/alembic/versions/xxx_reentry_config.py` | Add reentry_config column, new status |

---

## Implementation Order

1. **Week 1: Strike Selection**
   - Day 1-2: Backend OrderExecutor ↔ StrikeFinderService integration
   - Day 3-4: StrikeSelector.vue component
   - Day 5: StrikeLadder.vue component
   - Day 6-7: Integration testing, API endpoint

2. **Week 2: Premium Monitoring**
   - Day 1-2: PremiumTracker service
   - Day 3-4: StraddlePremiumChart.vue
   - Day 5: ThetaDecayChart.vue
   - Day 6-7: Dashboard widget integration

3. **Week 3: Re-Entry & Adjustments**
   - Day 1-2: Backend re-entry logic + migration
   - Day 3-4: ReentryConfig.vue
   - Day 5: AdjustmentRuleBuilder.vue enhancement
   - Day 6-7: RollWizard.vue

4. **Week 4: UX Polish**
   - Day 1-3: ConditionBuilder.vue enhancement
   - Day 4-5: Dashboard enhancements
   - Day 6-7: StrategyDetailView tabs, final polish

---

## Success Criteria

- [ ] Strike selection supports delta, premium, SD modes with live preview
- [ ] Premium charts show real-time decay vs expected
- [ ] Re-entry works automatically based on configured conditions
- [ ] Adjustment rules can be visually configured and auto-execute
- [ ] Condition builder shows visual tree with real-time evaluation
- [ ] Dashboard provides at-a-glance portfolio view with risk metrics
