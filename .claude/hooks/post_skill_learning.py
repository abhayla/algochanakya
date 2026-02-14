#!/usr/bin/env python3
"""
PostToolUse hook: Capture skill outcomes and route to knowledge.db.

After every Skill invocation (except /reflect):
- Parses output for RESOLVED/UNRESOLVED/PASSED/FAILED outcomes
- Writes capture JSON to .claude/logs/learning/{date}/
- Routes to knowledge.db via db_helper.py
- Updates failure-index.json for non-PASSED outcomes
- Auto-escalation: 5+ failures for same (skill, issue_type) → flag for manual review

Exit codes:
    0 = success (non-blocking)
"""

import sys
import re
from pathlib import Path
from datetime import datetime
import json

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import (
    parse_hook_input,
    update_failure_index,
    log_event,
    detect_skill_outcome,
    exit_with_code,
    LEARNING_LOG_DIR
)


def route_to_knowledge_db(skill_name: str, outcome_data: dict, output: str):
    """
    Route skill outcome to knowledge.db via db_helper.

    Args:
        skill_name: Name of the skill
        outcome_data: Parsed outcome data
        output: Full skill output
    """
    try:
        # Import db_helper
        sys.path.insert(0, str(Path(".claude/learning")))
        from db_helper import (
            record_error,
            record_attempt,
            update_strategy_score,
            get_strategies
        )

        # Only route failures (successes already recorded via fix attempts)
        if outcome_data['outcome'] == 'FAILED' and outcome_data['error_type']:
            # Record error pattern
            error_id = record_error(
                error_type=outcome_data['error_type'],
                message=output[:500],  # First 500 chars
                file_path=outcome_data.get('component', '')  # Component as file_path placeholder
            )

            # Get applicable strategies
            strategies = get_strategies(outcome_data['error_type'])

            if strategies:
                # Record that strategies failed (since outcome is FAILED)
                for strategy in strategies[:3]:  # Top 3 strategies
                    record_attempt(
                        error_pattern_id=error_id,
                        strategy_id=strategy['id'],
                        outcome='failure',
                        fix_description=f"Skill {skill_name} attempted but failed"
                    )

                    # Update strategy score (recalculates from database)
                    update_strategy_score(strategy_id=strategy['id'])

    except Exception as e:
        # Non-critical, don't fail hook
        print(f"⚠️  Warning: Could not route to knowledge.db: {str(e)}", file=sys.stderr)


def check_escalation_threshold(skill_name: str, issue_type: str, component: str) -> bool:
    """
    Check if failure threshold reached for escalation.

    Args:
        skill_name: Skill name
        issue_type: Issue type
        component: Component name

    Returns:
        True if threshold reached (5+ failures)
    """
    try:
        from hook_utils import read_failure_entry

        entry = read_failure_entry(skill_name, issue_type, component)
        if entry and len(entry['occurrences']) >= 5:
            return True

    except Exception:
        pass

    return False


def main():
    """Main hook entry point."""
    hook_data = parse_hook_input()
    if not hook_data:
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})
    tool_output = hook_data.get('tool_output', '')

    # Only process Skill invocations
    if tool_name != 'Skill':
        exit_with_code(0)

    skill_name = tool_input.get('skill', 'unknown')

    # Skip /reflect (would cause recursion)
    if skill_name == 'reflect':
        exit_with_code(0)

    # Parse outcome
    outcome_data = detect_skill_outcome(tool_output)

    # Write capture JSON
    timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = LEARNING_LOG_DIR / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    capture_data = {
        'timestamp': datetime.now().isoformat(),
        'skill': skill_name,
        'outcome': outcome_data['outcome'],
        'error_type': outcome_data['error_type'],
        'component': outcome_data['component'],
        'workaround_used': outcome_data['workaround_used'],
        'output_preview': tool_output[:1000]  # First 1000 chars
    }

    capture_file = date_dir / f"skill-{skill_name}-{timestamp_str}.json"
    with open(capture_file, 'w', encoding='utf-8') as f:
        json.dump(capture_data, f, indent=2)

    # Route to knowledge.db
    route_to_knowledge_db(skill_name, outcome_data, tool_output)

    # Update failure index
    if outcome_data['outcome'] != 'RESOLVED':
        update_failure_index(
            skill=skill_name,
            issue_type=outcome_data['error_type'] or 'unknown',
            outcome=outcome_data['outcome'],
            component=outcome_data['component'],
            workaround_used=outcome_data['workaround_used']
        )

        # Check escalation threshold
        if outcome_data['error_type']:
            if check_escalation_threshold(
                skill_name,
                outcome_data['error_type'],
                outcome_data['component'] or 'unknown'
            ):
                message = (
                    f"\n⚠️  ESCALATION: {skill_name} has failed 5+ times for "
                    f"{outcome_data['error_type']} in {outcome_data['component']}\n"
                    "   Consider manual review or updating fix strategies.\n"
                )
                exit_with_code(1, message)

    # Log event
    log_event(
        'skill_learning_capture',
        skill=skill_name,
        outcome=outcome_data['outcome'],
        error_type=outcome_data['error_type'],
        component=outcome_data['component']
    )

    # Always allow (non-blocking)
    exit_with_code(0)


if __name__ == '__main__':
    main()
