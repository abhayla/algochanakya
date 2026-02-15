---
name: start-session
description: Resume a previously saved session with full context restoration. Use when starting a new conversation to continue previous work. Triggers on 'resume session', 'continue where I left off', 'load session', or 'start session'.
metadata:
  author: AlgoChanakya
  version: "1.0"
---

# Start Session

## When to Use
- Starting work and want to continue from a previous session
- User invokes /start-session [name]
- User invokes /start-session (loads most recent)
- User invokes /start-session --list (shows available sessions)

## When NOT to Use

- Mid-session when already working (context is already loaded)
- To save session (use save-session instead)

## Automatic Session Loading

**Auto-Load on Startup:** The `load_session_context.py` hook automatically loads key context from the most recent session file when you start Claude Code. This includes:
- "Where I Left Off" section
- "Resume Prompt" section

**Manual `/start-session` vs Auto-Load:**
- **Auto-load:** Shows brief context (500 chars) on startup - non-intrusive reminder
- **Manual start:** Full context restoration with file reads, doc links, todo recreation

**When to use manual `/start-session`:**
- Need full context restoration (not just reminder)
- Want to select specific session (not latest)
- Need to read working files mentioned in session
- Want to restore todo list state
- Need to review linked documentation

**Auto-load is sufficient for:**
- Quick reminder of last session
- Continuity between closely-spaced sessions
- Checking what was in progress

## Workflow

### Step 1: Find Session
**If name provided:**
- Load `.claude/sessions/{name}.md`
- If not found, show error with available sessions

**If no name:**
- List all `.md` files in `.claude/sessions/`
- Sort by timestamp (most recent first)
- Load the most recent session

**If --list flag:**
- List all available sessions with timestamps and summaries
- Do not load, just display list

### Step 2: Parse Session File
Extract the following sections:
- **Summary** - Overall context of what was being worked on
- **Working Files** - Files that were being modified/read
- **Recent Changes** - Git changes that were in progress
- **Todo State** - Todo list if present
- **Key Decisions** - Important decisions made
- **Where Left Off** - Specific state when session was saved
- **Resume Prompt** - Pre-written prompt for resuming work

### Step 3: Restore Context
1. **Read the working files** mentioned in the session
   - Use Read tool for each file listed
   - Focus on specific line ranges if mentioned
2. **Restore todo list** if present
   - Use TodoWrite to recreate the todo state
3. **Review key decisions**
   - Load relevant docs if referenced
   - Understand architectural choices made
4. **Read linked documentation**
   - Load any docs referenced in "Relevant Docs" section

### Step 4: Present Context
Output to user:
- **Session Name and Timestamp**
- **Summary** - Brief overview of the session
- **What was being worked on** - Main task/goal
- **Current State** - What was completed, what's in progress
- **Suggested Next Steps** - Clear action items from "Where I Left Off"
- **Any Blockers** - Open questions or issues noted

**Output Format:**
```markdown
# Resuming Session: {name}
**Saved:** {timestamp}

## Summary
{Session summary}

## What Was Being Worked On
{Main task/goal}

## Current State
**Completed:**
- {completed items}

**In Progress:**
- {in-progress items}

**Pending:**
- {pending items}

## Suggested Next Steps
1. {next action from "Where I Left Off"}
2. {follow-up actions}

## Blockers/Open Questions
- {any blockers noted in session}

---
Context has been restored. Ready to continue!
```

### Step 5: Validate Resume
After user continues work (at end of this session or next save):
- **Was the context sufficient?** Did user have all info needed?
- **What was missing?** Did user ask for files/info not in session?
- **Friction points?** Were there gaps in understanding?
- Update learnings in this SKILL.md

## Commands

```bash
/start-session                    # Load most recent session
/start-session {name}             # Load specific session by name
/start-session --list             # Show all available sessions
```

## Context Restoration Logic

### File Reading Priority
1. Files marked as "modified" - read in full
2. Files marked as "created" - read in full
3. Files marked as "read" with line numbers - read those sections
4. Files marked as "read" without line numbers - ask user if full read needed

### Documentation Loading
- Always load docs mentioned in "Relevant Docs"
- If architectural terms present, preemptively load relevant architecture docs
- Limit to 3-5 most relevant docs to avoid context overload

### Todo State Restoration
- If todo list present: Restore using TodoWrite with exact state
- If no todo list: Ask user if they want to create one from "Next Steps"

## Self-Improvement Section

### Learnings Log
<!-- Auto-updated based on resume success -->

**Instructions for self-update:**
After each /start-session use, when the session ends or next save occurs:
- Check if context was sufficient
- Note what additional files/info user requested
- Track if "Where I Left Off" was clear enough
- Append findings below

**Format:**
```
- YYYY-MM-DD: Session "{name}" - [What worked / What was missing]
```

### Missing Context Patterns
<!-- Track what context types were frequently missing -->

**Pattern Tracking:**
If certain types of context are frequently missing across multiple sessions:
- Git branch information
- Environment variables
- Database schema state
- Test results
- Build/compile errors

Then update the save-session skill to include these by default.

### Improvement History
| Date | Change | Reason |
|------|--------|--------|
| 2026-01-14 | Initial creation | First implementation of session management |

---

## Session List Output Format

When user runs `/start-session --list`:

```markdown
# Available Sessions

| Name | Saved | Summary |
|------|-------|---------|
| broker-docs | 2026-01-14 15:30 | Documenting multi-broker architecture |
| test-fixes | 2026-01-13 18:45 | Fixing AutoPilot E2E tests |
| api-refactor | 2026-01-12 14:20 | Refactoring order execution API |

**Most Recent:** broker-docs (2026-01-14 15:30)

Use `/start-session {name}` to load a specific session, or `/start-session` to load the most recent.
```

## Troubleshooting

**Session Not Found:**
```
❌ Session "{name}" not found.

Available sessions:
- broker-docs (2026-01-14 15:30)
- test-fixes (2026-01-13 18:45)

Use `/start-session --list` for full list with summaries.
```

**No Sessions Available:**
```
❌ No saved sessions found.

Use `/save-session [name]` to save your current session for later resumption.
```

## Usage Examples

```bash
# Load most recent session
/start-session

# Load specific session
/start-session broker-docs

# List all sessions
/start-session --list
```
