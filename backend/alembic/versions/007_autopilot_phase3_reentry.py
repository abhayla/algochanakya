"""Phase 3: Add re-entry configuration and status

Revision ID: 007_autopilot_phase3_reentry
Revises: 0f99bf85164b
Create Date: 2024-12-17

Phase 3: Re-Entry & Advanced Adjustments
- Add REENTRY_WAITING status to autopilot_strategy_status enum
- Add reentry_config JSONB column to autopilot_strategies table

Re-entry config structure:
{
    "enabled": true,
    "max_reentries": 2,
    "cooldown_minutes": 15,
    "conditions": {"logic": "AND", "conditions": [...]},
    "reentry_count": 0
}
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_autopilot_phase3_reentry'
down_revision = '0f99bf85164b'
branch_labels = None
depends_on = None


def upgrade():
    # Add reentry_waiting to autopilot_strategy_status enum
    op.execute("""
        ALTER TYPE autopilot_strategy_status ADD VALUE IF NOT EXISTS 'reentry_waiting';
    """)

    # Add reentry_config column to autopilot_strategies
    op.add_column(
        'autopilot_strategies',
        sa.Column(
            'reentry_config',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Re-entry settings: enabled, max_reentries, cooldown_minutes, conditions, reentry_count'
        )
    )


def downgrade():
    # Remove reentry_config column
    op.drop_column('autopilot_strategies', 'reentry_config')

    # Note: Cannot remove enum value in PostgreSQL without recreating the entire enum type
    # This would require dropping and recreating all columns using this enum
    # For safety, we'll leave the enum value in place
    pass
