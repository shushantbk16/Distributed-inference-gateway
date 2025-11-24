import asyncio
import httpx
import sys

API_URL = "http://localhost:8000/api/v1/inference"
API_KEY = "test_gateway_key_12345"

async def verify_providers():
    print("🚀 Verifying Groq and Gemini Providers...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                API_URL,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                },
                json={
                    "prompt": "Say 'Hello' and identify yourself.",
                    "execute_code": False,
                    "verify": False,
                    "temperature": 0.7
                }
            )
            
            if response.status_code != 200:
                print(f"❌ API Request Failed: {response.status_code}")
                print(response.text)
                return

            data = response.json()
            model_responses = data.get("model_responses", [])
            
            groq_found = False
            gemini_found = False
            
            print(f"\nReceived {len(model_responses)} responses:")
            
            for resp in model_responses:
                provider = resp.get("provider")
                model = resp.get("model_name")
                text = resp.get("text", "").strip()[:50] + "..."
                error = resp.get("error")
                
                status = "✅ Success" if not error else f"❌ Failed: {error}"
                print(f"  - Provider: {provider:<10} | Model: {model:<25} | {status}")
                
                if provider == "groq" and not error:
                    groq_found = True
                if provider == "gemini" and not error:
                    gemini_found = True
            
            print("\nSummary:")
            if groq_found:
                print("  ✅ Groq is working")
            else:
                print("  ❌ Groq is NOT working")
                
            if gemini_found:
                print("  ✅ Gemini is working")
            else:
                print("  ❌ Gemini is NOT working")
                
        except httpx.ConnectError:
            print("❌ Could not connect to API. Is the server running?")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_providers())
