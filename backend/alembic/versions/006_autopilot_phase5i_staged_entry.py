"""AutoPilot Phase 5I - Staged Entry (Half-Size & Staggered Entry)

Revision ID: 006_autopilot_phase5i
Revises: 005_autopilot_phase5h
Create Date: 2025-12-14

Changes:
- Add staged_entry_config JSONB column to autopilot_strategies table
- Update autopilot_strategy_status enum to include 'waiting_staged_entry' and 'cancelled'
- Add indexes for staged entry queries
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '006_autopilot_phase5i'
down_revision = '005_autopilot_phase5h'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new status values to existing enum
    op.execute("""
        ALTER TYPE autopilot_strategy_status ADD VALUE IF NOT EXISTS 'waiting_staged_entry';
        ALTER TYPE autopilot_strategy_status ADD VALUE IF NOT EXISTS 'cancelled';
    """)

    # Add staged_entry_config column to autopilot_strategies table
    op.add_column(
        'autopilot_strategies',
        sa.Column('staged_entry_config', JSONB, nullable=True)
    )

    # Add index for filtering by staged entry strategies
    op.create_index(
        'ix_autopilot_strategies_staged_entry',
        'autopilot_strategies',
        ['status'],
        postgresql_where=sa.text("staged_entry_config IS NOT NULL")
    )

    # Add comment to column
    op.execute("""
        COMMENT ON COLUMN autopilot_strategies.staged_entry_config IS
        'Phase 5I: Configuration for staged entry (half-size or staggered mode).
        Structure:
        {
            "enabled": true,
            "mode": "half_size" | "staggered",
            "initial_stage": {...},    // for half_size mode
            "add_stage": {...},         // for half_size mode
            "leg_entries": [...]        // for staggered mode
        }';
    """)


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_autopilot_strategies_staged_entry', table_name='autopilot_strategies')

    # Drop column
    op.drop_column('autopilot_strategies', 'staged_entry_config')

    # Note: Cannot remove enum values in PostgreSQL easily
    # The enum values 'waiting_staged_entry' and 'cancelled' will remain
    # but won't be used after downgrade
    print("Note: Enum values 'waiting_staged_entry' and 'cancelled' cannot be removed from autopilot_strategy_status enum")
