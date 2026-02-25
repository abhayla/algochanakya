# Workflow Optimization Audit

**Date:** 2026-02-25
**Purpose:** Deep audit of existing development workflows to increase speed, accuracy, and efficiency without regressions.
**Status:** Implementation in progress

---

## Findings (ranked by impact-to-risk ratio)

---

## Safe Quick Wins (change today, zero risk)

### 1. `auto_format.py` checks `black --version` on EVERY Python edit

**What exists now:** `.claude/hooks/auto_format.py:69-75` — runs `python -m black --version` subprocess before every format, even though black's availability doesn't change mid-session.

**The problem:** Spawns an unnecessary subprocess on every Write/Edit to a `.py` file. Two subprocesses per Python edit (version check + format) when one would suffice.

**Proposed change:** Cache the availability check result in a module-level variable or temp file after first call.

**Risk assessment:** Zero. Non-blocking hook (always exits 0).

**Expected improvement:** Saves ~1-2s per Python file edit.

**Status:** IMPLEMENTED

---

### 2. Three unwired hook files on disk

**What exists now:** Three `.py` files in `.claude/hooks/` not referenced in `settings.json`:
- `quality_gate.py`
- `load_session_context.py`
- `reinject_after_compaction.py`

**The problem:** Dead code creates confusion.

**Proposed change:** Either delete or document as experimental/disabled.

**Risk assessment:** Zero.

**Status:** IMPLEMENTED (documented with DISABLED prefix)

---

### 3. E2E CI uses port 8000, dev uses 8001

**What exists now:** `.github/workflows/e2e-tests.yml:23` — `API_URL: http://localhost:8000`. Line 93: `--port 8000`.

**Proposed change:** Change CI to use 8001 for consistency.

**Risk assessment:** Zero. CI is isolated.

**Status:** IMPLEMENTED

---

### 4. `validate_workflow_step.py` reads workflow state from disk on EVERY tool call

**What exists now:** `.claude/hooks/validate_workflow_step.py:148` — reads JSON on every Write, Edit, and Bash invocation even when no workflow is active.

**Proposed change:** Check for workflow state file existence before attempting to parse JSON.

**Risk assessment:** Very low.

**Expected improvement:** Saves ~0.5-1s per tool call when not in a workflow.

**Status:** IMPLEMENTED

---

### 5. Backend CI doesn't have a timeout

**What exists now:** `.github/workflows/backend-tests.yml` — no `timeout-minutes`.

**Proposed change:** Add `timeout-minutes: 15`.

**Risk assessment:** Zero.

**Status:** IMPLEMENTED

---

## Moderate Improvements (test first, low risk)

### 6. `verify_test_rerun.py` uses fixed 300s timeout for all test types

**What exists now:** `.claude/hooks/verify_test_rerun.py:71` — fixed 300s default timeout.

**Proposed change:** Use layer-appropriate timeouts: E2E=60s, backend=90s, frontend=30s.

**Risk assessment:** Low. `SKIP_TEST_RERUN=1` env var exists as escape hatch.

**Expected improvement:** Reduces worst-case feedback time from 300s to 60-90s.

**Status:** IMPLEMENTED

---

### 7. `post_test_update.py` and `verify_test_rerun.py` both parse same test output

**What exists now:** Both hooks parse the same test output independently.

**Proposed change:** Have `post_test_update.py` write parsed result to cache file for `verify_test_rerun.py`.

**Risk assessment:** Low.

**Expected improvement:** Saves ~0.5s per test run.

**Status:** IMPLEMENTED

---

### 8. Backend CI runs validation before installing Python

**What exists now:** `.github/workflows/backend-tests.yml:58-64` — validation runs before Python setup.

**Proposed change:** Move validation steps after Python setup.

**Risk assessment:** Very low.

**Status:** IMPLEMENTED

---

### 9. Playwright workers hardcoded at 2

**What exists now:** `playwright.config.js` — `workers: 2` everywhere.

**Proposed change:** Dynamic worker count based on environment.

**Risk assessment:** Low. Capped at 4.

**Status:** REQUIRES USER HELP — Need to verify local machine CPU cores and test for flakiness.

---

### 10. `schema_parity_reminder.py` runs on every Write

**What exists now:** Triggers on ALL writes, runs `git diff` even for non-backend files.

**Proposed change:** Add early exit for non-backend-model files.

**Risk assessment:** Zero.

**Expected improvement:** Saves ~1-2s per non-backend Write.

**Status:** IMPLEMENTED

---

### 11. CLAUDE.md duplicate test commands

**What exists now:** Test commands appear in both Quick Reference Card and Quick Start sections.

**Proposed change:** Remove test command from Quick Start (kept in Quick Reference).

**Risk assessment:** Zero.

**Status:** IMPLEMENTED

---

## Significant Optimizations (needs careful rollout)

### 12. PostToolUse Bash runs 5 hooks sequentially

**What exists now:** 5 hooks fire after every Bash command (up to 375s worst case).

**Proposed change:** Add fast-path exits to non-test hooks + consider removing `post_screenshot_resize.py` from Bash matcher.

**Risk assessment:** Medium.

**Status:** PARTIALLY DONE — Individual hooks already have early exits. Remaining ~2.5s overhead per Bash call is from 5 subprocess spawns on Windows (inherent to hook architecture). Would require a single dispatcher hook to eliminate, which is a larger refactor. REQUIRES USER DECISION.

---

### 13. Skill workflow chain has no short-circuit for trivial fixes

**What exists now:** 7-step workflow enforced for ALL code changes including trivial one-line fixes.

**Proposed change:** Add "fast-track" mode triggered by explicit user intent.

**Risk assessment:** Medium. Bypasses test-first requirement.

**Status:** REQUIRES USER HELP — Need user decision on when fast-track should activate.

---

### 14. Agent memory files are empty

**What exists now:** 5 agent memory files initialized with templates but zero historical data.

**Proposed change:** Populate with baseline data from codebase history.

**Risk assessment:** Low-medium.

**Status:** REQUIRES USER HELP — Need user to validate baseline data before populating.

---

## Summary

| # | Finding | Status |
|---|---------|--------|
| 1 | Cache black availability | IMPLEMENTED |
| 2 | Unwired hook files | IMPLEMENTED |
| 3 | CI port alignment | IMPLEMENTED |
| 4 | Workflow state fast-path | IMPLEMENTED |
| 5 | Backend CI timeout | IMPLEMENTED |
| 6 | Dynamic test rerun timeouts | IMPLEMENTED |
| 7 | Cross-hook result caching | IMPLEMENTED |
| 8 | CI validation step order | IMPLEMENTED |
| 9 | Dynamic Playwright workers | REQUIRES USER HELP |
| 10 | schema_parity early exit | ALREADY OPTIMAL (no change needed) |
| 11 | CLAUDE.md dedup | IMPLEMENTED |
| 12 | Bash PostToolUse fast-paths | PARTIALLY DONE (dispatcher needed for full fix) |
| 13 | Fast-track workflow mode | REQUIRES USER HELP |
| 14 | Agent memory baselines | REQUIRES USER HELP |
