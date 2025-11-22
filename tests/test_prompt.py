import asyncio
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestrator.inference_manager import InferenceManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

async def test_prompt():
    print("\n=== Testing Model Inference with Prompt ===\n")
    
    # Initialize manager
    manager = InferenceManager()
    
    # Test Prompt
    prompt = "Explain the concept of rate limiting in one sentence."
    print(f"Prompt: \"{prompt}\"\n")
    
    print("Sending request to all providers...")
    results = await manager.run_inference(prompt)
    
    print("\n=== Results ===\n")
    for response in results:
        status = "SUCCESS" if not response.error else "FAILED"
        print(f"Provider: {response.provider.ljust(12)} | Model: {response.model_name}")
        print(f"Status:   {status}")
        print(f"Latency:  {response.latency:.2f}s")
        if not response.error:
            print(f"Response: {response.text.strip()}")
        else:
            print(f"Error:    {response.error}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_prompt())
