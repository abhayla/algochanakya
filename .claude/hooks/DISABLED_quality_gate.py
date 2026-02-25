#!/usr/bin/env python3
"""
Stop hook: Auto-save session summary on exit.

On session end:
1. Auto-saves lightweight session summary to .claude/sessions/{date}-auto-save.md
2. Cleans up workflow-state.json (marks session ended)
3. Non-blocking (exit code 0) - just saves, doesn't prevent exit

Exit codes:
    0 = allow (silent or with message)
"""

import sys
from pathlib import Path
from datetime import datetime

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import read_workflow_state, write_workflow_state, exit_with_code


SESSIONS_DIR = Path(__file__).parent.parent / "sessions"


def create_auto_save() -> bool:
    """
    Create auto-save session file.

    Returns:
        True if created successfully
    """
    # Ensure sessions directory exists
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Read workflow state
    state = read_workflow_state()

    if not state:
        # No active workflow - skip auto-save
        return False

    # Generate filename
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = f"{timestamp}-auto-save.md"
    file_path = SESSIONS_DIR / filename

    # Build session summary
    active_cmd = state.get('activeCommand', 'none')
    steps = state.get('steps', {})
    session_id = state.get('sessionId', 'unknown')

    # Count completed steps
    completed_steps = [
        step_name for step_name, step_data in steps.items()
        if step_data.get('completed', False)
    ]

    # Get files changed
    files_changed = steps.get('step3_implement', {}).get('filesChanged', [])

    # Build markdown content
    content = f"""# Auto-Save: {timestamp}

**Session ID:** {session_id}
**Active Command:** /{active_cmd}
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Progress Summary

**Completed Steps:** {len(completed_steps)}/{len(steps)}

"""

    # Add completed steps list
    if completed_steps:
        content += "**Steps Completed:**\n"
        for step_name in completed_steps:
            content += f"- {step_name}\n"
        content += "\n"

    # Add files changed
    if files_changed:
        content += "**Files Changed:**\n"
        for file in files_changed[:10]:  # Limit to 10 files
            content += f"- {file}\n"
        if len(files_changed) > 10:
            content += f"- ... and {len(files_changed) - 10} more\n"
        content += "\n"

    # Add skill invocations
    skill_invocations = state.get('skillInvocations', {})
    if skill_invocations.get('fixLoopInvoked'):
        fix_count = skill_invocations.get('fixLoopCount', 0)
        fix_succeeded = skill_invocations.get('fixLoopSucceeded')
        content += f"**Fix Loop:** Invoked {fix_count} times"
        if fix_succeeded is not None:
            content += f" ({'succeeded' if fix_succeeded else 'failed'})"
        content += "\n\n"

    content += """---

## Where I Left Off

Auto-saved session context. Active workflow state preserved.

---

## Resume Prompt

Continue from the auto-saved state. Review progress summary above.

---

**Note:** This is an auto-saved session. Use `/start-session` to resume or view full session list.
"""

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False


def cleanup_workflow_state() -> bool:
    """Mark workflow session as ended."""
    state = read_workflow_state()
    if not state:
        return False

    # Mark session ended
    state['sessionEnded'] = datetime.now().isoformat()

    return write_workflow_state(state)


def main():
    """Main hook execution."""
    # Create auto-save
    saved = create_auto_save()

    # Cleanup workflow state
    cleanup_workflow_state()

    if saved:
        message = (
            "💾 Session auto-saved to .claude/sessions/\n"
            "   Use /start-session to resume in future sessions."
        )
        # Non-blocking informational message
        exit_with_code(0, message)
    else:
        # Silent success (no active workflow to save)
        exit_with_code(0)


if __name__ == '__main__':
    main()
