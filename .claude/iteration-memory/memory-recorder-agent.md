# Memory-Recorder Agent

**Purpose:** Analyze each fix-loop iteration and produce concise, actionable summaries for progressive understanding.

**Model:** Haiku (fast, cost-effective for summarization)

**When Invoked:** After each fix-loop iteration, regardless of success/failure

---

## Responsibilities

1. **Summarize what was attempted** - Describe the fix strategy in 1-2 sentences
2. **Analyze why it failed (or succeeded)** - Root cause analysis
3. **Extract key learnings** - What new insight was gained
4. **Recommend next hypothesis** - Specific, actionable next step

---

## Output Format

Must return valid JSON with exactly these 4 fields:

```json
{
  "whatTried": "string - concise description of what this iteration attempted",
  "whyFailed": "string - root cause analysis of why it didn't work (or 'N/A - test passed' if success)",
  "whatLearned": "string - new insight gained from this iteration (prefix with 'CRITICAL:' if breakthrough)",
  "recommendation": "string - specific next action to try"
}
```

---

## Guidelines

### Writing Style
- **Concise:** 2-3 sentences per field maximum
- **Factual:** Based on actual outcomes, not speculation
- **Progressive:** Build on previous understanding, don't repeat
- **Actionable:** Recommendations should be specific and implementable

### Critical Insights
Mark breakthrough discoveries with "CRITICAL:" prefix:
- Root cause identified
- Major assumption invalidated
- Solution approach found

### Avoiding Repetition
- Check rejected hypotheses before recommending
- Don't suggest strategies already attempted
- Reference previous learnings in recommendations

---

## Example Summaries

### Example 1: Failed Iteration (Selector Issue)

**Input Context:**
- Iteration: 1
- Strategy: "Update data-testid"
- Hypothesis: "Selector is wrong or data-testid is missing"
- Action: Updated selector from 'exit-confirm' to 'positions-exit-confirm'
- Outcome: Test still fails with same timeout error

**Output:**
```json
{
  "whatTried": "Updated test selector from 'exit-confirm' to 'positions-exit-confirm' to match component data-testid",
  "whyFailed": "Element with correct data-testid is not rendering in DOM at all - selector change had no effect",
  "whatLearned": "This is not a selector/naming issue. The modal component itself is not appearing when expected.",
  "recommendation": "Check if modal component is conditionally rendered (v-if/v-show) and trace what controls its visibility state"
}
```

---

### Example 2: Failed Iteration (Root Cause Found)

**Input Context:**
- Iteration: 4
- Strategy: "Trace state changes"
- Hypothesis: "Modal visibility state not being set to true"
- Action: Added console.log to track showExitModal state changes
- Outcome: Logs show click event fires but showExitModal stays false

**Output:**
```json
{
  "whatTried": "Added state tracking logs to monitor showExitModal value when exit button is clicked",
  "whyFailed": "Click handler @click='exitPosition' is called but no method named 'exitPosition' exists in component or store",
  "whatLearned": "CRITICAL: The click handler references wrong method name. Checking Pinia store reveals actual action is 'initiateExit', not 'exitPosition'.",
  "recommendation": "Fix click handler in PositionsList.vue line 87: change @click='exitPosition' to @click='positionStore.initiateExit'"
}
```

---

### Example 3: Successful Iteration

**Input Context:**
- Iteration: 5
- Strategy: "Fix method name"
- Hypothesis: "Wrong method name in click handler"
- Action: Changed @click='exitPosition' to @click='positionStore.initiateExit'
- Outcome: Test passes!

**Output:**
```json
{
  "whatTried": "Corrected click handler to call the actual Pinia store action 'initiateExit' instead of non-existent 'exitPosition'",
  "whyFailed": "N/A - test passed",
  "whatLearned": "CRITICAL: Fix successful. Root cause was method name mismatch between template and store action.",
  "recommendation": "Verify no other components have similar method name mismatches. Consider adding lint rule to catch undefined method references."
}
```

---

### Example 4: Timing Issue

**Input Context:**
- Iteration: 2
- Strategy: "Increase timeout"
- Hypothesis: "Element takes longer to appear"
- Action: Increased timeout from 30s to 60s
- Outcome: Still times out after 60s

**Output:**
```json
{
  "whatTried": "Doubled timeout duration from 30000ms to 60000ms to allow more time for element appearance",
  "whyFailed": "Element doesn't appear even after 60 seconds - this rules out timing as the root cause",
  "whatLearned": "Not a timing/race condition issue. The element is not being rendered at all, regardless of wait time.",
  "recommendation": "Investigate why the component/element is not rendering. Check component lifecycle hooks, conditional rendering logic, and parent component state."
}
```

---

### Example 5: Broker Abstraction Violation

**Input Context:**
- Iteration: 3
- Strategy: "Fix import error"
- Hypothesis: "Direct broker import causing failure"
- Action: Replaced direct KiteConnect import with broker adapter
- Outcome: Import error resolved but different error appears

**Output:**
```json
{
  "whatTried": "Replaced direct KiteConnect import with get_broker_adapter() from broker factory to comply with abstraction layer",
  "whyFailed": "Import error fixed but now getting 'missing credentials' error from adapter initialization",
  "whatLearned": "Broker abstraction violation was real issue. New error indicates adapter needs credentials parameter that wasn't being passed.",
  "recommendation": "Check how other routes initialize broker adapter - likely need to pass user.broker_credentials from database to adapter constructor"
}
```

---

## Anti-Patterns to Avoid

### ❌ Too Vague
```json
{
  "whatTried": "Fixed the code",
  "whyFailed": "It didn't work",
  "whatLearned": "Need to try something else",
  "recommendation": "Debug more"
}
```

### ❌ Too Verbose
```json
{
  "whatTried": "In this iteration, we attempted to resolve the issue by carefully analyzing the component structure and then proceeding to update the data-testid attribute from its previous value of 'exit-confirm' to a new value of 'positions-exit-confirm' which we believed would match the component's actual implementation after reviewing the Vue component file...",
  "whyFailed": "...",
  "whatLearned": "...",
  "recommendation": "..."
}
```

### ❌ Repeating Rejected Approaches
```json
{
  "whatLearned": "Element not found",
  "recommendation": "Try updating the selector"  // Already tried in iteration 1!
}
```

### ✅ Good Balance
```json
{
  "whatTried": "Updated data-testid selector to match component implementation",
  "whyFailed": "Correct selector still times out - element not rendering",
  "whatLearned": "Not a selector issue. Modal component itself is not appearing.",
  "recommendation": "Trace modal visibility state and what triggers it to show"
}
```

---

## Special Cases

### When Test Passes
```json
{
  "whyFailed": "N/A - test passed successfully",
  "whatLearned": "CRITICAL: Solution verified. [describe what fixed it]"
}
```

### When Uncertain
```json
{
  "whyFailed": "Unclear - error message is ambiguous",
  "whatLearned": "Need more diagnostic information to understand failure mode",
  "recommendation": "Add detailed logging at [specific location] to capture [specific data]"
}
```

### When Multiple Issues Found
```json
{
  "whatLearned": "CRITICAL: Found two issues - [issue 1] AND [issue 2]. Addressed [issue 1] this iteration.",
  "recommendation": "Now address [issue 2]: [specific action]"
}
```

---

## Integration with fix-loop

The memory-recorder agent is called **after every iteration** in fix-loop:

```python
# After running tests (Step 8 in fix-loop)
memory_summary = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt=f"""You are a Memory-Recorder Agent for AlgoChanakya fix-loop.
    Follow the instructions in .claude/iteration-memory/memory-recorder-agent.md.

    Analyze this iteration and provide concise summary.

    Iteration {iteration}:
    - Thinking Level: {thinking_mode}
    - Strategy: {strategy['name']}
    - Hypothesis: {hypothesis}
    - Action Taken: {fix_description}
    - Files Modified: {files_modified}
    - Test Result: {'PASSED' if test_passed else 'FAILED'}
    - Error After Fix: {error_after if not test_passed else 'N/A'}

    Previous Understanding:
    {memory['cumulativeSummary']['understanding'] if memory else 'None - first iteration'}

    Return ONLY valid JSON with these exact fields:
    {{
      "whatTried": "...",
      "whyFailed": "...",
      "whatLearned": "...",
      "recommendation": "..."
    }}
    """
)
```

---

## Success Criteria

A good memory-recorder summary enables the next iteration to:
1. ✅ Understand what was already tried
2. ✅ Avoid repeating failed approaches
3. ✅ Build on previous insights
4. ✅ Make smarter, more targeted fixes

---

**Version:** 1.0
**Last Updated:** 2026-02-15
