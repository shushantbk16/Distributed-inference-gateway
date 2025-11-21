"""Base provider interface for LLM providers."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str, model_name: str):
        """
        Initialize the provider.
        
        Args:
            api_key: API key for the provider
            model_name: Model identifier
        """
        self.api_key = api_key
        self.model_name = model_name
    
    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 2048,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict containing 'text' and any metadata
            
        Raises:
            ProviderError: If the provider request fails
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is available.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass
