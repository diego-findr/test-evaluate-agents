"""
Evaluation service for executing the workflow and building results
"""

import logging
from typing import Any

from ..models import EvaluationRequest, EvaluationResult, EvaluationState
from ..exceptions import GraphExecutionError


logger = logging.getLogger(__name__)


class EvaluationService:
    """Service class for executing the evaluation workflow and building results."""
    
    def __init__(self, graph: Any):
        self.graph = graph
        logger.info("Initialized EvaluationService")
    
    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """
        Execute the complete evaluation workflow.
        
        Args:
            request: EvaluationRequest with offer and candidate data
            
        Returns:
            EvaluationResult with final decision and reasoning
            
        Raises:
            GraphExecutionError: If workflow execution fails
        """
        try:
            logger.info(f"Starting evaluation for {request.offer.job_title} at {request.offer.company_name}")
            
            # Initialize state as EvaluationState instance
            # Convert Pydantic models to dicts for LangGraph compatibility
            initial_state = EvaluationState(
                offer=request.offer.model_dump(),
                candidate=request.candidate.model_dump()
            )
            
            # Execute graph
            config = {"configurable": {"thread_id": "evaluation_001"}}
            final_state = await self.graph.ainvoke(initial_state, config)
            
            # Convert dict result to EvaluationState if needed
            if isinstance(final_state, dict):
                final_state = EvaluationState(**final_state)
            
            # Build result
            result = self._build_result(final_state)
            
            logger.info(f"Evaluation completed: {'LIKED' if result.liked else 'REJECTED'} (Score: {result.compatibility})")
            return result
            
        except Exception as e:
            logger.error(f"Evaluation workflow failed: {str(e)}")
            raise GraphExecutionError(f"Workflow execution failed: {str(e)}") from e
    
    def _build_result(self, state: EvaluationState) -> EvaluationResult:
        """
        Build the final EvaluationResult from completed state.
        
        Prioritizes QA note in the final reason if human review is required.
        """
        # Collect all reasoning steps
        ai_swipe_reasons = [
            f"Technical Skills ({state.technical_score}/100): {state.technical_reason}",
            f"Career Trajectory ({state.trajectory_score}/100): {state.trajectory_reason}",
            f"Cultural Fit ({state.cultural_score}/100): {state.cultural_reason}"
        ]
        
        # Add QA note if present
        if state.qa_note:
            ai_swipe_reasons.append(f"QA Validation: {state.qa_note}")
        
        # Prioritize QA note in final reason if human review required
        if state.qa_required_human_review and state.qa_note:
            final_reason = f"⚠️ HUMAN REVIEW REQUIRED: {state.qa_note}\n\nAggregated Assessment: {state.aggregated_reason}"
        else:
            final_reason = state.aggregated_reason
        
        return EvaluationResult(
            liked=state.liked,
            reason=final_reason,
            compatibility=state.final_score,
            ai_swipe_reasons=ai_swipe_reasons,
            models_liked=state.models_liked,
            models_evaluated=state.models_evaluated,
            qa_required_human_review=state.qa_required_human_review
        )

