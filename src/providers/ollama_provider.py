"""Ollama local LLM provider - FREE and unlimited!"""
import httpx
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from src.providers.base import BaseLLMProvider
from src.utils.errors import ProviderError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider - runs models locally for free!"""
    
    BASE_URL = "http://localhost:11434"
    
    def __init__(self, api_key: str = "not-needed", model_name: str = "llama3.2"):
        """Initialize Ollama provider."""
        super().__init__(api_key, model_name)
        self.headers = {"Content-Type": "application/json"}
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "ollama"
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def generate_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 512,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion using Ollama.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens (Ollama uses num_predict)
            
        Returns:
            Dict with 'text' and metadata
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
                
                logger.info(f"Sending request to Ollama with model {self.model_name}")
                response = await client.post(
                    f"{self.BASE_URL}/api/generate",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_msg = f"Ollama returned status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise ProviderError("ollama", error_msg)
                
                data = response.json()
                text = data.get("response", "")
                
                return {
                    "text": text,
                    "model": self.model_name,
                    "finish_reason": "stop"
                }
                
        except httpx.ConnectError:
            raise ProviderError("ollama", "Ollama not running. Start with: ollama serve")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in Ollama provider: {e}")
            raise ProviderError("ollama", str(e), e)
        except Exception as e:
            logger.error(f"Unexpected error in Ollama provider: {e}")
            raise ProviderError("ollama", str(e), e)
    
    async def health_check(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.BASE_URL}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
