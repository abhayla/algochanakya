#!/usr/bin/env python3
"""
PostToolUse hook: Record test results to workflow state after test commands.

Records test results to workflow state:
- On PASS: marks Steps 4+5 complete
- On FAIL: increments fix-loop iteration counter, prints prompt to use /fix-loop
- Writes evidence JSON with timestamp, command, target, layer, result

Only activates after Bash commands that run tests.

Exit codes:
    0 = success (non-blocking)
    1 = warn with message
"""

import sys
import re
import json
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
    write_evidence,
    log_event,
    exit_with_code,
    LEARNING_LOG_DIR,
    PROJECT_ROOT
)

# Cache file for cross-hook result sharing (verify_test_rerun reads this)
_TEST_RESULT_CACHE = PROJECT_ROOT / ".claude" / "logs" / "last-test-result.json"


def extract_test_target(command: str) -> str:
    """
    Extract the test target (file or spec) from command.

    Args:
        command: Test command string

    Returns:
        Test target (filename or 'suite')
    """
    # Playwright: npx playwright test path/to/spec.js
    playwright_match = re.search(r'playwright\s+test\s+([^\s]+\.spec\.[jt]s)', command)
    if playwright_match:
        return playwright_match.group(1)

    # pytest: pytest tests/path/to/test_file.py
    pytest_match = re.search(r'pytest\s+([^\s]+\.py)', command)
    if pytest_match:
        return pytest_match.group(1)

    # Vitest: vitest path/to/test.spec.js
    vitest_match = re.search(r'vitest\s+([^\s]+\.(test|spec)\.[jt]sx?)', command)
    if vitest_match:
        return vitest_match.group(1)

    return 'suite'


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

    # Detect test layer and result
    layer = detect_test_layer(command)
    result, passed, failed = detect_test_result(tool_output, layer)

    if result is None:
        # Unable to determine result
        exit_with_code(0)

    # Write result cache for verify_test_rerun.py (avoids re-parsing same output)
    try:
        _TEST_RESULT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _TEST_RESULT_CACHE.write_text(json.dumps({
            "command": command,
            "result": result,
            "layer": layer,
            "passed": passed,
            "failed": failed,
            "timestamp": datetime.now().isoformat()
        }))
    except Exception:
        pass  # Non-critical

    # Extract test target
    target = extract_test_target(command)

    # Update workflow state
    state = read_workflow_state()
    if state:
        # Record test run in evidence
        evidence_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "target": target,
            "layer": layer,
            "claimedResult": result,
            "passed": passed,
            "failed": failed
        }

        state['evidence']['testRuns'].append(evidence_entry)

        # Update test layer results
        if layer in ['e2e', 'backend', 'frontend']:
            state['steps']['step4_runTests']['testLayers'][layer] = {
                "passed": passed,
                "failed": failed
            }

        # Update step completion
        if result == 'pass':
            # Mark Step 4 (run tests) as complete
            state['steps']['step4_runTests']['completed'] = True
            state['steps']['step4_runTests']['timestamp'] = datetime.now().isoformat()

            # If no previous failures, mark Step 5 (fix loop) as complete
            if state['steps']['step5_fixLoop']['iterations'] == 0:
                state['steps']['step5_fixLoop']['completed'] = True
                state['steps']['step5_fixLoop']['timestamp'] = datetime.now().isoformat()

        elif result == 'fail':
            # Increment fix-loop iteration counter
            state['steps']['step5_fixLoop']['iterations'] += 1

        state['lastActivity'] = datetime.now().isoformat()
        write_workflow_state(state)

        # Write evidence file
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        evidence_filename = f"test-run-{layer}-{timestamp_str}.json"
        write_evidence(LEARNING_LOG_DIR, evidence_filename, evidence_entry)

        # Log event
        log_event(
            'test_run',
            layer=layer,
            result=result,
            target=target,
            passed=passed,
            failed=failed
        )

    # If tests failed, print reminder to use /fix-loop
    if result == 'fail':
        message = f"\n⚠️  Tests failed ({failed} failed). Use Skill('fix-loop') to diagnose and fix.\n"
        exit_with_code(1, message)

    # Always allow
    exit_with_code(0)


if __name__ == '__main__':
    main()
