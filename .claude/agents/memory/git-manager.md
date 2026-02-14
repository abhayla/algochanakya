# Git-Manager Agent Memory

**Purpose:** Track commit patterns, co-committed files, and scope usage
**Agent:** git-manager
**Last Updated:** 2026-02-14

---

## Patterns Observed

### Commit Patterns

<!-- Track common commit patterns and message styles -->

#### Feature Commits
- None yet

#### Bug Fix Commits
- None yet

#### Refactor Commits
- None yet

### Co-Committed Files

<!-- Files that are frequently changed together -->

- None yet

---

## Decisions Made

### Commit Message Style

<!-- Document commit message conventions observed -->

#### Current Style
- Format: `type(scope): subject`
- Types: feat, fix, docs, refactor, test, chore
- Subject: imperative mood, no period

#### Scope Usage
- `autonomous-workflow` - workflow/hooks/commands
- `broker-abstraction` - broker adapter changes
- `autopilot` - AutoPilot strategy engine
- `option-chain` - Option chain service
- `e2e-tests` - E2E test changes

### Protected File Decisions

<!-- Decisions about which files should never be committed -->

- Never commit: `.env*`, `notes`, `knowledge.db`, `workflow-state.json`
- Never commit from: `C:\Apps\algochanakya` (production folder)

---

## Common Issues

### Accidental Includes

<!-- Files that are accidentally staged/committed -->

- None yet

### Premature Commits

<!-- Commits attempted before workflow steps complete -->

- None yet

---

## Last Updated

2026-02-14: Agent memory system initialized
