import uuid
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException

from app.schemas.conversation import ConversationCreate


@pytest.mark.asyncio
async def test_start_first_reply(
    conversation_service, 
    test_conversation, 
    message_service, 
    mock_llm_orchestrator, 
    mock_analysis_result
):
    """Test generating the first reply for a conversation"""
    # Setup - patch the LLMOrchestrator's process_query method
    mock_llm_orchestrator.process_query = AsyncMock(return_value=mock_analysis_result)
    conversation_service.llm_orchestrator = mock_llm_orchestrator
    conversation_service.message_service = message_service
    
    # Execute
    result = await conversation_service.start_first_reply(
        conversation_id=test_conversation.conversation_id,
        providers=["openai", "claude"],
        local_model_id="gemma3:12b"
    )
    
    # Assert
    assert result == mock_analysis_result.summary
    
    # Verify LLMOrchestrator was called correctly
    mock_llm_orchestrator.process_query.assert_called_once_with(
        query=test_conversation.topic,
        providers=["openai", "claude"]
    )
    
    # Verify message was created
    messages = await message_service.get_conversation_messages(test_conversation.conversation_id)
    assert any(m.role == "assistant" and m.content == mock_analysis_result.summary for m in messages)


@pytest.mark.asyncio
async def test_start_first_reply_timeout(
    conversation_service, 
    test_conversation, 
    message_service
):
    """Test timeout handling when generating the first reply"""
    # Setup - create mock LLMOrchestrator that times out
    mock_llm_orchestrator = AsyncMock()
    
    # Mock process_query to raise TimeoutError
    async def mock_timeout(*args, **kwargs):
        await asyncio.sleep(0.1)  # Small delay to simulate processing
        raise asyncio.TimeoutError("Operation timed out")
    
    mock_llm_orchestrator.process_query = mock_timeout
    conversation_service.llm_orchestrator = mock_llm_orchestrator
    conversation_service.message_service = message_service
    
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await conversation_service.start_first_reply(test_conversation.conversation_id)
    
    # Verify exception
    assert excinfo.value.status_code == 504
    assert "timed out" in excinfo.value.detail
    
    # Verify error message was created
    messages = await message_service.get_conversation_messages(test_conversation.conversation_id)
    assert any(m.role == "system" and "timed out" in m.content for m in messages)


@pytest.mark.asyncio
async def test_start_first_reply_error(
    conversation_service, 
    test_conversation, 
    message_service
):
    """Test generic error handling when generating the first reply"""
    # Setup - create mock LLMOrchestrator that raises error
    mock_llm_orchestrator = AsyncMock()
    
    # Mock process_query to raise Exception
    async def mock_error(*args, **kwargs):
        raise ValueError("Provider not available")
    
    mock_llm_orchestrator.process_query = mock_error
    conversation_service.llm_orchestrator = mock_llm_orchestrator
    conversation_service.message_service = message_service
    
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await conversation_service.start_first_reply(test_conversation.conversation_id)
    
    # Verify exception
    assert excinfo.value.status_code == 500
    assert "Error generating first reply" in excinfo.value.detail
    
    # Verify error message was created
    messages = await message_service.get_conversation_messages(test_conversation.conversation_id)
    assert any(m.role == "system" and "Error generating first reply" in m.content for m in messages)


@pytest.mark.asyncio
async def test_start_first_reply_conversation_not_found(conversation_service):
    """Test generating the first reply for a non-existent conversation"""
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await conversation_service.start_first_reply(uuid.uuid4())
    
    # Verify exception
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail
