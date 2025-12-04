from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


class InstrumentBase(BaseModel):
    """Base schema for instrument."""
    instrument_token: int
    exchange_token: Optional[int] = None
    tradingsymbol: str
    name: Optional[str] = None
    exchange: str
    segment: Optional[str] = None
    instrument_type: Optional[str] = None
    strike: Optional[Decimal] = None
    expiry: Optional[date] = None
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.05")


class InstrumentCreate(InstrumentBase):
    """Schema for creating an instrument."""
    pass


class InstrumentResponse(InstrumentBase):
    """Schema for instrument response."""
    id: UUID
    last_updated: datetime

    class Config:
        from_attributes = True


class InstrumentSearchResponse(BaseModel):
    """Schema for instrument search response."""
    instrument_token: int
    tradingsymbol: str
    name: Optional[str] = None
    exchange: str
    segment: Optional[str] = None
    instrument_type: Optional[str] = None
    expiry: Optional[date] = None
    strike: Optional[Decimal] = None

    class Config:
        from_attributes = True
