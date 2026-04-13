# Session: 2026-04-11-broker-fix-and-e2e-test-plan

**Date:** 2026-04-11 15:30
**Branch:** main

---

## Working Files

| File | Status | Notes |
|------|--------|-------|
| `CLAUDE.md` | modified | Fixed path typos (C:\→D:\, VideCoding→VibeCoding), removed duplicate section, added 3 missing rules |
| `.claude/skills/angelone-expert/SKILL.md` | modified | v3.2: ONE key per account (not 3), IP-per-app uniqueness, updated .env config |
| `.claude/skills/angelone-3key-guide/SKILL.md` | modified | Added deprecation notice — 3-key premise was wrong |
| `tests/e2e/global-setup.js` | modified | Fixed: load dotenv + otplib for auto-TOTP login (was sending empty body) |
| `package.json` | modified | Added devDeps: dotenv, otplib |
| `backend/.env` | modified | New AngelOne API key (kiFUIq5R), refreshed Upstox token |
| `.claude/tasks/e2e-test-plan-v2.md` | created | 129-spec E2E test plan with skills + subagent strategy |
| `memory/user_broker_accounts.md` | modified | Updated IP, one-key learning, credential status |
| `memory/feedback_no_run_without_approval.md` | created | Don't run tests without explicit user approval |

## Git State

- **Branch:** main
- **Last 5 commits:**
  - de10d6b fix(e2e): fix global-setup to send credentials with auto-TOTP for AngelOne login
  - 904703d fix(claude): fix CLAUDE.md paths, update AngelOne skill with one-key-per-account learning
  - 8c8b7ed chore(claude): update agents, rules, skills, and hooks configuration
  - 46317b6 feat(claude): add e2e-verify-screen-each-test-1-by-1 skill and writing-skills
  - f1deb9d chore(claude): trim CLAUDE.md files, add new agents/rules/skills
- **Uncommitted changes:** No (all committed)
- **Stash list:** stash@{0}: WIP: Token mapping changes before multi-broker ticker refactor

## Key Decisions

- **SmartAPI uses ONE API key per account:** Old 3-key architecture was wrong. All 3 `.env` slots (ANGEL_API_KEY, ANGEL_HIST_API_KEY, ANGEL_TRADE_API_KEY) must contain the same value. Updated skill and deprecated angelone-3key-guide.
- **Static IP unique per app:** SmartAPI doesn't allow same IP on multiple apps. One app ("AC LiveData") is sufficient.
- **Global setup needs dotenv+otplib:** Playwright global-setup.js couldn't access backend/.env credentials. Added dotenv to load them and otplib to auto-generate TOTP codes.
- **Test plan uses two E2E skills:** `/e2e-verify-screen-each-test-1-by-1` for sequential phases (1-8), `/e2e-visual-run` for Phase 9 (dual-signal visual verification).
- **Servers via `start cmd /k`:** Claude Code bash can't keep long-running servers alive. Use `start cmd /k` on Windows to spawn persistent cmd windows.

## Task Progress

### Completed

- Fixed CLAUDE.md path typos and rules table
- Fixed Upstox token (auto-refresh)
- Fixed AngelOne API key (created new app on SmartAPI portal)
- Updated angelone-expert skill v3.2 with learnings
- Deprecated angelone-3key-guide skill
- Fixed global-setup.js for auto-TOTP login
- Created E2E test plan v2 (129 specs, 10 phases)
- Phase 0a: Health check (backend 200, frontend 200)
- Phase 0b: Frontend Vitest (245/245 passed)
- Phase 0c: Auth state generation (`.auth-state.json` + `.auth-token` created)

### In Progress

- Phase 0b: Backend pytest — agent was spawned but results not yet received
- Phase 1: Foundation tests (12 specs) — not started
- Login isolated tests: 6 failures found (login page UI changed, data-testid missing)

### Blocked

- None

## Relevant Docs

| Document | Relevance |
|----------|-----------|
| `.claude/tasks/e2e-test-plan-v2.md` | The full test plan — 129 specs, 10 phases, skills map, subagent strategy |
| `tests/e2e/helpers/market-status.helper.js` | Market open/close detection — 18/129 specs use it |
| `tests/e2e/global-setup.js` | Auth state generation — just fixed |
| `docs/ROADMAP.md` | Project roadmap — next priority is live broker verification |

## Resume Notes

- **Start here:** Run Phase 0b backend pytest (may need `pip install freezegun` first). Then start Phase 1 (Foundation — 12 specs) using `/e2e-verify-screen-each-test-1-by-1`.
- **Watch out for:**
  - Login isolated tests (6 failures) — login page UI has changed, data-testid elements missing
  - ISP IP may change — verify `203.212.220.70` still matches before broker tests
  - Backend pytest needs `freezegun` installed for 2 autopilot test files
  - Token expires after ~8h — re-run global setup if session is long
- **Context needed:** Read `.claude/tasks/e2e-test-plan-v2.md` for the full execution plan
