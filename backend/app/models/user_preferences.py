"""
User Preferences SQLAlchemy Model

Stores user-specific preferences and settings for the application.
"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class MarketDataSource:
    """Valid market data source values."""
    SMARTAPI = "smartapi"
    KITE = "kite"

    VALID_SOURCES = [SMARTAPI, KITE]


class UserPreferences(Base):
    """User preferences and settings"""
    __tablename__ = "user_preferences"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # P/L Grid Settings
    pnl_grid_interval = Column(Integer, nullable=False, default=100)

    # Market Data Settings
    market_data_source = Column(
        String(20),
        nullable=False,
        default=MarketDataSource.SMARTAPI,
        server_default=MarketDataSource.SMARTAPI
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="user_preferences")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'pnl_grid_interval IN (50, 100)',
            name='check_pnl_grid_interval'
        ),
        CheckConstraint(
            "market_data_source IN ('smartapi', 'kite')",
            name='check_market_data_source'
        ),
    )
