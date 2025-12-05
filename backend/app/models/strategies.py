"""Strategy and StrategyLeg models for options strategy builder."""

import uuid
from sqlalchemy import Column, String, Integer, DateTime, Date, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Strategy(Base):
    """Strategy model for storing user's options strategies."""

    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=True)
    underlying = Column(String(20), nullable=False)  # NIFTY, BANKNIFTY, FINNIFTY
    share_code = Column(String(20), unique=True, nullable=True, index=True)
    status = Column(String(20), default="open", nullable=False)  # open, closed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    legs = relationship("StrategyLeg", back_populates="strategy", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<Strategy {self.id} name={self.name} underlying={self.underlying}>"


class StrategyLeg(Base):
    """StrategyLeg model for individual legs of an options strategy."""

    __tablename__ = "strategy_legs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    expiry_date = Column(Date, nullable=False)
    contract_type = Column(String(10), nullable=False)  # CE, PE, FUT, EQ
    transaction_type = Column(String(10), nullable=False)  # BUY, SELL
    strike_price = Column(DECIMAL(10, 2), nullable=True)
    lots = Column(Integer, default=1, nullable=False)
    strategy_type = Column(String(50), nullable=True)  # Naked Put, Iron Condor, etc.
    entry_price = Column(DECIMAL(10, 2), nullable=True)
    exit_price = Column(DECIMAL(10, 2), nullable=True)
    instrument_token = Column(Integer, nullable=True)
    order_id = Column(String(50), nullable=True)  # Kite order ID if executed
    position_status = Column(String(20), default="pending", nullable=False)  # pending, executed, closed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    strategy = relationship("Strategy", back_populates="legs")

    def __repr__(self):
        return f"<StrategyLeg {self.id} {self.contract_type} {self.strike_price} {self.transaction_type}>"
