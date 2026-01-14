# Session: {SESSION_NAME}
**Saved:** {TIMESTAMP}
**Auto-generated:** {true/false}

## Summary
{Brief 2-3 sentence summary of what was being worked on, the main goal, and current progress}

## Working Files
- {path/to/file1.py} (lines {X-Y}) - {What was being done with this file}
- {path/to/file2.vue} (modified) - {Changes made to this file}
- {path/to/file3.md} (read) - {Why this was referenced}
- {path/to/file4.ts} (created) - {Purpose of newly created file}

## Recent Changes
{Summary of git diff output, or manual description of uncommitted changes:
- Added: {new features/files}
- Modified: {changed functionality}
- Deleted: {removed code}
- In Progress: {partially completed changes}
}

{If no git changes: "No uncommitted changes at time of save."}

## Todo State
{If todo list exists, capture current state:
- [x] Completed task 1
- [~] In Progress: Task 2 (currently working on X part)
- [ ] Pending: Task 3
- [ ] Pending: Task 4
}

{If no todo list: "No active todo list."}

## Key Decisions
- **Decision 1:** {What was decided} - {Rationale: why this approach was chosen over alternatives}
- **Decision 2:** {What was decided} - {Rationale: technical or architectural reason}
- **Decision 3:** {What was decided} - {Rationale: context for future reference}

{If no major decisions: "No major decisions made in this session."}

## Relevant Docs
- [Doc Title](../../docs/path/to/doc.md) - {Why this doc is relevant: e.g., "Referenced for broker abstraction architecture"}
- [ADR-XXX: Decision Title](../../docs/decisions/XXX.md) - {Why relevant: e.g., "Followed patterns from this decision"}
- [Feature: Name](../../docs/features/{feature}/README.md) - {Why relevant: e.g., "Working on implementing this feature"}

{Auto-detection hints:
- If working in backend/app/api/routes/autopilot.py → Link docs/features/autopilot/
- If working on WebSocket → Link docs/architecture/websocket.md
- If working on broker code → Link docs/architecture/broker-abstraction.md
- If working on tests → Link docs/testing/README.md
}

## Where I Left Off
{Clear, actionable description including:

**Just Completed:**
- {What was just finished before saving}

**Currently In Progress:**
- {What was actively being worked on}
- {Specific file and line numbers if applicable}
- {Any partially written code or logic}

**Next Steps:**
1. {First thing to do when resuming}
2. {Second step}
3. {Third step}

**Blockers/Open Questions:**
- {Any issues that need resolution}
- {Questions that need answering}
- {Dependencies waiting on}
}

## Resume Prompt
{A pre-written, self-contained prompt that can be used with /start-session to quickly restore context:

"Continue working on {main task}. I was {what you were doing}. The current state is {brief state description}. Next steps: {immediate action}. Key files to review: {list 2-3 most important files}."
}

---

**Template Version:** 1.0
**Last Updated:** 2026-01-14
