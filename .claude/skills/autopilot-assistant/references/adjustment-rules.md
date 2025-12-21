# AutoPilot Adjustment Rules Reference

Comprehensive guide to adjustment rules for automated position management.

**Note:** Adjustment rules are **Phase 5+ features**. Basic AutoPilot (Phase 4) supports entry conditions and risk management only.

---

## Overview

Adjustment rules allow AutoPilot to automatically modify positions when specific conditions are met:
- Add protective hedges
- Roll strikes or expiries
- Exit partial or full positions
- Scale position size up/down
- Send alerts

---

## Adjustment Rule Structure

```json
{
  "id": "adj_1",
  "name": "Add hedge at 50% profit",
  "enabled": true,
  "priority": 1,
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "id": "trigger_1",
        "enabled": true,
        "variable": "PREMIUM.CAPTURED_PCT",
        "operator": "greater_equal",
        "value": 50.0
      }
    ]
  },
  "action": {
    "type": "add_hedge",
    "config": {
      "hedge_type": "both",
      "pe_strike": {"mode": "atm_offset", "offset": -1},
      "ce_strike": {"mode": "atm_offset", "offset": 1},
      "quantity_mode": "same_as_position",
      "max_cost": 500.00
    }
  },
  "execution_mode": "auto",
  "timeout_seconds": 60,
  "timeout_action": "skip",
  "max_executions": 1,
  "cooldown_minutes": 30
}
```

---

## Action Types

### 1. EXIT_ALL

Exit all positions and complete the strategy.

**When to use:**
- Profit target reached
- Max loss hit
- Specific time reached
- Adverse market conditions

**Config:**
```json
{
  "type": "exit_all",
  "config": {
    "order_type": "MARKET",
    "legs_to_exit": null  // null = all legs
  }
}
```

**Example:**
```json
{
  "id": "adj_exit",
  "name": "Exit at 70% profit",
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "variable": "PREMIUM.CAPTURED_PCT",
        "operator": "greater_equal",
        "value": 70.0
      }
    ]
  },
  "action": {
    "type": "exit_all",
    "config": {
      "order_type": "MARKET"
    }
  },
  "execution_mode": "auto"
}
```

---

### 2. EXIT_PARTIAL

Exit specific legs while keeping others open.

**When to use:**
- Lock profit from sold legs
- Remove directional bias
- Close losing legs

**Config:**
```json
{
  "type": "exit_partial",
  "config": {
    "order_type": "MARKET",
    "legs_to_exit": ["leg_1", "leg_3"]  // Specific leg IDs
  }
}
```

**Example:**
```json
{
  "id": "adj_partial",
  "name": "Exit sold legs at 60% profit",
  "trigger": {
    "logic": "AND",
    "conditions": [
      {
        "variable": "PREMIUM.CAPTURED_PCT",
        "operator": "greater_equal",
        "value": 60.0
      }
    ]
  },
  "action": {
    "type": "exit_partial",
    "config": {
      "order_type": "MARKET",
      "legs_to_exit": ["leg_1", "leg_3"]  // SELL legs
    }
  },
  "execution_mode": "auto"
}
```

---

### 3. ROLL

Roll strikes to next expiry or different strikes.

**When to use:**
- Roll to next expiry before current expiry
- Adjust strikes when market moves
- Maintain theta decay advantage

**Config:**
```json
{
  "type": "roll",
  "config": {
    "roll_to": "next_week",  // "next_week" | "monthly" | "custom"
    "strike_selection": "same_moneyness",  // "same" | "atm" | "same_moneyness"
    "roll_legs": "all",  // "all" | "sold_only" | "bought_only"
    "execution_style": "sequential"
  }
}
```

**Roll Strategies:**
- `same` - Same strike price in new expiry
- `atm` - ATM strikes in new expiry
- `same_moneyness` - Maintain same OTM/ITM distance

**Example:**
```json
{
  "id": "adj_roll",
  "name": "Roll to next week at 3 DTE",
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "variable": "STRATEGY.DTE",
        "operator": "less_equal",
        "value": 3
      }
    ]
  },
  "action": {
    "type": "roll",
    "config": {
      "roll_to": "next_week",
      "strike_selection": "same_moneyness",
      "roll_legs": "all",
      "execution_style": "sequential"
    }
  },
  "execution_mode": "semi_auto",  // Ask for confirmation
  "timeout_seconds": 300
}
```

---

### 4. SHIFT

Shift strikes away from or toward spot price.

**When to use:**
- Spot approaching sold strikes
- Reposition strikes after market move
- Manage delta exposure

**Config:**
```json
{
  "type": "shift",
  "config": {
    "direction": "away_from_spot",  // "away_from_spot" | "toward_spot" | "custom"
    "shift_amount": 100,  // Points to shift
    "shift_side": "breached"  // "ce_only" | "pe_only" | "both" | "breached"
  }
}
```

**Example:**
```json
{
  "id": "adj_shift",
  "name": "Shift breached strike away",
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "variable": "SPOT.DISTANCE_TO.leg_1",
        "operator": "less_than",
        "value": 0.5  // Spot within 0.5% of strike
      }
    ]
  },
  "action": {
    "type": "shift",
    "config": {
      "direction": "away_from_spot",
      "shift_amount": 200,
      "shift_side": "breached"
    }
  },
  "execution_mode": "auto"
}
```

---

### 5. ADD_HEDGE

Add protective legs to reduce risk.

**When to use:**
- Lock in profits
- Protect against adverse moves
- Reduce delta exposure

**Config:**
```json
{
  "type": "add_hedge",
  "config": {
    "hedge_type": "both",  // "pe_only" | "ce_only" | "both"
    "pe_strike": {
      "mode": "atm_offset",
      "offset": -1
    },
    "ce_strike": {
      "mode": "atm_offset",
      "offset": 1
    },
    "quantity_mode": "same_as_position",  // "same_as_position" | "custom"
    "max_cost": 500.00  // Max cost to pay for hedge
  }
}
```

**Example:**
```json
{
  "id": "adj_hedge",
  "name": "Add hedge at 50% profit",
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "variable": "PREMIUM.CAPTURED_PCT",
        "operator": "greater_equal",
        "value": 50.0
      }
    ]
  },
  "action": {
    "type": "add_hedge",
    "config": {
      "hedge_type": "both",
      "pe_strike": {"mode": "atm_offset", "offset": -1},
      "ce_strike": {"mode": "atm_offset", "offset": 1},
      "quantity_mode": "same_as_position",
      "max_cost": 500.00
    }
  },
  "execution_mode": "auto",
  "max_executions": 1
}
```

---

### 6. SCALE_UP

Increase position size by adding more lots.

**When to use:**
- Averaging into winning position
- Favorable market conditions
- Premium becomes attractive

**Config:**
```json
{
  "type": "scale_up",
  "config": {
    "scale_type": "lots",  // "lots" | "percentage"
    "value": 1,  // Add 1 lot or 50%
    "min_lots": 1,
    "max_lots": 5
  }
}
```

**Example:**
```json
{
  "id": "adj_scale_up",
  "name": "Add lot at 20% profit",
  "trigger": {
    "logic": "AND",
    "conditions": [
      {
        "variable": "PREMIUM.CAPTURED_PCT",
        "operator": "greater_equal",
        "value": 20.0
      },
      {
        "variable": "VIX.VALUE",
        "operator": "less_than",
        "value": 18.0
      }
    ]
  },
  "action": {
    "type": "scale_up",
    "config": {
      "scale_type": "lots",
      "value": 1,
      "max_lots": 3
    }
  },
  "execution_mode": "semi_auto",
  "max_executions": 2
}
```

---

### 7. SCALE_DOWN

Reduce position size by exiting partial lots.

**When to use:**
- Reduce risk in losing position
- Lock partial profits
- Manage exposure

**Config:**
```json
{
  "type": "scale_down",
  "config": {
    "scale_type": "percentage",  // "lots" | "percentage"
    "value": 50,  // Exit 50%
    "min_lots": 1
  }
}
```

**Example:**
```json
{
  "id": "adj_scale_down",
  "name": "Exit half at 30% loss",
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "variable": "PREMIUM.CAPTURED_PCT",
        "operator": "less_equal",
        "value": -30.0
      }
    ]
  },
  "action": {
    "type": "scale_down",
    "config": {
      "scale_type": "percentage",
      "value": 50,
      "min_lots": 1
    }
  },
  "execution_mode": "auto"
}
```

---

### 8. CONVERT

Convert position type or transaction type.

**When to use:**
- Convert intraday to positional
- Flip from Buy to Sell (or vice versa)

**Config:**
```json
{
  "type": "convert",
  "config": {
    "conversion_type": "intraday_to_positional",  // or "flip_direction"
    "legs_to_convert": ["leg_1", "leg_2"]
  }
}
```

---

### 9. ALERT_ONLY

Send alert without taking action. User must manually intervene.

**When to use:**
- Manual intervention required
- Complex adjustments
- Learning/testing mode

**Config:**
```json
{
  "type": "alert_only",
  "config": {
    "message": "Spot approaching upper strike - consider shifting",
    "priority": "urgent",  // "normal" | "urgent"
    "repeat_interval_minutes": 15  // Repeat alert every 15 min
  }
}
```

**Example:**
```json
{
  "id": "adj_alert",
  "name": "Alert when delta exceeds threshold",
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "variable": "STRATEGY.DELTA",
        "operator": "greater_than",
        "value": 0.30
      }
    ]
  },
  "action": {
    "type": "alert_only",
    "config": {
      "message": "Portfolio delta exceeds 0.30 - consider delta hedging",
      "priority": "urgent",
      "repeat_interval_minutes": 10
    }
  },
  "execution_mode": "auto"
}
```

---

## Trigger Conditions

Adjustment triggers use the same condition structure as entry conditions.

### Common Trigger Variables

#### P&L Based

```json
{
  "variable": "PREMIUM.CAPTURED_PCT",
  "operator": "greater_equal",
  "value": 50.0
}
```

#### Greeks Based

```json
{
  "variable": "STRATEGY.DELTA",
  "operator": "greater_than",
  "value": 0.30
}
```

#### Spot Distance

```json
{
  "variable": "SPOT.DISTANCE_TO.BREAKEVEN",
  "operator": "less_than",
  "value": 1.0  // Within 1% of breakeven
}
```

```json
{
  "variable": "SPOT.DISTANCE_TO.leg_1",
  "operator": "less_than",
  "value": 0.5  // Within 0.5% of leg_1 strike
}
```

#### Time Based

```json
{
  "variable": "STRATEGY.DTE",
  "operator": "less_equal",
  "value": 3  // 3 or fewer days to expiry
}
```

```json
{
  "variable": "TIME.CURRENT",
  "operator": "greater_equal",
  "value": "15:00"
}
```

#### Volatility Based

```json
{
  "variable": "VIX.VALUE",
  "operator": "greater_than",
  "value": 25.0
}
```

```json
{
  "variable": "IV.RANK",
  "operator": "less_than",
  "value": 30.0
}
```

---

## Execution Modes

### AUTO

Execute adjustment automatically without user confirmation.

**Best for:**
- Pre-tested adjustments
- Simple, low-risk adjustments
- High-frequency adjustments

**Example:**
```json
{
  "execution_mode": "auto",
  "timeout_seconds": 60,
  "timeout_action": "skip"
}
```

---

### SEMI_AUTO

Request user confirmation before executing.

**Best for:**
- Complex adjustments
- High-cost adjustments
- Learning/testing phase

**Example:**
```json
{
  "execution_mode": "semi_auto",
  "timeout_seconds": 300,  // 5 min to confirm
  "timeout_action": "skip"  // Skip if no response
}
```

**User receives:**
- Push notification
- WebSocket message
- Confirmation request in UI

**User can:**
- Confirm (execute as-is)
- Skip (ignore this time)
- Modify (change parameters before executing)

---

## Advanced Configuration

### Priority

When multiple adjustment rules trigger simultaneously, higher priority executes first.

```json
{
  "priority": 1  // 1 = highest, 100 = lowest
}
```

---

### Max Executions

Limit how many times a rule can execute for a strategy.

```json
{
  "max_executions": 1  // Execute only once
}
```

**Use case:** Add hedge only once at 50% profit

---

### Cooldown Period

Minimum time between consecutive executions of the same rule.

```json
{
  "cooldown_minutes": 30  // Wait 30 min before next execution
}
```

**Use case:** Prevent rapid repeated shifts

---

### Timeout Handling

What to do when confirmation times out (semi-auto mode).

```json
{
  "timeout_seconds": 180,
  "timeout_action": "skip"  // "skip" | "execute" | "alert"
}
```

- `skip` - Don't execute, log timeout
- `execute` - Execute anyway after timeout
- `alert` - Send another alert

---

## Common Adjustment Patterns

### Pattern 1: Profit Lock with Hedge

```json
{
  "id": "lock_profit",
  "name": "Lock 50% profit with ATM hedge",
  "enabled": true,
  "priority": 10,
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "variable": "PREMIUM.CAPTURED_PCT",
        "operator": "greater_equal",
        "value": 50.0
      }
    ]
  },
  "action": {
    "type": "add_hedge",
    "config": {
      "hedge_type": "both",
      "pe_strike": {"mode": "atm_offset", "offset": 0},
      "ce_strike": {"mode": "atm_offset", "offset": 0},
      "quantity_mode": "same_as_position"
    }
  },
  "execution_mode": "auto",
  "max_executions": 1
}
```

---

### Pattern 2: Time-Based Roll

```json
{
  "id": "weekly_roll",
  "name": "Roll to next week at 3 DTE",
  "enabled": true,
  "priority": 20,
  "trigger": {
    "logic": "AND",
    "conditions": [
      {
        "variable": "STRATEGY.DTE",
        "operator": "less_equal",
        "value": 3
      },
      {
        "variable": "TIME.CURRENT",
        "operator": "greater_equal",
        "value": "10:00"
      }
    ]
  },
  "action": {
    "type": "roll",
    "config": {
      "roll_to": "next_week",
      "strike_selection": "same_moneyness",
      "roll_legs": "all",
      "execution_style": "sequential"
    }
  },
  "execution_mode": "semi_auto",
  "timeout_seconds": 300,
  "max_executions": 1
}
```

---

### Pattern 3: Dynamic Strike Shift

```json
{
  "id": "shift_breach",
  "name": "Shift strike when spot breaches",
  "enabled": true,
  "priority": 1,
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "variable": "SPOT.DISTANCE_TO.leg_1",
        "operator": "less_than",
        "value": 0.3
      },
      {
        "variable": "SPOT.DISTANCE_TO.leg_3",
        "operator": "less_than",
        "value": 0.3
      }
    ]
  },
  "action": {
    "type": "shift",
    "config": {
      "direction": "away_from_spot",
      "shift_amount": 200,
      "shift_side": "breached"
    }
  },
  "execution_mode": "auto",
  "cooldown_minutes": 30
}
```

---

### Pattern 4: Partial Exit at Target

```json
{
  "id": "partial_exit",
  "name": "Exit half position at 60% profit",
  "enabled": true,
  "priority": 15,
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "variable": "PREMIUM.CAPTURED_PCT",
        "operator": "greater_equal",
        "value": 60.0
      }
    ]
  },
  "action": {
    "type": "scale_down",
    "config": {
      "scale_type": "percentage",
      "value": 50,
      "min_lots": 1
    }
  },
  "execution_mode": "auto",
  "max_executions": 1
}
```

---

### Pattern 5: Delta Hedge Alert

```json
{
  "id": "delta_alert",
  "name": "Alert when delta exceeds 0.30",
  "enabled": true,
  "priority": 5,
  "trigger": {
    "logic": "OR",
    "conditions": [
      {
        "variable": "STRATEGY.DELTA",
        "operator": "greater_than",
        "value": 0.30
      },
      {
        "variable": "STRATEGY.DELTA",
        "operator": "less_than",
        "value": -0.30
      }
    ]
  },
  "action": {
    "type": "alert_only",
    "config": {
      "message": "Portfolio delta breached ±0.30 - consider hedging",
      "priority": "urgent",
      "repeat_interval_minutes": 15
    }
  },
  "execution_mode": "auto"
}
```

---

## Multiple Rules Example

Iron Condor with comprehensive adjustment plan:

```json
{
  "adjustment_rules": [
    {
      "id": "adj_1",
      "name": "Profit lock at 50%",
      "priority": 10,
      "trigger": {
        "logic": "OR",
        "conditions": [
          {"variable": "PREMIUM.CAPTURED_PCT", "operator": "greater_equal", "value": 50.0}
        ]
      },
      "action": {
        "type": "add_hedge",
        "config": {
          "hedge_type": "both",
          "pe_strike": {"mode": "atm_offset", "offset": 0},
          "ce_strike": {"mode": "atm_offset", "offset": 0}
        }
      },
      "execution_mode": "auto",
      "max_executions": 1
    },
    {
      "id": "adj_2",
      "name": "Shift on breach",
      "priority": 1,
      "trigger": {
        "logic": "OR",
        "conditions": [
          {"variable": "SPOT.DISTANCE_TO.leg_1", "operator": "less_than", "value": 0.5}
        ]
      },
      "action": {
        "type": "shift",
        "config": {
          "direction": "away_from_spot",
          "shift_amount": 200,
          "shift_side": "breached"
        }
      },
      "execution_mode": "auto",
      "cooldown_minutes": 30
    },
    {
      "id": "adj_3",
      "name": "Exit at 70% profit",
      "priority": 5,
      "trigger": {
        "logic": "OR",
        "conditions": [
          {"variable": "PREMIUM.CAPTURED_PCT", "operator": "greater_equal", "value": 70.0}
        ]
      },
      "action": {
        "type": "exit_all",
        "config": {"order_type": "MARKET"}
      },
      "execution_mode": "auto",
      "max_executions": 1
    }
  ]
}
```

---

## Best Practices

1. **Start Simple** - Begin with 1-2 rules, add more as you gain confidence
2. **Test in Paper Mode** - Always test adjustment rules in paper trading first
3. **Set Max Executions** - Prevent rules from executing too many times
4. **Use Cooldown** - Avoid rapid repeated adjustments
5. **Priority Management** - Critical adjustments should have higher priority
6. **Semi-Auto for Complex** - Use semi-auto mode for expensive or complex adjustments
7. **Monitor First Week** - Watch closely during first week of live adjustments
8. **Alert Before Action** - Consider adding alert-only rule before auto-execution rule

---

## Phase 5 Roadmap

| Phase | Features |
|-------|----------|
| 5A | Greeks-based adjustments (Delta, Gamma, Vega, Theta) |
| 5B | Spot distance and premium capture adjustments |
| 5C | OI analysis and probability-based adjustments |
| 5D | AI-powered adjustment suggestions |
| 5E | Backtest adjustment rules |
| 5F | Multi-strategy adjustments |
