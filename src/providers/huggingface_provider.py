"""Hugging Face Inference API provider."""
import httpx
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from src.providers.base import BaseLLMProvider
from src.utils.errors import ProviderError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class HuggingFaceProvider(BaseLLMProvider):
    """Hugging Face Inference API provider - FREE tier available!"""
    
    BASE_URL = "https://router.huggingface.co/models"
    
    def __init__(self, api_key: str, model_name: str = "google/flan-t5-large"):
        """Initialize HuggingFace provider with a reliable free model."""
        super().__init__(api_key, model_name)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "huggingface"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 512,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion using HuggingFace Inference API.
        
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
                # Format for text generation models
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "temperature": temperature,
                        "max_new_tokens": max_tokens,
                        "return_full_text": False,
                        "do_sample": True
                    },
                    "options": {
                        "wait_for_model": True,
                        "use_cache": False
                    }
                }
                
                logger.info(f"Sending request to HuggingFace API with model {self.model_name}")
                response = await client.post(
                    f"{self.BASE_URL}/{self.model_name}",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 503:
                    # Model is loading, wait and retry
                    logger.warning("Model is loading, will retry...")
                    raise ProviderError("huggingface", "Model is loading")
                
                if response.status_code != 200:
                    error_msg = f"HuggingFace API returned status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise ProviderError("huggingface", error_msg)
                
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict):
                        text = data[0].get("generated_text", "")
                    else:
                        text = str(data[0])
                elif isinstance(data, dict):
                    text = data.get("generated_text", "") or data.get("text", "")
                else:
                    text = str(data)
                
                return {
                    "text": text,
                    "model": self.model_name,
                    "finish_reason": "stop"
                }
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in HuggingFace provider: {e}")
            raise ProviderError("huggingface", str(e), e)
        except Exception as e:
            logger.error(f"Unexpected error in HuggingFace provider: {e}")
            raise ProviderError("huggingface", str(e), e)
    
    async def health_check(self) -> bool:
        """Check if HuggingFace API is accessible."""
        try:
            # Try a simple generation
            result = await self.generate_completion(
                prompt="Hello",
                max_tokens=10
            )
            return bool(result.get("text"))
        except Exception as e:
            logger.warning(f"HuggingFace health check failed: {e}")
            return False
