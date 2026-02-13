# AutoPilot Phase 5 - Advanced Adjustments & Option Chain Integration

## Planning Document

**Project:** AlgoChanakya  
**Feature:** AutoPilot - Advanced Adjustments  
**Phase:** 5  
**Document Version:** 1.0  
**Created:** December 2024  
**Prerequisites:** Phase 1-4 Complete

---

## Executive Summary

Phase 5 addresses critical gaps identified when comparing AutoPilot's current capabilities against real-world professional adjustment strategies (specifically the "Break/Split Trade" technique used by experienced option sellers).

**Current State:** AutoPilot can create strategies, monitor conditions, and execute basic adjustments.

**Gap:** Cannot handle sophisticated real-time adjustments based on Greeks, cannot find strikes by delta/premium, cannot split losing trades into recovery positions, and lacks per-leg management.

**Goal:** Enable traders to execute professional-grade adjustments like shifting legs, breaking trades, and managing positions at the individual leg level.

---

## Reference: The Strategy We Must Support

### Strangle Adjustment Workflow (from Video)

```
Day 1: Sell 15-delta strangle
        - Sell 25000 PE (15 delta)
        - Sell 26800 CE (15 delta)

Day 3: Market falls, PUT delta doubles to 33
        - CALL premium decays to ₹51
        - ACTION: Book profit on CALL, shift down to 26200 CE

Day 5: Market breaks below 25000
        - Loss is ₹7,727
        - ACTION: BREAK THE TRADE
          1. Exit 25000 PE at ₹371
          2. Calculate recovery: ₹371 ÷ 2 = ₹185 per leg
          3. Find strikes with ~₹185 premium
          4. Sell 24400 PE at ₹160
          5. Sell 25300 CE at ₹207

Result: Position recentered, survived 750-point move, ended with ₹1,700 profit
```

### Key Techniques Used

| Technique | Description | Current Support |
|-----------|-------------|-----------------|
| Delta-based entry | Find 15 delta strikes | ❌ Missing |
| Delta monitoring | Track when delta doubles | ❌ Missing |
| Profitable leg shift | Move winning leg closer | ❌ Missing |
| Break/Split trade | Exit loser, split into 2 new positions | ❌ Missing |
| Premium-based strike finding | Find strikes by premium value | ❌ Missing |
| Per-leg management | Actions on individual legs | ❌ Missing |
| DTE-aware behavior | Different logic for month start vs end | ❌ Missing |

---

## Phase 5 Scope

### In Scope

1. Option Chain Integration (live data, strike lookup)
2. Delta-based & Premium-based Strike Selection
3. Per-Leg Position Management
4. Advanced Adjustment Actions (shift, split, roll)
5. Break/Split Trade Wizard
6. Real-time Greeks Monitoring per Leg
7. Time-to-Expiry Aware Logic
8. Adjustment Suggestions Engine
9. Position Visualization (P&L diagram, breakeven lines)
10. What-If Simulator for Adjustments

### Out of Scope

- Multi-expiry strategies (calendar spreads)
- Portfolio-level Greeks
- Automated machine learning suggestions
- Third-party signal integration

---

## Feature Specifications

### Feature 1: Option Chain Service

**Purpose:** Fetch and cache live option chain data with Greeks

**Data Required:**

```
OptionChainEntry {
  instrument_token: number
  tradingsymbol: string
  strike: number
  option_type: "CE" | "PE"
  expiry: date
  ltp: number
  bid: number
  ask: number
  volume: number
  oi: number
  oi_change: number
  iv: number
  delta: number
  gamma: number
  theta: number
  vega: number
}
```

**Capabilities:**

| Capability | Description |
|------------|-------------|
| Fetch full chain | Get all strikes for underlying + expiry |
| Filter by type | Get only CE or PE |
| Find by delta | Get strike closest to target delta |
| Find by premium | Get strike closest to target premium |
| Find by distance | Get strikes within X points of spot |
| Cache with TTL | Cache for 1-2 seconds to reduce API calls |
| Greeks calculation | Calculate Greeks if not from API |

**Strike Finder Queries:**

```
find_strike_by_delta(underlying, expiry, option_type, target_delta)
  → Returns strike where delta is closest to target

find_strike_by_premium(underlying, expiry, option_type, target_premium)
  → Returns strike where LTP is closest to target

find_strikes_in_range(underlying, expiry, option_type, min_premium, max_premium)
  → Returns all strikes with premium in range

find_atm_strike(underlying, expiry)
  → Returns ATM strike based on spot price

find_strikes_by_delta_range(underlying, expiry, option_type, min_delta, max_delta)
  → Returns all strikes with delta in range
```

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /option-chain/{underlying}/{expiry} | Full option chain |
| GET | /option-chain/{underlying}/{expiry}/strikes | Strike list only |
| GET | /option-chain/find-by-delta | Find strike by delta |
| GET | /option-chain/find-by-premium | Find strike by premium |
| GET | /option-chain/greeks/{tradingsymbol} | Greeks for specific option |

---

### Feature 2: Enhanced Strike Selection in Strategy Builder

**Purpose:** Allow strike selection by delta or premium, not just ATM offset

**Current Strike Selection Modes:**
- atm_offset: ATM + X points
- fixed: Specific strike number
- premium_based: (schema exists but not implemented)

**New Strike Selection Modes:**

| Mode | Description | Parameters |
|------|-------------|------------|
| delta_based | Find strike by delta | target_delta, tolerance |
| premium_based | Find strike by premium | target_premium, tolerance |
| delta_range | Delta between min and max | min_delta, max_delta |
| premium_range | Premium between min and max | min_premium, max_premium |

**Updated Strike Selection Schema:**

```
StrikeSelection {
  mode: "atm_offset" | "fixed" | "delta_based" | "premium_based" | "delta_range" | "premium_range"
  
  // For atm_offset
  offset: number
  
  // For fixed
  strike: number
  
  // For delta_based
  target_delta: number (0.05 to 0.95)
  delta_tolerance: number (default 0.02)
  
  // For premium_based
  target_premium: number
  premium_tolerance: number (default 10)
  
  // For range modes
  min_value: number
  max_value: number
  
  // Common
  prefer_round_strike: boolean (default true)
}
```

**Round Strike Preference Logic:**

```
If prefer_round_strike = true:
  - Prefer strikes divisible by 100 (25000, 25100, 25200)
  - If two strikes equally close, pick round figure
  - Example: 24950 vs 25000 with same delta → pick 25000
```

---

### Feature 3: Per-Leg Position Management

**Purpose:** Track, display, and manage each leg independently

**Current State:**
- Strategy has legs_config (configuration)
- No runtime tracking per leg
- No per-leg P&L
- No per-leg actions

**New Data Model - Position Legs:**

```
PositionLeg {
  leg_id: string (matches legs_config.leg_id)
  strategy_id: number
  
  // Configuration (from legs_config)
  contract_type: "CE" | "PE"
  action: "BUY" | "SELL"
  strike: number
  expiry: date
  lots: number
  
  // Runtime State
  status: "pending" | "open" | "closed" | "rolled"
  entry_price: number
  entry_time: datetime
  current_price: number
  exit_price: number
  exit_time: datetime
  
  // Greeks (updated real-time)
  delta: number
  gamma: number
  theta: number
  vega: number
  iv: number
  
  // P&L
  unrealized_pnl: number
  realized_pnl: number
  
  // Tracking
  tradingsymbol: string
  instrument_token: number
  order_ids: string[] (entry orders)
  exit_order_ids: string[] (exit orders)
  
  // Metadata
  created_at: datetime
  updated_at: datetime
}
```

**Per-Leg Actions:**

| Action | Description |
|--------|-------------|
| Exit Leg | Close this leg only |
| Roll Strike | Move to different strike, same expiry |
| Roll Expiry | Move to different expiry, same/different strike |
| Shift Leg | Close and reopen at better position (combines exit + new entry) |
| Add Hedge | Add protective option for this leg |
| Scale Down | Reduce lots for this leg |
| Scale Up | Increase lots for this leg |

**Per-Leg Display Requirements:**

```
┌─────────────────────────────────────────────────────────────┐
│ LEG 1: SELL 25000 PE                                   [⋮] │
├─────────────────────────────────────────────────────────────┤
│ Status: OPEN          Entry: ₹82.00       Current: ₹371.00 │
│ Lots: 1               Qty: 50             P&L: -₹14,450    │
├─────────────────────────────────────────────────────────────┤
│ Delta: 0.45 ▲         Theta: -₹125        IV: 18.5%        │
│ ITM by: 222 pts       DTE: 24 days                         │
├─────────────────────────────────────────────────────────────┤
│ [Exit] [Roll Strike] [Roll Expiry] [Add Hedge]             │
└─────────────────────────────────────────────────────────────┘
```

---

### Feature 4: Break/Split Trade

**Purpose:** The core technique from the video - exit a losing leg and split the loss recovery into two new positions

**When to Use:**
- Leg is deep in the money
- Delta has exceeded threshold (e.g., > 40)
- Significant unrealized loss
- Want to recenter position around current spot

**Break Trade Logic:**

```
BREAK TRADE ALGORITHM:

Input:
  - losing_leg: The leg to break
  - exit_price: Current market price to exit

Step 1: Calculate Exit Cost
  exit_cost = (exit_price - entry_price) * quantity * multiplier
  Example: (371 - 82) * 50 = ₹14,450 loss

Step 2: Calculate Recovery Premium
  target_premium_per_leg = exit_price / 2
  Example: 371 / 2 = ₹185.50 per new leg

Step 3: Find New Strikes
  new_put_strike = find_strike_by_premium(PE, target_premium)
  new_call_strike = find_strike_by_premium(CE, target_premium)
  
  // Adjust if one side has less premium
  If put_premium < target:
    call_target = exit_price - put_premium
    new_call_strike = find_strike_by_premium(CE, call_target)

Step 4: Execute
  a) Exit losing leg at market
  b) Sell new PUT at found strike
  c) Sell new CALL at found strike

Step 5: Update Position
  - Remove old leg
  - Add two new legs
  - Update strategy state
```

**Break Trade API:**

```
POST /api/v1/autopilot/strategies/{id}/legs/{leg_id}/break

Request:
{
  "execution_mode": "market" | "limit",
  "new_positions": "auto" | "manual",
  
  // If manual, specify strikes
  "new_put_strike": 24400,
  "new_call_strike": 25300,
  
  // If auto, specify constraints
  "premium_split": "equal" | "weighted",
  "prefer_round_strikes": true,
  "max_delta": 0.30
}

Response:
{
  "break_trade_id": "bt_123",
  "exit_order": { ... },
  "new_positions": [
    { "type": "PE", "strike": 24400, "premium": 160, "delta": 0.28 },
    { "type": "CE", "strike": 25300, "premium": 207, "delta": 0.18 }
  ],
  "recovery_premium": 367,
  "exit_cost": 371,
  "net_cost": 4,
  "status": "pending_confirmation" | "executed"
}
```

**Break Trade Wizard UI Flow:**

```
Step 1: Select Leg to Break
  - Show all legs with P&L
  - Highlight legs with high delta / big loss
  - User selects one leg

Step 2: Review Exit Cost
  - Show current price
  - Show loss amount
  - Show calculated recovery premium
  - User confirms

Step 3: Find New Strikes
  - Auto-suggest strikes based on premium
  - Show option chain for manual selection
  - Allow adjustment of strikes
  - Show Greeks of new positions
  - Show new position's P&L chart

Step 4: Preview & Confirm
  - Show side-by-side: Before vs After
  - Show new breakevens
  - Show net cost of adjustment
  - Confirm button

Step 5: Execute
  - Execute exit order
  - Execute new entry orders
  - Show confirmation
```

---

### Feature 5: Shift Leg

**Purpose:** Move a profitable leg closer to collect more premium, or move a losing leg further away

**Use Cases:**
- Profitable leg has very low delta (< 5) - shift closer to ATM
- Leg approaching ITM - shift further away
- Rebalance delta exposure

**Shift Logic:**

```
SHIFT LEG ALGORITHM:

Input:
  - leg_to_shift: The leg to move
  - target_strike: Where to move it (or criteria)

Step 1: Exit Current Leg
  - Place market/limit order to close

Step 2: Enter New Position
  - Same type (CE/PE)
  - Same action (BUY/SELL)
  - Same lots
  - New strike

Step 3: Update Position
  - Close old leg record
  - Create new leg record
  - Link as "rolled from" for tracking
```

**Shift Leg API:**

```
POST /api/v1/autopilot/strategies/{id}/legs/{leg_id}/shift

Request:
{
  "target_strike": 26200,
  // OR
  "target_delta": 0.15,
  // OR  
  "shift_direction": "closer" | "further",
  "shift_amount": 200, // points
  
  "execution_mode": "market" | "limit",
  "limit_offset": 1.0 // if limit
}

Response:
{
  "shift_id": "sh_123",
  "old_leg": { "strike": 26800, "exit_price": 14.5 },
  "new_leg": { "strike": 26200, "entry_price": 33.5 },
  "premium_change": +19.0,
  "delta_change": +0.05,
  "status": "executed"
}
```

---

### Feature 6: Roll Leg

**Purpose:** Move leg to different expiry (and optionally different strike)

**Roll Types:**

| Type | Description |
|------|-------------|
| Roll Expiry | Same strike, next expiry |
| Roll Strike | Same expiry, different strike |
| Roll Both | Different strike and expiry |
| Calendar Roll | Keep current, add next expiry |

**Roll Logic:**

```
ROLL LEG ALGORITHM:

Input:
  - leg_to_roll: Current leg
  - target_expiry: New expiry
  - target_strike: New strike (optional, defaults to same)

Step 1: Calculate Roll Cost/Credit
  current_price = get_ltp(current_leg)
  new_price = get_ltp(new_leg)
  roll_cost = new_price - current_price (for buys)
  roll_credit = current_price - new_price (for sells)

Step 2: Execute Roll
  - Exit current leg
  - Enter new leg

Step 3: Update Position
  - Mark old leg as "rolled"
  - Create new leg with "rolled_from" reference
```

**Roll Leg API:**

```
POST /api/v1/autopilot/strategies/{id}/legs/{leg_id}/roll

Request:
{
  "target_expiry": "2024-11-28",
  "target_strike": 25000, // optional
  "execution_mode": "market" | "limit"
}

Response:
{
  "roll_id": "rl_123",
  "old_leg": { "expiry": "2024-10-31", "strike": 25000 },
  "new_leg": { "expiry": "2024-11-28", "strike": 25000 },
  "roll_cost": -45.0, // negative means credit
  "status": "executed"
}
```

---

### Feature 7: Delta Monitoring & Alerts

**Purpose:** Track delta of each leg and trigger alerts/actions when thresholds crossed

**Delta Thresholds:**

| Level | Delta Range | Status | Action |
|-------|-------------|--------|--------|
| Safe | 0 - 0.20 | Green | None |
| Watch | 0.20 - 0.30 | Yellow | Monitor closely |
| Warning | 0.30 - 0.40 | Orange | Consider adjustment |
| Danger | 0.40+ | Red | Immediate attention |

**Delta Alert Configuration:**

```
DeltaAlertConfig {
  enabled: boolean
  watch_threshold: number (default 0.20)
  warning_threshold: number (default 0.30)
  danger_threshold: number (default 0.40)
  
  actions: {
    on_watch: "notify" | "none"
    on_warning: "notify" | "suggest_adjustment"
    on_danger: "notify" | "suggest_adjustment" | "auto_adjust"
  }
  
  cooldown_minutes: number (default 30)
}
```

**Delta Change Detection:**

```
Track:
  - Initial delta at entry
  - Current delta
  - Delta change (absolute)
  - Delta change (percentage)
  
Alert when:
  - Delta crosses threshold
  - Delta doubles from entry
  - Delta changes by > 0.10 in single day
```

**WebSocket Delta Updates:**

```json
{
  "type": "leg_delta_update",
  "strategy_id": 123,
  "leg_id": "leg_1",
  "data": {
    "previous_delta": 0.28,
    "current_delta": 0.35,
    "threshold_crossed": "warning",
    "suggestion": "Consider shifting leg or breaking trade"
  }
}
```

---

### Feature 8: Time-to-Expiry Aware Logic

**Purpose:** Adjust behavior based on days to expiry

**DTE Zones:**

| Zone | DTE Range | Behavior |
|------|-----------|----------|
| Early | > 15 days | Patient, allow more drawdown, adjustments effective |
| Middle | 8-15 days | Normal thresholds |
| Late | 4-7 days | Tighter thresholds, faster adjustments |
| Expiry Week | 0-3 days | Minimal adjustments, consider exit |

**DTE-Based Adjustment Rules:**

```
If DTE > 15:
  - Allow delta up to 0.40 before warning
  - Wait for price action before adjusting
  - Break trade effective
  
If DTE 8-15:
  - Standard thresholds (delta 0.30 warning)
  - Normal adjustment triggers
  
If DTE 4-7:
  - Tighter thresholds (delta 0.25 warning)
  - Faster adjustment execution
  - Prefer exit over complex adjustments
  
If DTE 0-3:
  - Warn user: "Adjustments less effective in last week"
  - Suggest exit over adjustment
  - Only allow simple adjustments (exit leg, not break)
```

**DTE Display:**

```
┌─────────────────────────────────────────┐
│ EXPIRY: Oct 31, 2024                    │
│ DTE: 24 days                            │
│ Zone: EARLY (adjustments effective)     │
└─────────────────────────────────────────┘
```

---

### Feature 9: Adjustment Suggestions Engine

**Purpose:** Automatically suggest appropriate adjustments based on position state

**Suggestion Triggers:**

| Condition | Suggestion |
|-----------|------------|
| Leg delta > 0.30, DTE > 15 | "Consider shifting {leg} or breaking trade" |
| Leg delta > 0.40, DTE > 7 | "Break trade recommended for {leg}" |
| Leg delta > 0.40, DTE < 7 | "Consider exiting {leg}" |
| Profitable leg delta < 0.05 | "Shift {leg} closer to collect more premium" |
| Premium < ₹10 on sold option | "Book profit on {leg}, shift closer" |
| Both legs profitable | "Position healthy, no action needed" |
| Spot near breakeven | "Monitor closely, prepare adjustment" |

**Suggestion Schema:**

```
AdjustmentSuggestion {
  id: string
  strategy_id: number
  leg_id: string (optional, if leg-specific)
  
  trigger_reason: string
  suggestion_type: "shift" | "break" | "roll" | "exit" | "add_hedge" | "no_action"
  
  description: string
  details: {
    current_state: { ... }
    suggested_action: { ... }
    expected_outcome: { ... }
  }
  
  urgency: "low" | "medium" | "high" | "critical"
  confidence: number (0-100)
  
  one_click_action: boolean
  action_params: { ... } // Pre-filled params for one-click
  
  created_at: datetime
  expires_at: datetime
  dismissed: boolean
  executed: boolean
}
```

**Suggestion API:**

```
GET /api/v1/autopilot/strategies/{id}/suggestions
  → Returns active suggestions for strategy

POST /api/v1/autopilot/strategies/{id}/suggestions/{suggestion_id}/execute
  → Execute suggested action

POST /api/v1/autopilot/strategies/{id}/suggestions/{suggestion_id}/dismiss
  → Dismiss suggestion
```

**Suggestion Card UI:**

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ SUGGESTION                                    [Dismiss] │
├─────────────────────────────────────────────────────────────┤
│ Leg 1 (25000 PE) delta has exceeded 0.30                   │
│                                                             │
│ Current: Delta 0.35, P&L -₹2,500                           │
│ Suggested: Break trade - split into 24400 PE + 25300 CE    │
│ Expected: Position recentered, new delta ~0.15 each side   │
│                                                             │
│ [Preview Adjustment]              [Execute Now]             │
└─────────────────────────────────────────────────────────────┘
```

---

### Feature 10: What-If Simulator

**Purpose:** Preview how an adjustment would affect the position before executing

**Simulation Inputs:**

```
WhatIfRequest {
  strategy_id: number
  adjustment_type: "break" | "shift" | "roll" | "exit" | "add_leg"
  adjustment_params: { ... }
  
  // Optional: Test against scenarios
  scenarios: [
    { "spot_change": -500 },
    { "spot_change": +500 },
    { "iv_change": +5 },
    { "days_forward": 7 }
  ]
}
```

**Simulation Outputs:**

```
WhatIfResponse {
  current_position: {
    net_delta: 0.15,
    net_theta: -250,
    max_profit: 5000,
    max_loss: -15000,
    breakeven_lower: 24500,
    breakeven_upper: 26300,
    current_pnl: -2500
  },
  
  after_adjustment: {
    net_delta: 0.02,
    net_theta: -180,
    max_profit: 3500,
    max_loss: -12000,
    breakeven_lower: 24100,
    breakeven_upper: 25600,
    current_pnl: -2500,
    adjustment_cost: 150
  },
  
  comparison: {
    delta_change: -0.13,
    theta_change: +70,
    max_loss_change: +3000,
    breakeven_change: "Lower moved from 24500 to 24100"
  },
  
  scenario_results: [
    { "scenario": "spot -500", "current_pnl": -8000, "adjusted_pnl": -4000 },
    { "scenario": "spot +500", "current_pnl": +1500, "adjusted_pnl": +1000 }
  ]
}
```

**What-If UI:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ WHAT-IF SIMULATOR                                                       │
├────────────────────────────────┬────────────────────────────────────────┤
│       CURRENT POSITION         │         AFTER ADJUSTMENT              │
├────────────────────────────────┼────────────────────────────────────────┤
│ Net Delta: 0.15                │ Net Delta: 0.02 (▼ 0.13)              │
│ Net Theta: -₹250/day           │ Net Theta: -₹180/day (▲ ₹70)          │
│ Max Profit: ₹5,000             │ Max Profit: ₹3,500 (▼ ₹1,500)         │
│ Max Loss: -₹15,000             │ Max Loss: -₹12,000 (▲ ₹3,000)         │
│ Lower BE: 24500                │ Lower BE: 24100 (▼ 400 pts)           │
│ Upper BE: 26300                │ Upper BE: 25600 (▼ 700 pts)           │
├────────────────────────────────┴────────────────────────────────────────┤
│                          P&L DIAGRAM                                    │
│                                                                         │
│     ₹5000 ─┼─────────────/‾‾‾‾‾\─────────────────                       │
│            │           /   ↑    \                                       │
│         0 ─┼──────────/────┼─────\──────────────                        │
│            │        /      │      \           Before (solid)            │
│   -₹15000 ─┼───────/       │       \          After (dashed)            │
│            └───────┴───────┴───────┴─────────                           │
│               24000    25000    26000                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                      SCENARIO ANALYSIS                                  │
├──────────────────┬──────────────────┬───────────────────────────────────┤
│ Scenario         │ Current P&L      │ After Adjustment P&L              │
├──────────────────┼──────────────────┼───────────────────────────────────┤
│ Spot -500 pts    │ -₹8,000          │ -₹4,000 (▲ ₹4,000 better)         │
│ Spot +500 pts    │ +₹1,500          │ +₹1,000 (▼ ₹500 worse)            │
│ IV +5%           │ -₹3,500          │ -₹3,000 (▲ ₹500 better)           │
│ 7 days later     │ +₹1,750          │ +₹1,260 (▼ ₹490 worse)            │
├──────────────────┴──────────────────┴───────────────────────────────────┤
│ Adjustment Cost: ₹150                                                   │
│                                                                         │
│                    [Cancel]              [Execute Adjustment]           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Feature 11: Position Visualization

**Purpose:** Visual P&L diagram showing current position, breakevens, and spot price

**P&L Chart Requirements:**

| Element | Description |
|---------|-------------|
| X-axis | Price range (spot ± 5%) |
| Y-axis | P&L in ₹ |
| Current position line | Solid line showing P&L at each price |
| After adjustment line | Dashed line (when previewing) |
| Spot price marker | Vertical line at current spot |
| Breakeven markers | Vertical lines at breakeven points |
| Entry price marker | Where position was entered |
| Max profit zone | Highlighted area |
| Max loss zone | Highlighted area |

**Breakeven Display:**

```
Lower Breakeven: 24500 (spot - 2.0%)
Upper Breakeven: 26300 (spot + 5.2%)
Current Spot: 25000
Distance to Lower BE: 500 points
Distance to Upper BE: 1300 points
```

**Chart Interactions:**

- Hover: Show P&L at that price point
- Click breakeven: Show details
- Toggle: Show/hide adjustment preview
- Zoom: Adjust price range

---

### Feature 12: Option Chain UI Component

**Purpose:** Interactive option chain for manual strike selection

**Option Chain Display:**

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ NIFTY OPTION CHAIN                    Expiry: Oct 31, 2024         Spot: 25000      │
├─────────────────────────────────────────┬───────────────────────────────────────────┤
│              CALLS                      │                 PUTS                      │
├────────┬───────┬───────┬───────┬────────┼────────┬───────┬───────┬───────┬─────────┤
│ OI     │ Delta │ LTP   │ IV    │ Strike │ Strike │ IV    │ LTP   │ Delta │ OI      │
├────────┼───────┼───────┼───────┼────────┼────────┼───────┼───────┼───────┼─────────┤
│ 125K   │ 0.85  │ 890   │ 15.2  │ 24200  │ 24200  │ 18.5  │ 45    │ 0.08  │ 89K     │
│ 156K   │ 0.78  │ 720   │ 14.8  │ 24400  │ 24400  │ 17.8  │ 72    │ 0.12  │ 112K    │
│ 189K   │ 0.68  │ 550   │ 14.2  │ 24600  │ 24600  │ 17.2  │ 105   │ 0.18  │ 145K    │
│ 220K   │ 0.55  │ 380   │ 13.8  │ 24800  │ 24800  │ 16.5  │ 160   │ 0.28  │ 178K    │
│ 245K   │ 0.42  │ 245   │ 13.5  │ 25000  │ 25000  │ 16.2  │ 240   │ 0.42  │ 198K ◄─┤
│ 198K   │ 0.30  │ 145   │ 13.2  │ 25200  │ 25200  │ 15.8  │ 340   │ 0.55  │ 165K    │
│ 167K   │ 0.20  │ 78    │ 13.0  │ 25400  │ 25400  │ 15.5  │ 470   │ 0.68  │ 134K    │
│ 134K   │ 0.12  │ 42    │ 12.8  │ 25600  │ 25600  │ 15.2  │ 620   │ 0.78  │ 98K     │
│ 98K    │ 0.06  │ 18    │ 12.5  │ 25800  │ 25800  │ 14.8  │ 790   │ 0.88  │ 67K     │
└────────┴───────┴───────┴───────┴────────┴────────┴───────┴───────┴───────┴─────────┘
│ [Filter: Delta 0.10-0.20]  [Filter: Premium 100-200]  [Show All]                    │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**Option Chain Features:**

| Feature | Description |
|---------|-------------|
| Strike highlighting | Highlight ATM, current position strikes |
| Delta filter | Show only strikes within delta range |
| Premium filter | Show only strikes within premium range |
| Click to select | Click strike to use in adjustment |
| Quick compare | Select multiple to compare |
| OI analysis | Show OI change, max pain |
| IV skew | Show IV across strikes |

---

## Database Schema Changes

### New Table: autopilot_position_legs

```sql
CREATE TABLE autopilot_position_legs (
    id BIGSERIAL PRIMARY KEY,
    strategy_id BIGINT NOT NULL REFERENCES autopilot_strategies(id) ON DELETE CASCADE,
    leg_id VARCHAR(50) NOT NULL,
    
    -- Configuration
    contract_type VARCHAR(2) NOT NULL, -- CE, PE
    action VARCHAR(4) NOT NULL, -- BUY, SELL
    strike DECIMAL(10,2) NOT NULL,
    expiry DATE NOT NULL,
    lots INTEGER NOT NULL,
    
    -- Instrument
    tradingsymbol VARCHAR(50),
    instrument_token BIGINT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, open, closed, rolled
    
    -- Entry
    entry_price DECIMAL(10,2),
    entry_time TIMESTAMP,
    entry_order_ids JSONB DEFAULT '[]',
    
    -- Exit
    exit_price DECIMAL(10,2),
    exit_time TIMESTAMP,
    exit_order_ids JSONB DEFAULT '[]',
    exit_reason VARCHAR(50),
    
    -- Greeks (updated real-time)
    delta DECIMAL(6,4),
    gamma DECIMAL(8,6),
    theta DECIMAL(10,2),
    vega DECIMAL(8,4),
    iv DECIMAL(6,2),
    
    -- P&L
    unrealized_pnl DECIMAL(12,2) DEFAULT 0,
    realized_pnl DECIMAL(12,2) DEFAULT 0,
    
    -- Roll tracking
    rolled_from_leg_id BIGINT REFERENCES autopilot_position_legs(id),
    rolled_to_leg_id BIGINT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_position_legs_strategy ON autopilot_position_legs(strategy_id);
CREATE INDEX idx_position_legs_status ON autopilot_position_legs(status);
CREATE UNIQUE INDEX idx_position_legs_strategy_leg ON autopilot_position_legs(strategy_id, leg_id) WHERE status = 'open';
```

### New Table: autopilot_adjustment_suggestions

```sql
CREATE TABLE autopilot_adjustment_suggestions (
    id BIGSERIAL PRIMARY KEY,
    strategy_id BIGINT NOT NULL REFERENCES autopilot_strategies(id) ON DELETE CASCADE,
    leg_id VARCHAR(50),
    
    trigger_reason TEXT NOT NULL,
    suggestion_type VARCHAR(30) NOT NULL, -- shift, break, roll, exit, add_hedge, no_action
    description TEXT NOT NULL,
    details JSONB,
    
    urgency VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    confidence INTEGER DEFAULT 50, -- 0-100
    
    one_click_action BOOLEAN DEFAULT FALSE,
    action_params JSONB,
    
    status VARCHAR(20) DEFAULT 'active', -- active, dismissed, executed, expired
    
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    responded_at TIMESTAMP
);

CREATE INDEX idx_suggestions_strategy ON autopilot_adjustment_suggestions(strategy_id);
CREATE INDEX idx_suggestions_status ON autopilot_adjustment_suggestions(status);
```

### New Table: autopilot_option_chain_cache

```sql
CREATE TABLE autopilot_option_chain_cache (
    id BIGSERIAL PRIMARY KEY,
    underlying VARCHAR(20) NOT NULL,
    expiry DATE NOT NULL,
    strike DECIMAL(10,2) NOT NULL,
    option_type VARCHAR(2) NOT NULL, -- CE, PE
    
    tradingsymbol VARCHAR(50) NOT NULL,
    instrument_token BIGINT NOT NULL,
    
    ltp DECIMAL(10,2),
    bid DECIMAL(10,2),
    ask DECIMAL(10,2),
    volume BIGINT,
    oi BIGINT,
    oi_change BIGINT,
    
    iv DECIMAL(6,2),
    delta DECIMAL(6,4),
    gamma DECIMAL(8,6),
    theta DECIMAL(10,2),
    vega DECIMAL(8,4),
    
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(underlying, expiry, strike, option_type)
);

CREATE INDEX idx_option_chain_underlying ON autopilot_option_chain_cache(underlying, expiry);
CREATE INDEX idx_option_chain_delta ON autopilot_option_chain_cache(underlying, expiry, option_type, delta);
```

### Update autopilot_strategies

Add new columns:

```sql
ALTER TABLE autopilot_strategies 
ADD COLUMN position_legs_snapshot JSONB,
ADD COLUMN net_delta DECIMAL(6,4),
ADD COLUMN net_theta DECIMAL(10,2),
ADD COLUMN net_gamma DECIMAL(8,6),
ADD COLUMN net_vega DECIMAL(8,4),
ADD COLUMN breakeven_lower DECIMAL(10,2),
ADD COLUMN breakeven_upper DECIMAL(10,2),
ADD COLUMN dte INTEGER;
```

### Update autopilot_user_settings

Add new columns:

```sql
ALTER TABLE autopilot_user_settings
ADD COLUMN delta_watch_threshold DECIMAL(4,2) DEFAULT 0.20,
ADD COLUMN delta_warning_threshold DECIMAL(4,2) DEFAULT 0.30,
ADD COLUMN delta_danger_threshold DECIMAL(4,2) DEFAULT 0.40,
ADD COLUMN delta_alert_enabled BOOLEAN DEFAULT TRUE,
ADD COLUMN suggestions_enabled BOOLEAN DEFAULT TRUE,
ADD COLUMN prefer_round_strikes BOOLEAN DEFAULT TRUE;
```

---

## API Endpoints Summary

### Option Chain APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /option-chain/{underlying}/{expiry} | Full option chain |
| GET | /option-chain/find-by-delta | Find strike by delta |
| GET | /option-chain/find-by-premium | Find strike by premium |
| GET | /option-chain/expiries/{underlying} | Available expiries |

### Position Leg APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /strategies/{id}/legs | Get all legs |
| GET | /strategies/{id}/legs/{leg_id} | Get single leg |
| POST | /strategies/{id}/legs/{leg_id}/exit | Exit single leg |
| POST | /strategies/{id}/legs/{leg_id}/shift | Shift leg to new strike |
| POST | /strategies/{id}/legs/{leg_id}/roll | Roll leg to new expiry |
| POST | /strategies/{id}/legs/{leg_id}/break | Break/split trade |
| POST | /strategies/{id}/legs/add | Add new leg |

### Suggestion APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /strategies/{id}/suggestions | Get active suggestions |
| POST | /strategies/{id}/suggestions/{sid}/execute | Execute suggestion |
| POST | /strategies/{id}/suggestions/{sid}/dismiss | Dismiss suggestion |

### Simulation APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /strategies/{id}/simulate | What-if simulation |
| POST | /strategies/{id}/simulate/break | Simulate break trade |
| POST | /strategies/{id}/simulate/shift | Simulate shift |

---

## Frontend Components

### New Components

| Component | Location | Description |
|-----------|----------|-------------|
| OptionChainView.vue | views/autopilot/ | Full option chain page |
| OptionChainTable.vue | components/autopilot/optionchain/ | Option chain table |
| OptionChainFilters.vue | components/autopilot/optionchain/ | Delta/premium filters |
| StrikeFinder.vue | components/autopilot/optionchain/ | Quick strike lookup |
| PositionLegsPanel.vue | components/autopilot/position/ | All legs display |
| LegCard.vue | components/autopilot/position/ | Single leg card |
| LegActions.vue | components/autopilot/position/ | Leg action buttons |
| LegGreeksDisplay.vue | components/autopilot/position/ | Leg Greeks |
| BreakTradeWizard.vue | components/autopilot/adjustments/ | Break trade flow |
| ShiftLegModal.vue | components/autopilot/adjustments/ | Shift leg modal |
| RollLegModal.vue | components/autopilot/adjustments/ | Roll leg modal |
| SuggestionCard.vue | components/autopilot/suggestions/ | Suggestion display |
| SuggestionsList.vue | components/autopilot/suggestions/ | All suggestions |
| WhatIfSimulator.vue | components/autopilot/simulator/ | What-if tool |
| WhatIfComparison.vue | components/autopilot/simulator/ | Before/after compare |
| PayoffChart.vue | components/autopilot/charts/ | P&L diagram |
| BreakevenDisplay.vue | components/autopilot/charts/ | Breakeven info |
| DeltaGauge.vue | components/autopilot/indicators/ | Delta visual gauge |
| DTEIndicator.vue | components/autopilot/indicators/ | Days to expiry |

### Updated Components

| Component | Changes |
|-----------|---------|
| StrategyDetailView.vue | Add legs panel, suggestions, payoff chart |
| StrategyBuilderView.vue | Add delta/premium strike selection |
| DashboardView.vue | Add suggestions summary |

---

## Services

### New Backend Services

| Service | File | Description |
|---------|------|-------------|
| OptionChainService | option_chain.py | Fetch and cache option chain |
| StrikeFinderService | strike_finder.py | Find strikes by criteria |
| PositionLegService | position_leg.py | Manage position legs |
| BreakTradeService | break_trade.py | Execute break trades |
| ShiftLegService | shift_leg.py | Execute leg shifts |
| RollLegService | roll_leg.py | Execute leg rolls |
| SuggestionEngine | suggestion_engine.py | Generate suggestions |
| WhatIfSimulator | whatif_simulator.py | Run simulations |
| PayoffCalculator | payoff_calculator.py | Calculate P&L diagram |

### Updated Backend Services

| Service | Changes |
|---------|---------|
| StrategyMonitor | Add leg-level monitoring, delta tracking |
| ConditionEngine | Add delta conditions, premium conditions |
| OrderExecutor | Add per-leg order tracking |

---

## WebSocket Messages

### New Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| leg_update | Server→Client | Leg state changed |
| leg_greeks_update | Server→Client | Leg Greeks updated |
| leg_delta_alert | Server→Client | Delta threshold crossed |
| suggestion_new | Server→Client | New suggestion available |
| suggestion_expired | Server→Client | Suggestion expired |
| option_chain_update | Server→Client | Option chain data refresh |
| break_trade_status | Server→Client | Break trade execution status |
| shift_leg_status | Server→Client | Shift leg execution status |

---

## Implementation Phases

### Phase 5A: Foundation (Week 1-2)

1. Database migration
2. Option chain service
3. Strike finder service
4. Position leg model and service
5. Basic API endpoints

### Phase 5B: Core Adjustments (Week 2-3)

6. Exit single leg
7. Shift leg functionality
8. Roll leg functionality
9. Break trade logic
10. Per-leg P&L tracking

### Phase 5C: Intelligence (Week 3-4)

11. Delta monitoring
12. Suggestion engine
13. What-if simulator
14. Payoff calculator
15. DTE-aware logic

### Phase 5D: Frontend (Week 4-5)

16. Option chain UI
17. Position legs panel
18. Leg cards with actions
19. Break trade wizard
20. Shift/Roll modals
21. Suggestion cards
22. What-if simulator UI
23. Payoff chart
24. Delta gauge

### Phase 5E: Integration & Polish (Week 5-6)

25. WebSocket updates for legs
26. Strategy monitor integration
27. Strategy detail page update
28. Builder strike selection update
29. Testing
30. Documentation

---

## Success Criteria

Phase 5 is complete when:

1. ✅ Can find strikes by delta (e.g., "15 delta PUT")
2. ✅ Can find strikes by premium (e.g., "₹180 premium")
3. ✅ Can view and manage individual legs
4. ✅ Can exit a single leg without affecting others
5. ✅ Can shift a leg to a new strike
6. ✅ Can roll a leg to a new expiry
7. ✅ Can execute break/split trade
8. ✅ Delta alerts trigger at configured thresholds
9. ✅ System suggests appropriate adjustments
10. ✅ What-if simulator shows before/after comparison
11. ✅ Payoff chart displays correctly
12. ✅ All leg actions work in semi-auto mode
13. ✅ DTE displayed and affects behavior
14. ✅ Option chain UI allows strike selection
15. ✅ All adjustments logged properly

---

## Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| Option chain API rate limits | Cache aggressively, batch requests |
| Greeks calculation accuracy | Use standard Black-Scholes, document limitations |
| Break trade execution failure | Atomic transactions, rollback on partial failure |
| UI complexity | Progressive disclosure, wizard flows |
| Performance with real-time updates | Throttle updates, use efficient diffing |

---

## Appendix: Reference Formulas

### Delta-based Strike Finding

```python
def find_strike_by_delta(chain, target_delta, option_type):
    strikes = chain[option_type]
    closest = min(strikes, key=lambda s: abs(s.delta - target_delta))
    
    # Prefer round strike if close
    if closest.delta == target_delta:
        return closest
    
    nearby = [s for s in strikes if abs(s.delta - target_delta) < 0.03]
    round_strikes = [s for s in nearby if s.strike % 100 == 0]
    
    return round_strikes[0] if round_strikes else closest
```

### Break Trade Premium Calculation

```python
def calculate_recovery_premiums(exit_cost, split_ratio=0.5):
    put_target = exit_cost * split_ratio
    call_target = exit_cost * (1 - split_ratio)
    return put_target, call_target
```

### Payoff at Expiry

```python
def calculate_payoff(legs, spot_price):
    total = 0
    for leg in legs:
        if leg.option_type == "CE":
            intrinsic = max(0, spot_price - leg.strike)
        else:
            intrinsic = max(0, leg.strike - spot_price)
        
        if leg.action == "BUY":
            pnl = (intrinsic - leg.entry_price) * leg.quantity
        else:
            pnl = (leg.entry_price - intrinsic) * leg.quantity
        
        total += pnl
    return total
```

---

## Document End

This document serves as the comprehensive specification for Phase 5 implementation. Claude Code should use this as the primary reference for building all features.

**Next Step:** Create implementation prompts based on this plan.
