import asyncio
import httpx
import json

API_URL = "http://localhost:8000/api/v1/inference"
API_KEY = "test_gateway_key_12345"

async def test_combinations():
    print("🚀 Testing Feature Combinations...\n")
    
    prompt = "Write a python function to add two numbers and print the result of 2+2"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Case 1: Execute Only
        print("1️⃣  Case: Execute=TRUE, Verify=FALSE")
        resp1 = await client.post(
            API_URL, headers={"X-API-Key": API_KEY},
            json={"prompt": prompt, "execute_code": True, "verify": False}
        )
        data1 = resp1.json()
        has_exec1 = len(data1['model_responses'][0]['execution_results']) > 0
        has_verif1 = data1['verification'] is not None
        print(f"   -> Execution Results Present: {has_exec1}")
        print(f"   -> Verification Report Present: {has_verif1}")
        print(f"   -> Output: {data1['model_responses'][0]['execution_results'][0]['stdout'].strip() if has_exec1 else 'N/A'}\n")

        # Case 2: Verify Only
        print("2️⃣  Case: Execute=FALSE, Verify=TRUE")
        resp2 = await client.post(
            API_URL, headers={"X-API-Key": API_KEY},
            json={"prompt": prompt, "execute_code": False, "verify": True}
        )
        data2 = resp2.json()
        has_exec2 = len(data2['model_responses'][0]['execution_results']) > 0
        has_verif2 = data2['verification'] is not None
        print(f"   -> Execution Results Present: {has_exec2}")
        print(f"   -> Verification Report Present: {has_verif2}")
        if has_verif2:
            print(f"   -> Strategy: {data2['verification']['synthesis_strategy']}")
        print("")

        # Case 3: Both
        print("3️⃣  Case: Execute=TRUE, Verify=TRUE")
        resp3 = await client.post(
            API_URL, headers={"X-API-Key": API_KEY},
            json={"prompt": prompt, "execute_code": True, "verify": True}
        )
        data3 = resp3.json()
        has_exec3 = len(data3['model_responses'][0]['execution_results']) > 0
        has_verif3 = data3['verification'] is not None
        print(f"   -> Execution Results Present: {has_exec3}")
        print(f"   -> Verification Report Present: {has_verif3}")
        if has_verif3:
            print(f"   -> Consensus: {data3['verification']['consensus']}")

if __name__ == "__main__":
    asyncio.run(test_combinations())
