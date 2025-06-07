from uuid import UUID
from typing import List, Optional, Dict, Any
import asyncio
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from async_timeout import timeout

from app.core.database import get_db_session
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationDB
from app.services.user_service import UserService
from app.services.message_service import MessageService
from app.services.llm_providers.orchestrator import LLMOrchestrator


class ConversationService:
    """Service for handling conversation operations"""

    def __init__(
        self, 
        db: AsyncSession = Depends(get_db_session),
        user_service: UserService = Depends(),
        message_service: MessageService = Depends()
    ):
        self.db = db
        self.user_service = user_service
        self.message_service = message_service
        self.llm_orchestrator = LLMOrchestrator()

    async def create_conversation(self, conversation_data: ConversationCreate) -> ConversationDB:
        """Create a new conversation"""
        # Check if user exists
        user = await self.user_service.get_user(conversation_data.user_id)
        
        # Use provided user_name or fallback to stored user name
        user_name = conversation_data.user_name or user.user_name
        
        # Create conversation
        conversation = Conversation(
            user_id=user.user_id,
            user_name=user_name,
            topic=conversation_data.topic
        )
        
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        
        return conversation

    async def get_conversation(self, conversation_id: UUID) -> ConversationDB:
        """Get a conversation by ID with all related messages"""
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.conversation_id == conversation_id)
        )
        conversation = result.scalars().first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation

    async def get_user_conversations(self, user_id: UUID) -> List[ConversationDB]:
        """Get all conversations for a user"""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        conversations = result.scalars().all()
        
        return list(conversations)

    async def update_conversation(
        self, conversation_id: UUID, conversation_data: ConversationUpdate
    ) -> ConversationDB:
        """Update a conversation by ID"""
        result = await self.db.execute(
            select(Conversation).where(Conversation.conversation_id == conversation_id)
        )
        conversation = result.scalars().first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update fields
        if conversation_data.topic is not None:
            conversation.topic = conversation_data.topic
            
        if conversation_data.user_name is not None:
            conversation.user_name = conversation_data.user_name
        
        await self.db.commit()
        await self.db.refresh(conversation)
        
        return conversation

    async def delete_conversation(self, conversation_id: UUID) -> bool:
        """Delete a conversation by ID"""
        result = await self.db.execute(
            select(Conversation).where(Conversation.conversation_id == conversation_id)
        )
        conversation = result.scalars().first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        await self.db.delete(conversation)
        await self.db.commit()
        
        return True
        
    async def add_conversation_reply(
        self, 
        conversation_id: UUID,
        message_content: str,
        providers: List[str] = None,
        local_model_id: str = "gemma3:12b"
    ) -> str:
        """
        Add a follow-up reply to an existing conversation
        
        This method:
        1. Validates the conversation exists
        2. Creates a new user message
        3. Calls LLMOrchestrator to process the follow-up with conversation history
        4. Stores the summarized response as a message
        5. Handles timeouts and other errors
        
        Args:
            conversation_id: UUID of the conversation
            message_content: Content of the user's follow-up question
            providers: List of LLM provider names to use (defaults to settings)
            local_model_id: ID of the local model to use for summarization
            
        Returns:
            Summary text from the LLM orchestrator
            
        Raises:
            HTTPException: If conversation not found, timeout occurred, or other error
        """
        # Get conversation to validate it exists
        conversation = await self.get_conversation(conversation_id)
        
        # Use default providers if none specified
        if providers is None:
            providers = ["openai", "claude", "gemini"]
        
        # Get all messages for conversation history context
        messages = await self.message_service.get_conversation_messages(conversation_id)
        
        # Get the latest message as parent (if any)
        parent_message_id = messages[-1].message_id if messages else None
        
        # Create a new user message
        user_message = await self.message_service.create_user_message(
            conversation_id=conversation_id,
            content=message_content,
            parent_message_id=parent_message_id
        )
        
        try:
            # Apply timeout constraint
            async with timeout(120):
                # Get all messages for conversation history context
                messages = await self.message_service.get_conversation_messages(conversation_id)
                
                # Extract message contents for LLM context
                history_blocks = []
                for message in messages:
                    history_blocks.append(f"{self.llm_orchestrator.summary_divider}\n[{message.role}]: {message.content}")
                history_blocks.append(self.llm_orchestrator.summary_divider)
                
                # Join all blocks
                history_text = "\n".join(history_blocks)
                
                # Process the follow-up with full conversation history
                analysis_result = await self.llm_orchestrator.process_query(
                    query=message_content,  # Current question
                    providers=providers,
                    history_text=history_text,
                    local_model_id=local_model_id
                )
                
                # Create assistant message with the summary
                await self.message_service.create_assistant_message(
                    conversation_id=conversation_id,
                    content=analysis_result.summary,
                    llm_id=f"ollama/{local_model_id}",
                    llm_metadata=analysis_result.to_dict(),
                    parent_message_id=user_message.message_id
                )
                
                # Return the summary text
                return analysis_result.summary
                
        except asyncio.TimeoutError:
            # Handle timeout
            await self.message_service.create_system_message(
                conversation_id=conversation_id,
                content="Reply generation timed out (120s limit)",
                parent_message_id=user_message.message_id
            )
            raise HTTPException(
                status_code=504,
                detail="LLM response timed out"
            )
            
        except Exception as e:
            # Handle other errors
            error_message = f"Error generating reply: {str(e)}"
            
            # Log the error and create system message
            await self.message_service.create_system_message(
                conversation_id=conversation_id,
                content=error_message,
                parent_message_id=user_message.message_id
            )
            
            # Raise HTTP exception
            raise HTTPException(
                status_code=500,
                detail=error_message
            )

    async def generate_assistant_reply(
        self,
        conversation_id: UUID,
        user_message_content: str,
        parent_message_id: UUID,
        providers: List[str] = None,
        local_model_id: str = "gemma3:12b"
    ) -> str:
        """
        Generate an assistant reply for a specific user message (used for retries)
        
        This method:
        1. Validates the conversation exists
        2. Calls LLMOrchestrator to process the user message with conversation history
        3. Stores the summarized response as a new assistant message
        4. Handles timeouts and other errors
        
        Args:
            conversation_id: UUID of the conversation
            user_message_content: Content of the user message to respond to
            parent_message_id: ID of the user message this is responding to
            providers: List of LLM provider names to use (defaults to settings)
            local_model_id: ID of the local model to use for summarization
            
        Returns:
            Summary text from the LLM orchestrator
            
        Raises:
            HTTPException: If conversation not found, timeout occurred, or other error
        """
        # Get conversation to validate it exists
        conversation = await self.get_conversation(conversation_id)
        
        # Use default providers if none specified
        if providers is None:
            providers = ["openai", "claude", "gemini"]
        
        try:
            # Apply timeout constraint
            async with timeout(120):
                # Get all messages for conversation history context (up to the parent message)
                messages = await self.message_service.get_conversation_messages(conversation_id)
                
                # Filter messages to only include those up to and including the parent message
                # to avoid including future messages that shouldn't be part of the context
                filtered_messages = []
                for message in messages:
                    filtered_messages.append(message)
                    if message.message_id == parent_message_id:
                        break
                
                # Extract message contents for LLM context
                history_blocks = []
                for message in filtered_messages:
                    history_blocks.append(f"{self.llm_orchestrator.summary_divider}\n[{message.role}]: {message.content}")
                history_blocks.append(self.llm_orchestrator.summary_divider)
                
                # Join all blocks
                history_text = "\n".join(history_blocks)
                
                # Process the user message with conversation history
                analysis_result = await self.llm_orchestrator.process_query(
                    query=user_message_content,
                    providers=providers,
                    history_text=history_text,
                    local_model_id=local_model_id
                )
                
                # Create assistant message with the summary
                await self.message_service.create_assistant_message(
                    conversation_id=conversation_id,
                    content=analysis_result.summary,
                    llm_id=f"ollama/{local_model_id}",
                    llm_metadata=analysis_result.to_dict(),
                    parent_message_id=parent_message_id
                )
                
                # Return the summary text
                return analysis_result.summary
                
        except asyncio.TimeoutError:
            # Handle timeout
            await self.message_service.create_system_message(
                conversation_id=conversation_id,
                content="Assistant reply generation timed out (120s limit)",
                parent_message_id=parent_message_id
            )
            raise HTTPException(
                status_code=504,
                detail="LLM response timed out"
            )
            
        except Exception as e:
            # Handle other errors
            error_message = f"Error generating assistant reply: {str(e)}"
            
            # Log the error and create system message
            await self.message_service.create_system_message(
                conversation_id=conversation_id,
                content=error_message,
                parent_message_id=parent_message_id
            )
            
            # Raise HTTP exception
            raise HTTPException(
                status_code=500,
                detail=error_message
            )
    
    async def start_first_reply(
        self, 
        conversation_id: UUID,
        providers: List[str] = None,
        local_model_id: str = "gemma3:12b"
    ) -> str:
        """
        Generate the first reply for a conversation using LLM orchestrator
        
        This method:
        1. Retrieves the conversation to get the topic (user's question)
        2. Calls LLMOrchestrator to process the query with the specified providers
        3. Stores the summarized response as a message
        4. Handles timeouts and other errors
        
        Args:
            conversation_id: UUID of the conversation
            providers: List of LLM provider names to use (defaults to settings)
            local_model_id: ID of the local model to use for summarization
            
        Returns:
            Summary text from the LLM orchestrator
            
        Raises:
            HTTPException: If conversation not found, timeout occurred, or other error
        """
        # Get conversation to access the topic
        conversation = await self.get_conversation(conversation_id)
        
        # Use default providers if none specified
        if providers is None:
            providers = ["openai", "claude", "gemini"]
        
        try:
            # Apply timeout constraint
            async with timeout(120):
                # Get summarized response from LLM orchestrator
                analysis_result = await self.llm_orchestrator.process_query(
                    query=conversation.topic,
                    providers=providers,
                    local_model_id=local_model_id
                )
                
                # Create the first user message with the topic as content
                user_message = await self.message_service.create_user_message(
                    conversation_id=conversation_id,
                    content=conversation.topic
                )
                
                # Create assistant message with the summary
                await self.message_service.create_assistant_message(
                    conversation_id=conversation_id,
                    content=analysis_result.summary,
                    llm_id=f"ollama/{local_model_id}",
                    llm_metadata=analysis_result.to_dict(),
                    parent_message_id=user_message.message_id
                )
                
                # Return the summary text
                return analysis_result.summary
                
        except asyncio.TimeoutError:
            # Create initial user message even on timeout
            user_message = await self.message_service.create_user_message(
                conversation_id=conversation_id,
                content=conversation.topic
            )
            
            # Handle timeout
            await self.message_service.create_system_message(
                conversation_id=conversation_id,
                content="First reply generation timed out (120s limit)",
                parent_message_id=user_message.message_id
            )
            raise HTTPException(
                status_code=504,
                detail="LLM response timed out"
            )
            
        except Exception as e:
            # Handle other errors
            error_message = f"Error generating first reply: {str(e)}"
            
            # Create initial user message even on error
            user_message = await self.message_service.create_user_message(
                conversation_id=conversation_id,
                content=conversation.topic
            )
            
            # Log the error and create system message
            await self.message_service.create_system_message(
                conversation_id=conversation_id,
                content=error_message,
                parent_message_id=user_message.message_id
            )
            
            # Raise HTTP exception
            raise HTTPException(
                status_code=500,
                detail=error_message
            )
