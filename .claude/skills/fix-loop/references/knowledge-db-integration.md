# Integration with knowledge.db

**Reading:**
```python
from db_helper import get_strategies, get_error_pattern

# Get ranked strategies for error type
strategies = get_strategies("selector_not_found")
# Returns: [{"id": 1, "description": "...", "success_rate": 0.85, "code_snippet": "..."}, ...]

# Get error pattern details
pattern = get_error_pattern(error_type="selector_not_found", component="positions")
```

**Writing:**
```python
from db_helper import record_error, record_attempt, update_strategy_score

# Record new error occurrence
error_id = record_error(
    error_type="selector_not_found",
    component="positions",
    file_path="tests/e2e/specs/positions/positions.happy.spec.js",
    error_message="Timeout waiting for locator...",
    stack_trace=stack_trace
)

# Record fix attempt
record_attempt(
    error_pattern_id=error_id,
    strategy_id=strategy['id'],
    outcome='success',  # or 'failure'
    fix_description="Updated data-testid from 'exit-confirm' to 'positions-exit-confirm'"
)

# Update strategy score
update_strategy_score(strategy_id=strategy['id'], outcome='success')
```
