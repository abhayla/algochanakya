"""
AI User Configuration SQLAlchemy Model

Stores user-specific configuration for autonomous AI trading including
autonomy settings, deployment schedule, position sizing, and limits.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column, BigInteger, String, Integer, Boolean, Numeric,
    Date, DateTime, ForeignKey, Text, CheckConstraint,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AIUserConfig(Base):
    """
    User-specific configuration for AI autonomous trading.

    Each user has exactly one configuration (enforced by unique constraint on user_id).
    Default values are provided for all settings to enable quick onboarding.
    """
    __tablename__ = "ai_user_config"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key to users (one-to-one relationship)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Autonomy Settings
    ai_enabled = Column(Boolean, nullable=False, default=False)
    autonomy_mode = Column(String(20), nullable=False, default='paper')  # paper, live

    # Auto-Deployment Settings
    auto_deploy_enabled = Column(Boolean, nullable=False, default=False)
    deploy_time = Column(String(5), nullable=True, default='09:20')  # HH:MM format
    deploy_days = Column(
        ARRAY(String),
        nullable=False,
        default=['MON', 'TUE', 'WED', 'THU', 'FRI']
    )
    skip_event_days = Column(Boolean, nullable=False, default=True)
    skip_weekly_expiry = Column(Boolean, nullable=False, default=False)

    # Strategy Universe (JSONB array of template IDs)
    allowed_strategies = Column(JSONB, nullable=False, default=list)

    # Position Sizing
    sizing_mode = Column(String(20), nullable=False, default='tiered')  # fixed, tiered, kelly
    base_lots = Column(Integer, nullable=False, default=1)
    confidence_tiers = Column(
        JSONB,
        nullable=False,
        default=[
            {"name": "SKIP", "min": 0, "max": 60, "multiplier": 0},
            {"name": "LOW", "min": 60, "max": 75, "multiplier": 1.0},
            {"name": "MEDIUM", "min": 75, "max": 85, "multiplier": 1.5},
            {"name": "HIGH", "min": 85, "max": 100, "multiplier": 2.0}
        ]
    )

    # AI-Specific Limits
    max_lots_per_strategy = Column(Integer, nullable=False, default=2)
    max_lots_per_day = Column(Integer, nullable=False, default=6)
    max_strategies_per_day = Column(Integer, nullable=False, default=5)
    min_confidence_to_trade = Column(Numeric(5, 2), nullable=False, default=Decimal('60.00'))
    max_vix_to_trade = Column(Numeric(5, 2), nullable=False, default=Decimal('25.00'))
    min_dte_to_enter = Column(Integer, nullable=False, default=2)
    weekly_loss_limit = Column(Numeric(12, 2), nullable=False, default=Decimal('50000.00'))

    # Preferred Underlyings
    preferred_underlyings = Column(
        ARRAY(String(20)),
        nullable=False,
        default=['NIFTY', 'BANKNIFTY']
    )

    # Paper Trading Graduation
    paper_start_date = Column(Date, nullable=True)
    paper_trades_completed = Column(Integer, nullable=False, default=0)
    paper_win_rate = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    paper_total_pnl = Column(Numeric(14, 2), nullable=False, default=Decimal('0'))
    paper_graduation_approved = Column(Boolean, nullable=False, default=False)

    # Claude API
    claude_api_key_encrypted = Column(Text, nullable=True)
    enable_ai_explanations = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="ai_config")

    # Table constraints
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_ai_user_config_user_id'),
        CheckConstraint(
            'min_confidence_to_trade >= 0 AND min_confidence_to_trade <= 100',
            name='chk_min_confidence_range'
        ),
        CheckConstraint('max_vix_to_trade > 0', name='chk_max_vix_positive'),
        CheckConstraint('base_lots > 0', name='chk_base_lots_positive'),
        CheckConstraint('max_lots_per_strategy > 0', name='chk_max_lots_per_strategy_positive'),
        CheckConstraint('max_lots_per_day > 0', name='chk_max_lots_per_day_positive'),
        CheckConstraint('max_strategies_per_day > 0', name='chk_max_strategies_per_day_positive'),
        CheckConstraint('min_dte_to_enter >= 0', name='chk_min_dte_non_negative'),
        CheckConstraint(
            'paper_win_rate >= 0 AND paper_win_rate <= 100',
            name='chk_paper_win_rate_range'
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AIUserConfig(id={self.id}, user_id={self.user_id}, "
            f"ai_enabled={self.ai_enabled}, autonomy_mode={self.autonomy_mode})>"
        )


class AIModelRegistry(Base):
    """
    ML Model Registry for tracking model versions, metrics, and deployment status.

    Stores metadata for trained ML models used in strategy scoring.
    """
    __tablename__ = "ai_model_registry"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Model Identification
    version = Column(String(50), nullable=False, unique=True)
    model_type = Column(String(20), nullable=False)  # xgboost, lightgbm
    file_path = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Evaluation Metrics
    accuracy = Column(Numeric(5, 4), nullable=True)  # 0.0000 to 1.0000
    precision = Column(Numeric(5, 4), nullable=True)
    recall = Column(Numeric(5, 4), nullable=True)
    f1_score = Column(Numeric(5, 4), nullable=True)
    roc_auc = Column(Numeric(5, 4), nullable=True)

    # Deployment Status
    is_active = Column(Boolean, nullable=False, default=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    trained_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Table constraints
    __table_args__ = (
        UniqueConstraint('version', name='uq_ai_model_registry_version'),
        CheckConstraint('accuracy >= 0 AND accuracy <= 1', name='chk_accuracy_range'),
        CheckConstraint('precision >= 0 AND precision <= 1', name='chk_precision_range'),
        CheckConstraint('recall >= 0 AND recall <= 1', name='chk_recall_range'),
        CheckConstraint('f1_score >= 0 AND f1_score <= 1', name='chk_f1_score_range'),
        CheckConstraint('roc_auc >= 0 AND roc_auc <= 1', name='chk_roc_auc_range'),
    )

    def __repr__(self) -> str:
        return (
            f"<AIModelRegistry(id={self.id}, version={self.version}, "
            f"model_type={self.model_type}, is_active={self.is_active})>"
        )


class AILearningReport(Base):
    """
    Daily self-learning pipeline results and model training reports.

    Tracks decision quality, model performance, and insights from autonomous trading.
    """
    __tablename__ = "ai_learning_reports"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key to users
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    report_date = Column(Date, nullable=False)

    # Trade Statistics
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    losing_trades = Column(Integer, nullable=False, default=0)
    win_rate = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))

    # P&L Statistics
    total_pnl = Column(Numeric(14, 2), nullable=False, default=Decimal('0'))
    avg_pnl_per_trade = Column(Numeric(14, 2), nullable=False, default=Decimal('0'))
    max_win = Column(Numeric(14, 2), nullable=True)
    max_loss = Column(Numeric(14, 2), nullable=True)

    # Decision Quality Scores (0-100)
    avg_overall_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    avg_pnl_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    avg_risk_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    avg_entry_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    avg_adjustment_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    avg_exit_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))

    # Model Training
    model_retrained = Column(Boolean, nullable=False, default=False)
    new_model_version = Column(String(50), nullable=True)
    model_accuracy = Column(Numeric(5, 4), nullable=True)

    # Insights (JSONB array of strings)
    insights = Column(JSONB, nullable=False, default=list)

    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    user = relationship("User")

    # Table constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'report_date', name='uq_ai_learning_reports_user_date'),
        CheckConstraint('total_trades >= 0', name='chk_total_trades_non_negative'),
        CheckConstraint('winning_trades >= 0', name='chk_winning_trades_non_negative'),
        CheckConstraint('losing_trades >= 0', name='chk_losing_trades_non_negative'),
        CheckConstraint('win_rate >= 0 AND win_rate <= 100', name='chk_win_rate_range'),
        CheckConstraint('avg_overall_score >= 0 AND avg_overall_score <= 100', name='chk_avg_overall_score_range'),
        CheckConstraint('avg_pnl_score >= 0 AND avg_pnl_score <= 100', name='chk_avg_pnl_score_range'),
        CheckConstraint('avg_risk_score >= 0 AND avg_risk_score <= 100', name='chk_avg_risk_score_range'),
        CheckConstraint('avg_entry_score >= 0 AND avg_entry_score <= 100', name='chk_avg_entry_score_range'),
        CheckConstraint('avg_adjustment_score >= 0 AND avg_adjustment_score <= 100', name='chk_avg_adjustment_score_range'),
        CheckConstraint('avg_exit_score >= 0 AND avg_exit_score <= 100', name='chk_avg_exit_score_range'),
        CheckConstraint('model_accuracy >= 0 AND model_accuracy <= 1', name='chk_model_accuracy_range'),
    )

    def __repr__(self) -> str:
        return (
            f"<AILearningReport(id={self.id}, user_id={self.user_id}, "
            f"report_date={self.report_date}, total_trades={self.total_trades})>"
        )
