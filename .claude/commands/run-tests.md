# /run-tests - Multi-Layer Test Runner

**Purpose:** Execute tests across all 3 layers (E2E, backend, frontend) with auto-fix on failure.

**When to use:** Manual test execution, CI/CD validation, pre-commit verification.

**Integration:** Invokes `/fix-loop` on failures, `/post-fix-pipeline` if fixes applied, `/reflect` at end.

---

## Argument Parsing

**Syntax:**
```
/run-tests [layer][:screen|module]
```

**Examples:**
```bash
/run-tests                    # All layers sequentially
/run-tests e2e                # All E2E tests
/run-tests e2e:positions      # Positions screen E2E tests only
/run-tests backend            # All backend tests
/run-tests backend:autopilot  # Autopilot module tests only
/run-tests frontend           # All frontend tests
```

**Mapping:**
- `e2e` → `npm test`
- `e2e:positions` → `npm run test:specs:positions`
- `e2e:autopilot` → `npm run test:specs:autopilot`
- `backend` → `pytest tests/ -v`
- `backend:autopilot` → `pytest backend/tests/autopilot/ -v`
- `frontend` → `npm run test:run`

---

## Algorithm

### All Layers (No Arguments)

```
1. Run backend tests (pytest)
   → If fail: /fix-loop (budget=1) → retry
2. Run frontend tests (vitest)
   → If fail: /fix-loop (budget=1) → retry
3. Run E2E tests (playwright)
   → If fail: /fix-loop (budget=1) → retry
4. If any fixes applied: /post-fix-pipeline
5. /reflect session
```

---

### E2E Tests (Per-Screen Strategy)

**Run specs one at a time to isolate failures:**

```python
screens = [
    'login', 'dashboard', 'watchlist', 'positions',
    'optionchain', 'strategy', 'strategylibrary',
    'autopilot', 'ofo', 'navigation', 'audit'
]

for screen in screens:
    print(f"\n{'='*60}")
    print(f"Running {screen} E2E tests...")
    print(f"{'='*60}\n")

    # Get all specs for this screen
    specs = glob(f"tests/e2e/specs/{screen}/*.spec.js")

    for spec in specs:
        print(f"\n📝 Running {spec}...")

        # Run single spec
        result = Bash(
            command=f"npx playwright test {spec}",
            timeout=180000  # 3 minutes per spec
        )

        # Check result (hooks record automatically)
        if "failed" in result.lower():
            print(f"❌ {spec} failed")

            # Attempt fix (budget=1, single iteration)
            print(f"🔧 Attempting fix with /fix-loop (budget=1)...")
            fix_result = Skill("fix-loop")

            if "RESOLVED" in fix_result or "PASSED" in fix_result:
                print(f"✅ Fix successful, restarting {screen} screen")
                break  # Restart this screen from first spec
            else:
                print(f"⚠️  Fix failed, continuing to next spec")
                failed_specs.append(spec)

                # Check failure limit
                if len(failed_specs) >= 10:
                    print(f"\n🚫 10 failures reached, stopping E2E tests")
                    break

        else:
            print(f"✅ {spec} passed")
```

**10-failure limit:** Stop if 10 specs fail across all screens (prevents cascading failures).

**Per-screen restart:** If a fix succeeds, restart that screen from the first spec (fix may have affected multiple tests).

---

### Backend Tests (Per-Module Strategy)

```python
modules = [
    'autopilot', 'brokers', 'options', 'ai',
    'routes', 'models', 'services'
]

for module in modules:
    module_path = f"backend/tests/{module}/"
    if not os.path.exists(module_path):
        continue

    print(f"\n{'='*60}")
    print(f"Running {module} backend tests...")
    print(f"{'='*60}\n")

    result = Bash(
        command=f"pytest {module_path} -v",
        timeout=120000  # 2 minutes per module
    )

    # Check result
    if "failed" in result.lower():
        print(f"❌ {module} tests failed")

        # Attempt fix (budget=1)
        print(f"🔧 Attempting fix with /fix-loop (budget=1)...")
        fix_result = Skill("fix-loop")

        if "RESOLVED" in fix_result or "PASSED" in fix_result:
            print(f"✅ Fix successful, re-running {module} tests")

            # Re-run module tests
            rerun_result = Bash(
                command=f"pytest {module_path} -v",
                timeout=120000
            )

            if "failed" in rerun_result.lower():
                print(f"⚠️  {module} still failing after fix")
                failed_modules.append(module)
            else:
                print(f"✅ {module} tests now passing")
        else:
            print(f"⚠️  Fix failed for {module}")
            failed_modules.append(module)

    else:
        print(f"✅ {module} tests passed")
```

---

### Frontend Tests (Single Run)

```python
print(f"\n{'='*60}")
print("Running frontend tests (Vitest)...")
print(f"{'='*60}\n")

result = Bash(
    command="npm run test:run",
    timeout=60000  # 1 minute (Vitest is fast)
)

# Check result
if "failed" in result.lower():
    print("❌ Frontend tests failed")

    # Attempt fix (budget=1)
    print("🔧 Attempting fix with /fix-loop (budget=1)...")
    fix_result = Skill("fix-loop")

    if "RESOLVED" in fix_result or "PASSED" in fix_result:
        print("✅ Fix successful, re-running frontend tests")

        # Re-run frontend tests
        rerun_result = Bash(
            command="npm run test:run",
            timeout=60000
        )

        if "failed" in rerun_result.lower():
            print("⚠️  Frontend tests still failing after fix")
        else:
            print("✅ Frontend tests now passing")
    else:
        print("⚠️  Fix failed for frontend tests")

else:
    print("✅ Frontend tests passed")
```

---

## Post-Run Actions

### If Fixes Applied

```python
# Check workflow state
state = read_workflow_state()
fix_iterations = state['steps']['step5_fixLoop']['iterations']

if fix_iterations > 0:
    print("\n" + "="*60)
    print("Fixes were applied. Running post-fix verification...")
    print("="*60 + "\n")

    # Invoke post-fix-pipeline
    Skill("post-fix-pipeline")
```

### Learning Reflection

```python
# Always run reflection at end
print("\n" + "="*60)
print("Running learning reflection...")
print("="*60 + "\n")

Skill("reflect", args="session")
```

---

## Output Format

### Summary Report

```
╔══════════════════════════════════════════════════════════╗
║               Test Run Summary                           ║
╚══════════════════════════════════════════════════════════╝

Layers Run: E2E, Backend, Frontend
Duration: 12m 34s

┌──────────────────────────────────────────────────────────┐
│ E2E Tests (Playwright)                                   │
├──────────────────────────────────────────────────────────┤
│ Passed:  115                                             │
│ Failed:    3                                             │
│ Skipped:   0                                             │
│ Duration: 8m 23s                                         │
│                                                          │
│ Failed specs:                                            │
│   - tests/e2e/specs/positions/positions.happy.spec.js    │
│   - tests/e2e/specs/autopilot/autopilot.edge.spec.js     │
│   - tests/e2e/specs/optionchain/optionchain.api.spec.js  │
│                                                          │
│ Fix attempts: 3                                          │
│ Fixes resolved: 1 (positions)                            │
│ Remaining failures: 2                                    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Backend Tests (pytest)                                   │
├──────────────────────────────────────────────────────────┤
│ Passed:   43                                             │
│ Failed:    2                                             │
│ Skipped:   0                                             │
│ Duration: 2m 12s                                         │
│                                                          │
│ Failed tests:                                            │
│   - test_kill_switch.py::test_emergency_exit             │
│   - test_order_executor.py::test_place_order             │
│                                                          │
│ Fix attempts: 2                                          │
│ Fixes resolved: 0                                        │
│ Remaining failures: 2                                    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Frontend Tests (Vitest)                                  │
├──────────────────────────────────────────────────────────┤
│ Passed:   21                                             │
│ Failed:    0                                             │
│ Skipped:   0                                             │
│ Duration: 1m 59s                                         │
│                                                          │
│ All frontend tests passed ✅                             │
└──────────────────────────────────────────────────────────┘

╔══════════════════════════════════════════════════════════╗
║ Overall Result: FAILED (4 remaining failures)            ║
╚══════════════════════════════════════════════════════════╝

Next steps:
1. Review failures:
   - E2E: 2 failures (autopilot, optionchain)
   - Backend: 2 failures (kill_switch, order_executor)

2. Manual investigation recommended (auto-fix exhausted)

3. Use /fix-issue to target specific failures:
   /fix-issue autopilot.edge.spec.js
```

---

## Integration with Knowledge System

**Record outcomes to failure-index.json:**

```python
for failed_spec in failed_specs:
    screen = extract_screen_from_path(failed_spec)  # e.g., "positions"
    error_type = detect_error_type(failed_spec)  # e.g., "selector_not_found"

    update_failure_index(
        skill="run-tests",
        issue_type=error_type,
        component=screen,
        outcome="FAILED",  # Not resolved
        workaround_used=None
    )
```

**Log to workflow-sessions.log:**

```python
log_event(
    'test_run_complete',
    layers=['e2e', 'backend', 'frontend'],
    total_passed=179,
    total_failed=4,
    fixes_applied=5,
    fixes_resolved=1,
    duration_seconds=754
)
```

---

## Budget Limits

**Per-spec fix budget:** 1 iteration (single /fix-loop call)

**Rationale:** Prevents spending too much time on single failure. If auto-fix fails, move to next test and aggregate failures for manual review.

**10-failure limit:** Stop after 10 E2E spec failures across all screens.

**Rationale:** Cascading failures indicate systemic issue (backend down, auth broken, etc.). Stop and investigate root cause instead of running all tests.

---

## Skills Called

| Skill | When | Purpose |
|-------|------|---------|
| `fix-loop` | Per-test/module failure | Auto-fix with budget=1 |
| `post-fix-pipeline` | If fixes applied | Final verification and commit |
| `reflect` | Always at end | Learning reflection |

---

## Example Usage

```bash
# All layers
/run-tests

# Specific layer
/run-tests e2e
/run-tests backend

# Specific screen/module
/run-tests e2e:positions
/run-tests backend:autopilot
```

---

## Success Criteria

✅ Tests execute for specified layer(s)
✅ Failures trigger auto-fix (budget=1)
✅ Summary report shows pass/fail counts
✅ If fixes applied, post-fix-pipeline runs
✅ Learning reflection runs at end
✅ Outcome recorded in workflow logs

---

## Exit Codes

- **0:** All tests passed (or all failures fixed)
- **1:** Some tests failed (after auto-fix attempts)
