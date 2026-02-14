#!/usr/bin/env python3
"""
PreToolUse hook: Enforce cross-layer import separation.

Blocks:
- Backend files importing from frontend/
- Frontend files importing from backend/ or app.models/app.services
- Cross-layer imports that break architectural boundaries

Allows:
- Backend-to-backend imports
- Frontend-to-frontend imports
- Tests importing from both layers (for testing purposes)

Skips: .claude/, docs/, config files, node_modules/

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


def detect_layer(file_path: str) -> str:
    """
    Detect which layer a file belongs to.

    Args:
        file_path: File path to check

    Returns:
        "backend", "frontend", "test", or "unknown"
    """
    normalized_path = file_path.replace('\\', '/')

    if re.search(r'backend/', normalized_path):
        return "backend"
    elif re.search(r'frontend/', normalized_path):
        return "frontend"
    elif re.search(r'tests/', normalized_path):
        return "test"
    else:
        return "unknown"


def check_python_imports(content: str, file_path: str) -> tuple[bool, str]:
    """
    Check Python files for cross-layer imports (backend importing frontend).

    Args:
        content: File content to check
        file_path: File path being written

    Returns:
        Tuple of (is_violation: bool, message: str)
    """
    # Only check backend Python files
    layer = detect_layer(file_path)
    if layer != "backend":
        return (False, "")

    # Pattern: from frontend.* or import frontend.*
    if re.search(r'(from\s+frontend\.|import\s+frontend\.)', content):
        message = (
            "🚫 BLOCKED: Backend files cannot import from frontend.\n"
            f"   File: {file_path}\n"
            f"   Problem: Backend layer importing from frontend layer\n\n"
            f"❌ Detected patterns:\n"
            f"   - from frontend.*\n"
            f"   - import frontend.*\n\n"
            f"✅ Solution:\n"
            f"   - Backend should only import from app.*, backend.*, or Python stdlib\n"
            f"   - Move shared logic to backend/app/utils/ or backend/app/models/\n"
            f"   - Use API endpoints for frontend-backend communication\n\n"
            f"See .claude/rules.md for cross-layer import rules."
        )
        return (True, message)

    return (False, "")


def check_javascript_imports(content: str, file_path: str) -> tuple[bool, str]:
    """
    Check JavaScript files for cross-layer imports (frontend importing backend).

    Args:
        content: File content to check
        file_path: File path being written

    Returns:
        Tuple of (is_violation: bool, message: str)
    """
    # Only check frontend JavaScript/Vue files
    layer = detect_layer(file_path)
    if layer != "frontend":
        return (False, "")

    # Pattern: from.*backend/ or import.*backend/ or from.*app\.models or from.*app\.services
    patterns = [
        (r'from\s+["\'].*backend/', "from '*/backend/'"),
        (r'import\s+.*backend/', "import */backend/"),
        (r'from\s+["\'].*app\.models', "from '*/app.models'"),
        (r'from\s+["\'].*app\.services', "from '*/app.services'"),
    ]

    detected = []
    for pattern, description in patterns:
        if re.search(pattern, content):
            detected.append(description)

    if detected:
        message = (
            "🚫 BLOCKED: Frontend files cannot import from backend.\n"
            f"   File: {file_path}\n"
            f"   Problem: Frontend layer importing from backend layer\n\n"
            f"❌ Detected patterns:\n"
        )
        for desc in detected:
            message += f"   - {desc}\n"

        message += (
            f"\n✅ Solution:\n"
            f"   - Use API calls via src/services/api.js instead\n"
            f"   - Frontend should only import from @/*, relative paths, or node_modules\n"
            f"   - Define TypeScript types/interfaces in frontend/src/types/ (if needed)\n"
            f"   - Never directly import backend Python modules\n\n"
            f"See .claude/rules.md for cross-layer import rules."
        )
        return (True, message)

    return (False, "")


def should_skip_file(file_path: str) -> bool:
    """
    Check if file should skip validation.

    Args:
        file_path: File path to check

    Returns:
        True if should skip
    """
    normalized_path = file_path.replace('\\', '/')

    skip_patterns = [
        r'/\.claude/',
        r'/docs/',
        r'/node_modules/',
        r'\.md$',
        r'\.json$',
        r'\.config\.(js|ts)$',
        r'\.setup\.(js|ts)$',
        r'package\.json$',
        r'tsconfig\.json$',
        r'vite\.config\.(js|ts)$',
        r'playwright\.config\.(js|ts)$',
        r'vitest\.config\.(js|ts)$',
        r'alembic\.ini$',
        r'\.env',
        r'/tests/',  # Tests can import from both layers
    ]

    return any(re.search(pattern, normalized_path) for pattern in skip_patterns)


def main():
    """Main hook execution."""
    hook_data = parse_hook_input()
    if not hook_data:
        # Empty input - allow by default
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})

    # Process both Write and Edit tools
    if tool_name not in ['Write', 'Edit']:
        exit_with_code(0)

    # Extract file path
    file_path = tool_input.get('file_path', '')
    if not file_path:
        # No file path - allow
        exit_with_code(0)

    # Skip certain files
    if should_skip_file(file_path):
        exit_with_code(0)

    # Extract content to check
    content = ""
    if tool_name == 'Write':
        content = tool_input.get('content', '')
    elif tool_name == 'Edit':
        # For Edit, check the new_string being added
        content = tool_input.get('new_string', '')

    if not content:
        # No content to check - allow
        exit_with_code(0)

    # Run checks based on file type
    checks = []

    # Python files: check for backend importing frontend
    if file_path.endswith('.py'):
        checks.append(check_python_imports)

    # JavaScript/Vue files: check for frontend importing backend
    elif file_path.endswith(('.js', '.ts', '.vue', '.jsx', '.tsx')):
        checks.append(check_javascript_imports)

    for check_func in checks:
        is_violation, message = check_func(content, file_path)
        if is_violation:
            exit_with_code(2, message)

    # Allow
    exit_with_code(0)


if __name__ == '__main__':
    main()
