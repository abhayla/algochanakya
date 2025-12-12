"""
AutoPilot Phase 3 - Advanced Features Migration

Revision ID: 002_autopilot_phase3
Revises: 001_autopilot_initial
Create Date: 2025-12-10

This migration adds:
- Kill Switch functionality
- Adjustment Rules Engine
- Semi-Auto Execution Mode (Confirmations)
- Trailing Stop Loss
- Intraday Auto-Exit
- Position Sizing fields
- Greeks Calculator support

New tables:
- autopilot_adjustment_logs
- autopilot_pending_confirmations

New enum types:
- autopilot_execution_mode
- autopilot_adjustment_trigger_type
- autopilot_adjustment_action_type
- autopilot_confirmation_status

Run with: alembic upgrade head
Rollback with: alembic downgrade 001_autopilot_initial
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_autopilot_phase3'
down_revision = '001_autopilot_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add Phase 3 tables, columns, and enum types.
    """

    # =========================================================================
    # STEP 1: CREATE NEW ENUM TYPES
    # =========================================================================

    # Execution mode enum (auto, semi_auto, manual)
    op.execute("""
        CREATE TYPE autopilot_execution_mode AS ENUM (
            'auto',
            'semi_auto',
            'manual'
        )
    """)

    # Adjustment trigger type enum
    op.execute("""
        CREATE TYPE autopilot_adjustment_trigger_type AS ENUM (
            'pnl_based',
            'delta_based',
            'time_based',
            'premium_based',
            'vix_based',
            'spot_based'
        )
    """)

    # Adjustment action type enum
    op.execute("""
        CREATE TYPE autopilot_adjustment_action_type AS ENUM (
            'add_hedge',
            'close_leg',
            'roll_strike',
            'roll_expiry',
            'exit_all',
            'scale_down',
            'scale_up'
        )
    """)

    # Confirmation status enum
    op.execute("""
        CREATE TYPE autopilot_confirmation_status AS ENUM (
            'pending',
            'confirmed',
            'rejected',
            'expired',
            'cancelled'
        )
    """)

    # Add new event types to autopilot_log_event enum
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'kill_switch_reset';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'trailing_stop_activated';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'trailing_stop_updated';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'auto_exit_warning';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'auto_exit_executed';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'position_sized';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'greeks_calculated';
    """)

    # =========================================================================
    # STEP 2: ALTER EXISTING TABLES - Add new columns
    # =========================================================================

    # -------------------------------------------------------------------------
    # autopilot_user_settings - Add Kill Switch and Phase 3 columns
    # -------------------------------------------------------------------------

    # Kill Switch columns
    op.add_column('autopilot_user_settings',
        sa.Column('kill_switch_enabled', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('autopilot_user_settings',
        sa.Column('kill_switch_triggered_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Semi-Auto Execution columns
    op.add_column('autopilot_user_settings',
        sa.Column('default_execution_mode',
                  postgresql.ENUM('auto', 'semi_auto', 'manual',
                                  name='autopilot_execution_mode', create_type=False),
                  nullable=False, server_default='auto')
    )
    op.add_column('autopilot_user_settings',
        sa.Column('confirmation_timeout_seconds', sa.Integer(), nullable=False, server_default='30')
    )

    # Auto-Exit columns
    op.add_column('autopilot_user_settings',
        sa.Column('auto_exit_time', sa.String(5), nullable=True, server_default='15:15')
    )

    # Position Sizing columns
    op.add_column('autopilot_user_settings',
        sa.Column('account_capital', sa.Numeric(14, 2), nullable=True)
    )
    op.add_column('autopilot_user_settings',
        sa.Column('risk_per_trade_pct', sa.Numeric(5, 2), nullable=True, server_default='2.00')
    )

    # -------------------------------------------------------------------------
    # autopilot_strategies - Add execution mode and trailing stop
    # -------------------------------------------------------------------------

    # Execution mode per strategy (overrides user default)
    op.add_column('autopilot_strategies',
        sa.Column('execution_mode',
                  postgresql.ENUM('auto', 'semi_auto', 'manual',
                                  name='autopilot_execution_mode', create_type=False),
                  nullable=True)
    )

    # Trailing stop configuration (JSONB)
    op.add_column('autopilot_strategies',
        sa.Column('trailing_stop_config', postgresql.JSONB(), nullable=True,
                  server_default='{"enabled": false, "activation_profit": null, "trail_distance": null, "trail_type": "fixed", "min_profit_lock": null}')
    )

    # Greeks snapshot (JSONB)
    op.add_column('autopilot_strategies',
        sa.Column('greeks_snapshot', postgresql.JSONB(), nullable=True)
    )

    # =========================================================================
    # STEP 3: CREATE NEW TABLES
    # =========================================================================

    # -------------------------------------------------------------------------
    # Table: autopilot_adjustment_logs - Track adjustment rule executions
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_adjustment_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('strategy_id', sa.BigInteger(),
                  sa.ForeignKey('autopilot_strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),

        # Rule Reference
        sa.Column('rule_id', sa.String(50), nullable=False),
        sa.Column('rule_name', sa.String(100), nullable=False),

        # Trigger Details
        sa.Column('trigger_type',
                  postgresql.ENUM('pnl_based', 'delta_based', 'time_based', 'premium_based',
                                  'vix_based', 'spot_based',
                                  name='autopilot_adjustment_trigger_type', create_type=False),
                  nullable=False),
        sa.Column('trigger_condition', sa.String(200), nullable=False),
        sa.Column('trigger_value', postgresql.JSONB(), nullable=False),
        sa.Column('actual_value', postgresql.JSONB(), nullable=False),

        # Action Details
        sa.Column('action_type',
                  postgresql.ENUM('add_hedge', 'close_leg', 'roll_strike', 'roll_expiry',
                                  'exit_all', 'scale_down', 'scale_up',
                                  name='autopilot_adjustment_action_type', create_type=False),
                  nullable=False),
        sa.Column('action_params', postgresql.JSONB(), nullable=False, server_default='{}'),

        # Execution Status
        sa.Column('execution_mode',
                  postgresql.ENUM('auto', 'semi_auto', 'manual',
                                  name='autopilot_execution_mode', create_type=False),
                  nullable=False),
        sa.Column('executed', sa.Boolean(), nullable=False, default=False),
        sa.Column('execution_result', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.String(500), nullable=True),

        # Related Orders
        sa.Column('order_ids', postgresql.ARRAY(sa.BigInteger()), nullable=True),

        # Confirmation (for semi-auto)
        sa.Column('confirmation_id', sa.BigInteger(), nullable=True),
        sa.Column('confirmed_by_user', sa.Boolean(), nullable=True),

        # Timestamps
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )

    # Indexes for autopilot_adjustment_logs
    op.create_index('idx_adjustment_logs_strategy', 'autopilot_adjustment_logs', ['strategy_id'])
    op.create_index('idx_adjustment_logs_user', 'autopilot_adjustment_logs', ['user_id'])
    op.create_index('idx_adjustment_logs_triggered', 'autopilot_adjustment_logs',
                    [sa.text('triggered_at DESC')])
    op.create_index('idx_adjustment_logs_rule', 'autopilot_adjustment_logs', ['rule_id'])

    # -------------------------------------------------------------------------
    # Table: autopilot_pending_confirmations - Semi-auto confirmation requests
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_pending_confirmations',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', sa.BigInteger(),
                  sa.ForeignKey('autopilot_strategies.id', ondelete='CASCADE'), nullable=False),

        # Action Type
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('action_description', sa.String(500), nullable=False),
        sa.Column('action_data', postgresql.JSONB(), nullable=False, server_default='{}'),

        # Related Rule (for adjustments)
        sa.Column('rule_id', sa.String(50), nullable=True),
        sa.Column('rule_name', sa.String(100), nullable=True),

        # Status
        sa.Column('status',
                  postgresql.ENUM('pending', 'confirmed', 'rejected', 'expired', 'cancelled',
                                  name='autopilot_confirmation_status', create_type=False),
                  nullable=False, server_default='pending'),

        # Timing
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),

        # Response
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_source', sa.String(50), nullable=True),  # 'user', 'timeout', 'system'

        # Execution Result
        sa.Column('execution_result', postgresql.JSONB(), nullable=True),
        sa.Column('order_ids', postgresql.ARRAY(sa.BigInteger()), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )

    # Indexes for autopilot_pending_confirmations
    op.create_index('idx_confirmations_user', 'autopilot_pending_confirmations', ['user_id'])
    op.create_index('idx_confirmations_strategy', 'autopilot_pending_confirmations', ['strategy_id'])
    op.create_index('idx_confirmations_status', 'autopilot_pending_confirmations', ['status'])
    op.create_index('idx_confirmations_expires', 'autopilot_pending_confirmations', ['expires_at'],
                    postgresql_where=sa.text("status = 'pending'"))
    op.create_index('idx_confirmations_created', 'autopilot_pending_confirmations',
                    [sa.text('created_at DESC')])

    # Partial index for pending confirmations only
    op.execute("""
        CREATE INDEX idx_confirmations_pending
        ON autopilot_pending_confirmations(user_id, strategy_id, expires_at)
        WHERE status = 'pending'
    """)

    # =========================================================================
    # STEP 4: ADD CONSTRAINTS
    # =========================================================================

    # Constraint for confirmation timeout
    op.execute("""
        ALTER TABLE autopilot_user_settings
        ADD CONSTRAINT chk_confirmation_timeout
        CHECK (confirmation_timeout_seconds BETWEEN 10 AND 300)
    """)

    # Constraint for auto_exit_time format (HH:MM)
    op.execute("""
        ALTER TABLE autopilot_user_settings
        ADD CONSTRAINT chk_auto_exit_time_format
        CHECK (auto_exit_time IS NULL OR auto_exit_time ~ '^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
    """)

    # Constraint for risk_per_trade_pct
    op.execute("""
        ALTER TABLE autopilot_user_settings
        ADD CONSTRAINT chk_risk_per_trade
        CHECK (risk_per_trade_pct IS NULL OR (risk_per_trade_pct > 0 AND risk_per_trade_pct <= 100))
    """)

    # =========================================================================
    # STEP 5: CREATE TRIGGER FOR updated_at ON NEW TABLES
    # =========================================================================

    op.execute("""
        CREATE TRIGGER tr_autopilot_pending_confirmations_updated
        BEFORE UPDATE ON autopilot_pending_confirmations
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # =========================================================================
    # STEP 6: ADD FOREIGN KEY FOR adjustment_logs confirmation_id
    # =========================================================================

    op.create_foreign_key(
        'fk_adjustment_logs_confirmation',
        'autopilot_adjustment_logs', 'autopilot_pending_confirmations',
        ['confirmation_id'], ['id'],
        ondelete='SET NULL'
    )

    print("AutoPilot Phase 3 migration completed successfully!")
    print("   - 4 new enum types created")
    print("   - 7 new event types added to autopilot_log_event")
    print("   - 7 new columns added to autopilot_user_settings")
    print("   - 3 new columns added to autopilot_strategies")
    print("   - 2 new tables created (autopilot_adjustment_logs, autopilot_pending_confirmations)")
    print("   - Multiple indexes and constraints added")


def downgrade() -> None:
    """
    Remove Phase 3 tables, columns, and enum types.
    """

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS tr_autopilot_pending_confirmations_updated ON autopilot_pending_confirmations")

    # Drop foreign key
    op.drop_constraint('fk_adjustment_logs_confirmation', 'autopilot_adjustment_logs', type_='foreignkey')

    # Drop constraints
    op.execute("ALTER TABLE autopilot_user_settings DROP CONSTRAINT IF EXISTS chk_confirmation_timeout")
    op.execute("ALTER TABLE autopilot_user_settings DROP CONSTRAINT IF EXISTS chk_auto_exit_time_format")
    op.execute("ALTER TABLE autopilot_user_settings DROP CONSTRAINT IF EXISTS chk_risk_per_trade")

    # Drop new tables
    op.drop_table('autopilot_pending_confirmations')
    op.drop_table('autopilot_adjustment_logs')

    # Drop columns from autopilot_strategies
    op.drop_column('autopilot_strategies', 'greeks_snapshot')
    op.drop_column('autopilot_strategies', 'trailing_stop_config')
    op.drop_column('autopilot_strategies', 'execution_mode')

    # Drop columns from autopilot_user_settings
    op.drop_column('autopilot_user_settings', 'risk_per_trade_pct')
    op.drop_column('autopilot_user_settings', 'account_capital')
    op.drop_column('autopilot_user_settings', 'auto_exit_time')
    op.drop_column('autopilot_user_settings', 'confirmation_timeout_seconds')
    op.drop_column('autopilot_user_settings', 'default_execution_mode')
    op.drop_column('autopilot_user_settings', 'kill_switch_triggered_at')
    op.drop_column('autopilot_user_settings', 'kill_switch_enabled')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS autopilot_confirmation_status CASCADE")
    op.execute("DROP TYPE IF EXISTS autopilot_adjustment_action_type CASCADE")
    op.execute("DROP TYPE IF EXISTS autopilot_adjustment_trigger_type CASCADE")
    op.execute("DROP TYPE IF EXISTS autopilot_execution_mode CASCADE")

    # Note: We cannot remove enum values from autopilot_log_event in PostgreSQL
    # without recreating the type, which is complex. Leaving them as-is.

    print("AutoPilot Phase 3 migration rolled back successfully!")
