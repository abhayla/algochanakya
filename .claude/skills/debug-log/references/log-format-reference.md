# Debug Log Format Reference

This document provides the complete template for debug log files created at `.claude/logs/debug/{issue-name}.md`.

## Template Structure

```markdown
# Debug Log: {issue-name}

**Created:** {timestamp}
**Last Updated:** {timestamp}
**Status:** ACTIVE | RESOLVED | ESCALATED
**Current Tier:** Tier 1 | Tier 2 | Tier 3 | Tier 4

---

## Issue Summary

**Description:**
{Clear description of the issue being debugged}

**Error Message:**
```
{Primary error message or symptom}
```

**Affected Component:**
{Screen/module/service affected}

**Severity:**
- Critical (blocks functionality)
- High (impacts user experience)
- Medium (workaround available)
- Low (minor issue)

---

## Iteration 1 (Tier 1: Standard)

**Timestamp:** {timestamp}

**Hypothesis:**
{What we think is causing the issue}

**Investigation:**
- {Action 1: Read file X, checked lines Y-Z}
- {Action 2: Ran test command, observed output}
- {Action 3: Reviewed error trace}

**Fix Attempted:**
```{language}
{Code change or configuration change}
```

**Result:**
- ❌ FAILED | ✅ RESOLVED | ⏭️ PARTIAL
- {Outcome description}
- {New error or behavior observed}

**Learning:**
{What this attempt taught us about the issue}

---

## Iteration 2 (Tier 1: Standard)

{Same structure as Iteration 1}

---

## Iteration 3 (Tier 2: ThinkHard)

**Timestamp:** {timestamp}

**Escalation Reason:**
Previous attempts did not resolve. Escalating to ThinkHard mode for deeper analysis.

**Hypothesis:**
{Refined hypothesis based on Iterations 1-2}

**Investigation:**
- {Deeper investigation steps}
- {Cross-file analysis}
- {Edge case checks}

**Fix Attempted:**
```{language}
{Code change}
```

**Result:**
- ❌ FAILED | ✅ RESOLVED | ⏭️ PARTIAL

**Learning:**
{What we learned}

---

## Iteration 5 (Tier 3: UltraThink)

**Escalation Reason:**
ThinkHard attempts unsuccessful. Escalating to UltraThink for comprehensive analysis.

{Same structure}

---

## Iteration 6+ (Tier 4: Human Review)

**Escalation Reason:**
Multiple UltraThink attempts unsuccessful. Recommending human developer review.

**Summary for Handoff:**
- **Attempts:** 6 iterations across 3 tiers
- **Hypotheses tested:** {list}
- **Fixes attempted:** {summary}
- **Current understanding:** {what we know}
- **Open questions:** {what we don't know}

**Recommended Next Steps:**
1. {Action 1}
2. {Action 2}

---

## Resolution

**Final Status:** RESOLVED | ESCALATED | ABANDONED

**Successful Fix:**
```{language}
{Final working fix}
```

**Root Cause:**
{Ultimate cause of the issue}

**Lessons Learned:**
- {Lesson 1}
- {Lesson 2}

**Prevention:**
{How to prevent this issue in future}
```

## Field Descriptions

### Issue Summary Fields

- **Description:** Clear, concise explanation of what's broken or not working
- **Error Message:** Primary error message, stack trace, or symptoms
- **Affected Component:** Which screen, module, or service is impacted
- **Severity:** Impact level to prioritize debugging effort

### Iteration Fields

- **Timestamp:** When this iteration started
- **Hypothesis:** What you think is causing the issue based on available evidence
- **Investigation:** Specific actions taken to gather information (file reads, test runs, log checks)
- **Fix Attempted:** Actual code or configuration changes made
- **Result:** Outcome (FAILED/RESOLVED/PARTIAL)
- **Learning:** What this attempt revealed about the problem

### Escalation Triggers

- **Tier 1 → Tier 2:** After 2 failed standard attempts
- **Tier 2 → Tier 3:** After 4 total failed attempts (2 ThinkHard)
- **Tier 3 → Tier 4:** After 6 total failed attempts (2 UltraThink)

### Resolution Fields

- **Final Status:** How the debug session ended
- **Successful Fix:** The fix that ultimately resolved the issue
- **Root Cause:** Fundamental reason the issue occurred
- **Lessons Learned:** Key takeaways for preventing similar issues
- **Prevention:** Specific steps to avoid this in future

## Usage Notes

1. **One log per issue:** Each unique issue gets its own log file
2. **Chronological iterations:** Add iterations sequentially, don't skip numbers
3. **Complete all fields:** Even if "N/A", document why
4. **Link to commits:** Reference git commit hashes for fix attempts
5. **Archive resolved logs:** Move to `archive/` after 7 days
