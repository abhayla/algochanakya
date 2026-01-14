"""Update user_preferences constraint for 6 brokers

Revision ID: bc0dd372730d
Revises: 30e8151f97fd
Create Date: 2026-01-14 23:59:14.428137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc0dd372730d'
down_revision: Union[str, Sequence[str], None] = '30e8151f97fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update user_preferences.market_data_source constraint to support 6 brokers."""
    # Drop old constraint
    op.drop_constraint('check_market_data_source', 'user_preferences', type_='check')

    # Create new constraint with all 6 brokers
    op.create_check_constraint(
        'check_market_data_source',
        'user_preferences',
        "market_data_source IN ('smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm')"
    )


def downgrade() -> None:
    """Revert to original 2-broker constraint."""
    # Drop new constraint
    op.drop_constraint('check_market_data_source', 'user_preferences', type_='check')

    # Recreate old constraint (only smartapi, kite)
    op.create_check_constraint(
        'check_market_data_source',
        'user_preferences',
        "market_data_source IN ('smartapi', 'kite')"
    )
