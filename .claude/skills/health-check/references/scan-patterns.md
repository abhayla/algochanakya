# Health Check Scan Patterns Reference

Detailed patterns, commands, and interpretation guide for each health check scan step.

---

## 1. Stale Import Scan Patterns

### Backend Python Imports

**Moved Services (app/services/ → app/services/autopilot/):**

```bash
# Check for old import paths
grep -r "from app.services.kill_switch import" backend/app --include="*.py"
grep -r "from app.services.condition_engine import" backend/app --include="*.py"
grep -r "from app.services.order_executor import" backend/app --include="*.py"
grep -r "from app.services.strategy_monitor import" backend/app --include="*.py"
grep -r "from app.services.adjustment_engine import" backend/app --include="*.py"
grep -r "from app.services.suggestion_engine import" backend/app --include="*.py"

# Should be:
# from app.services.autopilot.kill_switch import KillSwitch
# from app.services.autopilot.condition_engine import ConditionEngine
# etc.
```

**Moved Services (app/services/ → app/services/options/):**

```bash
# Check for old import paths
grep -r "from app.services.pnl_calculator import" backend/app --include="*.py"
grep -r "from app.services.greeks_calculator import" backend/app --include="*.py"
grep -r "from app.services.payoff_calculator import" backend/app --include="*.py"
grep -r "from app.services.iv_metrics_service import" backend/app --include="*.py"

# Should be:
# from app.services.options.pnl_calculator import PnLCalculator
# from app.services.options.greeks_calculator import GreeksCalculator
# etc.
```

**Renamed Classes:**

```bash
# Check for old class names
grep -r "SuggestionPriority" backend/app --include="*.py"
# Should be: SuggestionUrgency

grep -r "OldClassName" backend/app --include="*.py"
# Should be: NewClassName
```

### Frontend Import Patterns

**Moved Components:**

```bash
# Check for old component paths
grep -r "from '@/components/ExitModal.vue'" frontend/src --include="*.js" --include="*.vue"
# Should check if component moved to subdirectory

grep -r "from '@/views/OldView.vue'" frontend/src --include="*.js" --include="*.vue"
# Should verify current path
```

**Renamed Stores:**

```bash
# Check for old store names
grep -r "useOldStore" frontend/src --include="*.js" --include="*.vue"
# Should be: useNewStore
```

### Interpretation

| Pattern Found | Severity | Action |
|---------------|----------|--------|
| 1-2 stale imports | Low | Fix in current session |
| 3-5 stale imports | Medium | Create fix task, may indicate incomplete refactor |
| 6+ stale imports | High | Major refactor incomplete, review entire codebase |

---

## 2. Missing Test Coverage Patterns

### File-to-Test Mappings

**Backend Services → API Tests:**

```bash
# AutoPilot services → autopilot.api.spec.js
ls -la backend/app/services/autopilot/*.py
# Check: tests/e2e/specs/autopilot/autopilot.api.spec.js

# Options services → strategy.api.spec.js
ls -la backend/app/services/options/*.py
# Check: tests/e2e/specs/strategy/strategy.api.spec.js
```

**Frontend Components → Happy/Visual Tests:**

```bash
# Views → {feature}.happy.spec.js
ls -la frontend/src/views/*View.vue
# Check corresponding: tests/e2e/specs/{feature}/{feature}.happy.spec.js

# Modals → {feature}.happy.spec.js (test modal interactions)
ls -la frontend/src/components/modals/*.vue
```

**Pinia Stores → Feature Tests:**

```bash
# Stores test via UI that uses them
ls -la frontend/src/stores/*.js
# Check: tests/e2e/specs/{feature}/{feature}.happy.spec.js
```

### Detection Algorithm

```python
import os
from datetime import datetime, timedelta

def check_test_coverage(changed_file):
    """Check if changed file has recent test coverage."""

    # Get file change date
    file_mtime = os.path.getmtime(changed_file)
    file_date = datetime.fromtimestamp(file_mtime)

    # Map file to expected test
    test_file = map_file_to_test(changed_file)

    if not test_file or not os.path.exists(test_file):
        return f"MISSING: No test file for {changed_file}"

    # Get test change date
    test_mtime = os.path.getmtime(test_file)
    test_date = datetime.fromtimestamp(test_mtime)

    # Check if test was updated within 7 days of code change
    days_diff = (file_date - test_date).days

    if days_diff > 7:
        return f"STALE: {test_file} not updated ({days_diff} days old)"

    return "OK"
```

### Interpretation

| Gap | Severity | Action |
|-----|----------|--------|
| Test file missing | High | Create test immediately |
| Test 7-14 days stale | Medium | Update test soon |
| Test 14-30 days stale | High | Test likely obsolete |
| Test 30+ days stale | Critical | Test definitely obsolete |

---

## 3. File Risk Score Calculation

### Risk Score Formula

```
error_weight = 1.0
revert_weight = 2.0

raw_risk = (error_count * error_weight) + (revert_count * revert_weight)
normalized_risk = min(raw_risk / 10.0, 1.0)  # Clamp to [0, 1]
```

### Example Calculations

**Example 1: High-Risk File**
```
File: backend/app/services/autopilot/suggestion_engine.py
Errors: 8
Reverts: 2

raw_risk = (8 * 1.0) + (2 * 2.0) = 8 + 4 = 12
normalized_risk = min(12 / 10.0, 1.0) = 1.0

Risk Level: CRITICAL (1.0)
```

**Example 2: Medium-Risk File**
```
File: frontend/src/stores/strategy.js
Errors: 5
Reverts: 1

raw_risk = (5 * 1.0) + (1 * 2.0) = 5 + 2 = 7
normalized_risk = min(7 / 10.0, 1.0) = 0.7

Risk Level: HIGH (0.7)
```

**Example 3: Low-Risk File**
```
File: tests/e2e/specs/watchlist/watchlist.happy.spec.js
Errors: 2
Reverts: 0

raw_risk = (2 * 1.0) + (0 * 2.0) = 2
normalized_risk = min(2 / 10.0, 1.0) = 0.2

Risk Level: LOW (0.2)
```

### Risk Thresholds

| Score Range | Level | Color | Recommendation |
|-------------|-------|-------|----------------|
| 0.0-0.3 | Low | 🟢 Green | Normal development |
| 0.3-0.5 | Medium-Low | 🟡 Yellow | Be cautious |
| 0.5-0.7 | Medium-High | 🟠 Orange | Extra testing needed |
| 0.7-0.9 | High | 🔴 Red | Review before changes |
| 0.9-1.0 | Critical | 🔴🔴 Dark Red | Refactor or stabilize first |

### Query Command

```bash
cd .claude/learning
python -c "
from db_helper import get_connection

conn = get_connection()
cursor = conn.execute('''
    SELECT file_path, risk_score, error_count, fix_count, revert_count, last_error
    FROM file_risk_scores
    WHERE risk_score > 0.5
    ORDER BY risk_score DESC
    LIMIT 10
''')

for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]:.2f} (E:{row[2]}, F:{row[3]}, R:{row[4]})')

conn.close()
"
```

---

## 4. Unresolved Error Pattern Detection

### Query Command

```bash
cd .claude/learning
python -c "
from db_helper import get_connection

conn = get_connection()

# Find patterns that occur multiple times but never resolved
cursor = conn.execute('''
    SELECT
        fingerprint,
        error_type,
        message_pattern,
        file_pattern,
        occurrence_count,
        first_seen,
        last_seen
    FROM error_patterns
    WHERE auto_resolved_count = 0
      AND manual_resolved_count = 0
      AND occurrence_count > 1
    ORDER BY occurrence_count DESC
    LIMIT 10
''')

print('Recurring Unresolved Errors:')
for row in cursor.fetchall():
    print(f'  {row[1]}: {row[2][:60]}')
    print(f'    Fingerprint: {row[0]}')
    print(f'    Occurrences: {row[5]} (first: {row[4]}, last: {row[6]})')
    print()

conn.close()
"
```

### Interpretation

| Occurrences | Age (days) | Severity | Action |
|-------------|------------|----------|--------|
| 2-3 | Any | Low | May be coincidence |
| 4-5 | < 7 | Medium | Investigate pattern |
| 6-10 | < 30 | High | Create learned strategy |
| 10+ | Any | Critical | Systemic issue, needs immediate fix |

### Creating Learned Strategy

If an unresolved pattern occurs ≥5 times:

```python
from db_helper import get_connection
import json
from datetime import datetime

conn = get_connection()

# Create learned strategy based on investigation
conn.execute(
    """INSERT INTO fix_strategies
       (name, error_type, description, steps, preconditions, created_at, source)
       VALUES (?, ?, ?, ?, ?, ?, 'learned')""",
    (
        'Fix: Recurring {error_type}',
        '{error_type}',
        'Strategy created from recurring unresolved pattern',
        json.dumps([
            'Step 1: Investigate root cause',
            'Step 2: Apply identified fix',
            'Step 3: Verify resolution'
        ]),
        json.dumps({'fingerprint': '{fingerprint}'}),
        datetime.utcnow().isoformat()
    )
)

conn.commit()
conn.close()
```

---

## 5. Strategy Effectiveness Analysis

### Query Command

```bash
cd .claude/learning
python -c "
from db_helper import get_connection

conn = get_connection()

# Find strategies with low success rate but significant attempts
cursor = conn.execute('''
    SELECT
        id,
        name,
        error_type,
        current_score,
        success_count,
        failure_count,
        total_attempts,
        source,
        last_used
    FROM fix_strategies
    WHERE total_attempts >= 3
      AND current_score < 0.2
    ORDER BY current_score ASC
''')

print('Ineffective Strategies (score < 0.2, attempts >= 3):')
for row in cursor.fetchall():
    success_rate = (row[4] / row[6]) * 100 if row[6] > 0 else 0
    print(f'  [{row[3]:.2f}] {row[1]} ({row[2]})')
    print(f'    Success: {row[4]}/{row[6]} ({success_rate:.1f}%)')
    print(f'    Source: {row[7]}, Last used: {row[8] or \"Never\"}')
    print()

conn.close()
"
```

### Interpretation

| Score | Attempts | Success Rate | Action |
|-------|----------|--------------|--------|
| < 0.1 | ≥ 5 | < 20% | Deprecate immediately |
| 0.1-0.2 | ≥ 3 | 20-40% | Review and improve or deprecate |
| 0.2-0.3 | ≥ 10 | 40-60% | Marginal, monitor |
| 0.3-0.5 | Any | 60-80% | OK, room for improvement |
| ≥ 0.5 | Any | ≥ 80% | Effective |

### Deprecating a Strategy

```python
from db_helper import get_connection

conn = get_connection()

# Mark strategy as deprecated (set score to 0)
conn.execute(
    "UPDATE fix_strategies SET current_score = 0.0 WHERE id = ?",
    (strategy_id,)
)

# Or delete entirely
conn.execute(
    "DELETE FROM fix_strategies WHERE id = ?",
    (strategy_id,)
)

conn.commit()
conn.close()
```

---

## 6. Synthesis Rules Check Patterns

### Synthesis Criteria

```python
def meets_synthesis_criteria(strategy):
    """Check if strategy meets criteria for rule synthesis."""

    # Minimum evidence instances
    if strategy['success_count'] < 5:
        return False, "Insufficient evidence (need ≥5 successes)"

    # Minimum confidence
    success_rate = strategy['success_count'] / strategy['total_attempts']
    if success_rate < 0.7:
        return False, f"Low confidence ({success_rate:.1%} < 70%)"

    # Not already synthesized
    if strategy['source'] == 'synthesized':
        return False, "Already synthesized"

    # Check if rule already exists
    # ... (query synthesized_rules table)

    return True, "Eligible for synthesis"
```

### Query Eligible Strategies

```bash
cd .claude/learning
python -c "
from db_helper import get_connection

conn = get_connection()

# Find strategies eligible for synthesis
cursor = conn.execute('''
    SELECT
        s.id,
        s.name,
        s.error_type,
        s.success_count,
        s.total_attempts,
        s.current_score,
        s.source
    FROM fix_strategies s
    WHERE s.success_count >= 5
      AND s.total_attempts >= 5
      AND s.current_score >= 0.7
      AND s.source != 'synthesized'
      AND NOT EXISTS (
          SELECT 1 FROM synthesized_rules r
          WHERE r.error_type = s.error_type
            AND r.rule_name = 'Auto: ' || s.name
            AND r.superseded_by IS NULL
      )
''')

print('Strategies Eligible for Synthesis:')
for row in cursor.fetchall():
    success_rate = (row[3] / row[4]) * 100
    print(f'  {row[1]} ({row[2]})')
    print(f'    Success: {row[3]}/{row[4]} ({success_rate:.1f}%)')
    print(f'    Score: {row[5]:.2f}, Source: {row[6]}')
    print()

conn.close()
"
```

### Running Synthesis

```bash
cd .claude/learning
python -c "
from db_helper import synthesize_rules

new_rules = synthesize_rules(min_confidence=0.7, min_evidence=5)

if new_rules:
    print(f'✨ {len(new_rules)} new rules synthesized:')
    for rule in new_rules:
        print(f'  - {rule[\"rule_name\"]}')
        print(f'    Confidence: {rule[\"confidence\"]:.1%}')
        print(f'    Evidence: {rule[\"evidence_count\"]} successful fixes')
else:
    print('No new rules to synthesize')
"
```

---

## 7. Git Health Check Patterns

### Uncommitted Changes

```bash
# List uncommitted files
git status --porcelain

# Interpretation:
# M  = Modified (staged)
# MM = Modified (staged and unstaged)
# ?? = Untracked
# D  = Deleted
# A  = Added
```

### Stale Branches

```bash
# List branches by last commit date
git for-each-ref --sort=-committerdate refs/heads/ \
  --format='%(refname:short)|%(committerdate:relative)|%(authorname)' | \
  column -t -s '|'

# Find branches not updated in 30+ days
git for-each-ref --sort=-committerdate refs/heads/ \
  --format='%(refname:short) %(committerdate:relative)' | \
  grep -E '([4-9][0-9]|[0-9]{3,}) days ago|weeks ago|months ago'
```

### Large Files

```bash
# Find large files in recent commits (> 1MB)
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {if ($3 > 1048576) print $3/1048576 " MB", $4}' | \
  sort -nr | \
  head -10
```

### Merge Conflicts

```bash
# Check for unresolved merge conflicts
git diff --name-only --diff-filter=U

# Check for conflict markers in files
grep -r "<<<<<<< HEAD" . --exclude-dir=.git || echo "No conflicts"
```

### Interpretation

| Finding | Severity | Action |
|---------|----------|--------|
| 1-3 uncommitted files | Low | Commit before continuing |
| 4-10 uncommitted files | Medium | Review and commit/stash |
| 10+ uncommitted files | High | Significant WIP, organize commits |
| Stale branches (30+ days) | Low | Consider deleting or merging |
| Stale branches (90+ days) | Medium | Likely obsolete, delete |
| Large files (> 1MB) | Medium | Consider Git LFS |
| Large files (> 10MB) | High | Must use Git LFS or gitignore |
| Merge conflicts | Critical | Resolve immediately |

---

## Combined Health Score

Calculate overall health score (0-100):

```python
def calculate_health_score(scan_results):
    """Calculate overall codebase health score."""

    score = 100

    # Deduct for stale imports (max -10)
    score -= min(scan_results['stale_imports'] * 2, 10)

    # Deduct for missing tests (max -15)
    score -= min(scan_results['missing_tests'] * 3, 15)

    # Deduct for high-risk files (max -20)
    score -= min(scan_results['high_risk_files'] * 4, 20)

    # Deduct for unresolved patterns (max -15)
    score -= min(scan_results['unresolved_patterns'] * 5, 15)

    # Deduct for ineffective strategies (max -10)
    score -= min(scan_results['ineffective_strategies'] * 2, 10)

    # Deduct for git issues (max -10)
    score -= min(scan_results['git_issues'] * 1, 10)

    # Bonus for synthesized rules (max +10)
    score += min(scan_results['new_rules_synthesized'] * 2, 10)

    return max(score, 0)  # Clamp to 0-100
```

**Health Score Ranges:**

| Score | Grade | Status |
|-------|-------|--------|
| 90-100 | A | Excellent |
| 80-89 | B | Good |
| 70-79 | C | Acceptable |
| 60-69 | D | Needs Attention |
| < 60 | F | Critical Issues |

---

## Automated Fixes

Some issues can be auto-fixed with `/health-check --fix`:

### Auto-Fixable Issues

1. **Stale Imports** - Update import paths automatically
2. **Missing Test Stubs** - Generate test file skeletons
3. **Ineffective Strategies** - Deprecate strategies with score < 0.1
4. **Stale Branches** - Delete branches not updated in 90+ days (with confirmation)

### Not Auto-Fixable (Manual Required)

1. **Missing Test Coverage** - Requires understanding of functionality
2. **High-Risk Files** - Requires code review and refactoring
3. **Unresolved Patterns** - Requires investigation and strategy creation
4. **Large Files** - Requires decision on Git LFS or gitignore
5. **Merge Conflicts** - Requires manual resolution
