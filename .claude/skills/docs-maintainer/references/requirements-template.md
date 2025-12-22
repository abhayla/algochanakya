# REQUIREMENTS.md Template

Template and guidelines for feature REQUIREMENTS.md files.

## Format

```markdown
# [Feature Name] Requirements

## Core Requirements
- [x] Requirement 1 with brief description
- [x] Requirement 2 with brief description
- [ ] Future requirement (not yet implemented)

## API Requirements
- [x] GET /api/endpoint - Description
- [x] POST /api/endpoint - Description
- [x] PUT /api/endpoint/{id} - Description
- [x] DELETE /api/endpoint/{id} - Description

## UI Requirements
- [x] Component requirement with user-facing description
- [x] Layout requirement
- [x] Interaction requirement

## Data Requirements
- [x] `table_name` table with description
- [x] Index on field_name
- [x] JSON field for flexible data

## Integration Requirements
- [x] External service integration (e.g., WebSocket, Kite API)
- [x] Internal service dependency

## Performance Requirements
- [x] Load time constraint
- [x] Concurrent user support
- [x] Data volume handling

---
Last updated: YYYY-MM-DD
```

## Section Guidelines

### Core Requirements
**Purpose:** High-level feature capabilities

**Format:**
```markdown
- [x] Brief capability description (user-focused)
```

**Examples:**
```markdown
- [x] Create up to 5 watchlists per user
- [x] Real-time price updates via WebSocket
- [x] Search instruments by name or symbol
```

### API Requirements
**Purpose:** All API endpoints for the feature

**Format:**
```markdown
- [x] METHOD /api/path - Brief description
```

**Examples:**
```markdown
- [x] GET /api/watchlists - Get all user watchlists
- [x] POST /api/watchlists - Create new watchlist
- [x] DELETE /api/watchlists/{id} - Delete watchlist
```

### UI Requirements
**Purpose:** User interface components and interactions

**Format:**
```markdown
- [x] Component/interaction description
```

**Examples:**
```markdown
- [x] Tabbed interface for multiple watchlists
- [x] "+ Add Instrument" button with search modal
- [x] Drag-and-drop reordering (not implemented yet)
```

### Data Requirements
**Purpose:** Database tables, fields, indexes

**Format:**
```markdown
- [x] `table_name` description
```

**Examples:**
```markdown
- [x] `watchlists` table with JSONB instruments array
- [x] Index on instrument_token
- [x] One-to-many relationship with user
```

### Integration Requirements
**Purpose:** External services, APIs, shared services

**Format:**
```markdown
- [x] Service name and purpose
```

**Examples:**
```markdown
- [x] WebSocket at ws://localhost:8000/ws/ticks
- [x] Kite Connect API for instrument master
- [x] Redis caching for instrument data
```

### Performance Requirements
**Purpose:** Performance benchmarks and constraints

**Format:**
```markdown
- [x] Metric with threshold
```

**Examples:**
```markdown
- [x] Handle up to 100 instruments per watchlist
- [x] Real-time updates within 500ms
- [x] Search results within 200ms
```

## Checkbox Rules

### ✅ Checked Boxes
Use `[x]` for requirements that are **implemented and working**.

### ⬜ Unchecked Boxes
Use `[ ]` for requirements that are:
- Planned but not yet implemented
- Future enhancements
- Nice-to-have features

### ❌ Don't Uncheck
**NEVER uncheck a box once it's checked.** If a feature is removed, delete the requirement entirely.

## Adding New Requirements

When code changes add new capabilities:

1. Identify the appropriate section
2. Add new checkbox item
3. Mark as `[x]` if implemented, `[ ]` if planned
4. Update timestamp at bottom

**Example:**
```markdown
## API Requirements
- [x] GET /api/watchlists - Get all watchlists
- [x] POST /api/watchlists/bulk - Bulk create watchlists  # NEW

---
Last updated: 2025-12-22  # UPDATED
```

## Removing Requirements

If a feature is deprecated or removed:

1. Delete the requirement line entirely
2. Don't uncheck or mark as removed
3. Update timestamp

**Example:**
```markdown
# Before
- [x] Legacy export format

# After
# (line deleted entirely)
---
Last updated: 2025-12-22
```

## Full Example

```markdown
# Watchlist Requirements

## Core Requirements
- [x] Create up to 5 watchlists per user
- [x] Add up to 100 instruments per watchlist
- [x] Remove instruments from watchlist
- [x] Real-time price updates via WebSocket
- [ ] Drag-and-drop reordering (planned)

## API Requirements
- [x] GET /api/watchlists - Get all user watchlists
- [x] POST /api/watchlists - Create new watchlist
- [x] PUT /api/watchlists/{id} - Update watchlist
- [x] DELETE /api/watchlists/{id} - Delete watchlist

## UI Requirements
- [x] Tabbed interface for multiple watchlists
- [x] "+ Add Instrument" button with search modal
- [x] Live price display with color coding
- [x] Connection status indicator

## Data Requirements
- [x] `watchlists` table with JSONB instruments array
- [x] `instruments` table with Kite master data
- [x] Index on instrument_token

## Integration Requirements
- [x] WebSocket at ws://localhost:8000/ws/ticks
- [x] Kite WebSocket for live prices
- [x] Instrument master download from Kite API

## Performance Requirements
- [x] Handle up to 100 instruments per watchlist
- [x] Real-time updates within 500ms
- [x] Search results within 200ms

---
Last updated: 2025-12-22
```
