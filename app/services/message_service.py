from datetime import datetime
from uuid import UUID
from typing import List, Optional, Dict, Any, Tuple, Set
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db_session
from app.models.message import Message
from app.models.conversation import Conversation
from app.schemas.message import MessageCreate, MessageUpdate, MessageDB, MessageResponse, RoleEnum


class MessageService:
    """Service for handling message operations"""

    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        self.db = db

    async def create_message(self, message_data: MessageCreate) -> MessageDB:
        """Create a new message"""
        # Check if conversation exists
        result = await self.db.execute(
            select(Conversation).where(Conversation.conversation_id == message_data.conversation_id)
        )
        conversation = result.scalars().first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Validate parent message if provided
        if message_data.parent_message_id:
            parent_result = await self.db.execute(
                select(Message).where(Message.message_id == message_data.parent_message_id)
            )
            parent_message = parent_result.scalars().first()
            if not parent_message:
                raise HTTPException(status_code=404, detail="Parent message not found")
            
            # Check that parent message belongs to the same conversation
            if parent_message.conversation_id != message_data.conversation_id:
                raise HTTPException(
                    status_code=400, 
                    detail="Parent message must belong to the same conversation"
                )
        
        # Create message
        message = Message(
            conversation_id=message_data.conversation_id,
            role=message_data.role,
            content=message_data.content,
            parent_message_id=message_data.parent_message_id,
            llm_id=message_data.llm_id,
            llm_metadata=message_data.llm_metadata
        )
        
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        
        # Update conversation last modified time
        conversation.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return message

    async def create_user_message(
        self, 
        conversation_id: UUID,
        content: str,
        parent_message_id: Optional[UUID] = None
    ) -> MessageDB:
        """Helper to create a user message"""
        message_data = MessageCreate(
            conversation_id=conversation_id,
            role=RoleEnum.user,
            content=content,
            parent_message_id=parent_message_id,
            llm_id=None,
            llm_metadata=None
        )
        return await self.create_message(message_data)
    
    async def create_assistant_message(
        self, 
        conversation_id: UUID,
        content: str,
        llm_id: str,
        parent_message_id: Optional[UUID] = None,
        llm_metadata: Optional[Dict[str, Any]] = None
    ) -> MessageDB:
        """Helper to create an assistant message"""
        message_data = MessageCreate(
            conversation_id=conversation_id,
            role=RoleEnum.assistant,
            content=content,
            parent_message_id=parent_message_id,
            llm_id=llm_id,
            llm_metadata=llm_metadata or {}
        )
        return await self.create_message(message_data)
    
    async def create_system_message(
        self, 
        conversation_id: UUID,
        content: str,
        parent_message_id: Optional[UUID] = None
    ) -> MessageDB:
        """Helper to create a system message"""
        message_data = MessageCreate(
            conversation_id=conversation_id,
            role=RoleEnum.system,
            content=content,
            parent_message_id=parent_message_id,
            llm_id=None,
            llm_metadata=None
        )
        return await self.create_message(message_data)

    async def get_message(self, message_id: UUID) -> MessageDB:
        """Get a message by ID"""
        result = await self.db.execute(
            select(Message).where(Message.message_id == message_id)
        )
        message = result.scalars().first()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return message

    async def get_conversation_messages(self, conversation_id: UUID) -> List[MessageDB]:
        """Get all messages for a conversation ordered by timestamp"""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
        )
        messages = result.scalars().all()
        
        return list(messages)
    
    async def get_conversation_thread(self, conversation_id: UUID) -> List[MessageResponse]:
        """Get all root messages and their replies in a threaded structure"""
        # First get all messages in this conversation
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
        )
        all_messages = list(result.scalars().all())
        
        # Identify root messages (no parent_message_id)
        root_messages = [m for m in all_messages if m.parent_message_id is None]
        
        # Build a map of message_id to replies
        replies_map: Dict[UUID, List[Message]] = {}
        for message in all_messages:
            if message.parent_message_id:
                if message.parent_message_id not in replies_map:
                    replies_map[message.parent_message_id] = []
                replies_map[message.parent_message_id].append(message)
        
        # Recursive function to build thread structure
        def build_thread(message: Message) -> MessageResponse:
            # Create basic response without replies first
            msg_dict = {
                "message_id": message.message_id,
                "conversation_id": message.conversation_id,
                "role": message.role,
                "content": message.content,
                "parent_message_id": message.parent_message_id,
                "llm_id": message.llm_id,
                "llm_metadata": message.llm_metadata,
                "timestamp": message.timestamp,
                "replies": None  # Initialize with None
            }
            
            # If there are replies, process them
            if message.message_id in replies_map:
                # Sort replies by timestamp
                sorted_replies = sorted(replies_map[message.message_id], key=lambda m: m.timestamp)
                # Process replies recursively and add to dict
                msg_dict["replies"] = [build_thread(reply) for reply in sorted_replies]
            
            # Create response object after setting all fields
            return MessageResponse(**msg_dict)
        
        # Build thread structure for each root message
        root_messages.sort(key=lambda m: m.timestamp)
        return [build_thread(root) for root in root_messages]

    async def update_message(self, message_id: UUID, message_data: MessageUpdate) -> MessageDB:
        """Update a message with new data"""
        result = await self.db.execute(
            select(Message).where(Message.message_id == message_id)
        )
        message = result.scalars().first()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Update fields if provided
        if message_data.content is not None:
            message.content = message_data.content
            
        if message_data.llm_metadata is not None:
            message.llm_metadata = message_data.llm_metadata
        
        await self.db.commit()
        await self.db.refresh(message)
        
        # Update conversation last modified time
        result = await self.db.execute(
            select(Conversation).where(Conversation.conversation_id == message.conversation_id)
        )
        conversation = result.scalars().first()
        conversation.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return message

    async def delete_message(self, message_id: UUID) -> bool:
        """Delete a message by ID"""
        result = await self.db.execute(
            select(Message).where(Message.message_id == message_id)
        )
        message = result.scalars().first()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Get all child messages in the thread
        deleted_ids = set([message_id])
        await self._collect_descendant_messages(message_id, deleted_ids)
        
        # Delete all messages in the thread - correct SQLAlchemy async syntax
        for msg_id in deleted_ids:
            # First get the message
            result = await self.db.execute(
                select(Message).where(Message.message_id == msg_id)
            )
            msg_to_delete = result.scalars().first()
            
            if msg_to_delete:
                await self.db.delete(msg_to_delete)
        
        await self.db.commit()
        
        return True
    
    async def _collect_descendant_messages(self, message_id: UUID, result_set: Set[UUID]) -> None:
        """Recursively collect all descendant message IDs"""
        result = await self.db.execute(
            select(Message.message_id).where(Message.parent_message_id == message_id)
        )
        child_ids = [row[0] for row in result.all()]
        
        for child_id in child_ids:
            result_set.add(child_id)
            await self._collect_descendant_messages(child_id, result_set)

    async def retry_assistant_message(
        self, 
        message_id: UUID, 
        providers: List[str], 
        local_model_id: str
    ) -> None:
        """
        Retry generating an assistant message with different models
        
        This method:
        1. Validates the target message is an assistant message
        2. Deletes all subsequent messages (children and descendants)
        3. Regenerates the assistant message using LLM orchestrator
        """
        from app.services.conversation_service import ConversationService
        
        try:
            # Get the target message
            result = await self.db.execute(
                select(Message).where(Message.message_id == message_id)
            )
            target_message = result.scalars().first()
            
            if not target_message:
                raise HTTPException(status_code=404, detail="Message not found")
            
            # Validate it's an assistant message
            if target_message.role != 'assistant':
                raise HTTPException(
                    status_code=400, 
                    detail="Can only retry assistant messages"
                )
            
            # Find the user message that this assistant message is responding to
            result = await self.db.execute(
                select(Message).where(
                    Message.conversation_id == target_message.conversation_id,
                    Message.message_id == target_message.parent_message_id
                )
            )
            parent_message = result.scalars().first()
            
            if not parent_message or parent_message.role != 'user':
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot find the user message this assistant message responds to"
                )
            
            # Store info for later use
            conversation_id = target_message.conversation_id
            parent_message_id = parent_message.message_id
            user_message_content = parent_message.content
            
            # Delete all descendant messages (subsequent messages in the conversation thread)
            descendant_ids = set()
            await self._collect_descendant_messages(message_id, descendant_ids)
            
            # Delete all descendant messages
            for descendant_id in descendant_ids:
                result = await self.db.execute(
                    select(Message).where(Message.message_id == descendant_id)
                )
                msg_to_delete = result.scalars().first()
                if msg_to_delete:
                    await self.db.delete(msg_to_delete)
            
            # Delete the target message itself
            await self.db.delete(target_message)
            await self.db.commit()
            
            # Regenerate the assistant response using the orchestrator
            from app.services.user_service import UserService
            conversation_service = ConversationService(
                db=self.db,
                user_service=UserService(self.db),
                message_service=self
            )
            await conversation_service.generate_assistant_reply(
                conversation_id=conversation_id,
                user_message_content=user_message_content,
                parent_message_id=parent_message_id,
                providers=providers,
                local_model_id=local_model_id
            )
            
        except Exception as e:
            # If any error occurs during retry, create a system message to inform the user
            try:
                error_message = f"Retry failed: {str(e)}"
                await self.create_system_message(
                    conversation_id=target_message.conversation_id if 'target_message' in locals() else conversation_id,
                    content=error_message,
                    parent_message_id=parent_message.message_id if 'parent_message' in locals() else parent_message_id
                )
            except Exception as inner_e:
                # Log the error but don't raise to avoid infinite loops
                print(f"Failed to create error system message during retry: {inner_e}")
                # Re-raise the original exception
                raise e
