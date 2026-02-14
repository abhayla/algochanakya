#!/usr/bin/env python3
"""
CI validation script: Enforce cross-layer import separation on changed files.

Mirrors guard_cross_feature_imports.py hook for CI/CD pipeline.
Validates git diff output to catch cross-layer import violations.

Blocks:
- Backend files importing from frontend/
- Frontend files importing from backend/ or app.models/app.services

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


def detect_layer(file_path: str) -> str:
    """Detect which layer a file belongs to."""
    normalized_path = file_path.replace("\\", "/")

    if re.search(r"backend/", normalized_path):
        return "backend"
    elif re.search(r"frontend/", normalized_path):
        return "frontend"
    elif re.search(r"tests/", normalized_path):
        return "test"
    else:
        return "unknown"


def read_file_content(file_path: str) -> str:
    """Read file content safely."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def check_python_imports(file_path: str) -> tuple[bool, str]:
    """Check Python files for backend importing frontend."""
    layer = detect_layer(file_path)
    if layer != "backend":
        return (False, "")

    content = read_file_content(file_path)
    if not content:
        return (False, "")

    # Pattern: from frontend.* or import frontend.*
    if re.search(r"(from\s+frontend\.|import\s+frontend\.)", content):
        message = (
            f"❌ VIOLATION: {file_path}\n"
            f"   Backend files cannot import from frontend layer\n"
            f"   Detected: from frontend.* or import frontend.*\n"
            f"   Solution: Use API endpoints for frontend-backend communication"
        )
        return (True, message)

    return (False, "")


def check_javascript_imports(file_path: str) -> tuple[bool, str]:
    """Check JavaScript files for frontend importing backend."""
    layer = detect_layer(file_path)
    if layer != "frontend":
        return (False, "")

    content = read_file_content(file_path)
    if not content:
        return (False, "")

    # Patterns for cross-layer imports
    patterns = [
        (r"from\s+['\"].*backend/", "from '*/backend/'"),
        (r"import\s+.*backend/", "import */backend/"),
        (r"from\s+['\"].*app\.models", "from '*/app.models'"),
        (r"from\s+['\"].*app\.services", "from '*/app.services'"),
    ]

    detected = []
    for pattern, description in patterns:
        if re.search(pattern, content):
            detected.append(description)

    if detected:
        message = (
            f"❌ VIOLATION: {file_path}\n"
            f"   Frontend files cannot import from backend layer\n"
            f"   Detected patterns: {', '.join(detected)}\n"
            f"   Solution: Use API calls via src/services/api.js instead"
        )
        return (True, message)

    return (False, "")


def should_skip_file(file_path: str) -> bool:
    """Check if file should skip validation."""
    normalized_path = file_path.replace("\\", "/")

    skip_patterns = [
        r"/\.claude/",
        r"/docs/",
        r"/node_modules/",
        r"\.md$",
        r"\.json$",
        r"\.config\.(js|ts)$",
        r"/tests/",  # Tests can import from both layers
    ]

    return any(re.search(pattern, normalized_path) for pattern in skip_patterns)


def main():
    """Main validation."""
    changed_files = get_changed_files()

    if not changed_files:
        print("✅ No changed files to validate")
        sys.exit(0)

    print(
        f"🔍 Validating {len(changed_files)} changed files for cross-layer imports..."
    )

    violations = []

    for file_path in changed_files:
        # Skip certain files
        if should_skip_file(file_path):
            continue

        # Check based on file type
        checks = []

        if file_path.endswith(".py"):
            checks.append(check_python_imports)
        elif file_path.endswith((".js", ".ts", ".vue", ".jsx", ".tsx")):
            checks.append(check_javascript_imports)

        for check_func in checks:
            is_violation, message = check_func(file_path)
            if is_violation:
                violations.append(message)

    if violations:
        print("\n🚫 CROSS-LAYER IMPORT VIOLATIONS FOUND:\n")
        for violation in violations:
            print(violation)
            print()
        print(f"Total violations: {len(violations)}")
        print("\nBackend must not import from frontend.")
        print("Frontend must not import from backend (use API calls instead).")
        print("See .claude/rules.md for cross-layer import rules.")
        sys.exit(1)
    else:
        print("✅ All files follow cross-layer import rules")
        sys.exit(0)


if __name__ == "__main__":
    main()
