"""Docker sandbox executor for secure code execution."""
import asyncio
import docker
import time
import tempfile
import os
from typing import Dict, Any, Optional
from pathlib import Path
from src.models.response import CodeBlock, ExecutionResult
from src.config import settings
from src.utils.errors import SandboxError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SandboxExecutor:
    """Execute code in isolated Docker containers."""
    
    # Image names for different languages
    IMAGES = {
        'python': 'inference-gateway-python-sandbox',
        'javascript': 'inference-gateway-js-sandbox',
        'bash': 'inference-gateway-python-sandbox'  # Use Python image for bash
    }
    
    def __init__(self):
        """Initialize the Docker client."""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise SandboxError(f"Docker initialization failed: {e}")
    
    async def execute_code(
        self,
        code_block: CodeBlock,
        timeout: Optional[int] = None,
        memory_limit: Optional[str] = None,
        cpu_limit: Optional[float] = None
    ) -> ExecutionResult:
        """
        Execute code in a sandboxed container.
        
        Args:
            code_block: The code block to execute
            timeout: Execution timeout in seconds (default from settings)
            memory_limit: Memory limit (default from settings)
            cpu_limit: CPU limit (default from settings)
            
        Returns:
            ExecutionResult with execution details
        """
        if timeout is None:
            timeout = settings.sandbox_timeout
        if memory_limit is None:
            memory_limit = settings.sandbox_memory_limit
        if cpu_limit is None:
            cpu_limit = settings.sandbox_cpu_limit
        
        language = code_block.language
        
        # Check if we support this language
        if language not in self.IMAGES:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Unsupported language: {language}",
                execution_time=0.0,
                error=f"Language '{language}' is not supported for execution"
            )
        
        logger.info(f"Executing {language} code in sandbox (timeout={timeout}s)")
        
        # Run execution in thread pool to avoid blocking
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._execute_sync,
                code_block,
                timeout,
                memory_limit,
                cpu_limit
            )
            return result
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=0.0,
                error=f"Execution failed: {e}"
            )
    
    def _execute_sync(
        self,
        code_block: CodeBlock,
        timeout: int,
        memory_limit: str,
        cpu_limit: float
    ) -> ExecutionResult:
        """
        Synchronous execution of code in Docker.
        
        This runs in a thread pool via run_in_executor.
        """
        start_time = time.time()
        container = None
        
        try:
            # Get the appropriate image
            image_name = self.IMAGES[code_block.language]
            
            # Ensure image exists (build if needed)
            self._ensure_image(code_block.language, image_name)
            
            # Create temporary file with code
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=self._get_file_extension(code_block.language),
                delete=False
            ) as f:
                f.write(code_block.code)
                temp_file = f.name
            
            try:
                # Prepare command based on language
                command = self._get_execution_command(code_block.language, '/workspace/code')
                
                # Create and run container
                container = self.docker_client.containers.run(
                    image_name,
                    command=command,
                    detach=True,
                    mem_limit=memory_limit,
                    nano_cpus=int(cpu_limit * 1e9),  # Convert to nanocpus
                    network_disabled=settings.sandbox_network_disabled,
                    volumes={
                        temp_file: {'bind': '/workspace/code', 'mode': 'ro'}
                    },
                    remove=False  # We'll remove manually after getting logs
                )
                
                # Wait for container with timeout
                result = container.wait(timeout=timeout)
                exit_code = result['StatusCode']
                
                # Get logs
                stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
                stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
                
                execution_time = time.time() - start_time
                
                success = exit_code == 0
                
                logger.info(
                    f"Execution completed: exit_code={exit_code}, "
                    f"time={execution_time:.2f}s, success={success}"
                )
                
                return ExecutionResult(
                    success=success,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    execution_time=execution_time,
                    error=stderr if not success else None
                )
                
            finally:
                # Cleanup temporary file
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")
                
                # Cleanup container
                if container and settings.cleanup_containers:
                    try:
                        container.remove(force=True)
                    except Exception as e:
                        logger.warning(f"Failed to remove container: {e}")
        
        except docker.errors.ContainerError as e:
            execution_time = time.time() - start_time
            logger.error(f"Container error: {e}")
            return ExecutionResult(
                success=False,
                exit_code=e.exit_status,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                error=f"Container error: {e}"
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Execution error: {e}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                error=f"Execution failed: {e}"
            )
    
    def _ensure_image(self, language: str, image_name: str):
        """Ensure Docker image exists, build if needed."""
        try:
            self.docker_client.images.get(image_name)
            logger.debug(f"Image {image_name} already exists")
        except docker.errors.ImageNotFound:
            logger.info(f"Building image {image_name}")
            self._build_image(language, image_name)
    
    def _build_image(self, language: str, image_name: str):
        """Build Docker image from Dockerfile."""
        # Map language to dockerfile directory
        lang_dir_map = {
            'python': 'python',
            'javascript': 'javascript',
            'bash': 'python'
        }
        
        dockerfile_dir = Path(__file__).parent.parent.parent / 'docker' / 'sandbox' / lang_dir_map[language]
        
        if not dockerfile_dir.exists():
            raise SandboxError(f"Dockerfile directory not found: {dockerfile_dir}")
        
        logger.info(f"Building Docker image from {dockerfile_dir}")
        
        try:
            self.docker_client.images.build(
                path=str(dockerfile_dir),
                tag=image_name,
                rm=True
            )
            logger.info(f"Successfully built image {image_name}")
        except Exception as e:
            logger.error(f"Failed to build image: {e}")
            raise SandboxError(f"Failed to build Docker image: {e}")
    
    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            'python': '.py',
            'javascript': '.js',
            'bash': '.sh'
        }
        return extensions.get(language, '.txt')
    
    def _get_execution_command(self, language: str, file_path: str) -> list:
        """Get execution command for language."""
        commands = {
            'python': ['python3', file_path],
            'javascript': ['node', file_path],
            'bash': ['sh', file_path]
        }
        return commands.get(language, ['cat', file_path])
    
    def cleanup(self):
        """Cleanup Docker resources."""
        try:
            self.docker_client.close()
            logger.info("Docker client closed")
        except Exception as e:
            logger.warning(f"Error closing Docker client: {e}")
