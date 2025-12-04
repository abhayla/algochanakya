from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional


class BrokerConnectionBase(BaseModel):
    """Base broker connection schema."""
    broker: str
    broker_user_id: str


class BrokerConnectionCreate(BrokerConnectionBase):
    """Schema for creating a new broker connection."""
    user_id: UUID4
    access_token: str
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None


class BrokerConnectionResponse(BrokerConnectionBase):
    """Schema for broker connection response."""
    id: UUID4
    user_id: UUID4
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Note: Never expose access_token or refresh_token in response

    class Config:
        from_attributes = True
