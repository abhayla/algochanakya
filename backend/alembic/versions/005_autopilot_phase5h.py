"""
AutoPilot Phase 5H - Adjustment Intelligence Migration

Revision ID: 005_autopilot_phase5h
Revises: 004_autopilot_phase5
Create Date: 2024-12-14

This migration adds support for:
- Offensive/Defensive categorization for adjustment suggestions (Feature #45)
- Enhanced suggestion metadata

New columns on autopilot_adjustment_suggestions:
- category (defensive, offensive, neutral)

Run with: alembic upgrade head
Rollback with: alembic downgrade 004_autopilot_phase5
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '005_autopilot_phase5h'
down_revision = '004_autopilot_phase5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add Phase 5H columns for adjustment intelligence.
    """
    # Add category column to autopilot_adjustment_suggestions
    op.add_column(
        'autopilot_adjustment_suggestions',
        sa.Column('category', sa.String(20), server_default='defensive', nullable=False)
    )

    # Add comment explaining the column
    op.execute("""
        COMMENT ON COLUMN autopilot_adjustment_suggestions.category IS
        'Adjustment category: defensive (reduces risk), offensive (increases risk for premium), neutral (rebalances)'
    """)


def downgrade() -> None:
    """
    Remove Phase 5H columns.
    """
    op.drop_column('autopilot_adjustment_suggestions', 'category')
