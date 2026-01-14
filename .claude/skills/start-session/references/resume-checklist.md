# Resume Session Checklist

This checklist ensures all necessary context is loaded when resuming a saved session.

## Pre-Resume: Session Discovery
- [ ] Check if session name provided by user
- [ ] If no name: Find most recent session by timestamp
- [ ] If --list flag: Show all available sessions and stop
- [ ] Verify session file exists at `.claude/sessions/{name}.md`
- [ ] If not found: Show error with available sessions

## Step 1: Parse Session File
- [ ] Read session file contents
- [ ] Extract Summary section
- [ ] Extract Working Files section
- [ ] Extract Recent Changes section
- [ ] Extract Todo State section
- [ ] Extract Key Decisions section
- [ ] Extract Relevant Docs section
- [ ] Extract Where I Left Off section
- [ ] Extract Resume Prompt section

## Step 2: Restore File Context
- [ ] Identify all files in "Working Files" section
- [ ] For files marked "modified" or "created": Read full file with Read tool
- [ ] For files marked "read" with line ranges: Read those specific sections
- [ ] For files marked "read" without line ranges: Ask user if full read needed
- [ ] Verify all files still exist (some may have been deleted/moved)

## Step 3: Restore Todo List
- [ ] Check if "Todo State" section exists and has content
- [ ] If yes: Use TodoWrite to recreate the exact todo state
- [ ] If no: Skip this step (or ask user if they want to create from Next Steps)
- [ ] Verify todo statuses: completed, in_progress, pending

## Step 4: Load Documentation
- [ ] Identify all docs in "Relevant Docs" section
- [ ] Read each linked document with Read tool
- [ ] Limit to 3-5 most critical docs to avoid context overload
- [ ] Prioritize: Architecture docs > Feature docs > ADRs > Testing docs

## Step 5: Review Decisions
- [ ] Read through "Key Decisions" section
- [ ] Note any architectural patterns chosen
- [ ] Note any trade-offs or alternatives rejected
- [ ] Keep these decisions in mind for consistency

## Step 6: Check Git State (Optional)
- [ ] Run `git status` to see current uncommitted changes
- [ ] Run `git log --oneline -5` to see recent commits
- [ ] Compare current git state to "Recent Changes" in session
- [ ] Note if changes have been committed since session save

## Step 7: Present Context to User
- [ ] Output session name and timestamp
- [ ] Output summary of what was being worked on
- [ ] Output current state (completed/in-progress/pending)
- [ ] Output suggested next steps from "Where I Left Off"
- [ ] Output any blockers or open questions
- [ ] Confirm context restored and ready to continue

## Post-Resume: Validation (For Self-Improvement)
After user continues working, check:
- [ ] Was the restored context sufficient?
- [ ] Did user ask for additional files not in session?
- [ ] Did user ask for information that should have been saved?
- [ ] Were the "Next Steps" clear and actionable?
- [ ] Were there any friction points or confusion?

## Common Context Gaps to Watch For
Track if these are frequently missing (update save-session if needed):
- [ ] Git branch information
- [ ] Environment variables or configuration
- [ ] Database migration state
- [ ] Test results or build errors
- [ ] Dependency versions or package updates
- [ ] Open terminal commands or running processes
- [ ] Browser console errors or network logs

## Output Template

```markdown
# Resuming Session: {name}
**Saved:** {timestamp}
**Elapsed Time:** {X hours/days ago}

## Summary
{2-3 sentence summary from session}

## What Was Being Worked On
{Main task/goal from session}

## Current State
**Completed:**
- {list completed items from todo or "Where I Left Off"}

**In Progress:**
- {list in-progress items}

**Pending:**
- {list pending items}

## Suggested Next Steps
1. {First action from "Where I Left Off"}
2. {Second action}
3. {Third action}

## Blockers/Open Questions
{List any blockers or questions noted in session}
{If none: "No blockers noted."}

## Files Loaded
{List files that were read to restore context}

## Docs Referenced
{List docs that were loaded}

---
✅ Context restored. Ready to continue!
```

## Error Scenarios

### Session File Corrupted
- [ ] Check file is valid markdown
- [ ] Check all required sections present
- [ ] If corrupted: Show error, suggest creating new session

### Files No Longer Exist
- [ ] Note which files from session are missing
- [ ] Inform user these files were referenced but not found
- [ ] Ask user if they were renamed/moved or should skip

### Todo State Conflicts
- [ ] If current session already has active todos
- [ ] Ask user: Overwrite with saved state or merge?
- [ ] Default: Merge (keep current + add saved)

---

**Checklist Version:** 1.0
**Last Updated:** 2026-01-14
