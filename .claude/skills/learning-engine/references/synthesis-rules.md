# Rule Synthesis Reference

Complete guide to automatic rule generation from successful fix strategies.

## Overview

**Rule Synthesis** is the process of promoting proven fix strategies into **reusable, injectable rules** that can be automatically applied to similar errors in future sessions.

**Purpose:**
- Codify successful patterns into documentation
- Auto-inject rules into test-fixer and auto-verify skills
- Reduce manual intervention over time (autonomous learning)

---

## Synthesis Algorithm

### Trigger Conditions

Rule synthesis runs:
1. **On session end** (automatic via save-session integration)
2. **On manual command** `/learning-engine synthesize`
3. **Periodically** (every N fix attempts, configurable)

### Eligibility Criteria

A strategy is eligible for synthesis if:

```python
# Must meet ALL criteria:
1. success_count >= min_evidence (default: 5)
2. total_attempts >= min_evidence
3. current_score >= min_confidence (default: 0.7)
4. source != 'synthesized' (don't synthesize already-synthesized rules)
5. NOT EXISTS in synthesized_rules table (no duplicates)
```

**Rationale:**
- **≥5 evidence instances:** Prevents one-off flukes from becoming rules
- **≥70% confidence:** Only proven-effective strategies graduate
- **Not already synthesized:** Avoids duplicates

### Synthesis Process

```python
from db_helper import synthesize_rules

# Run synthesis
new_rules = synthesize_rules(min_confidence=0.7, min_evidence=5)

for rule in new_rules:
    print(f"✨ Synthesized: {rule['rule_name']}")
    print(f"   Confidence: {rule['confidence']:.1%}")
    print(f"   Evidence: {rule['evidence_count']} successful fixes")
```

**Database Operations:**
1. Query `fix_strategies` for eligible strategies
2. For each eligible strategy:
   - Calculate final confidence score
   - Generate markdown content from strategy data
   - Insert into `synthesized_rules` table
3. Return list of newly created rules

---

## Graduation Criteria

### Minimum Evidence (Default: 5)

**Why 5?**
- 1-2 successes: Could be luck
- 3-4 successes: Pattern emerging, but not proven
- 5+ successes: High confidence in effectiveness

**Adjust for different contexts:**
```python
# Strict: Require 10+ successes
synthesize_rules(min_evidence=10)

# Lenient: Accept 3+ successes (testing mode)
synthesize_rules(min_evidence=3)
```

### Minimum Confidence (Default: 0.7 = 70%)

**Why 70%?**
- Balances proven effectiveness with reasonable attempt count
- Below 70%: Too many failures, not reliable
- Above 80%: Too strict, may take long to reach

**Confidence Calculation:**
```python
confidence = success_count / max(total_attempts, 1)

# Examples:
# 7/10 = 0.70 → Eligible
# 8/10 = 0.80 → Eligible (even better)
# 5/10 = 0.50 → NOT eligible (too many failures)
```

---

## Generated Rule Structure

### Markdown Template

Synthesized rules follow this structure:

```markdown
## {Strategy Name}

**Error Type:** {error_type}
**Confidence:** {confidence}% ({success_count}/{total_attempts} attempts)

**Description:** {description}

**When to Apply:**
- Error type matches `{error_type}`
- Pattern has been successful in {success_count} previous cases
{Additional preconditions if specified}

**Steps:**
1. {step_1}
2. {step_2}
...

**Auto-synthesized:** {timestamp}
```

### Example: Fix Missing Import Rule

**Source Strategy:**
```python
{
    "name": "Fix Missing Import",
    "error_type": "ImportError",
    "description": "Add missing import statement at file top",
    "steps": ["Identify missing module", "Add import statement", "Verify import path"],
    "success_count": 12,
    "total_attempts": 15,
    "current_score": 0.82
}
```

**Synthesized Rule:**

```markdown
## Fix Missing Import

**Error Type:** ImportError
**Confidence:** 80.0% (12/15 attempts)

**Description:** Add missing import statement at file top

**When to Apply:**
- Error type matches `ImportError`
- Pattern has been successful in 12 previous cases

**Steps:**
1. Identify missing module
2. Add import statement
3. Verify import path

**Auto-synthesized:** 2025-01-15T14:23:45Z
```

---

## Rule Storage

### Database Schema

```sql
CREATE TABLE synthesized_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    condition_pattern TEXT NOT NULL,         -- When to apply
    action_pattern TEXT NOT NULL,            -- What to do (JSON steps)
    confidence REAL NOT NULL,                -- 0.0-1.0
    evidence_count INTEGER NOT NULL,         -- Number of successful fixes
    markdown_content TEXT NOT NULL,          -- Full rule as markdown
    created_at TEXT NOT NULL,
    superseded_by INTEGER REFERENCES synthesized_rules(id)
);
```

### Rule Naming Convention

```
rule_name = "Auto: {original_strategy_name}"

Examples:
- "Auto: Fix Missing Import"
- "Auto: Update Stale Selector"
- "Auto: Fix Async Timing"
```

**Why "Auto:" prefix?**
- Distinguishes synthesized rules from manually written ones
- Makes it clear this is machine-generated
- Allows filtering in queries

---

## Integration with Skills

### Injection Points

Synthesized rules are **auto-injected** into skill documentation:

#### 1. test-fixer/references/common-failure-patterns.md

**Marker:**
```markdown
## Synthesized Patterns (Auto-Generated)

<!-- LEARNING_ENGINE_SYNTHESIS_MARKER - Do not remove -->
<!-- Auto-generated rules will be inserted below this line -->
```

**Injection:**
On session start, learning-engine skill:
1. Reads all active synthesized rules (WHERE superseded_by IS NULL)
2. Filters by error_type = 'TestFailure'
3. Injects markdown_content below marker
4. Rules are available to test-fixer during session

#### 2. auto-verify/references/ (Future)

Similar injection for error types handled by auto-verify.

### Manual Injection (for testing)

```python
from db_helper import get_connection

conn = get_connection()
cursor = conn.execute(
    """SELECT markdown_content FROM synthesized_rules
       WHERE error_type = ? AND superseded_by IS NULL
       ORDER BY confidence DESC""",
    ('TestFailure',)
)

rules_md = '\n\n---\n\n'.join(row['markdown_content'] for row in cursor.fetchall())
print(rules_md)
```

---

## Rule Evolution and Superseding

### When Strategies Improve

If a strategy gets updated (e.g., additional steps added) and achieves higher confidence:

**Option 1: Create New Rule, Supersede Old**

```python
# Mark old rule as superseded
conn.execute(
    "UPDATE synthesized_rules SET superseded_by = ? WHERE id = ?",
    (new_rule_id, old_rule_id)
)
```

**Option 2: Update Existing Rule**

```python
# Update markdown_content and confidence
conn.execute(
    """UPDATE synthesized_rules
       SET markdown_content = ?, confidence = ?, evidence_count = ?
       WHERE id = ?""",
    (new_markdown, new_confidence, new_evidence, rule_id)
)
```

**Recommended:** Use Option 1 (superseding) to maintain history and auditability.

---

## Synthesis Examples

### Example 1: ImportError Fix Graduates

**Initial Strategy (Seeded):**
```
Name: Fix Missing Import
Error Type: ImportError
Success: 0/0 (never used)
Score: 0.5 (baseline)
Source: seeded
```

**After 8 Fixes:**
```
Success: 7/8 (87.5% success rate)
Score: 0.78
```

**Synthesis Check:**
```python
synthesize_rules(min_confidence=0.7, min_evidence=5)

# Result:
# ✨ New rule: "Auto: Fix Missing Import"
# Confidence: 87.5% (7/8 attempts)
# Rule inserted into synthesized_rules table
```

---

### Example 2: TestFailure Selector Update

**Initial Strategy (Learned):**
```
Name: Update Stale Selector
Error Type: TestFailure
Success: 0/0
Source: learned (created during a session)
```

**After 12 Fixes:**
```
Success: 10/12 (83.3% success rate)
Score: 0.81
```

**Synthesis:**
```python
# Eligible! Success rate > 70%, evidence >= 5
new_rules = synthesize_rules()

# Result:
# Rule "Auto: Update Stale Selector" created
# Injected into test-fixer/references/common-failure-patterns.md
```

---

### Example 3: Strategy Below Threshold

**Strategy:**
```
Name: Clear Build Cache
Error Type: BuildError
Success: 3/6 (50% success rate)
Score: 0.42
```

**Synthesis Check:**
```python
synthesize_rules(min_confidence=0.7, min_evidence=5)

# Result:
# Not eligible - confidence too low (50% < 70%)
# Strategy remains in fix_strategies, not promoted to rule
```

---

## Preventing Duplicate Rules

### Uniqueness Check

Before inserting a new rule:

```python
cursor = conn.execute(
    """SELECT id FROM synthesized_rules
       WHERE rule_name = ? AND error_type = ? AND superseded_by IS NULL""",
    (rule_name, error_type)
)

if cursor.fetchone():
    # Rule already exists, skip
    continue
```

**Duplicate Prevention:**
- Rule name + error type must be unique (unless superseded)
- Multiple strategies for same error type → multiple rules (OK)
- Same strategy synthesized twice → duplicate detected, skipped

---

## Rule Maintenance

### Periodic Review

On session start, check for stale rules:

```python
from datetime import datetime, timedelta

# Find rules created > 90 days ago
stale_threshold = (datetime.utcnow() - timedelta(days=90)).isoformat()

cursor = conn.execute(
    """SELECT id, rule_name, created_at FROM synthesized_rules
       WHERE created_at < ? AND superseded_by IS NULL""",
    (stale_threshold,)
)

stale_rules = cursor.fetchall()
if stale_rules:
    print(f"⚠ {len(stale_rules)} rules are >90 days old. Consider review.")
```

### Removing Bad Rules

If a synthesized rule later proves ineffective (detected via revert feedback):

```python
# Option 1: Soft delete (supersede with NULL)
conn.execute(
    "UPDATE synthesized_rules SET superseded_by = -1 WHERE id = ?",
    (rule_id,)
)

# Option 2: Hard delete (rare)
conn.execute("DELETE FROM synthesized_rules WHERE id = ?", (rule_id,))
```

---

## Synthesis Statistics

### Track Synthesis Rate

```python
from db_helper import get_connection

conn = get_connection()

# Total synthesized rules
cursor = conn.execute(
    "SELECT COUNT(*) as count FROM synthesized_rules WHERE superseded_by IS NULL"
)
active_rules = cursor.fetchone()['count']

# Rules per error type
cursor = conn.execute(
    """SELECT error_type, COUNT(*) as count FROM synthesized_rules
       WHERE superseded_by IS NULL
       GROUP BY error_type
       ORDER BY count DESC"""
)

print("=== Synthesized Rules by Error Type ===")
for row in cursor.fetchall():
    print(f"{row['error_type']}: {row['count']} rules")
```

### Session Metrics

```python
from db_helper import update_session_metrics

# Record rule synthesis in session
update_session_metrics(
    session_id='session_123',
    rules_synthesized=len(new_rules)
)
```

---

## Future Enhancements

### Auto-Pruning Low-Performing Rules

If a synthesized rule's underlying strategy later drops below 50% success:

```python
# Find rules with degraded strategies
cursor = conn.execute(
    """SELECT r.id, r.rule_name, s.current_score
       FROM synthesized_rules r
       JOIN fix_strategies s ON s.name = REPLACE(r.rule_name, 'Auto: ', '')
       WHERE s.current_score < 0.5 AND r.superseded_by IS NULL"""
)

for row in cursor.fetchall():
    print(f"⚠ Rule '{row['rule_name']}' strategy degraded to {row['current_score']:.2f}")
    # Optionally supersede or flag for review
```

### Cross-Error-Type Pattern Detection

Detect patterns that work across multiple error types:

```python
# Find strategies with similar steps across error types
# (e.g., "Check file path" appears in ImportError, BuildError, ModuleNotFoundError)
# → Synthesize a meta-rule
```

---

## Best Practices

1. **Run synthesis on session end** - Captures learning while context is fresh
2. **Use default thresholds (70%, 5 evidence)** - Proven balance for most cases
3. **Review synthesized rules monthly** - Remove outdated or ineffective rules
4. **Track synthesis rate** - Should increase over time as system learns
5. **Don't over-synthesize** - If too many rules exist, consider consolidation
6. **Inject rules into relevant skills** - Rules are useless if not accessible

---

## CLI Usage

```bash
cd .claude/learning

# Force synthesis check
python -c "from db_helper import synthesize_rules; print(synthesize_rules())"

# View all active rules
python -c "
from db_helper import get_connection
conn = get_connection()
cursor = conn.execute('SELECT rule_name, confidence, evidence_count FROM synthesized_rules WHERE superseded_by IS NULL ORDER BY confidence DESC')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]:.1%} ({row[2]} evidence)')
"
```
