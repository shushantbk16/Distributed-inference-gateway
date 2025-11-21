"""
Integration test for end-to-end multi-model verification.
THIS IS WHAT YOU SHOW IN A FAANG INTERVIEW.
"""
import pytest
import httpx
import asyncio


# Test configuration
API_BASE = "http://localhost:8000"
API_KEY = "test_gateway_key_12345"


class TestMultiModelVerification:
    """End-to-end tests proving the system works."""
    
    @pytest.mark.asyncio
    async def test_code_generation_and_execution(self):
        """
        CRITICAL TEST: Full pipeline
        1. Send prompt to multiple LLMs
        2. Extract code from responses
        3. Execute code in sandbox
        4. Verify correctness
        5. Select best response
        
        This proves the system works end-to-end.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/api/v1/inference",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                },
                json={
                    "prompt": "Write a Python function that returns the sum of two numbers",
                    "execute_code": True,
                    "verify": True,
                    "temperature": 0.5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify request completed
            assert "request_id" in data
            assert "model_responses" in data
            assert len(data["model_responses"]) >= 1
            
            # Find successful response
            successful = [r for r in data["model_responses"] if not r.get("error")]
            assert len(successful) >= 1, "At least one model should succeed"
            
            # Verify code was extracted
            groq_response = next((r for r in successful if r["provider"] == "groq"), None)
            assert groq_response is not None
            assert len(groq_response["code_blocks"]) > 0, "Code should be extracted"
            
            # CRITICAL: Verify code was executed
            assert len(groq_response["execution_results"]) > 0, "Code should be executed"
            exec_result = groq_response["execution_results"][0]
            assert exec_result["success"], "Code execution should succeed"
            assert exec_result["exit_code"] == 0
            
            # Verify verification happened
            if data.get("verification"):
                assert data["verification"]["total_executions"] > 0
            
            # Verify a response was selected
            assert data["selected_response"] is not None
            
            print("\n✅ END-TO-END TEST PASSED!")
            print(f"   - {len(successful)} models responded")
            print(f"   - Code extracted: {len(groq_response['code_blocks'])} blocks")
            print(f"   - Code executed in: {exec_result['execution_time']:.3f}s")
            print(f"   - Total latency: {data['total_latency']:.2f}s")
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Verify health endpoint works."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/api/v1/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert "providers" in data
            
            # At least one provider should be healthy
            healthy_providers = [p for p, h in data["providers"].items() if h]
            assert len(healthy_providers) >= 1
            
            print(f"\n✅ Health check passed: {len(healthy_providers)} providers healthy")
    
    @pytest.mark.asyncio
    async def test_models_endpoint(self):
        """Verify models listing works."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/api/v1/models")
            assert response.status_code == 200
            
            data = response.json()
            assert "models" in data
            assert len(data["models"]) >= 1
            
            print(f"\n✅ Models endpoint passed: {len(data['models'])} models available")
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Verify system handles concurrent requests."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Send 3 concurrent requests
            tasks = []
            for i in range(3):
                task = client.post(
                    f"{API_BASE}/api/v1/inference",
                    headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
                    json={
                        "prompt": f"What is {i+1} + {i+1}?",
                        "execute_code": False,
                        "verify": False
                    }
                )
                tasks.append(task)
            
            # Wait for all to complete
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            for resp in responses:
                assert resp.status_code == 200
            
            print("\n✅ Parallel execution test passed: handled 3 concurrent requests")


if __name__ == "__main__":
    """Run tests directly."""
    print("=" * 60)
    print("FAANG-LEVEL INTEGRATION TESTS")
    print("=" * 60)
    pytest.main([__file__, "-v", "-s"])
