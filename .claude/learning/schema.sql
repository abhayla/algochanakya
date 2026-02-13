-- Learning Engine SQLite Schema
-- Autonomous self-recursive learning system for error patterns and fix strategies

-- Error patterns: Deduplicated errors by fingerprint
CREATE TABLE IF NOT EXISTS error_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT UNIQUE NOT NULL,        -- SHA256(error_type + message_pattern + file_pattern)
    error_type TEXT NOT NULL,                -- 'ImportError', 'TestFailure', 'BuildError', etc.
    message_pattern TEXT NOT NULL,           -- Normalized regex-ready pattern
    file_pattern TEXT,                       -- File glob pattern where error occurs
    first_seen TEXT NOT NULL,                -- ISO timestamp
    last_seen TEXT NOT NULL,
    occurrence_count INTEGER DEFAULT 1,
    auto_resolved_count INTEGER DEFAULT 0,
    manual_resolved_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_error_fingerprint ON error_patterns(fingerprint);
CREATE INDEX IF NOT EXISTS idx_error_type ON error_patterns(error_type);

-- Fix strategies: Ranked approaches for each error type
CREATE TABLE IF NOT EXISTS fix_strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                      -- Human-readable name
    error_type TEXT NOT NULL,                -- Links to error_patterns.error_type
    description TEXT,                        -- What this strategy does
    steps TEXT NOT NULL,                     -- JSON array of step descriptions
    preconditions TEXT,                      -- JSON: when to apply this strategy
    current_score REAL DEFAULT 0.5,          -- 0.0-1.0, higher = better
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    total_attempts INTEGER DEFAULT 0,
    avg_time_seconds REAL,
    source TEXT DEFAULT 'seeded',            -- 'seeded', 'learned', 'synthesized'
    created_at TEXT NOT NULL,
    last_used TEXT
);
CREATE INDEX IF NOT EXISTS idx_strategy_error_type ON fix_strategies(error_type);
CREATE INDEX IF NOT EXISTS idx_strategy_score ON fix_strategies(current_score DESC);

-- Fix attempts: Every fix try with outcome
CREATE TABLE IF NOT EXISTS fix_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    error_pattern_id INTEGER NOT NULL REFERENCES error_patterns(id),
    strategy_id INTEGER REFERENCES fix_strategies(id),
    session_id TEXT,                         -- Claude session identifier
    file_path TEXT,                          -- File where fix was applied
    error_message TEXT,                      -- Full error message
    fix_description TEXT,                    -- What was done
    outcome TEXT NOT NULL,                   -- 'success', 'failure', 'partial', 'reverted'
    duration_seconds REAL,
    git_commit_hash TEXT,                    -- Commit that contains the fix
    was_reverted INTEGER DEFAULT 0,          -- Set to 1 if later detected as reverted
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempt_error ON fix_attempts(error_pattern_id);
CREATE INDEX IF NOT EXISTS idx_attempt_outcome ON fix_attempts(outcome);
CREATE INDEX IF NOT EXISTS idx_attempt_commit ON fix_attempts(git_commit_hash);

-- File risk scores: Track error-prone files
CREATE TABLE IF NOT EXISTS file_risk_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    error_count INTEGER DEFAULT 0,
    fix_count INTEGER DEFAULT 0,
    revert_count INTEGER DEFAULT 0,
    last_error TEXT,
    risk_score REAL DEFAULT 0.0,            -- Calculated: errors × revert_weight
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_file_risk ON file_risk_scores(risk_score DESC);

-- Synthesized rules: Auto-generated patterns from successful strategies
CREATE TABLE IF NOT EXISTS synthesized_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    condition_pattern TEXT NOT NULL,         -- When to apply
    action_pattern TEXT NOT NULL,            -- What to do
    confidence REAL NOT NULL,               -- 0.0-1.0
    evidence_count INTEGER NOT NULL,        -- Number of successful fixes backing this
    markdown_content TEXT NOT NULL,          -- Full rule as markdown (for skill injection)
    created_at TEXT NOT NULL,
    superseded_by INTEGER REFERENCES synthesized_rules(id)
);
CREATE INDEX IF NOT EXISTS idx_rule_confidence ON synthesized_rules(confidence DESC);

-- Session metrics: Per-session tracking
CREATE TABLE IF NOT EXISTS session_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_errors_encountered INTEGER DEFAULT 0,
    total_auto_resolved INTEGER DEFAULT 0,
    total_manual_resolved INTEGER DEFAULT 0,
    total_strategies_tried INTEGER DEFAULT 0,
    new_patterns_discovered INTEGER DEFAULT 0,
    rules_synthesized INTEGER DEFAULT 0
);
