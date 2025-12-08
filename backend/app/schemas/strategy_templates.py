"""Pydantic schemas for Strategy Templates and Wizard."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class MarketOutlook(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"


class VolatilityPreference(str, Enum):
    HIGH_IV = "high_iv"
    LOW_IV = "low_iv"
    ANY = "any"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class StrategyCategory(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"
    INCOME = "income"
    ADVANCED = "advanced"


# Leg configuration within template
class LegConfig(BaseModel):
    """Configuration for a single leg in a strategy template."""
    type: str  # CE, PE, FUT, EQ
    position: str  # BUY, SELL
    strike_offset: int = 0  # Offset from ATM in points
    expiry_offset: int = 0  # 0 = current expiry, 1 = next month


class AdjustmentRule(BaseModel):
    """Adjustment rule for a strategy."""
    trigger: str
    action: str


# Strategy Template Schemas
class StrategyTemplateBase(BaseModel):
    """Base schema for strategy template."""
    name: str
    display_name: str
    category: StrategyCategory
    description: str


class StrategyTemplateListItem(StrategyTemplateBase):
    """Schema for listing strategy templates."""
    id: UUID
    legs_config: List[LegConfig]
    max_profit: str
    max_loss: str
    market_outlook: str
    volatility_preference: str
    risk_level: str
    capital_requirement: str
    theta_positive: bool
    vega_positive: bool
    delta_neutral: bool
    win_probability: Optional[str] = None
    difficulty_level: str
    popularity_score: int
    tags: Optional[List[str]] = None

    class Config:
        from_attributes = True


class StrategyTemplateDetail(StrategyTemplateListItem):
    """Full detail schema for a strategy template."""
    breakeven: Optional[str] = None
    ideal_iv_rank: Optional[str] = None
    margin_requirement: Optional[str] = None
    gamma_risk: Optional[str] = None
    profit_target: Optional[str] = None
    when_to_use: Optional[str] = None
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    common_mistakes: Optional[List[str]] = None
    exit_rules: Optional[List[str]] = None
    adjustments: Optional[List[AdjustmentRule]] = None
    example_underlying: Optional[str] = None
    example_spot: Optional[float] = None
    example_setup: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryCount(BaseModel):
    """Schema for category with count."""
    category: str
    count: int
    display_name: str


class CategoriesResponse(BaseModel):
    """Schema for categories response."""
    categories: List[CategoryCount]
    total: int


# Wizard Schemas
class WizardInputs(BaseModel):
    """Schema for wizard inputs."""
    market_outlook: MarketOutlook
    volatility_view: VolatilityPreference
    risk_tolerance: RiskLevel
    capital_size: Optional[str] = None  # low, medium, high
    experience_level: Optional[DifficultyLevel] = None
    underlying: Optional[str] = "NIFTY"


class WizardRecommendation(BaseModel):
    """Schema for a single wizard recommendation."""
    template: StrategyTemplateListItem
    score: int  # 0-100
    match_reasons: List[str]
    warnings: Optional[List[str]] = None


class WizardResponse(BaseModel):
    """Schema for wizard response."""
    recommendations: List[WizardRecommendation]
    inputs: WizardInputs
    total_matches: int


# Deploy Schemas
class DeployLeg(BaseModel):
    """Schema for a deployed leg with live data."""
    type: str
    position: str
    strike: Decimal
    expiry: date
    instrument_token: int
    tradingsymbol: str
    ltp: Optional[float] = None
    lots: int = 1


class DeployRequest(BaseModel):
    """Schema for deploying a strategy template."""
    template_name: str
    underlying: str = "NIFTY"
    expiry: Optional[date] = None
    lots: int = Field(default=1, ge=1)
    atm_strike: Optional[Decimal] = None  # If not provided, will be calculated


class DeployResponse(BaseModel):
    """Schema for deploy response."""
    template_name: str
    display_name: str
    underlying: str
    spot_price: float
    atm_strike: Decimal
    expiry: date
    legs: List[DeployLeg]
    estimated_premium: Optional[float] = None
    margin_required: Optional[float] = None
    strategy_id: Optional[str] = None  # UUID of created strategy


# Compare Schemas
class CompareRequest(BaseModel):
    """Schema for comparing strategies."""
    template_names: List[str] = Field(..., min_length=2, max_length=4)
    underlying: str = "NIFTY"


class CompareItem(BaseModel):
    """Schema for a strategy in comparison."""
    template: StrategyTemplateListItem
    metrics: Dict[str, Any]


class CompareResponse(BaseModel):
    """Schema for compare response."""
    strategies: List[CompareItem]
    comparison_matrix: Dict[str, Dict[str, Any]]


# Popular Strategies
class PopularStrategiesResponse(BaseModel):
    """Schema for popular strategies response."""
    strategies: List[StrategyTemplateListItem]
