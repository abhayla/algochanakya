#!/usr/bin/env python3
"""
PostToolUse hook: Auto-format files after edit/write.

Runs formatters after file edits:
- .py files → black (if installed)
- .js/.vue/.ts files → prettier (if installed)

Skips: .claude/, docs/, config files
Non-blocking: Always exits with code 0 (success)

Exit codes:
    0 = allow (always, even if formatting fails)
"""

import sys
import subprocess
import re
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import parse_hook_input, exit_with_code, PROJECT_ROOT


def should_skip_file(file_path: str) -> bool:
    """
    Check if file should skip auto-formatting.

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
        r'/venv/',
        r'/env/',
        r'/\.venv/',
        r'\.config\.(js|ts)$',
        r'\.setup\.(js|ts)$',
        r'\.json$',
        r'\.md$',
        r'package\.json$',
        r'tsconfig\.json$',
        r'alembic/versions/',  # Skip migration files
    ]

    return any(re.search(pattern, normalized_path) for pattern in skip_patterns)


def format_python_file(file_path: Path) -> tuple[bool, str]:
    """
    Format Python file with black.

    Args:
        file_path: Path to Python file

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Check if black is installed
        check_result = subprocess.run(
            ['python', '-m', 'black', '--version'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )

        if check_result.returncode != 0:
            return (False, "black not installed")

        # Run black
        format_result = subprocess.run(
            ['python', '-m', 'black', str(file_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15
        )

        if format_result.returncode == 0:
            # Check if file was reformatted
            if 'reformatted' in format_result.stdout.lower():
                return (True, f"Formatted {file_path.name} with black")
            else:
                return (True, f"{file_path.name} already formatted")
        else:
            return (False, f"black failed: {format_result.stderr[:100]}")

    except subprocess.TimeoutExpired:
        return (False, "black timed out")
    except Exception as e:
        return (False, f"black error: {str(e)[:100]}")


def format_js_file(file_path: Path) -> tuple[bool, str]:
    """
    Format JavaScript/TypeScript/Vue file with prettier.

    Args:
        file_path: Path to file

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Check if prettier is installed (npx will download if needed)
        # Run prettier --write
        format_result = subprocess.run(
            ['npx', 'prettier', '--write', str(file_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15
        )

        if format_result.returncode == 0:
            return (True, f"Formatted {file_path.name} with prettier")
        else:
            # Prettier not configured or failed - not critical
            return (False, f"prettier not available: {format_result.stderr[:100]}")

    except subprocess.TimeoutExpired:
        return (False, "prettier timed out")
    except Exception as e:
        return (False, f"prettier error: {str(e)[:100]}")


def main():
    """Main hook execution."""
    hook_data = parse_hook_input()
    if not hook_data:
        # Empty input - allow
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})

    # Only process Write and Edit tools
    if tool_name not in ['Write', 'Edit']:
        exit_with_code(0)

    # Extract file path
    file_path_str = tool_input.get('file_path', '')
    if not file_path_str:
        # No file path - allow
        exit_with_code(0)

    # Skip certain files
    if should_skip_file(file_path_str):
        exit_with_code(0)

    file_path = Path(file_path_str)

    # Determine file type and format
    if file_path.suffix == '.py':
        success, message = format_python_file(file_path)
        if success:
            # Informational message about formatting
            print(f"ℹ️  {message}", file=sys.stderr)
    elif file_path.suffix in ['.js', '.ts', '.vue', '.jsx', '.tsx']:
        success, message = format_js_file(file_path)
        if success:
            # Informational message about formatting
            print(f"ℹ️  {message}", file=sys.stderr)

    # Always allow (non-blocking)
    exit_with_code(0)


if __name__ == '__main__':
    main()
