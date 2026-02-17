"""Add order_broker column and platform market_data_source

Revision ID: a1b2c3d4e5f6
Revises: bc0dd372730d
Create Date: 2026-02-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'bc0dd372730d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    - Add order_broker column (nullable, for future order execution broker selection)
    - Update market_data_source constraint to include 'platform' as a valid value
    - Update market_data_source default to 'platform'
    """
    # Add order_broker column
    op.add_column(
        'user_preferences',
        sa.Column('order_broker', sa.String(20), nullable=True)
    )

    # Add check constraint for order_broker
    op.create_check_constraint(
        'check_order_broker',
        'user_preferences',
        "order_broker IS NULL OR order_broker IN ('kite', 'angel', 'upstox', 'dhan', 'fyers', 'paytm')"
    )

    # Update market_data_source constraint to include 'platform'
    op.drop_constraint('check_market_data_source', 'user_preferences', type_='check')
    op.create_check_constraint(
        'check_market_data_source',
        'user_preferences',
        "market_data_source IN ('platform', 'smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm')"
    )

    # Update default for market_data_source to 'platform'
    op.alter_column(
        'user_preferences',
        'market_data_source',
        server_default='platform'
    )


def downgrade() -> None:
    """Revert order_broker column and platform market_data_source changes."""
    # Remove order_broker check constraint and column
    op.drop_constraint('check_order_broker', 'user_preferences', type_='check')
    op.drop_column('user_preferences', 'order_broker')

    # Revert market_data_source constraint (remove 'platform')
    op.drop_constraint('check_market_data_source', 'user_preferences', type_='check')
    op.create_check_constraint(
        'check_market_data_source',
        'user_preferences',
        "market_data_source IN ('smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm')"
    )

    # Revert default back to 'smartapi'
    op.alter_column(
        'user_preferences',
        'market_data_source',
        server_default='smartapi'
    )
