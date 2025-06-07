from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.message import MessageResponse

class ConversationBase(BaseModel):
    """Base schema for conversation data"""
    topic: str
    user_id: UUID  # Reference to existing user

class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation"""
    # conversation_id will be auto-generated
    user_name: Optional[str] = None  # Optional name if user wants to override their stored name

class ConversationUpdate(BaseModel):
    """Schema for updating an existing conversation"""
    topic: Optional[str] = None
    user_name: Optional[str] = None

class ConversationDB(ConversationBase):
    """Database representation of a conversation"""
    conversation_id: UUID
    user_name: Optional[str] = None
    messages: List[MessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class ConversationResponse(ConversationDB):
    """Schema for conversation responses"""
    pass

class StreamRequest(BaseModel):
    """Schema for streaming request"""
    topic: str = Field(..., description="Topic to learn about")
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
