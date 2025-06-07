from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any, List, TypeVar, Union
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

# Create a type variable for self-references as 'Self' is not available in Python 3.10
T = TypeVar('T', bound='MessageBase')

class RoleEnum(str, Enum):
    """Enumeration of valid message roles"""
    user = "user"
    assistant = "assistant"
    system = "system"

class MessageBase(BaseModel):
    """Base schema for all message data"""
    role: RoleEnum = Field(..., description="Role of the message sender (user/assistant/system)")
    content: str = Field(..., description="Content of the message")
    parent_message_id: Optional[UUID] = Field(None, description="ID of the parent message in a thread")
    llm_id: Optional[str] = Field(None, description="ID of the LLM model used (for assistant messages)")
    llm_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata from LLM response")
    
    @model_validator(mode='after')
    def validate_llm_fields(self) -> 'MessageBase':
        """Validate that llm fields are only set for assistant messages"""
        if self.role in (RoleEnum.user, RoleEnum.system):
            if self.llm_id is not None:
                raise ValueError("LLM ID not allowed for user/system messages")
            if self.llm_metadata is not None:
                raise ValueError("LLM metadata not allowed for user/system messages")
                
        if self.role == RoleEnum.assistant and self.llm_id is None:
            raise ValueError("LLM ID required for assistant messages")
            
        return self

class MessageCreate(MessageBase):
    """Schema for creating a new message"""
    conversation_id: UUID = Field(..., description="ID of the conversation this message belongs to")

class MessageUpdate(BaseModel):
    """Schema for updating an existing message"""
    content: Optional[str] = None
    llm_metadata: Optional[Dict[str, Any]] = None

class MessageDB(MessageBase):
    """Database representation of a message"""
    message_id: UUID
    conversation_id: UUID
    timestamp: datetime
    
    model_config = {
        "from_attributes": True
    }

class MessageResponse(MessageDB):
    """Schema for message responses, including any child messages"""
    replies: Optional[List["MessageResponse"]] = Field(default=None)
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# Support for nested response self-referencing
MessageResponse.model_rebuild()
