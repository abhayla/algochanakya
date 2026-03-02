---
name: post-fix-pipeline
description: Final verification pipeline that runs after fixes are applied. Ensures regression tests pass, full test suite passes, docs are updated, and creates a safe commit. Hard blocks commit if tests fail. Use after fixes are applied, automatically invoked by implement Step 7, or standalone after any bug fix.
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: workflow
---

# post-fix-pipeline - Verification + Commit

**Purpose:** Final verification pipeline that runs after fixes are applied. Ensures regression tests pass, full test suite passes, docs are updated, and creates a safe commit.

**When to use:** Automatically invoked by `/implement` Step 7. Can be invoked standalone after any bug fix.

**Enforcement:** Hooks require this to be invoked before allowing `git commit`.

---

## Overview

The post-fix-pipeline implements a comprehensive verification workflow:
1. **Gate check:** Skip if no fixes applied (optimize for no-op case)
2. **Regression tests:** Re-run affected tests, auto-fix if fail (max 3 attempts)
3. **Test suite verification:** Run full test suites (pytest + npm test)
4. **Documentation:** Invoke docs-maintainer skill
5. **Git commit:** Delegate to git-manager agent with safety checks

**Hard blocks:**
- Commit blocked if regression tests fail after max attempts
- Commit blocked if full test suite fails after max attempts

---

## Step-by-Step Process

### Step 1: Gate Check

**Purpose:** Skip pipeline if no fixes were applied (tests passed initially).

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(".claude/hooks")))
from hook_utils import read_workflow_state

state = read_workflow_state()
fix_iterations = state['steps']['step5_fixLoop']['iterations']

if fix_iterations == 0:
    print("✅ No fixes applied (tests passed on first run). Skipping pipeline.")
    # Mark step complete and exit
    state['steps']['step7_verify']['completed'] = True
    write_workflow_state(state)
    exit(0)
```

**Continue if:** `fix_iterations > 0` (fixes were applied)

---

### Step 2: Regression Tests

**Purpose:** Verify that fixes didn't break previously passing tests.

#### 2.1 Identify Affected Tests

Use `docs/feature-registry.yaml` to map changed files to test files:

```python
import yaml
from pathlib import Path

registry_path = Path("docs/feature-registry.yaml")
with open(registry_path) as f:
    registry = yaml.safe_load(f)

changed_files = state['steps']['step3_implement']['filesChanged']
affected_tests = set()

for file in changed_files:
    # Find features that include this file
    for feature_name, feature_data in registry['features'].items():
        if file in feature_data.get('files', []):
            # Add test files for this feature
            affected_tests.update(feature_data.get('tests', []))

# Also add tests written in Step 2
affected_tests.update(state['steps']['step2_tests']['testFiles'])
```

#### 2.2 Run Regression Tests

Run each affected test with independent verification:

```python
MAX_REGRESSION_ATTEMPTS = 3

for test_file in affected_tests:
    attempt = 0
    test_passed = False

    while attempt < MAX_REGRESSION_ATTEMPTS and not test_passed:
        attempt += 1

        # Determine test command based on file type
        if test_file.endswith('.spec.js') or test_file.endswith('.spec.ts'):
            # Playwright E2E test
            command = f"npx playwright test {test_file}"
            layer = "e2e"
        elif test_file.startswith('backend/tests/') and test_file.endswith('.py'):
            # pytest backend test
            command = f"pytest {test_file} -v"
            layer = "backend"
        elif test_file.endswith('.test.js') or test_file.endswith('.spec.js'):
            # Vitest frontend test
            command = f"vitest run {test_file}"
            layer = "frontend"
        else:
            continue  # Unknown test type

        # Run test
        result = Bash(command=command, timeout=120000)

        # Parse result (hooks will also verify independently)
        from hook_utils import detect_test_result
        test_result, passed, failed = detect_test_result(result, layer)

        if test_result == 'pass':
            test_passed = True
            print(f"✅ Regression test passed: {test_file}")
        else:
            print(f"❌ Regression test failed (attempt {attempt}/{MAX_REGRESSION_ATTEMPTS}): {test_file}")

            if attempt < MAX_REGRESSION_ATTEMPTS:
                # Auto-fix attempt
                print(f"🔧 Attempting auto-fix (iteration {attempt})...")
                Skill("fix-loop")

    if not test_passed:
        # Hard block - regression test failed after max attempts
        print(f"\n🚫 BLOCKED: Regression test failed after {MAX_REGRESSION_ATTEMPTS} attempts.")
        print(f"   Test: {test_file}")
        print(f"   Cannot proceed with commit until this is resolved.")
        exit(1)
```

**If all regression tests pass:** Continue to Step 3

---

### Step 3: Test Suite Verification

**Purpose:** Run full test suites to catch any unexpected side effects.

#### 3.1 Backend Test Suite

```bash
# Run all backend tests (quick mode)
pytest tests/ --tb=short -q
```

**Parse result:**
```python
from hook_utils import detect_test_result

result, passed, failed = detect_test_result(output, 'backend')

if result != 'pass':
    print(f"❌ Backend test suite failed: {failed} tests failed")

    # Launch tester agent for analysis
    agent_result = Task(
        subagent_type="general-purpose",
        model="sonnet",
        prompt=f"""You are a Tester Agent for AlgoChanakya.
        Follow the instructions in .claude/agents/tester.md.

        Read .claude/agents/tester.md first, then:

        Analyze backend test suite failures:

        Failures: {failed}
        Test output:
        {output}

        Provide:
        1. Summary of failing tests
        2. Common failure patterns
        3. Recommended fix approach
        4. Whether failures are related to recent changes
        """
    )

    # Ask user how to proceed
    AskUserQuestion(
        questions=[{
            "question": "Backend test suite has failures. How should we proceed?",
            "header": "Test Failures",
            "multiSelect": False,
            "options": [
                {"label": "Investigate and fix", "description": "Use fix-loop to resolve failures"},
                {"label": "Revert changes", "description": "Undo recent changes and restart"},
                {"label": "Commit anyway", "description": "Proceed with commit despite failures (not recommended)"}
            ]
        }]
    )

    exit(1)  # Block commit
```

#### 3.2 Frontend Test Suite

```bash
# Run all frontend tests (once, no watch)
npm run test:run
```

**Parse result:**
```python
result, passed, failed = detect_test_result(output, 'frontend')

if result != 'pass':
    print(f"❌ Frontend test suite failed: {failed} tests failed")

    # Launch tester agent for analysis (same as backend)
    # ...

    exit(1)  # Block commit
```

**If both suites pass:** Continue to Step 3.3

---

#### 3.3 E2E Smoke + Affected Screens

**Purpose:** Catch UI regressions that pass unit tests but break the actual rendered interface.

**Why:** Unit tests (pytest/Vitest) can't catch broken Vue components, missing `data-testid`, or broken navigation. E2E is the only gate that catches these.

**Execution strategy:**
1. Always run **login smoke** first — if auth breaks, all other E2E tests will fail
2. Run affected screens based on changed files
3. Fallback to `npm run test:main-features` if no specific screen is affected
4. Time budget: 10 minutes maximum, `--retries=1` for flakiness

**Step 3.3 Implementation:**

```python
import subprocess

# Step 3.3.1: Always run login smoke (foundation — auth breakage cascades to all tests)
print("🔐 Step 3.3.1: Login smoke test...")
login_result = Bash(
    command="npx playwright test tests/e2e/specs/login/login.isolated.spec.js --retries=1",
    timeout=60000  # 1 minute
)

if "failed" in login_result.lower():
    print("🚫 BLOCKED: Login smoke test failed.")
    print("   Auth is broken — all E2E tests will fail. Fix auth before proceeding.")
    exit(1)

print("✅ Login smoke passed")

# Step 3.3.2: Determine affected screens from changed files
changed_files = state['steps']['step3_implement']['filesChanged']

SCREEN_MAP = {
    'positions': ['PositionsView.vue', 'positions.py', 'PositionsPage.js', 'specs/positions/'],
    'watchlist': ['WatchlistView.vue', 'watchlist.py', 'WatchlistPage.js', 'specs/watchlist/'],
    'optionchain': ['OptionChainView.vue', 'option_chain', 'OptionChainPage.js', 'specs/optionchain/'],
    'strategy': ['StrategyBuilderView.vue', 'strategy.py', 'StrategyBuilderPage.js', 'specs/strategy/'],
    'strategylibrary': ['StrategyLibrary', 'strategy_library', 'StrategyLibraryPage.js', 'specs/strategylibrary/'],
    'autopilot': ['autopilot/', 'AutoPilot', 'specs/autopilot/', 'specs/ai/'],
    'dashboard': ['DashboardView.vue', 'dashboard.py', 'DashboardPage.js', 'specs/dashboard/'],
    'ofo': ['OFOView.vue', 'ofo.py', 'OFOPage.js', 'specs/ofo/'],
    'navigation': ['KiteHeader.vue', 'router/', 'specs/navigation/'],
    'auth': ['auth.py', 'auth.js', 'specs/auth/', 'specs/login/', 'specs/integration/'],
}

affected_screens = set()
for f in changed_files:
    for screen, patterns in SCREEN_MAP.items():
        if any(p in f for p in patterns):
            affected_screens.add(screen)

# Step 3.3.3: Run affected screen tests (or fallback to main-features)
if affected_screens:
    print(f"📋 Running E2E for affected screens: {', '.join(sorted(affected_screens))}")
    e2e_failed = False
    for screen in sorted(affected_screens):
        result = Bash(
            command=f"npm run test:specs:{screen} -- --retries=1",
            timeout=300000  # 5 minutes per screen
        )
        if "failed" in result.lower():
            print(f"❌ E2E failed for screen: {screen}")
            e2e_failed = True
        else:
            print(f"✅ E2E passed for screen: {screen}")
    if e2e_failed:
        print("🚫 BLOCKED: E2E smoke tests failed for affected screens.")
        exit(1)
else:
    print("📋 No specific screen affected — running main feature smoke tests...")
    result = Bash(
        command="npm run test:main-features -- --retries=1",
        timeout=600000  # 10 minutes budget
    )
    if "failed" in result.lower():
        print("🚫 BLOCKED: E2E main-features smoke test failed.")
        exit(1)
    print("✅ E2E main-features smoke passed")
```

**Hard blocks:**
- Login smoke failure → immediate block (auth breakage cascades to everything)
- Any affected screen failure → block (UI regression detected)

**If E2E smoke passes:** Continue to Step 4

---

### Step 4: Documentation Update

**Purpose:** Ensure documentation stays in sync with code changes.

```python
# Invoke docs-maintainer skill
Skill("docs-maintainer")
```

**What docs-maintainer does:**
1. Reads `docs/feature-registry.yaml` to map changed files to features
2. Updates feature documentation:
   - `docs/features/{feature}/CHANGELOG.md` - Add entry with changes
   - `docs/features/{feature}/README.md` - Update if API/behavior changed
3. Generates updated API documentation (if backend routes changed)
4. Updates architecture docs (if structural changes)

**Docs-maintainer is non-blocking** - it warns if it can't update docs but doesn't fail the pipeline.

---

### Step 5: Git Commit

**Purpose:** Create a safe, conventional commit with secret scanning.

#### 5.1 Delegate to git-manager Agent

```python
agent_result = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt=f"""You are a Git-Manager Agent for AlgoChanakya.
    Follow the instructions in .claude/agents/git-manager.md.

    Read .claude/agents/git-manager.md first, then:

    Create a git commit for the following changes:

    Changed files:
    {format_changed_files(state)}

    Feature/fix description:
    {get_commit_message_description()}

    Requirements:
    1. Use conventional commits format: type(scope): message
    2. Include Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
    3. Run secret scanning before commit
    4. Never commit: notes, .env*, knowledge.db, workflow-state.json, .claude/logs/
    5. Stage only the changed files (not --all)

    Return: Commit SHA or error message
    """
)
```

#### 5.2 Git-Manager Safety Checks

The git-manager agent performs:

**Secret Scanning:**
```bash
# Check for API keys, tokens, passwords
git diff --cached | grep -E "(api[_-]?key|api[_-]?secret|password|token|secret|credential)" -i

# Block if found
if [ $? -eq 0 ]; then
    echo "🚫 BLOCKED: Potential secrets detected in commit"
    exit 1
fi
```

**Protected Files:**
```python
protected_files = [
    'notes',
    '.env', '.env.local', '.env.production',
    '.claude/learning/knowledge.db',
    '.claude/workflow-state.json',
    '.claude/logs/'
]

staged_files = get_staged_files()
for file in staged_files:
    if any(protected in file for protected in protected_files):
        print(f"🚫 BLOCKED: Cannot commit protected file: {file}")
        exit(1)
```

**Conventional Commits:**
```python
# Format: type(scope): message
# Types: feat, fix, docs, style, refactor, test, chore
# Example: feat(positions): add delete button with confirmation modal

commit_message = format_conventional_commit(
    type=commit_type,  # feat, fix, docs, etc.
    scope=affected_feature,  # positions, autopilot, optionchain, etc.
    message=short_description,
    body=detailed_changes,
    footer=f"Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
)
```

#### 5.3 Execute Commit

```bash
# Stage specific files
git add backend/app/api/routes/positions.py
git add frontend/src/components/positions/DeleteButton.vue
git add tests/e2e/specs/positions/delete.happy.spec.js

# Commit with formatted message
git commit -m "$(cat <<'EOF'
feat(positions): add delete button with confirmation modal

- Add DeleteButton.vue component with confirmation dialog
- Implement DELETE /api/positions/{id} endpoint
- Add E2E test for delete flow
- Update positions.py route handler

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

**Commit never auto-pushes** - user must manually push to remote.

---

### Step 6: Update Workflow State

```python
from datetime import datetime
from hook_utils import write_workflow_state

state['steps']['step7_verify']['completed'] = True
state['steps']['step7_verify']['timestamp'] = datetime.now().isoformat()
state['skillInvocations']['postFixPipelineInvoked'] = True
write_workflow_state(state)

print("\n✅ Post-fix pipeline completed successfully!")
print(f"Commit SHA: {commit_sha}")
```

---

## Hard Blocks

**The pipeline will BLOCK (exit 1) if:**

1. **Regression tests fail after 3 attempts:**
   ```
   🚫 BLOCKED: Regression test failed after 3 attempts.
      Test: tests/e2e/specs/positions/positions.happy.spec.js
      Cannot proceed with commit until this is resolved.
   ```

2. **Backend test suite fails:**
   ```
   🚫 BLOCKED: Backend test suite has 5 failing tests.
      Cannot commit with failing test suite.
   ```

3. **Frontend test suite fails:**
   ```
   🚫 BLOCKED: Frontend test suite has 2 failing tests.
      Cannot commit with failing test suite.
   ```

4. **Secret detected in commit:**
   ```
   🚫 BLOCKED: Potential secrets detected in commit.
      File: backend/.env.local
      Pattern: API_KEY=abc123
   ```

5. **Protected file in commit:**
   ```
   🚫 BLOCKED: Cannot commit protected file: notes
   ```

---

## Soft Warnings

**The pipeline will WARN (exit 1 non-blocking) if:**

1. **Documentation update failed:**
   ```
   ⚠️  WARNING: Could not update documentation automatically.
      Please manually update docs/features/positions/CHANGELOG.md
   ```

2. **Flaky regression test:**
   ```
   ⚠️  WARNING: Regression test passed on retry (flaky test detected).
      Test: tests/e2e/specs/positions/positions.happy.spec.js
      Consider investigating test reliability.
   ```

---

## Skills Called

| Skill | When | Purpose |
|-------|------|---------|
| `fix-loop` | Regression test fails | Auto-fix regression failures (max 3 attempts) |
| `docs-maintainer` | Step 4 | Update documentation |

---

## Agents Called

| Agent | When | Purpose |
|-------|------|---------|
| `tester` | Test suite fails | Analyze failures and recommend fixes |
| `git-manager` | Step 5 | Create safe commit with secret scanning |

---

## Output Format

**On success:**
```
✅ Post-fix pipeline completed successfully!

Pipeline results:
  ✅ Regression tests: 3/3 passed
  ✅ Backend test suite: 45 passed
  ✅ Frontend test suite: 23 passed
  ✅ Documentation updated
  ✅ Git commit created

Commit SHA: a1b2c3d4
Commit message: feat(positions): add delete button with confirmation modal

Ready to push:
  git push origin main
```

**On failure:**
```
❌ Post-fix pipeline failed.

Pipeline results:
  ✅ Regression tests: 3/3 passed
  ❌ Backend test suite: 2 failed, 43 passed
  ⏭️  Frontend test suite: Skipped (backend failed)
  ⏭️  Documentation: Skipped
  ⏭️  Git commit: Blocked

Failing tests:
  - tests/backend/autopilot/test_kill_switch.py::test_emergency_exit
  - tests/backend/autopilot/test_order_executor.py::test_place_order

Cannot commit until all tests pass.
```

---

## Example Usage

```
# Automatically invoked by implement
Step 7: Skill("post-fix-pipeline")

# Standalone invocation after manual fixes
Skill("post-fix-pipeline")
```

---

## Implementation Notes

**The skill orchestrates:**
1. Hook utilities (workflow state, test detection)
2. feature-registry.yaml (file-to-test mapping)
3. Sub-agents (tester, git-manager)
4. Other skills (fix-loop, docs-maintainer)
5. Test execution (via Bash)
6. Git operations (via git-manager agent)

**Exit codes:**
- **0:** Pipeline completed successfully, commit created
- **1:** Pipeline failed, commit blocked (hard block scenarios)

---

## Integration with Hooks

**Hooks track that this skill was invoked:**

`log_workflow.py` records:
```json
{
  "timestamp": "2026-02-13T15:45:23",
  "type": "skill_invocation",
  "skill": "post-fix-pipeline",
  "succeeded": true
}
```

**Workflow state updated:**
```json
{
  "skillInvocations": {
    "postFixPipelineInvoked": true
  }
}
```

**This enables the commit gate in `verify_evidence_artifacts.py`:**
- If fixes were applied (`fix_iterations > 0`) but `postFixPipelineInvoked == false`, commit is BLOCKED
- User must invoke `Skill("post-fix-pipeline")` before committing
