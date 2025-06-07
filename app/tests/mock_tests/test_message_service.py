import uuid
from datetime import datetime
import pytest
from fastapi import HTTPException

from app.schemas.message import MessageCreate, MessageUpdate, RoleEnum


@pytest.mark.asyncio
async def test_create_user_message(message_service, test_conversation):
    """Test creating a user message"""
    # Execute
    message = await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="Hello, this is a test message"
    )
    
    # Assert
    assert message is not None
    assert message.message_id is not None
    assert message.conversation_id == test_conversation.conversation_id
    assert message.role == RoleEnum.user
    assert message.content == "Hello, this is a test message"
    assert message.timestamp is not None
    assert message.parent_message_id is None
    assert message.llm_id is None
    assert message.llm_metadata is None


@pytest.mark.asyncio
async def test_create_assistant_message(message_service, test_conversation):
    """Test creating an assistant message"""
    # Execute
    message = await message_service.create_assistant_message(
        conversation_id=test_conversation.conversation_id,
        content="I'm an AI assistant responding to you",
        llm_id="gpt-4",
        llm_metadata={"model": "gpt-4", "usage": {"total_tokens": 20}}
    )
    
    # Assert
    assert message is not None
    assert message.message_id is not None
    assert message.conversation_id == test_conversation.conversation_id
    assert message.role == RoleEnum.assistant
    assert message.content == "I'm an AI assistant responding to you"
    assert message.timestamp is not None
    assert message.parent_message_id is None
    assert message.llm_id == "gpt-4"
    assert message.llm_metadata == {"model": "gpt-4", "usage": {"total_tokens": 20}}


@pytest.mark.asyncio
async def test_create_system_message(message_service, test_conversation):
    """Test creating a system message"""
    # Execute
    message = await message_service.create_system_message(
        conversation_id=test_conversation.conversation_id,
        content="System initialization message"
    )
    
    # Assert
    assert message is not None
    assert message.message_id is not None
    assert message.conversation_id == test_conversation.conversation_id
    assert message.role == RoleEnum.system
    assert message.content == "System initialization message"
    assert message.timestamp is not None
    assert message.parent_message_id is None
    assert message.llm_id is None
    assert message.llm_metadata is None


@pytest.mark.asyncio
async def test_create_message(message_service, test_conversation):
    """Test creating a new message directly"""
    # Setup
    message_data = MessageCreate(
        conversation_id=test_conversation.conversation_id,
        role=RoleEnum.user,
        content="Test message content"
    )
    
    # Execute
    message = await message_service.create_message(message_data)
    
    # Assert
    assert message is not None
    assert message.message_id is not None
    assert message.conversation_id == test_conversation.conversation_id
    assert message.role == RoleEnum.user
    assert message.content == "Test message content"
    assert message.timestamp is not None


@pytest.mark.asyncio
async def test_create_message_with_parent(message_service, test_conversation):
    """Test creating a message with a parent message"""
    # Create parent message
    parent = await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="Parent message"
    )
    
    # Create child message
    child = await message_service.create_assistant_message(
        conversation_id=test_conversation.conversation_id,
        content="Child message response",
        llm_id="gpt-4",
        parent_message_id=parent.message_id
    )
    
    # Assert
    assert child.parent_message_id == parent.message_id


@pytest.mark.asyncio
async def test_create_message_invalid_parent(message_service, test_conversation):
    """Test creating a message with invalid parent message ID"""
    # Setup
    invalid_uuid = uuid.uuid4()
    
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await message_service.create_assistant_message(
            conversation_id=test_conversation.conversation_id,
            content="This has an invalid parent",
            llm_id="gpt-4",
            parent_message_id=invalid_uuid
        )
    
    assert excinfo.value.status_code == 404
    assert "Parent message not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_create_message_conversation_not_found(message_service):
    """Test creating a message with non-existent conversation"""
    # Setup
    invalid_uuid = uuid.uuid4()
    
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await message_service.create_user_message(
            conversation_id=invalid_uuid,
            content="This conversation doesn't exist"
        )
    
    assert excinfo.value.status_code == 404
    assert "Conversation not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_message(message_service, test_conversation):
    """Test getting a message by ID"""
    # Create a message to test with
    created = await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="Test message for retrieval"
    )
    
    # Execute
    message = await message_service.get_message(created.message_id)
    
    # Assert
    assert message is not None
    assert message.message_id == created.message_id
    assert message.conversation_id == test_conversation.conversation_id
    assert message.content == "Test message for retrieval"


@pytest.mark.asyncio
async def test_get_message_not_found(message_service):
    """Test getting a non-existent message"""
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await message_service.get_message(uuid.uuid4())
    
    assert excinfo.value.status_code == 404
    assert "Message not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_conversation_messages(message_service, test_conversation):
    """Test getting all messages for a conversation"""
    # Create some messages
    await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="First message"
    )
    
    await message_service.create_assistant_message(
        conversation_id=test_conversation.conversation_id,
        content="First response",
        llm_id="gpt-4"
    )
    
    # Execute
    messages = await message_service.get_conversation_messages(test_conversation.conversation_id)
    
    # Assert
    assert len(messages) >= 2
    assert any(msg.role == RoleEnum.user and msg.content == "First message" for msg in messages)
    assert any(msg.role == RoleEnum.assistant and msg.content == "First response" for msg in messages)


@pytest.mark.asyncio
async def test_get_conversation_thread(message_service, test_conversation):
    """Test getting conversation messages in a threaded structure"""
    # Create a conversation with threaded messages
    root1 = await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="First thread root"
    )
    
    child1 = await message_service.create_assistant_message(
        conversation_id=test_conversation.conversation_id,
        content="Response to first thread",
        llm_id="gpt-4",
        parent_message_id=root1.message_id
    )
    
    child2 = await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="Follow-up question",
        parent_message_id=child1.message_id
    )
    
    root2 = await message_service.create_system_message(
        conversation_id=test_conversation.conversation_id,
        content="Second thread root"
    )
    
    # Execute
    threads = await message_service.get_conversation_thread(test_conversation.conversation_id)
    
    # Assert
    assert len(threads) >= 2  # At least our two root messages
    
    # Find the first thread
    first_thread = next((t for t in threads if t.content == "First thread root"), None)
    assert first_thread is not None
    assert first_thread.replies is not None
    assert len(first_thread.replies) == 1
    assert first_thread.replies[0].content == "Response to first thread"
    
    # Check second level reply
    assert first_thread.replies[0].replies is not None
    assert len(first_thread.replies[0].replies) == 1
    assert first_thread.replies[0].replies[0].content == "Follow-up question"
    
    # Find the second thread
    second_thread = next((t for t in threads if t.content == "Second thread root"), None)
    assert second_thread is not None
    assert second_thread.replies is None or len(second_thread.replies) == 0


@pytest.mark.asyncio
async def test_update_message(message_service, test_conversation):
    """Test updating a message with new data"""
    # Create message to update
    message = await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="Original content"
    )
    
    # Setup update
    update_data = MessageUpdate(content="Updated content")
    
    # Execute
    updated_message = await message_service.update_message(message.message_id, update_data)
    
    # Assert
    assert updated_message is not None
    assert updated_message.message_id == message.message_id
    assert updated_message.content == "Updated content"


@pytest.mark.asyncio
async def test_update_assistant_message_metadata(message_service, test_conversation):
    """Test updating an assistant message's metadata"""
    # Create message to update
    message = await message_service.create_assistant_message(
        conversation_id=test_conversation.conversation_id,
        content="AI response",
        llm_id="gpt-4",
        llm_metadata={"initial": "metadata"}
    )
    
    # Setup update
    update_data = MessageUpdate(llm_metadata={"updated": "metadata", "usage": {"total_tokens": 50}})
    
    # Execute
    updated_message = await message_service.update_message(message.message_id, update_data)
    
    # Assert
    assert updated_message is not None
    assert updated_message.llm_metadata == {"updated": "metadata", "usage": {"total_tokens": 50}}


@pytest.mark.asyncio
async def test_update_message_not_found(message_service):
    """Test updating a non-existent message"""
    # Setup
    update_data = MessageUpdate(content="This message doesn't exist")
    
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await message_service.update_message(uuid.uuid4(), update_data)
    
    assert excinfo.value.status_code == 404
    assert "Message not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_delete_message(message_service, test_conversation):
    """Test deleting a message"""
    # Create message to delete
    message = await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="Message to delete"
    )
    
    # Execute
    result = await message_service.delete_message(message.message_id)
    
    # Assert
    assert result is True
    
    # Verify message is deleted
    with pytest.raises(HTTPException) as excinfo:
        await message_service.get_message(message.message_id)
    
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_message_with_children(message_service, test_conversation):
    """Test deleting a message with child messages (should delete entire thread)"""
    # Create a thread of messages
    root = await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="Root message to delete"
    )
    
    child = await message_service.create_assistant_message(
        conversation_id=test_conversation.conversation_id,
        content="Child message",
        llm_id="gpt-4",
        parent_message_id=root.message_id
    )
    
    # Execute - delete the root
    result = await message_service.delete_message(root.message_id)
    
    # Assert
    assert result is True
    
    # Verify both messages are deleted
    with pytest.raises(HTTPException):
        await message_service.get_message(root.message_id)
        
    with pytest.raises(HTTPException):
        await message_service.get_message(child.message_id)


@pytest.mark.asyncio
async def test_delete_message_not_found(message_service):
    """Test deleting a non-existent message"""
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await message_service.delete_message(uuid.uuid4())
    
    assert excinfo.value.status_code == 404
    assert "Message not found" in excinfo.value.detail
