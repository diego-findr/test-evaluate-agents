"""
Technical Skills Evaluation Agent
Analyzes candidate's technical competencies against job requirements.
Weight: 50% in final score.
"""

from typing import Any, Callable

from ..models import EvaluationState, OfferData, CandidateData, ScoreOutput


class TechnicalSkillsAgent:
    """Agent for evaluating technical skills match."""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def evaluate(self, state: EvaluationState, executor: Callable) -> dict[str, Any]:
        """Evaluate technical skills compatibility."""
        
        # Convert dict to Pydantic models for type-safe access
        offer = OfferData(**state.offer)
        candidate = CandidateData(**state.candidate)
        
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

**JOB OFFER - {offer.job_title} at {offer.company_name}**

Technical Requirements:
- Mandatory Skills: {', '.join(offer.mandatory_skills) if offer.mandatory_skills else 'None specified'}
- Nice-to-Have Skills: {', '.join(offer.nice_to_have_skills) if offer.nice_to_have_skills else 'None specified'}
- Experience Required: {offer.experience_required}
- Responsibilities: {offer.responsibilities}

**CANDIDATE PROFILE**

Headline: {candidate.heading}
Experience: {candidate.experience_years} years

Technical Skills:
{chr(10).join([f"- {skill.name}" + (f" ({skill.level})" if skill.level else "") for skill in candidate.skills])}

Work Experience:
{chr(10).join([f"- {exp.role} at {exp.company}: {exp.description}" for exp in candidate.experiences[:3]])}

Evaluate the technical match and provide your assessment."""

        result = await executor(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=ScoreOutput,
            agent_name="Technical Skills Agent"
        )
        
        return {
            "technical_score": result.score,
            "technical_reason": result.reason
        }

