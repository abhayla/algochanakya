# AlgoChanakya Automation Feature Proposals

**Date:** February 14, 2026
**Based on:** Gap analysis comparing AlgoChanakya vs CricApp automation
**Related Docs:**
- [Automation Gap Report](./AUTOMATION-GAP-REPORT.md)
- [Automation Workflows Guide](./AUTOMATION_WORKFLOWS.md)

---

## Overview

This document proposes 7 new automation features inspired by CricApp's AUTOMATION_WORKFLOWS.md. Each proposal includes problem statement, implementation details, files to create, and example pseudocode.

**Priority Distribution:**
- **P0 (Sprint 1):** 3 proposals (hooks + CI parity)
- **P1 (Sprint 2):** 2 proposals (TDD skill + researcher agents)
- **P2 (Sprint 3):** 2 proposals (convenience skills)

---

## Table of Contents

1. [P1: Cross-Feature Import Guard Hook](#proposal-1-cross-feature-import-guard-hook) (P0)
2. [P2: Schema Parity Reminder Hook](#proposal-2-schema-parity-reminder-hook) (P0)
3. [P3: Hook-CI Parity Enforcement](#proposal-3-hook-ci-parity-enforcement) (P0)
4. [P4: TDD Skill](#proposal-4-tdd-skill) (P1)
5. [P5: Specialized Researcher Agents](#proposal-5-specialized-researcher-agents) (P1)
6. [P6: /commit-draft Skill](#proposal-6-commit-draft-skill) (P2)
7. [P7: /issue-create Skill](#proposal-7-issue-create-skill) (P2)

---

## Proposal 1: Cross-Feature Import Guard Hook

**Priority:** P0 (Sprint 1)
**Effort:** Medium (6-8 hours)
**Impact:** High (prevents common architectural violations)

### Problem

Currently, nothing prevents importing UI code in the API layer or vice versa. This leads to architectural violations like:

```python
# backend/app/api/routes/positions.py (WRONG!)
from frontend.src.components.positions import ExitPositionModal  # Should NEVER import frontend in backend

# frontend/src/services/positionsApi.js (WRONG!)
from app.models.position import Position  # Should NEVER import backend models in frontend
```

These cross-layer imports create:
- Circular dependencies
- Deployment complexity (frontend can't build without backend code)
- Tight coupling

### Proposal

Add PreToolUse hook that blocks cross-feature imports based on layer boundaries.

### Files to Create

**1. `.claude/hooks/guard_cross_feature_imports.py`** (~120 lines)

```python
#!/usr/bin/env python3
"""
PreToolUse hook: Block cross-feature/cross-layer imports
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import parse_hook_input, exit_with_code

def check_import_violations(file_path: str, content: str) -> list:
    """
    Check for cross-layer import violations.

    Layers:
    - backend/ (Python): Can import ONLY from backend/
    - frontend/ (JS/TS/Vue): Can import ONLY from frontend/
    - tests/ (shared): Can import from both (for testing)

    Returns list of (line_num, import_statement, violation_reason)
    """
    violations = []

    # Determine layer
    if 'backend/' in file_path:
        layer = 'backend'
    elif 'frontend/' in file_path:
        layer = 'frontend'
    elif 'tests/' in file_path:
        return []  # Tests can import from anywhere
    else:
        return []  # Other files (docs, config) - allow

    # Parse imports
    lines = content.split('\n')

    for i, line in enumerate(lines, start=1):
        # Python imports
        if layer == 'backend':
            # Check for frontend imports
            if re.search(r'from\s+frontend\.', line) or re.search(r'import\s+frontend\.', line):
                violations.append((i, line.strip(), "Backend cannot import from frontend/"))

            # Check for JS/TS imports (rare but possible via execjs or similar)
            if re.search(r'require\(.*\.js', line) or re.search(r'import.*\.vue', line):
                violations.append((i, line.strip(), "Backend cannot import frontend JS/Vue files"))

        # JS/TS/Vue imports
        elif layer == 'frontend':
            # Check for backend imports
            if re.search(r'from.*backend/', line) or re.search(r'import.*backend/', line):
                violations.append((i, line.strip(), "Frontend cannot import from backend/"))

            if re.search(r'from.*app\.models', line) or re.search(r'import.*app\.services', line):
                violations.append((i, line.strip(), "Frontend cannot import backend Python modules"))

    return violations


hook_data = parse_hook_input()
if not hook_data:
    exit_with_code(0, "No input")

tool_input = hook_data['tool_input']
file_path = tool_input.get('file_path', '')

# Only check code files
if not (file_path.endswith('.py') or file_path.endswith(('.js', '.ts', '.vue'))):
    exit_with_code(0, "Not a code file")

# Get file content
if hook_data['tool_name'] == 'Write':
    content = tool_input.get('content', '')
elif hook_data['tool_name'] == 'Edit':
    new_string = tool_input.get('new_string', '')
    # Check new content for violations
    content = new_string
else:
    exit_with_code(0, "Not Write/Edit")

# Check violations
violations = check_import_violations(file_path, content)

if violations:
    violation_msgs = []
    for line_num, import_stmt, reason in violations:
        violation_msgs.append(f"  Line {line_num}: {import_stmt}\n    Reason: {reason}")

    exit_with_code(2, f"""
❌ BLOCKED: Cross-layer import violation in {file_path}

Violations found:
{chr(10).join(violation_msgs)}

Architecture rules:
- backend/ can ONLY import from backend/
- frontend/ can ONLY import from frontend/
- tests/ can import from both (for testing)

Fix:
- Use API contracts (JSON over HTTP) for cross-layer communication
- Define TypeScript interfaces in frontend matching backend schemas
- NEVER import code across layer boundaries
    """)

exit_with_code(0, "✅ No cross-layer imports detected")
```

**2. Register in `.claude/settings.json`:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/guard_cross_feature_imports.py",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/guard_cross_feature_imports.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**3. Document in `.claude/rules.md`:**

```markdown
## Cross-Layer Import Rules

**Enforcement:** PreToolUse hook (`guard_cross_feature_imports.py`)

### Layer Boundaries

- **backend/** (Python): Can ONLY import from `backend/`
- **frontend/** (JS/TS/Vue): Can ONLY import from `frontend/`
- **tests/** (shared): Can import from both (for testing purposes)

### Communication Between Layers

Use API contracts (JSON over HTTP), NOT direct imports:

✅ **Correct:**
```javascript
// frontend/src/services/positionsApi.js
const response = await api.get('/positions')  // API call
```

❌ **Wrong:**
```javascript
// frontend/src/services/positionsApi.js
import { Position } from 'backend/app/models/position'  // BLOCKED!
```

### Rationale

- Prevents circular dependencies
- Enables independent deployment
- Enforces loose coupling
```

### Verification

**Test cases:**

1. **Should BLOCK:** Backend imports frontend
   ```python
   # backend/app/api/routes/positions.py
   from frontend.src.components.positions import ExitPositionModal  # BLOCKED
   ```

2. **Should BLOCK:** Frontend imports backend
   ```javascript
   // frontend/src/services/positionsApi.js
   import { Position } from 'app/models/position'  // BLOCKED
   ```

3. **Should ALLOW:** Backend imports backend
   ```python
   # backend/app/api/routes/positions.py
   from app.services.legacy.positions import PositionsService  # OK
   ```

4. **Should ALLOW:** Frontend imports frontend
   ```javascript
   // frontend/src/components/positions/ExitPositionModal.vue
   import { usePositionsStore } from '@/stores/positions'  // OK
   ```

5. **Should ALLOW:** Tests import both
   ```javascript
   // tests/e2e/specs/positions/positions.spec.js
   // Can use both backend test fixtures and frontend components
   ```

---

## Proposal 2: Schema Parity Reminder Hook

**Priority:** P0 (Sprint 1)
**Effort:** Low (2-4 hours)
**Impact:** High (catches schema mismatches early)

### Problem

When backend schema changes (e.g., add field to `Position` model), frontend TypeScript interfaces often lag behind, causing:
- Runtime errors (accessing undefined fields)
- Type mismatches
- Integration bugs

**Example:**
```python
# backend/app/models/position.py
class Position(Base):
    ...
    exit_reason: str  # NEW FIELD ADDED
```

```typescript
// frontend/src/types/position.ts (OUTDATED!)
interface Position {
  ...
  // exit_reason missing!
}
```

### Proposal

Add PostToolUse hook that detects backend schema changes and warns if frontend types aren't updated in the same commit.

### Files to Create

**1. `.claude/hooks/schema_parity_reminder.py`** (~100 lines)

```python
#!/usr/bin/env python3
"""
PostToolUse hook: Warn when backend schema changes without frontend type updates
"""
import sys
import re
from pathlib import Path
import subprocess

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import parse_hook_input, exit_with_code

def detect_schema_change(file_path: str) -> bool:
    """Check if file is a backend model or Alembic migration."""
    return (
        'backend/app/models/' in file_path and file_path.endswith('.py') or
        'backend/alembic/versions/' in file_path
    )

def get_model_name(file_path: str) -> str:
    """Extract model name from file path."""
    # backend/app/models/position.py -> Position
    return Path(file_path).stem.title()

def check_frontend_type_exists(model_name: str) -> tuple:
    """
    Check if corresponding TypeScript interface exists.
    Returns (exists: bool, file_path: str)
    """
    # Search for interface {ModelName} in frontend
    result = subprocess.run(
        ['grep', '-r', f'interface {model_name}', 'frontend/src/types/'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        # Found interface
        match = re.search(r'(frontend/[^:]+)', result.stdout)
        if match:
            return (True, match.group(1))

    return (False, '')

hook_data = parse_hook_input()
if not hook_data:
    exit_with_code(0, "No input")

tool_input = hook_data['tool_input']
file_path = tool_input.get('file_path', '')

# Only check Write/Edit of backend models
if not detect_schema_change(file_path):
    exit_with_code(0, "Not a schema file")

model_name = get_model_name(file_path)

# Check if frontend type exists
type_exists, type_file = check_frontend_type_exists(model_name)

if not type_exists:
    exit_with_code(1, f"""
⚠️  SCHEMA PARITY WARNING:

Backend model changed: {model_name}
File: {file_path}

Frontend TypeScript interface NOT FOUND: interface {model_name}

Did you forget to update frontend types?

Expected location: frontend/src/types/{model_name.lower()}.ts

Action required:
1. Create/update TypeScript interface to match backend model
2. Ensure field names and types align
3. Include in this commit

This is a WARNING (not blocking), but schema mismatches cause runtime errors.
    """)

# Check if frontend type was modified in current session
result = subprocess.run(['git', 'diff', '--name-only', '--cached'], capture_output=True, text=True)
staged_files = result.stdout.strip().split('\n')

if type_file and type_file not in staged_files:
    exit_with_code(1, f"""
⚠️  SCHEMA PARITY WARNING:

Backend model changed: {model_name} ({file_path})
Frontend interface exists: {type_file}

BUT frontend type was NOT updated in this commit.

Did the backend schema change require frontend type updates?

If yes:
1. Update {type_file} to match backend changes
2. Stage and include in this commit

If no (backwards-compatible change):
3. Ignore this warning

This is a WARNING (not blocking).
    """)

exit_with_code(0, "✅ Schema parity check passed")
```

**2. Register in `.claude/settings.json`:**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/schema_parity_reminder.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### Verification

**Test cases:**

1. **Should WARN:** Backend model changed, no frontend type
2. **Should WARN:** Backend model changed, frontend type exists but not updated
3. **Should PASS:** Backend model changed, frontend type updated in same commit
4. **Should PASS:** Non-schema file modified

---

## Proposal 3: Hook-CI Parity Enforcement

**Priority:** P0 (Sprint 1)
**Effort:** Medium (6-8 hours)
**Impact:** High (prevents CI-only failures)

### Problem

Hooks enforce rules locally, but CI runs independently. If hooks and CI checks diverge, developers get:
- Local passes, CI fails (frustrating)
- CI passes, local fails (confusing)

**Example:** `auto_format.py` hook formats files locally, but CI doesn't run formatter → unformatted code passes CI but fails on next developer's machine.

### Proposal

Add GitHub Actions workflow that verifies hooks match CI checks.

### Files to Create

**1. `.github/workflows/hook-parity.yml`** (~150 lines)

```yaml
name: Hook-CI Parity Check

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  check-parity:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Parse hook registrations
        id: parse-hooks
        run: |
          python3 << 'EOF'
          import json
          from pathlib import Path

          settings = json.loads(Path('.claude/settings.json').read_text())
          hooks = settings['hooks']

          hook_checks = set()

          for phase in ['PreToolUse', 'PostToolUse']:
              for matcher_group in hooks.get(phase, []):
                  for hook in matcher_group.get('hooks', []):
                      command = hook.get('command', '')
                      # Extract hook script name
                      if '.claude/hooks/' in command:
                          script = command.split('.claude/hooks/')[1].replace('.py', '')
                          hook_checks.add(script)

          print(f"HOOK_CHECKS={','.join(sorted(hook_checks))}")
          EOF

      - name: Check folder structure (matches guard_folder_structure.py)
        run: |
          echo "Checking backend services/ subdirectory rule..."

          # Find services at root (should only be allowed files)
          ALLOWED_ROOT="__init__.py instruments.py ofo_calculator.py option_chain_service.py"

          for file in backend/app/services/*.py; do
            filename=$(basename "$file")
            if [[ ! " $ALLOWED_ROOT " =~ " $filename " ]]; then
              echo "❌ FAIL: $file should be in subdirectory (autopilot/, options/, etc.)"
              exit 1
            fi
          done

          echo "✅ PASS: Folder structure valid"

      - name: Check code formatting (matches auto_format.py)
        run: |
          echo "Checking Python formatting with black..."

          pip install black
          black --check backend/ || {
            echo "❌ FAIL: Python files not formatted (auto_format.py hook formats locally)"
            exit 1
          }

          echo "✅ PASS: Python formatting valid"

      - name: Check cross-layer imports (matches guard_cross_feature_imports.py)
        run: |
          echo "Checking for cross-layer imports..."

          # Check backend doesn't import frontend
          grep -r "from frontend\." backend/ && {
            echo "❌ FAIL: Backend imports frontend"
            exit 1
          } || true

          # Check frontend doesn't import backend
          grep -r "from.*backend/" frontend/src/ && {
            echo "❌ FAIL: Frontend imports backend"
            exit 1
          } || true

          echo "✅ PASS: No cross-layer imports"

      - name: Parity Summary
        run: |
          echo "=== Hook-CI Parity Check Summary ==="
          echo ""
          echo "Verified:"
          echo "  ✅ Folder structure (guard_folder_structure.py)"
          echo "  ✅ Code formatting (auto_format.py)"
          echo "  ✅ Cross-layer imports (guard_cross_feature_imports.py)"
          echo ""
          echo "Not enforced in CI (local-only hooks):"
          echo "  ⚠️  protect_sensitive_files.py (local paths)"
          echo "  ⚠️  validate_workflow_step.py (workflow state)"
          echo "  ⚠️  verify_evidence_artifacts.py (local state)"
          echo ""
          echo "Hook-CI parity: ✅ PASSING"
```

### Verification

1. Push code that violates folder structure → CI fails
2. Push unformatted code → CI fails
3. Push code with cross-layer imports → CI fails
4. Push valid code → CI passes

---

## Proposal 4: TDD Skill

**Priority:** P1 (Sprint 2)
**Effort:** Medium (8-12 hours)
**Impact:** Medium (improves code quality, reduces bugs)

### Problem

Test-driven development (TDD) is recommended but not automated. Developers often:
1. Write code first
2. Write tests later (or forget)
3. End up with lower test coverage

### Proposal

Create `/tdd` skill that enforces:
1. Write failing test first (red)
2. Write minimum code to pass (green)
3. Refactor (refactor)

### Files to Create

**1. `.claude/skills/tdd/SKILL.md`** (~200 lines)

**2. `.claude/skills/tdd/references/tdd-workflow.md`** (~150 lines)

### Example Invocation

```
User: "I need a function to validate email addresses"

Claude: Starting TDD workflow...

[RED] Step 1: Write failing test
Created: backend/tests/utils/test_email_validator.py
Test: test_valid_email_returns_true()
Running test... ❌ FAILED (function doesn't exist yet)

[GREEN] Step 2: Write minimum code
Created: backend/app/utils/email_validator.py
Running test... ✅ PASSED

[REFACTOR] Step 3: Refactor
(no refactoring needed for simple function)

✅ TDD cycle complete!
```

---

## Proposal 5: Specialized Researcher Agents

**Priority:** P1 (Sprint 2)
**Effort:** High (20-30 hours for all 3 agents)
**Impact:** Medium (improves debugging speed)

### Problem

Current agents are generalists. For domain-specific research (database schema, API endpoints, UI components), they need to search widely. Specialized agents would be faster.

### Proposal

Create 3 specialized researcher agents:

1. **database-researcher** - Schema, migrations, query optimization
2. **api-researcher** - Endpoints, middleware, request/response formats
3. **ui-researcher** - Components, accessibility, responsive design

### Files to Create

**Per agent (3 sets):**
- `.claude/agents/{agent}-researcher.md` (~300 lines each)
- `.claude/agents/memory/{agent}-researcher.md` (initial empty with sections)

**Total:** 6 files (~1,800 lines)

### Example Usage

```
Skill("database-researcher", args="Find all tables that reference the positions table")

Agent analyzes:
- backend/app/models/*.py (all SQLAlchemy models)
- backend/alembic/versions/*.py (migrations)
- Identifies foreign keys, joins, dependencies

Returns:
- trades table (foreign key: position_id)
- autopilot_executions table (foreign key: position_id)
- option_chain_cache table (indirect via symbol)
```

---

## Proposal 6: /commit-draft Skill

**Priority:** P2 (Sprint 3)
**Effort:** Low (2-4 hours)
**Impact:** Low (developer convenience)

### Problem

Writing good conventional commit messages is time-consuming. Currently, git-manager agent does this during `/post-fix-pipeline`, but developers sometimes want to draft messages separately.

### Proposal

Create skill that drafts commit message from staged changes without committing.

### Files to Create

**1. `.claude/skills/commit-draft/SKILL.md`** (~100 lines)

### Example Usage

```
Skill("commit-draft")

Analyzing staged changes...
- backend/app/services/autopilot/kill_switch.py (modified)
- frontend/src/components/autopilot/KillSwitchButton.vue (new)
- tests/e2e/specs/autopilot/kill-switch.spec.js (new)

Draft commit message:
---
feat(autopilot): add emergency kill switch button

- Implement KillSwitch service for emergency position exits
- Add KillSwitchButton component to AutoPilot dashboard
- Add E2E test for kill switch functionality

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
---

To commit: git commit -m "$(cat above message)"
Or: Continue with /post-fix-pipeline to commit automatically
```

---

## Proposal 7: /issue-create Skill

**Priority:** P2 (Sprint 3)
**Effort:** Low (2-4 hours)
**Impact:** Low (developer convenience)

### Problem

When encountering bugs or needed improvements, developers must:
1. Switch to GitHub
2. Manually create issue
3. Copy error messages, stack traces
4. Return to development

### Proposal

Create skill that creates GitHub issue from error message + context.

### Files to Create

**1. `.claude/skills/issue-create/SKILL.md`** (~120 lines)

### Example Usage

```
User: "Test is failing with timeout error. Create an issue for this."

Claude: Skill("issue-create", args="test-timeout-positions-spec")

Analyzing error:
- Test: tests/e2e/specs/positions/positions.happy.spec.js:45
- Error: Timeout waiting for locator('[data-testid="positions-exit-confirm"]')
- Stack trace: [captured from test output]

Created GitHub issue #234:
---
Title: [Bug] E2E test timeout in positions exit modal

Labels: bug, test-failure, e2e

Description:
**Test:** tests/e2e/specs/positions/positions.happy.spec.js:45
**Error:** Timeout waiting for locator('[data-testid="positions-exit-confirm"]')

**Stack Trace:**
```
[stack trace here]
```

**Possible Causes:**
- data-testid mismatch (component may use different testid)
- Modal not rendering (Vue reactivity issue)
- Slow API response (backend timeout)

**Environment:**
- Branch: main
- Commit: e8c899f
- Node: 20.11.0
- Playwright: 1.41.0

---

View issue: https://github.com/user/algochanakya/issues/234
```

---

## Implementation Priority & Timeline

### Sprint 1 (Week 3) - P0: Critical Hooks

**Goal:** Prevent common architectural violations

| # | Proposal | Effort | Assignee |
|---|----------|--------|----------|
| P1 | Cross-Feature Import Guard | 6-8h | TBD |
| P2 | Schema Parity Reminder | 2-4h | TBD |
| P3 | Hook-CI Parity | 6-8h | TBD |

**Total:** 14-20 hours

### Sprint 2 (Week 4-5) - P1: Quality Improvements

**Goal:** Improve development workflow and debugging

| # | Proposal | Effort | Assignee |
|---|----------|--------|----------|
| P4 | TDD Skill | 8-12h | TBD |
| P5 | Specialized Researcher Agents (3) | 20-30h | TBD |

**Total:** 28-42 hours

### Sprint 3 (Week 6) - P2: Convenience Features

**Goal:** Developer experience improvements

| # | Proposal | Effort | Assignee |
|---|----------|--------|----------|
| P6 | /commit-draft Skill | 2-4h | TBD |
| P7 | /issue-create Skill | 2-4h | TBD |

**Total:** 4-8 hours

---

## Success Metrics

**P0 (Sprint 1):**
- Zero cross-layer imports in codebase
- Zero schema parity warnings ignored
- CI and hooks enforce same rules (100% parity)

**P1 (Sprint 2):**
- TDD adoption rate: ≥50% of new features
- Debug time reduction: ~30% (specialized agents find issues faster)

**P2 (Sprint 3):**
- Commit message quality: ≥90% conventional format
- Issue creation time: ≤2 minutes (vs ~5-10 minutes manual)

---

## Conclusion

These 7 proposals address the automation gaps identified in the Gap Report. Implementing all proposals will bring AlgoChanakya's automation documentation and enforcement capabilities to parity with (and beyond) CricApp's gold standard.

**Next Steps:**
1. Review and approve proposals
2. Assign sprint work
3. Implement P0 proposals first (Sprint 1)
4. Iterate based on feedback

---

**End of Feature Proposals**
**Version:** 1.0
**Last Updated:** February 14, 2026
