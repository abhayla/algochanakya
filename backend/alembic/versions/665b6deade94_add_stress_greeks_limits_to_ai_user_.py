"""add stress greeks limits to ai user config

Revision ID: 665b6deade94
Revises: 854fcf898768
Create Date: 2025-12-26 14:52:52.670631

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '665b6deade94'
down_revision: Union[str, Sequence[str], None] = '854fcf898768'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add stress Greeks limits to ai_user_config."""
    # Add columns as nullable first
    op.add_column('ai_user_config', sa.Column('max_stress_risk_score', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('ai_user_config', sa.Column('max_portfolio_delta', sa.Numeric(precision=6, scale=3), nullable=True))
    op.add_column('ai_user_config', sa.Column('max_portfolio_gamma', sa.Numeric(precision=8, scale=5), nullable=True))

    # Set default values for existing rows
    op.execute("UPDATE ai_user_config SET max_stress_risk_score = 75.00 WHERE max_stress_risk_score IS NULL")
    op.execute("UPDATE ai_user_config SET max_portfolio_delta = 1.000 WHERE max_portfolio_delta IS NULL")
    op.execute("UPDATE ai_user_config SET max_portfolio_gamma = 0.05000 WHERE max_portfolio_gamma IS NULL")

    # Now make them NOT NULL
    op.alter_column('ai_user_config', 'max_stress_risk_score', nullable=False)
    op.alter_column('ai_user_config', 'max_portfolio_delta', nullable=False)
    op.alter_column('ai_user_config', 'max_portfolio_gamma', nullable=False)


def downgrade() -> None:
    """Downgrade schema - Remove stress Greeks limits."""
    op.drop_column('ai_user_config', 'max_portfolio_gamma')
    op.drop_column('ai_user_config', 'max_portfolio_delta')
    op.drop_column('ai_user_config', 'max_stress_risk_score')
