"""AI Week 2: User Configuration

Revision ID: 010_ai_week2
Revises: 009_ai_week1
Create Date: 2025-12-24

Adds ai_user_config table for storing user-specific AI trading configuration
including autonomy settings, deployment schedule, position sizing, and limits.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '010_ai_week2'
down_revision = '009_ai_week1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create AI user configuration table."""

    # Create ai_user_config table
    op.create_table(
        'ai_user_config',

        # Primary Key
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),

        # Foreign Key to users
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Autonomy Settings
        sa.Column('ai_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('autonomy_mode', sa.String(20), nullable=False, server_default='paper'),

        # Auto-Deployment Settings
        sa.Column('auto_deploy_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deploy_time', sa.String(5), nullable=True, server_default='09:20'),
        sa.Column('deploy_days', postgresql.ARRAY(sa.String()), nullable=False,
                  server_default="{'MON','TUE','WED','THU','FRI'}"),
        sa.Column('skip_event_days', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('skip_weekly_expiry', sa.Boolean(), nullable=False, server_default='false'),

        # Strategy Universe (JSONB array of template IDs)
        sa.Column('allowed_strategies', postgresql.JSONB, nullable=False,
                  server_default='[]'),

        # Position Sizing
        sa.Column('sizing_mode', sa.String(20), nullable=False, server_default='tiered'),
        sa.Column('base_lots', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('confidence_tiers', postgresql.JSONB, nullable=False,
                  server_default='''[
                      {"name": "SKIP", "min": 0, "max": 60, "multiplier": 0},
                      {"name": "LOW", "min": 60, "max": 75, "multiplier": 1.0},
                      {"name": "MEDIUM", "min": 75, "max": 85, "multiplier": 1.5},
                      {"name": "HIGH", "min": 85, "max": 100, "multiplier": 2.0}
                  ]'''),

        # AI-Specific Limits
        sa.Column('max_lots_per_strategy', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('max_lots_per_day', sa.Integer(), nullable=False, server_default='6'),
        sa.Column('max_strategies_per_day', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('min_confidence_to_trade', sa.Numeric(5, 2), nullable=False, server_default='60.00'),
        sa.Column('max_vix_to_trade', sa.Numeric(5, 2), nullable=False, server_default='25.00'),
        sa.Column('min_dte_to_enter', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('weekly_loss_limit', sa.Numeric(12, 2), nullable=False, server_default='50000.00'),

        # Preferred Underlyings
        sa.Column('preferred_underlyings', postgresql.ARRAY(sa.String(20)), nullable=False,
                  server_default="{'NIFTY', 'BANKNIFTY'}"),

        # Paper Trading Graduation
        sa.Column('paper_start_date', sa.Date(), nullable=True),
        sa.Column('paper_trades_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('paper_win_rate', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('paper_total_pnl', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('paper_graduation_approved', sa.Boolean(), nullable=False, server_default='false'),

        # Claude API
        sa.Column('claude_api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('enable_ai_explanations', sa.Boolean(), nullable=False, server_default='true'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_ai_user_config_user_id'),
        sa.CheckConstraint('min_confidence_to_trade >= 0 AND min_confidence_to_trade <= 100',
                          name='chk_min_confidence_range'),
        sa.CheckConstraint('max_vix_to_trade > 0',
                          name='chk_max_vix_positive'),
        sa.CheckConstraint('base_lots > 0',
                          name='chk_base_lots_positive'),
        sa.CheckConstraint('max_lots_per_strategy > 0',
                          name='chk_max_lots_per_strategy_positive'),
        sa.CheckConstraint('max_lots_per_day > 0',
                          name='chk_max_lots_per_day_positive'),
        sa.CheckConstraint('max_strategies_per_day > 0',
                          name='chk_max_strategies_per_day_positive'),
        sa.CheckConstraint('min_dte_to_enter >= 0',
                          name='chk_min_dte_non_negative'),
        sa.CheckConstraint('paper_win_rate >= 0 AND paper_win_rate <= 100',
                          name='chk_paper_win_rate_range')
    )

    # Indexes for efficient querying
    op.create_index(
        'idx_ai_user_config_user_id',
        'ai_user_config',
        ['user_id'],
        unique=True
    )

    op.create_index(
        'idx_ai_user_config_enabled',
        'ai_user_config',
        ['ai_enabled']
    )


def downgrade() -> None:
    """Drop AI user configuration table."""

    # Drop indexes
    op.drop_index('idx_ai_user_config_enabled', table_name='ai_user_config')
    op.drop_index('idx_ai_user_config_user_id', table_name='ai_user_config')

    # Drop table
    op.drop_table('ai_user_config')
