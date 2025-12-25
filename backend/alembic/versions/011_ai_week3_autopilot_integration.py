"""AI Week 3: AutoPilot Integration - Add AI metadata fields

Revision ID: 011_ai_week3
Revises: 010_ai_week2
Create Date: 2025-12-25 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011_ai_week3'
down_revision = '010_ai_week2'
branch_labels = None
depends_on = None


def upgrade():
    """Add AI metadata fields to AutoPilot tables."""

    # Add AI fields to autopilot_strategies
    op.add_column('autopilot_strategies',
        sa.Column('ai_deployed', sa.Boolean(), nullable=True, default=False,
                  comment='Whether this strategy was deployed by AI'))
    op.add_column('autopilot_strategies',
        sa.Column('ai_confidence_score', sa.DECIMAL(5, 2), nullable=True,
                  comment='AI confidence score (0-100) for this strategy'))
    op.add_column('autopilot_strategies',
        sa.Column('ai_regime_type', sa.String(30), nullable=True,
                  comment='Market regime at deployment (TRENDING_BULLISH, RANGEBOUND, etc.)'))
    op.add_column('autopilot_strategies',
        sa.Column('ai_lots_tier', sa.String(20), nullable=True,
                  comment='Position sizing tier used (SKIP, LOW, MEDIUM, HIGH)'))
    op.add_column('autopilot_strategies',
        sa.Column('ai_explanation', sa.Text(), nullable=True,
                  comment='AI-generated explanation for strategy selection'))

    # Add AI fields to autopilot_orders
    op.add_column('autopilot_orders',
        sa.Column('ai_sizing_mode', sa.String(20), nullable=True,
                  comment='Position sizing mode used (fixed, tiered, kelly)'))
    op.add_column('autopilot_orders',
        sa.Column('ai_tier_multiplier', sa.DECIMAL(5, 2), nullable=True,
                  comment='Tier multiplier applied to base lots'))

    # Create index for AI-deployed strategies
    op.create_index('idx_autopilot_strategies_ai_deployed',
                    'autopilot_strategies', ['ai_deployed', 'user_id'])
    op.create_index('idx_autopilot_strategies_ai_confidence',
                    'autopilot_strategies', ['ai_confidence_score'])


def downgrade():
    """Remove AI metadata fields from AutoPilot tables."""

    # Drop indexes
    op.drop_index('idx_autopilot_strategies_ai_confidence', 'autopilot_strategies')
    op.drop_index('idx_autopilot_strategies_ai_deployed', 'autopilot_strategies')

    # Drop columns from autopilot_orders
    op.drop_column('autopilot_orders', 'ai_tier_multiplier')
    op.drop_column('autopilot_orders', 'ai_sizing_mode')

    # Drop columns from autopilot_strategies
    op.drop_column('autopilot_strategies', 'ai_explanation')
    op.drop_column('autopilot_strategies', 'ai_lots_tier')
    op.drop_column('autopilot_strategies', 'ai_regime_type')
    op.drop_column('autopilot_strategies', 'ai_confidence_score')
    op.drop_column('autopilot_strategies', 'ai_deployed')
