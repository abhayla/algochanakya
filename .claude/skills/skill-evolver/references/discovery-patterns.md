# Discovery Patterns

How skill-evolver identifies skill candidates from different data sources.

## Pattern 1: Unresolved Error Clusters

**Source:** knowledge.db `error_patterns` table

**Signal:** Error type with `occurrence_count >= 3` AND no strategy with `current_score >= 0.3`

**Skill candidate type:** Error-fixing skill (category: `debugging`)

**Example:**
- AlembicError seen 7 times, no effective strategy → candidate: `migration-fixer`
- WebSocketError seen 4 times, best strategy score 0.15 → candidate: `ws-reconnector`

## Pattern 2: Repeated Tool Sequences

**Source:** Session logs (`.claude/logs/workflow-sessions.log`)

**Signal:** Same sequence of 3+ tool calls appearing in 3+ different sessions

**Skill candidate type:** Workflow automation skill (category: `workflow`)

**Example:**
- `[Read → Grep → Edit → Bash(test) → Edit]` repeated 5 times for selector updates → candidate: `selector-updater`
- `[Bash(git) → Bash(git) → Bash(git)]` branch cleanup 4 times → candidate: `branch-cleaner`

## Pattern 3: User Override Patterns

**Source:** Session logs — cases where user rejected Claude's approach and provided correction

**Signal:** User correction after skill invocation, same correction pattern 2+ times

**Skill candidate type:** Improved version of existing skill, or new specialized skill

**Example:**
- User keeps correcting test-fixer to use `waitForResponse` instead of `waitForTimeout` → evolve test-fixer, don't create new skill

## Pattern 4: High-Risk File Clusters

**Source:** knowledge.db `file_risk_scores` table

**Signal:** Files with `risk_score > 0.7` that share a common module/feature area

**Skill candidate type:** Specialized validation/audit skill (category: `testing`)

**Example:**
- 3 files in `autopilot/` all have risk > 0.7 → candidate: `autopilot-validator`

## Anti-Patterns (DO NOT create skills for)

1. **One-off tasks** — If it happened once, it's not a pattern
2. **Already covered** — Check existing skills before proposing new ones
3. **Too generic** — "Fix all errors" is not a skill, it's what fix-loop does
4. **Environment-specific** — Issues caused by local setup, not code patterns
5. **User preference** — Style choices (tabs vs spaces) are rules, not skills
