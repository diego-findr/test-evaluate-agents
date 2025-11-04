"""
Cultural Fit Evaluation Agent
Analyzes candidate's alignment with company culture and work style.
Weight: 15% in final score.
"""

from typing import Any, Callable

from ..models import EvaluationState, OfferData, CandidateData, ScoreOutput


class CulturalFitAgent:
    """Agent for evaluating cultural fit match."""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def evaluate(self, state: EvaluationState, executor: Callable) -> dict[str, Any]:
        """Evaluate cultural fit compatibility."""
        
        # Convert dict to Pydantic models for type-safe access
        offer = OfferData(**state.offer)
        candidate = CandidateData(**state.candidate)
        
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

**JOB OFFER - {offer.job_title} at {offer.company_name}**

Work Environment:
- Company: {offer.company_name}
- Work Type: {offer.type}
- Contract: {offer.contract}
- Mandatory Languages: {', '.join(offer.mandatory_languages) if offer.mandatory_languages else 'None specified'}
- Nice-to-Have Languages: {', '.join(offer.nice_to_have_languages) if offer.nice_to_have_languages else 'None specified'}
- Description: {offer.description[:300]}...

**CANDIDATE PROFILE**

Languages:
{chr(10).join([f"- {lang.name}: {lang.level}" for lang in candidate.languages])}

Work History Context:
{chr(10).join([f"- {exp.role} at {exp.company}" for exp in candidate.experiences[:5]])}

Total Experience: {candidate.experience_years} years

Evaluate the cultural and work style compatibility and provide your assessment."""

        result = await executor(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=ScoreOutput,
            agent_name="Cultural Fit Agent"
        )
        
        return {
            "cultural_score": result.score,
            "cultural_reason": result.reason
        }

