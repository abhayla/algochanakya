#!/usr/bin/env python3
"""
PostToolUse hook: Log all tool uses to workflow sessions log.

For Skill invocations, detects skill name and success status - this is the key
mechanism that tracks when /fix-loop and /post-fix-pipeline are invoked,
enabling the commit gate.

Exit codes:
    0 = success (always non-blocking)
"""

import sys
import re
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import (
    parse_hook_input,
    log_event,
    record_skill_invocation,
    exit_with_code
)


def detect_skill_outcome(output: str) -> bool:
    """
    Detect if skill invocation succeeded based on output patterns.

    Args:
        output: Tool output string

    Returns:
        True if skill succeeded, False if failed
    """
    # Success indicators
    success_patterns = [
        r'\bRESOLVED\b',
        r'\bPASSED\b',
        r'\bSUCCESS\b',
        r'✅',
        r'All tests passed',
        r'Verification complete'
    ]

    # Failure indicators
    failure_patterns = [
        r'\bFAILED\b',
        r'\bERROR\b',
        r'❌',
        r'Tests failed',
        r'Verification failed'
    ]

    has_success = any(re.search(pattern, output, re.IGNORECASE) for pattern in success_patterns)
    has_failure = any(re.search(pattern, output, re.IGNORECASE) for pattern in failure_patterns)

    # If both or neither, default to success (optimistic)
    if has_success and not has_failure:
        return True
    elif has_failure and not has_success:
        return False
    else:
        return True  # Assume success if ambiguous


def main():
    """Main hook entry point."""
    hook_data = parse_hook_input()
    if not hook_data:
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})
    tool_output = hook_data.get('tool_output', '')

    # Log the tool use
    if tool_name == 'Skill':
        # Extract skill name
        skill_name = tool_input.get('skill', 'unknown')
        skill_args = tool_input.get('args', '')

        # Detect outcome
        succeeded = detect_skill_outcome(tool_output) if tool_output else None

        # Record skill invocation
        record_skill_invocation(skill_name, succeeded)

        log_event(
            'skill_invocation',
            skill=skill_name,
            args=skill_args,
            succeeded=succeeded
        )

    elif tool_name in ['Write', 'Edit']:
        file_path = tool_input.get('file_path', 'unknown')
        log_event(
            'file_modification',
            tool=tool_name,
            file=file_path
        )

    elif tool_name == 'Bash':
        command = tool_input.get('command', 'unknown')
        log_event(
            'bash_command',
            command=command[:200]  # Truncate long commands
        )

    # Always allow (non-blocking)
    exit_with_code(0)


if __name__ == '__main__':
    main()
