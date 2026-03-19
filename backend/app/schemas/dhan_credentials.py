"""
Dhan Credentials Pydantic Schemas

Schemas for Dhan static token credential management (Tier 3).
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DhanCredentialsCreate(BaseModel):
    """Request schema for storing Dhan credentials."""
    client_id: str = Field(..., min_length=1, max_length=50, description="Dhan Client ID")
    access_token: str = Field(..., min_length=1, description="Dhan Access Token")


class DhanCredentialsResponse(BaseModel):
    """Response schema for Dhan credentials status (never returns actual token)."""
    has_credentials: bool
    client_id: Optional[str] = None
    is_active: bool = False
    last_auth_at: Optional[datetime] = None
    last_error: Optional[str] = None

    class Config:
        from_attributes = True
