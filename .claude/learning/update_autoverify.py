"""Update auto-verify SKILL.md with learning engine integration."""

# Read original file
with open('../skills/auto-verify/SKILL.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find insertion points
step3_idx = None
step6_idx = None
step7_end_idx = None

for i, line in enumerate(lines):
    if line.strip() == '### Step 3: Run Targeted Tests':
        step3_idx = i
    elif line.strip() == '### Step 6: Decision Point':
        step6_idx = i
    elif line.strip() == '## Approval Checkpoints':
        step7_end_idx = i

# Step 2c content (insert before Step 3)
step2c = '''### Step 2c: Knowledge Base Pre-Check (Learning Engine)

**Before attempting any fix**, consult the learning engine for known solutions:

```bash
cd .claude/learning
python -c "
import sys
sys.path.insert(0, '.')
from db_helper import record_error, get_strategies

# Record the error (or get existing pattern)
error_id = record_error(
    error_type='TestFailure',  # or 'ImportError', 'BuildError', etc.
    message='<error_message_from_test>',
    file_path='<file_path_where_error_occurred>'
)

# Get ranked strategies
strategies = get_strategies('TestFailure', limit=5)

if strategies:
    print('KNOWN PATTERN - Ranked fixes:')
    for s in strategies:
        if s['effective_score'] >= 0.3:
            print(f'  [{s[\\"effective_score\\"]:.2f}] {s[\\"name\\"]}: {s[\\"description\\"]}')
            if s['effective_score'] >= 0.7:
                print(f'    HIGH CONFIDENCE - Try this first!')
else:
    print('UNKNOWN PATTERN - Proceed with standard diagnosis')
"
```

**Decision Logic:**

| Strategy Score | Action |
|----------------|--------|
| **≥ 0.7** (High confidence) | Try this strategy FIRST, skip standard diagnosis |
| **0.3-0.7** (Medium) | Use as hint, but verify with standard diagnosis |
| **< 0.3** (Low/unproven) | Skip strategy, proceed with standard diagnosis |
| **None found** | Proceed with standard diagnosis, record as new pattern when fixed |

**Example Workflow:**

```
# Error detected: Locator 'positions-exit-modal' not found
# Learning engine query returns:
#   [0.82] Update Stale Selector: Update test selector after UI changes (10/12 attempts)
#   [0.54] Fix Async Timing: Add proper wait (3/6 attempts)

# Action: Try "Update Stale Selector" first (high confidence)
# If that fails, try "Fix Async Timing" (medium confidence)
# If both fail, proceed to Step 3 standard diagnosis
```

'''

# Updated Step 6 content (replace existing Step 6 through line before Step 6b)
step6_updated = '''### Step 6: Decision Point

Based on analysis:

| Outcome | Action |
|---------|--------|
| Tests pass + Screenshots look correct | **SUCCESS** - Proceed to Step 8 (record to knowledge base) |
| Tests fail | Analyze error, fix code, go to Step 3 |
| Tests pass but screenshots show issues | Fix code, go to Step 3 |
| **Hit stuck condition** (see below) | **STOP** - Ask user with knowledge context |

**Stuck Conditions** (STOP and ask user when ANY are met):

1. **Same fingerprinted error 3x** - Same error pattern with 3 different strategies all failing
2. **All strategies exhausted** - All known strategies have score < 0.1 (proven ineffective)
3. **20 total attempts in session** - Safety valve to prevent infinite loops
4. **Fix scope exceeds feature** - Fix requires modifying files outside current feature
5. **Completely unknown error** - No matching error_type in knowledge base strategies

**Stuck Message Template:**

```
I'm stuck on this error. Here's what I know:

**Error:** {error_type} - {error_message_summary}
**Fingerprint:** {fingerprint} (seen {occurrence_count} times in knowledge base)
**File:** {file_path}

**Knowledge Base Context:**
- Total patterns: {total_patterns}
- This error pattern: {known/unknown}
- Best available strategy: {strategy_name} (score: {score})
- Threshold for trying: 0.3

**Strategies attempted:**
1. [{score}] {strategy_name} - {outcome}
2. [{score}] {strategy_name} - {outcome}
...

Would you like me to:
1. Try a different heuristic approach (describe what)
2. Record this as a new learned pattern
3. Skip and move to other verification tasks
```

'''

# Step 8 content (insert before "## Approval Checkpoints")
step8 = '''
### Step 8: Record to Knowledge Base (Learning Engine)

**After EVERY fix attempt** (success or failure), record to knowledge base:

```bash
cd .claude/learning
python -c "
import sys
import subprocess
sys.path.insert(0, '.')
from db_helper import record_attempt, update_strategy_score

# Get current git commit hash (first 7 chars)
try:
    commit_hash = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True, text=True
    ).stdout.strip()[:7]
except:
    commit_hash = None

# Record the attempt
attempt_id = record_attempt(
    error_pattern_id={error_id},  # From Step 2c
    strategy_id={strategy_id},    # Or None if no strategy used
    outcome='success',            # or 'failure'
    session_id='{session_id}',    # Current Claude session
    file_path='{file_path}',
    error_message='{full_error}',
    fix_description='{what_was_done}',
    duration_seconds={elapsed_time},
    git_commit_hash=commit_hash
)

# Update strategy score if one was used
if {strategy_id}:
    update_strategy_score({strategy_id})

print(f'✓ Recorded attempt #{attempt_id} to knowledge base')
"
```

**On SUCCESS:**

1. **Run verification loop** (expand test radius):
   ```bash
   # Run adjacent feature tests to check for regressions
   # Example: If fixed positions, also run watchlist tests
   npx playwright test tests/e2e/specs/watchlist/watchlist.happy.spec.js
   ```

2. **If verification passes**, boost strategy score:
   ```python
   # Boost score by 0.1 for verified fix
   from db_helper import get_connection
   conn = get_connection()
   conn.execute(
       "UPDATE fix_strategies SET current_score = MIN(current_score + 0.1, 1.0) WHERE id = ?",
       ({strategy_id},)
   )
   conn.commit()
   conn.close()
   ```

3. **Check for synthesis** - If strategy now meets criteria (≥70% success, ≥5 evidence):
   ```bash
   cd .claude/learning
   python -c "
   from db_helper import synthesize_rules
   new_rules = synthesize_rules(min_confidence=0.7, min_evidence=5)
   if new_rules:
       print(f'✨ {len(new_rules)} new rules synthesized!')
   "
   ```

**On FAILURE:**

1. **Decrease strategy score** (automatic in `update_strategy_score()`)
2. **Try next ranked strategy** from Step 2c
3. **If no more strategies**, check stuck conditions (Step 6)

**On FIRST FIX for unknown pattern:**

1. **Create new strategy** in knowledge base:
   ```python
   from db_helper import get_connection
   import json
   from datetime import datetime

   conn = get_connection()
   conn.execute(
       """INSERT INTO fix_strategies
          (name, error_type, description, steps, preconditions, created_at, source)
          VALUES (?, ?, ?, ?, ?, ?, 'learned')""",
       (
           'Fix: {descriptive_name}',
           '{error_type}',
           '{what_this_fix_does}',
           json.dumps(['{step_1}', '{step_2}', ...]),
           json.dumps({precondition_dict}),
           datetime.utcnow().isoformat()
       )
   )
   conn.commit()
   conn.close()
   print('✓ New strategy recorded for future use')
   ```

'''

# Perform insertions
result = []

# Add lines up to Step 3
result.extend(lines[:step3_idx])

# Add Step 2c
result.append(step2c)

# Add Step 3 through Step 6 header
step6_header_idx = step6_idx
result.extend(lines[step3_idx:step6_header_idx])

# Add updated Step 6
result.append(step6_updated)

# Find Step 6b start
step6b_idx = None
for i in range(step6_idx, len(lines)):
    if lines[i].strip() == '### Step 6b: Visual Debugging with Claude Chrome (PRIMARY METHOD)':
        step6b_idx = i
        break

# Add Step 6b through Step 7 end
result.extend(lines[step6b_idx:step7_end_idx])

# Add Step 8
result.append(step8)

# Add remaining content (Approval Checkpoints onward)
result.extend(lines[step7_end_idx:])

# Write updated file
with open('../skills/auto-verify/SKILL.md', 'w', encoding='utf-8') as f:
    f.writelines(result)

print('✓ auto-verify SKILL.md updated with learning engine integration')
print(f'  - Step 2c added (Knowledge Base Pre-Check)')
print(f'  - Step 6 updated (Stuck Conditions)')
print(f'  - Step 8 added (Record to Knowledge Base)')
