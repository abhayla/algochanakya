"""add_source_broker_option_type_to_instruments

Revision ID: d348ce964ac9
Revises: efdf0659b0ab
Create Date: 2026-03-06 16:27:37.440827

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd348ce964ac9'
down_revision: Union[str, Sequence[str], None] = 'efdf0659b0ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns
    op.add_column('instruments', sa.Column('option_type', sa.String(length=5), nullable=True))
    # Add source_broker as nullable first, then backfill, then make NOT NULL
    op.add_column('instruments', sa.Column('source_broker', sa.String(length=20), nullable=True))

    # Backfill existing rows with 'kite' (they were from Kite CSV)
    op.execute("UPDATE instruments SET source_broker = 'kite' WHERE source_broker IS NULL")
    # Backfill option_type from instrument_type for existing CE/PE rows
    op.execute("UPDATE instruments SET option_type = instrument_type WHERE instrument_type IN ('CE', 'PE')")

    # Now make source_broker NOT NULL
    op.alter_column('instruments', 'source_broker', nullable=False, server_default='kite')

    # Change instrument_token from unique to non-unique (different brokers have different tokens)
    op.drop_index(op.f('ix_instruments_instrument_token'), table_name='instruments')
    op.create_index(op.f('ix_instruments_instrument_token'), 'instruments', ['instrument_token'], unique=False)

    # Add composite unique constraint
    op.create_unique_constraint('uq_instrument_token_source_broker', 'instruments', ['instrument_token', 'source_broker'])

    # Add new indexes
    op.create_index('idx_instruments_name_exchange_type', 'instruments', ['name', 'exchange', 'instrument_type'], unique=False)
    op.create_index('idx_instruments_source_broker', 'instruments', ['source_broker'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_instrument_token_source_broker', 'instruments', type_='unique')
    op.drop_index('idx_instruments_source_broker', table_name='instruments')
    op.drop_index('idx_instruments_name_exchange_type', table_name='instruments')
    op.drop_index(op.f('ix_instruments_instrument_token'), table_name='instruments')
    op.create_index(op.f('ix_instruments_instrument_token'), 'instruments', ['instrument_token'], unique=True)
    op.drop_column('instruments', 'source_broker')
    op.drop_column('instruments', 'option_type')
