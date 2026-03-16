---
description: >
  Autopilot adjustments are categorized as OFFENSIVE/DEFENSIVE/NEUTRAL.
  DEGRADED risk state MUST disable offensive adjustments. Misclassification is a safety bug.
globs: ["backend/app/services/autopilot/**/*.py"]
synthesized: true
private: false
---

# Adjustment Offensive/Defensive Classification

## Categories

Every autopilot adjustment action MUST be classified:

| Category | Risk Impact | Examples |
|----------|-------------|---------|
| **OFFENSIVE** | Increases risk for more premium | roll_strike_closer, scale_up, add_to_opposite_side, widen_spread |
| **DEFENSIVE** | Reduces risk (priority: protection) | add_hedge, close_leg, scale_down, exit_all, roll_strike_farther |
| **NEUTRAL** | Rebalances without changing risk | roll_expiry (same strike), time-based rebalance |

## Risk State Interaction

The AI risk state engine (NORMAL → DEGRADED → PAUSED) controls which adjustments are allowed:

| Risk State | Offensive | Defensive | Neutral |
|-----------|-----------|-----------|---------|
| NORMAL | Allowed | Allowed | Allowed |
| DEGRADED | **BLOCKED** | Allowed | Allowed |
| PAUSED | BLOCKED | Exit-only | BLOCKED |

## DEGRADED Mode Restrictions

When risk state is DEGRADED:
- Offensive adjustments are suppressed (not executed)
- Confidence threshold increased by 15%
- Lot multiplier reduced by 50%
- Only defensive and neutral adjustments proceed

## Adding New Adjustment Types

When adding a new adjustment trigger to `AdjustmentEngine`:
1. Define the trigger type
2. Classify it in `ADJUSTMENT_CATEGORIES` dict as OFFENSIVE, DEFENSIVE, or NEUTRAL
3. Also classify in `SuggestionEngine.SUGGESTION_CATEGORY_MAP`
4. Misclassification is a safety bug — an offensive action running in DEGRADED state
   could increase losses when the system is already in drawdown

