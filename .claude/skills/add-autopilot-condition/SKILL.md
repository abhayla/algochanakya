---
name: add-autopilot-condition
description: >
  Add a new condition variable to the AutoPilot ConditionEngine.
  Use when extending the rule engine with new market signals or computed metrics.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<variable_namespace> <variable_name> (e.g., PREMIUM.DECAY_RATE)"
version: "1.0.0"
synthesized: true
private: false
---

# Add AutoPilot Condition Variable

Add a new condition variable that users can reference in AutoPilot rules. The ConditionEngine
evaluates rules like `SPOT.CHANGE_PCT > 1.5 AND VIX.VALUE < 18` — this skill walks through
adding a new variable to that system.

## Existing Variable Namespaces

| Namespace | Examples | Source |
|-----------|----------|--------|
| `TIME.*` | TIME.HOUR, TIME.MINUTES_TO_CLOSE | System clock + market calendar |
| `SPOT.*` | SPOT.PRICE, SPOT.CHANGE_PCT, SPOT.HIGH | Live ticker data |
| `VIX.*` | VIX.VALUE, VIX.CHANGE, VIX.PERCENTILE | India VIX feed |
| `PREMIUM.*` | PREMIUM.TOTAL, PREMIUM.DECAY_PCT | Position P&L service |
| `STRATEGY.*` | STRATEGY.POP, STRATEGY.MAX_LOSS | Strategy analytics |
| `OI.*` | OI.PCR, OI.CHANGE_PCT | Open interest data |
| `PROBABILITY.*` | PROBABILITY.PROFIT, PROBABILITY.TOUCH | Monte Carlo / BS model |
| `IV.*` | IV.RANK, IV.PERCENTILE, IV.SKEW | Implied volatility metrics |

## STEP 1: Define the Variable Specification

Determine:
- **Namespace**: Use an existing namespace if the variable fits, or propose a new one
- **Variable name**: ALL_CAPS with underscores (e.g., `PREMIUM.DECAY_RATE`)
- **Data type**: float, int, bool, or str — most variables are float
- **Supported operators**: `>`, `<`, `>=`, `<=`, `==`, `!=`, `BETWEEN`, `IN`
- **Unit/range**: Document expected value ranges for user guidance

Search for the ConditionEngine class:

```
Grep pattern="class ConditionEngine" type="py"
```

## STEP 2: Implement the Evaluator Method

Open the ConditionEngine file and add a new evaluator method. Each variable maps to
a method that fetches or computes its current value.

```python
async def _evaluate_NAMESPACE_VARIABLE(self, context: ConditionContext) -> ConditionResult:
    """Evaluate NAMESPACE.VARIABLE — <brief description>.
    
    Returns:
        ConditionResult with value (float), timestamp, and metadata.
    """
    try:
        # Fetch the raw data from the appropriate service
        raw_value = await self._some_service.get_value(context.symbol)
        
        return ConditionResult(
            variable="NAMESPACE.VARIABLE",
            value=raw_value,
            timestamp=datetime.now(),
            metadata={"source": "service_name"},
            success=True,
        )
    except Exception as e:
        return ConditionResult(
            variable="NAMESPACE.VARIABLE",
            value=None,
            timestamp=datetime.now(),
            metadata={"error": str(e)},
            success=False,
        )
```

Key requirements:
- Method MUST be async
- Method MUST return a `ConditionResult` dataclass
- Method MUST handle exceptions and return `success=False` on failure
- Method MUST set `timestamp` to current time

## STEP 3: Register in the Variable Map

Find the `VARIABLE_MAP` dictionary (or `_variable_evaluators`) and register the new variable:

```
Grep pattern="VARIABLE_MAP|_variable_evaluators" type="py"
```

Add the mapping:
```python
"NAMESPACE.VARIABLE": self._evaluate_NAMESPACE_VARIABLE,
```

## STEP 4: Register Supported Operators

Find where operators are registered per variable (often `VARIABLE_OPERATORS` or
`_supported_operators`). Add the operators your variable supports:

```python
"NAMESPACE.VARIABLE": [Operator.GT, Operator.LT, Operator.GTE, Operator.LTE, Operator.EQ, Operator.NEQ],
```

If the variable is categorical (e.g., a regime label), use `EQ`, `NEQ`, `IN`.
If the variable is numeric, include comparison operators and optionally `BETWEEN`.

## STEP 5: Update Class Docstring and Documentation

Update the ConditionEngine class docstring to list the new variable:
- Add to the variable table in the docstring
- Include expected value range and units
- Add usage example: `NAMESPACE.VARIABLE > threshold`

## STEP 6: Inject Required Dependencies

If the evaluator needs a new service dependency:
1. Add the service parameter to `ConditionEngine.__init__()`
2. Store as `self._service_name`
3. Update the factory/DI container where ConditionEngine is instantiated
4. Verify the service is available during AutoPilot initialization

```
Grep pattern="ConditionEngine(" type="py"
```

## STEP 7: Write Tests

Create or extend tests in the autopilot test directory:

```
Grep pattern="test.*condition" type="py" -i
```

Required test cases:
1. **Happy path**: Variable evaluates correctly with valid data
2. **Missing data**: Service returns None — evaluator returns `success=False`
3. **Operator evaluation**: Each supported operator computes correctly
4. **Integration with rule parser**: A complete rule string using the variable parses and evaluates
5. **Edge cases**: Zero values, negative values, boundary conditions

```python
@pytest.mark.asyncio
async def test_new_variable_evaluates(condition_engine, mock_service):
    mock_service.get_value.return_value = 42.5
    result = await condition_engine._evaluate_NAMESPACE_VARIABLE(context)
    assert result.success is True
    assert result.value == 42.5

@pytest.mark.asyncio
async def test_new_variable_handles_failure(condition_engine, mock_service):
    mock_service.get_value.side_effect = ConnectionError("timeout")
    result = await condition_engine._evaluate_NAMESPACE_VARIABLE(context)
    assert result.success is False
    assert result.value is None
```

## STEP 8: Verify End-to-End

1. Run the condition engine tests: `pytest backend/tests/ -k "condition" -v`
2. Test a full rule string manually in a Python shell or test:
   ```python
   rule = "NAMESPACE.VARIABLE > 10 AND SPOT.CHANGE_PCT < 2"
   result = await engine.evaluate_rule(rule, context)
   ```
3. Verify the variable appears in the API endpoint that lists available variables
   (if such an endpoint exists)

## CRITICAL RULES

- Every evaluator MUST return `ConditionResult` — never raise exceptions to the caller
- Variables MUST use the `NAMESPACE.NAME` dot-notation format
- Numeric variables MUST return Python `float` or `Decimal`, never strings
- The variable name MUST be registered in both the variable map AND the operator map
- MUST NOT modify existing variable evaluators while adding a new one
- If the variable depends on live market data, handle market-closed scenarios gracefully
- Test with the AutoPilot disabled (kill switch ON) to ensure evaluation still works
  but actions are blocked
