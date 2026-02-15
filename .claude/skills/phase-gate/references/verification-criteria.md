# Phase Gate Verification Criteria

This document provides detailed criteria for each of the 6 verification checks used by the phase-gate skill.

---

## 1. Requirements Documented (Step 1)

**Checks:**
- Workflow state shows `step1_requirements.completed = true`
- Evidence of understanding stated (2-3 sentences in conversation)
- Evidence of codebase research (Grep/Glob/Read tool usage)
- Evidence of documentation checks (CLAUDE.md, docs/ references)

**PASS if:** All 4 checks satisfied
**FAIL if:** Any check missing

**Verification Method:**
1. Read `.claude/workflow-state.json`
2. Check `step1_requirements.completed` field
3. Scan conversation history for understanding statements
4. Scan tool usage for Grep/Glob/Read calls
5. Scan tool usage for documentation reads

**Common Failures:**
- Implementing without understanding requirements first
- No evidence of architectural research
- Skipped documentation review

---

## 2. Tests Written (Step 2)

**Checks:**
- Workflow state shows `step2_tests.completed = true`
- Test files listed in `step2_tests.testFiles` array
- Test layers identified in `step2_tests.testLayers` array
- Test files exist on disk (verify with Glob/Read)

**PASS if:** All 4 checks satisfied
**FAIL if:** Any check missing

**Verification Method:**
1. Read `.claude/workflow-state.json`
2. Check `step2_tests.completed` and `testFiles` array
3. Use Glob to verify each test file exists
4. Verify test layers array is not empty

**Common Failures:**
- Tests not written before implementation (violates TDD)
- Test files listed but don't exist on disk
- Test layers not properly identified

---

## 3. Implementation Done (Step 3)

**Checks:**
- Workflow state shows `step3_implement.completed = true`
- Files changed listed in `step3_implement.filesChanged` array
- Changed files exist on disk (verify with Glob)
- Code follows architectural rules (.claude/rules.md compliance)

**PASS if:** All 4 checks satisfied
**FAIL if:** Any check missing

**Verification Method:**
1. Read `.claude/workflow-state.json`
2. Check `step3_implement.completed` and `filesChanged` array
3. Use Glob to verify each changed file exists
4. Read `.claude/rules.md` and verify compliance (manual check)

**Common Failures:**
- Implementation marked complete but files not changed
- Files listed but don't exist (typos in paths)
- Violated architectural rules (hardcoded constants, wrong folder structure)

---

## 4. Tests Pass (Step 4)

**Checks:**
- Workflow state shows `step4_runTests.completed = true`
- Test layers show passed counts (e2e/backend/frontend)
- No failed tests in any layer
- Test execution evidence exists (.claude/logs/ or conversation)

**PASS if:** All 4 checks satisfied
**FAIL if:** Any failed tests or missing execution evidence

**Verification Method:**
1. Read `.claude/workflow-state.json`
2. Check `step4_runTests.completed` and test layer results
3. Verify `failed` count is 0 for all layers
4. Check `.claude/logs/` for test execution logs OR conversation history for test output

**Common Failures:**
- Tests marked as passing but failures exist
- No evidence of test execution (just assumed they pass)
- Partial test runs (only ran one layer)

---

## 5. Fix Loop Resolved (Step 5 - conditional)

**Checks:**
- **If failures occurred:** `step5_fixLoop.completed = true` AND `skillInvocations.fixLoopSucceeded = true`
- **If no failures:** Step 5 skipped (PASS automatically)

**PASS if:** No failures OR fix loop succeeded
**FAIL if:** Failures occurred but not resolved

**Verification Method:**
1. Read `.claude/workflow-state.json`
2. Check if `step4_runTests` had any failures
3. If failures: Check `step5_fixLoop.completed` and `skillInvocations.fixLoopSucceeded`
4. If no failures: PASS automatically

**Common Failures:**
- Failures occurred but fix loop not invoked
- Fix loop invoked but didn't succeed
- Fix loop marked complete but failures remain

---

## 6. Evidence Captured (Step 6)

**Checks:**
- Screenshots captured (for E2E changes)
- Test evidence files exist (.claude/logs/evidence/)
- Visual verification complete (for UI changes)
- Evidence referenced in workflow state

**PASS if:** Evidence captured OR not required (backend-only changes)
**FAIL if:** E2E/UI changes without visual evidence

**Verification Method:**
1. Read `.claude/workflow-state.json`
2. Check `step6_evidence` field for screenshot paths
3. Use Glob to verify screenshots exist in `.claude/logs/evidence/`
4. Determine if evidence is required (E2E or UI changes)

**Common Failures:**
- UI changes without screenshots
- Screenshots referenced but files don't exist
- Evidence directory not created
- Backend-only changes incorrectly flagged as needing evidence

---

## Overall Status Logic

**PASS:** All 6 criteria (or applicable subset) meet their PASS conditions
**FAIL:** ANY criterion fails its checks

**Note:** Criteria 5 and 6 are conditional:
- Criterion 5 only applies if Step 4 had failures
- Criterion 6 only applies if E2E or UI changes were made

## Workflow State Structure Reference

```json
{
  "workflow": "/implement",
  "sessionId": "20260215-143000",
  "step1_requirements": {
    "completed": true,
    "understanding": "Brief description...",
    "docsChecked": ["CLAUDE.md", "docs/architecture/..."]
  },
  "step2_tests": {
    "completed": true,
    "testFiles": ["tests/e2e/specs/positions/..."],
    "testLayers": ["e2e"]
  },
  "step3_implement": {
    "completed": true,
    "filesChanged": ["backend/app/api/routes/positions.py", ...]
  },
  "step4_runTests": {
    "completed": true,
    "e2e": { "total": 5, "passed": 5, "failed": 0 },
    "backend": { "total": 10, "passed": 10, "failed": 0 },
    "frontend": { "total": 8, "passed": 8, "failed": 0 }
  },
  "step5_fixLoop": {
    "completed": false,
    "skipped": true,
    "reason": "No failures in Step 4"
  },
  "step6_evidence": {
    "screenshots": [".claude/logs/evidence/positions-exit-modal.png"],
    "visualVerified": true
  },
  "skillInvocations": {
    "autoVerifyUsed": true,
    "fixLoopSucceeded": null
  }
}
```
