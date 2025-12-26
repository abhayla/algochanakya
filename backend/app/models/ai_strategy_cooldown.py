"""
AI Strategy Cooldown SQLAlchemy Model

Stores strategy-regime failure registry for preventing repeated losses.
Implements cooldown periods based on failure count and recency.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column, BigInteger, String, Integer, Numeric,
    DateTime, ForeignKey, Text, CheckConstraint,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AIStrategyCooldown(Base):
    """
    Strategy-Regime failure registry for cooldown management.

    Tracks failures of specific strategies in specific market regimes.
    Implements progressive cooldown periods:
    - 1 failure: 1 day cooldown
    - 2 failures in 7 days: 3 day cooldown
    - 3+ failures in 14 days: 7 day cooldown + alert

    Each user has one record per (strategy, regime) combination.
    """
    __tablename__ = "ai_strategy_cooldown"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key to users
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Strategy and Regime Identification
    strategy_name = Column(String(50), nullable=False)  # e.g., "iron_condor"
    regime_type = Column(String(30), nullable=False)    # e.g., "VOLATILE"

    # Failure Tracking
    failure_count = Column(Integer, nullable=False, default=1)
    total_loss = Column(Numeric(14, 2), nullable=False, default=Decimal('0'))  # Cumulative loss

    # Cooldown Management
    last_failure_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    cooldown_until = Column(DateTime(timezone=True), nullable=True)

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
        UniqueConstraint(
            'user_id', 'strategy_name', 'regime_type',
            name='uq_ai_strategy_cooldown_user_strategy_regime'
        ),
        CheckConstraint('failure_count > 0', name='chk_failure_count_positive'),
        CheckConstraint('total_loss >= 0', name='chk_total_loss_non_negative'),
    )

    def __repr__(self) -> str:
        return (
            f"<AIStrategyCooldown(id={self.id}, user_id={self.user_id}, "
            f"strategy={self.strategy_name}, regime={self.regime_type}, "
            f"failures={self.failure_count}, cooldown_until={self.cooldown_until})>"
        )


__all__ = ["AIStrategyCooldown"]
