"""
AutoPilot Pydantic Schemas

Reference: docs/autopilot/api-contracts.md
Phase 3: Added ExecutionMode, AdjustmentTriggerType, AdjustmentActionType, ConfirmationStatus
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# Enums
class StrategyStatus(str, Enum):
    draft = "draft"
    waiting = "waiting"
    waiting_staged_entry = "waiting_staged_entry"  # Phase 5I: Partial entry completed, waiting for stage 2+
    active = "active"
    pending = "pending"
    paused = "paused"
    completed = "completed"
    error = "error"
    expired = "expired"
    cancelled = "cancelled"  # Phase 5I: Strategy cancelled during staged entry


class Underlying(str, Enum):
    NIFTY = "NIFTY"
    BANKNIFTY = "BANKNIFTY"
    FINNIFTY = "FINNIFTY"
    SENSEX = "SENSEX"


class PositionType(str, Enum):
    intraday = "intraday"
    positional = "positional"


class ContractType(str, Enum):
    CE = "CE"
    PE = "PE"
    FUT = "FUT"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class ExpiryType(str, Enum):
    current_week = "current_week"
    next_week = "next_week"
    monthly = "monthly"
    custom = "custom"


class ExecutionStyle(str, Enum):
    simultaneous = "simultaneous"
    sequential = "sequential"
    with_delay = "with_delay"


class ConditionOperator(str, Enum):
    equals = "equals"
    not_equals = "not_equals"
    greater_than = "greater_than"
    less_than = "less_than"
    between = "between"
    crosses_above = "crosses_above"
    crosses_below = "crosses_below"


class ConditionLogic(str, Enum):
    AND = "AND"
    OR = "OR"


# Phase 3 Enums
class ExecutionMode(str, Enum):
    auto = "auto"
    semi_auto = "semi_auto"
    manual = "manual"


class AdjustmentTriggerType(str, Enum):
    pnl_based = "pnl_based"
    delta_based = "delta_based"
    time_based = "time_based"
    premium_based = "premium_based"
    vix_based = "vix_based"
    spot_based = "spot_based"
    # Phase 5D: Exit Rules
    profit_pct_based = "profit_pct_based"
    premium_captured_pct = "premium_captured_pct"
    return_on_margin = "return_on_margin"
    capital_recycling = "capital_recycling"
    dte_based = "dte_based"
    days_in_trade = "days_in_trade"
    theta_curve_based = "theta_curve_based"
    # Phase 5E: Risk-Based Exits
    gamma_based = "gamma_based"
    atr_based = "atr_based"
    delta_doubles = "delta_doubles"
    delta_change = "delta_change"
    # Phase 5G: Greek-Based Triggers
    theta_based = "theta_based"
    vega_based = "vega_based"


class AdjustmentActionType(str, Enum):
    add_hedge = "add_hedge"
    close_leg = "close_leg"
    roll_strike = "roll_strike"
    roll_expiry = "roll_expiry"
    exit_all = "exit_all"
    scale_down = "scale_down"
    scale_up = "scale_up"
    # Phase 5F/5G additions
    add_to_opposite_side = "add_to_opposite_side"
    widen_spread = "widen_spread"
    shift_leg = "shift_leg"
    delta_neutral_rebalance = "delta_neutral_rebalance"


class ConfirmationStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"
    expired = "expired"
    cancelled = "cancelled"


class TrailType(str, Enum):
    fixed = "fixed"
    percentage = "percentage"
    atr_based = "atr_based"


# Nested Models
class StrikeSelection(BaseModel):
    mode: str = Field(..., description="fixed | atm_offset | premium_based | delta_based | premium_range | delta_range")
    offset: Optional[int] = None
    fixed_strike: Optional[Decimal] = None
    target_premium: Optional[Decimal] = None
    target_delta: Optional[float] = None
    # Phase 5A: Range-based selection
    premium_min: Optional[Decimal] = None
    premium_max: Optional[Decimal] = None
    delta_min: Optional[float] = None
    delta_max: Optional[float] = None
    # Phase 5A: Round strike preference
    prefer_round_strike: bool = True


class LegConfig(BaseModel):
    id: str
    contract_type: ContractType
    transaction_type: TransactionType
    strike_selection: StrikeSelection
    quantity_multiplier: int = 1
    execution_order: int = 1


class Condition(BaseModel):
    id: str
    enabled: bool = True
    variable: str
    operator: ConditionOperator
    value: Union[int, float, str, bool, List]


class EntryConditions(BaseModel):
    logic: ConditionLogic = ConditionLogic.AND
    custom_expression: Optional[str] = None
    conditions: List[Condition] = []


class SlippageProtection(BaseModel):
    enabled: bool = True
    max_per_leg_pct: float = 2.0
    max_total_pct: float = 5.0
    on_exceed: str = "retry"
    max_retries: int = 3


class OrderSettings(BaseModel):
    order_type: OrderType = OrderType.MARKET
    execution_style: ExecutionStyle = ExecutionStyle.sequential
    leg_sequence: List[str] = []
    delay_between_legs: int = 2
    slippage_protection: SlippageProtection = SlippageProtection()
    on_leg_failure: str = "stop"


class TrailingStop(BaseModel):
    enabled: bool = False
    trigger_profit: Optional[Decimal] = None
    trail_amount: Optional[Decimal] = None


class RiskSettings(BaseModel):
    max_loss: Optional[Decimal] = None
    max_loss_pct: Optional[float] = None
    trailing_stop: TrailingStop = TrailingStop()
    max_margin: Optional[Decimal] = None
    time_stop: Optional[str] = None


class ScheduleConfig(BaseModel):
    activation_mode: str = "always"
    active_days: List[str] = ["MON", "TUE", "WED", "THU", "FRI"]
    start_time: str = "09:15"
    end_time: str = "15:30"
    expiry_days_only: bool = False
    date_range: Optional[Dict[str, str]] = None


# Request Schemas
class StrategyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    underlying: Underlying
    expiry_type: ExpiryType = ExpiryType.current_week
    expiry_date: Optional[date] = None
    lots: int = Field(1, ge=1, le=50)
    position_type: PositionType = PositionType.intraday
    legs_config: List[LegConfig] = Field(..., min_length=1, max_length=20)
    entry_conditions: EntryConditions
    adjustment_rules: List[Dict[str, Any]] = []
    order_settings: Optional[OrderSettings] = None
    risk_settings: Optional[RiskSettings] = None
    schedule_config: Optional[ScheduleConfig] = None
    priority: int = Field(100, ge=1, le=1000)
    source_template_id: Optional[int] = None

    @field_validator('legs_config')
    @classmethod
    def validate_unique_leg_ids(cls, v):
        ids = [leg.id for leg in v]
        if len(ids) != len(set(ids)):
            raise ValueError('Leg IDs must be unique')
        return v


class StrategyUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    lots: Optional[int] = Field(None, ge=1, le=50)
    legs_config: Optional[List[LegConfig]] = None
    entry_conditions: Optional[EntryConditions] = None
    adjustment_rules: Optional[List[Dict[str, Any]]] = None
    order_settings: Optional[OrderSettings] = None
    risk_settings: Optional[RiskSettings] = None
    schedule_config: Optional[ScheduleConfig] = None
    priority: Optional[int] = Field(None, ge=1, le=1000)


class ActivateRequest(BaseModel):
    confirm: bool = True
    paper_trading: bool = False


class ExitRequest(BaseModel):
    confirm: bool = True
    exit_type: str = "market"
    reason: Optional[str] = None


class CloneRequest(BaseModel):
    new_name: Optional[str] = None
    reset_schedule: bool = True


# Response Schemas
class StrategyListItem(BaseModel):
    id: int
    name: str
    status: StrategyStatus
    underlying: Underlying
    lots: int
    leg_count: int
    current_pnl: Optional[Decimal] = None
    margin_used: Optional[Decimal] = None
    priority: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyResponse(BaseModel):
    id: int
    user_id: UUID
    name: str
    description: Optional[str]
    status: StrategyStatus
    underlying: Underlying
    expiry_type: str
    expiry_date: Optional[date]
    lots: int
    position_type: PositionType
    legs_config: List[Dict[str, Any]]
    entry_conditions: Dict[str, Any]
    adjustment_rules: List[Dict[str, Any]]
    order_settings: Dict[str, Any]
    risk_settings: Dict[str, Any]
    schedule_config: Dict[str, Any]
    priority: int
    runtime_state: Optional[Dict[str, Any]]
    version: int
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# User Settings Schemas
class UserSettingsResponse(BaseModel):
    daily_loss_limit: Decimal
    per_strategy_loss_limit: Decimal
    max_capital_deployed: Decimal
    max_active_strategies: int
    no_trade_first_minutes: int
    no_trade_last_minutes: int
    cooldown_after_loss: bool
    cooldown_minutes: int
    cooldown_threshold: Decimal
    default_order_settings: Dict[str, Any]
    notification_prefs: Dict[str, Any]
    failure_handling: Dict[str, Any]
    paper_trading_mode: bool
    show_advanced_features: bool
    # Phase 3 fields
    kill_switch_enabled: bool = False
    kill_switch_triggered_at: Optional[datetime] = None
    default_execution_mode: ExecutionMode = ExecutionMode.auto
    confirmation_timeout_seconds: int = 30
    auto_exit_time: Optional[str] = "15:15"
    account_capital: Optional[Decimal] = None
    risk_per_trade_pct: Optional[Decimal] = None

    class Config:
        from_attributes = True


class UserSettingsUpdateRequest(BaseModel):
    daily_loss_limit: Optional[Decimal] = None
    per_strategy_loss_limit: Optional[Decimal] = None
    max_capital_deployed: Optional[Decimal] = None
    max_active_strategies: Optional[int] = Field(None, ge=1, le=10)
    no_trade_first_minutes: Optional[int] = Field(None, ge=0, le=60)
    no_trade_last_minutes: Optional[int] = Field(None, ge=0, le=60)
    cooldown_after_loss: Optional[bool] = None
    cooldown_minutes: Optional[int] = Field(None, ge=5, le=240)
    cooldown_threshold: Optional[Decimal] = None
    default_order_settings: Optional[Dict[str, Any]] = None
    notification_prefs: Optional[Dict[str, Any]] = None
    failure_handling: Optional[Dict[str, Any]] = None
    paper_trading_mode: Optional[bool] = None
    show_advanced_features: Optional[bool] = None
    # Phase 3 fields
    default_execution_mode: Optional[ExecutionMode] = None
    confirmation_timeout_seconds: Optional[int] = Field(None, ge=10, le=300)
    auto_exit_time: Optional[str] = None
    account_capital: Optional[Decimal] = None
    risk_per_trade_pct: Optional[Decimal] = Field(None, gt=0, le=100)


# Dashboard Schemas
class RiskMetrics(BaseModel):
    daily_loss_limit: Decimal
    daily_loss_used: Decimal
    daily_loss_pct: float
    max_capital: Decimal
    capital_used: Decimal
    capital_pct: float
    max_active_strategies: int
    active_strategies_count: int
    status: str  # safe | warning | critical


class DashboardSummary(BaseModel):
    active_strategies: int
    waiting_strategies: int
    pending_confirmations: int
    today_realized_pnl: Decimal
    today_unrealized_pnl: Decimal
    today_total_pnl: Decimal
    risk_metrics: RiskMetrics
    strategies: List[StrategyListItem]
    kite_connected: bool
    websocket_connected: bool
    last_update: datetime


# Generic Response Wrapper
class DataResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    data: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    status: str = "success"
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Phase 3 Schemas
# =============================================================================

# Kill Switch Schemas
class KillSwitchStatus(BaseModel):
    """Current kill switch status"""
    enabled: bool
    triggered_at: Optional[datetime] = None
    affected_strategies: int = 0
    can_reset: bool = True


class KillSwitchTriggerRequest(BaseModel):
    """Request to trigger kill switch"""
    reason: Optional[str] = None
    force: bool = False


class KillSwitchTriggerResponse(BaseModel):
    """Response after triggering kill switch"""
    success: bool
    strategies_affected: int
    positions_exited: int
    orders_placed: List[int] = []
    triggered_at: datetime
    message: str


class KillSwitchResetRequest(BaseModel):
    """Request to reset kill switch"""
    confirm: bool = True


# Adjustment Rule Schemas
class AdjustmentTrigger(BaseModel):
    """Trigger configuration for adjustment rule"""
    type: AdjustmentTriggerType
    condition: str  # 'loss_exceeds', 'profit_exceeds', 'delta_exceeds', etc.
    value: Union[int, float, str, List]


class AdjustmentAction(BaseModel):
    """Action configuration for adjustment rule"""
    type: AdjustmentActionType
    params: Dict[str, Any] = {}


class AdjustmentRule(BaseModel):
    """Complete adjustment rule configuration"""
    id: str
    enabled: bool = True
    name: str
    trigger: AdjustmentTrigger
    action: AdjustmentAction
    execution_mode: ExecutionMode = ExecutionMode.auto
    max_executions: Optional[int] = None
    cooldown_seconds: int = 0


class AdjustmentLogResponse(BaseModel):
    """Adjustment log entry response"""
    id: int
    strategy_id: int
    rule_id: str
    rule_name: str
    trigger_type: AdjustmentTriggerType
    trigger_condition: str
    trigger_value: Any
    actual_value: Any
    action_type: AdjustmentActionType
    action_params: Dict[str, Any]
    execution_mode: ExecutionMode
    executed: bool
    execution_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    confirmed_by_user: Optional[bool] = None
    triggered_at: datetime
    executed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ManualAdjustmentRequest(BaseModel):
    """Request to manually trigger an adjustment"""
    rule_id: str
    force: bool = False


# Confirmation Schemas
class PendingConfirmationResponse(BaseModel):
    """Pending confirmation response"""
    id: int
    strategy_id: int
    strategy_name: str
    action_type: str
    action_description: str
    action_data: Dict[str, Any]
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    status: ConfirmationStatus
    timeout_seconds: int
    expires_at: datetime
    time_remaining_seconds: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConfirmationActionRequest(BaseModel):
    """Request to confirm or reject a confirmation"""
    action: str = Field(..., pattern="^(confirm|reject)$")


class ConfirmationActionResponse(BaseModel):
    """Response after confirming or rejecting"""
    success: bool
    confirmation_id: int
    action_taken: str
    execution_result: Optional[Dict[str, Any]] = None
    orders_placed: List[int] = []
    message: str


# Trailing Stop Schemas
class TrailingStopConfig(BaseModel):
    """Trailing stop configuration"""
    enabled: bool = False
    activation_profit: Optional[Decimal] = None
    trail_distance: Optional[Decimal] = None
    trail_type: TrailType = TrailType.fixed
    min_profit_lock: Optional[Decimal] = None


class TrailingStopStatus(BaseModel):
    """Current trailing stop status for a strategy"""
    enabled: bool
    active: bool = False
    high_water_mark: Optional[Decimal] = None
    current_stop_level: Optional[Decimal] = None
    current_pnl: Optional[Decimal] = None
    distance_to_stop: Optional[Decimal] = None


# Position Sizing Schemas
class PositionSizingRequest(BaseModel):
    """Request to calculate position size"""
    underlying: Underlying
    strategy_type: Optional[str] = None
    legs_config: Optional[List[Dict[str, Any]]] = None
    max_loss_per_lot: Optional[Decimal] = None


class PositionSizingResponse(BaseModel):
    """Position sizing calculation response"""
    recommended_lots: int
    max_loss_amount: Decimal
    risk_per_trade: Decimal
    account_capital: Decimal
    vix_adjusted: bool = False
    calculation_details: Dict[str, Any] = {}


# Greeks Schemas
class GreeksSnapshot(BaseModel):
    """Greeks for a position"""
    delta: float
    gamma: float
    theta: float
    vega: float
    calculated_at: datetime


class PositionGreeksResponse(BaseModel):
    """Complete Greeks for strategy position"""
    strategy_id: int
    net_delta: float
    net_gamma: float
    net_theta: float
    net_vega: float
    legs: List[Dict[str, Any]] = []  # Per-leg Greeks
    calculated_at: datetime


# Strategy Response with Phase 3 fields
class StrategyResponseWithPhase3(BaseModel):
    """Extended strategy response with Phase 3 fields"""
    id: int
    user_id: UUID
    name: str
    description: Optional[str]
    status: StrategyStatus
    underlying: Underlying
    expiry_type: str
    expiry_date: Optional[date]
    lots: int
    position_type: PositionType
    legs_config: List[Dict[str, Any]]
    entry_conditions: Dict[str, Any]
    adjustment_rules: List[Dict[str, Any]]
    order_settings: Dict[str, Any]
    risk_settings: Dict[str, Any]
    schedule_config: Dict[str, Any]
    priority: int
    runtime_state: Optional[Dict[str, Any]]
    version: int
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime]
    completed_at: Optional[datetime]
    # Phase 3 fields
    execution_mode: Optional[ExecutionMode] = None
    trailing_stop_config: Optional[Dict[str, Any]] = None
    greeks_snapshot: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Dashboard with Kill Switch status
class DashboardSummaryWithKillSwitch(BaseModel):
    """Dashboard summary with kill switch status"""
    active_strategies: int
    waiting_strategies: int
    pending_confirmations: int
    today_realized_pnl: Decimal
    today_unrealized_pnl: Decimal
    today_total_pnl: Decimal
    risk_metrics: RiskMetrics
    strategies: List[StrategyListItem]
    kite_connected: bool
    websocket_connected: bool
    last_update: datetime
    # Phase 3 fields
    kill_switch_enabled: bool = False
    kill_switch_triggered_at: Optional[datetime] = None


# WebSocket Message Schemas
class WebSocketMessage(BaseModel):
    """Base WebSocket message"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConfirmationRequiredMessage(BaseModel):
    """WebSocket message for confirmation required"""
    type: str = "confirmation_required"
    confirmation_id: int
    strategy_id: int
    strategy_name: str
    action_type: str
    action_description: str
    expires_at: datetime
    timeout_seconds: int


class KillSwitchMessage(BaseModel):
    """WebSocket message for kill switch events"""
    type: str  # 'kill_switch_triggered' or 'kill_switch_reset'
    triggered_at: Optional[datetime] = None
    strategies_affected: int = 0
    reason: Optional[str] = None


class TrailingStopMessage(BaseModel):
    """WebSocket message for trailing stop events"""
    type: str  # 'trailing_stop_activated', 'trailing_stop_updated'
    strategy_id: int
    high_water_mark: Optional[Decimal] = None
    current_stop_level: Optional[Decimal] = None
    current_pnl: Optional[Decimal] = None


class AdjustmentMessage(BaseModel):
    """WebSocket message for adjustment events"""
    type: str  # 'adjustment_triggered', 'adjustment_executed'
    strategy_id: int
    rule_id: str
    rule_name: str
    action_type: str
    executed: bool = False
    execution_result: Optional[Dict[str, Any]] = None


# =============================================================================
# Phase 4 Enums
# =============================================================================

class ExitReason(str, Enum):
    target_hit = "target_hit"
    stop_loss = "stop_loss"
    trailing_stop = "trailing_stop"
    time_exit = "time_exit"
    manual_exit = "manual_exit"
    adjustment_exit = "adjustment_exit"
    kill_switch = "kill_switch"
    auto_exit = "auto_exit"
    error = "error"


class TemplateCategory(str, Enum):
    income = "income"
    directional = "directional"
    volatility = "volatility"
    hedging = "hedging"
    advanced = "advanced"
    custom = "custom"


class ReportType(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    custom = "custom"
    strategy = "strategy"
    tax = "tax"


class ReportFormat(str, Enum):
    pdf = "pdf"
    excel = "excel"
    csv = "csv"


class BacktestStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ShareMode(str, Enum):
    private = "private"
    link = "link"
    public = "public"


class MarketOutlook(str, Enum):
    bullish = "bullish"
    bearish = "bearish"
    neutral = "neutral"
    volatile = "volatile"


class IVEnvironment(str, Enum):
    high = "high"
    low = "low"
    normal = "normal"


# =============================================================================
# Phase 4 Schemas - Strategy Templates
# =============================================================================

class TemplateEducationalContent(BaseModel):
    """Educational content for templates"""
    when_to_use: Optional[str] = None
    pros: Optional[List[str]] = []
    cons: Optional[List[str]] = []
    common_mistakes: Optional[List[str]] = []
    exit_rules: Optional[List[str]] = []
    adjustments: Optional[List[str]] = []


class TemplateListItem(BaseModel):
    """Template list item for browsing"""
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    underlying: Optional[str]
    position_type: Optional[str]
    risk_level: Optional[str]
    market_outlook: Optional[str]
    iv_environment: Optional[str]
    expected_return_pct: Optional[Decimal]
    max_risk_pct: Optional[Decimal]
    usage_count: int
    avg_rating: Optional[Decimal]
    rating_count: int
    is_system: bool
    is_public: bool
    tags: List[str] = []
    thumbnail_url: Optional[str] = None
    author_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateResponse(BaseModel):
    """Full template response"""
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    underlying: Optional[str]
    position_type: Optional[str]
    risk_level: Optional[str]
    market_outlook: Optional[str]
    iv_environment: Optional[str]
    expected_return_pct: Optional[Decimal]
    max_risk_pct: Optional[Decimal]
    usage_count: int
    avg_rating: Optional[Decimal]
    rating_count: int
    is_system: bool
    is_public: bool
    tags: List[str] = []
    thumbnail_url: Optional[str] = None
    author_name: Optional[str] = None
    strategy_config: Dict[str, Any]
    educational_content: Optional[Dict[str, Any]] = None
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateCreateRequest(BaseModel):
    """Request to create a template"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = None
    underlying: Optional[str] = None
    position_type: Optional[str] = None
    risk_level: Optional[str] = None
    market_outlook: Optional[str] = None
    iv_environment: Optional[str] = None
    expected_return_pct: Optional[Decimal] = None
    max_risk_pct: Optional[Decimal] = None
    tags: List[str] = []
    strategy_config: Dict[str, Any]
    educational_content: Optional[Dict[str, Any]] = None
    is_public: bool = False


class TemplateUpdateRequest(BaseModel):
    """Request to update a template"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = None
    risk_level: Optional[str] = None
    market_outlook: Optional[str] = None
    iv_environment: Optional[str] = None
    expected_return_pct: Optional[Decimal] = None
    max_risk_pct: Optional[Decimal] = None
    tags: Optional[List[str]] = None
    strategy_config: Optional[Dict[str, Any]] = None
    educational_content: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None


class TemplateDeployRequest(BaseModel):
    """Request to deploy a template as a strategy"""
    name: Optional[str] = None  # Override template name
    lots: int = Field(1, ge=1, le=50)
    expiry_type: Optional[str] = None
    expiry_date: Optional[date] = None
    execution_mode: Optional[ExecutionMode] = None
    activate_immediately: bool = False


class TemplateRatingRequest(BaseModel):
    """Request to rate a template"""
    rating: int = Field(..., ge=1, le=5)
    review: Optional[str] = Field(None, max_length=1000)


class TemplateRatingResponse(BaseModel):
    """Template rating response"""
    id: int
    template_id: int
    user_id: UUID
    rating: int
    review: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Phase 4 Schemas - Trade Journal
# =============================================================================

class MarketConditions(BaseModel):
    """Market conditions at trade time"""
    vix_at_entry: Optional[float] = None
    vix_at_exit: Optional[float] = None
    spot_at_entry: Optional[Decimal] = None
    spot_at_exit: Optional[Decimal] = None
    iv_rank: Optional[float] = None
    trend_direction: Optional[str] = None


class TradeJournalLegSnapshot(BaseModel):
    """Snapshot of a leg at trade time"""
    leg_id: str
    contract_type: str
    transaction_type: str
    strike: Decimal
    expiry: date
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    quantity: int


class TradeJournalListItem(BaseModel):
    """Trade journal list item"""
    id: int
    strategy_id: Optional[int]
    strategy_name: str
    underlying: str
    position_type: str
    entry_time: datetime
    exit_time: Optional[datetime]
    holding_duration_minutes: Optional[int]
    lots: int
    gross_pnl: Optional[Decimal]
    net_pnl: Optional[Decimal]
    pnl_percentage: Optional[Decimal]
    exit_reason: Optional[str]
    tags: List[str] = []
    is_open: bool

    class Config:
        from_attributes = True


class TradeJournalResponse(BaseModel):
    """Full trade journal entry response"""
    id: int
    user_id: UUID
    strategy_id: Optional[int]
    strategy_name: str
    underlying: str
    position_type: str
    entry_time: datetime
    exit_time: Optional[datetime]
    holding_duration_minutes: Optional[int]
    legs: List[Dict[str, Any]]
    lots: int
    total_quantity: int
    entry_premium: Optional[Decimal]
    exit_premium: Optional[Decimal]
    gross_pnl: Optional[Decimal]
    brokerage: Optional[Decimal]
    taxes: Optional[Decimal]
    other_charges: Optional[Decimal]
    net_pnl: Optional[Decimal]
    pnl_percentage: Optional[Decimal]
    max_profit_reached: Optional[Decimal]
    max_loss_reached: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    exit_reason: Optional[str]
    market_conditions: Optional[Dict[str, Any]]
    notes: Optional[str]
    tags: List[str] = []
    screenshots: List[str] = []
    entry_order_ids: List[int] = []
    exit_order_ids: List[int] = []
    is_open: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TradeJournalUpdateRequest(BaseModel):
    """Request to update trade journal entry (notes/tags)"""
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class TradeJournalExportRequest(BaseModel):
    """Request to export trade journal"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    underlying: Optional[str] = None
    exit_reason: Optional[str] = None
    format: ReportFormat = ReportFormat.csv


# =============================================================================
# Phase 4 Schemas - Analytics
# =============================================================================

class PerformanceMetrics(BaseModel):
    """Performance metrics"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_pnl: Decimal
    net_pnl: Decimal
    total_brokerage: Decimal
    avg_win: Optional[Decimal] = None
    avg_loss: Optional[Decimal] = None
    profit_factor: Optional[float] = None
    max_drawdown: Optional[Decimal] = None
    max_drawdown_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    expectancy: Optional[Decimal] = None


class DailyPnL(BaseModel):
    """Daily P&L data point"""
    date: date
    pnl: Decimal
    trades: int
    cumulative_pnl: Decimal


class WeeklyPnL(BaseModel):
    """Weekly P&L data point"""
    week_start: date
    week_end: date
    pnl: Decimal
    trades: int


class MonthlyPnL(BaseModel):
    """Monthly P&L data point"""
    year: int
    month: int
    pnl: Decimal
    trades: int


class StrategyPerformance(BaseModel):
    """Performance by strategy"""
    strategy_name: str
    underlying: str
    trades: int
    win_rate: float
    pnl: Decimal
    avg_holding_minutes: Optional[int] = None


class WeekdayPerformance(BaseModel):
    """Performance by weekday"""
    weekday: str
    trades: int
    pnl: Decimal
    win_rate: float


class AnalyticsSummary(BaseModel):
    """Analytics summary response"""
    period: str  # '30d', '90d', 'ytd', 'all'
    start_date: date
    end_date: date
    performance: PerformanceMetrics
    best_trade: Optional[Decimal] = None
    worst_trade: Optional[Decimal] = None
    avg_trade_pnl: Optional[Decimal] = None
    avg_holding_minutes: Optional[int] = None
    most_traded_underlying: Optional[str] = None
    most_profitable_strategy: Optional[str] = None


class AnalyticsPerformanceResponse(BaseModel):
    """Full analytics performance response"""
    summary: AnalyticsSummary
    daily_pnl: List[DailyPnL] = []
    weekly_pnl: List[WeeklyPnL] = []
    monthly_pnl: List[MonthlyPnL] = []
    by_strategy: List[StrategyPerformance] = []
    by_underlying: List[Dict[str, Any]] = []
    by_weekday: List[WeekdayPerformance] = []


# =============================================================================
# Phase 4 Schemas - Reports
# =============================================================================

class ReportListItem(BaseModel):
    """Report list item"""
    id: int
    report_type: str
    name: str
    description: Optional[str]
    start_date: date
    end_date: date
    format: Optional[str]
    is_ready: bool
    file_size_bytes: Optional[int]
    created_at: datetime
    generated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    """Full report response"""
    id: int
    user_id: UUID
    report_type: str
    name: str
    description: Optional[str]
    start_date: date
    end_date: date
    strategy_id: Optional[int]
    report_data: Dict[str, Any]
    format: Optional[str]
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    is_ready: bool
    error_message: Optional[str]
    created_at: datetime
    generated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReportGenerateRequest(BaseModel):
    """Request to generate a report"""
    report_type: ReportType
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: date
    end_date: date
    strategy_id: Optional[int] = None
    format: ReportFormat = ReportFormat.pdf


class TaxSummary(BaseModel):
    """Tax summary for a financial year"""
    financial_year: str  # '2024-25'
    total_turnover: Decimal
    speculative_pnl: Decimal  # Intraday equity
    non_speculative_pnl: Decimal  # F&O
    total_brokerage: Decimal
    total_taxes_paid: Decimal
    net_taxable_income: Decimal
    audit_required: bool  # Turnover > threshold


# =============================================================================
# Phase 4 Schemas - Backtests
# =============================================================================

class BacktestListItem(BaseModel):
    """Backtest list item"""
    id: int
    name: str
    description: Optional[str]
    start_date: date
    end_date: date
    initial_capital: Decimal
    status: str
    progress_pct: int
    total_trades: Optional[int]
    win_rate: Optional[Decimal]
    net_pnl: Optional[Decimal]
    max_drawdown_pct: Optional[Decimal]
    sharpe_ratio: Optional[Decimal]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class BacktestResponse(BaseModel):
    """Full backtest response"""
    id: int
    user_id: UUID
    name: str
    description: Optional[str]
    strategy_config: Dict[str, Any]
    start_date: date
    end_date: date
    initial_capital: Decimal
    slippage_pct: Decimal
    charges_per_lot: Decimal
    data_interval: str
    status: str
    progress_pct: int
    error_message: Optional[str]
    results: Optional[Dict[str, Any]]
    total_trades: Optional[int]
    winning_trades: Optional[int]
    losing_trades: Optional[int]
    win_rate: Optional[Decimal]
    gross_pnl: Optional[Decimal]
    net_pnl: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    max_drawdown_pct: Optional[Decimal]
    sharpe_ratio: Optional[Decimal]
    profit_factor: Optional[Decimal]
    equity_curve: List[Dict[str, Any]] = []
    trades: List[Dict[str, Any]] = []
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class BacktestCreateRequest(BaseModel):
    """Request to create a backtest"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    strategy_config: Dict[str, Any]
    start_date: date
    end_date: date
    initial_capital: Decimal = Field(500000, gt=0)
    slippage_pct: Decimal = Field(0.1, ge=0, le=5)
    charges_per_lot: Decimal = Field(40, ge=0)
    data_interval: str = "1min"


# =============================================================================
# Phase 4 Schemas - Strategy Sharing
# =============================================================================

class StrategyShareRequest(BaseModel):
    """Request to share a strategy"""
    share_mode: ShareMode = ShareMode.link


class StrategyShareResponse(BaseModel):
    """Response after sharing a strategy"""
    share_token: str
    share_url: str
    share_mode: str
    shared_at: datetime


class SharedStrategyResponse(BaseModel):
    """Public view of a shared strategy"""
    id: int
    name: str
    description: Optional[str]
    underlying: str
    position_type: str
    legs_config: List[Dict[str, Any]]
    entry_conditions: Dict[str, Any]
    adjustment_rules: List[Dict[str, Any]]
    risk_settings: Dict[str, Any]
    author_name: Optional[str] = None
    shared_at: datetime
    # Performance stats if shared
    performance_stats: Optional[Dict[str, Any]] = None


class StrategyCloneFromSharedRequest(BaseModel):
    """Request to clone a shared strategy"""
    new_name: Optional[str] = None
    lots: int = Field(1, ge=1, le=50)


# =============================================================================
# Phase 5 Schemas - Advanced Adjustments & Option Chain Integration
# =============================================================================

# Position Leg Schemas

class PositionLegBase(BaseModel):
    """Base schema for position leg"""
    leg_id: str
    contract_type: str = Field(..., pattern="^(CE|PE)$")
    action: str = Field(..., pattern="^(BUY|SELL)$")
    strike: Decimal
    expiry: date
    lots: int = Field(..., gt=0)
    tradingsymbol: Optional[str] = None
    instrument_token: Optional[int] = None


class PositionLegCreate(PositionLegBase):
    """Create position leg"""
    entry_price: Optional[Decimal] = None


class PositionLegUpdate(BaseModel):
    """Update position leg"""
    status: Optional[str] = None
    entry_price: Optional[Decimal] = None
    entry_time: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    delta: Optional[Decimal] = None
    gamma: Optional[Decimal] = None
    theta: Optional[Decimal] = None
    vega: Optional[Decimal] = None
    iv: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None


class PositionLegResponse(PositionLegBase):
    """Response schema for position leg"""
    id: int
    strategy_id: int
    status: str
    entry_price: Optional[Decimal]
    entry_time: Optional[datetime]
    entry_order_ids: List[str] = []
    exit_price: Optional[Decimal]
    exit_time: Optional[datetime]
    exit_order_ids: List[str] = []
    exit_reason: Optional[str]
    delta: Optional[Decimal]
    gamma: Optional[Decimal]
    theta: Optional[Decimal]
    vega: Optional[Decimal]
    iv: Optional[Decimal]
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    rolled_from_leg_id: Optional[int]
    rolled_to_leg_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Adjustment Suggestion Schemas

class AdjustmentSuggestionBase(BaseModel):
    """Base schema for adjustment suggestion"""
    leg_id: Optional[str] = None
    trigger_reason: str
    suggestion_type: str
    description: str
    details: Optional[Dict[str, Any]] = None
    urgency: str = "medium"
    confidence: int = Field(50, ge=0, le=100)
    category: str = "defensive"  # defensive, offensive, neutral (Phase 5H Feature #45)
    one_click_action: bool = False
    action_params: Optional[Dict[str, Any]] = None


class AdjustmentSuggestionCreate(AdjustmentSuggestionBase):
    """Create adjustment suggestion"""
    expires_at: Optional[datetime] = None


class AdjustmentSuggestionResponse(AdjustmentSuggestionBase):
    """Response schema for adjustment suggestion"""
    id: int
    strategy_id: int
    status: str
    created_at: datetime
    expires_at: Optional[datetime]
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True


# Option Chain Schemas

class OptionChainEntry(BaseModel):
    """Single option in the chain"""
    instrument_token: int
    tradingsymbol: str
    strike: Decimal
    option_type: str
    expiry: date
    ltp: Optional[Decimal]
    bid: Optional[Decimal]
    ask: Optional[Decimal]
    volume: Optional[int]
    oi: Optional[int]
    oi_change: Optional[int]
    iv: Optional[Decimal]
    delta: Optional[Decimal]
    gamma: Optional[Decimal]
    theta: Optional[Decimal]
    vega: Optional[Decimal]


class OptionChainResponse(BaseModel):
    """Full option chain response"""
    underlying: str
    expiry: date
    spot_price: Optional[Decimal]
    options: List[OptionChainEntry]
    cached: bool = False
    cached_at: Optional[datetime] = None


class StrikeFindByDeltaRequest(BaseModel):
    """Request to find strike by delta"""
    underlying: str
    expiry: date
    option_type: str = Field(..., pattern="^(CE|PE)$")
    target_delta: Decimal = Field(..., ge=0, le=1)
    tolerance: Decimal = Field(0.02, ge=0, le=0.1)
    prefer_round_strike: bool = True


class StrikeFindByPremiumRequest(BaseModel):
    """Request to find strike by premium"""
    underlying: str
    expiry: date
    option_type: str = Field(..., pattern="^(CE|PE)$")
    target_premium: Decimal = Field(..., gt=0)
    tolerance: Decimal = Field(10, ge=0)
    prefer_round_strike: bool = True


class StrikeFindResponse(BaseModel):
    """Response for strike finder"""
    strike: Decimal
    tradingsymbol: str
    instrument_token: int
    ltp: Optional[Decimal]
    delta: Optional[Decimal]
    iv: Optional[Decimal]
    distance_from_target: Decimal


# Leg Action Request Schemas

class ExitLegRequest(BaseModel):
    """Request to exit a single leg"""
    execution_mode: str = Field("market", pattern="^(market|limit)$")
    limit_price: Optional[Decimal] = None


class ShiftLegRequest(BaseModel):
    """Request to shift a leg to new strike"""
    target_strike: Optional[Decimal] = None
    target_delta: Optional[Decimal] = None
    shift_direction: Optional[str] = Field(None, pattern="^(closer|further)$")
    shift_amount: Optional[int] = None
    execution_mode: str = Field("market", pattern="^(market|limit)$")
    limit_offset: Decimal = Field(1.0, ge=0)


class RollLegRequest(BaseModel):
    """Request to roll a leg to new expiry"""
    target_expiry: date
    target_strike: Optional[Decimal] = None
    execution_mode: str = Field("market", pattern="^(market|limit)$")


class BreakTradeRequest(BaseModel):
    """Request to break/split trade"""
    execution_mode: str = Field("market", pattern="^(market|limit)$")
    new_positions: str = Field("auto", pattern="^(auto|manual)$")
    new_put_strike: Optional[Decimal] = None
    new_call_strike: Optional[Decimal] = None
    premium_split: str = Field("equal", pattern="^(equal|weighted)$")
    prefer_round_strikes: bool = True
    max_delta: Decimal = Field(0.30, ge=0, le=1)


class BreakTradeResponse(BaseModel):
    """Response for break trade"""
    break_trade_id: str
    exit_order: Dict[str, Any]
    new_positions: List[Dict[str, Any]]
    recovery_premium: Decimal
    exit_cost: Decimal
    net_cost: Decimal
    status: str


# What-If Simulator Schemas

class WhatIfScenario(BaseModel):
    """Scenario for what-if analysis"""
    spot_change: Optional[Decimal] = None
    iv_change: Optional[Decimal] = None
    days_forward: Optional[int] = None


class WhatIfRequest(BaseModel):
    """Request for what-if simulation"""
    strategy_id: int
    adjustment_type: str
    adjustment_params: Dict[str, Any]
    scenarios: List[WhatIfScenario] = []


class PositionMetrics(BaseModel):
    """Position metrics for comparison"""
    net_delta: Optional[Decimal]
    net_theta: Optional[Decimal]
    net_gamma: Optional[Decimal]
    net_vega: Optional[Decimal]
    max_profit: Optional[Decimal]
    max_loss: Optional[Decimal]
    breakeven_lower: Optional[Decimal]
    breakeven_upper: Optional[Decimal]
    current_pnl: Decimal


class WhatIfResponse(BaseModel):
    """Response for what-if simulation"""
    current_position: PositionMetrics
    after_adjustment: PositionMetrics
    comparison: Dict[str, Any]
    scenario_results: List[Dict[str, Any]] = []


# Payoff Chart Data Schema

class PayoffDataPoint(BaseModel):
    """Single point on payoff chart"""
    spot_price: Decimal
    pnl: Decimal
    is_breakeven: bool = False
    is_max_profit: bool = False
    is_max_loss: bool = False


class PayoffChartResponse(BaseModel):
    """Payoff chart data"""
    data_points: List[PayoffDataPoint]
    breakeven_points: List[Decimal]
    max_profit: Optional[Decimal]
    max_loss: Optional[Decimal]
    current_spot: Decimal
    current_pnl: Decimal


# ========== PHASE 5G: ANALYTICS & INTELLIGENCE ==========

class AdjustmentCategory(str, Enum):
    """
    Categorization of adjustment actions by risk impact (Phase 5G #45)

    OFFENSIVE: Increase risk to collect more premium
    DEFENSIVE: Reduce risk to protect capital
    NEUTRAL: Rebalance position without major risk change
    """
    offensive = "offensive"
    defensive = "defensive"
    neutral = "neutral"


class AdjustmentCostItem(BaseModel):
    """Single adjustment cost entry"""
    timestamp: datetime
    order_id: int
    action_type: str
    cost: Decimal
    reason: str
    status: str


class AdjustmentCostSummary(BaseModel):
    """
    Summary of adjustment costs for a strategy (Phase 5G #46)

    Tracks cumulative cost of adjustments relative to original premium.
    Professional traders avoid exceeding 50% of original premium in adjustment costs.
    """
    original_premium: Decimal = Field(..., description="Initial premium collected (credit strategies)")
    total_adjustment_cost: Decimal = Field(..., description="Sum of all adjustment costs")
    adjustment_cost_pct: float = Field(..., description="Cost as percentage of original premium")
    net_potential_profit: Decimal = Field(..., description="Original premium - adjustment costs")
    adjustments: List[AdjustmentCostItem] = Field(default_factory=list, description="List of adjustments")
    warning_threshold_pct: float = Field(default=50.0, description="Warning threshold percentage")
    alert_level: str = Field(..., description="success | info | warning | danger")
    alert_message: str = Field(..., description="Human-readable alert message")


class AdjustmentCostThresholdCheck(BaseModel):
    """Result of checking adjustment cost threshold"""
    threshold_exceeded: bool
    current_pct: float
    threshold_pct: float
    alert_level: str
    alert_message: str
    recommendation: str


class GreekConditionVariable(str, Enum):
    """Greek variables for entry/exit conditions (Phase 5G)"""
    STRATEGY_DELTA = "STRATEGY.DELTA"
    STRATEGY_GAMMA = "STRATEGY.GAMMA"
    STRATEGY_THETA = "STRATEGY.THETA"
    STRATEGY_VEGA = "STRATEGY.VEGA"


# =============================================================================
# Phase 5I Schemas - Staged Entry (Half-Size & Staggered Entry)
# =============================================================================

class StagedEntryMode(str, Enum):
    """
    Entry mode for staged strategies (Phase 5I #12, #13)

    half_size: Start with 50% position, add remaining when conditions met
    staggered: Enter legs at different times based on independent conditions
    """
    half_size = "half_size"
    staggered = "staggered"


class HalfSizeStageConfig(BaseModel):
    """Configuration for half-size entry stage"""
    legs: List[str] = Field(["all"], description="Leg IDs to enter (or 'all' for all legs)")
    lots_multiplier: float = Field(0.5, ge=0.1, le=1.0, description="Lot size multiplier (0.5 = 50%)")


class HalfSizeAddCondition(BaseModel):
    """Condition for adding remaining position in half-size entry"""
    condition: Condition = Field(..., description="Condition to trigger adding remaining position")
    lots_multiplier: float = Field(0.5, ge=0.1, le=1.0, description="Additional lot size multiplier")


class HalfSizeEntryConfig(BaseModel):
    """
    Configuration for half-size entry strategy (Phase 5I #12)

    Example: Start with 50% position on CE side, add remaining when spot rallies 1%
    """
    mode: StagedEntryMode = StagedEntryMode.half_size
    initial_stage: HalfSizeStageConfig = Field(..., description="Initial entry configuration")
    add_stage: HalfSizeAddCondition = Field(..., description="Add condition configuration")


class StaggeredLegEntry(BaseModel):
    """Single leg entry configuration for staggered entry"""
    leg_ids: List[str] = Field(..., min_length=1, description="Leg IDs to enter in this stage")
    condition: Optional[Condition] = Field(None, description="Entry condition (None = immediate entry)")
    lots_multiplier: float = Field(1.0, ge=0.1, le=1.0, description="Lot size multiplier")


class StaggeredEntryConfig(BaseModel):
    """
    Configuration for staggered entry strategy (Phase 5I #13)

    Example: Enter PE side at 9:20 AM, enter CE side when VIX < 15
    """
    mode: StagedEntryMode = StagedEntryMode.staggered
    leg_entries: List[StaggeredLegEntry] = Field(..., min_length=1, description="Leg entry configurations")


class StagedEntryConfig(BaseModel):
    """
    Base configuration for staged entry strategies (Phase 5I)

    Supports both half-size and staggered entry modes.
    """
    enabled: bool = Field(True, description="Enable staged entry")
    mode: StagedEntryMode = Field(..., description="Entry mode: half_size or staggered")
    config: Union[HalfSizeEntryConfig, StaggeredEntryConfig] = Field(
        ...,
        description="Mode-specific configuration"
    )


class StagedEntryStatus(BaseModel):
    """
    Current status of staged entry for display in UI
    """
    mode: Optional[StagedEntryMode] = None
    current_stage: int = Field(0, description="Current stage number (0 = not started)")
    total_stages: int = Field(0, description="Total number of stages")
    entered_legs: List[str] = Field(default_factory=list, description="Leg IDs that have been entered")
    pending_legs: List[str] = Field(default_factory=list, description="Leg IDs pending entry")
    next_condition: Optional[Dict[str, Any]] = Field(None, description="Next condition to be met")
    progress_pct: float = Field(0.0, ge=0, le=100, description="Overall progress percentage")


class StagedEntryProgressUpdate(BaseModel):
    """WebSocket message for staged entry progress updates"""
    type: str = "staged_entry_progress"
    strategy_id: int
    stage: int
    legs_entered: List[str] = []
    is_complete: bool = False
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StagedEntryCreateRequest(BaseModel):
    """Request to create a strategy with staged entry"""
    # Include all fields from StrategyCreateRequest
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    underlying: Underlying
    expiry_type: ExpiryType = ExpiryType.current_week
    expiry_date: Optional[date] = None
    lots: int = Field(1, ge=1, le=50)
    position_type: PositionType = PositionType.intraday
    legs_config: List[LegConfig] = Field(..., min_length=1, max_length=20)
    entry_conditions: EntryConditions
    adjustment_rules: List[Dict[str, Any]] = []
    order_settings: Optional[OrderSettings] = None
    risk_settings: Optional[RiskSettings] = None
    schedule_config: Optional[ScheduleConfig] = None
    priority: int = Field(100, ge=1, le=1000)
    source_template_id: Optional[int] = None
    # Phase 5I addition
    staged_entry_config: Optional[StagedEntryConfig] = Field(
        None,
        description="Staged entry configuration (half-size or staggered)"
    )
