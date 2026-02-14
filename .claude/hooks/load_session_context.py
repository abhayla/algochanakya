#!/usr/bin/env python3
"""
SessionStart hook: Auto-load last session context.

On session start (startup or resume), finds the most recent session file
and outputs key context (Where I Left Off, Resume Prompt) as informational message.

Exit codes:
    0 = allow (silent)
    1 = warn (non-blocking message to user)
"""

import sys
from pathlib import Path
from datetime import datetime

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import exit_with_code


SESSIONS_DIR = Path(__file__).parent.parent / "sessions"


def find_latest_session() -> tuple[Path | None, str]:
    """
    Find the most recent session file.

    Returns:
        Tuple of (session_file_path, session_name)
    """
    if not SESSIONS_DIR.exists():
        return (None, "")

    # Get all session files (*.md)
    session_files = list(SESSIONS_DIR.glob("*.md"))

    if not session_files:
        return (None, "")

    # Sort by modification time, most recent first
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    latest_file = session_files[0]
    session_name = latest_file.stem

    return (latest_file, session_name)


def extract_key_context(session_file: Path) -> str:
    """
    Extract key context from session file.

    Args:
        session_file: Path to session markdown file

    Returns:
        Formatted context string
    """
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract "Where I Left Off" section
        left_off = ""
        if "## Where I Left Off" in content:
            parts = content.split("## Where I Left Off")
            if len(parts) >= 2:
                section = parts[1].split("##")[0].strip()
                left_off = section[:500]  # First 500 chars

        # Extract "Resume Prompt" section
        resume_prompt = ""
        if "## Resume Prompt" in content:
            parts = content.split("## Resume Prompt")
            if len(parts) >= 2:
                section = parts[1].split("##")[0].strip()
                resume_prompt = section[:300]  # First 300 chars

        if not left_off and not resume_prompt:
            return ""

        context_msg = "📋 **Session Context Loaded**\n\n"

        if left_off:
            context_msg += f"**Where I Left Off:**\n{left_off}\n\n"

        if resume_prompt:
            context_msg += f"**Resume Prompt:**\n{resume_prompt}\n\n"

        return context_msg

    except Exception:
        return ""


def main():
    """Main hook execution."""
    # Find latest session
    session_file, session_name = find_latest_session()

    if not session_file:
        # No previous session - silent success
        exit_with_code(0)

    # Extract and display context
    context = extract_key_context(session_file)

    if not context:
        # No extractable context - silent success
        exit_with_code(0)

    # Display context as informational message
    message = (
        f"🔄 Resuming from last session: {session_name}\n\n"
        f"{context}"
        f"💡 Use `/start-session` to select a different session or view full context."
    )

    # Exit with code 1 (non-blocking informational message)
    exit_with_code(1, message)


if __name__ == '__main__':
    main()
