# Development Tooling Audit & Action Plan

**Date:** 2026-02-25
**Status:** In Progress
**Purpose:** Comprehensive audit of all tools, integrations, and automation available to accelerate AlgoChanakya development.

---

## Current State Summary

The automation layer is **exceptionally mature** — 17 hooks, 29 skills, 5 agents, 4 CI workflows, a learning engine, and full workflow state machine enforcement. The gaps are primarily in **standard dev tooling** and **MCP server integrations** that complement the existing Claude Code automation.

---

## RANKED ACTION PLAN

### TIER 1: QUICK WINS (Trivial effort, immediate impact)

#### 1. Add MCP Servers for GitHub + PostgreSQL
- **Status:** NEEDS USER (credentials required)
- **Current:** Zero MCP servers configured
- **Benefit:** Native GitHub issue/PR management + direct PostgreSQL debugging
- **Effort:** Trivial | **Impact:** High

#### 2. Add ESLint + Prettier for Frontend
- **Status:** IMPLEMENTED
- **Current:** Zero JS/Vue linting or formatting
- **Benefit:** Catches Vue 3 Composition API mistakes, enforces consistent formatting
- **Effort:** Trivial | **Impact:** Medium

#### 3. Add Ruff for Backend Python Linting
- **Status:** IMPLEMENTED
- **Current:** No Python linter (no Ruff, Black, Flake8, or isort)
- **Benefit:** 100x faster than Flake8+Black, catches async/await mistakes, auto-fixes
- **Effort:** Trivial | **Impact:** Medium

#### 4. Create `.vscode/` Workspace Configuration
- **Status:** IMPLEMENTED
- **Current:** No VS Code workspace settings, extensions, or debug configs
- **Benefit:** One-click debug for FastAPI/Playwright/pytest, recommended extensions
- **Effort:** Trivial | **Impact:** Medium

### TIER 2: MODERATE WINS (Moderate effort, high impact)

#### 5. Add Dependabot Security Scanning
- **Status:** IMPLEMENTED
- **Current:** No dependency vulnerability scanning
- **Benefit:** Auto-PRs for vulnerable deps (critical for trading platform with encrypted credentials)
- **Effort:** Moderate | **Impact:** High

#### 6. Add `pre-commit` Git Hooks
- **Status:** IMPLEMENTED
- **Current:** Claude Code hooks work but standard `git commit` bypasses them
- **Benefit:** ESLint/Ruff/Prettier on staged files, secret scanning on every commit
- **Effort:** Moderate | **Impact:** Medium

#### 7. Auto-generate TypeScript API Client from OpenAPI
- **Status:** NEEDS USER (tooling decision + running backend)
- **Current:** Manual Axios calls in `src/services/*Api.js`
- **Benefit:** Typed API client auto-generated from FastAPI's OpenAPI spec
- **Effort:** Moderate | **Impact:** High

#### 8. Visual Regression Testing with Playwright Screenshots
- **Status:** FUTURE
- **Current:** Screenshots captured but not diffed against baselines
- **Benefit:** Catch CSS regressions, layout shifts
- **Effort:** Moderate | **Impact:** Medium

### TIER 3: STRATEGIC INVESTMENTS

#### 9. Docker Compose for Dev Environment
- **Status:** FUTURE
- **Current:** Manual installation of Python, Node, PostgreSQL, Redis
- **Benefit:** `docker-compose up` → full stack in 30 seconds
- **Effort:** Moderate | **Impact:** High (when team grows)

#### 10. TypeScript Migration for Frontend
- **Status:** FUTURE
- **Current:** Pure JavaScript frontend
- **Benefit:** Type-safe broker interfaces, catch undefined property access
- **Effort:** Significant (incremental) | **Impact:** High

#### 11. Staging Environment
- **Status:** FUTURE
- **Current:** Dev (localhost) → Production (direct)
- **Benefit:** Test with real broker APIs before production
- **Effort:** Significant | **Impact:** High

### TIER 4: NICE-TO-HAVE

#### 12. Structured Logging with Correlation IDs
- **Status:** FUTURE
- **Effort:** Moderate | **Impact:** Medium

#### 13. API Rate Limit Dashboard
- **Status:** FUTURE
- **Effort:** Moderate | **Impact:** Medium

#### 14. Database Migration Testing in CI
- **Status:** FUTURE
- **Effort:** Moderate | **Impact:** Medium

---

## What's Already Excellent (Don't Change)

| Category | Assessment |
|----------|-----------|
| Hook System | 17 hooks covering all critical paths |
| Skill System | 29 skills with domain expertise (6 broker experts) |
| Agent System | 5 specialized agents with persistent memory |
| Learning Engine | knowledge.db with auto-synthesis |
| Workflow Enforcement | 7-step implement with state machine |
| E2E Testing | 125 Playwright specs with POM, Allure |
| CI/CD | 4 workflows with Allure on GitHub Pages |
| Documentation | SSOT principle with CLAUDE.md hierarchy |
| Production Safety | Multi-layer protection (deny rules + hooks + agents) |

## What's Underutilized

| Capability | Recommendation |
|-----------|---------------|
| MCP Servers | Add GitHub + PostgreSQL MCP |
| Claude Code worktrees | Use for parallel feature branches |
| Background agents | Run test suites in background while coding |
| Parallel Task execution | Run backend + frontend tests simultaneously |
| Plan mode | Use for complex multi-file refactors |
