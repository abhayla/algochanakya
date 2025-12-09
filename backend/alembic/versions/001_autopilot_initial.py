"""
AutoPilot Database Migration - Initial Schema

Revision ID: 001_autopilot_initial
Revises: None (or your last migration ID)
Create Date: 2025-12-08

This migration creates all tables required for the AutoPilot feature.
Run with: alembic upgrade head
Rollback with: alembic downgrade -1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_autopilot_initial'
down_revision = None  # Change this to your last migration ID if you have existing migrations
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create all AutoPilot tables, types, indexes, and triggers.
    """
    
    # =========================================================================
    # STEP 1: CREATE ENUM TYPES
    # =========================================================================
    
    # Strategy status enum
    op.execute("""
        CREATE TYPE autopilot_strategy_status AS ENUM (
            'draft',
            'waiting',
            'active',
            'pending',
            'paused',
            'completed',
            'error',
            'expired'
        )
    """)
    
    # Underlying enum
    op.execute("""
        CREATE TYPE autopilot_underlying AS ENUM (
            'NIFTY',
            'BANKNIFTY',
            'FINNIFTY',
            'SENSEX'
        )
    """)
    
    # Position type enum
    op.execute("""
        CREATE TYPE autopilot_position_type AS ENUM (
            'intraday',
            'positional'
        )
    """)
    
    # Order type enum
    op.execute("""
        CREATE TYPE autopilot_order_type AS ENUM (
            'MARKET',
            'LIMIT',
            'SL',
            'SL-M'
        )
    """)
    
    # Transaction type enum
    op.execute("""
        CREATE TYPE autopilot_transaction_type AS ENUM (
            'BUY',
            'SELL'
        )
    """)
    
    # Order status enum
    op.execute("""
        CREATE TYPE autopilot_order_status AS ENUM (
            'pending',
            'placed',
            'open',
            'complete',
            'cancelled',
            'rejected',
            'error'
        )
    """)
    
    # Order purpose enum
    op.execute("""
        CREATE TYPE autopilot_order_purpose AS ENUM (
            'entry',
            'adjustment',
            'hedge',
            'exit',
            'roll_close',
            'roll_open',
            'kill_switch'
        )
    """)
    
    # Log event type enum
    op.execute("""
        CREATE TYPE autopilot_log_event AS ENUM (
            'strategy_created',
            'strategy_activated',
            'strategy_paused',
            'strategy_resumed',
            'strategy_completed',
            'strategy_expired',
            'strategy_error',
            'entry_condition_evaluated',
            'entry_condition_triggered',
            'entry_started',
            'entry_completed',
            'entry_failed',
            'adjustment_condition_evaluated',
            'adjustment_condition_triggered',
            'confirmation_requested',
            'confirmation_received',
            'confirmation_timeout',
            'confirmation_skipped',
            'adjustment_started',
            'adjustment_completed',
            'adjustment_failed',
            'order_placed',
            'order_filled',
            'order_partial_fill',
            'order_cancelled',
            'order_rejected',
            'order_modified',
            'exit_triggered',
            'exit_started',
            'exit_completed',
            'exit_failed',
            'risk_limit_warning',
            'risk_limit_breach',
            'daily_loss_limit_hit',
            'margin_warning',
            'margin_insufficient',
            'kill_switch_activated',
            'connection_lost',
            'connection_restored',
            'system_error',
            'api_error',
            'user_modified_settings',
            'user_force_entry',
            'user_force_exit'
        )
    """)
    
    # Log severity enum
    op.execute("""
        CREATE TYPE autopilot_log_severity AS ENUM (
            'debug',
            'info',
            'warning',
            'error',
            'critical'
        )
    """)
    
    # =========================================================================
    # STEP 2: CREATE TABLES
    # =========================================================================
    
    # -------------------------------------------------------------------------
    # Table: autopilot_templates (no FK to other autopilot tables)
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_templates',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=False),
        sa.Column('strategy_config', postgresql.JSONB(), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), default=[]),
        sa.Column('risk_level', sa.String(20), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('avg_rating', sa.Numeric(3, 2), nullable=True),
        sa.Column('rating_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('avg_rating IS NULL OR (avg_rating >= 1 AND avg_rating <= 5)', name='chk_template_rating')
    )
    
    op.create_index('idx_autopilot_templates_user', 'autopilot_templates', ['user_id'], 
                    postgresql_where=sa.text('user_id IS NOT NULL'))
    op.create_index('idx_autopilot_templates_public', 'autopilot_templates', ['is_public', 'usage_count'],
                    postgresql_where=sa.text('is_public = true'))
    op.create_index('idx_autopilot_templates_category', 'autopilot_templates', ['category'],
                    postgresql_where=sa.text('category IS NOT NULL'))
    op.create_index('idx_autopilot_templates_tags', 'autopilot_templates', ['tags'],
                    postgresql_using='gin')
    
    # -------------------------------------------------------------------------
    # Table: autopilot_user_settings
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_user_settings',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        
        # Risk Limits
        sa.Column('daily_loss_limit', sa.Numeric(12, 2), nullable=False, default=20000.00),
        sa.Column('per_strategy_loss_limit', sa.Numeric(12, 2), nullable=False, default=10000.00),
        sa.Column('max_capital_deployed', sa.Numeric(14, 2), nullable=False, default=500000.00),
        sa.Column('max_active_strategies', sa.Integer(), nullable=False, default=3),
        
        # Time Restrictions
        sa.Column('no_trade_first_minutes', sa.Integer(), nullable=False, default=5),
        sa.Column('no_trade_last_minutes', sa.Integer(), nullable=False, default=5),
        
        # Cooldown
        sa.Column('cooldown_after_loss', sa.Boolean(), nullable=False, default=False),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, default=30),
        sa.Column('cooldown_threshold', sa.Numeric(12, 2), nullable=False, default=5000.00),
        
        # JSONB Settings
        sa.Column('default_order_settings', postgresql.JSONB(), nullable=False, 
                  server_default='{"order_type": "MARKET", "execution_style": "sequential", "delay_between_legs": 2, "slippage_protection": true, "max_slippage_pct": 2.0, "price_improvement": false}'),
        sa.Column('notification_prefs', postgresql.JSONB(), nullable=False,
                  server_default='{"enabled": true, "channels": ["in_app"], "frequency": "realtime", "events": {"entry_triggered": true, "order_executed": true, "adjustment_triggered": true, "exit_executed": true, "error": true, "daily_summary": true}}'),
        sa.Column('failure_handling', postgresql.JSONB(), nullable=False,
                  server_default='{"on_network_error": "retry", "on_api_error": "alert", "on_margin_insufficient": "cancel", "max_retries": 3, "retry_delay_seconds": 5}'),
        
        # Feature Flags
        sa.Column('paper_trading_mode', sa.Boolean(), nullable=False, default=False),
        sa.Column('show_advanced_features', sa.Boolean(), nullable=False, default=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        # Constraints
        sa.CheckConstraint('max_active_strategies BETWEEN 1 AND 10', name='chk_max_strategies'),
        sa.CheckConstraint('no_trade_first_minutes BETWEEN 0 AND 60', name='chk_no_trade_first'),
        sa.CheckConstraint('no_trade_last_minutes BETWEEN 0 AND 60', name='chk_no_trade_last'),
        sa.CheckConstraint('cooldown_minutes BETWEEN 5 AND 240', name='chk_cooldown_minutes'),
        sa.CheckConstraint('per_strategy_loss_limit <= daily_loss_limit', name='chk_loss_limits'),
        sa.CheckConstraint('max_capital_deployed > 0', name='chk_capital_positive')
    )
    
    op.create_index('idx_autopilot_user_settings_user', 'autopilot_user_settings', ['user_id'])
    
    # -------------------------------------------------------------------------
    # Table: autopilot_strategies
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_strategies',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        
        # Basic Info
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('status', postgresql.ENUM('draft', 'waiting', 'active', 'pending', 'paused', 'completed', 'error', 'expired', 
                                            name='autopilot_strategy_status', create_type=False), 
                  nullable=False, default='draft'),
        
        # Instrument Configuration
        sa.Column('underlying', postgresql.ENUM('NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX',
                                                name='autopilot_underlying', create_type=False), nullable=False),
        sa.Column('expiry_type', sa.String(20), nullable=False, default='current_week'),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('lots', sa.Integer(), nullable=False, default=1),
        sa.Column('position_type', postgresql.ENUM('intraday', 'positional',
                                                   name='autopilot_position_type', create_type=False),
                  nullable=False, default='intraday'),
        
        # JSONB Configurations
        sa.Column('legs_config', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('entry_conditions', postgresql.JSONB(), nullable=False, 
                  server_default='{"logic": "AND", "conditions": []}'),
        sa.Column('adjustment_rules', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('order_settings', postgresql.JSONB(), nullable=False,
                  server_default='{"order_type": "MARKET", "execution_style": "sequential", "leg_sequence": [], "delay_between_legs": 2, "slippage_protection": {"enabled": true, "max_per_leg_pct": 2.0, "max_total_pct": 5.0, "on_exceed": "retry"}, "on_leg_failure": "stop"}'),
        sa.Column('risk_settings', postgresql.JSONB(), nullable=False,
                  server_default='{"max_loss": null, "max_loss_pct": null, "trailing_stop": {"enabled": false, "trigger_profit": null, "trail_amount": null}, "max_margin": null, "time_stop": null}'),
        sa.Column('schedule_config', postgresql.JSONB(), nullable=False,
                  server_default='{"activation_mode": "always", "active_days": ["MON", "TUE", "WED", "THU", "FRI"], "start_time": "09:15", "end_time": "15:30", "expiry_days_only": false, "date_range": null}'),
        
        # Priority & State
        sa.Column('priority', sa.Integer(), nullable=False, default=100),
        sa.Column('runtime_state', postgresql.JSONB(), nullable=True),
        
        # References
        sa.Column('source_template_id', sa.BigInteger(), sa.ForeignKey('autopilot_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('cloned_from_id', sa.BigInteger(), nullable=True),  # Self-reference added later
        
        # Version & Timestamps
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        
        # Constraints
        sa.CheckConstraint("LENGTH(TRIM(name)) > 0", name='chk_name_not_empty'),
        sa.CheckConstraint('lots BETWEEN 1 AND 50', name='chk_lots_range'),
        sa.CheckConstraint('priority BETWEEN 1 AND 1000', name='chk_priority_range')
    )
    
    # Add self-referencing foreign key
    op.create_foreign_key(
        'fk_strategies_cloned_from',
        'autopilot_strategies', 'autopilot_strategies',
        ['cloned_from_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Indexes
    op.create_index('idx_autopilot_strategies_user', 'autopilot_strategies', ['user_id'])
    op.create_index('idx_autopilot_strategies_status', 'autopilot_strategies', ['status'])
    op.create_index('idx_autopilot_strategies_user_status', 'autopilot_strategies', ['user_id', 'status'])
    op.create_index('idx_autopilot_strategies_underlying', 'autopilot_strategies', ['underlying'])
    op.create_index('idx_autopilot_strategies_created', 'autopilot_strategies', [sa.text('created_at DESC')])
    
    # Partial index for active strategies
    op.execute("""
        CREATE INDEX idx_autopilot_strategies_active 
        ON autopilot_strategies(user_id, priority)
        WHERE status IN ('waiting', 'active', 'pending')
    """)
    
    # GIN indexes for JSONB
    op.create_index('idx_autopilot_strategies_legs', 'autopilot_strategies', ['legs_config'],
                    postgresql_using='gin', postgresql_ops={'legs_config': 'jsonb_path_ops'})
    op.create_index('idx_autopilot_strategies_schedule', 'autopilot_strategies', ['schedule_config'],
                    postgresql_using='gin', postgresql_ops={'schedule_config': 'jsonb_path_ops'})
    
    # -------------------------------------------------------------------------
    # Table: autopilot_orders
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_orders',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('strategy_id', sa.BigInteger(), sa.ForeignKey('autopilot_strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        
        # Broker Reference
        sa.Column('kite_order_id', sa.String(50), nullable=True),
        sa.Column('kite_exchange_order_id', sa.String(50), nullable=True),
        
        # Order Context
        sa.Column('purpose', postgresql.ENUM('entry', 'adjustment', 'hedge', 'exit', 'roll_close', 'roll_open', 'kill_switch',
                                             name='autopilot_order_purpose', create_type=False), nullable=False),
        sa.Column('rule_name', sa.String(100), nullable=True),
        sa.Column('leg_index', sa.Integer(), nullable=False, default=0),
        
        # Instrument Details
        sa.Column('exchange', sa.String(10), nullable=False, default='NFO'),
        sa.Column('tradingsymbol', sa.String(50), nullable=False),
        sa.Column('instrument_token', sa.BigInteger(), nullable=True),
        sa.Column('underlying', postgresql.ENUM('NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX',
                                                name='autopilot_underlying', create_type=False), nullable=False),
        sa.Column('contract_type', sa.String(2), nullable=False),
        sa.Column('strike', sa.Numeric(10, 2), nullable=True),
        sa.Column('expiry', sa.Date(), nullable=False),
        
        # Order Details
        sa.Column('transaction_type', postgresql.ENUM('BUY', 'SELL', name='autopilot_transaction_type', create_type=False), nullable=False),
        sa.Column('order_type', postgresql.ENUM('MARKET', 'LIMIT', 'SL', 'SL-M', name='autopilot_order_type', create_type=False), nullable=False),
        sa.Column('product', sa.String(10), nullable=False, default='NRML'),
        sa.Column('quantity', sa.Integer(), nullable=False),
        
        # Prices
        sa.Column('order_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('trigger_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('ltp_at_order', sa.Numeric(10, 2), nullable=True),
        sa.Column('executed_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('executed_quantity', sa.Integer(), default=0),
        sa.Column('pending_quantity', sa.Integer(), nullable=True),
        
        # Slippage
        sa.Column('slippage_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('slippage_pct', sa.Numeric(5, 2), nullable=True),
        
        # Status
        sa.Column('status', postgresql.ENUM('pending', 'placed', 'open', 'complete', 'cancelled', 'rejected', 'error',
                                            name='autopilot_order_status', create_type=False), nullable=False, default='pending'),
        sa.Column('rejection_reason', sa.String(500), nullable=True),
        
        # Timing
        sa.Column('order_placed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('order_filled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_duration_ms', sa.Integer(), nullable=True),
        
        # Retry Tracking
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('parent_order_id', sa.BigInteger(), nullable=True),  # Self-reference
        
        # Metadata
        sa.Column('raw_response', postgresql.JSONB(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        # Constraints
        sa.CheckConstraint('quantity > 0', name='chk_order_quantity_positive'),
        sa.CheckConstraint('executed_quantity >= 0 AND executed_quantity <= quantity', name='chk_executed_quantity'),
        sa.CheckConstraint("contract_type IN ('CE', 'PE', 'FUT')", name='chk_contract_type')
    )
    
    # Add self-referencing foreign key for retries
    op.create_foreign_key(
        'fk_orders_parent',
        'autopilot_orders', 'autopilot_orders',
        ['parent_order_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Indexes
    op.create_index('idx_autopilot_orders_strategy', 'autopilot_orders', ['strategy_id'])
    op.create_index('idx_autopilot_orders_user', 'autopilot_orders', ['user_id'])
    op.create_index('idx_autopilot_orders_kite', 'autopilot_orders', ['kite_order_id'],
                    postgresql_where=sa.text('kite_order_id IS NOT NULL'))
    op.create_index('idx_autopilot_orders_status', 'autopilot_orders', ['status'])
    op.create_index('idx_autopilot_orders_created', 'autopilot_orders', [sa.text('created_at DESC')])
    op.create_index('idx_autopilot_orders_user_date', 'autopilot_orders', ['user_id', sa.text('created_at DESC')])
    
    # Partial index for pending orders
    op.execute("""
        CREATE INDEX idx_autopilot_orders_pending 
        ON autopilot_orders(strategy_id, created_at)
        WHERE status IN ('pending', 'placed', 'open')
    """)
    
    # -------------------------------------------------------------------------
    # Table: autopilot_logs
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', sa.BigInteger(), sa.ForeignKey('autopilot_strategies.id', ondelete='SET NULL'), nullable=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('autopilot_orders.id', ondelete='SET NULL'), nullable=True),
        
        # Event Details
        sa.Column('event_type', postgresql.ENUM(
            'strategy_created', 'strategy_activated', 'strategy_paused', 'strategy_resumed',
            'strategy_completed', 'strategy_expired', 'strategy_error',
            'entry_condition_evaluated', 'entry_condition_triggered', 'entry_started',
            'entry_completed', 'entry_failed', 'adjustment_condition_evaluated',
            'adjustment_condition_triggered', 'confirmation_requested', 'confirmation_received',
            'confirmation_timeout', 'confirmation_skipped', 'adjustment_started',
            'adjustment_completed', 'adjustment_failed', 'order_placed', 'order_filled',
            'order_partial_fill', 'order_cancelled', 'order_rejected', 'order_modified',
            'exit_triggered', 'exit_started', 'exit_completed', 'exit_failed',
            'risk_limit_warning', 'risk_limit_breach', 'daily_loss_limit_hit',
            'margin_warning', 'margin_insufficient', 'kill_switch_activated',
            'connection_lost', 'connection_restored', 'system_error', 'api_error',
            'user_modified_settings', 'user_force_entry', 'user_force_exit',
            name='autopilot_log_event', create_type=False
        ), nullable=False),
        sa.Column('severity', postgresql.ENUM('debug', 'info', 'warning', 'error', 'critical',
                                              name='autopilot_log_severity', create_type=False), 
                  nullable=False, default='info'),
        
        # Context
        sa.Column('rule_name', sa.String(100), nullable=True),
        sa.Column('condition_id', sa.String(50), nullable=True),
        
        # Event Data
        sa.Column('event_data', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('message', sa.String(1000), nullable=False),
        
        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    
    # Indexes
    op.create_index('idx_autopilot_logs_user', 'autopilot_logs', ['user_id'])
    op.create_index('idx_autopilot_logs_strategy', 'autopilot_logs', ['strategy_id'],
                    postgresql_where=sa.text('strategy_id IS NOT NULL'))
    op.create_index('idx_autopilot_logs_created', 'autopilot_logs', [sa.text('created_at DESC')])
    op.create_index('idx_autopilot_logs_user_created', 'autopilot_logs', ['user_id', sa.text('created_at DESC')])
    op.create_index('idx_autopilot_logs_event', 'autopilot_logs', ['event_type'])
    op.create_index('idx_autopilot_logs_severity', 'autopilot_logs', ['severity'],
                    postgresql_where=sa.text("severity IN ('error', 'critical')"))
    
    # Partial index for recent logs
    op.execute("""
        CREATE INDEX idx_autopilot_logs_recent 
        ON autopilot_logs(user_id, strategy_id, created_at DESC)
        WHERE created_at > NOW() - INTERVAL '7 days'
    """)
    
    # GIN index for event_data
    op.create_index('idx_autopilot_logs_data', 'autopilot_logs', ['event_data'],
                    postgresql_using='gin', postgresql_ops={'event_data': 'jsonb_path_ops'})
    
    # -------------------------------------------------------------------------
    # Table: autopilot_condition_eval
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_condition_eval',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('strategy_id', sa.BigInteger(), sa.ForeignKey('autopilot_strategies.id', ondelete='CASCADE'), nullable=False),
        
        # Condition Reference
        sa.Column('condition_type', sa.String(20), nullable=False),
        sa.Column('condition_index', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(100), nullable=True),
        
        # Condition Details
        sa.Column('variable', sa.String(50), nullable=False),
        sa.Column('operator', sa.String(20), nullable=False),
        sa.Column('target_value', postgresql.JSONB(), nullable=False),
        
        # Evaluation Result
        sa.Column('current_value', postgresql.JSONB(), nullable=False),
        sa.Column('is_satisfied', sa.Boolean(), nullable=False),
        sa.Column('progress_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('distance_to_trigger', sa.String(100), nullable=True),
        
        # Timestamp
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    
    # Indexes
    op.create_index('idx_autopilot_condition_eval_strategy', 'autopilot_condition_eval', ['strategy_id'])
    op.create_index('idx_autopilot_condition_eval_time', 'autopilot_condition_eval', [sa.text('evaluated_at DESC')])
    op.create_index('idx_autopilot_condition_eval_latest', 'autopilot_condition_eval', 
                    ['strategy_id', 'condition_type', 'condition_index', sa.text('evaluated_at DESC')])
    
    # -------------------------------------------------------------------------
    # Table: autopilot_daily_summary
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_daily_summary',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('summary_date', sa.Date(), nullable=False),
        
        # Strategy Counts
        sa.Column('strategies_run', sa.Integer(), nullable=False, default=0),
        sa.Column('strategies_completed', sa.Integer(), nullable=False, default=0),
        sa.Column('strategies_errored', sa.Integer(), nullable=False, default=0),
        
        # Order Counts
        sa.Column('orders_placed', sa.Integer(), nullable=False, default=0),
        sa.Column('orders_filled', sa.Integer(), nullable=False, default=0),
        sa.Column('orders_rejected', sa.Integer(), nullable=False, default=0),
        
        # P&L
        sa.Column('total_realized_pnl', sa.Numeric(14, 2), nullable=False, default=0),
        sa.Column('total_brokerage', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('total_slippage', sa.Numeric(10, 2), nullable=False, default=0),
        
        # Best/Worst
        sa.Column('best_strategy_pnl', sa.Numeric(12, 2), nullable=True),
        sa.Column('best_strategy_name', sa.String(100), nullable=True),
        sa.Column('worst_strategy_pnl', sa.Numeric(12, 2), nullable=True),
        sa.Column('worst_strategy_name', sa.String(100), nullable=True),
        
        # Execution Stats
        sa.Column('avg_execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('total_adjustments', sa.Integer(), nullable=False, default=0),
        sa.Column('kill_switch_used', sa.Boolean(), nullable=False, default=False),
        
        # Risk Metrics
        sa.Column('max_drawdown', sa.Numeric(12, 2), nullable=True),
        sa.Column('peak_margin_used', sa.Numeric(14, 2), nullable=True),
        sa.Column('daily_loss_limit_hit', sa.Boolean(), nullable=False, default=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        # Unique constraint
        sa.UniqueConstraint('user_id', 'summary_date', name='uq_user_date')
    )
    
    # Indexes
    op.create_index('idx_autopilot_daily_summary_user', 'autopilot_daily_summary', ['user_id'])
    op.create_index('idx_autopilot_daily_summary_date', 'autopilot_daily_summary', [sa.text('summary_date DESC')])
    op.create_index('idx_autopilot_daily_summary_user_date', 'autopilot_daily_summary', 
                    ['user_id', sa.text('summary_date DESC')])
    
    # =========================================================================
    # STEP 3: CREATE FUNCTIONS & TRIGGERS
    # =========================================================================
    
    # Function: Update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Apply updated_at trigger to all relevant tables
    for table in ['autopilot_user_settings', 'autopilot_strategies', 'autopilot_orders', 
                  'autopilot_daily_summary', 'autopilot_templates']:
        op.execute(f"""
            CREATE TRIGGER tr_{table}_updated
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
    
    # Function: Increment strategy version
    op.execute("""
        CREATE OR REPLACE FUNCTION increment_strategy_version()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.version = OLD.version + 1;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER tr_autopilot_strategies_version
        BEFORE UPDATE ON autopilot_strategies
        FOR EACH ROW 
        WHEN (OLD.* IS DISTINCT FROM NEW.*)
        EXECUTE FUNCTION increment_strategy_version();
    """)
    
    # Function: Log strategy status changes
    op.execute("""
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
    """)
    
    op.execute("""
        CREATE TRIGGER tr_autopilot_strategies_status_log
        AFTER UPDATE ON autopilot_strategies
        FOR EACH ROW EXECUTE FUNCTION log_strategy_status_change();
    """)
    
    # Function: Check max active strategies
    op.execute("""
        CREATE OR REPLACE FUNCTION check_max_active_strategies()
        RETURNS TRIGGER AS $$
        DECLARE
            active_count INTEGER;
            max_allowed INTEGER;
        BEGIN
            IF NEW.status IN ('waiting', 'active', 'pending') THEN
                SELECT COUNT(*) INTO active_count
                FROM autopilot_strategies
                WHERE user_id = NEW.user_id
                  AND status IN ('waiting', 'active', 'pending')
                  AND id != NEW.id;
                
                SELECT COALESCE(max_active_strategies, 3) INTO max_allowed
                FROM autopilot_user_settings
                WHERE user_id = NEW.user_id;
                
                IF max_allowed IS NULL THEN
                    max_allowed := 3;
                END IF;
                
                IF active_count >= max_allowed THEN
                    RAISE EXCEPTION 'Maximum active strategies limit (%) reached', max_allowed;
                END IF;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER tr_autopilot_strategies_max_check
        BEFORE INSERT OR UPDATE ON autopilot_strategies
        FOR EACH ROW EXECUTE FUNCTION check_max_active_strategies();
    """)
    
    # Function: Increment template usage count
    op.execute("""
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
    """)
    
    op.execute("""
        CREATE TRIGGER tr_autopilot_strategies_template_usage
        AFTER INSERT ON autopilot_strategies
        FOR EACH ROW EXECUTE FUNCTION increment_template_usage();
    """)
    
    # =========================================================================
    # STEP 4: INSERT SYSTEM TEMPLATES (Optional)
    # =========================================================================
    
    op.execute("""
        INSERT INTO autopilot_templates (name, description, is_system, is_public, category, risk_level, tags, strategy_config)
        VALUES 
        (
            'Iron Condor - Conservative',
            'Weekly iron condor with wide wings. Suitable for low volatility environments.',
            true,
            true,
            'iron_condor',
            'conservative',
            ARRAY['weekly', 'neutral', 'low_risk'],
            '{
                "underlying": "NIFTY",
                "expiry_type": "current_week",
                "lots": 1,
                "position_type": "intraday",
                "legs_config": [
                    {"id": "leg_1", "contract_type": "PE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": -300}, "quantity_multiplier": 1, "execution_order": 1},
                    {"id": "leg_2", "contract_type": "PE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": -500}, "quantity_multiplier": 1, "execution_order": 2},
                    {"id": "leg_3", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 300}, "quantity_multiplier": 1, "execution_order": 3},
                    {"id": "leg_4", "contract_type": "CE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": 500}, "quantity_multiplier": 1, "execution_order": 4}
                ],
                "entry_conditions": {
                    "logic": "AND",
                    "conditions": [
                        {"id": "c1", "enabled": true, "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:20"},
                        {"id": "c2", "enabled": true, "variable": "VOLATILITY.VIX", "operator": "less_than", "value": 18}
                    ]
                },
                "adjustment_rules": [
                    {
                        "id": "r1",
                        "name": "Stop Loss Exit",
                        "enabled": true,
                        "priority": 1,
                        "trigger": {"logic": "OR", "conditions": [{"id": "t1", "variable": "STRATEGY.PNL", "operator": "less_than", "value": -5000}]},
                        "action": {"type": "exit_all", "config": {"order_type": "MARKET"}},
                        "execution_mode": "auto",
                        "timeout_seconds": 60,
                        "timeout_action": "skip"
                    },
                    {
                        "id": "r2",
                        "name": "Profit Target Exit",
                        "enabled": true,
                        "priority": 2,
                        "trigger": {"logic": "OR", "conditions": [{"id": "t2", "variable": "STRATEGY.PNL", "operator": "greater_than", "value": 6000}]},
                        "action": {"type": "exit_all", "config": {"order_type": "MARKET"}},
                        "execution_mode": "auto",
                        "timeout_seconds": 60,
                        "timeout_action": "skip"
                    }
                ]
            }'::jsonb
        ),
        (
            'Short Straddle with Hedge',
            'ATM short straddle with OTM hedge protection. Higher premium collection.',
            true,
            true,
            'straddle',
            'moderate',
            ARRAY['weekly', 'neutral', 'hedged'],
            '{
                "underlying": "NIFTY",
                "expiry_type": "current_week",
                "lots": 1,
                "position_type": "intraday",
                "legs_config": [
                    {"id": "leg_1", "contract_type": "PE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}, "quantity_multiplier": 1, "execution_order": 1},
                    {"id": "leg_2", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}, "quantity_multiplier": 1, "execution_order": 2}
                ],
                "entry_conditions": {
                    "logic": "AND",
                    "conditions": [
                        {"id": "c1", "enabled": true, "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:20"},
                        {"id": "c2", "enabled": true, "variable": "VOLATILITY.VIX", "operator": "between", "value": [14, 20]}
                    ]
                },
                "adjustment_rules": [
                    {
                        "id": "r1",
                        "name": "Add Hedge on Loss",
                        "enabled": true,
                        "priority": 1,
                        "trigger": {"logic": "OR", "conditions": [{"id": "t1", "variable": "STRATEGY.PNL", "operator": "less_than", "value": -3000}]},
                        "action": {"type": "add_hedge", "config": {"hedge_type": "both", "pe_strike": {"mode": "offset_from_spot", "offset": -300}, "ce_strike": {"mode": "offset_from_spot", "offset": 300}, "quantity_mode": "same_as_position", "max_cost": 4000}},
                        "execution_mode": "semi_auto",
                        "timeout_seconds": 60,
                        "timeout_action": "skip",
                        "max_executions": 1
                    }
                ]
            }'::jsonb
        );
    """)
    
    print("✅ AutoPilot migration completed successfully!")
    print("   - 7 tables created")
    print("   - 9 enum types created")
    print("   - 25+ indexes created")
    print("   - 5 trigger functions created")
    print("   - 2 system templates inserted")


def downgrade() -> None:
    """
    Drop all AutoPilot tables, types, and functions.
    """
    
    # Drop triggers first
    triggers = [
        ('tr_autopilot_user_settings_updated', 'autopilot_user_settings'),
        ('tr_autopilot_strategies_updated', 'autopilot_strategies'),
        ('tr_autopilot_orders_updated', 'autopilot_orders'),
        ('tr_autopilot_daily_summary_updated', 'autopilot_daily_summary'),
        ('tr_autopilot_templates_updated', 'autopilot_templates'),
        ('tr_autopilot_strategies_version', 'autopilot_strategies'),
        ('tr_autopilot_strategies_status_log', 'autopilot_strategies'),
        ('tr_autopilot_strategies_max_check', 'autopilot_strategies'),
        ('tr_autopilot_strategies_template_usage', 'autopilot_strategies'),
    ]
    
    for trigger_name, table_name in triggers:
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}")
    
    # Drop functions
    functions = [
        'update_updated_at_column',
        'increment_strategy_version',
        'log_strategy_status_change',
        'check_max_active_strategies',
        'increment_template_usage',
    ]
    
    for func in functions:
        op.execute(f"DROP FUNCTION IF EXISTS {func}() CASCADE")
    
    # Drop tables in reverse order (respecting foreign keys)
    tables = [
        'autopilot_daily_summary',
        'autopilot_condition_eval',
        'autopilot_logs',
        'autopilot_orders',
        'autopilot_strategies',
        'autopilot_user_settings',
        'autopilot_templates',
    ]
    
    for table in tables:
        op.drop_table(table)
    
    # Drop enum types
    enums = [
        'autopilot_log_severity',
        'autopilot_log_event',
        'autopilot_order_purpose',
        'autopilot_order_status',
        'autopilot_transaction_type',
        'autopilot_order_type',
        'autopilot_position_type',
        'autopilot_underlying',
        'autopilot_strategy_status',
    ]
    
    for enum in enums:
        op.execute(f"DROP TYPE IF EXISTS {enum} CASCADE")
    
    print("✅ AutoPilot migration rolled back successfully!")
