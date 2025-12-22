---
name: docs-maintainer
description: Automatically maintain project documentation after code changes. Use proactively after any code modification to keep docs in sync.
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

## References

- [Feature Registry Schema](./references/feature-registry-schema.md) - Registry file format and patterns
- [Requirements Template](./references/requirements-template.md) - REQUIREMENTS.md structure
- [Changelog Template](./references/changelog-template.md) - CHANGELOG.md format and examples
- [Doc Update Rules](./references/doc-update-rules.md) - Comprehensive update rules by file type
- [Path Validation](./references/path-validation.md) - **CRITICAL** - Exact path templates and validation rules

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
