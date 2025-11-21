"""Google Gemini API provider."""
import google.generativeai as genai
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from src.providers.base import BaseLLMProvider
from src.utils.errors import ProviderError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
        """Initialize Gemini provider."""
        super().__init__(api_key, model_name)
        genai.configure(api_key=api_key)
        
        # Initialize the model with minimal safety settings
        self.model = genai.GenerativeModel(model_name=model_name)
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "gemini"
    
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
        Generate completion using Gemini API.
        
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
            logger.info(f"Sending request to Gemini API with model {self.model_name}")
            
            # Create generation config
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            # Generate content
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            
            # Extract text from response
            if not response.parts:
                raise ProviderError("gemini", "Empty response from Gemini API")
            
            text = response.text
            
            return {
                "text": text,
                "model": self.model_name,
                "finish_reason": response.candidates[0].finish_reason.name if response.candidates else None,
                "safety_ratings": [
                    {
                        "category": rating.category.name,
                        "probability": rating.probability.name
                    }
                    for rating in (response.candidates[0].safety_ratings if response.candidates else [])
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in Gemini provider: {e}")
            raise ProviderError("gemini", str(e), e)
    
    async def health_check(self) -> bool:
        """Check if Gemini API is accessible."""
        try:
            # Try a simple generation
            response = await self.model.generate_content_async(
                "Hello",
                generation_config=genai.GenerationConfig(max_output_tokens=10)
            )
            return bool(response.text)
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False
