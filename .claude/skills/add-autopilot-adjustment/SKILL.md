---
name: add-autopilot-adjustment
description: >
  Add a new adjustment trigger to the AutoPilot AdjustmentEngine with
  proper offensive/defensive classification and risk state interaction.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<trigger-name>"
version: "1.0.0"
synthesized: true
private: false
---

# Add AutoPilot Adjustment Trigger

## STEP 1: Define Trigger Type Enum

In `backend/app/models/autopilot.py`, add to `AdjustmentTriggerType`:

```python
class AdjustmentTriggerType(str, Enum):
    ...
    NEW_TRIGGER = "new_trigger"
```

## STEP 2: Classify as Offensive/Defensive/Neutral

In `backend/app/services/autopilot/adjustment_engine.py`, add to `ADJUSTMENT_CATEGORIES`:

```python
ADJUSTMENT_CATEGORIES = {
    ...
    "new_trigger_action": AdjustmentCategory.DEFENSIVE,
}
```

Classification guide:
- OFFENSIVE: increases risk for more premium (roll closer, scale up, widen spread)
- DEFENSIVE: reduces risk (add hedge, close leg, scale down, exit all)
- NEUTRAL: rebalances without changing risk profile (roll same-strike to new expiry)

**Misclassifying OFFENSIVE as NEUTRAL is a safety bug** - allows risk-increasing actions during drawdown.

## STEP 3: Implement Trigger Evaluation

Add evaluation method to `AdjustmentEngine`:

```python
async def _evaluate_new_trigger(self, strategy, legs, market_data, config):
    threshold = config.get("threshold", default_value)
    current = ...  # Calculate from market data/positions
    if current > threshold:
        return AdjustmentAction(
            trigger_type=AdjustmentTriggerType.NEW_TRIGGER,
            action_type=AdjustmentActionType.SCALE_DOWN,
            category=AdjustmentCategory.DEFENSIVE,
            reason=f"Triggered: {current} > {threshold}",
        )
    return None
```

## STEP 4: Register in Evaluation Loop

In `evaluate_adjustments()`:

```python
if "new_trigger" in adjustment_config:
    action = await self._evaluate_new_trigger(strategy, legs, market_data, adjustment_config)
    if action:
        actions.append(action)
```

## STEP 5: Add to SuggestionEngine

In `backend/app/services/autopilot/suggestion_engine.py`:

```python
SUGGESTION_CATEGORY_MAP = {
    ...
    SuggestionType.NEW_TYPE: AdjustmentCategory.DEFENSIVE,
}
```

## STEP 6: Write Tests

```python
async def test_trigger_fires_when_threshold_exceeded(db_session):
    ...

async def test_offensive_trigger_blocked_in_degraded_state(db_session):
    """DEGRADED risk state MUST block offensive adjustments."""
    ...
```

## CRITICAL RULES

- MUST classify in ADJUSTMENT_CATEGORIES dict
- MUST add to SUGGESTION_CATEGORY_MAP
- MUST test risk state interaction (NORMAL=all, DEGRADED=blocks offensive, PAUSED=exit only)
- MUST handle missing market data gracefully
- Document phase/feature number in docstring
