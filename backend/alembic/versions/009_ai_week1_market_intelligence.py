"""AI Week 1: Market Intelligence Engine

Revision ID: 009_ai_week1
Revises: c16511af0abe
Create Date: 2025-12-24

Adds ai_market_snapshots table for storing market regime classifications
and technical indicators snapshots used for autonomous AI trading decisions.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '009_ai_week1'
down_revision = 'c16511af0abe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create AI market intelligence tables."""

    # Create ai_market_snapshots table
    op.create_table(
        'ai_market_snapshots',

        # Primary Key
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),

        # Timestamp
        sa.Column('snapshot_time', sa.DateTime(timezone=True), nullable=False),

        # Underlying
        sa.Column('underlying', sa.String(20), nullable=False),

        # Regime
        sa.Column('regime_type', sa.String(30), nullable=False),
        sa.Column('confidence', sa.Numeric(5, 2), nullable=False),

        # Spot & VIX
        sa.Column('spot_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('vix', sa.Numeric(6, 2), nullable=True),

        # Trend Indicators
        sa.Column('rsi_14', sa.Numeric(6, 2), nullable=True),
        sa.Column('adx_14', sa.Numeric(6, 2), nullable=True),
        sa.Column('ema_9', sa.Numeric(10, 2), nullable=True),
        sa.Column('ema_21', sa.Numeric(10, 2), nullable=True),
        sa.Column('ema_50', sa.Numeric(10, 2), nullable=True),

        # Volatility Indicators
        sa.Column('atr_14', sa.Numeric(10, 2), nullable=True),
        sa.Column('bb_upper', sa.Numeric(10, 2), nullable=True),
        sa.Column('bb_lower', sa.Numeric(10, 2), nullable=True),
        sa.Column('bb_width_pct', sa.Numeric(6, 2), nullable=True),

        # OI Data (for future use)
        sa.Column('oi_pcr', sa.Numeric(5, 2), nullable=True),
        sa.Column('max_pain', sa.Numeric(10, 2), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        # Constraints
        sa.CheckConstraint('confidence >= 0 AND confidence <= 100',
                          name='chk_confidence_range')
    )

    # Indexes for efficient querying
    op.create_index(
        'idx_ai_market_snapshots_time',
        'ai_market_snapshots',
        [sa.text('snapshot_time DESC')]
    )

    op.create_index(
        'idx_ai_market_snapshots_underlying',
        'ai_market_snapshots',
        ['underlying', sa.text('snapshot_time DESC')]
    )

    op.create_index(
        'idx_ai_market_snapshots_regime',
        'ai_market_snapshots',
        ['regime_type']
    )


def downgrade() -> None:
    """Drop AI market intelligence tables."""

    # Drop indexes
    op.drop_index('idx_ai_market_snapshots_regime', table_name='ai_market_snapshots')
    op.drop_index('idx_ai_market_snapshots_underlying', table_name='ai_market_snapshots')
    op.drop_index('idx_ai_market_snapshots_time', table_name='ai_market_snapshots')

    # Drop table
    op.drop_table('ai_market_snapshots')
