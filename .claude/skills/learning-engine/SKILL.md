---
name: learning-engine
description: Autonomous self-recursive learning system that records errors, ranks fix strategies, synthesizes rules, and improves across sessions. Use after test failures, bug fixes, or verification cycles to capture learnings. Integrates with auto-verify and test-fixer. Triggers on fix completions, test outcomes, and session reflections.
---

# Learning Engine Skill

**Purpose:** Autonomous self-recursive learning system that remembers errors, ranks fix strategies, and continuously improves across Claude Code sessions.

**Status:** Foundation for auto-verify and test-fixer integration. Enables zero-manual-intervention error resolution over time.

---

## Three Core Loops

### 1. Fix Loop (Autonomous Error Resolution)

**Workflow:**

1. **Error occurs** → Fingerprint it using normalization algorithm
2. **Query knowledge.db** for matching error pattern:
   ```python
   from db_helper import record_error, get_strategies
   error_id = record_error(error_type, message, file_path)
   strategies = get_strategies(error_type, limit=5)
   ```
3. **If known pattern** → Retrieve ranked strategies (sorted by score DESC)
4. **Try top strategy** → Record attempt → Update score
5. **If failure** → Try next strategy → Record → Update
6. **If stuck** → Stop and ask user (see Stuck Detection below)
7. **If success** → Record, update score, proceed to Verification Loop

**Example:**

```python
# Error: ImportError - cannot import name 'SuggestionPriority'
# File: backend/app/services/autopilot/suggestion_engine.py

# Step 1: Record error
error_id = record_error("ImportError", "cannot import name 'SuggestionPriority'",
                        "backend/app/services/autopilot/suggestion_engine.py")

# Step 2: Get strategies
strategies = get_strategies("ImportError", limit=5)

# Step 3: Try strategies in order
for strategy in strategies:
    if strategy['effective_score'] < 0.1:
        continue  # Skip proven ineffective strategies

    print(f"Trying: {strategy['name']} (score: {strategy['effective_score']:.2f})")

    # Apply fix based on strategy steps
    success = apply_strategy(strategy)

    # Record outcome
    record_attempt(
        error_pattern_id=error_id,
        strategy_id=strategy['id'],
        outcome='success' if success else 'failure',
        file_path=file_path,
        fix_description=f"Applied: {strategy['name']}"
    )

    # Update strategy score
    update_strategy_score(strategy['id'])

    if success:
        break  # Exit loop, proceed to verification
```

---

### 2. Verification Loop (Post-Fix Regression Check)

**Workflow:**

1. **After successful fix** → Run targeted tests (same logic as auto-verify Step 3)
2. **If tests pass** → Expand radius: run adjacent feature tests
3. **If adjacent tests fail** → New error detected, enter Fix Loop for it
4. **If all pass** → Mark fix as "verified", boost strategy score by 0.1
5. **Record session metrics**

**Example:**

```python
# Fix succeeded, now verify
test_result = run_targeted_tests(file_path)

if test_result['passed']:
    # Expand test radius
    adjacent_result = run_adjacent_tests(file_path)

    if adjacent_result['passed']:
        # Verified! Boost strategy score
        conn.execute(
            "UPDATE fix_strategies SET current_score = MIN(current_score + 0.1, 1.0) WHERE id = ?",
            (strategy['id'],)
        )
        print(f"✓ Fix verified - strategy score boosted to {strategy['current_score'] + 0.1:.2f}")
    else:
        # New error in adjacent features
        print(f"⚠ Adjacent tests failed: {adjacent_result['error']}")
        # Enter Fix Loop for new error
else:
    # Fix didn't actually work - this shouldn't happen if tests ran
    print(f"✗ Verification failed: {test_result['error']}")
```

---

### 3. Feedback Loop (Git-Aware Regression Detection)

**Workflow:**

1. **On session start** → Run git checks:
   ```bash
   git log --oneline -20
   git diff HEAD~5..HEAD
   git log --grep="revert" --since="7 days ago"
   ```
2. **Check for reverts:** Explicit "revert" commits
3. **Check for same-file-fix-within-24h:** Query fix_attempts for repeated file fixes
4. **If revert detected:**
   - Mark original fix_attempt as `was_reverted=1`
   - Decrease strategy score by 0.2
   - Increase file risk_score
5. **If repeated fix detected:**
   - Flag file in file_risk_scores
   - Warn: "File XYZ has high risk score (0.8) - extra caution needed"

**Example:**

```python
from db_helper import check_for_reverts

# On session start
reverts = check_for_reverts(since_hours=24)

for revert in reverts:
    if revert['type'] == 'explicit_revert':
        print(f"⚠ Git revert detected: {revert['commit_hash']}")
        # Find and mark affected fix_attempts
        conn.execute(
            "UPDATE fix_attempts SET was_reverted = 1 WHERE git_commit_hash = ?",
            (revert['commit_hash'],)
        )

        # Downrank associated strategies
        cursor = conn.execute(
            "SELECT DISTINCT strategy_id FROM fix_attempts WHERE git_commit_hash = ?",
            (revert['commit_hash'],)
        )
        for row in cursor.fetchall():
            if row['strategy_id']:
                conn.execute(
                    "UPDATE fix_strategies SET current_score = MAX(current_score - 0.2, 0.0) WHERE id = ?",
                    (row['strategy_id'],)
                )

    elif revert['type'] == 'repeated_fix':
        print(f"⚠ Repeated fix detected: {revert['file_path']} ({revert['fix_count']} times in 24h)")
        risk = get_file_risk(revert['file_path'])
        if risk and risk['risk_score'] > 0.7:
            print(f"   ⚠⚠ HIGH RISK FILE - Extra caution needed!")
```

---

## Stuck Detection

Claude should **stop and ask the user** when ANY of these conditions are met:

1. **Same fingerprinted error appears 3 times** with different strategies all failing
2. **All strategies exhausted** (all scores below 0.1)
3. **Total fix attempts > 20** in current session (safety valve)
4. **Fix requires modifying files outside current feature scope**
5. **Error type completely unknown** (no matching error_type in strategies table)

**Stuck Message Template:**

```
I'm stuck on this error. Here's what I know:

**Error:** {error_type} - {message_summary}
**Fingerprint:** {fingerprint} (seen {occurrence_count} times)
**File:** {file_path}

**Strategies tried:**
{list of strategies with outcomes}

**Knowledge DB status:**
- Total patterns: {total_patterns}
- This error pattern: {known/unknown}
- Best strategy score: {best_score} (threshold: 0.3)

Would you like me to:
1. Try a different approach (describe heuristic)
2. Record this as a new pattern for future learning
3. Skip this error and continue with other tasks
```

---

## Seeded Strategies

Pre-populated fix_strategies with ~25-30 strategies extracted from existing patterns:

### ImportError (3 strategies)
- **Fix Missing Import** - Add missing import statement at file top
- **Fix Circular Import** - Move import inside function scope
- **Update Import Path After Move** - Update import to reflect file reorganization

### ModuleNotFoundError (1 strategy)
- **Install Missing Package** - Run pip install or npm install

### AttributeError (1 strategy)
- **Fix Undefined Attribute** - Check for typos or add missing attribute

### TestFailure (3 strategies, from test-fixer)
- **Update Stale Selector** - Update test selector after UI changes
- **Fix Async Timing** - Add proper wait for async operations
- **Fix API Mock** - Update API mock to match current schema

### BuildError (1 strategy)
- **Clear Build Cache** - Clear dist/build folder and rebuild

### SyntaxError (1 strategy)
- **Fix Python Syntax** - Fix common Python syntax issues (colons, indentation)

### TypeError (1 strategy)
- **Fix Type Mismatch** - Fix type mismatches in function calls

**Seeding Command:**

```bash
cd .claude/learning
python db_helper.py seed
# Output: ✓ Seeded 11 strategies
```

---

## Manual Commands

### Status

```
/learning-engine status
```

**Output:**

```
=== Learning Engine Statistics ===
Error Patterns:      42
Fix Strategies:      28
Successful Fixes:    156
Failed Fixes:        23
Success Rate:        87.2%
Synthesized Rules:   8
Risky Files:         3

Top 5 Strategies by Score:
  [0.89] Fix Missing Import (ImportError) - 15/17 attempts
  [0.82] Update Stale Selector (TestFailure) - 10/12 attempts
  [0.76] Fix Async Timing (TestFailure) - 8/11 attempts
  [0.68] Install Missing Package (ModuleNotFoundError) - 5/7 attempts
  [0.54] Clear Build Cache (BuildError) - 3/6 attempts
==================================
```

---

### Query

```
/learning-engine query ImportError
```

**Output:**

```
=== ImportError Strategies ===
[0.89] Fix Missing Import
  Description: Add missing import statement at file top
  Success: 15/17 (88.2%)
  Last used: 2 days ago
  Steps:
    1. Identify missing module
    2. Add import statement
    3. Verify import path

[0.72] Fix Circular Import
  Description: Resolve circular import by moving import inside function
  Success: 5/7 (71.4%)
  Last used: 10 days ago

[0.58] Update Import Path After Move
  Description: Update import path to reflect file reorganization
  Success: 3/5 (60%)
  Last used: 25 days ago (STALE)
==============================
```

---

### Risk Report

```
/learning-engine risk-report
```

**Output:**

```
=== High-Risk Files (risk_score > 0.5) ===
[0.85] backend/app/services/autopilot/suggestion_engine.py
  Errors: 8, Fixes: 7, Reverts: 2
  Last error: 2025-01-14T10:23:45Z

[0.72] tests/e2e/specs/positions/exit.spec.js
  Errors: 6, Fixes: 5, Reverts: 1
  Last error: 2025-01-13T14:12:33Z

[0.61] frontend/src/stores/strategy.js
  Errors: 5, Fixes: 4, Reverts: 1
  Last error: 2025-01-12T09:45:12Z
==========================================
```

---

### Synthesize

```
/learning-engine synthesize
```

**Output:**

```
Running synthesis check (min_confidence=0.7, min_evidence=5)...

✨ 2 new rules synthesized:
  - Auto: Fix Missing Import (ImportError) - 88.2% confidence
  - Auto: Update Stale Selector (TestFailure) - 83.3% confidence

Rules injected into:
  - .claude/skills/test-fixer/references/common-failure-patterns.md
```

---

### Reset

```
/learning-engine reset
```

**Output:**

```
⚠ WARNING: This will delete ALL learning data:
  - 42 error patterns
  - 28 fix strategies
  - 179 fix attempts
  - 8 synthesized rules
  - 12 file risk scores

Type 'CONFIRM RESET' to proceed: _
```

---

## Session Lifecycle Integration

### On Session Start (Automatic)

```python
# 1. Initialize knowledge.db if not exists
if not DB_PATH.exists():
    init_db()
    seed_strategies()

# 2. Run Feedback Loop (check for reverts)
reverts = check_for_reverts(since_hours=168)  # 7 days
if reverts:
    print(f"⚠ {len(reverts)} reverts detected since last session")

# 3. Load synthesized rules into active context
cursor = conn.execute(
    "SELECT markdown_content FROM synthesized_rules WHERE superseded_by IS NULL"
)
rules = [row['markdown_content'] for row in cursor.fetchall()]
# Inject rules into test-fixer/auto-verify (future enhancement)

# 4. Report status
stats = get_stats()
print(f"Learning Engine: {stats['total_patterns']} patterns, "
      f"{stats['total_strategies']} strategies, "
      f"{stats['active_rules']} synthesized rules")

# 5. Create session metrics entry
update_session_metrics(session_id=current_session_id, started_at=now)
```

---

### On Session End (Automatic)

```python
# 1. Record final session metrics
update_session_metrics(
    session_id=current_session_id,
    ended_at=now,
    total_errors_encountered=error_count,
    total_auto_resolved=resolved_count,
    total_strategies_tried=strategy_count
)

# 2. Run synthesis check
new_rules = synthesize_rules(min_confidence=0.7, min_evidence=5)
if new_rules:
    update_session_metrics(
        session_id=current_session_id,
        rules_synthesized=len(new_rules)
    )
    print(f"✨ {len(new_rules)} new rules synthesized this session")

# 3. Report session stats
metrics = get_session_metrics(current_session_id)
print(f"\nSession Summary:")
print(f"  Errors: {metrics['total_errors_encountered']}")
print(f"  Auto-resolved: {metrics['total_auto_resolved']}")
print(f"  Success rate: {metrics['total_auto_resolved'] / max(metrics['total_errors_encountered'], 1):.1%}")
print(f"  New patterns: {metrics['new_patterns_discovered']}")
print(f"  Rules synthesized: {metrics['rules_synthesized']}")
```

---

## Integration with Other Skills

### With auto-verify

**Pre-check (Step 2c):** Before attempting fix, query knowledge base

**Post-record (Step 8):** After every fix attempt, record outcome

See Phase 2 modifications in implementation plan.

### With test-fixer

**Lookup (Step 0):** Check if test failure is known pattern

**Post-fix:** Record new strategies discovered during test fixing

See Phase 3 modifications in implementation plan.

### With health-check

Proactive scan uses knowledge.db to:
- Identify risky files (high error count)
- Detect unresolved patterns (auto_resolved_count = 0)
- Flag weak strategies (score < 0.2)

See Phase 4 in implementation plan.

---

## Error Fingerprinting

**Purpose:** Deduplicate errors by normalizing error messages and file paths.

**Algorithm:**

```python
def fingerprint(error_type, message, file_path):
    # Normalize message
    norm_msg = re.sub(r'\bline \d+\b', 'line N', message, flags=re.IGNORECASE)
    norm_msg = re.sub(r"'[^']*'", "'X'", norm_msg)
    norm_msg = re.sub(r'"[^"]*"', '"X"', norm_msg)
    norm_msg = re.sub(r'\d+', 'N', norm_msg)

    # Normalize file path to pattern
    if file_path:
        norm_file = re.sub(r'/[^/]+\.(py|js|vue)$', r'/*.\1', file_path)
    else:
        norm_file = ''

    # Hash
    raw = f"{error_type}|{norm_msg}|{norm_file}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

**Example:**

```python
# Error 1
fp1 = fingerprint("ImportError", "cannot import 'Foo' at line 42", "app/services/a.py")
# Normalized: "ImportError|cannot import 'X' at line N|app/services/*.py"
# → "abc123def456"

# Error 2 (same pattern, different specifics)
fp2 = fingerprint("ImportError", "cannot import 'Bar' at line 99", "app/services/b.py")
# Normalized: "ImportError|cannot import 'X' at line N|app/services/*.py"
# → "abc123def456" (SAME!)
```

See `references/error-fingerprinting.md` for complete guide.

---

## Strategy Scoring

**Formula:**

```python
raw_success_rate = success_count / max(total_attempts, 1)
recency_factor = 1.0 / (1.0 + days_since_last_use * 0.1)
confidence_factor = min(total_attempts / 10.0, 1.0)

current_score = (
    0.6 * raw_success_rate +
    0.3 * recency_factor +
    0.1 * confidence_factor
)
```

**Thresholds:**

- **0.7-1.0:** High confidence - try first
- **0.5-0.7:** Medium confidence - try if high-conf fails
- **0.3-0.5:** Low confidence - try only if no better options
- **< 0.3:** Very low / ineffective - skip or ask user

See `references/strategy-ranking.md` for worked examples.

---

## Rule Synthesis

**Criteria:**
- Success count ≥ 5
- Success rate ≥ 70%
- Not already synthesized

**Output:** Markdown rule injected into skill references

**Example:**

```markdown
## Auto: Fix Missing Import

**Error Type:** ImportError
**Confidence:** 88.2% (15/17 attempts)

**When to Apply:**
- Error type matches `ImportError`
- Pattern has been successful in 15 previous cases

**Steps:**
1. Identify missing module
2. Add import statement
3. Verify import path
```

See `references/synthesis-rules.md` for complete guide.

---

## References

- [Database Operations](references/db-operations.md) - Complete Python API reference
- [Error Fingerprinting](references/error-fingerprinting.md) - Normalization algorithm and examples
- [Strategy Ranking](references/strategy-ranking.md) - Scoring formula and thresholds
- [Synthesis Rules](references/synthesis-rules.md) - Rule generation and injection

---

## Implementation Status

**Phase 1: Foundation** ✅ Complete
- SQLite schema created
- db_helper.py with all operations
- Reference documentation
- Manual commands available

**Phase 2-3: Integration** 🚧 Pending
- auto-verify integration (Step 2c, Step 8)
- test-fixer integration (Step 0, post-fix recording)

**Phase 4: Health Check** 🚧 Pending
- health-check skill creation
- Proactive codebase scanning

**Phase 5: Documentation** 🚧 Pending
- CLAUDE.md updates
- Full verification plan
