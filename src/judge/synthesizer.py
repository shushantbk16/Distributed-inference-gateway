"""Result synthesis logic."""
from typing import List, Optional
from src.models.response import ModelResponse, VerificationReport
from src.judge.verifier import Verifier
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Synthesizer:
    """Synthesize final response from multiple model responses."""
    
    @staticmethod
    def synthesize(
        responses: List[ModelResponse],
        verify: bool = True
    ) -> tuple[Optional[ModelResponse], VerificationReport]:
        """
        Synthesize the best response from multiple models.
        
        Args:
            responses: List of model responses
            verify: Whether to verify execution results
            
        Returns:
            Tuple of (selected_response, verification_report)
        """
        if not responses:
            logger.warning("No responses to synthesize")
            return None, VerificationReport(
                verified=False,
                consensus=False,
                successful_executions=0,
                total_executions=0,
                synthesis_strategy="no_responses",
                details={"error": "No responses available"}
            )
        
        # Count successful executions
        successful, total = Verifier.count_successful_executions(responses)
        
        # Check for consensus
        has_consensus = Verifier.check_consensus(responses)
        
        # Score all responses
        scored_responses = [
            (response, Verifier.score_result(response))
            for response in responses
        ]
        
        # Sort by score (highest first)
        scored_responses.sort(key=lambda x: x[1], reverse=True)
        
        # Log scores
        for response, score in scored_responses:
            logger.info(
                f"Model {response.provider}/{response.model_name} scored {score:.2f}"
            )
        
        # Select best response
        selected_response, best_score = scored_responses[0]
        
        # Determine synthesis strategy
        if has_consensus:
            strategy = "consensus"
        elif best_score >= 0.8:
            strategy = "high_confidence"
        elif best_score >= 0.5:
            strategy = "best_available"
        else:
            strategy = "fallback"
        
        logger.info(f"Selected response using strategy: {strategy}")
        
        # Create verification report
        verification_report = VerificationReport(
            verified=verify and successful > 0,
            consensus=has_consensus,
            successful_executions=successful,
            total_executions=total,
            synthesis_strategy=strategy,
            details={
                "best_score": best_score,
                "selected_provider": selected_response.provider,
                "selected_model": selected_response.model_name,
                "scores": {
                    f"{r.provider}/{r.model_name}": s
                    for r, s in scored_responses
                }
            }
        )
        
        return selected_response, verification_report
    
    @staticmethod
    def create_summary(
        responses: List[ModelResponse],
        verification: VerificationReport
    ) -> str:
        """
        Create a human-readable summary of the synthesis.
        
        Args:
            responses: List of model responses
            verification: Verification report
            
        Returns:
            Summary string
        """
        summary_parts = []
        
        summary_parts.append(
            f"Received {len(responses)} response(s) from LLM providers"
        )
        
        if verification.total_executions > 0:
            summary_parts.append(
                f"Executed {verification.total_executions} code block(s): "
                f"{verification.successful_executions} successful"
            )
        
        if verification.consensus:
            summary_parts.append("Models reached consensus on output")
        
        summary_parts.append(
            f"Selected response using '{verification.synthesis_strategy}' strategy"
        )
        
        return ". ".join(summary_parts) + "."
