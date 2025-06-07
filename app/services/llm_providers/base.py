import time
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List

class RateLimiter:
    """
    Implements a leaky bucket rate limiter for API calls
    """
    
    def __init__(self, requests_per_minute: int = 5):
        self.requests_per_minute = requests_per_minute
        self.interval = 120 / requests_per_minute  # seconds between requests
        self.last_request_time = 0
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until a request can be made according to the rate limit"""
        async with self.lock:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            
            if time_since_last_request < self.interval:
                delay = self.interval - time_since_last_request
                await asyncio.sleep(delay)
            
            self.last_request_time = time.time()
            return True


class LLMResponse:
    """
    Standardized response format for all LLM providers
    """
    
    def __init__(
        self,
        content: str,
        source: str,
        timestamp: Optional[datetime] = None,
        metrics: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.source = source
        self.timestamp = timestamp or datetime.utcnow()
        self.metrics = metrics or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for storage"""
        return {
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMResponse":
        """Create response object from dictionary"""
        return cls(
            content=data["content"],
            source=data["source"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metrics=data["metrics"]
        )


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers
    
    All LLM provider implementations should inherit from this class
    and implement the required methods.
    """
    
    def __init__(
        self,
        name: str,
        rate_limit: int = 5,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.name = name
        self.rate_limiter = RateLimiter(rate_limit)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM based on the prompt
        
        Args:
            prompt: The input prompt to send to the model
            kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse: A standardized response object
        """
        pass
    
    async def _handle_rate_limit(self):
        """Wait until a request can be made based on rate limiting"""
        await self.rate_limiter.acquire()
    
    @abstractmethod
    def _validate_response(self, response: Any) -> bool:
        """
        Validate the response from the provider
        
        Args:
            response: The raw response from the provider API
            
        Returns:
            bool: True if the response is valid, False otherwise
        """
        pass
    
    async def _handle_error(self, error: Exception, attempt: int) -> bool:
        """
        Handle error during API call with retry logic
        
        Args:
            error: The exception that was raised
            attempt: The current attempt number
            
        Returns:
            bool: True if retry should be attempted, False otherwise
        """
        if attempt < self.max_retries:
            wait_time = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
            print(f"{self.name} API error: {str(error)}. Retrying in {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            return True
        return False
