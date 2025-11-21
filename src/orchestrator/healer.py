"""Self-healing (Reflexion) logic."""
from typing import Optional
from src.providers.base import BaseLLMProvider
from src.parser import CodeExtractor
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Healer:
    """
    Healer attempts to fix broken code by feeding errors back to the LLM.
    """
    
    @staticmethod
    async def heal_code(
        code: str,
        error: str,
        provider: BaseLLMProvider,
        model_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Attempt to fix the code using the provided LLM.
        
        Args:
            code: The broken code
            error: The error message (stderr)
            provider: The LLM provider to use for fixing
            model_name: Optional model override
            
        Returns:
            The fixed code, or None if healing failed
        """
        try:
            logger.info(f"Attempting to heal code with {provider.get_provider_name()}")
            
            # Construct the healing prompt
            prompt = (
                f"The following Python code failed to execute with an error.\n"
                f"Please fix the code to resolve the error. Return ONLY the fixed code.\n\n"
                f"ERROR:\n{error}\n\n"
                f"BROKEN CODE:\n```python\n{code}\n```\n\n"
                f"FIXED CODE:"
            )
            
            # Call the LLM
            response = await provider.generate_completion(
                prompt=prompt,
                temperature=0.2,  # Low temperature for precise fixes
                max_tokens=2048
            )
            
            text = response.get("text", "")
            if not text:
                logger.warning("Healer received empty response")
                return None
                
            # Extract code from response
            code_blocks = CodeExtractor.extract_code_blocks(text)
            executable_blocks = CodeExtractor.filter_executable_blocks(code_blocks)
            
            if executable_blocks:
                fixed_code = executable_blocks[0].code
                logger.info("Successfully generated potential fix")
                return fixed_code
            
            # Fallback: if no blocks found, maybe the whole text is code?
            # But usually models wrap in backticks. Let's be safe and return None if unsure.
            logger.warning("No executable code blocks found in healer response")
            return None
            
        except Exception as e:
            logger.error(f"Healing failed: {e}")
            return None
