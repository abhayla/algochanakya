# Feature Registry Schema

The feature registry (`docs/feature-registry.yaml`) maps code files to features for automatic documentation maintenance.

## File Structure

```yaml
# Auto-detection patterns
auto_detect_patterns:
  - pattern: "glob/pattern/**"
    feature: feature-name

# Explicit feature mappings
features:
  feature-name:
    name: "Display Name"
    docs_folder: "docs/features/feature-name/"
    description: "Brief description"
    backend_files:
      - path/to/file.py
    frontend_files:
      - path/to/file.vue
    tests:
      - tests/path/**
    used_by_features:  # Optional - for shared services
      - other-feature
    additional_docs:   # Optional - for extra docs folders
      - docs/autopilot/**

# Shared/infrastructure files
shared_files:
  category:
    - file/path
    docs: "docs/path/to/docs.md"

# Unassigned (auto-populated)
unassigned: []

# Metadata
version: "1.0.0"
last_updated: "YYYY-MM-DD"
maintained_by: "docs-maintainer skill"
```

## Auto-Detection Patterns

Patterns use glob syntax to match file paths:

```yaml
auto_detect_patterns:
  # Exact match
  - pattern: "backend/app/api/routes/auth.py"
    feature: authentication

  # Wildcard file match
  - pattern: "backend/app/api/routes/watchlist*.py"
    feature: watchlist

  # Directory wildcard
  - pattern: "frontend/src/components/watchlist/**"
    feature: watchlist

  # Multiple wildcards
  - pattern: "backend/app/api/v1/autopilot/**"
    feature: autopilot
```

### Pattern Matching Rules

1. **Most specific pattern wins**
2. **Multiple matches possible** (file can belong to multiple features)
3. **Case-sensitive** on Linux/Mac, case-insensitive on Windows

## Feature Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name for the feature |
| `docs_folder` | string | Yes | Path to feature documentation folder |
| `description` | string | Yes | Brief feature description |
| `backend_files` | array | No | List of backend file paths |
| `frontend_files` | array | No | List of frontend file paths |
| `tests` | array | No | Test file paths (can use globs) |
| `used_by_features` | array | No | Features that use this (for shared services) |
| `additional_docs` | array | No | Extra documentation folders |

## Shared Files

Files used across multiple features:

```yaml
shared_files:
  constants:
    - backend/app/constants/trading.py
    - frontend/src/constants/trading.js
    docs: "docs/architecture/constants.md"

  database:
    - backend/app/database.py
    - backend/alembic/**
    docs: "docs/architecture/database.md"
```

## Adding a New Feature

1. Add auto-detect patterns:
```yaml
auto_detect_patterns:
  - pattern: "backend/app/api/routes/newfeature*.py"
    feature: newfeature
  - pattern: "frontend/src/views/NewFeatureView.vue"
    feature: newfeature
```

2. Add explicit feature entry:
```yaml
features:
  newfeature:
    name: "New Feature"
    docs_folder: "docs/features/newfeature/"
    description: "Description of new feature"
    backend_files:
      - backend/app/api/routes/newfeature.py
      - backend/app/models/newfeature.py
    frontend_files:
      - frontend/src/views/NewFeatureView.vue
      - frontend/src/stores/newfeature.js
    tests:
      - tests/e2e/specs/newfeature/**
```

3. Update metadata:
```yaml
last_updated: "2025-12-22"
```

## Updating Registry

The skill automatically updates the registry when:
- New files are created
- Files don't match any existing patterns

Manual updates needed when:
- Reorganizing file structure
- Renaming features
- Changing documentation structure
