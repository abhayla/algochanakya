# /reflect - Learning + Self-Modification

**Purpose:** Capture outcomes to learning stores, synthesize rules, and optionally modify commands/hooks to improve workflow.

**Modes:**
- `session` - Capture outcomes, update knowledge.db, no file modifications (safe, default)
- `deep` - Analyze gaps + modify commands/hooks with safety protocol (requires user approval)
- `meta` - High-level convergence analysis across all modifications (read-only)
- `test-run` - Dry-run of deep mode (propose but don't apply)

**When to use:** After `/implement`, `/run-tests`, or `/fix-loop` completes.

---

## Mode: Session (Default - Safe)

**Purpose:** Capture outcomes and synthesize rules without modifying files.

### Algorithm

**1. Read workflow sessions log:**
```python
from pathlib import Path
import json

log_file = Path(".claude/logs/workflow-sessions.log")
sessions = []

with open(log_file) as f:
    for line in f:
        sessions.append(json.loads(line))

# Get sessions from last hour
recent_sessions = [s for s in sessions if is_recent(s['timestamp'], hours=1)]
```

**2. Group by outcome:**
```python
from collections import defaultdict

outcomes = defaultdict(list)

for session in recent_sessions:
    if session['type'] == 'test_run':
        outcome_key = (session['layer'], session['result'])
        outcomes[outcome_key].append(session)

    elif session['type'] == 'skill_invocation':
        outcome_key = (session['skill'], 'success' if session['succeeded'] else 'failure')
        outcomes[outcome_key].append(session)
```

**3. Update knowledge.db:**
```python
import sys
sys.path.insert(0, str(Path(".claude/learning")))
from db_helper import (
    record_error,
    record_attempt,
    update_strategy_score,
    synthesize_rules,
    get_stats
)

# For each failed test
for (layer, result), sessions in outcomes.items():
    if result == 'fail':
        for session in sessions:
            # Record error pattern
            error_id = record_error(
                error_type=detect_error_type(session),
                component=extract_component(session['target']),
                file_path=session['target'],
                error_message=extract_error_message(session),
                stack_trace=None
            )

# For each skill invocation
for (skill, outcome), sessions in outcomes.items():
    for session in sessions:
        # Update strategy scores
        strategy_id = session.get('strategy_id')
        if strategy_id:
            update_strategy_score(
                strategy_id=strategy_id,
                outcome='success' if outcome == 'success' else 'failure'
            )

# Attempt synthesis
print("\n🧠 Attempting rule synthesis...")
synthesized = synthesize_rules()

if synthesized:
    print(f"✨ Synthesized {len(synthesized)} new rules:")
    for rule in synthesized:
        print(f"  - {rule['description']}")
        print(f"    Confidence: {rule['confidence']:.1%}")
        print(f"    Evidence: {rule['evidence_count']} instances")
else:
    print("No rules reached synthesis threshold (≥70% confidence, ≥5 evidence).")
```

**4. Update failure-index.json:**
```python
from hook_utils import update_failure_index

for (layer, result), sessions in outcomes.items():
    if result == 'fail':
        for session in sessions:
            update_failure_index(
                skill='run-tests',
                issue_type=detect_error_type(session),
                outcome='FAILED',
                component=extract_component(session['target'])
            )
```

**5. Generate learning report:**
```python
stats = get_stats()

print("\n" + "="*60)
print("Learning Report")
print("="*60)
print(f"Knowledge DB stats:")
print(f"  Error patterns: {stats['error_patterns']}")
print(f"  Fix strategies: {stats['fix_strategies']}")
print(f"  Fix attempts: {stats['fix_attempts']}")
print(f"  Synthesized rules: {stats['synthesized_rules']}")
print()
print(f"Session outcomes:")
print(f"  Test runs: {len([s for s in recent_sessions if s['type'] == 'test_run'])}")
print(f"  Skill invocations: {len([s for s in recent_sessions if s['type'] == 'skill_invocation'])}")
print(f"  Success rate: {calculate_success_rate(recent_sessions):.1%}")
```

---

## Mode: Deep (Self-Modification with Safety)

**Purpose:** Analyze workflow gaps and modify commands/hooks to improve.

**⚠️ REQUIRES USER APPROVAL:** This mode modifies workflow files.

### Safety Protocol

**Before any modifications:**

1. **Create safety backup:**
   ```bash
   git stash push -m "reflect-deep-$(date +%Y%m%d-%H%M%S)" \
       .claude/commands/ \
       .claude/hooks/ \
       .claude/agents/
   ```

2. **Deny list (NEVER modify):**
   ```python
   DENY_LIST = [
       'CLAUDE.md',
       'conftest.py',
       '.claude/settings.local.json',
       '*.env',
       'alembic/versions/*',
       'notes'
   ]
   ```

3. **Limits:**
   - **Max files per session:** 5
   - **Max lines per file:** 50
   - **Max recursion depth:** 3 (deep → meta → convergence)

4. **Validation after each modification:**
   ```python
   import py_compile
   import json

   def validate_file(file_path):
       if file_path.endswith('.py'):
           # Validate Python syntax
           try:
               py_compile.compile(file_path, doraise=True)
           except py_compile.PyCompileError:
               print(f"❌ Python syntax error in {file_path}")
               return False

       elif file_path.endswith('.json'):
           # Validate JSON syntax
           try:
               with open(file_path) as f:
                   json.load(f)
           except json.JSONDecodeError:
               print(f"❌ JSON syntax error in {file_path}")
               return False

       elif file_path.endswith('.md'):
           # Basic markdown validation (check headings)
           with open(file_path) as f:
               content = f.read()
               if not any(line.startswith('#') for line in content.split('\n')):
                   print(f"⚠️  Warning: {file_path} has no headings")
                   # Non-blocking warning

       return True
   ```

5. **Revert on validation failure:**
   ```bash
   git checkout -- {file}
   ```

---

### Deep Mode Algorithm

**1. Analyze workflow gaps:**
```python
# Read recent sessions
sessions = read_recent_sessions(hours=24)

# Identify gaps
gaps = []

# Gap 1: Recurring failures with no auto-fix rule
failure_patterns = {}
for session in sessions:
    if session['type'] == 'test_run' and session['result'] == 'fail':
        key = (session['layer'], detect_error_type(session))
        failure_patterns[key] = failure_patterns.get(key, 0) + 1

for (layer, error_type), count in failure_patterns.items():
    if count >= 3:  # 3+ occurrences
        # Check if auto-fix rule exists
        rules = get_synthesized_rules(error_type=error_type)
        if not rules or rules[0]['confidence'] < 0.7:
            gaps.append({
                'type': 'missing_auto_fix',
                'layer': layer,
                'error_type': error_type,
                'occurrences': count
            })

# Gap 2: Hook not catching known issue
for session in sessions:
    if session['type'] == 'skill_invocation' and session['skill'] == 'fix-loop':
        # Check if issue should have been caught by hook
        if is_preventable_by_hook(session):
            gaps.append({
                'type': 'hook_gap',
                'issue': extract_issue(session)
            })

# Gap 3: Command inefficiency
command_durations = defaultdict(list)
for session in sessions:
    if session['type'] == 'skill_invocation':
        command_durations[session['skill']].append(session.get('duration', 0))

for skill, durations in command_durations.items():
    avg_duration = sum(durations) / len(durations)
    if avg_duration > 300:  # 5+ minutes average
        gaps.append({
            'type': 'slow_command',
            'skill': skill,
            'avg_duration': avg_duration
        })

print(f"\n🔍 Identified {len(gaps)} workflow gaps:")
for gap in gaps:
    print(f"  - {gap['type']}: {gap}")
```

**2. Propose modifications:**
```python
modifications = []

for gap in gaps:
    if gap['type'] == 'missing_auto_fix':
        # Propose adding auto-fix pattern to post_test_update.py
        modification = {
            'file': '.claude/hooks/post_test_update.py',
            'action': 'add_auto_fix_pattern',
            'pattern': gap['error_type'],
            'code': generate_auto_fix_code(gap)  # [PLANNED - pseudocode]
        }
        modifications.append(modification)

    elif gap['type'] == 'hook_gap':
        # Propose adding validation to PreToolUse hook
        modification = {
            'file': '.claude/hooks/validate_workflow_step.py',
            'action': 'add_validation',
            'issue': gap['issue'],
            'code': generate_validation_code(gap)  # [PLANNED - pseudocode]
        }
        modifications.append(modification)

    elif gap['type'] == 'slow_command':
        # Propose optimization to command
        modification = {
            'file': f'.claude/commands/{gap["skill"]}.md',
            'action': 'optimize',
            'issue': f"Average duration {gap['avg_duration']:.0f}s",
            'suggestion': generate_optimization_suggestion(gap)  # [PLANNED - pseudocode]
        }
        modifications.append(modification)

print(f"\n📝 Proposed modifications: {len(modifications)}")
for mod in modifications:
    print(f"  - {mod['file']}: {mod['action']}")
```

**3. Ask user approval:**
```python
from hook_utils import AskUserQuestion

answer = AskUserQuestion(
    questions=[{
        "question": f"Apply {len(modifications)} proposed modifications to improve workflow?",
        "header": "Modifications",
        "multiSelect": False,
        "options": [
            {
                "label": "Apply all",
                "description": "Apply all proposed modifications with safety checks"
            },
            {
                "label": "Review first",
                "description": "Show detailed diffs before applying"
            },
            {
                "label": "Skip",
                "description": "Don't apply modifications this session"
            }
        ]
    }]
)

if answer == "Skip":
    print("Skipping modifications.")
    return

if answer == "Review first":
    # Show detailed diffs
    for mod in modifications:
        print(f"\n{'='*60}")
        print(f"File: {mod['file']}")
        print(f"Action: {mod['action']}")
        print(f"{'='*60}")
        print(mod['code'])

    # Ask again
    confirm = AskUserQuestion(
        questions=[{
            "question": "Apply modifications?",
            "header": "Confirm",
            "multiSelect": False,
            "options": [
                {"label": "Yes", "description": "Apply all"},
                {"label": "No", "description": "Cancel"}
            ]
        }]
    )

    if confirm == "No":
        print("Cancelled.")
        return
```

**4. Apply modifications with safety:**
```python
# Create safety backup
Bash(command='git stash push -m "reflect-deep-$(date +%Y%m%d-%H%M%S)" .claude/')

modified_files = []
failed_files = []

for mod in modifications:
    file_path = Path(mod['file'])

    # Check deny list
    if any(denied in str(file_path) for denied in DENY_LIST):
        print(f"❌ {file_path} is on deny list, skipping")
        continue

    # Apply modification
    try:
        if mod['action'] == 'add_auto_fix_pattern':
            # Use Edit tool to add pattern
            Edit(
                file_path=str(file_path),
                old_string=find_insertion_point(file_path),
                new_string=mod['code']
            )

        elif mod['action'] == 'optimize':
            # Use Edit tool to optimize
            Edit(
                file_path=str(file_path),
                old_string=mod['old_code'],
                new_string=mod['new_code']
            )

        # Validate
        if not validate_file(file_path):
            # Revert
            Bash(command=f'git checkout -- {file_path}')
            failed_files.append(file_path)
            print(f"❌ Validation failed for {file_path}, reverted")
        else:
            modified_files.append(file_path)
            print(f"✅ Modified {file_path}")

    except Exception as e:
        print(f"❌ Error modifying {file_path}: {str(e)}")
        failed_files.append(file_path)

print(f"\n✅ Successfully modified {len(modified_files)} files")
print(f"❌ Failed to modify {len(failed_files)} files")

# Record modifications
record_modifications(modified_files, modifications)
```

**5. Check for degradation:**
```python
# Run smoke tests
print("\n🧪 Running smoke tests to verify no degradation...")

# Test: Hooks load correctly
result = Bash(command="python .claude/hooks/hook_utils.py")
if result.returncode != 0:
    print("❌ hook_utils.py failed to load")
    revert_all_modifications()
    return

# Test: Commands parse correctly
for cmd_file in Path(".claude/commands/").glob("*.md"):
    # Basic markdown validation
    if not validate_file(cmd_file):
        print(f"❌ {cmd_file} validation failed")
        revert_all_modifications()
        return

print("✅ Smoke tests passed")
```

---

### Deep Mode Recursion

**Auto-escalate to meta mode if:**
- **Recursion depth < 3**
- **Modifications applied > 5 times in last 30 days**

```python
recursion_state_file = Path(".claude/logs/learning/recursion-state.json")  # [PLANNED - created at runtime by reflect deep mode]

# Load state
if recursion_state_file.exists():
    with open(recursion_state_file) as f:
        state = json.load(f)
else:
    state = {'depth': 0, 'last_meta': None}

# Check escalation criteria
if state['depth'] < 3 and modification_count_last_30_days() > 5:
    print("\n🔄 Escalating to meta mode (high modification frequency)")
    Skill("reflect", args="meta")
    state['depth'] += 1
else:
    state['depth'] = 0

# Save state
with open(recursion_state_file, 'w') as f:
    json.dump(state, f)
```

---

## Mode: Meta (Convergence Analysis)

**Purpose:** High-level analysis of modification patterns and convergence.

**Read-only:** No file modifications, only analysis.

### Algorithm

**1. Load modification history:**
```python
modifications_file = Path(".claude/logs/learning/modifications.json")  # [PLANNED - created at runtime by reflect deep mode]

with open(modifications_file) as f:
    history = json.load(f)

# Group by file
by_file = defaultdict(list)
for mod in history:
    by_file[mod['file']].append(mod)
```

**2. Detect patterns:**
```python
patterns = []

# Pattern 1: Same file modified repeatedly
for file, mods in by_file.items():
    if len(mods) >= 3:
        patterns.append({
            'type': 'repeated_modification',
            'file': file,
            'count': len(mods),
            'actions': [m['action'] for m in mods]
        })

# Pattern 2: Same action across multiple files
by_action = defaultdict(list)
for mod in history:
    by_action[mod['action']].append(mod['file'])

for action, files in by_action.items():
    if len(files) >= 3:
        patterns.append({
            'type': 'repeated_action',
            'action': action,
            'files': files
        })

# Pattern 3: Revert pattern (modification → revert → remodification)
for file, mods in by_file.items():
    reverted_count = sum(1 for m in mods if m.get('reverted', False))
    if reverted_count > 0:
        patterns.append({
            'type': 'revert_pattern',
            'file': file,
            'revert_count': reverted_count,
            'total_mods': len(mods)
        })
```

**3. Assess convergence:**
```python
# Convergence metric: fewer modifications over time
recent_mods = [m for m in history if is_recent(m['timestamp'], days=7)]
older_mods = [m for m in history if is_recent(m['timestamp'], days=30) and not is_recent(m['timestamp'], days=7)]

if len(recent_mods) < len(older_mods) / 3:
    convergence = "CONVERGING"
elif len(recent_mods) > len(older_mods) * 2:
    convergence = "DIVERGING"
else:
    convergence = "STABLE"

print(f"\n📊 Convergence assessment: {convergence}")
print(f"  Recent modifications (7d): {len(recent_mods)}")
print(f"  Older modifications (8-30d): {len(older_mods)}")
```

**4. Generate meta-report:**
```markdown
# Meta-Analysis Report

**Convergence:** {convergence}
**Total modifications:** {len(history)}
**Files modified:** {len(by_file)}

## Patterns Detected

{patterns}

## Recommendations

- If DIVERGING: Reduce modification frequency, focus on stability
- If STABLE: Continue current approach, monitor for new gaps
- If CONVERGING: Workflow maturing, consider finalizing rules

## High-Churn Files

{files with most modifications}

These files may indicate:
1. Complex requirements that change frequently
2. Initial design needing refinement
3. External factors (broker API changes, etc.)
```

---

## Mode: Test-Run (Dry-Run)

**Purpose:** Preview deep mode modifications without applying.

**Same as deep mode but:**
- No `git stash` backup
- No `Edit` tool usage
- Only show proposed modifications
- No validation

```python
# Run deep mode analysis
gaps = analyze_workflow_gaps()  # [PLANNED - pseudocode]
modifications = propose_modifications(gaps)  # [PLANNED - pseudocode]

# Show modifications
for mod in modifications:
    print(f"\n{'='*60}")
    print(f"File: {mod['file']}")
    print(f"Action: {mod['action']}")
    print(f"{'='*60}")
    print("BEFORE:")
    print(mod['old_code'])
    print("\nAFTER:")
    print(mod['new_code'])

print(f"\n{len(modifications)} modifications proposed.")
print("Run `Skill('reflect', args='deep')` to apply.")
```

---

## Output Formats

### Session Mode

```
╔══════════════════════════════════════════════════════════╗
║         Learning Reflection (Session Mode)               ║
╚══════════════════════════════════════════════════════════╝

Knowledge DB Updated:
  ✅ 3 error patterns recorded
  ✅ 5 fix attempts logged
  ✅ 2 strategy scores updated
  ✨ 1 new rule synthesized

Failure Index Updated:
  ✅ 2 new entries added
  ⚠️  1 pattern reached threshold (5+ occurrences)

Session Outcomes (last 1 hour):
  Test runs: 12 (8 passed, 4 failed)
  Skill invocations: 7 (5 succeeded, 2 failed)
  Success rate: 76.3%

Synthesized Rules:
  1. "Update data-testid when component refactored" (confidence: 85%, evidence: 6)
     → Auto-fix eligible

Next session:
  - Auto-fix will attempt "Update data-testid" pattern automatically
  - Monitor success rate to refine rule
```

### Deep Mode

```
╔══════════════════════════════════════════════════════════╗
║      Learning Reflection (Deep Mode - Applied)           ║
╚══════════════════════════════════════════════════════════╝

Workflow Gaps Identified: 3
  1. Missing auto-fix: selector_not_found (5 occurrences)
  2. Hook gap: Broker abstraction not validated
  3. Slow command: fix-loop (avg 8m 23s)

Proposed Modifications: 3
  1. post_test_update.py: Add auto-fix pattern
  2. validate_workflow_step.py: Add broker abstraction check
  3. fix-loop.md: Optimize debugger agent invocation

User approved: Apply all

Applied Modifications:
  ✅ .claude/hooks/post_test_update.py (validated)
  ✅ .claude/hooks/validate_workflow_step.py (validated)
  ✅ .claude/commands/fix-loop.md (validated)

Smoke Tests:
  ✅ Hooks load correctly
  ✅ Commands parse correctly
  ✅ No degradation detected

Modifications recorded to:
  .claude/logs/learning/modifications.json

Safety backup created:
  git stash list | head -1
```

---

## Exit Codes

- **0:** Success (session mode) or modifications applied (deep mode)
- **1:** Modifications failed validation or user cancelled
