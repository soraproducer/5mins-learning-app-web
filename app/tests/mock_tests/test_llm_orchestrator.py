import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, List, Tuple, Any

from app.services.llm_providers.base import LLMResponse
from app.services.llm_providers import (
    OpenAIProvider, 
    ClaudeProvider,
    GeminiProvider,
    OllamaProvider,
    LLMOrchestrator,
    AnalysisResult
)
from app.core.config import settings

@pytest.mark.asyncio
class TestLLMOrchestrator:
    """Test the LLM orchestrator functionality"""
    
    @pytest.fixture
    def provider_mocks(self, mock_openai_provider, mock_claude_provider, mock_gemini_provider, mock_ollama_provider):
        """Return a dictionary of all provider mocks"""
        return {
            "openai": mock_openai_provider,
            "claude": mock_claude_provider,
            "gemini": mock_gemini_provider,
            "ollama": mock_ollama_provider
        }
    
    @pytest.fixture
    def default_orchestrator(self, mock_openai_provider, mock_claude_provider, mock_gemini_provider, mock_ollama_provider):
        """Create a default orchestrator with all providers"""
        return self._create_orchestrator(
            mock_openai_provider=mock_openai_provider,
            mock_claude_provider=mock_claude_provider,
            mock_gemini_provider=mock_gemini_provider,
            mock_ollama_provider=mock_ollama_provider
        )
    
    # Common response data and helper methods
    PROVIDER_RESPONSES = {
        "openai": "OpenAI test response",
        "claude": "Claude test response",
        "gemini": "Gemini test response",
        "ollama": "Summary of responses from all models"
    }
    
    def _create_provider_response(self, provider_name: str, custom_content: str = None) -> LLMResponse:
        """Create a standard response for a given provider"""
        content = custom_content or self.PROVIDER_RESPONSES.get(provider_name, f"{provider_name} response")
        return LLMResponse(
            content=content,
            source=provider_name.capitalize(),
            metrics={"total_tokens": 50 + len(provider_name)}
        )
    
    def _configure_provider_mocks(
        self, 
        mock_providers: Dict[str, AsyncMock],
        custom_responses: Dict[str, str] = None
    ) -> None:
        """Configure all provider mocks with standard responses"""
        custom_responses = custom_responses or {}
        
        for name, mock in mock_providers.items():
            response = self._create_provider_response(
                name, 
                custom_content=custom_responses.get(name)
            )
            mock.generate_response.return_value = response
    
    def _verify_provider_calls(
        self, 
        mock_providers: Dict[str, AsyncMock],
        expected_called: List[str],
        prompt: str = "Test query",
        system_prompt: str = "You are helpful"
    ) -> None:
        """Verify which providers were called with the expected arguments"""
        all_providers = set(mock_providers.keys())
        expected_called_set = set(expected_called)
        
        # Verify all expected providers were called
        for name in expected_called:
            mock = mock_providers[name]
            # Just verify the provider was called, not checking exact arguments
            # since we now use EXPERT_SYSTEM_PROMPT template
            assert mock.generate_response.call_count == 1
            # Verify system prompt is passed correctly
            assert mock.generate_response.call_args[1]['system_prompt'] == system_prompt
            # Verify the prompt contains our original query
            formatted_prompt = mock.generate_response.call_args[1]['prompt']
            assert prompt in formatted_prompt
        
        # For all providers except Ollama that are not expected to be called
        for name, mock in mock_providers.items():
            if name not in expected_called_set and name != "ollama":
                mock.generate_response.assert_not_called()
        
        # Ollama should always be called for analysis, so we don't check it here
    
    def _create_orchestrator(
        self,
        mock_openai_provider: AsyncMock,
        mock_claude_provider: AsyncMock,
        mock_gemini_provider: AsyncMock,
        mock_ollama_provider: AsyncMock,
        reset_mocks: bool = True
    ) -> LLMOrchestrator:
        """Create an orchestrator instance with all mock providers"""
        # Reset mocks if requested
        if reset_mocks:
            for mock in [mock_openai_provider, mock_claude_provider, mock_gemini_provider, mock_ollama_provider]:
                mock.reset_mock()
        
        # Create and return orchestrator
        return LLMOrchestrator(
            openai_provider=mock_openai_provider,
            claude_provider=mock_claude_provider,
            gemini_provider=mock_gemini_provider,
            ollama_provider=mock_ollama_provider
        )
    
    async def test_orchestrator_initialization(self):
        """Test orchestrator initialization with defaults"""
        # Create manual mocks instead of patching
        mock_openai = AsyncMock(spec=OpenAIProvider)
        mock_claude = AsyncMock(spec=ClaudeProvider)
        mock_gemini = AsyncMock(spec=GeminiProvider)
        mock_ollama = AsyncMock(spec=OllamaProvider)
        
        # Configure mocks
        mock_openai.name = "OpenAI"
        mock_claude.name = "Claude"
        mock_gemini.name = "Gemini"
        mock_ollama.name = "Ollama"
        
        # Use dependency injection
        orchestrator = LLMOrchestrator(
            openai_provider=mock_openai,
            claude_provider=mock_claude,
            gemini_provider=mock_gemini,
            ollama_provider=mock_ollama
        )
        
        # Check provider initialization
        assert "openai" in orchestrator.providers
        assert "claude" in orchestrator.providers
        assert "gemini" in orchestrator.providers
        assert "ollama" in orchestrator.providers
        
        # Verify the correct providers were set
        assert orchestrator.providers["openai"] == mock_openai
        assert orchestrator.providers["claude"] == mock_claude 
        assert orchestrator.providers["gemini"] == mock_gemini
        assert orchestrator.providers["ollama"] == mock_ollama
    
    async def test_gather_responses(self, mock_openai_provider, mock_claude_provider, mock_gemini_provider, mock_ollama_provider):
        """Test gathering responses from multiple providers"""
        # Create different responses for each provider
        openai_response = LLMResponse(
            content="OpenAI test response",
            source="OpenAI",
            metrics={"total_tokens": 50}
        )
        claude_response = LLMResponse(
            content="Claude test response",
            source="Claude",
            metrics={"total_tokens": 50}
        )
        gemini_response = LLMResponse(
            content="Gemini test response",
            source="Gemini",
            metrics={"total_tokens": 50}
        )
        
        # Update mock providers to return different responses
        mock_openai_provider.generate_response.return_value = openai_response
        mock_claude_provider.generate_response.return_value = claude_response
        mock_gemini_provider.generate_response.return_value = gemini_response
        
        # Create orchestrator with all mock providers
        orchestrator = self._create_orchestrator(
            mock_openai_provider=mock_openai_provider,
            mock_claude_provider=mock_claude_provider,
            mock_gemini_provider=mock_gemini_provider,
            mock_ollama_provider=mock_ollama_provider
        )
        
        # Test gather_responses
        responses = await orchestrator.gather_responses(
            prompt="Test prompt",
            system_prompt="You are a helpful assistant"
        )
        
        # Verify the correct providers were called
        assert mock_openai_provider.generate_response.call_count == 1
        assert mock_claude_provider.generate_response.call_count == 1
        assert mock_gemini_provider.generate_response.call_count == 1
        
        # Verify system prompt is passed correctly
        assert mock_openai_provider.generate_response.call_args[1]['system_prompt'] == "You are a helpful assistant"
        assert mock_claude_provider.generate_response.call_args[1]['system_prompt'] == "You are a helpful assistant"
        assert mock_gemini_provider.generate_response.call_args[1]['system_prompt'] == "You are a helpful assistant"
        
        # Verify expert prompt format is used and contains original query
        assert "Test prompt" in mock_openai_provider.generate_response.call_args[1]['prompt']
        assert "Test prompt" in mock_claude_provider.generate_response.call_args[1]['prompt']
        assert "Test prompt" in mock_gemini_provider.generate_response.call_args[1]['prompt']
        
        # Verify responses were collected correctly
        assert len(responses) == 2
        assert "responses" in responses
        assert "errors" in responses
        assert "openai" in responses["responses"]
        assert "claude" in responses["responses"]
        assert "gemini" in responses["responses"]
        assert responses["responses"]["openai"].content == "OpenAI test response"
        assert responses["responses"]["claude"].content == "Claude test response"
        assert responses["responses"]["gemini"].content == "Gemini test response"
    
    async def test_gather_responses_with_provider_list(
        self, mock_openai_provider, mock_claude_provider, mock_gemini_provider, mock_ollama_provider
    ):
        """Test gathering responses with a specific provider list"""
        # Create responses
        openai_response = LLMResponse(content="OpenAI response", source="OpenAI")
        ollama_response = LLMResponse(content="Ollama response", source="Ollama")
        
        # Configure mocks
        mock_openai_provider.generate_response.return_value = openai_response
        mock_ollama_provider.generate_response.return_value = ollama_response
        
        # Create orchestrator with all mock providers
        orchestrator = self._create_orchestrator(
            mock_openai_provider=mock_openai_provider,
            mock_claude_provider=mock_claude_provider,
            mock_gemini_provider=mock_gemini_provider,
            mock_ollama_provider=mock_ollama_provider
        )
        
        # Test gather_responses with specific providers list
        responses = await orchestrator.gather_responses(
            prompt="Test prompt",
            providers=["openai", "ollama"]  # Only request these two
        )
        
        # Verify only the specified providers were called
        mock_openai_provider.generate_response.assert_called_once()
        mock_claude_provider.generate_response.assert_not_called()
        mock_ollama_provider.generate_response.assert_called_once()
        
        # Verify responses
        assert len(responses) == 2
        assert "errors" in responses
        assert "responses" in responses
        assert "openai" in responses["responses"]
        assert "ollama" in responses["responses"]
        assert "claude" not in responses["responses"]
    
    async def test_analyze_consensus(
        self, mock_openai_provider, mock_claude_provider, mock_gemini_provider, mock_ollama_provider
    ):
        """Test consensus analysis with Ollama"""
        # Create responses from external LLMs
        responses = {
            "openai": LLMResponse(
                content="OpenAI believes X is true and Y is false.",
                source="OpenAI"
            ),
            "claude": LLMResponse(
                content="Claude thinks X is true but Y is potentially true as well.",
                source="Claude"
            ),
            "gemini": LLMResponse(
                content="Gemini analysis shows X is true and Y requires more investigation.",
                source="Gemini"
            )
        }
        
        # Create a mock summary response from Ollama
        summary_response = LLMResponse(
            content="""
            # Consensus Analysis
            
            ## Consensus Summary
            - All models agree that X is true
            
            ## Key Differences
            - They differ on Y: ChatGPT says it's false, Claude says it might be true, Gemini wants more investigation
            
            ## Confidence Level
            Medium confidence based on partial agreement
            """,
            source="Ollama"
        )
        
        # Configure Ollama mock to return the summary
        mock_ollama_provider.generate_response.return_value = summary_response
        
        # Create orchestrator with mock providers
        orchestrator = LLMOrchestrator(
            openai_provider=mock_openai_provider,
            claude_provider=mock_claude_provider,
            gemini_provider=mock_gemini_provider,
            ollama_provider=mock_ollama_provider
        )
        
        # Test the analyze_consensus method
        result = await orchestrator.analyze_consensus(
            topic="Is X true and is Y true?",
            responses=responses
        )
        
        # Verify Ollama was called with the correct formatted prompt
        mock_ollama_provider.generate_response.assert_called_once()
        
        # Check that the call includes the original responses and uses the new dynamic format
        prompt_arg = mock_ollama_provider.generate_response.call_args[1]['prompt']
        assert "[ChatGPT]" in prompt_arg
        assert "OpenAI believes X is true" in prompt_arg
        assert "[Claude]" in prompt_arg
        assert "Claude thinks X is true" in prompt_arg
        assert "[Gemini]" in prompt_arg
        assert "Gemini analysis shows X is true" in prompt_arg
        
        # Verify result
        assert isinstance(result, AnalysisResult)
        assert result.summary == summary_response.content
        assert set(result.sources) == {"openai", "claude", "gemini"}
        assert len(result.consensus_items) == 1
        assert "All models agree that X is true" in result.consensus_items
        assert len(result.difference_items) == 1
        assert "They differ on Y" in result.difference_items[0]
        assert result.confidence == "Medium"
        assert result.raw_responses == responses
    
    async def test_process_query(
        self, mock_openai_provider, mock_claude_provider, mock_gemini_provider, mock_ollama_provider
    ):
        """Test the complete query processing pipeline with all providers"""
        # Create responses for external providers
        openai_response = LLMResponse(
            content="OpenAI answer about quantum physics",
            source="OpenAI"
        )
        claude_response = LLMResponse(
            content="Claude answer about quantum physics",
            source="Claude"
        )
        gemini_response = LLMResponse(
            content="Gemini answer about quantum physics",
            source="Gemini"
        )
        
        # Create summary response
        summary_response = LLMResponse(
            content="Summary of quantum physics explanations from all three models",
            source="Ollama"
        )
        
        # Configure mocks
        mock_openai_provider.generate_response.return_value = openai_response
        mock_claude_provider.generate_response.return_value = claude_response
        mock_gemini_provider.generate_response.return_value = gemini_response
        mock_ollama_provider.generate_response.return_value = summary_response
        
        # Create orchestrator
        orchestrator = LLMOrchestrator(
            openai_provider=mock_openai_provider,
            claude_provider=mock_claude_provider,
            gemini_provider=mock_gemini_provider,
            ollama_provider=mock_ollama_provider
        )
        
        # Test the complete pipeline with all three providers
        result = await orchestrator.process_query(
            query="Explain quantum physics",
            system_prompt="You are a physics expert",
            providers=["openai", "claude", "gemini"]
        )
        
        # Verify all external LLMs were called
        assert mock_openai_provider.generate_response.call_count == 1
        assert mock_claude_provider.generate_response.call_count == 1 
        assert mock_gemini_provider.generate_response.call_count == 1
        
        # Verify system prompt is passed correctly
        assert mock_openai_provider.generate_response.call_args[1]['system_prompt'] == "You are a physics expert"
        assert mock_claude_provider.generate_response.call_args[1]['system_prompt'] == "You are a physics expert"
        assert mock_gemini_provider.generate_response.call_args[1]['system_prompt'] == "You are a physics expert"
        
        # Verify the prompt contains our original query
        assert "Explain quantum physics" in mock_openai_provider.generate_response.call_args[1]['prompt']
        assert "Explain quantum physics" in mock_claude_provider.generate_response.call_args[1]['prompt']
        assert "Explain quantum physics" in mock_gemini_provider.generate_response.call_args[1]['prompt']
        
        # Verify Ollama was called for summary
        mock_ollama_provider.generate_response.assert_called_once()
        
        # Verify result
        assert isinstance(result, AnalysisResult)
        assert result.summary == "Summary of quantum physics explanations from all three models"
        assert "openai" in result.raw_responses
        assert "claude" in result.raw_responses
        assert "gemini" in result.raw_responses
    
    @pytest.fixture
    def mock_gemini_provider(self):
        """Mock Gemini provider"""
        mock = AsyncMock(spec=GeminiProvider)
        mock.name = "Gemini"
        return mock
    
    async def test_orchestrator_with_gemini(
        self, mock_openai_provider, mock_claude_provider, mock_gemini_provider, mock_ollama_provider
    ):
        """Test orchestrator with Gemini provider"""
        # Create responses
        gemini_response = LLMResponse(content="Gemini response", source="Gemini")
        mock_gemini_provider.generate_response.return_value = gemini_response
        
        # Create summary response
        summary_response = LLMResponse(content="Summary", source="Ollama")
        mock_ollama_provider.generate_response.return_value = summary_response
        
        # Create orchestrator with all providers
        orchestrator = LLMOrchestrator(
            openai_provider=mock_openai_provider,
            claude_provider=mock_claude_provider,
            gemini_provider=mock_gemini_provider,
            ollama_provider=mock_ollama_provider
        )
        
        # Check provider initialization
        assert "gemini" in orchestrator.providers
        assert orchestrator.providers["gemini"] == mock_gemini_provider
    
    @pytest.mark.parametrize("provider_selection, expected_called", [
        # Single provider cases
        (["openai"], ["openai"]),
        (["claude"], ["claude"]),
        (["gemini"], ["gemini"]),
        # Two provider combinations
        (["openai", "claude"], ["openai", "claude"]),
        (["openai", "gemini"], ["openai", "gemini"]),
        (["claude", "gemini"], ["claude", "gemini"]),
        # All three providers
        (["openai", "claude", "gemini"], ["openai", "claude", "gemini"]),
    ])
    async def test_process_query_with_all_provider_combinations(
        self, 
        provider_selection: List[str],
        expected_called: List[str],
        provider_mocks: Dict[str, AsyncMock],
        default_orchestrator: LLMOrchestrator
    ):
        """Test process_query with all possible provider combinations"""
        # Configure provider responses
        self._configure_provider_mocks(provider_mocks)
        
        query = "Explain quantum computing"
        system_prompt = "You are a helpful assistant"
        
        # Run the process_query method with the current provider selection
        result = await default_orchestrator.process_query(
            query=query,
            system_prompt=system_prompt,
            providers=provider_selection
        )
        
        # Verify the correct providers were called
        self._verify_provider_calls(
            provider_mocks, 
            expected_called,
            prompt=query,
            system_prompt=system_prompt
        )
        
        # Verify Ollama was always called for analysis
        provider_mocks["ollama"].generate_response.assert_called_once()
        
        # Verify result contains the correct sources
        assert set(result.sources) == set(expected_called)
        
        # Verify raw_responses contains only the expected providers
        assert set(result.raw_responses.keys()) == set(expected_called)
        
    @patch("app.services.llm_providers.orchestrator.settings")
    async def test_default_enabled_providers(
        self, mock_settings, mock_openai_provider, mock_claude_provider, 
        mock_gemini_provider, mock_ollama_provider
    ):
        """Test that orchestrator uses the default enabled providers from settings"""
        # Mock the settings.get_enabled_providers() method
        mock_settings.get_enabled_providers.return_value = ["openai", "gemini"]
        
        # Create responses
        openai_response = LLMResponse(content="OpenAI response", source="OpenAI")
        gemini_response = LLMResponse(content="Gemini response", source="Gemini")
        summary_response = LLMResponse(content="Summary", source="Ollama")
        
        # Configure mocks
        mock_openai_provider.generate_response.return_value = openai_response
        mock_gemini_provider.generate_response.return_value = gemini_response
        mock_ollama_provider.generate_response.return_value = summary_response
        
        # Create orchestrator
        orchestrator = LLMOrchestrator(
            openai_provider=mock_openai_provider,
            claude_provider=mock_claude_provider,
            gemini_provider=mock_gemini_provider,
            ollama_provider=mock_ollama_provider
        )
        
        # Check the default_enabled_providers in the orchestrator
        assert orchestrator.default_enabled_providers == ["openai", "gemini"]
        
        # Test the process_query method without specifying providers
        result = await orchestrator.process_query(
            query="Test query",
            system_prompt="You are helpful"
        )
        
        # Verify that only the default enabled providers were called
        mock_openai_provider.generate_response.assert_called_once()
        mock_claude_provider.generate_response.assert_not_called()
        mock_gemini_provider.generate_response.assert_called_once()
        
        # Verify result has the correct sources
        assert set(result.sources) == {"openai", "gemini"}
        
    async def test_provider_error_handling(
        self,
        provider_mocks: Dict[str, AsyncMock],
        default_orchestrator: LLMOrchestrator
    ):
        """Test that orchestrator handles errors from providers gracefully"""
        # Set up responses for providers
        self._configure_provider_mocks(provider_mocks)
        
        # Make Claude provider raise an exception
        provider_mocks["claude"].generate_response.side_effect = Exception("Claude API error")
        
        # Test process_query with all providers
        result = await default_orchestrator.process_query(
            query="Test error handling",
            system_prompt="You are a helpful assistant",
            providers=["openai", "claude", "gemini"]
        )
        
        # Verify all providers were attempted
        provider_mocks["openai"].generate_response.assert_called_once()
        provider_mocks["claude"].generate_response.assert_called_once()
        provider_mocks["gemini"].generate_response.assert_called_once()
        
        # Verify Ollama was called for summary
        provider_mocks["ollama"].generate_response.assert_called_once()
        
        # Verify result includes successful providers only
        assert set(result.sources) == {"openai", "gemini"}
        assert "claude" not in result.raw_responses
        
        # Verify the result contains successful responses
        assert result.raw_responses["openai"].source == "Openai"
        assert result.raw_responses["gemini"].source == "Gemini"
        
    async def test_empty_provider_list_handling(
        self,
        provider_mocks: Dict[str, AsyncMock],
        default_orchestrator: LLMOrchestrator
    ):
        """Test that orchestrator handles empty provider lists appropriately"""
        # Configure provider responses
        self._configure_provider_mocks(provider_mocks)
        
        # Mock the default_enabled_providers to include all three providers
        default_orchestrator.default_enabled_providers = ["openai", "claude", "gemini"]
        
        # Test with empty provider list - should fall back to defaults
        result = await default_orchestrator.process_query(
            query="Test empty list handling",
            system_prompt="You are a helpful assistant",
            providers=[]  # Empty list
        )
        
        # It should use the default_enabled_providers
        assert provider_mocks["openai"].generate_response.call_count > 0
        assert provider_mocks["claude"].generate_response.call_count > 0
        assert provider_mocks["gemini"].generate_response.call_count > 0
        
        # Verify Ollama was called for analysis
        assert provider_mocks["ollama"].generate_response.call_count > 0
        
        # Verify the result contains responses from all providers
        assert len(result.sources) >= 3
    
    async def test_invalid_provider_name_handling(
        self,
        provider_mocks: Dict[str, AsyncMock],
        default_orchestrator: LLMOrchestrator
    ):
        """Test that orchestrator handles invalid provider names gracefully"""
        # Configure mocks
        self._configure_provider_mocks(provider_mocks)
        
        # Configure mocks for the next test
        for mock in provider_mocks.values():
            mock.reset_mock()
        self._configure_provider_mocks(provider_mocks)
        
        try:
            # Test with an invalid provider name should raise ValueError
            result = await default_orchestrator.process_query(
                query="Test invalid provider",
                system_prompt="You are a helpful assistant",
                providers=["openai", "invalid_provider", "gemini"]  # Include an invalid name
            )
            
            # If this doesn't raise an error, the result should still include the valid providers
            assert "openai" in result.sources
            assert "gemini" in result.sources
            assert "invalid_provider" not in result.sources
            
            # Verify only valid providers were called
            assert provider_mocks["openai"].generate_response.call_count > 0
            assert provider_mocks["claude"].generate_response.call_count == 0
            assert provider_mocks["gemini"].generate_response.call_count > 0
            
            # Verify Ollama was still called for summary
            assert provider_mocks["ollama"].generate_response.call_count > 0
        except ValueError as e:
            # If it raises ValueError, that's also acceptable
            assert "Unknown providers: invalid_provider" in str(e)
        
        # Verify result contains only valid providers
        assert set(result.sources) == {"openai", "gemini"}
        assert "invalid_provider" not in result.raw_responses
    
    async def test_ollama_failure_handling(
        self,
        provider_mocks: Dict[str, AsyncMock],
        default_orchestrator: LLMOrchestrator
    ):
        """Test orchestrator handles Ollama provider failures"""
        # Configure mocks for external LLM providers
        self._configure_provider_mocks(provider_mocks)
        
        # Make Ollama provider raise an exception
        provider_mocks["ollama"].generate_response.side_effect = Exception("Ollama API error")
        
        # Test process_query
        result = await default_orchestrator.process_query(
            query="Test Ollama failure",
            system_prompt="You are a helpful assistant",
            providers=["openai", "claude"]
        )
        
        # Verify external providers were called
        provider_mocks["openai"].generate_response.assert_called_once()
        provider_mocks["claude"].generate_response.assert_called_once()
        
        # Verify Ollama was attempted
        provider_mocks["ollama"].generate_response.assert_called_once()
        
        # Verify result contains raw responses but no summary or analysis
        assert "openai" in result.raw_responses
        assert "claude" in result.raw_responses
        assert set(result.sources) == {"openai", "claude"}
        assert result.summary is not None
        assert "Error generating summary with Ollama" in result.summary
