# Mode: Meta (Convergence Analysis)

**Purpose:** High-level analysis of modification patterns and convergence.

**Read-only:** No file modifications, only analysis.

## Algorithm

**1. Load modification history:**
```python
modifications_file = Path(".claude/logs/learning/modifications.json")  # [PLANNED - created at runtime by reflect deep mode]

with open(modifications_file) as f:
    history = json.load(f)

# Group by file
by_file = defaultdict(list)
for mod in history:
    by_file[mod['file']].append(mod)
```

**2. Detect patterns:**
```python
patterns = []

# Pattern 1: Same file modified repeatedly
for file, mods in by_file.items():
    if len(mods) >= 3:
        patterns.append({
            'type': 'repeated_modification',
            'file': file,
            'count': len(mods),
            'actions': [m['action'] for m in mods]
        })

# Pattern 2: Same action across multiple files
by_action = defaultdict(list)
for mod in history:
    by_action[mod['action']].append(mod['file'])

for action, files in by_action.items():
    if len(files) >= 3:
        patterns.append({
            'type': 'repeated_action',
            'action': action,
            'files': files
        })

# Pattern 3: Revert pattern (modification → revert → remodification)
for file, mods in by_file.items():
    reverted_count = sum(1 for m in mods if m.get('reverted', False))
    if reverted_count > 0:
        patterns.append({
            'type': 'revert_pattern',
            'file': file,
            'revert_count': reverted_count,
            'total_mods': len(mods)
        })
```

**3. Assess convergence:**
```python
# Convergence metric: fewer modifications over time
recent_mods = [m for m in history if is_recent(m['timestamp'], days=7)]
older_mods = [m for m in history if is_recent(m['timestamp'], days=30) and not is_recent(m['timestamp'], days=7)]

if len(recent_mods) < len(older_mods) / 3:
    convergence = "CONVERGING"
elif len(recent_mods) > len(older_mods) * 2:
    convergence = "DIVERGING"
else:
    convergence = "STABLE"

print(f"\n📊 Convergence assessment: {convergence}")
print(f"  Recent modifications (7d): {len(recent_mods)}")
print(f"  Older modifications (8-30d): {len(older_mods)}")
```

**4. Generate meta-report:**
```markdown
# Meta-Analysis Report

**Convergence:** {convergence}
**Total modifications:** {len(history)}
**Files modified:** {len(by_file)}

## Patterns Detected

{patterns}

## Recommendations

- If DIVERGING: Reduce modification frequency, focus on stability
- If STABLE: Continue current approach, monitor for new gaps
- If CONVERGING: Workflow maturing, consider finalizing rules

## High-Churn Files

{files with most modifications}

These files may indicate:
1. Complex requirements that change frequently
2. Initial design needing refinement
3. External factors (broker API changes, etc.)
```

---

# Mode: Test-Run (Dry-Run)

**Purpose:** Preview deep mode modifications without applying.

**Same as deep mode but:**
- No `git stash` backup
- No `Edit` tool usage
- Only show proposed modifications
- No validation

```python
# Run deep mode analysis
gaps = analyze_workflow_gaps()  # [PLANNED - pseudocode]
modifications = propose_modifications(gaps)  # [PLANNED - pseudocode]

# Show modifications
for mod in modifications:
    print(f"\n{'='*60}")
    print(f"File: {mod['file']}")
    print(f"Action: {mod['action']}")
    print(f"{'='*60}")
    print("BEFORE:")
    print(mod['old_code'])
    print("\nAFTER:")
    print(mod['new_code'])

print(f"\n{len(modifications)} modifications proposed.")
print("Run `Skill('reflect', args='deep')` to apply.")
```
