---
name: autopilot-assistant
description: Comprehensive AutoPilot strategy configuration guidance. Use when working with AutoPilot features, strategies, conditions, adjustments, or risk management.
---

# AutoPilot Assistant

Complete guidance for AlgoChanakya's AutoPilot auto-execution system.

## When to Use

- User works with AutoPilot features
- User creates or modifies strategies
- User writes entry conditions or adjustment rules
- User needs database schema reference
- User asks about AutoPilot API endpoints
- User implements AutoPilot-related features

## AutoPilot Overview

AutoPilot is an automated strategy execution system with:
- Conditional entry based on market conditions
- Real-time monitoring via WebSocket
- Automatic adjustments (planned Phase 5+)
- Risk management (max loss, trailing stop, time stop)
- Live and Paper trading modes
- Order execution via Kite Connect

## Key Concepts

### 1. Strategy Lifecycle

```
Created → Waiting → Active → (Paused) → Exited
  ↓         ↓         ↓         ↓         ↓
Draft   Monitoring Entry   Running  Temporarily  Complete
        conditions  executed         stopped
```

**Status Values:**
- `draft` - Not yet activated
- `waiting` - Monitoring entry conditions
- `active` - Positions open, monitoring risks
- `paused` - Temporarily stopped by user
- `exited` - All positions closed, complete

### 2. Strategy Components

1. **Strategy Details** - Underlying, expiry, lots, position type
2. **Legs Configuration** - Option legs (CE/PE, Buy/Sell, Strike selection)
3. **Entry Conditions** - When to enter (TIME, SPOT, VIX, PREMIUM variables)
4. **Adjustment Rules** - When and how to adjust (Phase 5+)
5. **Order Settings** - Order type, execution style, slippage protection
6. **Risk Settings** - Max loss, trailing stop, time stop
7. **Schedule** - Active days and time windows

### 3. Trading Modes

- **Live** - Real orders via Kite Connect
- **Paper** - Simulated orders for testing

---

## Database Schema Quick Reference

14 core tables (see [database-schema.md](./references/database-schema.md) for details):

| Table | Purpose |
|-------|---------|
| `autopilot_user_settings` | Global user risk limits and preferences |
| `autopilot_strategies` | Strategy configurations (legs, conditions, settings) |
| `autopilot_orders` | Order execution history with slippage tracking |
| `autopilot_order_batches` | Grouped orders (entry/adjustment/exit) |
| `autopilot_logs` | Activity logs and events |
| `autopilot_condition_eval` | Condition evaluation snapshots |
| `autopilot_daily_summary` | Daily P&L aggregates |
| `autopilot_templates` | Pre-built strategy templates |
| `autopilot_adjustment_logs` | Adjustment rule execution history (Phase 5+) |
| `autopilot_pending_confirmations` | Semi-auto confirmation requests (Phase 5+) |
| `autopilot_position_legs` | Individual leg tracking with Greeks (Phase 5+) |
| `autopilot_adjustment_suggestions` | AI-generated suggestions (Phase 5+) |
| `autopilot_trade_journal` | Trade logging for analysis (Phase 5+) |
| `autopilot_backtests` | Backtest results (Phase 5+) |

---

## Entry Conditions

### Condition Variables

See [condition-variables.md](./references/condition-variables.md) for complete list.

**Core Variables:**
- `TIME.CURRENT` - Current time (HH:MM)
- `TIME.MINUTES_SINCE_OPEN` - Minutes since 9:15 AM
- `SPOT.{UNDERLYING}` - Spot price (e.g., `SPOT.NIFTY`)
- `SPOT.{UNDERLYING}.CHANGE_PCT` - Spot change %
- `VIX.VALUE` - India VIX
- `WEEKDAY` - MON, TUE, WED, THU, FRI
- `PREMIUM.{LEG_ID}` - Premium for a specific leg

**Phase 5 Variables:**
- `STRATEGY.DELTA|GAMMA|THETA|VEGA` - Net Greeks
- `SPOT.DISTANCE_TO.BREAKEVEN` - Distance to breakeven %
- `IV.RANK|IV.PERCENTILE` - IV metrics
- `OI.PCR|OI.MAX_PAIN` - OI analysis

### Condition Operators

- `equals`, `not_equals`
- `greater_than`, `less_than`, `greater_equal`, `less_equal`
- `between`, `not_between`
- `crosses_above`, `crosses_below`

### Condition Structure

```json
{
  "logic": "AND|OR",
  "conditions": [
    {
      "id": "cond_1",
      "enabled": true,
      "variable": "TIME.CURRENT",
      "operator": "greater_equal",
      "value": "09:20"
    },
    {
      "id": "cond_2",
      "enabled": true,
      "variable": "SPOT.NIFTY",
      "operator": "between",
      "value": [24000, 25000]
    }
  ]
}
```

---

## Legs Configuration

### Strike Selection Modes

1. **ATM Offset** - Offset from ATM strike
   ```json
   {"mode": "atm_offset", "offset": 0}  // ATM
   {"mode": "atm_offset", "offset": 2}  // 2 strikes OTM
   ```

2. **Premium Based** - Target premium value
   ```json
   {"mode": "premium_based", "target_premium": 100.0}
   ```

3. **Delta Based** - Target delta value (Phase 5)
   ```json
   {"mode": "delta_based", "target_delta": 0.30}
   ```

4. **Fixed** - Specific strike price
   ```json
   {"mode": "fixed", "strike": 24500}
   ```

### Leg Example

```json
{
  "id": "leg_1",
  "contract_type": "CE",
  "transaction_type": "SELL",
  "strike_selection": {
    "mode": "atm_offset",
    "offset": 2
  },
  "quantity_multiplier": 1
}
```

---

## Adjustment Rules (Phase 5+)

### Trigger Types

- `pnl_based` - Trigger on P&L thresholds
- `delta_based` - Trigger on net delta
- `time_based` - Trigger at specific time
- `premium_based` - Trigger on premium capture
- `vix_based` - Trigger on VIX changes

### Action Types

- `add_hedge` - Add protective legs
- `close_leg` - Close specific leg
- `roll_strike` - Roll strike price
- `roll_expiry` - Roll to next expiry
- `exit_all` - Close all positions
- `scale_down` - Reduce position size

### Execution Modes

- `auto` - Execute automatically
- `semi_auto` - Request confirmation
- `manual` - Alert only, user executes

---

## API Endpoints

See [api-endpoints.md](./references/api-endpoints.md) for complete reference.

**Base URL:** `/api/v1/autopilot/`

**Strategy Endpoints:**
- `GET/POST /strategies` - List/Create
- `GET/PUT/DELETE /strategies/{id}` - CRUD
- `POST /strategies/{id}/activate` - Start monitoring
- `POST /strategies/{id}/pause` - Pause strategy
- `POST /strategies/{id}/resume` - Resume paused strategy
- `POST /strategies/{id}/exit` - Exit all positions
- `GET /strategies/{id}/conditions` - Get condition states

**Dashboard Endpoints:**
- `GET /dashboard/summary` - Overview
- `GET /dashboard/activity` - Activity feed

**Settings Endpoints:**
- `GET/PUT /settings` - User settings

**Kill Switch:**
- `POST /kill-switch/trigger` - Emergency stop all

---

## Common Patterns

### Pattern 1: Simple Entry Condition

Enter at 9:20 AM if NIFTY above 24,000:

```json
{
  "logic": "AND",
  "conditions": [
    {
      "id": "cond_1",
      "enabled": true,
      "variable": "TIME.CURRENT",
      "operator": "greater_equal",
      "value": "09:20"
    },
    {
      "id": "cond_2",
      "enabled": true,
      "variable": "SPOT.NIFTY",
      "operator": "greater_than",
      "value": 24000
    }
  ]
}
```

### Pattern 2: Iron Condor Strategy

```json
{
  "name": "Auto Iron Condor",
  "underlying": "NIFTY",
  "expiry_type": "current_week",
  "lots": 2,
  "legs_config": [
    {
      "id": "leg_1",
      "contract_type": "CE",
      "transaction_type": "SELL",
      "strike_selection": {"mode": "atm_offset", "offset": 2},
      "quantity_multiplier": 1
    },
    {
      "id": "leg_2",
      "contract_type": "CE",
      "transaction_type": "BUY",
      "strike_selection": {"mode": "atm_offset", "offset": 4},
      "quantity_multiplier": 1
    },
    {
      "id": "leg_3",
      "contract_type": "PE",
      "transaction_type": "SELL",
      "strike_selection": {"mode": "atm_offset", "offset": -2},
      "quantity_multiplier": 1
    },
    {
      "id": "leg_4",
      "contract_type": "PE",
      "transaction_type": "BUY",
      "strike_selection": {"mode": "atm_offset", "offset": -4},
      "quantity_multiplier": 1
    }
  ]
}
```

### Pattern 3: Risk Settings

```json
{
  "max_loss": 5000.00,
  "max_loss_pct": 50.0,
  "trailing_stop": {
    "enabled": true,
    "trigger_profit": 2000.00,
    "trail_amount": 1000.00
  },
  "time_stop": "15:15"
}
```

---

## References

- [Database Schema](./references/database-schema.md) - All 14 tables with JSONB structures
- [Condition Variables](./references/condition-variables.md) - Complete list of variables and operators
- [API Endpoints](./references/api-endpoints.md) - AutoPilot API reference
- [Adjustment Rules](./references/adjustment-rules.md) - Adjustment patterns (Phase 5+)

---

## Best Practices

1. **Entry Conditions**
   - Keep conditions simple and testable
   - Use AND logic for multiple conditions
   - Test with paper trading first

2. **Legs Configuration**
   - Use ATM offset for flexibility
   - Validate strike selection makes sense
   - Test with single lot first

3. **Risk Management**
   - Always set max_loss
   - Use time_stop to exit before market close
   - Enable trailing_stop for profitable strategies

4. **Order Execution**
   - Use `sequential` for legs with dependencies
   - Use `simultaneous` for independent legs
   - Enable slippage protection (max 2-3%)

5. **Testing**
   - Start with paper trading mode
   - Monitor first few executions manually
   - Verify condition evaluation logic
   - Test during different market conditions
