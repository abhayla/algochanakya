# Auto-Verify Quick Checklist

## Before Starting
- [ ] Clean screenshots older than 24 hours
- [ ] Ensure frontend running (localhost:5173)
- [ ] Ensure backend running (localhost:8000)

## Per Attempt
- [ ] Identify changed files
- [ ] Map to feature using feature-registry.yaml
- [ ] Run appropriate tests
- [ ] Capture screenshots
- [ ] Analyze test output
- [ ] Analyze screenshots visually
- [ ] Make decision: SUCCESS / FIX / STOP

## Approval Checks
Before proceeding, ask user if:
- [ ] Using mock/dummy data?
- [ ] Making behavior assumptions?
- [ ] Modifying test assertions?
- [ ] Modifying shared utilities?
- [ ] Using workaround instead of fix?
- [ ] Reached 5 attempts?

## Success Criteria
- All related tests pass
- Screenshots show correct UI state
- No visual regressions
- No console errors
