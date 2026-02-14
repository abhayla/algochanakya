#!/usr/bin/env python3
"""
PreToolUse hook: Enforce folder structure rules.

Blocks:
- backend/app/services/*.py at root (except __init__.py, instruments.py, ofo_calculator.py, option_chain_service.py)
- frontend/src/assets/css/* (must be in styles/)
- frontend/src/assets/*.{png,jpg,svg} (must be in logos/)
- tests/e2e/specs/*.spec.js at root (must be in {screen}/ subdirectory)
- tests/backend/*.py at root (must be in {module}/ subdirectory)

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


# Backend services allowed at root (all others must be in subdirectories)
ALLOWED_BACKEND_ROOT_SERVICES = [
    '__init__.py',
    'instruments.py',
    'ofo_calculator.py',
    'option_chain_service.py'
]


def check_backend_services(file_path: str) -> tuple[bool, str]:
    """
    Check backend services folder structure.

    Args:
        file_path: File path to check

    Returns:
        Tuple of (is_violation: bool, message: str)
    """
    # Match: backend/app/services/*.py (root level only)
    match = re.search(r'backend[/\\]app[/\\]services[/\\]([^/\\]+\.py)$', file_path)
    if not match:
        return (False, "")

    filename = match.group(1)

    # Check if it's allowed at root
    if filename not in ALLOWED_BACKEND_ROOT_SERVICES:
        message = (
            "🚫 BLOCKED: Backend services must be in subdirectories.\n"
            f"   File: {file_path}\n"
            f"   Problem: Service files cannot be at backend/app/services/ root\n\n"
            f"✅ Allowed at root: {', '.join(ALLOWED_BACKEND_ROOT_SERVICES)}\n\n"
            f"Move to appropriate subdirectory:\n"
            f"   - autopilot/ (strategy engine, conditions, adjustments)\n"
            f"   - options/ (pricing, Greeks, strike selection)\n"
            f"   - legacy/ (legacy watchlist, positions services)\n"
            f"   - ai/ (regime detection, risk scoring)\n"
            f"   - brokers/ (broker adapters, market data)\n\n"
            f"See .claude/rules.md for details."
        )
        return (True, message)

    return (False, "")


def check_frontend_assets(file_path: str) -> tuple[bool, str]:
    """
    Check frontend assets folder structure.

    Args:
        file_path: File path to check

    Returns:
        Tuple of (is_violation: bool, message: str)
    """
    normalized_path = file_path.replace('\\', '/')

    # Check for CSS files in wrong location
    if re.search(r'frontend/src/assets/css/', normalized_path):
        message = (
            "🚫 BLOCKED: CSS files must be in styles/ not css/.\n"
            f"   File: {file_path}\n"
            f"   Problem: frontend/src/assets/css/ is not allowed\n\n"
            f"✅ Correct location: frontend/src/assets/styles/\n"
            f"See .claude/rules.md for details."
        )
        return (True, message)

    # Check for images at assets root (must be in logos/)
    if re.search(r'frontend/src/assets/[^/\\]+\.(png|jpg|jpeg|svg)$', normalized_path):
        message = (
            "🚫 BLOCKED: Image files must be in logos/ subdirectory.\n"
            f"   File: {file_path}\n"
            f"   Problem: Images cannot be at frontend/src/assets/ root\n\n"
            f"✅ Correct location: frontend/src/assets/logos/\n"
            f"See .claude/rules.md for details."
        )
        return (True, message)

    return (False, "")


def check_test_files(file_path: str) -> tuple[bool, str]:
    """
    Check test files folder structure.

    Args:
        file_path: File path to check

    Returns:
        Tuple of (is_violation: bool, message: str)
    """
    normalized_path = file_path.replace('\\', '/')

    # E2E tests: Must be in specs/{screen}/ subdirectory
    if re.search(r'tests/e2e/specs/[^/]+\.spec\.(js|ts)$', normalized_path):
        message = (
            "🚫 BLOCKED: E2E test files must be in screen subdirectory.\n"
            f"   File: {file_path}\n"
            f"   Problem: Tests cannot be at tests/e2e/specs/ root\n\n"
            f"✅ Correct structure: tests/e2e/specs/{{screen}}/{{feature}}.spec.js\n"
            f"   Examples:\n"
            f"     - tests/e2e/specs/dashboard/positions-display.spec.js\n"
            f"     - tests/e2e/specs/strategy/iron-condor.spec.js\n"
            f"     - tests/e2e/specs/autopilot/strategy-engine.spec.js\n\n"
            f"See .claude/rules.md for details."
        )
        return (True, message)

    # Backend tests: Must be in module subdirectory
    if re.search(r'tests/backend/[^/]+\.py$', normalized_path):
        # Exclude __init__.py and conftest.py (allowed at root)
        if not re.search(r'(__init__|conftest)\.py$', file_path):
            message = (
                "🚫 BLOCKED: Backend test files must be in module subdirectory.\n"
                f"   File: {file_path}\n"
                f"   Problem: Tests cannot be at tests/backend/ root\n\n"
                f"✅ Correct structure: tests/backend/{{module}}/test_{{feature}}.py\n"
                f"   Examples:\n"
                f"     - tests/backend/autopilot/test_strategy_engine.py\n"
                f"     - tests/backend/options/test_strike_selector.py\n"
                f"     - tests/backend/brokers/test_adapter_factory.py\n\n"
                f"See .claude/rules.md for details."
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

    # Only process Write tool (not Edit - editing existing files is OK)
    if tool_name != 'Write':
        exit_with_code(0)

    # Extract file path
    file_path = tool_input.get('file_path', '')
    if not file_path:
        # No file path - allow
        exit_with_code(0)

    # Skip certain files
    if should_skip_file(file_path):
        exit_with_code(0)

    # Run all checks
    checks = [
        check_backend_services,
        check_frontend_assets,
        check_test_files
    ]

    for check_func in checks:
        is_violation, message = check_func(file_path)
        if is_violation:
            exit_with_code(2, message)

    # Allow
    exit_with_code(0)


if __name__ == '__main__':
    main()
