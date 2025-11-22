"""Verification script for models and rate limiting."""
import asyncio
import time
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.orchestrator.inference_manager import InferenceManager
from src.config import settings

async def verify_models():
    """Verify that both Groq and Gemini are working and rate limiter is active."""
    print(f"Initializing InferenceManager with Rate Limit: {settings.max_requests_per_minute} RPM")
    manager = InferenceManager()
    
    print("\n--- Test 1: Single Request (Connectivity Check) ---")
    prompt = "Reply with 'OK' only."
    
    try:
        responses = await manager.run_inference(prompt, max_tokens=10)
        for response in responses:
            status = "SUCCESS" if not response.error else f"FAILED: {response.error}"
            print(f"Provider: {response.provider:<10} | Status: {status} | Latency: {response.latency:.2f}s")
            
        if not responses:
            print("No responses received!")
            
    except Exception as e:
        print(f"Test 1 Failed: {e}")

    print("\n--- Test 2: Rate Limit Check (Burst of 5 requests) ---")
    # We expect these to go through quickly if tokens are available, 
    # or slow down if we hit the limit (10 RPM = 1 request every 6s on average, 
    # but token bucket allows burst if initialized full).
    # Since we just initialized, we have 10 tokens. 
    # 1 used in Test 1. 9 remaining.
    # Burst of 5 should be instant.
    
    start_time = time.time()
    tasks = []
    for i in range(5):
        tasks.append(manager.run_inference(f"Request {i}", max_tokens=5))
        
    print("Sending 5 parallel requests...")
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    print(f"Completed 5 requests in {total_time:.2f}s")
    
    success_count = 0
    for batch in results:
        for response in batch:
            if not response.error:
                success_count += 1
                
    print(f"Successful responses: {success_count}/{len(results) * len(manager.providers)}")

if __name__ == "__main__":
    asyncio.run(verify_models())
