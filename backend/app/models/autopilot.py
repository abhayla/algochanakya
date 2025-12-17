"""
AutoPilot SQLAlchemy Models

Reference: docs/autopilot/database-schema.md
Phase 3: Added ExecutionMode, AdjustmentTriggerType, AdjustmentActionType, ConfirmationStatus
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column, BigInteger, String, Integer, Boolean, Numeric,
    Date, DateTime, ForeignKey, Text, CheckConstraint,
    UniqueConstraint, Index, Enum
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID, ENUM as PgEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


# Enums
class StrategyStatus(str, enum.Enum):
    DRAFT = "draft"
    WAITING = "waiting"
    WAITING_STAGED_ENTRY = "waiting_staged_entry"  # Phase 5I: Partial entry completed, waiting for stage 2+
    ACTIVE = "active"
    PENDING = "pending"
    PAUSED = "paused"
    REENTRY_WAITING = "reentry_waiting"  # Phase 3: Exited, waiting for re-entry conditions
    COMPLETED = "completed"
    ERROR = "error"
    EXPIRED = "expired"
    CANCELLED = "cancelled"  # Phase 5I: Strategy cancelled during staged entry


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


# Phase 3 Enums
class ExecutionMode(str, enum.Enum):
    AUTO = "auto"
    SEMI_AUTO = "semi_auto"
    MANUAL = "manual"


class AdjustmentTriggerType(str, enum.Enum):
    PNL_BASED = "pnl_based"
    DELTA_BASED = "delta_based"
    TIME_BASED = "time_based"
    PREMIUM_BASED = "premium_based"
    VIX_BASED = "vix_based"
    SPOT_BASED = "spot_based"


class AdjustmentActionType(str, enum.Enum):
    ADD_HEDGE = "add_hedge"
    CLOSE_LEG = "close_leg"
    ROLL_STRIKE = "roll_strike"
    ROLL_EXPIRY = "roll_expiry"
    EXIT_ALL = "exit_all"
    SCALE_DOWN = "scale_down"
    SCALE_UP = "scale_up"


class ConfirmationStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


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

    # Phase 3: Kill Switch
    kill_switch_enabled = Column(Boolean, nullable=False, default=False)
    kill_switch_triggered_at = Column(DateTime(timezone=True), nullable=True)

    # Phase 3: Semi-Auto Execution
    default_execution_mode = Column(
        PgEnum('auto', 'semi_auto', 'manual',
               name='autopilot_execution_mode', create_type=False),
        nullable=False,
        default="auto"
    )
    confirmation_timeout_seconds = Column(Integer, nullable=False, default=30)

    # Phase 3: Auto-Exit
    auto_exit_time = Column(String(5), nullable=True, default="15:15")

    # Phase 3: Position Sizing
    account_capital = Column(Numeric(14, 2), nullable=True)
    risk_per_trade_pct = Column(Numeric(5, 2), nullable=True, default=2.00)

    # Phase 5: Delta Monitoring Thresholds
    delta_watch_threshold = Column(Numeric(4, 2), nullable=False, server_default='0.20')
    delta_warning_threshold = Column(Numeric(4, 2), nullable=False, server_default='0.30')
    delta_danger_threshold = Column(Numeric(4, 2), nullable=False, server_default='0.40')
    delta_alert_enabled = Column(Boolean, nullable=False, server_default='true')

    # Phase 5: Adjustment Preferences
    suggestions_enabled = Column(Boolean, nullable=False, server_default='true')
    prefer_round_strikes = Column(Boolean, nullable=False, server_default='true')

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
    status = Column(
        PgEnum('draft', 'waiting', 'waiting_staged_entry', 'active', 'pending', 'paused', 'reentry_waiting',
               'completed', 'error', 'expired', 'cancelled',
               name='autopilot_strategy_status', create_type=False),
        nullable=False,
        default="draft"
    )

    # Instrument Configuration
    underlying = Column(
        PgEnum('NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX',
               name='autopilot_underlying', create_type=False),
        nullable=False
    )
    expiry_type = Column(String(20), nullable=False, default="current_week")
    expiry_date = Column(Date, nullable=True)
    lots = Column(Integer, nullable=False, default=1)
    position_type = Column(
        PgEnum('intraday', 'positional',
               name='autopilot_position_type', create_type=False),
        nullable=False,
        default="intraday"
    )

    # JSONB Configurations
    legs_config = Column(JSONB, nullable=False, default=list)
    entry_conditions = Column(JSONB, nullable=False, default=dict)
    adjustment_rules = Column(JSONB, nullable=False, default=list)
    order_settings = Column(JSONB, nullable=False, default=dict)
    risk_settings = Column(JSONB, nullable=False, default=dict)
    schedule_config = Column(JSONB, nullable=False, default=dict)

    # Phase 3: Re-Entry Configuration
    reentry_config = Column(JSONB, nullable=True, comment="Re-entry settings: enabled, max_reentries, cooldown_minutes, conditions, reentry_count")

    # Phase 3: Execution Mode (overrides user default)
    execution_mode = Column(
        PgEnum('auto', 'semi_auto', 'manual',
               name='autopilot_execution_mode', create_type=False),
        nullable=True
    )

    # Phase 3: Trailing Stop Configuration
    trailing_stop_config = Column(JSONB, nullable=True)

    # Phase 3: Greeks Snapshot
    greeks_snapshot = Column(JSONB, nullable=True)

    # Phase 5I: Staged Entry Configuration
    staged_entry_config = Column(JSONB, nullable=True, comment="Configuration for staged entry (half-size or staggered mode)")

    # Phase 5: Position Legs & Greeks Tracking
    position_legs_snapshot = Column(JSONB, nullable=True)
    net_delta = Column(Numeric(6, 4), nullable=True)
    net_theta = Column(Numeric(10, 2), nullable=True)
    net_gamma = Column(Numeric(8, 6), nullable=True)
    net_vega = Column(Numeric(8, 4), nullable=True)
    breakeven_lower = Column(Numeric(10, 2), nullable=True)
    breakeven_upper = Column(Numeric(10, 2), nullable=True)
    dte = Column(Integer, nullable=True)  # Days to expiry

    # Priority & State
    priority = Column(Integer, nullable=False, default=100)
    runtime_state = Column(JSONB, nullable=True)

    # References
    source_template_id = Column(BigInteger, ForeignKey("autopilot_templates.id", ondelete="SET NULL"), nullable=True)
    cloned_from_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="SET NULL"), nullable=True)

    # Phase 4: Sharing
    share_mode = Column(
        PgEnum('private', 'link', 'public',
               name='autopilot_share_mode', create_type=False),
        nullable=False,
        default="private"
    )
    share_token = Column(String(50), nullable=True, unique=True)
    shared_at = Column(DateTime(timezone=True), nullable=True)

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
    adjustment_logs = relationship("AutoPilotAdjustmentLog", back_populates="strategy", cascade="all, delete-orphan")
    pending_confirmations = relationship("AutoPilotPendingConfirmation", back_populates="strategy", cascade="all, delete-orphan")
    # Phase 5 Relationships
    position_legs = relationship("AutoPilotPositionLeg", back_populates="strategy", cascade="all, delete-orphan")
    suggestions = relationship("AutoPilotAdjustmentSuggestion", back_populates="strategy", cascade="all, delete-orphan")


class AutoPilotOrder(Base):
    __tablename__ = "autopilot_orders"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    strategy_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Broker Reference
    kite_order_id = Column(String(50), nullable=True)
    kite_exchange_order_id = Column(String(50), nullable=True)

    # Order Context
    purpose = Column(
        PgEnum('entry', 'adjustment', 'hedge', 'exit', 'roll_close', 'roll_open', 'kill_switch',
               name='autopilot_order_purpose', create_type=False),
        nullable=False
    )
    rule_name = Column(String(100), nullable=True)
    leg_index = Column(Integer, nullable=False, default=0)

    # Instrument Details
    exchange = Column(String(10), nullable=False, default="NFO")
    tradingsymbol = Column(String(50), nullable=False)
    instrument_token = Column(BigInteger, nullable=True)
    underlying = Column(
        PgEnum('NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX',
               name='autopilot_underlying', create_type=False),
        nullable=False
    )
    contract_type = Column(String(2), nullable=False)
    strike = Column(Numeric(10, 2), nullable=True)
    expiry = Column(Date, nullable=False)

    # Order Details
    transaction_type = Column(
        PgEnum('BUY', 'SELL',
               name='autopilot_transaction_type', create_type=False),
        nullable=False
    )
    order_type = Column(
        PgEnum('MARKET', 'LIMIT', 'SL', 'SL-M',
               name='autopilot_order_type', create_type=False),
        nullable=False
    )
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
    status = Column(
        PgEnum('pending', 'placed', 'open', 'complete', 'cancelled', 'rejected', 'error',
               name='autopilot_order_status', create_type=False),
        nullable=False,
        default="pending"
    )
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
    event_type = Column(
        PgEnum('strategy_created', 'strategy_activated', 'strategy_paused', 'strategy_resumed',
               'strategy_completed', 'strategy_expired', 'strategy_error',
               'entry_condition_evaluated', 'entry_condition_triggered',
               'entry_started', 'entry_completed', 'entry_failed',
               'adjustment_condition_evaluated', 'adjustment_condition_triggered',
               'confirmation_requested', 'confirmation_received', 'confirmation_timeout', 'confirmation_skipped',
               'adjustment_started', 'adjustment_completed', 'adjustment_failed',
               'order_placed', 'order_filled', 'order_partial_fill', 'order_cancelled', 'order_rejected', 'order_modified',
               'exit_triggered', 'exit_started', 'exit_completed', 'exit_failed',
               'risk_limit_warning', 'risk_limit_breach', 'daily_loss_limit_hit',
               'margin_warning', 'margin_insufficient', 'kill_switch_activated',
               'connection_lost', 'connection_restored', 'system_error', 'api_error',
               'user_modified_settings', 'user_force_entry', 'user_force_exit',
               name='autopilot_log_event', create_type=False),
        nullable=False
    )
    severity = Column(
        PgEnum('debug', 'info', 'warning', 'error', 'critical',
               name='autopilot_log_severity', create_type=False),
        nullable=False,
        default="info"
    )

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

    # Phase 4: Enhanced template fields
    author_name = Column(String(100), nullable=True)
    underlying = Column(String(20), nullable=True)
    position_type = Column(String(20), nullable=True)
    expected_return_pct = Column(Numeric(5, 2), nullable=True)
    max_risk_pct = Column(Numeric(5, 2), nullable=True)
    market_outlook = Column(String(50), nullable=True)  # bullish, bearish, neutral, volatile
    iv_environment = Column(String(50), nullable=True)  # high, low, normal
    thumbnail_url = Column(String(500), nullable=True)
    educational_content = Column(JSONB, nullable=True, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    ratings = relationship("AutoPilotTemplateRating", back_populates="template", cascade="all, delete-orphan")


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


# Phase 3 Models
class AutoPilotAdjustmentLog(Base):
    """
    Phase 3: Track adjustment rule executions.
    Logs when adjustment rules are triggered and their outcomes.
    """
    __tablename__ = "autopilot_adjustment_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    strategy_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Rule Reference
    rule_id = Column(String(50), nullable=False)
    rule_name = Column(String(100), nullable=False)

    # Trigger Details
    trigger_type = Column(
        PgEnum('pnl_based', 'delta_based', 'time_based', 'premium_based', 'vix_based', 'spot_based',
               name='autopilot_adjustment_trigger_type', create_type=False),
        nullable=False
    )
    trigger_condition = Column(String(200), nullable=False)
    trigger_value = Column(JSONB, nullable=False)
    actual_value = Column(JSONB, nullable=False)

    # Action Details
    action_type = Column(
        PgEnum('add_hedge', 'close_leg', 'roll_strike', 'roll_expiry', 'exit_all', 'scale_down', 'scale_up',
               name='autopilot_adjustment_action_type', create_type=False),
        nullable=False
    )
    action_params = Column(JSONB, nullable=False, default=dict)

    # Execution Status
    execution_mode = Column(
        PgEnum('auto', 'semi_auto', 'manual',
               name='autopilot_execution_mode', create_type=False),
        nullable=False
    )
    executed = Column(Boolean, nullable=False, default=False)
    execution_result = Column(JSONB, nullable=True)
    error_message = Column(String(500), nullable=True)

    # Related Orders
    order_ids = Column(ARRAY(BigInteger), nullable=True)

    # Confirmation (for semi-auto)
    confirmation_id = Column(BigInteger, ForeignKey("autopilot_pending_confirmations.id", ondelete="SET NULL"), nullable=True)
    confirmed_by_user = Column(Boolean, nullable=True)

    # Timestamps
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    strategy = relationship("AutoPilotStrategy", back_populates="adjustment_logs")
    user = relationship("User")
    confirmation = relationship("AutoPilotPendingConfirmation", foreign_keys=[confirmation_id])


class AutoPilotPendingConfirmation(Base):
    """
    Phase 3: Semi-auto confirmation requests.
    When execution_mode is 'semi_auto', actions require user confirmation.
    """
    __tablename__ = "autopilot_pending_confirmations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="CASCADE"), nullable=False)

    # Action Type
    action_type = Column(String(50), nullable=False)  # 'entry', 'adjustment', 'exit', 'hedge'
    action_description = Column(String(500), nullable=False)
    action_data = Column(JSONB, nullable=False, default=dict)

    # Related Rule (for adjustments)
    rule_id = Column(String(50), nullable=True)
    rule_name = Column(String(100), nullable=True)

    # Status
    status = Column(
        PgEnum('pending', 'confirmed', 'rejected', 'expired', 'cancelled',
               name='autopilot_confirmation_status', create_type=False),
        nullable=False,
        default="pending"
    )

    # Timing
    timeout_seconds = Column(Integer, nullable=False, default=30)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Response
    responded_at = Column(DateTime(timezone=True), nullable=True)
    response_source = Column(String(50), nullable=True)  # 'user', 'timeout', 'system'

    # Execution Result
    execution_result = Column(JSONB, nullable=True)
    order_ids = Column(ARRAY(BigInteger), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    strategy = relationship("AutoPilotStrategy", back_populates="pending_confirmations")
    user = relationship("User")


# =============================================================================
# Phase 4 Enums
# =============================================================================

class ExitReason(str, enum.Enum):
    TARGET_HIT = "target_hit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    TIME_EXIT = "time_exit"
    MANUAL_EXIT = "manual_exit"
    ADJUSTMENT_EXIT = "adjustment_exit"
    KILL_SWITCH = "kill_switch"
    AUTO_EXIT = "auto_exit"
    ERROR = "error"


class TemplateCategory(str, enum.Enum):
    INCOME = "income"
    DIRECTIONAL = "directional"
    VOLATILITY = "volatility"
    HEDGING = "hedging"
    ADVANCED = "advanced"
    CUSTOM = "custom"


class ReportType(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"
    STRATEGY = "strategy"
    TAX = "tax"


class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"


class BacktestStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ShareMode(str, enum.Enum):
    PRIVATE = "private"
    LINK = "link"
    PUBLIC = "public"


# =============================================================================
# Phase 4 Models
# =============================================================================

class AutoPilotTradeJournal(Base):
    """
    Phase 4: Automatic trade logging.
    Records all trades with full details for analysis and reporting.
    """
    __tablename__ = "autopilot_trade_journal"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="SET NULL"), nullable=True)

    # Strategy Info (snapshot at trade time)
    strategy_name = Column(String(100), nullable=False)
    underlying = Column(String(20), nullable=False)
    position_type = Column(String(20), nullable=False)

    # Trade Timing
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    holding_duration_minutes = Column(Integer, nullable=True)

    # Legs Snapshot (JSONB)
    legs = Column(JSONB, nullable=False, default=list)

    # Quantities
    lots = Column(Integer, nullable=False)
    total_quantity = Column(Integer, nullable=False)

    # Prices
    entry_premium = Column(Numeric(12, 2), nullable=True)
    exit_premium = Column(Numeric(12, 2), nullable=True)

    # P&L
    gross_pnl = Column(Numeric(14, 2), nullable=True)
    brokerage = Column(Numeric(10, 2), nullable=True, default=0)
    taxes = Column(Numeric(10, 2), nullable=True, default=0)
    other_charges = Column(Numeric(10, 2), nullable=True, default=0)
    net_pnl = Column(Numeric(14, 2), nullable=True)
    pnl_percentage = Column(Numeric(8, 4), nullable=True)

    # Tracking metrics
    max_profit_reached = Column(Numeric(14, 2), nullable=True)
    max_loss_reached = Column(Numeric(14, 2), nullable=True)
    max_drawdown = Column(Numeric(14, 2), nullable=True)

    # Exit Details
    exit_reason = Column(
        PgEnum('target_hit', 'stop_loss', 'trailing_stop', 'time_exit',
               'manual_exit', 'adjustment_exit', 'kill_switch', 'auto_exit', 'error',
               name='autopilot_exit_reason', create_type=False),
        nullable=True
    )

    # Market Conditions (JSONB)
    market_conditions = Column(JSONB, nullable=True, default=dict)

    # User Notes & Tags
    notes = Column(Text, nullable=True)
    tags = Column(ARRAY(String(50)), default=[])

    # Screenshots (JSONB array of URLs)
    screenshots = Column(JSONB, nullable=True, default=list)

    # Order IDs (for reference)
    entry_order_ids = Column(ARRAY(BigInteger), nullable=True)
    exit_order_ids = Column(ARRAY(BigInteger), nullable=True)

    # Status
    is_open = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    strategy = relationship("AutoPilotStrategy")


class AutoPilotAnalyticsCache(Base):
    """
    Phase 4: Pre-calculated analytics cache.
    Stores computed metrics for fast dashboard loading.
    """
    __tablename__ = "autopilot_analytics_cache"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Cache Key (e.g., 'summary_30d', 'performance_ytd')
    cache_key = Column(String(100), nullable=False)

    # Date Range
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Cached Metrics (JSONB)
    metrics = Column(JSONB, nullable=False)

    # Cache Validity
    is_valid = Column(Boolean, nullable=False, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'cache_key', name='uq_analytics_cache_user_key'),
    )


class AutoPilotReport(Base):
    """
    Phase 4: Generated reports.
    Stores report configurations and generated files.
    """
    __tablename__ = "autopilot_reports"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Report Type
    report_type = Column(
        PgEnum('daily', 'weekly', 'monthly', 'custom', 'strategy', 'tax',
               name='autopilot_report_type', create_type=False),
        nullable=False
    )

    # Report Name
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)

    # Date Range
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Strategy Filter (optional)
    strategy_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="SET NULL"), nullable=True)

    # Report Data (JSONB)
    report_data = Column(JSONB, nullable=False)

    # Export Format & File
    format = Column(
        PgEnum('pdf', 'excel', 'csv',
               name='autopilot_report_format', create_type=False),
        nullable=True
    )
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)

    # Status
    is_ready = Column(Boolean, nullable=False, default=False)
    error_message = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")
    strategy = relationship("AutoPilotStrategy")


class AutoPilotBacktest(Base):
    """
    Phase 4: Backtest results.
    Stores backtest configurations and results.
    """
    __tablename__ = "autopilot_backtests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Backtest Name
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)

    # Strategy Configuration (JSONB snapshot)
    strategy_config = Column(JSONB, nullable=False)

    # Backtest Parameters
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(Numeric(14, 2), nullable=False)
    slippage_pct = Column(Numeric(5, 2), nullable=False, default=0.1)
    charges_per_lot = Column(Numeric(10, 2), nullable=False, default=40)
    data_interval = Column(String(20), nullable=False, default="1min")

    # Status
    status = Column(
        PgEnum('pending', 'running', 'completed', 'failed', 'cancelled',
               name='autopilot_backtest_status', create_type=False),
        nullable=False,
        default="pending"
    )
    progress_pct = Column(Integer, nullable=False, default=0)
    error_message = Column(String(500), nullable=True)

    # Results (JSONB)
    results = Column(JSONB, nullable=True)

    # Summary Metrics
    total_trades = Column(Integer, nullable=True)
    winning_trades = Column(Integer, nullable=True)
    losing_trades = Column(Integer, nullable=True)
    win_rate = Column(Numeric(5, 2), nullable=True)
    gross_pnl = Column(Numeric(14, 2), nullable=True)
    net_pnl = Column(Numeric(14, 2), nullable=True)
    max_drawdown = Column(Numeric(14, 2), nullable=True)
    max_drawdown_pct = Column(Numeric(5, 2), nullable=True)
    sharpe_ratio = Column(Numeric(6, 3), nullable=True)
    profit_factor = Column(Numeric(6, 3), nullable=True)

    # Equity Curve (JSONB array)
    equity_curve = Column(JSONB, nullable=True, default=list)

    # Trades List (JSONB array)
    trades = Column(JSONB, nullable=True, default=list)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")


class AutoPilotTemplateRating(Base):
    """
    Phase 4: User ratings for templates.
    One rating per user per template.
    """
    __tablename__ = "autopilot_template_ratings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    template_id = Column(BigInteger, ForeignKey("autopilot_templates.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Rating
    rating = Column(Integer, nullable=False)
    review = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    template = relationship("AutoPilotTemplate", back_populates="ratings")
    user = relationship("User")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('template_id', 'user_id', name='uq_template_rating_user'),
        CheckConstraint('rating >= 1 AND rating <= 5', name='chk_rating_value'),
    )


# =============================================================================
# PHASE 5 MODELS: Advanced Adjustments & Option Chain Integration
# =============================================================================


class PositionLegStatus(str, enum.Enum):
    """Status of an individual position leg"""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    ROLLED = "rolled"


class SuggestionType(str, enum.Enum):
    """Type of adjustment suggestion"""
    SHIFT = "shift"
    BREAK = "break"
    ROLL = "roll"
    EXIT = "exit"
    ADD_HEDGE = "add_hedge"
    NO_ACTION = "no_action"


class SuggestionUrgency(str, enum.Enum):
    """Urgency level of suggestion"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SuggestionStatus(str, enum.Enum):
    """Status of suggestion"""
    ACTIVE = "active"
    DISMISSED = "dismissed"
    EXECUTED = "executed"
    EXPIRED = "expired"


class AutoPilotPositionLeg(Base):
    """
    Phase 5: Individual leg tracking with Greeks and P&L.
    Tracks each option leg separately for advanced adjustments.
    """
    __tablename__ = "autopilot_position_legs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    strategy_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="CASCADE"), nullable=False)
    leg_id = Column(String(50), nullable=False)

    # Configuration
    contract_type = Column(String(2), nullable=False)  # CE, PE
    action = Column(String(4), nullable=False)  # BUY, SELL
    strike = Column(Numeric(10, 2), nullable=False)
    expiry = Column(Date, nullable=False)
    lots = Column(Integer, nullable=False)

    # Instrument
    tradingsymbol = Column(String(50))
    instrument_token = Column(BigInteger)

    # Status
    status = Column(String(20), server_default="pending")

    # Entry
    entry_price = Column(Numeric(10, 2))
    entry_time = Column(DateTime)
    entry_order_ids = Column(JSONB, server_default='[]')

    # Exit
    exit_price = Column(Numeric(10, 2))
    exit_time = Column(DateTime)
    exit_order_ids = Column(JSONB, server_default='[]')
    exit_reason = Column(String(50))

    # Greeks (updated real-time)
    delta = Column(Numeric(6, 4))
    gamma = Column(Numeric(8, 6))
    theta = Column(Numeric(10, 2))
    vega = Column(Numeric(8, 4))
    iv = Column(Numeric(6, 2))

    # P&L
    unrealized_pnl = Column(Numeric(12, 2), server_default='0')
    realized_pnl = Column(Numeric(12, 2), server_default='0')

    # Roll tracking
    rolled_from_leg_id = Column(BigInteger, ForeignKey("autopilot_position_legs.id"))
    rolled_to_leg_id = Column(BigInteger)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    strategy = relationship("AutoPilotStrategy", back_populates="position_legs")
    rolled_from = relationship("AutoPilotPositionLeg", remote_side=[id], foreign_keys=[rolled_from_leg_id])

    # Indexes
    __table_args__ = (
        Index('idx_position_legs_strategy', 'strategy_id'),
        Index('idx_position_legs_status', 'status'),
        Index('idx_position_legs_strategy_leg', 'strategy_id', 'leg_id',
              unique=True, postgresql_where=Column('status') == 'open'),
    )


class AutoPilotAdjustmentSuggestion(Base):
    """
    Phase 5: AI-generated adjustment suggestions.
    Analyzes position state and suggests appropriate adjustments.
    """
    __tablename__ = "autopilot_adjustment_suggestions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    strategy_id = Column(BigInteger, ForeignKey("autopilot_strategies.id", ondelete="CASCADE"), nullable=False)
    leg_id = Column(String(50), nullable=True)

    trigger_reason = Column(Text, nullable=False)
    suggestion_type = Column(String(30), nullable=False)
    description = Column(Text, nullable=False)
    details = Column(JSONB)

    urgency = Column(String(20), server_default="medium")
    confidence = Column(Integer, server_default='50')
    category = Column(String(20), server_default="defensive")  # defensive, offensive, neutral

    one_click_action = Column(Boolean, server_default='false')
    action_params = Column(JSONB)

    status = Column(String(20), server_default="active")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    responded_at = Column(DateTime(timezone=True))

    # Relationships
    strategy = relationship("AutoPilotStrategy", back_populates="suggestions")

    # Indexes
    __table_args__ = (
        Index('idx_suggestions_strategy', 'strategy_id'),
        Index('idx_suggestions_status', 'status'),
    )


class AutoPilotOptionChainCache(Base):
    """
    Phase 5: Option chain data cache with Greeks.
    Caches option chain data to reduce API calls.
    """
    __tablename__ = "autopilot_option_chain_cache"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    underlying = Column(String(20), nullable=False)
    expiry = Column(Date, nullable=False)
    strike = Column(Numeric(10, 2), nullable=False)
    option_type = Column(String(2), nullable=False)  # CE, PE

    tradingsymbol = Column(String(50), nullable=False)
    instrument_token = Column(BigInteger, nullable=False)

    ltp = Column(Numeric(10, 2))
    bid = Column(Numeric(10, 2))
    ask = Column(Numeric(10, 2))
    volume = Column(BigInteger)
    oi = Column(BigInteger)
    oi_change = Column(BigInteger)

    iv = Column(Numeric(6, 2))
    delta = Column(Numeric(6, 4))
    gamma = Column(Numeric(8, 6))
    theta = Column(Numeric(10, 2))
    vega = Column(Numeric(8, 4))

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('underlying', 'expiry', 'strike', 'option_type',
                         name='uq_option_chain_cache'),
        Index('idx_option_chain_underlying', 'underlying', 'expiry'),
        Index('idx_option_chain_delta', 'underlying', 'expiry', 'option_type', 'delta'),
    )
