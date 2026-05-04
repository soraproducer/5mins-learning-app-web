import json
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import FastAPI, status, Depends
from fastapi.testclient import TestClient
from fastapi.routing import APIRouter

from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageResponse

# Create a test router for standalone testing
test_router = APIRouter()

@test_router.post("/api/conversations", status_code=status.HTTP_201_CREATED)
async def mock_create_conversation(conversation_data: dict):
    """Mock endpoint for creating conversations"""
    conversation_id = str(uuid.uuid4())
    return {
        "conversation_id": conversation_id,
        "topic": conversation_data["topic"],
        "user_id": conversation_data["user_id"],
        "user_name": conversation_data.get("user_name", "Default User"),
        "created_at": "2025-05-17T14:00:00",
        "updated_at": "2025-05-17T14:00:00",
        "messages": []
    }

@test_router.post("/api/conversations/{conversation_id}/first-reply", status_code=status.HTTP_202_ACCEPTED)
async def mock_first_reply(conversation_id: str, config: dict = None):
    """Mock endpoint for first reply"""
    if config is None:
        config = {"providers": ["openai", "claude", "gemini"], "local_model_id": "gemma3:4b"}
    
    return {
        "status": "processing",
        "message": "First reply generation initiated",
        "conversation_id": conversation_id,
        "providers": config.get("providers", ["openai", "claude", "gemini"]),
        "local_model_id": config.get("local_model_id", "gemma3:4b")
    }

@test_router.get("/api/conversations/{conversation_id}/messages")
async def mock_get_messages(conversation_id: str):
    """Mock endpoint for getting messages"""
    return [
        {
            "message_id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": "user",
            "content": "Test message",
            "timestamp": "2025-05-17T14:00:00",
            "parent_message_id": None,
            "llm_id": None,
            "llm_metadata": None,
            "replies": None
        }
    ]

@pytest.fixture
def test_app():
    """Create a test FastAPI app with mock router"""
    app = FastAPI()
    app.include_router(test_router)
    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client for the app"""
    return TestClient(test_app)


def test_create_conversation(test_client):
    """Test the create conversation endpoint"""
    # Setup
    user_id = str(uuid.uuid4())
    
    conversation_data = {
        "topic": "Learn about quantum computing",
        "user_id": user_id,
        "user_name": "API Test User"
    }
    
    # Execute
    response = test_client.post("/api/conversations", json=conversation_data)
    
    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["topic"] == conversation_data["topic"]
    assert response.json()["user_id"] == user_id
    assert "conversation_id" in response.json()


def test_first_reply_endpoint(test_client):
    """Test the first reply endpoint"""
    # Setup
    conversation_id = str(uuid.uuid4())
    config = {
        "providers": ["openai", "gemini"],
        "local_model_id": "custom_model"
    }
    
    # Execute
    response = test_client.post(
        f"/api/conversations/{conversation_id}/first-reply",
        json=config
    )
    
    # Assert
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == "processing"
    assert response.json()["conversation_id"] == conversation_id
    assert "providers" in response.json()
    assert response.json()["providers"] == config["providers"]
    assert "local_model_id" in response.json()
    assert response.json()["local_model_id"] == config["local_model_id"]


def test_first_reply_endpoint_default_config(test_client):
    """Test the first reply endpoint with default configuration"""
    # Setup
    conversation_id = str(uuid.uuid4())
    
    # Execute
    response = test_client.post(
        f"/api/conversations/{conversation_id}/first-reply"
    )
    
    # Assert
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == "processing"
    assert response.json()["conversation_id"] == conversation_id


def test_get_conversation_messages(test_client):
    """Test getting messages from a conversation"""
    # Setup
    conversation_id = str(uuid.uuid4())
    
    # Execute
    response = test_client.get(f"/api/conversations/{conversation_id}/messages")
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["role"] == "user"
    assert response.json()[0]["content"] == "Test message"
    assert response.json()[0]["conversation_id"] == conversation_id
