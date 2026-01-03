"""
User Preferences Pydantic Schemas
"""
from typing import Optional
from pydantic import BaseModel, Field


class UserPreferencesResponse(BaseModel):
    """User preferences response schema"""
    pnl_grid_interval: int = 100
    market_data_source: str = "smartapi"

    class Config:
        from_attributes = True


class UserPreferencesUpdateRequest(BaseModel):
    """User preferences update request schema"""
    pnl_grid_interval: Optional[int] = Field(None, ge=50, le=100, description="P/L grid interval (50 or 100)")
    market_data_source: Optional[str] = Field(None, pattern="^(smartapi|kite)$", description="Market data source")

    @staticmethod
    def validate_interval(v: int) -> int:
        """Validate that interval is either 50 or 100"""
        if v not in [50, 100]:
            raise ValueError("pnl_grid_interval must be either 50 or 100")
        return v
