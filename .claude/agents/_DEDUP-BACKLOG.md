# Agent Directory Dedup Backlog

**Status:** Analyzed, cleanup deferred to a focused PR.
**Date analyzed:** 2026-04-17

## Summary

`.claude/agents/` has **33 logical agents** across **51 files**. **18 pairs** exist as both `foo.md` and `foo-agent.md`. The pairs are NOT identical — they diverged over time.

Two distinct shapes exist in the directory:

| Shape | Example | Recognition | Runtime-loadable? |
|---|---|---|---|
| **YAML-frontmatter agent** | `fastapi-api-tester-agent.md` | starts with `---` + `name:` + `tools:` | Yes (Claude Code agent format) |
| **Plain-markdown notes** | `debugger.md` | starts with `# Title` + `**Model:**` | No (pre-formalization notes) |

## Classification of the 18 duplicate pairs

### Tier A — `-agent.md` is YAML, `.md` is PLAIN markdown (delete plain)
5 pairs. The plain files are superseded notes with no frontmatter; Claude Code cannot load them.

- `debugger.md` → keep `debugger-agent.md`
- `tester.md` → keep `tester-agent.md`
- `code-reviewer.md` → keep `code-reviewer-agent.md`
- `git-manager.md` → keep `git-manager-agent.md`
- `planner-researcher.md` → keep `planner-researcher-agent.md`

### Tier B — both YAML (diverged content, manual review needed)
13 pairs. Diff ranges from 4 lines (near-duplicate) to 32 lines (substantial drift). Before deleting, the content of both must be reviewed and merged where needed.

| Pair | Diff lines | Suggested action |
|---|---|---|
| `context-reducer` | 12 | Compare bodies; merge into `-agent.md`; delete plain |
| `docs-manager` | 4 | Near-duplicate; delete plain |
| `fastapi-api-tester` | 2 (name only) | Delete plain — already inspected, only `name:` differs |
| `fastapi-database-admin` | 4 | Near-duplicate; delete plain |
| `flutter-dart` | 4 | Near-duplicate; delete plain |
| `parallel-worktree-orchestrator` | 8 | Review + merge + delete plain |
| `plan-executor` | 4 | Near-duplicate; delete plain |
| `quality-gate-evaluator` | 11 | Review + merge + delete plain |
| `security-auditor` | 16 | Review + merge + delete plain |
| `session-summarizer` | 12 | Review + merge + delete plain |
| `skill-author` | 32 | **Substantial drift — manual merge required** |
| `test-failure-analyzer` | 21 | Review + merge + delete plain |
| `web-research-specialist` | 8 | Review + merge + delete plain |

## Outgoing references to verify

These 4 doc files reference the stale plain agents and will need updating when the plain files are deleted:

- `.claude/AUDIT-FIXES-2026-02-14.md`
- `.claude/IMPLEMENTATION-NOTES.md`
- `.claude/rules.md`
- `.claude/WORKFLOW-DESIGN-SPEC.md`

Any reference to `agents/<name>.md` (without `-agent` suffix) should be updated to `agents/<name>-agent.md` at cleanup time.

## Agents WITHOUT a `-agent.md` pair (already canonical — do not touch)

These 7 use the plain name but have proper YAML frontmatter. They are reviewer/domain-specific agents that follow the canonical single-file convention:

- `autopilot-safety-reviewer`
- `broker-adapter-reviewer`
- `options-greeks-reviewer`
- `risk-state-reviewer`
- `smartapi-session-manager` (added 2026-04-17)
- `ticker-system-reviewer`
- `vue-pinia-reviewer` (added 2026-04-17)

## Agents with only `-agent.md` (newer, already canonical — do not touch)

- `e2e-conductor-agent`
- `pipeline-orchestrator-agent`
- `project-manager-agent`
- `test-healer-agent`
- `test-pipeline-agent`
- `test-scout-agent`
- `trading-domain-reviewer-agent`
- `visual-inspector-agent`

## Execution plan for the cleanup PR

1. Delete the 5 Tier A plain files (safe — no content loss).
2. For each Tier B pair, manually merge any unique content from the plain file into the `-agent.md`, then delete the plain file.
3. For `skill-author` specifically, review the 32-line diff carefully — the plain and `-agent` versions may have substantively different scopes.
4. Grep for `agents/<name>.md` references in the 4 doc files listed above and update to `-agent.md` form.
5. Run `/ssot-audit` skill to verify configuration-SSOT compliance post-cleanup.
6. Verify `.claude/settings.json` has no hook references to deleted files (none found at analysis time).

Estimated effort: 2-3 hours, one PR.
