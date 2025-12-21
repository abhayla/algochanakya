"""merge autopilot heads

Revision ID: c79149025c75
Revises: 007_autopilot_phase3_reentry, 008_autopilot_trading_modes
Create Date: 2025-12-21 14:37:23.685178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c79149025c75'
down_revision: Union[str, Sequence[str], None] = ('007_autopilot_phase3_reentry', '008_autopilot_trading_modes')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
