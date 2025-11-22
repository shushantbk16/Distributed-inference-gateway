import asyncio
import httpx
import sys

# Configuration
LIVE_URL = "https://distributed-multi-model-inference.onrender.com"
API_KEY = "test_gateway_key_12345"  # Default key from web/app.js

async def verify_live():
    print(f"=== Verifying Live Deployment: {LIVE_URL} ===\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 0. Root Check
        print("0. Checking Root URL...")
        try:
            response = await client.get(f"{LIVE_URL}/")
            if response.status_code == 200:
                print(f"   ✅ Root Status: {response.status_code} (Server is UP)")
            else:
                print(f"   ❌ Root Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Root Error: {e}")
            
        print("-" * 50)

        # 0.5 Docs Check
        print("0.5 Checking /docs...")
        try:
            response = await client.get(f"{LIVE_URL}/docs")
            if response.status_code == 200:
                print(f"   ✅ Docs Status: {response.status_code} (Swagger UI is UP)")
            else:
                print(f"   ❌ Docs Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Docs Error: {e}")
            
        print("-" * 50)

        # 0.6 OpenAPI Check
        print("0.6 Checking /openapi.json...")
        try:
            response = await client.get(f"{LIVE_URL}/openapi.json")
            if response.status_code == 200:
                schema = response.json()
                print(f"   ✅ Schema Found!")
                print(f"   ✅ Available Paths:")
                for path in schema.get('paths', {}):
                    print(f"      - {path}")
            else:
                print(f"   ❌ Schema Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Schema Error: {e}")
            
        print("-" * 50)

        # 1. Health Check
        print("1. Checking Health...")
        try:
            response = await client.get(f"{LIVE_URL}/api/v1/health")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Status: {data['status']}")
                print(f"   ✅ Providers: {data.get('providers', 'Unknown')}")
            else:
                print(f"   ❌ Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        print("-" * 50)
        
        # 2. Inference Test
        print("2. Testing Inference...")
        prompt = "Explain the concept of rate limiting in one sentence."
        print(f"   Prompt: \"{prompt}\"")
        
        try:
            response = await client.post(
                f"{LIVE_URL}/api/v1/inference",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                },
                json={
                    "prompt": prompt,
                    "execute_code": False,
                    "verify": False,
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Request ID: {data['request_id']}")
                print(f"   ✅ Total Latency: {data['total_latency']:.2f}s")
                
                print("\n   Responses:")
                for model_res in data['model_responses']:
                    status = "✅ Success" if not model_res.get('error') else f"❌ Error: {model_res.get('error')}"
                    print(f"   - {model_res['provider'].ljust(10)}: {status}")
                    if not model_res.get('error'):
                        print(f"     \"{model_res['text'][:100]}...\"")
            else:
                print(f"   ❌ Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # 3. Ensemble Check (Legacy/Different App?)
        print("-" * 50)
        print("3. Testing /ensemble (Discovered via OpenAPI)...")
        try:
            response = await client.post(
                f"{LIVE_URL}/ensemble",
                headers={"Content-Type": "application/json"},
                json={"prompt": prompt}
            )
            if response.status_code == 200:
                print(f"   ✅ Ensemble Status: {response.status_code}")
                print(f"   ✅ Response: {response.text[:100]}...")
            else:
                print(f"   ❌ Ensemble Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"   ❌ Ensemble Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_live())
