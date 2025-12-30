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
    UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

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

    # Stress Greeks Limits (Priority 1.1)
    max_stress_risk_score = Column(Numeric(5, 2), nullable=False, default=Decimal('75.00'))  # 0-100
    max_portfolio_delta = Column(Numeric(6, 3), nullable=False, default=Decimal('1.000'))   # Absolute delta
    max_portfolio_gamma = Column(Numeric(8, 5), nullable=False, default=Decimal('0.05000'))  # Absolute gamma

    # Drawdown-Aware Position Sizing (Priority 1.2)
    enable_drawdown_sizing = Column(Boolean, nullable=False, default=False)
    drawdown_thresholds = Column(
        JSONB,
        nullable=False,
        default=[
            {"level": "NORMAL", "min_dd": 0.0, "max_dd": 5.0, "multiplier": 1.0},
            {"level": "CAUTION", "min_dd": 5.0, "max_dd": 10.0, "multiplier": 0.8},
            {"level": "WARNING", "min_dd": 10.0, "max_dd": 15.0, "multiplier": 0.6},
            {"level": "CRITICAL", "min_dd": 15.0, "max_dd": 20.0, "multiplier": 0.4},
            {"level": "SEVERE", "min_dd": 20.0, "max_dd": 100.0, "multiplier": 0.2}
        ]
    )
    enable_volatility_sizing = Column(Boolean, nullable=False, default=False)
    volatility_lookback_days = Column(Integer, nullable=False, default=30)
    volatility_thresholds = Column(
        JSONB,
        nullable=False,
        default=[
            {"level": "LOW", "max_volatility": 5000.0, "multiplier": 1.0},
            {"level": "MEDIUM", "max_volatility": 10000.0, "multiplier": 0.8},
            {"level": "HIGH", "max_volatility": 999999.0, "multiplier": 0.6}
        ]
    )
    max_drawdown_to_trade = Column(Numeric(5, 2), nullable=False, default=Decimal('25.00'))  # % - pause above this
    high_water_mark = Column(Numeric(14, 2), nullable=True)  # Peak portfolio value
    current_drawdown_pct = Column(Numeric(5, 2), nullable=False, default=Decimal('0.00'))  # Current drawdown %

    # Regime Drift Detection (Priority 1.3)
    enable_drift_detection = Column(Boolean, nullable=False, default=True)
    drift_lookback_periods = Column(Integer, nullable=False, default=20)  # Number of periods to analyze
    drift_threshold = Column(Numeric(5, 2), nullable=False, default=Decimal('30.00'))  # % - drift alert threshold
    drift_confidence_penalty = Column(Numeric(5, 2), nullable=False, default=Decimal('10.00'))  # % - reduce confidence
    min_regime_stability_score = Column(Numeric(5, 2), nullable=False, default=Decimal('40.00'))  # 0-100
    current_regime_stability = Column(Numeric(5, 2), nullable=False, default=Decimal('100.00'))  # 0-100
    last_drift_check_at = Column(DateTime(timezone=True), nullable=True)

    # Global → Personalized ML Blending (Priority 2.1)
    enable_ml_blending = Column(Boolean, nullable=False, default=True)
    blending_alpha_start = Column(Numeric(3, 2), nullable=False, default=Decimal('1.00'))  # Initial global weight (1.0 = 100% global)
    blending_alpha_min = Column(Numeric(3, 2), nullable=False, default=Decimal('0.20'))  # Minimum global weight (0.2 = 20% global, 80% user)
    blending_trades_threshold = Column(Integer, nullable=False, default=100)  # Trades needed for full personalization
    total_trades_completed = Column(Integer, nullable=False, default=0)  # Track user's total completed trades

    # Retraining Frequency Optimization (Priority 2.3)
    retraining_cadence = Column(String(20), nullable=False, default='weekly')  # daily, weekly, volume_based
    retraining_volume_threshold = Column(Integer, nullable=False, default=25)  # Trades before retrain (volume_based mode)
    high_volume_trades_per_week = Column(Integer, nullable=False, default=50)  # Threshold to switch weekly→daily
    last_user_model_retrain_at = Column(DateTime(timezone=True), nullable=True)  # Last user model retrain timestamp
    min_model_stability_threshold = Column(Numeric(5, 2), nullable=False, default=Decimal('5.00'))  # Max allowed degradation % (0-100)
    enable_confidence_weighting = Column(Boolean, nullable=False, default=True)  # Weight training samples by quality scores
    trades_since_last_retrain = Column(Integer, nullable=False, default=0)  # Counter for volume-based retraining

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
        CheckConstraint(
            'max_stress_risk_score >= 0 AND max_stress_risk_score <= 100',
            name='chk_max_stress_risk_score_range'
        ),
        CheckConstraint('max_portfolio_delta > 0', name='chk_max_portfolio_delta_positive'),
        CheckConstraint('max_portfolio_gamma > 0', name='chk_max_portfolio_gamma_positive'),
        CheckConstraint(
            'max_drawdown_to_trade >= 0 AND max_drawdown_to_trade <= 100',
            name='chk_max_drawdown_to_trade_range'
        ),
        CheckConstraint(
            'current_drawdown_pct >= 0 AND current_drawdown_pct <= 100',
            name='chk_current_drawdown_pct_range'
        ),
        CheckConstraint('volatility_lookback_days > 0', name='chk_volatility_lookback_days_positive'),
        CheckConstraint('drift_lookback_periods > 0', name='chk_drift_lookback_periods_positive'),
        CheckConstraint('retraining_volume_threshold > 0', name='chk_retraining_volume_threshold_positive'),
        CheckConstraint('high_volume_trades_per_week > 0', name='chk_high_volume_trades_per_week_positive'),
        CheckConstraint(
            'min_model_stability_threshold >= 0 AND min_model_stability_threshold <= 100',
            name='chk_min_model_stability_threshold_range'
        ),
        CheckConstraint('trades_since_last_retrain >= 0', name='chk_trades_since_last_retrain_non_negative'),
        CheckConstraint(
            'drift_threshold >= 0 AND drift_threshold <= 100',
            name='chk_drift_threshold_range'
        ),
        CheckConstraint(
            'drift_confidence_penalty >= 0 AND drift_confidence_penalty <= 100',
            name='chk_drift_confidence_penalty_range'
        ),
        CheckConstraint(
            'min_regime_stability_score >= 0 AND min_regime_stability_score <= 100',
            name='chk_min_regime_stability_score_range'
        ),
        CheckConstraint(
            'current_regime_stability >= 0 AND current_regime_stability <= 100',
            name='chk_current_regime_stability_range'
        ),
        CheckConstraint(
            'blending_alpha_start >= 0 AND blending_alpha_start <= 1',
            name='chk_blending_alpha_start_range'
        ),
        CheckConstraint(
            'blending_alpha_min >= 0 AND blending_alpha_min <= 1',
            name='chk_blending_alpha_min_range'
        ),
        CheckConstraint('blending_trades_threshold > 0', name='chk_blending_trades_threshold_positive'),
        CheckConstraint('total_trades_completed >= 0', name='chk_total_trades_completed_non_negative'),
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
    Supports both global (trained on all users) and user-specific models.
    """
    __tablename__ = "ai_model_registry"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Model Identification
    version = Column(String(50), nullable=False)
    model_type = Column(String(20), nullable=False)  # xgboost, lightgbm
    scope = Column(String(10), nullable=False, default='user')  # 'global' or 'user'
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True  # NULL for global models, set for user-specific models
    )
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

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    # Table constraints
    __table_args__ = (
        # Partial unique index for global models (version must be unique among global models)
        Index('idx_ai_model_registry_global_version', 'version',
              unique=True,
              postgresql_where=text("scope = 'global'")),
        # Partial unique index for user models (version must be unique per user)
        Index('idx_ai_model_registry_user_version', 'version', 'user_id',
              unique=True,
              postgresql_where=text("user_id IS NOT NULL")),
        CheckConstraint('accuracy >= 0 AND accuracy <= 1', name='chk_accuracy_range'),
        CheckConstraint('precision >= 0 AND precision <= 1', name='chk_precision_range'),
        CheckConstraint('recall >= 0 AND recall <= 1', name='chk_recall_range'),
        CheckConstraint('f1_score >= 0 AND f1_score <= 1', name='chk_f1_score_range'),
        CheckConstraint('roc_auc >= 0 AND roc_auc <= 1', name='chk_roc_auc_range'),
        CheckConstraint("scope IN ('global', 'user')", name='chk_scope_valid'),
        CheckConstraint(
            "(scope = 'global' AND user_id IS NULL) OR (scope = 'user' AND user_id IS NOT NULL)",
            name='chk_scope_user_id_consistency'
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AIModelRegistry(id={self.id}, version={self.version}, "
            f"scope={self.scope}, user_id={self.user_id}, "
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

    # Regime-Conditioned Metrics (Priority 2.2)
    # Stores per-regime breakdown: {regime_type: {trades, win_rate, avg_score, ...}}
    regime_breakdown = Column(JSONB, nullable=False, default=dict)

    # Dominant regime during report period
    dominant_regime = Column(String(30), nullable=True)
    dominant_regime_pct = Column(Numeric(5, 2), nullable=True)  # % of trades in dominant regime

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


class AIPaperTrade(Base):
    """
    Paper trading records for AI Autopilot testing and graduation.

    Tracks simulated trades placed by the AI system before graduating to live trading.
    Stores entry/exit details, strategy configuration, and P&L calculations.
    """
    __tablename__ = "ai_paper_trades"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=text('gen_random_uuid()'))

    # Foreign Key to users
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Strategy Information
    strategy_name = Column(String(100), nullable=False)
    underlying = Column(String(20), nullable=False)  # NIFTY, BANKNIFTY, FINNIFTY

    # Entry Details
    entry_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    entry_regime = Column(String(30), nullable=False)  # Market regime at entry
    entry_confidence = Column(Numeric(5, 2), nullable=False)  # AI confidence score 0-100
    sizing_mode = Column(String(20), nullable=False)  # fixed, tiered, kelly
    lots = Column(Integer, nullable=False)

    # Strategy Legs (JSONB array)
    # Each leg: {strike: int, option_type: 'CE'|'PE', transaction_type: 'BUY'|'SELL',
    #            entry_premium: float, exit_premium: float|null, qty: int}
    legs = Column(JSONB, nullable=False)

    # Exit Details
    exit_time = Column(DateTime(timezone=True), nullable=True)
    exit_reason = Column(String(50), nullable=True)  # manual, target, stoploss, expiry, ai_decision

    # P&L Tracking
    entry_total_premium = Column(Numeric(12, 2), nullable=False)  # Total premium received/paid at entry
    exit_total_premium = Column(Numeric(12, 2), nullable=True)  # Total premium at exit
    realized_pnl = Column(Numeric(12, 2), nullable=True)  # Final P&L after exit

    # Status
    status = Column(String(20), nullable=False, default='open')  # open, closed

    # Metadata
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
    user = relationship("User")

    # Table constraints
    __table_args__ = (
        CheckConstraint('lots > 0', name='chk_ai_paper_trades_lots_positive'),
        CheckConstraint(
            'entry_confidence >= 0 AND entry_confidence <= 100',
            name='chk_ai_paper_trades_confidence_range'
        ),
        CheckConstraint(
            "status IN ('open', 'closed')",
            name='chk_ai_paper_trades_status_valid'
        ),
        CheckConstraint(
            "sizing_mode IN ('fixed', 'tiered', 'kelly')",
            name='chk_ai_paper_trades_sizing_mode_valid'
        ),
        Index('idx_ai_paper_trades_user_id', 'user_id'),
        Index('idx_ai_paper_trades_status', 'status'),
        Index('idx_ai_paper_trades_entry_time', 'entry_time'),
    )

    def __repr__(self) -> str:
        return (
            f"<AIPaperTrade(id={self.id}, user_id={self.user_id}, "
            f"strategy={self.strategy_name}, status={self.status}, "
            f"pnl={self.realized_pnl})>"
        )
