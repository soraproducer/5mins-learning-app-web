import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.services.llm_providers.base import BaseLLMProvider, LLMResponse
from app.services.llm_providers.openai_provider import OpenAIProvider
from app.services.llm_providers.claude_provider import ClaudeProvider
from app.services.llm_providers.gemini_provider import GeminiProvider
from app.services.llm_providers.ollama_provider import OllamaProvider
from app.core.config import settings
from app.core.prompts import SUMMARY_SYSTEM_PROMPT, EXPERT_SYSTEM_PROMPT


class AnalysisResult:
    """Result of consensus analysis between multiple LLM responses"""
    
    def __init__(
        self,
        summary: str,
        sources: List[str],
        consensus_items: List[str],
        difference_items: List[str],
        confidence: str,
        raw_responses: Dict[str, LLMResponse],
        provider_errors: Dict[str, str] = None
    ):
        self.summary = summary
        self.sources = sources
        self.consensus_items = consensus_items
        self.difference_items = difference_items
        self.confidence = confidence
        self.raw_responses = raw_responses
        self.provider_errors = provider_errors or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis result to dictionary"""
        return {
            "summary": self.summary,
            "sources": self.sources,
            "consensus_items": self.consensus_items,
            "difference_items": self.difference_items,
            "confidence": self.confidence,
            "raw_responses": {
                source: response.to_dict() 
                for source, response in self.raw_responses.items()
            },
            "provider_errors": self.provider_errors,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        """Create analysis result from dictionary"""
        # Convert raw_responses back to LLMResponse objects
        raw_responses = {
            source: LLMResponse.from_dict(response_data)
            for source, response_data in data.get("raw_responses", {}).items()
        }
        
        return cls(
            summary=data.get("summary", ""),
            sources=data.get("sources", []),
            consensus_items=data.get("consensus_items", []),
            difference_items=data.get("difference_items", []),
            confidence=data.get("confidence", "Low"),
            raw_responses=raw_responses,
            provider_errors=data.get("provider_errors", {})
        )


class LLMOrchestrator:
    """
    Orchestrates multiple LLM providers and analyzes their responses
    
    This class manages the flow of:
    1. Sending prompts to external LLMs (OpenAI, Claude)
    2. Processing their responses
    3. Using local Ollama to summarize and highlight consensus/differences
    """
    
    def __init__(
        self,
        openai_provider: Optional[OpenAIProvider] = None,
        claude_provider: Optional[ClaudeProvider] = None,
        gemini_provider: Optional[GeminiProvider] = None,
        ollama_provider: Optional[OllamaProvider] = None,
        summary_divider: str = "------"
    ):
        # Initialize providers with defaults if not provided
        self.providers = {}
        self.providers["openai"] = openai_provider or OpenAIProvider()
        self.providers["claude"] = claude_provider or ClaudeProvider()
        self.providers["gemini"] = gemini_provider or GeminiProvider()
        self.providers["ollama"] = ollama_provider or OllamaProvider()
        
        # Configuration
        self.summary_divider = summary_divider
        
        # Default enabled providers from settings
        self.default_enabled_providers = settings.get_enabled_providers()
    
    async def gather_responses(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        providers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Gather responses from multiple providers
        
        Args:
            prompt: The user prompt to send to LLMs
            system_prompt: Optional system prompt for context
            providers: List of provider names to query (default: openai, claude)
            
        Returns:
            A dictionary containing successful responses and provider errors
        """
        # Default to external providers
        if providers is None:
            providers = ["openai", "claude", "gemini"]
        
        # Filter out invalid providers instead of raising an error
        available_providers = set(self.providers.keys())
        requested_providers = set(providers)
        
        if not requested_providers.issubset(available_providers):
            unknown = requested_providers - available_providers
            # Just filter out invalid providers instead of raising an error
            valid_providers = [p for p in providers if p in available_providers]
            print(f"Warning: Unknown providers: {', '.join(unknown)}. Using only valid providers.")
            providers = valid_providers
        
        # Gather responses concurrently
        tasks = []

        expert_prompt = EXPERT_SYSTEM_PROMPT.format(
            topic=prompt
        )

        for provider_name in providers:
            provider = self.providers[provider_name]
            tasks.append(
                self._get_provider_response(provider, expert_prompt, system_prompt)
            )
        
        # Wait for all responses
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process responses, filtering out exceptions
        result = {}
        provider_errors = {}
        
        for provider_name, response in zip(providers, responses):
            if isinstance(response, Exception):
                error_msg = str(response)
                print(f"Error from {provider_name}: {error_msg}")
                provider_errors[provider_name] = error_msg
                continue
            
            result[provider_name] = response
        
        return {
            "responses": result,
            "errors": provider_errors
        }
    
    async def _get_provider_response(
        self,
        provider: BaseLLMProvider,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Get response from a single provider with error handling"""
        try:
            return await provider.generate_response(
                prompt=prompt,
                system_prompt=system_prompt
            )
        except Exception as e:
            # Re-raise the exception to be caught by gather
            raise
    
    async def analyze_consensus(
        self,
        topic: str,
        responses: Dict[str, LLMResponse],
        local_model_id: Optional[str] = None
    ) -> AnalysisResult:
        """
        Generate consensus analysis using Ollama
        
        Args:
            topic: The original topic/question
            responses: Dictionary of provider responses
            local_model_id: Optional local model ID to use for summarization
            
        Returns:
            AnalysisResult with consensus and differences
        """
        # Use the specified local model or default Ollama provider
        if local_model_id:
            # Create a new OllamaProvider instance with the specified model
            ollama = OllamaProvider(model=local_model_id)
        else:
            # Use the default Ollama provider
            ollama = self.providers["ollama"]
        
        # Build response blocks for each provider
        response_blocks = []
        for provider_name, response in responses.items():
            # Map provider names to more readable names
            display_names = {
                "openai": "ChatGPT",
                "claude": "Claude",
                "gemini": "Gemini"
            }
            display_name = display_names.get(provider_name, provider_name.capitalize())
            
            # Format each response block
            response_blocks.append(f"{self.summary_divider}\n[{display_name}]: {response.content}")
        
        # Add final divider
        response_blocks.append(self.summary_divider)
        
        # Join all blocks
        all_blocks = "\n".join(response_blocks)
        
        # Format the summary prompt
        summary_prompt = SUMMARY_SYSTEM_PROMPT.format(
            topic=topic,
            response_blocks=all_blocks
        )
        
        # Get summary from Ollama using the specified model
        summary_response = await ollama.generate_response(
            prompt=summary_prompt,
            # Use system prompt to guide the local model
            system_prompt="You are an impartial analyzer that compares responses from multiple AI models."
        )
        
        # Parse the summary to extract structured data
        # This is a simple implementation - in practice, you might want to use a more robust parsing
        summary = summary_response.content
        
        # Extract consensus items (simplified parsing)
        consensus_items = []
        difference_items = []
        confidence = "Medium"  # Default
        
        # Very basic parsing - in production you'd want more robust extraction
        for line in summary.split("\n"):
            line = line.strip()
            if line.startswith("- ") and "agree" in line.lower():
                consensus_items.append(line[2:])
            elif line.startswith("- ") and any(x in line.lower() for x in ["differ", "contrast", "disagree"]):
                difference_items.append(line[2:])
            elif "confidence" in line.lower():
                if "high" in line.lower():
                    confidence = "High"
                elif "medium" in line.lower():
                    confidence = "Medium"
                elif "low" in line.lower():
                    confidence = "Low"
        
        return AnalysisResult(
            summary=summary,
            sources=list(responses.keys()),
            consensus_items=consensus_items,
            difference_items=difference_items,
            confidence=confidence,
            raw_responses=responses
        )
    
    async def process_query(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        providers: Optional[List[str]] = None,
        history_text: Optional[str] = None,
        local_model_id: Optional[str] = None
    ) -> AnalysisResult:
        """
        Process a user query through the complete pipeline
        
        Args:
            query: The user's question or topic
            system_prompt: Optional system prompt for external LLMs
            providers: Optional list of provider names to use (default: use settings.DEFAULT_ENABLED_PROVIDERS)
            history_text: Optional conversation history to provide context for follow-up questions
            local_model_id: Optional local model ID to use for summarization
            
        Returns:
            AnalysisResult with the consensus summary and raw responses
        """
        # Use default enabled providers if none specified or empty
        if providers is None or len(providers) == 0:
            providers = self.default_enabled_providers
        
        # 1. Gather responses from external LLMs
        try:
            # Include conversation history in system prompt if available
            effective_system_prompt = system_prompt
            if history_text:
                if effective_system_prompt:
                    effective_system_prompt = f"{effective_system_prompt}\n\nPrevious conversation context: \n{history_text}"
                else:
                    effective_system_prompt = f"Previous conversation context: \n{history_text}"
            
            result = await self.gather_responses(
                prompt=query,
                system_prompt=effective_system_prompt,
                providers=providers
            )
            responses = result["responses"]
            provider_errors = result["errors"] 
        except ValueError as e:
            # Handle invalid provider errors
            return AnalysisResult(
                summary=f"Error: {str(e)}",
                sources=[],
                consensus_items=[],
                difference_items=[f"Error: {str(e)}"],
                confidence="Low",
                raw_responses={}
            )
        
        # Handle empty responses
        if not responses:
            return AnalysisResult(
                summary="No responses were received from any LLM providers.",
                sources=[],
                consensus_items=[],
                difference_items=["No analysis possible - no provider responses received."],
                confidence="Low",
                raw_responses={},
                provider_errors=provider_errors
            )
        
        # 2. Analyze consensus using Ollama with the specified local model
        try:
            result = await self.analyze_consensus(
                topic=query,
                responses=responses,
                local_model_id=local_model_id
            )
            # Add provider errors to the result
            result.provider_errors = provider_errors
            return result
        except Exception as e:
            # Handle Ollama failures gracefully
            error_message = f"Error generating summary with Ollama: {str(e)}"
            return AnalysisResult(
                summary=error_message,
                sources=list(responses.keys()),
                consensus_items=[],
                difference_items=[f"Analysis failed: {str(e)}"],
                confidence="Low",
                raw_responses=responses,
                provider_errors=provider_errors
            )
