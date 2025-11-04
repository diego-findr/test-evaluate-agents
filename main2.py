"""
Candidate Evaluation System using LangGraph
A simplified multi-agent system for candidate-offer compatibility evaluation.
"""

import logging
import sys
from typing import Annotated, List, Optional
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver

# ============================================================================
# CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application configuration"""
    openai_api_key: str = Field(..., description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model")
    openai_temperature: float = Field(default=0.2, description="LLM temperature")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()

# ============================================================================
# DATA MODELS
# ============================================================================

class OfferData(BaseModel):
    """Job offer structure"""
    job_title: str
    company_name: str
    contract: str
    type: str
    description: str
    salary_range: Optional[str] = None
    responsibilities: str
    experience_required: str
    mandatory_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)
    mandatory_languages: List[str] = Field(default_factory=list)
    nice_to_have_languages: List[str] = Field(default_factory=list)


class Education(BaseModel):
    """Candidate education"""
    degree: str
    name: str
    institute: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Experience(BaseModel):
    """Candidate experience"""
    role: str
    company: str
    description: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None


class Skill(BaseModel):
    """Candidate skill"""
    name: str
    level: Optional[str] = None


class Language(BaseModel):
    """Candidate language"""
    name: str
    level: str


class CandidateData(BaseModel):
    """Candidate profile"""
    heading: str
    experience_years: int
    educations: List[Education] = Field(default_factory=list)
    experiences: List[Experience] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    languages: List[Language] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    """Evaluation endpoint input"""
    offer: OfferData
    candidate: CandidateData


# ============================================================================
# STATE DEFINITION
# ============================================================================

class EvaluationState(MessagesState):
    """Graph state for evaluation workflow"""
    offer: OfferData
    candidate: CandidateData
    technical_score: Optional[int] = None
    technical_reason: Optional[str] = None
    trajectory_score: Optional[int] = None
    trajectory_reason: Optional[str] = None
    cultural_score: Optional[int] = None
    cultural_reason: Optional[str] = None
    final_score: Optional[int] = None
    liked: Optional[bool] = None
    aggregated_reason: Optional[str] = None
    qa_required_human_review: Optional[bool] = None
    qa_note: Optional[str] = None


# ============================================================================
# STRUCTURED OUTPUT SCHEMAS
# ============================================================================

class ScoreOutput(BaseModel):
    """Output for evaluation agents"""
    score: int = Field(..., ge=0, le=100, description="Score 0-100")
    reason: str = Field(..., description="Reasoning")


class ScoringOutput(BaseModel):
    """Output from scoring agent"""
    final_score: int = Field(..., ge=0, le=100)
    liked: bool
    aggregated_reason: str


class QAOutput(BaseModel):
    """Output from QA agent"""
    qa_required_human_review: bool
    qa_note: str


class EvaluationResult(BaseModel):
    """Final API response"""
    liked: bool
    reason: str
    compatibility: int = Field(..., ge=0, le=100)
    ai_swipe_reasons: List[str]
    models_liked: int = Field(default=5)
    models_evaluated: int = Field(default=5)
    qa_required_human_review: bool


# ============================================================================
# PROMPTS
# ============================================================================

TECHNICAL_PROMPT = """You are a Technical Skills Evaluator.

Evaluate the technical compatibility between candidate and job:

**JOB: {job_title} at {company_name}**
- Mandatory Skills: {mandatory_skills}
- Nice-to-Have Skills: {nice_to_have_skills}
- Experience Required: {experience_required}

**CANDIDATE**
- Experience: {experience_years} years
- Skills: {skills}
- Recent Work: {experiences}

Scoring:
- 90-100: Exceptional - exceeds all requirements
- 70-89: Strong - meets all mandatory + most nice-to-have
- 50-69: Moderate - meets most mandatory
- 30-49: Weak - gaps in mandatory skills
- 0-29: Poor - significant gaps

Provide score and detailed reasoning focusing ONLY on technical aspects."""

TRAJECTORY_PROMPT = """You are a Career Trajectory Evaluator.

Evaluate career progression and experience relevance:

**JOB: {job_title} at {company_name}**
- Experience Required: {experience_required}

**CANDIDATE**
- Total Experience: {experience_years} years
- Work History: {experiences}
- Education: {educations}

Scoring:
- 90-100: Exceptional trajectory - clear growth, highly relevant
- 70-89: Strong trajectory - consistent growth, relevant experience
- 50-69: Moderate trajectory - some relevant experience
- 30-49: Weak trajectory - limited relevant experience
- 0-29: Poor trajectory - mismatched experience

Provide score and reasoning focusing ONLY on career trajectory."""

CULTURAL_PROMPT = """You are a Cultural Fit Evaluator.

Evaluate work style and cultural alignment:

**JOB: {job_title} at {company_name}**
- Work Type: {work_type}
- Contract: {contract}
- Mandatory Languages: {mandatory_languages}

**CANDIDATE**
- Languages: {languages}
- Work History: {companies}

Scoring:
- 90-100: Exceptional fit - perfect alignment
- 70-89: Strong fit - compatible preferences
- 50-69: Moderate fit - acceptable alignment
- 30-49: Weak fit - some misalignment
- 0-29: Poor fit - significant incompatibility

Provide score and reasoning focusing ONLY on cultural fit."""

SCORING_PROMPT = """Calculate final compatibility score using weighted formula:

**SCORES:**
- Technical: {technical_score}/100 (Weight: 50%)
- Trajectory: {trajectory_score}/100 (Weight: 35%)
- Cultural: {cultural_score}/100 (Weight: 15%)

**REASONING:**
{reasoning}

Calculate: Final = (Technical × 0.50) + (Trajectory × 0.35) + (Cultural × 0.15)
Decision: LIKED if Final >= 70, REJECTED otherwise

Provide final score, decision, and synthesized reasoning."""

QA_PROMPT = """Perform QA validation:

**SCORES:**
- Technical: {technical_score}/100
- Trajectory: {trajectory_score}/100
- Cultural: {cultural_score}/100
- Final: {final_score}/100
- Decision: {decision}

**VALIDATION RULES:**
Rule 1: Flag if Final >= 70 AND Technical < 50 (lacks fundamental skills)
Rule 2: Flag if Final < 70 AND all three scores > 80 (potential edge case)

If flagged, set qa_required_human_review=True with explanation.
Otherwise, set qa_required_human_review=False."""


# ============================================================================
# GRAPH NODES
# ============================================================================

# Initialize LLM
llm = ChatOpenAI(model=settings.openai_model, temperature=settings.openai_temperature)


def evaluate_technical(state: EvaluationState) -> dict:
    """Evaluate technical skills"""
    logger.info("Evaluating technical skills...")
    
    prompt = TECHNICAL_PROMPT.format(
        job_title=state["offer"].job_title,
        company_name=state["offer"].company_name,
        mandatory_skills=", ".join(state["offer"].mandatory_skills) or "None",
        nice_to_have_skills=", ".join(state["offer"].nice_to_have_skills) or "None",
        experience_required=state["offer"].experience_required,
        experience_years=state["candidate"].experience_years,
        skills=", ".join([f"{s.name} ({s.level})" if s.level else s.name for s in state["candidate"].skills]),
        experiences="\n".join([f"- {e.role} at {e.company}" for e in state["candidate"].experiences[:3]])
    )
    
    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=prompt)])
    
    return {
        "technical_score": result.score,
        "technical_reason": result.reason
    }


def evaluate_trajectory(state: EvaluationState) -> dict:
    """Evaluate career trajectory"""
    logger.info("Evaluating career trajectory...")
    
    prompt = TRAJECTORY_PROMPT.format(
        job_title=state["offer"].job_title,
        company_name=state["offer"].company_name,
        experience_required=state["offer"].experience_required,
        experience_years=state["candidate"].experience_years,
        experiences="\n".join([f"{i+1}. {e.role} at {e.company} ({e.duration or 'N/A'})" 
                               for i, e in enumerate(state["candidate"].experiences)]),
        educations="\n".join([f"- {ed.degree} in {ed.name} from {ed.institute}" 
                              for ed in state["candidate"].educations])
    )
    
    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=prompt)])
    
    return {
        "trajectory_score": result.score,
        "trajectory_reason": result.reason
    }


def evaluate_cultural(state: EvaluationState) -> dict:
    """Evaluate cultural fit"""
    logger.info("Evaluating cultural fit...")
    
    prompt = CULTURAL_PROMPT.format(
        job_title=state["offer"].job_title,
        company_name=state["offer"].company_name,
        work_type=state["offer"].type,
        contract=state["offer"].contract,
        mandatory_languages=", ".join(state["offer"].mandatory_languages) or "None",
        languages="\n".join([f"- {lang.name}: {lang.level}" for lang in state["candidate"].languages]),
        companies="\n".join([f"- {exp.company}" for exp in state["candidate"].experiences[:5]])
    )
    
    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=prompt)])
    
    return {
        "cultural_score": result.score,
        "cultural_reason": result.reason
    }


def calculate_score(state: EvaluationState) -> dict:
    """Calculate weighted final score"""
    logger.info("Calculating final score...")
    
    reasoning = f"""Technical: {state['technical_reason']}

Trajectory: {state['trajectory_reason']}

Cultural: {state['cultural_reason']}"""
    
    prompt = SCORING_PROMPT.format(
        technical_score=state["technical_score"],
        trajectory_score=state["trajectory_score"],
        cultural_score=state["cultural_score"],
        reasoning=reasoning
    )
    
    structured_llm = llm.with_structured_output(ScoringOutput)
    result = structured_llm.invoke([SystemMessage(content=prompt)])
    
    return {
        "final_score": result.final_score,
        "liked": result.liked,
        "aggregated_reason": result.aggregated_reason
    }


def qa_validation(state: EvaluationState) -> dict:
    """QA validation for inconsistencies"""
    logger.info("Performing QA validation...")
    
    prompt = QA_PROMPT.format(
        technical_score=state["technical_score"],
        trajectory_score=state["trajectory_score"],
        cultural_score=state["cultural_score"],
        final_score=state["final_score"],
        decision="LIKED" if state["liked"] else "REJECTED"
    )
    
    structured_llm = llm.with_structured_output(QAOutput)
    result = structured_llm.invoke([SystemMessage(content=prompt)])
    
    return {
        "qa_required_human_review": result.qa_required_human_review,
        "qa_note": result.qa_note
    }


# ============================================================================
# BUILD GRAPH
# ============================================================================

def build_evaluation_graph():
    """Build the evaluation workflow graph"""
    
    builder = StateGraph(EvaluationState)
    
    # Add nodes
    builder.add_node("evaluate_technical", evaluate_technical)
    builder.add_node("evaluate_trajectory", evaluate_trajectory)
    builder.add_node("evaluate_cultural", evaluate_cultural)
    builder.add_node("calculate_score", calculate_score)
    builder.add_node("qa_validation", qa_validation)
    
    # Define flow
    builder.add_edge(START, "evaluate_technical")
    builder.add_edge("evaluate_technical", "evaluate_trajectory")
    builder.add_edge("evaluate_trajectory", "evaluate_cultural")
    builder.add_edge("evaluate_cultural", "calculate_score")
    builder.add_edge("calculate_score", "qa_validation")
    builder.add_edge("qa_validation", END)
    
    # Compile with memory
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


# Global graph instance
graph = build_evaluation_graph()


# ============================================================================
# SERVICE LAYER
# ============================================================================

async def evaluate_candidate(request: EvaluationRequest) -> EvaluationResult:
    """Execute evaluation workflow"""
    try:
        logger.info(f"Starting evaluation: {request.offer.job_title} at {request.offer.company_name}")
        
        # Initialize state
        initial_state = {
            "offer": request.offer,
            "candidate": request.candidate,
            "messages": []
        }
        
        # Execute graph
        config = {"configurable": {"thread_id": "eval_001"}}
        final_state = await graph.ainvoke(initial_state, config)
        
        # Build result
        ai_swipe_reasons = [
            f"Technical Skills ({final_state['technical_score']}/100): {final_state['technical_reason']}",
            f"Career Trajectory ({final_state['trajectory_score']}/100): {final_state['trajectory_reason']}",
            f"Cultural Fit ({final_state['cultural_score']}/100): {final_state['cultural_reason']}"
        ]
        
        if final_state["qa_note"]:
            ai_swipe_reasons.append(f"QA Validation: {final_state['qa_note']}")
        
        # Prioritize QA note if human review required
        if final_state["qa_required_human_review"]:
            final_reason = f"⚠️ HUMAN REVIEW REQUIRED: {final_state['qa_note']}\n\n{final_state['aggregated_reason']}"
        else:
            final_reason = final_state["aggregated_reason"]
        
        result = EvaluationResult(
            liked=final_state["liked"],
            reason=final_reason,
            compatibility=final_state["final_score"],
            ai_swipe_reasons=ai_swipe_reasons,
            models_liked=5,
            models_evaluated=5,
            qa_required_human_review=final_state["qa_required_human_review"]
        )
        
        logger.info(f"Evaluation complete: {'LIKED' if result.liked else 'REJECTED'} (Score: {result.compatibility})")
        return result
        
    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        raise


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Candidate Evaluation System",
    description="AI-powered candidate evaluation using LangGraph",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "candidate-evaluation",
        "version": "2.0.0"
    }


@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_endpoint(request: EvaluationRequest) -> EvaluationResult:
    """Main evaluation endpoint"""
    try:
        return await evaluate_candidate(request)
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Launching FastAPI server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )