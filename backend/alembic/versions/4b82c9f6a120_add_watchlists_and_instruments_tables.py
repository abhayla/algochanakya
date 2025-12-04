"""add watchlists and instruments tables

Revision ID: 4b82c9f6a120
Revises: 3078a2344f3d
Create Date: 2025-12-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4b82c9f6a120'
down_revision: Union[str, None] = '3078a2344f3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create instruments table
    op.create_table('instruments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_token', sa.Integer(), nullable=False),
        sa.Column('exchange_token', sa.Integer(), nullable=True),
        sa.Column('tradingsymbol', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('exchange', sa.String(length=10), nullable=False),
        sa.Column('segment', sa.String(length=20), nullable=True),
        sa.Column('instrument_type', sa.String(length=20), nullable=True),
        sa.Column('strike', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('expiry', sa.Date(), nullable=True),
        sa.Column('lot_size', sa.Integer(), nullable=False),
        sa.Column('tick_size', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_instruments_exchange', 'instruments', ['exchange'], unique=False)
    op.create_index('idx_instruments_token', 'instruments', ['instrument_token'], unique=False)
    op.create_index('idx_instruments_tradingsymbol', 'instruments', ['tradingsymbol'], unique=False)
    op.create_index(op.f('ix_instruments_id'), 'instruments', ['id'], unique=False)
    op.create_index(op.f('ix_instruments_instrument_token'), 'instruments', ['instrument_token'], unique=True)
    op.create_index(op.f('ix_instruments_tradingsymbol'), 'instruments', ['tradingsymbol'], unique=False)

    # Create watchlists table
    op.create_table('watchlists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('instruments', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_watchlists_id'), 'watchlists', ['id'], unique=False)
    op.create_index(op.f('ix_watchlists_user_id'), 'watchlists', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop watchlists table
    op.drop_index(op.f('ix_watchlists_user_id'), table_name='watchlists')
    op.drop_index(op.f('ix_watchlists_id'), table_name='watchlists')
    op.drop_table('watchlists')

    # Drop instruments table
    op.drop_index(op.f('ix_instruments_tradingsymbol'), table_name='instruments')
    op.drop_index(op.f('ix_instruments_instrument_token'), table_name='instruments')
    op.drop_index(op.f('ix_instruments_id'), table_name='instruments')
    op.drop_index('idx_instruments_tradingsymbol', table_name='instruments')
    op.drop_index('idx_instruments_token', table_name='instruments')
    op.drop_index('idx_instruments_exchange', table_name='instruments')
    op.drop_table('instruments')
