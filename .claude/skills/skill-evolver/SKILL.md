---
name: skill-evolver
description: Autonomous skill creation and lifecycle management. Discovers skill gaps from session patterns and knowledge.db, creates new skills from templates, evolves underperforming skills via reflect-deep, and prunes dead/redundant skills. Self-healing loop that closes the gap between learning-engine insights and actionable automation.
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: meta-workflow
---

# skill-evolver — Autonomous Skill Creation & Lifecycle

**Purpose:** Close the automation loop. `learning-engine` learns from errors, `reflect` analyzes gaps, but neither **creates new skills**. This skill bridges that gap — it discovers what's missing, creates new skills, evolves weak ones, and prunes dead ones.

**Key principle:** Every repeated manual workflow is a skill waiting to be born.

## When to Use

- After `reflect deep` identifies workflow gaps that need a NEW skill (not just a patch)
- When the same manual multi-step workflow is performed 3+ times across sessions
- When `learning-engine` detects error patterns with no matching skill coverage
- On explicit invocation: "evolve skills", "create skill", "improve skills", "skill gap"
- Periodically (every 10-15 sessions) for prune/audit

## When NOT to Use

- To modify an existing skill's steps → use `reflect deep` instead
- To fix a single test failure → use `test-fixer`
- To record an error pattern → use `learning-engine`
- For one-off tasks that won't recur

---

## Architecture: Where skill-evolver Fits

```
learning-engine (records errors, ranks strategies)
       |
       v
reflect session (captures outcomes to knowledge.db)
       |
       v
reflect deep (analyzes gaps, patches existing skills)
       |
       v
skill-evolver discover (finds gaps that need NEW skills, not patches)
       |
       v
skill-evolver create (builds new skill from template)
       |
       v
health-check (validates no conflicts, runs audit)
```

**Data flow:**
- **Input:** knowledge.db tables (`error_patterns`, `fix_strategies`, `synthesized_rules`), session logs (`.claude/logs/`), git history
- **Output:** New skill directories in `.claude/skills/`, lifecycle records in knowledge.db `skill_lifecycle` table

---

## Mode 1: Discover

**Purpose:** Scan for skill gaps — recurring patterns that should be automated but aren't.

### Data Sources (checked in order)

**Source 1: knowledge.db — Unresolved patterns without skill coverage**
```python
from db_helper import get_connection

conn = get_connection()

# Find error types that recur but have no high-confidence strategy
cursor = conn.execute('''
    SELECT ep.error_type, ep.message_pattern, ep.occurrence_count,
           MAX(fs.current_score) as best_strategy_score
    FROM error_patterns ep
    LEFT JOIN fix_strategies fs ON ep.error_type = fs.error_type
    WHERE ep.occurrence_count >= 3
    GROUP BY ep.error_type
    HAVING best_strategy_score IS NULL OR best_strategy_score < 0.3
    ORDER BY ep.occurrence_count DESC
''')

uncovered_patterns = cursor.fetchall()
```

**Source 2: Session logs — Repeated manual workflows**
```python
from pathlib import Path
import json

log_file = Path(".claude/logs/workflow-sessions.log")

# Count tool-call sequences that repeat across sessions
# A "workflow" = sequence of 3+ tool calls with same pattern
workflow_sequences = {}

for line in log_file.open():
    session = json.loads(line)
    if session.get('tool_sequence'):
        seq_key = tuple(session['tool_sequence'][:5])  # First 5 tools as fingerprint
        workflow_sequences[seq_key] = workflow_sequences.get(seq_key, 0) + 1

# Filter: 3+ occurrences = skill candidate
candidates = {k: v for k, v in workflow_sequences.items() if v >= 3}
```

**Source 3: Git history — Recurring fix patterns**
```bash
# Files fixed 3+ times in last 30 days (same file, different commits)
git log --since="30 days ago" --diff-filter=M --name-only --format="" | \
    sort | uniq -c | sort -rn | awk '$1 >= 3 {print $1, $2}' | head -10
```

**Source 4: Existing skills — Coverage gaps**
```python
# Map skills to the error_types they handle
skill_coverage = {
    'test-fixer': ['TestFailure', 'SelectorNotFound', 'TimeoutError'],
    'fix-loop': ['*'],  # Generic
    'auto-verify': ['BuildError', 'RuntimeError'],
}

# Find error_types from knowledge.db not covered by any specific skill
all_error_types = set(row[0] for row in conn.execute(
    'SELECT DISTINCT error_type FROM error_patterns WHERE occurrence_count >= 2'
).fetchall())

covered = set()
for types in skill_coverage.values():
    if '*' not in types:
        covered.update(types)

uncovered = all_error_types - covered
```

### Discover Output

```
=== Skill Gap Discovery Report ===

Skill Candidates (ranked by impact):

1. [HIGH] Database Migration Fixer
   Source: knowledge.db — 7 occurrences of AlembicError with no strategy
   Pattern: "Target database is not up to date" / "Can't locate revision"
   Estimated saves: ~15 min per occurrence

2. [MEDIUM] WebSocket Reconnection Handler
   Source: Session logs — 4 sessions had manual WS reconnect workflow
   Pattern: Read logs → kill WS → restart → verify ticks
   Estimated saves: ~5 min per occurrence

3. [LOW] Stale Branch Cleaner
   Source: Git history — 3 manual branch cleanup sessions
   Pattern: List branches → check merged → delete stale
   Estimated saves: ~3 min per occurrence

Already Covered:
  - ImportError → learning-engine has 3 strategies (avg score 0.78)
  - TestFailure → test-fixer skill handles this
  - BuildError → auto-verify handles this

Would you like to create any of these skills? [1/2/3/all/skip]
```

---

## Mode 2: Create

**Purpose:** Generate a new skill from the standard template, with user approval at every step.

### Step 1: Gather Requirements

```python
# If called from discover mode, requirements come from the gap analysis
# If called directly, ask the user

from hook_utils import AskUserQuestion

if not requirements:
    answer = AskUserQuestion(
        questions=[{
            "question": "What should this new skill automate?",
            "header": "Skill Purpose",
            "multiSelect": False,
            "options": [
                {"label": "Error fix pattern", "description": "Automate fixing a recurring error type"},
                {"label": "Multi-step workflow", "description": "Automate a manual workflow I keep repeating"},
                {"label": "Code generation", "description": "Generate boilerplate code for a pattern"},
                {"label": "Validation/audit", "description": "Check codebase for a specific quality rule"}
            ]
        }]
    )
```

### Step 2: Generate Skill Skeleton

```python
SKILL_TEMPLATE = '''---
name: {name}
description: {description}
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: {category}
  created_by: skill-evolver
  created_from: {source}
---

# {display_name}

**Purpose:** {purpose}

## When to Use

{when_to_use}

## When NOT to Use

{when_not_to_use}

---

## Steps

{steps}

---

## Integration

{integration}

---

## References

- Created by skill-evolver from {source}
- Related skills: {related_skills}
'''

# Fill template from requirements
skill_content = SKILL_TEMPLATE.format(
    name=slugify(skill_name),
    description=description,
    category=detect_category(requirements),
    source=source_mode,  # "discover", "user-request", "reflect-deep"
    display_name=skill_name,
    purpose=purpose,
    when_to_use=generate_when_to_use(requirements),
    when_not_to_use=generate_when_not_to_use(requirements),
    steps=generate_steps(requirements),
    integration=generate_integration(requirements),
    related_skills=find_related_skills(requirements)
)
```

### Step 3: User Review & Approval

```python
# Show the generated skill content to user
print(f"\n{'='*60}")
print(f"Generated Skill: {skill_name}")
print(f"{'='*60}")
print(skill_content)
print(f"{'='*60}")

# MANDATORY: Ask user approval before writing ANY files
answer = AskUserQuestion(
    questions=[{
        "question": f"Create skill '{skill_name}' with the above content?",
        "header": "Approve Skill",
        "multiSelect": False,
        "options": [
            {"label": "Create", "description": "Create the skill directory and SKILL.md"},
            {"label": "Edit first", "description": "Let me modify the content before creating"},
            {"label": "Cancel", "description": "Don't create this skill"}
        ]
    }]
)

if answer == "Cancel":
    print("Skill creation cancelled.")
    return
```

### Step 4: Write Files

```python
from pathlib import Path

skill_dir = Path(f".claude/skills/{skill_slug}")
skill_dir.mkdir(parents=True, exist_ok=True)
(skill_dir / "references").mkdir(exist_ok=True)

# Write SKILL.md
Write(
    file_path=str(skill_dir / "SKILL.md"),
    content=skill_content
)

# Write references if applicable
if reference_content:
    Write(
        file_path=str(skill_dir / "references" / "patterns.md"),
        content=reference_content
    )

print(f"\n Created: .claude/skills/{skill_slug}/")
print(f"  - SKILL.md ({len(skill_content)} chars)")
if reference_content:
    print(f"  - references/patterns.md")
```

### Step 5: Register in knowledge.db

```python
conn = get_connection()
conn.execute('''
    INSERT INTO skill_lifecycle (
        skill_name, created_at, created_by, source,
        version, status, invocation_count, success_count,
        last_invoked_at, performance_score
    ) VALUES (?, datetime('now'), 'skill-evolver', ?, '1.0', 'active', 0, 0, NULL, NULL)
''', (skill_name, source_mode))
conn.commit()

print(f"Registered in knowledge.db skill_lifecycle table")
```

### Step 6: Validation

```python
# Verify the skill file is valid markdown with required sections
skill_file = skill_dir / "SKILL.md"
content = skill_file.read_text()

checks = {
    'Has frontmatter': content.startswith('---'),
    'Has name field': 'name:' in content.split('---')[1],
    'Has description': 'description:' in content.split('---')[1],
    'Has When to Use': '## When to Use' in content,
    'Has Steps or Algorithm': '## Steps' in content or '## Algorithm' in content,
}

all_passed = all(checks.values())
for check, passed in checks.items():
    status = 'PASS' if passed else 'FAIL'
    print(f"  [{status}] {check}")

if not all_passed:
    print("\n Warning: Skill validation has failures. Review and fix manually.")
else:
    print(f"\n Skill '{skill_name}' created and validated successfully!")
```

---

## Mode 3: Evolve

**Purpose:** Improve underperforming skills. Delegates modification to `reflect deep` but adds lifecycle tracking and structural changes (split/merge).

### When to Trigger

```python
# Auto-trigger when:
# 1. A skill's success rate drops below 50% after 10+ invocations
# 2. A skill hasn't been updated in 30+ days but has recent failures
# 3. Two skills have >60% overlap in their trigger conditions

conn = get_connection()

# Check underperforming skills
underperforming = conn.execute('''
    SELECT skill_name, invocation_count, success_count,
           CAST(success_count AS FLOAT) / MAX(invocation_count, 1) as success_rate
    FROM skill_lifecycle
    WHERE invocation_count >= 10
      AND CAST(success_count AS FLOAT) / MAX(invocation_count, 1) < 0.5
    ORDER BY success_rate ASC
''').fetchall()
```

### Evolution Strategies

**Strategy 1: Patch (delegate to reflect deep)**
```python
# For skills with specific failing steps
# Invoke reflect deep targeting the skill
Skill("reflect", args=f"deep --target .claude/skills/{skill_name}/SKILL.md")
```

**Strategy 2: Split**
```python
# When a skill is too broad (handles too many unrelated patterns)
# Propose splitting into focused sub-skills

print(f"Skill '{skill_name}' handles {len(patterns)} different patterns.")
print(f"Recommend splitting into:")
for cluster in pattern_clusters:
    print(f"  - {cluster['name']}: {len(cluster['patterns'])} patterns")

# Requires user approval, then calls create mode for each sub-skill
```

**Strategy 3: Merge**
```python
# When two skills overlap significantly
# Propose merging into one unified skill

print(f"Skills '{skill_a}' and '{skill_b}' overlap by {overlap_pct:.0%}")
print(f"Recommend merging into '{merged_name}'")

# Requires user approval
# Creates new skill, marks old ones as deprecated
```

### Evolution Output

```
=== Skill Evolution Report ===

Underperforming Skills:
  1. fix-loop (42% success, 24 invocations)
     Issue: Steps 3-4 frequently fail on async errors
     Recommendation: Patch — add async-specific strategy branch

  2. e2e-test-generator (38% success, 16 invocations)
     Issue: Generated tests often miss data-testid selectors
     Recommendation: Patch — inject audit-testids check before generation

Overlap Detected:
  - test-fixer + fix-loop: 65% trigger overlap
    Recommendation: Clarify trigger boundaries (test-fixer = test-specific, fix-loop = general)

Action: [patch-all / review / skip]
```

---

## Mode 4: Prune

**Purpose:** Identify dead, redundant, or conflicting skills for cleanup.

### Prune Criteria

```python
from pathlib import Path
from datetime import datetime, timedelta

# Criterion 1: Never invoked (exists but never triggered)
never_invoked = conn.execute('''
    SELECT skill_name FROM skill_lifecycle
    WHERE invocation_count = 0
      AND created_at < datetime('now', '-14 days')
''').fetchall()

# Criterion 2: Not invoked recently (20+ sessions)
stale_skills = conn.execute('''
    SELECT skill_name, last_invoked_at, invocation_count
    FROM skill_lifecycle
    WHERE last_invoked_at < datetime('now', '-60 days')
      AND status = 'active'
    ORDER BY last_invoked_at ASC
''').fetchall()

# Criterion 3: Very low success rate after sufficient attempts
failing_skills = conn.execute('''
    SELECT skill_name, success_count, invocation_count,
           CAST(success_count AS FLOAT) / MAX(invocation_count, 1) as rate
    FROM skill_lifecycle
    WHERE invocation_count >= 10
      AND CAST(success_count AS FLOAT) / MAX(invocation_count, 1) < 0.3
''').fetchall()

# Criterion 4: Conflict with current rules.md
# Read rules.md and check if any skill violates architectural rules
rules_content = Path(".claude/rules.md").read_text()
for skill_dir in Path(".claude/skills/").iterdir():
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        skill_content = skill_md.read_text()
        conflicts = check_rule_conflicts(skill_content, rules_content)
        if conflicts:
            conflicting_skills.append((skill_dir.name, conflicts))
```

### Prune Actions (ALL require user approval)

```python
# Present findings
print("=== Skill Prune Report ===\n")

if never_invoked:
    print(f"Never Invoked ({len(never_invoked)} skills):")
    for skill in never_invoked:
        print(f"  - {skill[0]} (created but never triggered)")

if stale_skills:
    print(f"\nStale ({len(stale_skills)} skills):")
    for skill in stale_skills:
        print(f"  - {skill[0]} (last invoked: {skill[1]}, total: {skill[2]} times)")

if failing_skills:
    print(f"\nFailing ({len(failing_skills)} skills):")
    for skill in failing_skills:
        print(f"  - {skill[0]} ({skill[3]:.0%} success rate, {skill[2]} invocations)")

# Ask user what to do
answer = AskUserQuestion(
    questions=[{
        "question": "How should we handle these skills?",
        "header": "Prune Action",
        "multiSelect": False,
        "options": [
            {"label": "Archive stale", "description": "Move stale/never-invoked to .claude/skills/_archived/"},
            {"label": "Delete failing", "description": "Remove skills with <30% success rate"},
            {"label": "Review each", "description": "Go through each skill individually"},
            {"label": "Skip", "description": "Take no action"}
        ]
    }]
)

# Archive = move to _archived/ directory (reversible)
# Delete = remove directory entirely (irreversible, git can recover)
# NEVER auto-delete without explicit user confirmation
```

---

## knowledge.db Schema Addition

```sql
-- Add to existing knowledge.db (managed by learning-engine)
CREATE TABLE IF NOT EXISTS skill_lifecycle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'manual',          -- 'manual', 'skill-evolver', 'reflect-deep'
    source TEXT,                                -- 'discover', 'user-request', 'reflect-deep'
    version TEXT DEFAULT '1.0',
    status TEXT DEFAULT 'active',               -- 'active', 'deprecated', 'archived'
    invocation_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_invoked_at TIMESTAMP,
    last_evolved_at TIMESTAMP,
    performance_score REAL,                     -- 0.0 to 1.0, computed
    notes TEXT
);

-- Track skill evolution history
CREATE TABLE IF NOT EXISTS skill_evolution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL,
    evolution_type TEXT NOT NULL,               -- 'created', 'patched', 'split', 'merged', 'archived', 'pruned'
    description TEXT,
    before_version TEXT,
    after_version TEXT,
    evolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evolved_by TEXT DEFAULT 'skill-evolver'
);
```

---

## Safety Guards

1. **User approval required** for ALL file operations (create, modify, delete, archive)
2. **Deny list** — NEVER create skills that modify:
   - `CLAUDE.md` (root or sub-project)
   - `.env` files
   - `alembic/versions/*`
   - Production paths (`C:\Apps\*`)
3. **Validation gate** — every created skill must pass:
   - Valid YAML frontmatter
   - Required sections: name, description, When to Use, Steps
   - No conflicts with `.claude/rules.md`
4. **Git safety** — created skills are NOT auto-committed. User decides when to commit.
5. **No recursive skill creation** — skill-evolver cannot create another skill-evolver or modify itself

---

## Manual Commands

```bash
/skill-evolver discover              # Scan for skill gaps
/skill-evolver create                # Create new skill interactively
/skill-evolver create --template     # Show blank skill template only
/skill-evolver evolve                # Analyze and improve weak skills
/skill-evolver evolve --target=NAME  # Evolve a specific skill
/skill-evolver prune                 # Identify dead/redundant skills
/skill-evolver status                # Show skill lifecycle stats
```

### Status Output

```
=== Skill Lifecycle Dashboard ===

Total Skills: 31
  Active: 28    Deprecated: 2    Archived: 1

Top 5 by Invocation:
  1. auto-verify      (142 invocations, 94% success)
  2. test-fixer       (89 invocations, 78% success)
  3. implement        (67 invocations, 85% success)
  4. fix-loop         (52 invocations, 71% success)
  5. run-tests        (48 invocations, 92% success)

Skills Created by Evolver: 3
  - migration-fixer (active, 12 invocations, 83% success)
  - ws-reconnector  (active, 5 invocations, 80% success)
  - branch-cleaner  (archived — merged into health-check)

Needs Attention:
  - e2e-test-generator: 38% success rate (below 50% threshold)
  - debug-log: 0 invocations in 45 days

Next recommended action: /skill-evolver evolve --target=e2e-test-generator
=====================================
```

---

## Integration with Existing Skills

| Skill | Relationship |
|-------|-------------|
| `learning-engine` | **Data source** — provides error patterns, strategy scores, risk data |
| `reflect session` | **Upstream trigger** — captures outcomes that feed discover mode |
| `reflect deep` | **Delegate** — evolve mode delegates modifications to reflect deep |
| `health-check` | **Downstream validator** — validates created skills don't conflict |
| `implement` | **Consumer** — new skills become available for implement workflow |
| `docs-maintainer` | **Post-action** — invoke after creating skills to update docs |

---

## References

- [Skill Template](references/skill-template.md) — Blank template for new skills
- [Discovery Patterns](references/discovery-patterns.md) — How to identify skill candidates
- [knowledge.db Schema](../../learning/db_helper.py) — Database operations
