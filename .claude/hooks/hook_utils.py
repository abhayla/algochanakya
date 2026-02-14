"""
Shared utility library for Claude Code hooks.
Provides common functions for workflow state management, test detection, and logging.

This is the foundational module that all hook scripts import from.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Project root (2 levels up from .claude/hooks/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
WORKFLOW_STATE_FILE = PROJECT_ROOT / ".claude" / "workflow-state.json"
FAILURE_INDEX_FILE = PROJECT_ROOT / ".claude" / "logs" / "learning" / "failure-index.json"
WORKFLOW_LOG_FILE = PROJECT_ROOT / ".claude" / "logs" / "workflow-sessions.log"
LEARNING_LOG_DIR = PROJECT_ROOT / ".claude" / "logs" / "learning"
AGENT_MEMORY_DIR = PROJECT_ROOT / ".claude" / "agents" / "memory"


# ============================================================================
# Hook Input/Output Protocol
# ============================================================================

def parse_hook_input() -> Optional[Dict[str, Any]]:
    """
    Parse JSON input from stdin according to Claude Code hook protocol.

    Expected format:
    {
        "tool_name": "Bash|Write|Edit|Skill|...",
        "tool_input": {...},
        "tool_output": "..." (PostToolUse only)
    }

    Returns None if stdin is empty or invalid JSON.
    """
    try:
        input_data = sys.stdin.read().strip()
        if not input_data:
            # Log empty input for debugging
            print("[DEBUG] Hook received empty stdin", file=sys.stderr)
            return None

        parsed = json.loads(input_data)
        return parsed
    except json.JSONDecodeError as e:
        # Log JSON parse failures for debugging
        print(f"[DEBUG] Hook failed to parse JSON: {e}", file=sys.stderr)
        print(f"[DEBUG] Raw input (first 200 chars): {input_data[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        # Log unexpected errors for debugging
        print(f"[DEBUG] Hook parse_hook_input error: {e}", file=sys.stderr)
        return None


def exit_with_code(code: int, message: str = "") -> None:
    """
    Exit hook with appropriate exit code.

    Exit codes:
        0 = allow (success)
        1 = warn (non-blocking message to user)
        2 = block (reject tool use)

    Args:
        code: Exit code (0, 1, or 2)
        message: Optional message to print to stderr before exiting
    """
    if message:
        print(message, file=sys.stderr)
    sys.exit(code)


# ============================================================================
# Workflow State Management
# ============================================================================

def read_workflow_state() -> Optional[Dict[str, Any]]:
    """
    Read workflow state from JSON file with atomic read.
    Returns None if file doesn't exist or is invalid.
    """
    if not WORKFLOW_STATE_FILE.exists():
        return None

    try:
        with open(WORKFLOW_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def write_workflow_state(state: Dict[str, Any]) -> bool:
    """
    Write workflow state to JSON file with atomic write (via temp file + os.replace).

    Returns True on success, False on failure.
    """
    try:
        # Ensure parent directory exists
        WORKFLOW_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        temp_file = WORKFLOW_STATE_FILE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)

        # Atomic replace (Windows and Unix compatible)
        os.replace(str(temp_file), str(WORKFLOW_STATE_FILE))

        return True
    except Exception:
        return False


def init_workflow_state(command_name: str) -> Dict[str, Any]:
    """
    Initialize fresh workflow state for a new command invocation.
    Creates log directories if they don't exist.

    Args:
        command_name: Name of the command (e.g., 'implement', 'fix-loop')

    Returns:
        Fresh workflow state dict
    """
    # Ensure log directories exist
    LEARNING_LOG_DIR.mkdir(parents=True, exist_ok=True)

    session_id = datetime.now().strftime("%Y%m%d-%H%M%S")

    state = {
        "sessionId": session_id,
        "activeCommand": command_name,
        "lastActivity": datetime.now().isoformat(),
        "steps": {
            "step1_requirements": {
                "completed": False,
                "timestamp": None
            },
            "step2_tests": {
                "completed": False,
                "testFiles": [],
                "testLayers": []
            },
            "step3_implement": {
                "completed": False,
                "filesChanged": []
            },
            "step4_runTests": {
                "completed": False,
                "testLayers": {
                    "e2e": {"passed": None, "failed": None},
                    "backend": {"passed": None, "failed": None},
                    "frontend": {"passed": None, "failed": None}
                }
            },
            "step5_fixLoop": {
                "completed": False,
                "iterations": 0
            },
            "step6_screenshots": {
                "completed": False
            },
            "step7_postFixPipeline": {
                "completed": False
            }
        },
        "skillInvocations": {
            "fixLoopInvoked": False,
            "fixLoopCount": 0,
            "fixLoopSucceeded": None,
            "postFixPipelineInvoked": False
        },
        "evidence": {
            "testRuns": []
        },
        "pendingAutoFixes": []
    }

    write_workflow_state(state)
    return state


# ============================================================================
# Test Detection and Classification
# ============================================================================

def is_test_command(cmd: str) -> bool:
    """
    Detect if a command is running tests.

    Args:
        cmd: Command string to check

    Returns:
        True if command runs tests
    """
    test_patterns = [
        r'\bpytest\b',
        r'\bnpx\s+playwright\s+test\b',
        r'\bplaywright\s+test\b',
        r'\bnpm\s+(run\s+)?test\b',
        r'\bvitest\b',
        r'\bpython\s+-m\s+pytest\b'
    ]

    return any(re.search(pattern, cmd, re.IGNORECASE) for pattern in test_patterns)


def detect_test_layer(cmd: str) -> str:
    """
    Determine which test layer (e2e, backend, frontend) a command targets.

    Args:
        cmd: Command string to analyze

    Returns:
        One of: 'e2e', 'backend', 'frontend', 'unknown'
    """
    if re.search(r'\bplaywright\b', cmd, re.IGNORECASE):
        return 'e2e'
    elif re.search(r'\bpytest\b', cmd, re.IGNORECASE):
        return 'backend'
    elif re.search(r'\bvitest\b', cmd, re.IGNORECASE):
        return 'frontend'
    elif re.search(r'\bnpm\s+run\s+test:(run|coverage)\b', cmd):
        # npm run test:run or npm run test:coverage - Vitest frontend tests
        return 'frontend'
    elif re.search(r'\bnpm\s+(run\s+)?test\b', cmd):
        # npm test (without :run) runs Playwright E2E
        return 'e2e'
    else:
        return 'unknown'


def detect_test_result(output: str, layer: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """
    Parse test output to determine pass/fail and counts.

    Args:
        output: Test command output
        layer: Test layer ('e2e', 'backend', 'frontend')

    Returns:
        Tuple of (result, passed_count, failed_count)
        result is one of: 'pass', 'fail', None
    """
    if layer == 'e2e':
        # Playwright: "5 passed (12.3s)" or "2 failed (5.2s)"
        passed_match = re.search(r'(\d+)\s+passed', output)
        failed_match = re.search(r'(\d+)\s+failed', output)

        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0

        if failed > 0:
            return ('fail', passed, failed)
        elif passed > 0:
            return ('pass', passed, failed)
        else:
            return (None, None, None)

    elif layer == 'backend':
        # pytest: "5 passed in 2.35s" or "2 failed, 3 passed in 1.52s"
        passed_match = re.search(r'(\d+)\s+passed', output)
        failed_match = re.search(r'(\d+)\s+failed', output)

        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0

        if failed > 0:
            return ('fail', passed, failed)
        elif passed > 0:
            return ('pass', passed, failed)
        else:
            return (None, None, None)

    elif layer == 'frontend':
        # Vitest: "Test Files  3 passed (5)" or "Test Files  1 failed | 2 passed (3)"
        passed_match = re.search(r'Test Files\s+(\d+)\s+passed', output)
        failed_match = re.search(r'Test Files\s+(\d+)\s+failed', output)

        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0

        if failed > 0:
            return ('fail', passed, failed)
        elif passed > 0:
            return ('pass', passed, failed)
        else:
            return (None, None, None)

    return (None, None, None)


# ============================================================================
# File Classification
# ============================================================================

def is_test_file(file_path: str) -> bool:
    """Check if a file is a test file."""
    test_patterns = [
        r'test_.*\.py$',
        r'.*\.spec\.(js|ts)$',
        r'.*\.test\.(js|ts|vue)$',
        r'/tests/',
        r'/e2e/',
        r'/__tests__/'
    ]
    return any(re.search(pattern, file_path) for pattern in test_patterns)


def is_code_file(file_path: str) -> bool:
    """Check if a file is production code (not tests, docs, config)."""
    # Check if it's a code extension
    code_extensions = ['.py', '.js', '.ts', '.vue', '.jsx', '.tsx']
    if not any(file_path.endswith(ext) for ext in code_extensions):
        return False

    # Exclude test files
    if is_test_file(file_path):
        return False

    # Exclude docs, config, and Claude files
    exclude_patterns = [
        r'/docs/',
        r'\.md$',
        r'/\.claude/',
        r'alembic/versions/',
        r'\.config\.(js|ts)$',
        r'\.setup\.(js|ts)$',
        r'/conftest\.py$'
    ]

    return not any(re.search(pattern, file_path) for pattern in exclude_patterns)


def is_always_allowed_file(file_path: str) -> bool:
    """Check if a file is always allowed (docs, Claude configs, etc.)."""
    allowed_patterns = [
        r'/\.claude/',
        r'/docs/',
        r'\.md$',
        r'CLAUDE\.md$',
        r'README\.md$'
    ]
    return any(re.search(pattern, file_path) for pattern in allowed_patterns)


# ============================================================================
# Evidence Recording
# ============================================================================

def write_evidence(evidence_dir: Path, filename: str, data: Dict[str, Any]) -> bool:
    """
    Write evidence JSON file to specified directory.

    Args:
        evidence_dir: Directory to write evidence to
        filename: Name of evidence file (should end in .json)
        data: Evidence data to write

    Returns:
        True on success, False on failure
    """
    try:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_file = evidence_dir / filename

        with open(evidence_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        return True
    except Exception:
        return False


# ============================================================================
# Workflow Event Logging
# ============================================================================

def log_event(event_type: str, **kwargs) -> None:
    """
    Append event to workflow sessions log.

    Args:
        event_type: Type of event (e.g., 'test_run', 'skill_invocation', 'step_complete')
        **kwargs: Additional event data
    """
    try:
        WORKFLOW_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **kwargs
        }

        with open(WORKFLOW_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event) + '\n')
    except Exception:
        pass  # Non-critical, don't fail hook


def record_skill_invocation(skill_name: str, succeeded: Optional[bool] = None) -> None:
    """
    Record skill invocation in workflow state.

    Args:
        skill_name: Name of the skill (e.g., 'fix-loop', 'auto-verify')
        succeeded: True if skill succeeded, False if failed, None if in progress
    """
    state = read_workflow_state()
    if not state:
        return

    # Update skill invocations
    if skill_name == 'fix-loop':
        state['skillInvocations']['fixLoopInvoked'] = True
        state['skillInvocations']['fixLoopCount'] += 1
        if succeeded is not None:
            state['skillInvocations']['fixLoopSucceeded'] = succeeded

    elif skill_name == 'post-fix-pipeline':
        state['skillInvocations']['postFixPipelineInvoked'] = True

    # Log the event
    log_event('skill_invocation', skill=skill_name, succeeded=succeeded)

    # Update workflow state
    state['lastActivity'] = datetime.now().isoformat()
    write_workflow_state(state)


# ============================================================================
# Skill Outcome Detection
# ============================================================================

def detect_skill_outcome(output: str) -> dict:
    """
    Parse skill output to determine outcome (unified version used by all hooks).

    Args:
        output: Skill output string

    Returns:
        Dict with outcome, error_type, component, workaround_used, succeeded (bool)
    """
    outcome_data = {
        'outcome': 'UNKNOWN',
        'error_type': None,
        'component': None,
        'workaround_used': None,
        'succeeded': None
    }

    # Outcome detection patterns
    if re.search(r'\b(RESOLVED|SUCCESS|PASSED)\b', output, re.IGNORECASE):
        outcome_data['outcome'] = 'RESOLVED'
        outcome_data['succeeded'] = True
    elif re.search(r'\b(FAILED|ERROR|UNRESOLVED)\b', output, re.IGNORECASE):
        outcome_data['outcome'] = 'FAILED'
        outcome_data['succeeded'] = False
    else:
        # Ambiguous - try to detect from context
        if '✅' in output or 'All tests passed' in output or 'Verification complete' in output:
            outcome_data['outcome'] = 'RESOLVED'
            outcome_data['succeeded'] = True
        elif '❌' in output or 'Tests failed' in output or 'Verification failed' in output:
            outcome_data['outcome'] = 'FAILED'
            outcome_data['succeeded'] = False
        else:
            # Default to success if truly ambiguous
            outcome_data['succeeded'] = True

    # Error type detection
    error_patterns = {
        'selector_not_found': r'(Timeout waiting for locator|selector not found|element not found)',
        'timeout': r'(Timeout|timed out|exceeded)',
        'assertion_error': r'(AssertionError|assert.*failed|expected.*got)',
        'import_error': r'(ModuleNotFoundError|ImportError|cannot import)',
        'database_error': r'(relation.*does not exist|database.*error|connection refused)',
        'api_error': r'(401|403|404|500|API.*error)',
        'broker_error': r'(Incorrect api_key|broker.*error|order.*rejected)',
    }

    for error_type, pattern in error_patterns.items():
        if re.search(pattern, output, re.IGNORECASE):
            outcome_data['error_type'] = error_type
            break

    # Component detection (from file paths or error messages)
    component_patterns = [
        r'(positions|autopilot|optionchain|strategy|watchlist|dashboard)',
        r'tests/e2e/specs/(\w+)/',
        r'backend/app/api/routes/(\w+)\.py',
        r'frontend/src/components/(\w+)/'
    ]

    for pattern in component_patterns:
        match = re.search(pattern, output)
        if match:
            outcome_data['component'] = match.group(1)
            break

    # Workaround detection
    workaround_patterns = {
        'update_testid': r'(Update|Change|Fix) data-testid',
        'increase_timeout': r'(Increase|Extend|Raise) timeout',
        'fix_import': r'(Fix|Update|Correct) import',
        'add_wait': r'(Add|Insert) (wait|waitFor)',
        'fix_broker_adapter': r'(Fix|Update) (broker adapter|adapter pattern)',
    }

    for workaround, pattern in workaround_patterns.items():
        if re.search(pattern, output, re.IGNORECASE):
            outcome_data['workaround_used'] = workaround
            break

    return outcome_data


# ============================================================================
# Failure Index Management
# ============================================================================

def init_failure_index() -> Dict[str, Any]:
    """
    Initialize or load failure index.

    Returns:
        Failure index dict with 'version' and 'entries'
    """
    if FAILURE_INDEX_FILE.exists():
        try:
            with open(FAILURE_INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # Return fresh index
    return {"version": 1, "entries": []}


def read_failure_entry(skill: str, issue_type: str, component: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Find specific failure entry in index.

    Args:
        skill: Skill name
        issue_type: Issue type identifier
        component: Optional component name

    Returns:
        Matching entry dict or None
    """
    index = init_failure_index()

    for entry in index['entries']:
        if entry['skill'] == skill and entry['issue_type'] == issue_type:
            if component is None or entry.get('component') == component:
                return entry

    return None


def update_failure_index(skill: str, issue_type: str, outcome: str,
                        component: Optional[str] = None,
                        workaround_used: Optional[str] = None) -> None:
    """
    Update failure index with new occurrence.

    Args:
        skill: Skill name
        issue_type: Issue type identifier
        outcome: Outcome ('RESOLVED', 'FAILED', etc.)
        component: Optional component name
        workaround_used: Optional workaround description
    """
    try:
        FAILURE_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        index = init_failure_index()

        # Find or create entry
        entry = read_failure_entry(skill, issue_type, component)

        if entry is None:
            entry = {
                "skill": skill,
                "issue_type": issue_type,
                "component": component,
                "first_seen": datetime.now().strftime("%Y-%m-%d"),
                "occurrences": [],
                "known_workaround": workaround_used or "",
                "threshold_reached": False,
                "auto_fix_eligible": False
            }
            index['entries'].append(entry)

        # Add occurrence
        occurrence = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "outcome": outcome,
            "workaround_used": workaround_used or ""
        }
        entry['occurrences'].append(occurrence)

        # Update thresholds
        if len(entry['occurrences']) >= 5:
            entry['threshold_reached'] = True

            # Check if eligible for auto-fix (70% success rate)
            resolved = sum(1 for occ in entry['occurrences'] if occ['outcome'] == 'RESOLVED')
            if resolved / len(entry['occurrences']) >= 0.7:
                entry['auto_fix_eligible'] = True

        # Write back
        with open(FAILURE_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)

    except Exception:
        pass  # Non-critical


# ============================================================================
# Agent Memory Management
# ============================================================================

def read_agent_memory(agent_name: str) -> str:
    """
    Read agent's persistent memory file.

    Args:
        agent_name: Agent name (e.g., 'debugger', 'code-reviewer', 'tester')

    Returns:
        Memory file content as string, or empty string if file doesn't exist
    """
    memory_file = AGENT_MEMORY_DIR / f"{agent_name}.md"

    if not memory_file.exists():
        return ""

    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def append_agent_memory(agent_name: str, section: str, entry: str) -> bool:
    """
    Append entry to agent's memory file under specified section.

    Args:
        agent_name: Agent name (e.g., 'debugger', 'code-reviewer')
        section: Section name (e.g., 'Root Causes by Category', 'Flaky Tests')
        entry: Entry to append (markdown formatted)

    Returns:
        True on success, False on failure
    """
    memory_file = AGENT_MEMORY_DIR / f"{agent_name}.md"

    if not memory_file.exists():
        return False

    try:
        # Read current content
        with open(memory_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find section header (## Section Name)
        section_pattern = f"## {section}"
        if section_pattern not in content:
            return False

        # Append entry after section header
        # Split at section, then find next ## or end of file
        parts = content.split(section_pattern)
        if len(parts) != 2:
            return False

        before_section = parts[0]
        after_section_header = parts[1]

        # Find next section or end
        next_section_match = re.search(r'\n## ', after_section_header)
        if next_section_match:
            # Insert before next section
            insert_pos = next_section_match.start()
            section_content = after_section_header[:insert_pos]
            remaining = after_section_header[insert_pos:]

            new_content = (
                before_section +
                section_pattern +
                section_content +
                f"\n{entry}\n" +
                remaining
            )
        else:
            # Append at end of section
            new_content = (
                before_section +
                section_pattern +
                after_section_header +
                f"\n{entry}\n"
            )

        # Write back
        with open(memory_file, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True
    except Exception:
        return False
