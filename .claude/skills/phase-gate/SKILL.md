---
name: phase-gate
description: Verify phase/step completion before proceeding to next workflow stage. Use when running /implement, multi-step features, or any phased workflow to ensure all 6 criteria are met before advancing. Triggers on 'check phase', 'verify step', or 'gate check'.
metadata:
  author: AlgoChanakya
  version: "1.0"
---

# Phase Gate Verification

## When to Use
- Before moving to next workflow phase/step
- User invokes /phase-gate
- After completing a workflow step to verify completion criteria
- Before creating a commit to ensure all requirements met

## When NOT to Use

- For standalone bug fixes outside /implement workflow
- When not using a phased/multi-step workflow

## Purpose

Verifies that the current workflow phase/step meets completion criteria with 6 standardized checks. Acts as a quality gate to prevent premature progression.

## Verification Criteria

The phase gate verifies 6 standardized criteria:

1. **Requirements Documented** - Understanding stated, codebase researched, docs checked
2. **Tests Written** - Test files exist, layers identified, TDD followed
3. **Implementation Done** - Files changed, exist on disk, follow architectural rules
4. **Tests Pass** - All layers passing, no failures, execution evidence exists
5. **Fix Loop Resolved** (conditional) - Failures fixed OR no failures occurred
6. **Evidence Captured** (conditional) - Screenshots for E2E/UI changes

**Detailed checks and verification methods:** See [references/verification-criteria.md](./references/verification-criteria.md)

---

## Workflow

### Step 1: Read Workflow State
```python
import json
from pathlib import Path

state_file = Path('.claude/workflow-state.json')
if state_file.exists():
    with open(state_file) as f:
        state = json.load(f)
else:
    print("❌ FAIL: No active workflow found")
    exit()
```

### Step 2: Run All 6 Checks
For each criterion (1-6):
- Extract relevant state data
- Verify conditions
- Record PASS/FAIL status
- Collect failure reasons

### Step 3: Generate Report
Output format:
```markdown
# Phase Gate Verification

**Workflow:** /{active_command}
**Session ID:** {session_id}
**Timestamp:** {timestamp}

---

## Verification Results

| Criterion | Status | Details |
|-----------|--------|---------|
| 1. Requirements Documented | ✅ PASS | All 4 checks satisfied |
| 2. Tests Written | ✅ PASS | 3 test files, 2 layers |
| 3. Implementation Done | ✅ PASS | 5 files changed |
| 4. Tests Pass | ❌ FAIL | 2 E2E tests failed |
| 5. Fix Loop Resolved | ⏭️ SKIP | No failures |
| 6. Evidence Captured | ✅ PASS | 3 screenshots captured |

---

## Overall Status: ❌ FAIL

**Blocking Issues:**
- Tests failing: 2 E2E tests need fixing

**Required Actions:**
1. Run /fix-loop to resolve test failures
2. Re-run /phase-gate after fixes

---

## Details

### Tests Pass (FAIL)
**Failed tests:**
- tests/e2e/specs/positions/exit-flow.spec.js
- tests/e2e/specs/dashboard/pnl-display.spec.js

**Evidence:**
- Last test run: {timestamp}
- Test layer: e2e
- Failure mode: selector_not_found
```

### Step 4: Provide Guidance
**If PASS:**
- Congratulate on meeting criteria
- Suggest next step (commit, move to next phase)
- Remind to invoke /post-fix-pipeline if not done

**If FAIL:**
- List blocking issues
- Provide clear action items
- Suggest relevant skills (/fix-loop, /run-tests, etc.)

---

## Implementation Notes

### Criterion Weights
All criteria have equal weight (no partial credit). A single FAIL blocks the entire phase gate.

### Conditional Criteria
- Criterion 5 (Fix Loop) only applies if Step 4 failed at least once
- Criterion 6 (Evidence) only applies if E2E or UI changes made

### Workflow State Dependencies
Relies on accurate workflow-state.json. If state is corrupted or missing, phase gate cannot verify.

### Integration Points
- Used by /post-fix-pipeline before commit
- Used manually by developers to self-check
- Can be invoked multiple times (idempotent)

---

## Example Usage

### Scenario 1: All Criteria Met
```
User: /phase-gate

# Phase Gate Verification
**Workflow:** /implement
**Session ID:** 20260214-153000

## Verification Results
| Criterion | Status | Details |
|-----------|--------|---------|
| 1. Requirements Documented | ✅ PASS | All checks satisfied |
| 2. Tests Written | ✅ PASS | 2 test files (E2E, backend) |
| 3. Implementation Done | ✅ PASS | 3 files changed |
| 4. Tests Pass | ✅ PASS | All tests passing |
| 5. Fix Loop Resolved | ⏭️ SKIP | No failures |
| 6. Evidence Captured | ✅ PASS | 2 screenshots |

## Overall Status: ✅ PASS

Ready to commit! Run /post-fix-pipeline to complete workflow.
```

### Scenario 2: Missing Tests
```
User: /phase-gate

# Phase Gate Verification
**Workflow:** /implement

## Verification Results
| Criterion | Status | Details |
|-----------|--------|---------|
| 1. Requirements Documented | ✅ PASS | All checks satisfied |
| 2. Tests Written | ❌ FAIL | No test files found |
| ... (remaining checks skipped) ...

## Overall Status: ❌ FAIL

**Blocking Issues:**
- No tests written (required by Step 2)

**Required Actions:**
1. Write tests before implementing code
2. Follow test-driven development workflow

Use /e2e-test-generator or /vitest-generator to create tests.
```

---

## Self-Improvement

After each invocation, consider:
- Were the criteria clear and unambiguous?
- Did the report help the user understand what's missing?
- Were the suggested actions helpful?
- Any false positives/negatives in verification?

Document learnings below for future improvements.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Workflow state file not found | `.claude/workflow-state.json` doesn't exist | No active workflow - only use phase-gate during `/implement` or similar workflows |
| Criteria always passing | Not reading actual workflow state | Verify reading from `.claude/workflow-state.json`, not assuming values |
| Evidence check failing for backend | Incorrectly requiring screenshots for non-UI | Check if `filesChanged` contains only backend files (no `.vue` files) |
| Fix loop check failing | `fixLoopSucceeded` not updated | Ensure `/fix-loop` skill updates workflow state on success |

---

## References

- [Verification Criteria](./references/verification-criteria.md) - Detailed checks, verification methods, common failures

---

## Learnings Log

2026-02-14: Phase gate skill initialized
