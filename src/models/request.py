"""Request models for the inference gateway API."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class CodeExecutionConfig(BaseModel):
    """Configuration for sandbox code execution."""
    
    timeout: int = Field(default=30, description="Execution timeout in seconds")
    memory_limit: str = Field(default="256m", description="Memory limit (e.g., '256m', '1g')")
    cpu_limit: float = Field(default=0.5, description="CPU limit (fraction of cores)")
    network_disabled: bool = Field(default=True, description="Disable network access")


class InferenceRequest(BaseModel):
    """Main request model for inference endpoint."""
    
    prompt: str = Field(..., description="The prompt to send to LLMs")
    execute_code: bool = Field(default=True, description="Whether to execute extracted code")
    verify: bool = Field(default=True, description="Whether to verify and synthesize results")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: Optional[int] = Field(default=2048, description="Maximum tokens to generate")
    execution_config: Optional[CodeExecutionConfig] = Field(
        default_factory=CodeExecutionConfig,
        description="Sandbox execution configuration"
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Write a Python function that calculates factorial",
                "execute_code": True,
                "verify": True,
                "temperature": 0.7,
                "max_tokens": 2048
            }
        }
