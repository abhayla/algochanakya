"""
Upstox Credentials Pydantic Schemas

Schemas for Upstox API app credential management (Tier 3).
"""
from typing import Optional
from pydantic import BaseModel, Field


class UpstoxCredentialsCreate(BaseModel):
    """Request schema for storing Upstox API app credentials."""
    api_key: str = Field(..., min_length=1, max_length=64, description="Upstox API key")
    api_secret: str = Field(..., min_length=1, max_length=128, description="Upstox API secret")


class UpstoxCredentialsResponse(BaseModel):
    """Response schema for Upstox credentials status (never returns actual secrets)."""
    has_credentials: bool
    api_key: Optional[str] = None
    is_active: bool = False
    last_error: Optional[str] = None

    class Config:
        from_attributes = True
