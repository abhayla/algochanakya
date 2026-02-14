### Step 2c: Knowledge Base Pre-Check (Learning Engine)

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
            print(f'  [{s[\"effective_score\"]:.2f}] {s[\"name\"]}: {s[\"description\"]}')
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

