"""AI Week 7: Learning Reports

Revision ID: 014_ai_week7
Revises: 013_ai_week5
Create Date: 2025-12-25 19:45:00

Creates ai_learning_reports table for daily self-learning pipeline results.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014_ai_week7'
down_revision = '013_ai_week5'
branch_labels = None
depends_on = None


def upgrade():
    # Create ai_learning_reports table
    op.create_table(
        'ai_learning_reports',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),

        # Trade Statistics
        sa.Column('total_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('winning_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('losing_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('win_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),

        # P&L Statistics
        sa.Column('total_pnl', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'),
        sa.Column('avg_pnl_per_trade', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'),
        sa.Column('max_win', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('max_loss', sa.Numeric(precision=14, scale=2), nullable=True),

        # Decision Quality Scores (0-100)
        sa.Column('avg_overall_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('avg_pnl_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('avg_risk_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('avg_entry_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('avg_adjustment_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('avg_exit_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),

        # Model Training
        sa.Column('model_retrained', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('new_model_version', sa.String(length=50), nullable=True),
        sa.Column('model_accuracy', sa.Numeric(precision=5, scale=4), nullable=True),

        # Insights (JSONB array of strings)
        sa.Column('insights', postgresql.JSONB(), nullable=False, server_default='[]'),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id', name='pk_ai_learning_reports'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_ai_learning_reports_user_id'),
        sa.UniqueConstraint('user_id', 'report_date', name='uq_ai_learning_reports_user_date'),
        sa.CheckConstraint('total_trades >= 0', name='chk_total_trades_non_negative'),
        sa.CheckConstraint('winning_trades >= 0', name='chk_winning_trades_non_negative'),
        sa.CheckConstraint('losing_trades >= 0', name='chk_losing_trades_non_negative'),
        sa.CheckConstraint('win_rate >= 0 AND win_rate <= 100', name='chk_win_rate_range'),
        sa.CheckConstraint('avg_overall_score >= 0 AND avg_overall_score <= 100', name='chk_avg_overall_score_range'),
        sa.CheckConstraint('avg_pnl_score >= 0 AND avg_pnl_score <= 100', name='chk_avg_pnl_score_range'),
        sa.CheckConstraint('avg_risk_score >= 0 AND avg_risk_score <= 100', name='chk_avg_risk_score_range'),
        sa.CheckConstraint('avg_entry_score >= 0 AND avg_entry_score <= 100', name='chk_avg_entry_score_range'),
        sa.CheckConstraint('avg_adjustment_score >= 0 AND avg_adjustment_score <= 100', name='chk_avg_adjustment_score_range'),
        sa.CheckConstraint('avg_exit_score >= 0 AND avg_exit_score <= 100', name='chk_avg_exit_score_range'),
        sa.CheckConstraint('model_accuracy >= 0 AND model_accuracy <= 1', name='chk_model_accuracy_range'),
    )

    # Create indexes for common queries
    op.create_index(
        'ix_ai_learning_reports_user_id',
        'ai_learning_reports',
        ['user_id']
    )

    op.create_index(
        'ix_ai_learning_reports_report_date',
        'ai_learning_reports',
        ['report_date']
    )

    op.create_index(
        'ix_ai_learning_reports_user_id_report_date',
        'ai_learning_reports',
        ['user_id', 'report_date']
    )

    print("[OK] Created ai_learning_reports table")


def downgrade():
    op.drop_index('ix_ai_learning_reports_user_id_report_date', table_name='ai_learning_reports')
    op.drop_index('ix_ai_learning_reports_report_date', table_name='ai_learning_reports')
    op.drop_index('ix_ai_learning_reports_user_id', table_name='ai_learning_reports')
    op.drop_table('ai_learning_reports')

    print("[OK] Dropped ai_learning_reports table")
