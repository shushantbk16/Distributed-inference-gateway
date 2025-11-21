"""Result verification logic."""
from typing import List
from src.models.response import ModelResponse, ExecutionResult
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Verifier:
    """Verify execution results and assess quality."""
    
    @staticmethod
    def verify_execution(execution_result: ExecutionResult) -> bool:
        """
        Verify if execution was successful.
        
        Args:
            execution_result: The execution result to verify
            
        Returns:
            True if execution was successful
        """
        return execution_result.success and execution_result.exit_code == 0
    
    @staticmethod
    def score_result(model_response: ModelResponse) -> float:
        """
        Score a model response based on execution results.
        
        Args:
            model_response: The model response to score
            
        Returns:
            Score from 0.0 to 1.0
        """
        if model_response.error:
            return 0.0
        
        if not model_response.execution_results:
            # No execution results - give partial credit
            return 0.5 if model_response.text else 0.0
        
        # Calculate success rate
        total = len(model_response.execution_results)
        successful = sum(
            1 for result in model_response.execution_results
            if Verifier.verify_execution(result)
        )
        
        base_score = successful / total if total > 0 else 0.0
        
        # Bonus for low latency (normalize to 0-0.2)
        latency_bonus = max(0, 0.2 - (model_response.latency / 100))
        
        return min(1.0, base_score + latency_bonus)
    
    @staticmethod
    def check_consensus(responses: List[ModelResponse]) -> bool:
        """
        Check if responses have consensus on outputs.
        
        Args:
            responses: List of model responses
            
        Returns:
            True if there's consensus
        """
        if len(responses) < 2:
            return False
        
        # Get successful execution outputs
        outputs = []
        for response in responses:
            for result in response.execution_results:
                if Verifier.verify_execution(result):
                    outputs.append(result.stdout.strip())
        
        if not outputs:
            return False
        
        # Check if all outputs are the same
        first_output = outputs[0]
        return all(output == first_output for output in outputs)
    
    @staticmethod
    def count_successful_executions(responses: List[ModelResponse]) -> tuple:
        """
        Count successful and total executions.
        
        Args:
            responses: List of model responses
            
        Returns:
            Tuple of (successful_count, total_count)
        """
        total = 0
        successful = 0
        
        for response in responses:
            for result in response.execution_results:
                total += 1
                if Verifier.verify_execution(result):
                    successful += 1
        
        return successful, total
