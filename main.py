"""
MAS-Eval: Multi-Agent System for Candidate Evaluation Microservice

A production-grade microservice using LangGraph to orchestrate 5 specialized AI agents
for candidate-offer compatibility evaluation.

Architecture:
- 3 Parallel Evaluation Agents: Technical Skills, Career Trajectory, Cultural Fit
- 2 Sequential Finalizer Agents: Scoring, QA Validation
- LangGraph State Management with Pydantic Models
- FastAPI REST API with Dependency Injection
- OpenAI GPT-4o-mini LLM Backend
"""

import logging
import sys
from typing import Annotated, Any, Literal, Optional, Sequence
from contextlib import asynccontextmanager
import asyncio

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# ============================================================================
# SECTION 1: CONFIGURATION & LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application configuration using pydantic-settings for type-safe environment variables."""
    
    openai_api_key: str = Field(..., description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    openai_temperature: float = Field(default=0.2, description="LLM temperature")
    log_level: str = Field(default="INFO", description="Logging level")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()
logger.setLevel(settings.log_level)


# ============================================================================
# SECTION 2: CUSTOM EXCEPTIONS
# ============================================================================

class MASEvalException(Exception):
    """Base exception for MAS-Eval microservice."""
    pass


class AgentExecutionError(MASEvalException):
    """Raised when an agent fails to execute properly."""
    pass


class InvalidInputDataError(MASEvalException):
    """Raised when input data validation fails."""
    pass


class GraphExecutionError(MASEvalException):
    """Raised when LangGraph execution fails."""
    pass


# ============================================================================
# SECTION 3: PYDANTIC DATA MODELS - INPUT STRUCTURES
# ============================================================================

class OfferData(BaseModel):
    """Pydantic model for Offer/Job data structure."""
    
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    contract: str = Field(..., description="Contract type (full-time, part-time, etc.)")
    type: str = Field(..., description="Work type: remote, on-site, hybrid")
    description: str = Field(..., description="Job description")
    salary_range: Optional[str] = Field(None, description="Salary range")
    responsibilities: str = Field(..., description="Key responsibilities")
    experience_required: str = Field(..., description="Required experience level")
    mandatory_skills: list[str] = Field(default_factory=list, description="Mandatory technical skills")
    nice_to_have_skills: list[str] = Field(default_factory=list, description="Nice-to-have skills")
    mandatory_languages: list[str] = Field(default_factory=list, description="Required languages")
    nice_to_have_languages: list[str] = Field(default_factory=list, description="Nice-to-have languages")
    preferred_companies: list[str] = Field(default_factory=list, description="Preferred previous companies")
    extra_requirements_to_consider: Optional[str] = Field(None, description="Additional requirements")


class Education(BaseModel):
    """Candidate education entry."""
    
    degree: str = Field(..., description="Degree type (Bachelor's, Master's, etc.)")
    name: str = Field(..., description="Field of study")
    institute: str = Field(..., description="Educational institution")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")


class Experience(BaseModel):
    """Candidate work experience entry."""
    
    role: str = Field(..., description="Job role/title")
    company: str = Field(..., description="Company name")
    description: str = Field(..., description="Role description and achievements")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")
    duration: Optional[str] = Field(None, description="Duration of employment")


class Skill(BaseModel):
    """Candidate skill with proficiency level."""
    
    name: str = Field(..., description="Skill name")
    level: Optional[str] = Field(None, description="Proficiency level")


class Language(BaseModel):
    """Candidate language with proficiency level."""
    
    name: str = Field(..., description="Language name")
    level: str = Field(..., description="Proficiency level (native, fluent, intermediate, basic)")


class CandidateData(BaseModel):
    """Pydantic model for Candidate data structure."""
    
    heading: str = Field(..., description="Professional headline/summary")
    experience_years: int = Field(..., description="Total years of professional experience")
    educations: list[Education] = Field(default_factory=list, description="Education history")
    experiences: list[Experience] = Field(default_factory=list, description="Work experience history")
    skills: list[Skill] = Field(default_factory=list, description="Technical and soft skills")
    languages: list[Language] = Field(default_factory=list, description="Language proficiencies")


class EvaluationRequest(BaseModel):
    """Main input model for the evaluation endpoint."""
    
    offer: OfferData = Field(..., description="Job offer data")
    candidate: CandidateData = Field(..., description="Candidate profile data")


# ============================================================================
# SECTION 4: PYDANTIC DATA MODELS - AGENT OUTPUTS & STATE
# ============================================================================

class ScoreOutput(BaseModel):
    """Structured output for evaluation agents."""
    
    score: int = Field(..., ge=0, le=100, description="Compatibility score (0-100)")
    reason: str = Field(..., description="Detailed reasoning for the score")
    
    @validator('score')
    def validate_score_range(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Score must be between 0 and 100')
        return v


class ScoringAgentOutput(BaseModel):
    """Output from the scoring agent with weighted final score."""
    
    final_score: int = Field(..., ge=0, le=100, description="Weighted compatibility score")
    liked: bool = Field(..., description="Binary decision: True if score >= 70")
    aggregated_reason: str = Field(..., description="Combined reasoning from all evaluators")


class QAAgentOutput(BaseModel):
    """Output from the QA validation agent."""
    
    qa_required_human_review: bool = Field(..., description="Flag for human review requirement")
    qa_note: Optional[str] = Field(None, description="QA validation note or concern")


class EvaluationState(BaseModel):
    """LangGraph state model tracking the evaluation process."""
    
    # Input data
    offer: OfferData
    candidate: CandidateData
    
    # Evaluation agent outputs
    technical_score: Optional[int] = None
    technical_reason: Optional[str] = None
    
    trajectory_score: Optional[int] = None
    trajectory_reason: Optional[str] = None
    
    cultural_score: Optional[int] = None
    cultural_reason: Optional[str] = None
    
    # Scoring agent output
    final_score: Optional[int] = None
    liked: Optional[bool] = None
    aggregated_reason: Optional[str] = None
    
    # QA agent output
    qa_required_human_review: Optional[bool] = None
    qa_note: Optional[str] = None
    
    # Metadata
    models_evaluated: int = Field(default=5, description="Total number of agents")
    models_liked: int = Field(default=5, description="Number of agents in agreement")
    
    class Config:
        arbitrary_types_allowed = True


class EvaluationResult(BaseModel):
    """Final output model for the evaluation API."""
    
    liked: bool = Field(..., description="Final binary decision")
    reason: str = Field(..., description="Final explanation prioritizing QA notes")
    compatibility: int = Field(..., ge=0, le=100, description="Final compatibility score")
    ai_swipe_reasons: list[str] = Field(..., description="All reasoning steps from agents")
    models_liked: int = Field(default=5, description="Number of models in agreement")
    models_evaluated: int = Field(default=5, description="Total models evaluated")
    qa_required_human_review: bool = Field(..., description="Human review flag")


# ============================================================================
# SECTION 5: AGENT IMPLEMENTATIONS
# ============================================================================

class AgentFactory:
    """Factory class for creating and managing LLM agents with structured outputs."""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
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
        """
        Agent 1: Technical Skills Evaluator
        Analyzes candidate's technical competencies against job requirements.
        Weight: 50% in final score.
        """
        system_prompt = """You are a **Technical Skills Evaluator** specialized in assessing technical competencies.

Your EXCLUSIVE focus areas:
- Match between candidate's technical skills and mandatory/nice-to-have skills
- Relevance of candidate's technical experience to the job role
- Depth and breadth of technical expertise
- Programming languages, frameworks, tools, and technologies

DO NOT evaluate:
- Company culture fit
- Career trajectory or job stability
- Soft skills or personality traits

Scoring guidelines:
- 90-100: Exceptional match - exceeds all technical requirements
- 70-89: Strong match - meets all mandatory + most nice-to-have skills
- 50-69: Moderate match - meets most mandatory skills
- 30-49: Weak match - gaps in mandatory skills
- 0-29: Poor match - significant technical gaps

Provide a score (0-100) and detailed reasoning focusing ONLY on technical aspects."""

        user_prompt = f"""Evaluate the technical compatibility between this candidate and job offer:

**JOB OFFER - {state.offer.job_title} at {state.offer.company_name}**

Technical Requirements:
- Mandatory Skills: {', '.join(state.offer.mandatory_skills) if state.offer.mandatory_skills else 'None specified'}
- Nice-to-Have Skills: {', '.join(state.offer.nice_to_have_skills) if state.offer.nice_to_have_skills else 'None specified'}
- Experience Required: {state.offer.experience_required}
- Responsibilities: {state.offer.responsibilities}

**CANDIDATE PROFILE**

Headline: {state.candidate.heading}
Experience: {state.candidate.experience_years} years

Technical Skills:
{chr(10).join([f"- {skill.name}" + (f" ({skill.level})" if skill.level else "") for skill in state.candidate.skills])}

Work Experience:
{chr(10).join([f"- {exp.role} at {exp.company}: {exp.description}" for exp in state.candidate.experiences[:3]])}

Evaluate the technical match and provide your assessment."""

        result = await self._execute_agent(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=ScoreOutput,
            agent_name="Technical Skills Agent"
        )
        
        return {
            "technical_score": result.score,
            "technical_reason": result.reason
        }
    
    async def career_trajectory_agent(self, state: EvaluationState) -> dict[str, Any]:
        """
        Agent 2: Career Trajectory Evaluator
        Analyzes candidate's career progression and experience relevance.
        Weight: 35% in final score.
        """
        system_prompt = """You are a **Career Trajectory Evaluator** specialized in assessing professional growth and experience relevance.

Your EXCLUSIVE focus areas:
- Career progression and growth trajectory
- Relevance of previous roles to the target position
- Company prestige and industry experience alignment
- Years of experience adequacy
- Job stability and consistency

DO NOT evaluate:
- Technical skills or specific technologies
- Cultural fit or personality traits
- Communication skills

Scoring guidelines:
- 90-100: Exceptional trajectory - clear upward progression, highly relevant experience
- 70-89: Strong trajectory - consistent growth, relevant industry experience
- 50-69: Moderate trajectory - some relevant experience, acceptable progression
- 30-49: Weak trajectory - limited relevant experience or unclear progression
- 0-29: Poor trajectory - mismatched experience or unstable history

Provide a score (0-100) and detailed reasoning focusing ONLY on career trajectory aspects."""

        user_prompt = f"""Evaluate the career trajectory compatibility between this candidate and job offer:

**JOB OFFER - {state.offer.job_title} at {state.offer.company_name}**

Position Context:
- Job Title: {state.offer.job_title}
- Company: {state.offer.company_name}
- Experience Required: {state.offer.experience_required}
- Contract: {state.offer.contract}
- Preferred Companies: {', '.join(state.offer.preferred_companies) if state.offer.preferred_companies else 'None specified'}

**CANDIDATE PROFILE**

Total Experience: {state.candidate.experience_years} years
Headline: {state.candidate.heading}

Work History:
{chr(10).join([f"{i+1}. {exp.role} at {exp.company} ({exp.duration if exp.duration else 'Duration not specified'}): {exp.description}" for i, exp in enumerate(state.candidate.experiences)])}

Education:
{chr(10).join([f"- {edu.degree} in {edu.name} from {edu.institute}" for edu in state.candidate.educations])}

Evaluate the career trajectory match and provide your assessment."""

        result = await self._execute_agent(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=ScoreOutput,
            agent_name="Career Trajectory Agent"
        )
        
        return {
            "trajectory_score": result.score,
            "trajectory_reason": result.reason
        }
    
    async def cultural_fit_agent(self, state: EvaluationState) -> dict[str, Any]:
        """
        Agent 3: Cultural Fit Evaluator
        Analyzes candidate's alignment with company culture and work style.
        Weight: 15% in final score.
        """
        system_prompt = """You are a **Cultural Fit Evaluator** specialized in assessing work style and organizational alignment.

Your EXCLUSIVE focus areas:
- Work environment preferences (remote/on-site/hybrid alignment)
- Language proficiency for communication requirements
- Company size and culture compatibility inferred from experience
- Contract type preferences (full-time/part-time/contract)
- Geographic and work style flexibility

DO NOT evaluate:
- Technical skills or technologies
- Career progression or experience level
- Specific project achievements

Scoring guidelines:
- 90-100: Exceptional fit - perfect alignment with work style and culture
- 70-89: Strong fit - compatible preferences and communication ability
- 50-69: Moderate fit - acceptable alignment with minor concerns
- 30-49: Weak fit - some cultural or logistical misalignment
- 0-29: Poor fit - significant cultural or practical incompatibility

Provide a score (0-100) and detailed reasoning focusing ONLY on cultural fit aspects."""

        user_prompt = f"""Evaluate the cultural fit between this candidate and job offer:

**JOB OFFER - {state.offer.job_title} at {state.offer.company_name}**

Work Environment:
- Company: {state.offer.company_name}
- Work Type: {state.offer.type}
- Contract: {state.offer.contract}
- Mandatory Languages: {', '.join(state.offer.mandatory_languages) if state.offer.mandatory_languages else 'None specified'}
- Nice-to-Have Languages: {', '.join(state.offer.nice_to_have_languages) if state.offer.nice_to_have_languages else 'None specified'}
- Description: {state.offer.description[:300]}...

**CANDIDATE PROFILE**

Languages:
{chr(10).join([f"- {lang.name}: {lang.level}" for lang in state.candidate.languages])}

Work History Context:
{chr(10).join([f"- {exp.role} at {exp.company}" for exp in state.candidate.experiences[:5]])}

Total Experience: {state.candidate.experience_years} years

Evaluate the cultural and work style compatibility and provide your assessment."""

        result = await self._execute_agent(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=ScoreOutput,
            agent_name="Cultural Fit Agent"
        )
        
        return {
            "cultural_score": result.score,
            "cultural_reason": result.reason
        }
    
    async def scoring_agent(self, state: EvaluationState) -> dict[str, Any]:
        """
        Agent 4: Scoring & Decision Agent
        Applies weighted scoring formula and makes binary decision.
        
        Weights:
        - Technical Skills: 50%
        - Career Trajectory: 35%
        - Cultural Fit: 15%
        
        Decision Rule: liked = True if final_score >= 70
        """
        system_prompt = """You are a **Scoring & Decision Agent** responsible for calculating the final compatibility score.

Your task:
1. Apply weighted scoring formula: (Technical × 0.50) + (Trajectory × 0.35) + (Cultural × 0.15)
2. Calculate the final score (0-100)
3. Make binary decision: LIKED if score >= 70, REJECTED if score < 70
4. Synthesize all reasoning into a cohesive explanation

The formula weights reflect business priorities:
- Technical competency is most critical (50%)
- Career fit is important but secondary (35%)
- Cultural alignment is a supporting factor (15%)

Provide the exact weighted score, binary decision, and comprehensive aggregated reasoning."""

        user_prompt = f"""Calculate the final compatibility score using the weighted formula:

**EVALUATION SCORES:**
- Technical Skills: {state.technical_score}/100 (Weight: 50%)
- Career Trajectory: {state.trajectory_score}/100 (Weight: 35%)
- Cultural Fit: {state.cultural_score}/100 (Weight: 15%)

**REASONING FROM EVALUATORS:**

Technical Skills Assessment:
{state.technical_reason}

Career Trajectory Assessment:
{state.trajectory_reason}

Cultural Fit Assessment:
{state.cultural_reason}

Calculate: Final Score = ({state.technical_score} × 0.50) + ({state.trajectory_score} × 0.35) + ({state.cultural_score} × 0.15)
Decision: LIKED if Final Score >= 70, REJECTED otherwise

Provide the final weighted score, decision, and synthesized reasoning."""

        result = await self._execute_agent(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=ScoringAgentOutput,
            agent_name="Scoring Agent"
        )
        
        return {
            "final_score": result.final_score,
            "liked": result.liked,
            "aggregated_reason": result.aggregated_reason
        }
    
    async def qa_validation_agent(self, state: EvaluationState) -> dict[str, Any]:
        """
        Agent 5: QA Validation Agent
        Detects critical inconsistencies requiring human review.
        
        Inconsistency Detection Rules:
        1. Final Score >= 70 (LIKED) but Technical Score < 50
        2. Final Score < 70 (REJECTED) but ALL THREE evaluator scores > 80
        """
        system_prompt = """You are a **QA Validation Agent** responsible for detecting critical inconsistencies in the evaluation.

Your task is to identify situations requiring human review:

**CRITICAL INCONSISTENCY RULE 1:**
If Final Score >= 70 (LIKED) BUT Technical Skills Score < 50:
→ Flag for human review (qa_required_human_review = True)
→ Reason: Candidate lacks fundamental technical competency despite passing overall

**CRITICAL INCONSISTENCY RULE 2:**
If Final Score < 70 (REJECTED) BUT ALL THREE evaluator scores > 80:
→ Flag for human review (qa_required_human_review = True)
→ Reason: All evaluators scored highly but weighted formula rejected - potential edge case

If no critical inconsistencies detected:
→ qa_required_human_review = False
→ qa_note = "No critical inconsistencies detected. Evaluation validated."

Analyze the scores and make your determination."""

        user_prompt = f"""Perform QA validation on this evaluation:

**EVALUATION RESULTS:**
- Technical Skills Score: {state.technical_score}/100
- Career Trajectory Score: {state.trajectory_score}/100
- Cultural Fit Score: {state.cultural_score}/100
- Final Weighted Score: {state.final_score}/100
- Decision: {"LIKED" if state.liked else "REJECTED"}

**INCONSISTENCY CHECK:**

Rule 1: Is Final Score >= 70 AND Technical Score < 50?
- Final Score >= 70: {state.final_score >= 70}
- Technical Score < 50: {state.technical_score < 50}
- Rule 1 Triggered: {state.final_score >= 70 and state.technical_score < 50}

Rule 2: Is Final Score < 70 AND all three scores > 80?
- Final Score < 70: {state.final_score < 70}
- All scores > 80: {state.technical_score > 80 and state.trajectory_score > 80 and state.cultural_score > 80}
- Rule 2 Triggered: {state.final_score < 70 and state.technical_score > 80 and state.trajectory_score > 80 and state.cultural_score > 80}

Determine if human review is required and provide your QA note."""

        result = await self._execute_agent(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=QAAgentOutput,
            agent_name="QA Validation Agent"
        )
        
        return {
            "qa_required_human_review": result.qa_required_human_review,
            "qa_note": result.qa_note
        }


# ============================================================================
# SECTION 6: LANGGRAPH WORKFLOW BUILDER
# ============================================================================

class GraphBuilder:
    """Builder class for constructing the LangGraph evaluation workflow."""
    
    def __init__(self, agent_factory: AgentFactory):
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
        
        # Define edges - parallel evaluation
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
        async def wrapped(state: dict) -> dict:
            # Convert dict to Pydantic model
            state_obj = EvaluationState(**state)
            # Call agent function
            updates = await agent_func(state_obj)
            # Return dict updates
            return updates
        return wrapped


# ============================================================================
# SECTION 7: GRAPH EXECUTOR & RESULT BUILDER
# ============================================================================

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
            
            # Initialize state as dict
            initial_state = {
                "offer": request.offer,
                "candidate": request.candidate,
                "technical_score": None,
                "technical_reason": None,
                "trajectory_score": None,
                "trajectory_reason": None,
                "cultural_score": None,
                "cultural_reason": None,
                "final_score": None,
                "liked": None,
                "aggregated_reason": None,
                "qa_required_human_review": None,
                "qa_note": None,
                "models_evaluated": 5,
                "models_liked": 5
            }
            
            # Execute graph
            config = {"configurable": {"thread_id": "evaluation_001"}}
            final_state_dict = await self.graph.ainvoke(initial_state, config)
            
            # Convert result dict to Pydantic model
            final_state = EvaluationState(**final_state_dict)
            
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


# ============================================================================
# SECTION 8: DEPENDENCY INJECTION & RESOURCE MANAGEMENT
# ============================================================================

class DependencyContainer:
    """Container for managing application dependencies."""
    
    def __init__(self):
        self.llm: Optional[ChatOpenAI] = None
        self.agent_factory: Optional[AgentFactory] = None
        self.graph: Optional[Any] = None
        self.evaluation_service: Optional[EvaluationService] = None
    
    async def initialize(self):
        """Initialize all dependencies."""
        logger.info("Initializing application dependencies...")
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key
        )
        logger.info(f"LLM initialized: {settings.openai_model}")
        
        # Initialize agent factory
        self.agent_factory = AgentFactory(self.llm)
        
        # Build graph
        graph_builder = GraphBuilder(self.agent_factory)
        self.graph = graph_builder.build_graph()
        
        # Initialize evaluation service
        self.evaluation_service = EvaluationService(self.graph)
        
        logger.info("All dependencies initialized successfully")
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up application resources...")
        # Add cleanup logic if needed


# Global dependency container
container = DependencyContainer()


# ============================================================================
# SECTION 9: FASTAPI APPLICATION & ENDPOINTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup
    await container.initialize()
    logger.info("FastAPI application startup complete")
    
    yield
    
    # Shutdown
    await container.cleanup()
    logger.info("FastAPI application shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="MAS-Eval: Multi-Agent Candidate Evaluation System",
    description="AI-powered candidate evaluation microservice using LangGraph",
    version="1.0.0",
    lifespan=lifespan
)


def get_evaluation_service() -> EvaluationService:
    """Dependency injection for EvaluationService."""
    if container.evaluation_service is None:
        raise HTTPException(
            status_code=503,
            detail="Evaluation service not initialized"
        )
    return container.evaluation_service


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mas-eval",
        "version": "1.0.0"
    }


@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_candidate(
    request: EvaluationRequest,
    service: EvaluationService = Depends(get_evaluation_service)
) -> EvaluationResult:
    """
    Main evaluation endpoint.
    
    Receives offer and candidate data, executes the multi-agent workflow,
    and returns the evaluation result with compatibility score and decision.
    """
    try:
        result = await service.evaluate(request)
        return result
        
    except InvalidInputDataError as e:
        logger.error(f"Invalid input data: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except (AgentExecutionError, GraphExecutionError) as e:
        logger.error(f"Evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )


# ============================================================================
# SECTION 10: MOCK DATA & TEST EXECUTION
# ============================================================================

def create_mock_data() -> EvaluationRequest:
    """Create high-fidelity mock data for testing the evaluation workflow."""
    
    mock_offer = OfferData(
        job_title="Senior Full-Stack Developer",
        company_name="TechCorp Innovation Labs",
        contract="full-time",
        type="hybrid",
        description="We are seeking an experienced Full-Stack Developer to join our innovative team building next-generation SaaS platforms. The ideal candidate will have strong expertise in modern web technologies, cloud architecture, and agile methodologies.",
        salary_range="€60,000 - €80,000",
        responsibilities="Design and develop scalable web applications, lead technical architecture decisions, mentor junior developers, collaborate with product teams, implement CI/CD pipelines, ensure code quality and best practices.",
        experience_required="5+ years of professional software development experience",
        mandatory_skills=["Python", "React", "Node.js", "PostgreSQL", "AWS", "Docker", "REST APIs"],
        nice_to_have_skills=["TypeScript", "GraphQL", "Kubernetes", "Redis", "Microservices", "LangChain"],
        mandatory_languages=["English", "Spanish"],
        nice_to_have_languages=["German"],
        preferred_companies=["Google", "Amazon", "Microsoft", "Meta", "Startup experience"],
        extra_requirements_to_consider="Experience with AI/ML integration is a plus. Must be comfortable with remote collaboration and agile workflows."
    )
    
    mock_candidate = CandidateData(
        heading="Senior Full-Stack Engineer | Python & React Specialist | Cloud Architecture",
        experience_years=7,
        educations=[
            Education(
                degree="Master of Science",
                name="Computer Science",
                institute="Universidad Politécnica de Madrid",
                start_date="2014",
                end_date="2016"
            ),
            Education(
                degree="Bachelor of Science",
                name="Software Engineering",
                institute="Universidad Complutense de Madrid",
                start_date="2010",
                end_date="2014"
            )
        ],
        experiences=[
            Experience(
                role="Senior Full-Stack Developer",
                company="InnovateTech Solutions",
                description="Led development of cloud-based SaaS platform using Python/Django, React, and AWS. Architected microservices infrastructure with Docker and Kubernetes. Implemented CI/CD pipelines reducing deployment time by 60%. Mentored team of 4 junior developers.",
                start_date="2020-03",
                end_date="2024-10",
                duration="4 years 7 months"
            ),
            Experience(
                role="Full-Stack Developer",
                company="Digital Ventures Startup",
                description="Built and maintained multiple web applications using Python Flask, React, and PostgreSQL. Integrated third-party APIs and payment gateways. Worked in fast-paced agile environment with 2-week sprints. Reduced page load times by 40% through optimization.",
                start_date="2018-01",
                end_date="2020-02",
                duration="2 years 1 month"
            ),
            Experience(
                role="Junior Software Developer",
                company="WebDev Consulting",
                description="Developed frontend components with React and backend APIs with Node.js. Participated in code reviews and learned best practices. Worked with MongoDB and MySQL databases. Contributed to 15+ client projects.",
                start_date="2016-06",
                end_date="2017-12",
                duration="1 year 6 months"
            )
        ],
        skills=[
            Skill(name="Python", level="Expert"),
            Skill(name="React", level="Expert"),
            Skill(name="Node.js", level="Advanced"),
            Skill(name="PostgreSQL", level="Advanced"),
            Skill(name="AWS", level="Advanced"),
            Skill(name="Docker", level="Advanced"),
            Skill(name="TypeScript", level="Intermediate"),
            Skill(name="GraphQL", level="Intermediate"),
            Skill(name="Kubernetes", level="Intermediate"),
            Skill(name="REST APIs", level="Expert"),
            Skill(name="CI/CD", level="Advanced"),
            Skill(name="Microservices", level="Advanced"),
            Skill(name="Git", level="Expert"),
            Skill(name="Agile/Scrum", level="Advanced")
        ],
        languages=[
            Language(name="Spanish", level="native"),
            Language(name="English", level="fluent"),
            Language(name="French", level="intermediate")
        ]
    )
    
    return EvaluationRequest(offer=mock_offer, candidate=mock_candidate)


async def test_evaluation_workflow():
    """Test the complete evaluation workflow with mock data."""
    logger.info("=" * 80)
    logger.info("TESTING MAS-EVAL WORKFLOW WITH MOCK DATA")
    logger.info("=" * 80)
    
    try:
        # Initialize dependencies
        await container.initialize()
        
        # Create mock data
        mock_request = create_mock_data()
        
        logger.info(f"\n📋 EVALUATING:")
        logger.info(f"   Position: {mock_request.offer.job_title}")
        logger.info(f"   Company: {mock_request.offer.company_name}")
        logger.info(f"   Candidate: {mock_request.candidate.heading}")
        logger.info(f"   Experience: {mock_request.candidate.experience_years} years\n")
        
        # Execute evaluation
        result = await container.evaluation_service.evaluate(mock_request)
        
        # Display results
        logger.info("=" * 80)
        logger.info("🎯 EVALUATION RESULTS")
        logger.info("=" * 80)
        logger.info(f"\n✅ Decision: {'LIKED ❤️' if result.liked else 'REJECTED ❌'}")
        logger.info(f"📊 Compatibility Score: {result.compatibility}/100")
        logger.info(f"⚠️  Human Review Required: {'YES' if result.qa_required_human_review else 'NO'}")
        logger.info(f"\n📝 Final Reason:\n{result.reason}\n")
        logger.info(f"🤖 Agent Evaluations:")
        for i, reason in enumerate(result.ai_swipe_reasons, 1):
            logger.info(f"\n{i}. {reason}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 80 + "\n")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}", exc_info=True)
        raise


# ============================================================================
# SECTION 11: MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run test first
    logger.info("Starting test execution before launching server...")
    asyncio.run(test_evaluation_workflow())
    
    # Launch FastAPI server
    logger.info("\n🚀 Launching FastAPI server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )
