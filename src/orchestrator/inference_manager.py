"""Inference orchestration manager."""
import asyncio
import time
from typing import List, Dict, Any
from datetime import datetime
from src.providers import GroqProvider, GeminiProvider, BaseLLMProvider
from src.models.response import ModelResponse
from src.config import settings
from src.utils.logger import setup_logger
from src.utils.errors import ProviderError

logger = setup_logger(__name__)


class InferenceManager:
    """Manages parallel inference requests to multiple LLM providers."""
    
    def __init__(self):
        """Initialize the inference manager with all providers."""
        self.providers: List[BaseLLMProvider] = []
        
        # Initialize Groq provider
        try:
            groq = GroqProvider(
                api_key=settings.groq_api_key,
                model_name=settings.groq_model
            )
            self.providers.append(groq)
            logger.info(f"Initialized Groq provider with model {settings.groq_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq provider: {e}")
        
        # Initialize Gemini provider
        try:
            gemini = GeminiProvider(
                api_key=settings.google_api_key,
                model_name=settings.gemini_model
            )
            self.providers.append(gemini)
            logger.info(f"Initialized Gemini provider with model {settings.gemini_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini provider: {e}")
        
        # Initialize OpenAI provider (if API key is provided)
        if settings.openai_api_key:
            try:
                from src.providers.openai_provider import OpenAIProvider
                openai = OpenAIProvider(
                    api_key=settings.openai_api_key,
                    model_name=settings.openai_model
                )
                self.providers.append(openai)
                logger.info(f"Initialized OpenAI provider with model {settings.openai_model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI provider: {e}")
        
        # Initialize HuggingFace provider (FREE tier - if API key provided)
        if settings.huggingface_api_key:
            try:
                from src.providers.huggingface_provider import HuggingFaceProvider
                huggingface = HuggingFaceProvider(
                    api_key=settings.huggingface_api_key,
                    model_name=settings.huggingface_model
                )
                self.providers.append(huggingface)
                logger.info(f"Initialized HuggingFace provider with model {settings.huggingface_model}")
            except Exception as e:
                logger.error(f"Failed to initialize HuggingFace provider: {e}")
        
        # Initialize Ollama provider (local, always try - it's FREE!)
        try:
            from src.providers.ollama_provider import OllamaProvider
            ollama = OllamaProvider(
                model_name=settings.ollama_model
            )
            self.providers.append(ollama)
            logger.info(f"Initialized Ollama provider with model {settings.ollama_model}")
        except Exception as e:
            logger.warning(f"Ollama not available (install with: brew install ollama): {e}")
        
        if not self.providers:
            raise RuntimeError("No LLM providers could be initialized")
    
    async def run_inference(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float = None
    ) -> List[ModelResponse]:
        """
        Run inference on all providers in parallel.
        
        Args:
            prompt: The prompt to send to all providers
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Optional timeout for each provider request
            
        Returns:
            List of ModelResponse objects (may be incomplete if some providers fail)
        """
        if timeout is None:
            timeout = settings.request_timeout
        
        logger.info(f"Starting parallel inference with {len(self.providers)} provider(s)")
        
        # Create tasks for all providers
        tasks = [
            self._run_provider_inference(
                provider,
                prompt,
                temperature,
                max_tokens,
                timeout
            )
            for provider in self.providers
        ]
        
        # Run all tasks in parallel and wait for all to complete (or fail)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and collect successful responses
        responses = []
        for result in results:
            if isinstance(result, ModelResponse):
                responses.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Provider inference failed: {result}")
        
        logger.info(f"Completed inference: {len(responses)}/{len(self.providers)} provider(s) succeeded")
        
        return responses
    
    async def _run_provider_inference(
        self,
        provider: BaseLLMProvider,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> ModelResponse:
        """
        Run inference for a single provider with timeout.
        
        Args:
            provider: The LLM provider
            prompt: The prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            timeout: Timeout in seconds
            
        Returns:
            ModelResponse object
            
        Raises:
            ProviderError: If the provider fails
            asyncio.TimeoutError: If the request times out
        """
        provider_name = provider.get_provider_name()
        start_time = time.time()
        
        try:
            logger.info(f"Starting inference for provider: {provider_name}")
            
            # Run with timeout
            result = await asyncio.wait_for(
                provider.generate_completion(
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                ),
                timeout=timeout
            )
            
            latency = time.time() - start_time
            
            response = ModelResponse(
                model_name=result.get("model", provider.model_name),
                provider=provider_name,
                text=result["text"],
                code_blocks=[],  # Will be populated later by code extractor
                execution_results=[],
                latency=latency,
                timestamp=datetime.utcnow(),
                error=None
            )
            
            logger.info(f"Provider {provider_name} completed in {latency:.2f}s")
            return response
            
        except asyncio.TimeoutError:
            latency = time.time() - start_time
            error_msg = f"Provider {provider_name} timed out after {timeout}s"
            logger.error(error_msg)
            
            return ModelResponse(
                model_name=provider.model_name,
                provider=provider_name,
                text="",
                code_blocks=[],
                execution_results=[],
                latency=latency,
                timestamp=datetime.utcnow(),
                error=error_msg
            )
            
        except Exception as e:
            latency = time.time() - start_time
            error_msg = f"Provider {provider_name} failed: {str(e)}"
            logger.error(error_msg)
            
            return ModelResponse(
                model_name=provider.model_name,
                provider=provider_name,
                text="",
                code_blocks=[],
                execution_results=[],
                latency=latency,
                timestamp=datetime.utcnow(),
                error=error_msg
            )
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all providers.
        
        Returns:
            Dict mapping provider name to health status
        """
        health_tasks = [
            provider.health_check()
            for provider in self.providers
        ]
        
        results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        health_status = {}
        for provider, result in zip(self.providers, results):
            provider_name = provider.get_provider_name()
            if isinstance(result, bool):
                health_status[provider_name] = result
            else:
                health_status[provider_name] = False
        
        return health_status
