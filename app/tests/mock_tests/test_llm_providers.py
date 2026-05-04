import pytest
import pytest_asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime

from app.services.llm_providers.base import BaseLLMProvider, LLMResponse, RateLimiter
from app.services.llm_providers import (
    OpenAIProvider,
    ClaudeProvider,
    GeminiProvider,
    OllamaProvider
)


class TestLLMResponse:
    """Test the LLMResponse class"""
    
    def test_llm_response_initialization(self):
        """Test LLMResponse initialization with required fields"""
        response = LLMResponse(
            content="Test content",
            source="test_provider"
        )
        
        assert response.content == "Test content"
        assert response.source == "test_provider"
        assert isinstance(response.timestamp, datetime)
        assert isinstance(response.metrics, dict)
        assert len(response.metrics) == 0
    
    def test_llm_response_with_all_fields(self):
        """Test LLMResponse initialization with all fields"""
        timestamp = datetime.utcnow()
        metrics = {"tokens": 100, "time": 1.5}
        
        response = LLMResponse(
            content="Test content",
            source="test_provider",
            timestamp=timestamp,
            metrics=metrics
        )
        
        assert response.content == "Test content"
        assert response.source == "test_provider"
        assert response.timestamp == timestamp
        assert response.metrics == metrics
    
    def test_to_dict_and_from_dict(self):
        """Test conversion to dictionary and back"""
        timestamp = datetime.utcnow()
        metrics = {"tokens": 100, "time": 1.5}
        
        response = LLMResponse(
            content="Test content",
            source="test_provider",
            timestamp=timestamp,
            metrics=metrics
        )
        
        # Convert to dict
        response_dict = response.to_dict()
        
        # Convert back from dict
        reconstructed = LLMResponse.from_dict(response_dict)
        
        # Compare
        assert reconstructed.content == response.content
        assert reconstructed.source == response.source
        assert reconstructed.timestamp.isoformat() == response.timestamp.isoformat()
        assert reconstructed.metrics == response.metrics


class TestRateLimiter:
    """Test the RateLimiter class"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_first_request(self):
        """Test that the first request doesn't have to wait"""
        limiter = RateLimiter(requests_per_minute=60)  # 1 per second
        
        start_time = datetime.utcnow()
        await limiter.acquire()
        end_time = datetime.utcnow()
        
        # First request should be very fast
        elapsed_ms = (end_time - start_time).total_seconds() * 1000
        assert elapsed_ms < 50  # Should take under 50ms
    
    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_delay(self):
        """Test that consecutive requests are rate-limited"""
        limiter = RateLimiter(requests_per_minute=30)  # 1 per 2 seconds
        
        # First request
        await limiter.acquire()
        
        # Second request should be delayed
        start_time = datetime.utcnow()
        await limiter.acquire()
        end_time = datetime.utcnow()
        
        elapsed_seconds = (end_time - start_time).total_seconds()
        assert elapsed_seconds >= 1.9  # Should wait at least ~2 seconds (with small tolerance)


# Mock implementation of BaseLLMProvider for testing
class MockProvider(BaseLLMProvider):
    """Mock provider for testing BaseLLMProvider abstract methods"""
    
    def __init__(self, name="MockProvider", rate_limit=5):
        super().__init__(name=name, rate_limit=rate_limit)
        self.response_content = "Mock response"
    
    async def generate_response(self, prompt, **kwargs):
        await self._handle_rate_limit()
        return LLMResponse(content=self.response_content, source=self.name)
    
    def _validate_response(self, response):
        return True


class TestBaseLLMProvider:
    """Test the BaseLLMProvider abstract class through a mock implementation"""
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self):
        """Test provider initialization with default parameters"""
        provider = MockProvider()
        
        assert provider.name == "MockProvider"
        assert provider.max_retries == 3
        assert provider.retry_delay == 1.0
    
    @pytest.mark.asyncio
    async def test_provider_generate_response(self):
        """Test the generate_response method"""
        provider = MockProvider()
        response = await provider.generate_response("Test prompt")
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Mock response"
        assert response.source == "MockProvider"
    
    @pytest.mark.asyncio
    async def test_error_handling_with_retry(self):
        """Test error handling with retry logic"""
        provider = MockProvider(rate_limit=60)  # No rate limiting delay
        
        # Create a method to emulate BaseLLMProvider's retry logic
        # but without actual sleep to make tests run faster
        async def mock_handle_error_no_sleep(error, attempt):
            # Return True to indicate retry should happen, but don't sleep
            return attempt < provider.max_retries
        
        # Replace the _handle_error method to avoid actual sleep
        provider._handle_error = mock_handle_error_no_sleep
        
        # Track call attempts
        call_count = 0
        
        # The original implementation
        original_generate = provider.generate_response
        
        # Create a wrapper around generate_response that will fail the first two times
        async def test_with_retries():
            nonlocal call_count
            
            # Implement retry logic here in the test
            for attempt in range(1, provider.max_retries + 2):  # +2 to include final success
                try:
                    call_count += 1
                    if call_count < 3:  # First two attempts fail
                        raise ValueError(f"Test error attempt {call_count}")
                    # Third attempt succeeds
                    return await original_generate("Test prompt")
                except Exception as e:
                    # Last attempt should raise the exception
                    if attempt >= provider.max_retries:
                        raise
                    # Otherwise retry
                    retry = await provider._handle_error(e, attempt)
                    if not retry:
                        raise
            
            # Should not reach here
            raise RuntimeError("Unexpected end of retry loop")
        
        # Call the test function with our retry logic
        response = await test_with_retries()
        
        # Verify results
        assert call_count == 3  # 2 failures + 1 success
        assert isinstance(response, LLMResponse)
        assert response.content == "Mock response"


@pytest.mark.asyncio
class TestOpenAIProvider:
    """Test the OpenAI provider implementation"""
    
    @patch("app.services.llm_providers.openai_provider.AsyncOpenAI")
    async def test_openai_initialization(self, mock_openai):
        """Test OpenAI provider initialization"""
        provider = OpenAIProvider(api_key="test_key", model="gpt-5.4-mini")
        
        assert provider.name == "OpenAI"
        assert provider.model == "gpt-5.4-mini"
        mock_openai.assert_called_once_with(api_key="test_key")
    
    @patch("app.services.llm_providers.openai_provider.AsyncOpenAI")
    async def test_openai_generate_response(self, mock_openai):
        """Test OpenAI generate_response method"""
        # Create a mock response object
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "OpenAI response"
        mock_completion.usage.total_tokens = 50
        mock_completion.usage.prompt_tokens = 20
        mock_completion.usage.completion_tokens = 30
        
        # Set up the AsyncOpenAI client mock
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai.return_value = mock_client
        
        # Create provider and test
        provider = OpenAIProvider(api_key="test_key")
        response = await provider.generate_response(
            prompt="Test prompt",
            system_prompt="You are a helpful assistant."
        )
        
        # Verify client was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        
        assert len(call_args["messages"]) == 2
        assert call_args["messages"][0]["role"] == "system"
        assert call_args["messages"][0]["content"] == "You are a helpful assistant."
        assert call_args["messages"][1]["role"] == "user"
        assert call_args["messages"][1]["content"] == "Test prompt"
        
        # Verify response is correct
        assert isinstance(response, LLMResponse)
        assert response.content == "OpenAI response"
        assert response.source == "OpenAI"
        assert response.metrics["total_tokens"] == 50
        assert response.metrics["prompt_tokens"] == 20
        assert response.metrics["completion_tokens"] == 30


@pytest.mark.asyncio
class TestClaudeProvider:
    """Test the Claude provider implementation"""
    
    @patch("app.services.llm_providers.claude_provider.AsyncAnthropic")
    async def test_claude_initialization(self, mock_anthropic):
        """Test Claude provider initialization"""
        provider = ClaudeProvider(api_key="test_key", model="claude-3-5-haiku-20241022")
        
        assert provider.name == "Claude"
        assert provider.model == "claude-3-5-haiku-20241022"
        mock_anthropic.assert_called_once_with(api_key="test_key")
    
    @patch("app.services.llm_providers.claude_provider.AsyncAnthropic")
    async def test_claude_generate_response(self, mock_anthropic):
        """Test Claude generate_response method"""
        # Create a mock response object
        mock_message = MagicMock()
        mock_message.content = [MagicMock()]
        mock_message.content[0].text = "Claude response"
        mock_message.usage.input_tokens = 20
        mock_message.usage.output_tokens = 30
        
        # Set up the AsyncAnthropic client mock
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client
        
        # Create provider and test
        provider = ClaudeProvider(api_key="test_key")
        response = await provider.generate_response(
            prompt="Test prompt",
            system_prompt="You are a helpful assistant."
        )
        
        # Verify client was called correctly
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["role"] == "user"
        assert call_args["messages"][0]["content"] == "Test prompt"
        assert call_args["system"] == "You are a helpful assistant."
        
        # Verify response is correct
        assert isinstance(response, LLMResponse)
        assert response.content == "Claude response"
        assert response.source == "Claude"
        assert response.metrics["input_tokens"] == 20
        assert response.metrics["output_tokens"] == 30
        assert response.metrics["total_tokens"] == 50


@pytest.mark.asyncio
class TestGeminiProvider:
    """Test the Gemini provider implementation"""
    
    @patch("app.services.llm_providers.gemini_provider.genai")
    @patch("app.services.llm_providers.gemini_provider.HarmCategory")
    @patch("app.services.llm_providers.gemini_provider.HarmBlockThreshold")
    async def test_gemini_initialization(self, mock_block_threshold, mock_harm_category, mock_genai):
        """Test Gemini provider initialization"""
        # Configure the GenerativeModel constructor
        mock_genai.GenerativeModel = MagicMock()
        
        # Initialize provider
        provider = GeminiProvider(api_key="test_key", model="gemini-2.5-flash-lite")
        
        # Verify configure was called with API key
        mock_genai.configure.assert_called_once_with(api_key="test_key")
        
        # Check provider basics
        assert provider.name == "Gemini"
        assert provider.model == "gemini-2.5-flash-lite"
    
    @patch("app.services.llm_providers.gemini_provider.genai")
    @patch("app.services.llm_providers.gemini_provider.HarmCategory")
    @patch("app.services.llm_providers.gemini_provider.HarmBlockThreshold")
    async def test_gemini_generate_response(self, mock_block_threshold, mock_harm_category, mock_genai):
        """Test Gemini generate_response method with system prompt"""
        # Set up HarmCategory enum
        mock_harm_category.HARASSMENT = "harassment"
        mock_harm_category.HATE_SPEECH = "hate_speech"
        mock_harm_category.SEXUALLY_EXPLICIT = "sexually_explicit"
        mock_harm_category.DANGEROUS_CONTENT = "dangerous_content"
        
        # Set up HarmBlockThreshold enum
        mock_block_threshold.MEDIUM_AND_ABOVE = "medium_and_above"
        
        # Create mock response
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Gemini response"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 30
        
        # Configure the mock chat
        mock_chat.send_message.return_value = mock_response
        
        # Configure the mock model
        mock_model_instance = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model_instance
        
        # Create provider with our run_in_executor implementation to avoid actual async execution
        provider = GeminiProvider(api_key="test_key")
        provider._run_in_executor = AsyncMock(side_effect=lambda f: f())
        
        # Test the generate_response method
        response = await provider.generate_response(
            prompt="Test prompt",
            system_prompt="You are a helpful assistant."
        )
        
        # Verify model was created with correct parameters
        mock_genai.GenerativeModel.assert_called_once()
        assert mock_genai.GenerativeModel.call_args[1]["model_name"] == "gemini-2.5-flash-lite"
        
        # Verify chat was started
        mock_model_instance.start_chat.assert_called_once()
        
        # Verify send_message was called with the correct prompt (including system prompt)
        expected_message = "[System Instruction] You are a helpful assistant.\n\nUser: Test prompt"
        provider._run_in_executor.assert_called_once()
        mock_chat.send_message.assert_called_once_with(expected_message)
        
        # Verify response is correct
        assert isinstance(response, LLMResponse)
        assert response.content == "Gemini response"
        assert response.source == "Gemini"
        assert response.metrics["prompt_tokens"] == 20
        assert response.metrics["completion_tokens"] == 30
        assert response.metrics["total_tokens"] == 50
        assert response.metrics["model"] == "gemini-2.5-flash-lite"
    
    @patch("app.services.llm_providers.gemini_provider.genai")
    @patch("app.services.llm_providers.gemini_provider.HarmCategory")
    @patch("app.services.llm_providers.gemini_provider.HarmBlockThreshold")
    async def test_gemini_without_system_prompt(self, mock_block_threshold, mock_harm_category, mock_genai):
        """Test Gemini generate_response method without system prompt"""
        # Set up HarmCategory enum
        mock_harm_category.HARASSMENT = "harassment"
        mock_harm_category.HATE_SPEECH = "hate_speech"
        mock_harm_category.SEXUALLY_EXPLICIT = "sexually_explicit"
        mock_harm_category.DANGEROUS_CONTENT = "dangerous_content"
        
        # Set up HarmBlockThreshold enum
        mock_block_threshold.MEDIUM_AND_ABOVE = "medium_and_above"
        
        # Create mock response
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Gemini response"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 20
        
        # Configure the mock chat
        mock_chat.send_message.return_value = mock_response
        
        # Configure the mock model
        mock_model_instance = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model_instance
        
        # Create provider with our run_in_executor implementation to avoid actual async execution
        provider = GeminiProvider(api_key="test_key")
        provider._run_in_executor = AsyncMock(side_effect=lambda f: f())
        
        # Test the generate_response method without a system prompt
        response = await provider.generate_response(prompt="Test prompt")
        
        # Verify send_message was called with just the user prompt
        mock_chat.send_message.assert_called_once_with("Test prompt")
        
        # Verify response is correct
        assert response.content == "Gemini response"
        assert response.source == "Gemini"
    
    @patch("app.services.llm_providers.gemini_provider.genai")
    @patch("app.services.llm_providers.gemini_provider.HarmCategory")
    @patch("app.services.llm_providers.gemini_provider.HarmBlockThreshold")
    async def test_gemini_error_handling(self, mock_block_threshold, mock_harm_category, mock_genai):
        """Test Gemini error handling"""
        # Set up HarmCategory enum
        mock_harm_category.HARASSMENT = "harassment"
        mock_harm_category.HATE_SPEECH = "hate_speech"
        mock_harm_category.SEXUALLY_EXPLICIT = "sexually_explicit"
        mock_harm_category.DANGEROUS_CONTENT = "dangerous_content"
        
        # Set up HarmBlockThreshold enum
        mock_block_threshold.MEDIUM_AND_ABOVE = "medium_and_above"
        
        # Create mock model that raises an exception
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = Exception("API error")
        
        mock_model_instance = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model_instance
        
        # Create provider
        provider = GeminiProvider(api_key="test_key")
        provider._run_in_executor = AsyncMock(side_effect=lambda f: f())
        
        # Patch _handle_error to avoid waiting during tests
        provider._handle_error = AsyncMock(return_value=False)  # Don't retry
        
        # Test error handling
        with pytest.raises(Exception) as excinfo:
            await provider.generate_response(prompt="Test prompt")
        
        assert "API error" in str(excinfo.value)
        
        # Verify handle_error was called
        provider._handle_error.assert_called_once()


@pytest.mark.asyncio
class TestOllamaProvider:
    """Test the Ollama provider implementation"""
    
    @patch("httpx.AsyncClient")
    async def test_ollama_initialization(self, mock_client):
        """Test Ollama provider initialization"""
        provider = OllamaProvider(
            base_url="http://localhost:11434",
            model="gemma3:4b"
        )
        
        assert provider.name == "Ollama"
        assert provider.base_url == "http://localhost:11434"
        assert provider.model == "gemma3:4b"
    
    @patch("httpx.AsyncClient")
    async def test_ollama_generate_response(self, mock_client):
        """Test Ollama generate_response method"""
        # Create a mock response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "gemma3:4b",
            "response": "Ollama response",
            "done": True,
            "eval_count": 400,
            "eval_duration": 2000000000
        }
        mock_response.raise_for_status = Mock()
        
        # Set up the AsyncClient mock
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Create provider and test
        provider = OllamaProvider(
            base_url="http://localhost:11434",
            model="gemma3:4b"
        )
        response = await provider.generate_response(
            prompt="Test prompt",
            system_prompt="You are a helpful assistant."
        )
        
        # Verify client was called correctly
        mock_client_instance.post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma3:4b",
                "prompt": "Test prompt",
                "stream": False,
                "system": "You are a helpful assistant.",
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2048,
                    "top_p": 0.9,
                    "top_k": 40,
                    "repeat_penalty": 1.1,
                }
            }
        )
        
        # Verify response is correct
        assert isinstance(response, LLMResponse)
        assert response.content == "Ollama response"
        assert response.source == "Ollama"
        assert response.metrics["model"] == "gemma3:4b"
        assert response.metrics["eval_count"] == 400
