"""Code extraction from LLM responses."""
import re
from typing import List, Tuple
from src.models.response import CodeBlock
from src.utils.errors import CodeExtractionError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class CodeExtractor:
    """Extract code blocks from LLM-generated text."""
    
    # Regex pattern for code fences
    CODE_FENCE_PATTERN = re.compile(
        r'```(\w+)?\n(.*?)```',
        re.DOTALL | re.MULTILINE
    )
    
    # Supported languages
    SUPPORTED_LANGUAGES = {
        'python', 'py', 'javascript', 'js', 'node',
        'typescript', 'ts', 'bash', 'sh', 'shell'
    }
    
    @classmethod
    def extract_code_blocks(cls, text: str) -> List[CodeBlock]:
        """
        Extract all code blocks from text.
        
        Args:
            text: Text containing code blocks
            
        Returns:
            List of CodeBlock objects
        """
        code_blocks = []
        
        # Find all code fences
        matches = cls.CODE_FENCE_PATTERN.finditer(text)
        
        for match in matches:
            language = match.group(1) or 'unknown'
            code = match.group(2).strip()
            
            # Normalize language names
            language = cls._normalize_language(language)
            
            # Calculate line numbers
            line_start = text[:match.start()].count('\n') + 1
            line_end = line_start + code.count('\n')
            
            code_block = CodeBlock(
                language=language,
                code=code,
                line_start=line_start,
                line_end=line_end
            )
            
            code_blocks.append(code_block)
            logger.debug(f"Extracted {language} code block ({len(code)} chars)")
        
        if not code_blocks:
            logger.warning("No code blocks found in text")
        else:
            logger.info(f"Extracted {len(code_blocks)} code block(s)")
        
        return code_blocks
    
    @classmethod
    def _normalize_language(cls, language: str) -> str:
        """
        Normalize language identifier.
        
        Args:
            language: Raw language identifier
            
        Returns:
            Normalized language name
        """
        language = language.lower().strip()
        
        # Map common variations
        language_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'sh': 'bash',
            'shell': 'bash',
            'node': 'javascript'
        }
        
        return language_map.get(language, language)
    
    @classmethod
    def filter_executable_blocks(cls, code_blocks: List[CodeBlock]) -> List[CodeBlock]:
        """
        Filter code blocks to only executable ones.
        
        Args:
            code_blocks: List of all code blocks
            
        Returns:
            List of executable code blocks (Python, JavaScript)
        """
        executable = ['python', 'javascript', 'bash']
        filtered = [
            block for block in code_blocks
            if block.language in executable
        ]
        
        logger.info(f"Filtered to {len(filtered)} executable block(s) from {len(code_blocks)} total")
        return filtered
    
    @classmethod
    def validate_syntax(cls, code_block: CodeBlock) -> Tuple[bool, str]:
        """
        Perform basic syntax validation.
        
        Args:
            code_block: Code block to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if code_block.language == 'python':
            try:
                compile(code_block.code, '<string>', 'exec')
                return True, ""
            except SyntaxError as e:
                return False, f"Python syntax error: {e}"
        
        # For other languages, just check if code is not empty
        if not code_block.code.strip():
            return False, "Empty code block"
        
        return True, ""
