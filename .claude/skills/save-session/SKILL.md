---
name: save-session
description: Save current session context for later resumption. Usage: /save-session [name]
---

# Save Session

## When to Use
- When ending a work session and want to continue later
- Before switching to a different task
- When user explicitly invokes /save-session

## Workflow

### Step 1: Gather Context
Collect the following information:
- **Current working files** - Recently read or modified files (check tool usage in current conversation)
- **Recent changes summary** - Run `git diff` and `git status` to capture uncommitted changes
- **Current todo list state** - If TodoWrite was used, capture the current state
- **Key decisions made** - Extract important decisions or design choices from conversation
- **Relevant documentation references** - Track which docs were referenced

### Step 2: Detect Relevant Docs
Scan work context and auto-link docs from:
- `docs/features/{feature}/` if working on a specific feature
- `docs/architecture/` if working on system design
- `docs/testing/` if working on tests
- `docs/api/` if working on API changes
- `docs/decisions/` if referencing ADRs

**Detection Logic:**
- Check file paths for feature names (e.g., `backend/app/api/routes/autopilot.py` → `docs/features/autopilot/`)
- Check conversation for explicit doc mentions
- Check for architectural terms (WebSocket, authentication, broker, etc.) → link relevant architecture docs

### Step 3: Generate Session File
Create `.claude/sessions/{session-name}.md` with:
- Session metadata (timestamp, name)
- Context summary in natural language
- File references with specific line numbers if available
- Todo state if present
- Doc references with relevance explanation
- "Where I left off" summary with clear next steps
- "Resume Prompt" - pre-written prompt for /start-session

### Step 4: Self-Improvement Check
After each save, evaluate:
- Was all relevant context captured?
- Were the right docs linked?
- Is the "where I left off" summary clear enough?
- Append findings to Learnings Log below

## Session File Format

```markdown
# Session: {name}
**Saved:** {timestamp}
**Auto-generated:** {true/false}

## Summary
{Natural language summary of current state - what was being worked on, main goal, progress made}

## Working Files
- path/to/file1.py (lines X-Y) - {what was being done}
- path/to/file2.vue (modified) - {changes made}
- path/to/file3.md (read) - {why it was referenced}

## Recent Changes
{Git diff summary or manual description of uncommitted changes}

## Todo State
{Current todo list if any, with status of each item}

## Key Decisions
- Decision 1: {what was decided and why}
- Decision 2: {rationale for approach taken}

## Relevant Docs
- [Doc Name](../../docs/path/to/doc.md) - {why relevant to this session}
- [ADR-XXX](../../docs/decisions/XXX.md) - {related architectural decision}

## Where I Left Off
{Clear description of:
- What was just completed
- What was in progress
- What needs to be done next
- Any blockers or open questions
}

## Resume Prompt
{Pre-written prompt to feed to /start-session that includes:
- Brief context summary
- Specific next action
- File references if needed
}
```

## Implementation Notes

### Session Naming
- If user provides a name: Use it as-is
- If no name provided: Auto-generate from `{date}-{task-summary}`
  - Example: `2026-01-14-broker-abstraction-docs`
  - Task summary: Extract from conversation context (max 3-4 words)

### File Path Handling
- Use relative paths from project root
- Include line numbers when specific sections were modified
- Mark files as: (modified), (read), (created), (deleted)

### Git Integration
- Always run `git status` to check for uncommitted changes
- Run `git diff` to capture actual changes
- If no git changes: Note "No uncommitted changes"

## Self-Improvement Section

### Learnings Log
<!-- Auto-updated based on usage patterns -->

**Instructions for self-update:**
After each /save-session use, append an entry here with:
- Date
- What worked well (context captured correctly)
- What was missing (if user later reports something missing)
- Adjustments made to workflow

**Format:**
```
- YYYY-MM-DD: [Learning or observation]
```

### Improvement History
| Date | Change | Reason |
|------|--------|--------|
| 2026-01-14 | Initial creation | First implementation of session management |

---

## Usage Examples

```
/save-session broker-docs
→ Saves current context as broker-docs.md

/save-session
→ Auto-generates name like "2026-01-14-session-management-skills"
```
