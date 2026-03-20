#!/usr/bin/env python3
"""
PreToolUse hook: Scan file content for leaked secrets before writing.

Event: PreToolUse
Matcher: Write|Edit
Exit codes: 0 = allow, 2 = block (message fed back to Claude)
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import parse_hook_input, exit_with_code

SAFE_EXTENSIONS = {".md", ".txt", ".csv", ".svg", ".png", ".jpg", ".gif", ".ico"}

SECRET_PATTERNS = [
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}', "AWS Secret Access Key"),
    (r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', "Private key (PEM)"),
    (r'gh[pousr]_[A-Za-z0-9_]{36,}', "GitHub personal access token"),
    (r'AIza[0-9A-Za-z_\-]{35}', "Google API key"),
    (r'xox[baprs]-[0-9a-zA-Z\-]{10,}', "Slack token"),
    (r'(?:sk|pk)_(?:test|live)_[0-9a-zA-Z]{24,}', "Stripe API key"),
    (r'(?i)(?:postgres|mysql|mongodb|redis)://[^:]+:[^@]+@', "Database connection string with password"),
    (r'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_\-]{10,}', "JWT token"),
    (r'sk-ant-[A-Za-z0-9_\-]{20,}', "Anthropic API key"),
]

API_KEY_PATTERN = re.compile(
    r'(?i)(?:api_key|apikey|api_secret|access_token|auth_token|secret_key)'
    r'\s*[=:]\s*["\'][A-Za-z0-9_\-]{20,}["\']'
)

OPENAI_PATTERN = re.compile(r'sk-[A-Za-z0-9]{20,}')
STRIPE_PATTERN = re.compile(r'sk_(?:test|live)_')

PASSWORD_PATTERN = re.compile(
    r'(?i)(?:password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']'
)
PASSWORD_PLACEHOLDER = re.compile(
    r'(?i)(?:password|passwd|pwd)\s*[=:]\s*["\']'
    r'(?:password|changeme|example|placeholder|your_|TODO|xxx|REPLACE_ME)'
)


def scan_content(content: str) -> list[str]:
    findings = []

    for pattern, label in SECRET_PATTERNS:
        if re.search(pattern, content):
            findings.append(label)

    if API_KEY_PATTERN.search(content):
        findings.append("API key or token assignment")

    if OPENAI_PATTERN.search(content) and not STRIPE_PATTERN.search(content):
        if "Anthropic API key" not in findings:
            findings.append("OpenAI API key")

    if PASSWORD_PATTERN.search(content) and not PASSWORD_PLACEHOLDER.search(content):
        findings.append("Hardcoded password")

    return findings


def main():
    hook_data = parse_hook_input()
    if not hook_data:
        exit_with_code(0)

    tool_input = hook_data.get("tool_input", {})
    content = tool_input.get("content") or tool_input.get("new_string") or ""
    file_path = tool_input.get("file_path", "")

    if not content:
        exit_with_code(0)

    ext = Path(file_path).suffix.lower() if file_path else ""
    if ext in SAFE_EXTENSIONS:
        exit_with_code(0)

    findings = scan_content(content)
    if findings:
        msg = (
            f"BLOCKED: Potential secrets detected in '{file_path}'.\n\n"
            f"Detected patterns:\n"
            + "\n".join(f"- {f}" for f in findings)
            + "\n\nUse environment variables or .env files (gitignored) instead.\n"
            "If this is a false positive (docs or test fixtures), ask the user to confirm."
        )
        exit_with_code(2, msg)

    exit_with_code(0)


if __name__ == "__main__":
    main()
