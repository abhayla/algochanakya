#!/usr/bin/env python3
"""
SessionStart hook: Reinject critical context after compaction.

After context compaction, reinjects:
1. Current workflow state (active command, incomplete steps)
2. Key rules summary (broker abstraction, trading constants, protected files)
3. Recent agent memory highlights
4. Current git state (branch, last commit, modified files)

Exit codes:
    0 = allow (silent)
    1 = warn (non-blocking message with reinjected context)
"""

import sys
import subprocess
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import read_workflow_state, read_agent_memory, exit_with_code, PROJECT_ROOT


def get_git_state() -> str:
    """Get current git state (branch, last commit, modified files)."""
    try:
        # Get current branch
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

        # Get last commit
        commit_result = subprocess.run(
            ['git', 'log', '--oneline', '-1'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        last_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "none"

        # Get modified files count
        status_result = subprocess.run(
            ['git', 'status', '--short'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        modified_files = len(status_result.stdout.strip().split('\n')) if status_result.returncode == 0 else 0

        return f"Branch: {branch} | Last commit: {last_commit} | Modified files: {modified_files}"

    except Exception:
        return "Git state unavailable"


def get_workflow_summary() -> str:
    """Get workflow state summary."""
    state = read_workflow_state()
    if not state:
        return "No active workflow"

    active_cmd = state.get('activeCommand', 'none')
    steps = state.get('steps', {})

    completed_steps = sum(1 for step_data in steps.values() if step_data.get('completed', False))
    total_steps = len(steps)

    return f"Active: /{active_cmd} | Progress: {completed_steps}/{total_steps} steps"


def get_key_rules() -> str:
    """Get critical rules summary."""
    return (
        "1. Broker Abstraction: Use adapters, never direct KiteConnect/SmartAPI\n"
        "2. Trading Constants: Use get_lot_size(), get_strike_step(), INDEX_TOKENS\n"
        "3. Protected Files: Never touch notes, .env*, C:\\Apps\\algochanakya\n"
        "4. Folder Structure: Services in subdirs, E2E tests in specs/{screen}/"
    )


def get_agent_memory_highlights() -> str:
    """Get recent highlights from agent memories."""
    highlights = []

    # Check debugger memory for frequent errors
    debugger_memory = read_agent_memory('debugger')
    if 'Recurring Error Patterns' in debugger_memory:
        highlights.append("- Debugger: Check recurring error patterns")

    # Check tester memory for flaky tests
    tester_memory = read_agent_memory('tester')
    if 'Flaky Tests' in tester_memory and 'None tracked yet' not in tester_memory:
        highlights.append("- Tester: Known flaky tests tracked")

    # Check code-reviewer memory for violations
    reviewer_memory = read_agent_memory('code-reviewer')
    if 'Frequent Violations' in reviewer_memory and 'None yet' not in reviewer_memory:
        highlights.append("- Code-reviewer: Frequent violations tracked")

    if not highlights:
        return "No agent highlights"

    return "\n".join(highlights)


def main():
    """Main hook execution."""
    # Build reinjection message
    message = (
        "🔄 **Context Reinjected After Compaction**\n\n"
        "**Workflow State:**\n"
        f"{get_workflow_summary()}\n\n"
        "**Git State:**\n"
        f"{get_git_state()}\n\n"
        "**Critical Rules:**\n"
        f"{get_key_rules()}\n\n"
        "**Agent Memory:**\n"
        f"{get_agent_memory_highlights()}\n\n"
        "💡 Full context available in .claude/rules.md and agent memory files."
    )

    # Exit with code 1 (non-blocking informational message)
    exit_with_code(1, message)


if __name__ == '__main__':
    main()
