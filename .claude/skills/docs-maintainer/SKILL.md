---
name: docs-maintainer
description: Automatically maintain project documentation after code changes. Use proactively after any code modification to keep docs in sync.
metadata:
  author: AlgoChanakya
  version: "2.0"
---

# Documentation Maintainer

Automatically maintain all project documentation (feature docs, CHANGELOG, REQUIREMENTS, API docs, CLAUDE.md) after any code change. This skill activates proactively to keep documentation synchronized with the codebase.

## When to Use

**PROACTIVE TRIGGERS** - Activate this skill automatically after Claude completes ANY of these actions:

- Creates a new file
- Edits an existing file (backend or frontend)
- Deletes a file
- Adds or modifies API endpoints
- Changes database models
- Modifies Vue components
- Updates services or utilities
- Adds/modifies tests

**IMPORTANT:** This skill should run **AFTER** code changes are complete, not before. Think of it as a post-commit hook for documentation.

## When NOT to Use

- Before code changes are complete (wait until implementation done)
- For non-code changes (documentation edits, comments, README updates)
- When modifying .claude internal files only (skills, commands, agents, hooks)

## Feature Registry

The skill uses `docs/feature-registry.yaml` to map code files to features. This registry contains:

1. **Auto-detection patterns** - Glob patterns that automatically assign new files to features
2. **Explicit feature mappings** - Complete lists of files belonging to each feature
3. **Shared files** - Infrastructure files used across features

### How Feature Detection Works

```
1. Check if modified file exists in registry's explicit mappings
   → If found, use those feature(s)

2. If not in explicit mappings, try auto-detect patterns:
   → Match file path against patterns in auto_detect_patterns
   → A file can match multiple patterns (belongs to multiple features)

3. If no pattern match, infer from:
   → Parent folder name (e.g., */watchlist/* → watchlist)
   → File name keywords (e.g., *autopilot* → autopilot)
   → Import analysis (what modules does it import from?)

4. If still unknown:
   → Add to "unassigned" section in registry
   → Log for manual review
   → Skip doc updates for this file
```

## Documentation Update Rules

| Changed File Type | Docs to Update | What to Add |
|-------------------|----------------|-------------|
| **API route** | Feature CHANGELOG, Feature REQUIREMENTS (API section), docs/api/README.md | New endpoint signature, brief description |
| **Database model** | Feature CHANGELOG, Feature REQUIREMENTS (Data section), docs/architecture/database.md | New table/field, migration note |
| **Vue component** | Feature CHANGELOG, Feature REQUIREMENTS (UI section) | Component description, props, events |
| **Service/util** | Feature CHANGELOG | Service function added/modified |
| **Test file** | docs/testing/coverage-matrix.md | Test count update |
| **Any major change** | Root CHANGELOG.md (under [Unreleased]) | High-level summary |
| **Architecture change** | CLAUDE.md, docs/architecture/*.md | Pattern update, new service docs |

## Broker-Specific Documentation Rules

When broker adapter code changes, additional documentation must be updated beyond the standard rules above.

### Trigger → Action Matrix

| Trigger (Code Change) | Documentation Actions |
|----------------------|----------------------|
| **New broker adapter created** | Update [comparison-matrix.md](../.claude/skills/broker-shared/comparison-matrix.md) Implementation Status table, [feature-registry.yaml](../../docs/feature-registry.yaml) broker-abstraction patterns, [CLAUDE.md](../../CLAUDE.md) Supported Brokers table |
| **Adapter status change** (planned→complete) | Update comparison-matrix.md section 11, CLAUDE.md Implementation Status, [IMPLEMENTATION-CHECKLIST.md](../../docs/IMPLEMENTATION-CHECKLIST.md) Progress Tracking table |
| **Ticker/WebSocket change** | Update [ADR-003](../../docs/decisions/003-multi-broker-ticker-architecture.md) status if applicable, IMPLEMENTATION-CHECKLIST.md Phase 4 tasks |
| **Symbol converter change** | Verify the relevant broker expert skill's Symbol Format section matches (e.g., `/angelone-expert`, `/zerodha-expert`) |
| **Rate limiter change** | Update comparison-matrix.md section 3 (Rate Limits) + relevant broker expert skill's Rate Limits section |
| **New broker expert skill created** | Update comparison-matrix.md skill callout, CLAUDE.md skills table, [DEVELOPER-QUICK-REFERENCE.md](../../docs/DEVELOPER-QUICK-REFERENCE.md) broker skills references |

### Cross-Reference Consistency Checklist

On ANY broker adapter change, verify these 5 docs are consistent:

- [ ] `CLAUDE.md` — Implementation Status, Supported Brokers table
- [ ] `docs/IMPLEMENTATION-CHECKLIST.md` — Progress Tracking table
- [ ] `.claude/skills/broker-shared/comparison-matrix.md` — Section 11 (Implementation Status)
- [ ] `docs/feature-registry.yaml` — broker-abstraction shared_files
- [ ] `docs/DEVELOPER-QUICK-REFERENCE.md` — Multi-Broker System section

### Broker Adapter Auto-Detection Example

When a new file like `backend/app/services/brokers/market_data/upstox_adapter.py` is created:

```
1. auto_detect_patterns matches: "backend/app/services/brokers/**_adapter.py" → broker-abstraction
2. Also matches: "backend/app/services/brokers/market_data/*.py" → broker-abstraction
3. Actions triggered:
   → Update feature-registry.yaml (add to broker-abstraction files)
   → Update comparison-matrix.md section 11 (Upstox: Planned → Complete)
   → Update CLAUDE.md Supported Brokers table
   → Update IMPLEMENTATION-CHECKLIST.md Phase 5 tasks
   → Alert: "New broker adapter detected. Run cross-reference checklist."
```

## CHANGELOG Entry Format

Use the Keep a Changelog format:

```markdown
### Added
- Brief description of what was added (file: relative/path/to/file.ext)

### Changed
- Brief description of what changed (file: relative/path/to/file.ext)

### Fixed
- Brief description of bug fix (file: relative/path/to/file.ext)

### Removed
- Brief description of what was removed (file: relative/path/to/file.ext)
```

**Rules:**
- Always include the file path in parentheses
- Use present tense ("Add feature" not "Added feature")
- Be concise (1 line per change)
- Group related changes under same section

## REQUIREMENTS.md Update Rules

When updating REQUIREMENTS.md:

1. **New Feature Added:** Add new checkbox items under appropriate section
2. **Feature Modified:** Leave checkbox checked (don't uncheck)
3. **Feature Removed:** Remove checkbox item entirely
4. **Update timestamp:** Change "Last updated" date at bottom

**Example:**
```markdown
## API Requirements
- [x] GET /api/watchlists - Get all watchlists
- [x] POST /api/watchlists - Create new watchlist  # Already implemented
- [x] DELETE /api/watchlists/{id}/instruments/{token} - Remove instrument  # NEW - just added

---
Last updated: 2025-12-22
```

## Registry Auto-Update Logic

When a NEW file is created that doesn't exist in the registry:

```
1. Try to match against auto_detect_patterns:
   pattern: "backend/app/api/routes/watchlist*.py"
   feature: watchlist

   If new file is: backend/app/api/routes/watchlist_bulk.py
   → Matches pattern → Assign to watchlist feature

2. If no pattern match, analyze:
   - Folder: backend/app/api/routes/autopilot/
   → Contains "autopilot" → Assign to autopilot

   - Imports: from app.services.kite_ticker import...
   → Uses kite_ticker → Might be watchlist/positions/optionchain

3. Add to registry:
   features:
     watchlist:
       backend_files:
         - backend/app/api/routes/watchlist_bulk.py  # AUTO-ADDED

4. Update registry version and last_updated timestamp
```

## Cross-Feature Files

Some files (like `kite_ticker.py`) are used by multiple features:

```yaml
features:
  watchlist:
    backend_files:
      - backend/app/services/kite_ticker.py

  positions:
    backend_files:
      - backend/app/services/kite_ticker.py

  option-chain:
    backend_files:
      - backend/app/services/kite_ticker.py
```

**Action:** Update CHANGELOG.md for ALL related features when this file changes.

## Step-by-Step Workflow

### After Code Change

1. **Identify Changed Files:**
   ```
   - backend/app/api/routes/watchlist.py (modified)
   - frontend/src/views/WatchlistView.vue (modified)
   ```

2. **Map Files to Features:**
   ```
   → Check feature-registry.yaml
   → Both files belong to: watchlist
   ```

3. **Determine Doc Updates Needed:**
   ```
   API route changed:
   - Update docs/features/watchlist/CHANGELOG.md
   - Update docs/features/watchlist/REQUIREMENTS.md (if new endpoint)
   - Update docs/api/README.md

   Vue component changed:
   - Update docs/features/watchlist/CHANGELOG.md
   ```

4. **Update Feature CHANGELOG.md:**
   ```markdown
   ## [Unreleased]

   ### Changed
   - Added bulk delete endpoint for watchlist instruments (file: backend/app/api/routes/watchlist.py)
   - Updated watchlist view with bulk actions UI (file: frontend/src/views/WatchlistView.vue)
   ```

5. **Update Feature REQUIREMENTS.md (if applicable):**
   ```markdown
   ## API Requirements
   - [x] DELETE /api/watchlists/{id}/instruments/bulk - Bulk remove instruments

   ---
   Last updated: 2025-12-22
   ```

6. **Update Root CHANGELOG.md (for major changes):**
   ```markdown
   ## [Unreleased]

   ### Changed
   - Watchlist bulk delete functionality
   ```

7. **Update CLAUDE.md (for architecture changes):**
   Only if the change affects patterns or important architecture.

8. **Check for Orphaned Files (Proactive Detection):**
   After completing documentation updates, scan for misplaced files and suggest cleanup:

   ```
   Quick scan for orphaned files:
   - Root *.md files (except allowed list)
   - Root test_*.py or test-*.js
   - docs/features/*.md (not in subfolders)

   If orphans found:
   → Alert user: "Found X orphaned files that should be reorganized"
   → Suggest: "Run /docs-maintainer cleanup to organize them"
   → DO NOT move files automatically
   ```

## Examples

### Example 1: Adding New API Endpoint

**Code Change:**
```python
# backend/app/api/routes/positions.py
@router.get("/grouped")
async def get_grouped_positions(...):
    # New endpoint
```

**Doc Updates:**

1. Feature CHANGELOG (`docs/features/positions/CHANGELOG.md`):
```markdown
## [Unreleased]

### Added
- Grouped positions endpoint (file: backend/app/api/routes/positions.py)
```

2. Feature REQUIREMENTS (`docs/features/positions/REQUIREMENTS.md`):
```markdown
## API Requirements
- [x] GET /api/positions/grouped - Grouped positions

---
Last updated: 2025-12-22
```

3. API Docs (`docs/api/README.md`):
```markdown
### Positions
- GET /api/positions/grouped - Get positions grouped by underlying
```

### Example 2: New Vue Component

**Code Change:**
```
Created: frontend/src/components/watchlist/BulkActionsBar.vue
```

**Doc Updates:**

1. Feature CHANGELOG:
```markdown
## [Unreleased]

### Added
- Bulk actions bar component for watchlist (file: frontend/src/components/watchlist/BulkActionsBar.vue)
```

2. Feature README (optional, if significant):
Mention in component list.

3. Feature REQUIREMENTS:
```markdown
## UI Requirements
- [x] Bulk actions bar with select all/delete selected

---
Last updated: 2025-12-22
```

### Example 3: Database Model Change

**Code Change:**
```python
# backend/app/models/watchlists.py
# Added new column: is_default
```

**Doc Updates:**

1. Feature CHANGELOG:
```markdown
## [Unreleased]

### Changed
- Added is_default column to watchlists table (file: backend/app/models/watchlists.py)
```

2. Feature REQUIREMENTS:
```markdown
## Data Requirements
- [x] `is_default` column for default watchlist marking

---
Last updated: 2025-12-22
```

3. Architecture Docs (`docs/architecture/database.md`):
Update schema documentation.

## Anti-Patterns (What NOT to Do)

### ❌ NEVER update docs without understanding the code change
```
# WRONG
### Changed
- Updated some stuff (file: backend/app/api/routes/watchlist.py)

# RIGHT
### Changed
- Added pagination support to watchlist API (file: backend/app/api/routes/watchlist.py)
```

### ❌ NEVER uncheck completed requirements
```
# WRONG
## API Requirements
- [ ] GET /api/watchlists - Get all watchlists  # Don't uncheck!

# RIGHT
## API Requirements
- [x] GET /api/watchlists - Get all watchlists  # Keep checked
- [x] GET /api/watchlists?page=1 - Paginated watchlists  # Add new
```

### ❌ NEVER skip the file path in CHANGELOG
```
# WRONG
### Added
- Bulk delete feature

# RIGHT
### Added
- Bulk delete feature (file: backend/app/api/routes/watchlist.py)
```

### ❌ NEVER create duplicate entries in CHANGELOG
```
# WRONG
### Added
- Feature X (file: a.py)
- Feature X (file: a.py)  # Duplicate!

# RIGHT
### Added
- Feature X with implementation in multiple files (files: a.py, b.vue)
```

---

## Cleanup Workflow

**Trigger:** When user explicitly requests "clean up docs", "organize files", or "/docs-maintainer cleanup"

This workflow handles file reorganization and detection of misplaced documentation/script files that should be moved to their proper locations.

### 0. Run Automated Cleanup (Pre-Step)

Before any manual file reorganization, run the cleanup script to bulk-delete gitignored artifacts:

```bash
bash scripts/cleanup.sh --dry-run   # Preview what will be deleted
bash scripts/cleanup.sh             # Execute cleanup
```

This handles: tmpclaude dirs, debug scripts, test artifact dirs (allure-results/, playwright-report/), corrupted filenames, root-level screenshots, and stale backend files.

See `references/cleanup-rules.md` § "Automated Cleanup via Script" for full details on the 10 categories and what is intentionally NOT touched.

Skip this step only when the user explicitly requests docs reorganization without filesystem cleanup.

### 1. Scan for Orphaned Files

Check for files that don't belong in their current location:

```bash
# Documentation files in root (except allowed files)
Allowed in root: README.md, CLAUDE.md, CHANGELOG.md, package.json, playwright.config.js, .gitignore

# Check for orphaned docs
Root directory:
- *.md files (except allowed) → Should be in docs/
- test_*.py → Should be in scripts/debug/ or backend/tests/
- test-*.js → Should be in scripts/testing/ or tests/e2e/
- *.log, *.txt (logs) → Should be in .gitignore or deleted
- *.png, *.jpg (screenshots) → Should be in docs/assets/screenshots/

docs/features/ directory:
- *.md files NOT in subfolders → Should be in docs/features/{feature}/README.md
```

### 2. Match Orphaned Files to Features

Use feature-registry.yaml to determine proper location:

```
Example orphan: watchlist.md in docs/features/

1. Check registry for "watchlist" feature:
   features:
     watchlist:
       docs_folder: docs/features/watchlist/

2. Target file: docs/features/watchlist/README.md

3. Action: Merge content or rename to .bak
```

### 3. Reorganize Files

**For root-level orphaned files:**
```
1. Create target directory if missing
2. Move file to proper location
3. Update any references in codebase (imports, documentation links)
4. Update .gitignore patterns if needed
```

**For docs/features/ orphaned standalone files:**
```
1. Check if folder-based docs exist (e.g., docs/features/watchlist/README.md)
2. If exists: Rename orphan to .bak (keep as backup)
3. If missing: Create folder structure and move/rename file
4. Update cross-references in other docs
```

### 4. Update References

After moving files, search for and update references:

```bash
# Search for hardcoded paths
grep -r "path/to/old/location" .

# Common patterns to check:
- Import statements (Python)
- Image src paths (Vue/React)
- Documentation links (Markdown)
- Script references in package.json
- Path references in README files
```

### 5. Verification

**Build check:**
```bash
# Frontend build
cd frontend && npm run build

# Backend syntax
cd backend && python -m py_compile run.py

# Test suite (if applicable)
npm test
```

### Cleanup Triggers

In addition to after-code-change triggers, also run when:
- User explicitly requests "clean up docs" or "organize files"
- User runs "/docs-maintainer cleanup" command
- A new feature folder is created (check for orphaned docs)
- Pull request is being prepared (suggest cleanup if orphans detected)

---

## Proactive Orphan Detection

**Purpose:** Alert users about misplaced files without disrupting their workflow.

**When:** Run automatically AFTER completing normal documentation updates (Step 8 in workflow).

### Detection Logic

```python
def detect_orphans():
    orphans = []

    # 1. Check root directory for non-allowed .md files
    allowed_root_files = [
        'README.md', 'CLAUDE.md', 'CHANGELOG.md',
        'package.json', 'package-lock.json', 'playwright.config.js',
        '.gitignore', '.eslintrc*', '.prettierrc*',
        'tsconfig.json', 'jsconfig.json', 'vite.config.js'
    ]

    root_md_files = glob('*.md')
    for file in root_md_files:
        if file not in allowed_root_files:
            orphans.append(('root_doc', file, 'docs/'))

    # 2. Check root for test/debug scripts
    root_test_py = glob('test_*.py')
    root_test_js = glob('test-*.js') + glob('test*.js')

    orphans.extend([('script', f, 'scripts/debug/') for f in root_test_py])
    orphans.extend([('script', f, 'scripts/testing/') for f in root_test_js])

    # 3. Check docs/features/ for standalone .md files
    features_orphans = glob('docs/features/*.md')
    for file in features_orphans:
        # Extract feature name from filename (e.g., watchlist.md -> watchlist)
        feature_name = file.stem
        expected_location = f'docs/features/{feature_name}/README.md'
        orphans.append(('feature_doc', file, expected_location))

    # 4. Check for temp/log files
    temp_files = glob('*.log') + glob('*-output.txt') + glob('*.pid')
    orphans.extend([('temp', f, '.gitignore') for f in temp_files])

    # 5. Check for corrupted filenames (Windows shell expansion artifacts)
    corrupted_patterns = ['{,', '80%', 'nul', 'NUL']
    for name in corrupted_patterns:
        if os.path.exists(name):
            orphans.append(('corrupted', name, 'run: bash scripts/cleanup.sh'))
    mangled = glob('D?AbhayVibeCoding*') + glob('C?AbhayVideCoding*')
    orphans.extend([('corrupted', f, 'run: bash scripts/cleanup.sh') for f in mangled])

    # 6. Check for tmpclaude working directories (Claude Code artifacts)
    tmpclaude_dirs = glob('tmpclaude-*')
    if tmpclaude_dirs:
        orphans.append(('artifact', f'{len(tmpclaude_dirs)} tmpclaude-* dirs', 'run: bash scripts/cleanup.sh'))

    # 7. Check for test artifact accumulation (trigger cleanup if large)
    large_artifact_dirs = ['allure-results', 'test-results', 'playwright-report']
    for d in large_artifact_dirs:
        if os.path.isdir(d):
            count = sum(1 for _ in os.scandir(d))
            if count > 100:
                orphans.append(('artifact', f'{d}/ ({count} entries)', 'run: bash scripts/cleanup.sh'))

    return orphans
```

### Alert Format

**If orphans found:**
```
⚠️  Orphan Files Detected

Found 8 files that should be reorganized:

Root Documentation (3):
  • AUTOPILOT_PHASE_3.md → docs/autopilot/
  • DATABASE_SETUP.md → docs/guides/
  • TEST_SUMMARY.md → docs/testing/

Root Scripts (2):
  • test_connections.py → scripts/debug/
  • test-strike.js → scripts/testing/

Legacy Feature Docs (2):
  • docs/features/watchlist.md → docs/features/watchlist/README.md
  • docs/features/positions.md → docs/features/positions/README.md

Temporary Files (1):
  • test-output.log → Add to .gitignore

💡 Run `/docs-maintainer cleanup` to organize these files automatically.
```

**If no orphans:**
```
✅ No orphaned files detected. Project structure looks clean!
```

### Important Rules

1. **Never move files automatically** - Always wait for user permission
2. **Run after doc updates** - Don't interrupt the main workflow
3. **Be concise** - Don't overwhelm user with too much detail
4. **Categorize clearly** - Group by file type for easy understanding
5. **Suggest action** - Tell user how to fix (run cleanup command)

### Frequency

- **Every time:** After completing documentation updates
- **Exception:** Skip if user just ran cleanup (avoid redundant alerts)
- **Throttle:** If same orphans detected multiple times in short period, mention once per session

---

## Pre-Commit Validation Mode

**Trigger:** Before `git commit` or when user runs `/docs-maintainer validate`

Run these checks before allowing a commit that includes documentation changes:

### Check 1: Stale Timestamps
```bash
# Find REQUIREMENTS.md files with "Last updated" older than 30 days
grep -rl "Last updated:" docs/features/*/REQUIREMENTS.md | while read f; do
  date=$(grep -oP 'Last updated:\s*\K[\d-]+' "$f")
  echo "$f: $date"
done
```
Flag any REQUIREMENTS.md where `Last updated` is > 30 days old AND the corresponding code files were modified recently.

### Check 2: Missing CHANGELOG Entries
```bash
# Get files changed since last commit
git diff --cached --name-only | while read f; do
  # For each changed code file, check if its feature CHANGELOG was also updated
  feature=$(python -c "
import yaml
with open('docs/feature-registry.yaml') as fh:
    reg = yaml.safe_load(fh)
for name, data in reg.get('features', {}).items():
    files = data.get('backend_files', []) + data.get('frontend_files', [])
    if '$f' in files:
        print(name)
        break
" 2>/dev/null)
  if [ -n "$feature" ]; then
    changelog="docs/features/$feature/CHANGELOG.md"
    if ! git diff --cached --name-only | grep -q "$changelog"; then
      echo "⚠ $f changed but $changelog not updated"
    fi
  fi
done
```

### Check 3: Broken Doc Links
```bash
# Scan staged .md files for broken relative links
git diff --cached --name-only --diff-filter=AM -- '*.md' | while read f; do
  grep -oP '\[.*?\]\(\K[^)]+' "$f" | grep -v '^http' | while read link; do
    target=$(dirname "$f")/"$link"
    [ ! -e "$target" ] && echo "⚠ Broken link in $f: $link"
  done
done
```

### Check 4: Orphan Detection
Run the existing orphan detection logic (from Proactive Orphan Detection section) on staged files only.

**Output format:**
```
📋 Pre-Commit Validation
  ✓ Timestamps: All current
  ⚠ CHANGELOG: 2 features missing entries
  ✓ Links: No broken links
  ✓ Orphans: None detected

  Result: 1 warning — proceed with commit? (y/n)
```

---

## Continuous Monitoring Mode

**Trigger:** On session start (via `start-session` skill integration) or `/docs-maintainer monitor`

Collects documentation health metrics without blocking the user's workflow.

### Metric 1: CLAUDE.md Modification Frequency
```bash
# Count CLAUDE.md modifications in last 20 commits
claude_changes=$(git log --oneline -20 --diff-filter=M -- CLAUDE.md | wc -l)
echo "CLAUDE.md changed in $claude_changes of last 20 commits"
# Threshold: > 5 changes = high churn, consider splitting
```

### Metric 2: Feature Doc Coverage
```bash
# For each feature in registry, check if all 3 required docs exist
python -c "
import yaml, os
with open('docs/feature-registry.yaml') as f:
    reg = yaml.safe_load(f)
for name, data in reg.get('features', {}).items():
    folder = data.get('docs_folder', f'docs/features/{name}/')
    missing = []
    for doc in ['README.md', 'REQUIREMENTS.md', 'CHANGELOG.md']:
        if not os.path.exists(os.path.join(folder, doc)):
            missing.append(doc)
    if missing:
        print(f'⚠ {name}: missing {", ".join(missing)}')
"
```

### Metric 3: Cross-Reference Staleness
Check if key cross-references are still valid:
- Port numbers in CLAUDE.md match `backend/.env` and `frontend/.env.local`
- API URLs in frontend config match backend config
- Broker implementation status in comparison-matrix.md matches actual adapter files

**Output format:**
```
📊 Documentation Health (Session Start)
  CLAUDE.md churn:     3/20 commits (normal)
  Feature doc coverage: 8/10 features complete
  Cross-ref staleness:  1 stale reference found

  💡 Run `/docs-maintainer validate` for detailed check
```

---

## Cross-Reference Audit Matrix

Expanded cross-reference validation covering all critical documentation consistency points.

| Source Doc | Must Match | Field/Section |
|-----------|------------|---------------|
| `CLAUDE.md` Development Environment table | `backend/.env` PORT value | Dev Backend port |
| `CLAUDE.md` Development Environment table | `frontend/.env.local` VITE_API_BASE_URL | Frontend API URL |
| `CLAUDE.md` Implementation Status | `docs/IMPLEMENTATION-CHECKLIST.md` Progress | Feature completion % |
| `comparison-matrix.md` Section 11 | Actual adapter files in `backend/app/services/brokers/` | Broker implementation status |
| Broker expert skill `last_verified` | Current date | Freshness (< 30 days) |
| `docs/feature-registry.yaml` file lists | Actual files on filesystem | File existence |
| `frontend/CLAUDE.md` fixture exports | Actual exports in `tests/e2e/fixtures/auth.fixture.js` | Named export list |
| `docs/testing/e2e-test-rules.md` | `tests/e2e/helpers/wait-helpers.js` exports | Helper function list |

### Audit Workflow

1. **Read** each source doc's relevant section
2. **Read** the corresponding target file/directory
3. **Compare** values — flag any mismatches
4. **Report** with specific file:line references for easy fixing

**Output format:**
```
🔍 Cross-Reference Audit
  ✓ Ports: CLAUDE.md ↔ .env files consistent
  ✓ API URLs: Frontend ↔ Backend consistent
  ⚠ comparison-matrix.md: Lists 6 brokers, found 5 adapter dirs
  ✓ Feature registry: All 47 files exist
  ⚠ zerodha-expert: last_verified 45 days ago

  2 issues found — see details above
```

---

## References

- [Feature Registry Schema](./references/feature-registry-schema.md) - Registry file format and patterns
- [Requirements Template](./references/requirements-template.md) - REQUIREMENTS.md structure
- [Changelog Template](./references/changelog-template.md) - CHANGELOG.md format and examples
- [Doc Update Rules](./references/doc-update-rules.md) - Comprehensive update rules by file type
- [Path Validation](./references/path-validation.md) - **CRITICAL** - Exact path templates and validation rules
- [Cleanup Rules](./references/cleanup-rules.md) - File organization and orphan detection rules

## Mandatory Validation Steps

**CRITICAL:** Before updating ANY documentation, you MUST complete these validation steps in order:

### Step 1: Verify Feature Exists
```
1. Open docs/feature-registry.yaml
2. Check if feature exists in the 'features:' section
3. If feature doesn't exist:
   → STOP: Add feature to registry first OR
   → STOP: Add to 'unassigned' and alert user
```

### Step 2: Verify Folder Exists
```
1. Read the docs_folder path from registry for this feature
   Example: watchlist → docs_folder: "docs/features/watchlist/"

2. Verify this folder exists on filesystem
   Use: ls docs/features/{feature}/ OR glob pattern

3. If folder doesn't exist:
   → CREATE IT FIRST: mkdir -p docs/features/{feature}/
   → Then create README.md, REQUIREMENTS.md, CHANGELOG.md in that folder
```

### Step 3: Build Exact Paths Using Templates
```
DO NOT guess or infer paths. Use the exact template:

Feature Docs:
  README.md       → {docs_folder}/README.md
  REQUIREMENTS.md → {docs_folder}/REQUIREMENTS.md
  CHANGELOG.md    → {docs_folder}/CHANGELOG.md

Where {docs_folder} comes from registry, e.g., "docs/features/watchlist/"

Final paths:
  ✅ docs/features/watchlist/README.md
  ✅ docs/features/watchlist/REQUIREMENTS.md
  ✅ docs/features/watchlist/CHANGELOG.md
```

### Step 4: Verify Paths Before Writing
```
Before using Edit or Write tool:
1. Double-check the full path matches template
2. Ensure feature name in path matches registry
3. Ensure doc type (README/REQUIREMENTS/CHANGELOG) is correct
```

### Step 5: Document New Feature Folders
```
If you created a new feature folder:
1. Add entry to docs/feature-registry.yaml under 'features:'
2. Include docs_folder path
3. List backend_files and frontend_files
4. Create all 3 required files (README, REQUIREMENTS, CHANGELOG)
```

---

**Validation Errors to Avoid:**

❌ **WRONG - Using inferred path:**
```
Writing to: docs/features/my-feature/CHANGELOG.md
(without checking registry first)
```

✅ **RIGHT - Using validated path:**
```
1. Check registry: features.my-feature.docs_folder = "docs/features/my-feature/"
2. Build path: docs/features/my-feature/CHANGELOG.md
3. Verify folder exists: ls docs/features/my-feature/
4. Write to: docs/features/my-feature/CHANGELOG.md
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Feature not found in registry` | New feature not in `feature-registry.yaml` | Add feature entry to registry first |
| Doc written to wrong path | Path inferred instead of read from registry | Follow Step 3 of Mandatory Validation |
| Duplicate CHANGELOG entries | Skill re-ran after partial completion | Check for existing `[Unreleased]` entries before appending |

---

## Quality Checklist

Before finishing doc updates:

**Path Validation (MANDATORY):**
- [ ] Verified feature exists in feature-registry.yaml
- [ ] Verified docs_folder path exists on filesystem
- [ ] Used exact path from registry (NOT inferred or guessed)
- [ ] Created missing folders before writing docs
- [ ] All doc paths follow template: `{docs_folder}/{DOC_TYPE}.md`

**Content Quality:**
- [ ] Identified correct feature(s) for changed files
- [ ] Updated feature CHANGELOG.md with clear descriptions
- [ ] Updated feature REQUIREMENTS.md if new capabilities added
- [ ] Updated root CHANGELOG.md if major change
- [ ] Updated API/architecture docs if applicable
- [ ] Included file paths in all CHANGELOG entries
- [ ] Used Keep a Changelog format
- [ ] Updated "Last updated" timestamp in REQUIREMENTS.md
- [ ] Updated feature-registry.yaml if new files created
- [ ] All doc files are valid Markdown

**Proactive Detection:**
- [ ] Scanned for orphaned files in root directory
- [ ] Scanned for orphaned files in docs/features/
- [ ] If orphans found: Alerted user with categorized list
- [ ] If orphans found: Suggested `/docs-maintainer cleanup` command
- [ ] If no orphans: Confirmed project structure is clean

**Broker-Specific (only for broker adapter changes):**
- [ ] comparison-matrix.md Implementation Status (section 11) matches actual adapter status
- [ ] CLAUDE.md Supported Brokers table reflects current implementation
- [ ] IMPLEMENTATION-CHECKLIST.md Progress Tracking table is accurate
- [ ] Relevant broker expert skill's Implementation Status table is current
- [ ] feature-registry.yaml broker-abstraction paths include new adapter files
