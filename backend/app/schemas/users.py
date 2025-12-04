from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """Base user schema."""
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID4
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True
