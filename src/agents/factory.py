"""
Agent factory for creating and executing specialized AI agents
"""

import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from ..exceptions import AgentExecutionError
from ..models import EvaluationState, OfferData, CandidateData
from .technical_skills import TechnicalSkillsAgent
from .career_trajectory import CareerTrajectoryAgent
from .cultural_fit import CulturalFitAgent
from .scoring import ScoringAgent
from .qa_validation import QAValidationAgent


logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory class for creating and managing LLM agents with structured outputs."""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self._technical_agent = TechnicalSkillsAgent(llm)
        self._trajectory_agent = CareerTrajectoryAgent(llm)
        self._cultural_agent = CulturalFitAgent(llm)
        self._scoring_agent = ScoringAgent(llm)
        self._qa_agent = QAValidationAgent(llm)
        logger.info(f"Initialized AgentFactory with model: {llm.model_name}")
    
    async def _execute_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[BaseModel],
        agent_name: str
    ) -> BaseModel:
        """
        Execute an agent with structured output using Pydantic schema.
        
        Args:
            system_prompt: System instructions for the agent
            user_prompt: User message with evaluation context
            output_schema: Pydantic model for structured output
            agent_name: Name of the agent for logging
            
        Returns:
            Parsed Pydantic model instance
            
        Raises:
            AgentExecutionError: If agent execution fails
        """
        try:
            logger.info(f"Executing {agent_name}...")
            
            # Create LLM with structured output
            structured_llm = self.llm.with_structured_output(output_schema)
            
            # Prepare messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Invoke LLM
            result = await structured_llm.ainvoke(messages)
            
            logger.info(f"{agent_name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"{agent_name} execution failed: {str(e)}")
            raise AgentExecutionError(f"{agent_name} failed: {str(e)}") from e
    
    async def technical_skills_agent(self, state: EvaluationState) -> dict[str, Any]:
        """Agent 1: Technical Skills Evaluator"""
        return await self._technical_agent.evaluate(state, self._execute_agent)
    
    async def career_trajectory_agent(self, state: EvaluationState) -> dict[str, Any]:
        """Agent 2: Career Trajectory Evaluator"""
        return await self._trajectory_agent.evaluate(state, self._execute_agent)
    
    async def cultural_fit_agent(self, state: EvaluationState) -> dict[str, Any]:
        """Agent 3: Cultural Fit Evaluator"""
        return await self._cultural_agent.evaluate(state, self._execute_agent)
    
    async def scoring_agent(self, state: EvaluationState) -> dict[str, Any]:
        """Agent 4: Scoring & Decision Agent"""
        return await self._scoring_agent.evaluate(state, self._execute_agent)
    
    async def qa_validation_agent(self, state: EvaluationState) -> dict[str, Any]:
        """Agent 5: QA Validation Agent"""
        return await self._qa_agent.evaluate(state, self._execute_agent)

