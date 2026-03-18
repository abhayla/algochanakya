"""
User Preferences Pydantic Schemas
"""
from typing import Optional
from pydantic import BaseModel, Field

VALID_MARKET_DATA_SOURCES = ("platform", "smartapi", "kite", "upstox", "dhan", "fyers", "paytm")
VALID_ORDER_BROKERS = ("kite", "angel", "upstox", "dhan", "fyers", "paytm")


class UserPreferencesResponse(BaseModel):
    """User preferences response schema"""
    pnl_grid_interval: int = 100
    market_data_source: str = "platform"
    order_broker: Optional[str] = None

    class Config:
        from_attributes = True


class UserPreferencesUpdateRequest(BaseModel):
    """User preferences update request schema"""
    pnl_grid_interval: Optional[int] = Field(None, ge=50, le=100, description="P/L grid interval (50 or 100)")
    market_data_source: Optional[str] = Field(
        None,
        pattern="^(platform|smartapi|kite|upstox|dhan|fyers|paytm)$",
        description="Market data source"
    )
    order_broker: Optional[str] = Field(
        None,
        pattern="^(kite|angel|upstox|dhan|fyers|paytm)$",
        description="Order execution broker"
    )

    @staticmethod
    def validate_interval(v: int) -> int:
        """Validate that interval is either 50 or 100"""
        if v not in [50, 100]:
            raise ValueError("pnl_grid_interval must be either 50 or 100")
        return v


class BrokerCredentialStatusResponse(BaseModel):
    """Credential configuration status for all supported brokers."""
    smartapi: bool = False
    kite: bool = False
    upstox: bool = False
    dhan: bool = False
    fyers: bool = False
    paytm: bool = False
