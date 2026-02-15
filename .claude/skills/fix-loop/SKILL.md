---
name: fix-loop
description: Iterative fix cycle with 6-level gradual thinking escalation (Normal → Basic → Moderate → Deep → VeryDeep → UltraThink), code review gates, and knowledge.db integration. Diagnoses and fixes test failures using ranked strategies. Use when tests fail during implement Step 5, or standalone for any bug fix.
metadata:
  author: AlgoChanakya
  version: "2.0"
  category: workflow
---

# fix-loop - Iterative Fix Cycle

**Purpose:** Central fix engine with 6-level gradual thinking escalation, code review gates, and knowledge.db integration.

**When to use:** Automatically invoked by implement Step 5 when tests fail. Can be invoked standalone for any bug fix.

**Integration:** Reads strategies from `knowledge.db`, records every attempt, updates strategy scores.

---

## Overview

The fix-loop implements a sophisticated fix strategy with:
- **Thinking escalation:** 6 gradual levels (Normal → Basic → Moderate → Deep → VeryDeep → UltraThink), 2 cycles per level
- **Code review gate:** Every fix validated by code-reviewer agent
- **Knowledge integration:** Pre-check strategies, post-record outcomes
- **Prohibited actions:** Cannot skip tests, weaken assertions, or delete tests

---

## Algorithm

### Initialization

1. **Read workflow state:**
   ```python
   from pathlib import Path
   import sys
   sys.path.insert(0, str(Path(".claude/hooks")))
   from hook_utils import read_workflow_state, write_workflow_state

   state = read_workflow_state()
   current_iteration = state['steps']['step5_fixLoop']['iterations']
   ```

2. **Query knowledge.db for ranked strategies:**
   ```python
   sys.path.insert(0, str(Path(".claude/learning")))
   from db_helper import get_strategies, record_error

   # Get strategies for error type
   error_type = detect_error_type(test_output)  # [PLANNED - pseudocode]
   strategies = get_strategies(error_type)

   # Strategies are ranked by success rate with time decay
   # Format: [{"id": 1, "description": "...", "code_snippet": "...", "success_rate": 0.85}, ...]
   ```

3. **Set thinking depth based on iteration (6 gradual levels):**
   - **Level 1 - Normal** (Iterations 1-2): Standard analysis, direct error interpretation
   - **Level 2 - Basic** (Iterations 3-4): Basic root cause, file context, common patterns
   - **Level 3 - Moderate** (Iterations 5-6): Cross-file dependencies, component interactions
   - **Level 4 - Deep** (Iterations 7-8): Timing, async, architecture, broker abstraction
   - **Level 5 - VeryDeep** (Iterations 9-10): Previous attempts analysis, anti-patterns, alternatives
   - **Level 6 - UltraThink** (Iterations 11-12): Maximum depth, test validity, fundamental assumptions

---

### Main Loop

**Budget limits:**
- **Max iterations:** 12 (total fix attempts for this command invocation, 2 cycles per thinking level)
- **Max attempts per issue:** 3 (before moving to next strategy)
- **Max cascade depth:** 2 (fixes can trigger new failures, but only 2 levels deep)

```
FOR iteration = 1 TO 12:
    1. Identify failing tests
    2. Select fix strategy
    3. Apply thinking escalation (6 gradual levels)
    4. Generate fix
    5. Run code review gate
    6. Apply fix
    7. Run tests
    8. Record outcome to knowledge.db
    9. IF all pass: SUCCESS, exit loop
   10. IF max attempts: ESCALATE or FAIL
```

---

### Step-by-Step Process

#### 1. Identify Failing Tests

Parse test output to extract:
- Test file/spec name
- Specific test case that failed
- Error message
- Stack trace (if available)

**For E2E (Playwright):**
```
Failed tests:
  tests/e2e/specs/positions/positions.happy.spec.js:45:5 › Positions › should exit position successfully
    Error: Timeout 30000ms exceeded waiting for locator('[data-testid="positions-exit-confirm"]')
```

**For Backend (pytest):**
```
FAILED tests/backend/autopilot/test_kill_switch.py::test_emergency_exit - AssertionError: assert 0 == 2
```

**For Frontend (Vitest):**
```
FAIL src/components/positions/ExitPositionModal.spec.js > ExitPositionModal > should emit exit event
    AssertionError: expected "spy" to be called with arguments: [{ quantity: 10 }]
```

---

#### 2. Select Fix Strategy

**Priority order:**

1. **Known strategies from knowledge.db** (ranked by success rate):
   ```python
   strategies = get_strategies(error_type)
   if strategies:
       # Use highest-ranked untried strategy
       strategy = strategies[0]
       print(f"Using strategy (success rate: {strategy['success_rate']}): {strategy['description']}")
   ```

2. **Error type heuristics** (if no strategies in DB):
   - `selector_not_found` → Check data-testid, component may have been refactored
   - `timeout` → Increase timeout or add wait conditions
   - `assertion_error` → Review expected vs actual values, check test logic
   - `import_error` → Check file paths, circular imports
   - `database_error` → Check async/await, transaction handling

3. **Fallback to debugger agent:**
   ```
   Task(
       subagent_type="general-purpose",
       prompt="""You are a Debugger Agent for AlgoChanakya.
       Follow the instructions in .claude/agents/debugger.md.

       Read .claude/agents/debugger.md first, then:
       Analyze this test failure: [error details]"""
   )
   ```

---

#### 3. Apply Thinking Escalation

```python
iteration = state['steps']['step5_fixLoop']['iterations']

# Level 1: Normal (Iterations 1-2)
if iteration <= 2:
    thinking_mode = "normal"
    # Direct fix attempt without debugger agent

# Level 2: Basic (Iterations 3-4)
elif iteration <= 4:
    thinking_mode = "basic"
    agent_result = Task(
        subagent_type="general-purpose",
        model="sonnet",
        prompt=f"""You are a Debugger Agent for AlgoChanakya.
        Follow the instructions in .claude/agents/debugger.md.

        LEVEL 2 - BASIC ROOT CAUSE ANALYSIS:

        Failing test: {test_name}
        Error: {error_message}
        Stack trace: {stack_trace}

        Provide:
        1. Error type classification
        2. File/component context check
        3. Common fix pattern recommendation
        """
    )

# Level 3: Moderate (Iterations 5-6)
elif iteration <= 6:
    thinking_mode = "moderate"
    agent_result = Task(
        subagent_type="general-purpose",
        model="sonnet",
        prompt=f"""You are a Debugger Agent for AlgoChanakya.
        Follow the instructions in .claude/agents/debugger.md.

        LEVEL 3 - MODERATE CROSS-FILE ANALYSIS:

        Failing test: {test_name}
        Error: {error_message}
        Stack trace: {stack_trace}
        Component: {component_name}

        Provide:
        1. Import chain analysis
        2. Function call hierarchy
        3. State propagation paths
        4. API contract validation
        """
    )

# Level 4: Deep (Iterations 7-8)
elif iteration <= 8:
    thinking_mode = "deep"
    agent_result = Task(
        subagent_type="general-purpose",
        model="sonnet",
        prompt=f"""You are a Debugger Agent for AlgoChanakya.
        Follow the instructions in .claude/agents/debugger.md.

        LEVEL 4 - DEEP SYSTEM-LEVEL ANALYSIS:

        Failing test: {test_name}
        Error: {error_message}
        Stack trace: {stack_trace}
        Component: {component_name}
        Recent changes: {recent_file_changes}

        Provide:
        1. Race condition analysis
        2. Event propagation timing
        3. Async/await flow validation
        4. Broker abstraction compliance check
        5. Database transaction handling
        """
    )

# Level 5: VeryDeep (Iterations 9-10)
elif iteration <= 10:
    thinking_mode = "verydeep"
    agent_result = Task(
        subagent_type="general-purpose",
        model="sonnet",
        prompt=f"""You are a Debugger Agent for AlgoChanakya.
        Follow the instructions in .claude/agents/debugger.md.

        LEVEL 5 - VERY DEEP HISTORICAL PATTERN ANALYSIS:

        We have attempted {iteration - 1} fixes without success.

        Failing test: {test_name}
        Error: {error_message}
        Stack trace: {stack_trace}

        Previous fix attempts:
        {format_previous_attempts()}

        Provide:
        1. Analysis of why previous 8 fixes failed
        2. Similar past errors from knowledge.db
        3. Anti-pattern detection
        4. Alternative architectural approaches
        5. Test logic validity review
        """
    )

# Level 6: UltraThink (Iterations 11-12)
else:  # iteration >= 11
    thinking_mode = "ultrathink"
    agent_result = Task(
        subagent_type="general-purpose",
        model="sonnet",
        prompt=f"""You are a Debugger Agent for AlgoChanakya.
        Follow the instructions in .claude/agents/debugger.md.

        LEVEL 6 - ULTRATHINK MAXIMUM DEPTH + META-REASONING:

        CRITICAL: We have attempted {iteration - 1} fixes without success.

        Failing test: {test_name}
        Error: {error_message}
        Stack trace: {stack_trace}

        Previous fix attempts:
        {format_previous_attempts()}

        Provide:
        1. Question test correctness (is the test itself wrong?)
        2. Challenge requirement interpretation
        3. Explore complete redesign options
        4. Consider external factors (infrastructure, timing, environment)
        5. Full system state reconstruction
        6. Meta-analysis: Are we solving the right problem?
        """
    )
```

---

#### 4. Generate Fix

Based on selected strategy and thinking analysis, generate the fix:

**Common fix patterns:**

- **Data-testid not found:**
  ```javascript
  // Check if element exists with different testid
  const element = await page.locator('[data-testid="new-positions-exit-confirm"]')
  ```

- **Timeout waiting for element:**
  ```javascript
  // Add explicit wait
  await page.waitForSelector('[data-testid="positions-exit-confirm"]', { timeout: 60000 })
  ```

- **Assertion mismatch:**
  ```python
  # Fix expected value based on actual behavior
  assert actual_value == expected_value, f"Expected {expected_value}, got {actual_value}"
  ```

- **Import error:**
  ```python
  # Fix import path
  from app.services.autopilot.kill_switch import KillSwitch  # Correct subdirectory
  ```

- **Broker abstraction violation:**
  ```python
  # Replace direct KiteConnect usage
  from app.services.brokers.factory import get_broker_adapter
  adapter = get_broker_adapter(user.order_broker_type, credentials)
  ```

---

#### 5. Run Code Review Gate

**Every fix MUST pass code review before applying.**

```
agent_result = Task(
    subagent_type="general-purpose",
    model="inherit",
    prompt=f"""You are a Code-Reviewer Agent for AlgoChanakya.
    Follow the instructions in .claude/agents/code-reviewer.md.

    Read .claude/agents/code-reviewer.md first, then:

    Review this fix for AlgoChanakya codebase compliance:

    File: {file_path}
    Fix description: {fix_description}

    Proposed changes:
    ```
    {diff}
    ```

    Check:
    1. Broker abstraction: No direct KiteConnect/SmartAPI imports
    2. Trading constants: No hardcoded lot sizes/strike steps
    3. Folder structure: Services in correct subdirectories
    4. Data-testid: All interactive elements have [screen]-[component]-[element]
    5. Async: All SQLAlchemy uses async/await
    6. Security: No credentials in code
    7. Prohibited: No test skipping, assertion weakening, test deletion

    Return: APPROVED or FLAGGED(severity, issue)
    """
)
```

**If FLAGGED with Critical or High severity:**
- **Reject the fix**
- Increment attempt counter
- Try next strategy

**If APPROVED:**
- Proceed to apply fix

---

#### 6. Apply Fix

Use `Edit` tool to apply the fix:

```python
Edit(
    file_path=target_file,
    old_string=original_code,
    new_string=fixed_code
)
```

**Record the attempt:**
```python
from db_helper import record_attempt

record_attempt(
    error_pattern_id=error_pattern['id'],
    strategy_id=strategy['id'],
    outcome='applied',  # or 'rejected' if code review failed
    fix_description=fix_description
)
```

---

#### 7. Run Tests

Re-run the specific failing test:

```bash
# E2E
npx playwright test path/to/spec.js

# Backend
pytest path/to/test_file.py::test_function -v

# Frontend
vitest run path/to/test.spec.js
```

**Hooks automatically:**
- Record result via `post_test_update.py`
- Independently verify via `verify_test_rerun.py`

---

#### 8. Record Outcome to knowledge.db

```python
from db_helper import update_strategy_score

if test_passed:
    outcome = 'success'
    update_strategy_score(strategy_id, outcome='success')
else:
    outcome = 'failure'
    update_strategy_score(strategy_id, outcome='failure')

record_attempt(
    error_pattern_id=error_pattern['id'],
    strategy_id=strategy['id'],
    outcome=outcome,
    fix_description=fix_description
)
```

**Strategy scoring with time decay:**
- Success: +0.1 to success_rate (decayed by recency)
- Failure: -0.05 to success_rate
- Time decay: Recent outcomes weighted 2x more than old outcomes

---

#### 9. Check Exit Conditions

**SUCCESS (exit with code 0):**
- All tests pass
- Update workflow state:
  ```python
  state['steps']['step5_fixLoop']['completed'] = True
  state['skillInvocations']['fixLoopSucceeded'] = True
  write_workflow_state(state)
  ```

**CONTINUE (next iteration):**
- Some tests still failing
- Budget not exhausted (iteration < 12)
- Increment iteration counter

**FAIL (exit with code 1):**
- Max iterations reached (12)
- OR: Same error 3x with different strategies
- OR: All strategies exhausted (scores < 0.1)
- Update workflow state:
  ```python
  state['skillInvocations']['fixLoopSucceeded'] = False
  write_workflow_state(state)
  ```

---

## Prohibited Actions

**The fix-loop enforces these prohibitions:**

### ❌ NEVER Skip Tests

```python
# BLOCKED
@pytest.mark.skip("Flaky test")
def test_something():
    ...

# BLOCKED
test.skip('Not working')
```

### ❌ NEVER Weaken Assertions

```python
# BLOCKED - weakening from == to >=
# OLD: assert result == 5
# NEW: assert result >= 5  # This is weakening!

# BLOCKED - removing assertions
# OLD: assert response.status_code == 200
# NEW: pass  # Removed assertion!
```

### ❌ NEVER Delete Tests

```python
# BLOCKED - removing entire test function
# This is only allowed if user explicitly requests test removal
```

### ❌ NEVER Add @pytest.mark.skip

```python
# BLOCKED
@pytest.mark.skip(reason="TODO: Fix later")
```

**If a fix violates these prohibitions, code review gate BLOCKS it.**

---

## Cascade Handling

Fixes can trigger new failures (cascade). Handle up to depth 2:

```python
cascade_depth = 0
MAX_CASCADE_DEPTH = 2

while has_failures and iteration < 12:
    fix_result = apply_fix()

    if fix_result.new_failures and fix_result.new_failures != previous_failures:
        cascade_depth += 1

        if cascade_depth > MAX_CASCADE_DEPTH:
            print("⚠️  Cascade depth exceeded. Stopping to prevent infinite loop.")
            break

    # Continue fixing
```

---

## Stuck Conditions

**Stop and ask user if:**
1. Same error 3x with different strategies failing
2. All strategies exhausted (scores < 0.1)
3. 12 total attempts reached (all 6 thinking levels exhausted)
4. Fix requires modifying files outside feature scope
5. Error type completely unknown (no strategies, no heuristics)

**Ask user:**
```
AskUserQuestion(
    questions=[{
        "question": "Fix loop is stuck after 12 attempts (all 6 thinking levels exhausted). How should we proceed?",
        "header": "Stuck",
        "multiSelect": False,
        "options": [
            {"label": "Continue with manual intervention", "description": "I'll help you investigate"},
            {"label": "Revert changes and retry", "description": "Start fresh with different approach"},
            {"label": "Skip this test for now", "description": "Mark as known issue, fix later"},
            {"label": "Escalate to user", "description": "Stop and let me handle it"}
        ]
    }]
)
```

---

## Integration with knowledge.db

See [references/knowledge-db-integration.md](references/knowledge-db-integration.md) for detailed database integration patterns.

---

## Output Format

**On success:**
```
✅ Fix loop completed successfully!

Iterations: 3
Fixes applied: 2
Tests passed: 5/5

Changes:
  - tests/e2e/specs/positions/positions.happy.spec.js: Updated data-testid
  - backend/app/api/routes/positions.py: Fixed broker adapter usage

All tests now passing.
```

**On failure:**
```
❌ Fix loop failed after 12 iterations (all 6 thinking levels exhausted).

Remaining failures:
  - tests/e2e/specs/positions/positions.happy.spec.js:45 - Timeout waiting for selector
  - backend/tests/autopilot/test_kill_switch.py::test_emergency_exit - AssertionError

Last strategy attempted: "Update data-testid" (success rate: 0.45)
Thinking level reached: Level 6 (UltraThink)

User intervention required.
```

---

## Skills Called

| Skill | When | Purpose |
|-------|------|---------|
| `test-fixer` | Attempt 1-2 | Pattern detection and diagnosis |
| None (direct fix) | Attempt 1 | Normal fix attempt |

---

## Agents Called

| Agent | When | Purpose |
|-------|------|---------|
| `debugger` | Iteration 2+ | Root cause analysis with ThinkHard/UltraThink |
| `code-reviewer` | Every fix | Validate fix before applying |

---

## Example Usage

```
# Automatically invoked by implement
Step 5: Skill("fix-loop")

# Standalone invocation
Skill("fix-loop")
```

---

## Implementation Notes

**The skill orchestrates:**
1. Hook utilities (workflow state, logging)
2. knowledge.db queries (via db_helper.py)
3. Sub-agents (debugger, code-reviewer)
4. Test execution (via Bash)
5. File modifications (via Edit)

**Exit codes:**
- **0:** All tests fixed successfully
- **1:** Failed to fix all tests (user intervention needed)
