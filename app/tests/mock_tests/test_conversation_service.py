import uuid
import pytest
from fastapi import HTTPException

from app.schemas.conversation import ConversationCreate, ConversationUpdate


@pytest.mark.asyncio
async def test_create_conversation(conversation_service, test_user):
    """Test creating a new conversation"""
    # Setup
    conversation_data = ConversationCreate(
        topic="Test Conversation",
        user_id=test_user.user_id,
        user_name="Custom User Name"
    )
    
    # Execute
    conversation = await conversation_service.create_conversation(conversation_data)
    
    # Assert
    assert conversation is not None
    assert conversation.conversation_id is not None
    assert conversation.user_id == test_user.user_id
    assert conversation.topic == "Test Conversation"
    assert conversation.user_name == "Custom User Name"


@pytest.mark.asyncio
async def test_create_conversation_no_user_name(conversation_service, test_user):
    """Test creating a new conversation without providing user_name"""
    # Setup
    conversation_data = ConversationCreate(
        topic="Test Conversation",
        user_id=test_user.user_id
    )
    
    # Execute
    conversation = await conversation_service.create_conversation(conversation_data)
    
    # Assert
    assert conversation is not None
    assert conversation.conversation_id is not None
    assert conversation.user_id == test_user.user_id
    assert conversation.topic == "Test Conversation"
    assert conversation.user_name == test_user.user_name  # Should fallback to user's stored name


@pytest.mark.asyncio
async def test_get_conversation(conversation_service, test_conversation):
    """Test getting a conversation by ID"""
    # Execute
    conversation = await conversation_service.get_conversation(test_conversation.conversation_id)
    
    # Assert
    assert conversation is not None
    assert conversation.conversation_id == test_conversation.conversation_id
    assert conversation.user_id == test_conversation.user_id
    assert conversation.topic == test_conversation.topic


@pytest.mark.asyncio
async def test_get_conversation_not_found(conversation_service):
    """Test getting a non-existent conversation"""
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await conversation_service.get_conversation(uuid.uuid4())
    
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_user_conversations(conversation_service, test_user, test_conversation):
    """Test getting all conversations for a user"""
    # Execute
    conversations = await conversation_service.get_user_conversations(test_user.user_id)
    
    # Assert
    assert len(conversations) >= 1
    assert any(conv.conversation_id == test_conversation.conversation_id for conv in conversations)


@pytest.mark.asyncio
async def test_get_user_conversations_empty(conversation_service):
    """Test getting conversations for a user with no conversations"""
    # Execute
    conversations = await conversation_service.get_user_conversations(uuid.uuid4())
    
    # Assert
    assert len(conversations) == 0


@pytest.mark.asyncio
async def test_update_conversation(conversation_service, test_conversation):
    """Test updating a conversation"""
    # Setup
    update_data = ConversationUpdate(
        topic="Updated Topic",
        user_name="Updated User Name"
    )
    
    # Execute
    updated_conversation = await conversation_service.update_conversation(
        test_conversation.conversation_id, update_data
    )
    
    # Assert
    assert updated_conversation is not None
    assert updated_conversation.conversation_id == test_conversation.conversation_id
    assert updated_conversation.topic == "Updated Topic"
    assert updated_conversation.user_name == "Updated User Name"


@pytest.mark.asyncio
async def test_update_conversation_partial(conversation_service, test_conversation):
    """Test updating a conversation partially"""
    # Setup
    update_data = ConversationUpdate(topic="Updated Topic Only")
    
    # Execute
    updated_conversation = await conversation_service.update_conversation(
        test_conversation.conversation_id, update_data
    )
    
    # Assert
    assert updated_conversation is not None
    assert updated_conversation.conversation_id == test_conversation.conversation_id
    assert updated_conversation.topic == "Updated Topic Only"
    assert updated_conversation.user_name == test_conversation.user_name  # Unchanged


@pytest.mark.asyncio
async def test_update_conversation_not_found(conversation_service):
    """Test updating a non-existent conversation"""
    # Setup
    update_data = ConversationUpdate(topic="Updated Topic")
    
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await conversation_service.update_conversation(uuid.uuid4(), update_data)
    
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_delete_conversation(conversation_service, test_conversation):
    """Test deleting a conversation"""
    # Execute
    result = await conversation_service.delete_conversation(test_conversation.conversation_id)
    
    # Assert
    assert result is True
    
    # Verify conversation is deleted
    with pytest.raises(HTTPException) as excinfo:
        await conversation_service.get_conversation(test_conversation.conversation_id)
    
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation_not_found(conversation_service):
    """Test deleting a non-existent conversation"""
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await conversation_service.delete_conversation(uuid.uuid4())
    
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail
