"""
Career Trajectory Evaluation Agent
Analyzes candidate's career progression and experience relevance.
Weight: 35% in final score.
"""

from typing import Any, Callable

from ..models import EvaluationState, OfferData, CandidateData, ScoreOutput


class CareerTrajectoryAgent:
    """Agent for evaluating career trajectory match."""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def evaluate(self, state: EvaluationState, executor: Callable) -> dict[str, Any]:
        """Evaluate career trajectory compatibility."""
        
        # Convert dict to Pydantic models for type-safe access
        offer = OfferData(**state.offer)
        candidate = CandidateData(**state.candidate)
        
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

**JOB OFFER - {offer.job_title} at {offer.company_name}**

Position Context:
- Job Title: {offer.job_title}
- Company: {offer.company_name}
- Experience Required: {offer.experience_required}
- Contract: {offer.contract}
- Preferred Companies: {', '.join(offer.preferred_companies) if offer.preferred_companies else 'None specified'}

**CANDIDATE PROFILE**

Total Experience: {candidate.experience_years} years
Headline: {candidate.heading}

Work History:
{chr(10).join([f"{i+1}. {exp.role} at {exp.company} ({exp.duration if exp.duration else 'Duration not specified'}): {exp.description}" for i, exp in enumerate(candidate.experiences)])}

Education:
{chr(10).join([f"- {edu.degree} in {edu.name} from {edu.institute}" for edu in candidate.educations])}

Evaluate the career trajectory match and provide your assessment."""

        result = await executor(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=ScoreOutput,
            agent_name="Career Trajectory Agent"
        )
        
        return {
            "trajectory_score": result.score,
            "trajectory_reason": result.reason
        }

