import asyncio
import httpx
import time
import json

API_URL = "http://localhost:8000/api/v1/inference"
API_KEY = "test_gateway_key_12345"

async def verify_backend():
    print("🚀 Verifying Backend Features...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Test Normal Response & Caching
        print("\n1️⃣  Testing Normal Response & Caching...")
        prompt = "Write a python function to multiply two numbers"
        
        # First request (Uncached)
        start = time.time()
        resp1 = await client.post(
            API_URL,
            headers={"X-API-Key": API_KEY},
            json={"prompt": prompt, "execute_code": False, "verify": False}
        )
        duration1 = time.time() - start
        print(f"   Request 1 (Uncached): {duration1:.2f}s - Status: {resp1.status_code}")
        
        # Second request (Cached)
        start = time.time()
        resp2 = await client.post(
            API_URL,
            headers={"X-API-Key": API_KEY},
            json={"prompt": prompt, "execute_code": False, "verify": False}
        )
        duration2 = time.time() - start
        print(f"   Request 2 (Cached):   {duration2:.2f}s - Status: {resp2.status_code}")
        
        if duration2 < duration1 and duration2 < 0.5:
            print("   ✅ Caching is WORKING (Response time significantly reduced)")
        else:
            print("   ⚠️ Caching might NOT be working (Response time not significantly reduced)")

        # 2. Test Self-Healing
        print("\n2️⃣  Testing Self-Healing...")
        # Prompt designed to generate broken code (or we simulate it if we could, but here we rely on the LLM making a mistake or us forcing it)
        # Since we can't easily force the LLM to make a mistake, we'll check if the *mechanism* is active by checking logs or response structure.
        # Actually, we can try a prompt that asks for code that *might* fail if not handled, but self-healing relies on execution failure.
        # Let's try to ask for code that uses a non-existent library, which should fail execution.
        
        broken_prompt = "Write a python script that calculates 10 divided by 0 and prints the result. Do not handle the exception."
        
        resp3 = await client.post(
            API_URL,
            headers={"X-API-Key": API_KEY},
            json={"prompt": broken_prompt, "execute_code": True, "verify": False}
        )
        
        data = resp3.json()
        print(f"   Status: {resp3.status_code}")
        
        # Check for execution results
        model_responses = data.get("model_responses", [])
        healing_detected = False
        
        for resp in model_responses:
            exec_results = resp.get("execution_results", [])
            if len(exec_results) > 1:
                print(f"   ✅ Multiple execution results found for {resp['provider']} (Healing attempted)")
                healing_detected = True
                for i, res in enumerate(exec_results):
                    print(f"      - Attempt {i+1}: Success={res['success']}, Error={res.get('stderr', '')[:50]}...")
            elif len(exec_results) == 1:
                print(f"   ℹ️ Single execution result for {resp['provider']}: Success={exec_results[0]['success']}")
                print(f"      Code: {resp.get('code_blocks', [{}])[0].get('code', '')[:50]}...")
                print(f"      Stdout: {exec_results[0].get('stdout', '').strip()}")
                print(f"      Stderr: {exec_results[0].get('stderr', '').strip()}")
                
        if not healing_detected:
            print("   ⚠️ No healing detected (LLM might have refused to write broken code or execution didn't fail in a way that triggered healing)")

if __name__ == "__main__":
    asyncio.run(verify_backend())
