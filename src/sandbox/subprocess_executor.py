"""Subprocess-based code executor - works without Docker!"""
import asyncio
import subprocess
import tempfile
import os
from typing import Dict, Any
from pathlib import Path
from src.models.response import CodeBlock, ExecutionResult
from src.utils.logger import setup_logger
from src.utils.errors import SandboxError

logger = setup_logger(__name__)


class SubprocessExecutor:
    """
    Execute code in isolated subprocesses.
    Fallback when Docker is not available.
    """
    
    def __init__(self):
        """Initialize subprocess executor."""
        self.timeout = 30
        logger.info("Initialized Subprocess executor (Docker fallback)")
    
    async def execute_code(
        self,
        code_block: CodeBlock,
        timeout: int = 30,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute code in a subprocess.
        
        Args:
            code_block: Code block to execute
            timeout: Execution timeout in seconds
            
        Returns:
            ExecutionResult with output
        """
        import time
        start_time = time.time()
        
        try:
            # Create temporary file for code
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=self._get_file_extension(code_block.language),
                delete=False
            ) as f:
                f.write(code_block.code)
                code_file = f.name
            
            try:
                # Get command to execute
                cmd = self._get_exec_command(code_block.language, code_file)
                
                logger.info(f"Executing {code_block.language} code in subprocess")
                
                # Run with timeout
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tempfile.gettempdir()
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                    
                    execution_time = time.time() - start_time
                    
                    return ExecutionResult(
                        success=(process.returncode == 0),
                        exit_code=process.returncode or 0,
                        stdout=stdout.decode('utf-8', errors='replace'),
                        stderr=stderr.decode('utf-8', errors='replace'),
                        execution_time=execution_time,
                        error=None if process.returncode == 0 else "Non-zero exit code"
                    )
                    
                except asyncio.TimeoutError:
                    process.kill()
                    raise SandboxError(f"Execution timed out after {timeout}s")
                    
            finally:
                # Cleanup temp file
                try:
                    os.unlink(code_file)
                except:
                    pass
                    
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Subprocess execution failed: {e}")
            
            return ExecutionResult(
                success=False,
                exit_code=1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                error=str(e)
            )
    
    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            'python': '.py',
            'javascript': '.js',
            'bash': '.sh',
            'shell': '.sh'
        }
        return extensions.get(language.lower(), '.txt')
    
    def _get_exec_command(self, language: str, file_path: str) -> list:
        """Get execution command for language."""
        commands = {
            'python': ['python3', file_path],
            'javascript': ['node', file_path],
            'bash': ['bash', file_path],
            'shell': ['bash', file_path]
        }
        
        cmd = commands.get(language.lower())
        if not cmd:
            raise SandboxError(f"Unsupported language: {language}")
        
        return cmd
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Subprocess executor cleanup complete")
