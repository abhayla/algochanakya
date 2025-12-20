"""
AutoPilot Trading Modes - Live/Paper Trading Support

Revision ID: 008_autopilot_trading_modes
Revises: 0f99bf85164b
Create Date: 2025-12-20

This migration adds:
1. Trading mode enum (live, paper)
2. Order batches table for grouping related orders
3. Market snapshot fields (Greeks, IV, Spot, VIX) on orders
4. Trading mode tracking on strategies and orders
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = '008_autopilot_trading_modes'
down_revision = '0f99bf85164b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add trading modes and enhanced order tracking.
    """

    # =========================================================================
    # STEP 1: CREATE TRADING MODE ENUM
    # =========================================================================

    op.execute("""
        CREATE TYPE autopilot_trading_mode AS ENUM (
            'live',
            'paper'
        )
    """)

    # =========================================================================
    # STEP 2: CREATE ORDER BATCHES TABLE
    # =========================================================================

    op.create_table(
        'autopilot_order_batches',

        # Primary Key
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Foreign Keys
        sa.Column('strategy_id', sa.BigInteger, sa.ForeignKey('autopilot_strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),

        # Batch Context
        sa.Column('purpose', postgresql.ENUM('entry', 'adjustment', 'hedge', 'exit', 'roll_close', 'roll_open', 'kill_switch', name='autopilot_order_purpose', create_type=False), nullable=False),
        sa.Column('rule_name', sa.String(100), nullable=True),
        sa.Column('adjustment_log_id', sa.BigInteger, nullable=True),

        # Batch Status
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('total_orders', sa.Integer, nullable=False, server_default='0'),
        sa.Column('completed_orders', sa.Integer, nullable=False, server_default='0'),
        sa.Column('failed_orders', sa.Integer, nullable=False, server_default='0'),

        # Market Snapshot (at batch creation)
        sa.Column('spot_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('vix', sa.Numeric(6, 2), nullable=True),

        # Greeks Snapshot (aggregate for all legs in batch)
        sa.Column('net_delta', sa.Numeric(6, 4), nullable=True),
        sa.Column('net_gamma', sa.Numeric(8, 6), nullable=True),
        sa.Column('net_theta', sa.Numeric(10, 2), nullable=True),
        sa.Column('net_vega', sa.Numeric(8, 4), nullable=True),

        # Triggered Condition
        sa.Column('triggered_condition', JSONB, nullable=True),
        sa.Column('trigger_value', JSONB, nullable=True),

        # Trading Mode
        sa.Column('trading_mode', postgresql.ENUM('live', 'paper', name='autopilot_trading_mode', create_type=False), nullable=False, server_default='paper'),

        # Timing
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        # Execution Stats
        sa.Column('total_slippage', sa.Numeric(12, 2), nullable=True),
        sa.Column('execution_duration_ms', sa.Integer, nullable=True),
    )

    # Create indexes for order batches
    op.create_index('idx_order_batches_strategy', 'autopilot_order_batches', ['strategy_id'])
    op.create_index('idx_order_batches_user', 'autopilot_order_batches', ['user_id'])
    op.create_index('idx_order_batches_created', 'autopilot_order_batches', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_order_batches_trading_mode', 'autopilot_order_batches', ['trading_mode'])

    # =========================================================================
    # STEP 3: ADD COLUMNS TO autopilot_orders TABLE
    # =========================================================================

    # Trading Mode
    op.add_column('autopilot_orders',
        sa.Column('trading_mode', postgresql.ENUM('live', 'paper', name='autopilot_trading_mode', create_type=False), nullable=True, server_default='paper'))

    # Batch Reference
    op.add_column('autopilot_orders',
        sa.Column('batch_id', UUID(as_uuid=True), nullable=True))
    op.add_column('autopilot_orders',
        sa.Column('batch_sequence', sa.Integer, nullable=True))

    # Triggered Condition
    op.add_column('autopilot_orders',
        sa.Column('triggered_condition', JSONB, nullable=True))

    # Market Context at Order Time
    op.add_column('autopilot_orders',
        sa.Column('spot_at_order', sa.Numeric(10, 2), nullable=True))
    op.add_column('autopilot_orders',
        sa.Column('vix_at_order', sa.Numeric(6, 2), nullable=True))

    # Greeks at Order Time
    op.add_column('autopilot_orders',
        sa.Column('delta_at_order', sa.Numeric(6, 4), nullable=True))
    op.add_column('autopilot_orders',
        sa.Column('gamma_at_order', sa.Numeric(8, 6), nullable=True))
    op.add_column('autopilot_orders',
        sa.Column('theta_at_order', sa.Numeric(10, 2), nullable=True))
    op.add_column('autopilot_orders',
        sa.Column('vega_at_order', sa.Numeric(8, 4), nullable=True))
    op.add_column('autopilot_orders',
        sa.Column('iv_at_order', sa.Numeric(6, 2), nullable=True))

    # Order Book Snapshot
    op.add_column('autopilot_orders',
        sa.Column('oi_at_order', sa.BigInteger, nullable=True))
    op.add_column('autopilot_orders',
        sa.Column('bid_at_order', sa.Numeric(10, 2), nullable=True))
    op.add_column('autopilot_orders',
        sa.Column('ask_at_order', sa.Numeric(10, 2), nullable=True))

    # Create foreign key constraint for batch_id
    op.create_foreign_key(
        'fk_autopilot_orders_batch_id',
        'autopilot_orders', 'autopilot_order_batches',
        ['batch_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create indexes for new columns
    op.create_index('idx_autopilot_orders_batch_id', 'autopilot_orders', ['batch_id'])
    op.create_index('idx_autopilot_orders_trading_mode', 'autopilot_orders', ['trading_mode'])

    # =========================================================================
    # STEP 4: ADD COLUMNS TO autopilot_strategies TABLE
    # =========================================================================

    # Default trading mode for strategy
    op.add_column('autopilot_strategies',
        sa.Column('trading_mode', postgresql.ENUM('live', 'paper', name='autopilot_trading_mode', create_type=False), nullable=True))

    # Mode when strategy was activated
    op.add_column('autopilot_strategies',
        sa.Column('activated_in_mode', postgresql.ENUM('live', 'paper', name='autopilot_trading_mode', create_type=False), nullable=True))

    # Create index
    op.create_index('idx_autopilot_strategies_trading_mode', 'autopilot_strategies', ['trading_mode'])


def downgrade() -> None:
    """
    Rollback trading modes and enhanced order tracking.
    """

    # Drop indexes from autopilot_strategies
    op.drop_index('idx_autopilot_strategies_trading_mode', 'autopilot_strategies')

    # Drop columns from autopilot_strategies
    op.drop_column('autopilot_strategies', 'activated_in_mode')
    op.drop_column('autopilot_strategies', 'trading_mode')

    # Drop indexes from autopilot_orders
    op.drop_index('idx_autopilot_orders_trading_mode', 'autopilot_orders')
    op.drop_index('idx_autopilot_orders_batch_id', 'autopilot_orders')

    # Drop foreign key constraint
    op.drop_constraint('fk_autopilot_orders_batch_id', 'autopilot_orders', type_='foreignkey')

    # Drop columns from autopilot_orders
    op.drop_column('autopilot_orders', 'ask_at_order')
    op.drop_column('autopilot_orders', 'bid_at_order')
    op.drop_column('autopilot_orders', 'oi_at_order')
    op.drop_column('autopilot_orders', 'iv_at_order')
    op.drop_column('autopilot_orders', 'vega_at_order')
    op.drop_column('autopilot_orders', 'theta_at_order')
    op.drop_column('autopilot_orders', 'gamma_at_order')
    op.drop_column('autopilot_orders', 'delta_at_order')
    op.drop_column('autopilot_orders', 'vix_at_order')
    op.drop_column('autopilot_orders', 'spot_at_order')
    op.drop_column('autopilot_orders', 'triggered_condition')
    op.drop_column('autopilot_orders', 'batch_sequence')
    op.drop_column('autopilot_orders', 'batch_id')
    op.drop_column('autopilot_orders', 'trading_mode')

    # Drop indexes from order batches
    op.drop_index('idx_order_batches_trading_mode', 'autopilot_order_batches')
    op.drop_index('idx_order_batches_created', 'autopilot_order_batches')
    op.drop_index('idx_order_batches_user', 'autopilot_order_batches')
    op.drop_index('idx_order_batches_strategy', 'autopilot_order_batches')

    # Drop order batches table
    op.drop_table('autopilot_order_batches')

    # Drop trading mode enum
    op.execute('DROP TYPE autopilot_trading_mode')
