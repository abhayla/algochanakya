#!/usr/bin/env python3
"""
CI validation script: Enforce folder structure rules on changed files.

Mirrors guard_folder_structure.py hook for CI/CD pipeline.
Validates git diff output to catch folder structure violations.

Exit codes:
    0 = all files valid
    1 = violations found
"""

import re
import sys
import subprocess
from pathlib import Path

# Fix Windows encoding for emoji support
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Backend services allowed at root
ALLOWED_BACKEND_ROOT_SERVICES = [
    "__init__.py",
    "instruments.py",
    "ofo_calculator.py",
    "option_chain_service.py",
]


def get_changed_files() -> list[str]:
    """Get list of changed files from git diff."""
    try:
        # Get files in current diff (staged + unstaged)
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            # Fallback: get all tracked files with changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Parse porcelain format (first 2 chars are status, rest is path)
            files = [line[3:].strip() for line in result.stdout.split("\n") if line]
        else:
            files = result.stdout.strip().split("\n") if result.stdout.strip() else []

        return [f for f in files if f]

    except Exception as e:
        print(f"Error getting changed files: {e}", file=sys.stderr)
        return []


def check_backend_services(file_path: str) -> tuple[bool, str]:
    """Check backend services folder structure."""
    match = re.search(r"backend[/\\]app[/\\]services[/\\]([^/\\]+\.py)$", file_path)
    if not match:
        return (False, "")

    filename = match.group(1)

    if filename not in ALLOWED_BACKEND_ROOT_SERVICES:
        message = (
            f"❌ VIOLATION: {file_path}\n"
            f"   Backend services must be in subdirectories.\n"
            f"   Allowed at root: {', '.join(ALLOWED_BACKEND_ROOT_SERVICES)}\n"
            f"   Move to: autopilot/, options/, legacy/, ai/, or brokers/"
        )
        return (True, message)

    return (False, "")


def check_frontend_assets(file_path: str) -> tuple[bool, str]:
    """Check frontend assets folder structure."""
    normalized_path = file_path.replace("\\", "/")

    # CSS files in wrong location
    if re.search(r"frontend/src/assets/css/", normalized_path):
        message = (
            f"❌ VIOLATION: {file_path}\n"
            f"   CSS files must be in styles/ not css/\n"
            f"   Correct: frontend/src/assets/styles/"
        )
        return (True, message)

    # Images at assets root
    if re.search(r"frontend/src/assets/[^/\\]+\.(png|jpg|jpeg|svg)$", normalized_path):
        message = (
            f"❌ VIOLATION: {file_path}\n"
            f"   Image files must be in logos/ subdirectory\n"
            f"   Correct: frontend/src/assets/logos/"
        )
        return (True, message)

    return (False, "")


def check_test_files(file_path: str) -> tuple[bool, str]:
    """Check test files folder structure."""
    normalized_path = file_path.replace("\\", "/")

    # E2E tests at root
    if re.search(r"tests/e2e/specs/[^/]+\.spec\.(js|ts)$", normalized_path):
        message = (
            f"❌ VIOLATION: {file_path}\n"
            f"   E2E tests must be in screen subdirectory\n"
            f"   Correct: tests/e2e/specs/{{screen}}/{{feature}}.spec.js"
        )
        return (True, message)

    # Backend tests at root (except __init__.py, conftest.py)
    if re.search(r"tests/backend/[^/]+\.py$", normalized_path):
        if not re.search(r"(__init__|conftest)\.py$", file_path):
            message = (
                f"❌ VIOLATION: {file_path}\n"
                f"   Backend tests must be in module subdirectory\n"
                f"   Correct: tests/backend/{{module}}/test_{{feature}}.py"
            )
            return (True, message)

    return (False, "")


def main():
    """Main validation."""
    changed_files = get_changed_files()

    if not changed_files:
        print("✅ No changed files to validate")
        sys.exit(0)

    print(f"🔍 Validating {len(changed_files)} changed files...")

    violations = []

    for file_path in changed_files:
        # Run all checks
        checks = [check_backend_services, check_frontend_assets, check_test_files]

        for check_func in checks:
            is_violation, message = check_func(file_path)
            if is_violation:
                violations.append(message)

    if violations:
        print("\n🚫 FOLDER STRUCTURE VIOLATIONS FOUND:\n")
        for violation in violations:
            print(violation)
            print()
        print(f"Total violations: {len(violations)}")
        print("\nSee .claude/rules.md for folder structure rules.")
        sys.exit(1)
    else:
        print("✅ All files follow folder structure rules")
        sys.exit(0)


if __name__ == "__main__":
    main()
