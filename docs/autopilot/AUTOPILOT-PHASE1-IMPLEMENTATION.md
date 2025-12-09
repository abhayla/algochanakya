# AutoPilot Phase 1 - Claude Code Implementation Guide

## Overview

This document provides implementation instructions for Claude Code to build Phase 1 of the AutoPilot feature for AlgoChanakya - an options trading platform with automated strategy execution.

**Project:** AlgoChanakya  
**Feature:** AutoPilot - Auto-execution and adjustment system  
**Phase:** 1 - Core Strategy Builder & Basic Execution  
**Duration:** 4 weeks  

---

## Documentation References

Before starting implementation, read these documentation files in order:

| Priority | Document | Location | Purpose |
|----------|----------|----------|---------|
| 1 | UI/UX Design | `docs/autopilot/ui-ux-design.md` | Screens, flows, wireframes |
| 2 | Database Schema | `docs/autopilot/database-schema.md` | PostgreSQL tables, JSONB structures |
| 3 | API Contracts | `docs/autopilot/api-contracts.md` | FastAPI endpoints, Pydantic models |
| 4 | Component Design | `docs/autopilot/component-design.md` | Vue.js component specifications |

---

## Project Context

### Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | Vue.js 3 (Composition API) | 3.4.x |
| State | Pinia | 2.x |
| Styling | Tailwind CSS | 3.x |
| HTTP | Axios | 1.x |
| Backend | FastAPI | 0.109.x |
| ORM | SQLAlchemy (Async) | 2.0.x |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7.x |
| Broker API | Kite Connect | 5.x |
| WebSocket | FastAPI WebSocket + Kite Ticker | - |

### Existing Project Structure

```
algochanakya/
├── backend/
│   ├── alembic/versions/           # Migrations
│   ├── app/
│   │   ├── api/routes/             # Existing endpoints
│   │   ├── api/v1/autopilot/       # NEW: AutoPilot endpoints
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── services/               # Business logic
│   │   ├── utils/dependencies.py   # Auth dependencies
│   │   └── websocket/              # NEW: WebSocket handlers
│   ├── main.py                     # FastAPI app
│   ├── config.py                   # Settings
│   └── database.py                 # DB connection
│
├── frontend/src/
│   ├── components/autopilot/       # NEW: AutoPilot components
│   ├── composables/autopilot/      # NEW: AutoPilot composables
│   ├── views/autopilot/            # NEW: AutoPilot pages
│   ├── stores/                     # Pinia stores
│   ├── services/api.js             # Axios instance
│   └── router/index.js             # Routes
│
└── tests/
    ├── e2e/specs/autopilot/        # Playwright tests
    └── postman/autopilot-collection.json
```

### Existing Patterns to Follow

**Backend - Route Pattern** (`backend/app/api/routes/strategy.py`):
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.dependencies import get_current_user, get_db
from app.schemas.strategy import StrategyCreate, StrategyResponse

router = APIRouter(prefix="/strategies", tags=["strategies"])

@router.get("/", response_model=list[StrategyResponse])
async def get_strategies(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Implementation
    pass
```

**Frontend - Store Pattern** (`frontend/src/stores/strategy.js`):
```javascript
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useStrategyStore = defineStore('strategy', {
  state: () => ({
    strategies: [],
    currentStrategy: null,
    loading: false,
    error: null
  }),
  
  getters: {
    activeStrategies: (state) => state.strategies.filter(s => s.status === 'active')
  },
  
  actions: {
    async fetchStrategies() {
      this.loading = true
      try {
        const response = await api.get('/strategies')
        this.strategies = response.data
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    }
  }
})
```

**Frontend - Component Pattern** (`frontend/src/components/strategy/StrategyLegRow.vue`):
```vue
<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  leg: { type: Object, required: true },
  index: { type: Number, required: true }
})

const emit = defineEmits(['update', 'delete'])

// Component logic
</script>

<template>
  <div class="flex items-center gap-4 p-4 bg-white rounded-lg shadow">
    <!-- Template -->
  </div>
</template>
```

---

## Phase 1 Scope

### What to Build

| Component | Priority | Description |
|-----------|----------|-------------|
| Database Migration | P0 | Run existing migration to create tables |
| User Settings API | P0 | GET/PUT settings endpoints |
| Strategy CRUD API | P0 | Create, Read, Update, Delete strategies |
| Strategy Activate/Pause | P0 | Lifecycle management |
| Dashboard API | P1 | Summary endpoint |
| AutoPilot Pinia Store | P0 | State management |
| Dashboard View | P1 | Basic dashboard with strategy cards |
| Strategy Builder View | P0 | Multi-step form wizard |
| Settings View | P1 | User settings page |
| Basic WebSocket | P2 | Connection setup (no real-time updates yet) |

### What NOT to Build in Phase 1

- Real-time condition monitoring
- Automatic order execution
- Adjustment rules execution
- Semi-auto confirmation flow
- Kill switch functionality
- Templates system
- Analytics/reporting
- Backtest functionality

---

## Implementation Tasks

### Task 1: Database Setup

**Objective:** Run migration and verify tables created.

```bash
cd backend
source venv/bin/activate  # Windows: .\venv\Scripts\Activate
alembic upgrade head
```

**Verify tables exist:**
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_name LIKE 'autopilot_%';
```

Expected tables:
- `autopilot_user_settings`
- `autopilot_strategies`
- `autopilot_orders`
- `autopilot_logs`
- `autopilot_condition_eval`
- `autopilot_daily_summary`
- `autopilot_templates`

---

### Task 2: Backend - SQLAlchemy Models

**File:** `backend/app/models/autopilot.py`

Create SQLAlchemy models matching the database schema. Reference `docs/autopilot/database-schema.md`.

```python
"""
AutoPilot SQLAlchemy Models

Reference: docs/autopilot/database-schema.md
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column, BigInteger, String, Integer, Boolean, Numeric, 
    Date, DateTime, ForeignKey, Text, Enum, CheckConstraint,
    UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
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
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
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
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
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
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
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
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
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
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
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
```

**Update User model** (`backend/app/models/user.py`):
```python
# Add to existing User model
autopilot_settings = relationship("AutoPilotUserSettings", back_populates="user", uselist=False)
autopilot_strategies = relationship("AutoPilotStrategy", back_populates="user")
```

---

### Task 3: Backend - Pydantic Schemas

**File:** `backend/app/schemas/autopilot.py`

Create Pydantic schemas for request/response validation. Reference `docs/autopilot/api-contracts.md`.

```python
"""
AutoPilot Pydantic Schemas

Reference: docs/autopilot/api-contracts.md
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union
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
    user_id: int
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
```

---

### Task 4: Backend - API Routes

**File:** `backend/app/api/v1/autopilot/router.py`

```python
"""
AutoPilot API Router

Reference: docs/autopilot/api-contracts.md
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.utils.dependencies import get_current_user, get_db
from app.models.autopilot import (
    AutoPilotStrategy, AutoPilotUserSettings, AutoPilotOrder, AutoPilotLog
)
from app.schemas.autopilot import (
    StrategyCreateRequest, StrategyUpdateRequest, StrategyResponse, 
    StrategyListItem, ActivateRequest, ExitRequest, CloneRequest,
    UserSettingsResponse, UserSettingsUpdateRequest,
    DashboardSummary, RiskMetrics, DataResponse, PaginatedResponse
)

router = APIRouter(prefix="/autopilot", tags=["autopilot"])


# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@router.get("/settings", response_model=DataResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get user's AutoPilot settings."""
    result = await db.execute(
        select(AutoPilotUserSettings).where(
            AutoPilotUserSettings.user_id == current_user.id
        )
    )
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Create default settings
        settings = AutoPilotUserSettings(
            user_id=current_user.id,
            default_order_settings={
                "order_type": "MARKET",
                "execution_style": "sequential",
                "delay_between_legs": 2
            },
            notification_prefs={
                "enabled": True,
                "channels": ["in_app"]
            },
            failure_handling={
                "on_network_error": "retry",
                "max_retries": 3
            }
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return DataResponse(
        data=UserSettingsResponse.model_validate(settings),
        timestamp=datetime.utcnow()
    )


@router.put("/settings", response_model=DataResponse)
async def update_settings(
    request: UserSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update user's AutoPilot settings."""
    result = await db.execute(
        select(AutoPilotUserSettings).where(
            AutoPilotUserSettings.user_id == current_user.id
        )
    )
    settings = result.scalar_one_or_none()
    
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    # Validate constraints
    update_data = request.model_dump(exclude_unset=True)
    
    if 'per_strategy_loss_limit' in update_data and 'daily_loss_limit' in update_data:
        if update_data['per_strategy_loss_limit'] > update_data['daily_loss_limit']:
            raise HTTPException(
                status_code=400, 
                detail="per_strategy_loss_limit cannot exceed daily_loss_limit"
            )
    
    # Apply updates
    for key, value in update_data.items():
        setattr(settings, key, value)
    
    await db.commit()
    await db.refresh(settings)
    
    return DataResponse(
        message="Settings updated successfully",
        data=UserSettingsResponse.model_validate(settings),
        timestamp=datetime.utcnow()
    )


# ============================================================================
# STRATEGY ENDPOINTS
# ============================================================================

@router.get("/strategies", response_model=PaginatedResponse)
async def list_strategies(
    status: Optional[str] = None,
    underlying: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List user's AutoPilot strategies with pagination."""
    query = select(AutoPilotStrategy).where(
        AutoPilotStrategy.user_id == current_user.id
    )
    
    # Apply filters
    if status:
        query = query.where(AutoPilotStrategy.status == status)
    if underlying:
        query = query.where(AutoPilotStrategy.underlying == underlying)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = getattr(AutoPilotStrategy, sort_by, AutoPilotStrategy.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    strategies = result.scalars().all()
    
    # Convert to list items
    items = []
    for s in strategies:
        items.append(StrategyListItem(
            id=s.id,
            name=s.name,
            status=s.status,
            underlying=s.underlying,
            lots=s.lots,
            leg_count=len(s.legs_config) if s.legs_config else 0,
            current_pnl=s.runtime_state.get('current_pnl') if s.runtime_state else None,
            margin_used=s.runtime_state.get('margin_used') if s.runtime_state else None,
            priority=s.priority,
            created_at=s.created_at,
            updated_at=s.updated_at
        ))
    
    total_pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.post("/strategies", response_model=DataResponse, status_code=201)
async def create_strategy(
    request: StrategyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new AutoPilot strategy."""
    # Check strategy count limit
    count_result = await db.execute(
        select(func.count()).where(
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy_count = count_result.scalar()
    
    if strategy_count >= 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 strategies allowed per user"
        )
    
    # Create strategy
    strategy = AutoPilotStrategy(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        status="draft",
        underlying=request.underlying.value,
        expiry_type=request.expiry_type.value,
        expiry_date=request.expiry_date,
        lots=request.lots,
        position_type=request.position_type.value,
        legs_config=[leg.model_dump() for leg in request.legs_config],
        entry_conditions=request.entry_conditions.model_dump(),
        adjustment_rules=request.adjustment_rules,
        order_settings=request.order_settings.model_dump() if request.order_settings else {},
        risk_settings=request.risk_settings.model_dump() if request.risk_settings else {},
        schedule_config=request.schedule_config.model_dump() if request.schedule_config else {},
        priority=request.priority,
        source_template_id=request.source_template_id
    )
    
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    
    # Log creation
    log = AutoPilotLog(
        user_id=current_user.id,
        strategy_id=strategy.id,
        event_type="strategy_created",
        severity="info",
        message=f"Strategy '{strategy.name}' created",
        event_data={"strategy_id": strategy.id, "name": strategy.name}
    )
    db.add(log)
    await db.commit()
    
    return DataResponse(
        message="Strategy created successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.get("/strategies/{strategy_id}", response_model=DataResponse)
async def get_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get strategy details."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return DataResponse(
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.put("/strategies/{strategy_id}", response_model=DataResponse)
async def update_strategy(
    strategy_id: int,
    request: StrategyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update strategy configuration."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Only allow updates for draft/paused strategies
    if strategy.status not in ["draft", "paused"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update strategy in '{strategy.status}' status"
        )
    
    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == 'legs_config' and value:
            value = [leg.model_dump() if hasattr(leg, 'model_dump') else leg for leg in value]
        elif key in ['entry_conditions', 'order_settings', 'risk_settings', 'schedule_config'] and value:
            value = value.model_dump() if hasattr(value, 'model_dump') else value
        setattr(strategy, key, value)
    
    await db.commit()
    await db.refresh(strategy)
    
    return DataResponse(
        message="Strategy updated successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.delete("/strategies/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Only allow deletion for draft/completed/error strategies
    if strategy.status not in ["draft", "completed", "error"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete strategy in '{strategy.status}' status. Pause or exit first."
        )
    
    await db.delete(strategy)
    await db.commit()


@router.post("/strategies/{strategy_id}/activate", response_model=DataResponse)
async def activate_strategy(
    strategy_id: int,
    request: ActivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Activate a draft strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if strategy.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot activate strategy in '{strategy.status}' status"
        )
    
    # Check max active strategies
    settings_result = await db.execute(
        select(AutoPilotUserSettings).where(
            AutoPilotUserSettings.user_id == current_user.id
        )
    )
    settings = settings_result.scalar_one_or_none()
    max_active = settings.max_active_strategies if settings else 3
    
    active_count_result = await db.execute(
        select(func.count()).where(
            AutoPilotStrategy.user_id == current_user.id,
            AutoPilotStrategy.status.in_(["waiting", "active", "pending"])
        )
    )
    active_count = active_count_result.scalar()
    
    if active_count >= max_active:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum active strategies limit ({max_active}) reached"
        )
    
    # Activate
    strategy.status = "waiting"
    strategy.activated_at = datetime.utcnow()
    strategy.runtime_state = {
        "paper_trading": request.paper_trading,
        "current_pnl": 0,
        "margin_used": 0,
        "current_positions": [],
        "adjustments_made": []
    }
    
    await db.commit()
    await db.refresh(strategy)
    
    # Log activation
    log = AutoPilotLog(
        user_id=current_user.id,
        strategy_id=strategy.id,
        event_type="strategy_activated",
        severity="info",
        message=f"Strategy '{strategy.name}' activated",
        event_data={"paper_trading": request.paper_trading}
    )
    db.add(log)
    await db.commit()
    
    return DataResponse(
        message="Strategy activated successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.post("/strategies/{strategy_id}/pause", response_model=DataResponse)
async def pause_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Pause an active strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if strategy.status not in ["waiting", "active", "pending"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause strategy in '{strategy.status}' status"
        )
    
    strategy.status = "paused"
    await db.commit()
    await db.refresh(strategy)
    
    return DataResponse(
        message="Strategy paused successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.post("/strategies/{strategy_id}/resume", response_model=DataResponse)
async def resume_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Resume a paused strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if strategy.status != "paused":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume strategy in '{strategy.status}' status"
        )
    
    # Resume to waiting (will become active when conditions met)
    strategy.status = "waiting"
    await db.commit()
    await db.refresh(strategy)
    
    return DataResponse(
        message="Strategy resumed successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.post("/strategies/{strategy_id}/clone", response_model=DataResponse, status_code=201)
async def clone_strategy(
    strategy_id: int,
    request: CloneRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Clone an existing strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    original = result.scalar_one_or_none()
    
    if not original:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Create clone
    clone_name = request.new_name or f"{original.name} (Copy)"
    
    clone = AutoPilotStrategy(
        user_id=current_user.id,
        name=clone_name,
        description=original.description,
        status="draft",
        underlying=original.underlying,
        expiry_type=original.expiry_type,
        expiry_date=None if request.reset_schedule else original.expiry_date,
        lots=original.lots,
        position_type=original.position_type,
        legs_config=original.legs_config,
        entry_conditions=original.entry_conditions,
        adjustment_rules=original.adjustment_rules,
        order_settings=original.order_settings,
        risk_settings=original.risk_settings,
        schedule_config=original.schedule_config,
        priority=original.priority,
        cloned_from_id=original.id
    )
    
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    
    return DataResponse(
        message="Strategy cloned successfully",
        data=StrategyResponse.model_validate(clone),
        timestamp=datetime.utcnow()
    )


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get("/dashboard/summary", response_model=DataResponse)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get dashboard summary."""
    # Get strategy counts
    strategies_result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategies = strategies_result.scalars().all()
    
    active_strategies = [s for s in strategies if s.status == "active"]
    waiting_strategies = [s for s in strategies if s.status == "waiting"]
    pending_strategies = [s for s in strategies if s.status == "pending"]
    
    # Calculate P&L
    today_realized = sum(
        float(s.runtime_state.get('realized_pnl', 0) or 0) 
        for s in strategies if s.runtime_state
    )
    today_unrealized = sum(
        float(s.runtime_state.get('current_pnl', 0) or 0) 
        for s in strategies if s.runtime_state and s.status in ['active', 'waiting']
    )
    
    # Get settings for risk metrics
    settings_result = await db.execute(
        select(AutoPilotUserSettings).where(
            AutoPilotUserSettings.user_id == current_user.id
        )
    )
    settings = settings_result.scalar_one_or_none()
    
    daily_loss_limit = float(settings.daily_loss_limit) if settings else 20000
    max_capital = float(settings.max_capital_deployed) if settings else 500000
    max_active = settings.max_active_strategies if settings else 3
    
    capital_used = sum(
        float(s.runtime_state.get('margin_used', 0) or 0)
        for s in strategies if s.runtime_state and s.status in ['active', 'waiting', 'pending']
    )
    
    # Determine risk status
    loss_pct = abs(min(today_realized + today_unrealized, 0)) / daily_loss_limit * 100 if daily_loss_limit else 0
    if loss_pct >= 90:
        risk_status = "critical"
    elif loss_pct >= 70:
        risk_status = "warning"
    else:
        risk_status = "safe"
    
    risk_metrics = RiskMetrics(
        daily_loss_limit=daily_loss_limit,
        daily_loss_used=abs(min(today_realized + today_unrealized, 0)),
        daily_loss_pct=loss_pct,
        max_capital=max_capital,
        capital_used=capital_used,
        capital_pct=(capital_used / max_capital * 100) if max_capital else 0,
        max_active_strategies=max_active,
        active_strategies_count=len(active_strategies) + len(waiting_strategies) + len(pending_strategies),
        status=risk_status
    )
    
    # Convert strategies to list items
    strategy_items = []
    for s in strategies:
        if s.status in ['active', 'waiting', 'pending', 'paused']:
            strategy_items.append(StrategyListItem(
                id=s.id,
                name=s.name,
                status=s.status,
                underlying=s.underlying,
                lots=s.lots,
                leg_count=len(s.legs_config) if s.legs_config else 0,
                current_pnl=s.runtime_state.get('current_pnl') if s.runtime_state else None,
                margin_used=s.runtime_state.get('margin_used') if s.runtime_state else None,
                priority=s.priority,
                created_at=s.created_at,
                updated_at=s.updated_at
            ))
    
    summary = DashboardSummary(
        active_strategies=len(active_strategies),
        waiting_strategies=len(waiting_strategies),
        pending_confirmations=len(pending_strategies),
        today_realized_pnl=today_realized,
        today_unrealized_pnl=today_unrealized,
        today_total_pnl=today_realized + today_unrealized,
        risk_metrics=risk_metrics,
        strategies=strategy_items,
        kite_connected=True,  # TODO: Check actual connection
        websocket_connected=True,  # TODO: Check actual connection
        last_update=datetime.utcnow()
    )
    
    return DataResponse(
        data=summary,
        timestamp=datetime.utcnow()
    )
```

**File:** `backend/app/api/v1/autopilot/__init__.py`

```python
from .router import router

__all__ = ["router"]
```

**Register router in main.py:**
```python
# Add to backend/main.py
from app.api.v1.autopilot import router as autopilot_router

app.include_router(autopilot_router, prefix="/api/v1")
```

---

### Task 5: Frontend - Pinia Store

**File:** `frontend/src/stores/autopilot.js`

```javascript
/**
 * AutoPilot Pinia Store
 * 
 * Reference: docs/autopilot/component-design.md
 */
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useAutopilotStore = defineStore('autopilot', {
  state: () => ({
    // Strategies
    strategies: [],
    currentStrategy: null,
    
    // Dashboard
    dashboardSummary: null,
    
    // Settings
    settings: null,
    
    // UI State
    loading: false,
    saving: false,
    error: null,
    
    // Pagination
    pagination: {
      page: 1,
      pageSize: 20,
      total: 0,
      totalPages: 0
    },
    
    // Filters
    filters: {
      status: null,
      underlying: null
    },
    
    // Builder State
    builder: {
      step: 1,
      strategy: createEmptyStrategy(),
      validation: {}
    }
  }),

  getters: {
    activeStrategies: (state) => 
      state.strategies.filter(s => ['active', 'waiting', 'pending'].includes(s.status)),
    
    draftStrategies: (state) => 
      state.strategies.filter(s => s.status === 'draft'),
    
    completedStrategies: (state) => 
      state.strategies.filter(s => ['completed', 'error', 'expired'].includes(s.status)),
    
    hasActiveStrategies: (state) => 
      state.strategies.some(s => ['active', 'waiting', 'pending'].includes(s.status)),
    
    todayPnL: (state) => 
      state.dashboardSummary?.today_total_pnl || 0,
    
    riskStatus: (state) => 
      state.dashboardSummary?.risk_metrics?.status || 'safe',
    
    isKiteConnected: (state) => 
      state.dashboardSummary?.kite_connected || false,
    
    canCreateStrategy: (state) => {
      if (!state.settings || !state.dashboardSummary) return true
      const active = state.dashboardSummary.active_strategies + 
                     state.dashboardSummary.waiting_strategies
      return active < state.settings.max_active_strategies
    }
  },

  actions: {
    // ========================================================================
    // STRATEGIES
    // ========================================================================
    
    async fetchStrategies(options = {}) {
      this.loading = true
      this.error = null
      
      try {
        const params = {
          page: options.page || this.pagination.page,
          page_size: options.pageSize || this.pagination.pageSize,
          ...this.filters
        }
        
        // Remove null values
        Object.keys(params).forEach(key => {
          if (params[key] === null) delete params[key]
        })
        
        const response = await api.get('/api/v1/autopilot/strategies', { params })
        
        this.strategies = response.data.data
        this.pagination = {
          page: response.data.page,
          pageSize: response.data.page_size,
          total: response.data.total,
          totalPages: response.data.total_pages
        }
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async fetchStrategy(id) {
      this.loading = true
      this.error = null
      
      try {
        const response = await api.get(`/api/v1/autopilot/strategies/${id}`)
        this.currentStrategy = response.data.data
        return this.currentStrategy
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async createStrategy(strategyData) {
      this.saving = true
      this.error = null
      
      try {
        const response = await api.post('/api/v1/autopilot/strategies', strategyData)
        const newStrategy = response.data.data
        
        // Add to list
        this.strategies.unshift(newStrategy)
        
        return newStrategy
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },
    
    async updateStrategy(id, updates) {
      this.saving = true
      this.error = null
      
      try {
        const response = await api.put(`/api/v1/autopilot/strategies/${id}`, updates)
        const updated = response.data.data
        
        // Update in list
        const index = this.strategies.findIndex(s => s.id === id)
        if (index !== -1) {
          this.strategies[index] = updated
        }
        
        // Update current if same
        if (this.currentStrategy?.id === id) {
          this.currentStrategy = updated
        }
        
        return updated
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },
    
    async deleteStrategy(id) {
      this.saving = true
      this.error = null
      
      try {
        await api.delete(`/api/v1/autopilot/strategies/${id}`)
        
        // Remove from list
        this.strategies = this.strategies.filter(s => s.id !== id)
        
        // Clear current if same
        if (this.currentStrategy?.id === id) {
          this.currentStrategy = null
        }
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },
    
    async activateStrategy(id, options = {}) {
      this.saving = true
      this.error = null
      
      try {
        const response = await api.post(`/api/v1/autopilot/strategies/${id}/activate`, {
          confirm: true,
          paper_trading: options.paperTrading || false
        })
        
        const updated = response.data.data
        this.updateStrategyInList(id, updated)
        
        return updated
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },
    
    async pauseStrategy(id) {
      this.saving = true
      this.error = null
      
      try {
        const response = await api.post(`/api/v1/autopilot/strategies/${id}/pause`)
        const updated = response.data.data
        this.updateStrategyInList(id, updated)
        return updated
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },
    
    async resumeStrategy(id) {
      this.saving = true
      this.error = null
      
      try {
        const response = await api.post(`/api/v1/autopilot/strategies/${id}/resume`)
        const updated = response.data.data
        this.updateStrategyInList(id, updated)
        return updated
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },
    
    async cloneStrategy(id, newName = null) {
      this.saving = true
      this.error = null
      
      try {
        const response = await api.post(`/api/v1/autopilot/strategies/${id}/clone`, {
          new_name: newName,
          reset_schedule: true
        })
        
        const cloned = response.data.data
        this.strategies.unshift(cloned)
        
        return cloned
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },
    
    // ========================================================================
    // DASHBOARD
    // ========================================================================
    
    async fetchDashboardSummary() {
      this.loading = true
      this.error = null
      
      try {
        const response = await api.get('/api/v1/autopilot/dashboard/summary')
        this.dashboardSummary = response.data.data
        return this.dashboardSummary
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // ========================================================================
    // SETTINGS
    // ========================================================================
    
    async fetchSettings() {
      this.loading = true
      this.error = null
      
      try {
        const response = await api.get('/api/v1/autopilot/settings')
        this.settings = response.data.data
        return this.settings
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async updateSettings(updates) {
      this.saving = true
      this.error = null
      
      try {
        const response = await api.put('/api/v1/autopilot/settings', updates)
        this.settings = response.data.data
        return this.settings
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },
    
    // ========================================================================
    // BUILDER
    // ========================================================================
    
    initBuilder(strategy = null) {
      if (strategy) {
        this.builder.strategy = { ...strategy }
      } else {
        this.builder.strategy = createEmptyStrategy()
      }
      this.builder.step = 1
      this.builder.validation = {}
    },
    
    setBuilderStep(step) {
      this.builder.step = step
    },
    
    updateBuilderStrategy(updates) {
      this.builder.strategy = {
        ...this.builder.strategy,
        ...updates
      }
    },
    
    addLeg(leg) {
      this.builder.strategy.legs_config.push({
        id: `leg_${Date.now()}`,
        ...leg
      })
    },
    
    updateLeg(index, updates) {
      if (this.builder.strategy.legs_config[index]) {
        this.builder.strategy.legs_config[index] = {
          ...this.builder.strategy.legs_config[index],
          ...updates
        }
      }
    },
    
    removeLeg(index) {
      this.builder.strategy.legs_config.splice(index, 1)
    },
    
    addCondition(condition) {
      this.builder.strategy.entry_conditions.conditions.push({
        id: `cond_${Date.now()}`,
        enabled: true,
        ...condition
      })
    },
    
    updateCondition(index, updates) {
      if (this.builder.strategy.entry_conditions.conditions[index]) {
        this.builder.strategy.entry_conditions.conditions[index] = {
          ...this.builder.strategy.entry_conditions.conditions[index],
          ...updates
        }
      }
    },
    
    removeCondition(index) {
      this.builder.strategy.entry_conditions.conditions.splice(index, 1)
    },
    
    // ========================================================================
    // HELPERS
    // ========================================================================
    
    updateStrategyInList(id, updated) {
      const index = this.strategies.findIndex(s => s.id === id)
      if (index !== -1) {
        this.strategies[index] = updated
      }
      if (this.currentStrategy?.id === id) {
        this.currentStrategy = updated
      }
    },
    
    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
    },
    
    clearFilters() {
      this.filters = { status: null, underlying: null }
    },
    
    clearError() {
      this.error = null
    }
  }
})

// Helper function to create empty strategy
function createEmptyStrategy() {
  return {
    name: '',
    description: '',
    underlying: 'NIFTY',
    expiry_type: 'current_week',
    expiry_date: null,
    lots: 1,
    position_type: 'intraday',
    legs_config: [],
    entry_conditions: {
      logic: 'AND',
      conditions: []
    },
    adjustment_rules: [],
    order_settings: {
      order_type: 'MARKET',
      execution_style: 'sequential',
      leg_sequence: [],
      delay_between_legs: 2,
      slippage_protection: {
        enabled: true,
        max_per_leg_pct: 2.0,
        max_total_pct: 5.0,
        on_exceed: 'retry',
        max_retries: 3
      },
      on_leg_failure: 'stop'
    },
    risk_settings: {
      max_loss: null,
      max_loss_pct: null,
      trailing_stop: { enabled: false },
      max_margin: null,
      time_stop: null
    },
    schedule_config: {
      activation_mode: 'always',
      active_days: ['MON', 'TUE', 'WED', 'THU', 'FRI'],
      start_time: '09:15',
      end_time: '15:30',
      expiry_days_only: false
    },
    priority: 100
  }
}
```

---

### Task 6: Frontend - Vue Router

**File:** Update `frontend/src/router/index.js`

```javascript
// Add AutoPilot routes
{
  path: '/autopilot',
  name: 'AutoPilot',
  component: () => import('@/views/autopilot/DashboardView.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/autopilot/strategies/new',
  name: 'AutoPilotStrategyBuilder',
  component: () => import('@/views/autopilot/StrategyBuilderView.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/autopilot/strategies/:id',
  name: 'AutoPilotStrategyDetail',
  component: () => import('@/views/autopilot/StrategyDetailView.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/autopilot/strategies/:id/edit',
  name: 'AutoPilotStrategyEdit',
  component: () => import('@/views/autopilot/StrategyBuilderView.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/autopilot/settings',
  name: 'AutoPilotSettings',
  component: () => import('@/views/autopilot/SettingsView.vue'),
  meta: { requiresAuth: true }
}
```

---

### Task 7: Frontend - Views

Create basic view components. Reference `docs/autopilot/ui-ux-design.md` and `docs/autopilot/component-design.md`.

**File:** `frontend/src/views/autopilot/DashboardView.vue`

```vue
<script setup>
/**
 * AutoPilot Dashboard View
 * 
 * Reference: docs/autopilot/ui-ux-design.md - Screen 1
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'

const router = useRouter()
const store = useAutopilotStore()

const refreshInterval = ref(null)

onMounted(async () => {
  await store.fetchDashboardSummary()
  await store.fetchStrategies()
  
  // Refresh every 5 seconds
  refreshInterval.value = setInterval(() => {
    store.fetchDashboardSummary()
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})

const navigateToBuilder = () => {
  router.push('/autopilot/strategies/new')
}

const navigateToStrategy = (id) => {
  router.push(`/autopilot/strategies/${id}`)
}

const handlePause = async (strategy) => {
  if (confirm(`Pause strategy "${strategy.name}"?`)) {
    await store.pauseStrategy(strategy.id)
  }
}

const handleResume = async (strategy) => {
  await store.resumeStrategy(strategy.id)
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(value)
}

const getPnLClass = (value) => {
  if (value > 0) return 'text-green-600'
  if (value < 0) return 'text-red-600'
  return 'text-gray-600'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    active: 'bg-green-100 text-green-800',
    waiting: 'bg-yellow-100 text-yellow-800',
    pending: 'bg-orange-100 text-orange-800',
    paused: 'bg-gray-100 text-gray-800',
    draft: 'bg-blue-100 text-blue-800',
    completed: 'bg-purple-100 text-purple-800',
    error: 'bg-red-100 text-red-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}
</script>

<template>
  <div class="p-6">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">AutoPilot Dashboard</h1>
        <p class="text-gray-500 mt-1">Automated options trading strategies</p>
      </div>
      <button
        @click="navigateToBuilder"
        :disabled="!store.canCreateStrategy"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        + New Strategy
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="store.loading && !store.dashboardSummary" class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-500">Loading dashboard...</p>
    </div>

    <!-- Dashboard Content -->
    <template v-else-if="store.dashboardSummary">
      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <!-- Today's P&L -->
        <div class="bg-white rounded-lg shadow p-4">
          <p class="text-sm text-gray-500">Today's P&L</p>
          <p :class="['text-2xl font-bold', getPnLClass(store.dashboardSummary.today_total_pnl)]">
            {{ formatCurrency(store.dashboardSummary.today_total_pnl) }}
          </p>
        </div>

        <!-- Active Strategies -->
        <div class="bg-white rounded-lg shadow p-4">
          <p class="text-sm text-gray-500">Active Strategies</p>
          <p class="text-2xl font-bold text-gray-900">
            {{ store.dashboardSummary.active_strategies + store.dashboardSummary.waiting_strategies }}
            <span class="text-sm font-normal text-gray-500">
              / {{ store.dashboardSummary.risk_metrics.max_active_strategies }}
            </span>
          </p>
        </div>

        <!-- Daily Loss Limit -->
        <div class="bg-white rounded-lg shadow p-4">
          <p class="text-sm text-gray-500">Daily Loss Used</p>
          <p class="text-2xl font-bold text-gray-900">
            {{ store.dashboardSummary.risk_metrics.daily_loss_pct.toFixed(0) }}%
          </p>
          <div class="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div 
              class="h-2 rounded-full transition-all"
              :class="{
                'bg-green-500': store.dashboardSummary.risk_metrics.status === 'safe',
                'bg-yellow-500': store.dashboardSummary.risk_metrics.status === 'warning',
                'bg-red-500': store.dashboardSummary.risk_metrics.status === 'critical'
              }"
              :style="{ width: Math.min(store.dashboardSummary.risk_metrics.daily_loss_pct, 100) + '%' }"
            ></div>
          </div>
        </div>

        <!-- Connection Status -->
        <div class="bg-white rounded-lg shadow p-4">
          <p class="text-sm text-gray-500">Broker Status</p>
          <div class="flex items-center mt-1">
            <span 
              class="h-3 w-3 rounded-full mr-2"
              :class="store.dashboardSummary.kite_connected ? 'bg-green-500' : 'bg-red-500'"
            ></span>
            <span class="text-lg font-medium">
              {{ store.dashboardSummary.kite_connected ? 'Connected' : 'Disconnected' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Strategies List -->
      <div class="bg-white rounded-lg shadow">
        <div class="p-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold">Strategies</h2>
        </div>

        <div v-if="store.strategies.length === 0" class="p-8 text-center">
          <p class="text-gray-500 mb-4">No strategies yet. Create your first AutoPilot strategy!</p>
          <button
            @click="navigateToBuilder"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Create Strategy
          </button>
        </div>

        <div v-else class="divide-y divide-gray-200">
          <div
            v-for="strategy in store.strategies"
            :key="strategy.id"
            class="p-4 hover:bg-gray-50 cursor-pointer"
            @click="navigateToStrategy(strategy.id)"
          >
            <div class="flex justify-between items-start">
              <div>
                <div class="flex items-center gap-2">
                  <h3 class="font-medium text-gray-900">{{ strategy.name }}</h3>
                  <span 
                    :class="['px-2 py-0.5 text-xs rounded-full', getStatusBadgeClass(strategy.status)]"
                  >
                    {{ strategy.status }}
                  </span>
                </div>
                <p class="text-sm text-gray-500 mt-1">
                  {{ strategy.underlying }} • {{ strategy.lots }} lot(s) • {{ strategy.leg_count }} legs
                </p>
              </div>
              
              <div class="text-right">
                <p :class="['font-medium', getPnLClass(strategy.current_pnl)]">
                  {{ formatCurrency(strategy.current_pnl) }}
                </p>
                <div class="flex gap-2 mt-2" @click.stop>
                  <button
                    v-if="['active', 'waiting', 'pending'].includes(strategy.status)"
                    @click="handlePause(strategy)"
                    class="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200"
                  >
                    Pause
                  </button>
                  <button
                    v-if="strategy.status === 'paused'"
                    @click="handleResume(strategy)"
                    class="px-2 py-1 text-xs bg-green-100 text-green-800 rounded hover:bg-green-200"
                  >
                    Resume
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Error State -->
    <div v-if="store.error" class="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
      <p class="text-red-800">{{ store.error }}</p>
      <button @click="store.clearError" class="text-red-600 underline mt-2">Dismiss</button>
    </div>
  </div>
</template>
```

**Additional views to create:**
- `frontend/src/views/autopilot/StrategyBuilderView.vue` - Multi-step wizard
- `frontend/src/views/autopilot/StrategyDetailView.vue` - Strategy monitoring
- `frontend/src/views/autopilot/SettingsView.vue` - User settings

See `docs/autopilot/component-design.md` for detailed component specifications.

---

## Phase 1 Completion Checklist

### Backend ✓
- [ ] Run Alembic migration
- [ ] Create SQLAlchemy models (`app/models/autopilot.py`)
- [ ] Create Pydantic schemas (`app/schemas/autopilot.py`)
- [ ] Create API router (`app/api/v1/autopilot/router.py`)
- [ ] Register router in `main.py`
- [ ] Test with Postman collection

### Frontend ✓
- [ ] Create Pinia store (`stores/autopilot.js`)
- [ ] Add routes to router
- [ ] Create DashboardView
- [ ] Create StrategyBuilderView (basic multi-step form)
- [ ] Create StrategyDetailView
- [ ] Create SettingsView

### Testing ✓
- [ ] Import Postman collection
- [ ] Test all CRUD endpoints
- [ ] Test strategy lifecycle (create → activate → pause → resume)
- [ ] Verify dashboard data

---

## Code Quality Guidelines

1. **Follow existing patterns** - Match the coding style of existing files
2. **Use async/await** - All database operations are async
3. **Proper error handling** - Use HTTPException with meaningful messages
4. **Type hints** - Add Python type hints everywhere
5. **Comments** - Add docstrings to all functions
6. **Validation** - Use Pydantic validators for complex rules
7. **Logging** - Log important events to AutoPilotLog table

---

## Testing Commands

```bash
# Backend tests
cd backend
pytest tests/autopilot/ -v

# Run specific test
pytest tests/autopilot/test_strategies.py -v

# Frontend dev server
cd frontend
npm run dev

# E2E tests
npx playwright test tests/e2e/specs/autopilot/
```

---

## Questions for Clarification

If you need clarification during implementation:

1. Check the documentation files first
2. Look at existing similar code in the project
3. Ask for clarification with specific context

---

## Success Criteria

Phase 1 is complete when:

1. ✅ User can create a strategy with legs and entry conditions
2. ✅ User can activate/pause/resume strategies
3. ✅ Dashboard shows strategy status and P&L
4. ✅ Settings page allows configuration
5. ✅ All API endpoints return correct responses
6. ✅ No console errors in frontend
7. ✅ Postman tests pass

---

**Start with Task 1 (Database Setup) and proceed sequentially.**
