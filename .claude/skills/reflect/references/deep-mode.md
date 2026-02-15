# Mode: Deep (Self-Modification with Safety)

**Purpose:** Analyze workflow gaps and modify commands/hooks to improve.

**⚠️ REQUIRES USER APPROVAL:** This mode modifies workflow files.

## Safety Protocol

**Before any modifications:**

1. **Create safety backup:**
   ```bash
   git stash push -m "reflect-deep-$(date +%Y%m%d-%H%M%S)" \
       .claude/skills/ \
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

## Deep Mode Algorithm

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
            'file': f'.claude/skills/{gap["skill"]}/SKILL.md',
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
for skill_dir in Path(".claude/skills/").glob("*/"):
    skill_file = skill_dir / "SKILL.md"
    if skill_file.exists():
        # Basic markdown validation
        if not validate_file(skill_file):
            print(f"❌ {skill_file} validation failed")
            revert_all_modifications()
            return

print("✅ Smoke tests passed")
```

---

## Deep Mode Recursion

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
