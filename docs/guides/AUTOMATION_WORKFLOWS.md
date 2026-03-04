# AlgoChanakya Automation Workflows

**Complete Guide to Hooks, Commands, Agents, Skills, and Learning System**
**Last Updated:** February 14, 2026
**Version:** 2.0

This is the unified automation guide for AlgoChanakya. It documents the entire automation system: hooks, commands, agents, skills, and the knowledge.db learning system.

---

## Table of Contents

1. [Quick Start & Priority Tiers](#1-quick-start--priority-tiers)
2. [Prerequisites & Concepts](#2-prerequisites--concepts)
3. [Hook Automations](#3-hook-automations)
4. [Command Workflows](#4-command-workflows)
5. [Agent Automations](#5-agent-automations)
6. [Skill Automations](#6-skill-automations)
7. [Learning System](#7-learning-system)
8. [Settings & Permissions](#8-settings--permissions)
9. [CI/CD Pipeline](#9-cicd-pipeline)
10. [Code Generation Workflow](#10-code-generation-workflow)
11. [Session Management](#11-session-management)
12. [Debugging Workflow](#12-debugging-workflow)
13. [Integration Patterns](#13-integration-patterns)
14. [Customization Guide](#14-customization-guide)
15. [Appendix: File Inventory](#appendix-file-inventory)

---

## 1. Quick Start & Priority Tiers

### 1.1 First-Time Setup Verification

**Before using the automation system, verify:**

```bash
# 1. Check hooks are registered
cat .claude/settings.json | grep -A 5 "hooks"

# 2. Verify learning database exists
ls -lh .claude/learning/knowledge.db

# 3. Check workflow state file
cat .claude/workflow-state.json

# 4. Verify all hook scripts are executable
ls -l .claude/hooks/*.py
```

### 1.2 Priority Tiers (Start Here!)

**Tier 0: Must Know (Start here)**
- `Skill("implement")` command - 7-step workflow for all code changes
- `auto-verify` skill - Auto-test after code changes
- Hook enforcement - Understand what's blocked and why

**Tier 1: Daily Use**
- `Skill("fix-loop")` - Fix failing tests iteratively
- `test-fixer` skill - Diagnose test failures
- Learning system - How knowledge.db improves over time

**Tier 2: Advanced**
- Custom agents - When to use debugger, code-reviewer, tester
- Session management - Save/resume context
- Knowledge queries - How to read strategies from knowledge.db

**Tier 3: Customization**
- Adding new hooks
- Creating custom skills
- Modifying workflow state machine

### 1.3 Common Scenarios (Quick Reference)

| Scenario | Command/Skill | Priority |
|----------|---------------|----------|
| **Implementing a new feature** | `Skill("implement")` | Tier 0 |
| **Fixing a bug** | `Skill("fix-loop")` or `Skill("implement")` | Tier 0 |
| **Test is failing** | `test-fixer` | Tier 1 |
| **Code change needs verification** | `auto-verify` | Tier 0 |
| **Need to update docs** | `docs-maintainer` | Tier 1 |
| **Check codebase health** | `health-check` | Tier 2 |
| **Creating a Vue component** | `vue-component-generator` | Tier 1 |
| **Writing E2E tests** | `e2e-test-generator` | Tier 1 |
| **Broker API question** | `smartapi-expert`, `zerodha-expert`, etc. | Tier 2 |
| **Save current work** | `save-session` | Tier 2 |
| **Debug complex failure** | Launch `debugger` agent | Tier 2 |

### 1.4 File Locations Cheat Sheet

```
.claude/
├── hooks/              # 14 hook scripts + hook_utils.py (shared library)
├── commands/           # 6 command workflow definitions
├── agents/             # 5 agent definitions
│   └── memory/         # Persistent agent memory files
├── skills/             # 21 skills (each in subdirectory with SKILL.md)
├── learning/           # Learning system (knowledge.db, schema.sql, db_helper.py)
├── sessions/           # Saved session files
├── logs/               # Workflow and learning logs
├── settings.json       # Hook registrations and permissions
└── rules.md            # Architectural rules (555 lines)
```

---

## 2. Prerequisites & Concepts

### 2.1 Hook Lifecycle

**Hooks execute at specific points in tool usage:**

```
┌─────────────────────────────────────────────────────────┐
│                    Tool Invocation                       │
│   (Write, Edit, Bash, Skill, mcp__playwright__, etc.)   │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
          ┌─────────────────────────────────┐
          │   PreToolUse Hooks (4 hooks)    │
          │   - protect_sensitive_files     │
          │   - guard_folder_structure      │
          │   - validate_workflow_step      │
          │   - verify_evidence_artifacts   │
          └─────────────────────────────────┘
                            │
                            ▼ (Exit code 0=allow, 1=warn, 2=block)
                            │
        ┌───────────────────┴───────────────────┐
        │ Blocked (exit 2)?                     │
        │ Yes → Tool execution prevented        │
        │ No  → Tool executes                   │
        └───────────────────┬───────────────────┘
                            │
                            ▼
          ┌─────────────────────────────────┐
          │      Tool Executes              │
          │   (Write file, run command,     │
          │    invoke skill, etc.)          │
          └─────────────────────────────────┘
                            │
                            ▼
          ┌─────────────────────────────────┐
          │  PostToolUse Hooks (7 hooks)    │
          │  - post_test_update             │
          │  - verify_test_rerun            │
          │  - post_screenshot_resize       │
          │  - auto_fix_pattern_scan        │
          │  - log_workflow                 │
          │  - post_skill_learning          │
          │  - auto_format                  │
          └─────────────────────────────────┘
                            │
                            ▼
                      ┌─────────┐
                      │  Done   │
                      └─────────┘
```

**Exit Codes:**
- `0` = Allow (continue)
- `1` = Warn (show message but continue)
- `2` = Block (prevent tool execution)

### 2.2 Agent vs Skill vs Command Decision Matrix

| Use Case | Use Agent | Use Skill | Use Command |
|----------|-----------|-----------|-------------|
| **Research/Investigation** | ✅ Read-only analysis | ❌ Skills modify | ❌ Commands orchestrate |
| **Code Review** | ✅ code-reviewer agent | ❌ | ❌ |
| **Root Cause Analysis** | ✅ debugger agent | ❌ | ❌ |
| **Fix Failing Tests** | ❌ | ✅ test-fixer | ✅ Skill("fix-loop") (orchestrates) |
| **Generate Code** | ❌ | ✅ vue-component-generator | ❌ |
| **Run Tests** | ❌ | ✅ auto-verify | ✅ run-tests (multi-layer) |
| **Full Feature Implementation** | ❌ | ❌ | ✅ Skill("implement") (7 steps) |
| **Update Documentation** | ❌ | ✅ docs-maintainer | ✅ post-fix-pipeline (includes docs) |
| **Git Operations** | ✅ git-manager | ❌ | ✅ post-fix-pipeline (includes commit) |
| **Learning Reflection** | ❌ | ✅ learning-engine | ✅ reflect (orchestrates) |

**Key Differences:**

- **Agents:** Read-only, return analysis/recommendations, have persistent memory
- **Skills:** Execute actions (write files, run tests, invoke tools), stateless
- **Commands:** High-level workflows that orchestrate multiple skills/agents

### 2.3 Workflow State Machine

**File:** `.claude/workflow-state.json`

The `Skill("implement")` command uses a 7-step state machine:

```
Step 1: Requirements/Clarification
  ↓ (validate_workflow_step blocks code changes until complete)
Step 2: Write/Update Tests
  ↓ (validate_workflow_step blocks code changes until tests written)
Step 3: Implement Feature
  ↓
Step 4: Run Targeted Tests
  ↓ (post_test_update records results)
  ↓ (verify_test_rerun independently verifies)
Step 5: Fix Loop (if tests failed)
  ↓ (iterative with code-reviewer gate)
Step 6: Visual Verification
  ↓ (post_screenshot_resize auto-resizes)
Step 7: Post-Fix Pipeline
  ↓ (final verification + docs + commit)
  ↓
✅ Complete
```

**State File Schema:**
```json
{
  "sessionId": "20260214-153045",
  "activeCommand": "implement",
  "lastActivity": "2026-02-14T15:45:23Z",
  "steps": {
    "step1_requirements": {"completed": true, "timestamp": "..."},
    "step2_tests": {"completed": true, "testFiles": [...], "testLayers": [...]},
    "step3_implement": {"completed": true, "filesChanged": [...]},
    "step4_runTests": {"completed": true, "testLayers": {...}},
    "step5_fixLoop": {"completed": true, "iterations": 2},
    "step6_screenshots": {"completed": true},
    "step7_postFixPipeline": {"completed": true}
  },
  "skillInvocations": {
    "fixLoopInvoked": true,
    "fixLoopCount": 1,
    "fixLoopSucceeded": true,
    "postFixPipelineInvoked": true
  },
  "evidence": {
    "testRuns": [...]
  },
  "pendingAutoFixes": []
}
```

### 2.4 Directory Structure

```
.claude/
├── hooks/
│   ├── hook_utils.py              # 725 lines - Shared library for all hooks
│   ├── protect_sensitive_files.py # PreToolUse: Block .env, knowledge.db writes
│   ├── guard_folder_structure.py  # PreToolUse: Enforce subdirectory rules
│   ├── validate_workflow_step.py  # PreToolUse: Enforce Skill("implement") step order
│   ├── verify_evidence_artifacts.py # PreToolUse: Require evidence before Bash
│   ├── post_test_update.py        # PostToolUse: Record test results
│   ├── verify_test_rerun.py       # PostToolUse: Independent test verification
│   ├── post_screenshot_resize.py  # PostToolUse: Resize large images
│   ├── auto_fix_pattern_scan.py   # PostToolUse: Scan for error patterns
│   ├── log_workflow.py            # PostToolUse: Append to workflow log
│   ├── post_skill_learning.py     # PostToolUse: Record to knowledge.db
│   ├── auto_format.py             # PostToolUse: Format Python/JS files
│   ├── load_session_context.py    # Session: Restore on resume
│   ├── reinject_after_compaction.py # Session: Re-inject after compression
│   └── quality_gate.py            # Session: Final commit checks
├── commands/
│   ├── implement.md               # Skill("implement") - 7-step workflow
│   ├── fix-loop.md                # Skill("fix-loop") - Iterative fix cycle
│   ├── post-fix-pipeline.md       # post-fix-pipeline - Final verification
│   ├── run-tests.md               # run-tests - Multi-layer test runner
│   ├── fix-issue.md               # fix-issue - GitHub issue fixer
│   └── reflect.md                 # reflect - Learning reflection
├── agents/
│   ├── code-reviewer.md           # Validate against architectural rules
│   ├── debugger.md                # Root cause analysis (ThinkHard/UltraThink)
│   ├── git-manager.md             # Conventional commits + secret scanning
│   ├── planner-researcher.md      # Feature planning
│   ├── tester.md                  # Test suite diagnosis
│   └── memory/                    # Persistent memory for each agent
│       ├── code-reviewer.md
│       ├── debugger.md
│       ├── git-manager.md
│       ├── planner-researcher.md
│       └── tester.md
├── skills/                        # 21 skills (see section 6 for full list)
├── learning/
│   ├── knowledge.db               # SQLite database (6 tables)
│   ├── schema.sql                 # Database schema definition
│   └── db_helper.py               # 759 lines - Database operations
├── sessions/                      # Saved sessions
├── logs/
│   ├── workflow-sessions.log      # Event log (appended by log_workflow hook)
│   └── learning/
│       └── failure-index.json     # Quick failure lookup
├── settings.json                  # Hook registrations + permissions
├── settings.local.json            # Local overrides (gitignored)
└── rules.md                       # 555 lines - Architectural rules
```

---

## 3. Hook Automations

**Total:** 14 hooks (4 PreToolUse, 7 PostToolUse, 3 Session)

### 3.1 Shared Library: hook_utils.py

**Location:** `.claude/hooks/hook_utils.py` (725 lines)

**Purpose:** Common functions used by all hooks to avoid code duplication.

**API:**

```python
# Input/Output Protocol
parse_hook_input() -> Optional[Dict]      # Parse stdin JSON
exit_with_code(code: int, message: str)   # Exit with 0/1/2

# Workflow State Management
read_workflow_state() -> Optional[Dict]
write_workflow_state(state: Dict) -> bool
init_workflow_state(command_name: str) -> Dict

# Test Detection
is_test_command(cmd: str) -> bool
detect_test_layer(cmd: str) -> str        # 'e2e', 'backend', 'frontend'
detect_test_result(output: str, layer: str) -> Tuple[str, int, int]

# File Classification
is_test_file(path: str) -> bool
is_code_file(path: str) -> bool
is_always_allowed_file(path: str) -> bool

# Evidence Recording
write_evidence(dir: Path, filename: str, data: Dict) -> bool

# Logging
log_event(event_type: str, **kwargs)
record_skill_invocation(skill: str, succeeded: bool)

# Skill Outcome Detection
detect_skill_outcome(output: str) -> dict  # Returns outcome, error_type, component

# Failure Index Management
init_failure_index() -> Dict
read_failure_entry(skill: str, issue_type: str) -> Optional[Dict]
update_failure_index(skill: str, issue_type: str, outcome: str, ...)

# Agent Memory Management
read_agent_memory(agent_name: str) -> str
append_agent_memory(agent_name: str, section: str, entry: str) -> bool
```

**Usage Example:**
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import parse_hook_input, exit_with_code, read_workflow_state

# Parse input
hook_data = parse_hook_input()
if not hook_data:
    exit_with_code(0, "No input")

# Check workflow state
state = read_workflow_state()
if state and not state['steps']['step2_tests']['completed']:
    exit_with_code(2, "❌ Must write tests first (Step 2)")

exit_with_code(0, "✅ Allowed")
```

---

### 3.2 PreToolUse Hooks (4 Hooks)

PreToolUse hooks run **before** a tool executes. They can block the tool.

#### 3.2.1 protect_sensitive_files.py

**Triggers:** Write, Edit
**Purpose:** Prevent accidental modification of sensitive files

**Pseudocode:**
```python
hook_data = parse_hook_input()
tool_input = hook_data['tool_input']
file_path = tool_input.get('file_path', '')

PROTECTED_PATTERNS = [
    r'\.env$', r'\.env\..*$',           # Environment files
    r'knowledge\.db$',                   # Learning database
    r'workflow-state\.json$',            # Workflow state
    r'\.auth-state\.json$',              # Auth state
    r'\.auth-token$',                    # Auth token
    r'^C:\\Apps\\algochanakya',          # Production folder
]

for pattern in PROTECTED_PATTERNS:
    if re.search(pattern, file_path):
        exit_with_code(2, f"❌ BLOCKED: {file_path} is protected")

exit_with_code(0, "✅ File not protected")
```

**Configuration (settings.json):**
```json
{
  "permissions": {
    "deny": [
      "Write(C:\\Apps\\algochanakya/**)",
      "Edit(C:\\Apps\\algochanakya/**)",
      "Write(**/.env)",
      "Edit(**/.env)",
      "Write(**/knowledge.db)",
      "Edit(**/knowledge.db)"
    ]
  }
}
```

**Customization:**
- Add patterns to `PROTECTED_PATTERNS` list
- Add to `deny` list in settings.json for UI-level blocking

#### 3.2.2 guard_folder_structure.py

**Triggers:** Write
**Purpose:** Enforce folder structure rules (backend services, frontend assets)

**Pseudocode:**
```python
hook_data = parse_hook_input()
file_path = hook_data['tool_input'].get('file_path', '')

# Backend services check
if 'backend/app/services/' in file_path:
    # Allow specific root files
    ALLOWED_ROOT = ['__init__.py', 'instruments.py', 'ofo_calculator.py', 'option_chain_service.py']
    filename = Path(file_path).name

    # Check if file is in root (no subdirectory)
    service_path = file_path.split('backend/app/services/')[1]
    is_root = '/' not in service_path.replace('\\', '/')

    if is_root and filename not in ALLOWED_ROOT:
        exit_with_code(2, f"❌ BLOCKED: Services must be in subdirectories (autopilot/, options/, legacy/, ai/, brokers/)")

# Frontend assets check
if 'frontend/src/assets/' in file_path:
    # CSS must be in styles/, not css/
    if '/css/' in file_path:
        exit_with_code(2, f"❌ BLOCKED: CSS must be in src/assets/styles/, not src/assets/css/")

    # Images must be in logos/
    if file_path.endswith(('.png', '.jpg', '.svg')) and '/logos/' not in file_path:
        exit_with_code(2, f"❌ BLOCKED: Images must be in src/assets/logos/")

exit_with_code(0, "✅ Folder structure valid")
```

**Rationale:**
- **Backend:** Prevent services/ root bloat, enforce subdirectory organization
- **Frontend:** Enforce consistent asset organization

**Customization:**
- Modify `ALLOWED_ROOT` list for backend exceptions
- Add new directory rules for other modules

#### 3.2.3 validate_workflow_step.py

**Triggers:** Write, Edit, Bash
**Purpose:** Enforce Skill("implement") step order (prevent code before tests)

**Pseudocode:**
```python
hook_data = parse_hook_input()
tool_name = hook_data['tool_name']
tool_input = hook_data['tool_input']

state = read_workflow_state()
if not state:
    exit_with_code(0, "No active workflow")

# Check if modifying production code
file_path = tool_input.get('file_path', '')
if is_code_file(file_path) and not is_test_file(file_path):
    # Production code - check Step 2 complete
    if not state['steps']['step2_tests']['completed']:
        exit_with_code(2, """
❌ BLOCKED: Must write tests first (Step 2 of implement workflow)

Current step: Step 1 (Requirements)
You must:
  1. Complete Step 1 (state understanding + research)
  2. Write tests in Step 2
  3. Then write production code in Step 3

Run: Skill("e2e-test-generator") or Skill("vitest-generator")
        """)

# Check if attempting to commit
if tool_name == 'Bash' and 'git commit' in tool_input.get('command', ''):
    # All steps must be complete
    all_complete = all(
        state['steps'][step]['completed']
        for step in ['step1_requirements', 'step2_tests', 'step3_implement',
                     'step4_runTests', 'step5_fixLoop', 'step6_screenshots', 'step7_postFixPipeline']
    )

    if not all_complete:
        exit_with_code(2, "❌ BLOCKED: Complete all 7 steps before committing")

    # post-fix-pipeline must be invoked
    if not state['skillInvocations']['postFixPipelineInvoked']:
        exit_with_code(2, "❌ BLOCKED: Must run post-fix-pipeline before commit")

exit_with_code(0, "✅ Workflow step valid")
```

**Configuration:**
- Workflow steps defined in `.claude/skills/implement/SKILL.md`
- Step progression tracked in `workflow-state.json`

**Customization:**
- Modify step definitions in `Skill("implement")` command
- Adjust blocking logic for different workflows

#### 3.2.4 verify_evidence_artifacts.py

**Triggers:** Bash
**Purpose:** Require evidence files before running tests (audit trail)

**Pseudocode:**
```python
hook_data = parse_hook_input()
command = hook_data['tool_input'].get('command', '')

# Check if running tests
if not is_test_command(command):
    exit_with_code(0, "Not a test command")

state = read_workflow_state()
if not state:
    exit_with_code(0, "No workflow state")

# Require evidence directory exists
evidence_dir = Path(".claude/logs/evidence") / state['sessionId']
if not evidence_dir.exists():
    exit_with_code(1, f"⚠️  Warning: No evidence directory for session {state['sessionId']}")

exit_with_code(0, "✅ Evidence check passed")
```

**Rationale:** Ensures test runs have traceable evidence (for learning system and debugging)

**Customization:**
- Modify evidence directory location
- Add requirements for specific evidence file types

---

### 3.3 PostToolUse Hooks (7 Hooks)

PostToolUse hooks run **after** a tool executes successfully. They cannot block (tool already ran).

#### 3.3.1 post_test_update.py

**Triggers:** Bash
**Purpose:** Record test results to workflow-state.json

**Pseudocode:**
```python
hook_data = parse_hook_input()
command = hook_data['tool_input'].get('command', '')
output = hook_data.get('tool_output', '')

if not is_test_command(command):
    exit_with_code(0, "Not a test command")

layer = detect_test_layer(command)  # 'e2e', 'backend', 'frontend'
result, passed, failed = detect_test_result(output, layer)

state = read_workflow_state()
if not state:
    exit_with_code(0, "No workflow state")

# Update Step 4 test results
state['steps']['step4_runTests']['testLayers'][layer] = {
    'passed': passed,
    'failed': failed
}

# Record evidence
evidence = {
    'timestamp': datetime.now().isoformat(),
    'layer': layer,
    'command': command,
    'result': result,
    'passed': passed,
    'failed': failed
}
state['evidence']['testRuns'].append(evidence)

write_workflow_state(state)
log_event('test_run', layer=layer, result=result, passed=passed, failed=failed)

exit_with_code(0, f"✅ Recorded {layer} test result: {result}")
```

**Configuration:** Uses test detection functions from `hook_utils.py`

**Customization:**
- Add new test layers (currently supports e2e, backend, frontend)
- Modify result parsing patterns for different test frameworks

#### 3.3.2 verify_test_rerun.py

**Triggers:** Bash
**Purpose:** Independently re-run tests to prevent false positives

**Pseudocode:**
```python
hook_data = parse_hook_input()
command = hook_data['tool_input'].get('command', '')
original_output = hook_data.get('tool_output', '')

if not is_test_command(command):
    exit_with_code(0, "Not a test command")

# Parse claimed result
claimed_result, _, _ = detect_test_result(original_output, detect_test_layer(command))

if claimed_result != 'pass':
    exit_with_code(0, "Tests didn't pass, no verification needed")

# Re-run the same command independently
import subprocess
rerun_result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
rerun_output = rerun_result.stdout + rerun_result.stderr

# Check if rerun matches claim
actual_result, _, _ = detect_test_result(rerun_output, detect_test_layer(command))

if actual_result == 'pass' and claimed_result == 'pass':
    exit_with_code(0, "✅ Test claim verified - tests actually pass")
elif claimed_result == 'pass' and actual_result != 'pass':
    # FALSE POSITIVE DETECTED
    exit_with_code(1, f"""
⚠️  WARNING: Test claim mismatch!
Claimed: PASS
Actual:  {actual_result.upper()}

The tests you ran claimed to pass, but independent verification found failures.
This could indicate:
  - Flaky tests (timing issues, race conditions)
  - Environment-specific failures
  - False positive in test output parsing

Please investigate and fix before proceeding.
    """)
else:
    exit_with_code(0, "✅ Test verification complete")
```

**Rationale:** Prevents Claude from claiming tests passed when they actually failed.

**Budget:** 300s timeout per re-run

**Customization:**
- Adjust timeout for slow test suites
- Add skip conditions for specific test patterns

#### 3.3.3 post_screenshot_resize.py

**Triggers:** Bash, mcp__playwright__browser_take_screenshot
**Purpose:** Resize large screenshots to prevent file bloat

**Pseudocode:**
```python
hook_data = parse_hook_input()

# Find screenshot path
if hook_data['tool_name'] == 'Bash':
    output = hook_data.get('tool_output', '')
    # Parse screenshot path from Playwright output
    match = re.search(r'Screenshot: (.+\.png)', output)
    if not match:
        exit_with_code(0, "No screenshot found")
    screenshot_path = match.group(1)
else:
    # mcp__playwright__browser_take_screenshot
    screenshot_path = hook_data['tool_input'].get('filename', '')

if not Path(screenshot_path).exists():
    exit_with_code(0, "Screenshot file not found")

# Check size
from PIL import Image
img = Image.open(screenshot_path)
width, height = img.size

MAX_WIDTH = 1800
if width > MAX_WIDTH:
    # Resize maintaining aspect ratio
    ratio = MAX_WIDTH / width
    new_height = int(height * ratio)
    resized = img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
    resized.save(screenshot_path, optimize=True, quality=85)

    exit_with_code(0, f"✅ Resized screenshot: {width}x{height} → {MAX_WIDTH}x{new_height}")
else:
    exit_with_code(0, "✅ Screenshot size OK")
```

**Configuration:**
- `MAX_WIDTH = 1800` pixels
- Quality: 85% (good balance of size vs quality)

**Customization:**
- Adjust MAX_WIDTH threshold
- Modify quality setting
- Add height limits

#### 3.3.4 auto_fix_pattern_scan.py

**Triggers:** Bash
**Purpose:** Scan output for recurring error patterns, suggest auto-fixes

**Pseudocode:**
```python
hook_data = parse_hook_input()
output = hook_data.get('tool_output', '')

# Load failure index
index = init_failure_index()

# Scan for known patterns
ERROR_PATTERNS = [
    ('selector_not_found', r'Timeout waiting for locator'),
    ('import_error', r'ModuleNotFoundError|ImportError'),
    ('database_error', r'relation.*does not exist'),
    ('broker_error', r'Incorrect api_key|broker.*error'),
]

for error_type, pattern in ERROR_PATTERNS:
    if re.search(pattern, output, re.IGNORECASE):
        # Check if auto-fix eligible
        entry = read_failure_entry('test-fixer', error_type)

        if entry and entry.get('auto_fix_eligible'):
            workaround = entry.get('known_workaround', '')
            exit_with_code(1, f"""
💡 Auto-fix suggestion for {error_type}:

This error has occurred {len(entry['occurrences'])} times with 70%+ resolution rate.
Known workaround: {workaround}

Would you like to apply auto-fix? (This is a suggestion, not automatic)
            """)

exit_with_code(0)
```

**Rationale:** Surfaces learned patterns to speed up debugging

**Customization:**
- Add new error patterns
- Adjust auto-fix threshold (currently 70% success rate, 5+ occurrences)

#### 3.3.5 log_workflow.py

**Triggers:** Bash, Write, Edit, Skill
**Purpose:** Append events to workflow-sessions.log

**Pseudocode:**
```python
hook_data = parse_hook_input()
tool_name = hook_data['tool_name']
tool_input = hook_data['tool_input']

event = {
    'timestamp': datetime.now().isoformat(),
    'tool': tool_name,
    'input': {
        'file_path': tool_input.get('file_path'),
        'command': tool_input.get('command'),
        'skill': tool_input.get('skill')
    }
}

# Append to log
log_file = Path(".claude/logs/workflow-sessions.log")
log_file.parent.mkdir(parents=True, exist_ok=True)

with open(log_file, 'a') as f:
    f.write(json.dumps(event) + '\n')

exit_with_code(0)
```

**Log Format:** JSONL (one JSON object per line)

**Customization:**
- Add custom fields to event
- Filter specific tools from logging

#### 3.3.6 post_skill_learning.py

**Triggers:** Skill
**Purpose:** Record skill outcomes to knowledge.db

**Pseudocode:**
```python
hook_data = parse_hook_input()
skill_name = hook_data['tool_input'].get('skill', '')
output = hook_data.get('tool_output', '')

# Detect outcome
outcome_data = detect_skill_outcome(output)
# Returns: {'outcome': 'RESOLVED', 'error_type': '...', 'component': '...', 'workaround_used': '...', 'succeeded': True}

if outcome_data['error_type']:
    # Import knowledge.db helper
    sys.path.insert(0, str(Path(".claude/learning")))
    from db_helper import record_error, record_attempt

    # Record error pattern
    error_id = record_error(
        error_type=outcome_data['error_type'],
        message=output[:500],  # Truncate
        file_path=outcome_data.get('component')
    )

    # Record attempt
    record_attempt(
        error_pattern_id=error_id,
        outcome='success' if outcome_data['succeeded'] else 'failure',
        fix_description=outcome_data.get('workaround_used', '')
    )

# Update workflow state
record_skill_invocation(skill_name, outcome_data['succeeded'])

exit_with_code(0, f"✅ Recorded {skill_name} outcome: {outcome_data['outcome']}")
```

**Rationale:** Enables learning system to rank strategies over time

**Customization:**
- Modify outcome detection patterns in `hook_utils.detect_skill_outcome()`
- Add skill-specific outcome parsers

#### 3.3.7 auto_format.py

**Triggers:** Write, Edit
**Purpose:** Auto-format Python/JS files after modification

**Pseudocode:**
```python
hook_data = parse_hook_input()
file_path = hook_data['tool_input'].get('file_path', '')

if file_path.endswith('.py'):
    # Format with black
    subprocess.run(['black', file_path, '--quiet'], check=False)
    exit_with_code(0, f"✅ Formatted Python file: {file_path}")

elif file_path.endswith(('.js', '.vue')):
    # Format with prettier (if available)
    result = subprocess.run(['npx', 'prettier', '--write', file_path], capture_output=True, check=False)
    if result.returncode == 0:
        exit_with_code(0, f"✅ Formatted JS/Vue file: {file_path}")

exit_with_code(0)
```

**Configuration:**
- Python: Uses `black` (must be installed in venv)
- JS/Vue: Uses `prettier` (must be in node_modules)

**Customization:**
- Add support for other languages
- Modify formatter settings (.black, .prettierrc)

---

### 3.4 Session Hooks (3 Hooks)

Session hooks run at specific lifecycle events.

#### 3.4.1 load_session_context.py

**Trigger:** Session start (when resuming saved session)
**Purpose:** Restore workflow state and context

**Pseudocode:**
```python
session_id = sys.argv[1]  # Passed by Claude Code

session_file = Path(f".claude/sessions/{session_id}.md")
if not session_file.exists():
    exit_with_code(0, "No saved session")

# Read session metadata
with open(session_file) as f:
    content = f.read()

# Extract workflow state ID from session file
state_match = re.search(r'Workflow State: (.+)', content)
if state_match:
    state_id = state_match.group(1)

    # Restore workflow state
    archived_state = Path(f".claude/logs/workflow-states/{state_id}.json")
    if archived_state.exists():
        import shutil
        shutil.copy(archived_state, WORKFLOW_STATE_FILE)

exit_with_code(0, "✅ Session context loaded")
```

**Rationale:** Allows resuming Skill("implement") workflow across sessions

**Customization:**
- Add custom context restoration (environment vars, temp files)

#### 3.4.2 reinject_after_compaction.py

**Trigger:** After conversation compaction (when approaching context limit)
**Purpose:** Re-inject critical context that may have been compressed away

**Pseudocode:**
```python
# Read critical files that should always be in context
critical_files = [
    '.claude/rules.md',
    'CLAUDE.md',
    '.claude/workflow-state.json'
]

context_injection = []

for file_path in critical_files:
    if Path(file_path).exists():
        with open(file_path) as f:
            content = f.read()
        context_injection.append(f"# {file_path}\n{content}\n")

# Output as system reminder
print("\n".join(context_injection), file=sys.stderr)

exit_with_code(0)
```

**Rationale:** Prevents loss of architectural rules after compaction

**Customization:**
- Add files critical to your project
- Modify injection format

#### 3.4.3 quality_gate.py

**Trigger:** Pre-commit (before git commit)
**Purpose:** Final checks before allowing commit

**Pseudocode:**
```python
# Check workflow completion
state = read_workflow_state()
if state:
    all_complete = all(state['steps'][step]['completed'] for step in state['steps'])
    if not all_complete:
        exit_with_code(2, "❌ BLOCKED: Workflow incomplete - finish all Skill("implement") steps")

# Check for TODO/FIXME in staged files
staged_files = subprocess.run(['git', 'diff', '--cached', '--name-only'], capture_output=True, text=True).stdout.strip().split('\n')

for file_path in staged_files:
    if Path(file_path).exists():
        with open(file_path) as f:
            content = f.read()
        if re.search(r'\bTODO\b|\bFIXME\b', content):
            exit_with_code(1, f"⚠️  Warning: {file_path} contains TODO/FIXME comments")

exit_with_code(0, "✅ Quality gate passed")
```

**Configuration:**
- Runs automatically before commit
- Can be bypassed with `--no-verify` (not recommended)

**Customization:**
- Add custom quality checks (linting, security scans)
- Modify TODO/FIXME detection

---

## 4. Command Workflows

**Total:** 6 commands (high-level workflow orchestration)

Commands are AlgoChanakya's **unique feature** - CricApp has zero commands. Commands orchestrate multiple skills/agents into cohesive workflows.

### 4.1 Skill("implement") - 7-Step Mandatory Workflow

**File:** `.claude/skills/implement/SKILL.md`
**Purpose:** Primary workflow for all feature implementations

**When to use:**
- Any feature implementation
- Bug fixes requiring tests
- Refactoring tasks

**Enforcement:** Hooks block code changes until steps complete in order.

**Flow Diagram:**
```
┌──────────────────────────────────────────┐
│ Step 0: Pre-Execution Knowledge Check    │
│ - Query knowledge.db for known issues    │
│ - Review failure index                   │
│ - Initialize workflow state              │
└────────────────┬─────────────────────────┘
                 ▼
┌──────────────────────────────────────────┐
│ Step 1: Requirements/Clarification       │
│ - State understanding (2-3 sentences)    │
│ - Research codebase patterns             │
│ - Check docs                             │
│ - Ask clarifying questions               │
└────────────────┬─────────────────────────┘
                 ▼ (validate_workflow_step blocks until complete)
┌──────────────────────────────────────────┐
│ Step 2: Write/Update Tests               │
│ - Determine test layers (E2E/backend/UI) │
│ - Generate tests (e2e-test-generator)    │
│ - Record test files in state             │
└────────────────┬─────────────────────────┘
                 ▼ (validate_workflow_step blocks code until tests written)
┌──────────────────────────────────────────┐
│ Step 3: Implement Feature                │
│ - Follow broker abstraction              │
│ - Use centralized trading constants      │
│ - Follow folder structure rules          │
│ - Track files changed                    │
└────────────────┬─────────────────────────┘
                 ▼
┌──────────────────────────────────────────┐
│ Step 4: Run Targeted Tests               │
│ - Skill("auto-verify")                   │
│ - post_test_update records results       │
│ - verify_test_rerun verifies claims      │
└────────────────┬─────────────────────────┘
                 ▼
        ┌────────┴────────┐
        │ Tests pass?     │
        └────────┬────────┘
                 │
         ┌───────┴───────┐
         │ Yes           │ No
         ▼               ▼
┌─────────────────┐ ┌──────────────────────┐
│ Step 5:         │ │ Step 5: Fix Loop     │
│ Auto-complete   │ │ MANDATORY            │
└─────────────────┘ │ - Skill("fix-loop")  │
                    │ - Max 10 iterations  │
                    │ - Code review gate   │
                    │ - Record to DB       │
                    └──────────────────────┘
                             │
                             ▼
                    ┌──────────────────────┐
                    │ All tests pass?      │
                    └──────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────┐
│ Step 6: Visual Verification              │
│ - Capture screenshots (UI changes)       │
│ - Document API responses (backend)       │
│ - post_screenshot_resize auto-resizes    │
└────────────────┬─────────────────────────┘
                 ▼
┌──────────────────────────────────────────┐
│ Step 7: Post-Fix Pipeline (MANDATORY)    │
│ - Skill("post-fix-pipeline")             │
│ - Regression tests                       │
│ - Full test suite                        │
│ - Update docs (docs-maintainer)          │
│ - Git commit (git-manager)               │
└────────────────┬─────────────────────────┘
                 ▼
┌──────────────────────────────────────────┐
│ Post-Workflow: Learning Reflection       │
│ - Skill("reflect", args="session")       │
│ - Update knowledge.db                    │
│ - Synthesize new rules (if threshold)    │
└──────────────────────────────────────────┘
```

**Skills Called:**
- `auto-verify` (Step 4)
- `e2e-test-generator` (Step 2)
- `vitest-generator` (Step 2)
- `fix-loop` (Step 5, if tests fail)
- `post-fix-pipeline` (Step 7)
- `reflect` (Post-workflow)
- `docs-maintainer` (Step 7, via post-fix-pipeline)

**Agents Called:**
- `debugger` (Step 5, via fix-loop)
- `code-reviewer` (Step 5, via fix-loop)
- `git-manager` (Step 7, via post-fix-pipeline)
- `tester` (Step 7, via post-fix-pipeline if full suite fails)

**Budget:**
- Total time: ~30-60 minutes (depending on test suite size)
- Fix loop: 10 iterations max
- Regression tests: 3 attempts max

**Example Invocation:**
```
User: "Add a kill switch button to the AutoPilot dashboard"

Claude: I understand you want to add a kill switch button to AutoPilot.
I see there's already a kill_switch.py in backend/app/services/autopilot/.

Questions:
1. Should it exit positions or just cancel pending orders?
2. Add to existing AutoPilot screen or new modal?

[User responds...]

Claude: Starting Skill("implement") workflow...

Step 1: ✅ Requirements understood
Step 2: Generating E2E test... Skill("e2e-test-generator", args="autopilot kill-switch happy")
Step 3: Implementing feature...
  - backend/app/services/autopilot/kill_switch.py (updated)
  - frontend/src/components/autopilot/KillSwitchButton.vue (new)
  - backend/app/api/routes/autopilot.py (new endpoint)
Step 4: Running tests... Skill("auto-verify")
  ✅ E2E: 5/5 passed
  ✅ Backend: 12/12 passed
Step 5: (skipped - all tests passed)
Step 6: Capturing screenshots...
Step 7: Skill("post-fix-pipeline")
  ✅ Regression tests passed
  ✅ Full test suite passed
  ✅ Docs updated
  ✅ Committed: feat(autopilot): add kill switch button

✅ Skill("implement") complete!
```

---

### 4.2 Skill("fix-loop") - Iterative Fix Cycle

**File:** `.claude/skills/fix-loop/SKILL.md`
**Purpose:** Fix failing tests with thinking escalation + code review gates

**When to use:**
- Automatically invoked by `Skill("implement")` Step 5 when tests fail
- Can be invoked standalone for any bug fix
- When you have failing tests that need systematic debugging

**Integration:** Reads strategies from `knowledge.db`, records every attempt, updates strategy scores

**Algorithm:**
```
INIT:
  - Read workflow state (current iteration count)
  - Query knowledge.db for ranked strategies
  - Set thinking depth based on iteration

LOOP (max 10 iterations):
  1. Identify failing tests (parse output)
  2. Select fix strategy:
     a. Known strategies from knowledge.db (ranked by success rate)
     b. Error type heuristics (fallback)
     c. Launch debugger agent (if strategies exhausted)
  3. Apply thinking escalation:
     - Iteration 1: Normal analysis
     - Iterations 2-3: Launch debugger agent with ThinkHard
     - Iterations 4+: Launch debugger agent with UltraThink
  4. Generate fix
  5. Run code review gate (code-reviewer agent):
     - Check broker abstraction compliance
     - Check trading constants compliance
     - Check folder structure compliance
     - Check no test skipping/weakening
     - BLOCK if Critical/High severity issues found
  6. Apply fix (if approved)
  7. Run tests
  8. Record outcome to knowledge.db:
     - update_strategy_score()
     - record_attempt()
  9. Exit if all pass, continue if fail, error if stuck

STUCK conditions:
  - 10 iterations reached
  - Same error 3x with different strategies
  - All strategies exhausted (scores < 0.1)
```

**Thinking Escalation:**

| Iteration | Mode | Description | Time Budget |
|-----------|------|-------------|-------------|
| 1 | Normal | Default Claude thinking | ~30s |
| 2-3 | ThinkHard | Debugger agent with extended thinking | ~2min |
| 4+ | UltraThink | Maximum depth, analyze previous attempts | ~5min |

**Prohibited Actions:**

The fix-loop enforces these prohibitions via code-reviewer agent:

❌ **NEVER Skip Tests**
```python
@pytest.mark.skip("Flaky test")  # BLOCKED
test.skip('Not working')         # BLOCKED
```

❌ **NEVER Weaken Assertions**
```python
# OLD: assert result == 5
# NEW: assert result >= 5  # BLOCKED - weakening!
```

❌ **NEVER Delete Tests** (unless user explicitly requests)

**Code Review Gate:**

Every fix passes through code-reviewer agent:

```
Task(
  subagent_type="general-purpose",
  prompt="""You are a Code-Reviewer Agent for AlgoChanakya.
  Follow instructions in .claude/agents/code-reviewer.md.

  Review this fix for compliance:
  File: {file_path}
  Fix: {fix_description}

  Diff:
  ```
  {diff}
  ```

  Check:
  1. Broker abstraction (no direct KiteConnect/SmartAPI)
  2. Trading constants (no hardcoded lot sizes)
  3. Folder structure (services in subdirectories)
  4. Data-testid (all interactive elements tagged)
  5. Async (all SQLAlchemy uses async/await)
  6. Security (no credentials in code)
  7. Prohibited (no test skipping/weakening/deletion)

  Return: APPROVED or FLAGGED(severity, issue)
  """
)
```

**If FLAGGED:** Reject fix, try next strategy
**If APPROVED:** Apply fix and re-run tests

**Knowledge.db Integration:**

```python
# Read ranked strategies
from db_helper import get_strategies
strategies = get_strategies("selector_not_found")
# Returns: [{"id": 1, "name": "...", "current_score": 0.85, "steps": [...]}, ...]

# Record attempt
from db_helper import record_attempt, update_strategy_score
record_attempt(
    error_pattern_id=error_id,
    strategy_id=strategy['id'],
    outcome='success',  # or 'failure'
    fix_description="Updated data-testid from 'exit-confirm' to 'positions-exit-confirm'"
)

# Update strategy score (with time decay formula)
update_strategy_score(strategy_id=strategy['id'])
```

**Cascade Handling:**

Fixes can trigger new failures (cascade). Handle up to depth 2:

```python
cascade_depth = 0
MAX_CASCADE_DEPTH = 2

while has_failures and iteration < 10:
    fix_result = apply_fix()

    if fix_result.new_failures != previous_failures:
        cascade_depth += 1
        if cascade_depth > MAX_CASCADE_DEPTH:
            break  # Prevent infinite loop
```

**Output Format:**

```
✅ Fix loop completed successfully!

Iterations: 3
Fixes applied: 2
Tests passed: 5/5

Changes:
  - tests/e2e/specs/positions/positions.happy.spec.js: Updated data-testid
  - backend/app/api/routes/positions.py: Fixed broker adapter usage

All tests now passing.
```

**Or on failure:**

```
❌ Fix loop failed after 10 iterations.

Remaining failures:
  - tests/e2e/specs/positions/positions.happy.spec.js:45 - Timeout waiting for selector
  - backend/tests/autopilot/test_kill_switch.py::test_emergency_exit - AssertionError

Last strategy attempted: "Update data-testid" (current_score: 0.45)

User intervention required.
```

---

### 4.3 post-fix-pipeline - Final Verification + Commit

**File:** `.claude/skills/post-fix-pipeline/SKILL.md`
**Purpose:** Final verification, documentation update, and git commit
**When to use:** Automatically invoked by `Skill("implement")` Step 7 (MANDATORY)

**Flow:**
1. **Gate check:** Skip if no fixes applied
2. **Regression tests:** Re-run affected tests, auto-fix if fail (max 3 attempts)
3. **Full test suite:** Run all tests, launch tester agent on failure
4. **Documentation:** Invoke docs-maintainer skill
5. **Git commit:** Delegate to git-manager agent

**Hard blocks:**
- Commit blocked if regression tests fail after max attempts
- Commit blocked if full test suite fails after max attempts

---

### 4.4 run-tests - Multi-Layer Test Runner

**File:** `.claude/skills/run-tests/SKILL.md`
**Purpose:** Run E2E, backend, and frontend tests in sequence
**Layers:** Playwright (E2E) → pytest (backend) → Vitest (frontend)

---

### 4.5 fix-issue - Fix GitHub Issue

**File:** `.claude/skills/fix-issue/SKILL.md`
**Purpose:** Fetch GitHub issue, analyze, fix, and link commit to issue
**Uses:** `gh` CLI for issue management

---

### 4.6 reflect - Learning + Self-Modification

**File:** `.claude/skills/reflect/SKILL.md`
**Purpose:** Learning reflection and self-modification
**Modes:**
- `session` - Read-only reflection, update knowledge.db
- `modify` - Update skills/hooks based on learnings

---

## 5. Agent Automations

**Total:** 5 agents (all with persistent memory)

### 5.1 Model Assignment Strategy

| Agent | Model | Rationale |
|-------|-------|-----------|
| code-reviewer | inherit | Fast checks, inherits from parent |
| debugger | sonnet | Complex analysis, needs full capability |
| git-manager | inherit | Simple git operations |
| planner-researcher | sonnet | Strategic planning |
| tester | sonnet | Test suite analysis |

### 5.2 Knowledge Accumulation Pattern

All 5 agents have persistent memory files in `.claude/agents/memory/{agent}.md`:

**Before task:**
```python
memory = read_agent_memory(agent_name)
# Inject into agent prompt
```

**After task:**
```python
append_agent_memory(agent_name, section="Decisions Made", entry="""
- 2026-02-14: Fixed broker abstraction violation in positions.py
  - Issue: Direct KiteConnect import
  - Solution: Used get_broker_adapter() factory
  - Files: backend/app/api/routes/positions.py
""")
```

### 5.3 Per-Agent Details

#### code-reviewer

- **Purpose:** Validate fixes against architectural rules
- **Checks:** 7 categories (broker abstraction, trading constants, folder structure, data-testid, async, security, prohibited)
- **Memory sections:** Common Violations, Approved Patterns, Edge Cases

#### debugger

- **Purpose:** Root cause analysis with thinking escalation
- **Capabilities:** Playwright trace analysis, FastAPI async debugging, Vue reactivity debugging, WebSocket debugging
- **Memory sections:** Root Causes by Category, Successful Fix Strategies, Failed Approaches, Flaky Tests

#### git-manager

- **Purpose:** Conventional commits + secret scanning
- **Memory sections:** Commit Patterns, Rejected Commits

#### planner-researcher

- **Purpose:** Feature planning and design
- **Memory sections:** Architecture Decisions, Design Patterns

#### tester

- **Purpose:** Test suite diagnosis
- **Memory sections:** Test Failures Resolved, Test Patterns

---

## 6. Skill Automations

**Total:** 21 skills grouped by category

### 6.1 Core Workflow Skills (7)

| Skill | Trigger | Purpose | Reference Files |
|-------|---------|---------|-----------------|
| `auto-verify` | After code changes | Test changes immediately | 3 files (SKILL.md + 2 refs) |
| `docs-maintainer` | After code changes | Update docs | 6 files (SKILL.md + 5 refs) |
| `learning-engine` | Manual | Record errors, rank strategies | 5 files (SKILL.md + 4 refs) |
| `health-check` | Session start / manual | 7-step codebase scan | 2 files (SKILL.md + 1 ref) |
| `test-fixer` | Test failures | Diagnose + suggest fixes | 2 files (SKILL.md + 1 ref) |
| `save-session` | Manual | Save context | 2 files (SKILL.md + 1 ref) |
| `start-session` | Manual | Resume context | 2 files (SKILL.md + 1 ref) |

### 6.2 Code Generation Skills (3)

| Skill | Purpose | Reference Files |
|-------|---------|-----------------|
| `e2e-test-generator` | Generate Playwright tests with Page Objects | 4 files |
| `vitest-generator` | Generate Vitest unit tests | 2 files |
| `vue-component-generator` | Create Vue 3 components/Pinia stores | 5 files |

### 6.3 Domain-Specific Skills (3)

| Skill | Purpose | Reference Files |
|-------|---------|-----------------|
| `autopilot-assistant` | AutoPilot strategy configuration | 5 files |
| `trading-constants-manager` | Enforce centralized trading constants | 2 files |
| `browser-testing` | Browser automation | 4 files |

### 6.4 Broker Expert Skills (6)

All broker experts follow the same pattern:
- Authentication flow guidance
- Endpoints catalog
- WebSocket protocol
- Error codes reference
- Symbol format conversion

| Skill | Broker | Reference Files (each) |
|-------|--------|------------------------|
| `smartapi-expert` | Angel One | 6 files (SKILL.md + 5 refs) |
| `zerodha-expert` | Zerodha | 11 files |
| `upstox-expert` | Upstox | 6 files |
| `dhan-expert` | Dhan | 6 files |
| `fyers-expert` | Fyers | 6 files |
| `paytm-expert` | Paytm Money | 6 files |

---

## 7. Learning System

**Database:** `.claude/learning/knowledge.db` (SQLite)
**Schema:** `.claude/learning/schema.sql`
**Helper:** `.claude/learning/db_helper.py` (759 lines)

### 7.1 Database Schema (6 Tables)

**error_patterns** - Deduplicated errors by fingerprint
```sql
id, fingerprint (SHA256), error_type, message_pattern, file_pattern,
first_seen, last_seen, occurrence_count, auto_resolved_count, manual_resolved_count
```

**fix_strategies** - Ranked approaches for each error type
```sql
id, name, error_type, description, steps (JSON), preconditions (JSON),
current_score (0.0-1.0), success_count, failure_count, total_attempts,
avg_time_seconds, source (seeded/learned/synthesized), created_at, last_used
```

**fix_attempts** - Every fix try with outcome
```sql
id, error_pattern_id, strategy_id, session_id, file_path, error_message,
fix_description, outcome (success/failure/partial/reverted), duration_seconds,
git_commit_hash, was_reverted, created_at
```

**file_risk_scores** - Track error-prone files
```sql
id, file_path, error_count, fix_count, revert_count, last_error,
risk_score (calculated), updated_at
```

**synthesized_rules** - Auto-generated patterns from successful strategies
```sql
id, rule_name, error_type, condition_pattern, action_pattern,
confidence (0.0-1.0), evidence_count, markdown_content, created_at, superseded_by
```

**session_metrics** - Per-session tracking
```sql
id, session_id, started_at, ended_at, total_errors_encountered,
total_auto_resolved, total_manual_resolved, total_strategies_tried,
new_patterns_discovered, rules_synthesized
```

### 7.2 Error Fingerprinting

**Algorithm:**
```python
def fingerprint(error_type: str, message: str, file_path: Optional[str]) -> str:
    # Normalize message
    norm_msg = message
    norm_msg = re.sub(r'\bline \d+\b', 'line N', norm_msg)          # line 42 → line N
    norm_msg = re.sub(r"'[^']*'", "'X'", norm_msg)                  # 'value' → 'X'
    norm_msg = re.sub(r'\b\d{4}-\d{2}-\d{2}', 'DATE', norm_msg)     # dates → DATE
    norm_msg = re.sub(r'\d+', 'N', norm_msg)                        # numbers → N

    # Normalize file path to pattern
    if file_path:
        norm_file = re.sub(r'/[^/]+\.py$', '/*.py', file_path)      # foo.py → *.py

    # SHA256 hash
    raw = f"{error_type}|{norm_msg}|{norm_file}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

**Purpose:** Group similar errors together despite minor variations (line numbers, variable names)

### 7.3 Strategy Ranking Formula

**Components:**
```python
raw_success_rate = success_count / max(total_attempts, 1)

# Time decay (recent use weighted 2x more than old)
if last_used:
    days_since = (now - last_used).days
    recency_factor = 1.0 / (1.0 + days_since * 0.1)
else:
    recency_factor = 0.5  # Never used

# Confidence (more attempts = higher confidence)
confidence_factor = min(total_attempts / 10.0, 1.0)

# Final score
current_score = (
    0.6 * raw_success_rate +
    0.3 * recency_factor +
    0.1 * confidence_factor
)
current_score = max(0.0, min(1.0, current_score))  # Clamp to [0, 1]
```

**Weights:**
- 60% success rate (most important)
- 30% recency (prefer recently used strategies)
- 10% confidence (prefer well-tested strategies)

### 7.4 Rule Synthesis

**Threshold:** ≥70% confidence, ≥5 successful attempts

```python
def synthesize_rules(min_confidence=0.7, min_evidence=5):
    # Find eligible strategies
    strategies = get_strategies_with_high_success_rate(min_confidence, min_evidence)

    for strategy in strategies:
        confidence = strategy['success_count'] / strategy['total_attempts']

        # Generate markdown rule
        markdown_content = f"""
## {strategy['name']}

**Error Type:** {strategy['error_type']}
**Confidence:** {confidence:.1%} ({strategy['success_count']}/{strategy['total_attempts']} attempts)

**Description:** {strategy['description']}

**When to Apply:**
- Error type matches `{strategy['error_type']}`
- Pattern successful in {strategy['success_count']} previous cases

**Steps:**
{format_steps(strategy['steps'])}

**Auto-synthesized:** {now}
"""

        # Insert into synthesized_rules table
        insert_rule(strategy, confidence, markdown_content)
```

**Purpose:** Automatically create documentation for proven fix patterns

---

## 8. Settings & Permissions

**File:** `.claude/settings.json`

### 8.1 Annotated Settings

```json
{
  "permissions": {
    "allow": [
      "Bash(python -m venv:*)",    // Allow venv creation
      "Bash(dir:*)",                // Allow directory listing
      "Bash(python .claude/hooks/*)" // Allow hook execution
    ],
    "deny": [
      // CRITICAL: Production folder (on same machine)
      "Write(C:\\Apps\\algochanakya/**)",
      "Edit(C:\\Apps\\algochanakya/**)",
      "Read(C:\\Apps\\algochanakya/**)",
      "Bash(*C:\\Apps\\algochanakya*)",

      // Environment files (secrets)
      "Write(**/.env)",
      "Edit(**/.env)",
      "Write(**/.env.*)",
      "Edit(**/.env.*)",

      // Learning database (managed by hooks)
      "Write(**/knowledge.db)",
      "Edit(**/knowledge.db)",

      // Workflow state (managed by hooks)
      "Write(**/workflow-state.json)",
      "Edit(**/workflow-state.json)",

      // Auth files (sensitive)
      "Write(**/.auth-state.json)",
      "Edit(**/.auth-state.json)",
      "Write(**/.auth-token)",
      "Edit(**/.auth-token)")
    ],
    "ask": []  // Nothing requires explicit ask (all handled by hooks)
  },
  "hooks": {
    "PreToolUse": [...],   // See section 3.2
    "PostToolUse": [...],  // See section 3.3
    "Session": [...]       // See section 3.4
  }
}
```

### 8.2 Defense-in-Depth Strategy (4 Layers)

1. **UI-level permissions** (settings.json `deny` list)
2. **PreToolUse hooks** (protect_sensitive_files, guard_folder_structure, validate_workflow_step)
3. **Code review gates** (code-reviewer agent validates all fixes)
4. **User approval** (for risky operations)

**Rationale:** Multiple layers prevent accidental damage even if one layer fails

---

## 9. CI/CD Pipeline

**Location:** `.github/workflows/`

### 9.1 Workflows (3)

**backend-tests.yml**
```yaml
on: [push, pull_request]
services:
  postgres:
    image: postgres:15
  redis:
    image: redis:7
steps:
  - pytest backend/tests/ -v --cov
```

**e2e-tests.yml**
```yaml
on: [push, pull_request]
timeout-minutes: 30
steps:
  - Start backend (port 8001)
  - Start frontend (port 5173)
  - npx playwright test
  - Upload Allure report
```

**deploy.yml**
```yaml
on:
  push:
    branches: [main]
steps:
  - Deploy to production
  - Run smoke tests
```

### 9.2 Hook-CI Parity Table

| Check | Hook | CI Workflow | Status |
|-------|------|-------------|--------|
| Folder structure | guard_folder_structure.py | ❌ | **GAP** |
| Test execution | verify_test_rerun.py | ✅ backend-tests.yml, e2e-tests.yml | ✅ |
| Code formatting | auto_format.py | ❌ | **GAP** |
| Protected files | protect_sensitive_files.py | N/A (local only) | N/A |
| Workflow steps | validate_workflow_step.py | N/A (local only) | N/A |

**Recommendation:** Add `hook-parity.yml` workflow to enforce hooks match CI (see Gap Report)

---

## 10. Code Generation Workflow

### 10.1 Vue Component Generation

```
Skill("vue-component-generator", args="ExitPositionModal component")
  ↓
1. Read component templates
2. Generate component with:
   - Props validation
   - Emits declaration
   - data-testid attributes ([screen]-[component]-[element])
   - Composition API
3. Use trading constants imports (not hardcoded)
4. Follow folder structure (src/components/{screen}/)
```

### 10.2 E2E Test Generation

```
Skill("e2e-test-generator", args="positions exit-modal happy")
  ↓
1. Read Page Object Model base (BasePage.js)
2. Generate test with:
   - Import from auth.fixture.js (NOT @playwright/test)
   - Use authenticatedPage fixture
   - Use data-testid selectors ONLY
   - Pattern: [screen]-[component]-[element]
3. Place in tests/e2e/specs/positions/
```

### 10.3 Unit Test Generation

```
Skill("vitest-generator", args="ExitPositionModal unit")
  ↓
1. Read test patterns
2. Generate test with:
   - Mount component
   - Test props/events/reactivity
   - Mock API calls
3. Place in frontend/src/components/positions/ExitPositionModal.spec.js
```

---

## 11. Session Management

### 11.1 Session Lifecycle

```
┌──────────────────────┐
│ start-session        │
│ (load context)       │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Work on task         │
│ (workflow state      │
│  tracks progress)    │
└──────────┬───────────┘
           ▼
    ┌──────┴──────┐
    │ Save?       │
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │ Yes         │ No (session ends, state cleared)
    ▼
┌──────────────────────┐
│ save-session         │
│ (archive state)      │
└──────────────────────┘
```

### 11.2 Session File Format

```markdown
# Session: Feature Implementation

**Date:** 2026-02-14
**Task:** Add kill switch to AutoPilot
**Workflow State:** 20260214-153045

## Progress

- ✅ Step 1: Requirements clarified
- ✅ Step 2: Tests written
- ✅ Step 3: Feature implemented
- 🔄 Step 4: Tests running...

## Files Changed

- backend/app/services/autopilot/kill_switch.py
- frontend/src/components/autopilot/KillSwitchButton.vue

## Notes

- User wants kill switch to exit positions, not just cancel orders
- Added to existing AutoPilot dashboard (no new modal)
```

### 11.3 Context Restoration Logic

1. Read session file metadata
2. Restore workflow-state.json from archived copy
3. Re-inject critical context (rules.md, CLAUDE.md)
4. Resume from last completed step

---

## 12. Debugging Workflow

### 12.1 8-Step RCA Process

When using debugger agent:

1. **Identify symptom** - What failed? (test, build, runtime error)
2. **Classify error type** - ImportError, TestFailure, DatabaseError, etc.
3. **Analyze trace** - Playwright trace, stack trace, logs
4. **Form hypothesis** - Root cause theory
5. **Verify hypothesis** - Read code, check assumptions
6. **Identify fix** - Specific code change needed
7. **Verify fix** - How to test the fix
8. **Document** - Add to agent memory

### 12.2 4 Escalation Tiers

| Tier | Trigger | Action | Time Budget |
|------|---------|--------|-------------|
| 1: Normal | Iteration 1 | Direct fix attempt | ~30s |
| 2: ThinkHard | Iterations 2-3 | Launch debugger agent | ~2min |
| 3: UltraThink | Iterations 4+ | Max depth analysis | ~5min |
| 4: Human | 10 iterations / stuck | Ask user for help | N/A |

### 12.3 /debug-log Integration

The debug workflow integrates with workflow logs:

```bash
# View recent events
tail -50 .claude/logs/workflow-sessions.log | jq

# Filter by event type
cat .claude/logs/workflow-sessions.log | jq 'select(.type == "test_run")'

# Find failing tests
cat .claude/logs/workflow-sessions.log | jq 'select(.result == "fail")'
```

### 12.4 Knowledge.db Strategy Lookup

Before debugging, check known strategies:

```python
from db_helper import get_strategies

# Get strategies for error type
strategies = get_strategies("selector_not_found", limit=5)

for strategy in strategies:
    print(f"{strategy['name']} (score: {strategy['current_score']:.2f})")
    print(f"  Steps: {strategy['steps']}")
    print(f"  Success rate: {strategy['success_count']}/{strategy['total_attempts']}")
```

---

## 13. Integration Patterns

### 13.1 Hook + Agent Pattern

**Example:** validate_workflow_step hook + code-reviewer agent

```
User attempts to Write code
  ↓
validate_workflow_step.py (PreToolUse hook)
  - Checks: Step 2 (tests) complete?
  - If No: BLOCK (exit code 2)
  - If Yes: Allow
  ↓
Code written
  ↓
Skill("fix-loop") invoked (if tests fail)
  ↓
code-reviewer agent launched for every fix
  - Validates broker abstraction compliance
  - Validates trading constants compliance
  - Returns: APPROVED or FLAGGED
  ↓
If FLAGGED: Reject fix, try next strategy
If APPROVED: Apply fix
```

### 13.2 Hook + Knowledge.db Pattern

**Example:** post_skill_learning hook + knowledge.db

```
Skill("test-fixer") executes
  ↓
test-fixer analyzes failure, applies fix
  ↓
post_skill_learning.py (PostToolUse hook)
  - Parses skill output
  - Detects outcome (RESOLVED, FAILED)
  - Extracts error_type, component, workaround_used
  ↓
record_error(error_type, message, file_path)
  - Generates fingerprint
  - Upserts to error_patterns table
  - Returns error_pattern_id
  ↓
record_attempt(error_pattern_id, strategy_id, outcome='success')
  - Inserts to fix_attempts table
  - Updates strategy success/failure counts
  ↓
update_strategy_score(strategy_id)
  - Recalculates current_score using formula
  - Updates fix_strategies table
  ↓
synthesize_rules(min_confidence=0.7, min_evidence=5)
  - If threshold reached: create markdown rule
  - Insert to synthesized_rules table
```

### 13.3 Command + Skill + Agent Pattern

**Example:** Skill("implement") command

```
Skill("implement") invoked
  ↓
Step 1: Requirements (Claude direct)
  ↓
Step 2: Skill("e2e-test-generator")
  ↓
Step 3: Implement (Claude direct)
  ↓
Step 4: Skill("auto-verify")
  ↓
Step 5: Skill("fix-loop")
        ↓
        Launch debugger agent (if iteration 2+)
        ↓
        Launch code-reviewer agent (every fix)
        ↓
        Record to knowledge.db (hook)
  ↓
Step 6: Screenshots (Claude direct)
  ↓
Step 7: Skill("post-fix-pipeline")
        ↓
        Skill("docs-maintainer")
        ↓
        Launch git-manager agent
  ↓
Post: Skill("reflect")
```

### 13.4 Session + Hook Pattern

**Example:** Session resume + load_session_context hook

```
User resumes saved session
  ↓
load_session_context.py (Session hook)
  - Reads session file (.claude/sessions/{id}.md)
  - Extracts workflow state ID
  - Restores workflow-state.json from archive
  ↓
Claude receives restored context
  ↓
validate_workflow_step.py (PreToolUse hook)
  - Reads restored workflow-state.json
  - Enforces step order based on completed steps
  ↓
Work continues from where it left off
```

---

## 14. Customization Guide

### 14.1 How to Add a New Hook

**Steps:**
1. Create hook script: `.claude/hooks/my_new_hook.py`
2. Register in `.claude/settings.json`:
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Write",
           "hooks": [
             {
               "type": "command",
               "command": "python .claude/hooks/my_new_hook.py",
               "timeout": 5
             }
           ]
         }
       ]
     }
   }
   ```
3. Implement using `hook_utils.py`:
   ```python
   #!/usr/bin/env python3
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent))
   from hook_utils import parse_hook_input, exit_with_code

   hook_data = parse_hook_input()
   if not hook_data:
       exit_with_code(0, "No input")

   # Your logic here
   exit_with_code(0, "✅ Check passed")
   ```

### 14.2 How to Add a New Agent

**Steps:**
1. Create agent definition: `.claude/agents/my_agent.md`
2. Create memory file: `.claude/agents/memory/my_agent.md`
3. Document agent purpose, capabilities, memory sections
4. Invoke in skills/commands:
   ```python
   Task(
       subagent_type="general-purpose",
       model="sonnet",
       prompt="""You are MyAgent for AlgoChanakya.
       Follow instructions in .claude/agents/my_agent.md.

       Read .claude/agents/my_agent.md first, then:
       [Task description...]
       """
   )
   ```

### 14.3 How to Add a New Skill

**Steps:**
1. Create skill directory: `.claude/skills/my-skill/`
2. Create `SKILL.md` with skill definition
3. Create reference files in `references/` subdirectory
4. Register in CLAUDE.md:
   ```markdown
   - `my-skill`: Description of what skill does
   ```
5. Invoke via:
   ```python
   Skill("my-skill", args="optional arguments")
   ```

### 14.4 How to Add a New Command

**Steps:**
1. Create command file: `.claude/skills/my-skill/SKILL.md`
2. Document workflow steps, skills called, agents used
3. Add to CLAUDE.md:
   ```markdown
   - `/my-command`: Description
   ```
4. Invoke via:
   ```python
   Skill("my-command")  # Commands are invoked like skills
   ```

### 14.5 Tech Stack Notes

**Backend:**
- Python 3.11+
- FastAPI (async)
- SQLAlchemy (async)
- PostgreSQL 15+
- Redis 7+

**Frontend:**
- Vue 3 (Composition API)
- Vite
- Pinia (state management)
- Tailwind CSS 4

**Testing:**
- Playwright (E2E)
- pytest (backend)
- Vitest (frontend)

### 14.6 Anti-Patterns (8)

❌ **DON'T:**
1. Bypass hooks with `--no-verify`
2. Modify knowledge.db directly (use db_helper.py)
3. Edit workflow-state.json manually
4. Skip workflow steps
5. Hardcode broker-specific logic
6. Hardcode trading constants
7. Violate folder structure rules
8. Delete tests to make CI pass

✅ **DO:**
1. Let hooks enforce rules
2. Use db_helper.py for knowledge.db operations
3. Let hooks manage workflow state
4. Complete all workflow steps
5. Use broker abstractions
6. Use centralized trading constants
7. Follow folder structure
8. Fix tests, don't delete them

---

## Appendix: File Inventory

### Complete Automation File List

**Total:** ~123 files, ~7,500+ lines of automation code

#### Hooks (14 files + 1 shared library)
- `.claude/hooks/hook_utils.py` (725 lines)
- `.claude/hooks/protect_sensitive_files.py` (~50 lines)
- `.claude/hooks/guard_folder_structure.py` (~80 lines)
- `.claude/hooks/validate_workflow_step.py` (~150 lines)
- `.claude/hooks/verify_evidence_artifacts.py` (~60 lines)
- `.claude/hooks/post_test_update.py` (~120 lines)
- `.claude/hooks/verify_test_rerun.py` (~180 lines)
- `.claude/hooks/post_screenshot_resize.py` (~70 lines)
- `.claude/hooks/auto_fix_pattern_scan.py` (~100 lines)
- `.claude/hooks/log_workflow.py` (~50 lines)
- `.claude/hooks/post_skill_learning.py` (~140 lines)
- `.claude/hooks/auto_format.py` (~60 lines)
- `.claude/hooks/load_session_context.py` (~80 lines)
- `.claude/hooks/reinject_after_compaction.py` (~70 lines)
- `.claude/hooks/quality_gate.py` (~90 lines)

**Hooks subtotal:** ~2,025 lines

#### Commands (6 files)
- `.claude/skills/implement/SKILL.md` (~600 lines)
- `.claude/skills/fix-loop/SKILL.md` (~620 lines)
- `.claude/skills/post-fix-pipeline/SKILL.md` (~250 lines)
- `.claude/skills/run-tests/SKILL.md` (~180 lines)
- `.claude/skills/fix-issue/SKILL.md` (~150 lines)
- `.claude/skills/reflect/SKILL.md` (~200 lines)

**Commands subtotal:** ~2,000 lines

#### Agents (5 definitions + 5 memory files)
- `.claude/agents/code-reviewer.md` (~300 lines)
- `.claude/agents/debugger.md` (~500 lines)
- `.claude/agents/git-manager.md` (~200 lines)
- `.claude/agents/planner-researcher.md` (~250 lines)
- `.claude/agents/tester.md` (~300 lines)
- `.claude/agents/memory/*.md` (5 files, ~500 lines total)

**Agents subtotal:** ~2,050 lines

#### Skills (21 skills, ~110 files)
Each skill has SKILL.md + reference files (varies by skill)

**Major skills:**
- `auto-verify`: 3 files (~400 lines)
- `docs-maintainer`: 6 files (~550 lines)
- `learning-engine`: 5 files (~500 lines)
- `test-fixer`: 2 files (~250 lines)
- `e2e-test-generator`: 4 files (~500 lines)
- `vitest-generator`: 2 files (~250 lines)
- `vue-component-generator`: 5 files (~600 lines)
- `autopilot-assistant`: 5 files (~500 lines)
- `trading-constants-manager`: 2 files (~200 lines)
- Broker experts (6 skills): 36 files (~1,800 lines)
- Other skills: 40 files (~1,200 lines)

**Skills subtotal:** ~6,750 lines (estimate)

#### Learning System (3 files)
- `.claude/learning/schema.sql` (100 lines)
- `.claude/learning/db_helper.py` (759 lines)
- `.claude/learning/knowledge.db` (binary)

**Learning subtotal:** ~860 lines

#### Configuration & Rules (3 files)
- `.claude/settings.json` (~170 lines)
- `.claude/rules.md` (555 lines)
- `.claude/recommended-hooks.json` (~50 lines)

**Config subtotal:** ~775 lines

---

**GRAND TOTAL:** ~14,460 lines of automation code (excluding binary knowledge.db)

---

## Summary

AlgoChanakya's automation system is a sophisticated, multi-layered workflow engine with:

- **14 hooks** enforcing architectural rules and workflow steps
- **6 commands** orchestrating high-level workflows
- **5 agents** with persistent memory and knowledge accumulation
- **21 skills** for code generation, testing, and domain expertise
- **knowledge.db** learning system ranking fix strategies over time

**Key Differentiators:**
1. Workflow state machine (7-step implement)
2. Learning system (self-improving fix strategies)
3. Thinking escalation (Normal → ThinkHard → UltraThink)
4. Code review gates (every fix validated)
5. Independent test verification (anti-false-positive)
6. Evidence-based debugging (workflow logs + knowledge.db)
7. Domain expertise (6 broker experts for Indian trading)

**Getting Started:**
1. Start with `Skill("implement")` for any code change
2. Use `auto-verify` after modifications
3. Let hooks guide you through the workflow
4. Trust the learning system to improve over time

**Next Steps:**
- Read Gap Report: `docs/guides/AUTOMATION-GAP-REPORT.md`
- Review feature proposals: `docs/guides/AUTOMATION-FEATURE-PROPOSALS.md` (to be created)
- Explore skill definitions in `.claude/skills/*/SKILL.md`
- Review agent definitions in `.claude/agents/`

---

**End of Automation Workflows Guide**
**Version:** 2.0
**Last Updated:** February 14, 2026


