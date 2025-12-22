# Path Validation Reference

This document provides exact path templates and validation rules to ensure documentation is always placed in the correct location.

## Path Templates

### Feature Documentation Paths

All feature docs MUST use this exact structure:

```
docs/features/{feature}/
├── README.md           # Feature overview and architecture
├── REQUIREMENTS.md     # Checklist of requirements
└── CHANGELOG.md        # Feature-specific changelog
```

**Template:**
```
{docs_folder} = Value from feature-registry.yaml (e.g., "docs/features/watchlist/")

README.md       → {docs_folder}/README.md
REQUIREMENTS.md → {docs_folder}/REQUIREMENTS.md
CHANGELOG.md    → {docs_folder}/CHANGELOG.md
```

**Examples:**
```
Watchlist feature:
  Registry: docs_folder: "docs/features/watchlist/"
  Paths:
    ✅ docs/features/watchlist/README.md
    ✅ docs/features/watchlist/REQUIREMENTS.md
    ✅ docs/features/watchlist/CHANGELOG.md

AutoPilot feature:
  Registry: docs_folder: "docs/features/autopilot/"
  Paths:
    ✅ docs/features/autopilot/README.md
    ✅ docs/features/autopilot/REQUIREMENTS.md
    ✅ docs/features/autopilot/CHANGELOG.md
```

---

### Project-Level Documentation Paths

| Doc Type | Exact Path | When to Update |
|----------|-----------|----------------|
| Root Changelog | `CHANGELOG.md` | Major changes, new features |
| Main Instructions | `CLAUDE.md` | Architecture/pattern changes |
| Docs Index | `docs/README.md` | New feature added |
| API Overview | `docs/api/README.md` | New endpoint added |
| API Spec | `docs/api/openapi.yaml` | API contract changes |
| Architecture Docs | `docs/architecture/{topic}.md` | System design changes |
| Testing Docs | `docs/testing/{topic}.md` | Test infrastructure changes |
| Guides | `docs/guides/{topic}.md` | Setup/troubleshooting updates |

---

## Folder Existence Verification

### Before Writing Any Doc

**Step 1: Read Registry**
```yaml
# Open: docs/feature-registry.yaml
features:
  watchlist:
    docs_folder: "docs/features/watchlist/"  # ← Use this exact path
```

**Step 2: Verify Folder Exists**
```bash
# Use Bash tool or Glob tool
ls docs/features/watchlist/

# OR
glob pattern: "docs/features/watchlist/*"
```

**Step 3: Create If Missing**
```bash
# If folder doesn't exist:
mkdir -p docs/features/watchlist/

# Then create all 3 required files
```

---

## Creating New Feature Folders

When adding a completely new feature to the project:

### Step 1: Add to Registry
```yaml
# Edit: docs/feature-registry.yaml

features:
  new-feature:
    name: "New Feature Display Name"
    docs_folder: "docs/features/new-feature/"  # ← Define path
    description: "Brief feature description"
    backend_files:
      - backend/app/api/routes/new_feature.py
    frontend_files:
      - frontend/src/views/NewFeatureView.vue
```

### Step 2: Create Folder Structure
```bash
mkdir -p docs/features/new-feature/
```

### Step 3: Create All Required Files

**README.md:**
```markdown
# New Feature

## Overview
Brief description of the feature.

## Features
- Feature capability 1
- Feature capability 2

## Technical Implementation
### Backend
### Frontend
```

**REQUIREMENTS.md:**
```markdown
# New Feature Requirements

## Core Requirements
- [ ] Requirement 1

## API Requirements
- [ ] GET /api/new-feature

---
Last updated: YYYY-MM-DD
```

**CHANGELOG.md:**
```markdown
# New Feature Changelog

All notable changes to this feature will be documented here.

## [Unreleased]

## [1.0.0] - YYYY-MM-DD
### Added
- Initial implementation (file: backend/app/api/routes/new_feature.py)
```

---

## Validation Checklist

Use this checklist every time you update documentation:

### Pre-Write Validation
- [ ] **Step 1:** Opened `docs/feature-registry.yaml`
- [ ] **Step 2:** Found feature in `features:` section
- [ ] **Step 3:** Read `docs_folder` value from registry
- [ ] **Step 4:** Verified folder exists (used ls or glob)
- [ ] **Step 5:** If folder missing, created it with mkdir -p
- [ ] **Step 6:** Built full path using template: `{docs_folder}/{DOC_TYPE}.md`

### Path Correctness
- [ ] Path matches registry exactly (no inference)
- [ ] Feature name in path matches registry key
- [ ] Doc type is correct (README/REQUIREMENTS/CHANGELOG)
- [ ] No typos in folder or file name

### Post-Write Validation
- [ ] File was created at correct path
- [ ] File is valid Markdown
- [ ] File contains required sections
- [ ] Updated registry if new feature added

---

## Common Mistakes & Fixes

### ❌ Mistake 1: Inferring Path Without Registry Check
```
# WRONG
Writing to: docs/features/watchlists/CHANGELOG.md  # Guessed "watchlists" (plural)
```

**Fix:**
```
1. Check registry: features.watchlist.docs_folder
2. Get exact path: "docs/features/watchlist/"  # Singular, not plural
3. Use that: docs/features/watchlist/CHANGELOG.md
```

---

### ❌ Mistake 2: Skipping Folder Verification
```
# WRONG
Write tool: docs/features/new-feature/README.md
Error: Directory doesn't exist
```

**Fix:**
```
1. Verify folder: ls docs/features/new-feature/
2. If missing: mkdir -p docs/features/new-feature/
3. Then write: docs/features/new-feature/README.md
```

---

### ❌ Mistake 3: Wrong Doc Type in Path
```
# WRONG
Writing to: docs/features/watchlist/changelog.md  # Lowercase, wrong name
```

**Fix:**
```
Use exact template:
  ✅ CHANGELOG.md (uppercase, correct name)
  ✅ REQUIREMENTS.md
  ✅ README.md
```

---

### ❌ Mistake 4: Feature Not in Registry
```
# WRONG
Updating docs for "reports" feature
Error: Feature doesn't exist in registry
```

**Fix:**
```
1. Add feature to registry first
2. Define docs_folder
3. Create folder structure
4. Then update docs
```

---

## Error Handling

### Scenario 1: Feature Not Found in Registry

**Action:**
1. Check if feature should be added to registry
2. If yes: Add to registry with proper structure
3. If no: Add file to `unassigned` section
4. Alert user about missing feature

---

### Scenario 2: Folder Doesn't Exist

**Action:**
1. Create folder: `mkdir -p {docs_folder}`
2. Create all 3 required files (README, REQUIREMENTS, CHANGELOG)
3. Use templates from references
4. Proceed with updates

---

### Scenario 3: Multiple Features Share a File

**Action:**
1. Update docs for ALL related features
2. Add same CHANGELOG entry to each feature's CHANGELOG.md
3. Example: `kite_ticker.py` used by watchlist, positions, option-chain
   → Update all 3 feature CHANGELOGs

---

## Quick Reference

| Action | Tool | Command |
|--------|------|---------|
| Read registry | Read | `docs/feature-registry.yaml` |
| Check folder exists | Bash or Glob | `ls docs/features/{feature}/` |
| Create folder | Bash | `mkdir -p docs/features/{feature}/` |
| Get all features | Grep | Search "docs_folder:" in registry |
| Verify path template | Manual | Check against template above |

---

## Validation Examples

### Example 1: Updating Watchlist CHANGELOG

**Validation Steps:**
```
1. ✅ Read registry: docs/feature-registry.yaml
2. ✅ Found: features.watchlist.docs_folder = "docs/features/watchlist/"
3. ✅ Verify exists: ls docs/features/watchlist/
4. ✅ Build path: docs/features/watchlist/CHANGELOG.md
5. ✅ Edit file: docs/features/watchlist/CHANGELOG.md
```

---

### Example 2: Creating New Feature "Reports"

**Validation Steps:**
```
1. ✅ Add to registry:
   features:
     reports:
       docs_folder: "docs/features/reports/"

2. ✅ Create folder: mkdir -p docs/features/reports/

3. ✅ Create files:
   - docs/features/reports/README.md
   - docs/features/reports/REQUIREMENTS.md
   - docs/features/reports/CHANGELOG.md

4. ✅ Update docs/README.md with link
```

---

## Summary

**Always follow this sequence:**
1. Read feature-registry.yaml
2. Get docs_folder value
3. Verify folder exists
4. Create if missing
5. Build exact path using template
6. Write/edit doc at validated path
7. Run checklist

**Never:**
- Guess or infer paths
- Skip folder verification
- Use lowercase doc names
- Write before validating
