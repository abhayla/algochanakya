# Git-Manager Agent Memory

**Purpose:** Track commit patterns, co-committed files, and scope usage
**Agent:** git-manager
**Last Updated:** 2026-02-25

---

## Patterns Observed

### Commit Patterns

#### Feature Commits
- `feat(phase-4): complete multi-broker ticker/WebSocket architecture`
- `feat(phase-5): implement frontend broker selection UI`
- `feat(phase-5): implement order execution adapters for all 6 brokers`
- `feat(multi-broker): add OAuth flows for 4 brokers, DataSourceBadge visibility, and WebSocket reconnect`
- `feat(market-data): implement Dhan REST market data adapter`
- `feat(auto-verify): complete Section 10 with enhanced iteration tracking`

#### Bug Fix Commits
- `fix(auth): fix duplicate user creation when same email connects multiple brokers`
- `fix(rate-limiter): correct Kite and Upstox rate limits`
- `fix(e2e): fix reset button visibility and test for broker settings`
- `fix(tests): add ARRAY/UUID/BigInteger/ENUM SQLite compilers to root conftest`
- `fix(deps): add aiosqlite to requirements.txt for async SQLite tests`

#### Documentation Commits
- `docs(skills): comprehensive overhaul of broker comparison matrix to v2.5`
- `docs(rate-limiter): document Fyers daily 100K limit and historical 1 req/sec`
- `docs: modularize CLAUDE.md and sync multi-broker architecture docs`

#### Performance/Chore Commits
- `perf(hooks,ci): optimize workflow hooks, CI pipelines, and dev tooling`
- `chore(security): clean up .env.example - remove real credentials, add all 6 brokers`
- `test(phase-6): add E2E tests for broker abstraction`

### Co-Committed Files

- `backend/app/models/*.py` + `backend/alembic/versions/*.py` — model + migration always together
- `backend/app/services/brokers/*.py` + `backend/tests/backend/brokers/*.py` — adapter + test
- `.claude/skills/*/SKILL.md` + `docs/guides/AUTOMATION_WORKFLOWS.md` — skill + automation docs
- `frontend/package.json` + `frontend/package-lock.json` — always together
- `CLAUDE.md` + `backend/CLAUDE.md` + `frontend/CLAUDE.md` — when architecture changes

---

## Decisions Made

### Commit Message Style

#### Current Style
- Format: `type(scope): subject`
- Types: feat, fix, docs, refactor, test, chore, perf
- Subject: imperative mood, lowercase, no period
- Multi-scope: `perf(hooks,ci):` with comma separator
- Footer: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

#### Scope Usage (from git log analysis)
- `skills` — skill definition changes (most frequent: 4 commits)
- `tests`, `e2e` — test additions/fixes
- `rate-limiter` — rate limiting changes
- `phase-N` — multi-broker implementation phases (phase-4, phase-5, phase-6)
- `market-data` — market data adapter work
- `broker-abstraction` — broker adapter architecture
- `hooks,ci` — hook pipeline and CI changes
- `auth` — authentication fixes
- `deps` — dependency changes
- `security` — security-related changes
- `ai` — AI module changes
- `autopilot` — AutoPilot engine changes

### Protected File Decisions

- Never commit: `.env*`, `notes`, `knowledge.db`, `workflow-state.json`
- Never commit from: `C:\Apps\algochanakya` (production folder)
- Never commit: `.auth-state.json`, `.auth-token` (test credentials)
- Careful with: `frontend/package-lock.json` (large diffs, always include with package.json)

---

## Common Issues

### Accidental Includes

- `notes` file sometimes modified but should not be committed
- `.env` files — protected by deny rules in settings.json
- `knowledge.db` — hook-managed, protected by deny rules

### Premature Commits

- Attempting commit before post-fix-pipeline in full workflow mode
- Attempting commit before all 7 steps complete (blocked by verify_evidence_artifacts.py)
- Fast-track mode: only requires step1 + step4 (understanding + tests pass)

---

## Last Updated

2026-02-14: Agent memory system initialized
2026-02-25: Populated with baseline data from git log (30 most recent commits)
