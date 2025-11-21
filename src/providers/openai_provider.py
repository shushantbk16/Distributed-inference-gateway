"""OpenAI API provider."""
import httpx
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from src.providers.base import BaseLLMProvider
from src.utils.errors import ProviderError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""
    
    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
        """Initialize OpenAI provider."""
        super().__init__(api_key, model_name)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "openai"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 2048,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion using OpenAI API.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Dict with 'text' and metadata
            
        Raises:
            ProviderError: If API request fails
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                logger.info(f"Sending request to OpenAI API with model {self.model_name}")
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_msg = f"OpenAI API returned status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise ProviderError("openai", error_msg)
                
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                
                return {
                    "text": text,
                    "model": self.model_name,
                    "usage": data.get("usage", {}),
                    "finish_reason": data["choices"][0].get("finish_reason")
                }
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in OpenAI provider: {e}")
            raise ProviderError("openai", str(e), e)
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {e}")
            raise ProviderError("openai", str(e), e)
    
    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers=self.headers
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False
