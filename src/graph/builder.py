"""
LangGraph workflow builder for the evaluation pipeline
"""

import logging
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models import EvaluationState


logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builder class for constructing the LangGraph evaluation workflow."""
    
    def __init__(self, agent_factory):
        self.agent_factory = agent_factory
        logger.info("Initialized GraphBuilder")
    
    def build_graph(self) -> Any:
        """
        Build and compile the LangGraph workflow.
        
        Graph Structure:
        1. START -> Parallel Execution of 3 Evaluators
        2. Evaluators -> Scoring Agent
        3. Scoring Agent -> QA Validation Agent
        4. QA Validation -> END
        
        Returns:
            Compiled LangGraph workflow
        """
        logger.info("Building LangGraph workflow...")
        
        # Create StateGraph with EvaluationState
        workflow = StateGraph(EvaluationState)
        
        # Add evaluation agent nodes
        workflow.add_node("technical_agent", self._wrap_node(self.agent_factory.technical_skills_agent))
        workflow.add_node("trajectory_agent", self._wrap_node(self.agent_factory.career_trajectory_agent))
        workflow.add_node("cultural_agent", self._wrap_node(self.agent_factory.cultural_fit_agent))
        
        # Add finalizer agent nodes
        workflow.add_node("scoring_agent", self._wrap_node(self.agent_factory.scoring_agent))
        workflow.add_node("qa_agent", self._wrap_node(self.agent_factory.qa_validation_agent))
        
        # Define edges - sequential evaluation (could be parallel in future)
        workflow.set_entry_point("technical_agent")
        workflow.add_edge("technical_agent", "trajectory_agent")
        workflow.add_edge("trajectory_agent", "cultural_agent")
        
        # Sequential finalizers
        workflow.add_edge("cultural_agent", "scoring_agent")
        workflow.add_edge("scoring_agent", "qa_agent")
        workflow.add_edge("qa_agent", END)
        
        # Compile graph with memory checkpointer
        compiled_graph = workflow.compile(checkpointer=MemorySaver())
        
        logger.info("LangGraph workflow compiled successfully")
        return compiled_graph
    
    def _wrap_node(self, agent_func):
        """Wrap agent function to handle state updates properly."""
        async def wrapped(state):
            # LangGraph passes EvaluationState instance when using StateGraph(EvaluationState)
            if isinstance(state, dict):
                state_obj = EvaluationState(**state)
            else:
                # State is already an EvaluationState instance
                state_obj = state
            
            # Call agent function
            updates = await agent_func(state_obj)
            
            # Return dict updates for LangGraph to merge
            return updates
        return wrapped

