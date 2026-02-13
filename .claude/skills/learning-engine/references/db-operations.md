# Database Operations Reference

Complete guide to using `db_helper.py` functions in the Learning Engine.

## Initialization

### init_db()
Creates database and tables from schema.sql.

```python
from db_helper import init_db

# Initialize database (creates knowledge.db)
init_db()
```

**When to use:** First time setup, or after database corruption.

---

## Error Recording

### record_error(error_type, message, file_path=None)
Records an error occurrence with automatic fingerprinting and deduplication.

```python
from db_helper import record_error

# Record an ImportError
error_id = record_error(
    error_type="ImportError",
    message="cannot import name 'SuggestionPriority' from 'app.models.autopilot_models'",
    file_path="backend/app/services/autopilot/suggestion_engine.py"
)
# Returns: error_pattern_id (int)
```

**Behavior:**
- If fingerprint exists: Increments `occurrence_count`, updates `last_seen`
- If new pattern: Creates new record in `error_patterns` table
- Automatically normalizes message (strips line numbers, values)
- Converts file path to pattern (e.g., `*/suggestion_engine.py` → `*/*.py`)

**Error Types:**
- `ImportError`, `ModuleNotFoundError`, `AttributeError`
- `TestFailure`, `BuildError`, `SyntaxError`, `TypeError`
- Custom types as needed

---

## Strategy Retrieval

### get_strategies(error_type, limit=5)
Gets ranked fix strategies for an error type, sorted by effective score.

```python
from db_helper import get_strategies

# Get top 5 strategies for ImportError
strategies = get_strategies("ImportError", limit=5)

for strategy in strategies:
    print(f"[{strategy['effective_score']:.2f}] {strategy['name']}")
    print(f"  {strategy['description']}")
    print(f"  Success: {strategy['success_count']}/{strategy['total_attempts']}")
    if strategy['effective_score'] > 0.5:
        print(f"  Steps: {strategy['steps']}")
```

**Returns:** List of dictionaries with:
- `id`, `name`, `description`, `error_type`
- `steps` (list), `preconditions` (dict)
- `current_score`, `effective_score` (with time decay applied)
- `success_count`, `failure_count`, `total_attempts`
- `source` ('seeded', 'learned', 'synthesized')

**Scoring:**
- Sorted by `effective_score` (current_score with time decay)
- Scores range 0.0-1.0, higher = better
- Skip strategies with score < 0.1 (proven ineffective)
- Try strategies with score > 0.5 first (proven effective)

---

## Fix Attempt Recording

### record_attempt(error_pattern_id, outcome, **kwargs)
Records every fix attempt with outcome and metadata.

```python
from db_helper import record_attempt
import subprocess

# Get git commit hash
commit_hash = subprocess.run(
    ['git', 'rev-parse', 'HEAD'],
    capture_output=True, text=True
).stdout.strip()[:7]

# Record successful fix
attempt_id = record_attempt(
    error_pattern_id=error_id,
    strategy_id=strategy['id'],
    outcome='success',  # or 'failure', 'partial', 'reverted'
    session_id='session_123',
    file_path='backend/app/services/autopilot/suggestion_engine.py',
    error_message='Full error message...',
    fix_description='Updated import from SuggestionPriority to SuggestionUrgency',
    duration_seconds=12.5,
    git_commit_hash=commit_hash
)
```

**Outcomes:**
- `success` - Fix resolved the error
- `failure` - Fix did not resolve error
- `partial` - Fix improved but didn't fully resolve
- `reverted` - Fix was later reverted (set by feedback loop)

**Side Effects:**
- On `success`: Increments `error_patterns.auto_resolved_count`
- Updates `file_risk_scores` for the file
- Triggers strategy score recalculation

---

## Strategy Score Management

### update_strategy_score(strategy_id)
Recalculates strategy score based on historical performance.

```python
from db_helper import update_strategy_score

# After recording an attempt, update the strategy score
update_strategy_score(strategy['id'])
```

**Formula:**
```
raw_success_rate = success_count / max(total_attempts, 1)
recency_factor = 1.0 / (1.0 + days_since_last_use * 0.1)
confidence_factor = min(total_attempts / 10.0, 1.0)

current_score = (
    0.6 * raw_success_rate +
    0.3 * recency_factor +
    0.1 * confidence_factor
)
```

**Automatic Updates:**
- Called automatically by `record_attempt()`
- No need to call manually unless batch updating

---

## File Risk Tracking

### get_file_risk(file_path)
Retrieves risk score for a specific file.

```python
from db_helper import get_file_risk

risk = get_file_risk('backend/app/services/autopilot/suggestion_engine.py')
if risk and risk['risk_score'] > 0.5:
    print(f"⚠ High-risk file: {risk['risk_score']:.2f}")
    print(f"  Errors: {risk['error_count']}, Reverts: {risk['revert_count']}")
```

**Returns:** Dictionary with:
- `file_path`, `error_count`, `fix_count`, `revert_count`
- `risk_score` (0.0-1.0, calculated as `errors + reverts*2`)
- `last_error` (timestamp), `updated_at`

**Risk Thresholds:**
- `< 0.3` - Low risk (green)
- `0.3-0.7` - Medium risk (yellow)
- `> 0.7` - High risk (red) - extra caution needed

---

## Revert Detection

### check_for_reverts(since_hours=24)
Git-aware detection of reverted fixes.

```python
from db_helper import check_for_reverts

# Check for reverts in last 24 hours
reverts = check_for_reverts(since_hours=24)

for revert in reverts:
    if revert['type'] == 'explicit_revert':
        print(f"Git revert detected: {revert['commit_hash']}")
    elif revert['type'] == 'repeated_fix':
        print(f"Same-file repeated fix: {revert['file_path']} ({revert['fix_count']} times)")
```

**Detection Methods:**
1. **Explicit Reverts:** Searches git log for commits with "revert" in message
2. **Repeated Fixes:** Finds files fixed multiple times within timeframe (indicates previous fix failed)

**Returns:** List of detected reverts with `type`, `commit_hash`, or `file_path`

---

## Rule Synthesis

### synthesize_rules(min_confidence=0.7, min_evidence=5)
Auto-generates rules from successful strategies.

```python
from db_helper import synthesize_rules

# Synthesize rules (run periodically)
new_rules = synthesize_rules(min_confidence=0.7, min_evidence=5)

for rule in new_rules:
    print(f"✨ New rule synthesized: {rule['rule_name']}")
    print(f"   Confidence: {rule['confidence']:.1%} ({rule['evidence_count']} successful fixes)")
```

**Criteria:**
- Success rate ≥ 70% (min_confidence)
- At least 5 successful fixes (min_evidence)
- Not already synthesized (avoids duplicates)

**Output:**
- Inserts into `synthesized_rules` table
- Generates markdown content for skill injection
- Returns list of newly created rules

---

## Session Metrics

### get_session_metrics(session_id)
Retrieves metrics for a Claude Code session.

```python
from db_helper import get_session_metrics

metrics = get_session_metrics('session_abc123')
if metrics:
    print(f"Errors encountered: {metrics['total_errors_encountered']}")
    print(f"Auto-resolved: {metrics['total_auto_resolved']}")
    print(f"Success rate: {metrics['total_auto_resolved'] / max(metrics['total_errors_encountered'], 1):.1%}")
```

### update_session_metrics(session_id, **kwargs)
Updates session metrics (auto-creates session if not exists).

```python
from db_helper import update_session_metrics

# Increment counters
update_session_metrics(
    session_id='session_abc123',
    total_errors_encountered=5,
    total_auto_resolved=3,
    new_patterns_discovered=1
)
```

---

## Database Statistics

### get_stats()
Gets overall knowledge base statistics.

```python
from db_helper import get_stats

stats = get_stats()
print(f"Total patterns: {stats['total_patterns']}")
print(f"Total strategies: {stats['total_strategies']}")
print(f"Success rate: {stats['successful_fixes'] / max(stats['successful_fixes'] + stats['failed_fixes'], 1):.1%}")
```

---

## Seeding Initial Strategies

### seed_strategies()
Populates database with initial seeded strategies.

```python
from db_helper import seed_strategies

# Seed ~25-30 initial strategies
count = seed_strategies()
print(f"Seeded {count} strategies")
```

**Pre-seeded Strategies:**
- ImportError: Fix Missing Import, Fix Circular Import, Update Import Path After Move
- ModuleNotFoundError: Install Missing Package
- AttributeError: Fix Undefined Attribute
- TestFailure: Update Stale Selector, Fix Async Timing, Fix API Mock
- BuildError: Clear Build Cache
- SyntaxError: Fix Python Syntax
- TypeError: Fix Type Mismatch

---

## CLI Usage

```bash
# Initialize database
cd .claude/learning && python db_helper.py init

# Seed strategies
python db_helper.py seed

# Show statistics
python db_helper.py stats
```

---

## Error Handling

All functions use try/finally to ensure connections are closed:

```python
conn = get_connection()
try:
    # Database operations
    conn.commit()
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
```

**Common Errors:**
- `FileNotFoundError` - schema.sql not found (check path)
- `sqlite3.OperationalError` - Database locked (close other connections)
- `sqlite3.IntegrityError` - Constraint violation (check unique constraints)
