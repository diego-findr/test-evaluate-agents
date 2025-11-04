"""
MAS-Eval: Multi-Agent System for Candidate Evaluation

A simplified implementation following LangChain Academy best practices.
Uses LangGraph to orchestrate specialized evaluation agents.
"""

import os
from typing import Optional, TypedDict
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# ============================================================================
# Data Models
# ============================================================================

class OfferData(BaseModel):
    """Job offer data structure."""
    job_title: str
    company_name: str
    contract: str
    type: str
    description: str
    salary_range: Optional[str] = None
    responsibilities: str
    experience_required: str
    mandatory_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    mandatory_languages: list[str] = Field(default_factory=list)
    nice_to_have_languages: list[str] = Field(default_factory=list)
    preferred_companies: list[str] = Field(default_factory=list)
    extra_requirements_to_consider: Optional[str] = None


class Education(BaseModel):
    """Candidate education entry."""
    degree: str
    name: str
    institute: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Experience(BaseModel):
    """Candidate work experience entry."""
    role: str
    company: str
    description: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None


class Skill(BaseModel):
    """Candidate skill."""
    name: str
    level: Optional[str] = None


class Language(BaseModel):
    """Candidate language."""
    name: str
    level: str


class CandidateData(BaseModel):
    """Candidate data structure."""
    heading: str
    experience_years: int
    educations: list[Education] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    """Main input model."""
    offer: OfferData
    candidate: CandidateData


class ScoreOutput(BaseModel):
    """Structured output for evaluation agents."""
    score: int = Field(..., ge=0, le=100)
    reason: str


class ScoringAgentOutput(BaseModel):
    """Output from scoring agent."""
    final_score: int = Field(..., ge=0, le=100)
    liked: bool
    aggregated_reason: str


class QAAgentOutput(BaseModel):
    """Output from QA validation agent."""
    qa_required_human_review: bool
    qa_note: Optional[str] = None


class EvaluationResult(BaseModel):
    """Final output model."""
    liked: bool
    reason: str
    compatibility: int
    ai_swipe_reasons: list[str]
    models_liked: int = 5
    models_evaluated: int = 5
    qa_required_human_review: bool


# ============================================================================
# State Definition
# ============================================================================

class EvaluationState(TypedDict):
    """LangGraph state for evaluation process."""
    # Input data
    offer: OfferData
    candidate: CandidateData
    
    # Evaluation agent outputs
    technical_score: Optional[int]
    technical_reason: Optional[str]
    trajectory_score: Optional[int]
    trajectory_reason: Optional[str]
    cultural_score: Optional[int]
    cultural_reason: Optional[str]
    
    # Scoring agent output
    final_score: Optional[int]
    liked: Optional[bool]
    aggregated_reason: Optional[str]
    
    # QA agent output
    qa_required_human_review: Optional[bool]
    qa_note: Optional[str]


# ============================================================================
# LLM Setup
# ============================================================================

# Initialize LLM
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY")
)


# ============================================================================
# Agent Nodes
# ============================================================================

def technical_skills_agent(state: EvaluationState) -> dict:
    """Agent 1: Technical Skills Evaluator (Weight: 50%)."""
    system_prompt = """You are a Technical Skills Evaluator specialized in assessing technical competencies.

Your focus:
- Match between candidate's technical skills and mandatory/nice-to-have skills
- Relevance of technical experience to the job role
- Depth and breadth of technical expertise

Scoring:
- 90-100: Exceptional match - exceeds all requirements
- 70-89: Strong match - meets all mandatory + most nice-to-have
- 50-69: Moderate match - meets most mandatory skills
- 30-49: Weak match - gaps in mandatory skills
- 0-29: Poor match - significant gaps

Provide a score (0-100) and detailed reasoning focusing ONLY on technical aspects."""

    offer = state["offer"]
    candidate = state["candidate"]
    
    user_prompt = f"""Evaluate technical compatibility:

JOB OFFER - {offer.job_title} at {offer.company_name}
- Mandatory Skills: {', '.join(offer.mandatory_skills) if offer.mandatory_skills else 'None'}
- Nice-to-Have Skills: {', '.join(offer.nice_to_have_skills) if offer.nice_to_have_skills else 'None'}
- Experience Required: {offer.experience_required}
- Responsibilities: {offer.responsibilities}

CANDIDATE PROFILE
- Headline: {candidate.heading}
- Experience: {candidate.experience_years} years
- Skills: {', '.join([f"{s.name} ({s.level})" if s.level else s.name for s in candidate.skills])}
- Recent Roles: {chr(10).join([f"- {exp.role} at {exp.company}: {exp.description[:200]}" for exp in candidate.experiences[:3]])}

Evaluate the technical match."""

    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "technical_score": result.score,
        "technical_reason": result.reason
    }


def career_trajectory_agent(state: EvaluationState) -> dict:
    """Agent 2: Career Trajectory Evaluator (Weight: 35%)."""
    system_prompt = """You are a Career Trajectory Evaluator specialized in assessing professional growth.

Your focus:
- Career progression and growth trajectory
- Relevance of previous roles to target position
- Company prestige and industry alignment
- Years of experience adequacy
- Job stability

Scoring:
- 90-100: Exceptional trajectory - clear upward progression
- 70-89: Strong trajectory - consistent growth
- 50-69: Moderate trajectory - some relevant experience
- 30-49: Weak trajectory - limited relevant experience
- 0-29: Poor trajectory - mismatched experience

Provide a score (0-100) and detailed reasoning focusing ONLY on career trajectory."""

    offer = state["offer"]
    candidate = state["candidate"]
    
    user_prompt = f"""Evaluate career trajectory compatibility:

JOB OFFER - {offer.job_title} at {offer.company_name}
- Experience Required: {offer.experience_required}
- Preferred Companies: {', '.join(offer.preferred_companies) if offer.preferred_companies else 'None'}

CANDIDATE PROFILE
- Total Experience: {candidate.experience_years} years
- Headline: {candidate.heading}
- Work History: {chr(10).join([f"{i+1}. {exp.role} at {exp.company} ({exp.duration or 'N/A'}): {exp.description[:200]}" for i, exp in enumerate(candidate.experiences)])}
- Education: {chr(10).join([f"- {edu.degree} in {edu.name} from {edu.institute}" for edu in candidate.educations])}

Evaluate the career trajectory match."""

    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "trajectory_score": result.score,
        "trajectory_reason": result.reason
    }


def cultural_fit_agent(state: EvaluationState) -> dict:
    """Agent 3: Cultural Fit Evaluator (Weight: 15%)."""
    system_prompt = """You are a Cultural Fit Evaluator specialized in assessing work style alignment.

Your focus:
- Work environment preferences (remote/on-site/hybrid)
- Language proficiency for communication
- Contract type preferences
- Work style flexibility

Scoring:
- 90-100: Exceptional fit - perfect alignment
- 70-89: Strong fit - compatible preferences
- 50-69: Moderate fit - acceptable alignment
- 30-49: Weak fit - some misalignment
- 0-29: Poor fit - significant incompatibility

Provide a score (0-100) and detailed reasoning focusing ONLY on cultural fit."""

    offer = state["offer"]
    candidate = state["candidate"]
    
    user_prompt = f"""Evaluate cultural fit:

JOB OFFER - {offer.job_title} at {offer.company_name}
- Work Type: {offer.type}
- Contract: {offer.contract}
- Mandatory Languages: {', '.join(offer.mandatory_languages) if offer.mandatory_languages else 'None'}
- Description: {offer.description[:300]}

CANDIDATE PROFILE
- Languages: {chr(10).join([f"- {lang.name}: {lang.level}" for lang in candidate.languages])}
- Work History: {chr(10).join([f"- {exp.role} at {exp.company}" for exp in candidate.experiences[:5]])}
- Experience: {candidate.experience_years} years

Evaluate cultural and work style compatibility."""

    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "cultural_score": result.score,
        "cultural_reason": result.reason
    }


def scoring_agent(state: EvaluationState) -> dict:
    """Agent 4: Scoring & Decision Agent.
    
    Weights:
    - Technical Skills: 50%
    - Career Trajectory: 35%
    - Cultural Fit: 15%
    
    Decision: liked = True if final_score >= 70
    """
    system_prompt = """You are a Scoring & Decision Agent.

Your task:
1. Apply weighted formula: (Technical × 0.50) + (Trajectory × 0.35) + (Cultural × 0.15)
2. Calculate final score (0-100)
3. Make decision: LIKED if score >= 70, REJECTED if score < 70
4. Synthesize all reasoning into cohesive explanation

Provide the weighted score, binary decision, and aggregated reasoning."""

    technical_score = state["technical_score"]
    trajectory_score = state["trajectory_score"]
    cultural_score = state["cultural_score"]
    
    user_prompt = f"""Calculate final compatibility score:

EVALUATION SCORES:
- Technical Skills: {technical_score}/100 (Weight: 50%)
- Career Trajectory: {trajectory_score}/100 (Weight: 35%)
- Cultural Fit: {cultural_score}/100 (Weight: 15%)

REASONING:
Technical: {state['technical_reason']}
Trajectory: {state['trajectory_reason']}
Cultural: {state['cultural_reason']}

Calculate: Final Score = ({technical_score} × 0.50) + ({trajectory_score} × 0.35) + ({cultural_score} × 0.15)
Decision: LIKED if Final Score >= 70, REJECTED otherwise"""

    structured_llm = llm.with_structured_output(ScoringAgentOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "final_score": result.final_score,
        "liked": result.liked,
        "aggregated_reason": result.aggregated_reason
    }


def qa_validation_agent(state: EvaluationState) -> dict:
    """Agent 5: QA Validation Agent.
    
    Detects critical inconsistencies:
    1. Final Score >= 70 but Technical Score < 50
    2. Final Score < 70 but all three scores > 80
    """
    system_prompt = """You are a QA Validation Agent detecting critical inconsistencies.

CRITICAL RULE 1:
If Final Score >= 70 BUT Technical Score < 50:
→ Flag for human review
→ Reason: Lacks fundamental technical competency despite passing

CRITICAL RULE 2:
If Final Score < 70 BUT ALL THREE scores > 80:
→ Flag for human review
→ Reason: All evaluators scored highly but weighted formula rejected

If no inconsistencies:
→ qa_required_human_review = False
→ qa_note = "No critical inconsistencies detected.""""

    technical_score = state["technical_score"]
    trajectory_score = state["trajectory_score"]
    cultural_score = state["cultural_score"]
    final_score = state["final_score"]
    liked = state["liked"]
    
    user_prompt = f"""Perform QA validation:

EVALUATION RESULTS:
- Technical: {technical_score}/100
- Trajectory: {trajectory_score}/100
- Cultural: {cultural_score}/100
- Final: {final_score}/100
- Decision: {"LIKED" if liked else "REJECTED"}

Rule 1: Final >= 70 AND Technical < 50? {final_score >= 70 and technical_score < 50}
Rule 2: Final < 70 AND all > 80? {final_score < 70 and technical_score > 80 and trajectory_score > 80 and cultural_score > 80}

Determine if human review is required."""

    structured_llm = llm.with_structured_output(QAAgentOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "qa_required_human_review": result.qa_required_human_review,
        "qa_note": result.qa_note
    }


# ============================================================================
# Graph Construction
# ============================================================================

def build_graph():
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(EvaluationState)
    
    # Add nodes
    workflow.add_node("technical_agent", technical_skills_agent)
    workflow.add_node("trajectory_agent", career_trajectory_agent)
    workflow.add_node("cultural_agent", cultural_fit_agent)
    workflow.add_node("scoring_agent", scoring_agent)
    workflow.add_node("qa_agent", qa_validation_agent)
    
    # Define edges - sequential execution
    workflow.add_edge(START, "technical_agent")
    workflow.add_edge("technical_agent", "trajectory_agent")
    workflow.add_edge("trajectory_agent", "cultural_agent")
    workflow.add_edge("cultural_agent", "scoring_agent")
    workflow.add_edge("scoring_agent", "qa_agent")
    workflow.add_edge("qa_agent", END)
    
    # Compile graph with checkpointer
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# ============================================================================
# Result Builder
# ============================================================================

def build_result(state: EvaluationState) -> EvaluationResult:
    """Build final EvaluationResult from state."""
    # Collect all reasoning steps
    ai_swipe_reasons = [
        f"Technical Skills ({state['technical_score']}/100): {state['technical_reason']}",
        f"Career Trajectory ({state['trajectory_score']}/100): {state['trajectory_reason']}",
        f"Cultural Fit ({state['cultural_score']}/100): {state['cultural_reason']}"
    ]
    
    if state.get("qa_note"):
        ai_swipe_reasons.append(f"QA Validation: {state['qa_note']}")
    
    # Prioritize QA note in final reason if human review required
    if state.get("qa_required_human_review") and state.get("qa_note"):
        final_reason = f"⚠️ HUMAN REVIEW REQUIRED: {state['qa_note']}\n\nAggregated Assessment: {state['aggregated_reason']}"
    else:
        final_reason = state.get("aggregated_reason", "")
    
    return EvaluationResult(
        liked=state["liked"],
        reason=final_reason,
        compatibility=state["final_score"],
        ai_swipe_reasons=ai_swipe_reasons,
        models_liked=5,
        models_evaluated=5,
        qa_required_human_review=state.get("qa_required_human_review", False)
    )


# ============================================================================
# FastAPI Application
# ============================================================================

# Compile graph
graph = build_graph()

app = FastAPI(
    title="MAS-Eval: Multi-Agent Candidate Evaluation",
    description="AI-powered candidate evaluation using LangGraph",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mas-eval", "version": "1.0.0"}


@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_candidate(request: EvaluationRequest) -> EvaluationResult:
    """Main evaluation endpoint."""
    try:
        # Initialize state
        initial_state: EvaluationState = {
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
            "qa_note": None
        }
        
        # Execute graph
        config = {"configurable": {"thread_id": "evaluation_001"}}
        final_state = await graph.ainvoke(initial_state, config)
        
        # Build result
        result = build_result(final_state)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

MAS-Eval: Multi-Agent System for Candidate Evaluation

A simplified implementation following LangChain Academy best practices.
Uses LangGraph to orchestrate specialized evaluation agents.
"""

import os
from typing import Optional, TypedDict
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# ============================================================================
# Data Models
# ============================================================================

class OfferData(BaseModel):
    """Job offer data structure."""
    job_title: str
    company_name: str
    contract: str
    type: str
    description: str
    salary_range: Optional[str] = None
    responsibilities: str
    experience_required: str
    mandatory_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    mandatory_languages: list[str] = Field(default_factory=list)
    nice_to_have_languages: list[str] = Field(default_factory=list)
    preferred_companies: list[str] = Field(default_factory=list)
    extra_requirements_to_consider: Optional[str] = None


class Education(BaseModel):
    """Candidate education entry."""
    degree: str
    name: str
    institute: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Experience(BaseModel):
    """Candidate work experience entry."""
    role: str
    company: str
    description: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None


class Skill(BaseModel):
    """Candidate skill."""
    name: str
    level: Optional[str] = None


class Language(BaseModel):
    """Candidate language."""
    name: str
    level: str


class CandidateData(BaseModel):
    """Candidate data structure."""
    heading: str
    experience_years: int
    educations: list[Education] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    """Main input model."""
    offer: OfferData
    candidate: CandidateData


class ScoreOutput(BaseModel):
    """Structured output for evaluation agents."""
    score: int = Field(..., ge=0, le=100)
    reason: str


class ScoringAgentOutput(BaseModel):
    """Output from scoring agent."""
    final_score: int = Field(..., ge=0, le=100)
    liked: bool
    aggregated_reason: str


class QAAgentOutput(BaseModel):
    """Output from QA validation agent."""
    qa_required_human_review: bool
    qa_note: Optional[str] = None


class EvaluationResult(BaseModel):
    """Final output model."""
    liked: bool
    reason: str
    compatibility: int
    ai_swipe_reasons: list[str]
    models_liked: int = 5
    models_evaluated: int = 5
    qa_required_human_review: bool


# ============================================================================
# State Definition
# ============================================================================

class EvaluationState(TypedDict):
    """LangGraph state for evaluation process."""
    # Input data
    offer: OfferData
    candidate: CandidateData
    
    # Evaluation agent outputs
    technical_score: Optional[int]
    technical_reason: Optional[str]
    trajectory_score: Optional[int]
    trajectory_reason: Optional[str]
    cultural_score: Optional[int]
    cultural_reason: Optional[str]
    
    # Scoring agent output
    final_score: Optional[int]
    liked: Optional[bool]
    aggregated_reason: Optional[str]
    
    # QA agent output
    qa_required_human_review: Optional[bool]
    qa_note: Optional[str]


# ============================================================================
# LLM Setup
# ============================================================================

# Initialize LLM
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY")
)


# ============================================================================
# Agent Nodes
# ============================================================================

def technical_skills_agent(state: EvaluationState) -> dict:
    """Agent 1: Technical Skills Evaluator (Weight: 50%)."""
    system_prompt = """You are a Technical Skills Evaluator specialized in assessing technical competencies.

Your focus:
- Match between candidate's technical skills and mandatory/nice-to-have skills
- Relevance of technical experience to the job role
- Depth and breadth of technical expertise

Scoring:
- 90-100: Exceptional match - exceeds all requirements
- 70-89: Strong match - meets all mandatory + most nice-to-have
- 50-69: Moderate match - meets most mandatory skills
- 30-49: Weak match - gaps in mandatory skills
- 0-29: Poor match - significant gaps

Provide a score (0-100) and detailed reasoning focusing ONLY on technical aspects."""

    offer = state["offer"]
    candidate = state["candidate"]
    
    user_prompt = f"""Evaluate technical compatibility:

JOB OFFER - {offer.job_title} at {offer.company_name}
- Mandatory Skills: {', '.join(offer.mandatory_skills) if offer.mandatory_skills else 'None'}
- Nice-to-Have Skills: {', '.join(offer.nice_to_have_skills) if offer.nice_to_have_skills else 'None'}
- Experience Required: {offer.experience_required}
- Responsibilities: {offer.responsibilities}

CANDIDATE PROFILE
- Headline: {candidate.heading}
- Experience: {candidate.experience_years} years
- Skills: {', '.join([f"{s.name} ({s.level})" if s.level else s.name for s in candidate.skills])}
- Recent Roles: {chr(10).join([f"- {exp.role} at {exp.company}: {exp.description[:200]}" for exp in candidate.experiences[:3]])}

Evaluate the technical match."""

    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "technical_score": result.score,
        "technical_reason": result.reason
    }


def career_trajectory_agent(state: EvaluationState) -> dict:
    """Agent 2: Career Trajectory Evaluator (Weight: 35%)."""
    system_prompt = """You are a Career Trajectory Evaluator specialized in assessing professional growth.

Your focus:
- Career progression and growth trajectory
- Relevance of previous roles to target position
- Company prestige and industry alignment
- Years of experience adequacy
- Job stability

Scoring:
- 90-100: Exceptional trajectory - clear upward progression
- 70-89: Strong trajectory - consistent growth
- 50-69: Moderate trajectory - some relevant experience
- 30-49: Weak trajectory - limited relevant experience
- 0-29: Poor trajectory - mismatched experience

Provide a score (0-100) and detailed reasoning focusing ONLY on career trajectory."""

    offer = state["offer"]
    candidate = state["candidate"]
    
    user_prompt = f"""Evaluate career trajectory compatibility:

JOB OFFER - {offer.job_title} at {offer.company_name}
- Experience Required: {offer.experience_required}
- Preferred Companies: {', '.join(offer.preferred_companies) if offer.preferred_companies else 'None'}

CANDIDATE PROFILE
- Total Experience: {candidate.experience_years} years
- Headline: {candidate.heading}
- Work History: {chr(10).join([f"{i+1}. {exp.role} at {exp.company} ({exp.duration or 'N/A'}): {exp.description[:200]}" for i, exp in enumerate(candidate.experiences)])}
- Education: {chr(10).join([f"- {edu.degree} in {edu.name} from {edu.institute}" for edu in candidate.educations])}

Evaluate the career trajectory match."""

    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "trajectory_score": result.score,
        "trajectory_reason": result.reason
    }


def cultural_fit_agent(state: EvaluationState) -> dict:
    """Agent 3: Cultural Fit Evaluator (Weight: 15%)."""
    system_prompt = """You are a Cultural Fit Evaluator specialized in assessing work style alignment.

Your focus:
- Work environment preferences (remote/on-site/hybrid)
- Language proficiency for communication
- Contract type preferences
- Work style flexibility

Scoring:
- 90-100: Exceptional fit - perfect alignment
- 70-89: Strong fit - compatible preferences
- 50-69: Moderate fit - acceptable alignment
- 30-49: Weak fit - some misalignment
- 0-29: Poor fit - significant incompatibility

Provide a score (0-100) and detailed reasoning focusing ONLY on cultural fit."""

    offer = state["offer"]
    candidate = state["candidate"]
    
    user_prompt = f"""Evaluate cultural fit:

JOB OFFER - {offer.job_title} at {offer.company_name}
- Work Type: {offer.type}
- Contract: {offer.contract}
- Mandatory Languages: {', '.join(offer.mandatory_languages) if offer.mandatory_languages else 'None'}
- Description: {offer.description[:300]}

CANDIDATE PROFILE
- Languages: {chr(10).join([f"- {lang.name}: {lang.level}" for lang in candidate.languages])}
- Work History: {chr(10).join([f"- {exp.role} at {exp.company}" for exp in candidate.experiences[:5]])}
- Experience: {candidate.experience_years} years

Evaluate cultural and work style compatibility."""

    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "cultural_score": result.score,
        "cultural_reason": result.reason
    }


def scoring_agent(state: EvaluationState) -> dict:
    """Agent 4: Scoring & Decision Agent.
    
    Weights:
    - Technical Skills: 50%
    - Career Trajectory: 35%
    - Cultural Fit: 15%
    
    Decision: liked = True if final_score >= 70
    """
    system_prompt = """You are a Scoring & Decision Agent.

Your task:
1. Apply weighted formula: (Technical × 0.50) + (Trajectory × 0.35) + (Cultural × 0.15)
2. Calculate final score (0-100)
3. Make decision: LIKED if score >= 70, REJECTED if score < 70
4. Synthesize all reasoning into cohesive explanation

Provide the weighted score, binary decision, and aggregated reasoning."""

    technical_score = state["technical_score"]
    trajectory_score = state["trajectory_score"]
    cultural_score = state["cultural_score"]
    
    user_prompt = f"""Calculate final compatibility score:

EVALUATION SCORES:
- Technical Skills: {technical_score}/100 (Weight: 50%)
- Career Trajectory: {trajectory_score}/100 (Weight: 35%)
- Cultural Fit: {cultural_score}/100 (Weight: 15%)

REASONING:
Technical: {state['technical_reason']}
Trajectory: {state['trajectory_reason']}
Cultural: {state['cultural_reason']}

Calculate: Final Score = ({technical_score} × 0.50) + ({trajectory_score} × 0.35) + ({cultural_score} × 0.15)
Decision: LIKED if Final Score >= 70, REJECTED otherwise"""

    structured_llm = llm.with_structured_output(ScoringAgentOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "final_score": result.final_score,
        "liked": result.liked,
        "aggregated_reason": result.aggregated_reason
    }


def qa_validation_agent(state: EvaluationState) -> dict:
    """Agent 5: QA Validation Agent.
    
    Detects critical inconsistencies:
    1. Final Score >= 70 but Technical Score < 50
    2. Final Score < 70 but all three scores > 80
    """
    system_prompt = """You are a QA Validation Agent detecting critical inconsistencies.

CRITICAL RULE 1:
If Final Score >= 70 BUT Technical Score < 50:
→ Flag for human review
→ Reason: Lacks fundamental technical competency despite passing

CRITICAL RULE 2:
If Final Score < 70 BUT ALL THREE scores > 80:
→ Flag for human review
→ Reason: All evaluators scored highly but weighted formula rejected

If no inconsistencies:
→ qa_required_human_review = False
→ qa_note = "No critical inconsistencies detected.""""

    technical_score = state["technical_score"]
    trajectory_score = state["trajectory_score"]
    cultural_score = state["cultural_score"]
    final_score = state["final_score"]
    liked = state["liked"]
    
    user_prompt = f"""Perform QA validation:

EVALUATION RESULTS:
- Technical: {technical_score}/100
- Trajectory: {trajectory_score}/100
- Cultural: {cultural_score}/100
- Final: {final_score}/100
- Decision: {"LIKED" if liked else "REJECTED"}

Rule 1: Final >= 70 AND Technical < 50? {final_score >= 70 and technical_score < 50}
Rule 2: Final < 70 AND all > 80? {final_score < 70 and technical_score > 80 and trajectory_score > 80 and cultural_score > 80}

Determine if human review is required."""

    structured_llm = llm.with_structured_output(QAAgentOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "qa_required_human_review": result.qa_required_human_review,
        "qa_note": result.qa_note
    }


# ============================================================================
# Graph Construction
# ============================================================================

def build_graph():
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(EvaluationState)
    
    # Add nodes
    workflow.add_node("technical_agent", technical_skills_agent)
    workflow.add_node("trajectory_agent", career_trajectory_agent)
    workflow.add_node("cultural_agent", cultural_fit_agent)
    workflow.add_node("scoring_agent", scoring_agent)
    workflow.add_node("qa_agent", qa_validation_agent)
    
    # Define edges - sequential execution
    workflow.add_edge(START, "technical_agent")
    workflow.add_edge("technical_agent", "trajectory_agent")
    workflow.add_edge("trajectory_agent", "cultural_agent")
    workflow.add_edge("cultural_agent", "scoring_agent")
    workflow.add_edge("scoring_agent", "qa_agent")
    workflow.add_edge("qa_agent", END)
    
    # Compile graph
    return workflow.compile()


# ============================================================================
# Result Builder
# ============================================================================

def build_result(state: EvaluationState) -> EvaluationResult:
    """Build final EvaluationResult from state."""
    # Collect all reasoning steps
    ai_swipe_reasons = [
        f"Technical Skills ({state['technical_score']}/100): {state['technical_reason']}",
        f"Career Trajectory ({state['trajectory_score']}/100): {state['trajectory_reason']}",
        f"Cultural Fit ({state['cultural_score']}/100): {state['cultural_reason']}"
    ]
    
    if state.get("qa_note"):
        ai_swipe_reasons.append(f"QA Validation: {state['qa_note']}")
    
    # Prioritize QA note in final reason if human review required
    if state.get("qa_required_human_review") and state.get("qa_note"):
        final_reason = f"⚠️ HUMAN REVIEW REQUIRED: {state['qa_note']}\n\nAggregated Assessment: {state['aggregated_reason']}"
    else:
        final_reason = state.get("aggregated_reason", "")
    
    return EvaluationResult(
        liked=state["liked"],
        reason=final_reason,
        compatibility=state["final_score"],
        ai_swipe_reasons=ai_swipe_reasons,
        models_liked=5,
        models_evaluated=5,
        qa_required_human_review=state.get("qa_required_human_review", False)
    )


# ============================================================================
# FastAPI Application
# ============================================================================

# Compile graph
graph = build_graph()

app = FastAPI(
    title="MAS-Eval: Multi-Agent Candidate Evaluation",
    description="AI-powered candidate evaluation using LangGraph",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mas-eval", "version": "1.0.0"}


@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_candidate(request: EvaluationRequest) -> EvaluationResult:
    """Main evaluation endpoint."""
    try:
        # Initialize state
        initial_state: EvaluationState = {
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
            "qa_note": None
        }
        
        # Execute graph
        config = {"configurable": {"thread_id": "evaluation_001"}}
        final_state = await graph.ainvoke(initial_state, config)
        
        # Build result
        result = build_result(final_state)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

MAS-Eval: Multi-Agent System for Candidate Evaluation

A simplified implementation following LangChain Academy best practices.
Uses LangGraph to orchestrate specialized evaluation agents.
"""

import os
from typing import Optional, TypedDict
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

# ============================================================================
# Data Models
# ============================================================================

class OfferData(BaseModel):
    """Job offer data structure."""
    job_title: str
    company_name: str
    contract: str
    type: str
    description: str
    salary_range: Optional[str] = None
    responsibilities: str
    experience_required: str
    mandatory_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    mandatory_languages: list[str] = Field(default_factory=list)
    nice_to_have_languages: list[str] = Field(default_factory=list)
    preferred_companies: list[str] = Field(default_factory=list)
    extra_requirements_to_consider: Optional[str] = None


class Education(BaseModel):
    """Candidate education entry."""
    degree: str
    name: str
    institute: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Experience(BaseModel):
    """Candidate work experience entry."""
    role: str
    company: str
    description: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None


class Skill(BaseModel):
    """Candidate skill."""
    name: str
    level: Optional[str] = None


class Language(BaseModel):
    """Candidate language."""
    name: str
    level: str


class CandidateData(BaseModel):
    """Candidate data structure."""
    heading: str
    experience_years: int
    educations: list[Education] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    """Main input model."""
    offer: OfferData
    candidate: CandidateData


class ScoreOutput(BaseModel):
    """Structured output for evaluation agents."""
    score: int = Field(..., ge=0, le=100)
    reason: str


class ScoringAgentOutput(BaseModel):
    """Output from scoring agent."""
    final_score: int = Field(..., ge=0, le=100)
    liked: bool
    aggregated_reason: str


class QAAgentOutput(BaseModel):
    """Output from QA validation agent."""
    qa_required_human_review: bool
    qa_note: Optional[str] = None


class EvaluationResult(BaseModel):
    """Final output model."""
    liked: bool
    reason: str
    compatibility: int
    ai_swipe_reasons: list[str]
    models_liked: int = 5
    models_evaluated: int = 5
    qa_required_human_review: bool


# ============================================================================
# State Definition
# ============================================================================

class EvaluationState(TypedDict):
    """LangGraph state for evaluation process."""
    # Input data
    offer: OfferData
    candidate: CandidateData
    
    # Evaluation agent outputs
    technical_score: Optional[int]
    technical_reason: Optional[str]
    trajectory_score: Optional[int]
    trajectory_reason: Optional[str]
    cultural_score: Optional[int]
    cultural_reason: Optional[str]
    
    # Scoring agent output
    final_score: Optional[int]
    liked: Optional[bool]
    aggregated_reason: Optional[str]
    
    # QA agent output
    qa_required_human_review: Optional[bool]
    qa_note: Optional[str]


# ============================================================================
# LLM Setup
# ============================================================================

# Initialize LLM
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY")
)


# ============================================================================
# Agent Nodes
# ============================================================================

def technical_skills_agent(state: EvaluationState) -> dict:
    """Agent 1: Technical Skills Evaluator (Weight: 50%)."""
    system_prompt = """You are a Technical Skills Evaluator specialized in assessing technical competencies.

Your focus:
- Match between candidate's technical skills and mandatory/nice-to-have skills
- Relevance of technical experience to the job role
- Depth and breadth of technical expertise

Scoring:
- 90-100: Exceptional match - exceeds all requirements
- 70-89: Strong match - meets all mandatory + most nice-to-have
- 50-69: Moderate match - meets most mandatory skills
- 30-49: Weak match - gaps in mandatory skills
- 0-29: Poor match - significant gaps

Provide a score (0-100) and detailed reasoning focusing ONLY on technical aspects."""

    offer = state["offer"]
    candidate = state["candidate"]
    
    user_prompt = f"""Evaluate technical compatibility:

JOB OFFER - {offer.job_title} at {offer.company_name}
- Mandatory Skills: {', '.join(offer.mandatory_skills) if offer.mandatory_skills else 'None'}
- Nice-to-Have Skills: {', '.join(offer.nice_to_have_skills) if offer.nice_to_have_skills else 'None'}
- Experience Required: {offer.experience_required}
- Responsibilities: {offer.responsibilities}

CANDIDATE PROFILE
- Headline: {candidate.heading}
- Experience: {candidate.experience_years} years
- Skills: {', '.join([f"{s.name} ({s.level})" if s.level else s.name for s in candidate.skills])}
- Recent Roles: {chr(10).join([f"- {exp.role} at {exp.company}: {exp.description[:200]}" for exp in candidate.experiences[:3]])}

Evaluate the technical match."""

    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "technical_score": result.score,
        "technical_reason": result.reason
    }


def career_trajectory_agent(state: EvaluationState) -> dict:
    """Agent 2: Career Trajectory Evaluator (Weight: 35%)."""
    system_prompt = """You are a Career Trajectory Evaluator specialized in assessing professional growth.

Your focus:
- Career progression and growth trajectory
- Relevance of previous roles to target position
- Company prestige and industry alignment
- Years of experience adequacy
- Job stability

Scoring:
- 90-100: Exceptional trajectory - clear upward progression
- 70-89: Strong trajectory - consistent growth
- 50-69: Moderate trajectory - some relevant experience
- 30-49: Weak trajectory - limited relevant experience
- 0-29: Poor trajectory - mismatched experience

Provide a score (0-100) and detailed reasoning focusing ONLY on career trajectory."""

    offer = state["offer"]
    candidate = state["candidate"]
    
    user_prompt = f"""Evaluate career trajectory compatibility:

JOB OFFER - {offer.job_title} at {offer.company_name}
- Experience Required: {offer.experience_required}
- Preferred Companies: {', '.join(offer.preferred_companies) if offer.preferred_companies else 'None'}

CANDIDATE PROFILE
- Total Experience: {candidate.experience_years} years
- Headline: {candidate.heading}
- Work History: {chr(10).join([f"{i+1}. {exp.role} at {exp.company} ({exp.duration or 'N/A'}): {exp.description[:200]}" for i, exp in enumerate(candidate.experiences)])}
- Education: {chr(10).join([f"- {edu.degree} in {edu.name} from {edu.institute}" for edu in candidate.educations])}

Evaluate the career trajectory match."""

    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "trajectory_score": result.score,
        "trajectory_reason": result.reason
    }


def cultural_fit_agent(state: EvaluationState) -> dict:
    """Agent 3: Cultural Fit Evaluator (Weight: 15%)."""
    system_prompt = """You are a Cultural Fit Evaluator specialized in assessing work style alignment.

Your focus:
- Work environment preferences (remote/on-site/hybrid)
- Language proficiency for communication
- Contract type preferences
- Work style flexibility

Scoring:
- 90-100: Exceptional fit - perfect alignment
- 70-89: Strong fit - compatible preferences
- 50-69: Moderate fit - acceptable alignment
- 30-49: Weak fit - some misalignment
- 0-29: Poor fit - significant incompatibility

Provide a score (0-100) and detailed reasoning focusing ONLY on cultural fit."""

    offer = state["offer"]
    candidate = state["candidate"]
    
    user_prompt = f"""Evaluate cultural fit:

JOB OFFER - {offer.job_title} at {offer.company_name}
- Work Type: {offer.type}
- Contract: {offer.contract}
- Mandatory Languages: {', '.join(offer.mandatory_languages) if offer.mandatory_languages else 'None'}
- Description: {offer.description[:300]}

CANDIDATE PROFILE
- Languages: {chr(10).join([f"- {lang.name}: {lang.level}" for lang in candidate.languages])}
- Work History: {chr(10).join([f"- {exp.role} at {exp.company}" for exp in candidate.experiences[:5]])}
- Experience: {candidate.experience_years} years

Evaluate cultural and work style compatibility."""

    structured_llm = llm.with_structured_output(ScoreOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "cultural_score": result.score,
        "cultural_reason": result.reason
    }


def scoring_agent(state: EvaluationState) -> dict:
    """Agent 4: Scoring & Decision Agent.
    
    Weights:
    - Technical Skills: 50%
    - Career Trajectory: 35%
    - Cultural Fit: 15%
    
    Decision: liked = True if final_score >= 70
    """
    system_prompt = """You are a Scoring & Decision Agent.

Your task:
1. Apply weighted formula: (Technical × 0.50) + (Trajectory × 0.35) + (Cultural × 0.15)
2. Calculate final score (0-100)
3. Make decision: LIKED if score >= 70, REJECTED if score < 70
4. Synthesize all reasoning into cohesive explanation

Provide the weighted score, binary decision, and aggregated reasoning."""

    technical_score = state["technical_score"]
    trajectory_score = state["trajectory_score"]
    cultural_score = state["cultural_score"]
    
    user_prompt = f"""Calculate final compatibility score:

EVALUATION SCORES:
- Technical Skills: {technical_score}/100 (Weight: 50%)
- Career Trajectory: {trajectory_score}/100 (Weight: 35%)
- Cultural Fit: {cultural_score}/100 (Weight: 15%)

REASONING:
Technical: {state['technical_reason']}
Trajectory: {state['trajectory_reason']}
Cultural: {state['cultural_reason']}

Calculate: Final Score = ({technical_score} × 0.50) + ({trajectory_score} × 0.35) + ({cultural_score} × 0.15)
Decision: LIKED if Final Score >= 70, REJECTED otherwise"""

    structured_llm = llm.with_structured_output(ScoringAgentOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "final_score": result.final_score,
        "liked": result.liked,
        "aggregated_reason": result.aggregated_reason
    }


def qa_validation_agent(state: EvaluationState) -> dict:
    """Agent 5: QA Validation Agent.
    
    Detects critical inconsistencies:
    1. Final Score >= 70 but Technical Score < 50
    2. Final Score < 70 but all three scores > 80
    """
    system_prompt = """You are a QA Validation Agent detecting critical inconsistencies.

CRITICAL RULE 1:
If Final Score >= 70 BUT Technical Score < 50:
→ Flag for human review
→ Reason: Lacks fundamental technical competency despite passing

CRITICAL RULE 2:
If Final Score < 70 BUT ALL THREE scores > 80:
→ Flag for human review
→ Reason: All evaluators scored highly but weighted formula rejected

If no inconsistencies:
→ qa_required_human_review = False
→ qa_note = "No critical inconsistencies detected.""""

    technical_score = state["technical_score"]
    trajectory_score = state["trajectory_score"]
    cultural_score = state["cultural_score"]
    final_score = state["final_score"]
    liked = state["liked"]
    
    user_prompt = f"""Perform QA validation:

EVALUATION RESULTS:
- Technical: {technical_score}/100
- Trajectory: {trajectory_score}/100
- Cultural: {cultural_score}/100
- Final: {final_score}/100
- Decision: {"LIKED" if liked else "REJECTED"}

Rule 1: Final >= 70 AND Technical < 50? {final_score >= 70 and technical_score < 50}
Rule 2: Final < 70 AND all > 80? {final_score < 70 and technical_score > 80 and trajectory_score > 80 and cultural_score > 80}

Determine if human review is required."""

    structured_llm = llm.with_structured_output(QAAgentOutput)
    result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    return {
        "qa_required_human_review": result.qa_required_human_review,
        "qa_note": result.qa_note
    }


# ============================================================================
# Graph Construction
# ============================================================================

def build_graph():
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(EvaluationState)
    
    # Add nodes
    workflow.add_node("technical_agent", technical_skills_agent)
    workflow.add_node("trajectory_agent", career_trajectory_agent)
    workflow.add_node("cultural_agent", cultural_fit_agent)
    workflow.add_node("scoring_agent", scoring_agent)
    workflow.add_node("qa_agent", qa_validation_agent)
    
    # Define edges - sequential execution
    workflow.add_edge(START, "technical_agent")
    workflow.add_edge("technical_agent", "trajectory_agent")
    workflow.add_edge("trajectory_agent", "cultural_agent")
    workflow.add_edge("cultural_agent", "scoring_agent")
    workflow.add_edge("scoring_agent", "qa_agent")
    workflow.add_edge("qa_agent", END)
    
    # Compile graph
    return workflow.compile()


# ============================================================================
# Result Builder
# ============================================================================

def build_result(state: EvaluationState) -> EvaluationResult:
    """Build final EvaluationResult from state."""
    # Collect all reasoning steps
    ai_swipe_reasons = [
        f"Technical Skills ({state['technical_score']}/100): {state['technical_reason']}",
        f"Career Trajectory ({state['trajectory_score']}/100): {state['trajectory_reason']}",
        f"Cultural Fit ({state['cultural_score']}/100): {state['cultural_reason']}"
    ]
    
    if state.get("qa_note"):
        ai_swipe_reasons.append(f"QA Validation: {state['qa_note']}")
    
    # Prioritize QA note in final reason if human review required
    if state.get("qa_required_human_review") and state.get("qa_note"):
        final_reason = f"⚠️ HUMAN REVIEW REQUIRED: {state['qa_note']}\n\nAggregated Assessment: {state['aggregated_reason']}"
    else:
        final_reason = state.get("aggregated_reason", "")
    
    return EvaluationResult(
        liked=state["liked"],
        reason=final_reason,
        compatibility=state["final_score"],
        ai_swipe_reasons=ai_swipe_reasons,
        models_liked=5,
        models_evaluated=5,
        qa_required_human_review=state.get("qa_required_human_review", False)
    )


# ============================================================================
# FastAPI Application
# ============================================================================

# Compile graph
graph = build_graph()

app = FastAPI(
    title="MAS-Eval: Multi-Agent Candidate Evaluation",
    description="AI-powered candidate evaluation using LangGraph",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mas-eval", "version": "1.0.0"}


@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_candidate(request: EvaluationRequest) -> EvaluationResult:
    """Main evaluation endpoint."""
    try:
        # Initialize state
        initial_state: EvaluationState = {
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
            "qa_note": None
        }
        
        # Execute graph
        config = {"configurable": {"thread_id": "evaluation_001"}}
        final_state = await graph.ainvoke(initial_state, config)
        
        # Build result
        result = build_result(final_state)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

