"""
AutoPilot Pydantic Schemas

Reference: docs/autopilot/api-contracts.md
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
    active = "active"
    pending = "pending"
    paused = "paused"
    completed = "completed"
    error = "error"
    expired = "expired"


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


# Nested Models
class StrikeSelection(BaseModel):
    mode: str = Field(..., description="fixed | atm_offset | premium_based | delta_based")
    offset: Optional[int] = None
    fixed_strike: Optional[Decimal] = None
    target_premium: Optional[Decimal] = None
    target_delta: Optional[float] = None


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
