"""Main FastAPI application for the Inference Gateway."""
import uuid
import time
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
from typing import Optional

from src.models.request import InferenceRequest
from src.models.response import InferenceResponse, ModelResponse
from src.orchestrator import InferenceManager
from src.parser import CodeExtractor
from src.sandbox import SandboxExecutor
from src.judge import Synthesizer
from src.config import settings
from src.utils.logger import setup_logger
from src.utils.errors import InferenceGatewayError

logger = setup_logger(__name__)

# Global instances
inference_manager: Optional[InferenceManager] = None
sandbox_executor: Optional[SandboxExecutor] = None
instrumentator: Optional[Instrumentator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global inference_manager, sandbox_executor
    
    # Startup
    logger.info("Starting Inference Gateway...")
    try:
        inference_manager = InferenceManager()
        logger.info("Inference manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize inference manager: {e}")
        raise
    
    # Try to initialize sandbox executor (optional if Docker not available)
    try:
        from src.sandbox.executor import SandboxExecutor
        sandbox_executor = SandboxExecutor()
        logger.info("Sandbox executor initialized successfully (Docker)")
    except Exception as e:
        logger.warning(f"Docker sandbox failed, using subprocess fallback: {e}")
        try:
            from src.sandbox.subprocess_executor import SubprocessExecutor
            sandbox_executor = SubprocessExecutor()
            logger.info("Subprocess executor initialized successfully (fallback)")
        except Exception as e2:
            logger.error(f"All executors failed: {e2}")
            sandbox_executor = None
    
    yield
    
    # Shutdown
    logger.info("Shutting down Inference Gateway...")
    if sandbox_executor:
        sandbox_executor.cleanup()


# Create FastAPI app
app = FastAPI(
    title="Distributed Multi-Model Inference Verification Gateway",
    description="MLOps system for trusted AI with multi-model inference and sandbox verification",
    version="1.0.0",
    lifespan=lifespan
)

# Setup Prometheus Instrumentation
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[".*admin.*", "/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="inference_gateway_inprogress",
    inprogress_labels=True,
)
instrumentator.instrument(app).expose(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for web interface
app.mount("/web", StaticFiles(directory="web", html=True), name="web")



# Authentication dependency
async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key from request header."""
    if x_api_key != settings.gateway_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@app.get("/")
async def root():
    """Root endpoint serving the Web UI."""
    from fastapi.responses import FileResponse
    return FileResponse("web/index.html")


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check provider health
        provider_health = await inference_manager.health_check()
        
        return {
            "status": "healthy",
            "providers": provider_health,
            "models": {
                "groq": settings.groq_model,
                "gemini": settings.gemini_model
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")


@app.get("/api/v1/debug/config")
async def debug_config(api_key: str = Depends(verify_api_key)):
    """Debug endpoint to check loaded configuration (Masked)."""
    def mask(s: str) -> str:
        return f"{s[:4]}...{s[-4:]}" if s and len(s) > 8 else "Not Set"

    import google.generativeai as genai
    return {
        "groq_key": mask(settings.groq_api_key),
        "google_key": mask(settings.google_api_key),
        "gateway_key": mask(settings.gateway_api_key),
        "groq_model": settings.groq_model,
        "gemini_model": settings.gemini_model,
        "environment": settings.environment,
        "genai_version": getattr(genai, "__version__", "unknown")
    }


@app.get("/api/v1/models")
async def list_models():
    """List available models."""
    return {
        "models": [
            {"provider": "groq", "model": settings.groq_model, "name": "Llama 3.3 70B"},
            {"provider": "gemini", "model": settings.gemini_model, "name": "Gemini 1.5 Pro"}
        ]
    }


@app.get("/api/v1/cache/stats")
async def cache_stats():
    """Get semantic cache statistics."""
    from src.cache import get_cache
    cache = get_cache()
    return cache.get_stats()


@app.post("/api/v1/cache/clear")
async def clear_cache(api_key: str = Depends(verify_api_key)):
    """Clear semantic cache (authenticated)."""
    from src.cache import get_cache
    cache = get_cache()
    cache.clear()
    return {"status": "cache_cleared"}


@app.post("/api/v1/inference", response_model=InferenceResponse)
async def run_inference(
    request: InferenceRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Main inference endpoint.
    
    Orchestrates parallel LLM requests, extracts code, executes in sandbox,
    and returns verified results.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"[{request_id}] Starting inference request")
    logger.info(f"[{request_id}] Prompt: {request.prompt[:100]}...")
    
    try:
        # Step 1: Run inference on all providers in parallel
        logger.info(f"[{request_id}] Running parallel inference")
        model_responses = await inference_manager.run_inference(
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if not model_responses:
            raise HTTPException(
                status_code=503,
                detail="All LLM providers failed"
            )
        
        logger.info(f"[{request_id}] Received {len(model_responses)} response(s)")
        
        # Step 2: Extract code blocks from responses
        if request.execute_code:
            logger.info(f"[{request_id}] Extracting code blocks")
            
            for response in model_responses:
                if response.text and not response.error:
                    response.code_blocks = CodeExtractor.extract_code_blocks(response.text)
                    response.code_blocks = CodeExtractor.filter_executable_blocks(response.code_blocks)
                    logger.info(
                        f"[{request_id}] Extracted {len(response.code_blocks)} "
                        f"executable block(s) from {response.provider}"
                    )
            
        # Step 3: Execute code blocks in sandbox
        if sandbox_executor is None:
            logger.warning(f"[{request_id}] Sandbox executor not available, skipping code execution")
        else:
            logger.info(f"[{request_id}] Executing code in sandbox")
            
            for response in model_responses:
                for code_block in response.code_blocks:
                    try:
                        exec_result = await sandbox_executor.execute_code(
                            code_block,
                            timeout=request.execution_config.timeout,
                            memory_limit=request.execution_config.memory_limit,
                            cpu_limit=request.execution_config.cpu_limit
                        )
                        response.execution_results.append(exec_result)
                        
                        logger.info(
                            f"[{request_id}] Executed {code_block.language} code: "
                            f"success={exec_result.success}"
                        )
                    except Exception as e:
                        logger.error(f"[{request_id}] Execution failed: {e}")

            # Step 3.5: Self-Healing (Reflexion)
            # If code failed, ask the LLM to fix it and re-run
            from src.orchestrator.healer import Healer
            
            for response in model_responses:
                # Check for failed executions with error output
                for i, result in enumerate(response.execution_results):
                    if not result.success and result.stderr:
                        logger.info(f"[{request_id}] Detected execution failure for {response.provider}. Attempting to heal...")
                        
                        # Find the provider instance
                        provider_instance = next(
                            (p for p in inference_manager.providers if p.get_provider_name() == response.provider),
                            None
                        )
                        
                        if provider_instance and i < len(response.code_blocks):
                            broken_code = response.code_blocks[i].code
                            
                            # Attempt to heal
                            fixed_code = await Healer.heal_code(
                                code=broken_code,
                                error=result.stderr,
                                provider=provider_instance
                            )
                            
                            if fixed_code:
                                logger.info(f"[{request_id}] Healer generated fix. Re-executing...")
                                
                                try:
                                    # Create new code block
                                    from src.models.response import CodeBlock
                                    new_block = CodeBlock(language="python", code=fixed_code)
                                    
                                    # Re-execute
                                    new_result = await sandbox_executor.execute_code(
                                        new_block,
                                        timeout=request.execution_config.timeout,
                                        memory_limit=request.execution_config.memory_limit,
                                        cpu_limit=request.execution_config.cpu_limit
                                    )
                                    
                                    # Update response with fixed code and new result
                                    response.code_blocks[i] = new_block
                                    response.execution_results[i] = new_result
                                    
                                    logger.info(f"[{request_id}] Healing result: success={new_result.success}")
                                    
                                except Exception as e:
                                    logger.error(f"[{request_id}] Re-execution of healed code failed: {e}")
        
        # Step 4: Verify and synthesize results
        verification = None
        selected_response = None
        
        if request.verify:
            logger.info(f"[{request_id}] Verifying and synthesizing results")
            selected_response, verification = Synthesizer.synthesize(
                model_responses,
                verify=True
            )
            
            logger.info(
                f"[{request_id}] Synthesis complete: "
                f"strategy={verification.synthesis_strategy}, "
                f"consensus={verification.consensus}"
            )
        else:
            # Just pick the first successful response
            selected_response = next(
                (r for r in model_responses if not r.error),
                model_responses[0] if model_responses else None
            )
        
        # Calculate total latency
        total_latency = time.time() - start_time
        
        logger.info(f"[{request_id}] Request completed in {total_latency:.2f}s")
        
        return InferenceResponse(
            request_id=request_id,
            model_responses=model_responses,
            verification=verification,
            selected_response=selected_response,
            total_latency=total_latency
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Inference failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Inference failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
