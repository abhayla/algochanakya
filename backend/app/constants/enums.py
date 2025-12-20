"""
Centralized Enums

This is the SINGLE SOURCE OF TRUTH for all status and type enums.
Import these in both models and schemas to avoid duplication.

Updated: 2025-12-21
"""

import enum


# =============================================================================
# STRATEGY ENUMS
# =============================================================================

class StrategyStatus(str, enum.Enum):
    """Status of an AutoPilot strategy."""
    DRAFT = "draft"
    WAITING = "waiting"
    WAITING_STAGED_ENTRY = "waiting_staged_entry"
    ACTIVE = "active"
    PENDING = "pending"
    PAUSED = "paused"
    REENTRY_WAITING = "reentry_waiting"
    COMPLETED = "completed"
    ERROR = "error"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Underlying(str, enum.Enum):
    """Supported underlying instruments."""
    NIFTY = "NIFTY"
    BANKNIFTY = "BANKNIFTY"
    FINNIFTY = "FINNIFTY"
    SENSEX = "SENSEX"


class PositionType(str, enum.Enum):
    """Type of position (intraday or positional)."""
    INTRADAY = "intraday"
    POSITIONAL = "positional"


# =============================================================================
# ORDER ENUMS
# =============================================================================

class OrderStatus(str, enum.Enum):
    """Status of an order."""
    PENDING = "pending"
    PLACED = "placed"
    OPEN = "open"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ERROR = "error"


class OrderPurpose(str, enum.Enum):
    """Purpose of an order."""
    ENTRY = "entry"
    ADJUSTMENT = "adjustment"
    HEDGE = "hedge"
    EXIT = "exit"
    ROLL_CLOSE = "roll_close"
    ROLL_OPEN = "roll_open"
    KILL_SWITCH = "kill_switch"


class OrderType(str, enum.Enum):
    """Order type for placement."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class TransactionType(str, enum.Enum):
    """Transaction type (buy or sell)."""
    BUY = "BUY"
    SELL = "SELL"


# =============================================================================
# CONTRACT/OPTION ENUMS
# =============================================================================

class ContractType(str, enum.Enum):
    """Option contract type."""
    CE = "CE"
    PE = "PE"
    FUT = "FUT"


class ExpiryType(str, enum.Enum):
    """Expiry selection type."""
    CURRENT_WEEK = "current_week"
    NEXT_WEEK = "next_week"
    MONTHLY = "monthly"
    CUSTOM = "custom"


# =============================================================================
# EXECUTION ENUMS
# =============================================================================

class ExecutionMode(str, enum.Enum):
    """Execution mode for strategies."""
    AUTO = "auto"
    SEMI_AUTO = "semi_auto"
    MANUAL = "manual"


class ExecutionStyle(str, enum.Enum):
    """Order execution style."""
    SIMULTANEOUS = "simultaneous"
    SEQUENTIAL = "sequential"
    WITH_DELAY = "with_delay"


class TradingMode(str, enum.Enum):
    """Trading mode (live or paper)."""
    LIVE = "live"
    PAPER = "paper"


# =============================================================================
# CONDITION ENUMS
# =============================================================================

class ConditionOperator(str, enum.Enum):
    """Condition comparison operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    BETWEEN = "between"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"


class ConditionLogic(str, enum.Enum):
    """Logic for combining multiple conditions."""
    AND = "AND"
    OR = "OR"


# =============================================================================
# ADJUSTMENT ENUMS
# =============================================================================

class AdjustmentTriggerType(str, enum.Enum):
    """Type of trigger for adjustments."""
    PNL_BASED = "pnl_based"
    DELTA_BASED = "delta_based"
    TIME_BASED = "time_based"
    PREMIUM_BASED = "premium_based"
    VIX_BASED = "vix_based"
    SPOT_BASED = "spot_based"
    PROFIT_PCT_BASED = "profit_pct_based"
    PREMIUM_CAPTURED_PCT = "premium_captured_pct"
    RETURN_ON_MARGIN = "return_on_margin"
    CAPITAL_RECYCLING = "capital_recycling"
    DTE_BASED = "dte_based"
    DAYS_IN_TRADE = "days_in_trade"
    THETA_CURVE_BASED = "theta_curve_based"
    GAMMA_BASED = "gamma_based"
    ATR_BASED = "atr_based"
    DELTA_DOUBLES = "delta_doubles"
    DELTA_CHANGE = "delta_change"
    THETA_BASED = "theta_based"
    VEGA_BASED = "vega_based"


class AdjustmentActionType(str, enum.Enum):
    """Action to take for adjustments."""
    ADD_HEDGE = "add_hedge"
    CLOSE_LEG = "close_leg"
    ROLL_STRIKE = "roll_strike"
    ROLL_EXPIRY = "roll_expiry"
    EXIT_ALL = "exit_all"
    SCALE_DOWN = "scale_down"
    SCALE_UP = "scale_up"
    ADD_TO_OPPOSITE_SIDE = "add_to_opposite_side"
    WIDEN_SPREAD = "widen_spread"
    SHIFT_LEG = "shift_leg"
    DELTA_NEUTRAL_REBALANCE = "delta_neutral_rebalance"


class AdjustmentCategory(str, enum.Enum):
    """Category of adjustment."""
    OFFENSIVE = "offensive"
    DEFENSIVE = "defensive"
    NEUTRAL = "neutral"


# =============================================================================
# CONFIRMATION & STATUS ENUMS
# =============================================================================

class ConfirmationStatus(str, enum.Enum):
    """Status of user confirmations."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class LogSeverity(str, enum.Enum):
    """Log severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BacktestStatus(str, enum.Enum):
    """Status of backtest runs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PositionLegStatus(str, enum.Enum):
    """Status of an individual position leg."""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    ROLLED = "rolled"


class SuggestionStatus(str, enum.Enum):
    """Status of adjustment suggestions."""
    ACTIVE = "active"
    DISMISSED = "dismissed"
    EXECUTED = "executed"
    EXPIRED = "expired"


# =============================================================================
# TEMPLATE & REPORT ENUMS
# =============================================================================

class ExitReason(str, enum.Enum):
    """Reason for strategy exit."""
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
    """Category of strategy templates."""
    INCOME = "income"
    DIRECTIONAL = "directional"
    VOLATILITY = "volatility"
    HEDGING = "hedging"
    ADVANCED = "advanced"
    CUSTOM = "custom"


class ReportType(str, enum.Enum):
    """Type of report."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"
    STRATEGY = "strategy"
    TAX = "tax"


class ReportFormat(str, enum.Enum):
    """Format for report export."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"


class ShareMode(str, enum.Enum):
    """Sharing mode for strategies."""
    PRIVATE = "private"
    LINK = "link"
    PUBLIC = "public"


# =============================================================================
# MARKET & STRATEGY ANALYSIS ENUMS
# =============================================================================

class MarketOutlook(str, enum.Enum):
    """Market outlook."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"


class IVEnvironment(str, enum.Enum):
    """Implied volatility environment."""
    HIGH = "high"
    LOW = "low"
    NORMAL = "normal"


# =============================================================================
# STRIKE & ENTRY ENUMS
# =============================================================================

class StrikeMode(str, enum.Enum):
    """Strike selection mode."""
    FIXED = "fixed"
    ATM_OFFSET = "atm_offset"
    PREMIUM_BASED = "premium_based"
    DELTA_BASED = "delta_based"
    PREMIUM_RANGE = "premium_range"
    DELTA_RANGE = "delta_range"
    SD_BASED = "sd_based"


class StagedEntryMode(str, enum.Enum):
    """Staged entry mode."""
    HALF_SIZE = "half_size"
    STAGGERED = "staggered"


# =============================================================================
# GREEKS & TRAILING ENUMS
# =============================================================================

class GreekConditionVariable(str, enum.Enum):
    """Greek variables for conditions."""
    STRATEGY_DELTA = "STRATEGY.DELTA"
    STRATEGY_GAMMA = "STRATEGY.GAMMA"
    STRATEGY_THETA = "STRATEGY.THETA"
    STRATEGY_VEGA = "STRATEGY.VEGA"


class TrailType(str, enum.Enum):
    """Trailing stop type."""
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    ATR_BASED = "atr_based"


# =============================================================================
# SUGGESTION ENUMS
# =============================================================================

class SuggestionType(str, enum.Enum):
    """Type of adjustment suggestion."""
    SHIFT = "shift"
    BREAK = "break"
    ROLL = "roll"
    EXIT = "exit"
    ADD_HEDGE = "add_hedge"
    NO_ACTION = "no_action"


class SuggestionUrgency(str, enum.Enum):
    """Urgency level of suggestion."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
