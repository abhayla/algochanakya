"""StrategyTemplate model for pre-defined options strategy templates."""

import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from app.database import Base


class StrategyTemplate(Base):
    """Pre-defined options strategy templates with educational content."""

    __tablename__ = "strategy_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Basic info
    name = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "iron_condor"
    display_name = Column(String(100), nullable=False)  # e.g., "Iron Condor"
    category = Column(String(50), nullable=False, index=True)  # bullish, bearish, neutral, volatile, income, advanced
    description = Column(Text, nullable=False)

    # Legs configuration (JSON array)
    # Format: [{"type": "CE/PE", "position": "BUY/SELL", "strike_offset": 0/100/-100, "expiry_offset": 0}]
    legs_config = Column(JSON, nullable=False)

    # Risk/reward characteristics
    max_profit = Column(String(100), nullable=False)  # "Limited", "Unlimited", or formula
    max_loss = Column(String(100), nullable=False)  # "Limited", "Unlimited", or formula
    breakeven = Column(String(200), nullable=True)  # Formula or description

    # Market conditions
    market_outlook = Column(String(50), nullable=False)  # bullish, bearish, neutral, volatile
    volatility_preference = Column(String(50), nullable=False)  # high_iv, low_iv, any
    ideal_iv_rank = Column(String(50), nullable=True)  # e.g., ">50%", "<30%"

    # Risk metrics
    risk_level = Column(String(20), nullable=False)  # low, medium, high
    capital_requirement = Column(String(20), nullable=False)  # low, medium, high
    margin_requirement = Column(String(50), nullable=True)  # Description

    # Greeks exposure
    theta_positive = Column(Boolean, default=False)  # Profits from time decay
    vega_positive = Column(Boolean, default=False)  # Profits from IV increase
    delta_neutral = Column(Boolean, default=False)  # Direction neutral
    gamma_risk = Column(String(20), nullable=True)  # low, medium, high

    # Probabilities
    win_probability = Column(String(50), nullable=True)  # e.g., "~68%", "High"
    profit_target = Column(String(100), nullable=True)  # e.g., "50% of max profit"

    # Educational content
    when_to_use = Column(Text, nullable=True)
    pros = Column(JSON, nullable=True)  # Array of strings
    cons = Column(JSON, nullable=True)  # Array of strings
    common_mistakes = Column(JSON, nullable=True)  # Array of strings
    exit_rules = Column(JSON, nullable=True)  # Array of strings
    adjustments = Column(JSON, nullable=True)  # Array of adjustment strategies

    # Example trade
    example_underlying = Column(String(20), default="NIFTY")
    example_spot = Column(Float, nullable=True)
    example_setup = Column(Text, nullable=True)

    # Metadata
    popularity_score = Column(Integer, default=0)  # For sorting by popularity
    difficulty_level = Column(String(20), default="intermediate")  # beginner, intermediate, advanced
    tags = Column(JSON, nullable=True)  # Array of tags for search

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<StrategyTemplate {self.name} ({self.category})>"
