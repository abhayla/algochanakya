# Approval Scenarios

## Scenario 1: Using Mock/Dummy Data

**When:** Tests need specific data that doesn't exist in current state

**Ask:**
> "The test requires [specific data] which isn't available. I can:
> 1. Use mock data for testing (may not catch real API issues)
> 2. Wait for you to set up the required data
> Which approach would you prefer?"

## Scenario 2: Making Assumptions

**When:** Intended behavior is unclear from code/tests

**Ask:**
> "I'm not certain about the expected behavior for [scenario].
> Based on the code, it could be:
> - Option A: [description]
> - Option B: [description]
> Which is correct?"

## Scenario 3: Modifying Test Assertions

**When:** Test assertion seems wrong, not the code

**Ask:**
> "The test expects [current assertion] but the code produces [actual result].
> I can either:
> 1. Change the code to match the test assertion
> 2. Update the test assertion to match the new behavior
> The new behavior appears [correct/incorrect] because [reason].
> How should I proceed?"

## Scenario 4: Modifying Shared Utilities

**When:** Fix requires changes to helpers/fixtures/POMs

**Ask:**
> "To fix this issue, I need to modify [shared file] which is used by [N] other tests.
> The change is: [description]
> This could affect: [list of affected areas]
> Should I proceed with this change?"

## Scenario 5: Hit Stuck Condition (Learning Engine)

**When:** Any of these stuck conditions are met:
- Same fingerprinted error appears 3x with different strategies all failing
- All strategies exhausted (all scores < 0.1)
- 20 total attempts in session (safety valve)
- Fix requires modifying files outside current feature scope
- Completely unknown error type

**Ask:**
> "I'm stuck on this error. Here's what I know:
>
> **Error:** {error_type} - {error_message_summary}
> **Fingerprint:** {fingerprint} (seen {occurrence_count} times in knowledge base)
> **File:** {file_path}
>
> **Knowledge Base Context:**
> - Total patterns: {total_patterns}
> - This error pattern: {known/unknown}
> - Best available strategy: {strategy_name} (score: {score})
> - Threshold for trying: 0.3
>
> **Strategies attempted:**
> 1. [{score}] {strategy_name} - {outcome}
> 2. [{score}] {strategy_name} - {outcome}
> ...
>
> **Stuck Condition:** {specific_condition_met}
>
> Would you like me to:
> 1. Try a different heuristic approach (describe what)
> 2. Record this as a new learned pattern
> 3. Skip and move to other verification tasks"

## Scenario 6: Using Workarounds

**When:** Proper fix is complex, workaround is available

**Ask:**
> "I can fix this issue with:
>
> **Proper fix:** [description] - More complex but correct solution
> **Workaround:** [description] - Quick fix but may cause [drawback]
>
> Which approach should I use?"
