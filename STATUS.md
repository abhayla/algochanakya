# T-386 Status Report

**Task:** Fix PR Gate's backend-test step missing allure-pytest dependency

**Status:** ✅ DONE

## What Was Done

1. **Identified the root cause:** `backend/tests/conftest.py` imports `allure` at line 15, but `.github/workflows/pr-gate.yml` at line 50 only installs `pytest pytest-asyncio httpx`, missing `allure-pytest`.

2. **Applied the fix:** Added `allure-pytest` to the pip install line in the "Set up Python deps (backend)" step of `.github/workflows/pr-gate.yml`.

3. **Pushed the fix:** Created and pushed branch `T-386-allure-pytest-dep` with commit:
   - `7c198d2 fix(ci): add allure-pytest to backend test dependencies`

4. **Created PR #99:** https://github.com/abhayla/algochanakya/pull/99
   - Title: `fix(ci): add allure-pytest to backend test dependencies`
   - PR Gate validation: ✅ SUCCESS

## Verification

- PR #99 CI Status: **PASSED**
  - "PR Gate — validate" check completed with **SUCCESS**
  - Workflow run #38 conclusion: **success**
  
- Expected outcome: PR #98 (T-385) can now re-run against this fix and get past the `ModuleNotFoundError: No module named 'allure'` collection failure that was blocking all backend PRs.

## Notes

- PR #99 only modifies the workflow file (not backend code), so the "Run backend tests" step itself did not execute on this PR. This is expected — the validation confirms the workflow syntax is correct and CI jobs execute.
- PR #98 will need to be re-run (via GitHub re-run workflow or new commit) to validate that it now passes the backend test collection step with `allure-pytest` available.
- The fix is narrowly scoped to the stated requirement: unblock the `ModuleNotFoundError: No module named 'allure'` collection failure.

## Files Changed

- `.github/workflows/pr-gate.yml` (+1 line: added `allure-pytest` to pip install)

All work is committed and pushed. No further action required from this worker.
