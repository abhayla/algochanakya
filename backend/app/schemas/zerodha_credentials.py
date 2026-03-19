"""
Zerodha Credentials Pydantic Schemas

Schemas for Zerodha Kite Connect app credential management (Tier 3).
"""
from typing import Optional
from pydantic import BaseModel, Field


class ZerodhaCredentialsCreate(BaseModel):
    """Request schema for storing Zerodha Kite Connect app credentials."""
    api_key: str = Field(..., min_length=1, max_length=64, description="Kite Connect app API key")
    api_secret: str = Field(..., min_length=1, max_length=128, description="Kite Connect app API secret")


class ZerodhaCredentialsResponse(BaseModel):
    """Response schema for Zerodha credentials status (never returns actual secrets)."""
    has_credentials: bool
    api_key: Optional[str] = None
    is_active: bool = False
    last_error: Optional[str] = None

    class Config:
        from_attributes = True
