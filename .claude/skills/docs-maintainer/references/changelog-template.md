# CHANGELOG.md Template

Template and guidelines for feature CHANGELOG.md files using Keep a Changelog format.

## Format

```markdown
# [Feature Name] Changelog

All notable changes to this feature will be documented in this file.

## [Unreleased]

### Added
- New feature description (file: path/to/file.ext)

### Changed
- Modified feature description (file: path/to/file.ext)

### Fixed
- Bug fix description (file: path/to/file.ext)

### Removed
- Removed feature description (file: path/to/file.ext)

## [1.1.0] - YYYY-MM-DD

### Added
- Feature added in this version (file: path/to/file.ext)

## [1.0.0] - YYYY-MM-DD

### Added
- Initial implementation (file: path/to/file.ext)
```

## Keep a Changelog Sections

| Section | When to Use | Example |
|---------|-------------|---------|
| **Added** | New features, endpoints, components | "Added bulk delete endpoint (file: backend/app/api/routes/watchlist.py)" |
| **Changed** | Changes to existing functionality | "Changed P/L grid to use user preferences (file: frontend/src/views/StrategyBuilderView.vue)" |
| **Fixed** | Bug fixes | "Fixed WebSocket reconnection issue (file: backend/app/services/kite_ticker.py)" |
| **Deprecated** | Features marked for removal | "Deprecated legacy export format (file: backend/app/api/routes/export.py)" |
| **Removed** | Features removed entirely | "Removed CSV export (file: backend/app/api/routes/export.py)" |
| **Security** | Security fixes | "Fixed SQL injection in search (file: backend/app/api/routes/search.py)" |

## Entry Rules

### Always Include File Path
```markdown
# WRONG
### Added
- Bulk delete feature

# RIGHT
### Added
- Bulk delete feature (file: backend/app/api/routes/watchlist.py)
```

### Use Present Tense
```markdown
# WRONG
### Added
- Added new feature

# RIGHT
### Added
- New feature description
```

### Be Concise (One Line)
```markdown
# WRONG
### Added
- Added a new bulk delete feature that allows users to
  delete multiple items at once by selecting them and
  clicking the delete button

# RIGHT
### Added
- Bulk delete functionality for multiple item removal (file: backend/app/api/routes/watchlist.py)
```

### Multiple Files
```markdown
### Changed
- Redesigned login UI with new theme (files: frontend/src/views/LoginView.vue, frontend/src/styles/login.css)
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes
- **MINOR** (1.0.0 → 1.1.0): New features (backwards-compatible)
- **PATCH** (1.0.0 → 1.0.1): Bug fixes (backwards-compatible)

## [Unreleased] Section

**Purpose:** Track changes since the last release.

**When to Add:**
- After every code change
- Before any versioned release

**When to Move to Version:**
- When creating a new release
- Move all [Unreleased] entries to new version section

**Example:**
```markdown
# Before release
## [Unreleased]

### Added
- New feature X (file: a.py)
- New feature Y (file: b.py)

## [1.0.0] - 2024-12-01
### Added
- Initial release

# After creating v1.1.0 release
## [Unreleased]

## [1.1.0] - 2024-12-22
### Added
- New feature X (file: a.py)
- New feature Y (file: b.py)

## [1.0.0] - 2024-12-01
### Added
- Initial release
```

## Adding Entries

### Step 1: Identify Section
- New capability → Added
- Modification → Changed
- Bug fix → Fixed
- Removal → Removed

### Step 2: Write Description
- What changed (not how or why)
- User-facing language
- Include file path

### Step 3: Add to [Unreleased]
```markdown
## [Unreleased]

### Added
- Pagination support for watchlist API (file: backend/app/api/routes/watchlist.py)
```

## Examples by File Type

### API Route Change
```markdown
### Added
- GET /api/positions/grouped endpoint (file: backend/app/api/routes/positions.py)

### Changed
- Updated /api/watchlists response format (file: backend/app/api/routes/watchlist.py)
```

### Database Model Change
```markdown
### Added
- `is_default` column to watchlists table (file: backend/app/models/watchlists.py)

### Changed
- Made `name` column nullable in strategies table (file: backend/app/models/strategies.py)
```

### Vue Component Change
```markdown
### Added
- Bulk actions bar component (file: frontend/src/components/watchlist/BulkActionsBar.vue)

### Changed
- Redesigned position exit modal (file: frontend/src/components/positions/ExitModal.vue)
```

### Service Change
```markdown
### Added
- Retry logic for order execution (file: backend/app/services/order_executor.py)

### Fixed
- Memory leak in WebSocket ticker service (file: backend/app/services/kite_ticker.py)
```

### Bug Fix
```markdown
### Fixed
- Breakeven calculation accuracy in P/L grid (file: backend/app/services/pnl_calculator.py)
- WebSocket auto-reconnect timing issue (file: frontend/src/stores/watchlist.js)
```

## Full Example

```markdown
# Watchlist Changelog

All notable changes to the Watchlist feature will be documented in this file.

## [Unreleased]

### Added
- Bulk delete for multiple instruments (file: backend/app/api/routes/watchlist.py)
- Keyboard shortcuts for watchlist navigation (file: frontend/src/views/WatchlistView.vue)

### Changed
- Improved search performance with debounce (file: frontend/src/components/watchlist/InstrumentSearch.vue)

### Fixed
- Connection indicator not updating on reconnect (file: frontend/src/components/watchlist/IndexHeader.vue)

## [1.1.0] - 2024-12-10

### Added
- Filter instruments by Cash/F&O (file: frontend/src/components/watchlist/InstrumentSearch.vue)

### Changed
- Increased max instruments per watchlist to 150 (file: backend/app/models/watchlists.py)

## [1.0.0] - 2024-12-04

### Added
- Initial watchlist feature with real-time prices (file: frontend/src/views/WatchlistView.vue)
- WebSocket integration for live tick data (file: backend/app/api/routes/websocket.py)
- Instrument search functionality (file: backend/app/api/routes/instruments.py)
```

## Common Mistakes to Avoid

### ❌ Don't duplicate entries
```markdown
# WRONG
### Added
- Feature X (file: a.py)
- Feature X (file: a.py)  # Duplicate!
```

### ❌ Don't skip file paths
```markdown
# WRONG
### Added
- New feature

# RIGHT
### Added
- New feature (file: path/to/file.ext)
```

### ❌ Don't use past tense
```markdown
# WRONG
### Added
- Added new feature

# RIGHT
### Added
- New feature description
```

### ❌ Don't put technical implementation details
```markdown
# WRONG
### Changed
- Refactored watchlist store to use Composition API with ref instead of reactive

# RIGHT
### Changed
- Improved watchlist state management (file: frontend/src/stores/watchlist.js)
```
