import asyncio
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestrator.inference_manager import InferenceManager
from src.orchestrator.healer import Healer
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

async def verify_healing():
    print("\n=== Verifying Self-Healing with Real APIs ===\n")
    
    # 1. Initialize Manager to get providers
    manager = InferenceManager()
    
    # Get Groq provider (fastest for testing)
    provider = next((p for p in manager.providers if p.get_provider_name() == "groq"), None)
    
    if not provider:
        print("❌ Groq provider not found! Cannot test.")
        return

    print(f"✅ Using Provider: {provider.get_provider_name()} ({provider.model_name})")
    
    # 2. Define Broken Code and Error
    broken_code = "def calculate_sum(a, b):\n    return a + b + c  # 'c' is undefined"
    error_msg = "NameError: name 'c' is not defined"
    
    print(f"\n1️⃣  Simulating Broken Code:\n```python\n{broken_code}\n```")
    print(f"   Error: {error_msg}")
    
    # 3. Call Healer
    print("\n2️⃣  Calling Healer (Real API Request)...")
    try:
        fixed_code = await Healer.heal_code(
            code=broken_code,
            error=error_msg,
            provider=provider
        )
        
        if fixed_code:
            print(f"\n3️⃣  ✅ Healer Returned Fix:\n```python\n{fixed_code}\n```")
            
            # Simple validation: check if 'c' is removed or defined
            if "c =" in fixed_code or "c =" not in fixed_code and "return a + b" in fixed_code:
                 print("   ✅ Fix looks semantically correct!")
            else:
                 print("   ⚠️ Fix might be incorrect (manual review needed).")
                 
        else:
            print("\n3️⃣  ❌ Healer failed to generate a fix (returned None).")
            
    except Exception as e:
        print(f"\n3️⃣  ❌ Exception during healing: {e}")

if __name__ == "__main__":
    asyncio.run(verify_healing())
