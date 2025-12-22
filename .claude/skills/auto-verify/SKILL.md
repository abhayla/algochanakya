---
name: auto-verify
description: Automatically test code changes, capture screenshots, analyze results, and iterate until verified working. Use after making code changes to ensure they work correctly.
---

# Auto-Verify Skill

Automated verification loop for code changes with visual confirmation.

## When to Use

- After making code changes to fix a bug
- After implementing a new feature
- After refactoring existing code
- When you need visual confirmation that changes work

## Workflow

### Step 0: Cleanup Old Screenshots

Before starting, clean up screenshots older than 24 hours:

```powershell
# Create folder if not exists
if (-not (Test-Path "screenshots/verification")) {
    New-Item -ItemType Directory -Path "screenshots/verification" -Force
}

# Delete files older than 24 hours
Get-ChildItem "screenshots/verification" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddHours(-24) } |
    Remove-Item -Force
```

### Step 1: Identify Changed Files

List files modified in this session or use git to identify changes:

```bash
git diff --name-only HEAD
git diff --name-only --cached
```

### Step 2: Detect Affected Feature

Use `docs/feature-registry.yaml` to map changed files to features:

1. Read `docs/feature-registry.yaml`
2. Match changed file paths against `auto_detect_patterns`
3. Identify the feature (e.g., `positions`, `autopilot`, `watchlist`)
4. Get the test path from `features.{feature}.tests`

**If uncertain:** Ask user which feature/tests to run.

### Step 3: Run Tests

Execute the appropriate test command:

| Feature | Test Command |
|---------|--------------|
| positions | `npm run test:specs:positions` |
| watchlist | `npm run test:specs:watchlist` |
| optionchain | `npm run test:specs:optionchain` |
| strategy-builder | `npm run test:specs:strategy` |
| strategy-library | `npm run test:specs:strategylibrary` |
| autopilot | `npm run test:specs:autopilot` |
| dashboard | `npm run test:specs:dashboard` |
| login | `npm run test:specs:login` |

For specific test files:
```bash
npx playwright test tests/e2e/specs/{feature}/{specific-file}.spec.js
```

### Step 4: Capture Screenshots

After tests complete (pass or fail), capture screenshots of affected screens:

1. Analyze test file to identify which views/modals/states are tested
2. Run the verification screenshot script:

```bash
node tests/e2e/utils/verification-screenshot.js --feature={feature} --screen={screen}
```

Screenshot naming convention:
- `{feature}_{screen}_{state}_{YYYY-MM-DD_HHmmss}.png`
- Example: `positions_exit-modal_open_2025-12-22_143052.png`

### Step 5: Analyze Results

#### 5a. Analyze Test Output
- Check for passed/failed tests
- Read error messages for failed tests
- Identify the root cause

#### 5b. Analyze Screenshots
Use the Read tool to view screenshots and verify:

1. **Layout correctness** - Elements positioned correctly?
2. **Content accuracy** - Data displayed correctly?
3. **State consistency** - UI reflects expected state?
4. **No visual regressions** - No unintended changes?

See `references/screenshot-analysis-guide.md` for detailed checklist.

### Step 6: Decision Point

Based on analysis:

| Outcome | Action |
|---------|--------|
| Tests pass + Screenshots look correct | **SUCCESS** - Verification complete |
| Tests fail | Analyze error, fix code, go to Step 3 |
| Tests pass but screenshots show issues | Fix code, go to Step 3 |
| Reached 5 attempts | **STOP** - Ask user for guidance |

### Step 7: Fix and Iterate

If issues found:
1. Identify the root cause
2. **Check approval requirements** (see below)
3. Make the fix
4. Increment attempt counter
5. Return to Step 3

## Approval Checkpoints

**STOP and ask user approval before:**

1. **Using mock/dummy data** instead of real API data
2. **Making assumptions** about intended behavior
3. **Modifying test assertions** to match new behavior
4. **Modifying shared utilities** (helpers, fixtures, POMs)
5. **Stopping after 5 attempts** - ask for guidance
6. **Using workarounds** instead of proper fixes

## Attempt Tracking

Track attempts in your responses:
```
[Attempt 1/5] Running tests for positions feature...
[Attempt 2/5] Previous fix didn't work. Trying alternative approach...
```

After 5 failed attempts, STOP and ask:
> "I've attempted 5 fixes but the issue persists. Here's what I've tried:
> 1. [First approach]
> 2. [Second approach]
> ...
> Would you like me to continue with a different strategy, or would you prefer to investigate manually?"

## References

- `references/workflow-checklist.md` - Quick checklist version
- `references/screenshot-analysis-guide.md` - How to analyze screenshots
- `references/approval-scenarios.md` - Detailed approval scenarios
