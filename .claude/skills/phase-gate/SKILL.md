---
name: phase-gate
description: Verify phase/step completion before proceeding. Usage: /phase-gate
---

# Phase Gate Verification

## When to Use
- Before moving to next workflow phase/step
- User invokes /phase-gate
- After completing a workflow step to verify completion criteria
- Before creating a commit to ensure all requirements met

## Purpose

Verifies that the current workflow phase/step meets completion criteria with 6 standardized checks. Acts as a quality gate to prevent premature progression.

## Verification Criteria

### 1. Requirements Documented (Step 1)
**Checks:**
- Workflow state shows `step1_requirements.completed = true`
- Evidence of understanding stated (2-3 sentences in conversation)
- Evidence of codebase research (Grep/Glob/Read tool usage)
- Evidence of documentation checks (CLAUDE.md, docs/ references)

**PASS if:** All 4 checks satisfied
**FAIL if:** Any check missing

---

### 2. Tests Written (Step 2)
**Checks:**
- Workflow state shows `step2_tests.completed = true`
- Test files listed in `step2_tests.testFiles` array
- Test layers identified in `step2_tests.testLayers` array
- Test files exist on disk (verify with Glob/Read)

**PASS if:** All 4 checks satisfied
**FAIL if:** Any check missing

---

### 3. Implementation Done (Step 3)
**Checks:**
- Workflow state shows `step3_implement.completed = true`
- Files changed listed in `step3_implement.filesChanged` array
- Changed files exist on disk (verify with Glob)
- Code follows architectural rules (.claude/rules.md compliance)

**PASS if:** All 4 checks satisfied
**FAIL if:** Any check missing

---

### 4. Tests Pass (Step 4)
**Checks:**
- Workflow state shows `step4_runTests.completed = true`
- Test layers show passed counts (e2e/backend/frontend)
- No failed tests in any layer
- Test execution evidence exists (.claude/logs/ or conversation)

**PASS if:** All 4 checks satisfied
**FAIL if:** Any failed tests or missing execution evidence

---

### 5. Fix Loop Resolved (Step 5 - conditional)
**Checks:**
- **If failures occurred:** `step5_fixLoop.completed = true` AND `skillInvocations.fixLoopSucceeded = true`
- **If no failures:** Step 5 skipped (PASS automatically)

**PASS if:** No failures OR fix loop succeeded
**FAIL if:** Failures occurred but not resolved

---

### 6. Evidence Captured (Step 6)
**Checks:**
- Screenshots captured (for E2E changes)
- Test evidence files exist (.claude/logs/evidence/)
- Visual verification complete (for UI changes)
- Evidence referenced in workflow state

**PASS if:** Evidence captured OR not required (backend-only changes)
**FAIL if:** E2E/UI changes without visual evidence

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

## Learnings Log

2026-02-14: Phase gate skill initialized
