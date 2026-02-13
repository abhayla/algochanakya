"""
Learning Engine Database Helper
Provides database operations for the autonomous learning system.
"""

import sqlite3
import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DB_PATH = Path(__file__).parent / "knowledge.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database from schema.sql."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()

    conn = get_connection()
    try:
        conn.executescript(schema_sql)
        conn.commit()
        print(f"[OK] Database initialized: {DB_PATH}")
        return True
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        return False
    finally:
        conn.close()


def fingerprint(error_type: str, message: str, file_path: Optional[str] = None) -> str:
    """
    Generate error fingerprint by normalizing and hashing.

    Normalization rules:
    - Strip line numbers: 'line 42' → 'line N'
    - Strip quoted values: 'SomeValue' → 'X'
    - Strip timestamps and UUIDs
    - Normalize file paths to patterns: 'foo/bar.py' → 'foo/*.py'
    """
    # Normalize message
    norm_msg = message
    norm_msg = re.sub(r'\bline \d+\b', 'line N', norm_msg, flags=re.IGNORECASE)
    norm_msg = re.sub(r"'[^']*'", "'X'", norm_msg)
    norm_msg = re.sub(r'"[^"]*"', '"X"', norm_msg)
    norm_msg = re.sub(r'\b\d{4}-\d{2}-\d{2}', 'DATE', norm_msg)
    norm_msg = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', 'UUID', norm_msg, flags=re.IGNORECASE)
    norm_msg = re.sub(r'\d+', 'N', norm_msg)

    # Normalize file path to pattern
    if file_path:
        file_path = file_path.replace('\\', '/')
        # Replace specific filename with wildcard
        norm_file = re.sub(r'/[^/]+\.py$', '/*.py', file_path)
        norm_file = re.sub(r'/[^/]+\.js$', '/*.js', norm_file)
        norm_file = re.sub(r'/[^/]+\.vue$', '/*.vue', norm_file)
    else:
        norm_file = ''

    # Generate fingerprint
    raw = f"{error_type}|{norm_msg}|{norm_file}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def record_error(error_type: str, message: str, file_path: Optional[str] = None) -> int:
    """
    Record an error occurrence.
    Returns error_pattern_id.
    """
    fp = fingerprint(error_type, message, file_path)
    now = datetime.utcnow().isoformat()

    # Normalize file path to pattern
    if file_path:
        file_path = file_path.replace('\\', '/')
        file_pattern = re.sub(r'/[^/]+\.(py|js|vue)$', r'/*.\1', file_path)
    else:
        file_pattern = None

    conn = get_connection()
    try:
        # Check if pattern exists
        cursor = conn.execute(
            "SELECT id, occurrence_count FROM error_patterns WHERE fingerprint = ?",
            (fp,)
        )
        row = cursor.fetchone()

        if row:
            # Update existing pattern
            error_id = row['id']
            conn.execute(
                """UPDATE error_patterns
                   SET last_seen = ?, occurrence_count = occurrence_count + 1
                   WHERE id = ?""",
                (now, error_id)
            )
        else:
            # Insert new pattern
            cursor = conn.execute(
                """INSERT INTO error_patterns
                   (fingerprint, error_type, message_pattern, file_pattern, first_seen, last_seen)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (fp, error_type, message, file_pattern, now, now)
            )
            error_id = cursor.lastrowid

        conn.commit()
        return error_id
    finally:
        conn.close()


def get_strategies(error_type: str, limit: int = 5) -> List[Dict]:
    """
    Get ranked strategies for an error type.
    Sorted by current_score DESC with time decay applied.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """SELECT id, name, description, steps, preconditions, current_score,
                      success_count, failure_count, total_attempts, avg_time_seconds,
                      source, created_at, last_used
               FROM fix_strategies
               WHERE error_type = ?
               ORDER BY current_score DESC
               LIMIT ?""",
            (error_type, limit)
        )

        strategies = []
        now = datetime.utcnow()

        for row in cursor.fetchall():
            strategy = dict(row)

            # Apply time decay to score
            if strategy['last_used']:
                last_used = datetime.fromisoformat(strategy['last_used'])
                days_since = (now - last_used).days
                recency_factor = 1.0 / (1.0 + days_since * 0.1)

                # Recalculate score with decay
                raw_score = strategy['current_score']
                strategy['effective_score'] = raw_score * (0.7 + 0.3 * recency_factor)
            else:
                strategy['effective_score'] = strategy['current_score']

            # Parse JSON fields
            if strategy['steps']:
                strategy['steps'] = json.loads(strategy['steps'])
            if strategy['preconditions']:
                strategy['preconditions'] = json.loads(strategy['preconditions'])

            strategies.append(strategy)

        # Re-sort by effective score
        strategies.sort(key=lambda s: s['effective_score'], reverse=True)

        return strategies
    finally:
        conn.close()


def record_attempt(
    error_pattern_id: int,
    outcome: str,
    strategy_id: Optional[int] = None,
    session_id: Optional[str] = None,
    file_path: Optional[str] = None,
    error_message: Optional[str] = None,
    fix_description: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    git_commit_hash: Optional[str] = None
) -> int:
    """
    Record a fix attempt.
    Returns attempt_id.
    """
    now = datetime.utcnow().isoformat()

    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO fix_attempts
               (error_pattern_id, strategy_id, session_id, file_path, error_message,
                fix_description, outcome, duration_seconds, git_commit_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (error_pattern_id, strategy_id, session_id, file_path, error_message,
             fix_description, outcome, duration_seconds, git_commit_hash, now)
        )
        attempt_id = cursor.lastrowid

        # Update error pattern resolution counts
        if outcome == 'success':
            conn.execute(
                "UPDATE error_patterns SET auto_resolved_count = auto_resolved_count + 1 WHERE id = ?",
                (error_pattern_id,)
            )

        # Update strategy counts if strategy was used
        if strategy_id:
            now = datetime.utcnow().isoformat()
            if outcome == 'success':
                conn.execute(
                    """UPDATE fix_strategies
                       SET success_count = success_count + 1,
                           total_attempts = total_attempts + 1,
                           last_used = ?
                       WHERE id = ?""",
                    (now, strategy_id)
                )
            elif outcome == 'failure':
                conn.execute(
                    """UPDATE fix_strategies
                       SET failure_count = failure_count + 1,
                           total_attempts = total_attempts + 1,
                           last_used = ?
                       WHERE id = ?""",
                    (now, strategy_id)
                )

        # Update file risk scores
        if file_path:
            update_file_risk(conn, file_path, outcome == 'success', outcome == 'reverted')

        conn.commit()
        return attempt_id
    finally:
        conn.close()


def update_strategy_score(strategy_id: int):
    """
    Recalculate strategy score based on historical performance.

    Formula:
    raw_success_rate = success_count / max(total_attempts, 1)
    recency_factor = 1.0 / (1.0 + days_since_last_use * 0.1)
    confidence_factor = min(total_attempts / 10.0, 1.0)
    current_score = 0.6 * raw_success_rate + 0.3 * recency_factor + 0.1 * confidence_factor
    """
    conn = get_connection()
    try:
        # Get strategy stats
        cursor = conn.execute(
            """SELECT success_count, failure_count, total_attempts, last_used
               FROM fix_strategies WHERE id = ?""",
            (strategy_id,)
        )
        row = cursor.fetchone()
        if not row:
            return

        success_count = row['success_count']
        total_attempts = max(row['total_attempts'], 1)
        last_used = row['last_used']

        # Calculate components
        raw_success_rate = success_count / total_attempts

        if last_used:
            last_used_dt = datetime.fromisoformat(last_used)
            days_since = (datetime.utcnow() - last_used_dt).days
            recency_factor = 1.0 / (1.0 + days_since * 0.1)
        else:
            recency_factor = 0.5  # Never used, middle value

        confidence_factor = min(total_attempts / 10.0, 1.0)

        # Final score
        new_score = (
            0.6 * raw_success_rate +
            0.3 * recency_factor +
            0.1 * confidence_factor
        )
        new_score = max(0.0, min(1.0, new_score))  # Clamp to [0, 1]

        # Update database
        conn.execute(
            "UPDATE fix_strategies SET current_score = ? WHERE id = ?",
            (new_score, strategy_id)
        )
        conn.commit()
    finally:
        conn.close()


def update_file_risk(conn, file_path: str, is_success: bool, is_revert: bool):
    """Update file risk score (internal helper)."""
    now = datetime.utcnow().isoformat()

    # Get current risk data
    cursor = conn.execute(
        "SELECT error_count, fix_count, revert_count FROM file_risk_scores WHERE file_path = ?",
        (file_path,)
    )
    row = cursor.fetchone()

    if row:
        error_count = row['error_count'] + (0 if is_success else 1)
        fix_count = row['fix_count'] + (1 if is_success else 0)
        revert_count = row['revert_count'] + (1 if is_revert else 0)
    else:
        error_count = 0 if is_success else 1
        fix_count = 1 if is_success else 0
        revert_count = 1 if is_revert else 0

    # Calculate risk score: errors × revert_weight
    revert_weight = 2.0
    risk_score = error_count + (revert_count * revert_weight)
    risk_score = min(risk_score / 10.0, 1.0)  # Normalize to [0, 1]

    # Upsert
    if row:
        conn.execute(
            """UPDATE file_risk_scores
               SET error_count = ?, fix_count = ?, revert_count = ?, risk_score = ?, updated_at = ?
               WHERE file_path = ?""",
            (error_count, fix_count, revert_count, risk_score, now, file_path)
        )
    else:
        conn.execute(
            """INSERT INTO file_risk_scores
               (file_path, error_count, fix_count, revert_count, risk_score, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (file_path, error_count, fix_count, revert_count, risk_score, now)
        )


def get_file_risk(file_path: str) -> Optional[Dict]:
    """Get risk score for a file."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM file_risk_scores WHERE file_path = ?",
            (file_path,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def check_for_reverts(since_hours: int = 24) -> List[Dict]:
    """
    Check git history for reverts and same-file-fix patterns.
    Returns list of detected reverts.
    """
    since_date = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat()
    reverts = []

    # Check git log for explicit reverts
    try:
        result = subprocess.run(
            ['git', 'log', '--grep=revert', f'--since={since_hours} hours ago', '--oneline'],
            capture_output=True,
            text=True,
            check=True
        )

        for line in result.stdout.strip().split('\n'):
            if line:
                commit_hash = line.split()[0]
                reverts.append({
                    'type': 'explicit_revert',
                    'commit_hash': commit_hash,
                    'message': line
                })
    except subprocess.CalledProcessError:
        pass

    # Check for same-file-fix-within-24h pattern
    conn = get_connection()
    try:
        cursor = conn.execute(
            """SELECT file_path, COUNT(*) as fix_count
               FROM fix_attempts
               WHERE created_at > ? AND outcome = 'success'
               GROUP BY file_path
               HAVING fix_count > 1""",
            (since_date,)
        )

        for row in cursor.fetchall():
            reverts.append({
                'type': 'repeated_fix',
                'file_path': row['file_path'],
                'fix_count': row['fix_count']
            })

        return reverts
    finally:
        conn.close()


def synthesize_rules(min_confidence: float = 0.7, min_evidence: int = 5) -> List[Dict]:
    """
    Auto-generate rules from successful strategies.
    Returns list of newly synthesized rules.
    """
    conn = get_connection()
    try:
        # Find strategies eligible for synthesis
        cursor = conn.execute(
            """SELECT s.id, s.name, s.error_type, s.description, s.steps,
                      s.success_count, s.total_attempts, s.current_score
               FROM fix_strategies s
               WHERE s.success_count >= ?
                 AND s.total_attempts >= ?
                 AND s.current_score >= ?
                 AND s.source != 'synthesized'
                 AND NOT EXISTS (
                     SELECT 1 FROM synthesized_rules r
                     WHERE r.error_type = s.error_type
                       AND r.rule_name = 'Auto: ' || s.name
                       AND r.superseded_by IS NULL
                 )""",
            (min_evidence, min_evidence, min_confidence)
        )

        new_rules = []
        now = datetime.utcnow().isoformat()

        for row in cursor.fetchall():
            strategy = dict(row)
            confidence = strategy['success_count'] / max(strategy['total_attempts'], 1)

            # Generate markdown content
            steps = json.loads(strategy['steps'])
            steps_md = '\n'.join(f"{i+1}. {step}" for i, step in enumerate(steps))

            markdown_content = f"""## {strategy['name']}

**Error Type:** {strategy['error_type']}
**Confidence:** {confidence:.1%} ({strategy['success_count']}/{strategy['total_attempts']} attempts)

**Description:** {strategy['description']}

**When to Apply:**
- Error type matches `{strategy['error_type']}`
- Pattern has been successful in {strategy['success_count']} previous cases

**Steps:**
{steps_md}

**Auto-synthesized:** {now}
"""

            # Insert rule
            rule_cursor = conn.execute(
                """INSERT INTO synthesized_rules
                   (rule_name, error_type, condition_pattern, action_pattern,
                    confidence, evidence_count, markdown_content, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"Auto: {strategy['name']}", strategy['error_type'],
                 strategy['error_type'], json.dumps(steps),
                 confidence, strategy['success_count'], markdown_content, now)
            )

            new_rules.append({
                'id': rule_cursor.lastrowid,
                'rule_name': f"Auto: {strategy['name']}",
                'confidence': confidence,
                'evidence_count': strategy['success_count']
            })

        conn.commit()
        return new_rules
    finally:
        conn.close()


def get_session_metrics(session_id: str) -> Optional[Dict]:
    """Get metrics for a specific session."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM session_metrics WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_session_metrics(session_id: str, **kwargs):
    """Update session metrics."""
    conn = get_connection()
    try:
        # Check if session exists
        cursor = conn.execute(
            "SELECT id FROM session_metrics WHERE session_id = ?",
            (session_id,)
        )
        exists = cursor.fetchone() is not None

        if not exists:
            # Create new session
            now = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT INTO session_metrics (session_id, started_at) VALUES (?, ?)",
                (session_id, now)
            )

        # Update fields
        if kwargs:
            set_clause = ', '.join(f"{k} = ?" for k in kwargs.keys())
            values = list(kwargs.values()) + [session_id]
            conn.execute(
                f"UPDATE session_metrics SET {set_clause} WHERE session_id = ?",
                values
            )

        conn.commit()
    finally:
        conn.close()


def seed_strategies():
    """Populate initial seeded strategies from common patterns."""
    strategies_seed = [
        # ImportError strategies
        {
            "name": "Fix Missing Import",
            "error_type": "ImportError",
            "description": "Add missing import statement at file top",
            "steps": ["Identify missing module", "Add import statement", "Verify import path"],
            "preconditions": {"error_contains": ["cannot import name", "No module named"]}
        },
        {
            "name": "Fix Circular Import",
            "error_type": "ImportError",
            "description": "Resolve circular import by moving import inside function",
            "steps": ["Identify circular dependency", "Move import to function scope", "Test"],
            "preconditions": {"error_contains": ["circular import"]}
        },
        {
            "name": "Update Import Path After Move",
            "error_type": "ImportError",
            "description": "Update import path to reflect file reorganization",
            "steps": ["Find new file location", "Update import path", "Check all references"],
            "preconditions": {"file_moved": True}
        },

        # ModuleNotFoundError strategies
        {
            "name": "Install Missing Package",
            "error_type": "ModuleNotFoundError",
            "description": "Install package via pip/npm",
            "steps": ["Identify package name", "Run pip install or npm install", "Verify installation"],
            "preconditions": {"error_contains": ["No module named"]}
        },

        # AttributeError strategies
        {
            "name": "Fix Undefined Attribute",
            "error_type": "AttributeError",
            "description": "Check for typos or missing class/module attributes",
            "steps": ["Verify attribute name spelling", "Check class definition", "Add missing attribute if needed"],
            "preconditions": {"error_contains": ["has no attribute"]}
        },

        # TestFailure strategies (from test-fixer)
        {
            "name": "Update Stale Selector",
            "error_type": "TestFailure",
            "description": "Update test selector after UI changes",
            "steps": ["Find current data-testid in code", "Update test selector", "Verify test passes"],
            "preconditions": {"error_contains": ["locator", "not found"]}
        },
        {
            "name": "Fix Async Timing",
            "error_type": "TestFailure",
            "description": "Add proper wait for async operations",
            "steps": ["Identify async operation", "Add waitFor or appropriate wait", "Test stability"],
            "preconditions": {"error_contains": ["timeout", "timed out"]}
        },
        {
            "name": "Fix API Mock",
            "error_type": "TestFailure",
            "description": "Update API mock to match current schema",
            "steps": ["Check current API schema", "Update mock data", "Verify mock setup"],
            "preconditions": {"error_contains": ["mock", "API", "response"]}
        },

        # BuildError strategies
        {
            "name": "Clear Build Cache",
            "error_type": "BuildError",
            "description": "Clear build cache and rebuild",
            "steps": ["Clear dist/build folder", "Clear node_modules/.cache if exists", "Rebuild"],
            "preconditions": {"error_contains": ["build failed", "compilation"]}
        },

        # SyntaxError strategies
        {
            "name": "Fix Python Syntax",
            "error_type": "SyntaxError",
            "description": "Fix common Python syntax issues",
            "steps": ["Check for missing colons, parentheses, brackets", "Fix indentation", "Verify syntax"],
            "preconditions": {"file_extension": ".py"}
        },

        # TypeError strategies
        {
            "name": "Fix Type Mismatch",
            "error_type": "TypeError",
            "description": "Fix type mismatches in function calls or operations",
            "steps": ["Check expected type", "Convert or fix argument type", "Test"],
            "preconditions": {"error_contains": ["expected", "got"]}
        },
    ]

    conn = get_connection()
    try:
        now = datetime.utcnow().isoformat()
        inserted = 0

        for strategy in strategies_seed:
            # Check if already exists
            cursor = conn.execute(
                "SELECT id FROM fix_strategies WHERE name = ? AND error_type = ?",
                (strategy['name'], strategy['error_type'])
            )
            if cursor.fetchone():
                continue

            conn.execute(
                """INSERT INTO fix_strategies
                   (name, error_type, description, steps, preconditions, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (strategy['name'], strategy['error_type'], strategy['description'],
                 json.dumps(strategy['steps']), json.dumps(strategy.get('preconditions', {})), now)
            )
            inserted += 1

        conn.commit()
        print(f"[OK] Seeded {inserted} strategies")
        return inserted
    finally:
        conn.close()


def get_stats() -> Dict:
    """Get overall knowledge base statistics."""
    conn = get_connection()
    try:
        stats = {}

        cursor = conn.execute("SELECT COUNT(*) as count FROM error_patterns")
        stats['total_patterns'] = cursor.fetchone()['count']

        cursor = conn.execute("SELECT COUNT(*) as count FROM fix_strategies")
        stats['total_strategies'] = cursor.fetchone()['count']

        cursor = conn.execute("SELECT COUNT(*) as count FROM fix_attempts WHERE outcome = 'success'")
        stats['successful_fixes'] = cursor.fetchone()['count']

        cursor = conn.execute("SELECT COUNT(*) as count FROM fix_attempts WHERE outcome = 'failure'")
        stats['failed_fixes'] = cursor.fetchone()['count']

        cursor = conn.execute("SELECT COUNT(*) as count FROM synthesized_rules WHERE superseded_by IS NULL")
        stats['active_rules'] = cursor.fetchone()['count']

        cursor = conn.execute("SELECT COUNT(*) as count FROM file_risk_scores WHERE risk_score > 0.5")
        stats['risky_files'] = cursor.fetchone()['count']

        return stats
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python db_helper.py [init|seed|stats]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        init_db()
    elif command == "seed":
        if not DB_PATH.exists():
            init_db()
        seed_strategies()
    elif command == "stats":
        if not DB_PATH.exists():
            print("Database not initialized. Run 'python db_helper.py init' first.")
            sys.exit(1)
        stats = get_stats()
        print("\n=== Learning Engine Statistics ===")
        print(f"Error Patterns:      {stats['total_patterns']}")
        print(f"Fix Strategies:      {stats['total_strategies']}")
        print(f"Successful Fixes:    {stats['successful_fixes']}")
        print(f"Failed Fixes:        {stats['failed_fixes']}")
        print(f"Synthesized Rules:   {stats['active_rules']}")
        print(f"Risky Files:         {stats['risky_files']}")
        print("==================================\n")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
