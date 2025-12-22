# Documentation Update Rules

Comprehensive rules for updating different types of documentation based on code changes.

## Quick Reference Table

| Changed File Type | Update These Docs | Add This Information |
|-------------------|-------------------|----------------------|
| API route | Feature CHANGELOG, Feature REQUIREMENTS (API), `docs/api/README.md` | Endpoint signature, brief description |
| Database model | Feature CHANGELOG, Feature REQUIREMENTS (Data), `docs/architecture/database.md` | Table/field info, migration notes |
| Vue component | Feature CHANGELOG, Feature REQUIREMENTS (UI) | Component description, props, events |
| Pinia store | Feature CHANGELOG, Feature REQUIREMENTS | Store actions, state additions |
| Service/util | Feature CHANGELOG | Service function description |
| Test file | `docs/testing/coverage-matrix.md` | Updated test counts |
| Constants | Feature CHANGELOG, `CLAUDE.md` (if trading constants) | New constant values |
| Config | `docs/guides/development.md`, `.env.example` | New env variables |
| Major feature | Root `CHANGELOG.md` (Unreleased) | High-level summary |
| Architecture | `CLAUDE.md`, relevant `docs/architecture/*.md` | Pattern updates, diagrams |

## Detailed Rules by File Type

### 1. API Routes (`backend/app/api/routes/*.py`)

**Always Update:**
- Feature `CHANGELOG.md`
- Feature `REQUIREMENTS.md` (API Requirements section)
- `docs/api/README.md`

**When to Update Root CHANGELOG:**
- New major endpoint (e.g., first API for a feature)
- Breaking API change

**CHANGELOG Entry Example:**
```markdown
### Added
- GET /api/watchlists/{id}/bulk endpoint for batch operations (file: backend/app/api/routes/watchlist.py)
```

**REQUIREMENTS Entry Example:**
```markdown
## API Requirements
- [x] GET /api/watchlists/{id}/bulk - Batch retrieve instruments
```

**API Docs Entry:**
```markdown
### Watchlist Endpoints
- `GET /api/watchlists/{id}/bulk` - Batch retrieve instruments by IDs
  - Query params: `ids` (comma-separated list)
  - Returns: Array of instruments
```

---

### 2. Database Models (`backend/app/models/*.py`)

**Always Update:**
- Feature `CHANGELOG.md`
- Feature `REQUIREMENTS.md` (Data Requirements section)
- `docs/architecture/database.md`

**When to Update Root CHANGELOG:**
- New table creation
- Major schema change

**CHANGELOG Entry Example:**
```markdown
### Added
- `is_default` column to watchlists table for default watchlist marking (file: backend/app/models/watchlists.py)
```

**REQUIREMENTS Entry Example:**
```markdown
## Data Requirements
- [x] `is_default` boolean column in watchlists table
- [x] Unique constraint on user_id + is_default=true
```

**Database Docs Update:**
Update schema table with new fields:
```markdown
### Watchlists Table

| Column | Type | Description |
|--------|------|-------------|
| is_default | Boolean | Whether this is the user's default watchlist |
```

---

### 3. Vue Components (`frontend/src/components/**/*.vue`, `frontend/src/views/**/*.vue`)

**Always Update:**
- Feature `CHANGELOG.md`
- Feature `REQUIREMENTS.md` (UI Requirements section)

**When to Update:**
- New component created
- Significant UI/UX change
- New props/events added

**CHANGELOG Entry Example:**
```markdown
### Added
- Bulk actions toolbar component for watchlist (file: frontend/src/components/watchlist/BulkActionsToolbar.vue)

### Changed
- Redesigned position exit modal with tabbed interface (file: frontend/src/components/positions/ExitModal.vue)
```

**REQUIREMENTS Entry Example:**
```markdown
## UI Requirements
- [x] Bulk actions toolbar with select all/clear/delete buttons
- [x] Keyboard shortcut support (Ctrl+A for select all)
```

---

### 4. Pinia Stores (`frontend/src/stores/*.js`)

**Always Update:**
- Feature `CHANGELOG.md`
- Feature `REQUIREMENTS.md` (if new state/actions affect requirements)

**CHANGELOG Entry Example:**
```markdown
### Added
- Bulk selection state management in watchlist store (file: frontend/src/stores/watchlist.js)
```

---

### 5. Services (`backend/app/services/*.py`)

**Always Update:**
- Feature `CHANGELOG.md`

**When to Update Root CHANGELOG:**
- New shared service affecting multiple features
- Major algorithm change

**CHANGELOG Entry Example:**
```markdown
### Added
- Retry logic with exponential backoff in order executor (file: backend/app/services/order_executor.py)

### Fixed
- Memory leak in Kite ticker service (file: backend/app/services/kite_ticker.py)
```

---

### 6. Test Files (`tests/**`)

**Always Update:**
- `docs/testing/coverage-matrix.md`

**When to Update Feature CHANGELOG:**
- Only if test reveals/fixes a significant issue

**Coverage Matrix Update:**
```markdown
| Screen | Happy Path | Edge Cases | Visual | API | Total |
|--------|-----------|-----------|--------|-----|-------|
| Watchlist | 15 (+2) | 12 | 5 | 8 | 40 (+2) |
```

---

### 7. Trading Constants (`backend/app/constants/trading.py`, `frontend/src/constants/trading.js`)

**Always Update:**
- `CLAUDE.md` (if new underlying or major change)
- All affected feature `CHANGELOG.md` files

**CHANGELOG Entry Example:**
```markdown
### Added
- MIDCPNIFTY underlying with lot size 75 and strike step 25 (file: backend/app/constants/trading.py)
```

**CLAUDE.md Update:**
Add to trading constants section:
```markdown
- MIDCPNIFTY: 75 lots, 25 strike step
```

---

### 8. Configuration (`backend/app/config.py`, `*.env.example`)

**Always Update:**
- `docs/guides/development.md`
- `.env.example` file itself

**When to Update Root CHANGELOG:**
- New environment variable required

**Development Guide Update:**
```markdown
### Environment Variables

**New in v1.2.0:**
- `FEATURE_FLAG_BULK_DELETE` - Enable bulk delete feature (default: false)
```

---

### 9. WebSocket (`backend/app/websocket/*.py`, `backend/app/api/routes/websocket.py`)

**Always Update:**
- `docs/features/websocket/CHANGELOG.md`
- All affected feature `CHANGELOG.md` files (watchlist, positions, etc.)

**When to Update Architecture Docs:**
- New message types
- Protocol changes

**CHANGELOG Entry Example:**
```markdown
### Added
- BULK_UPDATE message type for batch tick updates (file: backend/app/websocket/manager.py)
```

---

### 10. Major Feature Addition

**Always Update:**
- Root `CHANGELOG.md` (Unreleased section)
- Feature-specific docs (CHANGELOG, REQUIREMENTS, README)
- `CLAUDE.md` (add feature to overview)
- `docs/README.md` (add link to feature docs)

**Root CHANGELOG Entry:**
```markdown
## [Unreleased]

### Added
- AutoPilot Phase 5 with AI adjustment suggestions and delta monitoring
```

---

## Special Cases

### Cross-Feature Files

Files used by multiple features (e.g., `kite_ticker.py`):

**Update ALL related feature CHANGELOGs:**
```markdown
# docs/features/watchlist/CHANGELOG.md
### Fixed
- WebSocket reconnection timing (file: backend/app/services/kite_ticker.py)

# docs/features/positions/CHANGELOG.md
### Fixed
- WebSocket reconnection timing (file: backend/app/services/kite_ticker.py)

# docs/features/option-chain/CHANGELOG.md
### Fixed
- WebSocket reconnection timing (file: backend/app/services/kite_ticker.py)
```

### New File Creation

**If file matches auto-detect pattern:**
1. Automatically assign to feature
2. Add to feature-registry.yaml
3. Update feature CHANGELOG

**If file doesn't match any pattern:**
1. Infer feature from folder/imports
2. Add to unassigned if unsure
3. Update feature CHANGELOG if confident

### File Deletion

**Update:**
- Feature CHANGELOG (under "Removed")
- Feature REQUIREMENTS (remove related requirements)
- Remove from feature-registry.yaml

**Example:**
```markdown
### Removed
- Legacy CSV export endpoint (file: backend/app/api/routes/export_csv.py)
```

---

## Update Frequency

| Doc Type | Update Frequency |
|----------|-----------------|
| Feature CHANGELOG | After every relevant code change |
| Feature REQUIREMENTS | When new capabilities added/removed |
| Root CHANGELOG | For major changes only |
| CLAUDE.md | For architecture/pattern changes |
| API Docs | When endpoints added/changed |
| Architecture Docs | When system design changes |
| Testing Docs | When test counts change significantly |

---

## Priority Levels

### High Priority (Always Update)
1. Feature CHANGELOG.md
2. Feature REQUIREMENTS.md (if capabilities changed)

### Medium Priority (Update if Applicable)
3. Root CHANGELOG.md (for major changes)
4. API/Architecture docs (for structural changes)

### Low Priority (Update Occasionally)
5. Testing coverage matrix
6. Development guides
