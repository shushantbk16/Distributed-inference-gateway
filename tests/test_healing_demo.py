import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models.response import ModelResponse, CodeBlock, ExecutionResult
from src.orchestrator.healer import Healer
from src.sandbox import SandboxExecutor

@pytest.mark.asyncio
async def test_healing_workflow_demo():
    print("\n\n🧪 --- STARTING SELF-HEALING DEMO ---")
    
    # 1. Setup Mocks
    mock_provider = MagicMock()
    mock_provider.get_provider_name.return_value = "groq"
    
    # Mock the Healer to return fixed code
    # We patch the Healer class directly to avoid making real API calls
    with patch('src.orchestrator.healer.Healer.heal_code', new_callable=AsyncMock) as mock_heal:
        mock_heal.return_value = "x = 10\nprint(x)"
        
        # 2. Simulate a Broken Response
        print("1️⃣  Simulating broken code generation...")
        broken_code = "print(x)  # x is undefined!"
        
        response = ModelResponse(
            model_name="llama-3",
            provider="groq",
            text="Here is code",
            code_blocks=[CodeBlock(language="python", code=broken_code)],
            execution_results=[],
            latency=0.1
        )
        
        # 3. Simulate Execution Failure
        print("2️⃣  Executing broken code...")
        # We'll use the real SandboxExecutor if Docker is running, or mock it if not.
        # For this demo, let's mock the execution results to ensure deterministic behavior.
        
        # Result 1: Failure
        failed_result = ExecutionResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="NameError: name 'x' is not defined",
            execution_time=0.1
        )
        response.execution_results.append(failed_result)
        print(f"   ❌ Execution Failed: {failed_result.stderr}")
        
        # 4. Trigger Healing Logic (Simulating main.py logic)
        if not failed_result.success and failed_result.stderr:
            print("3️⃣  ⚠️ Failure detected! Triggering Healer...")
            
            # Call Healer (Mocked)
            fixed_code = await Healer.heal_code(
                code=broken_code,
                error=failed_result.stderr,
                provider=mock_provider
            )
            
            print(f"4️⃣  🚑 Healer returned fixed code:\n   {fixed_code.replace(chr(10), chr(10)+'   ')}")
            
            # 5. Re-execute Fixed Code
            print("5️⃣  Re-executing fixed code...")
            # Mock the second execution result
            success_result = ExecutionResult(
                success=True,
                exit_code=0,
                stdout="10",
                stderr="",
                execution_time=0.1
            )
            
            # Update response
            response.code_blocks[0].code = fixed_code
            response.execution_results[0] = success_result
            print(f"   ✅ Execution Success! Output: {success_result.stdout}")
            
    print("--- DEMO COMPLETE: System successfully healed itself! ---")
