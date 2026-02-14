#!/usr/bin/env python3
"""
PostToolUse hook: Remind about frontend schema updates after backend model changes.

Warns when:
- Backend models (backend/app/models/*.py) are modified
- Alembic migrations (backend/alembic/versions/*.py) are created
- But no corresponding frontend service file (frontend/src/services/*Api.js) is modified

Adapted for JavaScript project (no TypeScript interfaces to check).

Exit codes:
    0 = allow (schema unchanged or frontend service already updated)
    1 = warn (non-blocking reminder)
"""

import sys
import re
import subprocess
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import parse_hook_input, exit_with_code


def detect_schema_change(file_path: str) -> bool:
    """
    Detect if file is a backend model or migration.

    Args:
        file_path: File path to check

    Returns:
        True if schema-related file
    """
    normalized_path = file_path.replace('\\', '/')

    # Backend models
    if re.search(r'backend/app/models/.*\.py$', normalized_path):
        # Exclude __init__.py
        if not file_path.endswith('__init__.py'):
            return True

    # Alembic migrations
    if re.search(r'backend/alembic/versions/.*\.py$', normalized_path):
        return True

    return False


def get_model_name(file_path: str) -> str:
    """
    Extract model name from file path.

    Args:
        file_path: File path

    Returns:
        Model name (e.g., "user", "position", "strategy")
    """
    path = Path(file_path)
    # Remove .py extension and return stem
    return path.stem


def check_frontend_service_updated() -> bool:
    """
    Check if any frontend service file was modified in current session.

    Uses git diff to check if frontend/src/services/ files have changes.

    Returns:
        True if frontend service was also modified
    """
    try:
        # Get changed files in current session
        result = subprocess.run(
            ['git', 'diff', '--name-only'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).parent.parent.parent  # Project root
        )

        if result.returncode != 0:
            # If git diff fails, assume frontend was updated (avoid false positives)
            return True

        changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []

        # Check if any frontend service file was modified
        for file_path in changed_files:
            normalized = file_path.replace('\\', '/')
            if re.search(r'frontend/src/services/.*Api\.js$', normalized):
                return True

        return False

    except Exception:
        # On error, assume frontend was updated (avoid false positives)
        return True


def main():
    """Main hook execution."""
    hook_data = parse_hook_input()
    if not hook_data:
        # Empty input - allow by default
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})

    # Only process Write tool (schema changes happen via Write)
    if tool_name != 'Write':
        exit_with_code(0)

    # Extract file path
    file_path = tool_input.get('file_path', '')
    if not file_path:
        # No file path - allow
        exit_with_code(0)

    # Check if this is a schema change
    if not detect_schema_change(file_path):
        # Not a schema file - allow
        exit_with_code(0)

    # Extract model name for better message
    model_name = get_model_name(file_path)

    # Check if frontend service was also updated
    frontend_updated = check_frontend_service_updated()

    if frontend_updated:
        # Frontend service was updated - all good
        exit_with_code(0)

    # Frontend service NOT updated - warn
    message = (
        "⚠️  REMINDER: Backend schema changed, frontend may need updates.\n\n"
        f"   Changed file: {file_path}\n"
        f"   Model: {model_name}\n\n"
        f"📋 Consider updating frontend:\n"
        f"   - Check if frontend/src/services/{model_name}Api.js needs updates\n"
        f"   - Update API request/response handling if schema changed\n"
        f"   - Add new fields to Pinia stores if needed\n"
        f"   - Update Vue components if UI needs to display new fields\n\n"
        f"✅ If frontend doesn't need updates, you can ignore this warning.\n"
        f"   This is a non-blocking reminder to maintain schema parity.\n"
    )

    # Exit with code 1 (warn, non-blocking)
    exit_with_code(1, message)


if __name__ == '__main__':
    main()
