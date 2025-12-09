"""
AutoPilot SQLAlchemy Models

Reference: docs/autopilot/database-schema.md
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column, BigInteger, String, Integer, Boolean, Numeric,
    Date, DateTime, ForeignKey, Text, CheckConstraint,
    UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


# Enums
class StrategyStatus(str, enum.Enum):
    DRAFT = "draft"
    WAITING = "waiting"
    ACTIVE = "active"
    PENDING = "pending"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    EXPIRED = "expired"


class Underlying(str, enum.Enum):
    NIFTY = "NIFTY"
    BANKNIFTY = "BANKNIFTY"
    FINNIFTY = "FINNIFTY"
    SENSEX = "SENSEX"


class PositionType(str, enum.Enum):
    INTRADAY = "intraday"
    POSITIONAL = "positional"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PLACED = "placed"
    OPEN = "open"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ERROR = "error"


class OrderPurpose(str, enum.Enum):
    ENTRY = "entry"
    ADJUSTMENT = "adjustment"
    HEDGE = "hedge"
    EXIT = "exit"
    ROLL_CLOSE = "roll_close"
    ROLL_OPEN = "roll_open"
    KILL_SWITCH = "kill_switch"


class LogSeverity(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Models
class AutoPilotUserSettings(Base):
    __tablename__ = "autopilot_user_settings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Risk Limits
    daily_loss_limit = Column(Numeric(12, 2), nullable=False, default=20000.00)
    per_strategy_loss_limit = Column(Numeric(12, 2), nullable=False, default=10000.00)
    max_capital_deployed = Column(Numeric(14, 2), nullable=False, default=500000.00)
    max_active_strategies = Column(Integer, nullable=False, default=3)

    # Time Restrictions
    no_trade_first_minutes = Column(Integer, nullable=False, default=5)
    no_trade_last_minutes = Column(Integer, nullable=False, default=5)

    # Cooldown
    cooldown_after_loss = Column(Boolean, nullable=False, default=False)
    cooldown_minutes = Column(Integer, nullable=False, default=30)
    cooldown_threshold = Column(Numeric(12, 2), nullable=False, default=5000.00)

    # JSONB Settings
    default_order_settings = Column(JSONB, nullable=False, default=dict)
    notification_prefs = Column(JSONB, nullable=False, default=dict)
    failure_handling = Column(JSONB, nullable=False, default=dict)

    # Feature Flags
    paper_trading_mode = Column(Boolean, nullable=False, default=False)
    show_advanced_features = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="autopilot_settings")


class AutoPilotStrategy(Base):
    __tablename__ = "autopilot_strategies"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Basic Info
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="draft")

    # Instrument Configuration
    underlying = Column(String(20), nullable=False)
    expiry_type = Column(String(20), nullable=False, default="current_week")
    expiry_date = Column(Date, nullable=True)
    lots = Column(Integer, nullable=False, default=1)
    position_type = Column(String(20), nullable=False, default="intraday")

    # JSONB Configurations
    legs_config = Column(JSONB, nullable=False, default=list)
    entry_conditions = Column(JSONB, nullable=False, default=dict)
    adjustment_rules = Column(JSONB, nullable=False, default=list)
    order_settings = Column(JSONB, nullable=False, default=dict)
    risk_settings = Column(JSONB, nullable=False, default=dict)
    schedule_config = Column(JSONB, nullable=False, default=dict)

    # Priority & State
    priority = Column(Integer, nullable=False, default=100)
    runtime_state = Column(JSONB, nullable=True)

    # References
    source_template_id = Column(BigInteger, ForeignKey("autopilot_templates.id", ondelete="SET NULL"), nullable=True)
    cloned_from_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="SET NULL"), nullable=True)

    # Version & Timestamps
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="autopilot_strategies")
    orders = relationship("AutoPilotOrder", back_populates="strategy", cascade="all, delete-orphan")
    logs = relationship("AutoPilotLog", back_populates="strategy")


class AutoPilotOrder(Base):
    __tablename__ = "autopilot_orders"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    strategy_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Broker Reference
    kite_order_id = Column(String(50), nullable=True)
    kite_exchange_order_id = Column(String(50), nullable=True)

    # Order Context
    purpose = Column(String(20), nullable=False)
    rule_name = Column(String(100), nullable=True)
    leg_index = Column(Integer, nullable=False, default=0)

    # Instrument Details
    exchange = Column(String(10), nullable=False, default="NFO")
    tradingsymbol = Column(String(50), nullable=False)
    instrument_token = Column(BigInteger, nullable=True)
    underlying = Column(String(20), nullable=False)
    contract_type = Column(String(3), nullable=False)
    strike = Column(Numeric(10, 2), nullable=True)
    expiry = Column(Date, nullable=False)

    # Order Details
    transaction_type = Column(String(4), nullable=False)
    order_type = Column(String(10), nullable=False)
    product = Column(String(10), nullable=False, default="NRML")
    quantity = Column(Integer, nullable=False)

    # Prices
    order_price = Column(Numeric(10, 2), nullable=True)
    trigger_price = Column(Numeric(10, 2), nullable=True)
    ltp_at_order = Column(Numeric(10, 2), nullable=True)
    executed_price = Column(Numeric(10, 2), nullable=True)
    executed_quantity = Column(Integer, default=0)
    pending_quantity = Column(Integer, nullable=True)

    # Slippage
    slippage_amount = Column(Numeric(10, 2), nullable=True)
    slippage_pct = Column(Numeric(5, 2), nullable=True)

    # Status
    status = Column(String(20), nullable=False, default="pending")
    rejection_reason = Column(String(500), nullable=True)

    # Timing
    order_placed_at = Column(DateTime(timezone=True), nullable=True)
    order_filled_at = Column(DateTime(timezone=True), nullable=True)
    execution_duration_ms = Column(Integer, nullable=True)

    # Retry Tracking
    retry_count = Column(Integer, nullable=False, default=0)
    parent_order_id = Column(BigInteger, ForeignKey("autopilot_orders.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    raw_response = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    strategy = relationship("AutoPilotStrategy", back_populates="orders")
    user = relationship("User")


class AutoPilotLog(Base):
    __tablename__ = "autopilot_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="SET NULL"), nullable=True)
    order_id = Column(BigInteger, ForeignKey("autopilot_orders.id", ondelete="SET NULL"), nullable=True)

    # Event Details
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="info")

    # Context
    rule_name = Column(String(100), nullable=True)
    condition_id = Column(String(50), nullable=True)

    # Event Data
    event_data = Column(JSONB, nullable=False, default=dict)
    message = Column(String(1000), nullable=False)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    strategy = relationship("AutoPilotStrategy", back_populates="logs")
    user = relationship("User")


class AutoPilotTemplate(Base):
    __tablename__ = "autopilot_templates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    name = Column(String(100), nullable=False)
    description = Column(String(1000), nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    is_public = Column(Boolean, nullable=False, default=False)
    strategy_config = Column(JSONB, nullable=False)
    category = Column(String(50), nullable=True)
    tags = Column(ARRAY(String(50)), default=[])
    risk_level = Column(String(20), nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)
    avg_rating = Column(Numeric(3, 2), nullable=True)
    rating_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")


class AutoPilotConditionEval(Base):
    __tablename__ = "autopilot_condition_eval"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    strategy_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="CASCADE"), nullable=False)

    # Condition Reference
    condition_type = Column(String(20), nullable=False)
    condition_index = Column(Integer, nullable=False)
    rule_name = Column(String(100), nullable=True)

    # Condition Details
    variable = Column(String(50), nullable=False)
    operator = Column(String(20), nullable=False)
    target_value = Column(JSONB, nullable=False)

    # Evaluation Result
    current_value = Column(JSONB, nullable=False)
    is_satisfied = Column(Boolean, nullable=False)
    progress_pct = Column(Numeric(5, 2), nullable=True)
    distance_to_trigger = Column(String(100), nullable=True)

    # Timestamp
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AutoPilotDailySummary(Base):
    __tablename__ = "autopilot_daily_summary"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    summary_date = Column(Date, nullable=False)

    # Strategy Counts
    strategies_run = Column(Integer, nullable=False, default=0)
    strategies_completed = Column(Integer, nullable=False, default=0)
    strategies_errored = Column(Integer, nullable=False, default=0)

    # Order Counts
    orders_placed = Column(Integer, nullable=False, default=0)
    orders_filled = Column(Integer, nullable=False, default=0)
    orders_rejected = Column(Integer, nullable=False, default=0)

    # P&L
    total_realized_pnl = Column(Numeric(14, 2), nullable=False, default=0)
    total_brokerage = Column(Numeric(10, 2), nullable=False, default=0)
    total_slippage = Column(Numeric(10, 2), nullable=False, default=0)

    # Best/Worst
    best_strategy_pnl = Column(Numeric(12, 2), nullable=True)
    best_strategy_name = Column(String(100), nullable=True)
    worst_strategy_pnl = Column(Numeric(12, 2), nullable=True)
    worst_strategy_name = Column(String(100), nullable=True)

    # Execution Stats
    avg_execution_time_ms = Column(Integer, nullable=True)
    total_adjustments = Column(Integer, nullable=False, default=0)
    kill_switch_used = Column(Boolean, nullable=False, default=False)

    # Risk Metrics
    max_drawdown = Column(Numeric(12, 2), nullable=True)
    peak_margin_used = Column(Numeric(14, 2), nullable=True)
    daily_loss_limit_hit = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'summary_date', name='uq_user_date'),
    )
