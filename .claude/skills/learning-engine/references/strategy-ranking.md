# Strategy Ranking Reference

Complete guide to strategy scoring, time decay, and confidence thresholds.

## Overview

Fix strategies are ranked by a **composite score** (0.0-1.0) that balances:
1. **Success Rate** - Historical effectiveness (60% weight)
2. **Recency** - How recently strategy was used (30% weight)
3. **Confidence** - Number of attempts (10% weight)

Higher scores indicate better strategies to try first.

---

## Scoring Formula

### Components

```python
# 1. Raw Success Rate (0.0-1.0)
raw_success_rate = success_count / max(total_attempts, 1)

# 2. Recency Factor (0.0-1.0)
if last_used:
    days_since_last_use = (now - last_used).days
    recency_factor = 1.0 / (1.0 + days_since_last_use * 0.1)
else:
    recency_factor = 0.5  # Never used = middle value

# 3. Confidence Factor (0.0-1.0)
confidence_factor = min(total_attempts / 10.0, 1.0)

# Final Score
current_score = (
    0.6 * raw_success_rate +
    0.3 * recency_factor +
    0.1 * confidence_factor
)
current_score = max(0.0, min(1.0, current_score))  # Clamp to [0, 1]
```

### Weights Rationale

- **60% Success Rate** - Primary indicator; a strategy that works is most valuable
- **30% Recency** - Recent usage suggests relevance to current codebase state
- **10% Confidence** - Prefer strategies with evidence, but don't over-index on it

---

## Worked Examples

### Example 1: High-Performing Recent Strategy

**Data:**
- Success: 8/10 attempts (80% success rate)
- Last used: 2 days ago
- Total attempts: 10

**Calculation:**
```python
raw_success_rate = 8 / 10 = 0.80
recency_factor = 1.0 / (1.0 + 2 * 0.1) = 1.0 / 1.2 = 0.833
confidence_factor = min(10 / 10.0, 1.0) = 1.0

current_score = 0.6 * 0.80 + 0.3 * 0.833 + 0.1 * 1.0
              = 0.48 + 0.25 + 0.1
              = 0.83
```

**Interpretation:** ⭐ Excellent strategy - high success, recent, well-tested. **Try this first!**

---

### Example 2: Perfect But Untested Strategy

**Data:**
- Success: 1/1 attempts (100% success rate)
- Last used: 1 day ago
- Total attempts: 1

**Calculation:**
```python
raw_success_rate = 1 / 1 = 1.0
recency_factor = 1.0 / (1.0 + 1 * 0.1) = 1.0 / 1.1 = 0.909
confidence_factor = min(1 / 10.0, 1.0) = 0.1

current_score = 0.6 * 1.0 + 0.3 * 0.909 + 0.1 * 0.1
              = 0.60 + 0.273 + 0.01
              = 0.88
```

**Interpretation:** High score, but **low confidence**. One success doesn't prove effectiveness. Try it, but verify carefully.

---

### Example 3: Proven But Stale Strategy

**Data:**
- Success: 15/20 attempts (75% success rate)
- Last used: 30 days ago
- Total attempts: 20

**Calculation:**
```python
raw_success_rate = 15 / 20 = 0.75
recency_factor = 1.0 / (1.0 + 30 * 0.1) = 1.0 / 4.0 = 0.25
confidence_factor = min(20 / 10.0, 1.0) = 1.0

current_score = 0.6 * 0.75 + 0.3 * 0.25 + 0.1 * 1.0
              = 0.45 + 0.075 + 0.1
              = 0.625
```

**Interpretation:** Good success rate, well-tested, but **stale**. Codebase may have changed. Try it, but if it fails, downrank heavily.

---

### Example 4: Failing Strategy

**Data:**
- Success: 2/10 attempts (20% success rate)
- Last used: 5 days ago
- Total attempts: 10

**Calculation:**
```python
raw_success_rate = 2 / 10 = 0.20
recency_factor = 1.0 / (1.0 + 5 * 0.1) = 1.0 / 1.5 = 0.667
confidence_factor = min(10 / 10.0, 1.0) = 1.0

current_score = 0.6 * 0.20 + 0.3 * 0.667 + 0.1 * 1.0
              = 0.12 + 0.20 + 0.1
              = 0.42
```

**Interpretation:** ⚠ Low success rate. Try only if higher-ranked strategies fail. If this also fails, **skip all strategies below 0.4**.

---

### Example 5: Never Used Seeded Strategy

**Data:**
- Success: 0
- Last used: None
- Total attempts: 0

**Calculation:**
```python
raw_success_rate = 0 / 1 = 0.0  # max(total_attempts, 1) = 1
recency_factor = 0.5  # Never used
confidence_factor = min(0 / 10.0, 1.0) = 0.0

current_score = 0.6 * 0.0 + 0.3 * 0.5 + 0.1 * 0.0
              = 0.0 + 0.15 + 0.0
              = 0.15
```

**Interpretation:** Baseline score for untested strategies. Try only if no proven strategies exist. **High risk.**

---

## Time Decay Explanation

### Why Time Decay?

Codebase evolves:
- File paths change (reorganization)
- APIs change (broker updates)
- Dependencies update (breaking changes)

A strategy that worked 6 months ago may fail today due to these changes.

### Decay Function

```python
recency_factor = 1.0 / (1.0 + days_since_last_use * 0.1)
```

**Decay Rate:** 10% per day (0.1 coefficient)

| Days Since Last Use | Recency Factor | Score Impact (30% weight) |
|---------------------|----------------|---------------------------|
| 0 (today)           | 1.000          | +0.30                     |
| 5 days              | 0.667          | +0.20                     |
| 10 days             | 0.500          | +0.15                     |
| 20 days             | 0.333          | +0.10                     |
| 30 days             | 0.250          | +0.075                    |
| 60 days             | 0.143          | +0.043                    |

**Interpretation:**
- Recent (< 7 days): Full recency bonus
- Moderate (7-30 days): Partial bonus
- Stale (> 30 days): Minimal bonus

---

## Confidence Thresholds

### Decision Matrix

| Score Range | Confidence Level | Action |
|-------------|-----------------|--------|
| **0.7-1.0** | ⭐⭐⭐ High | Try first, high trust, expand test radius on success |
| **0.5-0.7** | ⭐⭐ Medium | Try if high-confidence strategies fail |
| **0.3-0.5** | ⭐ Low | Try only if no better options exist |
| **0.1-0.3** | ⚠ Very Low | Untested/unproven, risky |
| **< 0.1** | ❌ Ineffective | **Skip entirely** - proven to fail |

### Usage Guidelines

#### High Confidence (0.7-1.0)

```python
strategies = get_strategies("ImportError", limit=5)
high_conf = [s for s in strategies if s['effective_score'] >= 0.7]

if high_conf:
    # Try top strategy with confidence
    strategy = high_conf[0]
    print(f"Applying proven fix: {strategy['name']} (score: {strategy['effective_score']:.2f})")

    # On success: Expand test radius (verification loop)
    # On failure: Unexpected! Investigate codebase changes
```

#### Medium Confidence (0.5-0.7)

```python
medium_conf = [s for s in strategies if 0.5 <= s['effective_score'] < 0.7]

if medium_conf:
    # Try with caution
    strategy = medium_conf[0]
    print(f"Trying: {strategy['name']} (score: {strategy['effective_score']:.2f})")

    # On success: Standard verification
    # On failure: Expected, move to next strategy
```

#### Low Confidence (0.3-0.5)

```python
low_conf = [s for s in strategies if 0.3 <= s['effective_score'] < 0.5]

if low_conf and len(high_conf) == 0 and len(medium_conf) == 0:
    # Only try if no better options
    strategy = low_conf[0]
    print(f"⚠ Low-confidence attempt: {strategy['name']} (score: {strategy['effective_score']:.2f})")

    # On failure: Quickly move to next or ask user
```

#### Very Low / Ineffective (< 0.3)

```python
ineffective = [s for s in strategies if s['effective_score'] < 0.3]

# Skip entirely or ask user
if len(strategies) > 0 and strategies[0]['effective_score'] < 0.3:
    print("All strategies have low confidence. Asking user for guidance.")
    # Trigger stuck condition
```

---

## When to Try Untested Strategies

**Scenario:** No existing strategies for error type, or all strategies have score < 0.3.

**Approach:**

1. **Check for similar error types:**
   ```python
   # If no strategies for "TestFailure:SelectorNotFound", try broader "TestFailure"
   strategies = get_strategies("TestFailure", limit=5)
   ```

2. **Seed a new strategy from common patterns:**
   - Consult existing documentation (test-fixer, auto-verify references)
   - Apply heuristic fix
   - **Record as new strategy** with source='learned'

3. **Ask user if completely unknown:**
   ```
   I don't have any proven strategies for this error type.
   Would you like me to:
   1. Try a heuristic approach (describe it)
   2. Skip and ask for manual guidance
   ```

---

## Score Adjustment on Fix Outcome

### After Recording an Attempt

```python
# Record attempt
record_attempt(
    error_pattern_id=err_id,
    strategy_id=strategy['id'],
    outcome='success',  # or 'failure'
    ...
)

# Update strategy score (automatic in record_attempt)
update_strategy_score(strategy['id'])
```

### Manual Boosting (Verification Loop Success)

If fix passes expanded verification (adjacent features also pass):

```python
# Boost score by 0.1 (verified fix bonus)
conn.execute(
    "UPDATE fix_strategies SET current_score = MIN(current_score + 0.1, 1.0) WHERE id = ?",
    (strategy['id'],)
)
```

### Manual Downranking (Revert Detected)

If fix is later reverted:

```python
# Decrease score by 0.2 (revert penalty)
conn.execute(
    "UPDATE fix_strategies SET current_score = MAX(current_score - 0.2, 0.0) WHERE id = ?",
    (strategy['id'],)
)
```

---

## Periodic Rule Synthesis

Strategies that consistently succeed (≥70% success, ≥5 attempts) are promoted to **synthesized rules**.

**Check Criteria:**

```python
from db_helper import synthesize_rules

# Run synthesis (e.g., on session end)
new_rules = synthesize_rules(min_confidence=0.7, min_evidence=5)

if new_rules:
    print(f"✨ {len(new_rules)} new rules synthesized!")
    for rule in new_rules:
        print(f"  - {rule['rule_name']} ({rule['confidence']:.1%} confidence)")
```

**Graduation Criteria:**
- Strategy score ≥ 0.7
- Success count ≥ 5
- Success rate ≥ 70%
- Not already synthesized

**Effect:**
- Creates entry in `synthesized_rules` table
- Generates markdown content for injection into test-fixer/auto-verify
- Original strategy remains in `fix_strategies` (rules don't replace strategies)

---

## Best Practices

1. **Always sort by effective_score** (with time decay applied), not raw current_score
2. **Skip strategies < 0.1** - proven ineffective, waste of time
3. **Boost on verified success** - expands confidence faster
4. **Downrank heavily on revert** - indicates fix was wrong
5. **Re-test stale strategies** (> 30 days) - codebase may have changed
6. **Track new strategies as 'learned'** - distinguish from seeded baselines

---

## Debugging Strategy Scores

### View Strategy History

```python
from db_helper import get_connection

conn = get_connection()
cursor = conn.execute(
    """SELECT s.name, s.current_score, s.success_count, s.total_attempts,
              COUNT(a.id) as recent_attempts
       FROM fix_strategies s
       LEFT JOIN fix_attempts a ON a.strategy_id = s.id AND a.created_at > datetime('now', '-7 days')
       WHERE s.error_type = ?
       GROUP BY s.id
       ORDER BY s.current_score DESC""",
    ('ImportError',)
)

for row in cursor.fetchall():
    print(f"{row['name']}: score={row['current_score']:.2f}, "
          f"success={row['success_count']}/{row['total_attempts']}, "
          f"recent_attempts={row['recent_attempts']}")
```

### Manually Adjust Score (Testing)

```python
# Temporarily boost a strategy for testing
conn.execute(
    "UPDATE fix_strategies SET current_score = 0.9 WHERE name = ?",
    ('Fix Missing Import',)
)
conn.commit()
```

### Reset All Scores (Dangerous!)

```python
# Reset all strategies to baseline 0.5
conn.execute("UPDATE fix_strategies SET current_score = 0.5, success_count = 0, failure_count = 0, total_attempts = 0")
conn.commit()
```
