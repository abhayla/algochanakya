# Documentation Structure Reorganization Plan

## Current State

**8 documentation files scattered across the project:**
- `README.md` (root) - Project overview
- `CLAUDE.md` (root) - AI assistant instructions
- `TESTING-PLAN.md` (root) - E2E testing documentation
- `DATABASE_SETUP.md` (root) - Database configuration
- `WATCHLIST_IMPLEMENTATION.md` (root) - Watchlist feature docs
- `frontend/README.md` - Vue template docs
- `docs/cmp-fallback-plan.md` - CMP feature plan

**Existing image/screenshot locations:**
- `images/` - Strategy Builder screenshots (SB-*.png) - needs to be moved
- `tests/screenshots/` - Test screenshots (gitignored)
- `.playwright-mcp/` - MCP-related screenshots - leave as-is
- `frontend/src/assets/` - Vue assets (vue.svg) - keep in place
- `frontend/public/` - Public assets (vite.svg) - keep in place

## Proposed Industry-Standard Structure

```
algochanakya/
├── README.md                    # Keep at root (entry point)
├── CLAUDE.md                    # Keep at root (Claude Code requires this location)
├── CHANGELOG.md                 # NEW: Version history
│
├── docs/
│   ├── README.md                # Docs index/navigation
│   │
│   ├── assets/
│   │   ├── diagrams/            # Architecture, flow diagrams
│   │   └── screenshots/         # FLAT structure with descriptive names
│   │       ├── login.png
│   │       ├── dashboard.png
│   │       ├── watchlist-live-prices.png
│   │       ├── optionchain-nifty.png
│   │       ├── strategy-builder-iron-condor.png
│   │       └── positions-pnl.png
│   │
│   ├── architecture/
│   │   ├── overview.md          # System architecture overview
│   │   ├── authentication.md    # OAuth flow, session management
│   │   ├── websocket.md         # Live price streaming
│   │   └── database.md          # Database models, migrations
│   │
│   ├── guides/
│   │   ├── development.md       # Dev environment setup
│   │   ├── database-setup.md    # ← Move DATABASE_SETUP.md
│   │   ├── deployment.md        # Future: production deployment
│   │   └── troubleshooting.md   # NEW: Common issues & fixes
│   │
│   ├── features/
│   │   ├── watchlist.md         # ← Move WATCHLIST_IMPLEMENTATION.md
│   │   ├── option-chain.md      # Option chain feature docs
│   │   ├── strategy-builder.md  # Strategy builder feature docs
│   │   └── positions.md         # Positions feature docs
│   │
│   ├── api/
│   │   ├── README.md            # API overview
│   │   ├── endpoints.md         # Manual endpoint docs
│   │   └── openapi.yaml         # NEW: Export from FastAPI /openapi.json
│   │
│   ├── testing/
│   │   ├── README.md            # ← Move TESTING-PLAN.md
│   │   └── conventions.md       # data-testid conventions
│   │
│   ├── decisions/               # NEW: Architecture Decision Records (ADRs)
│   │   ├── template.md          # ADR template
│   │   └── 001-tech-stack.md    # Initial tech stack decision
│   │
│   └── plans/
│       └── cmp-fallback.md      # ← Move docs/cmp-fallback-plan.md
│
├── tests/
│   └── screenshots/             # Keep existing (test artifacts, gitignored)
│
├── frontend/
│   └── README.md                # Keep (standard for subprojects)
└── backend/
    └── README.md                # Create (backend-specific setup)
```

## Files to Move

| Current Location | New Location |
|-----------------|--------------|
| `DATABASE_SETUP.md` | `docs/guides/database-setup.md` |
| `WATCHLIST_IMPLEMENTATION.md` | `docs/features/watchlist.md` |
| `TESTING-PLAN.md` | `docs/testing/README.md` |
| `docs/cmp-fallback-plan.md` | `docs/plans/cmp-fallback.md` |

## Files to Create

**Core:**
1. **`docs/README.md`** - Documentation index with links to all docs
2. **`backend/README.md`** - Backend-specific setup and structure
3. **`CHANGELOG.md`** - Version history (at root)

**Architecture (extract from CLAUDE.md):**
4. **`docs/architecture/overview.md`** - Project Overview, Tech Stack
5. **`docs/architecture/authentication.md`** - OAuth Flow, Session Management
6. **`docs/architecture/websocket.md`** - WebSocket Live Prices, KiteTickerService
7. **`docs/architecture/database.md`** - Database Models, Migrations

**New additions:**
8. **`docs/guides/troubleshooting.md`** - Common issues (token expiry, WebSocket disconnect, CORS, DB errors)
9. **`docs/api/README.md`** - API overview
10. **`docs/api/openapi.yaml`** - Export from FastAPI `/openapi.json`
11. **`docs/decisions/template.md`** - ADR template
12. **`docs/decisions/001-tech-stack.md`** - Initial tech stack decision (Vue, FastAPI, etc.)

## Files to Update (References)

1. **`CLAUDE.md`** - Update reference to `TESTING-PLAN.md` → `docs/testing/README.md`
2. **`README.md`** - Add link to docs/ directory

## Implementation Steps

1. **Create directory structure**
   ```
   docs/
   ├── assets/
   │   ├── diagrams/           # Architecture, flow diagrams
   │   └── screenshots/        # FLAT structure
   ├── architecture/
   ├── guides/
   ├── features/
   ├── api/
   ├── testing/
   ├── decisions/              # ADRs
   └── plans/
   ```

2. **Move existing documentation files**
   - `DATABASE_SETUP.md` → `docs/guides/database-setup.md`
   - `WATCHLIST_IMPLEMENTATION.md` → `docs/features/watchlist.md`
   - `TESTING-PLAN.md` → `docs/testing/README.md`
   - `docs/cmp-fallback-plan.md` → `docs/plans/cmp-fallback.md`

3. **Move & rename existing images (flat structure)**
   - `images/SB-1.png` → `docs/assets/screenshots/strategy-builder-overview.png`
   - `images/SB-iron-condor-1.png` → `docs/assets/screenshots/strategy-builder-iron-condor.png`
   - (rename other SB-*.png with descriptive names)
   - Delete empty `images/` folder after move

4. **Create new files**

   **Core docs:**
   - `docs/README.md` - Documentation index with links
   - `backend/README.md` - Backend-specific setup
   - `CHANGELOG.md` - Version history (at root)

   **Architecture (extract from CLAUDE.md):**
   - `docs/architecture/overview.md` - Tech Stack, Project Structure
   - `docs/architecture/authentication.md` - OAuth Flow, Session Management
   - `docs/architecture/websocket.md` - Live Prices, KiteTickerService
   - `docs/architecture/database.md` - Models, Migrations

   **New additions:**
   - `docs/guides/troubleshooting.md` - Token expiry, WebSocket, CORS, DB errors
   - `docs/api/README.md` - API overview
   - `docs/api/openapi.yaml` - Export from FastAPI
   - `docs/decisions/template.md` - ADR template
   - `docs/decisions/001-tech-stack.md` - Tech stack decision

   - `.gitkeep` files in empty asset directories

5. **Update CLAUDE.md (keep substantial!)**
   - Update `TESTING-PLAN.md` → `docs/testing/README.md`
   - Keep summaries of architecture with links to detailed docs
   - Example format:
     ```markdown
     ## Architecture
     Quick reference:
     - Tech: Vue 3 + FastAPI + PostgreSQL
     - Auth: Zerodha OAuth → JWT sessions
     - Live data: Kite WebSocket

     For details: [docs/architecture/](docs/architecture/)
     ```
   - Keep: Commands, patterns, key info for quick AI reference

6. **Update README.md**
   - Add "Documentation" section with link to `docs/`

7. **Update .gitignore** (if needed)
   - Ensure `tests/screenshots/` remains gitignored
   - `docs/assets/` should be tracked

## Image/Screenshot Conventions

| Type | Location | Git Status |
|------|----------|------------|
| Architecture diagrams | `docs/assets/diagrams/` | Tracked |
| UI screenshots (docs) | `docs/assets/screenshots/` | Tracked |
| Test screenshots | `tests/screenshots/` | Gitignored |

**Naming conventions (flat structure):**
- Diagrams: `{feature}-{description}.png` (e.g., `oauth-flow-diagram.png`, `websocket-architecture.png`)
- Screenshots: `{screen}-{description}.png` (e.g., `login-default.png`, `strategy-builder-iron-condor.png`)

## Priority Order

| Priority | Task | Time |
|----------|------|------|
| 1 | Create directory structure | 5 min |
| 2 | Move existing files | 5 min |
| 3 | Create `docs/README.md` index | 10 min |
| 4 | Create `backend/README.md` | 10 min |
| 5 | Extract architecture docs from CLAUDE.md | 30 min |
| 6 | Create `docs/guides/troubleshooting.md` | 15 min |
| 7 | Create `CHANGELOG.md` | 5 min |
| 8 | Create ADR template + first ADR | 15 min |
| 9 | Export OpenAPI spec | 5 min |

**Total: ~1.5 hours**

## Notes

- `CLAUDE.md` must stay at root (Claude Code looks for it there)
- `README.md` must stay at root (GitHub/GitLab convention)
- `frontend/README.md` stays in place (subproject convention)
- Empty directories need `.gitkeep` files to be tracked by git
- Test screenshots remain in `tests/screenshots/` (gitignored)
- **Keep CLAUDE.md substantial** - summaries + links, not just links
