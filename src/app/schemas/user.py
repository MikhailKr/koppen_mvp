"""User schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    """Base user schema with shared attributes."""

    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str


class UserUpdate(BaseModel):
    """Schema for user update (all fields optional)."""

    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = None


class UserRead(UserBase):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
