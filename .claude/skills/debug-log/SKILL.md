---
name: debug-log
description: Structured debug iteration tracking with escalation tiers (Standard, ThinkHard, UltraThink, Human). Use when debugging complex issues, tracking hypothesis iterations, or when fix attempts exceed 3 tries. Triggers on 'debug log', 'track debugging', or repeated fix failures.
metadata:
  author: AlgoChanakya
  version: "1.0"
---

# Debug Log

## When to Use
- Debugging a complex issue requiring multiple attempts
- User invokes /debug-log [issue-name]
- Tracking hypothesis → fix → result iterations
- Need escalation strategy (ThinkHard, UltraThink, human review)

## When NOT to Use

- Simple single-attempt fixes (just fix directly)
- Issues already diagnosed (no need to track iterations)

## Purpose

Creates/updates structured debug logs at `.claude/logs/debug/{issue-name}.md` with:
- Hypothesis tracking per iteration
- Fix attempts and outcomes
- Escalation tiers (Standard → ThinkHard → UltraThink → Human)
- Pattern recognition across iterations

## Escalation Tiers

### Tier 1: Standard Analysis (Attempts 1-2)
**Approach:**
- Read error messages and stack traces
- Check recent code changes
- Review related files
- Standard debugging techniques

**Tools:**
- Read, Grep, Glob for investigation
- Standard reasoning (no ThinkHard)

**Outcome:**
- Quick fixes for obvious issues
- Straightforward bugs

---

### Tier 2: ThinkHard Mode (Attempts 3-4)
**Approach:**
- Deeper investigation with extended thinking
- Cross-file analysis
- Check edge cases and race conditions
- Review architectural patterns

**Tools:**
- Task tool with debugger agent (ThinkHard mode)
- Extended context gathering
- Trace analysis (Playwright traces, logs)

**Outcome:**
- Complex logical errors
- Integration issues
- Timing/race condition bugs

---

### Tier 3: UltraThink Mode (Attempts 5+)
**Approach:**
- Ultra-deep analysis with maximum thinking depth
- System-level investigation
- Review fundamental assumptions
- Consider environmental factors

**Tools:**
- Task tool with debugger agent (UltraThink mode)
- Multiple investigation angles
- Comprehensive trace/log analysis
- Architecture review

**Outcome:**
- Deeply hidden bugs
- Environmental issues
- Architectural problems

---

### Tier 4: Human Review (Attempts 6+)
**Recommendation:**
- Suggest human developer review
- Provide comprehensive summary for handoff
- Document all attempts and hypotheses
- Recommend alternative approaches

**When to escalate:**
- 5+ failed attempts with no progress
- Issue appears to be environmental/external
- Requires domain knowledge beyond AI capability
- Fundamental architecture change needed

---

## Debug Log Format

Debug logs follow a structured template with:
- **Issue Summary:** Description, error message, affected component, severity
- **Iterations:** Numbered attempts with hypothesis, investigation, fix, result, learning
- **Escalation Markers:** Tier 1 (Standard) → Tier 2 (ThinkHard) → Tier 3 (UltraThink) → Tier 4 (Human)
- **Resolution:** Final status, successful fix, root cause, lessons learned

**Complete template with all fields:** See [references/log-format-reference.md](./references/log-format-reference.md)

---

## Workflow

### Step 1: Initialize or Load Debug Log

**If issue-name provided:**
- Check if `.claude/logs/debug/{issue-name}.md` exists
- If exists: Load and display current state
- If not exists: Create new debug log

**If no issue-name:**
- List all active debug logs
- Show status and iteration count for each

### Step 2: Detect Current Tier

Based on iteration count in log:
- Iterations 1-2: Tier 1 (Standard)
- Iterations 3-4: Tier 2 (ThinkHard)
- Iterations 5+: Tier 3 (UltraThink)
- Iterations 6+: Recommend Tier 4 (Human Review)

### Step 3: Record New Iteration

For current debugging attempt:
1. Read previous iterations to understand what's been tried
2. Formulate hypothesis based on learnings
3. Investigate using tier-appropriate tools
4. Attempt fix
5. Record result

### Step 4: Update Log File

Append new iteration to log with:
- Timestamp
- Current tier
- Hypothesis
- Investigation steps
- Fix attempted
- Result (FAILED/RESOLVED/PARTIAL)
- Learnings

### Step 5: Determine Next Steps

**If RESOLVED:**
- Mark log as RESOLVED
- Document root cause and lessons learned
- Close debug log

**If FAILED:**
- Increment iteration count
- Check if tier escalation needed
- Provide guidance for next attempt

**If 6+ attempts:**
- Recommend human review
- Generate handoff summary

---

## Implementation Notes

### Log Directory Structure
```
.claude/logs/debug/
├── e2e-login-timeout.md
├── backend-broker-adapter-error.md
├── frontend-pnl-calculation.md
└── ...
```

### Issue Naming Convention
- Use kebab-case
- Include component/screen prefix: `{component}-{issue-slug}`
- Examples:
  - `positions-exit-modal-not-showing`
  - `autopilot-kill-switch-not-triggering`
  - `optionchain-iv-calculation-nan`

### Auto-Close Resolved Logs
After 7 days, move resolved logs to archive:
`.claude/logs/debug/archive/{issue-name}.md`

### Integration with Learning Engine
Successful resolutions (especially Tier 2/3) should be recorded in learning engine via `/reflect`.

---

## Example Usage

### Scenario 1: New Issue
```
User: /debug-log positions-exit-modal-not-showing

Creating new debug log: positions-exit-modal-not-showing

# Debug Log: positions-exit-modal-not-showing
**Created:** 2026-02-14 15:30:00
**Status:** ACTIVE
**Current Tier:** Tier 1 (Standard)

## Issue Summary
**Description:** Exit modal not showing when clicking exit button in positions screen

Ready to record Iteration 1. What's your hypothesis?
```

### Scenario 2: Existing Issue (3rd Attempt)
```
User: /debug-log positions-exit-modal-not-showing

Loading debug log: positions-exit-modal-not-showing

**Status:** ACTIVE
**Current Tier:** Tier 2 (ThinkHard) - Escalating from Tier 1
**Previous Attempts:** 2 (both failed)

## Previous Hypotheses:
1. Missing data-testid (FAILED - testid was correct)
2. Z-index issue (FAILED - modal visible in DOM)

⚠️ Escalating to ThinkHard mode for deeper analysis.

Ready to record Iteration 3. Recommend using debugger agent with ThinkHard.
```

### Scenario 3: Escalation to Human
```
User: /debug-log backend-broker-adapter-timeout

Loading debug log: backend-broker-adapter-timeout

**Status:** ESCALATED
**Current Tier:** Tier 4 (Human Review Recommended)
**Attempts:** 6 (all unsuccessful)

🚨 This issue has been through 6 debugging iterations across 3 tiers without resolution.

## Summary for Handoff:
- **Issue:** Broker adapter timing out on all requests after 10min runtime
- **Hypotheses tested:**
  1. Rate limiting (FAILED - occurs even with delays)
  2. Token expiration (FAILED - token valid)
  3. Memory leak (PARTIAL - memory grows but timeout occurs before limit)
  4. Network connection (FAILED - network stable)
  5. Session timeout (FAILED - sessions refresh correctly)
  6. Thread pool exhaustion (FAILED - threads available)

## Recommended Actions:
1. Review production logs for patterns
2. Check broker API status/maintenance
3. Consider environmental differences (dev vs prod)
4. Escalate to broker API support if needed

Would you like to continue debugging or escalate to human review?
```

---

## Self-Improvement

After each debug session, consider:
- Was the tier escalation triggered at the right time?
- Did previous iteration learnings inform current hypothesis?
- Were investigation steps thorough enough for the tier?
- Should any patterns be added to learning engine?

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Debug log file not created | `.claude/logs/debug/` doesn't exist | Create: `mkdir -p .claude/logs/debug/` |
| Iteration count mismatch | Manually edited log | Renumber iterations sequentially (1, 2, 3...) |
| Tier not escalating | Forgot to update tier field | Check iteration count: 1-2=Tier 1, 3-4=Tier 2, 5+=Tier 3, 6+=Tier 4 |
| Can't find old debug log | Log was archived or deleted | Check `.claude/logs/debug/archive/` for resolved logs |

---

## References

- [Log Format Reference](./references/log-format-reference.md) - Complete debug log template with field descriptions

---

## Learnings Log

2026-02-14: Debug-log skill initialized
