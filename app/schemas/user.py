from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

class UserBase(BaseModel):
    """Base schema for user data"""
    user_name: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user"""
    pass  # user_id will be auto-generated

class UserUpdate(UserBase):
    """Schema for updating an existing user"""
    user_name: Optional[str] = None

class UserDB(UserBase):
    """Database representation of a user"""
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
class UserResponse(UserDB):
    """Schema for user responses"""
    pass
