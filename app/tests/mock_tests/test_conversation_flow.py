import uuid
import pytest
from datetime import datetime

from app.models.message import Message
from app.schemas.message import RoleEnum
from app.services.llm_providers.base import LLMResponse


@pytest.mark.asyncio
async def test_complete_conversation_flow(
    message_service, 
    test_conversation,
    mock_openai_provider,
    mock_claude_provider,
    mock_ollama_provider
):
    """Test a complete conversation flow with threaded messages"""
    # 1. First user query
    user_message = await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="What is quantum computing?"
    )
    
    # Verify user message
    assert user_message.role == RoleEnum.user
    assert user_message.content == "What is quantum computing?"
    assert user_message.parent_message_id is None
    assert user_message.llm_id is None
    assert user_message.llm_metadata is None
    
    # 2. Create mock LLM response
    mock_openai_provider.model_id = "gpt-4-turbo"
    mock_metrics = {
        "tokens": 150,
        "model": "gpt-4-turbo",
        "completion_tokens": 120,
        "prompt_tokens": 30
    }
    
    # 3. Record assistant response to the user query
    assistant_message = await message_service.create_assistant_message(
        conversation_id=test_conversation.conversation_id,
        content="Quantum computing uses quantum mechanics to perform calculations...",
        llm_id="gpt-4-turbo",
        parent_message_id=user_message.message_id,
        llm_metadata=mock_metrics
    )
    
    # Verify assistant message
    assert assistant_message.role == RoleEnum.assistant
    assert "Quantum computing" in assistant_message.content
    assert assistant_message.parent_message_id == user_message.message_id
    assert assistant_message.llm_id == "gpt-4-turbo"
    assert assistant_message.llm_metadata == mock_metrics
    
    # 4. User follow-up question (as a reply to assistant's message)
    followup_message = await message_service.create_user_message(
        conversation_id=test_conversation.conversation_id,
        content="What are qubits?",
        parent_message_id=assistant_message.message_id
    )
    
    # 5. System message (e.g., informational or warning)
    system_message = await message_service.create_system_message(
        conversation_id=test_conversation.conversation_id,
        content="This conversation is for educational purposes only."
    )
    
    # 6. Get conversation thread
    thread = await message_service.get_conversation_thread(test_conversation.conversation_id)
    
    # Verify thread structure
    assert len(thread) >= 2  # At least user query and system message as roots
    
    # Find the main conversation thread
    main_thread = next(t for t in thread if t.content == "What is quantum computing?")
    assert main_thread is not None
    assert main_thread.replies is not None
    assert len(main_thread.replies) == 1
    assert main_thread.replies[0].content == "Quantum computing uses quantum mechanics to perform calculations..."
    
    # Check the follow-up is properly threaded
    assert main_thread.replies[0].replies is not None
    assert len(main_thread.replies[0].replies) == 1
    assert main_thread.replies[0].replies[0].content == "What are qubits?"
    
    # Find the system message
    system_thread = next(t for t in thread if t.role == RoleEnum.system)
    assert system_thread is not None
    assert system_thread.content == "This conversation is for educational purposes only."
    
    # 7. Test message ordering
    flat_messages = await message_service.get_conversation_messages(test_conversation.conversation_id)
    
    # Should be ordered by timestamp
    for i in range(1, len(flat_messages)):
        assert flat_messages[i-1].timestamp <= flat_messages[i].timestamp
