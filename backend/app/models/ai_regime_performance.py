"""
AI Regime Performance Model

Stores regime-specific performance metrics for context-aware decision quality scoring.
Priority 2.2: Regime-Conditioned Decision Quality
"""

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Column, BigInteger, String, Integer, Numeric,
    Date, DateTime, ForeignKey, CheckConstraint,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AIRegimePerformance(Base):
    """
    Tracks performance metrics broken down by market regime.

    Enables regime-conditioned decision quality scoring by storing
    historical performance per regime type. Used to normalize scores
    and identify regime-relative strengths/weaknesses.
    """
    __tablename__ = "ai_regime_performance"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key to users
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Time period
    report_date = Column(Date, nullable=False, index=True)

    # Regime Type (TRENDING_BULLISH, TRENDING_BEARISH, RANGEBOUND, VOLATILE, PRE_EVENT, EVENT_DAY)
    regime_type = Column(String(30), nullable=False, index=True)

    # Trade Statistics for this regime
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    losing_trades = Column(Integer, nullable=False, default=0)
    win_rate = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))  # 0-100

    # P&L Statistics for this regime
    total_pnl = Column(Numeric(14, 2), nullable=False, default=Decimal('0'))
    avg_pnl_per_trade = Column(Numeric(14, 2), nullable=False, default=Decimal('0'))
    max_win = Column(Numeric(14, 2), nullable=True)
    max_loss = Column(Numeric(14, 2), nullable=True)

    # Decision Quality Scores (0-100) for this regime
    avg_overall_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    avg_pnl_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    avg_risk_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    avg_entry_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    avg_adjustment_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    avg_exit_score = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))

    # Regime-Normalized Scores (0-100)
    # These are calculated relative to user's historical performance in this regime
    normalized_overall_score = Column(Numeric(5, 2), nullable=True)
    normalized_pnl_score = Column(Numeric(5, 2), nullable=True)
    normalized_risk_score = Column(Numeric(5, 2), nullable=True)

    # Time in regime (total minutes spent in this regime during report period)
    total_minutes_in_regime = Column(Integer, nullable=False, default=0)

    # Regime prevalence (percentage of trading day spent in this regime)
    regime_prevalence_pct = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))  # 0-100

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
    user = relationship("User")

    # Table constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'report_date', 'regime_type',
                        name='uq_ai_regime_performance_user_date_regime'),
        CheckConstraint('total_trades >= 0', name='chk_regime_perf_total_trades_non_negative'),
        CheckConstraint('winning_trades >= 0', name='chk_regime_perf_winning_trades_non_negative'),
        CheckConstraint('losing_trades >= 0', name='chk_regime_perf_losing_trades_non_negative'),
        CheckConstraint('win_rate >= 0 AND win_rate <= 100', name='chk_regime_perf_win_rate_range'),
        CheckConstraint('avg_overall_score >= 0 AND avg_overall_score <= 100',
                       name='chk_regime_perf_avg_overall_score_range'),
        CheckConstraint('avg_pnl_score >= 0 AND avg_pnl_score <= 100',
                       name='chk_regime_perf_avg_pnl_score_range'),
        CheckConstraint('avg_risk_score >= 0 AND avg_risk_score <= 100',
                       name='chk_regime_perf_avg_risk_score_range'),
        CheckConstraint('avg_entry_score >= 0 AND avg_entry_score <= 100',
                       name='chk_regime_perf_avg_entry_score_range'),
        CheckConstraint('avg_adjustment_score >= 0 AND avg_adjustment_score <= 100',
                       name='chk_regime_perf_avg_adjustment_score_range'),
        CheckConstraint('avg_exit_score >= 0 AND avg_exit_score <= 100',
                       name='chk_regime_perf_avg_exit_score_range'),
        CheckConstraint('total_minutes_in_regime >= 0',
                       name='chk_regime_perf_total_minutes_non_negative'),
        CheckConstraint('regime_prevalence_pct >= 0 AND regime_prevalence_pct <= 100',
                       name='chk_regime_perf_prevalence_range'),
    )

    def __repr__(self) -> str:
        return (
            f"<AIRegimePerformance(id={self.id}, user_id={self.user_id}, "
            f"date={self.report_date}, regime={self.regime_type}, "
            f"trades={self.total_trades}, win_rate={self.win_rate})>"
        )


__all__ = ["AIRegimePerformance"]
