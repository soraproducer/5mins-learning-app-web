from uuid import UUID
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from async_timeout import timeout
from pydantic import BaseModel, Field

from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse
from app.schemas.message import MessageResponse
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.routers.messages import ReplyConfig

router = APIRouter()

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    service: ConversationService = Depends()
):
    """
    Create a new conversation
    
    This endpoint immediately returns the created conversation record
    with a conversation_id that can be used to generate the first reply.
    The user's initial question is stored as the conversation topic.
    """
    conversation = await service.create_conversation(conversation_data)
    # Manually construct response to avoid async relationship loading issues
    return {
        "conversation_id": str(conversation.conversation_id),
        "user_id": str(conversation.user_id),
        "user_name": conversation.user_name,
        "topic": conversation.topic,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "messages": []  # Empty list as new conversations have no messages
    }

@router.post("/{conversation_id}/first-reply", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def start_first_reply(
    conversation_id: UUID,
    background_tasks: BackgroundTasks,
    config: Optional[ReplyConfig] = None,
    service: ConversationService = Depends()
):
    """
    Generate the first reply for a conversation
    
    This endpoint initiates an asynchronous task to:
    1. Query multiple LLM providers with the conversation topic (user's question)
    2. Summarize responses using Ollama
    3. Store the summarized response as the first reply message in the conversation
    
    Parameters:
    - conversation_id: ID of the conversation
    - config: Optional configuration for LLM providers and local model
    
    Returns a 202 Accepted response with a status tracking endpoint
    """
    # Use default config if none provided
    if config is None:
        config = ReplyConfig()
    
    # Add task to background tasks
    background_tasks.add_task(
        service.start_first_reply, 
        conversation_id=conversation_id,
        providers=config.providers,
        local_model_id=config.local_model_id
    )
    
    # Return accepted response with tracking info
    return {
        "status": "processing",
        "message": "First reply generation initiated",
        "conversation_id": str(conversation_id),
        "providers": config.providers,
        "local_model_id": config.local_model_id
    }

@router.post("/{conversation_id}/reply", status_code=status.HTTP_202_ACCEPTED)
async def create_conversation_reply(
    conversation_id: UUID,
    background_tasks: BackgroundTasks,
    config: Optional[ReplyConfig] = None,
    service: ConversationService = Depends()
):
    """
    Generate a reply to a follow-up question in an existing conversation
    
    This endpoint initiates an asynchronous task to:
    1. Query multiple LLM providers with the follow-up question
    2. Summarize responses using Ollama
    3. Store the summarized response as a new message in the conversation
    
    Parameters:
    - conversation_id: ID of the conversation
    - config: Optional configuration with message_content (required), providers and local_model
    
    Returns a 202 Accepted response with a status tracking endpoint
    """
    # Use default config if none provided
    if config is None:
        config = ReplyConfig()
    
    # Validate message_content is provided for the reply endpoint
    if not config.message_content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="message_content is required for reply"
        )
    
    # Add task to background tasks
    background_tasks.add_task(
        service.add_conversation_reply, 
        conversation_id=conversation_id,
        message_content=config.message_content,
        providers=config.providers,
        local_model_id=config.local_model_id
    )
    
    # Return accepted response with tracking info
    return {
        "status": "processing",
        "message": "Reply generation initiated",
        "conversation_id": str(conversation_id),
        "providers": config.providers,
        "local_model_id": config.local_model_id
    }

@router.get("/user/{user_id}", response_model=List[ConversationResponse])
async def get_user_conversations(
    user_id: UUID,
    service: ConversationService = Depends()
):
    """
    Get all conversations for a user ordered by most recent
    """
    conversations = await service.get_user_conversations(user_id)
    
    # Convert to response format
    return [
        {
            "conversation_id": str(conversation.conversation_id),
            "user_id": str(conversation.user_id),
            "user_name": conversation.user_name,
            "topic": conversation.topic,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": []  # Don't load messages for list view for performance
        }
        for conversation in conversations
    ]

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: UUID,
    service: ConversationService = Depends(),
    message_service: MessageService = Depends()
):
    """
    Get all messages for a conversation in a threaded structure
    """
    # First verify the conversation exists
    await service.get_conversation(conversation_id)
    
    # Get messages with thread structure properly built
    return await message_service.get_conversation_thread(conversation_id)

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends()
):
    """
    Delete a conversation and all its messages
    """
    await service.delete_conversation(conversation_id)
    return None
