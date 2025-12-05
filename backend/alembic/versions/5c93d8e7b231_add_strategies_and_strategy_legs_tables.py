"""add strategies and strategy_legs tables

Revision ID: 5c93d8e7b231
Revises: 4b82c9f6a120
Create Date: 2025-12-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5c93d8e7b231'
down_revision: Union[str, None] = '4b82c9f6a120'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create strategies table
    op.create_table('strategies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('underlying', sa.String(length=20), nullable=False),
        sa.Column('share_code', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='open', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_strategies_user', 'strategies', ['user_id'], unique=False)
    op.create_index('idx_strategies_share_code', 'strategies', ['share_code'], unique=True)
    op.create_index(op.f('ix_strategies_id'), 'strategies', ['id'], unique=False)

    # Create strategy_legs table
    op.create_table('strategy_legs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=False),
        sa.Column('contract_type', sa.String(length=10), nullable=False),
        sa.Column('transaction_type', sa.String(length=10), nullable=False),
        sa.Column('strike_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('lots', sa.Integer(), server_default='1', nullable=False),
        sa.Column('strategy_type', sa.String(length=50), nullable=True),
        sa.Column('entry_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('exit_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('instrument_token', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.String(length=50), nullable=True),
        sa.Column('position_status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_strategy_legs_strategy', 'strategy_legs', ['strategy_id'], unique=False)
    op.create_index(op.f('ix_strategy_legs_id'), 'strategy_legs', ['id'], unique=False)


def downgrade() -> None:
    # Drop strategy_legs table
    op.drop_index(op.f('ix_strategy_legs_id'), table_name='strategy_legs')
    op.drop_index('idx_strategy_legs_strategy', table_name='strategy_legs')
    op.drop_table('strategy_legs')

    # Drop strategies table
    op.drop_index(op.f('ix_strategies_id'), table_name='strategies')
    op.drop_index('idx_strategies_share_code', table_name='strategies')
    op.drop_index('idx_strategies_user', table_name='strategies')
    op.drop_table('strategies')
