#!/usr/bin/env python3
"""
PreToolUse hook: Verify evidence artifacts before git commit.

Only activates on `git commit`. Blocks if:
- Tests failed but /fix-loop was never invoked
- /fix-loop was invoked but did not succeed
- Fixes were applied but /post-fix-pipeline was never invoked

Exit codes:
    0 = allow
    2 = block with message
"""

import sys
import re
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import (
    parse_hook_input,
    read_workflow_state,
    exit_with_code
)


def main():
    """Main hook entry point."""
    hook_data = parse_hook_input()
    if not hook_data:
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})

    # Only check git commit commands
    if tool_name != 'Bash':
        exit_with_code(0)

    command = tool_input.get('command', '')
    if not re.search(r'\bgit\s+commit\b', command):
        exit_with_code(0)

    # Read workflow state
    state = read_workflow_state()
    if not state:
        # No workflow active, allow commit
        exit_with_code(0)

    # Check evidence requirements
    test_runs = state.get('evidence', {}).get('testRuns', [])
    skill_invocations = state.get('skillInvocations', {})
    fix_loop_iterations = state.get('steps', {}).get('step5_fixLoop', {}).get('iterations', 0)

    # Check if tests failed
    has_failed_tests = any(run['claimedResult'] == 'fail' for run in test_runs)

    # Gate 1: Tests failed but fix-loop never invoked
    if has_failed_tests and not skill_invocations.get('fixLoopInvoked', False):
        message = (
            "🚫 BLOCKED: Cannot commit with failed tests without attempting fixes.\n"
            "   Tests failed but Skill('fix-loop') was never invoked.\n"
            "   Use Skill('fix-loop') to diagnose and fix the failures."
        )
        exit_with_code(2, message)

    # Gate 2: fix-loop was invoked but did not succeed
    if skill_invocations.get('fixLoopInvoked', False):
        fix_loop_succeeded = skill_invocations.get('fixLoopSucceeded')
        if fix_loop_succeeded is False:
            message = (
                "🚫 BLOCKED: Cannot commit because fix-loop did not resolve all issues.\n"
                "   Skill('fix-loop') was invoked but reported failures.\n"
                "   Resolve remaining issues before committing."
            )
            exit_with_code(2, message)

    # Gate 3: Fixes were applied but post-fix-pipeline never invoked
    if fix_loop_iterations > 0 and not skill_invocations.get('postFixPipelineInvoked', False):
        message = (
            "🚫 BLOCKED: Cannot commit without running post-fix verification.\n"
            f"   {fix_loop_iterations} fix iteration(s) were applied but Skill('post-fix-pipeline') was never invoked.\n"
            "   Use Skill('post-fix-pipeline') to run final verification and commit."
        )
        exit_with_code(2, message)

    # All gates passed
    exit_with_code(0)


if __name__ == '__main__':
    main()
