#!/usr/bin/env python3
"""
PreToolUse hook: Block writes/edits to protected files.

Protects:
- /notes (personal user file)
- **/.env* (environment credentials)
- C:\Apps\algochanakya/** (production folder)
- **/knowledge.db (learning database)
- **/workflow-state.json (hook-managed state)
- **/.auth-state.json (test credentials)
- **/.auth-token (test tokens)

Exit codes:
    0 = allow
    2 = block with message
"""

import sys
import re
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import parse_hook_input, exit_with_code


# Protected file patterns (regex)
PROTECTED_PATTERNS = [
    (r'\.env($|\..+$)', "Environment credentials (edit manually)"),
    (r'C:\\Apps\\algochanakya', "Production folder - NEVER touch production"),
    (r'/knowledge\.db$', "Learning database (hook-managed)"),
    (r'/workflow-state\.json$', "Workflow state (hook-managed)"),
    (r'\.auth-state\.json$', "Test credentials (Playwright-managed)"),
    (r'/\.auth-token', "Test tokens (Playwright-managed)"),
]


def is_protected_file(file_path: str) -> tuple[bool, str]:
    """
    Check if file matches protected patterns.

    Args:
        file_path: File path to check

    Returns:
        Tuple of (is_protected: bool, reason: str)
    """
    # Normalize path for Windows (forward slashes for regex)
    normalized_path = file_path.replace('\\', '/')

    for pattern, reason in PROTECTED_PATTERNS:
        if re.search(pattern, normalized_path):
            return (True, reason)

    return (False, "")


def main():
    """Main hook execution."""
    hook_data = parse_hook_input()
    if not hook_data:
        # Empty input - allow by default
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})

    # Only process Write and Edit tools
    if tool_name not in ['Write', 'Edit']:
        exit_with_code(0)

    # Extract file path
    file_path = tool_input.get('file_path', '')
    if not file_path:
        # No file path - allow
        exit_with_code(0)

    # Check if file is protected
    is_protected, reason = is_protected_file(file_path)

    if is_protected:
        message = (
            f"🚫 BLOCKED: Cannot {tool_name.lower()} protected file.\n"
            f"   File: {file_path}\n"
            f"   Reason: {reason}\n\n"
            f"Protected files are managed manually or by hooks. See .claude/rules.md for details."
        )
        exit_with_code(2, message)

    # Allow
    exit_with_code(0)


if __name__ == '__main__':
    main()
