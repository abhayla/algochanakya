"""Update test-fixer SKILL.md with learning engine integration."""

# Read original file
with open('../skills/test-fixer/SKILL.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find insertion points
step1_idx = None
diagnostic_workflow_end_idx = None

for i, line in enumerate(lines):
    if line.strip() == '### Step 1: Identify the Failure Type':
        step1_idx = i
    # Find the end of diagnostic workflow (last pattern section)
    if 'Diagnostic Workflow' in line or 'Additional Resources' in line:
        diagnostic_workflow_end_idx = i

# If we can't find diagnostic workflow end, use end of file
if diagnostic_workflow_end_idx is None:
    diagnostic_workflow_end_idx = len(lines)

# Step 0 content (insert before Step 1)
step0 = '''### Step 0: Knowledge Base Lookup (Learning Engine)

**Before standard diagnosis**, check if this test failure is already known:

```bash
cd .claude/learning
python -c "
import sys
sys.path.insert(0, '.')
from db_helper import record_error, get_strategies

# Fingerprint the error from test output
error_id = record_error(
    error_type='TestFailure',
    message='<error_message_from_test_output>',
    file_path='<test_file_path>'
)

# Get ranked strategies
strategies = get_strategies('TestFailure', limit=3)

if strategies:
    print('KNOWN PATTERN - Ranked fixes:')
    for s in strategies:
        print(f'  [{s[\\"effective_score\\"]:.2f}] {s[\\"name\\"]}: {s[\\"description\\"]}')
        if s['effective_score'] >= 0.5:
            print(f'    PROVEN FIX - Apply this strategy')
else:
    print('UNKNOWN PATTERN - Proceed with standard diagnosis (Step 1)')
"
```

**Decision Matrix:**

| Strategy Score | Action |
|----------------|--------|
| **≥ 0.5** (Proven) | Apply strategy directly, skip to fix |
| **0.2-0.5** (Moderate) | Use as hint during standard diagnosis |
| **< 0.2** (Unproven) | Ignore, proceed with standard diagnosis |
| **None found** | Proceed with Step 1, record as new pattern after fix |

**Example:**

```
# Test failure: Locator 'positions-exit-modal' not found
# Learning engine query returns:
#   [0.82] Update Stale Selector (10/12 attempts) - PROVEN FIX
#   [0.54] Fix Async Timing (3/6 attempts)

# Action: Apply "Update Stale Selector" directly
# 1. Find data-testid in component
# 2. Update Page Object getter
# 3. Run test again
# 4. Record outcome to knowledge base
```

**If High-Confidence Strategy Found:**
1. Apply the strategy steps directly
2. Run test to verify
3. Record attempt outcome (Step 7)
4. If success, you're done
5. If failure, try next strategy or proceed to Step 1

**If No Strategy or Low Confidence:**
1. Proceed to Step 1 (standard diagnosis)
2. After resolving, record as new learned pattern

---

'''

# Post-fix recording section (add at end)
post_fix = '''

---

## Step 7: Record to Knowledge Base (Learning Engine)

**After resolving ANY test failure**, record to knowledge base:

```bash
cd .claude/learning
python -c "
import sys
import subprocess
sys.path.insert(0, '.')
from db_helper import record_attempt, update_strategy_score, get_connection
import json
from datetime import datetime

# Get git commit hash
try:
    commit_hash = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True, text=True
    ).stdout.strip()[:7]
except:
    commit_hash = None

# Record the attempt
attempt_id = record_attempt(
    error_pattern_id={error_id},     # From Step 0
    strategy_id={strategy_id},       # Or None if no strategy used
    outcome='success',               # or 'failure'
    session_id='{session_id}',
    file_path='{test_file_path}',
    error_message='{full_error}',
    fix_description='{what_was_done}',
    duration_seconds={elapsed_time},
    git_commit_hash=commit_hash
)

# Update strategy score if one was used
if {strategy_id}:
    update_strategy_score({strategy_id})

print(f'[OK] Recorded attempt #{attempt_id} to knowledge base')
"
```

### On Success (Fix Worked)

1. **If strategy was used**, boost its score:
   ```python
   from db_helper import get_connection
   conn = get_connection()
   conn.execute(
       "UPDATE fix_strategies SET current_score = MIN(current_score + 0.05, 1.0) WHERE id = ?",
       ({strategy_id},)
   )
   conn.commit()
   conn.close()
   ```

2. **If pattern matches existing common pattern**, boost that pattern's score

3. **Check for synthesis** - If strategy now meets criteria (≥70% success, ≥5 evidence):
   ```bash
   cd .claude/learning
   python -c "
   from db_helper import synthesize_rules
   new_rules = synthesize_rules(min_confidence=0.7, min_evidence=5)
   if new_rules:
       print(f'[OK] {len(new_rules)} new rules synthesized!')
   "
   ```

### On First Fix for Unknown Pattern

If this test failure type was NOT in knowledge base (Step 0 returned empty):

```python
from db_helper import get_connection
import json
from datetime import datetime

conn = get_connection()

# Create new learned strategy based on what you did
conn.execute(
    """INSERT INTO fix_strategies
       (name, error_type, description, steps, preconditions, created_at, source)
       VALUES (?, ?, ?, ?, ?, ?, 'learned')""",
    (
        'Test Fix: {descriptive_name}',          # e.g., "Update Stale Modal Selector"
        'TestFailure',
        '{what_this_fix_does}',                  # e.g., "Update test selector after modal refactor"
        json.dumps([
            '{step_1}',                           # e.g., "Check component for current data-testid"
            '{step_2}',                           # e.g., "Update Page Object getter"
            '{step_3}'                            # e.g., "Verify test passes"
        ]),
        json.dumps({
            'error_contains': ['{pattern}']       # e.g., ['locator', 'not found']
        }),
        datetime.utcnow().isoformat()
    )
)
conn.commit()
conn.close()

print('[OK] New strategy recorded for future test failures')
```

**Example New Strategy:**

If you fixed "Locator 'autopilot-status-chip' not found" by:
1. Finding the component was refactored
2. Updating the data-testid from `autopilot-status-chip` to `autopilot-status-badge`
3. Updating Page Object getter

Record as:
```python
name = "Test Fix: Update Refactored Component Selector"
description = "Component was refactored with new data-testid, update Page Object"
steps = [
    "Check component file for current data-testid",
    "Update Page Object getter to match",
    "Run test to verify"
]
preconditions = {'error_contains': ['locator', 'not found', 'timeout']}
```

This becomes a learned strategy for future similar test failures.

---

'''

# Perform insertion
result = []

# Add lines up to Step 1
result.extend(lines[:step1_idx])

# Add Step 0
result.append(step0)

# Add Step 1 through end of file
result.extend(lines[step1_idx:])

# Add Step 7 at the end (before references if they exist)
# Find references section
refs_idx = None
for i in range(len(result)):
    if '## References' in result[i] or '## Additional Resources' in result[i]:
        refs_idx = i
        break

if refs_idx:
    # Insert before references
    result.insert(refs_idx, post_fix)
else:
    # Append at end
    result.append(post_fix)

# Write updated file
with open('../skills/test-fixer/SKILL.md', 'w', encoding='utf-8') as f:
    f.writelines(result)

print('[OK] test-fixer SKILL.md updated with learning engine integration')
print('  - Step 0 added (Knowledge Base Lookup)')
print('  - Step 7 added (Record to Knowledge Base)')
