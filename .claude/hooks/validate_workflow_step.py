#!/usr/bin/env python3
"""
PreToolUse hook: Enforce 7-step workflow ordering.

Blocks:
- Write/Edit test file before Step 1 (requirements) is complete
- Write/Edit code file before Step 2 (tests) is complete
- `git commit` before all 7 steps complete AND post-fix-pipeline invoked
- Bash `sed`/`tee` on code files before Step 2

Always allows: .claude/ files, docs/ files, CLAUDE.md, *.md docs

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
    is_test_file,
    is_code_file,
    is_always_allowed_file,
    exit_with_code
)


def check_write_edit_tool(file_path: str, state: dict) -> int:
    """
    Check if Write/Edit is allowed based on workflow state.

    Supports two modes:
    - "full": Standard 7-step TDD (test-first enforced)
    - "fast-track": Skip test-first for trivial fixes (step1 still required)

    Args:
        file_path: Path being written/edited
        state: Current workflow state

    Returns:
        0 = allow, 2 = block
    """
    # Always allow Claude files, docs, and markdown
    if is_always_allowed_file(file_path):
        return 0

    is_fast_track = state.get('mode') == 'fast-track'

    # Check if it's a test file
    if is_test_file(file_path):
        # Test files require Step 1 (requirements) to be complete
        if not state['steps']['step1_requirements']['completed']:
            message = (
                "🚫 BLOCKED: Cannot write test files before Step 1 (Requirements/Clarification) is complete.\n"
                "   Complete Step 1 first by stating understanding, researching codebase, and checking docs."
            )
            exit_with_code(2, message)
        return 0

    # Check if it's production code
    if is_code_file(file_path):
        if is_fast_track:
            # Fast-track: skip step2 (test-first) requirement, but step1 still needed
            if not state['steps']['step1_requirements']['completed']:
                message = (
                    "🚫 BLOCKED: Even in fast-track mode, Step 1 (Requirements/Clarification) is required.\n"
                    "   State your understanding of the fix before writing code."
                )
                exit_with_code(2, message)
            return 0

        # Full mode: code files require Step 2 (tests) to be complete
        if not state['steps']['step2_tests']['completed']:
            message = (
                "🚫 BLOCKED: Cannot write production code before Step 2 (Write Tests) is complete.\n"
                f"   File: {file_path}\n"
                "   Write tests first, then implement the feature.\n"
                "   Tip: Use fast-track mode for trivial fixes that don't need new tests."
            )
            exit_with_code(2, message)
        return 0

    # Allow all other files
    return 0


def check_bash_tool(command: str, state: dict) -> int:
    """
    Check if Bash command is allowed based on workflow state.

    Args:
        command: Bash command being executed
        state: Current workflow state

    Returns:
        0 = allow, 2 = block
    """
    # Check for git commit
    if re.search(r'\bgit\s+commit\b', command):
        is_fast_track = state.get('mode') == 'fast-track'
        steps = state['steps']

        if is_fast_track:
            # Fast-track: only require step1 (understanding) + step4 (tests pass)
            required_steps = ['step1_requirements', 'step4_runTests']
            incomplete = []
            for step_name in required_steps:
                if not steps.get(step_name, {}).get('completed', False):
                    step_num = step_name.split('_')[0].replace('step', '')
                    step_desc = step_name.split('_', 1)[1] if '_' in step_name else step_name
                    incomplete.append(f"  - Step {step_num}: {step_desc}")

            if incomplete:
                message = (
                    "🚫 BLOCKED: Fast-track commit requires understanding + passing tests.\n"
                    "Incomplete steps:\n" +
                    "\n".join(incomplete) +
                    "\n\nRun existing tests to verify your fix doesn't break anything."
                )
                exit_with_code(2, message)
        else:
            # Full mode: all 7 steps required
            incomplete_steps = []
            for step_name, step_data in steps.items():
                if not step_data.get('completed', False):
                    step_num = step_name.split('_')[0].replace('step', '')
                    step_desc = step_name.split('_', 1)[1] if '_' in step_name else step_name
                    incomplete_steps.append(f"  - Step {step_num}: {step_desc}")

            if incomplete_steps:
                message = (
                    "🚫 BLOCKED: Cannot commit before all 7 steps are complete.\n"
                    "Incomplete steps:\n" +
                    "\n".join(incomplete_steps) +
                    "\n\nComplete the workflow or use Skill('post-fix-pipeline') to finalize."
                )
                exit_with_code(2, message)

            # Full mode also requires post-fix-pipeline
            if not state['skillInvocations']['postFixPipelineInvoked']:
                message = (
                    "🚫 BLOCKED: Cannot commit before Skill('post-fix-pipeline') has been invoked.\n"
                    "   Use Skill('post-fix-pipeline') to run final verification and commit."
                )
                exit_with_code(2, message)

        return 0

    # Check for sed/tee on code files (code editing via bash)
    if re.search(r'\b(sed|tee)\b', command):
        # Extract potential file paths
        # Simple heuristic: look for .py, .js, .vue, .ts files in command
        file_matches = re.findall(r'([^\s]+\.(py|js|vue|ts|jsx|tsx))', command)

        for file_path, _ in file_matches:
            if is_code_file(file_path) and not state['steps']['step2_tests']['completed']:
                message = (
                    "🚫 BLOCKED: Cannot edit code files via sed/tee before Step 2 (Write Tests) is complete.\n"
                    f"   Command attempts to edit: {file_path}\n"
                    "   Write tests first using Write/Edit tools."
                )
                exit_with_code(2, message)

    # Allow all other bash commands
    return 0


def main():
    """Main hook entry point."""
    hook_data = parse_hook_input()
    if not hook_data:
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})

    # Read workflow state
    state = read_workflow_state()
    if not state:
        # No workflow active, allow everything
        exit_with_code(0)

    # Check based on tool type
    if tool_name in ['Write', 'Edit']:
        file_path = tool_input.get('file_path', '')
        exit_code = check_write_edit_tool(file_path, state)
        exit_with_code(exit_code)

    elif tool_name == 'Bash':
        command = tool_input.get('command', '')
        exit_code = check_bash_tool(command, state)
        exit_with_code(exit_code)

    # Allow all other tools
    exit_with_code(0)


if __name__ == '__main__':
    main()
