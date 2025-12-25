"""AI Week 5: ML Model Registry

Revision ID: 013_ai_week5
Revises: 012_ai_week4
Create Date: 2025-12-25 18:30:00

Creates ai_model_registry table for tracking ML model versions, metrics, and deployment status.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013_ai_week5'
down_revision = '012_ai_week4'
branch_labels = None
depends_on = None


def upgrade():
    # Create ai_model_registry table
    op.create_table(
        'ai_model_registry',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('model_type', sa.String(length=20), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('accuracy', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('precision', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('recall', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('f1_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('roc_auc', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trained_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_ai_model_registry'),
        sa.UniqueConstraint('version', name='uq_ai_model_registry_version'),
        sa.CheckConstraint('accuracy >= 0 AND accuracy <= 1', name='chk_accuracy_range'),
        sa.CheckConstraint('precision >= 0 AND precision <= 1', name='chk_precision_range'),
        sa.CheckConstraint('recall >= 0 AND recall <= 1', name='chk_recall_range'),
        sa.CheckConstraint('f1_score >= 0 AND f1_score <= 1', name='chk_f1_score_range'),
        sa.CheckConstraint('roc_auc >= 0 AND roc_auc <= 1', name='chk_roc_auc_range'),
    )

    # Create index on is_active for fast active model lookup
    op.create_index(
        'ix_ai_model_registry_is_active',
        'ai_model_registry',
        ['is_active']
    )

    print("[OK] Created ai_model_registry table")


def downgrade():
    op.drop_index('ix_ai_model_registry_is_active', table_name='ai_model_registry')
    op.drop_table('ai_model_registry')

    print("[OK] Dropped ai_model_registry table")
