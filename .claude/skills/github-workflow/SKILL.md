---
name: github-workflow
description: GitHub-based autonomous workflow orchestration. Creates issues from plan docs, picks next unblocked issue, creates branches, links PRs, and tracks progress via milestones. Use when managing multi-session autonomous implementation via GitHub Issues. Triggers on 'github-workflow', 'next issue', 'plan issues', or 'workflow status'.
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: workflow
---

# github-workflow — GitHub Issue Orchestration

**Purpose:** Manage autonomous multi-session implementation via GitHub Issues. Bridges the gap between session management (`start-session`/`save-session`) and implementation (`implement`/`fix-loop`).

**When to use:**
- Setting up a project plan as GitHub Issues (`plan`)
- Starting a session — pick next work item (`next`)
- Checkpointing progress mid-session (`progress`)
- Completing work — push, PR, close (`done`)
- Handling blockers — label, skip, pick next (`blocked`)
- Reviewing overall status (`status`)

**When NOT to use:**
- Reactive bug fixes from user-reported issues → use `/fix-issue` instead
- One-off tasks without a plan → use `/implement` directly
- Pure research or exploration → no issue needed

**Distinction from `/fix-issue`:**
- `/fix-issue` = reactive, user-driven, single issue, typically bug fixes
- `/github-workflow` = proactive, autonomous, multi-session orchestration, planned features

---

## Prerequisites

Before first use, verify GitHub CLI is authenticated:

```bash
gh auth status
```

If not authenticated, stop and inform the user:
```
GitHub CLI is not authenticated. Please run:
  gh auth login
```

---

## Commands

### Overview

| Command | Purpose | Typical Trigger |
|---------|---------|-----------------|
| `plan <doc-path>` | Create issues + milestones from plan doc | One-time project setup |
| `next [--issue N]` | Pick next unblocked issue, create branch | Session start |
| `progress [message]` | Comment on current issue with status | Mid-session checkpoint |
| `done` | Push, create PR, label for review | Session end |
| `blocked [reason]` | Label blocked, switch to next issue | When stuck |
| `status` | Show milestone progress dashboard | Anytime |

---

## Command: `plan`

**Usage:** `/github-workflow plan docs/guides/AUTONOMOUS-IMPLEMENTATION-PLAN.md`

**Purpose:** Parse a plan document and create GitHub Issues + Milestones.

### Plan Document Format

The parser expects this markdown structure:

```markdown
### PHASE NAME (S{NN}–S{MM})

#### S{NN}: Issue Title

**Pre-conditions:** S{XX} + S{YY} complete (or "None")
**Estimated time:** X-Y hours

**Deliverables:**
- [ ] Deliverable item 1
- [ ] Deliverable item 2

**Key reference:** [Doc Name](link) + `/skill-name`

**Autonomous flow:**
...

**Manual intervention:** None expected.
<!-- OR -->
**Manual intervention:**
- ⚠️ Add credentials to `.env`
```

### Algorithm

```
Step 1: Verify GitHub auth
  gh auth status
  → FAIL: Stop, inform user to run `gh auth login`

Step 2: Detect repository
  gh repo view --json nameWithOwner,defaultBranchRef
  → Extract: owner/repo, default branch (main/develop)

Step 3: Read plan document
  Read the file at <doc-path>

Step 4: Parse phases → milestones
  Regex: ### {PHASE_NAME} \(S(\d+)[–-]S(\d+)\)
  For each phase:
    title = phase name
    description = "Sessions S{start}–S{end}"

Step 5: Parse sessions → issues
  Regex: #### S(\d+): (.+)
  For each session, extract:
    - title: "S{NN}: {text}" (from H4 header)
    - deliverables: lines matching "- [ ] " under **Deliverables:**
    - pre_conditions: parse "S{NN}" references from **Pre-conditions:**
    - estimated_time: text from **Estimated time:**
    - references: text from **Key reference:**
    - manual_intervention: text from **Manual intervention:**
    - autonomous_flow: text from **Autonomous flow:**

Step 6: Create milestones (idempotent)
  For each phase:
    # Check if milestone already exists
    existing=$(gh api repos/{owner}/{repo}/milestones --jq '.[].title')
    if title NOT in existing:
      gh api repos/{owner}/{repo}/milestones -f title="{title}" -f description="{desc}"

Step 7: Create labels (idempotent)
  Required labels (create if missing):
    - "autonomous"     (color: 0E8A16, desc: "Autonomous implementation — no user needed")
    - "needs-user"     (color: D93F0B, desc: "Requires manual user intervention")
    - "in-progress"    (color: FBCA04, desc: "Currently being implemented")
    - "blocked"        (color: B60205, desc: "Blocked by dependency or external factor")
    - "pending-review" (color: 1D76DB, desc: "PR created, awaiting review/merge")

  For each label:
    gh label create "{name}" --color "{color}" --description "{desc}" --force 2>/dev/null || true

Step 8: Create issues (idempotent — two-pass)

  Pass 1: Create all issues, record session_id → issue_number mapping
    For each session:
      # Check if issue already exists (match by title prefix "S{NN}:")
      existing=$(gh issue list --search "S{NN}:" --json number,title --jq '.[0].number')
      if existing:
        mapping[S{NN}] = existing
        skip creation
      else:
        # Determine labels
        labels = ["autonomous"]
        if manual_intervention contains "⚠️":
          labels += ["needs-user"]
        if estimated_time:
          labels += ["estimate:{time}"]

        # Create issue with structured body
        gh issue create \
          --title "S{NN}: {title}" \
          --body "$(cat <<'EOF'
        ## Deliverables
        {deliverables checkboxes}

        ## References
        {key references}

        ## Autonomous Flow
        {autonomous flow text}

        ## Manual Intervention
        {manual intervention text}

        ---
        **Depends on:** (added in Pass 2)
        **Estimated time:** {time}
        **Session:** S{NN}
        EOF
        )" \
          --label "{labels}" \
          --milestone "{phase_milestone}"

        mapping[S{NN}] = new_issue_number

  Pass 2: Add dependency references
    For each session with pre_conditions:
      Parse "S{XX}" references → look up mapping[S{XX}] → issue numbers
      # Update issue body to include "**Depends on:** #{num1}, #{num2}"
      gh issue edit {issue_number} --body "{updated_body_with_depends}"
      # Also add a comment for visibility
      gh issue comment {issue_number} --body "**Dependencies:** #{dep1}, #{dep2}"

Step 9: Output summary
  "Created {N} issues across {M} milestones.
   Issues: #{first}–#{last}
   Milestones: {list}
   Ready to start: /github-workflow next"
```

### Error Handling

| Error | Action |
|-------|--------|
| Plan doc not found | Stop with clear error message |
| No sessions parsed | Warn: "No sessions found. Check format (expects `#### S{NN}: Title`)" |
| GitHub API error | Show error, suggest `gh auth status` |
| Milestone creation fails | Continue — milestones are optional metadata |
| Issue creation fails | Show error, skip, continue with remaining issues |
| Duplicate detected | Skip with message: "S{NN} already exists as #{num}, skipping" |

---

## Command: `next`

**Usage:** `/github-workflow next` or `/github-workflow next --issue 42`

**Purpose:** Pick the next unblocked issue, create a branch, and load requirements.

### Algorithm

```
Step 1: Check for in-progress work

  # Check current git branch
  current_branch=$(git branch --show-current)

  # Case A: Already on a feature branch (feat/GH-{N}-*)
  if current_branch matches "feat/GH-(\d+)-":
    issue_number = extracted number
    issue_state = $(gh issue view {issue_number} --json state --jq '.state')
    if issue_state == "OPEN":
      # Resume in-progress issue
      Output: "Resuming #{issue_number}: {title} (branch already exists)"
      → Jump to Step 6 (load requirements)

  # Case B: Explicit issue requested (--issue N)
  if --issue flag provided:
    issue_number = provided number
    → Jump to Step 3

  # Case C: Check GitHub for any in-progress issue
  in_progress=$(gh issue list --label "in-progress" --json number,title --jq '.[0]')
  if in_progress exists:
    issue_number = in_progress.number
    # Check if branch exists locally
    if branch "feat/GH-{issue_number}-*" exists:
      git checkout feat/GH-{issue_number}-*
      Output: "Resuming #{issue_number}: {title}"
      → Jump to Step 6
    else:
      # Branch was lost (e.g., new clone). Recreate.
      → Jump to Step 4

Step 2: Find next unblocked issue

  # Fetch all open issues
  issues=$(gh issue list --state open --json number,title,body,labels,milestone)

  # Filter: exclude 'blocked', exclude 'needs-user', exclude 'in-progress', exclude 'pending-review'
  candidates = issues where labels NOT contain any of [blocked, needs-user, in-progress, pending-review]

  # Check dependencies for each candidate
  for each candidate:
    Parse "**Depends on:** #X, #Y" from body
    For each dependency #X:
      dep_state = $(gh issue view X --json state --jq '.state')
      if dep_state != "CLOSED":
        mark candidate as blocked (skip)

  # Sort remaining by: milestone order → issue number (ascending)
  # Pick first unblocked candidate
  if no candidates:
    Output: "No unblocked issues available.
             Blocked issues: {list with reasons}
             Use /github-workflow status for details."
    → STOP

  issue_number = first candidate

Step 3: Verify issue is actionable

  # Fetch full issue details
  issue = $(gh issue view {issue_number} --json number,title,body,labels,milestone)

  # Check for manual intervention requirements
  if body contains "⚠️":
    Output: "⚠️ Issue #{issue_number} requires manual intervention:
             {manual intervention section}
             Proceed anyway? Or /github-workflow next to skip."
    # Wait for user confirmation before proceeding

Step 4: Create branch

  # Ensure clean working state
  git_status=$(git status --porcelain)
  if git_status is not empty:
    # Uncommitted changes exist
    Output: "Uncommitted changes detected. Committing as WIP."
    git add -A
    git commit -m "WIP: work in progress before switching to #{issue_number}"

  # Switch to default branch first
  default_branch=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name')
  git checkout {default_branch}
  git pull origin {default_branch}

  # Generate branch name
  slug = slugify(issue.title)  # lowercase, hyphens, max 50 chars
  branch_name = "feat/GH-{issue_number}-{slug}"

  # Check if branch already exists
  if git branch --list "{branch_name}" is not empty:
    git checkout {branch_name}
    Output: "Checked out existing branch: {branch_name}"
  else:
    git checkout -b {branch_name}
    Output: "Created branch: {branch_name}"

Step 5: Update issue labels

  # Remove 'autonomous' label, add 'in-progress'
  gh issue edit {issue_number} --remove-label "autonomous" --add-label "in-progress"

  # Comment on issue
  gh issue comment {issue_number} --body "🤖 Starting autonomous implementation on branch \`{branch_name}\`"

Step 6: Load requirements

  # Parse issue body for deliverables
  deliverables = extract "## Deliverables" section (checkbox items)

  # Parse references
  references = extract "## References" section (doc links, skill names)

  # Read referenced documents
  for each reference link:
    Read the linked document

  # Output to Claude's context
  Output: "
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Working on: #{issue_number} — {title}
  Branch: {branch_name}
  Milestone: {milestone}
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Deliverables:
  {deliverables}

  References loaded: {list}

  Manual intervention: {notes or 'None'}

  → Proceeding with /implement workflow
  "

  # Hand off to /implement with deliverables as requirements
```

### Edge Cases

| Scenario | Handling |
|----------|----------|
| No open issues | Output "All issues closed. Project complete!" |
| All issues blocked | Output blocked list with dependency details |
| Branch name collision | Include issue number (unique) — collision impossible |
| Dirty working tree | WIP commit before switching |
| Already on issue branch | Resume instead of creating new |
| `--issue N` is blocked | Warn about dependency, ask to proceed or skip |
| Issue has `needs-user` label | Show ⚠️ items, wait for user confirmation |

---

## Command: `progress`

**Usage:** `/github-workflow progress` or `/github-workflow progress "Completed ticker adapter, starting tests"`

**Purpose:** Post a progress update comment on the current issue.

### Algorithm

```
Step 1: Identify current issue
  Parse issue number from branch name: feat/GH-{N}-*
  if not on a feature branch:
    Output: "Not on a feature branch. Nothing to update."
    → STOP

Step 2: Gather progress data

  # Git changes
  files_changed = $(git diff --name-only {default_branch}...HEAD)
  commit_count = $(git rev-list --count {default_branch}...HEAD)

  # Test status (if tests were run recently)
  # Check for recent test output in .claude/logs/

  # User-provided message
  custom_message = ARGUMENTS (if provided)

Step 3: Post comment on issue

  gh issue comment {issue_number} --body "$(cat <<'EOF'
  ### Progress Update

  {custom_message if provided}

  **Files changed:** {count}
  {file list, abbreviated if >10}

  **Commits:** {commit_count} on branch `{branch_name}`

  **Status:** In progress
  EOF
  )"

Step 4: Output confirmation
  "Progress update posted on #{issue_number}"
```

---

## Command: `done`

**Usage:** `/github-workflow done`

**Purpose:** Push branch, create PR linked to issue, label for review.

### Algorithm

```
Step 1: Identify current issue
  Parse issue number from branch name: feat/GH-{N}-*
  if not on a feature branch:
    Output: "Not on a feature branch. Nothing to complete."
    → STOP

Step 2: Pre-flight checks

  # Check for commits
  default_branch=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name')
  commits_ahead=$(git rev-list --count {default_branch}...HEAD)
  if commits_ahead == 0:
    Output: "No commits on this branch. Did you forget to implement? Use /implement first."
    → STOP

  # Check for uncommitted changes
  git_status=$(git status --porcelain)
  if git_status is not empty:
    Output: "Uncommitted changes detected. Commit first via /post-fix-pipeline or commit manually."
    → STOP

  # Verify deliverables completion (advisory, not blocking)
  issue_body = $(gh issue view {issue_number} --json body --jq '.body')
  total_checkboxes = count "- [ ]" and "- [x]" in Deliverables section
  checked = count "- [x]" in Deliverables section
  if checked < total_checkboxes:
    unchecked = total_checkboxes - checked
    Output: "⚠️ {unchecked}/{total_checkboxes} deliverables unchecked in issue.
             Proceeding anyway — update the issue manually if needed."

Step 3: Push branch

  git push -u origin {branch_name}

Step 4: Create Pull Request

  # Generate PR body from issue + git log
  pr_body = "$(cat <<'EOF'
  ## Summary
  Closes #{issue_number}

  {bullet summary from git log --oneline}

  ## Deliverables (from issue)
  {deliverables checklist copied from issue}

  ## Test Results
  {summary from last test run, if available}

  ---
  🤖 Generated with [Claude Code](https://claude.ai/claude-code)

  Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
  EOF
  )"

  # Create PR
  pr_url=$(gh pr create \
    --title "{issue_title}" \
    --body "{pr_body}" \
    --base {default_branch} \
    --head {branch_name})

  pr_number = extract from pr_url

Step 5: Update issue

  # Add 'pending-review' label, remove 'in-progress'
  gh issue edit {issue_number} --remove-label "in-progress" --add-label "pending-review"

  # Comment linking to PR
  gh issue comment {issue_number} --body "🤖 Implementation complete. PR #{pr_number} created.
  Issue will close automatically when PR is merged."

Step 6: Switch back to default branch

  git checkout {default_branch}
  git pull origin {default_branch}

Step 7: Output summary

  "
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ #{issue_number}: {title} — PR Created
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  PR: {pr_url}
  Branch: {branch_name}
  Commits: {commits_ahead}
  Files changed: {files_changed_count}

  Issue #{issue_number} labeled 'pending-review'.
  It will auto-close when PR #{pr_number} is merged.

  Next: /github-workflow next (to pick next issue)
  "
```

### Safety Rules

- **NEVER merge the PR** — only create it. Merging is the user's responsibility.
- **NEVER close the issue directly** — use "Closes #N" in PR body for auto-close on merge.
- **NEVER force-push** — standard `git push` only.
- Issue stays open until PR is actually merged. This ensures dependent issues don't unblock prematurely.

---

## Command: `blocked`

**Usage:** `/github-workflow blocked "Dhan API credentials not in .env"` or `/github-workflow blocked`

**Purpose:** Mark current issue as blocked and switch to next unblocked issue.

### Algorithm

```
Step 1: Identify current issue
  Parse from branch name: feat/GH-{N}-*

Step 2: Save work in progress

  # Check for uncommitted changes
  git_status=$(git status --porcelain)
  if git_status is not empty:
    git add -A
    git commit -m "$(cat <<'EOF'
    WIP: #{issue_number} — blocked

    {reason if provided}

    Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
    EOF
    )"
    git push -u origin {branch_name}

Step 3: Update issue

  # Label as blocked
  gh issue edit {issue_number} --remove-label "in-progress" --add-label "blocked"

  # Comment with reason
  reason = ARGUMENTS or "No reason provided"
  gh issue comment {issue_number} --body "🚫 **Blocked:** {reason}

  Work saved on branch \`{branch_name}\`.
  Switching to next available issue."

Step 4: Switch to next issue

  # Return to default branch
  default_branch=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name')
  git checkout {default_branch}

  # Auto-pick next unblocked issue
  Output: "Issue #{issue_number} blocked. Picking next..."
  → Run `next` command
```

---

## Command: `status`

**Usage:** `/github-workflow status`

**Purpose:** Show overall project progress across milestones.

### Algorithm

```
Step 1: Fetch milestones with progress

  milestones=$(gh api repos/{owner}/{repo}/milestones --jq '.[] | {title, open_issues, closed_issues}')

Step 2: Fetch issue breakdown

  all_issues=$(gh issue list --state all --json number,title,state,labels,milestone --limit 100)

  # Categorize
  open_count = issues where state == "OPEN" and labels NOT contain "blocked"
  blocked_count = issues where labels contain "blocked"
  in_progress = issues where labels contain "in-progress"
  pending_review = issues where labels contain "pending-review"
  closed_count = issues where state == "CLOSED"
  total = all issues

Step 3: Detect current work

  current_branch = $(git branch --show-current)
  current_issue = parse from branch name (if feature branch)

Step 4: Find next available

  Run dependency check logic from `next` command (without creating branch)
  next_available = first unblocked issue

Step 5: Output dashboard

  "
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📊 GitHub Workflow Status
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  | Milestone                | Open | Blocked | Review | Closed | Progress |
  |--------------------------|------|---------|--------|--------|----------|
  {for each milestone: row with counts and progress bar}

  **Overall:** {closed}/{total} ({percentage}%)

  **Current:** #{current_issue} — {title} (if any)
  **Next unblocked:** #{next_available} — {title} (if any)
  **Blocked ({blocked_count}):**
  {for each blocked: - #{num}: {title} — {reason}}

  **Pending Review ({pending_review_count}):**
  {for each pending: - #{num}: {title} — PR #{pr_num}}
  "
```

---

## Recommended Session Workflow

The complete autonomous session follows this sequence:

```
┌─ User says "continue" ───────────────────────────────────┐
│                                                          │
│  /start-session           ← restore context              │
│       ↓                                                  │
│  /github-workflow next    ← pick issue, create branch    │
│       ↓                                                  │
│  /implement               ← 7-step TDD workflow         │
│     ├─ /auto-verify       ← test after code changes     │
│     ├─ /fix-loop          ← if tests fail               │
│     │   └─ stuck?                                        │
│     │       → /github-workflow blocked                   │
│     │       → /github-workflow next (auto)               │
│     └─ /post-fix-pipeline ← regression + commit          │
│       ↓                                                  │
│  /github-workflow done    ← push, PR, label              │
│       ↓                                                  │
│  /github-workflow next    ← pick next issue (optional)   │
│       ↓                                                  │
│  /save-session            ← checkpoint for next session  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Key principle:** Each skill stays independent. No skill auto-invokes another. Claude follows this sequence because the workflow is documented here, not because of code coupling.

---

## State Management

### Where state lives

| State | Source | Persistence |
|-------|--------|-------------|
| Current issue | Git branch name (`feat/GH-{N}-*`) | Survives sessions |
| Issue status | GitHub labels (`in-progress`, `blocked`, etc.) | Survives sessions |
| Dependencies | Issue body (`**Depends on:** #X`) | Survives sessions |
| Progress | GitHub issue comments | Survives sessions |
| Session context | `/save-session` checkpoint | Survives sessions |

**No custom state files.** All state is derived from git branch names and GitHub issue metadata. This means any session can recover state by reading git + GitHub.

### State Recovery

If Claude starts a new session with no context:

```
1. git branch --show-current
   → feat/GH-42-fyers-adapter? Resume #42.
   → main? Check GitHub for in-progress issues.

2. gh issue list --label "in-progress"
   → Found #42? Check out its branch.
   → Nothing? Run /github-workflow next.
```

---

## Error Handling

| Error | Action |
|-------|--------|
| `gh` not installed | "GitHub CLI required. Install: https://cli.github.com" |
| `gh` not authenticated | "Run `gh auth login` to authenticate" |
| No git remote | "No git remote found. Add one: `git remote add origin {url}`" |
| API rate limit | Wait and retry (gh handles this automatically) |
| Issue not found | "Issue #{N} not found. Check issue number." |
| Branch creation fails | Check if branch exists, checkout existing |
| PR creation fails | Show error, suggest manual PR creation |
| All issues complete | "All issues closed. Project complete! 🎉" |
| Network error | "GitHub API unreachable. Check network and retry." |

---

## Labels Reference

| Label | Color | When Applied | When Removed |
|-------|-------|-------------|--------------|
| `autonomous` | Green (#0E8A16) | `plan` creates issue | `next` picks issue |
| `in-progress` | Yellow (#FBCA04) | `next` starts issue | `done` or `blocked` |
| `blocked` | Red (#B60205) | `blocked` command | Manual unblock |
| `pending-review` | Blue (#1D76DB) | `done` creates PR | PR merged (auto) |
| `needs-user` | Orange (#D93F0B) | `plan` if ⚠️ items | Manual after user acts |

---

## Integration with Other Skills

| Skill | Integration Point | Direction |
|-------|-------------------|-----------|
| `/start-session` | Run `next` after session restore | Sequential (manual) |
| `/implement` | `next` feeds deliverables as requirements | Sequential (manual) |
| `/auto-verify` | Runs inside `/implement` Step 4 | Automatic |
| `/fix-loop` | If stuck → `blocked` command | Manual escalation |
| `/post-fix-pipeline` | Produces the commit that `done` pushes | Sequential |
| `/save-session` | Run `progress` before saving | Sequential (manual) |
| `/docs-maintainer` | Runs inside `/post-fix-pipeline` | Automatic |
| `/learning-engine` | Records outcomes for cross-session learning | Automatic |
| `/fix-issue` | Separate skill for reactive bug fixes | Independent |

---

## Example Usage

```bash
# One-time setup: create issues from plan
/github-workflow plan docs/guides/AUTONOMOUS-IMPLEMENTATION-PLAN.md

# Session start: pick next issue
/github-workflow next

# Mid-session: checkpoint progress
/github-workflow progress "Completed SmartAPI binary parser, tests passing"

# Session end: push and create PR
/github-workflow done

# Handle blocker: skip to next
/github-workflow blocked "Fyers API credentials not configured"

# Check overall progress
/github-workflow status

# Work on a specific issue
/github-workflow next --issue 42
```

---

## Success Criteria

- ✅ Issues created from plan doc with correct milestones and dependencies
- ✅ `next` picks correct unblocked issue respecting dependency order
- ✅ Branch naming follows `feat/GH-{N}-{slug}` convention
- ✅ PR body includes "Closes #{N}" for auto-close on merge
- ✅ Issue never closed directly — only via PR merge
- ✅ PR never auto-merged — user/CI controls merge
- ✅ Blocked issues skip cleanly to next available
- ✅ State recoverable from git branch + GitHub labels (no custom state files)
- ✅ Idempotent: running `plan` twice doesn't create duplicates
- ✅ Works with any plan doc following the format spec (not project-specific)
