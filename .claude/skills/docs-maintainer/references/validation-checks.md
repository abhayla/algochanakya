# Documentation Validation Checks — Implementation Details

Detailed grep commands and validation logic for each check in the docs-maintainer skill. This file keeps the main SKILL.md readable by offloading implementation details here.

## Pre-Commit Validation

### Stale Timestamp Detection
```bash
# Find all REQUIREMENTS.md with dates
find docs/features -name "REQUIREMENTS.md" -exec grep -l "Last updated" {} \; | while read f; do
  date_str=$(grep -oP 'Last updated:\s*\K[\d-]+' "$f")
  if [ -n "$date_str" ]; then
    days_old=$(( ($(date +%s) - $(date -d "$date_str" +%s 2>/dev/null || echo 0)) / 86400 ))
    [ $days_old -gt 30 ] && echo "STALE: $f (${days_old} days old)"
  fi
done
```

### CHANGELOG Gap Detection
```bash
# For staged code files, check if feature CHANGELOG was also staged
git diff --cached --name-only | grep -E '\.(py|vue|js|ts)$' | while read code_file; do
  # Map to feature via registry
  feature=$(python3 -c "
import yaml
with open('docs/feature-registry.yaml') as f:
    reg = yaml.safe_load(f)
for name, data in reg.get('features', {}).items():
    all_files = data.get('backend_files', []) + data.get('frontend_files', [])
    if '$code_file' in all_files:
        print(name); break
" 2>/dev/null)

  if [ -n "$feature" ] && [ "$feature" != "None" ]; then
    cl="docs/features/$feature/CHANGELOG.md"
    if ! git diff --cached --name-only | grep -qF "$cl"; then
      echo "GAP: $code_file → $cl not staged"
    fi
  fi
done
```

### Broken Link Scanner
```bash
# Check relative links in modified markdown files
git diff --cached --name-only -- '*.md' | while read md_file; do
  dir=$(dirname "$md_file")
  grep -noP '\[.*?\]\(\K[^)]+' "$md_file" | while IFS=: read line link; do
    # Skip URLs, anchors, and mailto
    echo "$link" | grep -qE '^(https?://|#|mailto:)' && continue
    # Strip anchor from path
    path=$(echo "$link" | sed 's/#.*//')
    [ -z "$path" ] && continue
    resolved="$dir/$path"
    [ ! -e "$resolved" ] && echo "BROKEN: $md_file:$line → $link"
  done
done
```

## Continuous Monitoring

### CLAUDE.md Churn Analysis
```bash
# Detailed churn breakdown
echo "=== CLAUDE.md Churn Report ==="
git log --oneline -20 --diff-filter=M -- CLAUDE.md | while read hash msg; do
  lines_changed=$(git show --stat "$hash" -- CLAUDE.md | tail -1 | grep -oP '\d+ insertion|\d+ deletion' | tr '\n' ', ')
  echo "  $hash $msg ($lines_changed)"
done

total=$(git log --oneline -20 --diff-filter=M -- CLAUDE.md | wc -l)
echo ""
echo "Total: $total/20 commits modified CLAUDE.md"
[ $total -ge 5 ] && echo "⚠ HIGH CHURN: Consider splitting volatile sections into sub-docs"
```

### Feature Coverage Matrix
```bash
python3 -c "
import yaml, os, json

with open('docs/feature-registry.yaml') as f:
    reg = yaml.safe_load(f)

results = {'complete': [], 'partial': [], 'missing': []}
required_docs = ['README.md', 'REQUIREMENTS.md', 'CHANGELOG.md']

for name, data in reg.get('features', {}).items():
    folder = data.get('docs_folder', f'docs/features/{name}/')
    existing = [d for d in required_docs if os.path.exists(os.path.join(folder, d))]

    if len(existing) == 3:
        results['complete'].append(name)
    elif len(existing) > 0:
        results['partial'].append((name, existing))
    else:
        results['missing'].append(name)

print(f'Complete: {len(results[\"complete\"])}/{len(results[\"complete\"])+len(results[\"partial\"])+len(results[\"missing\"])} features')
for name in results['missing']:
    print(f'  ❌ {name}: no docs folder')
for name, docs in results['partial']:
    print(f'  ⚠ {name}: has {len(docs)}/3 docs')
"
```

## Cross-Reference Audit

### Port Consistency Check
```bash
# Extract ports from all config sources
backend_port=$(grep -oP 'PORT=\K\d+' backend/.env 2>/dev/null || echo "NOT_SET")
frontend_url=$(grep -oP 'VITE_API_BASE_URL=\Khttp://[^\s]+' frontend/.env.local 2>/dev/null || echo "NOT_SET")
claude_port=$(grep -oP 'Dev Backend.*?\|\s*\K\d+' CLAUDE.md 2>/dev/null | head -1 || echo "NOT_SET")

echo "Backend .env PORT:        $backend_port"
echo "Frontend .env.local URL:  $frontend_url"
echo "CLAUDE.md documented:     $claude_port"

# Check consistency
[ "$backend_port" = "8001" ] || echo "⚠ Backend port should be 8001, got $backend_port"
echo "$frontend_url" | grep -q ":8001" || echo "⚠ Frontend URL should point to :8001"
[ "$claude_port" = "8001" ] || echo "⚠ CLAUDE.md port should be 8001"
```

### Adapter vs Documentation Sync
```bash
# List actual adapter directories
actual=$(ls -d backend/app/services/brokers/market_data/*_adapter.py backend/app/services/brokers/order/*_adapter.py 2>/dev/null | \
  sed 's/.*\///' | sed 's/_adapter.py//' | sort -u)

# List documented brokers in comparison-matrix
documented=$(grep -oP '^\| \*\*\K\w+(?=\*\*)' .claude/skills/broker-shared/comparison-matrix.md 2>/dev/null | \
  tr '[:upper:]' '[:lower:]' | sort -u)

echo "Actual adapters: $(echo $actual | tr '\n' ' ')"
echo "Documented:      $(echo $documented | tr '\n' ' ')"

# Diff
diff <(echo "$actual") <(echo "$documented") && echo "✓ Consistent" || echo "⚠ Mismatch detected"
```
