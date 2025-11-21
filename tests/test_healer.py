import pytest
from unittest.mock import AsyncMock, MagicMock
from src.orchestrator.healer import Healer
from src.providers.base import BaseLLMProvider

@pytest.mark.asyncio
async def test_heal_code_success():
    # Mock provider
    mock_provider = MagicMock(spec=BaseLLMProvider)
    mock_provider.get_provider_name.return_value = "mock_provider"
    
    # Mock response with fixed code
    mock_provider.generate_completion = AsyncMock(return_value={
        "text": "Here is the fixed code:\n```python\nprint('fixed')\n```"
    })
    
    broken_code = "print('broken')"
    error = "SyntaxError: unexpected EOF while parsing"
    
    fixed_code = await Healer.heal_code(broken_code, error, mock_provider)
    
    assert fixed_code == "print('fixed')"
    
    # Verify prompt contained error and broken code
    call_args = mock_provider.generate_completion.call_args[1]
    prompt = call_args["prompt"]
    assert broken_code in prompt
    assert error in prompt

@pytest.mark.asyncio
async def test_heal_code_failure():
    # Mock provider returning no code
    mock_provider = MagicMock(spec=BaseLLMProvider)
    mock_provider.get_provider_name.return_value = "mock_provider"
    mock_provider.generate_completion = AsyncMock(return_value={
        "text": "I cannot fix this."
    })
    
    fixed_code = await Healer.heal_code("code", "error", mock_provider)
    
    assert fixed_code is None
