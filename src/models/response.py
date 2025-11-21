"""Response models for the inference gateway API."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class CodeBlock(BaseModel):
    """Extracted code block."""
    
    language: str = Field(..., description="Programming language")
    code: str = Field(..., description="Code content")
    line_start: Optional[int] = Field(default=None, description="Starting line number")
    line_end: Optional[int] = Field(default=None, description="Ending line number")


class ExecutionResult(BaseModel):
    """Result from sandbox code execution."""
    
    success: bool = Field(..., description="Whether execution was successful")
    exit_code: int = Field(..., description="Exit code from execution")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    execution_time: float = Field(..., description="Execution time in seconds")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ModelResponse(BaseModel):
    """Response from a single LLM provider."""
    
    model_config = {"protected_namespaces": ()}
    
    model_name: str = Field(..., description="Model identifier")
    provider: str = Field(..., description="Provider name (groq, gemini)")
    text: str = Field(..., description="Generated text")
    code_blocks: List[CodeBlock] = Field(default_factory=list, description="Extracted code blocks")
    execution_results: List[ExecutionResult] = Field(
        default_factory=list,
        description="Execution results for code blocks"
    )
    latency: float = Field(..., description="Response latency in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class VerificationReport(BaseModel):
    """Verification and synthesis report."""
    
    verified: bool = Field(..., description="Whether results were verified")
    consensus: bool = Field(..., description="Whether models reached consensus")
    successful_executions: int = Field(..., description="Number of successful executions")
    total_executions: int = Field(..., description="Total number of executions")
    synthesis_strategy: str = Field(..., description="Strategy used for synthesis")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class InferenceResponse(BaseModel):
    """Complete response from the inference gateway."""
    
    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "request_id": "req_123456",
                "model_responses": [],
                "verification": None,
                "selected_response": None,
                "total_latency": 2.5,
                "timestamp": "2024-01-01T00:00:00"
            }
        }
    }
    
    request_id: str = Field(..., description="Unique request identifier")
    model_responses: List[ModelResponse] = Field(..., description="Responses from all models")
    verification: Optional[VerificationReport] = Field(default=None, description="Verification report")
    selected_response: Optional[ModelResponse] = Field(
        default=None,
        description="Selected/synthesized response"
    )
    total_latency: float = Field(..., description="Total request latency in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")
