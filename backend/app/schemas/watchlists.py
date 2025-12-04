from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class WatchlistInstrument(BaseModel):
    """Schema for instrument in watchlist."""
    token: int = Field(..., description="Instrument token")
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange (NSE, BSE, NFO, etc.)")


class WatchlistCreate(BaseModel):
    """Schema for creating a new watchlist."""
    name: str = Field(default="Watchlist 1", max_length=50)


class WatchlistUpdate(BaseModel):
    """Schema for updating a watchlist."""
    name: Optional[str] = Field(None, max_length=50)
    instruments: Optional[List[WatchlistInstrument]] = None
    order_index: Optional[int] = None


class WatchlistResponse(BaseModel):
    """Schema for watchlist response."""
    id: UUID
    user_id: UUID
    name: str
    instruments: List[WatchlistInstrument]
    order_index: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AddInstrumentRequest(BaseModel):
    """Schema for adding instrument to watchlist."""
    instrument_token: int = Field(..., description="Instrument token to add")
