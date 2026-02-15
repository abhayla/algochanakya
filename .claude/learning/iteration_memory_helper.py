"""
Iteration Memory Helper for fix-loop

Manages iteration-by-iteration memory to enable progressive understanding
and avoid repeating rejected approaches.

Usage:
    from iteration_memory_helper import (
        init_iteration_memory,
        read_iteration_memory,
        record_iteration_memory,
        format_memory_for_agent,
        archive_session_memory
    )
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional


# File paths - resolve from project root
# Find project root (where .git directory is)
def _find_project_root():
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    # Fallback: assume we're in .claude/learning
    return Path(__file__).resolve().parent.parent.parent

PROJECT_ROOT = _find_project_root()
MEMORY_FILE = PROJECT_ROOT / ".claude/iteration-memory/iteration-memory.json"
ARCHIVE_DIR = PROJECT_ROOT / ".claude/iteration-memory/session-archives"


def init_iteration_memory(error_context: Dict) -> None:
    """
    Initialize a new iteration memory session.

    Args:
        error_context: Dict containing test file, test name, error message, stack trace

    Example:
        error_context = {
            "testFile": "tests/e2e/specs/positions/positions.happy.spec.js",
            "testName": "should exit position successfully",
            "initialError": "Timeout 30000ms exceeded...",
            "stackTrace": "at positions.happy.spec.js:45:5"
        }
    """
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    memory = {
        "sessionId": f"fix-loop-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}",
        "startTime": datetime.now(timezone.utc).isoformat(),
        "errorContext": error_context,
        "cumulativeSummary": {
            "understanding": "Initial iteration - analyzing the problem.",
            "keyFindings": [],
            "hypotheses": {
                "current": "Diagnosing the root cause",
                "rejected": []
            },
            "nextSteps": "Attempt first fix strategy"
        },
        "iterations": [],
        "metadata": {
            "totalIterations": 0,
            "currentThinkingLevel": "Normal",
            "timeElapsed": "0 seconds",
            "strategiesAttempted": 0,
            "uniqueFilesModified": 0
        }
    }

    MEMORY_FILE.write_text(json.dumps(memory, indent=2), encoding='utf-8')
    print(f"[OK] Initialized iteration memory: {memory['sessionId']}")


def read_iteration_memory() -> Optional[Dict]:
    """
    Read current iteration memory.

    Returns:
        Dict containing iteration memory, or None if not initialized
    """
    if not MEMORY_FILE.exists():
        return None

    try:
        return json.loads(MEMORY_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f"[WARNING]  Memory file corrupted: {e}. Returning None.")
        return None


def record_iteration_memory(
    iteration: int,
    thinking_level: str,
    strategy: Dict,
    hypothesis: str,
    action_taken: Dict,
    outcome: Dict,
    agent_summary: Dict
) -> None:
    """
    Record a single iteration to memory.

    Args:
        iteration: Iteration number
        thinking_level: Current thinking level (Normal, Basic, Moderate, etc.)
        strategy: Dict with name, source, successRate
        hypothesis: What we believe is the problem
        action_taken: Dict with filesModified, changeDescription, diff
        outcome: Dict with testPassed, errorAfter, newInsights
        agent_summary: Dict with whatTried, whyFailed, whatLearned, recommendation
    """
    memory = read_iteration_memory()
    if not memory:
        raise ValueError("Memory not initialized. Call init_iteration_memory() first.")

    iteration_record = {
        "number": iteration,
        "thinkingLevel": thinking_level,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy": strategy,
        "hypothesis": hypothesis,
        "actionTaken": action_taken,
        "outcome": outcome,
        "agentSummary": agent_summary
    }

    memory["iterations"].append(iteration_record)
    memory["metadata"]["totalIterations"] = iteration
    memory["metadata"]["currentThinkingLevel"] = thinking_level
    memory["metadata"]["timeElapsed"] = _calculate_elapsed_time(memory["startTime"])

    # Track unique files
    all_files = set()
    for it in memory["iterations"]:
        all_files.update(it["actionTaken"].get("filesModified", []))
    memory["metadata"]["uniqueFilesModified"] = len(all_files)

    # Update cumulative summary based on agent summary
    _update_cumulative_summary(memory, agent_summary, hypothesis, outcome["testPassed"])

    MEMORY_FILE.write_text(json.dumps(memory, indent=2), encoding='utf-8')
    print(f"[OK] Recorded iteration {iteration} to memory")


def _update_cumulative_summary(
    memory: Dict,
    agent_summary: Dict,
    hypothesis: str,
    test_passed: bool
) -> None:
    """Update cumulative understanding based on latest iteration."""
    iteration_num = len(memory['iterations'])

    # Append new learning to understanding
    current_understanding = memory["cumulativeSummary"]["understanding"]
    new_insight = agent_summary.get("whatLearned", "")

    memory["cumulativeSummary"]["understanding"] = (
        f"{current_understanding} [{iteration_num}] {new_insight}"
    )

    # Add key finding if marked as CRITICAL
    if "CRITICAL" in new_insight:
        memory["cumulativeSummary"]["keyFindings"].append(
            new_insight.replace("CRITICAL: ", "").strip()
        )

    # Update current hypothesis from agent recommendation
    memory["cumulativeSummary"]["hypotheses"]["current"] = (
        agent_summary.get("recommendation", hypothesis)
    )

    # Add rejected hypothesis if test failed
    if not test_passed:
        why_failed = agent_summary.get("whyFailed", "unknown reason")
        memory["cumulativeSummary"]["hypotheses"]["rejected"].append(
            f"{hypothesis} (REJECTED: {why_failed})"
        )

    # Update next steps
    memory["cumulativeSummary"]["nextSteps"] = agent_summary.get(
        "recommendation",
        "Continue debugging"
    )


def format_memory_for_agent(memory: Dict, current_iteration: int) -> str:
    """
    Format memory for debugger agent prompt.

    Args:
        memory: Current iteration memory dict
        current_iteration: Current iteration number

    Returns:
        Formatted string for agent prompt
    """
    summary = memory["cumulativeSummary"]

    # Format key findings
    findings_text = ""
    if summary["keyFindings"]:
        findings_text = "Key Findings So Far:\n"
        findings_text += "\n".join(f"  • {f}" for f in summary["keyFindings"])
    else:
        findings_text = "Key Findings: None yet"

    # Format rejected hypotheses
    rejected_text = ""
    if summary["hypotheses"]["rejected"]:
        rejected_text = "Rejected Hypotheses (DO NOT RETRY):\n"
        rejected_text += "\n".join(f"  [FAILED] {h}" for h in summary["hypotheses"]["rejected"][-5:])  # Last 5
    else:
        rejected_text = "Rejected Hypotheses: None yet"

    # Format recent iterations (last 3)
    recent_text = ""
    if memory["iterations"]:
        recent_iterations = memory["iterations"][-3:]
        recent_text = "Recent Iteration History:\n"
        for it in recent_iterations:
            status = "[OK] PASSED" if it["outcome"]["testPassed"] else "[FAILED] FAILED"
            recent_text += f"\n  Iteration {it['number']} ({it['thinkingLevel']}): {status}\n"
            recent_text += f"    Tried: {it['agentSummary'].get('whatTried', 'N/A')}\n"
            recent_text += f"    Learned: {it['agentSummary'].get('whatLearned', 'N/A')}\n"

    formatted = f"""
=== CUMULATIVE UNDERSTANDING FROM PREVIOUS ITERATIONS ===

{summary['understanding']}

{findings_text}

Current Hypothesis:
  --> {summary['hypotheses']['current']}

{rejected_text}

{recent_text}

Next Steps Recommended:
  --> {summary['nextSteps']}

Total Attempts: {len(memory['iterations'])}
Time Elapsed: {memory['metadata']['timeElapsed']}

=== BUILD ON THIS KNOWLEDGE - DO NOT REPEAT REJECTED APPROACHES ===
"""

    return formatted.strip()


def _calculate_elapsed_time(start_time: str) -> str:
    """Calculate elapsed time since session start."""
    try:
        start = datetime.fromisoformat(start_time)
        now = datetime.now(timezone.utc)
        elapsed = (now - start).total_seconds()

        if elapsed < 60:
            return f"{int(elapsed)} seconds"
        elif elapsed < 3600:
            return f"{int(elapsed / 60)} minutes"
        else:
            return f"{int(elapsed / 3600)} hours {int((elapsed % 3600) / 60)} minutes"
    except Exception:
        return "unknown"


def archive_session_memory(success: bool) -> None:
    """
    Archive current session to history.

    Args:
        success: Whether the fix-loop succeeded or failed
    """
    memory = read_iteration_memory()
    if not memory:
        print("[WARNING]  No memory to archive")
        return

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    memory["metadata"]["finalOutcome"] = "success" if success else "failure"
    memory["metadata"]["endTime"] = datetime.now(timezone.utc).isoformat()

    # Generate archive filename
    status = "success" if success else "failed"
    archive_file = ARCHIVE_DIR / f"{memory['sessionId']}-{status}.json"

    archive_file.write_text(json.dumps(memory, indent=2), encoding='utf-8')
    print(f"[OK] Archived session to: {archive_file.name}")

    # Clean up current session
    if MEMORY_FILE.exists():
        MEMORY_FILE.unlink()
        print("[OK] Cleared current iteration memory")


def get_memory_stats() -> Dict:
    """
    Get statistics about current memory session.

    Returns:
        Dict with stats or None if no active session
    """
    memory = read_iteration_memory()
    if not memory:
        return None

    return {
        "sessionId": memory["sessionId"],
        "totalIterations": memory["metadata"]["totalIterations"],
        "currentLevel": memory["metadata"]["currentThinkingLevel"],
        "timeElapsed": memory["metadata"]["timeElapsed"],
        "keyFindings": len(memory["cumulativeSummary"]["keyFindings"]),
        "rejectedHypotheses": len(memory["cumulativeSummary"]["hypotheses"]["rejected"]),
        "filesModified": memory["metadata"]["uniqueFilesModified"]
    }


def clear_memory() -> None:
    """Clear current iteration memory without archiving (use with caution)."""
    if MEMORY_FILE.exists():
        MEMORY_FILE.unlink()
        print("[OK] Cleared iteration memory")
    else:
        print("No memory file to clear")


# For testing/debugging
if __name__ == "__main__":
    print("Iteration Memory Helper - Test Mode")
    print("=" * 50)

    # Test initialization
    test_error = {
        "testFile": "tests/e2e/specs/test.spec.js",
        "testName": "should work",
        "initialError": "Test error",
        "stackTrace": "at test.spec.js:10"
    }

    init_iteration_memory(test_error)

    # Test read
    memory = read_iteration_memory()
    print(f"\nSession ID: {memory['sessionId']}")

    # Test stats
    stats = get_memory_stats()
    print(f"\nStats: {stats}")

    # Clean up
    clear_memory()
    print("\nTest complete!")
