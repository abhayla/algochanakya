"""
AutoPilot Phase 5 - Advanced Adjustments & Option Chain Integration Migration

Revision ID: 004_autopilot_phase5
Revises: 003_autopilot_phase4
Create Date: 2024-12-13

This migration adds support for:
- Per-leg position tracking with Greeks
- Adjustment suggestions engine
- Option chain caching
- Delta monitoring thresholds
- Break/split trade functionality
- Shift/roll leg operations
- What-if simulator support

New tables:
- autopilot_position_legs
- autopilot_adjustment_suggestions
- autopilot_option_chain_cache

New columns on autopilot_strategies:
- net_delta, net_theta, net_gamma, net_vega
- breakeven_lower, breakeven_upper
- dte (days to expiry)
- position_legs_snapshot

New columns on autopilot_user_settings:
- delta_watch_threshold, delta_warning_threshold, delta_danger_threshold
- delta_alert_enabled, suggestions_enabled, prefer_round_strikes

Run with: alembic upgrade head
Rollback with: alembic downgrade 003_autopilot_phase4
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004_autopilot_phase5'
down_revision = '003_autopilot_phase4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add Phase 5 tables and columns for advanced adjustments.
    """

    # =========================================================================
    # STEP 1: CREATE NEW TABLES
    # =========================================================================

    # Table: autopilot_position_legs
    # Tracks individual leg state, Greeks, and P&L
    op.create_table(
        'autopilot_position_legs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('strategy_id', sa.BigInteger(), nullable=False),
        sa.Column('leg_id', sa.String(50), nullable=False),

        # Configuration
        sa.Column('contract_type', sa.String(2), nullable=False),  # CE, PE
        sa.Column('action', sa.String(4), nullable=False),  # BUY, SELL
        sa.Column('strike', sa.Numeric(10, 2), nullable=False),
        sa.Column('expiry', sa.Date(), nullable=False),
        sa.Column('lots', sa.Integer(), nullable=False),

        # Instrument
        sa.Column('tradingsymbol', sa.String(50)),
        sa.Column('instrument_token', sa.BigInteger()),

        # Status
        sa.Column('status', sa.String(20), server_default='pending'),  # pending, open, closed, rolled

        # Entry
        sa.Column('entry_price', sa.Numeric(10, 2)),
        sa.Column('entry_time', sa.DateTime()),
        sa.Column('entry_order_ids', postgresql.JSONB(), server_default='[]'),

        # Exit
        sa.Column('exit_price', sa.Numeric(10, 2)),
        sa.Column('exit_time', sa.DateTime()),
        sa.Column('exit_order_ids', postgresql.JSONB(), server_default='[]'),
        sa.Column('exit_reason', sa.String(50)),

        # Greeks (updated real-time)
        sa.Column('delta', sa.Numeric(6, 4)),
        sa.Column('gamma', sa.Numeric(8, 6)),
        sa.Column('theta', sa.Numeric(10, 2)),
        sa.Column('vega', sa.Numeric(8, 4)),
        sa.Column('iv', sa.Numeric(6, 2)),

        # P&L
        sa.Column('unrealized_pnl', sa.Numeric(12, 2), server_default='0'),
        sa.Column('realized_pnl', sa.Numeric(12, 2), server_default='0'),

        # Roll tracking
        sa.Column('rolled_from_leg_id', sa.BigInteger()),
        sa.Column('rolled_to_leg_id', sa.BigInteger()),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['autopilot_strategies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rolled_from_leg_id'], ['autopilot_position_legs.id'])
    )

    # Indexes for autopilot_position_legs
    op.create_index('idx_position_legs_strategy', 'autopilot_position_legs', ['strategy_id'])
    op.create_index('idx_position_legs_status', 'autopilot_position_legs', ['status'])
    op.create_index(
        'idx_position_legs_strategy_leg',
        'autopilot_position_legs',
        ['strategy_id', 'leg_id'],
        unique=True,
        postgresql_where=sa.text("status = 'open'")
    )

    # Table: autopilot_adjustment_suggestions
    # Stores AI-generated adjustment suggestions
    op.create_table(
        'autopilot_adjustment_suggestions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('strategy_id', sa.BigInteger(), nullable=False),
        sa.Column('leg_id', sa.String(50)),

        sa.Column('trigger_reason', sa.Text(), nullable=False),
        sa.Column('suggestion_type', sa.String(30), nullable=False),  # shift, break, roll, exit, add_hedge, no_action
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB()),

        sa.Column('urgency', sa.String(20), server_default='medium'),  # low, medium, high, critical
        sa.Column('confidence', sa.Integer(), server_default='50'),  # 0-100

        sa.Column('one_click_action', sa.Boolean(), server_default='false'),
        sa.Column('action_params', postgresql.JSONB()),

        sa.Column('status', sa.String(20), server_default='active'),  # active, dismissed, executed, expired

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('responded_at', sa.DateTime()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['autopilot_strategies.id'], ondelete='CASCADE')
    )

    # Indexes for autopilot_adjustment_suggestions
    op.create_index('idx_suggestions_strategy', 'autopilot_adjustment_suggestions', ['strategy_id'])
    op.create_index('idx_suggestions_status', 'autopilot_adjustment_suggestions', ['status'])

    # Table: autopilot_option_chain_cache
    # Caches option chain data with Greeks
    op.create_table(
        'autopilot_option_chain_cache',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('underlying', sa.String(20), nullable=False),
        sa.Column('expiry', sa.Date(), nullable=False),
        sa.Column('strike', sa.Numeric(10, 2), nullable=False),
        sa.Column('option_type', sa.String(2), nullable=False),  # CE, PE

        sa.Column('tradingsymbol', sa.String(50), nullable=False),
        sa.Column('instrument_token', sa.BigInteger(), nullable=False),

        sa.Column('ltp', sa.Numeric(10, 2)),
        sa.Column('bid', sa.Numeric(10, 2)),
        sa.Column('ask', sa.Numeric(10, 2)),
        sa.Column('volume', sa.BigInteger()),
        sa.Column('oi', sa.BigInteger()),
        sa.Column('oi_change', sa.BigInteger()),

        sa.Column('iv', sa.Numeric(6, 2)),
        sa.Column('delta', sa.Numeric(6, 4)),
        sa.Column('gamma', sa.Numeric(8, 6)),
        sa.Column('theta', sa.Numeric(10, 2)),
        sa.Column('vega', sa.Numeric(8, 4)),

        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('underlying', 'expiry', 'strike', 'option_type')
    )

    # Indexes for autopilot_option_chain_cache
    op.create_index('idx_option_chain_underlying', 'autopilot_option_chain_cache', ['underlying', 'expiry'])
    op.create_index('idx_option_chain_delta', 'autopilot_option_chain_cache', ['underlying', 'expiry', 'option_type', 'delta'])

    # =========================================================================
    # STEP 2: ADD COLUMNS TO EXISTING TABLES
    # =========================================================================

    # Add columns to autopilot_strategies
    op.add_column('autopilot_strategies', sa.Column('position_legs_snapshot', postgresql.JSONB()))
    op.add_column('autopilot_strategies', sa.Column('net_delta', sa.Numeric(6, 4)))
    op.add_column('autopilot_strategies', sa.Column('net_theta', sa.Numeric(10, 2)))
    op.add_column('autopilot_strategies', sa.Column('net_gamma', sa.Numeric(8, 6)))
    op.add_column('autopilot_strategies', sa.Column('net_vega', sa.Numeric(8, 4)))
    op.add_column('autopilot_strategies', sa.Column('breakeven_lower', sa.Numeric(10, 2)))
    op.add_column('autopilot_strategies', sa.Column('breakeven_upper', sa.Numeric(10, 2)))
    op.add_column('autopilot_strategies', sa.Column('dte', sa.Integer()))

    # Add columns to autopilot_user_settings
    op.add_column('autopilot_user_settings', sa.Column('delta_watch_threshold', sa.Numeric(4, 2), server_default='0.20'))
    op.add_column('autopilot_user_settings', sa.Column('delta_warning_threshold', sa.Numeric(4, 2), server_default='0.30'))
    op.add_column('autopilot_user_settings', sa.Column('delta_danger_threshold', sa.Numeric(4, 2), server_default='0.40'))
    op.add_column('autopilot_user_settings', sa.Column('delta_alert_enabled', sa.Boolean(), server_default='true'))
    op.add_column('autopilot_user_settings', sa.Column('suggestions_enabled', sa.Boolean(), server_default='true'))
    op.add_column('autopilot_user_settings', sa.Column('prefer_round_strikes', sa.Boolean(), server_default='true'))


def downgrade() -> None:
    """
    Remove Phase 5 tables and columns.
    """

    # Remove columns from autopilot_user_settings
    op.drop_column('autopilot_user_settings', 'prefer_round_strikes')
    op.drop_column('autopilot_user_settings', 'suggestions_enabled')
    op.drop_column('autopilot_user_settings', 'delta_alert_enabled')
    op.drop_column('autopilot_user_settings', 'delta_danger_threshold')
    op.drop_column('autopilot_user_settings', 'delta_warning_threshold')
    op.drop_column('autopilot_user_settings', 'delta_watch_threshold')

    # Remove columns from autopilot_strategies
    op.drop_column('autopilot_strategies', 'dte')
    op.drop_column('autopilot_strategies', 'breakeven_upper')
    op.drop_column('autopilot_strategies', 'breakeven_lower')
    op.drop_column('autopilot_strategies', 'net_vega')
    op.drop_column('autopilot_strategies', 'net_gamma')
    op.drop_column('autopilot_strategies', 'net_theta')
    op.drop_column('autopilot_strategies', 'net_delta')
    op.drop_column('autopilot_strategies', 'position_legs_snapshot')

    # Drop indexes for autopilot_option_chain_cache
    op.drop_index('idx_option_chain_delta', 'autopilot_option_chain_cache')
    op.drop_index('idx_option_chain_underlying', 'autopilot_option_chain_cache')

    # Drop autopilot_option_chain_cache table
    op.drop_table('autopilot_option_chain_cache')

    # Drop indexes for autopilot_adjustment_suggestions
    op.drop_index('idx_suggestions_status', 'autopilot_adjustment_suggestions')
    op.drop_index('idx_suggestions_strategy', 'autopilot_adjustment_suggestions')

    # Drop autopilot_adjustment_suggestions table
    op.drop_table('autopilot_adjustment_suggestions')

    # Drop indexes for autopilot_position_legs
    op.drop_index('idx_position_legs_strategy_leg', 'autopilot_position_legs')
    op.drop_index('idx_position_legs_status', 'autopilot_position_legs')
    op.drop_index('idx_position_legs_strategy', 'autopilot_position_legs')

    # Drop autopilot_position_legs table
    op.drop_table('autopilot_position_legs')
