import time
from typing import Dict, Any, Optional

from openai import AsyncOpenAI, BadRequestError, APITimeoutError, RateLimitError
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.llm_providers.base import BaseLLMProvider, LLMResponse


class OpenAIParams(BaseModel):
    """Parameters for OpenAI API calls"""
    model: str = Field(default=settings.OPENAI_MODEL)
    temperature: float = Field(default=0.3, ge=0, le=2.0)
    max_tokens: int = Field(default=1500, ge=1)
    top_p: float = Field(default=1.0, ge=0, le=1.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API provider for GPT models
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = settings.OPENAI_MODEL,
        rate_limit: int = 5
    ):
        super().__init__(name="OpenAI", rate_limit=rate_limit)
        
        # Use API key from settings if not provided
        api_key = api_key or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        # Initialize the client
        self.client = AsyncOpenAI(api_key=api_key)

        if not model:
            raise ValueError("Please sepecify OpenAI model ID")
        self.model = model
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from OpenAI's GPT model
        
        Args:
            prompt: The user message to send to the model
            system_prompt: Optional system message for setting context
            **kwargs: Additional parameters for the API call
            
        Returns:
            LLMResponse: A standardized response object
        """
        # Wait for rate limiter
        await self._handle_rate_limit()
        
        # Prepare parameters with defaults from OpenAIParams
        params = OpenAIParams(model=self.model).model_dump()
        params.update({k: v for k, v in kwargs.items() if k in OpenAIParams.__annotations__})
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Track metrics
        start_time = time.time()
        
        # Make API call with retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    messages=messages,
                    **params
                )
                
                # Validate response
                if not self._validate_response(response):
                    raise ValueError("Invalid response received from OpenAI API")
                
                # Calculate metrics
                elapsed_time = time.time() - start_time
                total_tokens = response.usage.total_tokens
                
                # Extract content
                content = response.choices[0].message.content
                
                return LLMResponse(
                    content=content,
                    source=self.name,
                    metrics={
                        "model": params["model"],
                        "elapsed_time": round(elapsed_time, 2),
                        "total_tokens": total_tokens,
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens
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
        Validate the response from OpenAI
        
        Args:
            response: The raw response from the OpenAI API
            
        Returns:
            bool: True if the response is valid, False otherwise
        """
        return (
            hasattr(response, "choices") and
            len(response.choices) > 0 and
            hasattr(response.choices[0], "message") and
            hasattr(response.choices[0].message, "content") and
            response.choices[0].message.content is not None
        )
