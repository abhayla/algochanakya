# Auto-Verify Quick Checklist

## Before Starting
- [ ] Clean screenshots older than 24 hours
- [ ] Ensure frontend running (localhost:5173)
- [ ] Ensure backend running (localhost:8000)

## Per Attempt
- [ ] Identify changed files
- [ ] Map to feature using feature-registry.yaml
- [ ] **Map to SPECIFIC test file(s)** (not whole feature)
- [ ] **Query knowledge base for known fixes** (Step 2c)
- [ ] Run targeted tests using priority order
- [ ] Capture screenshots
- [ ] Analyze test output
- [ ] Analyze screenshots visually
- [ ] Make decision: SUCCESS / FIX / STOP (check stuck conditions)
- [ ] **Record fix attempt to knowledge base** (Step 8)

## Approval Checks
Before proceeding, ask user if:
- [ ] Using mock/dummy data?
- [ ] Making behavior assumptions?
- [ ] Modifying test assertions?
- [ ] Modifying shared utilities?
- [ ] Using workaround instead of fix?
- [ ] **Hit stuck condition?** (Same error 3x, strategies exhausted, 20 attempts, unknown error)

## Success Criteria
- All related tests pass
- Screenshots show correct UI state
- No visual regressions
- No console errors
