import asyncio
import httpx
import json

API_URL = "http://localhost:8000/api/v1/inference"
API_KEY = "test_gateway_key_12345"

async def verify_synthesis():
    print("🚀 Verifying Synthesis (Judge) Logic...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        prompt = "Write a python function to return the list of first 5 prime numbers."
        
        print(f"\nSending request with verify=True...")
        try:
            response = await client.post(
                API_URL,
                headers={"X-API-Key": API_KEY},
                json={
                    "prompt": prompt,
                    "execute_code": True,  # Execution is needed for verification often
                    "verify": True,        # This triggers the Synthesizer
                    "temperature": 0.1
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Request failed: {response.status_code}")
                print(response.text)
                return

            data = response.json()
            verification = data.get("verification")
            
            if verification:
                print("\n✅ Verification Report Received:")
                print(f"  - Verified: {verification.get('verified')}")
                print(f"  - Consensus Reached: {verification.get('consensus')}")
                print(f"  - Strategy: {verification.get('synthesis_strategy')}")
                print(f"  - Successful Executions: {verification.get('successful_executions')}")
                
                details = verification.get("details", {})
                if details:
                    print(f"  - Details: {json.dumps(details, indent=2)}")
            else:
                print("\n❌ No verification report found in response.")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_synthesis())
