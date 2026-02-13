#!/usr/bin/env python3
"""
PostToolUse hook: Independently re-run tests to verify claimed results.

"Trust but verify" hook. After any targeted test completes:
- Re-runs the exact same test independently (subprocess, 300s timeout)
- BLOCKS (exit 2) if Claude claimed PASS but re-run shows FAIL
- Warns about flaky tests (claimed FAIL, re-run PASS)
- SKIPS full suite runs (too expensive) and Vitest (too fast to justify overhead)
- Only re-runs: single pytest file, single Playwright spec file

Exit codes:
    0 = allow (tests consistent or skipped verification)
    1 = warn (flaky test detected)
    2 = block (false positive detected)
"""

import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import (
    parse_hook_input,
    read_workflow_state,
    write_workflow_state,
    is_test_command,
    detect_test_layer,
    detect_test_result,
    exit_with_code,
    PROJECT_ROOT
)


def is_targeted_test(command: str) -> bool:
    """
    Check if command is a targeted test (single file, not full suite).

    Args:
        command: Test command string

    Returns:
        True if targeted, False if full suite
    """
    # Playwright: must have a specific spec file
    if 'playwright test' in command:
        # Check if it has a file path (not just 'npx playwright test')
        return bool(re.search(r'playwright\s+test\s+[^\s]+\.spec\.[jt]s', command))

    # pytest: must have a specific test file
    if 'pytest' in command:
        # Check if it has a specific .py file
        return bool(re.search(r'pytest\s+[^\s]+\.py', command))

    # Skip Vitest (too fast, not worth overhead)
    if 'vitest' in command:
        return False

    return False


def rerun_test(command: str, layer: str, timeout: int = 300) -> tuple:
    """
    Re-run the test command independently.

    Args:
        command: Test command to re-run
        layer: Test layer ('e2e', 'backend')
        timeout: Timeout in seconds (default 300)

    Returns:
        Tuple of (success, result, output)
        success: True if command executed, False if error
        result: 'pass' or 'fail' or None
        output: Command output
    """
    try:
        # Run command in project root
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = result.stdout + result.stderr

        # Detect result
        test_result, _, _ = detect_test_result(output, layer)

        return (True, test_result, output)

    except subprocess.TimeoutExpired:
        return (False, None, f"Test timed out after {timeout}s")
    except Exception as e:
        return (False, None, f"Error running test: {str(e)}")


def main():
    """Main hook entry point."""
    hook_data = parse_hook_input()
    if not hook_data:
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})
    tool_output = hook_data.get('tool_output', '')

    # Only process Bash commands
    if tool_name != 'Bash':
        exit_with_code(0)

    command = tool_input.get('command', '')

    # Check if it's a test command
    if not is_test_command(command):
        exit_with_code(0)

    # Check if it's a targeted test (skip full suites)
    if not is_targeted_test(command):
        exit_with_code(0)

    # Detect test layer and claimed result
    layer = detect_test_layer(command)
    claimed_result, _, _ = detect_test_result(tool_output, layer)

    if claimed_result is None:
        # Unable to determine result, skip verification
        exit_with_code(0)

    # Re-run the test independently
    print("\n🔍 Independently re-running test to verify result...", file=sys.stderr)

    success, rerun_result, rerun_output = rerun_test(command, layer)

    if not success:
        # Re-run failed (timeout or error), warn but don't block
        message = f"\n⚠️  Could not verify test result (re-run failed): {rerun_output}\n"
        exit_with_code(1, message)

    if rerun_result is None:
        # Unable to parse re-run result, skip
        exit_with_code(0)

    # Update workflow state with verification result
    state = read_workflow_state()
    if state and state['evidence']['testRuns']:
        # Update the last test run entry with verification result
        last_run = state['evidence']['testRuns'][-1]
        last_run['independentVerification'] = {
            "rerunResult": rerun_result,
            "consistent": (claimed_result == rerun_result),
            "timestamp": datetime.now().isoformat()
        }
        write_workflow_state(state)

    # Compare results
    if claimed_result == 'pass' and rerun_result == 'fail':
        # FALSE POSITIVE - Block this!
        message = (
            "\n🚫 BLOCKED: Test verification FAILED!\n"
            f"   Claude claimed: PASS\n"
            f"   Independent re-run: FAIL\n"
            "   This is a false positive. Review the test and fix the issue.\n"
        )
        exit_with_code(2, message)

    elif claimed_result == 'fail' and rerun_result == 'pass':
        # FLAKY TEST - Warn but allow
        message = (
            "\n⚠️  WARNING: Flaky test detected!\n"
            f"   Claude claimed: FAIL\n"
            f"   Independent re-run: PASS\n"
            "   This test may be unreliable. Consider investigating.\n"
        )
        exit_with_code(1, message)

    else:
        # Results consistent
        print(f"\n✅ Test verification passed: {claimed_result.upper()} result confirmed\n", file=sys.stderr)
        exit_with_code(0)


if __name__ == '__main__':
    main()
