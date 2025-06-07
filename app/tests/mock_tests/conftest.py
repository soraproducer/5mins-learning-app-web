import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.llm_providers.base import LLMResponse
from app.services.llm_providers import (
    OpenAIProvider,
    ClaudeProvider,
    OllamaProvider,
    LLMOrchestrator,
    AnalysisResult
)


# Use PostgreSQL database for testing
TEST_DATABASE_URL = "postgresql+asyncpg://sorap@localhost:5432/test_db"

# Create a new engine for test database
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

# Create test session factory
TestingSessionLocal = sessionmaker(
    test_engine, 
    expire_on_commit=False, 
    class_=AsyncSession,
)


# Override the get_db_session dependency to use the test database
@pytest_asyncio.fixture(scope="function")
async def db_session():
    # Create engine and session *inside* the fixture
    test_engine = create_async_engine(
        "postgresql+asyncpg://sorap@localhost:5432/test_db",
        echo=False,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Drop tables after the test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user for tests"""
    user = User(
        user_id=uuid4(),
        user_name="Test User"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_conversation(db_session, test_user):
    """Create a test conversation for tests"""
    conversation = Conversation(
        conversation_id=uuid4(),
        user_id=test_user.user_id,
        user_name=test_user.user_name,
        topic="Test Topic"
    )
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)
    return conversation


@pytest_asyncio.fixture
async def test_message(db_session, test_conversation):
    """Create a test message for tests"""
    message = Message(
        message_id=uuid4(),
        conversation_id=test_conversation.conversation_id,
        role="user",
        content="This is a test message",
        parent_message_id=None,
        llm_id=None,
        llm_metadata=None
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)
    return message


@pytest_asyncio.fixture
async def test_assistant_message(db_session, test_conversation, test_message):
    """Create a test assistant message that replies to test_message"""
    message = Message(
        message_id=uuid4(),
        conversation_id=test_conversation.conversation_id,
        role="assistant",
        content="This is a test assistant response",
        parent_message_id=test_message.message_id,
        llm_id="gpt-4",
        llm_metadata={"model": "gpt-4", "usage": {"total_tokens": 15}}
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)
    return message


@pytest.fixture
def user_service(db_session):
    """Fixture to create a UserService instance with test DB session"""
    from app.services.user_service import UserService
    return UserService(db=db_session)


@pytest.fixture
def conversation_service(db_session, user_service):
    """Fixture to create a ConversationService instance with test DB session"""
    from app.services.conversation_service import ConversationService
    return ConversationService(db=db_session, user_service=user_service)


@pytest.fixture
def message_service(db_session):
    """Fixture to create a MessageService instance with test DB session"""
    from app.services.message_service import MessageService
    return MessageService(db=db_session)


# LLM Provider Fixtures

@pytest_asyncio.fixture
async def mock_llm_response():
    """Create a mock LLM response for testing"""
    return LLMResponse(
        content="This is a mock response for testing",
        source="test_provider",
        timestamp=datetime.utcnow(),
        metrics={"elapsed_time": 0.1, "total_tokens": 20}
    )


@pytest_asyncio.fixture
async def mock_openai_provider(mock_llm_response):
    """Mock OpenAI provider that returns a predefined response"""
    provider = AsyncMock(spec=OpenAIProvider)
    provider.name = "OpenAI"
    provider.generate_response.return_value = mock_llm_response
    return provider


@pytest_asyncio.fixture
async def mock_claude_provider(mock_llm_response):
    """Mock Claude provider that returns a predefined response"""
    provider = AsyncMock(spec=ClaudeProvider)
    provider.name = "Claude"
    provider.generate_response.return_value = mock_llm_response
    return provider


@pytest_asyncio.fixture
async def mock_ollama_provider(mock_llm_response):
    """Mock Ollama provider that returns a predefined response"""
    provider = AsyncMock(spec=OllamaProvider)
    provider.name = "Ollama"
    provider.generate_response.return_value = mock_llm_response
    return provider


@pytest_asyncio.fixture
async def mock_llm_orchestrator(mock_openai_provider, mock_claude_provider, mock_ollama_provider):
    """Mock LLM orchestrator with mock providers"""
    orchestrator = LLMOrchestrator(
        openai_provider=mock_openai_provider,
        claude_provider=mock_claude_provider,
        ollama_provider=mock_ollama_provider
    )
    return orchestrator


@pytest_asyncio.fixture
async def mock_analysis_result(mock_llm_response):
    """Mock analysis result for testing"""
    return AnalysisResult(
        summary="This is a mock summary",
        sources=["OpenAI", "Claude"],
        consensus_items=["Point of agreement 1", "Point of agreement 2"],
        difference_items=["Difference 1"],
        confidence="High",
        raw_responses={
            "OpenAI": mock_llm_response,
            "Claude": mock_llm_response
        }
    )
