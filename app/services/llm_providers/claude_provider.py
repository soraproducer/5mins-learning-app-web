import time
from typing import Dict, Any, Optional

from anthropic import AsyncAnthropic, BadRequestError, APITimeoutError, RateLimitError
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.llm_providers.base import BaseLLMProvider, LLMResponse


class ClaudeParams(BaseModel):
    """Parameters for Claude API calls"""
    model: str = Field(default=settings.ANTHROPIC_MODEL)
    temperature: float = Field(default=0.3, ge=0, le=1.0)
    max_tokens: int = Field(default=1500, ge=1)
    top_p: float = Field(default=1.0, ge=0, le=1.0)
    top_k: int = Field(default=None, ge=1, le=500)


class ClaudeProvider(BaseLLMProvider):
    """
    Anthropic API provider for Claude models
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = settings.ANTHROPIC_MODEL,
        rate_limit: int = 5
    ):
        super().__init__(name="Claude", rate_limit=rate_limit)
        
        # Use API key from settings if not provided
        api_key = api_key or settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("Anthropic API key is required")
        
        # Initialize the client
        self.client = AsyncAnthropic(api_key=api_key)

        if not model:
            raise ValueError("Please sepecify Anthropic model ID")
        self.model = model
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from Anthropic's Claude model
        
        Args:
            prompt: The user message to send to the model
            system_prompt: Optional system message for setting context
            **kwargs: Additional parameters for the API call
            
        Returns:
            LLMResponse: A standardized response object
        """
        # Wait for rate limiter
        await self._handle_rate_limit()
        
        # Prepare parameters with defaults from ClaudeParams
        params = ClaudeParams(model=self.model).model_dump()
        # Filter out None values and only include valid parameters
        params = {k: v for k, v in params.items() if v is not None}
        params.update({k: v for k, v in kwargs.items() if k in ClaudeParams.__annotations__})
        
        # Track metrics
        start_time = time.time()
        
        # Make API call with retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                # Claude API uses different parameter names
                api_params = {
                    "model": params.get("model", self.model),
                    "max_tokens": params.get("max_tokens", 1500),
                    "temperature": params.get("temperature", 0.3),
                }
                
                if "top_p" in params:
                    api_params["top_p"] = params["top_p"]
                if "top_k" in params and params["top_k"] is not None:
                    api_params["top_k"] = params["top_k"]
                
                # Add system prompt if provided
                if system_prompt:
                    api_params["system"] = system_prompt
                
                response = await self.client.messages.create(
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    **api_params
                )
                
                # Validate response
                if not self._validate_response(response):
                    raise ValueError("Invalid response received from Claude API")
                
                # Calculate metrics
                elapsed_time = time.time() - start_time
                
                # Extract content
                content = response.content[0].text
                
                return LLMResponse(
                    content=content,
                    source=self.name,
                    metrics={
                        "model": params.get("model", self.model),
                        "elapsed_time": round(elapsed_time, 2),
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                    }
                )
                
            except (BadRequestError, APITimeoutError, RateLimitError, ValueError) as e:
                if not await self._handle_error(e, attempt):
                    # If retry limit reached, re-raise the exception
                    raise
        
        # This should not be reached due to exception handling
        raise RuntimeError("Failed to generate response after multiple attempts")
    
    def _validate_response(self, response: Any) -> bool:
        """
        Validate the response from Claude
        
        Args:
            response: The raw response from the Claude API
            
        Returns:
            bool: True if the response is valid, False otherwise
        """
        return (
            hasattr(response, "content") and
            len(response.content) > 0 and
            hasattr(response.content[0], "text") and
            response.content[0].text is not None
        )
