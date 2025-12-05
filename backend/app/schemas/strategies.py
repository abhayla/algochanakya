"""Pydantic schemas for Strategy Builder."""

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class ContractType(str, Enum):
    CE = "CE"
    PE = "PE"
    FUT = "FUT"
    EQ = "EQ"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class PositionStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    CLOSED = "closed"


class StrategyStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class PnLMode(str, Enum):
    EXPIRY = "expiry"
    CURRENT = "current"


# Strategy Leg Schemas
class StrategyLegBase(BaseModel):
    """Base schema for strategy leg."""
    expiry_date: date
    contract_type: ContractType
    transaction_type: TransactionType
    strike_price: Optional[Decimal] = None
    lots: int = Field(default=1, ge=1)
    strategy_type: Optional[str] = None
    entry_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    instrument_token: Optional[int] = None


class StrategyLegCreate(StrategyLegBase):
    """Schema for creating a strategy leg."""
    pass


class StrategyLegUpdate(BaseModel):
    """Schema for updating a strategy leg."""
    expiry_date: Optional[date] = None
    contract_type: Optional[ContractType] = None
    transaction_type: Optional[TransactionType] = None
    strike_price: Optional[Decimal] = None
    lots: Optional[int] = Field(default=None, ge=1)
    strategy_type: Optional[str] = None
    entry_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    instrument_token: Optional[int] = None
    order_id: Optional[str] = None
    position_status: Optional[PositionStatus] = None


class StrategyLegResponse(StrategyLegBase):
    """Schema for strategy leg response."""
    id: UUID
    strategy_id: UUID
    order_id: Optional[str] = None
    position_status: PositionStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Strategy Schemas
class StrategyBase(BaseModel):
    """Base schema for strategy."""
    name: Optional[str] = Field(None, max_length=100)
    underlying: str = Field(..., description="NIFTY, BANKNIFTY, or FINNIFTY")


class StrategyCreate(StrategyBase):
    """Schema for creating a strategy."""
    legs: Optional[List[StrategyLegCreate]] = []


class StrategyUpdate(BaseModel):
    """Schema for updating a strategy."""
    name: Optional[str] = Field(None, max_length=100)
    status: Optional[StrategyStatus] = None


class StrategyResponse(StrategyBase):
    """Schema for strategy response."""
    id: UUID
    user_id: UUID
    share_code: Optional[str] = None
    status: StrategyStatus
    legs: List[StrategyLegResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    """Schema for listing strategies."""
    id: UUID
    name: Optional[str] = None
    underlying: str
    status: StrategyStatus
    legs_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# P/L Calculation Schemas
class PnLLeg(BaseModel):
    """Schema for leg in P/L calculation."""
    strike: Decimal
    contract_type: ContractType
    transaction_type: TransactionType
    lots: int
    lot_size: int
    entry_price: Decimal
    expiry_date: date


class PnLCalculateRequest(BaseModel):
    """Schema for P/L calculation request."""
    underlying: str
    legs: List[PnLLeg]
    mode: PnLMode = PnLMode.EXPIRY
    target_date: Optional[date] = None
    volatility: Optional[float] = Field(default=0.15, ge=0.01, le=1.0)


class PnLCalculateResponse(BaseModel):
    """Schema for P/L calculation response."""
    spot_prices: List[float]
    leg_pnl: List[List[float]]
    total_pnl: List[float]
    current_spot: float
    max_profit: float
    max_loss: float
    breakeven: List[float]


# Share Strategy Schemas
class ShareStrategyResponse(BaseModel):
    """Schema for share strategy response."""
    share_code: str
    share_url: str


# Basket Order Schemas
class BasketOrderLeg(BaseModel):
    """Schema for a leg in basket order."""
    instrument_token: int
    transaction_type: TransactionType
    quantity: int = Field(..., ge=1)
    price: Optional[Decimal] = None
    order_type: str = Field(default="LIMIT", description="LIMIT or MARKET")


class BasketOrderRequest(BaseModel):
    """Schema for basket order request."""
    strategy_id: Optional[UUID] = None
    legs: List[BasketOrderLeg]


class BasketOrderResult(BaseModel):
    """Schema for individual order result."""
    instrument_token: int
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None


class BasketOrderResponse(BaseModel):
    """Schema for basket order response."""
    success: bool
    results: List[BasketOrderResult]
    total_orders: int
    successful_orders: int
    failed_orders: int


# Options Data Schemas
class ExpiryResponse(BaseModel):
    """Schema for expiry dates response."""
    expiries: List[date]


class StrikeResponse(BaseModel):
    """Schema for strike prices response."""
    strikes: List[Decimal]


class OptionChainItem(BaseModel):
    """Schema for option chain item."""
    instrument_token: int
    tradingsymbol: str
    strike: Decimal
    contract_type: ContractType
    expiry: date
    ltp: Optional[float] = None
    change: Optional[float] = None
    volume: Optional[int] = None
    oi: Optional[int] = None


class OptionChainResponse(BaseModel):
    """Schema for option chain response."""
    underlying: str
    expiry: date
    spot_price: Optional[float] = None
    options: List[OptionChainItem]


# Position Import Schemas
class ImportedPosition(BaseModel):
    """Schema for imported position."""
    tradingsymbol: str
    instrument_token: int
    exchange: str
    quantity: int
    average_price: Decimal
    last_price: float
    pnl: float


class ImportPositionsResponse(BaseModel):
    """Schema for import positions response."""
    positions: List[ImportedPosition]
    legs: List[StrategyLegCreate]
