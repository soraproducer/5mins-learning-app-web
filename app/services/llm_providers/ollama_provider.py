import asyncio
import httpx
import json
import time
from typing import Dict, Any, Optional, AsyncGenerator, Callable

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.llm_providers.base import BaseLLMProvider, LLMResponse


class OllamaParams(BaseModel):
    """Parameters for Ollama API calls"""
    model: str = Field(default="gemma3:4b")
    temperature: float = Field(default=0.3, ge=0, le=2.0)
    num_predict: int = Field(default=2048, ge=1)  # max_tokens equivalent
    top_p: float = Field(default=0.9, ge=0, le=1.0)
    top_k: int = Field(default=40, ge=0)
    repeat_penalty: float = Field(default=1.1, ge=0)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama API provider for local LLM models
    
    This provider connects to a locally running Ollama instance
    without strict rate limiting.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False
    ):
        # No strict rate limiting for local models
        super().__init__(name="Ollama", rate_limit=60)  # 60 req/min is not a practical constraint
        
        # Use config from settings if not provided
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.stream = stream
        
        if not self.base_url:
            raise ValueError("Ollama base URL is required")
        if not self.model:
            raise ValueError("Ollama model name is required")
        
        # Remove trailing slash if present
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
        
        # No client initialization needed, we'll use httpx directly
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from Ollama local model
        
        Args:
            prompt: The user message to send to the model
            system_prompt: Optional system message for setting context
            stream_callback: Optional callback for streaming responses
            **kwargs: Additional parameters for the API call
            
        Returns:
            LLMResponse: A standardized response object
        """
        # No strict rate limiting for local models
        await self._handle_rate_limit()
        
        # Prepare parameters with defaults from OllamaParams
        params = OllamaParams(model=self.model).model_dump()
        params.update({k: v for k, v in kwargs.items() if k in OllamaParams.__annotations__})
        
        # Track metrics
        start_time = time.time()
        total_tokens = 0
        
        # Prepare the request payload
        payload = {
            "model": params.get("model", self.model),
            "prompt": prompt,
            "stream": bool(stream_callback) or self.stream,
            "options": {
                "temperature": params.get("temperature", 0.3),
                "num_predict": params.get("num_predict", 2048),
                "top_p": params.get("top_p", 0.9),
                "top_k": params.get("top_k", 40),
                "repeat_penalty": params.get("repeat_penalty", 1.1),
            }
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
        
        # Make API call with retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                if payload.get("stream", False):
                    # Handle streaming response
                    streamed_content = []
                    
                    async for chunk in self._stream_response(payload):
                        if stream_callback:
                            stream_callback(chunk)
                        streamed_content.append(chunk)
                    
                    content = "".join(streamed_content)
                    elapsed_time = time.time() - start_time
                    
                    # We don't have precise token counts for streaming
                    return LLMResponse(
                        content=content,
                        source=self.name,
                        metrics={
                            "model": params.get("model", self.model),
                            "elapsed_time": round(elapsed_time, 2),
                            "streaming": True
                        }
                    )
                else:
                    # Handle non-streaming response
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            f"{self.base_url}/api/generate",
                            json=payload
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        # Validate response
                        if not self._validate_response(result):
                            raise ValueError("Invalid response received from Ollama API")
                        
                        # Calculate metrics
                        elapsed_time = time.time() - start_time
                        
                        # Extract content
                        content = result.get("response", "")
                        
                        return LLMResponse(
                            content=content,
                            source=self.name,
                            metrics={
                                "model": params.get("model", self.model),
                                "elapsed_time": round(elapsed_time, 2),
                                "eval_count": result.get("eval_count"),
                                "eval_duration": result.get("eval_duration"),
                                "prompt_eval_count": result.get("prompt_eval_count"),
                                "prompt_eval_duration": result.get("prompt_eval_duration")
                            }
                        )
                
            except (httpx.HTTPError, ValueError, json.JSONDecodeError) as e:
                if not await self._handle_error(e, attempt):
                    # If retry limit reached, re-raise the exception
                    raise
        
        # This should not be reached due to exception handling
        raise RuntimeError("Failed to generate response after multiple attempts")
    
    async def _stream_response(self, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Stream response chunks from Ollama
        
        Args:
            payload: The request payload to send to Ollama
            
        Yields:
            Chunks of the response content
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    try:
                        chunk_data = json.loads(line)
                        if "response" in chunk_data:
                            yield chunk_data["response"]
                        
                        # Check for done flag
                        if chunk_data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        # Skip invalid lines
                        continue
    
    def _validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate the response from Ollama
        
        Args:
            response: The JSON response from the Ollama API
            
        Returns:
            bool: True if the response is valid, False otherwise
        """
        return (
            isinstance(response, dict) and
            "response" in response
        )
