"""Tests for judge logic."""
import pytest
from src.judge.verifier import Verifier
from src.judge.synthesizer import Synthesizer
from src.models.response import ModelResponse, ExecutionResult, CodeBlock
from datetime import datetime


def test_verify_execution_success():
    """Test verification of successful execution."""
    result = ExecutionResult(
        success=True,
        exit_code=0,
        stdout="120",
        stderr="",
        execution_time=0.5
    )
    
    assert Verifier.verify_execution(result) is True


def test_verify_execution_failure():
    """Test verification of failed execution."""
    result = ExecutionResult(
        success=False,
        exit_code=1,
        stdout="",
        stderr="Error",
        execution_time=0.5,
        error="Execution failed"
    )
    
    assert Verifier.verify_execution(result) is False


def test_score_result_with_success():
    """Test scoring with successful execution."""
    response = ModelResponse(
        model_name="test-model",
        provider="test",
        text="Test response",
        execution_results=[
            ExecutionResult(success=True, exit_code=0, stdout="output", stderr="", execution_time=0.5)
        ],
        latency=1.0,
        timestamp=datetime.utcnow()
    )
    
    score = Verifier.score_result(response)
    assert score > 0.8  # Should be high for successful execution


def test_score_result_with_failure():
    """Test scoring with failed execution."""
    response = ModelResponse(
        model_name="test-model",
        provider="test",
        text="Test response",
        execution_results=[
            ExecutionResult(success=False, exit_code=1, stdout="", stderr="error", execution_time=0.5, error="Failed")
        ],
        latency=1.0,
        timestamp=datetime.utcnow()
    )
    
    score = Verifier.score_result(response)
    assert score < 0.5  # Should be low for failed execution


def test_check_consensus_success():
    """Test consensus detection with matching outputs."""
    responses = [
        ModelResponse(
            model_name="model1",
            provider="provider1",
            text="text1",
            execution_results=[
                ExecutionResult(success=True, exit_code=0, stdout="120", stderr="", execution_time=0.5)
            ],
            latency=1.0,
            timestamp=datetime.utcnow()
        ),
        ModelResponse(
            model_name="model2",
            provider="provider2",
            text="text2",
            execution_results=[
                ExecutionResult(success=True, exit_code=0, stdout="120", stderr="", execution_time=0.6)
            ],
            latency=1.2,
            timestamp=datetime.utcnow()
        )
    ]
    
    assert Verifier.check_consensus(responses) is True


def test_check_consensus_failure():
    """Test consensus detection with different outputs."""
    responses = [
        ModelResponse(
            model_name="model1",
            provider="provider1",
            text="text1",
            execution_results=[
                ExecutionResult(success=True, exit_code=0, stdout="120", stderr="", execution_time=0.5)
            ],
            latency=1.0,
            timestamp=datetime.utcnow()
        ),
        ModelResponse(
            model_name="model2",
            provider="provider2",
            text="text2",
            execution_results=[
                ExecutionResult(success=True, exit_code=0, stdout="24", stderr="", execution_time=0.6)
            ],
            latency=1.2,
            timestamp=datetime.utcnow()
        )
    ]
    
    assert Verifier.check_consensus(responses) is False


def test_synthesize_with_consensus():
    """Test synthesis with consensus."""
    responses = [
        ModelResponse(
            model_name="model1",
            provider="provider1",
            text="text1",
            execution_results=[
                ExecutionResult(success=True, exit_code=0, stdout="result", stderr="", execution_time=0.5)
            ],
            latency=1.0,
            timestamp=datetime.utcnow()
        ),
        ModelResponse(
            model_name="model2",
            provider="provider2",
            text="text2",
            execution_results=[
                ExecutionResult(success=True, exit_code=0, stdout="result", stderr="", execution_time=0.5)
            ],
            latency=1.1,
            timestamp=datetime.utcnow()
        )
    ]
    
    selected, verification = Synthesizer.synthesize(responses, verify=True)
    
    assert selected is not None
    assert verification.consensus is True
    assert verification.synthesis_strategy == "consensus"


def test_synthesize_empty_responses():
    """Test synthesis with no responses."""
    selected, verification = Synthesizer.synthesize([], verify=True)
    
    assert selected is None
    assert verification.verified is False
    assert verification.synthesis_strategy == "no_responses"
