import json
import uuid
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.services.conversation_service import ConversationService


@pytest.fixture
def test_client():
    """Create a test client for the app"""
    return TestClient(app)


@pytest.mark.asyncio
async def test_create_conversation_endpoint(test_client, test_user):
    """Test the create conversation endpoint"""
    # Setup
    conversation_data = {
        "topic": "Learn about quantum computing",
        "user_id": str(test_user.user_id),
        "user_name": "API Test User"
    }
    
    # Execute
    with patch.object(ConversationService, 'create_conversation') as mock_create:
        # Mock the service method to avoid DB interactions
        # Create a model-like object instead of a dictionary
        conversation_id = uuid.uuid4()
        mock_result = type('MockConversation', (), {
            'conversation_id': conversation_id,
            'topic': conversation_data["topic"],
            'user_id': conversation_data["user_id"],
            'user_name': conversation_data["user_name"],
            'created_at': type('MockDatetime', (), {'isoformat': lambda: "2025-05-17T14:00:00"}),
            'updated_at': type('MockDatetime', (), {'isoformat': lambda: "2025-05-17T14:00:00"}),
            'messages': []
        })
        mock_create.return_value = mock_result
        
        response = test_client.post("/api/conversations", json=conversation_data)
    
    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["topic"] == conversation_data["topic"]
    assert response.json()["user_id"] == conversation_data["user_id"]
    assert "conversation_id" in response.json()


@pytest.mark.asyncio
async def test_first_reply_endpoint(test_client):
    """Test the first reply endpoint"""
    # Setup
    conversation_id = str(uuid.uuid4())
    config = {
        "providers": ["openai", "gemini"],
        "local_model_id": "custom_model"
    }
    
    # Execute
    with patch('fastapi.BackgroundTasks.add_task') as mock_add_task:
        response = test_client.post(
            f"/api/conversations/{conversation_id}/first-reply",
            json=config
        )
    
    # Assert
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == "processing"
    assert response.json()["conversation_id"] == conversation_id
    assert "providers" in response.json()
    assert "local_model_id" in response.json()
    
    # Verify background task was added
    mock_add_task.assert_called_once()


@pytest.mark.asyncio
async def test_first_reply_endpoint_default_config(test_client):
    """Test the first reply endpoint with default configuration"""
    # Setup
    conversation_id = str(uuid.uuid4())
    
    # Execute
    with patch('fastapi.BackgroundTasks.add_task') as mock_add_task:
        response = test_client.post(
            f"/api/conversations/{conversation_id}/first-reply"
        )
    
    # Assert
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == "processing"
    assert response.json()["conversation_id"] == conversation_id
    
    # Verify background task was added
    mock_add_task.assert_called_once()


@pytest.mark.asyncio
async def test_conversation_reply_endpoint(test_client):
    """Test the conversation reply endpoint"""
    # Setup
    conversation_id = str(uuid.uuid4())
    config = {
        "message_content": "What is the difference between classical and quantum computing?",
        "providers": ["openai", "gemini"],
        "local_model_id": "custom_model"
    }
    
    # Execute
    with patch('fastapi.BackgroundTasks.add_task') as mock_add_task:
        response = test_client.post(
            f"/api/conversations/{conversation_id}/reply",
            json=config
        )
    
    # Assert
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == "processing"
    assert response.json()["conversation_id"] == conversation_id
    assert response.json()["providers"] == config["providers"]
    assert response.json()["local_model_id"] == config["local_model_id"]
    
    # Verify background task was added with message_content
    mock_add_task.assert_called_once()
    # Check the arguments passed to the background task
    call_args = mock_add_task.call_args[0]
    assert len(call_args) >= 1  # At least one arg (the function)
    # Check kwargs passed to the background task
    call_kwargs = mock_add_task.call_args[1]
    assert call_kwargs.get("message_content") == config["message_content"]
    assert call_kwargs.get("conversation_id") == uuid.UUID(conversation_id)


@pytest.mark.asyncio
async def test_conversation_reply_endpoint_missing_message(test_client):
    """Test the conversation reply endpoint with missing message content"""
    # Setup
    conversation_id = str(uuid.uuid4())
    config = {
        # Missing message_content
        "providers": ["openai", "gemini"],
        "local_model_id": "custom_model"
    }
    
    # Mock the conversation service to avoid DB interactions
    with patch.object(ConversationService, 'add_conversation_reply') as mock_reply:
        # Execute
        response = test_client.post(
            f"/api/conversations/{conversation_id}/reply",
            json=config
        )
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # Validation error response contains error details
        detail = response.json()["detail"]
        
        # Handle both string and list formats for error details
        if isinstance(detail, str):
            # String error message format
            assert "message_content" in detail
        else:
            # List of validation errors format
            assert any("message_content" in error.get("loc", []) for error in detail)
        
        # Verify service was not called
        mock_reply.assert_not_called()


@pytest.mark.asyncio
async def test_get_conversation_messages_endpoint(test_client, test_conversation, test_message):
    """Test getting conversation messages endpoint with threaded structure"""
    # Setup
    conversation_id = str(test_conversation.conversation_id)
    message_id = str(test_message.message_id)
    assistant_message_id = str(uuid.uuid4())
    
    # Create threaded message structure
    mock_thread = [
        {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "role": "user",
            "content": "Test question",
            "timestamp": "2025-05-17T14:00:00",
            "parent_message_id": None,
            "llm_id": None,
            "llm_metadata": None,
            "replies": [
                {
                    "message_id": assistant_message_id,
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": "Test answer",
                    "timestamp": "2025-05-17T14:01:00",
                    "parent_message_id": message_id,
                    "llm_id": "ollama/gemma3:12b",
                    "llm_metadata": {"confidence": 0.95},
                    "replies": None
                }
            ]
        }
    ]
    
    # Execute with both mocks
    with patch.object(ConversationService, 'get_conversation') as mock_get_conversation, \
         patch('app.services.message_service.MessageService.get_conversation_thread') as mock_get_thread:
        
        # Basic conversation object to verify it exists
        mock_conversation = type('MockConversation', (), {
            'conversation_id': uuid.UUID(conversation_id),
            'topic': "Test topic"
        })
        mock_get_conversation.return_value = mock_conversation
        
        # Return threaded message structure
        mock_get_thread.return_value = mock_thread
        
        response = test_client.get(f"/api/conversations/{conversation_id}/messages")
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result) == 1  # One root message
    
    # Verify root message
    root_message = result[0]
    assert root_message["role"] == "user"
    assert root_message["content"] == "Test question"
    assert root_message["parent_message_id"] is None
    
    # Verify replies structure exists
    assert "replies" in root_message
    assert isinstance(root_message["replies"], list)
    assert len(root_message["replies"]) == 1
    
    # Verify reply message
    reply = root_message["replies"][0]
    assert reply["role"] == "assistant"
    assert reply["content"] == "Test answer"
    assert reply["parent_message_id"] == message_id
    assert reply["llm_id"] == "ollama/gemma3:12b"
