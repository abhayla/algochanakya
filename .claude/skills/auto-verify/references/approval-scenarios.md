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

## Scenario 5: Stopping After 5 Attempts

**When:** 5 fix attempts haven't resolved the issue

**Ask:**
> "I've attempted 5 fixes but the issue persists.
>
> What I've tried:
> 1. [Approach 1] - Result: [outcome]
> 2. [Approach 2] - Result: [outcome]
> 3. [Approach 3] - Result: [outcome]
> 4. [Approach 4] - Result: [outcome]
> 5. [Approach 5] - Result: [outcome]
>
> Options:
> 1. Continue with a different strategy
> 2. Investigate the root cause together
> 3. Skip this fix for now
>
> What would you like to do?"

## Scenario 6: Using Workarounds

**When:** Proper fix is complex, workaround is available

**Ask:**
> "I can fix this issue with:
>
> **Proper fix:** [description] - More complex but correct solution
> **Workaround:** [description] - Quick fix but may cause [drawback]
>
> Which approach should I use?"
