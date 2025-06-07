from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field

from app.schemas.message import MessageCreate, MessageUpdate, MessageResponse
from app.services.message_service import MessageService

class ReplyConfig(BaseModel):
    """Configuration for conversation reply generation and message retry"""
    message_content: Optional[str] = Field(None, description="Content of the message to process")
    providers: List[str] = Field(default=["openai", "claude", "gemini"], 
                                description="LLM providers to use for generating responses")
    local_model_id: str = Field(default="gemma3:12b",
                               description="Local model ID for summarization")

router = APIRouter()

@router.post("", response_model=MessageResponse)
async def create_message(
    message_data: MessageCreate,
    service: MessageService = Depends()
):
    """Create a new message"""
    return await service.create_message(message_data)

@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: UUID,
    service: MessageService = Depends()
):
    """Get a message by ID"""
    return await service.get_message(message_id)

@router.post("/{message_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_message(
    message_id: UUID,
    background_tasks: BackgroundTasks,
    config: ReplyConfig,
    service: MessageService = Depends()
):
    """
    Retry generating an assistant message with different models
    
    This endpoint:
    1. Validates the target message is an assistant message
    2. Deletes all subsequent messages after the target message
    3. Regenerates the assistant message using the specified providers and local model
    
    Parameters:
    - message_id: ID of the assistant message to retry
    - config: Configuration with providers and local_model_id
    
    Returns a 202 Accepted response
    """
    # Add task to background tasks
    background_tasks.add_task(
        service.retry_assistant_message,
        message_id=message_id,
        providers=config.providers,
        local_model_id=config.local_model_id
    )
    
    # Return accepted response with tracking info
    return {
        "status": "processing",
        "message": "Message retry initiated",
        "message_id": str(message_id),
        "providers": config.providers,
        "local_model_id": config.local_model_id
    }
