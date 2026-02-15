---
name: implement
description: 7-step mandatory workflow for implementing features, bug fixes, and refactoring. Enforces test-driven development with requirements, test writing, implementation, verification, fix loop, visual verification, and commit pipeline. Use when user says 'implement', 'add feature', 'build', or any task requiring production code changes.
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: workflow
---

# implement - 7-Step Mandatory Workflow

**Purpose:** Primary orchestration command for implementing features with enforced test-driven workflow.

**When to use:** Any feature implementation, bug fix, or refactoring task that modifies production code.

**Enforcement:** Hooks block commits and code changes until all steps are complete.

---

## Workflow Steps

### Step 0: Pre-Execution Knowledge Check

**BEFORE starting implementation**, query existing knowledge for potential issues:

1. **Check failure index:**
   ```python
   from pathlib import Path
   import json

   failure_index_path = Path(".claude/logs/learning/failure-index.json")
   if failure_index_path.exists():
       with open(failure_index_path) as f:
           index = json.load(f)
           # Review entries for relevant components
   ```

2. **Query knowledge database:**
   ```python
   import sys
   sys.path.insert(0, str(Path(".claude/learning")))
   from db_helper import get_strategies, get_stats

   # Get strategies for relevant error types
   strategies = get_strategies("selector_not_found")
   print(f"Known strategies: {strategies}")
   ```

3. **Initialize workflow state:**
   ```python
   sys.path.insert(0, str(Path(".claude/hooks")))
   from hook_utils import init_workflow_state

   state = init_workflow_state("implement")
   ```

**Actions:**
- Review past failures for the component being modified
- Note high-risk patterns (broker abstraction violations, hardcoded constants, etc.)
- Prepare mitigation strategies

---

### Step 1: Requirements/Clarification

**Goal:** Understand the task fully before writing any code.

**Required actions (from CLAUDE.md Section 3):**

1. **State understanding in 2-3 sentences:**
   ```
   "I understand you want to [task description].
   This will affect [components/files].
   The expected outcome is [behavior]."
   ```

2. **Research codebase for existing patterns:**
   - Use `Glob` to find similar implementations
   - Use `Grep` to search for relevant patterns
   - Read existing code for the component

3. **Check relevant documentation:**
   - [Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md) for task-specific docs
   - [Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md) for ongoing work
   - [Broker Abstraction](docs/architecture/broker-abstraction.md) for multi-broker design
   - [Feature Registry](docs/feature-registry.yaml) for affected features

4. **Ask clarifying questions if needed:**
   - Use `AskUserQuestion` tool for scope, design, or integration questions
   - ONLY skip if: doc changes, obvious bug fixes, explicit user instructions

**Completion criteria:**
- Understanding stated clearly
- Relevant docs reviewed
- Existing patterns identified
- Questions resolved

**Mark complete:**
```python
from hook_utils import read_workflow_state, write_workflow_state
from datetime import datetime

state = read_workflow_state()
state['steps']['step1_requirements']['completed'] = True
state['steps']['step1_requirements']['timestamp'] = datetime.now().isoformat()
write_workflow_state(state)
```

---

### Step 2: Write/Update Tests

**Goal:** Define expected behavior through tests BEFORE implementing.

**Required actions:**

1. **Determine test layers needed:**
   - **E2E (Playwright):** User-facing behavior, UI interactions, screen-to-screen flows
   - **Backend (pytest):** API endpoints, business logic, database operations
   - **Frontend (Vitest):** Vue components, Pinia stores, composables

2. **Generate tests using appropriate skills:**
   - **E2E:** `Skill("e2e-test-generator", args="[screen] [feature] [test_type]")`
     - Example: `Skill("e2e-test-generator", args="positions exit-modal happy")`
   - **Backend:** Write pytest tests in `backend/tests/{module}/`
     - Follow pytest markers: `@pytest.mark.unit`, `@pytest.mark.api`, `@pytest.mark.integration`
   - **Frontend:** `Skill("vitest-generator", args="[component] [test_type]")`
     - Example: `Skill("vitest-generator", args="ExitPositionModal unit")`

3. **Follow conventions:**
   - **E2E:** Use `data-testid` with pattern `[screen]-[component]-[element]`
     - Import from `auth.fixture.js` (NOT `@playwright/test`)
     - Extend `BasePage.js` for Page Objects
   - **Backend:** Use async/await for all database operations
     - Test broker abstraction compliance
   - **Frontend:** Test component props, events, reactivity
     - Mock API calls using Vitest mocks

4. **Record test files in workflow state:**
   ```python
   state = read_workflow_state()
   state['steps']['step2_tests']['testFiles'].append('path/to/test/file')
   state['steps']['step2_tests']['testLayers'].append('e2e')  # or 'backend', 'frontend'
   state['steps']['step2_tests']['completed'] = True
   state['steps']['step2_tests']['timestamp'] = datetime.now().isoformat()
   write_workflow_state(state)
   ```

**Completion criteria:**
- Tests written for all affected layers
- Tests use correct conventions
- Tests initially fail (red phase of TDD)

**Note:** Hooks BLOCK production code changes until this step is complete.

---

### Step 3: Implement Feature

**Goal:** Write minimum code to pass the tests.

**Required actions:**

1. **Follow broker abstraction patterns (CRITICAL):**
   - **NEVER** directly use `KiteConnect` or `SmartAPI` client
   - **ALWAYS** use broker adapters and factories:
     ```python
     # Order execution
     from app.services.brokers.factory import get_broker_adapter
     adapter = get_broker_adapter(user.order_broker_type, credentials)
     order = await adapter.place_order(...)  # Returns UnifiedOrder

     # Market data
     from app.services.brokers.market_data.factory import get_market_data_adapter
     data_adapter = get_market_data_adapter(user.market_data_broker_type, credentials)
     quote = await data_adapter.get_live_quote(symbol)
     ```

2. **Use centralized trading constants:**
   ```python
   # Backend
   from app.constants.trading import get_lot_size, get_strike_step
   lot_size = get_lot_size("NIFTY")  # 25

   # Frontend
   import { getLotSize, getStrikeStep } from '@/constants/trading'
   const lotSize = getLotSize('NIFTY')
   ```

3. **Follow folder structure rules:**
   - Backend services: Must be in subdirectories (`autopilot/`, `options/`, `legacy/`, `ai/`, `brokers/`)
   - Frontend CSS: Must be in `frontend/src/assets/styles/` (NOT `assets/css/`)
   - Frontend images: Must be in `frontend/src/assets/logos/`

4. **Write secure, correct code:**
   - No security vulnerabilities (XSS, SQL injection, command injection)
   - Async database operations in backend
   - No hardcoded secrets or credentials

5. **Track files changed:**
   ```python
   state = read_workflow_state()
   state['steps']['step3_implement']['filesChanged'].append('path/to/file')
   state['steps']['step3_implement']['completed'] = True
   state['steps']['step3_implement']['timestamp'] = datetime.now().isoformat()
   write_workflow_state(state)
   ```

**Completion criteria:**
- Code implements required functionality
- Follows all architecture patterns
- No obvious bugs or security issues

---

### Step 4: Run Targeted Tests

**Goal:** Verify implementation works by running the tests from Step 2.

**Required actions:**

1. **Use auto-verify skill's file-to-test mapping:**
   ```
   Skill("auto-verify")
   ```

   This skill:
   - Detects changed files
   - Maps them to relevant test files using `docs/feature-registry.yaml`
   - Runs appropriate test layers
   - Captures screenshots for E2E tests
   - Records results

2. **Hooks automatically:**
   - Record test results via `post_test_update.py`
   - Re-run tests independently via `verify_test_rerun.py` to verify claims
   - Update workflow state with pass/fail counts

3. **Expected outcomes:**
   - **All tests pass:** Proceed to Step 5 (fix-loop will be no-op)
   - **Some tests fail:** Step 5 (fix-loop) becomes mandatory

**Completion criteria:**
- Tests executed for all affected layers
- Results recorded in workflow state
- If pass: Step 4 marked complete, Step 5 auto-completed
- If fail: Step 5 iteration counter incremented, `/fix-loop` required

**Note:** You don't need to manually mark this step complete - hooks do it automatically.

---

### Step 5: Fix Loop (MANDATORY if tests failed)

**Goal:** Diagnose and fix all test failures iteratively.

**Required actions:**

1. **Invoke fix-loop skill:**
   ```
   Skill("fix-loop")
   ```

2. **What fix-loop does:**
   - Reads ranked strategies from `knowledge.db`
   - Launches debugger agent at attempt 2+ (with escalating thinking depth)
   - Every fix goes through code-reviewer agent for:
     - Broker abstraction compliance
     - Trading constants compliance
     - Folder structure compliance
     - Security checks
   - Records every attempt to knowledge.db
   - Updates strategy scores based on outcomes
   - **Budget:** 10 iterations, 3 attempts per issue, cascade depth 2

3. **Prohibited actions (enforced by fix-loop):**
   - Skip tests
   - Weaken assertions
   - Delete tests
   - Add `@pytest.mark.skip`

4. **If tests passed initially:**
   - Fix-loop is a no-op (skipped)
   - Step 5 auto-completed by hooks in Step 4

**Completion criteria:**
- All test failures resolved
- No prohibited actions taken
- Code reviewer approved all fixes

**Note:** Hooks enforce that fix-loop was invoked before allowing commit (if tests ever failed).

---

### Step 6: Visual Verification

**Goal:** Capture visual evidence of the feature working.

**Required actions:**

1. **For UI changes - Capture screenshots:**
   - Use Playwright MCP browser tools:
     ```
     mcp__playwright__browser_navigate(url="http://localhost:5173/feature-path")
     mcp__playwright__browser_take_screenshot(filename="feature-before.png", fullPage=true)

     # Interact with feature
     mcp__playwright__browser_click(ref="...", element="...")

     mcp__playwright__browser_take_screenshot(filename="feature-after.png", fullPage=true)
     ```

2. **For backend-only changes:**
   - Capture API response examples
   - Log database state changes
   - Document relevant metrics

3. **Hook auto-resizes large screenshots:**
   - `post_screenshot_resize.py` runs after screenshot capture
   - Resizes images > 1800px to prevent bloat

4. **Mark complete:**
   ```python
   state = read_workflow_state()
   state['steps']['step6_screenshots']['completed'] = True
   state['steps']['step6_screenshots']['timestamp'] = datetime.now().isoformat()
   write_workflow_state(state)
   ```

**Completion criteria:**
- Visual evidence captured
- Screenshots reasonably sized
- Evidence demonstrates feature working

---

### Step 7: Post-Fix Pipeline (MANDATORY)

**Goal:** Final verification, documentation update, and commit.

**Required actions:**

1. **Invoke post-fix-pipeline:**
   ```
   Skill("post-fix-pipeline")
   ```

2. **What post-fix-pipeline does:**
   - **Gate check:** Skip if no fixes applied
   - **Regression tests:** Re-run affected tests, auto-fix if fail (max 3 attempts)
   - **Test suite verification:** Full pytest + npm test, launch tester agent on failure
   - **Documentation:** Invoke docs-maintainer skill to update docs
   - **Git commit:** Delegate to git-manager agent (conventional commits, secret scanning)

3. **Hard blocks:**
   - Commit blocked if regression tests fail after max attempts
   - Commit blocked if full test suite fails after max attempts

**Completion criteria:**
- All tests pass (unit + E2E)
- Documentation updated
- Git commit created with conventional format
- Step 7 marked complete

**Note:** Hooks enforce that post-fix-pipeline was invoked before allowing any commit.

---

### Post-Workflow: Learning Reflection

**After Step 7 completes:**

```
Skill("reflect", args="session")
```

**What reflection does:**
- Captures outcomes to learning stores
- Updates knowledge.db with strategy success/failure
- Synthesizes new rules if patterns reach threshold (≥70% confidence, ≥5 instances)
- Does NOT modify files (session mode is read-only)

---

## Skills Called

This command orchestrates these existing skills:

| Skill | Step | Purpose |
|-------|------|---------|
| `auto-verify` | Step 4 | Run targeted tests with screenshot capture |
| `e2e-test-generator` | Step 2 | Generate Playwright tests |
| `vitest-generator` | Step 2 | Generate Vitest unit tests |
| `fix-loop` | Step 5 | Diagnose and fix test failures |
| `post-fix-pipeline` | Step 7 | Final verification and commit |
| `reflect` | Post | Learning reflection |
| `docs-maintainer` | Step 7 (via post-fix-pipeline) | Update documentation |

---

## Commands Called

| Command | When | Purpose |
|---------|------|---------|
| `/fix-loop` | Step 5 (via Skill) | Called if Step 4 tests fail |
| `/post-fix-pipeline` | Step 7 (via Skill) | Always called at end |
| `/reflect` | Post-workflow (via Skill) | Learning and synthesis |

---

## Enforcement Summary

**PreToolUse hooks block:**
- Write/Edit test files before Step 1 complete
- Write/Edit code files before Step 2 complete
- `git commit` before all 7 steps complete
- `git commit` without post-fix-pipeline invoked

**PostToolUse hooks:**
- Record test results automatically
- Independently re-run tests to verify claims
- Block false positives (claimed PASS, actual FAIL)
- Track skill invocations for commit gate

---

## Example Usage

```
User: "Add a delete button to the positions screen"

Claude: I understand you want to add a delete button to the positions screen.
This will affect the PositionsList component and positions API route.
Expected outcome: Users can delete individual positions with confirmation dialog.

[Step 1 completed]

Now writing E2E test...
Skill("e2e-test-generator", args="positions delete-button happy")

[Continue through all 7 steps...]
```

---

## Implementation Notes

**This skill orchestrates:**
1. Hook utilities (workflow state, logging)
2. knowledge.db queries (via db_helper.py)
3. Sub-skills (auto-verify, test generators, fix-loop, post-fix-pipeline)
4. Test execution (via auto-verify)
5. File modifications (via Edit/Write)

**Exit codes:**
- **0:** All 7 steps completed successfully, commit created
- **1:** Workflow failed (tests not passing, user cancelled, etc.)
