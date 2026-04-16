#!/usr/bin/env python3
"""
PreToolUse hook: Enforce data-testid presence and naming convention on Vue SFC files.

Per .claude/rules/e2e-data-testid-only.md:
- Interactive elements in `.vue` files under frontend/src/views/ and frontend/src/components/
  MUST have a `data-testid` attribute.
- Static `data-testid` values MUST follow `{screen}-{component}-{element}` — at least 3
  lowercase hyphen-separated segments.
- Dynamic `:data-testid` bindings are accepted (pattern cannot be statically validated).

Interactive elements detected:
- Tags: <button>, <input>, <select>, <textarea>
- Any element carrying: @click, v-on:click, @submit, v-on:submit

Skips:
- Files outside frontend/src/views/ and frontend/src/components/
- Non-.vue files
- .claude/, docs/, tests/, node_modules/

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


# ============================================================================
# Configuration
# ============================================================================

# Segments like "optionchain", "kill-switch-btn" — each segment is lowercase
# alphanumeric starting with a letter; minimum 3 segments separated by hyphens.
TESTID_PATTERN = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+){2,}$')

# Tags that are inherently interactive and always require a testid.
INTERACTIVE_TAGS = {'button', 'input', 'select', 'textarea'}

# Event handler attributes that mark any element as interactive.
INTERACTIVE_HANDLERS = re.compile(
    r'(?:@click(?:\.[a-z]+)*|v-on:click(?:\.[a-z]+)*|@submit(?:\.[a-z]+)*|v-on:submit(?:\.[a-z]+)*)\s*='
)


# ============================================================================
# File scoping
# ============================================================================

def should_check_file(file_path: str) -> bool:
    """Only Vue files under frontend/src/views/ or frontend/src/components/."""
    if not file_path.endswith('.vue'):
        return False

    normalized = file_path.replace('\\', '/')

    # Must be under frontend/src/views/ or frontend/src/components/
    if not re.search(r'frontend/src/(views|components)/', normalized):
        return False

    # Skip typical non-production paths
    skip_patterns = [
        r'/\.claude/',
        r'/docs/',
        r'/node_modules/',
        r'/tests/',
        r'/__tests__/',
    ]
    return not any(re.search(pattern, normalized) for pattern in skip_patterns)


# ============================================================================
# Element extraction
# ============================================================================

def iter_opening_tags(content: str):
    """
    Yield (tag_name, opening_tag_text, attrs_text, start_offset) for every opening tag.

    Handles both self-closing (<input ... />) and regular (<button ...>) tags.
    The attribute section allows `>` inside quoted values (e.g., v-if="x > 0").
    Does NOT handle tags split across edit boundaries (acceptable — full Writes see
    the full file; Edits see only the new_string).
    """
    # Opening tag:
    #   <tagname
    #   then an attribute section where we allow quoted values containing anything:
    #       "..." | '...' | any char that is not >, ", or '
    #   then optional / and closing >
    tag_re = re.compile(
        r'<([a-zA-Z][a-zA-Z0-9-]*)\b((?:"[^"]*"|\'[^\']*\'|[^>"\'])*)(/?)>'
    )
    for match in tag_re.finditer(content):
        tag_name = match.group(1).lower()
        attrs = match.group(2)
        yield tag_name, match.group(0), attrs, match.start()


def extract_testid(attrs: str) -> tuple:
    """
    Extract a testid attribute from an attribute string.

    Returns:
        (kind, value) where kind is 'static', 'dynamic', or None.
        - 'static' means data-testid="literal" (no `:` or `v-bind:` prefix)
        - 'dynamic' means :data-testid="expr" or v-bind:data-testid="expr"
        - None means no testid at all
    """
    # Check dynamic FIRST so we don't misclassify bound attributes as static.
    # The prefix must be literally ":" or "v-bind:" immediately before "data-testid".
    if re.search(r'(?::|v-bind:)data-testid\s*=', attrs):
        return ('dynamic', None)

    # Static form: data-testid="value" or data-testid='value'
    # Must NOT be preceded by ":" or "v-bind:".
    static_match = re.search(
        r'(?<![:\w])data-testid\s*=\s*(["\'])([^"\']*)\1',
        attrs,
    )
    if static_match:
        return ('static', static_match.group(2))

    return (None, None)


def is_interactive(tag_name: str, attrs: str) -> bool:
    """Determine if an opening tag counts as interactive per the rule."""
    if tag_name in INTERACTIVE_TAGS:
        return True
    if INTERACTIVE_HANDLERS.search(attrs):
        return True
    return False


def line_of_offset(content: str, offset: int) -> int:
    """Return 1-based line number for a character offset."""
    return content.count('\n', 0, offset) + 1


# ============================================================================
# Violation detection
# ============================================================================

def find_violations(content: str, file_path: str) -> list:
    """
    Scan content and return a list of violation dicts.

    Each violation dict has:
        kind: 'missing' | 'invalid_pattern'
        tag: str
        snippet: str
        line: int
        testid: Optional[str]  (present when kind == 'invalid_pattern')
    """
    violations = []

    for tag_name, full_tag, attrs, offset in iter_opening_tags(content):
        if not is_interactive(tag_name, attrs):
            continue

        kind, value = extract_testid(attrs)
        line = line_of_offset(content, offset)

        # Truncate snippet to keep messages readable
        snippet = full_tag.strip()
        if len(snippet) > 120:
            snippet = snippet[:117] + '...'

        if kind is None:
            violations.append({
                'kind': 'missing',
                'tag': tag_name,
                'snippet': snippet,
                'line': line,
                'testid': None,
            })
        elif kind == 'static' and not TESTID_PATTERN.match(value):
            violations.append({
                'kind': 'invalid_pattern',
                'tag': tag_name,
                'snippet': snippet,
                'line': line,
                'testid': value,
            })
        # 'dynamic' kind accepted without further validation

    return violations


# ============================================================================
# Message formatting
# ============================================================================

def format_message(file_path: str, violations: list) -> str:
    """Build a compact block message citing violations with guidance."""
    lines = [
        "BLOCKED: Vue file violates data-testid rule.",
        f"   File: {file_path}",
        "",
    ]

    missing = [v for v in violations if v['kind'] == 'missing']
    invalid = [v for v in violations if v['kind'] == 'invalid_pattern']

    if missing:
        lines.append(f"[MISSING] {len(missing)} interactive element(s) lack data-testid:")
        for v in missing[:5]:
            lines.append(f"   line {v['line']}: <{v['tag']}>  {v['snippet']}")
        if len(missing) > 5:
            lines.append(f"   ... and {len(missing) - 5} more")
        lines.append("")

    if invalid:
        lines.append(f"[PATTERN] {len(invalid)} testid(s) violate naming:")
        for v in invalid[:5]:
            lines.append(
                f"   line {v['line']}: data-testid=\"{v['testid']}\" - need "
                f"{{screen}}-{{component}}-{{element}} (3+ hyphen-segments)"
            )
        if len(invalid) > 5:
            lines.append(f"   ... and {len(invalid) - 5} more")
        lines.append("")

    lines.extend([
        "Fix:",
        "   - Add data-testid=\"<screen>-<component>-<element>\" to every interactive element",
        "   - Use lowercase, hyphen-separated segments (3+ segments)",
        "   - Examples: optionchain-save-btn, autopilot-kill-switch-btn, dashboard-portfolio-card",
        "   - Dynamic binding is allowed: :data-testid=\"`optionchain-ce-ltp-${strike}`\"",
        "",
        "See .claude/rules/e2e-data-testid-only.md for the full rule.",
    ])

    return '\n'.join(lines)


# ============================================================================
# Hook entrypoint
# ============================================================================

def filter_grandfathered(violations: list, old_content: str) -> list:
    """
    Drop violations whose exact opening-tag text already appears in old_content.

    This makes the Edit tool brownfield-friendly: if a legacy violation exists
    in the pre-edit text and is preserved verbatim in the new text, it is NOT
    treated as "newly introduced". Only violations whose tag text is absent from
    the old content are reported.
    """
    if not old_content:
        return violations
    return [v for v in violations if v['snippet'] not in old_content]


def main():
    hook_data = parse_hook_input()
    if not hook_data:
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})

    if tool_name not in ('Write', 'Edit'):
        exit_with_code(0)

    file_path = tool_input.get('file_path', '')
    if not file_path or not should_check_file(file_path):
        exit_with_code(0)

    # Pull the content being written.
    if tool_name == 'Write':
        content = tool_input.get('content', '')
        old_content = ''
    else:  # Edit
        content = tool_input.get('new_string', '')
        old_content = tool_input.get('old_string', '') or ''

    if not content or not content.strip():
        exit_with_code(0)

    violations = find_violations(content, file_path)

    # For Edit: drop violations already present verbatim in old_string
    # (grandfathered / not introduced by this edit).
    if tool_name == 'Edit':
        violations = filter_grandfathered(violations, old_content)

    if violations:
        exit_with_code(2, format_message(file_path, violations))

    exit_with_code(0)


if __name__ == '__main__':
    main()
