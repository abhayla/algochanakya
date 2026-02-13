#!/usr/bin/env python3
"""
PostToolUse hook: Scan for unfixed auto-fix patterns from knowledge.db.

Queries knowledge.db synthesized_rules for patterns with auto_fix_eligible=true.
Logs pending fixes to workflow state.

Non-blocking - only informational.

Exit codes:
    0 = success (always non-blocking)
"""

import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import (
    parse_hook_input,
    read_workflow_state,
    write_workflow_state,
    exit_with_code
)


def query_auto_fix_patterns():
    """
    Query knowledge.db for auto-fix eligible patterns.

    Returns:
        List of synthesized rules that are auto-fix eligible
    """
    try:
        sys.path.insert(0, str(Path(".claude/learning")))
        from db_helper import get_synthesized_rules

        rules = get_synthesized_rules(auto_fix_eligible=True)
        return rules

    except Exception:
        return []


def check_if_pattern_applied(rule: dict, workflow_state: dict) -> bool:
    """
    Check if auto-fix pattern has been applied in current workflow.

    Args:
        rule: Synthesized rule dict
        workflow_state: Current workflow state

    Returns:
        True if pattern already applied
    """
    # Check if pattern matches any recent file changes
    changed_files = workflow_state.get('steps', {}).get('step3_implement', {}).get('filesChanged', [])

    # Simple heuristic: if rule error_type matches recent errors
    recent_errors = [run['claimedResult'] for run in workflow_state.get('evidence', {}).get('testRuns', [])]

    if 'fail' not in recent_errors:
        # No failures, pattern not relevant
        return True

    # Pattern not applied yet
    return False


def main():
    """Main hook entry point."""
    hook_data = parse_hook_input()
    if not hook_data:
        exit_with_code(0)

    # Only run after Bash commands (to avoid excessive queries)
    tool_name = hook_data.get('tool_name', '')
    if tool_name != 'Bash':
        exit_with_code(0)

    # Query auto-fix patterns
    patterns = query_auto_fix_patterns()

    if not patterns:
        # No patterns available
        exit_with_code(0)

    # Read workflow state
    state = read_workflow_state()
    if not state:
        # No workflow active
        exit_with_code(0)

    # Check which patterns are pending
    pending_patterns = []

    for pattern in patterns:
        if not check_if_pattern_applied(pattern, state):
            pending_patterns.append({
                'error_type': pattern['error_type'],
                'description': pattern['description'],
                'confidence': pattern['confidence'],
                'evidence_count': pattern['evidence_count']
            })

    # Update workflow state with pending patterns
    if pending_patterns:
        state['pendingAutoFixes'] = pending_patterns
        write_workflow_state(state)

        # Print informational message
        message = f"\n💡 {len(pending_patterns)} auto-fix pattern(s) available:\n"
        for p in pending_patterns:
            message += f"   - {p['description']} (confidence: {p['confidence']:.1%}, evidence: {p['evidence_count']})\n"
        message += "   These patterns will be attempted automatically if matching errors occur.\n"

        print(message, file=sys.stderr)

    # Always allow (non-blocking)
    exit_with_code(0)


if __name__ == '__main__':
    main()
