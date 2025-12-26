"""add retraining frequency optimization to ai_user_config

Revision ID: 4fdaa5624e7d
Revises: 3e53c2250f8a
Create Date: 2025-12-26 20:33:33.113626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fdaa5624e7d'
down_revision: Union[str, Sequence[str], None] = '3e53c2250f8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Priority 2.3: Retraining Frequency Optimization
    Adds adaptive retraining cadence configuration to AIUserConfig.
    """
    # Step 1: Add columns as nullable
    op.add_column('ai_user_config', sa.Column('retraining_cadence', sa.String(length=20), nullable=True))
    op.add_column('ai_user_config', sa.Column('retraining_volume_threshold', sa.Integer(), nullable=True))
    op.add_column('ai_user_config', sa.Column('high_volume_trades_per_week', sa.Integer(), nullable=True))
    op.add_column('ai_user_config', sa.Column('last_user_model_retrain_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ai_user_config', sa.Column('min_model_stability_threshold', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('ai_user_config', sa.Column('enable_confidence_weighting', sa.Boolean(), nullable=True))
    op.add_column('ai_user_config', sa.Column('trades_since_last_retrain', sa.Integer(), nullable=True))

    # Step 2: Set default values for existing rows
    op.execute("UPDATE ai_user_config SET retraining_cadence = 'weekly' WHERE retraining_cadence IS NULL")
    op.execute("UPDATE ai_user_config SET retraining_volume_threshold = 25 WHERE retraining_volume_threshold IS NULL")
    op.execute("UPDATE ai_user_config SET high_volume_trades_per_week = 50 WHERE high_volume_trades_per_week IS NULL")
    op.execute("UPDATE ai_user_config SET min_model_stability_threshold = 5.00 WHERE min_model_stability_threshold IS NULL")
    op.execute("UPDATE ai_user_config SET enable_confidence_weighting = true WHERE enable_confidence_weighting IS NULL")
    op.execute("UPDATE ai_user_config SET trades_since_last_retrain = 0 WHERE trades_since_last_retrain IS NULL")

    # Step 3: Make columns NOT NULL (except last_user_model_retrain_at which should remain nullable)
    op.alter_column('ai_user_config', 'retraining_cadence', nullable=False)
    op.alter_column('ai_user_config', 'retraining_volume_threshold', nullable=False)
    op.alter_column('ai_user_config', 'high_volume_trades_per_week', nullable=False)
    op.alter_column('ai_user_config', 'min_model_stability_threshold', nullable=False)
    op.alter_column('ai_user_config', 'enable_confidence_weighting', nullable=False)
    op.alter_column('ai_user_config', 'trades_since_last_retrain', nullable=False)

    # Step 4: Add check constraints
    op.create_check_constraint(
        'chk_retraining_volume_threshold_positive',
        'ai_user_config',
        'retraining_volume_threshold > 0'
    )
    op.create_check_constraint(
        'chk_high_volume_trades_per_week_positive',
        'ai_user_config',
        'high_volume_trades_per_week > 0'
    )
    op.create_check_constraint(
        'chk_min_model_stability_threshold_range',
        'ai_user_config',
        'min_model_stability_threshold >= 0 AND min_model_stability_threshold <= 100'
    )
    op.create_check_constraint(
        'chk_trades_since_last_retrain_non_negative',
        'ai_user_config',
        'trades_since_last_retrain >= 0'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Step 1: Drop check constraints
    op.drop_constraint('chk_trades_since_last_retrain_non_negative', 'ai_user_config', type_='check')
    op.drop_constraint('chk_min_model_stability_threshold_range', 'ai_user_config', type_='check')
    op.drop_constraint('chk_high_volume_trades_per_week_positive', 'ai_user_config', type_='check')
    op.drop_constraint('chk_retraining_volume_threshold_positive', 'ai_user_config', type_='check')

    # Step 2: Drop columns
    op.drop_column('ai_user_config', 'trades_since_last_retrain')
    op.drop_column('ai_user_config', 'enable_confidence_weighting')
    op.drop_column('ai_user_config', 'min_model_stability_threshold')
    op.drop_column('ai_user_config', 'last_user_model_retrain_at')
    op.drop_column('ai_user_config', 'high_volume_trades_per_week')
    op.drop_column('ai_user_config', 'retraining_volume_threshold')
    op.drop_column('ai_user_config', 'retraining_cadence')
