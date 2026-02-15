---
name: reflect
description: Learning and self-modification with four modes - session (capture outcomes, update knowledge.db), deep (analyze gaps, modify skills/hooks), meta (convergence analysis), test-run (dry-run deep mode). Use after implement, run-tests, or fix-loop completes.
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: workflow
---

# reflect - Learning + Self-Modification

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

See [references/deep-mode.md](references/deep-mode.md) for complete documentation.

**Summary:**
1. Analyze workflow gaps (recurring failures, hook gaps, slow commands)
2. Propose modifications to skills/hooks
3. Ask user approval
4. Apply with safety checks (backup, validation, smoke tests)
5. Auto-escalate to meta mode if high modification frequency

---

## Mode: Meta & Test-Run

See [references/meta-mode.md](references/meta-mode.md) for complete documentation.

**Meta (Read-only):**
- Analyze modification patterns
- Assess convergence (CONVERGING/STABLE/DIVERGING)
- Detect high-churn files
- Generate meta-analysis report

**Test-Run (Dry-run):**
- Same as deep mode but no file modifications
- Only show proposed changes
- Preview before applying

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
  ✅ .claude/skills/fix-loop/SKILL.md (validated)

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
