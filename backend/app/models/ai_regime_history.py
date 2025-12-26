"""
AI Regime History Model

Tracks regime classification snapshots over time for drift detection.
Part of Priority 1.3: Regime Drift Detection.
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class AIRegimeHistory(Base):
    """
    Historical snapshots of market regime classifications.

    Used for:
    - Regime drift detection (frequent changes = drift)
    - Regime stability scoring
    - Regime prediction accuracy tracking
    - Monitoring alerts for regime changes
    """
    __tablename__ = "ai_regime_history"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Regime Classification
    underlying = Column(String(20), nullable=False, index=True)
    regime_type = Column(String(30), nullable=False, index=True)
    confidence = Column(Numeric(5, 2), nullable=False)  # 0-100

    # Technical Indicators Snapshot (JSONB for flexibility)
    indicators = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Technical indicators at classification time"
    )

    # Reasoning
    reasoning = Column(String(500), nullable=True, comment="Why this regime was selected")

    # Metadata
    classified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True
    )

    # Drift Metrics (computed fields)
    was_drift = Column(
        Numeric(3, 2),
        nullable=True,
        comment="Drift score at this point (0-1, computed post-facto)"
    )
    regime_changed = Column(
        String(1),
        nullable=True,
        comment="Y if regime changed from previous, N otherwise"
    )

    __table_args__ = (
        # Index for querying recent history by underlying
        Index(
            'idx_regime_history_underlying_time',
            'underlying',
            'classified_at',
            postgresql_using='btree'
        ),
        # Index for drift analysis queries
        Index(
            'idx_regime_history_drift_lookup',
            'underlying',
            'classified_at',
            'regime_type'
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AIRegimeHistory(id={self.id}, underlying={self.underlying}, "
            f"regime={self.regime_type}, confidence={self.confidence}, "
            f"at={self.classified_at})>"
        )


__all__ = ["AIRegimeHistory"]
