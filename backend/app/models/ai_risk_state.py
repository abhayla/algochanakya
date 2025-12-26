"""
AI Risk State SQLAlchemy Model

Stores user-specific risk state for autonomous drawdown control.
Implements state machine: NORMAL -> DEGRADED -> PAUSED
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum
from sqlalchemy import (
    Column, BigInteger, String, Integer, Numeric,
    DateTime, ForeignKey, Text, CheckConstraint,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class RiskState(str, Enum):
    """Risk state types for autonomous drawdown control."""
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    PAUSED = "PAUSED"


class AIRiskState(Base):
    """
    User-specific risk state for autonomous drawdown control.

    Each user has exactly one risk state (enforced by unique constraint on user_id).
    State transitions:
    - NORMAL: All systems operational, normal trading
    - DEGRADED: Performance degrading, reduced position sizing and stricter thresholds
    - PAUSED: Performance severely degraded, all new deployments halted

    Auto-transition rules:
    - NORMAL -> DEGRADED: Sharpe < 0.5 over 20 trades OR Drawdown > 10%
    - DEGRADED -> PAUSED: Drawdown > 20% OR Sharpe < 0 over 20 trades
    - DEGRADED/PAUSED -> NORMAL: Manual recovery or performance improvement
    """
    __tablename__ = "ai_risk_state"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key to users (one-to-one relationship)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Current State
    state = Column(String(20), nullable=False, default='NORMAL')
    previous_state = Column(String(20), nullable=True)

    # Reason for state transition
    reason = Column(Text, nullable=True)

    # Performance Metrics at Transition
    sharpe_ratio = Column(Numeric(6, 3), nullable=True)  # -99.999 to 999.999
    current_drawdown = Column(Numeric(6, 2), nullable=True)  # 0 to 100.00 (percentage)
    consecutive_losses = Column(Integer, nullable=False, default=0)

    # Timestamps
    triggered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")

    # Table constraints
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_ai_risk_state_user_id'),
        CheckConstraint(
            "state IN ('NORMAL', 'DEGRADED', 'PAUSED')",
            name='chk_state_valid'
        ),
        CheckConstraint(
            'current_drawdown >= 0 AND current_drawdown <= 100',
            name='chk_drawdown_range'
        ),
        CheckConstraint(
            'consecutive_losses >= 0',
            name='chk_consecutive_losses_non_negative'
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AIRiskState(id={self.id}, user_id={self.user_id}, "
            f"state={self.state}, sharpe={self.sharpe_ratio}, dd={self.current_drawdown}%)>"
        )


__all__ = ["AIRiskState", "RiskState"]
