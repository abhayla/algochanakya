# AutoPilot API Contracts

## FastAPI Endpoint Definitions & Request/Response Schemas

**Version:** 1.0  
**Date:** December 2025  
**Framework:** FastAPI + Pydantic v2  
**Base URL:** `https://api.algochanakya.com/api/v1`

---

## Table of Contents

1. [API Overview](#1-api-overview)
2. [Authentication](#2-authentication)
3. [Common Models](#3-common-models)
4. [Strategy Endpoints](#4-strategy-endpoints)
5. [Dashboard Endpoints](#5-dashboard-endpoints)
6. [Order Endpoints](#6-order-endpoints)
7. [Log Endpoints](#7-log-endpoints)
8. [Settings Endpoints](#8-settings-endpoints)
9. [Template Endpoints](#9-template-endpoints)
10. [WebSocket Events](#10-websocket-events)
11. [Error Handling](#11-error-handling)
12. [TypeScript Interfaces](#12-typescript-interfaces)
13. [Example Requests](#13-example-requests)

---

## 1. API Overview

### 1.1 Endpoint Summary

| Category | Endpoints | Description |
|----------|-----------|-------------|
| Strategies | 12 | CRUD + lifecycle control |
| Dashboard | 4 | Overview, activity, risk |
| Orders | 3 | Order history & details |
| Logs | 3 | Activity logs & export |
| Settings | 2 | User settings |
| Templates | 5 | Strategy templates |
| Emergency | 1 | Kill switch |
| WebSocket | 1 | Real-time updates |

### 1.2 Base Configuration

```python
# app/api/v1/router.py

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")

# Include all routers
api_router.include_router(autopilot_strategies.router, prefix="/autopilot", tags=["AutoPilot - Strategies"])
api_router.include_router(autopilot_dashboard.router, prefix="/autopilot", tags=["AutoPilot - Dashboard"])
api_router.include_router(autopilot_orders.router, prefix="/autopilot", tags=["AutoPilot - Orders"])
api_router.include_router(autopilot_logs.router, prefix="/autopilot", tags=["AutoPilot - Logs"])
api_router.include_router(autopilot_settings.router, prefix="/autopilot", tags=["AutoPilot - Settings"])
api_router.include_router(autopilot_templates.router, prefix="/autopilot", tags=["AutoPilot - Templates"])
```

### 1.3 Endpoint Map

```
/api/v1/autopilot/
│
├── strategies/
│   ├── GET     /                           # List strategies
│   ├── POST    /                           # Create strategy
│   ├── GET     /{id}                       # Get strategy
│   ├── PUT     /{id}                       # Update strategy
│   ├── DELETE  /{id}                       # Delete strategy
│   ├── POST    /{id}/activate              # Activate strategy
│   ├── POST    /{id}/pause                 # Pause strategy
│   ├── POST    /{id}/resume                # Resume strategy
│   ├── POST    /{id}/exit                  # Force exit
│   ├── POST    /{id}/clone                 # Clone strategy
│   ├── GET     /{id}/conditions            # Get condition states
│   └── POST    /{id}/backtest              # Run backtest
│
├── dashboard/
│   ├── GET     /summary                    # Dashboard summary
│   ├── GET     /activity                   # Activity feed
│   ├── GET     /risk                       # Risk metrics
│   └── GET     /performance                # Performance stats
│
├── orders/
│   ├── GET     /                           # List orders
│   ├── GET     /{id}                       # Get order details
│   └── GET     /export                     # Export orders CSV
│
├── logs/
│   ├── GET     /                           # List logs
│   ├── GET     /{id}                       # Get log details
│   └── GET     /export                     # Export logs CSV
│
├── settings/
│   ├── GET     /                           # Get settings
│   └── PUT     /                           # Update settings
│
├── templates/
│   ├── GET     /                           # List templates
│   ├── POST    /                           # Create template
│   ├── GET     /{id}                       # Get template
│   ├── PUT     /{id}                       # Update template
│   └── DELETE  /{id}                       # Delete template
│
├── kill-switch/
│   └── POST    /                           # Emergency stop
│
└── ws/
    └── WS      /stream                     # WebSocket connection
```

---

## 2. Authentication

### 2.1 Authentication Dependency

```python
# app/api/dependencies/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate JWT token and return current user.
    
    Raises:
        HTTPException 401: Invalid or expired token
        HTTPException 403: User not active
    """
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user has active Kite session."""
    if not current_user.kite_access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kite session not active. Please login to Zerodha."
        )
    return current_user
```

### 2.2 Request Headers

```
Authorization: Bearer <jwt_token>
Content-Type: application/json
X-Request-ID: <uuid>  # Optional, for tracing
```

---

## 3. Common Models

### 3.1 Base Models

```python
# app/schemas/common.py

from datetime import datetime
from typing import Optional, List, Any, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

T = TypeVar('T')


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class BaseResponse(BaseModel):
    """Base response wrapper."""
    status: ResponseStatus = ResponseStatus.SUCCESS
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DataResponse(BaseResponse, Generic[T]):
    """Response with data payload."""
    data: T


class PaginatedResponse(BaseResponse, Generic[T]):
    """Paginated list response."""
    data: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ErrorDetail(BaseModel):
    """Detailed error information."""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    status: ResponseStatus = ResponseStatus.ERROR
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
```

### 3.2 Enums

```python
# app/schemas/enums.py

from enum import Enum


class StrategyStatus(str, Enum):
    DRAFT = "draft"
    WAITING = "waiting"
    ACTIVE = "active"
    PENDING = "pending"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    EXPIRED = "expired"


class Underlying(str, Enum):
    NIFTY = "NIFTY"
    BANKNIFTY = "BANKNIFTY"
    FINNIFTY = "FINNIFTY"
    SENSEX = "SENSEX"


class PositionType(str, Enum):
    INTRADAY = "intraday"
    POSITIONAL = "positional"


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


class OrderStatus(str, Enum):
    PENDING = "pending"
    PLACED = "placed"
    OPEN = "open"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ERROR = "error"


class OrderPurpose(str, Enum):
    ENTRY = "entry"
    ADJUSTMENT = "adjustment"
    HEDGE = "hedge"
    EXIT = "exit"
    ROLL_CLOSE = "roll_close"
    ROLL_OPEN = "roll_open"
    KILL_SWITCH = "kill_switch"


class ExecutionStyle(str, Enum):
    SIMULTANEOUS = "simultaneous"
    SEQUENTIAL = "sequential"
    WITH_DELAY = "with_delay"


class ExecutionMode(str, Enum):
    AUTO = "auto"
    SEMI_AUTO = "semi_auto"


class ConditionLogic(str, Enum):
    AND = "AND"
    OR = "OR"
    CUSTOM = "CUSTOM"


class ConditionOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUALS = "greater_equals"
    LESS_EQUALS = "less_equals"
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"
    BREACHES = "breaches"
    APPROACHES = "approaches"


class AdjustmentActionType(str, Enum):
    EXIT_ALL = "exit_all"
    EXIT_PARTIAL = "exit_partial"
    ROLL = "roll"
    SHIFT = "shift"
    ADD_HEDGE = "add_hedge"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    CONVERT = "convert"
    ALERT_ONLY = "alert_only"


class LogEventType(str, Enum):
    STRATEGY_CREATED = "strategy_created"
    STRATEGY_ACTIVATED = "strategy_activated"
    STRATEGY_PAUSED = "strategy_paused"
    STRATEGY_RESUMED = "strategy_resumed"
    STRATEGY_COMPLETED = "strategy_completed"
    STRATEGY_ERROR = "strategy_error"
    ENTRY_TRIGGERED = "entry_triggered"
    ENTRY_COMPLETED = "entry_completed"
    ADJUSTMENT_TRIGGERED = "adjustment_triggered"
    ADJUSTMENT_COMPLETED = "adjustment_completed"
    CONFIRMATION_REQUESTED = "confirmation_requested"
    CONFIRMATION_RECEIVED = "confirmation_received"
    CONFIRMATION_TIMEOUT = "confirmation_timeout"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    EXIT_TRIGGERED = "exit_triggered"
    EXIT_COMPLETED = "exit_completed"
    KILL_SWITCH_ACTIVATED = "kill_switch_activated"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    ERROR = "error"


class LogSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ExpiryType(str, Enum):
    CURRENT_WEEK = "current_week"
    NEXT_WEEK = "next_week"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ActivationMode(str, Enum):
    ALWAYS = "always"
    DATE_RANGE = "date_range"
    SPECIFIC_DAYS = "specific_days"
    EXPIRY_DAYS_ONLY = "expiry_days_only"
    ONE_TIME = "one_time"


class DayOfWeek(str, Enum):
    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
```

---

## 4. Strategy Endpoints

### 4.1 Strategy Schemas

```python
# app/schemas/strategy.py

from datetime import datetime, date, time
from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel, Field, field_validator, model_validator
from decimal import Decimal

from app.schemas.enums import *


# ============================================================================
# LEG CONFIGURATION
# ============================================================================

class StrikeSelection(BaseModel):
    """Strike selection configuration."""
    mode: str = Field(..., description="fixed | atm_offset | premium_based | delta_based")
    offset: Optional[int] = Field(None, description="Points from ATM (for atm_offset)")
    fixed_strike: Optional[Decimal] = Field(None, description="Exact strike (for fixed)")
    target_premium: Optional[Decimal] = Field(None, description="Target premium")
    target_delta: Optional[float] = Field(None, ge=-1, le=1, description="Target delta")
    
    @model_validator(mode='after')
    def validate_strike_selection(self):
        if self.mode == "fixed" and self.fixed_strike is None:
            raise ValueError("fixed_strike required when mode is 'fixed'")
        if self.mode == "atm_offset" and self.offset is None:
            raise ValueError("offset required when mode is 'atm_offset'")
        return self


class LegConfig(BaseModel):
    """Single leg configuration."""
    id: str = Field(..., min_length=1, max_length=20)
    contract_type: ContractType
    transaction_type: TransactionType
    strike_selection: StrikeSelection
    quantity_multiplier: int = Field(default=1, ge=1, le=10)
    execution_order: int = Field(default=1, ge=1)
    
    model_config = ConfigDict(use_enum_values=True)


# ============================================================================
# CONDITIONS
# ============================================================================

class Condition(BaseModel):
    """Single condition definition."""
    id: str = Field(..., min_length=1, max_length=50)
    enabled: bool = True
    variable: str = Field(..., description="Variable key like TIME.CURRENT, NIFTY.SPOT")
    operator: ConditionOperator
    value: Union[int, float, str, bool, List[Union[int, float, str]]]
    
    @field_validator('variable')
    @classmethod
    def validate_variable(cls, v):
        valid_prefixes = ['TIME', 'NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 
                         'VOLATILITY', 'VIX', 'OI', 'PCR', 'STRATEGY', 
                         'SPOT', 'PREMIUM', 'INDICATOR', 'EVENT']
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Invalid variable: {v}")
        return v


class EntryConditions(BaseModel):
    """Entry conditions configuration."""
    logic: ConditionLogic = ConditionLogic.AND
    custom_expression: Optional[str] = None
    conditions: List[Condition] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def validate_conditions(self):
        if self.logic == ConditionLogic.CUSTOM and not self.custom_expression:
            raise ValueError("custom_expression required when logic is CUSTOM")
        return self


# ============================================================================
# ADJUSTMENT RULES
# ============================================================================

class ExitConfig(BaseModel):
    """Exit action configuration."""
    order_type: OrderType = OrderType.MARKET
    legs_to_exit: Optional[List[str]] = None  # None = all legs


class RollConfig(BaseModel):
    """Roll action configuration."""
    roll_to: str = Field(..., description="next_week | monthly | custom")
    strike_selection: str = Field(default="same", description="same | atm | same_moneyness")
    roll_legs: str = Field(default="all", description="all | sold_only | bought_only")
    execution_style: ExecutionStyle = ExecutionStyle.SEQUENTIAL


class ShiftConfig(BaseModel):
    """Shift strikes configuration."""
    direction: str = Field(default="away_from_spot", description="away_from_spot | toward_spot | custom")
    shift_amount: int = Field(..., ge=50, le=1000, description="Points to shift")
    shift_side: str = Field(default="both", description="ce_only | pe_only | both | breached")


class HedgeConfig(BaseModel):
    """Add hedge configuration."""
    hedge_type: str = Field(default="both", description="pe_only | ce_only | both")
    pe_strike: Optional[Dict[str, Any]] = None
    ce_strike: Optional[Dict[str, Any]] = None
    quantity_mode: str = Field(default="same_as_position")
    max_cost: Optional[Decimal] = None


class ScaleConfig(BaseModel):
    """Scale up/down configuration."""
    scale_type: str = Field(..., description="lots | percentage")
    value: Union[int, float]
    min_lots: int = Field(default=1, ge=1)
    max_lots: int = Field(default=10, ge=1)


class AlertConfig(BaseModel):
    """Alert only configuration."""
    message: str = Field(..., max_length=500)
    priority: str = Field(default="normal", description="normal | urgent")
    repeat_interval_minutes: Optional[int] = Field(default=None, ge=1, le=60)


class AdjustmentAction(BaseModel):
    """Adjustment action definition."""
    type: AdjustmentActionType
    config: Union[ExitConfig, RollConfig, ShiftConfig, HedgeConfig, ScaleConfig, AlertConfig]


class AdjustmentTrigger(BaseModel):
    """Adjustment trigger conditions."""
    logic: ConditionLogic = ConditionLogic.OR
    conditions: List[Condition]


class AdjustmentRule(BaseModel):
    """Single adjustment rule."""
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True
    priority: int = Field(default=1, ge=1, le=100)
    trigger: AdjustmentTrigger
    action: AdjustmentAction
    execution_mode: ExecutionMode = ExecutionMode.AUTO
    timeout_seconds: int = Field(default=60, ge=10, le=300)
    timeout_action: str = Field(default="skip", description="skip | execute | alert")
    max_executions: Optional[int] = Field(default=None, ge=1)
    cooldown_minutes: Optional[int] = Field(default=None, ge=1, le=60)


# ============================================================================
# ORDER SETTINGS
# ============================================================================

class SlippageProtection(BaseModel):
    """Slippage protection settings."""
    enabled: bool = True
    max_per_leg_pct: float = Field(default=2.0, ge=0.1, le=10.0)
    max_total_pct: float = Field(default=5.0, ge=0.1, le=20.0)
    on_exceed: str = Field(default="retry", description="retry | skip | execute")
    max_retries: int = Field(default=3, ge=1, le=10)


class OrderSettings(BaseModel):
    """Order execution settings."""
    order_type: OrderType = OrderType.MARKET
    execution_style: ExecutionStyle = ExecutionStyle.SEQUENTIAL
    leg_sequence: List[str] = Field(default_factory=list, description="Leg IDs in execution order")
    delay_between_legs: int = Field(default=2, ge=0, le=30)
    slippage_protection: SlippageProtection = Field(default_factory=SlippageProtection)
    on_leg_failure: str = Field(default="stop", description="continue | stop | reverse")


# ============================================================================
# RISK SETTINGS
# ============================================================================

class TrailingStop(BaseModel):
    """Trailing stop configuration."""
    enabled: bool = False
    trigger_profit: Optional[Decimal] = None
    trail_amount: Optional[Decimal] = None
    trail_pct: Optional[float] = None


class RiskSettings(BaseModel):
    """Risk management settings."""
    max_loss: Optional[Decimal] = Field(default=None, description="Absolute loss limit")
    max_loss_pct: Optional[float] = Field(default=None, ge=1, le=100, description="Loss % of premium")
    trailing_stop: TrailingStop = Field(default_factory=TrailingStop)
    max_margin: Optional[Decimal] = Field(default=None, description="Max margin to use")
    time_stop: Optional[str] = Field(default=None, description="Exit at this time HH:MM")


# ============================================================================
# SCHEDULE SETTINGS
# ============================================================================

class DateRange(BaseModel):
    """Date range for scheduling."""
    start_date: date
    end_date: date
    
    @model_validator(mode='after')
    def validate_date_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class ScheduleConfig(BaseModel):
    """Schedule configuration."""
    activation_mode: ActivationMode = ActivationMode.ALWAYS
    active_days: List[DayOfWeek] = Field(
        default=[DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI]
    )
    start_time: str = Field(default="09:15", pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(default="15:30", pattern=r"^\d{2}:\d{2}$")
    expiry_days_only: bool = False
    date_range: Optional[DateRange] = None


# ============================================================================
# RUNTIME STATE (Read-Only)
# ============================================================================

class PositionState(BaseModel):
    """Current position state."""
    leg_id: str
    tradingsymbol: str
    transaction_type: TransactionType
    quantity: int
    average_price: Decimal
    last_price: Decimal
    unrealized_pnl: Decimal


class AdjustmentRecord(BaseModel):
    """Record of adjustment made."""
    rule_id: str
    rule_name: str
    executed_at: datetime
    action_type: AdjustmentActionType
    legs_added: List[str] = []
    legs_removed: List[str] = []
    cost: Optional[Decimal] = None


class ConditionState(BaseModel):
    """Condition evaluation state."""
    last_evaluated: datetime
    is_satisfied: bool
    progress_pct: Optional[float] = None
    current_value: Any
    executions_count: int = 0


class RuntimeState(BaseModel):
    """Strategy runtime state (read-only)."""
    entered_at: Optional[datetime] = None
    entry_price: Optional[Dict[str, Any]] = None
    current_positions: List[PositionState] = []
    margin_used: Decimal = Decimal("0")
    current_pnl: Decimal = Decimal("0")
    max_pnl: Decimal = Decimal("0")
    min_pnl: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    adjustments_made: List[AdjustmentRecord] = []
    condition_states: Dict[str, ConditionState] = {}
    last_updated: datetime


# ============================================================================
# STRATEGY REQUEST/RESPONSE MODELS
# ============================================================================

class StrategyCreateRequest(BaseModel):
    """Request body for creating a strategy."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    underlying: Underlying
    expiry_type: ExpiryType = ExpiryType.CURRENT_WEEK
    expiry_date: Optional[date] = None
    lots: int = Field(default=1, ge=1, le=50)
    position_type: PositionType = PositionType.INTRADAY
    legs_config: List[LegConfig] = Field(..., min_length=1, max_length=20)
    entry_conditions: EntryConditions
    adjustment_rules: List[AdjustmentRule] = Field(default_factory=list)
    order_settings: Optional[OrderSettings] = None
    risk_settings: Optional[RiskSettings] = None
    schedule_config: Optional[ScheduleConfig] = None
    priority: int = Field(default=100, ge=1, le=1000)
    source_template_id: Optional[int] = None
    
    model_config = ConfigDict(use_enum_values=True)
    
    @field_validator('legs_config')
    @classmethod
    def validate_legs(cls, v):
        leg_ids = [leg.id for leg in v]
        if len(leg_ids) != len(set(leg_ids)):
            raise ValueError("Leg IDs must be unique")
        return v


class StrategyUpdateRequest(BaseModel):
    """Request body for updating a strategy."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    expiry_type: Optional[ExpiryType] = None
    expiry_date: Optional[date] = None
    lots: Optional[int] = Field(default=None, ge=1, le=50)
    position_type: Optional[PositionType] = None
    legs_config: Optional[List[LegConfig]] = None
    entry_conditions: Optional[EntryConditions] = None
    adjustment_rules: Optional[List[AdjustmentRule]] = None
    order_settings: Optional[OrderSettings] = None
    risk_settings: Optional[RiskSettings] = None
    schedule_config: Optional[ScheduleConfig] = None
    priority: Optional[int] = Field(default=None, ge=1, le=1000)
    
    model_config = ConfigDict(use_enum_values=True)


class StrategyResponse(BaseModel):
    """Strategy response model."""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    status: StrategyStatus
    underlying: Underlying
    expiry_type: ExpiryType
    expiry_date: Optional[date]
    lots: int
    position_type: PositionType
    legs_config: List[LegConfig]
    entry_conditions: EntryConditions
    adjustment_rules: List[AdjustmentRule]
    order_settings: OrderSettings
    risk_settings: RiskSettings
    schedule_config: ScheduleConfig
    priority: int
    runtime_state: Optional[RuntimeState]
    source_template_id: Optional[int]
    cloned_from_id: Optional[int]
    version: int
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class StrategyListItem(BaseModel):
    """Lightweight strategy for list views."""
    id: int
    name: str
    status: StrategyStatus
    underlying: Underlying
    lots: int
    position_type: PositionType
    leg_count: int
    current_pnl: Optional[Decimal]
    margin_used: Optional[Decimal]
    priority: int
    created_at: datetime
    activated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class StrategyListResponse(PaginatedResponse[StrategyListItem]):
    """Paginated strategy list response."""
    pass


# ============================================================================
# ACTION REQUESTS
# ============================================================================

class ActivateRequest(BaseModel):
    """Request to activate a strategy."""
    confirm: bool = Field(..., description="Must be True to confirm activation")
    paper_trading: bool = Field(default=False, description="Run in paper trading mode")


class ExitRequest(BaseModel):
    """Request to force exit a strategy."""
    confirm: bool = Field(..., description="Must be True to confirm exit")
    exit_type: str = Field(default="market", description="market | limit")
    reason: Optional[str] = Field(default=None, max_length=200)


class CloneRequest(BaseModel):
    """Request to clone a strategy."""
    new_name: Optional[str] = Field(default=None, max_length=100)
    reset_schedule: bool = Field(default=True, description="Reset schedule to defaults")


class ConfirmationRequest(BaseModel):
    """Request to confirm/skip a pending adjustment."""
    action: str = Field(..., description="confirm | skip | modify")
    modifications: Optional[Dict[str, Any]] = None


class BacktestRequest(BaseModel):
    """Request to run backtest."""
    start_date: date
    end_date: date
    initial_capital: Decimal = Field(default=Decimal("500000"))
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if (self.end_date - self.start_date).days > 365:
            raise ValueError("Backtest period cannot exceed 365 days")
        return self


class BacktestResponse(BaseModel):
    """Backtest results."""
    strategy_id: int
    start_date: date
    end_date: date
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: Decimal
    max_drawdown: Decimal
    win_rate: float
    avg_profit: Decimal
    avg_loss: Decimal
    sharpe_ratio: Optional[float]
    trades: List[Dict[str, Any]]


# ============================================================================
# CONDITION STATE
# ============================================================================

class ConditionEvaluation(BaseModel):
    """Single condition evaluation result."""
    condition_id: str
    condition_type: str  # entry | adjustment
    rule_name: Optional[str]
    variable: str
    operator: str
    target_value: Any
    current_value: Any
    is_satisfied: bool
    progress_pct: Optional[float]
    distance_to_trigger: Optional[str]
    evaluated_at: datetime


class ConditionStateResponse(BaseModel):
    """All condition states for a strategy."""
    strategy_id: int
    strategy_status: StrategyStatus
    entry_conditions: List[ConditionEvaluation]
    adjustment_rules: Dict[str, List[ConditionEvaluation]]
    last_updated: datetime
```

### 4.2 Strategy Router

```python
# app/api/v1/endpoints/autopilot_strategies.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, PaginationParams
from app.schemas.strategy import *
from app.services.autopilot import AutoPilotService

router = APIRouter(prefix="/strategies")


# ============================================================================
# LIST STRATEGIES
# ============================================================================

@router.get(
    "/",
    response_model=StrategyListResponse,
    summary="List all strategies",
    description="Get paginated list of user's AutoPilot strategies with optional filters."
)
async def list_strategies(
    status: Optional[StrategyStatus] = Query(None, description="Filter by status"),
    underlying: Optional[Underlying] = Query(None, description="Filter by underlying"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List strategies with pagination and filtering.
    
    **Filters:**
    - `status`: Filter by strategy status (draft, waiting, active, etc.)
    - `underlying`: Filter by underlying instrument
    
    **Sorting:**
    - `sort_by`: Field to sort by (created_at, name, status, priority)
    - `sort_order`: asc or desc
    
    **Returns:** Paginated list of strategies with basic info
    """
    service = AutoPilotService(db)
    return service.list_strategies(
        user_id=current_user.id,
        status=status,
        underlying=underlying,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )


# ============================================================================
# CREATE STRATEGY
# ============================================================================

@router.post(
    "/",
    response_model=DataResponse[StrategyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create new strategy",
    description="Create a new AutoPilot strategy in draft status."
)
async def create_strategy(
    request: StrategyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new AutoPilot strategy.
    
    **Notes:**
    - Strategy is created in 'draft' status
    - Must be activated separately using POST /{id}/activate
    - Validates all conditions and rules on creation
    - Maximum 50 strategies per user (including drafts)
    
    **Required fields:**
    - name: Strategy name (unique per user)
    - underlying: NIFTY, BANKNIFTY, FINNIFTY, or SENSEX
    - legs_config: At least one leg
    - entry_conditions: Entry trigger rules
    
    **Returns:** Created strategy with ID
    """
    service = AutoPilotService(db)
    strategy = service.create_strategy(
        user_id=current_user.id,
        data=request
    )
    return DataResponse(data=strategy, message="Strategy created successfully")


# ============================================================================
# GET STRATEGY
# ============================================================================

@router.get(
    "/{strategy_id}",
    response_model=DataResponse[StrategyResponse],
    summary="Get strategy details",
    description="Get full details of a specific strategy including runtime state."
)
async def get_strategy(
    strategy_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get complete strategy details.
    
    **Returns:**
    - Full configuration (legs, conditions, rules)
    - Runtime state (positions, P&L) if active
    - Version history reference
    
    **Errors:**
    - 404: Strategy not found
    - 403: Not authorized to view this strategy
    """
    service = AutoPilotService(db)
    strategy = service.get_strategy(
        strategy_id=strategy_id,
        user_id=current_user.id
    )
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    return DataResponse(data=strategy)


# ============================================================================
# UPDATE STRATEGY
# ============================================================================

@router.put(
    "/{strategy_id}",
    response_model=DataResponse[StrategyResponse],
    summary="Update strategy",
    description="Update strategy configuration. Only allowed for draft/paused strategies."
)
async def update_strategy(
    strategy_id: int = Path(..., ge=1),
    request: StrategyUpdateRequest = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update strategy configuration.
    
    **Restrictions:**
    - Can only update strategies in 'draft' or 'paused' status
    - Cannot change underlying once strategy has been activated
    - Increments version number
    
    **Partial updates:** Only provided fields are updated
    
    **Errors:**
    - 404: Strategy not found
    - 400: Cannot update strategy in current status
    - 409: Optimistic locking conflict (version mismatch)
    """
    service = AutoPilotService(db)
    strategy = service.update_strategy(
        strategy_id=strategy_id,
        user_id=current_user.id,
        data=request
    )
    return DataResponse(data=strategy, message="Strategy updated successfully")


# ============================================================================
# DELETE STRATEGY
# ============================================================================

@router.delete(
    "/{strategy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete strategy",
    description="Delete a strategy. Only allowed for draft/completed/error strategies."
)
async def delete_strategy(
    strategy_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a strategy.
    
    **Restrictions:**
    - Cannot delete active/waiting/pending strategies
    - Must first exit or pause the strategy
    
    **Note:** Deleting a strategy also deletes all associated orders and logs
    
    **Errors:**
    - 404: Strategy not found
    - 400: Cannot delete strategy in current status
    """
    service = AutoPilotService(db)
    service.delete_strategy(
        strategy_id=strategy_id,
        user_id=current_user.id
    )


# ============================================================================
# ACTIVATE STRATEGY
# ============================================================================

@router.post(
    "/{strategy_id}/activate",
    response_model=DataResponse[StrategyResponse],
    summary="Activate strategy",
    description="Activate a draft strategy to start monitoring entry conditions."
)
async def activate_strategy(
    strategy_id: int = Path(..., ge=1),
    request: ActivateRequest = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Activate a strategy for live trading.
    
    **Pre-flight checks:**
    - Kite session is active
    - Sufficient margin available (estimated + 20% buffer)
    - Daily loss limit not breached
    - Max active strategies not reached (default: 3)
    - Schedule allows activation today
    - All conditions are valid
    
    **Status change:** draft → waiting
    
    **Paper trading:** Set `paper_trading=true` for simulation mode
    
    **Errors:**
    - 400: Strategy not in draft status
    - 400: Pre-flight checks failed
    - 409: Max active strategies reached
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Set confirm=true"
        )
    
    service = AutoPilotService(db)
    strategy = service.activate_strategy(
        strategy_id=strategy_id,
        user_id=current_user.id,
        paper_trading=request.paper_trading
    )
    return DataResponse(data=strategy, message="Strategy activated successfully")


# ============================================================================
# PAUSE STRATEGY
# ============================================================================

@router.post(
    "/{strategy_id}/pause",
    response_model=DataResponse[StrategyResponse],
    summary="Pause strategy",
    description="Pause an active strategy. Positions remain open."
)
async def pause_strategy(
    strategy_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Pause a running strategy.
    
    **Effect:**
    - Stops monitoring conditions
    - Keeps positions open
    - Can be resumed later
    
    **Status change:** waiting/active/pending → paused
    
    **Note:** Use exit endpoint to close positions
    """
    service = AutoPilotService(db)
    strategy = service.pause_strategy(
        strategy_id=strategy_id,
        user_id=current_user.id
    )
    return DataResponse(data=strategy, message="Strategy paused")


# ============================================================================
# RESUME STRATEGY
# ============================================================================

@router.post(
    "/{strategy_id}/resume",
    response_model=DataResponse[StrategyResponse],
    summary="Resume strategy",
    description="Resume a paused strategy."
)
async def resume_strategy(
    strategy_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Resume a paused strategy.
    
    **Pre-flight checks:** Same as activation
    
    **Status change:** paused → waiting/active (based on position state)
    """
    service = AutoPilotService(db)
    strategy = service.resume_strategy(
        strategy_id=strategy_id,
        user_id=current_user.id
    )
    return DataResponse(data=strategy, message="Strategy resumed")


# ============================================================================
# FORCE EXIT
# ============================================================================

@router.post(
    "/{strategy_id}/exit",
    response_model=DataResponse[StrategyResponse],
    summary="Force exit strategy",
    description="Immediately exit all positions and complete the strategy."
)
async def exit_strategy(
    strategy_id: int = Path(..., ge=1),
    request: ExitRequest = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Force exit all positions.
    
    **Effect:**
    - Cancels any pending orders
    - Places exit orders for all positions
    - Marks strategy as completed
    
    **Status change:** active/paused/pending → completed
    
    **Note:** Uses MARKET orders by default for immediate exit
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Set confirm=true"
        )
    
    service = AutoPilotService(db)
    strategy = service.exit_strategy(
        strategy_id=strategy_id,
        user_id=current_user.id,
        exit_type=request.exit_type,
        reason=request.reason
    )
    return DataResponse(data=strategy, message="Exit orders placed")


# ============================================================================
# CLONE STRATEGY
# ============================================================================

@router.post(
    "/{strategy_id}/clone",
    response_model=DataResponse[StrategyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Clone strategy",
    description="Create a copy of an existing strategy."
)
async def clone_strategy(
    strategy_id: int = Path(..., ge=1),
    request: CloneRequest = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Clone a strategy.
    
    **Creates:** New strategy in 'draft' status with same configuration
    
    **Options:**
    - `new_name`: Custom name (default: "Original Name (Copy)")
    - `reset_schedule`: Reset schedule to defaults
    
    **Note:** Runtime state is not copied
    """
    service = AutoPilotService(db)
    strategy = service.clone_strategy(
        strategy_id=strategy_id,
        user_id=current_user.id,
        new_name=request.new_name,
        reset_schedule=request.reset_schedule
    )
    return DataResponse(data=strategy, message="Strategy cloned successfully")


# ============================================================================
# GET CONDITION STATES
# ============================================================================

@router.get(
    "/{strategy_id}/conditions",
    response_model=DataResponse[ConditionStateResponse],
    summary="Get condition states",
    description="Get current evaluation state of all conditions."
)
async def get_condition_states(
    strategy_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get real-time condition evaluation states.
    
    **Returns:**
    - Entry conditions with progress percentage
    - Adjustment rules with trigger proximity
    - Current values vs target values
    
    **Use case:** For progress bars in UI
    
    **Note:** Updated every second for active strategies
    """
    service = AutoPilotService(db)
    states = service.get_condition_states(
        strategy_id=strategy_id,
        user_id=current_user.id
    )
    return DataResponse(data=states)


# ============================================================================
# BACKTEST
# ============================================================================

@router.post(
    "/{strategy_id}/backtest",
    response_model=DataResponse[BacktestResponse],
    summary="Run backtest",
    description="Run historical backtest on strategy configuration."
)
async def run_backtest(
    strategy_id: int = Path(..., ge=1),
    request: BacktestRequest = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Run backtest on historical data.
    
    **Parameters:**
    - `start_date`: Backtest start date
    - `end_date`: Backtest end date (max 365 days range)
    - `initial_capital`: Starting capital
    
    **Returns:**
    - Trade statistics (win rate, avg profit/loss)
    - P&L curve data
    - Individual trade records
    
    **Note:** Backtest uses EOD data, may not reflect intraday dynamics
    """
    service = AutoPilotService(db)
    results = service.run_backtest(
        strategy_id=strategy_id,
        user_id=current_user.id,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital
    )
    return DataResponse(data=results)


# ============================================================================
# CONFIRM ADJUSTMENT (for semi-auto)
# ============================================================================

@router.post(
    "/{strategy_id}/confirm",
    response_model=DataResponse[StrategyResponse],
    summary="Confirm pending adjustment",
    description="Confirm, skip, or modify a pending adjustment."
)
async def confirm_adjustment(
    strategy_id: int = Path(..., ge=1),
    request: ConfirmationRequest = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Handle semi-automatic adjustment confirmation.
    
    **Actions:**
    - `confirm`: Execute the proposed adjustment
    - `skip`: Skip this adjustment occurrence
    - `modify`: Apply modifications and execute
    
    **Only applicable when:** status = 'pending'
    
    **Timeout:** If not confirmed within timeout, auto-action is taken
    """
    service = AutoPilotService(db)
    strategy = service.handle_confirmation(
        strategy_id=strategy_id,
        user_id=current_user.id,
        action=request.action,
        modifications=request.modifications
    )
    return DataResponse(data=strategy)
```

---

## 5. Dashboard Endpoints

### 5.1 Dashboard Schemas

```python
# app/schemas/dashboard.py

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal

from app.schemas.enums import *


class ActiveStrategyCard(BaseModel):
    """Strategy card for dashboard."""
    id: int
    name: str
    status: StrategyStatus
    underlying: Underlying
    lots: int
    current_pnl: Decimal
    margin_used: Decimal
    entry_progress: Optional[float] = None  # % of entry conditions met
    next_trigger: Optional[str] = None  # Description of nearest trigger
    activated_at: Optional[datetime]


class RiskMetrics(BaseModel):
    """Risk gauge data."""
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
    """Main dashboard summary."""
    # Counts
    active_strategies: int
    waiting_strategies: int
    pending_confirmations: int
    
    # P&L
    today_realized_pnl: Decimal
    today_unrealized_pnl: Decimal
    today_total_pnl: Decimal
    
    # Risk
    risk_metrics: RiskMetrics
    
    # Strategies
    strategies: List[ActiveStrategyCard]
    
    # System status
    kite_connected: bool
    websocket_connected: bool
    last_update: datetime


class ActivityItem(BaseModel):
    """Single activity feed item."""
    id: int
    event_type: LogEventType
    severity: LogSeverity
    strategy_id: Optional[int]
    strategy_name: Optional[str]
    rule_name: Optional[str]
    message: str
    event_data: Dict[str, Any]
    created_at: datetime


class ActivityFeed(BaseModel):
    """Activity feed response."""
    items: List[ActivityItem]
    has_more: bool
    last_id: Optional[int]


class PerformanceMetrics(BaseModel):
    """Performance statistics."""
    period: str  # today | week | month | all
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: Decimal
    avg_profit: Decimal
    avg_loss: Decimal
    best_trade: Decimal
    worst_trade: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Optional[float]
    
    # By underlying
    by_underlying: Dict[str, Dict[str, Any]]
    
    # Daily P&L for chart
    daily_pnl: List[Dict[str, Any]]
```

### 5.2 Dashboard Router

```python
# app/api/v1/endpoints/autopilot_dashboard.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse
from app.schemas.dashboard import *
from app.services.autopilot import AutoPilotService

router = APIRouter(prefix="/dashboard")


@router.get(
    "/summary",
    response_model=DataResponse[DashboardSummary],
    summary="Get dashboard summary",
    description="Get overview of all AutoPilot activity."
)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard summary with:
    - Active strategy count and details
    - Today's P&L (realized + unrealized)
    - Risk metrics (limits usage)
    - System connection status
    
    **Refresh:** Every 5 seconds on frontend
    """
    service = AutoPilotService(db)
    summary = service.get_dashboard_summary(user_id=current_user.id)
    return DataResponse(data=summary)


@router.get(
    "/activity",
    response_model=DataResponse[ActivityFeed],
    summary="Get activity feed",
    description="Get recent AutoPilot activity for feed display."
)
async def get_activity_feed(
    limit: int = Query(50, ge=1, le=100),
    after_id: Optional[int] = Query(None, description="For pagination, get items after this ID"),
    event_types: Optional[str] = Query(None, description="Comma-separated event types to filter"),
    strategy_id: Optional[int] = Query(None, description="Filter by strategy"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get activity feed for real-time display.
    
    **Pagination:** Use `after_id` for infinite scroll
    
    **Filters:**
    - `event_types`: Comma-separated (e.g., "order_filled,adjustment_triggered")
    - `strategy_id`: Filter to specific strategy
    
    **Default:** Last 50 events from past 24 hours
    """
    event_type_list = event_types.split(",") if event_types else None
    
    service = AutoPilotService(db)
    feed = service.get_activity_feed(
        user_id=current_user.id,
        limit=limit,
        after_id=after_id,
        event_types=event_type_list,
        strategy_id=strategy_id
    )
    return DataResponse(data=feed)


@router.get(
    "/risk",
    response_model=DataResponse[RiskMetrics],
    summary="Get risk metrics",
    description="Get detailed risk metrics for gauges."
)
async def get_risk_metrics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get risk metrics for dashboard gauges.
    
    **Returns:**
    - Daily loss limit usage
    - Capital deployment
    - Active strategy count
    - Overall risk status
    """
    service = AutoPilotService(db)
    metrics = service.get_risk_metrics(user_id=current_user.id)
    return DataResponse(data=metrics)


@router.get(
    "/performance",
    response_model=DataResponse[PerformanceMetrics],
    summary="Get performance metrics",
    description="Get trading performance statistics."
)
async def get_performance_metrics(
    period: str = Query("month", pattern="^(today|week|month|all)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get performance statistics for reporting.
    
    **Periods:**
    - `today`: Today only
    - `week`: Last 7 days
    - `month`: Last 30 days
    - `all`: All time
    
    **Returns:**
    - Win/loss statistics
    - P&L breakdown by underlying
    - Daily P&L for charting
    """
    service = AutoPilotService(db)
    metrics = service.get_performance_metrics(
        user_id=current_user.id,
        period=period
    )
    return DataResponse(data=metrics)
```

---

## 6. Order Endpoints

### 6.1 Order Schemas

```python
# app/schemas/order.py

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal

from app.schemas.enums import *


class OrderResponse(BaseModel):
    """Full order details."""
    id: int
    strategy_id: int
    strategy_name: str
    kite_order_id: Optional[str]
    purpose: OrderPurpose
    rule_name: Optional[str]
    leg_index: int
    
    # Instrument
    exchange: str
    tradingsymbol: str
    underlying: Underlying
    contract_type: str
    strike: Optional[Decimal]
    expiry: date
    
    # Order details
    transaction_type: TransactionType
    order_type: OrderType
    product: str
    quantity: int
    
    # Prices
    order_price: Optional[Decimal]
    trigger_price: Optional[Decimal]
    ltp_at_order: Optional[Decimal]
    executed_price: Optional[Decimal]
    executed_quantity: int
    
    # Slippage
    slippage_amount: Optional[Decimal]
    slippage_pct: Optional[float]
    
    # Status
    status: OrderStatus
    rejection_reason: Optional[str]
    
    # Timing
    order_placed_at: Optional[datetime]
    order_filled_at: Optional[datetime]
    execution_duration_ms: Optional[int]
    
    # Metadata
    retry_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class OrderListItem(BaseModel):
    """Lightweight order for lists."""
    id: int
    strategy_id: int
    strategy_name: str
    tradingsymbol: str
    transaction_type: TransactionType
    order_type: OrderType
    quantity: int
    executed_price: Optional[Decimal]
    status: OrderStatus
    purpose: OrderPurpose
    slippage_pct: Optional[float]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class OrderListResponse(BaseModel):
    """Paginated order list."""
    data: List[OrderListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrderExportParams(BaseModel):
    """Export query parameters."""
    start_date: date
    end_date: date
    strategy_id: Optional[int] = None
    status: Optional[OrderStatus] = None
    format: str = Field(default="csv", pattern="^(csv|xlsx)$")
```

### 6.2 Order Router

```python
# app/api/v1/endpoints/autopilot_orders.py

from fastapi import APIRouter, Depends, Query, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse
from app.schemas.order import *
from app.services.autopilot import AutoPilotService

router = APIRouter(prefix="/orders")


@router.get(
    "/",
    response_model=OrderListResponse,
    summary="List orders",
    description="Get paginated list of AutoPilot orders."
)
async def list_orders(
    strategy_id: Optional[int] = Query(None),
    status: Optional[OrderStatus] = Query(None),
    purpose: Optional[OrderPurpose] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List orders with filtering.
    
    **Filters:**
    - `strategy_id`: Filter by strategy
    - `status`: Filter by order status
    - `purpose`: Filter by purpose (entry, adjustment, exit, etc.)
    - `start_date` / `end_date`: Date range filter
    
    **Default:** Last 7 days, all strategies
    """
    service = AutoPilotService(db)
    return service.list_orders(
        user_id=current_user.id,
        strategy_id=strategy_id,
        status=status,
        purpose=purpose,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{order_id}",
    response_model=DataResponse[OrderResponse],
    summary="Get order details",
    description="Get full details of a specific order."
)
async def get_order(
    order_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get complete order details including raw broker response.
    """
    service = AutoPilotService(db)
    order = service.get_order(
        order_id=order_id,
        user_id=current_user.id
    )
    return DataResponse(data=order)


@router.get(
    "/export",
    summary="Export orders",
    description="Export orders to CSV/Excel file."
)
async def export_orders(
    start_date: date = Query(...),
    end_date: date = Query(...),
    strategy_id: Optional[int] = Query(None),
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export orders to file.
    
    **Formats:**
    - `csv`: Comma-separated values
    - `xlsx`: Excel format
    
    **Max range:** 90 days
    
    **Returns:** File download
    """
    service = AutoPilotService(db)
    file_content, filename, media_type = service.export_orders(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        strategy_id=strategy_id,
        format=format
    )
    
    return StreamingResponse(
        file_content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

---

## 7. Log Endpoints

### 7.1 Log Schemas

```python
# app/schemas/log.py

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal

from app.schemas.enums import *


class LogResponse(BaseModel):
    """Full log entry details."""
    id: int
    user_id: int
    strategy_id: Optional[int]
    strategy_name: Optional[str]
    order_id: Optional[int]
    event_type: LogEventType
    severity: LogSeverity
    rule_name: Optional[str]
    condition_id: Optional[str]
    event_data: Dict[str, Any]
    message: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class LogListItem(BaseModel):
    """Lightweight log for lists."""
    id: int
    event_type: LogEventType
    severity: LogSeverity
    strategy_name: Optional[str]
    message: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class LogListResponse(BaseModel):
    """Paginated log list."""
    data: List[LogListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class LogStats(BaseModel):
    """Log statistics."""
    total_logs: int
    by_severity: Dict[str, int]
    by_event_type: Dict[str, int]
    error_count_today: int
```

### 7.2 Log Router

```python
# app/api/v1/endpoints/autopilot_logs.py

from fastapi import APIRouter, Depends, Query, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse
from app.schemas.log import *
from app.services.autopilot import AutoPilotService

router = APIRouter(prefix="/logs")


@router.get(
    "/",
    response_model=LogListResponse,
    summary="List logs",
    description="Get paginated list of AutoPilot logs."
)
async def list_logs(
    strategy_id: Optional[int] = Query(None),
    event_type: Optional[LogEventType] = Query(None),
    severity: Optional[LogSeverity] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    search: Optional[str] = Query(None, max_length=100, description="Search in message"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List logs with filtering.
    
    **Filters:**
    - `strategy_id`: Filter by strategy
    - `event_type`: Filter by event type
    - `severity`: Filter by severity (error, warning, etc.)
    - `search`: Full-text search in message
    - `start_date` / `end_date`: Date range
    
    **Default:** Last 7 days
    
    **Retention:** Logs older than 90 days are automatically deleted
    """
    service = AutoPilotService(db)
    return service.list_logs(
        user_id=current_user.id,
        strategy_id=strategy_id,
        event_type=event_type,
        severity=severity,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{log_id}",
    response_model=DataResponse[LogResponse],
    summary="Get log details",
    description="Get full details of a specific log entry."
)
async def get_log(
    log_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get complete log entry with full event_data payload.
    """
    service = AutoPilotService(db)
    log = service.get_log(
        log_id=log_id,
        user_id=current_user.id
    )
    return DataResponse(data=log)


@router.get(
    "/export",
    summary="Export logs",
    description="Export logs to CSV file."
)
async def export_logs(
    start_date: date = Query(...),
    end_date: date = Query(...),
    strategy_id: Optional[int] = Query(None),
    severity: Optional[LogSeverity] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export logs to CSV.
    
    **Max range:** 90 days
    """
    service = AutoPilotService(db)
    file_content, filename = service.export_logs(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        strategy_id=strategy_id,
        severity=severity
    )
    
    return StreamingResponse(
        file_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get(
    "/stats",
    response_model=DataResponse[LogStats],
    summary="Get log statistics",
    description="Get log statistics and counts."
)
async def get_log_stats(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get log statistics for the given period.
    """
    service = AutoPilotService(db)
    stats = service.get_log_stats(
        user_id=current_user.id,
        days=days
    )
    return DataResponse(data=stats)
```

---

## 8. Settings Endpoints

### 8.1 Settings Schemas

```python
# app/schemas/settings.py

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal

from app.schemas.enums import *


class NotificationEvent(BaseModel):
    """Notification event settings."""
    entry_triggered: bool = True
    order_executed: bool = True
    adjustment_triggered: bool = True
    exit_executed: bool = True
    error: bool = True
    daily_summary: bool = True


class NotificationPrefs(BaseModel):
    """Notification preferences."""
    enabled: bool = True
    channels: List[str] = Field(default=["in_app"])
    frequency: str = Field(default="realtime", pattern="^(realtime|batched)$")
    events: NotificationEvent = Field(default_factory=NotificationEvent)


class DefaultOrderSettings(BaseModel):
    """Default order settings."""
    order_type: OrderType = OrderType.MARKET
    execution_style: ExecutionStyle = ExecutionStyle.SEQUENTIAL
    delay_between_legs: int = Field(default=2, ge=0, le=30)
    slippage_protection: bool = True
    max_slippage_pct: float = Field(default=2.0, ge=0.1, le=10.0)
    price_improvement: bool = False


class FailureHandling(BaseModel):
    """Failure handling settings."""
    on_network_error: str = Field(default="retry", pattern="^(retry|alert|cancel)$")
    on_api_error: str = Field(default="alert", pattern="^(retry|alert|cancel)$")
    on_margin_insufficient: str = Field(default="cancel", pattern="^(retry|alert|cancel)$")
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay_seconds: int = Field(default=5, ge=1, le=60)


class UserSettingsResponse(BaseModel):
    """User settings response."""
    id: int
    user_id: int
    
    # Risk Limits
    daily_loss_limit: Decimal
    per_strategy_loss_limit: Decimal
    max_capital_deployed: Decimal
    max_active_strategies: int
    
    # Time Restrictions
    no_trade_first_minutes: int
    no_trade_last_minutes: int
    
    # Cooldown
    cooldown_after_loss: bool
    cooldown_minutes: int
    cooldown_threshold: Decimal
    
    # Defaults
    default_order_settings: DefaultOrderSettings
    notification_prefs: NotificationPrefs
    failure_handling: FailureHandling
    
    # Features
    paper_trading_mode: bool
    show_advanced_features: bool
    
    model_config = ConfigDict(from_attributes=True)


class UserSettingsUpdateRequest(BaseModel):
    """Request to update settings."""
    # Risk Limits
    daily_loss_limit: Optional[Decimal] = Field(default=None, gt=0)
    per_strategy_loss_limit: Optional[Decimal] = Field(default=None, gt=0)
    max_capital_deployed: Optional[Decimal] = Field(default=None, gt=0)
    max_active_strategies: Optional[int] = Field(default=None, ge=1, le=10)
    
    # Time Restrictions
    no_trade_first_minutes: Optional[int] = Field(default=None, ge=0, le=60)
    no_trade_last_minutes: Optional[int] = Field(default=None, ge=0, le=60)
    
    # Cooldown
    cooldown_after_loss: Optional[bool] = None
    cooldown_minutes: Optional[int] = Field(default=None, ge=5, le=240)
    cooldown_threshold: Optional[Decimal] = Field(default=None, gt=0)
    
    # Defaults
    default_order_settings: Optional[DefaultOrderSettings] = None
    notification_prefs: Optional[NotificationPrefs] = None
    failure_handling: Optional[FailureHandling] = None
    
    # Features
    paper_trading_mode: Optional[bool] = None
    show_advanced_features: Optional[bool] = None
    
    @field_validator('per_strategy_loss_limit')
    @classmethod
    def validate_strategy_limit(cls, v, info):
        if v and info.data.get('daily_loss_limit') and v > info.data['daily_loss_limit']:
            raise ValueError('per_strategy_loss_limit cannot exceed daily_loss_limit')
        return v
```

### 8.2 Settings Router

```python
# app/api/v1/endpoints/autopilot_settings.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse
from app.schemas.settings import *
from app.services.autopilot import AutoPilotService

router = APIRouter(prefix="/settings")


@router.get(
    "/",
    response_model=DataResponse[UserSettingsResponse],
    summary="Get settings",
    description="Get user's AutoPilot settings."
)
async def get_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current AutoPilot settings.
    
    **Note:** Settings are created with defaults on first access.
    """
    service = AutoPilotService(db)
    settings = service.get_or_create_settings(user_id=current_user.id)
    return DataResponse(data=settings)


@router.put(
    "/",
    response_model=DataResponse[UserSettingsResponse],
    summary="Update settings",
    description="Update user's AutoPilot settings."
)
async def update_settings(
    request: UserSettingsUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update AutoPilot settings.
    
    **Partial updates:** Only provided fields are updated.
    
    **Validation:**
    - per_strategy_loss_limit cannot exceed daily_loss_limit
    - Changes apply immediately to new strategies
    - Active strategies keep their original settings
    """
    service = AutoPilotService(db)
    settings = service.update_settings(
        user_id=current_user.id,
        data=request
    )
    return DataResponse(data=settings, message="Settings updated successfully")
```

---

## 9. Template Endpoints

### 9.1 Template Schemas

```python
# app/schemas/template.py

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal

from app.schemas.enums import *


class TemplateResponse(BaseModel):
    """Template response."""
    id: int
    user_id: Optional[int]
    name: str
    description: Optional[str]
    is_system: bool
    is_public: bool
    strategy_config: Dict[str, Any]
    category: Optional[str]
    tags: List[str]
    risk_level: Optional[str]
    usage_count: int
    avg_rating: Optional[float]
    rating_count: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TemplateListItem(BaseModel):
    """Lightweight template for lists."""
    id: int
    name: str
    description: Optional[str]
    is_system: bool
    is_public: bool
    category: Optional[str]
    tags: List[str]
    risk_level: Optional[str]
    usage_count: int
    avg_rating: Optional[float]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    """Paginated template list."""
    data: List[TemplateListItem]
    total: int
    page: int
    page_size: int


class TemplateCreateRequest(BaseModel):
    """Request to create template."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    strategy_config: Dict[str, Any] = Field(...)
    category: Optional[str] = Field(default=None, max_length=50)
    tags: List[str] = Field(default_factory=list)
    risk_level: Optional[str] = Field(default=None, pattern="^(conservative|moderate|aggressive)$")
    is_public: bool = Field(default=False)


class TemplateUpdateRequest(BaseModel):
    """Request to update template."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    strategy_config: Optional[Dict[str, Any]] = None
    category: Optional[str] = Field(default=None, max_length=50)
    tags: Optional[List[str]] = None
    risk_level: Optional[str] = Field(default=None, pattern="^(conservative|moderate|aggressive)$")
    is_public: Optional[bool] = None


class TemplateRatingRequest(BaseModel):
    """Request to rate a template."""
    rating: int = Field(..., ge=1, le=5)
```

### 9.2 Template Router

```python
# app/api/v1/endpoints/autopilot_templates.py

from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse
from app.schemas.template import *
from app.services.autopilot import AutoPilotService

router = APIRouter(prefix="/templates")


@router.get(
    "/",
    response_model=TemplateListResponse,
    summary="List templates",
    description="Get list of available strategy templates."
)
async def list_templates(
    category: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None, pattern="^(conservative|moderate|aggressive)$"),
    is_public: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List templates.
    
    **Returns:**
    - User's own templates
    - System templates (built-in)
    - Public templates (from other users)
    
    **Filters:**
    - `category`: iron_condor, straddle, bull_put, etc.
    - `risk_level`: conservative, moderate, aggressive
    - `is_public`: Filter to public only
    - `search`: Search in name and description
    """
    service = AutoPilotService(db)
    return service.list_templates(
        user_id=current_user.id,
        category=category,
        risk_level=risk_level,
        is_public=is_public,
        search=search,
        page=page,
        page_size=page_size
    )


@router.post(
    "/",
    response_model=DataResponse[TemplateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create template",
    description="Create a new strategy template."
)
async def create_template(
    request: TemplateCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new template from strategy configuration.
    
    **Note:** Can also create template directly from an existing strategy
    """
    service = AutoPilotService(db)
    template = service.create_template(
        user_id=current_user.id,
        data=request
    )
    return DataResponse(data=template, message="Template created successfully")


@router.get(
    "/{template_id}",
    response_model=DataResponse[TemplateResponse],
    summary="Get template",
    description="Get template details."
)
async def get_template(
    template_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get complete template with strategy_config.
    """
    service = AutoPilotService(db)
    template = service.get_template(
        template_id=template_id,
        user_id=current_user.id
    )
    return DataResponse(data=template)


@router.put(
    "/{template_id}",
    response_model=DataResponse[TemplateResponse],
    summary="Update template",
    description="Update a template you own."
)
async def update_template(
    template_id: int = Path(..., ge=1),
    request: TemplateUpdateRequest = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update template.
    
    **Note:** Can only update templates you own (not system or others' templates)
    """
    service = AutoPilotService(db)
    template = service.update_template(
        template_id=template_id,
        user_id=current_user.id,
        data=request
    )
    return DataResponse(data=template, message="Template updated successfully")


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete template",
    description="Delete a template you own."
)
async def delete_template(
    template_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete template.
    
    **Note:** Cannot delete system templates
    """
    service = AutoPilotService(db)
    service.delete_template(
        template_id=template_id,
        user_id=current_user.id
    )


@router.post(
    "/{template_id}/rate",
    response_model=DataResponse[TemplateResponse],
    summary="Rate template",
    description="Rate a public template."
)
async def rate_template(
    template_id: int = Path(..., ge=1),
    request: TemplateRatingRequest = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Rate a template (1-5 stars).
    
    **Note:** Can only rate public templates or system templates
    """
    service = AutoPilotService(db)
    template = service.rate_template(
        template_id=template_id,
        user_id=current_user.id,
        rating=request.rating
    )
    return DataResponse(data=template)
```

---

## 10. Emergency & WebSocket

### 10.1 Kill Switch

```python
# app/api/v1/endpoints/autopilot_emergency.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse
from app.services.autopilot import AutoPilotService

router = APIRouter(prefix="/kill-switch")


class KillSwitchRequest(BaseModel):
    """Kill switch request."""
    confirm_text: str = Field(..., description="Must be 'STOP' to confirm")


class KillSwitchResult(BaseModel):
    """Kill switch execution result."""
    strategies_paused: int
    orders_cancelled: int
    positions_closed: int
    exit_orders: List[dict]
    total_pnl: float
    execution_time_seconds: float
    success: bool
    errors: List[str]


@router.post(
    "/",
    response_model=DataResponse[KillSwitchResult],
    summary="Execute kill switch",
    description="Emergency stop: pause all strategies, cancel orders, exit positions."
)
async def execute_kill_switch(
    request: KillSwitchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    🚨 EMERGENCY STOP
    
    **Actions performed:**
    1. Pause all active AutoPilot strategies
    2. Cancel all pending orders
    3. Exit all open positions at MARKET price
    
    **Confirmation:** Must send confirm_text="STOP"
    
    **Note:** This action cannot be undone. Positions will be closed at market price.
    """
    if request.confirm_text != "STOP":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Send confirm_text='STOP'"
        )
    
    service = AutoPilotService(db)
    result = service.execute_kill_switch(user_id=current_user.id)
    
    return DataResponse(
        data=result,
        message="Kill switch executed" if result.success else "Kill switch completed with errors"
    )
```

### 10.2 WebSocket Events

```python
# app/api/v1/endpoints/autopilot_websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import json
import asyncio

from app.api.dependencies.auth import get_current_user_ws
from app.services.autopilot_ws import AutoPilotWebSocketManager

router = APIRouter(prefix="/ws")

ws_manager = AutoPilotWebSocketManager()


@router.websocket("/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token for authentication")
):
    """
    WebSocket endpoint for real-time AutoPilot updates.
    
    **Authentication:** Pass JWT token as query parameter
    
    **Message format (server -> client):**
    ```json
    {
        "type": "event_type",
        "data": { ... },
        "timestamp": "2025-12-08T10:30:00Z"
    }
    ```
    
    **Event types:**
    - `strategy_state_update`: Runtime state changed
    - `condition_progress`: Condition evaluation update
    - `order_update`: Order status changed
    - `activity`: New activity log entry
    - `confirmation_required`: Semi-auto confirmation needed
    - `risk_alert`: Risk limit warning/breach
    - `connection_status`: Kite/WebSocket connection status
    
    **Client commands (client -> server):**
    ```json
    {
        "action": "subscribe",
        "strategy_ids": [1, 2, 3]  // Subscribe to specific strategies
    }
    {
        "action": "unsubscribe",
        "strategy_ids": [1]
    }
    {
        "action": "ping"  // Keep-alive
    }
    ```
    """
    # Authenticate
    try:
        user = await get_current_user_ws(token)
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Accept connection
    await websocket.accept()
    await ws_manager.connect(user.id, websocket)
    
    try:
        # Send initial state
        await ws_manager.send_initial_state(user.id, websocket)
        
        # Listen for client messages
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 second timeout for keep-alive
                )
                message = json.loads(data)
                await ws_manager.handle_client_message(user.id, message, websocket)
            except asyncio.TimeoutError:
                # Send ping to check connection
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        ws_manager.disconnect(user.id, websocket)
    except Exception as e:
        ws_manager.disconnect(user.id, websocket)
        await websocket.close(code=4000, reason=str(e))
```

### 10.3 WebSocket Event Schemas

```python
# app/schemas/websocket.py

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel
from enum import Enum


class WSEventType(str, Enum):
    # Strategy events
    STRATEGY_STATE_UPDATE = "strategy_state_update"
    STRATEGY_STATUS_CHANGE = "strategy_status_change"
    
    # Condition events
    CONDITION_PROGRESS = "condition_progress"
    CONDITION_TRIGGERED = "condition_triggered"
    
    # Order events
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"
    
    # Activity
    ACTIVITY = "activity"
    
    # Confirmations
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMATION_TIMEOUT = "confirmation_timeout"
    
    # Risk
    RISK_WARNING = "risk_warning"
    RISK_BREACH = "risk_breach"
    
    # System
    CONNECTION_STATUS = "connection_status"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WSMessage(BaseModel):
    """Base WebSocket message."""
    type: WSEventType
    data: Dict[str, Any]
    timestamp: datetime
    strategy_id: Optional[int] = None


class WSStrategyStateUpdate(BaseModel):
    """Strategy state update event."""
    strategy_id: int
    current_pnl: float
    margin_used: float
    positions: List[Dict[str, Any]]
    condition_states: Dict[str, Any]


class WSConditionProgress(BaseModel):
    """Condition progress update."""
    strategy_id: int
    condition_id: str
    condition_type: str  # entry | adjustment
    rule_name: Optional[str]
    variable: str
    current_value: Any
    target_value: Any
    progress_pct: float
    is_satisfied: bool


class WSOrderUpdate(BaseModel):
    """Order status update."""
    order_id: int
    strategy_id: int
    tradingsymbol: str
    status: str
    executed_price: Optional[float]
    executed_quantity: Optional[int]
    rejection_reason: Optional[str]


class WSConfirmationRequired(BaseModel):
    """Semi-auto confirmation request."""
    strategy_id: int
    strategy_name: str
    rule_id: str
    rule_name: str
    trigger_reason: Dict[str, Any]
    proposed_action: Dict[str, Any]
    timeout_seconds: int
    timeout_action: str
    created_at: datetime


class WSRiskAlert(BaseModel):
    """Risk alert event."""
    alert_type: str  # warning | breach
    metric: str  # daily_loss | capital | margin
    current_value: float
    limit_value: float
    percentage: float
    message: str


class WSConnectionStatus(BaseModel):
    """Connection status update."""
    kite_connected: bool
    websocket_connected: bool
    last_tick: Optional[datetime]
```

---

## 11. Error Handling

### 11.1 Error Codes

```python
# app/core/errors.py

from enum import Enum
from fastapi import HTTPException, status
from typing import Optional, List, Dict, Any


class ErrorCode(str, Enum):
    # Authentication
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_EXPIRED_TOKEN = "AUTH_EXPIRED_TOKEN"
    AUTH_USER_NOT_FOUND = "AUTH_USER_NOT_FOUND"
    AUTH_USER_DISABLED = "AUTH_USER_DISABLED"
    AUTH_KITE_SESSION_EXPIRED = "AUTH_KITE_SESSION_EXPIRED"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_CONDITION = "INVALID_CONDITION"
    INVALID_LEG_CONFIG = "INVALID_LEG_CONFIG"
    INVALID_ADJUSTMENT_RULE = "INVALID_ADJUSTMENT_RULE"
    
    # Strategy
    STRATEGY_NOT_FOUND = "STRATEGY_NOT_FOUND"
    STRATEGY_INVALID_STATUS = "STRATEGY_INVALID_STATUS"
    STRATEGY_CANNOT_UPDATE = "STRATEGY_CANNOT_UPDATE"
    STRATEGY_CANNOT_DELETE = "STRATEGY_CANNOT_DELETE"
    STRATEGY_ACTIVATION_FAILED = "STRATEGY_ACTIVATION_FAILED"
    MAX_STRATEGIES_EXCEEDED = "MAX_STRATEGIES_EXCEEDED"
    
    # Orders
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_PLACEMENT_FAILED = "ORDER_PLACEMENT_FAILED"
    ORDER_REJECTED = "ORDER_REJECTED"
    INSUFFICIENT_MARGIN = "INSUFFICIENT_MARGIN"
    
    # Risk
    DAILY_LOSS_LIMIT_EXCEEDED = "DAILY_LOSS_LIMIT_EXCEEDED"
    CAPITAL_LIMIT_EXCEEDED = "CAPITAL_LIMIT_EXCEEDED"
    RISK_CHECK_FAILED = "RISK_CHECK_FAILED"
    
    # Template
    TEMPLATE_NOT_FOUND = "TEMPLATE_NOT_FOUND"
    TEMPLATE_CANNOT_MODIFY = "TEMPLATE_CANNOT_MODIFY"
    
    # System
    KITE_API_ERROR = "KITE_API_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


class AutoPilotException(HTTPException):
    """Custom exception with error code."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error": error_code.value,
                "message": message,
                "details": details
            }
        )


# Pre-defined exceptions
class StrategyNotFoundError(AutoPilotException):
    def __init__(self, strategy_id: int):
        super().__init__(
            error_code=ErrorCode.STRATEGY_NOT_FOUND,
            message=f"Strategy with ID {strategy_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class MaxStrategiesExceededError(AutoPilotException):
    def __init__(self, current: int, max_allowed: int):
        super().__init__(
            error_code=ErrorCode.MAX_STRATEGIES_EXCEEDED,
            message=f"Maximum active strategies limit ({max_allowed}) reached",
            status_code=status.HTTP_409_CONFLICT,
            details=[{"current": current, "max_allowed": max_allowed}]
        )


class InsufficientMarginError(AutoPilotException):
    def __init__(self, required: float, available: float):
        super().__init__(
            error_code=ErrorCode.INSUFFICIENT_MARGIN,
            message=f"Insufficient margin. Required: ₹{required:,.2f}, Available: ₹{available:,.2f}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=[{"required": required, "available": available}]
        )


class DailyLossLimitExceededError(AutoPilotException):
    def __init__(self, current_loss: float, limit: float):
        super().__init__(
            error_code=ErrorCode.DAILY_LOSS_LIMIT_EXCEEDED,
            message=f"Daily loss limit exceeded. Current: ₹{current_loss:,.2f}, Limit: ₹{limit:,.2f}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=[{"current_loss": current_loss, "limit": limit}]
        )


class KiteSessionExpiredError(AutoPilotException):
    def __init__(self):
        super().__init__(
            error_code=ErrorCode.AUTH_KITE_SESSION_EXPIRED,
            message="Kite session expired. Please login to Zerodha again.",
            status_code=status.HTTP_403_FORBIDDEN
        )
```

### 11.2 Error Handler

```python
# app/core/exception_handlers.py

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import traceback
import logging

from app.core.errors import AutoPilotException, ErrorCode

logger = logging.getLogger(__name__)


async def autopilot_exception_handler(request: Request, exc: AutoPilotException):
    """Handle AutoPilot custom exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            **exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "error": ErrorCode.VALIDATION_ERROR.value,
            "message": "Validation error",
            "details": errors,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors."""
    logger.error(f"Database error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error": ErrorCode.DATABASE_ERROR.value,
            "message": "A database error occurred. Please try again.",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error": ErrorCode.INTERNAL_ERROR.value,
            "message": "An unexpected error occurred. Please try again.",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Register handlers in main.py
def register_exception_handlers(app):
    app.add_exception_handler(AutoPilotException, autopilot_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
```

---

## 12. TypeScript Interfaces

### 12.1 Core Types

```typescript
// src/types/autopilot/enums.ts

export enum StrategyStatus {
  DRAFT = 'draft',
  WAITING = 'waiting',
  ACTIVE = 'active',
  PENDING = 'pending',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  ERROR = 'error',
  EXPIRED = 'expired'
}

export enum Underlying {
  NIFTY = 'NIFTY',
  BANKNIFTY = 'BANKNIFTY',
  FINNIFTY = 'FINNIFTY',
  SENSEX = 'SENSEX'
}

export enum PositionType {
  INTRADAY = 'intraday',
  POSITIONAL = 'positional'
}

export enum ContractType {
  CE = 'CE',
  PE = 'PE',
  FUT = 'FUT'
}

export enum TransactionType {
  BUY = 'BUY',
  SELL = 'SELL'
}

export enum OrderType {
  MARKET = 'MARKET',
  LIMIT = 'LIMIT',
  SL = 'SL',
  SL_M = 'SL-M'
}

export enum OrderStatus {
  PENDING = 'pending',
  PLACED = 'placed',
  OPEN = 'open',
  COMPLETE = 'complete',
  CANCELLED = 'cancelled',
  REJECTED = 'rejected',
  ERROR = 'error'
}

export enum OrderPurpose {
  ENTRY = 'entry',
  ADJUSTMENT = 'adjustment',
  HEDGE = 'hedge',
  EXIT = 'exit',
  ROLL_CLOSE = 'roll_close',
  ROLL_OPEN = 'roll_open',
  KILL_SWITCH = 'kill_switch'
}

export enum ExecutionStyle {
  SIMULTANEOUS = 'simultaneous',
  SEQUENTIAL = 'sequential',
  WITH_DELAY = 'with_delay'
}

export enum ExecutionMode {
  AUTO = 'auto',
  SEMI_AUTO = 'semi_auto'
}

export enum ConditionLogic {
  AND = 'AND',
  OR = 'OR',
  CUSTOM = 'CUSTOM'
}

export enum ConditionOperator {
  EQUALS = 'equals',
  NOT_EQUALS = 'not_equals',
  GREATER_THAN = 'greater_than',
  LESS_THAN = 'less_than',
  GREATER_EQUALS = 'greater_equals',
  LESS_EQUALS = 'less_equals',
  BETWEEN = 'between',
  NOT_BETWEEN = 'not_between',
  CROSSES_ABOVE = 'crosses_above',
  CROSSES_BELOW = 'crosses_below',
  BREACHES = 'breaches',
  APPROACHES = 'approaches'
}

export enum AdjustmentActionType {
  EXIT_ALL = 'exit_all',
  EXIT_PARTIAL = 'exit_partial',
  ROLL = 'roll',
  SHIFT = 'shift',
  ADD_HEDGE = 'add_hedge',
  SCALE_UP = 'scale_up',
  SCALE_DOWN = 'scale_down',
  CONVERT = 'convert',
  ALERT_ONLY = 'alert_only'
}

export enum LogEventType {
  STRATEGY_CREATED = 'strategy_created',
  STRATEGY_ACTIVATED = 'strategy_activated',
  STRATEGY_PAUSED = 'strategy_paused',
  STRATEGY_COMPLETED = 'strategy_completed',
  ENTRY_TRIGGERED = 'entry_triggered',
  ENTRY_COMPLETED = 'entry_completed',
  ADJUSTMENT_TRIGGERED = 'adjustment_triggered',
  ADJUSTMENT_COMPLETED = 'adjustment_completed',
  ORDER_PLACED = 'order_placed',
  ORDER_FILLED = 'order_filled',
  ORDER_REJECTED = 'order_rejected',
  EXIT_COMPLETED = 'exit_completed',
  KILL_SWITCH_ACTIVATED = 'kill_switch_activated',
  ERROR = 'error'
}

export enum LogSeverity {
  DEBUG = 'debug',
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical'
}

export enum ExpiryType {
  CURRENT_WEEK = 'current_week',
  NEXT_WEEK = 'next_week',
  MONTHLY = 'monthly',
  CUSTOM = 'custom'
}

export enum ActivationMode {
  ALWAYS = 'always',
  DATE_RANGE = 'date_range',
  SPECIFIC_DAYS = 'specific_days',
  EXPIRY_DAYS_ONLY = 'expiry_days_only',
  ONE_TIME = 'one_time'
}

export enum DayOfWeek {
  MON = 'MON',
  TUE = 'TUE',
  WED = 'WED',
  THU = 'THU',
  FRI = 'FRI'
}
```

### 12.2 Strategy Types

```typescript
// src/types/autopilot/strategy.ts

import {
  StrategyStatus,
  Underlying,
  PositionType,
  ContractType,
  TransactionType,
  OrderType,
  ExecutionStyle,
  ExecutionMode,
  ConditionLogic,
  ConditionOperator,
  AdjustmentActionType,
  ExpiryType,
  ActivationMode,
  DayOfWeek
} from './enums';

// ============================================================================
// Leg Configuration
// ============================================================================

export interface StrikeSelection {
  mode: 'fixed' | 'atm_offset' | 'premium_based' | 'delta_based';
  offset?: number;
  fixed_strike?: number;
  target_premium?: number;
  target_delta?: number;
}

export interface LegConfig {
  id: string;
  contract_type: ContractType;
  transaction_type: TransactionType;
  strike_selection: StrikeSelection;
  quantity_multiplier: number;
  execution_order: number;
}

// ============================================================================
// Conditions
// ============================================================================

export type ConditionValue = number | string | boolean | [number, number];

export interface Condition {
  id: string;
  enabled: boolean;
  variable: string;
  operator: ConditionOperator;
  value: ConditionValue;
}

export interface EntryConditions {
  logic: ConditionLogic;
  custom_expression?: string;
  conditions: Condition[];
}

// ============================================================================
// Adjustment Rules
// ============================================================================

export interface ExitConfig {
  order_type: OrderType;
  legs_to_exit?: string[];
}

export interface RollConfig {
  roll_to: string;
  strike_selection: string;
  roll_legs: string;
  execution_style: ExecutionStyle;
}

export interface ShiftConfig {
  direction: string;
  shift_amount: number;
  shift_side: string;
}

export interface HedgeConfig {
  hedge_type: string;
  pe_strike?: Record<string, any>;
  ce_strike?: Record<string, any>;
  quantity_mode: string;
  max_cost?: number;
}

export interface ScaleConfig {
  scale_type: string;
  value: number;
  min_lots: number;
  max_lots: number;
}

export interface AlertConfig {
  message: string;
  priority: string;
  repeat_interval_minutes?: number;
}

export type ActionConfig =
  | ExitConfig
  | RollConfig
  | ShiftConfig
  | HedgeConfig
  | ScaleConfig
  | AlertConfig;

export interface AdjustmentAction {
  type: AdjustmentActionType;
  config: ActionConfig;
}

export interface AdjustmentTrigger {
  logic: ConditionLogic;
  conditions: Condition[];
}

export interface AdjustmentRule {
  id: string;
  name: string;
  enabled: boolean;
  priority: number;
  trigger: AdjustmentTrigger;
  action: AdjustmentAction;
  execution_mode: ExecutionMode;
  timeout_seconds: number;
  timeout_action: string;
  max_executions?: number;
  cooldown_minutes?: number;
}

// ============================================================================
// Order Settings
// ============================================================================

export interface SlippageProtection {
  enabled: boolean;
  max_per_leg_pct: number;
  max_total_pct: number;
  on_exceed: string;
  max_retries: number;
}

export interface OrderSettings {
  order_type: OrderType;
  execution_style: ExecutionStyle;
  leg_sequence: string[];
  delay_between_legs: number;
  slippage_protection: SlippageProtection;
  on_leg_failure: string;
}

// ============================================================================
// Risk Settings
// ============================================================================

export interface TrailingStop {
  enabled: boolean;
  trigger_profit?: number;
  trail_amount?: number;
  trail_pct?: number;
}

export interface RiskSettings {
  max_loss?: number;
  max_loss_pct?: number;
  trailing_stop: TrailingStop;
  max_margin?: number;
  time_stop?: string;
}

// ============================================================================
// Schedule Settings
// ============================================================================

export interface DateRange {
  start_date: string;
  end_date: string;
}

export interface ScheduleConfig {
  activation_mode: ActivationMode;
  active_days: DayOfWeek[];
  start_time: string;
  end_time: string;
  expiry_days_only: boolean;
  date_range?: DateRange;
}

// ============================================================================
// Runtime State
// ============================================================================

export interface PositionState {
  leg_id: string;
  tradingsymbol: string;
  transaction_type: TransactionType;
  quantity: number;
  average_price: number;
  last_price: number;
  unrealized_pnl: number;
}

export interface AdjustmentRecord {
  rule_id: string;
  rule_name: string;
  executed_at: string;
  action_type: AdjustmentActionType;
  legs_added: string[];
  legs_removed: string[];
  cost?: number;
}

export interface ConditionState {
  last_evaluated: string;
  is_satisfied: boolean;
  progress_pct?: number;
  current_value: any;
  executions_count: number;
}

export interface RuntimeState {
  entered_at?: string;
  entry_price?: Record<string, any>;
  current_positions: PositionState[];
  margin_used: number;
  current_pnl: number;
  max_pnl: number;
  min_pnl: number;
  max_drawdown: number;
  adjustments_made: AdjustmentRecord[];
  condition_states: Record<string, ConditionState>;
  last_updated: string;
}

// ============================================================================
// Strategy Models
// ============================================================================

export interface Strategy {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  status: StrategyStatus;
  underlying: Underlying;
  expiry_type: ExpiryType;
  expiry_date?: string;
  lots: number;
  position_type: PositionType;
  legs_config: LegConfig[];
  entry_conditions: EntryConditions;
  adjustment_rules: AdjustmentRule[];
  order_settings: OrderSettings;
  risk_settings: RiskSettings;
  schedule_config: ScheduleConfig;
  priority: number;
  runtime_state?: RuntimeState;
  source_template_id?: number;
  cloned_from_id?: number;
  version: number;
  created_at: string;
  updated_at: string;
  activated_at?: string;
  completed_at?: string;
}

export interface StrategyListItem {
  id: number;
  name: string;
  status: StrategyStatus;
  underlying: Underlying;
  lots: number;
  position_type: PositionType;
  leg_count: number;
  current_pnl?: number;
  margin_used?: number;
  priority: number;
  created_at: string;
  activated_at?: string;
}

// ============================================================================
// Request Types
// ============================================================================

export interface StrategyCreateRequest {
  name: string;
  description?: string;
  underlying: Underlying;
  expiry_type?: ExpiryType;
  expiry_date?: string;
  lots?: number;
  position_type?: PositionType;
  legs_config: LegConfig[];
  entry_conditions: EntryConditions;
  adjustment_rules?: AdjustmentRule[];
  order_settings?: OrderSettings;
  risk_settings?: RiskSettings;
  schedule_config?: ScheduleConfig;
  priority?: number;
  source_template_id?: number;
}

export interface StrategyUpdateRequest {
  name?: string;
  description?: string;
  expiry_type?: ExpiryType;
  expiry_date?: string;
  lots?: number;
  position_type?: PositionType;
  legs_config?: LegConfig[];
  entry_conditions?: EntryConditions;
  adjustment_rules?: AdjustmentRule[];
  order_settings?: OrderSettings;
  risk_settings?: RiskSettings;
  schedule_config?: ScheduleConfig;
  priority?: number;
}

export interface ActivateRequest {
  confirm: boolean;
  paper_trading?: boolean;
}

export interface ExitRequest {
  confirm: boolean;
  exit_type?: string;
  reason?: string;
}

export interface CloneRequest {
  new_name?: string;
  reset_schedule?: boolean;
}

export interface ConfirmationRequest {
  action: 'confirm' | 'skip' | 'modify';
  modifications?: Record<string, any>;
}

export interface BacktestRequest {
  start_date: string;
  end_date: string;
  initial_capital?: number;
}
```

### 12.3 API Response Types

```typescript
// src/types/autopilot/api.ts

import { Strategy, StrategyListItem } from './strategy';
import { Order, OrderListItem } from './order';
import { Log, LogListItem } from './log';
import { UserSettings } from './settings';
import { Template, TemplateListItem } from './template';

// ============================================================================
// Base Response Types
// ============================================================================

export interface BaseResponse {
  status: 'success' | 'error';
  message?: string;
  timestamp: string;
}

export interface DataResponse<T> extends BaseResponse {
  data: T;
}

export interface PaginatedResponse<T> extends BaseResponse {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ErrorDetail {
  field?: string;
  message: string;
  code?: string;
}

export interface ErrorResponse {
  status: 'error';
  error: string;
  message: string;
  details?: ErrorDetail[];
  timestamp: string;
  request_id?: string;
}

// ============================================================================
// Specific Response Types
// ============================================================================

export type StrategyResponse = DataResponse<Strategy>;
export type StrategyListResponse = PaginatedResponse<StrategyListItem>;
export type OrderResponse = DataResponse<Order>;
export type OrderListResponse = PaginatedResponse<OrderListItem>;
export type LogResponse = DataResponse<Log>;
export type LogListResponse = PaginatedResponse<LogListItem>;
export type SettingsResponse = DataResponse<UserSettings>;
export type TemplateResponse = DataResponse<Template>;
export type TemplateListResponse = PaginatedResponse<TemplateListItem>;

// ============================================================================
// Dashboard Types
// ============================================================================

export interface ActiveStrategyCard {
  id: number;
  name: string;
  status: string;
  underlying: string;
  lots: number;
  current_pnl: number;
  margin_used: number;
  entry_progress?: number;
  next_trigger?: string;
  activated_at?: string;
}

export interface RiskMetrics {
  daily_loss_limit: number;
  daily_loss_used: number;
  daily_loss_pct: number;
  max_capital: number;
  capital_used: number;
  capital_pct: number;
  max_active_strategies: number;
  active_strategies_count: number;
  status: 'safe' | 'warning' | 'critical';
}

export interface DashboardSummary {
  active_strategies: number;
  waiting_strategies: number;
  pending_confirmations: number;
  today_realized_pnl: number;
  today_unrealized_pnl: number;
  today_total_pnl: number;
  risk_metrics: RiskMetrics;
  strategies: ActiveStrategyCard[];
  kite_connected: boolean;
  websocket_connected: boolean;
  last_update: string;
}

export interface ActivityItem {
  id: number;
  event_type: string;
  severity: string;
  strategy_id?: number;
  strategy_name?: string;
  rule_name?: string;
  message: string;
  event_data: Record<string, any>;
  created_at: string;
}

export interface ActivityFeed {
  items: ActivityItem[];
  has_more: boolean;
  last_id?: number;
}

export type DashboardResponse = DataResponse<DashboardSummary>;
export type ActivityFeedResponse = DataResponse<ActivityFeed>;
export type RiskMetricsResponse = DataResponse<RiskMetrics>;

// ============================================================================
// Kill Switch
// ============================================================================

export interface KillSwitchResult {
  strategies_paused: number;
  orders_cancelled: number;
  positions_closed: number;
  exit_orders: Record<string, any>[];
  total_pnl: number;
  execution_time_seconds: number;
  success: boolean;
  errors: string[];
}

export type KillSwitchResponse = DataResponse<KillSwitchResult>;

// ============================================================================
// Backtest
// ============================================================================

export interface BacktestResult {
  strategy_id: number;
  start_date: string;
  end_date: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  total_pnl: number;
  max_drawdown: number;
  win_rate: number;
  avg_profit: number;
  avg_loss: number;
  sharpe_ratio?: number;
  trades: Record<string, any>[];
}

export type BacktestResponse = DataResponse<BacktestResult>;

// ============================================================================
// Condition State
// ============================================================================

export interface ConditionEvaluation {
  condition_id: string;
  condition_type: string;
  rule_name?: string;
  variable: string;
  operator: string;
  target_value: any;
  current_value: any;
  is_satisfied: boolean;
  progress_pct?: number;
  distance_to_trigger?: string;
  evaluated_at: string;
}

export interface ConditionStateResponse {
  strategy_id: number;
  strategy_status: string;
  entry_conditions: ConditionEvaluation[];
  adjustment_rules: Record<string, ConditionEvaluation[]>;
  last_updated: string;
}
```

### 12.4 WebSocket Types

```typescript
// src/types/autopilot/websocket.ts

export enum WSEventType {
  STRATEGY_STATE_UPDATE = 'strategy_state_update',
  STRATEGY_STATUS_CHANGE = 'strategy_status_change',
  CONDITION_PROGRESS = 'condition_progress',
  CONDITION_TRIGGERED = 'condition_triggered',
  ORDER_PLACED = 'order_placed',
  ORDER_FILLED = 'order_filled',
  ORDER_REJECTED = 'order_rejected',
  ORDER_CANCELLED = 'order_cancelled',
  ACTIVITY = 'activity',
  CONFIRMATION_REQUIRED = 'confirmation_required',
  CONFIRMATION_TIMEOUT = 'confirmation_timeout',
  RISK_WARNING = 'risk_warning',
  RISK_BREACH = 'risk_breach',
  CONNECTION_STATUS = 'connection_status',
  ERROR = 'error',
  PING = 'ping',
  PONG = 'pong'
}

export interface WSMessage<T = any> {
  type: WSEventType;
  data: T;
  timestamp: string;
  strategy_id?: number;
}

export interface WSStrategyStateUpdate {
  strategy_id: number;
  current_pnl: number;
  margin_used: number;
  positions: any[];
  condition_states: Record<string, any>;
}

export interface WSConditionProgress {
  strategy_id: number;
  condition_id: string;
  condition_type: string;
  rule_name?: string;
  variable: string;
  current_value: any;
  target_value: any;
  progress_pct: number;
  is_satisfied: boolean;
}

export interface WSOrderUpdate {
  order_id: number;
  strategy_id: number;
  tradingsymbol: string;
  status: string;
  executed_price?: number;
  executed_quantity?: number;
  rejection_reason?: string;
}

export interface WSConfirmationRequired {
  strategy_id: number;
  strategy_name: string;
  rule_id: string;
  rule_name: string;
  trigger_reason: Record<string, any>;
  proposed_action: Record<string, any>;
  timeout_seconds: number;
  timeout_action: string;
  created_at: string;
}

export interface WSRiskAlert {
  alert_type: 'warning' | 'breach';
  metric: string;
  current_value: number;
  limit_value: number;
  percentage: number;
  message: string;
}

export interface WSConnectionStatus {
  kite_connected: boolean;
  websocket_connected: boolean;
  last_tick?: string;
}

// Client commands
export interface WSSubscribeCommand {
  action: 'subscribe';
  strategy_ids: number[];
}

export interface WSUnsubscribeCommand {
  action: 'unsubscribe';
  strategy_ids: number[];
}

export interface WSPingCommand {
  action: 'ping';
}

export type WSClientCommand = WSSubscribeCommand | WSUnsubscribeCommand | WSPingCommand;
```

---

## 13. Example Requests

### 13.1 cURL Examples

```bash
# ============================================================================
# AUTHENTICATION
# ============================================================================

# All requests require Bearer token
export TOKEN="your_jwt_token_here"
export BASE_URL="https://api.algochanakya.com/api/v1/autopilot"


# ============================================================================
# STRATEGIES
# ============================================================================

# List strategies
curl -X GET "$BASE_URL/strategies?status=active&page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"

# Create strategy
curl -X POST "$BASE_URL/strategies" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Iron Condor Weekly",
    "underlying": "NIFTY",
    "expiry_type": "current_week",
    "lots": 1,
    "position_type": "intraday",
    "legs_config": [
      {
        "id": "leg_1",
        "contract_type": "PE",
        "transaction_type": "SELL",
        "strike_selection": {"mode": "atm_offset", "offset": -200},
        "quantity_multiplier": 1,
        "execution_order": 1
      },
      {
        "id": "leg_2",
        "contract_type": "PE",
        "transaction_type": "BUY",
        "strike_selection": {"mode": "atm_offset", "offset": -400},
        "quantity_multiplier": 1,
        "execution_order": 2
      },
      {
        "id": "leg_3",
        "contract_type": "CE",
        "transaction_type": "SELL",
        "strike_selection": {"mode": "atm_offset", "offset": 200},
        "quantity_multiplier": 1,
        "execution_order": 3
      },
      {
        "id": "leg_4",
        "contract_type": "CE",
        "transaction_type": "BUY",
        "strike_selection": {"mode": "atm_offset", "offset": 400},
        "quantity_multiplier": 1,
        "execution_order": 4
      }
    ],
    "entry_conditions": {
      "logic": "AND",
      "conditions": [
        {"id": "c1", "enabled": true, "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:20"},
        {"id": "c2", "enabled": true, "variable": "VOLATILITY.VIX", "operator": "between", "value": [13, 18]}
      ]
    },
    "adjustment_rules": [
      {
        "id": "r1",
        "name": "Profit Exit",
        "enabled": true,
        "priority": 1,
        "trigger": {
          "logic": "OR",
          "conditions": [
            {"id": "t1", "variable": "STRATEGY.PNL", "operator": "greater_than", "value": 8000}
          ]
        },
        "action": {
          "type": "exit_all",
          "config": {"order_type": "MARKET"}
        },
        "execution_mode": "auto",
        "timeout_seconds": 60,
        "timeout_action": "skip"
      }
    ]
  }'

# Get strategy
curl -X GET "$BASE_URL/strategies/123" \
  -H "Authorization: Bearer $TOKEN"

# Update strategy
curl -X PUT "$BASE_URL/strategies/123" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Iron Condor Weekly - Updated",
    "lots": 2
  }'

# Activate strategy
curl -X POST "$BASE_URL/strategies/123/activate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true, "paper_trading": false}'

# Pause strategy
curl -X POST "$BASE_URL/strategies/123/pause" \
  -H "Authorization: Bearer $TOKEN"

# Resume strategy
curl -X POST "$BASE_URL/strategies/123/resume" \
  -H "Authorization: Bearer $TOKEN"

# Exit strategy
curl -X POST "$BASE_URL/strategies/123/exit" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true, "exit_type": "market", "reason": "Manual exit"}'

# Clone strategy
curl -X POST "$BASE_URL/strategies/123/clone" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_name": "Iron Condor Copy", "reset_schedule": true}'

# Get condition states
curl -X GET "$BASE_URL/strategies/123/conditions" \
  -H "Authorization: Bearer $TOKEN"

# Run backtest
curl -X POST "$BASE_URL/strategies/123/backtest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-01-01", "end_date": "2025-12-01", "initial_capital": 500000}'

# Confirm pending adjustment
curl -X POST "$BASE_URL/strategies/123/confirm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "confirm"}'


# ============================================================================
# DASHBOARD
# ============================================================================

# Get dashboard summary
curl -X GET "$BASE_URL/dashboard/summary" \
  -H "Authorization: Bearer $TOKEN"

# Get activity feed
curl -X GET "$BASE_URL/dashboard/activity?limit=50" \
  -H "Authorization: Bearer $TOKEN"

# Get risk metrics
curl -X GET "$BASE_URL/dashboard/risk" \
  -H "Authorization: Bearer $TOKEN"


# ============================================================================
# ORDERS
# ============================================================================

# List orders
curl -X GET "$BASE_URL/orders?strategy_id=123&start_date=2025-12-01" \
  -H "Authorization: Bearer $TOKEN"

# Get order details
curl -X GET "$BASE_URL/orders/456" \
  -H "Authorization: Bearer $TOKEN"

# Export orders
curl -X GET "$BASE_URL/orders/export?start_date=2025-12-01&end_date=2025-12-08&format=csv" \
  -H "Authorization: Bearer $TOKEN" \
  -o orders.csv


# ============================================================================
# LOGS
# ============================================================================

# List logs
curl -X GET "$BASE_URL/logs?severity=error&start_date=2025-12-01" \
  -H "Authorization: Bearer $TOKEN"

# Export logs
curl -X GET "$BASE_URL/logs/export?start_date=2025-12-01&end_date=2025-12-08" \
  -H "Authorization: Bearer $TOKEN" \
  -o logs.csv


# ============================================================================
# SETTINGS
# ============================================================================

# Get settings
curl -X GET "$BASE_URL/settings" \
  -H "Authorization: Bearer $TOKEN"

# Update settings
curl -X PUT "$BASE_URL/settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "daily_loss_limit": 25000,
    "max_active_strategies": 5,
    "notification_prefs": {
      "enabled": true,
      "channels": ["in_app"],
      "frequency": "realtime"
    }
  }'


# ============================================================================
# KILL SWITCH
# ============================================================================

# Execute kill switch
curl -X POST "$BASE_URL/kill-switch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm_text": "STOP"}'


# ============================================================================
# TEMPLATES
# ============================================================================

# List templates
curl -X GET "$BASE_URL/templates?category=iron_condor" \
  -H "Authorization: Bearer $TOKEN"

# Create template from strategy config
curl -X POST "$BASE_URL/templates" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Iron Condor Template",
    "description": "Weekly iron condor with VIX filter",
    "strategy_config": {...},
    "category": "iron_condor",
    "tags": ["weekly", "vix_filter"],
    "risk_level": "moderate"
  }'
```

### 13.2 TypeScript/Axios Examples

```typescript
// src/api/autopilot.ts

import axios from 'axios';
import {
  Strategy,
  StrategyCreateRequest,
  StrategyUpdateRequest,
  ActivateRequest,
  ExitRequest
} from '@/types/autopilot/strategy';
import {
  StrategyResponse,
  StrategyListResponse,
  DashboardResponse,
  ActivityFeedResponse,
  KillSwitchResponse
} from '@/types/autopilot/api';

const api = axios.create({
  baseURL: '/api/v1/autopilot',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add auth token to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ============================================================================
// STRATEGIES
// ============================================================================

export const strategyApi = {
  // List strategies
  list: async (params?: {
    status?: string;
    underlying?: string;
    page?: number;
    page_size?: number;
  }): Promise<StrategyListResponse> => {
    const { data } = await api.get('/strategies', { params });
    return data;
  },

  // Create strategy
  create: async (request: StrategyCreateRequest): Promise<StrategyResponse> => {
    const { data } = await api.post('/strategies', request);
    return data;
  },

  // Get strategy
  get: async (id: number): Promise<StrategyResponse> => {
    const { data } = await api.get(`/strategies/${id}`);
    return data;
  },

  // Update strategy
  update: async (id: number, request: StrategyUpdateRequest): Promise<StrategyResponse> => {
    const { data } = await api.put(`/strategies/${id}`, request);
    return data;
  },

  // Delete strategy
  delete: async (id: number): Promise<void> => {
    await api.delete(`/strategies/${id}`);
  },

  // Activate strategy
  activate: async (id: number, request: ActivateRequest): Promise<StrategyResponse> => {
    const { data } = await api.post(`/strategies/${id}/activate`, request);
    return data;
  },

  // Pause strategy
  pause: async (id: number): Promise<StrategyResponse> => {
    const { data } = await api.post(`/strategies/${id}/pause`);
    return data;
  },

  // Resume strategy
  resume: async (id: number): Promise<StrategyResponse> => {
    const { data } = await api.post(`/strategies/${id}/resume`);
    return data;
  },

  // Exit strategy
  exit: async (id: number, request: ExitRequest): Promise<StrategyResponse> => {
    const { data } = await api.post(`/strategies/${id}/exit`, request);
    return data;
  },

  // Clone strategy
  clone: async (id: number, newName?: string): Promise<StrategyResponse> => {
    const { data } = await api.post(`/strategies/${id}/clone`, { new_name: newName });
    return data;
  },

  // Get condition states
  getConditions: async (id: number): Promise<any> => {
    const { data } = await api.get(`/strategies/${id}/conditions`);
    return data;
  },

  // Confirm pending adjustment
  confirm: async (id: number, action: 'confirm' | 'skip' | 'modify', modifications?: any): Promise<StrategyResponse> => {
    const { data } = await api.post(`/strategies/${id}/confirm`, { action, modifications });
    return data;
  }
};

// ============================================================================
// DASHBOARD
// ============================================================================

export const dashboardApi = {
  // Get summary
  getSummary: async (): Promise<DashboardResponse> => {
    const { data } = await api.get('/dashboard/summary');
    return data;
  },

  // Get activity feed
  getActivity: async (params?: {
    limit?: number;
    after_id?: number;
    event_types?: string;
    strategy_id?: number;
  }): Promise<ActivityFeedResponse> => {
    const { data } = await api.get('/dashboard/activity', { params });
    return data;
  },

  // Get risk metrics
  getRisk: async (): Promise<any> => {
    const { data } = await api.get('/dashboard/risk');
    return data;
  }
};

// ============================================================================
// KILL SWITCH
// ============================================================================

export const killSwitch = async (): Promise<KillSwitchResponse> => {
  const { data } = await api.post('/kill-switch', { confirm_text: 'STOP' });
  return data;
};

// ============================================================================
// SETTINGS
// ============================================================================

export const settingsApi = {
  get: async (): Promise<any> => {
    const { data } = await api.get('/settings');
    return data;
  },

  update: async (settings: any): Promise<any> => {
    const { data } = await api.put('/settings', settings);
    return data;
  }
};
```

---

## Appendix: API Quick Reference

### Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| **Strategies** |
| GET | `/strategies` | List strategies |
| POST | `/strategies` | Create strategy |
| GET | `/strategies/{id}` | Get strategy |
| PUT | `/strategies/{id}` | Update strategy |
| DELETE | `/strategies/{id}` | Delete strategy |
| POST | `/strategies/{id}/activate` | Activate |
| POST | `/strategies/{id}/pause` | Pause |
| POST | `/strategies/{id}/resume` | Resume |
| POST | `/strategies/{id}/exit` | Force exit |
| POST | `/strategies/{id}/clone` | Clone |
| GET | `/strategies/{id}/conditions` | Condition states |
| POST | `/strategies/{id}/backtest` | Run backtest |
| POST | `/strategies/{id}/confirm` | Confirm adjustment |
| **Dashboard** |
| GET | `/dashboard/summary` | Summary |
| GET | `/dashboard/activity` | Activity feed |
| GET | `/dashboard/risk` | Risk metrics |
| GET | `/dashboard/performance` | Performance |
| **Orders** |
| GET | `/orders` | List orders |
| GET | `/orders/{id}` | Get order |
| GET | `/orders/export` | Export CSV |
| **Logs** |
| GET | `/logs` | List logs |
| GET | `/logs/{id}` | Get log |
| GET | `/logs/export` | Export CSV |
| **Settings** |
| GET | `/settings` | Get settings |
| PUT | `/settings` | Update settings |
| **Templates** |
| GET | `/templates` | List templates |
| POST | `/templates` | Create template |
| GET | `/templates/{id}` | Get template |
| PUT | `/templates/{id}` | Update template |
| DELETE | `/templates/{id}` | Delete template |
| **Emergency** |
| POST | `/kill-switch` | Kill switch |
| **WebSocket** |
| WS | `/ws/stream` | Real-time updates |

---

**End of API Contracts Document**
