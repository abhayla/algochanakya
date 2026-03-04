---
name: health-check
description: Proactive codebase health scan. Detects stale imports, missing tests, risky files, and known error patterns. Use manually via /health-check or auto-triggered on session start.
metadata:
  author: AlgoChanakya
  version: "2.0"
---

# Health Check Skill

Proactive codebase health scanning that identifies potential issues before they become problems.

## When to Use

- **Manually:** `/health-check` command to run full health scan
- **Auto-triggered:** On session start (if enabled in settings)
- After major refactoring or file reorganization
- Before creating a pull request
- When investigating recurring test failures

## When NOT to Use

- During active implementation (wait until changes complete)
- Not a replacement for running tests (use auto-verify or run-tests for that)

---

## 9-Step Health Scan

### 1. Stale Import Scan

**Purpose:** Detect imports of moved/deleted modules after codebase reorganization.

**Process:**
```bash
# Search for imports from old paths that may have moved
cd backend
grep -r "from app.services.kill_switch import" --include="*.py" . || echo "No stale imports found"
grep -r "from app.services.condition_engine import" --include="*.py" . || echo "No stale imports found"

# Check for common moved services
grep -r "from app.services.pnl_calculator import" --include="*.py" . || echo "OK"
grep -r "from app.services.greeks_calculator import" --include="*.py" . || echo "OK"
```

**Common Stale Patterns:**
- Services moved from `app/services/*.py` → `app/services/autopilot/*.py`
- Services moved from `app/services/*.py` → `app/services/options/*.py`
- Renamed classes/functions after refactoring

**Output:**
```
[1/9] Stale Import Scan
  ✓ No stale imports found
```

Or:

```
[1/9] Stale Import Scan
  ⚠ 2 stale imports detected:
    - backend/app/api/routes/autopilot.py:15
      from app.services.kill_switch import KillSwitch
      Should be: from app.services.autopilot.kill_switch import KillSwitch

    - backend/app/services/strategy_monitor.py:8
      from app.services.condition_engine import ConditionEngine
      Should be: from app.services.autopilot.condition_engine import ConditionEngine
```

---

### 2. Missing Test Coverage Scan

**Purpose:** Find changed files without corresponding test coverage.

**Process:**
```bash
# Get recently changed files
git diff --name-only HEAD~10..HEAD > /tmp/changed_files.txt

# Check against feature-registry.yaml test mappings
# For each changed file, verify test file exists and is recent
```

**Check Logic:**
1. Read `docs/feature-registry.yaml`
2. For each changed file, find its feature
3. Check if test file exists in `tests/e2e/specs/{feature}/`
4. Check if test file was updated recently (within 7 days of code change)

**Output:**
```
[2/9] Missing Test Coverage
  ✓ All changed files have recent test coverage
```

Or:

```
[2/9] Missing Test Coverage
  ⚠ 2 files changed without test updates:
    - frontend/src/views/StrategyBuilderView.vue (changed 3 days ago)
      Expected test: tests/e2e/specs/strategy/strategy.happy.spec.js (last updated 12 days ago)

    - backend/app/services/autopilot/adjustment_engine.py (changed 1 day ago)
      Expected test: tests/e2e/specs/autopilot/autopilot.phases123.spec.js (last updated 5 days ago)
```

---

### 3. File Risk Report

**Purpose:** Identify error-prone files from knowledge base.

**Process:**
```bash
cd .claude/learning
python -c "
from db_helper import get_connection

conn = get_connection()
cursor = conn.execute(
    'SELECT file_path, risk_score, error_count, revert_count FROM file_risk_scores WHERE risk_score > 0.5 ORDER BY risk_score DESC LIMIT 10'
)

print('[3/9] File Risk Report')
rows = cursor.fetchall()
if rows:
    print(f'  ⚠ {len(rows)} high-risk files detected:')
    for row in rows:
        print(f'    - {row[0]} (risk: {row[1]:.2f}, errors: {row[2]}, reverts: {row[3]})')
else:
    print('  ✓ No high-risk files detected')

conn.close()
"
```

**Risk Score Thresholds:**
- `0.0-0.3` - Low risk (green)
- `0.3-0.7` - Medium risk (yellow)
- `> 0.7` - High risk (red) - Extra caution needed

**Output:**
```
[3/9] File Risk Report
  ⚠ 3 high-risk files detected:
    - backend/app/services/autopilot/suggestion_engine.py (risk: 0.85, errors: 8, reverts: 2)
    - tests/e2e/specs/positions/exit.spec.js (risk: 0.72, errors: 6, reverts: 1)
    - frontend/src/stores/strategy.js (risk: 0.61, errors: 5, reverts: 1)

  Recommendation: Review these files carefully before making changes
```

---

### 4. Unresolved Error Patterns

**Purpose:** Find error patterns that have never been successfully resolved.

**Process:**
```bash
cd .claude/learning
python -c "
from db_helper import get_connection

conn = get_connection()
cursor = conn.execute(
    '''SELECT fingerprint, error_type, message_pattern, occurrence_count
       FROM error_patterns
       WHERE auto_resolved_count = 0 AND occurrence_count > 1
       ORDER BY occurrence_count DESC
       LIMIT 5'''
)

print('[4/9] Unresolved Error Patterns')
rows = cursor.fetchall()
if rows:
    print(f'  ⚠ {len(rows)} recurring unresolved errors:')
    for row in rows:
        print(f'    - {row[1]}: {row[2][:60]}...')
        print(f'      Fingerprint: {row[0]}, Seen {row[3]} times, Never resolved')
else:
    print('  ✓ No recurring unresolved errors')

conn.close()
"
```

**Output:**
```
[4/9] Unresolved Error Patterns
  ⚠ 2 recurring unresolved errors:
    - ImportError: cannot import name 'X' from 'X'
      Fingerprint: abc123def456, Seen 3 times, Never resolved

    - TestFailure: Locator 'X' not found
      Fingerprint: def456ghi789, Seen 5 times, Never resolved

  Recommendation: Investigate these patterns and create learned strategies
```

---

### 5. Strategy Effectiveness Review

**Purpose:** Identify ineffective fix strategies (low success rate).

**Process:**
```bash
cd .claude/learning
python -c "
from db_helper import get_connection

conn = get_connection()
cursor = conn.execute(
    '''SELECT name, error_type, current_score, success_count, total_attempts
       FROM fix_strategies
       WHERE total_attempts >= 3 AND current_score < 0.2
       ORDER BY current_score ASC
       LIMIT 5'''
)

print('[5/9] Strategy Effectiveness Review')
rows = cursor.fetchall()
if rows:
    print(f'  ⚠ {len(rows)} ineffective strategies (score < 0.2):')
    for row in rows:
        print(f'    - {row[0]} ({row[1]})')
        print(f'      Score: {row[2]:.2f}, Success: {row[3]}/{row[4]} attempts')
else:
    print('  ✓ No ineffective strategies detected')

conn.close()
"
```

**Output:**
```
[5/9] Strategy Effectiveness Review
  ⚠ 2 ineffective strategies (score < 0.2):
    - Fix Circular Import (ImportError)
      Score: 0.15, Success: 1/8 attempts

    - Clear Build Cache (BuildError)
      Score: 0.18, Success: 1/6 attempts

  Recommendation: Review these strategies or remove from active rotation
```

---

### 6. Synthesized Rules Check

**Purpose:** Check if new rules can be synthesized from successful patterns.

**Process:**
```bash
cd .claude/learning
python -c "
from db_helper import synthesize_rules, get_connection

# Run synthesis check
new_rules = synthesize_rules(min_confidence=0.7, min_evidence=5)

print('[6/9] Synthesized Rules Check')
if new_rules:
    print(f'  ✨ {len(new_rules)} new rules synthesized:')
    for rule in new_rules:
        print(f'    - {rule[\"rule_name\"]} ({rule[\"confidence\"]:.1%} confidence, {rule[\"evidence_count\"]} evidence)')
else:
    print('  ✓ No new rules to synthesize')

# Show total active rules
conn = get_connection()
cursor = conn.execute('SELECT COUNT(*) FROM synthesized_rules WHERE superseded_by IS NULL')
active_count = cursor.fetchone()[0]
print(f'  Total active synthesized rules: {active_count}')
conn.close()
"
```

**Output:**
```
[6/9] Synthesized Rules Check
  ✨ 2 new rules synthesized:
    - Auto: Update Stale Selector (83.3% confidence, 10 evidence)
    - Auto: Fix Missing Import (87.5% confidence, 7 evidence)
  Total active synthesized rules: 5

  Recommendation: Review new rules in test-fixer/references/common-failure-patterns.md
```

---

### 7. Git Health Check (Step 7 of 9)

**Purpose:** Check for uncommitted changes, stale branches, and large files.

**Process:**
```bash
# Check uncommitted changes
git status --porcelain > /tmp/git_status.txt

# Check for stale branches (not updated in 30 days)
git for-each-ref --sort=-committerdate refs/heads/ --format='%(refname:short) %(committerdate:relative)' | grep -E '(weeks|months) ago' || echo "No stale branches"

# Check for large files in recent commits
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {if ($3 > 1048576) print $3/1048576 " MB", $4}' | \
  sort -nr | head -5 || echo "No large files"
```

**Output:**
```
[7/9] Git Health Check
  ⚠ 3 uncommitted files:
    - backend/app/services/autopilot/suggestion_engine.py (modified)
    - frontend/src/stores/strategy.js (modified)
    - notes (modified)

  ⚠ 1 stale branch:
    - feature/old-implementation (5 weeks ago)

  ✓ No large files detected

  Recommendation: Commit changes or use git stash before continuing
```

---

### 8. data-testid Coverage Audit

**Purpose:** Detect Vue components with buttons, inputs, or selects missing `data-testid` attributes, before they become untestable in E2E.

**Process:**
```bash
node tests/e2e/scripts/audit-testids.js --fail-below=70
```

**Output:**
```
[8/9] data-testid Coverage Audit
  Overall: 64% coverage (threshold: 70%) — ⚠ BELOW THRESHOLD

  🔴 HIGH (61 files) — buttons/inputs/selects missing data-testid:
    - frontend/src/views/PositionsView.vue [35%] — 16 missing
    - frontend/src/components/autopilot/adjustments/ShiftLegModal.vue [0%] — 15 missing
    - frontend/src/views/StrategyBuilderView.vue [64%] — 12 missing

  🟡 MEDIUM (2 files) — clickable divs missing data-testid

  ✅ 26 files fully covered

  Recommendation: Add data-testid to HIGH priority files first (buttons/inputs/selects)
```

---

### 9. Documentation Validation Audit

**Purpose:** Detect documentation drift, stale cross-references, and inconsistencies between docs and code.

**Process:**

**9a. Broker comparison-matrix.md vs actual adapters:**
```bash
# Check that comparison-matrix.md section 11 lists all adapters that actually exist
ls backend/app/services/brokers/market_data/*_adapter.py backend/app/services/brokers/order/*_adapter.py 2>/dev/null | \
  sed 's/.*\///' | sed 's/_adapter.py//' | sort > /tmp/actual_adapters.txt

grep -oP '(?<=\| )\w+(?= +\| (Complete|Planned|In Progress))' .claude/skills/broker-shared/comparison-matrix.md | \
  tr '[:upper:]' '[:lower:]' | sort > /tmp/documented_adapters.txt

diff /tmp/actual_adapters.txt /tmp/documented_adapters.txt || echo "⚠ Adapter mismatch detected"
```

**9b. Broker expert skill freshness:**
```bash
# Check last_verified dates in broker expert skills (warn if > 30 days old)
for skill in angelone-expert zerodha-expert upstox-expert dhan-expert fyers-expert paytm-expert; do
  date=$(grep -oP 'last_verified:\s*"\K[^"]+' .claude/skills/$skill/SKILL.md 2>/dev/null)
  if [ -n "$date" ]; then
    days_old=$(( ($(date +%s) - $(date -d "$date" +%s)) / 86400 ))
    [ $days_old -gt 30 ] && echo "⚠ $skill last verified $days_old days ago"
  fi
done
```

**9c. Feature registry file existence:**
```bash
# Verify files listed in feature-registry.yaml actually exist
python -c "
import yaml
with open('docs/feature-registry.yaml') as f:
    registry = yaml.safe_load(f)
missing = []
for feature, data in registry.get('features', {}).items():
    for f in data.get('backend_files', []) + data.get('frontend_files', []):
        import os
        if not os.path.exists(f):
            missing.append(f'{feature}: {f}')
if missing:
    print(f'⚠ {len(missing)} registered files missing:')
    for m in missing[:10]:
        print(f'  - {m}')
else:
    print('✓ All registered files exist')
"
```

**9d. CLAUDE.md drift detection:**
```bash
# Check if CLAUDE.md has high churn (3+ changes in last 5 commits)
claude_changes=$(git log --oneline -5 --diff-filter=M -- CLAUDE.md | wc -l)
if [ "$claude_changes" -ge 3 ]; then
  echo "⚠ CLAUDE.md modified in $claude_changes of last 5 commits (high churn)"
  echo "  Consider stabilizing or splitting into sub-docs"
else
  echo "✓ CLAUDE.md churn is normal ($claude_changes changes in last 5 commits)"
fi
```

**9e. Rate limit consistency:**
```bash
# Cross-check rate limits in comparison-matrix vs broker expert skills
for skill in angelone-expert zerodha-expert upstox-expert dhan-expert fyers-expert paytm-expert; do
  skill_limit=$(grep -oP 'Rate Limit.*?(\d+)' .claude/skills/$skill/SKILL.md 2>/dev/null | head -1)
  matrix_limit=$(grep -A1 "$(echo $skill | sed 's/-expert//')" .claude/skills/broker-shared/comparison-matrix.md 2>/dev/null | grep -oP '\d+ req' | head -1)
  if [ -n "$skill_limit" ] && [ -n "$matrix_limit" ]; then
    [ "$skill_limit" != "$matrix_limit" ] && echo "⚠ Rate limit mismatch for $skill"
  fi
done
```

**Output:**
```
[9/9] Documentation Validation Audit
  9a. Broker adapters vs docs        ✓ All 6 brokers documented
  9b. Expert skill freshness         ⚠ 2 skills stale (> 30 days)
  9c. Feature registry files         ✓ All files exist
  9d. CLAUDE.md churn                ✓ Normal (1 change in 5 commits)
  9e. Rate limit consistency         ✓ All consistent

  Summary: 1 warning (broker expert freshness)
```

---

## Complete Health Report Format

```
==============================================
       AlgoChanakya Health Check Report
==============================================
Date: 2026-02-13 14:23:45
Scan Duration: 3.2 seconds

[1/9] Stale Import Scan               ✓ Clean
[2/9] Missing Test Coverage            ⚠ 2 issues
[3/9] File Risk Report                 ⚠ 3 high-risk files
[4/9] Unresolved Error Patterns        ⚠ 2 patterns
[5/9] Strategy Effectiveness           ⚠ 2 ineffective
[6/9] Synthesized Rules Check          ✨ 2 new rules
[7/9] Git Health                       ⚠ 3 uncommitted files
[8/9] data-testid Coverage             ⚠ 64% (below 70% threshold)
[9/9] Documentation Validation         ⚠ 2 sub-checks warned

==============================================
Summary: 6 warnings, 2 clean, 2 new rules
==============================================

Details:

⚠ Missing Test Coverage (2 files)
  - frontend/src/views/StrategyBuilderView.vue
    Expected: tests/e2e/specs/strategy/strategy.happy.spec.js
    Last test update: 12 days ago, code changed: 3 days ago

  - backend/app/services/autopilot/adjustment_engine.py
    Expected: tests/e2e/specs/autopilot/autopilot.phases123.spec.js
    Last test update: 5 days ago, code changed: 1 day ago

⚠ File Risk Report (3 high-risk files)
  - backend/app/services/autopilot/suggestion_engine.py (risk: 0.85)
    8 errors, 2 reverts - Extra caution needed

  - tests/e2e/specs/positions/exit.spec.js (risk: 0.72)
    6 errors, 1 revert - Review before changes

  - frontend/src/stores/strategy.js (risk: 0.61)
    5 errors, 1 revert - Monitor closely

⚠ Unresolved Error Patterns (2 patterns)
  1. ImportError: cannot import name 'X' from 'X'
     Fingerprint: abc123def456, Seen 3 times
     Recommendation: Create learned strategy

  2. TestFailure: Locator 'X' not found
     Fingerprint: def456ghi789, Seen 5 times
     Recommendation: Investigate selector patterns

⚠ Strategy Effectiveness (2 ineffective)
  1. Fix Circular Import (ImportError) - Score: 0.15
     Success: 1/8 attempts
     Recommendation: Review or deprecate strategy

  2. Clear Build Cache (BuildError) - Score: 0.18
     Success: 1/6 attempts
     Recommendation: Review or deprecate strategy

✨ Synthesized Rules (2 new)
  1. Auto: Update Stale Selector (83.3% confidence, 10 evidence)
  2. Auto: Fix Missing Import (87.5% confidence, 7 evidence)

  Injected into: test-fixer/references/common-failure-patterns.md

⚠ Git Health (3 uncommitted files)
  - backend/app/services/autopilot/suggestion_engine.py
  - frontend/src/stores/strategy.js
  - notes

  Recommendation: Commit or stash before continuing

==============================================
Next Actions:
1. Update tests for StrategyBuilderView.vue and adjustment_engine.py
2. Review high-risk files before making changes
3. Investigate 2 recurring unresolved error patterns
4. Deprecate 2 ineffective fix strategies
5. Review 2 newly synthesized rules
6. Commit or stash uncommitted changes
==============================================
```

---

## Auto-Trigger on Session Start

To enable automatic health check on session start, add to your session startup workflow:

```bash
# In start-session integration
/health-check --quick  # Quick scan (steps 3, 4, 6, 9 only)
/health-check          # Full scan (all 9 steps)
```

**Quick Scan** (30 seconds):
- File Risk Report
- Unresolved Error Patterns
- Synthesized Rules Check
- Documentation Validation Audit

**Full Scan** (2-3 minutes):
- All 9 steps

---

## Manual Commands

```bash
/health-check              # Run full health scan (all 9 steps)
/health-check --quick      # Quick scan (3 critical checks)
/health-check --step=3     # Run specific step only
/health-check --fix        # Auto-fix issues where possible
```

---

## Integration with Learning Engine

Health check uses knowledge.db to provide insights:
- **File Risk Scores** - From `file_risk_scores` table
- **Unresolved Patterns** - From `error_patterns` table
- **Strategy Effectiveness** - From `fix_strategies` table
- **Synthesis Opportunities** - Runs `synthesize_rules()` check

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `knowledge.db not found` | Learning engine never initialized | Run `/reflect` once to create the database |
| Steps return empty results | Database tables have no data yet | Expected on fresh installs; run tests to populate |
| `feature-registry.yaml` not found | File deleted or moved | Restore: `git checkout docs/feature-registry.yaml` |

---

## References

- `references/scan-patterns.md` - Detailed scan patterns and Grep commands
- `.claude/learning/db_helper.py` - Database query functions
- `docs/feature-registry.yaml` - File-to-test mappings
