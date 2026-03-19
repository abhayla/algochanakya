"""
SmartAPI Pydantic Schemas

Schemas for SmartAPI credential management and configuration.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SmartAPICredentialsCreate(BaseModel):
    """Request schema for storing SmartAPI credentials."""
    client_id: str = Field(..., min_length=1, max_length=20, description="AngelOne client ID")
    pin: str = Field(..., min_length=4, max_length=10, description="Trading PIN")
    totp_secret: str = Field(..., min_length=16, max_length=64, description="TOTP secret for auto-generation")


class SmartAPICredentialsResponse(BaseModel):
    """Response schema for SmartAPI credentials status."""
    has_credentials: bool
    client_id: Optional[str] = None
    is_active: bool = False
    last_auth_at: Optional[datetime] = None
    last_error: Optional[str] = None
    token_expiry: Optional[datetime] = None

    class Config:
        from_attributes = True


class SmartAPITestConnectionRequest(BaseModel):
    """Request schema for testing SmartAPI connection."""
    client_id: str = Field(..., min_length=1, max_length=20)
    pin: str = Field(..., min_length=4, max_length=10)
    totp_secret: str = Field(..., min_length=16, max_length=64)


class SmartAPITestConnectionResponse(BaseModel):
    """Response schema for connection test result."""
    success: bool
    message: str
    client_name: Optional[str] = None


class MarketDataSourceRequest(BaseModel):
    """Request schema for updating market data source."""
    source: str = Field(..., pattern="^(smartapi|kite|upstox|dhan|fyers|paytm)$", description="Market data source")


class MarketDataSourceResponse(BaseModel):
    """Response schema for market data source."""
    source: str
    smartapi_configured: bool
    kite_configured: bool


class SmartAPIQuoteRequest(BaseModel):
    """Request schema for SmartAPI quote."""
    instruments: list[str] = Field(..., min_length=1, description="List of EXCHANGE:SYMBOL")
    mode: str = Field("FULL", pattern="^(LTP|OHLC|FULL)$")


class SmartAPIHistoricalRequest(BaseModel):
    """Request schema for historical data."""
    exchange: str = Field(..., pattern="^(NSE|NFO|BSE|BFO|MCX)$")
    symbol: str = Field(..., min_length=1)
    interval: str = Field("1d", description="Candle interval")
    from_date: str = Field(..., description="Start date YYYY-MM-DD HH:MM")
    to_date: str = Field(..., description="End date YYYY-MM-DD HH:MM")
