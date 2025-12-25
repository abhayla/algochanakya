"""
AI Pydantic Schemas

Request and response models for AI API endpoints.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.ai.market_regime import RegimeType


class IndicatorsSnapshotResponse(BaseModel):
    """Indicators snapshot response."""
    underlying: str
    timestamp: datetime

    # Price Data
    spot_price: float
    vix: Optional[float] = None

    # Trend Indicators
    rsi_14: Optional[float] = None
    adx_14: Optional[float] = None
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    ema_50: Optional[float] = None

    # Volatility Indicators
    atr_14: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_width_pct: Optional[float] = None

    class Config:
        from_attributes = True


class RegimeResponse(BaseModel):
    """Market regime classification response."""
    regime_type: RegimeType
    confidence: float = Field(..., ge=0, le=100, description="Confidence score 0-100")
    indicators: IndicatorsSnapshotResponse
    reasoning: str = Field(..., description="Explanation for regime classification")

    class Config:
        from_attributes = True


# ============================================================================
# AI User Configuration Schemas
# ============================================================================

class ConfidenceTier(BaseModel):
    """Single confidence tier configuration."""
    name: str = Field(..., description="Tier name (e.g., SKIP, LOW, MEDIUM, HIGH)")
    min: float = Field(..., ge=0, le=100, description="Minimum confidence score for this tier")
    max: float = Field(..., ge=0, le=100, description="Maximum confidence score for this tier")
    multiplier: float = Field(..., ge=0, description="Lot size multiplier for this tier")

    @field_validator('max')
    @classmethod
    def validate_max_greater_than_min(cls, v, info):
        if 'min' in info.data and v < info.data['min']:
            raise ValueError('max must be greater than or equal to min')
        return v


class DeploymentScheduleConfig(BaseModel):
    """Deployment schedule configuration."""
    auto_deploy_enabled: bool = Field(False, description="Enable automatic deployment")
    deploy_time: str = Field("09:20", pattern=r"^\d{2}:\d{2}$", description="Deployment time (HH:MM)")
    deploy_days: List[str] = Field(
        ["MON", "TUE", "WED", "THU", "FRI"],
        description="Days to deploy (MON, TUE, WED, THU, FRI)"
    )
    skip_event_days: bool = Field(True, description="Skip deployment on event days")
    skip_weekly_expiry: bool = Field(False, description="Skip weekly expiry days (Thursday)")

    @field_validator('deploy_days')
    @classmethod
    def validate_deploy_days(cls, v):
        valid_days = {"MON", "TUE", "WED", "THU", "FRI"}
        for day in v:
            if day not in valid_days:
                raise ValueError(f"Invalid day: {day}. Must be one of {valid_days}")
        return v


class PositionSizingConfig(BaseModel):
    """Position sizing configuration."""
    sizing_mode: str = Field("tiered", description="Sizing mode: fixed, tiered, kelly")
    base_lots: int = Field(1, ge=1, le=50, description="Base lot size")
    confidence_tiers: List[ConfidenceTier] = Field(
        ...,
        description="Confidence tier configurations"
    )

    @field_validator('sizing_mode')
    @classmethod
    def validate_sizing_mode(cls, v):
        valid_modes = {"fixed", "tiered", "kelly"}
        if v not in valid_modes:
            raise ValueError(f"Invalid sizing mode: {v}. Must be one of {valid_modes}")
        return v

    @model_validator(mode='after')
    def validate_tiers_no_gaps(self):
        """Ensure confidence tiers have no gaps and no overlaps."""
        if not self.confidence_tiers:
            raise ValueError("At least one confidence tier is required")

        # Sort tiers by min value
        sorted_tiers = sorted(self.confidence_tiers, key=lambda t: t.min)

        # Check first tier starts at 0
        if sorted_tiers[0].min != 0:
            raise ValueError("First tier must start at 0")

        # Check last tier ends at 100
        if sorted_tiers[-1].max != 100:
            raise ValueError("Last tier must end at 100")

        # Check for gaps and overlaps
        for i in range(len(sorted_tiers) - 1):
            current_max = sorted_tiers[i].max
            next_min = sorted_tiers[i + 1].min

            if current_max < next_min:
                raise ValueError(f"Gap found between {current_max} and {next_min}")
            if current_max > next_min:
                raise ValueError(f"Overlap found between {current_max} and {next_min}")

        return self


class AILimitsConfig(BaseModel):
    """AI trading limits configuration."""
    max_lots_per_strategy: int = Field(2, ge=1, description="Maximum lots per strategy")
    max_lots_per_day: int = Field(6, ge=1, description="Maximum total lots per day")
    max_strategies_per_day: int = Field(5, ge=1, description="Maximum strategies per day")
    min_confidence_to_trade: float = Field(60.0, ge=0, le=100, description="Minimum confidence to enter trade")
    max_vix_to_trade: float = Field(25.0, gt=0, description="Maximum VIX level to enter trade")
    min_dte_to_enter: int = Field(2, ge=0, description="Minimum days to expiry to enter")
    weekly_loss_limit: Decimal = Field(Decimal('50000.00'), gt=0, description="Weekly loss limit in INR")


class PaperTradingStatus(BaseModel):
    """Paper trading graduation status."""
    paper_start_date: Optional[date] = Field(None, description="Date paper trading started")
    paper_trades_completed: int = Field(0, ge=0, description="Number of paper trades completed")
    paper_win_rate: float = Field(0, ge=0, le=100, description="Win rate percentage in paper trading")
    paper_total_pnl: Decimal = Field(Decimal('0'), description="Total P&L in paper trading")
    paper_graduation_approved: bool = Field(False, description="Whether graduation to live is approved")

    # Graduation criteria
    required_trades: int = Field(25, ge=0, description="Required number of trades for graduation")
    required_win_rate: float = Field(55.0, ge=0, le=100, description="Required win rate for graduation")
    required_days: int = Field(15, ge=0, description="Required trading days for graduation")

    class Config:
        from_attributes = True


class AIUserConfigCreate(BaseModel):
    """Request schema for creating AI user configuration."""
    # Autonomy
    ai_enabled: bool = Field(False, description="Enable AI trading")
    autonomy_mode: str = Field("paper", description="Autonomy mode: paper or live")

    # Deployment
    deployment: Optional[DeploymentScheduleConfig] = None

    # Position Sizing
    sizing: Optional[PositionSizingConfig] = None

    # Limits
    limits: Optional[AILimitsConfig] = None

    # Strategy Universe
    allowed_strategies: List[int] = Field([], description="List of allowed strategy template IDs")

    # Preferences
    preferred_underlyings: List[str] = Field(
        ["NIFTY", "BANKNIFTY"],
        description="Preferred underlyings for trading"
    )

    # Claude API
    claude_api_key: Optional[str] = Field(None, description="Claude API key (will be encrypted)")
    enable_ai_explanations: bool = Field(True, description="Enable AI-powered explanations")

    @field_validator('autonomy_mode')
    @classmethod
    def validate_autonomy_mode(cls, v):
        valid_modes = {"paper", "live"}
        if v not in valid_modes:
            raise ValueError(f"Invalid autonomy mode: {v}. Must be one of {valid_modes}")
        return v


class AIUserConfigUpdate(BaseModel):
    """Request schema for updating AI user configuration."""
    # All fields optional for partial updates
    ai_enabled: Optional[bool] = None
    autonomy_mode: Optional[str] = None
    auto_deploy_enabled: Optional[bool] = None
    deploy_time: Optional[str] = None
    deploy_days: Optional[List[str]] = None
    skip_event_days: Optional[bool] = None
    skip_weekly_expiry: Optional[bool] = None
    allowed_strategies: Optional[List[int]] = None
    sizing_mode: Optional[str] = None
    base_lots: Optional[int] = None
    confidence_tiers: Optional[List[ConfidenceTier]] = None
    max_lots_per_strategy: Optional[int] = None
    max_lots_per_day: Optional[int] = None
    max_strategies_per_day: Optional[int] = None
    min_confidence_to_trade: Optional[float] = None
    max_vix_to_trade: Optional[float] = None
    min_dte_to_enter: Optional[int] = None
    weekly_loss_limit: Optional[Decimal] = None
    preferred_underlyings: Optional[List[str]] = None
    claude_api_key: Optional[str] = None
    enable_ai_explanations: Optional[bool] = None


class AIUserConfigResponse(BaseModel):
    """Response schema for AI user configuration."""
    id: int
    user_id: UUID

    # Autonomy
    ai_enabled: bool
    autonomy_mode: str

    # Deployment
    auto_deploy_enabled: bool
    deploy_time: Optional[str]
    deploy_days: List[str]
    skip_event_days: bool
    skip_weekly_expiry: bool

    # Strategy Universe
    allowed_strategies: List[int]

    # Position Sizing
    sizing_mode: str
    base_lots: int
    confidence_tiers: List[dict]  # JSONB field

    # Limits
    max_lots_per_strategy: int
    max_lots_per_day: int
    max_strategies_per_day: int
    min_confidence_to_trade: Decimal
    max_vix_to_trade: Decimal
    min_dte_to_enter: int
    weekly_loss_limit: Decimal

    # Preferences
    preferred_underlyings: List[str]

    # Paper Trading
    paper_start_date: Optional[date]
    paper_trades_completed: int
    paper_win_rate: Decimal
    paper_total_pnl: Decimal
    paper_graduation_approved: bool

    # Claude API
    enable_ai_explanations: bool
    # Note: API key is NOT returned for security

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIConfigDefaults(BaseModel):
    """Default AI configuration template."""
    deployment: DeploymentScheduleConfig
    sizing: PositionSizingConfig
    limits: AILimitsConfig


class ClaudeKeyValidationRequest(BaseModel):
    """Request to validate Claude API key."""
    api_key: str = Field(..., min_length=10, description="Claude API key to validate")


class ClaudeKeyValidationResponse(BaseModel):
    """Response for Claude API key validation."""
    valid: bool = Field(..., description="Whether the key is valid")
    message: str = Field(..., description="Validation result message")


# ============================================================================
# ML Model Registry Schemas
# ============================================================================

class ModelRegistryCreate(BaseModel):
    """Request schema for registering a new ML model."""
    version: str = Field(..., min_length=1, max_length=50, description="Model version (e.g., v1, v2)")
    model_type: str = Field(..., description="Model type (xgboost, lightgbm)")
    file_path: str = Field(..., description="Path to saved model file")
    description: Optional[str] = Field(None, description="Model description")

    # Evaluation metrics
    accuracy: Optional[float] = Field(None, ge=0, le=1, description="Accuracy score (0-1)")
    precision: Optional[float] = Field(None, ge=0, le=1, description="Precision score (0-1)")
    recall: Optional[float] = Field(None, ge=0, le=1, description="Recall score (0-1)")
    f1_score: Optional[float] = Field(None, ge=0, le=1, description="F1 score (0-1)")
    roc_auc: Optional[float] = Field(None, ge=0, le=1, description="ROC AUC score (0-1)")

    @field_validator('model_type')
    @classmethod
    def validate_model_type(cls, v):
        valid_types = {"xgboost", "lightgbm"}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid model type: {v}. Must be one of {valid_types}")
        return v.lower()


class ModelRegistryResponse(BaseModel):
    """Response schema for ML model registry entry."""
    id: int
    version: str
    model_type: str
    file_path: str
    description: Optional[str]

    # Metrics
    accuracy: Optional[Decimal]
    precision: Optional[Decimal]
    recall: Optional[Decimal]
    f1_score: Optional[Decimal]
    roc_auc: Optional[Decimal]

    # Deployment status
    is_active: bool
    activated_at: Optional[datetime]

    # Timestamps
    trained_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ModelActivateRequest(BaseModel):
    """Request schema for activating a model version."""
    version: str = Field(..., description="Model version to activate")


class ModelCompareResponse(BaseModel):
    """Response schema for comparing two models."""
    version1: str
    version2: str
    metrics: dict = Field(..., description="Comparison of metrics between versions")
