# AutoPilot Database Schema

## PostgreSQL 16 Database Design for Auto-Execution & Adjustment System

**Version:** 1.0  
**Date:** December 2025  
**Database:** PostgreSQL 16

---

## Table of Contents

1. [Schema Overview](#1-schema-overview)
2. [Core Tables](#2-core-tables)
3. [JSONB Column Structures](#3-jsonb-column-structures)
4. [Indexes](#4-indexes)
5. [Constraints & Triggers](#5-constraints--triggers)
6. [Migration Scripts](#6-migration-scripts)
7. [Sample Queries](#7-sample-queries)
8. [Maintenance & Housekeeping](#8-maintenance--housekeeping)

---

## 1. Schema Overview

### 1.1 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTOPILOT SCHEMA                                  │
│                                                                             │
│  ┌──────────────────┐       ┌──────────────────────────┐                   │
│  │      users       │       │  autopilot_user_settings │                   │
│  │  (existing)      │───────│                          │                   │
│  │                  │  1:1  │  - daily_loss_limit      │                   │
│  └────────┬─────────┘       │  - max_capital           │                   │
│           │                 │  - notification_prefs    │                   │
│           │                 └──────────────────────────┘                   │
│           │ 1:N                                                             │
│           ▼                                                                 │
│  ┌──────────────────────────┐                                              │
│  │  autopilot_strategies    │                                              │
│  │                          │                                              │
│  │  - name, status          │                                              │
│  │  - underlying, expiry    │                                              │
│  │  - legs_config (JSONB)   │                                              │
│  │  - entry_conditions      │                                              │
│  │  - adjustment_rules      │                                              │
│  │  - order_settings        │                                              │
│  │  - risk_settings         │                                              │
│  │  - schedule_config       │                                              │
│  │  - runtime_state         │                                              │
│  └────────┬─────────────────┘                                              │
│           │                                                                 │
│           │ 1:N                                                             │
│           ├─────────────────────────────────┐                              │
│           │                                 │                              │
│           ▼                                 ▼                              │
│  ┌────────────────────┐          ┌─────────────────────┐                   │
│  │  autopilot_orders  │          │   autopilot_logs    │                   │
│  │                    │          │                     │                   │
│  │  - kite_order_id   │          │  - event_type       │                   │
│  │  - leg_index       │          │  - event_data       │                   │
│  │  - order_type      │          │  - severity         │                   │
│  │  - status          │          │  - created_at       │                   │
│  │  - slippage        │          │                     │                   │
│  └────────────────────┘          └─────────────────────┘                   │
│                                                                             │
│  ┌──────────────────────────┐    ┌─────────────────────────┐               │
│  │ autopilot_condition_eval │    │ autopilot_daily_summary │               │
│  │                          │    │                         │               │
│  │  - strategy_id           │    │  - user_id, date        │               │
│  │  - condition_id          │    │  - total_pnl            │               │
│  │  - current_value         │    │  - strategies_run       │               │
│  │  - progress_pct          │    │  - orders_executed      │               │
│  │  - evaluated_at          │    │                         │               │
│  └──────────────────────────┘    └─────────────────────────┘               │
│                                                                             │
│  ┌──────────────────────────┐                                              │
│  │ autopilot_templates      │                                              │
│  │                          │                                              │
│  │  - name, description     │                                              │
│  │  - strategy_config       │                                              │
│  │  - is_public             │                                              │
│  │  - usage_count           │                                              │
│  └──────────────────────────┘                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Table Summary

| Table | Purpose | Est. Rows/User | Retention |
|-------|---------|----------------|-----------|
| `autopilot_user_settings` | Global user settings | 1 | Permanent |
| `autopilot_strategies` | Strategy configurations | 5-20 | Permanent |
| `autopilot_orders` | Order execution records | 50-500/day | 90 days |
| `autopilot_logs` | Activity & event logs | 500-5000/day | 90 days |
| `autopilot_condition_eval` | Condition snapshots | 1000-10000/day | 7 days |
| `autopilot_daily_summary` | Daily aggregates | 1/day | 365 days |
| `autopilot_templates` | Saved/shared templates | 10-50 | Permanent |

---

## 2. Core Tables

### 2.1 autopilot_user_settings

Stores global AutoPilot settings per user.

```sql
-- ============================================================================
-- TABLE: autopilot_user_settings
-- Purpose: Global AutoPilot configuration for each user
-- ============================================================================

CREATE TABLE autopilot_user_settings (
    -- Primary Key
    id                      BIGSERIAL PRIMARY KEY,
    
    -- Foreign Key to users table
    user_id                 BIGINT NOT NULL UNIQUE,
    
    -- Risk Limits
    daily_loss_limit        DECIMAL(12,2) NOT NULL DEFAULT 20000.00,
    per_strategy_loss_limit DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    max_capital_deployed    DECIMAL(14,2) NOT NULL DEFAULT 500000.00,
    max_active_strategies   INTEGER NOT NULL DEFAULT 3 CHECK (max_active_strategies BETWEEN 1 AND 10),
    
    -- Time Restrictions
    no_trade_first_minutes  INTEGER NOT NULL DEFAULT 5 CHECK (no_trade_first_minutes BETWEEN 0 AND 60),
    no_trade_last_minutes   INTEGER NOT NULL DEFAULT 5 CHECK (no_trade_last_minutes BETWEEN 0 AND 60),
    
    -- Cooldown Settings
    cooldown_after_loss     BOOLEAN NOT NULL DEFAULT false,
    cooldown_minutes        INTEGER NOT NULL DEFAULT 30 CHECK (cooldown_minutes BETWEEN 5 AND 240),
    cooldown_threshold      DECIMAL(12,2) NOT NULL DEFAULT 5000.00,
    
    -- Default Order Settings (JSONB)
    default_order_settings  JSONB NOT NULL DEFAULT '{
        "order_type": "MARKET",
        "execution_style": "sequential",
        "delay_between_legs": 2,
        "slippage_protection": true,
        "max_slippage_pct": 2.0,
        "price_improvement": false
    }'::jsonb,
    
    -- Notification Preferences (JSONB)
    notification_prefs      JSONB NOT NULL DEFAULT '{
        "enabled": true,
        "channels": ["in_app"],
        "frequency": "realtime",
        "events": {
            "entry_triggered": true,
            "order_executed": true,
            "adjustment_triggered": true,
            "exit_executed": true,
            "error": true,
            "daily_summary": true
        }
    }'::jsonb,
    
    -- Failure Handling
    failure_handling        JSONB NOT NULL DEFAULT '{
        "on_network_error": "retry",
        "on_api_error": "alert",
        "on_margin_insufficient": "cancel",
        "max_retries": 3,
        "retry_delay_seconds": 5
    }'::jsonb,
    
    -- Feature Flags
    paper_trading_mode      BOOLEAN NOT NULL DEFAULT false,
    show_advanced_features  BOOLEAN NOT NULL DEFAULT false,
    
    -- Timestamps
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_user FOREIGN KEY (user_id) 
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_loss_limits CHECK (
        per_strategy_loss_limit <= daily_loss_limit
    ),
    CONSTRAINT chk_capital CHECK (
        max_capital_deployed > 0
    )
);

-- Indexes
CREATE INDEX idx_autopilot_user_settings_user ON autopilot_user_settings(user_id);

-- Comments
COMMENT ON TABLE autopilot_user_settings IS 'Global AutoPilot configuration per user';
COMMENT ON COLUMN autopilot_user_settings.daily_loss_limit IS 'Maximum loss allowed per day across all strategies';
COMMENT ON COLUMN autopilot_user_settings.cooldown_after_loss IS 'Whether to pause trading after significant loss';
```

---

### 2.2 autopilot_strategies

Main table storing strategy configurations and runtime state.

```sql
-- ============================================================================
-- TABLE: autopilot_strategies
-- Purpose: Strategy definitions with all configuration and runtime state
-- ============================================================================

CREATE TYPE autopilot_strategy_status AS ENUM (
    'draft',        -- Being created, not active
    'waiting',      -- Active, waiting for entry conditions
    'active',       -- Position entered, monitoring adjustments
    'pending',      -- Adjustment pending confirmation
    'paused',       -- Manually paused by user
    'completed',    -- Successfully completed (exited)
    'error',        -- Error state, needs attention
    'expired'       -- Strategy expired (schedule ended)
);

CREATE TYPE autopilot_underlying AS ENUM (
    'NIFTY',
    'BANKNIFTY',
    'FINNIFTY',
    'SENSEX'
);

CREATE TYPE autopilot_position_type AS ENUM (
    'intraday',     -- Auto square-off at day end
    'positional'    -- Can carry forward
);

CREATE TABLE autopilot_strategies (
    -- Primary Key
    id                      BIGSERIAL PRIMARY KEY,
    
    -- Foreign Key to users
    user_id                 BIGINT NOT NULL,
    
    -- Basic Info
    name                    VARCHAR(100) NOT NULL,
    description             VARCHAR(500),
    status                  autopilot_strategy_status NOT NULL DEFAULT 'draft',
    
    -- Instrument Configuration
    underlying              autopilot_underlying NOT NULL,
    expiry_type             VARCHAR(20) NOT NULL DEFAULT 'current_week',
    expiry_date             DATE,  -- NULL means auto-select based on expiry_type
    lots                    INTEGER NOT NULL DEFAULT 1 CHECK (lots BETWEEN 1 AND 50),
    position_type           autopilot_position_type NOT NULL DEFAULT 'intraday',
    
    -- Strategy Legs (JSONB array)
    legs_config             JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Entry Conditions (JSONB)
    entry_conditions        JSONB NOT NULL DEFAULT '{
        "logic": "AND",
        "conditions": []
    }'::jsonb,
    
    -- Adjustment Rules (JSONB array)
    adjustment_rules        JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Order Execution Settings (JSONB)
    order_settings          JSONB NOT NULL DEFAULT '{
        "order_type": "MARKET",
        "execution_style": "sequential",
        "leg_sequence": [],
        "delay_between_legs": 2,
        "slippage_protection": {
            "enabled": true,
            "max_per_leg_pct": 2.0,
            "max_total_pct": 5.0,
            "on_exceed": "retry"
        },
        "on_leg_failure": "stop"
    }'::jsonb,
    
    -- Risk Settings (JSONB)
    risk_settings           JSONB NOT NULL DEFAULT '{
        "max_loss": null,
        "max_loss_pct": null,
        "trailing_stop": {
            "enabled": false,
            "trigger_profit": null,
            "trail_amount": null
        },
        "max_margin": null,
        "time_stop": null
    }'::jsonb,
    
    -- Schedule Configuration (JSONB)
    schedule_config         JSONB NOT NULL DEFAULT '{
        "activation_mode": "always",
        "active_days": ["MON", "TUE", "WED", "THU", "FRI"],
        "start_time": "09:15",
        "end_time": "15:30",
        "expiry_days_only": false,
        "date_range": null
    }'::jsonb,
    
    -- Priority (lower number = higher priority)
    priority                INTEGER NOT NULL DEFAULT 100 CHECK (priority BETWEEN 1 AND 1000),
    
    -- Runtime State (JSONB) - Updated during execution
    runtime_state           JSONB DEFAULT NULL,
    
    -- Source/Template Reference
    source_template_id      BIGINT DEFAULT NULL,
    cloned_from_id          BIGINT DEFAULT NULL,
    
    -- Version for optimistic locking
    version                 INTEGER NOT NULL DEFAULT 1,
    
    -- Timestamps
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    activated_at            TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    completed_at            TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    -- Constraints
    CONSTRAINT fk_user FOREIGN KEY (user_id) 
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_template FOREIGN KEY (source_template_id)
        REFERENCES autopilot_templates(id) ON DELETE SET NULL,
    CONSTRAINT fk_cloned_from FOREIGN KEY (cloned_from_id)
        REFERENCES autopilot_strategies(id) ON DELETE SET NULL,
    CONSTRAINT chk_name_not_empty CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_lots_positive CHECK (lots > 0)
);

-- Indexes
CREATE INDEX idx_autopilot_strategies_user ON autopilot_strategies(user_id);
CREATE INDEX idx_autopilot_strategies_status ON autopilot_strategies(status);
CREATE INDEX idx_autopilot_strategies_user_status ON autopilot_strategies(user_id, status);
CREATE INDEX idx_autopilot_strategies_underlying ON autopilot_strategies(underlying);
CREATE INDEX idx_autopilot_strategies_created ON autopilot_strategies(created_at DESC);

-- Partial index for active strategies (most frequently queried)
CREATE INDEX idx_autopilot_strategies_active ON autopilot_strategies(user_id, priority)
    WHERE status IN ('waiting', 'active', 'pending');

-- JSONB indexes for searching
CREATE INDEX idx_autopilot_strategies_legs ON autopilot_strategies 
    USING GIN (legs_config jsonb_path_ops);
CREATE INDEX idx_autopilot_strategies_schedule ON autopilot_strategies 
    USING GIN (schedule_config jsonb_path_ops);

-- Comments
COMMENT ON TABLE autopilot_strategies IS 'AutoPilot strategy configurations with full lifecycle';
COMMENT ON COLUMN autopilot_strategies.runtime_state IS 'Live execution state - positions, P&L, condition progress';
COMMENT ON COLUMN autopilot_strategies.version IS 'Optimistic locking version number';
COMMENT ON COLUMN autopilot_strategies.priority IS 'Execution priority (1=highest, 1000=lowest)';
```

---

### 2.3 autopilot_orders

Records all orders placed by AutoPilot.

```sql
-- ============================================================================
-- TABLE: autopilot_orders
-- Purpose: Track all orders placed by AutoPilot strategies
-- ============================================================================

CREATE TYPE autopilot_order_type AS ENUM (
    'MARKET',
    'LIMIT',
    'SL',
    'SL-M'
);

CREATE TYPE autopilot_transaction_type AS ENUM (
    'BUY',
    'SELL'
);

CREATE TYPE autopilot_order_status AS ENUM (
    'pending',          -- Order created, not yet placed
    'placed',           -- Placed with broker
    'open',             -- Partially filled
    'complete',         -- Fully filled
    'cancelled',        -- Cancelled by user/system
    'rejected',         -- Rejected by broker
    'error'             -- Error during placement
);

CREATE TYPE autopilot_order_purpose AS ENUM (
    'entry',            -- Initial strategy entry
    'adjustment',       -- Position adjustment
    'hedge',            -- Adding hedge
    'exit',             -- Closing position
    'roll_close',       -- Closing leg for roll
    'roll_open',        -- Opening leg for roll
    'kill_switch'       -- Emergency exit
);

CREATE TABLE autopilot_orders (
    -- Primary Key
    id                      BIGSERIAL PRIMARY KEY,
    
    -- Foreign Keys
    strategy_id             BIGINT NOT NULL,
    user_id                 BIGINT NOT NULL,
    
    -- Broker Reference
    kite_order_id           VARCHAR(50) DEFAULT NULL,
    kite_exchange_order_id  VARCHAR(50) DEFAULT NULL,
    
    -- Order Context
    purpose                 autopilot_order_purpose NOT NULL,
    rule_name               VARCHAR(100) DEFAULT NULL,  -- Which adjustment rule triggered this
    leg_index               INTEGER NOT NULL DEFAULT 0,
    
    -- Instrument Details
    exchange                VARCHAR(10) NOT NULL DEFAULT 'NFO',
    tradingsymbol           VARCHAR(50) NOT NULL,
    instrument_token        BIGINT DEFAULT NULL,
    underlying              autopilot_underlying NOT NULL,
    contract_type           VARCHAR(2) NOT NULL CHECK (contract_type IN ('CE', 'PE', 'FUT')),
    strike                  DECIMAL(10,2) DEFAULT NULL,
    expiry                  DATE NOT NULL,
    
    -- Order Details
    transaction_type        autopilot_transaction_type NOT NULL,
    order_type              autopilot_order_type NOT NULL,
    product                 VARCHAR(10) NOT NULL DEFAULT 'NRML',
    quantity                INTEGER NOT NULL CHECK (quantity > 0),
    
    -- Prices
    order_price             DECIMAL(10,2) DEFAULT NULL,  -- Limit price if applicable
    trigger_price           DECIMAL(10,2) DEFAULT NULL,  -- For SL orders
    ltp_at_order            DECIMAL(10,2) DEFAULT NULL,  -- LTP when order was placed
    
    -- Execution Details
    executed_price          DECIMAL(10,2) DEFAULT NULL,
    executed_quantity       INTEGER DEFAULT 0,
    pending_quantity        INTEGER DEFAULT NULL,
    
    -- Slippage Tracking
    slippage_amount         DECIMAL(10,2) DEFAULT NULL,
    slippage_pct            DECIMAL(5,2) DEFAULT NULL,
    
    -- Status
    status                  autopilot_order_status NOT NULL DEFAULT 'pending',
    rejection_reason        VARCHAR(500) DEFAULT NULL,
    
    -- Timing
    order_placed_at         TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    order_filled_at         TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    execution_duration_ms   INTEGER DEFAULT NULL,  -- Time from place to fill
    
    -- Retry Tracking
    retry_count             INTEGER NOT NULL DEFAULT 0,
    parent_order_id         BIGINT DEFAULT NULL,  -- If this is a retry
    
    -- Metadata
    raw_response            JSONB DEFAULT NULL,  -- Raw broker response
    
    -- Timestamps
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_strategy FOREIGN KEY (strategy_id)
        REFERENCES autopilot_strategies(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_parent_order FOREIGN KEY (parent_order_id)
        REFERENCES autopilot_orders(id) ON DELETE SET NULL,
    CONSTRAINT chk_executed_quantity CHECK (
        executed_quantity >= 0 AND executed_quantity <= quantity
    )
);

-- Indexes
CREATE INDEX idx_autopilot_orders_strategy ON autopilot_orders(strategy_id);
CREATE INDEX idx_autopilot_orders_user ON autopilot_orders(user_id);
CREATE INDEX idx_autopilot_orders_kite ON autopilot_orders(kite_order_id) WHERE kite_order_id IS NOT NULL;
CREATE INDEX idx_autopilot_orders_status ON autopilot_orders(status);
CREATE INDEX idx_autopilot_orders_created ON autopilot_orders(created_at DESC);
CREATE INDEX idx_autopilot_orders_user_date ON autopilot_orders(user_id, created_at DESC);

-- Partial index for pending orders (need frequent checking)
CREATE INDEX idx_autopilot_orders_pending ON autopilot_orders(strategy_id, created_at)
    WHERE status IN ('pending', 'placed', 'open');

-- Comments
COMMENT ON TABLE autopilot_orders IS 'All orders placed by AutoPilot strategies';
COMMENT ON COLUMN autopilot_orders.slippage_amount IS 'Difference between LTP at order and executed price';
COMMENT ON COLUMN autopilot_orders.execution_duration_ms IS 'Milliseconds from order placement to fill';
```

---

### 2.4 autopilot_logs

Comprehensive logging for all AutoPilot events.

```sql
-- ============================================================================
-- TABLE: autopilot_logs
-- Purpose: Event logging for audit, debugging, and activity feed
-- ============================================================================

CREATE TYPE autopilot_log_event AS ENUM (
    -- Strategy Lifecycle
    'strategy_created',
    'strategy_activated',
    'strategy_paused',
    'strategy_resumed',
    'strategy_completed',
    'strategy_expired',
    'strategy_error',
    
    -- Entry Events
    'entry_condition_evaluated',
    'entry_condition_triggered',
    'entry_started',
    'entry_completed',
    'entry_failed',
    
    -- Adjustment Events
    'adjustment_condition_evaluated',
    'adjustment_condition_triggered',
    'confirmation_requested',
    'confirmation_received',
    'confirmation_timeout',
    'confirmation_skipped',
    'adjustment_started',
    'adjustment_completed',
    'adjustment_failed',
    
    -- Order Events
    'order_placed',
    'order_filled',
    'order_partial_fill',
    'order_cancelled',
    'order_rejected',
    'order_modified',
    
    -- Exit Events
    'exit_triggered',
    'exit_started',
    'exit_completed',
    'exit_failed',
    
    -- Risk Events
    'risk_limit_warning',
    'risk_limit_breach',
    'daily_loss_limit_hit',
    'margin_warning',
    'margin_insufficient',
    
    -- System Events
    'kill_switch_activated',
    'connection_lost',
    'connection_restored',
    'system_error',
    'api_error',
    
    -- User Actions
    'user_modified_settings',
    'user_force_entry',
    'user_force_exit'
);

CREATE TYPE autopilot_log_severity AS ENUM (
    'debug',
    'info',
    'warning',
    'error',
    'critical'
);

CREATE TABLE autopilot_logs (
    -- Primary Key
    id                      BIGSERIAL PRIMARY KEY,
    
    -- Foreign Keys
    user_id                 BIGINT NOT NULL,
    strategy_id             BIGINT DEFAULT NULL,  -- NULL for user-level events
    order_id                BIGINT DEFAULT NULL,
    
    -- Event Details
    event_type              autopilot_log_event NOT NULL,
    severity                autopilot_log_severity NOT NULL DEFAULT 'info',
    
    -- Context
    rule_name               VARCHAR(100) DEFAULT NULL,
    condition_id            VARCHAR(50) DEFAULT NULL,
    
    -- Event Data (JSONB for flexibility)
    event_data              JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Human-readable message
    message                 VARCHAR(1000) NOT NULL,
    
    -- Timestamp
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_strategy FOREIGN KEY (strategy_id)
        REFERENCES autopilot_strategies(id) ON DELETE SET NULL,
    CONSTRAINT fk_order FOREIGN KEY (order_id)
        REFERENCES autopilot_orders(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_autopilot_logs_user ON autopilot_logs(user_id);
CREATE INDEX idx_autopilot_logs_strategy ON autopilot_logs(strategy_id) WHERE strategy_id IS NOT NULL;
CREATE INDEX idx_autopilot_logs_created ON autopilot_logs(created_at DESC);
CREATE INDEX idx_autopilot_logs_user_created ON autopilot_logs(user_id, created_at DESC);
CREATE INDEX idx_autopilot_logs_event ON autopilot_logs(event_type);
CREATE INDEX idx_autopilot_logs_severity ON autopilot_logs(severity) WHERE severity IN ('error', 'critical');

-- Partial index for recent logs (activity feed)
CREATE INDEX idx_autopilot_logs_recent ON autopilot_logs(user_id, strategy_id, created_at DESC)
    WHERE created_at > NOW() - INTERVAL '7 days';

-- JSONB index for searching event data
CREATE INDEX idx_autopilot_logs_data ON autopilot_logs USING GIN (event_data jsonb_path_ops);

-- Comments
COMMENT ON TABLE autopilot_logs IS 'Comprehensive event log for all AutoPilot activities';
COMMENT ON COLUMN autopilot_logs.event_data IS 'JSON payload with event-specific details';
```

---

### 2.5 autopilot_condition_eval

Tracks condition evaluation snapshots for monitoring.

```sql
-- ============================================================================
-- TABLE: autopilot_condition_eval
-- Purpose: Track condition evaluation progress (for progress bars)
-- ============================================================================

CREATE TABLE autopilot_condition_eval (
    -- Primary Key
    id                      BIGSERIAL PRIMARY KEY,
    
    -- Foreign Keys
    strategy_id             BIGINT NOT NULL,
    
    -- Condition Reference
    condition_type          VARCHAR(20) NOT NULL,  -- 'entry' or 'adjustment'
    condition_index         INTEGER NOT NULL,
    rule_name               VARCHAR(100) DEFAULT NULL,
    
    -- Condition Details
    variable                VARCHAR(50) NOT NULL,
    operator                VARCHAR(20) NOT NULL,
    target_value            JSONB NOT NULL,
    
    -- Evaluation Result
    current_value           JSONB NOT NULL,
    is_satisfied            BOOLEAN NOT NULL,
    progress_pct            DECIMAL(5,2) DEFAULT NULL,  -- 0-100
    distance_to_trigger     VARCHAR(100) DEFAULT NULL,  -- Human readable
    
    -- Timestamp
    evaluated_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_strategy FOREIGN KEY (strategy_id)
        REFERENCES autopilot_strategies(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_autopilot_condition_eval_strategy ON autopilot_condition_eval(strategy_id);
CREATE INDEX idx_autopilot_condition_eval_time ON autopilot_condition_eval(evaluated_at DESC);

-- Partial index for latest evaluations only
CREATE INDEX idx_autopilot_condition_eval_latest ON autopilot_condition_eval(strategy_id, condition_type, condition_index, evaluated_at DESC);

-- Comments
COMMENT ON TABLE autopilot_condition_eval IS 'Condition evaluation snapshots for progress monitoring';
COMMENT ON COLUMN autopilot_condition_eval.progress_pct IS 'Percentage progress toward trigger (0-100)';
```

---

### 2.6 autopilot_daily_summary

Daily aggregated metrics for reporting.

```sql
-- ============================================================================
-- TABLE: autopilot_daily_summary
-- Purpose: Daily aggregated metrics for dashboard and reporting
-- ============================================================================

CREATE TABLE autopilot_daily_summary (
    -- Primary Key
    id                      BIGSERIAL PRIMARY KEY,
    
    -- Foreign Key
    user_id                 BIGINT NOT NULL,
    
    -- Date (one row per user per day)
    summary_date            DATE NOT NULL,
    
    -- Strategy Counts
    strategies_run          INTEGER NOT NULL DEFAULT 0,
    strategies_completed    INTEGER NOT NULL DEFAULT 0,
    strategies_errored      INTEGER NOT NULL DEFAULT 0,
    
    -- Order Counts
    orders_placed           INTEGER NOT NULL DEFAULT 0,
    orders_filled           INTEGER NOT NULL DEFAULT 0,
    orders_rejected         INTEGER NOT NULL DEFAULT 0,
    
    -- P&L
    total_realized_pnl      DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    total_brokerage         DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_slippage          DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    
    -- Best/Worst
    best_strategy_pnl       DECIMAL(12,2) DEFAULT NULL,
    best_strategy_name      VARCHAR(100) DEFAULT NULL,
    worst_strategy_pnl      DECIMAL(12,2) DEFAULT NULL,
    worst_strategy_name     VARCHAR(100) DEFAULT NULL,
    
    -- Execution Stats
    avg_execution_time_ms   INTEGER DEFAULT NULL,
    total_adjustments       INTEGER NOT NULL DEFAULT 0,
    kill_switch_used        BOOLEAN NOT NULL DEFAULT false,
    
    -- Risk Metrics
    max_drawdown            DECIMAL(12,2) DEFAULT NULL,
    peak_margin_used        DECIMAL(14,2) DEFAULT NULL,
    daily_loss_limit_hit    BOOLEAN NOT NULL DEFAULT false,
    
    -- Timestamps
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_user_date UNIQUE (user_id, summary_date)
);

-- Indexes
CREATE INDEX idx_autopilot_daily_summary_user ON autopilot_daily_summary(user_id);
CREATE INDEX idx_autopilot_daily_summary_date ON autopilot_daily_summary(summary_date DESC);
CREATE INDEX idx_autopilot_daily_summary_user_date ON autopilot_daily_summary(user_id, summary_date DESC);

-- Comments
COMMENT ON TABLE autopilot_daily_summary IS 'Daily aggregated AutoPilot metrics for reporting';
```

---

### 2.7 autopilot_templates

Saved and shared strategy templates.

```sql
-- ============================================================================
-- TABLE: autopilot_templates
-- Purpose: Reusable strategy templates (personal and shared)
-- ============================================================================

CREATE TABLE autopilot_templates (
    -- Primary Key
    id                      BIGSERIAL PRIMARY KEY,
    
    -- Owner (NULL for system templates)
    user_id                 BIGINT DEFAULT NULL,
    
    -- Basic Info
    name                    VARCHAR(100) NOT NULL,
    description             VARCHAR(1000),
    
    -- Template Type
    is_system               BOOLEAN NOT NULL DEFAULT false,  -- Built-in templates
    is_public               BOOLEAN NOT NULL DEFAULT false,  -- Shared with community
    
    -- Strategy Configuration (JSONB - same structure as autopilot_strategies)
    strategy_config         JSONB NOT NULL,
    
    -- Categorization
    category                VARCHAR(50) DEFAULT NULL,  -- 'iron_condor', 'straddle', etc.
    tags                    VARCHAR(50)[] DEFAULT '{}',
    risk_level              VARCHAR(20) DEFAULT NULL,  -- 'conservative', 'moderate', 'aggressive'
    
    -- Usage Stats
    usage_count             INTEGER NOT NULL DEFAULT 0,
    avg_rating              DECIMAL(3,2) DEFAULT NULL,
    rating_count            INTEGER NOT NULL DEFAULT 0,
    
    -- Timestamps
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT chk_rating CHECK (
        avg_rating IS NULL OR (avg_rating >= 1 AND avg_rating <= 5)
    )
);

-- Indexes
CREATE INDEX idx_autopilot_templates_user ON autopilot_templates(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_autopilot_templates_public ON autopilot_templates(is_public, usage_count DESC) WHERE is_public = true;
CREATE INDEX idx_autopilot_templates_category ON autopilot_templates(category) WHERE category IS NOT NULL;
CREATE INDEX idx_autopilot_templates_tags ON autopilot_templates USING GIN (tags);

-- Comments
COMMENT ON TABLE autopilot_templates IS 'Reusable strategy templates for quick strategy creation';
```

---

## 3. JSONB Column Structures

### 3.1 legs_config Structure

```jsonc
// autopilot_strategies.legs_config
[
    {
        "id": "leg_1",
        "contract_type": "PE",           // "CE" | "PE" | "FUT"
        "transaction_type": "SELL",      // "BUY" | "SELL"
        "strike_selection": {
            "mode": "atm_offset",        // "fixed" | "atm_offset" | "premium_based" | "delta_based"
            "offset": -200,              // Points from ATM (for atm_offset)
            "fixed_strike": null,        // Exact strike (for fixed)
            "target_premium": null,      // Target premium (for premium_based)
            "target_delta": null         // Target delta (for delta_based)
        },
        "quantity_multiplier": 1,        // Multiplier for lot size
        "execution_order": 1             // Order in leg sequence
    },
    {
        "id": "leg_2",
        "contract_type": "PE",
        "transaction_type": "BUY",
        "strike_selection": {
            "mode": "atm_offset",
            "offset": -400
        },
        "quantity_multiplier": 1,
        "execution_order": 2
    },
    {
        "id": "leg_3",
        "contract_type": "CE",
        "transaction_type": "SELL",
        "strike_selection": {
            "mode": "atm_offset",
            "offset": 200
        },
        "quantity_multiplier": 1,
        "execution_order": 3
    },
    {
        "id": "leg_4",
        "contract_type": "CE",
        "transaction_type": "BUY",
        "strike_selection": {
            "mode": "atm_offset",
            "offset": 400
        },
        "quantity_multiplier": 1,
        "execution_order": 4
    }
]
```

### 3.2 entry_conditions Structure

```jsonc
// autopilot_strategies.entry_conditions
{
    "logic": "AND",                      // "AND" | "OR" | "CUSTOM"
    "custom_expression": null,           // Expression string for CUSTOM logic
    "conditions": [
        {
            "id": "cond_1",
            "enabled": true,
            "variable": "TIME.CURRENT",
            "operator": "greater_than",
            "value": "09:20"
        },
        {
            "id": "cond_2",
            "enabled": true,
            "variable": "VOLATILITY.VIX",
            "operator": "between",
            "value": [13, 18]
        },
        {
            "id": "cond_3",
            "enabled": true,
            "variable": "OI.PCR",
            "operator": "greater_than",
            "value": 0.8
        }
    ]
}
```

### 3.3 adjustment_rules Structure

```jsonc
// autopilot_strategies.adjustment_rules
[
    {
        "id": "rule_1",
        "name": "Stop Loss Hedge",
        "enabled": true,
        "priority": 1,
        "trigger": {
            "logic": "OR",
            "conditions": [
                {
                    "id": "trig_1",
                    "variable": "STRATEGY.PNL",
                    "operator": "less_than",
                    "value": -5000
                }
            ]
        },
        "action": {
            "type": "add_hedge",
            "config": {
                "hedge_type": "both",
                "pe_strike": {
                    "mode": "offset_from_spot",
                    "offset": -200
                },
                "ce_strike": {
                    "mode": "offset_from_spot",
                    "offset": 200
                },
                "quantity_mode": "same_as_position",
                "max_cost": 3000
            }
        },
        "execution_mode": "semi_auto",
        "timeout_seconds": 60,
        "timeout_action": "skip"
    },
    {
        "id": "rule_2",
        "name": "Strike Breach Shift",
        "enabled": true,
        "priority": 2,
        "trigger": {
            "logic": "OR",
            "conditions": [
                {
                    "id": "trig_2",
                    "variable": "SPOT.VS_SOLD_CE",
                    "operator": "breaches",
                    "value": 0
                },
                {
                    "id": "trig_3",
                    "variable": "SPOT.VS_SOLD_PE",
                    "operator": "breaches",
                    "value": 0
                }
            ]
        },
        "action": {
            "type": "shift_strikes",
            "config": {
                "direction": "away_from_spot",
                "shift_amount": 100,
                "shift_side": "breached"
            }
        },
        "execution_mode": "auto",
        "max_executions": 3,
        "cooldown_minutes": 5
    },
    {
        "id": "rule_3",
        "name": "Profit Target Exit",
        "enabled": true,
        "priority": 3,
        "trigger": {
            "logic": "OR",
            "conditions": [
                {
                    "id": "trig_4",
                    "variable": "STRATEGY.PNL",
                    "operator": "greater_than",
                    "value": 8000
                },
                {
                    "id": "trig_5",
                    "variable": "TIME.CURRENT",
                    "operator": "greater_than",
                    "value": "15:15"
                }
            ]
        },
        "action": {
            "type": "exit_all",
            "config": {
                "order_type": "MARKET"
            }
        },
        "execution_mode": "auto"
    }
]
```

### 3.4 runtime_state Structure

```jsonc
// autopilot_strategies.runtime_state
{
    "entered_at": "2025-12-08T09:20:15.000Z",
    "entry_price": {
        "net_credit": 4200,
        "leg_prices": {
            "leg_1": 45.20,
            "leg_2": 28.50,
            "leg_3": 52.30,
            "leg_4": 31.80
        }
    },
    
    "current_positions": [
        {
            "leg_id": "leg_1",
            "tradingsymbol": "NIFTY2512525800PE",
            "transaction_type": "SELL",
            "quantity": 75,
            "average_price": 45.20,
            "last_price": 38.50,
            "unrealized_pnl": 502.50
        },
        // ... other legs
    ],
    
    "margin_used": 124000,
    "current_pnl": 6850,
    "max_pnl": 7200,
    "min_pnl": -2100,
    "max_drawdown": 4500,
    
    "adjustments_made": [
        {
            "rule_id": "rule_1",
            "rule_name": "Stop Loss Hedge",
            "executed_at": "2025-12-08T10:45:32.000Z",
            "legs_added": ["leg_5", "leg_6"],
            "cost": 2490
        }
    ],
    
    "condition_states": {
        "rule_2": {
            "last_evaluated": "2025-12-08T11:20:00.000Z",
            "is_satisfied": false,
            "progress_pct": 65,
            "executions_count": 0
        },
        "rule_3": {
            "last_evaluated": "2025-12-08T11:20:00.000Z",
            "is_satisfied": false,
            "progress_pct": 85.6,
            "executions_count": 0
        }
    },
    
    "last_updated": "2025-12-08T11:20:01.000Z"
}
```

### 3.5 event_data Structure Examples

```jsonc
// autopilot_logs.event_data - Entry Executed
{
    "strategy_name": "Iron Condor Weekly",
    "legs": [
        {
            "tradingsymbol": "NIFTY2512525800PE",
            "transaction_type": "SELL",
            "quantity": 75,
            "order_price": 45.20,
            "executed_price": 45.15,
            "slippage": -0.05
        },
        // ... other legs
    ],
    "total_premium": 4200,
    "margin_required": 124000,
    "execution_time_ms": 2340
}

// autopilot_logs.event_data - Condition Triggered
{
    "rule_name": "Stop Loss Hedge",
    "condition": {
        "variable": "STRATEGY.PNL",
        "operator": "less_than",
        "target": -5000,
        "actual": -5120
    },
    "execution_mode": "semi_auto",
    "proposed_action": {
        "type": "add_hedge",
        "legs_to_add": 2,
        "estimated_cost": 2490
    }
}

// autopilot_logs.event_data - Order Rejected
{
    "order_id": 123456,
    "tradingsymbol": "NIFTY2512525800PE",
    "rejection_reason": "Insufficient margin",
    "required_margin": 62000,
    "available_margin": 45000,
    "retry_attempted": true,
    "retry_count": 1
}
```

---

## 4. Indexes

### 4.1 Summary of All Indexes

```sql
-- ============================================================================
-- INDEX SUMMARY
-- ============================================================================

-- autopilot_user_settings
CREATE INDEX idx_autopilot_user_settings_user ON autopilot_user_settings(user_id);

-- autopilot_strategies
CREATE INDEX idx_autopilot_strategies_user ON autopilot_strategies(user_id);
CREATE INDEX idx_autopilot_strategies_status ON autopilot_strategies(status);
CREATE INDEX idx_autopilot_strategies_user_status ON autopilot_strategies(user_id, status);
CREATE INDEX idx_autopilot_strategies_underlying ON autopilot_strategies(underlying);
CREATE INDEX idx_autopilot_strategies_created ON autopilot_strategies(created_at DESC);
CREATE INDEX idx_autopilot_strategies_active ON autopilot_strategies(user_id, priority)
    WHERE status IN ('waiting', 'active', 'pending');
CREATE INDEX idx_autopilot_strategies_legs ON autopilot_strategies USING GIN (legs_config jsonb_path_ops);
CREATE INDEX idx_autopilot_strategies_schedule ON autopilot_strategies USING GIN (schedule_config jsonb_path_ops);

-- autopilot_orders
CREATE INDEX idx_autopilot_orders_strategy ON autopilot_orders(strategy_id);
CREATE INDEX idx_autopilot_orders_user ON autopilot_orders(user_id);
CREATE INDEX idx_autopilot_orders_kite ON autopilot_orders(kite_order_id) WHERE kite_order_id IS NOT NULL;
CREATE INDEX idx_autopilot_orders_status ON autopilot_orders(status);
CREATE INDEX idx_autopilot_orders_created ON autopilot_orders(created_at DESC);
CREATE INDEX idx_autopilot_orders_user_date ON autopilot_orders(user_id, created_at DESC);
CREATE INDEX idx_autopilot_orders_pending ON autopilot_orders(strategy_id, created_at)
    WHERE status IN ('pending', 'placed', 'open');

-- autopilot_logs
CREATE INDEX idx_autopilot_logs_user ON autopilot_logs(user_id);
CREATE INDEX idx_autopilot_logs_strategy ON autopilot_logs(strategy_id) WHERE strategy_id IS NOT NULL;
CREATE INDEX idx_autopilot_logs_created ON autopilot_logs(created_at DESC);
CREATE INDEX idx_autopilot_logs_user_created ON autopilot_logs(user_id, created_at DESC);
CREATE INDEX idx_autopilot_logs_event ON autopilot_logs(event_type);
CREATE INDEX idx_autopilot_logs_severity ON autopilot_logs(severity) WHERE severity IN ('error', 'critical');
CREATE INDEX idx_autopilot_logs_recent ON autopilot_logs(user_id, strategy_id, created_at DESC)
    WHERE created_at > NOW() - INTERVAL '7 days';
CREATE INDEX idx_autopilot_logs_data ON autopilot_logs USING GIN (event_data jsonb_path_ops);

-- autopilot_condition_eval
CREATE INDEX idx_autopilot_condition_eval_strategy ON autopilot_condition_eval(strategy_id);
CREATE INDEX idx_autopilot_condition_eval_time ON autopilot_condition_eval(evaluated_at DESC);
CREATE INDEX idx_autopilot_condition_eval_latest ON autopilot_condition_eval(
    strategy_id, condition_type, condition_index, evaluated_at DESC
);

-- autopilot_daily_summary
CREATE INDEX idx_autopilot_daily_summary_user ON autopilot_daily_summary(user_id);
CREATE INDEX idx_autopilot_daily_summary_date ON autopilot_daily_summary(summary_date DESC);
CREATE INDEX idx_autopilot_daily_summary_user_date ON autopilot_daily_summary(user_id, summary_date DESC);

-- autopilot_templates
CREATE INDEX idx_autopilot_templates_user ON autopilot_templates(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_autopilot_templates_public ON autopilot_templates(is_public, usage_count DESC) 
    WHERE is_public = true;
CREATE INDEX idx_autopilot_templates_category ON autopilot_templates(category) WHERE category IS NOT NULL;
CREATE INDEX idx_autopilot_templates_tags ON autopilot_templates USING GIN (tags);
```

---

## 5. Constraints & Triggers

### 5.1 Trigger Functions

```sql
-- ============================================================================
-- TRIGGER FUNCTIONS
-- ============================================================================

-- Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all tables
CREATE TRIGGER tr_autopilot_user_settings_updated
    BEFORE UPDATE ON autopilot_user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tr_autopilot_strategies_updated
    BEFORE UPDATE ON autopilot_strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tr_autopilot_orders_updated
    BEFORE UPDATE ON autopilot_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tr_autopilot_daily_summary_updated
    BEFORE UPDATE ON autopilot_daily_summary
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tr_autopilot_templates_updated
    BEFORE UPDATE ON autopilot_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Increment version on strategy update
CREATE OR REPLACE FUNCTION increment_strategy_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_autopilot_strategies_version
    BEFORE UPDATE ON autopilot_strategies
    FOR EACH ROW 
    WHEN (OLD.* IS DISTINCT FROM NEW.*)
    EXECUTE FUNCTION increment_strategy_version();


-- Log strategy status changes
CREATE OR REPLACE FUNCTION log_strategy_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO autopilot_logs (
            user_id, 
            strategy_id, 
            event_type, 
            severity,
            message,
            event_data
        )
        VALUES (
            NEW.user_id,
            NEW.id,
            CASE NEW.status
                WHEN 'waiting' THEN 'strategy_activated'::autopilot_log_event
                WHEN 'active' THEN 'entry_completed'::autopilot_log_event
                WHEN 'paused' THEN 'strategy_paused'::autopilot_log_event
                WHEN 'completed' THEN 'strategy_completed'::autopilot_log_event
                WHEN 'error' THEN 'strategy_error'::autopilot_log_event
                WHEN 'expired' THEN 'strategy_expired'::autopilot_log_event
                ELSE 'strategy_created'::autopilot_log_event
            END,
            CASE NEW.status
                WHEN 'error' THEN 'error'::autopilot_log_severity
                ELSE 'info'::autopilot_log_severity
            END,
            format('Strategy "%s" status changed from %s to %s', 
                   NEW.name, OLD.status, NEW.status),
            jsonb_build_object(
                'old_status', OLD.status,
                'new_status', NEW.status,
                'strategy_name', NEW.name
            )
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_autopilot_strategies_status_log
    AFTER UPDATE ON autopilot_strategies
    FOR EACH ROW EXECUTE FUNCTION log_strategy_status_change();


-- Validate max active strategies
CREATE OR REPLACE FUNCTION check_max_active_strategies()
RETURNS TRIGGER AS $$
DECLARE
    active_count INTEGER;
    max_allowed INTEGER;
BEGIN
    IF NEW.status IN ('waiting', 'active', 'pending') THEN
        -- Get current active count (excluding this strategy)
        SELECT COUNT(*) INTO active_count
        FROM autopilot_strategies
        WHERE user_id = NEW.user_id
          AND status IN ('waiting', 'active', 'pending')
          AND id != NEW.id;
        
        -- Get max allowed
        SELECT max_active_strategies INTO max_allowed
        FROM autopilot_user_settings
        WHERE user_id = NEW.user_id;
        
        IF max_allowed IS NULL THEN
            max_allowed := 3;  -- Default
        END IF;
        
        IF active_count >= max_allowed THEN
            RAISE EXCEPTION 'Maximum active strategies limit (%) reached', max_allowed;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_autopilot_strategies_max_check
    BEFORE INSERT OR UPDATE ON autopilot_strategies
    FOR EACH ROW EXECUTE FUNCTION check_max_active_strategies();


-- Update template usage count
CREATE OR REPLACE FUNCTION increment_template_usage()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.source_template_id IS NOT NULL THEN
        UPDATE autopilot_templates
        SET usage_count = usage_count + 1
        WHERE id = NEW.source_template_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_autopilot_strategies_template_usage
    AFTER INSERT ON autopilot_strategies
    FOR EACH ROW EXECUTE FUNCTION increment_template_usage();
```

### 5.2 Validation Functions

```sql
-- ============================================================================
-- VALIDATION FUNCTIONS
-- ============================================================================

-- Validate legs_config JSONB structure
CREATE OR REPLACE FUNCTION validate_legs_config(legs JSONB)
RETURNS BOOLEAN AS $$
DECLARE
    leg JSONB;
BEGIN
    IF legs IS NULL OR jsonb_typeof(legs) != 'array' THEN
        RETURN false;
    END IF;
    
    FOR leg IN SELECT * FROM jsonb_array_elements(legs)
    LOOP
        IF NOT (
            leg ? 'id' AND
            leg ? 'contract_type' AND
            leg ? 'transaction_type' AND
            leg ? 'strike_selection'
        ) THEN
            RETURN false;
        END IF;
        
        IF NOT (leg->>'contract_type' IN ('CE', 'PE', 'FUT')) THEN
            RETURN false;
        END IF;
        
        IF NOT (leg->>'transaction_type' IN ('BUY', 'SELL')) THEN
            RETURN false;
        END IF;
    END LOOP;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- Validate entry_conditions JSONB structure
CREATE OR REPLACE FUNCTION validate_entry_conditions(conditions JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    IF conditions IS NULL OR jsonb_typeof(conditions) != 'object' THEN
        RETURN false;
    END IF;
    
    IF NOT (conditions ? 'logic' AND conditions ? 'conditions') THEN
        RETURN false;
    END IF;
    
    IF NOT (conditions->>'logic' IN ('AND', 'OR', 'CUSTOM')) THEN
        RETURN false;
    END IF;
    
    IF jsonb_typeof(conditions->'conditions') != 'array' THEN
        RETURN false;
    END IF;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- Add constraint using validation functions
ALTER TABLE autopilot_strategies
ADD CONSTRAINT chk_valid_legs_config 
CHECK (validate_legs_config(legs_config));

ALTER TABLE autopilot_strategies
ADD CONSTRAINT chk_valid_entry_conditions 
CHECK (validate_entry_conditions(entry_conditions));
```

---

## 6. Migration Scripts

### 6.1 Initial Migration (V001)

```sql
-- ============================================================================
-- Migration V001: Create AutoPilot Schema
-- ============================================================================

BEGIN;

-- Create custom types
CREATE TYPE autopilot_strategy_status AS ENUM (
    'draft', 'waiting', 'active', 'pending', 'paused', 
    'completed', 'error', 'expired'
);

CREATE TYPE autopilot_underlying AS ENUM (
    'NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX'
);

CREATE TYPE autopilot_position_type AS ENUM (
    'intraday', 'positional'
);

CREATE TYPE autopilot_order_type AS ENUM (
    'MARKET', 'LIMIT', 'SL', 'SL-M'
);

CREATE TYPE autopilot_transaction_type AS ENUM (
    'BUY', 'SELL'
);

CREATE TYPE autopilot_order_status AS ENUM (
    'pending', 'placed', 'open', 'complete', 
    'cancelled', 'rejected', 'error'
);

CREATE TYPE autopilot_order_purpose AS ENUM (
    'entry', 'adjustment', 'hedge', 'exit', 
    'roll_close', 'roll_open', 'kill_switch'
);

CREATE TYPE autopilot_log_event AS ENUM (
    'strategy_created', 'strategy_activated', 'strategy_paused',
    'strategy_resumed', 'strategy_completed', 'strategy_expired', 
    'strategy_error', 'entry_condition_evaluated', 'entry_condition_triggered',
    'entry_started', 'entry_completed', 'entry_failed',
    'adjustment_condition_evaluated', 'adjustment_condition_triggered',
    'confirmation_requested', 'confirmation_received', 'confirmation_timeout',
    'confirmation_skipped', 'adjustment_started', 'adjustment_completed',
    'adjustment_failed', 'order_placed', 'order_filled', 'order_partial_fill',
    'order_cancelled', 'order_rejected', 'order_modified',
    'exit_triggered', 'exit_started', 'exit_completed', 'exit_failed',
    'risk_limit_warning', 'risk_limit_breach', 'daily_loss_limit_hit',
    'margin_warning', 'margin_insufficient', 'kill_switch_activated',
    'connection_lost', 'connection_restored', 'system_error', 'api_error',
    'user_modified_settings', 'user_force_entry', 'user_force_exit'
);

CREATE TYPE autopilot_log_severity AS ENUM (
    'debug', 'info', 'warning', 'error', 'critical'
);

-- Create tables (in dependency order)
-- 1. autopilot_templates (no foreign keys to other autopilot tables)
CREATE TABLE autopilot_templates (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 BIGINT DEFAULT NULL REFERENCES users(id) ON DELETE SET NULL,
    name                    VARCHAR(100) NOT NULL,
    description             VARCHAR(1000),
    is_system               BOOLEAN NOT NULL DEFAULT false,
    is_public               BOOLEAN NOT NULL DEFAULT false,
    strategy_config         JSONB NOT NULL,
    category                VARCHAR(50) DEFAULT NULL,
    tags                    VARCHAR(50)[] DEFAULT '{}',
    risk_level              VARCHAR(20) DEFAULT NULL,
    usage_count             INTEGER NOT NULL DEFAULT 0,
    avg_rating              DECIMAL(3,2) DEFAULT NULL,
    rating_count            INTEGER NOT NULL DEFAULT 0,
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rating CHECK (
        avg_rating IS NULL OR (avg_rating >= 1 AND avg_rating <= 5)
    )
);

-- 2. autopilot_user_settings
CREATE TABLE autopilot_user_settings (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    daily_loss_limit        DECIMAL(12,2) NOT NULL DEFAULT 20000.00,
    per_strategy_loss_limit DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    max_capital_deployed    DECIMAL(14,2) NOT NULL DEFAULT 500000.00,
    max_active_strategies   INTEGER NOT NULL DEFAULT 3 CHECK (max_active_strategies BETWEEN 1 AND 10),
    no_trade_first_minutes  INTEGER NOT NULL DEFAULT 5 CHECK (no_trade_first_minutes BETWEEN 0 AND 60),
    no_trade_last_minutes   INTEGER NOT NULL DEFAULT 5 CHECK (no_trade_last_minutes BETWEEN 0 AND 60),
    cooldown_after_loss     BOOLEAN NOT NULL DEFAULT false,
    cooldown_minutes        INTEGER NOT NULL DEFAULT 30 CHECK (cooldown_minutes BETWEEN 5 AND 240),
    cooldown_threshold      DECIMAL(12,2) NOT NULL DEFAULT 5000.00,
    default_order_settings  JSONB NOT NULL DEFAULT '{
        "order_type": "MARKET",
        "execution_style": "sequential",
        "delay_between_legs": 2,
        "slippage_protection": true,
        "max_slippage_pct": 2.0,
        "price_improvement": false
    }'::jsonb,
    notification_prefs      JSONB NOT NULL DEFAULT '{
        "enabled": true,
        "channels": ["in_app"],
        "frequency": "realtime",
        "events": {
            "entry_triggered": true,
            "order_executed": true,
            "adjustment_triggered": true,
            "exit_executed": true,
            "error": true,
            "daily_summary": true
        }
    }'::jsonb,
    failure_handling        JSONB NOT NULL DEFAULT '{
        "on_network_error": "retry",
        "on_api_error": "alert",
        "on_margin_insufficient": "cancel",
        "max_retries": 3,
        "retry_delay_seconds": 5
    }'::jsonb,
    paper_trading_mode      BOOLEAN NOT NULL DEFAULT false,
    show_advanced_features  BOOLEAN NOT NULL DEFAULT false,
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_loss_limits CHECK (per_strategy_loss_limit <= daily_loss_limit),
    CONSTRAINT chk_capital CHECK (max_capital_deployed > 0)
);

-- 3. autopilot_strategies
CREATE TABLE autopilot_strategies (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                    VARCHAR(100) NOT NULL,
    description             VARCHAR(500),
    status                  autopilot_strategy_status NOT NULL DEFAULT 'draft',
    underlying              autopilot_underlying NOT NULL,
    expiry_type             VARCHAR(20) NOT NULL DEFAULT 'current_week',
    expiry_date             DATE,
    lots                    INTEGER NOT NULL DEFAULT 1 CHECK (lots BETWEEN 1 AND 50),
    position_type           autopilot_position_type NOT NULL DEFAULT 'intraday',
    legs_config             JSONB NOT NULL DEFAULT '[]'::jsonb,
    entry_conditions        JSONB NOT NULL DEFAULT '{"logic": "AND", "conditions": []}'::jsonb,
    adjustment_rules        JSONB NOT NULL DEFAULT '[]'::jsonb,
    order_settings          JSONB NOT NULL DEFAULT '{
        "order_type": "MARKET",
        "execution_style": "sequential",
        "leg_sequence": [],
        "delay_between_legs": 2,
        "slippage_protection": {"enabled": true, "max_per_leg_pct": 2.0, "max_total_pct": 5.0, "on_exceed": "retry"},
        "on_leg_failure": "stop"
    }'::jsonb,
    risk_settings           JSONB NOT NULL DEFAULT '{
        "max_loss": null,
        "max_loss_pct": null,
        "trailing_stop": {"enabled": false, "trigger_profit": null, "trail_amount": null},
        "max_margin": null,
        "time_stop": null
    }'::jsonb,
    schedule_config         JSONB NOT NULL DEFAULT '{
        "activation_mode": "always",
        "active_days": ["MON", "TUE", "WED", "THU", "FRI"],
        "start_time": "09:15",
        "end_time": "15:30",
        "expiry_days_only": false,
        "date_range": null
    }'::jsonb,
    priority                INTEGER NOT NULL DEFAULT 100 CHECK (priority BETWEEN 1 AND 1000),
    runtime_state           JSONB DEFAULT NULL,
    source_template_id      BIGINT DEFAULT NULL REFERENCES autopilot_templates(id) ON DELETE SET NULL,
    cloned_from_id          BIGINT DEFAULT NULL,
    version                 INTEGER NOT NULL DEFAULT 1,
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    activated_at            TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    completed_at            TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    CONSTRAINT chk_name_not_empty CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_lots_positive CHECK (lots > 0)
);

-- Add self-referencing foreign key
ALTER TABLE autopilot_strategies
ADD CONSTRAINT fk_cloned_from 
FOREIGN KEY (cloned_from_id) REFERENCES autopilot_strategies(id) ON DELETE SET NULL;

-- 4. autopilot_orders
CREATE TABLE autopilot_orders (
    id                      BIGSERIAL PRIMARY KEY,
    strategy_id             BIGINT NOT NULL REFERENCES autopilot_strategies(id) ON DELETE CASCADE,
    user_id                 BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kite_order_id           VARCHAR(50) DEFAULT NULL,
    kite_exchange_order_id  VARCHAR(50) DEFAULT NULL,
    purpose                 autopilot_order_purpose NOT NULL,
    rule_name               VARCHAR(100) DEFAULT NULL,
    leg_index               INTEGER NOT NULL DEFAULT 0,
    exchange                VARCHAR(10) NOT NULL DEFAULT 'NFO',
    tradingsymbol           VARCHAR(50) NOT NULL,
    instrument_token        BIGINT DEFAULT NULL,
    underlying              autopilot_underlying NOT NULL,
    contract_type           VARCHAR(2) NOT NULL CHECK (contract_type IN ('CE', 'PE', 'FUT')),
    strike                  DECIMAL(10,2) DEFAULT NULL,
    expiry                  DATE NOT NULL,
    transaction_type        autopilot_transaction_type NOT NULL,
    order_type              autopilot_order_type NOT NULL,
    product                 VARCHAR(10) NOT NULL DEFAULT 'NRML',
    quantity                INTEGER NOT NULL CHECK (quantity > 0),
    order_price             DECIMAL(10,2) DEFAULT NULL,
    trigger_price           DECIMAL(10,2) DEFAULT NULL,
    ltp_at_order            DECIMAL(10,2) DEFAULT NULL,
    executed_price          DECIMAL(10,2) DEFAULT NULL,
    executed_quantity       INTEGER DEFAULT 0,
    pending_quantity        INTEGER DEFAULT NULL,
    slippage_amount         DECIMAL(10,2) DEFAULT NULL,
    slippage_pct            DECIMAL(5,2) DEFAULT NULL,
    status                  autopilot_order_status NOT NULL DEFAULT 'pending',
    rejection_reason        VARCHAR(500) DEFAULT NULL,
    order_placed_at         TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    order_filled_at         TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    execution_duration_ms   INTEGER DEFAULT NULL,
    retry_count             INTEGER NOT NULL DEFAULT 0,
    parent_order_id         BIGINT DEFAULT NULL,
    raw_response            JSONB DEFAULT NULL,
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_executed_quantity CHECK (executed_quantity >= 0 AND executed_quantity <= quantity)
);

-- Add self-referencing foreign key
ALTER TABLE autopilot_orders
ADD CONSTRAINT fk_parent_order 
FOREIGN KEY (parent_order_id) REFERENCES autopilot_orders(id) ON DELETE SET NULL;

-- 5. autopilot_logs
CREATE TABLE autopilot_logs (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy_id             BIGINT DEFAULT NULL REFERENCES autopilot_strategies(id) ON DELETE SET NULL,
    order_id                BIGINT DEFAULT NULL REFERENCES autopilot_orders(id) ON DELETE SET NULL,
    event_type              autopilot_log_event NOT NULL,
    severity                autopilot_log_severity NOT NULL DEFAULT 'info',
    rule_name               VARCHAR(100) DEFAULT NULL,
    condition_id            VARCHAR(50) DEFAULT NULL,
    event_data              JSONB NOT NULL DEFAULT '{}'::jsonb,
    message                 VARCHAR(1000) NOT NULL,
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 6. autopilot_condition_eval
CREATE TABLE autopilot_condition_eval (
    id                      BIGSERIAL PRIMARY KEY,
    strategy_id             BIGINT NOT NULL REFERENCES autopilot_strategies(id) ON DELETE CASCADE,
    condition_type          VARCHAR(20) NOT NULL,
    condition_index         INTEGER NOT NULL,
    rule_name               VARCHAR(100) DEFAULT NULL,
    variable                VARCHAR(50) NOT NULL,
    operator                VARCHAR(20) NOT NULL,
    target_value            JSONB NOT NULL,
    current_value           JSONB NOT NULL,
    is_satisfied            BOOLEAN NOT NULL,
    progress_pct            DECIMAL(5,2) DEFAULT NULL,
    distance_to_trigger     VARCHAR(100) DEFAULT NULL,
    evaluated_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 7. autopilot_daily_summary
CREATE TABLE autopilot_daily_summary (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary_date            DATE NOT NULL,
    strategies_run          INTEGER NOT NULL DEFAULT 0,
    strategies_completed    INTEGER NOT NULL DEFAULT 0,
    strategies_errored      INTEGER NOT NULL DEFAULT 0,
    orders_placed           INTEGER NOT NULL DEFAULT 0,
    orders_filled           INTEGER NOT NULL DEFAULT 0,
    orders_rejected         INTEGER NOT NULL DEFAULT 0,
    total_realized_pnl      DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    total_brokerage         DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_slippage          DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    best_strategy_pnl       DECIMAL(12,2) DEFAULT NULL,
    best_strategy_name      VARCHAR(100) DEFAULT NULL,
    worst_strategy_pnl      DECIMAL(12,2) DEFAULT NULL,
    worst_strategy_name     VARCHAR(100) DEFAULT NULL,
    avg_execution_time_ms   INTEGER DEFAULT NULL,
    total_adjustments       INTEGER NOT NULL DEFAULT 0,
    kill_switch_used        BOOLEAN NOT NULL DEFAULT false,
    max_drawdown            DECIMAL(12,2) DEFAULT NULL,
    peak_margin_used        DECIMAL(14,2) DEFAULT NULL,
    daily_loss_limit_hit    BOOLEAN NOT NULL DEFAULT false,
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_date UNIQUE (user_id, summary_date)
);

-- Create all indexes
-- [All indexes from Section 4.1 go here]

-- Create triggers
-- [All triggers from Section 5.1 go here]

COMMIT;
```

### 6.2 Rollback Migration

```sql
-- ============================================================================
-- Migration V001 Rollback: Drop AutoPilot Schema
-- ============================================================================

BEGIN;

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS autopilot_daily_summary CASCADE;
DROP TABLE IF EXISTS autopilot_condition_eval CASCADE;
DROP TABLE IF EXISTS autopilot_logs CASCADE;
DROP TABLE IF EXISTS autopilot_orders CASCADE;
DROP TABLE IF EXISTS autopilot_strategies CASCADE;
DROP TABLE IF EXISTS autopilot_user_settings CASCADE;
DROP TABLE IF EXISTS autopilot_templates CASCADE;

-- Drop custom types
DROP TYPE IF EXISTS autopilot_log_severity CASCADE;
DROP TYPE IF EXISTS autopilot_log_event CASCADE;
DROP TYPE IF EXISTS autopilot_order_purpose CASCADE;
DROP TYPE IF EXISTS autopilot_order_status CASCADE;
DROP TYPE IF EXISTS autopilot_transaction_type CASCADE;
DROP TYPE IF EXISTS autopilot_order_type CASCADE;
DROP TYPE IF EXISTS autopilot_position_type CASCADE;
DROP TYPE IF EXISTS autopilot_underlying CASCADE;
DROP TYPE IF EXISTS autopilot_strategy_status CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
DROP FUNCTION IF EXISTS increment_strategy_version CASCADE;
DROP FUNCTION IF EXISTS log_strategy_status_change CASCADE;
DROP FUNCTION IF EXISTS check_max_active_strategies CASCADE;
DROP FUNCTION IF EXISTS increment_template_usage CASCADE;
DROP FUNCTION IF EXISTS validate_legs_config CASCADE;
DROP FUNCTION IF EXISTS validate_entry_conditions CASCADE;

COMMIT;
```

---

## 7. Sample Queries

### 7.1 Dashboard Queries

```sql
-- ============================================================================
-- DASHBOARD QUERIES
-- ============================================================================

-- Get active strategies count and status for dashboard
SELECT 
    COUNT(*) FILTER (WHERE status = 'active') as active_count,
    COUNT(*) FILTER (WHERE status = 'waiting') as waiting_count,
    COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
    COUNT(*) FILTER (WHERE status IN ('active', 'waiting', 'pending')) as total_running
FROM autopilot_strategies
WHERE user_id = :user_id;


-- Get today's P&L across all strategies
SELECT 
    COALESCE(SUM((runtime_state->>'current_pnl')::decimal), 0) as total_unrealized_pnl,
    COALESCE(SUM(ds.total_realized_pnl), 0) as total_realized_pnl
FROM autopilot_strategies s
LEFT JOIN autopilot_daily_summary ds 
    ON ds.user_id = s.user_id AND ds.summary_date = CURRENT_DATE
WHERE s.user_id = :user_id
  AND s.status IN ('active', 'waiting', 'pending', 'completed')
  AND DATE(s.activated_at) = CURRENT_DATE;


-- Get running strategies with details
SELECT 
    s.id,
    s.name,
    s.status,
    s.underlying,
    s.lots,
    s.runtime_state->>'current_pnl' as current_pnl,
    s.runtime_state->>'margin_used' as margin_used,
    jsonb_array_length(s.legs_config) as leg_count,
    s.priority,
    s.activated_at
FROM autopilot_strategies s
WHERE s.user_id = :user_id
  AND s.status IN ('active', 'waiting', 'pending')
ORDER BY s.priority ASC, s.activated_at DESC;


-- Get recent activity for feed
SELECT 
    l.id,
    l.event_type,
    l.severity,
    l.message,
    l.event_data,
    l.created_at,
    s.name as strategy_name
FROM autopilot_logs l
LEFT JOIN autopilot_strategies s ON s.id = l.strategy_id
WHERE l.user_id = :user_id
  AND l.created_at > NOW() - INTERVAL '24 hours'
ORDER BY l.created_at DESC
LIMIT 50;


-- Get risk gauge data
SELECT 
    us.daily_loss_limit,
    us.max_capital_deployed,
    us.max_active_strategies,
    COALESCE(
        (SELECT SUM(total_realized_pnl) 
         FROM autopilot_daily_summary 
         WHERE user_id = :user_id AND summary_date = CURRENT_DATE),
        0
    ) as daily_loss_used,
    COALESCE(
        (SELECT SUM((runtime_state->>'margin_used')::decimal)
         FROM autopilot_strategies
         WHERE user_id = :user_id AND status IN ('active', 'waiting', 'pending')),
        0
    ) as capital_used,
    (SELECT COUNT(*) 
     FROM autopilot_strategies 
     WHERE user_id = :user_id AND status IN ('active', 'waiting', 'pending')
    ) as active_strategies_count
FROM autopilot_user_settings us
WHERE us.user_id = :user_id;
```

### 7.2 Strategy Queries

```sql
-- ============================================================================
-- STRATEGY QUERIES
-- ============================================================================

-- Get strategy with all details
SELECT 
    s.*,
    t.name as template_name,
    cloned.name as cloned_from_name
FROM autopilot_strategies s
LEFT JOIN autopilot_templates t ON t.id = s.source_template_id
LEFT JOIN autopilot_strategies cloned ON cloned.id = s.cloned_from_id
WHERE s.id = :strategy_id AND s.user_id = :user_id;


-- Get strategy orders
SELECT 
    o.*
FROM autopilot_orders o
WHERE o.strategy_id = :strategy_id
ORDER BY o.created_at DESC;


-- Get strategy logs
SELECT 
    l.*
FROM autopilot_logs l
WHERE l.strategy_id = :strategy_id
ORDER BY l.created_at DESC
LIMIT 100;


-- Get condition evaluation history
SELECT 
    ce.condition_type,
    ce.condition_index,
    ce.rule_name,
    ce.variable,
    ce.operator,
    ce.target_value,
    ce.current_value,
    ce.is_satisfied,
    ce.progress_pct,
    ce.evaluated_at
FROM autopilot_condition_eval ce
WHERE ce.strategy_id = :strategy_id
  AND ce.evaluated_at > NOW() - INTERVAL '1 hour'
ORDER BY ce.evaluated_at DESC;


-- Create new strategy
INSERT INTO autopilot_strategies (
    user_id, name, description, underlying, expiry_type, lots,
    position_type, legs_config, entry_conditions, adjustment_rules,
    order_settings, risk_settings, schedule_config, priority,
    source_template_id
)
VALUES (
    :user_id, :name, :description, :underlying, :expiry_type, :lots,
    :position_type, :legs_config, :entry_conditions, :adjustment_rules,
    :order_settings, :risk_settings, :schedule_config, :priority,
    :template_id
)
RETURNING *;


-- Activate strategy
UPDATE autopilot_strategies
SET 
    status = 'waiting',
    activated_at = NOW()
WHERE id = :strategy_id 
  AND user_id = :user_id
  AND status = 'draft'
RETURNING *;


-- Update runtime state (frequent operation)
UPDATE autopilot_strategies
SET 
    runtime_state = :runtime_state,
    status = CASE 
        WHEN :has_positions THEN 'active'::autopilot_strategy_status
        ELSE status
    END
WHERE id = :strategy_id
RETURNING version;


-- Clone strategy
INSERT INTO autopilot_strategies (
    user_id, name, description, underlying, expiry_type, lots,
    position_type, legs_config, entry_conditions, adjustment_rules,
    order_settings, risk_settings, schedule_config, priority,
    cloned_from_id
)
SELECT 
    user_id,
    name || ' (Copy)',
    description,
    underlying,
    expiry_type,
    lots,
    position_type,
    legs_config,
    entry_conditions,
    adjustment_rules,
    order_settings,
    risk_settings,
    schedule_config,
    priority + 1,
    id
FROM autopilot_strategies
WHERE id = :strategy_id AND user_id = :user_id
RETURNING *;
```

### 7.3 Order Queries

```sql
-- ============================================================================
-- ORDER QUERIES
-- ============================================================================

-- Insert new order
INSERT INTO autopilot_orders (
    strategy_id, user_id, purpose, rule_name, leg_index,
    tradingsymbol, underlying, contract_type, strike, expiry,
    transaction_type, order_type, quantity, order_price, ltp_at_order
)
VALUES (
    :strategy_id, :user_id, :purpose, :rule_name, :leg_index,
    :tradingsymbol, :underlying, :contract_type, :strike, :expiry,
    :transaction_type, :order_type, :quantity, :order_price, :ltp_at_order
)
RETURNING *;


-- Update order after placement
UPDATE autopilot_orders
SET 
    kite_order_id = :kite_order_id,
    status = 'placed',
    order_placed_at = NOW()
WHERE id = :order_id
RETURNING *;


-- Update order after fill
UPDATE autopilot_orders
SET 
    status = 'complete',
    executed_price = :executed_price,
    executed_quantity = :executed_quantity,
    slippage_amount = :executed_price - ltp_at_order,
    slippage_pct = ((:executed_price - ltp_at_order) / ltp_at_order) * 100,
    order_filled_at = NOW(),
    execution_duration_ms = EXTRACT(EPOCH FROM (NOW() - order_placed_at)) * 1000
WHERE id = :order_id
RETURNING *;


-- Get pending orders that need status check
SELECT 
    o.*,
    s.name as strategy_name
FROM autopilot_orders o
JOIN autopilot_strategies s ON s.id = o.strategy_id
WHERE o.status IN ('placed', 'open')
  AND o.order_placed_at < NOW() - INTERVAL '5 seconds'
ORDER BY o.order_placed_at ASC;


-- Calculate total slippage for a strategy entry
SELECT 
    SUM(slippage_amount * quantity) as total_slippage,
    AVG(slippage_pct) as avg_slippage_pct,
    SUM(CASE WHEN transaction_type = 'SELL' THEN executed_price * quantity ELSE 0 END) as total_credit,
    SUM(CASE WHEN transaction_type = 'BUY' THEN executed_price * quantity ELSE 0 END) as total_debit,
    AVG(execution_duration_ms) as avg_execution_time
FROM autopilot_orders
WHERE strategy_id = :strategy_id
  AND purpose = 'entry'
  AND status = 'complete';
```

### 7.4 Reporting Queries

```sql
-- ============================================================================
-- REPORTING QUERIES
-- ============================================================================

-- Get daily summary for a date range
SELECT 
    summary_date,
    strategies_run,
    strategies_completed,
    total_realized_pnl,
    total_slippage,
    best_strategy_name,
    best_strategy_pnl,
    worst_strategy_name,
    worst_strategy_pnl
FROM autopilot_daily_summary
WHERE user_id = :user_id
  AND summary_date BETWEEN :start_date AND :end_date
ORDER BY summary_date DESC;


-- Performance by underlying
SELECT 
    underlying,
    COUNT(*) as strategy_count,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
    AVG((runtime_state->>'current_pnl')::decimal) as avg_pnl,
    SUM((runtime_state->>'current_pnl')::decimal) as total_pnl
FROM autopilot_strategies
WHERE user_id = :user_id
  AND created_at > NOW() - INTERVAL '30 days'
GROUP BY underlying
ORDER BY total_pnl DESC;


-- Most used adjustment rules
SELECT 
    l.rule_name,
    COUNT(*) as trigger_count,
    COUNT(*) FILTER (WHERE event_type = 'adjustment_completed') as success_count,
    AVG((event_data->>'execution_time_ms')::integer) as avg_execution_time
FROM autopilot_logs l
WHERE l.user_id = :user_id
  AND l.event_type IN ('adjustment_condition_triggered', 'adjustment_completed')
  AND l.rule_name IS NOT NULL
  AND l.created_at > NOW() - INTERVAL '30 days'
GROUP BY l.rule_name
ORDER BY trigger_count DESC;


-- Export orders for a date range
SELECT 
    o.created_at,
    s.name as strategy_name,
    o.purpose,
    o.rule_name,
    o.tradingsymbol,
    o.transaction_type,
    o.order_type,
    o.quantity,
    o.ltp_at_order,
    o.executed_price,
    o.slippage_pct,
    o.status,
    o.execution_duration_ms
FROM autopilot_orders o
JOIN autopilot_strategies s ON s.id = o.strategy_id
WHERE o.user_id = :user_id
  AND o.created_at BETWEEN :start_date AND :end_date
ORDER BY o.created_at DESC;
```

---

## 8. Maintenance & Housekeeping

### 8.1 Data Retention Jobs

```sql
-- ============================================================================
-- HOUSEKEEPING PROCEDURES
-- ============================================================================

-- Delete old condition evaluations (keep 7 days)
CREATE OR REPLACE PROCEDURE cleanup_condition_evals()
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM autopilot_condition_eval
    WHERE evaluated_at < NOW() - INTERVAL '7 days';
    
    RAISE NOTICE 'Deleted % old condition evaluations', ROW_COUNT;
END;
$$;


-- Delete old logs (keep 90 days)
CREATE OR REPLACE PROCEDURE cleanup_old_logs()
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM autopilot_logs
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    RAISE NOTICE 'Deleted % old logs', ROW_COUNT;
END;
$$;


-- Delete old orders (keep 90 days)
CREATE OR REPLACE PROCEDURE cleanup_old_orders()
LANGUAGE plpgsql
AS $$
BEGIN
    -- First, mark old strategies as archived if needed
    UPDATE autopilot_strategies
    SET status = 'expired'
    WHERE status IN ('completed', 'error')
      AND completed_at < NOW() - INTERVAL '90 days';
    
    -- Then delete old orders
    DELETE FROM autopilot_orders
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    RAISE NOTICE 'Deleted % old orders', ROW_COUNT;
END;
$$;


-- Archive old daily summaries (keep 365 days)
CREATE OR REPLACE PROCEDURE cleanup_old_summaries()
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM autopilot_daily_summary
    WHERE summary_date < CURRENT_DATE - INTERVAL '365 days';
    
    RAISE NOTICE 'Deleted % old daily summaries', ROW_COUNT;
END;
$$;


-- Generate daily summary (run at end of day)
CREATE OR REPLACE PROCEDURE generate_daily_summary(p_user_id BIGINT, p_date DATE DEFAULT CURRENT_DATE)
LANGUAGE plpgsql
AS $$
DECLARE
    v_summary RECORD;
BEGIN
    -- Calculate summary
    SELECT 
        COUNT(DISTINCT s.id) FILTER (WHERE s.activated_at::date = p_date) as strategies_run,
        COUNT(DISTINCT s.id) FILTER (WHERE s.status = 'completed' AND s.completed_at::date = p_date) as strategies_completed,
        COUNT(DISTINCT s.id) FILTER (WHERE s.status = 'error') as strategies_errored,
        COUNT(o.id) as orders_placed,
        COUNT(o.id) FILTER (WHERE o.status = 'complete') as orders_filled,
        COUNT(o.id) FILTER (WHERE o.status = 'rejected') as orders_rejected,
        COALESCE(SUM(
            CASE WHEN o.status = 'complete' AND o.transaction_type = 'SELL' THEN o.executed_price * o.quantity 
                 WHEN o.status = 'complete' AND o.transaction_type = 'BUY' THEN -o.executed_price * o.quantity 
                 ELSE 0 
            END
        ), 0) as total_realized_pnl,
        COALESCE(SUM(o.slippage_amount * o.quantity) FILTER (WHERE o.status = 'complete'), 0) as total_slippage,
        AVG(o.execution_duration_ms) FILTER (WHERE o.status = 'complete') as avg_execution_time,
        COUNT(l.id) FILTER (WHERE l.event_type LIKE 'adjustment%') as total_adjustments,
        BOOL_OR(l.event_type = 'kill_switch_activated') as kill_switch_used,
        BOOL_OR(l.event_type = 'daily_loss_limit_hit') as daily_loss_limit_hit
    INTO v_summary
    FROM autopilot_strategies s
    LEFT JOIN autopilot_orders o ON o.strategy_id = s.id AND o.created_at::date = p_date
    LEFT JOIN autopilot_logs l ON l.user_id = s.user_id AND l.created_at::date = p_date
    WHERE s.user_id = p_user_id;
    
    -- Upsert summary
    INSERT INTO autopilot_daily_summary (
        user_id, summary_date, strategies_run, strategies_completed, strategies_errored,
        orders_placed, orders_filled, orders_rejected, total_realized_pnl, total_slippage,
        avg_execution_time_ms, total_adjustments, kill_switch_used, daily_loss_limit_hit
    )
    VALUES (
        p_user_id, p_date, 
        COALESCE(v_summary.strategies_run, 0),
        COALESCE(v_summary.strategies_completed, 0),
        COALESCE(v_summary.strategies_errored, 0),
        COALESCE(v_summary.orders_placed, 0),
        COALESCE(v_summary.orders_filled, 0),
        COALESCE(v_summary.orders_rejected, 0),
        COALESCE(v_summary.total_realized_pnl, 0),
        COALESCE(v_summary.total_slippage, 0),
        v_summary.avg_execution_time,
        COALESCE(v_summary.total_adjustments, 0),
        COALESCE(v_summary.kill_switch_used, false),
        COALESCE(v_summary.daily_loss_limit_hit, false)
    )
    ON CONFLICT (user_id, summary_date) DO UPDATE
    SET 
        strategies_run = EXCLUDED.strategies_run,
        strategies_completed = EXCLUDED.strategies_completed,
        strategies_errored = EXCLUDED.strategies_errored,
        orders_placed = EXCLUDED.orders_placed,
        orders_filled = EXCLUDED.orders_filled,
        orders_rejected = EXCLUDED.orders_rejected,
        total_realized_pnl = EXCLUDED.total_realized_pnl,
        total_slippage = EXCLUDED.total_slippage,
        avg_execution_time_ms = EXCLUDED.avg_execution_time_ms,
        total_adjustments = EXCLUDED.total_adjustments,
        kill_switch_used = EXCLUDED.kill_switch_used,
        daily_loss_limit_hit = EXCLUDED.daily_loss_limit_hit,
        updated_at = NOW();
END;
$$;


-- Master cleanup procedure (run daily)
CREATE OR REPLACE PROCEDURE run_daily_cleanup()
LANGUAGE plpgsql
AS $$
BEGIN
    CALL cleanup_condition_evals();
    CALL cleanup_old_logs();
    CALL cleanup_old_orders();
    CALL cleanup_old_summaries();
    
    -- Vacuum tables
    VACUUM ANALYZE autopilot_condition_eval;
    VACUUM ANALYZE autopilot_logs;
    VACUUM ANALYZE autopilot_orders;
    
    RAISE NOTICE 'Daily cleanup completed at %', NOW();
END;
$$;
```

### 8.2 Scheduled Jobs (pg_cron)

```sql
-- ============================================================================
-- SCHEDULED JOBS (requires pg_cron extension)
-- ============================================================================

-- Install pg_cron if not already installed
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule daily cleanup at 1:00 AM IST (19:30 UTC previous day)
SELECT cron.schedule('autopilot-daily-cleanup', '30 19 * * *', 'CALL run_daily_cleanup()');

-- Schedule summary generation at 4:00 PM IST (10:30 UTC)
SELECT cron.schedule('autopilot-daily-summary', '30 10 * * 1-5', 
    $$
    DO $$
    DECLARE
        r RECORD;
    BEGIN
        FOR r IN SELECT DISTINCT user_id FROM autopilot_strategies WHERE status != 'draft'
        LOOP
            CALL generate_daily_summary(r.user_id);
        END LOOP;
    END;
    $$
    $$
);

-- List scheduled jobs
SELECT * FROM cron.job;

-- To remove a job:
-- SELECT cron.unschedule('autopilot-daily-cleanup');
```

### 8.3 Monitoring Queries

```sql
-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) as table_size,
    pg_size_pretty(pg_indexes_size(schemaname || '.' || tablename)) as index_size
FROM pg_tables
WHERE tablename LIKE 'autopilot%'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;


-- Row counts
SELECT 
    'autopilot_strategies' as table_name, COUNT(*) as row_count FROM autopilot_strategies
UNION ALL
SELECT 'autopilot_orders', COUNT(*) FROM autopilot_orders
UNION ALL
SELECT 'autopilot_logs', COUNT(*) FROM autopilot_logs
UNION ALL
SELECT 'autopilot_condition_eval', COUNT(*) FROM autopilot_condition_eval
UNION ALL
SELECT 'autopilot_daily_summary', COUNT(*) FROM autopilot_daily_summary
UNION ALL
SELECT 'autopilot_templates', COUNT(*) FROM autopilot_templates;


-- Index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE tablename LIKE 'autopilot%'
ORDER BY idx_scan DESC;


-- Slow queries (requires pg_stat_statements)
SELECT 
    query,
    calls,
    mean_exec_time,
    total_exec_time
FROM pg_stat_statements
WHERE query LIKE '%autopilot%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Appendix: Quick Reference

### A. Table Relationships

| Parent Table | Child Table | Relationship | ON DELETE |
|--------------|-------------|--------------|-----------|
| users | autopilot_user_settings | 1:1 | CASCADE |
| users | autopilot_strategies | 1:N | CASCADE |
| users | autopilot_orders | 1:N | CASCADE |
| users | autopilot_logs | 1:N | CASCADE |
| users | autopilot_daily_summary | 1:N | CASCADE |
| users | autopilot_templates | 1:N | SET NULL |
| autopilot_strategies | autopilot_orders | 1:N | CASCADE |
| autopilot_strategies | autopilot_logs | 1:N | SET NULL |
| autopilot_strategies | autopilot_condition_eval | 1:N | CASCADE |
| autopilot_templates | autopilot_strategies | 1:N | SET NULL |

### B. JSONB Column Summary

| Table | Column | Purpose |
|-------|--------|---------|
| autopilot_user_settings | default_order_settings | Order defaults |
| autopilot_user_settings | notification_prefs | Notification config |
| autopilot_user_settings | failure_handling | Error handling config |
| autopilot_strategies | legs_config | Strategy leg definitions |
| autopilot_strategies | entry_conditions | Entry trigger rules |
| autopilot_strategies | adjustment_rules | Adjustment definitions |
| autopilot_strategies | order_settings | Order execution config |
| autopilot_strategies | risk_settings | Risk management config |
| autopilot_strategies | schedule_config | Schedule settings |
| autopilot_strategies | runtime_state | Live execution state |
| autopilot_logs | event_data | Event-specific payload |
| autopilot_orders | raw_response | Broker API response |
| autopilot_templates | strategy_config | Template configuration |

### C. Status State Machine

```
                    ┌──────────┐
                    │  draft   │ ◄──── Create
                    └────┬─────┘
                         │ Activate
                         ▼
                    ┌──────────┐
              ┌─────┤ waiting  │◄────────────────┐
              │     └────┬─────┘                 │
              │          │ Entry Triggered       │ Resume
              │          ▼                       │
              │     ┌──────────┐            ┌────┴─────┐
              │     │  active  │────────────┤  paused  │
              │     └────┬─────┘  Pause     └──────────┘
              │          │
              │          │ Adjustment Pending
              │          ▼
              │     ┌──────────┐
              │     │ pending  │ (Semi-auto confirmation)
              │     └────┬─────┘
              │          │
       Exit   │          │ Confirm/Timeout
       Error  │          │
              │     ┌────┴────┬─────────┐
              ▼     ▼         ▼         ▼
         ┌──────────┐   ┌──────────┐  ┌──────────┐
         │  error   │   │completed │  │ expired  │
         └──────────┘   └──────────┘  └──────────┘
```

---

**End of Database Schema Document**
