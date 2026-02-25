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
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import json

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

# Cache file written by post_test_update.py (avoids re-parsing same output)
_TEST_RESULT_CACHE = PROJECT_ROOT / ".claude" / "logs" / "last-test-result.json"

# Cooldown cache file
VERIFICATION_CACHE_FILE = PROJECT_ROOT / ".claude" / "logs" / "test-verification-cache.json"
COOLDOWN_MINUTES = 5


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


def get_layer_timeout(layer: str) -> int:
    """Get appropriate timeout for test layer."""
    return {
        'e2e': 60,       # Playwright specs rarely exceed 30s
        'backend': 90,   # pytest files with DB setup
        'frontend': 30,  # Vitest (already skipped, but just in case)
    }.get(layer, 120)


def rerun_test(command: str, layer: str, timeout: int = None) -> tuple:
    """
    Re-run the test command independently.

    Args:
        command: Test command to re-run
        layer: Test layer ('e2e', 'backend')
        timeout: Timeout in seconds (auto-detected from layer if None)

    Returns:
        Tuple of (success, result, output)
        success: True if command executed, False if error
        result: 'pass' or 'fail' or None
        output: Command output
    """
    if timeout is None:
        timeout = get_layer_timeout(layer)
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


def check_cooldown(test_identifier: str) -> bool:
    """
    Check if test was verified recently (within cooldown period).

    Args:
        test_identifier: Unique identifier for the test

    Returns:
        True if test was verified recently (skip re-run)
    """
    if not VERIFICATION_CACHE_FILE.exists():
        return False

    try:
        with open(VERIFICATION_CACHE_FILE, 'r') as f:
            cache = json.load(f)

        if test_identifier in cache:
            last_verified = datetime.fromisoformat(cache[test_identifier])
            if datetime.now() - last_verified < timedelta(minutes=COOLDOWN_MINUTES):
                return True

    except (json.JSONDecodeError, KeyError, ValueError):
        pass

    return False


def update_cooldown(test_identifier: str):
    """Update cooldown cache with latest verification timestamp."""
    try:
        VERIFICATION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        cache = {}
        if VERIFICATION_CACHE_FILE.exists():
            with open(VERIFICATION_CACHE_FILE, 'r') as f:
                cache = json.load(f)

        cache[test_identifier] = datetime.now().isoformat()

        with open(VERIFICATION_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)

    except Exception:
        pass  # Non-critical


def main():
    """Main hook entry point."""
    # Check if test rerun is disabled via environment variable
    if os.environ.get('SKIP_TEST_RERUN') == '1':
        exit_with_code(0)

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

    # Check cooldown (don't re-run if verified recently)
    test_identifier = command
    if check_cooldown(test_identifier):
        print(f"\n⏭️  Skipping re-verification (verified within last {COOLDOWN_MINUTES} min)\n", file=sys.stderr)
        exit_with_code(0)

    # Try reading cached result from post_test_update.py (avoids re-parsing)
    layer = detect_test_layer(command)
    claimed_result = None
    try:
        if _TEST_RESULT_CACHE.exists():
            import json as _json
            cache = _json.loads(_TEST_RESULT_CACHE.read_text())
            if cache.get('command') == command:
                claimed_result = cache.get('result')
                layer = cache.get('layer', layer)
    except Exception:
        pass

    # Fallback to direct parsing if cache miss
    if claimed_result is None:
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
        # Results consistent - update cooldown
        update_cooldown(test_identifier)
        print(f"\n✅ Test verification passed: {claimed_result.upper()} result confirmed\n", file=sys.stderr)
        exit_with_code(0)


if __name__ == '__main__':
    main()
