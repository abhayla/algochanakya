---
name: fix-issue
description: Fetch, understand, and fix a GitHub issue with full workflow enforcement. Accepts issue number or GitHub URL. Orchestrates implement, fix-loop, and post-fix-pipeline. Creates conventional commit with Fix #NNN reference. Use when user provides a GitHub issue number or URL.
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: workflow
---

# fix-issue - Fix GitHub Issue

**Purpose:** Fetch, understand, and fix a GitHub issue with full workflow enforcement.

**When to use:** User provides GitHub issue number or URL.

**Integration:** Uses implement workflow (7 steps), invokes fix-loop on test failures.

---

## Algorithm

### Step 1: Fetch Issue

```bash
# Accept issue number or full URL
# Examples:
#   Skill("fix-issue", args="123")
#   Skill("fix-issue", args="https://github.com/{owner}/{repo}/issues/123")

if is_url(ARGUMENTS):  # [PLANNED - pseudocode]
    issue_number = extract_number_from_url(ARGUMENTS)  # [PLANNED - pseudocode]
else:
    issue_number = ARGUMENTS

# Fetch issue details via gh CLI
gh issue view $issue_number
```

**Parse issue content:**
- Title
- Description
- Labels (bug, enhancement, documentation, etc.)
- Comments (for additional context)
- Linked PRs (if any)

---

### Step 2: Understand & Explore

**Understand the issue:**
```
Issue #$issue_number: $title

Description:
$description

Labels: $labels

My understanding:
[State understanding in 2-3 sentences]
```

**Explore codebase:**
- Use `Grep` to find relevant code sections
- Use `Glob` to find related files
- Read existing implementations

**Check documentation:**
- [Developer Quick Reference](docs/DEVELOPER-QUICK-REFERENCE.md)
- [Implementation Checklist](docs/IMPLEMENTATION-CHECKLIST.md)
- [Broker Abstraction](docs/architecture/broker-abstraction.md) (if broker-related)
- [Feature Registry](docs/feature-registry.yaml)

---

### Step 3: Plan Implementation

**For complex issues, invoke planner-researcher:**
```python
if is_complex_issue(issue):  # [PLANNED - pseudocode]
    plan = Task(
        subagent_type="general-purpose",
        model="opus",
        prompt=f"""You are a Planner-Researcher Agent for AlgoChanakya.
        Follow the instructions in .claude/agents/planner-researcher.md.

        Read .claude/agents/planner-researcher.md first, then:

        Design implementation plan for GitHub issue #{issue_number}:

        Title: {title}
        Description: {description}

        Context: {relevant_codebase_context}

        Provide:
        1. Architecture design
        2. Phase breakdown
        3. Testing strategy
        4. Risks and mitigations
        """
    )
```

**For simple issues, proceed directly to implementation.**

---

### Step 4: Implement

**Invoke implement workflow:**
```
Skill("implement")
```

This triggers the full 7-step workflow:
1. Requirements/Clarification (already done in Step 2)
2. Write/Update Tests
3. Implement Feature
4. Run Targeted Tests
5. Fix Loop (if tests fail)
6. Visual Verification
7. Post-Fix Pipeline

**Hooks enforce:**
- Cannot write code before tests
- Cannot commit before all steps complete
- Must invoke post-fix-pipeline before commit

---

### Step 5: Verification Tests

**Run tests for affected areas:**
```python
# Identify affected test layers based on changed files
changed_files = state['steps']['step3_implement']['filesChanged']

layers_to_test = set()
for file in changed_files:
    if file.startswith('backend/'):
        layers_to_test.add('backend')
    if file.startswith('frontend/'):
        layers_to_test.add('frontend')
    if file.endswith('.spec.js') or file.endswith('.spec.ts'):
        layers_to_test.add('e2e')

# Run targeted tests
for layer in layers_to_test:
    Bash(command=f"/run-tests {layer}")
```

---

### Step 6: Fix Loop (if tests fail)

**If any tests fail:**
```
Skill("fix-loop")
```

**Hooks automatically:**
- Record test failures
- Track fix iterations
- Require fix-loop before commit

---

### Step 7: Screenshots (if UI change)

**For UI changes, capture screenshots:**
```python
if has_frontend_changes(changed_files):
    print("📸 Capturing screenshots for UI changes...")

    # Navigate to affected screen
    mcp__playwright__browser_navigate(url=f"http://localhost:5173/{screen_path}")

    # Before (if applicable)
    # After
    mcp__playwright__browser_take_screenshot(
        filename=f"issue-{issue_number}-after.png",
        fullPage=True
    )
```

---

### Step 8: Post-Fix Pipeline

**Always invoke post-fix-pipeline:**
```
Skill("post-fix-pipeline")
```

**Post-fix-pipeline does:**
- Regression tests
- Full test suite
- Documentation update
- Git commit with issue reference

---

### Step 9: Commit Message

**Git-manager creates commit with issue reference:**
```
fix({scope}): {short_description}

{detailed_changes}

Fix #{issue_number}

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Example:**
```
fix(positions): handle empty position list gracefully

- Add null check in PositionsList.vue
- Display "No positions" message instead of error
- Add E2E test for empty positions scenario

Fix #123

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Issue Type Handling

### Bug Fix

**Labels:** `bug`, `defect`

**Workflow:**
1. Reproduce the bug (write failing test)
2. Identify root cause (use debugger agent if needed)
3. Fix the code
4. Verify test passes
5. Regression tests

**Commit type:** `fix`

---

### Enhancement

**Labels:** `enhancement`, `feature`

**Workflow:**
1. Clarify requirements (if ambiguous)
2. Design solution (use planner-researcher for complex)
3. Write tests first (TDD)
4. Implement feature
5. Visual verification

**Commit type:** `feat`

---

### Documentation

**Labels:** `documentation`, `docs`

**Workflow:**
1. Identify docs to update
2. Update content
3. Verify links and formatting
4. No tests required (unless code examples)

**Commit type:** `docs`

**Skip most workflow steps** (no tests, no code)

---

### Refactoring

**Labels:** `refactor`, `tech-debt`

**Workflow:**
1. Ensure existing tests cover behavior
2. Refactor code
3. Verify all tests still pass (no behavior change)
4. Check for performance improvement (if applicable)

**Commit type:** `refactor`

---

## GitHub Integration

### Link PR to Issue

**After commit, optionally create PR:**
```bash
# Create branch
git checkout -b fix/issue-$issue_number

# Commit (already done by post-fix-pipeline)

# Push
git push -u origin fix/issue-$issue_number

# Create PR
gh pr create \
    --title "Fix #$issue_number: $issue_title" \
    --body "Fixes #$issue_number" \
    --base main
```

**PR will auto-link to issue via "Fixes #123" in description.**

---

### Close Issue

**When PR is merged, issue auto-closes** (GitHub automation).

**Alternatively, close manually:**
```bash
gh issue close $issue_number --comment "Fixed in commit $commit_sha"
```

---

## Output Format

```
╔══════════════════════════════════════════════════════════╗
║          Fix Issue #123 - Complete                       ║
╚══════════════════════════════════════════════════════════╝

Issue: Handle empty position list gracefully
Type: Bug fix
Labels: bug, frontend

┌──────────────────────────────────────────────────────────┐
│ Implementation Summary                                   │
├──────────────────────────────────────────────────────────┤
│ Files changed: 3                                         │
│   - frontend/src/components/positions/PositionsList.vue  │
│   - tests/e2e/specs/positions/positions.edge.spec.js     │
│   - docs/features/positions/CHANGELOG.md                 │
│                                                          │
│ Tests added: 1 E2E test                                  │
│ Tests passed: All (118/118 E2E, 45/45 backend, 21/21 frontend) │
│                                                          │
│ Fix iterations: 0 (tests passed on first run)           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Commit Details                                           │
├──────────────────────────────────────────────────────────┤
│ SHA: a1b2c3d4                                            │
│ Type: fix                                                │
│ Scope: positions                                         │
│ Message: handle empty position list gracefully          │
│                                                          │
│ References: Fix #123                                     │
└──────────────────────────────────────────────────────────┘

Next steps:
1. Push to remote:
   git push origin main

2. Or create PR:
   git checkout -b fix/issue-123
   git push -u origin fix/issue-123
   gh pr create --title "Fix #123: Handle empty position list gracefully"

3. Issue will auto-close when commit/PR is merged.
```

---

## Skills Called

| Skill | When | Purpose |
|-------|------|---------|
| `implement` | Step 4 | 7-step workflow |
| `fix-loop` | If tests fail | Auto-fix test failures |
| `post-fix-pipeline` | Step 8 | Final verification and commit |

---

## Agents Called

| Agent | When | Purpose |
|-------|------|---------|
| `planner-researcher` | Complex issues | Design implementation plan |
| `debugger` | Bug fixes (via fix-loop) | Root cause analysis |
| `code-reviewer` | Every fix (via fix-loop) | Validate compliance |
| `git-manager` | Step 8 (via post-fix-pipeline) | Create commit |

---

## Example Usage

```bash
# By issue number
/fix-issue 123

# By full URL
/fix-issue https://github.com/{owner}/{repo}/issues/123
```

---

## Success Criteria

✅ Issue fetched and understood
✅ Implementation follows 7-step workflow
✅ All tests pass
✅ Commit created with issue reference (Fix #123)
✅ Documentation updated
✅ Ready to push or create PR

---

## Exit Codes

- **0:** Issue fixed successfully, commit created
- **1:** Issue fix failed (tests still failing after max attempts)
