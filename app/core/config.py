import os
from typing import Dict, Any, List
from pydantic import Field
from pydantic_settings import BaseSettings

class ThirdPartyLLMConfig(BaseSettings):
    """Configuration for a third-party LLM provider"""
    model_id: str
    api_key: str
    enabled: bool = True

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    # Database
    DATABASE_URL: str = Field(default="")
    
    # LLM API Keys and Models (consolidated)
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-5.4-mini")
    
    ANTHROPIC_API_KEY: str = Field(default="")
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-haiku-20241022")
    
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash-lite")
    
    # Default enabled providers (allows users to select which providers to use)
    DEFAULT_ENABLED_PROVIDERS: List[str] = Field(default=["openai", "claude", "gemini"])
    
    # Ollama Config (local LLM)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="gemma3:4b")

    model_config = {
        "env_file": ".env.local",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }
    
    @property
    def third_party_llm_configs(self) -> Dict[str, ThirdPartyLLMConfig]:
        """
        Get configuration for all third-party LLM providers
        
        Returns:
            Dictionary mapping provider names to their configurations
        """
        return {
            "openai": ThirdPartyLLMConfig(
                model_id=self.OPENAI_MODEL,
                api_key=self.OPENAI_API_KEY,
                enabled="openai" in self.DEFAULT_ENABLED_PROVIDERS
            ),
            "claude": ThirdPartyLLMConfig(
                model_id=self.ANTHROPIC_MODEL,
                api_key=self.ANTHROPIC_API_KEY,
                enabled="claude" in self.DEFAULT_ENABLED_PROVIDERS
            ),
            "gemini": ThirdPartyLLMConfig(
                model_id=self.GEMINI_MODEL,
                api_key=self.GEMINI_API_KEY,
                enabled="gemini" in self.DEFAULT_ENABLED_PROVIDERS
            )
        }
    
    def get_enabled_providers(self) -> List[str]:
        """
        Get list of enabled third-party LLM providers
        
        Returns:
            List of enabled provider names
        """
        return [
            provider
            for provider, config in self.third_party_llm_configs.items()
            if config.enabled and config.api_key
        ]

# Create settings instance
settings = Settings()
