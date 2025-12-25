"""ai_week4_decisions_log

Revision ID: 012_ai_week4
Revises: 010_ai_week2
Create Date: 2025-12-25 16:30:00

Week 4: AI Decision Logging for Paper Trading

Creates table to log all AI decisions with context and outcomes for:
- Strategy selection decisions
- Entry timing decisions
- Adjustment recommendations
- Exit decisions
- Regime change alerts
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012_ai_week4'
down_revision = '011_ai_week3'
branch_labels = None
depends_on = None


def upgrade():
    # Create ai_decisions_log table
    op.create_table(
        'ai_decisions_log',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('strategy_id', sa.BigInteger(), nullable=True),

        # Decision metadata
        sa.Column('decision_type', sa.VARCHAR(30), nullable=False),  # strategy_selection, entry, adjustment, exit, regime_change, health_alert
        sa.Column('action_taken', sa.VARCHAR(50), nullable=False),
        sa.Column('confidence', sa.DECIMAL(precision=5, scale=2), nullable=False),
        sa.Column('reasoning', sa.TEXT(), nullable=True),

        # Market context at decision time
        sa.Column('regime_at_decision', sa.VARCHAR(30), nullable=True),
        sa.Column('vix_at_decision', sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column('spot_at_decision', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('indicators_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Outcome tracking (filled after trade completes)
        sa.Column('outcome_pnl', sa.DECIMAL(precision=14, scale=2), nullable=True),
        sa.Column('outcome_score', sa.DECIMAL(precision=5, scale=2), nullable=True),  # Multi-factor quality score (0-100)
        sa.Column('was_correct', sa.Boolean(), nullable=True),

        # Timestamps
        sa.Column('decision_time', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('outcome_recorded_at', sa.TIMESTAMP(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['strategy_id'], ['autopilot_strategies.id'], ondelete='SET NULL'),
    )

    # Create indexes for common queries
    op.create_index('idx_ai_decisions_user_time', 'ai_decisions_log', ['user_id', 'decision_time'])
    op.create_index('idx_ai_decisions_type', 'ai_decisions_log', ['decision_type'])
    op.create_index('idx_ai_decisions_strategy', 'ai_decisions_log', ['strategy_id'])

    print("[OK] Created ai_decisions_log table for AI decision tracking")


def downgrade():
    op.drop_index('idx_ai_decisions_strategy', table_name='ai_decisions_log')
    op.drop_index('idx_ai_decisions_type', table_name='ai_decisions_log')
    op.drop_index('idx_ai_decisions_user_time', table_name='ai_decisions_log')
    op.drop_table('ai_decisions_log')
