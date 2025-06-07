import time
from typing import Dict, Any, Optional, List

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.llm_providers.base import BaseLLMProvider, LLMResponse


class GeminiParams(BaseModel):
    """Parameters for Gemini API calls"""
    model: str = Field(default=settings.GEMINI_MODEL)
    temperature: float = Field(default=0.3, ge=0, le=1.0)
    max_output_tokens: int = Field(default=1500, ge=1)
    top_p: float = Field(default=1.0, ge=0, le=1.0)
    top_k: int = Field(default=None, ge=1, le=128)


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini API provider
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = settings.GEMINI_MODEL,
        rate_limit: int = 5
    ):
        super().__init__(name="Gemini", rate_limit=rate_limit)
        
        # Use API key from settings if not provided
        api_key = api_key or settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        # Initialize the client
        genai.configure(api_key=api_key)

        if not model:
            raise ValueError("Please sepecify Gemini model ID")
        self.model = model
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from Google's Gemini model
        
        Args:
            prompt: The user message to send to the model
            system_prompt: Optional system message for setting context
            **kwargs: Additional parameters for the API call
            
        Returns:
            LLMResponse: A standardized response object
        """
        # Wait for rate limiter
        await self._handle_rate_limit()
        
        # Prepare parameters with defaults from GeminiParams
        params = GeminiParams(model=self.model).model_dump()
        params.update({k: v for k, v in kwargs.items() if k in GeminiParams.__annotations__})
        
        # Filter out None values
        params = {k: v for k, v in params.items() if v is not None}
        
        # Track metrics
        start_time = time.time()
        
        # Configure safety settings (medium filtering by default)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        # Make API call with retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                # Get Gemini model
                model = genai.GenerativeModel(
                    model_name=params.get("model", self.model),
                    generation_config={
                        "temperature": params.get("temperature", 0.3),
                        "max_output_tokens": params.get("max_output_tokens", 1500),
                        "top_p": params.get("top_p", 1.0),
                        "top_k": params.get("top_k") if "top_k" in params else None,
                    },
                    safety_settings=safety_settings,
                )
                
                # Generate chat session
                chat = model.start_chat(
                    history=[]
                )
                
                # Add system prompt if provided
                if system_prompt:
                    # Gemini doesn't have a dedicated system message, so we'll use a user message
                    # with a prefix to simulate system instruction
                    first_message = f"[System Instruction] {system_prompt}\n\nUser: {prompt}"
                else:
                    first_message = prompt
                
                # Send the message synchronously (using the async executor)
                response = await self._run_in_executor(
                    lambda: chat.send_message(first_message)
                )
                
                # Validate response
                if not self._validate_response(response):
                    raise ValueError("Invalid response received from Gemini API")
                
                # Calculate metrics
                elapsed_time = time.time() - start_time
                
                # Extract content
                content = response.text
                
                # Calculate tokens (if available)
                metrics = {
                    "model": params.get("model", self.model),
                    "elapsed_time": round(elapsed_time, 2)
                }
                
                # Get tokens usage if available
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    if hasattr(response.usage_metadata, "prompt_token_count"):
                        metrics["prompt_tokens"] = response.usage_metadata.prompt_token_count
                    if hasattr(response.usage_metadata, "candidates_token_count"):
                        metrics["completion_tokens"] = response.usage_metadata.candidates_token_count
                    if "prompt_tokens" in metrics and "completion_tokens" in metrics:
                        metrics["total_tokens"] = metrics["prompt_tokens"] + metrics["completion_tokens"]
                
                return LLMResponse(
                    content=content,
                    source=self.name,
                    metrics=metrics
                )
                
            except Exception as e:
                if not await self._handle_error(e, attempt):
                    # If retry limit reached, re-raise the exception
                    raise
        
        # This should not be reached due to exception handling
        raise RuntimeError("Failed to generate response after multiple attempts")
    
    def _validate_response(self, response: Any) -> bool:
        """
        Validate the response from Gemini
        
        Args:
            response: The raw response from the Gemini API
            
        Returns:
            bool: True if the response is valid, False otherwise
        """
        return (
            hasattr(response, "text") and
            response.text is not None and
            len(response.text) > 0
        )
    
    async def _run_in_executor(self, func):
        """Run a synchronous function in an async executor"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)
